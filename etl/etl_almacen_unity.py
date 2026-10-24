#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETL — ALMACEN_ANONIMO  ->  DM_ALMACEN_ANONIMO

Fuentes (4): OLTP SQL Server + Plan Excel + Sensores TXT + Conteos TXT.
Destino: 9 dimensiones + 1 hecho (3 medidas, incl. Dias_Permanencia) + 4 staging.
Re-ejecutable: vacía y recarga todo en UNA sola transacción.

Salidas: tablas cargadas + logs/etl_log_*.json + logs/movimientos_rechazados.csv
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

VERSION_ETL = "2.0"

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

T_MIN, T_MAX = 18.0, 27.0      # umbrales de anomalía: temperatura °C
H_MIN, H_MAX = 40.0, 60.0      # umbrales de anomalía: humedad % HR

SALIDA_REAL = {'SALIDA', 'ASIGNACION', 'BAJA', 'OBSOLESCENCIA'}

TABLES_OLTP = ['categoria_componente', 'marca', 'modelo_componente',
               'nivel_criticidad', 'estado_componente', 'ubicacion',
               'proveedor', 'responsable', 'proyecto_servicio',
               'componente', 'inventario', 'entrada', 'detalle_entrada',
               'salida', 'detalle_salida', 'tipo_movimiento',
               'movimiento_componente']

OBLIG_MOV = ['Fecha_Movimiento', 'Cod_Componente', 'Id_Tipo_Movimiento', 'Cantidad']

# DDL espejo para réplica SQLite (solo pruebas; en SQL Server se usa el .sql v2)
DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS Dim_Tiempo (Id_Fecha INTEGER PRIMARY KEY, Fecha DATE NOT NULL, Anio INTEGER NOT NULL, Trimestre INTEGER NOT NULL, Mes INTEGER NOT NULL, Nombre_Mes VARCHAR(20) NOT NULL, Dia_Semana INTEGER NOT NULL, Nombre_Dia VARCHAR(20) NOT NULL, Es_Fin_Semana INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Producto (Id_Producto INTEGER PRIMARY KEY AUTOINCREMENT, Cod_Componente VARCHAR(20) NOT NULL UNIQUE, Descripcion VARCHAR(180) NOT NULL, Categoria VARCHAR(80) NOT NULL, Marca VARCHAR(80) NOT NULL, Modelo VARCHAR(100) NOT NULL, Criticidad VARCHAR(20) NOT NULL, Stock_Minimo DECIMAL(12,2) NOT NULL, Precio_Unitario DECIMAL(12,2) NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Almacen (Id_Almacen INTEGER PRIMARY KEY AUTOINCREMENT, Codigo_Ubicacion VARCHAR(30) NOT NULL UNIQUE, Nombre_Ubicacion VARCHAR(100) NOT NULL, Tipo_Ubicacion VARCHAR(40) NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_TipoMovimiento (Id_TipoMovimiento INTEGER PRIMARY KEY AUTOINCREMENT, Codigo VARCHAR(30) NOT NULL UNIQUE, Nombre VARCHAR(80) NOT NULL, Signo_Stock SMALLINT NOT NULL, Es_Entrada INTEGER NOT NULL, Es_Salida_Real INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Proyecto (Id_Proyecto INTEGER PRIMARY KEY AUTOINCREMENT, Codigo_Proyecto VARCHAR(20) NOT NULL UNIQUE, Nombre_Proyecto VARCHAR(150) NOT NULL, Tipo_Proyecto VARCHAR(60) NOT NULL, Estado VARCHAR(30) NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Responsable (Id_Responsable INTEGER PRIMARY KEY AUTOINCREMENT, Codigo_Responsable VARCHAR(20) NOT NULL UNIQUE, Nombre VARCHAR(150) NOT NULL, Cargo VARCHAR(80) NULL);
CREATE TABLE IF NOT EXISTS Dim_Proveedor (Id_Proveedor INTEGER PRIMARY KEY AUTOINCREMENT, Ruc_Proveedor CHAR(11) NOT NULL UNIQUE, Nombre VARCHAR(150) NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Estado (Id_Estado INTEGER PRIMARY KEY AUTOINCREMENT, Nombre_Estado VARCHAR(30) NOT NULL UNIQUE, Disponible_Stock INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS Dim_Lote (Id_Lote INTEGER PRIMARY KEY AUTOINCREMENT, Codigo_Lote VARCHAR(45) NOT NULL UNIQUE, Cod_Componente VARCHAR(20) NOT NULL, Id_Entrada VARCHAR(20) NOT NULL, Fecha_Ingreso DATE NOT NULL, Cantidad_Lote DECIMAL(12,2) NOT NULL, Codigo_Ubicacion VARCHAR(30) NOT NULL);
CREATE TABLE IF NOT EXISTS Fact_Movimiento (Id_Movimiento_NK BIGINT PRIMARY KEY, Id_Fecha INTEGER NOT NULL, Id_Producto INTEGER NOT NULL, Id_TipoMovimiento INTEGER NOT NULL, Id_Almacen_Origen INTEGER NULL, Id_Almacen_Destino INTEGER NULL, Id_Proyecto INTEGER NULL, Id_Responsable INTEGER NULL, Id_Proveedor INTEGER NULL, Id_Estado_Anterior INTEGER NULL, Id_Estado_Nuevo INTEGER NULL, Id_Lote INTEGER NULL, Cantidad DECIMAL(12,2) NOT NULL, Costo_Total DECIMAL(14,2) NOT NULL, Dias_Permanencia DECIMAL(8,2) NULL);
CREATE TABLE IF NOT EXISTS stg_Plan_Mensual (Anio INTEGER NOT NULL, Mes INTEGER NOT NULL, Categoria VARCHAR(80) NOT NULL, Entradas_Plan DECIMAL(12,2) NOT NULL, Salidas_Plan DECIMAL(12,2) NOT NULL);
CREATE TABLE IF NOT EXISTS stg_Sensores (Timestamp DATETIME NOT NULL, Sensor_Id VARCHAR(20) NOT NULL, Codigo_Ubicacion VARCHAR(30) NOT NULL, Temperatura DECIMAL(5,1) NOT NULL, Humedad DECIMAL(5,1) NOT NULL, Es_Anomalia INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS stg_Conteos (Fecha DATE NOT NULL, Cod_Componente VARCHAR(20) NOT NULL, Codigo_Ubicacion VARCHAR(30) NOT NULL, Stock_Sistema DECIMAL(12,2) NOT NULL, Stock_Fisico DECIMAL(12,2) NOT NULL, Diferencia DECIMAL(12,2) NOT NULL, Responsable VARCHAR(20) NOT NULL, Resultado VARCHAR(20) NOT NULL, Exactitud_Linea DECIMAL(6,4) NOT NULL);
CREATE TABLE IF NOT EXISTS stg_Inventario_Actual (Cod_Componente VARCHAR(20) NOT NULL, Id_Ubicacion INTEGER NOT NULL, Stock_Disponible DECIMAL(12,2) NOT NULL, Stock_Minimo DECIMAL(12,2) NOT NULL, Criticidad VARCHAR(20) NOT NULL);
"""


def parse_args():
    ap = argparse.ArgumentParser(description='ETL v2 ALMACEN_ANONIMO -> DM_ALMACEN_ANONIMO')
    ap.add_argument('--datos', required=True, help='carpeta con Plan/Sensores/Conteos')
    ap.add_argument('--log', required=True, help='carpeta de salida del log JSON y CSV')
    ap.add_argument('--oltp-url', default=None, help='override de OLTP_URL')
    ap.add_argument('--dm-url', default=None, help='override de DM_URL')
    return ap.parse_args()


def read_table(eng, t):
    # dbo. en SQL Server; sin esquema en SQLite
    try:
        return pd.read_sql('SELECT * FROM dbo.%s' % t, eng)
    except Exception:
        return pd.read_sql('SELECT * FROM %s' % t, eng)


def main():
    args = parse_args()
    oltp_url = args.oltp_url or os.environ.get('OLTP_URL')
    dm_url = args.dm_url or os.environ.get('DM_URL')
    if not oltp_url or not dm_url:
        sys.exit('ERROR: defina OLTP_URL y DM_URL (o use --oltp-url/--dm-url).')
    os.makedirs(args.log, exist_ok=True)
    eng_o = create_engine(oltp_url)
    eng_d = create_engine(dm_url)
    is_sqlite_dm = dm_url.startswith('sqlite')

    # ---------------- EXTRACCIÓN ----------------
    t0 = time.time()
    oltp = {t: read_table(eng_o, t) for t in TABLES_OLTP}
    plan = pd.read_excel(os.path.join(args.datos, 'Plan_Demanda_2026.xlsx'),
                         sheet_name='Plan_Mensual')
    sen = pd.read_csv(os.path.join(args.datos, 'Sensores_Almacen_2026.txt'),
                      parse_dates=['timestamp'])
    con = pd.read_csv(os.path.join(args.datos, 'Conteos_Ciclicos_2026.txt'),
                      parse_dates=['fecha'])
    t_extraccion = time.time() - t0

    # ---------------- PERFILADO + LIMPIEZA ----------------
    t1 = time.time()
    mov = oltp['movimiento_componente'].copy()
    mov['Cantidad'] = pd.to_numeric(mov['Cantidad'], errors='coerce')
    mov['Fecha_Movimiento'] = pd.to_datetime(mov['Fecha_Movimiento'], errors='coerce')
    comp_codes = set(oltp['componente']['Cod_Componente'].astype(str))

    m_nulo = mov[OBLIG_MOV].isna().any(axis=1)
    m_nopos = mov['Cantidad'] <= 0
    m_sinprod = ~mov['Cod_Componente'].astype(str).isin(comp_codes)
    m_dup = mov.duplicated(subset=['Id_Movimiento'], keep='first')

    log = {}
    log['registros_origen'] = int(len(mov))
    log['nulos_obligatorios_antes'] = int(m_nulo.sum())
    log['cantidad_no_positiva_antes'] = int(m_nopos.sum())
    log['sin_producto_antes'] = int(m_sinprod.sum())
    log['duplicados_antes'] = int(m_dup.sum())

    bad = (m_nulo | m_nopos | m_sinprod | m_dup)
    rech = mov[bad].copy()
    motivos = []
    for i in rech.index:
        ms = []
        if m_nulo.get(i, False):
            ms.append('nulo_obligatorio')
        if m_nopos.get(i, False):
            ms.append('cantidad_no_positiva')
        if m_sinprod.get(i, False):
            ms.append('sin_producto')
        if m_dup.get(i, False):
            ms.append('duplicado')
        motivos.append('+'.join(ms))
    rech['Motivo_Rechazo'] = motivos
    rech.to_csv(os.path.join(args.log, 'movimientos_rechazados.csv'), index=False)
    movv = mov[~bad].copy().reset_index(drop=True)
    log['registros_cargados'] = int(len(movv))
    log['registros_rechazados'] = int(len(rech))

    # ---------------- TRANSFORMACIÓN: dimensiones ----------------
    comp = oltp['componente'].copy()
    modelo = oltp['modelo_componente'].copy()
    marca = oltp['marca'].copy()
    categ = oltp['categoria_componente'].copy()
    crit = oltp['nivel_criticidad'].copy()
    ubi = oltp['ubicacion'].copy()
    tipo = oltp['tipo_movimiento'].copy()
    estado = oltp['estado_componente'].copy()
    entrada = oltp['entrada'].copy()
    det_e = oltp['detalle_entrada'].copy()

    # Tiempo: unión de todas las fechas fuente, rango continuo
    fechas = pd.concat([
        movv['Fecha_Movimiento'].dt.date,
        pd.to_datetime(entrada['Fecha_Recepcion']).dt.date,
        pd.to_datetime(oltp['salida']['Fecha_Solicitud']).dt.date,
        pd.to_datetime(oltp['salida']['Fecha_Despacho'], errors='coerce').dt.date,
        con['fecha'].dt.date, sen['timestamp'].dt.date,
    ]).dropna()
    dias = pd.date_range(fechas.min(), fechas.max(), freq='D')
    dim_t = pd.DataFrame({'_f': dias})
    dim_t['Id_Fecha'] = dim_t['_f'].dt.strftime('%Y%m%d').astype(int)
    dim_t['Fecha'] = dim_t['_f'].dt.date
    dim_t['Anio'] = dim_t['_f'].dt.year
    dim_t['Trimestre'] = (dim_t['_f'].dt.month - 1) // 3 + 1
    dim_t['Mes'] = dim_t['_f'].dt.month
    dim_t['Nombre_Mes'] = dim_t['Mes'].map(lambda m: MESES[m - 1])
    dim_t['Dia_Semana'] = dim_t['_f'].dt.isocalendar().day.astype(int)
    dim_t['Nombre_Dia'] = dim_t['Dia_Semana'].map(lambda d: DIAS[d - 1])
    dim_t['Es_Fin_Semana'] = (dim_t['Dia_Semana'] >= 6).astype(int)
    dim_t = dim_t.drop(columns=['_f'])

    # Producto
    p = comp.merge(modelo, on='Id_Modelo', how='left', suffixes=('', '_mod'))
    p = p.merge(marca, on='Id_Marca', how='left')
    p = p.merge(categ, on='Id_Categoria', how='left')
    p = p.merge(crit, on='Id_Criticidad', how='left')
    dim_p = pd.DataFrame({
        'Cod_Componente': p['Cod_Componente'].astype(str),
        'Descripcion': p['Descripcion'].astype(str),
        'Categoria': p['Nombre_Categoria'].astype(str),
        'Marca': p['Nombre_Marca'].astype(str),
        'Modelo': p['Nombre_Modelo'].astype(str),
        'Criticidad': p['Nivel_Criticidad'].astype(str),
        'Stock_Minimo': pd.to_numeric(p['Stock_Minimo'], errors='coerce').fillna(0),
        'Precio_Unitario': pd.to_numeric(p['Precio_Unitario'], errors='coerce').fillna(0),
    }).drop_duplicates(subset=['Cod_Componente']).reset_index(drop=True)

    dim_a = pd.DataFrame({
        'Codigo_Ubicacion': ubi['Codigo_Ubicacion'].astype(str),
        'Nombre_Ubicacion': ubi['Nombre_Ubicacion'].astype(str),
        'Tipo_Ubicacion': ubi['Tipo_Ubicacion'].astype(str),
    }).drop_duplicates(subset=['Codigo_Ubicacion']).reset_index(drop=True)

    cod_tipo = tipo['Codigo'].astype(str)
    dim_tm = pd.DataFrame({
        'Codigo': cod_tipo,
        'Nombre': tipo['Nombre'].astype(str),
        'Signo_Stock': pd.to_numeric(tipo['Signo_Stock']).astype(int),
        'Es_Entrada': (cod_tipo == 'INGRESO').astype(int),
        'Es_Salida_Real': cod_tipo.isin(SALIDA_REAL).astype(int),
    }).drop_duplicates(subset=['Codigo']).reset_index(drop=True)

    pry = oltp['proyecto_servicio'].copy()
    dim_pry = pd.DataFrame({
        'Codigo_Proyecto': pry['Id_Proyecto'].astype(str),
        'Nombre_Proyecto': pry['Nombre_Proyecto'].astype(str),
        'Tipo_Proyecto': pry['Tipo_Proyecto'].astype(str),
        'Estado': pry['Estado'].astype(str),
    }).drop_duplicates(subset=['Codigo_Proyecto']).reset_index(drop=True)

    resp = oltp['responsable'].copy()  # minimización: sin Email
    dim_resp = pd.DataFrame({
        'Codigo_Responsable': resp['Id_Responsable'].astype(str),
        'Nombre': resp['Nom_Responsable'].astype(str),
        'Cargo': resp['Cargo'].where(resp['Cargo'].notna(), None),
    }).drop_duplicates(subset=['Codigo_Responsable']).reset_index(drop=True)

    prov = oltp['proveedor'].copy()  # minimización: sin teléfono/email/dirección
    dim_prov = pd.DataFrame({
        'Ruc_Proveedor': prov['Ruc_Proveedor'].astype(str),
        'Nombre': prov['Nom_Proveedor'].astype(str),
    }).drop_duplicates(subset=['Ruc_Proveedor']).reset_index(drop=True)

    dim_e = pd.DataFrame({
        'Nombre_Estado': estado['Nombre_Estado'].astype(str),
        'Disponible_Stock': pd.to_numeric(estado['Disponible_Stock']).astype(int),
    }).drop_duplicates(subset=['Nombre_Estado']).reset_index(drop=True)

    # Lote = 1 línea de entrada
    ent_f = pd.to_datetime(entrada['Fecha_Recepcion']).dt.date
    ent_fmap = dict(zip(entrada['Id_Entrada'].astype(str), ent_f))
    ubi_cod = dict(zip(pd.to_numeric(ubi['Id_Ubicacion'], errors='coerce'),
                       ubi['Codigo_Ubicacion'].astype(str)))
    dim_l = pd.DataFrame({
        'Codigo_Lote': det_e['Id_Entrada'].astype(str) + '-' + det_e['Cod_Componente'].astype(str),
        'Cod_Componente': det_e['Cod_Componente'].astype(str),
        'Id_Entrada': det_e['Id_Entrada'].astype(str),
        'Fecha_Ingreso': det_e['Id_Entrada'].astype(str).map(ent_fmap),
        'Cantidad_Lote': pd.to_numeric(det_e['Cantidad_Recibida'], errors='coerce').fillna(0),
        'Codigo_Ubicacion': pd.to_numeric(det_e['Id_Ubicacion_Destino'], errors='coerce').map(ubi_cod),
    })
    dim_l['Codigo_Ubicacion'] = dim_l['Codigo_Ubicacion'].fillna('DESCONOCIDA')
    dim_l = dim_l.drop_duplicates(subset=['Codigo_Lote']).reset_index(drop=True)

    # ---------------- TRANSFORMACIÓN: staging ----------------
    stg_plan = pd.DataFrame({
        'Anio': pd.to_numeric(plan['Anio']).astype(int),
        'Mes': pd.to_numeric(plan['Mes']).astype(int),
        'Categoria': plan['Categoria'].astype(str),
        'Entradas_Plan': pd.to_numeric(plan['Entradas_Plan']),
        'Salidas_Plan': pd.to_numeric(plan['Salidas_Plan']),
    })
    sen_t = pd.to_numeric(sen['temperatura_c'], errors='coerce')
    sen_h = pd.to_numeric(sen['humedad_pct'], errors='coerce')
    es_anom = ((sen_t < T_MIN) | (sen_t > T_MAX) | (sen_h < H_MIN) | (sen_h > H_MAX)).astype(int)
    stg_sen = pd.DataFrame({
        'Timestamp': pd.to_datetime(sen['timestamp']),
        'Sensor_Id': sen['sensor_id'].astype(str),
        'Codigo_Ubicacion': sen['codigo_ubicacion'].astype(str),
        'Temperatura': sen_t, 'Humedad': sen_h, 'Es_Anomalia': es_anom,
    })
    log['anomalias_sensores'] = int(es_anom.sum())
    log['lecturas_sensores'] = int(len(stg_sen))

    c_sis = pd.to_numeric(con['stock_sistema'], errors='coerce')
    c_fis = pd.to_numeric(con['stock_fisico'], errors='coerce')
    c_dif_file = pd.to_numeric(con['diferencia'], errors='coerce')
    c_dif = (c_fis - c_sis)
    recalc = (c_dif_file.fillna(c_dif) != c_dif).fillna(False)
    log['conteos_con_diferencia_recalculada'] = int(recalc.sum())
    denom = pd.concat([c_sis, c_fis], axis=1).max(axis=1)
    exact = (1 - c_dif.abs() / denom.where(denom != 0, 1)).where(denom != 0, 1.0)
    stg_con = pd.DataFrame({
        'Fecha': pd.to_datetime(con['fecha']).dt.date,
        'Cod_Componente': con['cod_componente'].astype(str),
        'Codigo_Ubicacion': con['codigo_ubicacion'].astype(str),
        'Stock_Sistema': c_sis, 'Stock_Fisico': c_fis, 'Diferencia': c_dif,
        'Responsable': con['responsable'].astype(str),
        'Resultado': con['resultado'].astype(str),
        'Exactitud_Linea': exact.round(4),
    })

    inv = oltp['inventario'].copy()
    inv = inv.merge(comp[['Cod_Componente', 'Stock_Minimo', 'Id_Criticidad']],
                    on='Cod_Componente', how='left')
    inv = inv.merge(crit[['Id_Criticidad', 'Nivel_Criticidad']],
                    on='Id_Criticidad', how='left')
    stg_inv = pd.DataFrame({
        'Cod_Componente': inv['Cod_Componente'].astype(str),
        'Id_Ubicacion': pd.to_numeric(inv['Id_Ubicacion']).astype(int),
        'Stock_Disponible': pd.to_numeric(inv['Cantidad_Disponible']),
        'Stock_Minimo': pd.to_numeric(inv['Stock_Minimo']),
        'Criticidad': inv['Nivel_Criticidad'].astype(str),
    })

    # ---------------- CARGA (una sola transacción) ----------------
    with eng_d.begin() as conn:
        if is_sqlite_dm:
            for stmt in [s for s in DDL_SQLITE.split(';') if s.strip()]:
                conn.execute(text(stmt))
        for t in ['Fact_Movimiento', 'stg_Plan_Mensual', 'stg_Sensores',
                  'stg_Conteos', 'stg_Inventario_Actual', 'Dim_Lote',
                  'Dim_Tiempo', 'Dim_Producto', 'Dim_Almacen',
                  'Dim_TipoMovimiento', 'Dim_Proyecto', 'Dim_Responsable',
                  'Dim_Proveedor', 'Dim_Estado']:
            conn.execute(text('DELETE FROM %s' % t))

        def put(df, tabla):
            df.to_sql(tabla, conn, if_exists='append', index=False)

        def keymap(tabla, idcol, natcol):
            r = conn.execute(text('SELECT %s, %s FROM %s' % (idcol, natcol, tabla))).fetchall()
            return {str(n): k for k, n in r}

        put(dim_t, 'Dim_Tiempo')
        put(dim_p, 'Dim_Producto')
        put(dim_a, 'Dim_Almacen')
        put(dim_tm, 'Dim_TipoMovimiento')
        put(dim_pry, 'Dim_Proyecto')
        put(dim_resp, 'Dim_Responsable')
        put(dim_prov, 'Dim_Proveedor')
        put(dim_e, 'Dim_Estado')
        put(dim_l, 'Dim_Lote')

        m_fec = keymap('Dim_Tiempo', 'Id_Fecha', 'Id_Fecha')
        m_prod = keymap('Dim_Producto', 'Id_Producto', 'Cod_Componente')
        m_alm = keymap('Dim_Almacen', 'Id_Almacen', 'Codigo_Ubicacion')
        m_tip = keymap('Dim_TipoMovimiento', 'Id_TipoMovimiento', 'Codigo')
        m_pry = keymap('Dim_Proyecto', 'Id_Proyecto', 'Codigo_Proyecto')
        m_resp = keymap('Dim_Responsable', 'Id_Responsable', 'Codigo_Responsable')
        m_prov = keymap('Dim_Proveedor', 'Id_Proveedor', 'Ruc_Proveedor')
        m_est = keymap('Dim_Estado', 'Id_Estado', 'Nombre_Estado')
        m_lote = keymap('Dim_Lote', 'Id_Lote', 'Codigo_Lote')

        # puentes OLTP -> natural
        tip_cod = dict(zip(tipo['Id_Tipo_Movimiento'].astype(int).astype(str), cod_tipo))
        est_nom = dict(zip(pd.to_numeric(estado['Id_Estado'], errors='coerce').astype(int).astype(str),
                           estado['Nombre_Estado'].astype(str)))
        ent_ruc = dict(zip(entrada['Id_Entrada'].astype(str),
                           entrada['Ruc_Proveedor'].astype(str)))
        precio = dict(zip(comp['Cod_Componente'].astype(str),
                          pd.to_numeric(comp['Precio_Unitario'], errors='coerce').fillna(0)))

        # FIFO por producto para Dias_Permanencia (solo salidas reales)
        lotes = {}
        dl = dim_l.sort_values(['Cod_Componente', 'Fecha_Ingreso', 'Codigo_Lote'])
        for _, r in dl.iterrows():
            lotes.setdefault(str(r['Cod_Componente']), []).append(
                [pd.to_datetime(r['Fecha_Ingreso']).date(), float(r['Cantidad_Lote'])])
        tipo_es_sal = dict(zip(cod_tipo, cod_tipo.isin(SALIDA_REAL)))
        movv['_cod'] = movv['Id_Tipo_Movimiento'].astype(int).astype(str).map(tip_cod)
        movv['_es_sal'] = movv['_cod'].map(tipo_es_sal).fillna(False)
        movv['_fecha'] = movv['Fecha_Movimiento'].dt.date
        movv = movv.sort_values(['_fecha', 'Id_Movimiento']).reset_index(drop=True)
        dias_perm, sin_lote = [], 0
        for _, r in movv.iterrows():
            if not r['_es_sal']:
                dias_perm.append(None)
                continue
            need = float(r['Cantidad'])
            acc, tot = 0.0, 0.0
            for lot in lotes.get(str(r['Cod_Componente']), []):
                if need <= 0:
                    break
                if lot[1] <= 0:
                    continue
                take = min(need, lot[1])
                age = (r['_fecha'] - lot[0]).days
                acc += take * age
                tot += take
                lot[1] -= take
                need -= take
            if need > 1e-9:
                sin_lote += 1
                dias_perm.append(None)
            else:
                dias_perm.append(round(acc / tot, 2) if tot else None)
        movv['Dias_Permanencia'] = dias_perm
        log['salidas_sin_lote_suficiente'] = int(sin_lote)

        def _fk_str(series, m):
            """Llave natural -> subrogada; cualquier nulo (None/NaN/NA) -> None."""
            return [m.get(str(v)) if not pd.isna(v) else None for v in series]

        def _fk_estado(series):
            """Id_Estado OLTP -> Dim_Estado; nulos o inválidos -> None."""
            out = []
            for v in series:
                if pd.isna(v):
                    out.append(None)
                    continue
                try:
                    out.append(m_est.get(est_nom.get(str(int(float(v))))))
                except (TypeError, ValueError):
                    out.append(None)
            return out

        cod_ubi_mov = lambda s: pd.to_numeric(s, errors='coerce').map(ubi_cod)
        fact = pd.DataFrame({
            'Id_Movimiento_NK': movv['Id_Movimiento'].astype(int),
            'Id_Fecha': movv['_fecha'].map(lambda d: m_fec.get(str(int(d.strftime('%Y%m%d'))))),
            'Id_Producto': movv['Cod_Componente'].astype(str).map(m_prod),
            'Id_TipoMovimiento': movv['_cod'].map(m_tip),
            'Id_Almacen_Origen': cod_ubi_mov(movv['Id_Ubicacion_Origen']).map(m_alm),
            'Id_Almacen_Destino': cod_ubi_mov(movv['Id_Ubicacion_Destino']).map(m_alm),
            'Id_Proyecto': _fk_str(movv['Id_Proyecto'], m_pry),
            'Id_Responsable': _fk_str(movv['Id_Responsable'], m_resp),
            'Id_Proveedor': _fk_str(movv['Id_Entrada'].map(ent_ruc), m_prov),
            'Id_Estado_Anterior': _fk_estado(movv['Id_Estado_Anterior']),
            'Id_Estado_Nuevo': _fk_estado(movv['Id_Estado_Nuevo']),
            'Id_Lote': [
                m_lote.get('%s-%s' % (e, c)) if t == 'INGRESO' else None
                for e, c, t in zip(movv['Id_Entrada'].astype(str),
                                   movv['Cod_Componente'].astype(str), movv['_cod'])],
            'Cantidad': movv['Cantidad'].astype(float),
            'Costo_Total': (movv['Cantidad'].astype(float)
                            * movv['Cod_Componente'].astype(str).map(precio)).round(2),
            'Dias_Permanencia': movv['Dias_Permanencia'],
        })
        put(fact, 'Fact_Movimiento')
        put(stg_plan, 'stg_Plan_Mensual')
        put(stg_sen, 'stg_Sensores')
        put(stg_con, 'stg_Conteos')
        put(stg_inv, 'stg_Inventario_Actual')

    t_transf = time.time() - t1

    # ---------------- MÉTRICAS DESPUÉS + RECONCILIACIÓN ----------------
    log['nulos_obligatorios_despues'] = int(
        fact[['Id_Movimiento_NK', 'Id_Fecha', 'Id_Producto',
              'Id_TipoMovimiento', 'Cantidad', 'Costo_Total']].isna().any(axis=1).sum())
    log['cantidad_no_positiva_despues'] = int((fact['Cantidad'] <= 0).sum())
    log['sin_producto_despues'] = int(fact['Id_Producto'].isna().sum())
    log['duplicados_despues'] = int(fact.duplicated(subset=['Id_Movimiento_NK']).sum())
    ob = ['Id_Movimiento_NK', 'Id_Fecha', 'Id_Producto',
          'Id_TipoMovimiento', 'Cantidad', 'Costo_Total']
    log['completitud_pct'] = round(
        100.0 * (~fact[ob].isna().any(axis=1)).mean() if len(fact) else 0.0, 2)
    log['filas_hecho'] = int(len(fact))
    es_ent = movv['_cod'] == 'INGRESO'
    log['unidades_por_es_entrada'] = {
        '0': float(movv.loc[~es_ent, 'Cantidad'].sum()),
        '1': float(movv.loc[es_ent, 'Cantidad'].sum()),
    }
    log['reconciliacion_ok'] = bool(
        log['filas_hecho'] == log['registros_cargados']
        and log['registros_origen'] == log['registros_cargados'] + log['registros_rechazados']
        and log['salidas_sin_lote_suficiente'] == 0)
    log['t_extraccion_s'] = round(t_extraccion, 2)
    log['t_transf_carga_s'] = round(t_transf, 2)
    log['version_etl'] = VERSION_ETL
    log['fecha_ejecucion'] = datetime.now().isoformat(timespec='seconds')

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(args.log, 'etl_log_%s.json' % stamp)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print('ETL v%s OK: %d cargados, %d rechazados, completitud %s%%, '
          'reconciliacion=%s' % (VERSION_ETL, log['registros_cargados'],
                                 log['registros_rechazados'], log['completitud_pct'],
                                 log['reconciliacion_ok']))
    print('Log:', log_path)


if __name__ == '__main__':
    main()
