#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calcular_kpis.py — Reconstruye el contenido del datamart DM_ALMACEN_ANONIMO a
partir de los scripts SQL del repositorio y de las 3 fuentes no-OLTP, aplicando
las MISMAS reglas del ETL v2.0 (etl/etl_almacen_unity.py).

Propósito:
  1. Verificar de forma independiente las cifras oficiales del informe
     (filas del hecho, conciliación, TPP, rotación, inversión, VM, anomalías,
     exactitud de conteos).
  2. Generar una copia del datamart en CSV (powerbi/respaldo/) para construir o
     refrescar el dashboard de Power BI sin depender de SQL Server.

Uso:
    python analisis/calcular_kpis.py

Salidas:
    analisis/salidas/kpis.json          -> métricas verificadas
    powerbi/respaldo/*.csv              -> 14 tablas del datamart (equivalente al modelo)
"""
import csv
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[1]
SALIDAS = RAIZ / "analisis" / "salidas"
RESPALDO = RAIZ / "powerbi" / "respaldo"
SALIDAS.mkdir(parents=True, exist_ok=True)
RESPALDO.mkdir(parents=True, exist_ok=True)

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Reglas de negocio del datamart (idénticas al ETL)
TIPOS_ENTRADA = {"INGRESO", "DEVOLUCION", "TRASLADO_ENTRADA", "MANTENIMIENTO_ENTRADA"}
TIPOS_SALIDA_REAL = {"SALIDA", "ASIGNACION", "BAJA", "OBSOLESCENCIA"}
TEMP_MIN, TEMP_MAX, HUM_MIN, HUM_MAX = 18.0, 27.0, 40.0, 60.0


# ---------------------------------------------------------------- utilidades
def parse_sql(path: Path):
    """Extrae INSERT INTO ... VALUES de un script T-SQL a listas de dicts."""
    txt = path.read_text(encoding="utf-8")
    pat = re.compile(r"INSERT INTO (?:dbo\.)?(\w+)\s*(?:\((.*?)\))?\s*VALUES(.*?);\s*", re.S)
    rows = defaultdict(list)
    for m in pat.finditer(txt):
        tabla = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")] if m.group(2) else None
        body = m.group(3).replace("\n", " ")
        grupos, depth, inq, cur = [], 0, False, ""
        for ch in body:
            if ch == "'":
                inq = not inq
            if not inq:
                if ch == "(":
                    depth += 1
                    if depth == 1:
                        cur = ""
                        continue
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        grupos.append(cur)
                        continue
            if depth >= 1:
                cur += ch
        for g in grupos:
            partes, cur, inq = [], "", False
            for ch in g:
                if ch == "'":
                    inq = not inq
                    cur += ch
                elif ch == "," and not inq:
                    partes.append(cur.strip())
                    cur = ""
                else:
                    cur += ch
            partes.append(cur.strip())
            d = {}
            for i, c in enumerate(cols or []):
                v = partes[i] if i < len(partes) else None
                if v is not None:
                    v = v.strip().strip("'")
                    if v.upper() == "NULL":
                        v = None
                d[c] = v
            rows[tabla].append(d)
    return rows


def escribir_csv(nombre, campos, filas):
    with open(RESPALDO / nombre, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, delimiter=";")
        w.writeheader()
        for f in filas:
            w.writerow({k: ("" if f.get(k) is None else f.get(k)) for k in campos})
    print(f"  {nombre:<28} {len(filas):>6} filas")


def main():
    print("== 1. Lectura de fuentes ==")
    oltp = parse_sql(RAIZ / "scripts" / "01_OLTP_ALMACEN_ANONIMIZADO.sql")
    extra = parse_sql(RAIZ / "scripts" / "02_DATOS_ANONIMOS_ALMACEN.sql")
    # El script 02 reemplaza los movimientos y transacciones y amplía los maestros
    transaccionales = {"movimiento_componente", "entrada", "salida", "detalle_entrada",
                       "detalle_salida", "inventario", "asignacion_componente",
                       "mantenimiento_componente", "reemplazo_componente"}
    for t, filas in extra.items():
        oltp[t] = filas if t in transaccionales else oltp.get(t, []) + filas

    cat = {i + 1: c["Nombre_Categoria"] for i, c in enumerate(oltp["categoria_componente"])}
    marca = {i + 1: c["Nombre_Marca"] for i, c in enumerate(oltp["marca"])}
    crit = [c["Nivel_Criticidad"] for c in oltp["nivel_criticidad"]]
    ubi = {i + 1: u for i, u in enumerate(oltp["ubicacion"])}
    modelo = {}
    for i, m in enumerate(oltp["modelo_componente"], 1):
        modelo[i] = {"Categoria": cat[int(m["Id_Categoria"])],
                     "Marca": marca[int(m["Id_Marca"])],
                     "Modelo": m["Nombre_Modelo"]}
    proyecto = {p["Id_Proyecto"]: p for p in oltp["proyecto_servicio"]}
    tipo_mov = {str(i + 1): t for i, t in enumerate(oltp["tipo_movimiento"])}
    responsables = {r["Id_Responsable"]: r for r in oltp["responsable"]}
    proveedores = {p["Ruc_Proveedor"]: p for p in oltp["proveedor"]}
    estados = oltp["estado_componente"]
    entradas = {e["Id_Entrada"]: e for e in oltp["entrada"]}

    componentes = {}
    for c in oltp["componente"]:
        mm = modelo[int(c["Id_Modelo"])]
        componentes[c["Cod_Componente"]] = {
            **c, **mm, "Criticidad": crit[int(c["Id_Criticidad"]) - 1]}

    movs = sorted(oltp["movimiento_componente"], key=lambda x: x["Fecha_Movimiento"])
    plan_rows = []
    wb = openpyxl.load_workbook(RAIZ / "datos" / "Plan_Demanda_2026.xlsx", data_only=True)
    ws = wb["Plan_Mensual"]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[0] is not None and isinstance(r[0], int):
            plan_rows.append({"Anio": int(r[0]), "Mes": int(r[1]), "Categoria": r[2],
                              "Entradas_Plan": float(r[3]), "Salidas_Plan": float(r[4])})
    sensores = list(csv.DictReader(open(RAIZ / "datos" / "Sensores_Almacen_2026.txt", encoding="utf-8")))
    conteos = list(csv.DictReader(open(RAIZ / "datos" / "Conteos_Ciclicos_2026.txt", encoding="utf-8")))

    print(f"  OLTP movimientos: {len(movs)} | componentes: {len(componentes)} | "
          f"plan: {len(plan_rows)} | sensores: {len(sensores)} | conteos: {len(conteos)}")

    print("== 2. Perfilado y calidad (antes de transformar) ==")
    obligatorios = ["Fecha_Movimiento", "Cod_Componente", "Id_Tipo_Movimiento", "Cantidad"]
    nulos = sum(1 for m in movs for k in obligatorios if not m.get(k))
    no_pos = sum(1 for m in movs if int(m["Cantidad"]) <= 0)
    sin_prod = sum(1 for m in movs if m["Cod_Componente"] not in componentes)
    dup = len(movs) - len({(m["Fecha_Movimiento"], m["Cod_Componente"], m["Cantidad"],
                            m.get("Id_Entrada"), m.get("Id_Salida")) for m in movs})
    rechazados = nulos + no_pos + sin_prod + dup

    print("== 3. Transformación (lotes FIFO, permanencia, anomalías, exactitud) ==")
    lotes = defaultdict(deque)          # componente -> deque[[fecha, cantidad, codigo_lote, id_entrada]]
    dim_lote = []
    for m in movs:
        if m.get("Id_Entrada"):
            fecha = datetime.fromisoformat(m["Fecha_Movimiento"])
            cod = f"{m['Id_Entrada']}-{m['Cod_Componente']}"
            dim_lote.append({"Codigo_Lote": cod, "Cod_Componente": m["Cod_Componente"],
                             "Id_Entrada": m["Id_Entrada"], "Fecha_Ingreso": fecha.date().isoformat(),
                             "Cantidad_Lote": int(m["Cantidad"]),
                             "Codigo_Ubicacion": ubi[int(m["Id_Ubicacion_Destino"])]["Codigo_Ubicacion"]})
            lotes[m["Cod_Componente"]].append([fecha, int(m["Cantidad"]), cod])

    permanencia = {}      # índice de movimiento -> (dias, codigo_lote)
    for i, m in enumerate(movs):
        if not m.get("Id_Salida"):
            continue
        qq = int(m["Cantidad"])
        fecha = datetime.fromisoformat(m["Fecha_Movimiento"])
        total, unidades = 0.0, 0
        while qq > 0 and lotes[m["Cod_Componente"]]:
            lote = lotes[m["Cod_Componente"]][0]
            toma = min(qq, lote[1])
            total += (fecha - lote[0]).days * toma
            unidades += toma
            lote[1] -= toma
            qq -= toma
            cod_lote = lote[2]
            if lote[1] == 0:
                lotes[m["Cod_Componente"]].popleft()
        if unidades:
            permanencia[i] = (round(total / unidades, 2), cod_lote)

    sensores_norm = []
    for s in sensores:
        t, h = float(s["temperatura_c"]), float(s["humedad_pct"])
        anom = not (TEMP_MIN <= t <= TEMP_MAX) or not (HUM_MIN <= h <= HUM_MAX)
        sensores_norm.append({"Timestamp": s["timestamp"], "Sensor_Id": s["sensor_id"],
                              "Codigo_Ubicacion": s["codigo_ubicacion"],
                              "Temperatura": t, "Humedad": h, "Es_Anomalia": int(anom)})

    conteos_norm = []
    for c in conteos:
        sis, fis = int(c["stock_sistema"]), int(c["stock_fisico"])
        exactitud = 1 - abs(sis - fis) / max(sis, fis, 1)
        conteos_norm.append({"Fecha": c["fecha"], "Cod_Componente": c["cod_componente"],
                             "Codigo_Ubicacion": c["codigo_ubicacion"], "Stock_Sistema": sis,
                             "Stock_Fisico": fis, "Diferencia": fis - sis,
                             "Responsable": c["responsable"], "Resultado": c["resultado"],
                             "Exactitud_Linea": round(exactitud, 4)})

    print("== 4. Construcción de dimensiones y del hecho ==")
    dim_producto = []
    id_prod = {}
    for i, cod in enumerate(sorted(componentes), 1):
        c = componentes[cod]
        id_prod[cod] = i
        dim_producto.append({"Id_Producto": i, "Cod_Componente": cod, "Descripcion": c["Descripcion"],
                             "Categoria": c["Categoria"], "Marca": c["Marca"], "Modelo": c["Modelo"],
                             "Criticidad": c["Criticidad"], "Stock_Minimo": float(c["Stock_Minimo"]),
                             "Precio_Unitario": float(c["Precio_Unitario"])})

    dim_almacen = [{"Id_Almacen": i, "Codigo_Ubicacion": u["Codigo_Ubicacion"],
                    "Nombre_Ubicacion": u["Nombre_Ubicacion"],
                    "Tipo_Ubicacion": u["Tipo_Ubicacion"]} for i, u in ubi.items()]

    dim_tipo = []
    for i, t in tipo_mov.items():
        cod = t["Codigo"]
        dim_tipo.append({"Id_TipoMovimiento": int(i), "Codigo": cod, "Nombre": t["Nombre"],
                         "Signo_Stock": int(t["Signo_Stock"]),
                         "Es_Entrada": int(cod in TIPOS_ENTRADA),
                         "Es_Salida_Real": int(cod in TIPOS_SALIDA_REAL)})

    dim_proyecto = [{"Id_Proyecto": i, "Codigo_Proyecto": p["Id_Proyecto"],
                     "Nombre_Proyecto": p["Nombre_Proyecto"],
                     "Tipo_Proyecto": p["Tipo_Proyecto"], "Estado": p["Estado"]}
                    for i, p in enumerate(proyecto.values(), 1)]
    id_proy = {p["Codigo_Proyecto"]: p["Id_Proyecto"] for p in dim_proyecto}

    dim_responsable = [{"Id_Responsable": i, "Codigo_Responsable": r["Id_Responsable"],
                        "Nombre": r["Nom_Responsable"], "Cargo": r["Cargo"]}
                       for i, r in enumerate(responsables.values(), 1)]
    id_resp = {r["Codigo_Responsable"]: r["Id_Responsable"] for r in dim_responsable}

    dim_proveedor = [{"Id_Proveedor": i, "Ruc_Proveedor": p["Ruc_Proveedor"],
                      "Nombre": p["Nom_Proveedor"]}
                     for i, p in enumerate(proveedores.values(), 1)]
    id_prov = {p["Ruc_Proveedor"]: p["Id_Proveedor"] for p in dim_proveedor}

    dim_estado = [{"Id_Estado": i, "Nombre_Estado": e["Nombre_Estado"],
                   "Disponible_Stock": int(e["Disponible_Stock"])}
                  for i, e in enumerate(estados, 1)]
    id_est = {e["Nombre_Estado"]: e["Id_Estado"] for e in dim_estado}

    dim_lote_final = [{"Id_Lote": i, **l} for i, l in enumerate(dim_lote, 1)]
    id_lote = {l["Codigo_Lote"]: l["Id_Lote"] for l in dim_lote_final}

    fechas = sorted({m["Fecha_Movimiento"][:10] for m in movs})
    dim_tiempo = []
    for f in fechas:
        d = datetime.fromisoformat(f)
        dim_tiempo.append({"Id_Fecha": int(d.strftime("%Y%m%d")), "Fecha": f, "Anio": d.year,
                           "Trimestre": (d.month - 1) // 3 + 1, "Mes": d.month,
                           "Nombre_Mes": MESES[d.month - 1], "Dia_Semana": d.isoweekday(),
                           "Nombre_Dia": DIAS[d.weekday()], "Es_Fin_Semana": int(d.isoweekday() >= 6)})

    fact = []
    for i, m in enumerate(movs):
        fecha = datetime.fromisoformat(m["Fecha_Movimiento"])
        tipo = tipo_mov[m["Id_Tipo_Movimiento"]]
        es_entrada = tipo["Codigo"] in TIPOS_ENTRADA
        perman, cod_lote = permanencia.get(i, (None, None))
        prov_id = None
        if m.get("Id_Entrada") and entradas.get(m["Id_Entrada"]):
            ruc = entradas[m["Id_Entrada"]]["Ruc_Proveedor"]
            prov_id = id_prov.get(ruc)
        fact.append({
            "Id_Movimiento_NK": 100000 + i,
            "Id_Fecha": int(fecha.strftime("%Y%m%d")),
            "Id_Producto": id_prod[m["Cod_Componente"]],
            "Id_TipoMovimiento": int(m["Id_Tipo_Movimiento"]),
            "Id_Almacen_Origen": int(m["Id_Ubicacion_Origen"]) if m.get("Id_Ubicacion_Origen") else None,
            "Id_Almacen_Destino": int(m["Id_Ubicacion_Destino"]) if m.get("Id_Ubicacion_Destino") else None,
            "Id_Proyecto": id_proy.get(m.get("Id_Proyecto")),
            "Id_Responsable": id_resp.get(m.get("Id_Responsable")),
            "Id_Proveedor": prov_id,
            "Id_Estado_Anterior": id_est.get(estados[int(m["Id_Estado_Anterior"]) - 1]["Nombre_Estado"]) if m.get("Id_Estado_Anterior") else None,
            "Id_Estado_Nuevo": id_est.get(estados[int(m["Id_Estado_Nuevo"]) - 1]["Nombre_Estado"]) if m.get("Id_Estado_Nuevo") else None,
            "Id_Lote": id_lote.get(cod_lote) if cod_lote else None,
            "Cantidad": int(m["Cantidad"]),
            "Costo_Total": round(float(componentes[m["Cod_Componente"]]["Precio_Unitario"]) * int(m["Cantidad"]), 2),
            "Dias_Permanencia": perman if not es_entrada else None,
            "Fecha": fecha.date().isoformat(),
        })

    print("== 5. Verificación y conciliación ==")
    u_ent = sum(f["Cantidad"] for f in fact if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Entrada"])
    u_sal = sum(f["Cantidad"] for f in fact if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Salida_Real"])
    c_ent = sum(f["Costo_Total"] for f in fact if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Entrada"])
    c_sal = sum(f["Costo_Total"] for f in fact if next(t for t in dim_tipo if f["Id_TipoMovimiento"] == t["Id_TipoMovimiento"])["Es_Salida_Real"])
    dias = [f["Dias_Permanencia"] for f in fact if f["Dias_Permanencia"] is not None]
    tpp = sum(dias) / len(dias)
    plan_e = sum(p["Entradas_Plan"] for p in plan_rows)
    plan_s = sum(p["Salidas_Plan"] for p in plan_rows)
    anomalias = sum(s["Es_Anomalia"] for s in sensores_norm)

    kpis = {
        "version_etl": "2.0",
        "fuente_oltp": "ALMACEN_ANONIMO",
        "destino": "DM_ALMACEN_ANONIMO",
        "registros_origen": len(movs),
        "registros_cargados": len(fact),
        "registros_rechazados": rechazados,
        "completitud_pct": round(100 * (1 - rechazados / len(movs)), 2),
        "nulos_obligatorios": nulos,
        "cantidad_no_positiva": no_pos,
        "sin_producto": sin_prod,
        "duplicados": dup,
        "filas_dim_tiempo": len(dim_tiempo),
        "filas_dim_producto": len(dim_producto),
        "filas_dim_lote": len(dim_lote_final),
        "total_tablas_dm": 14,
        "unidades_entradas": u_ent,
        "unidades_salidas": u_sal,
        "costo_entradas": round(c_ent, 2),
        "costo_salidas": round(c_sal, 2),
        "inversion_retenida": round(c_ent - c_sal, 2),
        "rotacion_global": round(u_sal / u_ent, 4),
        "stock_neto": u_ent - u_sal,
        "tpp": round(tpp, 6),
        "tpp_redondeado": round(tpp, 2),
        "salidas_con_permanencia": len(dias),
        "dias_min": min(dias),
        "dias_max": max(dias),
        "permanencia_negativa": sum(1 for d in dias if d < 0),
        "plan_entradas": plan_e,
        "plan_salidas": plan_s,
        "vm_entradas_pct": round((u_ent - plan_e) / plan_e * 100, 2),
        "vm_salidas_pct": round((u_sal - plan_s) / plan_s * 100, 2),
        "lecturas_sensores": len(sensores_norm),
        "anomalias_sensores": anomalias,
        "anomalias_pct": round(100 * anomalias / len(sensores_norm), 2),
        "conteos": len(conteos_norm),
        "conteos_conformes": sum(1 for c in conteos_norm if c["Resultado"] == "CONFORME"),
        "exactitud_global": round(sum(c["Exactitud_Linea"] for c in conteos_norm) / len(conteos_norm), 4),
        "reconciliacion_ok": (len(fact) == len(movs)) and (rechazados == 0),
        "fecha_verificacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Series para figuras y para el informe
    serie = defaultdict(lambda: {"entradas": 0, "salidas": 0, "tpp": [], "anomalias": 0, "lecturas": 0})
    for f in fact:
        mes = int(f["Fecha"][5:7])
        if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Entrada"]:
            serie[mes]["entradas"] += f["Cantidad"]
        else:
            serie[mes]["salidas"] += f["Cantidad"]
            if f["Dias_Permanencia"] is not None:
                serie[mes]["tpp"].append(f["Dias_Permanencia"])
    for s in sensores_norm:
        mes = int(s["Timestamp"][5:7])
        serie[mes]["lecturas"] += 1
        serie[mes]["anomalias"] += s["Es_Anomalia"]

    cat_serie = defaultdict(lambda: {"entradas": 0, "salidas": 0, "costo_entradas": 0.0,
                                     "costo_salidas": 0.0, "tpp": defaultdict(list)})
    prod = {p["Id_Producto"]: p for p in dim_producto}
    for f in fact:
        c = prod[f["Id_Producto"]]["Categoria"]
        if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Entrada"]:
            cat_serie[c]["entradas"] += f["Cantidad"]
            cat_serie[c]["costo_entradas"] += f["Costo_Total"]
        else:
            cat_serie[c]["salidas"] += f["Cantidad"]
            cat_serie[c]["costo_salidas"] += f["Costo_Total"]
            if f["Dias_Permanencia"] is not None:
                cat_serie[c]["tpp"][int(f["Fecha"][5:7])].append(f["Dias_Permanencia"])

    kpis["serie_mensual"] = {m: {"entradas": v["entradas"], "salidas": v["salidas"],
                                 "tpp": round(sum(v["tpp"]) / len(v["tpp"]), 2) if v["tpp"] else None,
                                 "salidas_con_permanencia": len(v["tpp"]),
                                 "anomalias": v["anomalias"], "lecturas": v["lecturas"]}
                             for m, v in sorted(serie.items())}
    kpis["serie_categoria"] = {c: {"entradas": v["entradas"], "salidas": v["salidas"],
                                   "costo_entradas": round(v["costo_entradas"], 2),
                                   "costo_salidas": round(v["costo_salidas"], 2),
                                   "rotacion": round(v["salidas"] / v["entradas"], 4),
                                   "tpp": round(sum(sum(x) / len(x) * len(x) for x in v["tpp"].values()) / max(sum(len(x) for x in v["tpp"].values()), 1), 2)}
                               for c, v in sorted(cat_serie.items())}
    kpis["matriz_tpp_categoria_mes"] = {c: {str(m): round(sum(v) / len(v), 2) for m, v in sorted(d["tpp"].items())}
                                        for c, d in sorted(cat_serie.items())}
    proy_consumo = defaultdict(int)
    for f in fact:
        if f["Id_Proyecto"]:
            proy_consumo[[p for p in dim_proyecto if p["Id_Proyecto"] == f["Id_Proyecto"]][0]["Codigo_Proyecto"]] += f["Cantidad"]
    kpis["consumo_por_proyecto"] = dict(sorted(proy_consumo.items()))

    (SALIDAS / "kpis.json").write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  TPP = {kpis['tpp']} | filas = {len(fact)} | rechazados = {rechazados} | "
          f"conciliación = {kpis['reconciliacion_ok']}")

    print("== 6. Exportación del datamart a CSV (respaldo para Power BI) ==")
    escribir_csv("Dim_Tiempo.csv", ["Id_Fecha", "Fecha", "Anio", "Trimestre", "Mes", "Nombre_Mes",
                                    "Dia_Semana", "Nombre_Dia", "Es_Fin_Semana"], dim_tiempo)
    escribir_csv("Dim_Producto.csv", ["Id_Producto", "Cod_Componente", "Descripcion", "Categoria",
                                      "Marca", "Modelo", "Criticidad", "Stock_Minimo", "Precio_Unitario"], dim_producto)
    escribir_csv("Dim_Almacen.csv", ["Id_Almacen", "Codigo_Ubicacion", "Nombre_Ubicacion", "Tipo_Ubicacion"], dim_almacen)
    escribir_csv("Dim_TipoMovimiento.csv", ["Id_TipoMovimiento", "Codigo", "Nombre", "Signo_Stock", "Es_Entrada", "Es_Salida_Real"], dim_tipo)
    escribir_csv("Dim_Proyecto.csv", ["Id_Proyecto", "Codigo_Proyecto", "Nombre_Proyecto", "Tipo_Proyecto", "Estado"], dim_proyecto)
    escribir_csv("Dim_Responsable.csv", ["Id_Responsable", "Codigo_Responsable", "Nombre", "Cargo"], dim_responsable)
    escribir_csv("Dim_Proveedor.csv", ["Id_Proveedor", "Ruc_Proveedor", "Nombre"], dim_proveedor)
    escribir_csv("Dim_Estado.csv", ["Id_Estado", "Nombre_Estado", "Disponible_Stock"], dim_estado)
    escribir_csv("Dim_Lote.csv", ["Id_Lote", "Codigo_Lote", "Cod_Componente", "Id_Entrada",
                                  "Fecha_Ingreso", "Cantidad_Lote", "Codigo_Ubicacion"], dim_lote_final)
    escribir_csv("Fact_Movimiento.csv", ["Id_Movimiento_NK", "Id_Fecha", "Id_Producto", "Id_TipoMovimiento",
                                         "Id_Almacen_Origen", "Id_Almacen_Destino", "Id_Proyecto",
                                         "Id_Responsable", "Id_Proveedor", "Id_Estado_Anterior",
                                         "Id_Estado_Nuevo", "Id_Lote", "Cantidad", "Costo_Total",
                                         "Dias_Permanencia", "Fecha"], fact)
    escribir_csv("stg_Plan_Mensual.csv", ["Anio", "Mes", "Categoria", "Entradas_Plan", "Salidas_Plan"], plan_rows)
    escribir_csv("stg_Sensores.csv", ["Timestamp", "Sensor_Id", "Codigo_Ubicacion", "Temperatura",
                                      "Humedad", "Es_Anomalia"], sensores_norm)
    escribir_csv("stg_Conteos.csv", ["Fecha", "Cod_Componente", "Codigo_Ubicacion", "Stock_Sistema",
                                     "Stock_Fisico", "Diferencia", "Responsable", "Resultado",
                                     "Exactitud_Linea"], conteos_norm)
    inv_actual = []
    for p in dim_producto:
        stock = sum(f["Cantidad"] if next(t for t in dim_tipo if t["Id_TipoMovimiento"] == f["Id_TipoMovimiento"])["Es_Entrada"] else -f["Cantidad"]
                    for f in fact if f["Id_Producto"] == p["Id_Producto"])
        inv_actual.append({"Cod_Componente": p["Cod_Componente"], "Id_Ubicacion": 1,
                           "Stock_Disponible": stock, "Stock_Minimo": p["Stock_Minimo"],
                           "Criticidad": p["Criticidad"]})
    escribir_csv("stg_Inventario_Actual.csv", ["Cod_Componente", "Id_Ubicacion", "Stock_Disponible",
                                               "Stock_Minimo", "Criticidad"], inv_actual)
    print(f"\n  kpis.json -> {SALIDAS / 'kpis.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
