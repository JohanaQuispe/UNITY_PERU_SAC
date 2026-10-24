#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
figuras.py — Genera las figuras del informe y de la presentación a partir de:
  - analisis/salidas/kpis.json      (métricas verificadas del datamart)
  - powerbi/respaldo/*.csv          (contenido del datamart)
  - el diseño documentado de la arquitectura y del modelo estrella

Uso:  python analisis/figuras.py
Salidas: evidencias/fig01..fig11*.png  (300 dpi)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

RAIZ = Path(__file__).resolve().parents[1]
EVID = RAIZ / "evidencias"
EVID.mkdir(exist_ok=True)
K = json.loads((RAIZ / "analisis" / "salidas" / "kpis.json").read_text(encoding="utf-8"))

AZUL = "#0B2545"
AZUL2 = "#1B6CA8"
CELESTE = "#8FB8DE"
AMBAR = "#F0A202"
VERDE = "#2A9D8F"
ROJO = "#C44536"
GRIS = "#6B7280"
FONDO = "#F4F6F8"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": "#9AA5B1",
    "axes.labelcolor": "#1F2937",
    "text.color": "#1F2937",
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "savefig.dpi": 300,
    "figure.dpi": 110,
})


# ------------------------------------------------------------------ helpers
def caja(ax, x, y, w, h, titulo, detalle="", color=AZUL2, tc="white", fs=8.5, fs2=7.2, r=0.02):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.004,rounding_size={r}",
                                linewidth=0, facecolor=color, zorder=2))
    ax.text(x + w / 2, y + h * (0.66 if detalle else 0.5), titulo, ha="center", va="center",
            color=tc, fontsize=fs, fontweight="bold", zorder=3)
    if detalle:
        ax.text(x + w / 2, y + h * 0.30, detalle, ha="center", va="center",
                color=tc, fontsize=fs2, zorder=3, linespacing=1.35)


def flecha(ax, x1, y1, x2, y2, color=AZUL, lw=1.6):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
                                 linewidth=lw, color=color, zorder=1,
                                 shrinkA=2, shrinkB=2))


def guardar(fig, nombre):
    ruta = EVID / nombre
    fig.savefig(ruta, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print("  ", ruta.name)


# ------------------------------------------------------- Fig 1: arquitectura
def fig01():
    fig, ax = plt.subplots(figsize=(11.6, 5.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(2, 57.6, "Arquitectura integrada de la solución de BI", fontsize=11.5,
            fontweight="bold", color=AZUL)
    ax.text(2, 55.2, "Alcance: Inteligencia de Negocios (SQL Server + Python + Power BI)",
            fontsize=8, color=GRIS)

    for x, titulo in [(2, "1. FUENTES"), (25, "2. INTEGRACIÓN"), (51, "3. DATAMART"),
                      (77.5, "4. CONSUMO")]:
        ax.add_patch(Rectangle((x, 48.6), 20, 3.8, facecolor="#E8EEF5", edgecolor="none", zorder=1))
        ax.text(x + 10, 50.5, titulo, ha="center", va="center", fontsize=8.6,
                fontweight="bold", color=AZUL)

    caja(ax, 2, 40.0, 20, 7.0, "ALMACEN_ANONIMO", "OLTP SQL Server · 11 tablas\n5,348 movimientos · 24 componentes", AZUL, fs=8.6, fs2=6.7)
    caja(ax, 2, 31.3, 20, 7.0, "Plan_Demanda_2026.xlsx", "63 líneas · entradas/salidas\nplan por categoría y mes", AZUL2, fs=7.6, fs2=6.7)
    caja(ax, 2, 22.6, 20, 7.0, "Sensores_Almacen_2026.txt", "25,824 lecturas horarias\n(temperatura y humedad)", AZUL2, fs=7.6, fs2=6.7)
    caja(ax, 2, 13.9, 20, 7.0, "Conteos_Ciclicos_2026.txt", "72 conteos cíclicos\n(stock sistema vs. físico)", AZUL2, fs=7.6, fs2=6.7)

    ax.add_patch(FancyBboxPatch((25, 13.9), 21, 33.1, boxstyle="round,pad=0.004,rounding_size=0.015",
                                facecolor="#E8EEF5", edgecolor="none", zorder=1))
    ax.text(35.5, 45.3, "ETL v2.0 · Python", ha="center", fontsize=9, fontweight="bold", color=AZUL)
    fases = [("1. Extracción", "pandas + SQLAlchemy · conexión\npor variables de entorno"),
             ("2. Perfilado", "nulos, duplicados, cantidades\n≤ 0, producto inexistente"),
             ("3. Limpieza", "reglas RQ-01…RQ-06 · rechazos\na movimientos_rechazados.csv"),
             ("4. Transformación", "lotes FIFO, Dias_Permanencia,\nanomalías, exactitud, llaves"),
             ("5. Carga", "1 transacción: stg → dims →\nhecho (revierte si falla)")]
    y = 38.6
    for t, d in fases:
        ax.add_patch(FancyBboxPatch((26.1, y), 18.8, 5.4, boxstyle="round,pad=0.004,rounding_size=0.02",
                                    linewidth=0.9, edgecolor=CELESTE, facecolor="white", zorder=2))
        ax.text(35.5, y + 3.7, t, ha="center", va="center", fontsize=8, fontweight="bold", color=AZUL, zorder=3)
        ax.text(35.5, y + 1.7, d, ha="center", va="center", fontsize=6.3, color="#41556B",
                zorder=3, linespacing=1.3)
        y -= 6.1

    caja(ax, 51, 37.2, 21, 9.8, "DM_ALMACEN_ANONIMO", "Modelo estrella (Kimball) · 14 tablas\n1 hecho + 9 dimensiones\n+ 4 tablas de staging", AZUL, fs=8.8, fs2=6.8)
    caja(ax, 51, 24.9, 21, 9.6, "Fact_Movimiento", "5,348 filas · 11 FK + 3 medidas\nCantidad · Costo_Total\nDias_Permanencia", AZUL2, fs=8.8, fs2=6.8)
    caja(ax, 51, 14.2, 21, 8.2, "Área de staging", "stg_Plan_Mensual · stg_Sensores\nstg_Conteos · stg_Inventario_Actual", CELESTE, tc=AZUL, fs=8.6, fs2=6.6)

    caja(ax, 77.5, 36.0, 21, 11.0, "Dashboard Power BI", "1 archivo .pbix · 3 páginas\nGerencial · Operativa · Proyectos\n12 medidas DAX · modo Importación", AZUL, fs=8.8, fs2=6.8)
    caja(ax, 77.5, 24.6, 21, 8.6, "Usuarios y decisiones", "Gerencia: reposición\nLogística: despacho FIFO\nProyectos: disponibilidad", AZUL2, fs=8.6, fs2=6.6)
    caja(ax, 77.5, 14.2, 21, 8.2, "Evidencias", "log JSON por corrida · rechazados.csv\ncapturas y consultas de validación", GRIS, fs=8.6, fs2=6.6)

    for yy in (43.5, 34.8, 26.1, 17.4):
        flecha(ax, 22.2, yy, 24.8, yy)
    flecha(ax, 46.2, 29.7, 50.8, 29.7)
    flecha(ax, 61.5, 24.7, 61.5, 14.0)
    flecha(ax, 61.5, 37.0, 61.5, 34.7)
    flecha(ax, 72.2, 41.0, 77.3, 41.0)
    ax.text(74.7, 41.0 - 1.9, "consulta\nbatch", ha="center", va="top", fontsize=6.3, color=GRIS, linespacing=1.2)

    ax.add_patch(FancyBboxPatch((2, 2.6), 96.4, 8.2, boxstyle="round,pad=0.006,rounding_size=0.03",
                                linewidth=1.1, edgecolor=AMBAR, facecolor="#FFF8E6", zorder=1))
    ax.text(3.4, 9.0, "Límite de alcance", fontsize=8.6, fontweight="bold", color="#8A5A00")
    ax.text(3.4, 7.0, "Solución de Big Data (PySpark/Databricks): evaluada y descartada para esta entrega por decisión del docente;\n"
                      "se documenta como trabajo futuro (§3.5 y §7.3). La solución entregada es exclusivamente de BI, con carga batch diaria.",
            fontsize=7.3, color="#6B4B00", linespacing=1.5)
    guardar(fig, "fig01_arquitectura.png")


# ----------------------------------------------------- Fig 2: flujo por capas
def fig02():
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
    capas = [
        ("Origen", "4 fuentes · 3 formatos\n31,307 registros leídos", AZUL, 4.0),
        ("Staging", "4 tablas stg_ (área de paso)\nsin claves foráneas", AZUL2, 23.0),
        ("Integración", "ETL v2.0 · perfilado, limpieza\ny transformación", "#2E7D9A", 42.0),
        ("Datamart", "estrella: 1 hecho + 9 dims\n5,348 filas · 3,685 lotes", VERDE, 61.0),
        ("Consumo", "Power BI: 12 medidas DAX\n3 vistas · 4 KPI de negocio", AMBAR, 80.0),
    ]
    for nombre, detalle, color, x in capas:
        caja(ax, x, 22, 16.5, 12, nombre, detalle, color=color, fs=9.5, fs2=6.8)
    for x in (20.7, 39.7, 58.7, 77.7):
        flecha(ax, x, 28, x + 2.1, 28, lw=2.0)

    ax.text(4, 18.5, "Controles de calidad aplicados en el límite de cada capa",
            fontsize=9, fontweight="bold", color=AZUL)
    controles = [
        ("Origen → Staging", "Tipado y codificación UTF-8; lectura tolerante\na separadores ; y , ; normalización de mayúsculas"),
        ("Staging → Transformación", "RQ-01 nulos obligatorios · RQ-02 cantidad > 0\nRQ-03 producto existente · RQ-04 sin duplicados"),
        ("Transformación → Datamart", "RQ-05 integridad referencial (11 FK)\nRQ-06 conciliación de unidades E/S y balance"),
        ("Datamart → Consumo", "Medidas DAX sobre el hecho; staging oculto\nal usuario final para evitar doble conteo"),
    ]
    x = 4
    for t, d in controles:
        caja(ax, x, 4.2, 22.3, 12.2, t, d, color="white", tc=AZUL, fs=7.8, fs2=6.2)
        ax.add_patch(FancyBboxPatch((x, 4.2), 22.3, 12.2, boxstyle="round,pad=0.004,rounding_size=0.02",
                                    linewidth=0.9, edgecolor=CELESTE, facecolor="none", zorder=3))
        x += 23.4
    guardar(fig, "fig02_flujo_capas.png")


# -------------------------------------------------- Fig 3: modelo estrella
def fig03():
    fig, ax = plt.subplots(figsize=(11.6, 7.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 68)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])

    # --- hecho
    fx, fy, fw, fh = 33, 24, 34, 23
    ax.add_patch(FancyBboxPatch((fx, fy), fw, fh, boxstyle="round,pad=0.004,rounding_size=0.02",
                                linewidth=0, facecolor=AZUL, zorder=3))
    ax.text(fx + fw / 2, fy + fh - 2.8, "Fact_Movimiento", ha="center", fontsize=10.5,
            fontweight="bold", color="white", zorder=4)
    ax.text(fx + fw / 2, fy + fh - 5.2, "grano: 1 fila por movimiento · 5,348 filas",
            ha="center", fontsize=6.8, color="#CBD9E8", zorder=4)
    izq = ["Id_Movimiento_NK", "Id_Fecha", "Id_Producto", "Id_TipoMovimiento",
           "Id_Almacen_Origen", "Id_Almacen_Destino"]
    der = ["Id_Proyecto", "Id_Responsable", "Id_Proveedor", "Id_Estado_Anterior",
           "Id_Estado_Nuevo", "Id_Lote"]
    ax.text(fx + 1.8, fy + 15.6, "\n".join(izq), fontsize=6.0, color="white",
            va="top", linespacing=1.95, zorder=4)
    ax.text(fx + fw / 2 + 1.4, fy + 15.6, "\n".join(der), fontsize=6.0, color="white",
            va="top", linespacing=1.95, zorder=4)
    ax.plot([fx + fw / 2 - 1.2, fx + fw / 2 - 1.2], [fy + 1.2, fy + 16.2],
            color="#4C749B", lw=0.6, zorder=4)
    ax.add_patch(FancyBboxPatch((fx + 1.6, fy + 1.4), fw - 3.2, 3.4,
                                boxstyle="round,pad=0.003,rounding_size=0.02",
                                facecolor="#173B63", edgecolor="none", zorder=4))
    ax.text(fx + fw / 2, fy + 3.1, "medidas: Cantidad · Costo_Total · Dias_Permanencia",
            ha="center", va="center", fontsize=6.6, color="#FFD98A", zorder=5, style="italic")

    dims = [
        ("Dim_Tiempo", "Id_Fecha (AAAAMMDD)\nAnio · Trimestre · Mes\nNombre_Mes · Dia_Semana", 36, 52, AZUL2),
        ("Dim_Producto", "Cod_Componente CMP001–CMP024\nCategoria · Marca · Modelo\nCriticidad · Stock_Minimo · Precio", 1, 44, AZUL2),
        ("Dim_TipoMovimiento", "Codigo · Nombre\nSigno_Stock\nEs_Entrada · Es_Salida_Real", 77, 44, AZUL2),
        ("Dim_Almacen", "Codigo_Ubicacion\nNombre_Ubicacion\nTipo_Ubicacion", 1, 28, VERDE),
        ("Dim_Lote", "Codigo_Lote · Id_Entrada\nFecha_Ingreso\nCantidad_Lote · Ubicación", 77, 28, AMBAR),
        ("Dim_Proyecto", "Codigo_Proyecto\nNombre · Tipo\nEstado", 1, 12, VERDE),
        ("Dim_Estado", "Nombre_Estado\nDisponible_Stock\n(rol anterior / nuevo)", 77, 12, AMBAR),
        ("Dim_Responsable", "Codigo_Responsable\nNombre · Cargo", 26, 3.5, VERDE),
        ("Dim_Proveedor", "Ruc_Proveedor · Nombre\n(anonimizado)", 52, 3.5, VERDE),
    ]
    for nombre, detalle, x, y, color in dims:
        w, h = 22, 10.5
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.02",
                                    linewidth=0, facecolor=color, zorder=3))
        ax.text(x + w / 2, y + h - 2.9, nombre, ha="center", va="center", color="white",
                fontsize=8.6, fontweight="bold", zorder=4)
        ax.text(x + w / 2, y + 3.6, detalle, ha="center", va="center", color="white",
                fontsize=6.2, zorder=4, linespacing=1.35)
        cx, cy = x + w / 2, y + h / 2
        px = min(max(cx, fx + 2), fx + fw - 2)
        py = min(max(cy, fy + 2), fy + fh - 2)
        ax.plot([cx, px], [cy, py], color="#AEBECD", lw=1.0, zorder=1, linestyle=(0, (3, 2)))

    ax.text(50, 66.4, "Modelo estrella del datamart DM_ALMACEN_ANONIMO",
            ha="center", fontsize=11.5, fontweight="bold", color=AZUL)
    ax.text(50, 1.2, "Las 4 tablas stg_ (plan, sensores, conteos, inventario) no forman parte de la estrella: "
                     "alimentan los indicadores de VM, exactitud y anomalías.",
            ha="center", fontsize=7, color=GRIS, style="italic")
    guardar(fig, "fig03_modelo_estrella.png")


# ------------------------------------------------- Fig 4: fases del ETL
def fig04():
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")
    fases = [
        ("1\nExtracción", "0.4 s", "4 fuentes\nSQL + Excel + TXT", AZUL),
        ("2\nPerfilado", "—", "0 nulos · 0 duplicados\n0 cantidades ≤ 0", AZUL2),
        ("3\nLimpieza", "—", "RQ-01…RQ-06\n0 rechazados", "#2E7D9A"),
        ("4\nTransformación", "—", "3,685 lotes FIFO\n297 anomalías", VERDE),
        ("5\nCarga", "14.2 s", "1 transacción\n14 tablas", AMBAR),
    ]
    x = 1.5
    for titulo, tiempo, detalle, color in fases:
        caja(ax, x, 16, 17.4, 16, titulo, detalle, color=color, fs=9.2, fs2=6.8)
        ax.add_patch(FancyBboxPatch((x + 4.5, 34.4), 8.4, 4.2, boxstyle="round,pad=0.004,rounding_size=0.02",
                                    facecolor="white", edgecolor=color, zorder=3))
        ax.text(x + 8.7, 36.5, tiempo, ha="center", va="center", fontsize=8,
                fontweight="bold", color=color)
        if x < 80:
            flecha(ax, x + 17.7, 24, x + 19.9, 24, lw=2)
        x += 19.7

    ax.text(1.5, 12.2, "Salidas de cada corrida (trazabilidad)", fontsize=8.6, fontweight="bold", color=AZUL)
    for i, t in enumerate(["logs/etl_log_AAAAMMDD_HHMMSS.json — conteos, tiempos, completitud, conciliación",
                           "logs/movimientos_rechazados.csv — detalle del registro y la regla incumplida",
                           "Consola: ETL v2.0 OK: 5348 cargados, 0 rechazados, completitud 100.0%, reconciliacion=True"]):
        ax.text(1.5, 9.0 - i * 3.0, "•  " + t, fontsize=7.4, color=GRIS)
    guardar(fig, "fig04_fases_etl.png")


# --------------------------------------------- Fig 5: flujo mensual E/S
def fig05():
    s = K["serie_mensual"]
    meses = [int(m) for m in sorted(s, key=int)]
    ent = [s[str(m)]["entradas"] for m in meses]
    sal = [s[str(m)]["salidas"] for m in meses]
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    x = np.arange(len(meses))
    ax.bar(x - 0.2, ent, 0.4, label="Entradas", color=AZUL2)
    ax.bar(x + 0.2, sal, 0.4, label="Salidas reales", color=AMBAR)
    for xi, (a, b) in enumerate(zip(ent, sal)):
        ax.text(xi - 0.2, a + 25, f"{a:,}".replace(",", " "), ha="center", fontsize=6.3, color=AZUL)
        ax.text(xi + 0.2, b + 25, f"{b:,}".replace(",", " "), ha="center", fontsize=6.3, color="#8A5A00")
    ax.set_xticks(x); ax.set_xticklabels(MESES[:len(meses)])
    ax.set_ylabel("Unidades")
    ax.set_title("Entradas y salidas reales por mes — 2026", loc="left")
    ax.set_ylim(0, max(ent) * 1.16)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E3E8EE")
    ax.set_axisbelow(True)
    ax.text(0, -0.22, "Total del periodo: 15,425 unidades de entrada y 15,078 de salida "
                      "(rotación 0.98; balance neto +347 unidades).",
            transform=ax.transAxes, fontsize=7.4, color=GRIS)
    guardar(fig, "fig05_flujo_mensual.png")


# --------------------------------------------- Fig 6: TPP mensual vs meta
def fig06():
    s = K["serie_mensual"]
    meses = [int(m) for m in sorted(s, key=int)]
    tpp = [s[str(m)]["tpp"] for m in meses]
    n = [s[str(m)]["salidas_con_permanencia"] for m in meses]
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    ax.plot(MESES[:len(meses)], tpp, marker="o", color=AZUL, lw=2, label="TPP mensual (días)")
    for i, v in enumerate(tpp):
        ax.annotate(f"{v:.2f}", (i, v), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=7, color=AZUL)
    ax.fill_between(range(len(meses)), tpp, color=CELESTE, alpha=0.22)
    ax.axhline(45, color=ROJO, lw=1.1, ls="--")
    ax.text(0.1, 47, "Meta del KPI: TPP ≤ 45 días", color=ROJO, fontsize=7.5)
    ax.set_ylim(0, 52)
    ax.set_ylabel("Días de permanencia")
    ax.set_title("Tiempo promedio de permanencia (TPP) por mes — meta ≤ 45 días", loc="left")
    ax2 = ax.twinx()
    ax2.bar(range(len(meses)), n, 0.45, color="#DCE6F0", zorder=0)
    ax2.set_ylabel("Salidas con permanencia", color=GRIS, fontsize=8)
    ax2.set_ylim(0, max(n) * 4.2)
    ax2.tick_params(colors=GRIS, labelsize=7)
    ax2.spines[["top"]].set_visible(False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E3E8EE")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.text(0, -0.2, "TPP del periodo = 3.87 días (promedio de 1,663 salidas). La curva crece porque el "
                     "stock inicial (enero) sale casi el mismo día\ny se va consumiendo el inventario acumulado.",
            transform=ax.transAxes, fontsize=7.2, color=GRIS)
    guardar(fig, "fig06_tpp_mensual.png")


# ------------------------------------------ Fig 7: anomalías ambientales
def fig07():
    import csv
    filas = list(csv.DictReader(open(RAIZ / "powerbi" / "respaldo" / "stg_Sensores.csv",
                                     encoding="utf-8-sig"), delimiter=";"))
    s = K["serie_mensual"]
    meses = [int(m) for m in sorted(s, key=int)]
    anom = [s[str(m)]["anomalias"] for m in meses]
    lect = [s[str(m)]["lecturas"] for m in meses]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 3.7),
                                 gridspec_kw={"width_ratios": [1.15, 1]})
    x = np.arange(len(meses))
    a1.bar(x, lect, 0.62, color="#E4EBF2", label="Lecturas válidas")
    a1.bar(x, anom, 0.62, color=ROJO, label="Anomalías")
    for xi, v in zip(x, anom):
        if v:
            a1.text(xi, max(lect) * 0.055 + v, f"{v}", ha="center", fontsize=6.5, color=ROJO)
    a1.set_xticks(x); a1.set_xticklabels(MESES[:len(meses)])
    a1.set_ylabel("Lecturas por mes")
    a1.set_title("Lecturas de sensores y anomalías por mes", loc="left")
    a1.legend(frameon=False, fontsize=7.4, loc="upper center")
    a1.spines[["top", "right"]].set_visible(False)
    a1.text(0, -0.24, "297 de 25,824 lecturas fuera de rango (1.15 %).\nSe concentran en marzo (125) y julio (104).",
            transform=a1.transAxes, fontsize=7, color=GRIS)

    t = [float(f["Temperatura"]) for f in filas]
    h = [float(f["Humedad"]) for f in filas]
    a = [f["Es_Anomalia"] == "1" for f in filas]
    a2.scatter([ti for ti, ai in zip(t, a) if not ai], [hi for hi, ai in zip(h, a) if not ai],
               s=2, color=CELESTE, alpha=0.5, label="En rango")
    a2.scatter([ti for ti, ai in zip(t, a) if ai], [hi for hi, ai in zip(h, a) if ai],
               s=6, color=ROJO, alpha=0.85, label="Anomalía")
    a2.axvspan(18, 27, color=VERDE, alpha=0.08)
    a2.axhspan(40, 60, color=AZUL2, alpha=0.07)
    a2.set_xlabel("Temperatura (°C)"); a2.set_ylabel("Humedad relativa (%)")
    a2.set_title("Rango operativo: 18–27 °C y 40–60 % HR", loc="left")
    a2.legend(frameon=False, fontsize=7.4, markerscale=3)
    a2.spines[["top", "right"]].set_visible(False)
    guardar(fig, "fig07_anomalias_ambiente.png")


# ------------------------------------ Fig 8: rotación y valor por categoría
def fig08():
    c = K["serie_categoria"]
    cats = list(c.keys())
    rot = [c[k]["rotacion"] for k in cats]
    costo = [c[k]["costo_entradas"] / 1000 for k in cats]
    tpp = [c[k]["tpp"] for k in cats]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 3.7), gridspec_kw={"width_ratios": [1, 1.1]})
    orden = np.argsort(rot)
    a1.barh([cats[i] for i in orden], [rot[i] for i in orden], color=AZUL2, height=0.62)
    for i, idx in enumerate(orden):
        a1.text(rot[idx] + 0.002, i, f"{rot[idx]:.3f}", va="center", fontsize=7, color=AZUL)
    a1.set_xlim(0.94, 1.0)
    a1.set_xlabel("Rotación (salidas ÷ entradas)")
    a1.set_title("Rotación por categoría", loc="left")
    a1.spines[["top", "right"]].set_visible(False)
    a1.text(0, -0.22, "Todas las categorías cierran entre 0.97 y 0.98: el\nflujo se consume y no se acumula stock muerto.",
            transform=a1.transAxes, fontsize=7, color=GRIS)

    orden2 = np.argsort(costo)
    a2.barh([cats[i] for i in orden2], [costo[i] for i in orden2], color=AMBAR, height=0.62)
    for i, idx in enumerate(orden2):
        a2.text(costo[idx] + 250, i, f"S/ {costo[idx]:,.0f} mil".replace(",", " "), va="center",
                fontsize=6.8, color="#8A5A00")
    a2.set_xlim(0, max(costo) * 1.32)
    a2.set_xlabel("Costo de entradas (miles de S/)")
    a2.set_title("Valor movilizado por categoría", loc="left")
    a2.spines[["top", "right"]].set_visible(False)
    a2.text(0, -0.22, "Energía concentra S/ 19.3 millones (45 % del valor)\ncon solo 13 % de las unidades: mayor exposición financiera.",
            transform=a2.transAxes, fontsize=7, color=GRIS)
    guardar(fig, "fig08_categoria_rotacion.png")


# --------------------------------------------------- lienzo de dashboard
def lienzo(titulo, subtitulo, ncols=3):
    fig = plt.figure(figsize=(12, 6.6))
    fig.patch.set_facecolor(FONDO)
    fig.text(0.019, 0.955, titulo, fontsize=13.5, fontweight="bold", color=AZUL)
    fig.text(0.019, 0.917, subtitulo, fontsize=8, color=GRIS)
    fig.text(0.981, 0.955, "DM_ALMACEN_ANONIMO  ·  corte 30/09/2026", fontsize=6.8,
             color=GRIS, ha="right")
    fig.text(0.981, 0.928, "Fuente: elaboración propia (2026)", fontsize=6.8, color=GRIS, ha="right")
    fig.add_artist(plt.Line2D([0.019, 0.981], [0.905, 0.905], color=AZUL2, lw=1.1))
    fig.add_artist(plt.Line2D([0.019, 0.981], [0.055, 0.055], color="#D5DCE4", lw=0.8))
    return fig


def tarjeta(fig, x, y, w, h, etiqueta, valor, sub="", color=AZUL):
    ax = fig.add_axes([x, y, w, h]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.02, 0.06), 0.96, 0.88, boxstyle="round,pad=0.01,rounding_size=0.06",
                                facecolor="white", edgecolor="#E1E7ED", lw=0.9, transform=ax.transAxes))
    ax.add_patch(Rectangle((0.02, 0.06), 0.012, 0.88, facecolor=color, edgecolor="none",
                           transform=ax.transAxes))
    ax.text(0.07, 0.76, etiqueta, fontsize=7.4, color=GRIS, transform=ax.transAxes)
    ax.text(0.07, 0.44, valor, fontsize=17, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.07, 0.19, sub, fontsize=6.6, color=GRIS, transform=ax.transAxes)


def panel(fig, rect, titulo):
    ax = fig.add_axes(rect)
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.01,rounding_size=0.02",
                                facecolor="white", edgecolor="#E1E7ED", lw=0.9,
                                transform=ax.transAxes, zorder=0))
    ax.set_title(titulo, fontsize=8.4, color=AZUL, loc="left", pad=8)
    ax.spines[["top", "right"]].set_visible(False)
    return ax


# ------------------------------------------- Fig 9: vista gerencial (PBI)
def fig09():
    fig = lienzo("Vista Gerencial — ¿compramos o esperamos?",
                 "KPI de inventario y flujo de los últimos 9 meses")
    tarjeta(fig, 0.019, 0.75, 0.19, 0.14, "TPP (días de permanencia)", "3.87", "meta ≤ 45 · cumple", VERDE)
    tarjeta(fig, 0.222, 0.75, 0.19, 0.14, "Rotación global", "0.98", "salidas ÷ entradas")
    tarjeta(fig, 0.425, 0.75, 0.19, 0.14, "Inversión retenida", "S/ 812 mil", "costo E − costo S", AMBAR)
    tarjeta(fig, 0.628, 0.75, 0.19, 0.14, "Cumplimiento del plan", "+0.77 %", "entradas · salidas −0.75 %", AZUL2)
    tarjeta(fig, 0.831, 0.75, 0.15, 0.14, "Anomalías ambiente", "297", "1.15 % de 25,824", ROJO)

    s = K["serie_mensual"]
    meses = [int(m) for m in sorted(s, key=int)]
    ax1 = panel(fig, [0.045, 0.40, 0.42, 0.30], "Entradas vs. salidas reales por mes")
    x = np.arange(len(meses))
    ax1.bar(x - 0.2, [s[str(m)]["entradas"] for m in meses], 0.4, color=AZUL2, label="Entradas")
    ax1.bar(x + 0.2, [s[str(m)]["salidas"] for m in meses], 0.4, color=AMBAR, label="Salidas")
    ax1.set_xticks(x); ax1.set_xticklabels(MESES[:len(meses)], fontsize=7)
    ax1.tick_params(labelsize=7)
    ax1.legend(frameon=False, fontsize=6.6, ncol=2, loc="upper center",
               bbox_to_anchor=(0.5, 1.02))
    ax1.grid(axis="y", color="#EEF1F4"); ax1.set_axisbelow(True)
    ax1.set_ylim(0, 2280)

    ax2 = panel(fig, [0.53, 0.40, 0.44, 0.30], "TPP mensual vs. meta (≤ 45 días)")
    ax2.plot(MESES[:len(meses)], [s[str(m)]["tpp"] for m in meses], marker="o", color=AZUL, lw=1.8)
    ax2.fill_between(range(len(meses)), [s[str(m)]["tpp"] for m in meses], color=CELESTE, alpha=0.25)
    ax2.axhline(45, color=ROJO, ls="--", lw=0.9)
    ax2.set_ylim(0, 50); ax2.tick_params(labelsize=7)
    ax2.grid(axis="y", color="#EEF1F4"); ax2.set_axisbelow(True)
    ax2.text(len(meses) - 1, 42, "meta 45", fontsize=6.4, color=ROJO, ha="right")

    c = K["serie_categoria"]
    cats = sorted(c, key=lambda k: -c[k]["costo_entradas"])
    ax3 = panel(fig, [0.045, 0.10, 0.42, 0.24], "Costo movilizado por categoría (miles de S/)")
    ax3.bar([k[:13] for k in cats], [c[k]["costo_entradas"] / 1000 for k in cats], color=AZUL2)
    ax3.set_xticklabels([k[:13] for k in cats], fontsize=6.2, rotation=18, ha="right")
    ax3.tick_params(labelsize=6.8)
    ax3.grid(axis="y", color="#EEF1F4"); ax3.set_axisbelow(True)

    ax4 = panel(fig, [0.53, 0.10, 0.44, 0.24], "Cumplimiento del plan por mes: (real − plan) ÷ plan")
    vm_e, vm_s = [], []
    for m in meses:
        real_e = s[str(m)]["entradas"]; real_s = s[str(m)]["salidas"]
        plan = [p for p in __import__("csv").DictReader(
            open(RAIZ / "powerbi" / "respaldo" / "stg_Plan_Mensual.csv", encoding="utf-8-sig"),
            delimiter=";") if int(p["Mes"]) == m]
        pe = sum(float(p["Entradas_Plan"]) for p in plan); ps = sum(float(p["Salidas_Plan"]) for p in plan)
        vm_e.append((real_e - pe) / pe * 100); vm_s.append((real_s - ps) / ps * 100)
    ax4.bar(x - 0.2, vm_e, 0.4, color=VERDE, label="Entradas")
    ax4.bar(x + 0.2, vm_s, 0.4, color=ROJO, label="Salidas")
    ax4.axhline(0, color="#9AA5B1", lw=0.8)
    ax4.axhspan(-10, 10, color=AMBAR, alpha=0.08)
    ax4.set_xticks(x); ax4.set_xticklabels(MESES[:len(meses)], fontsize=7)
    ax4.tick_params(labelsize=6.8)
    ax4.legend(frameon=False, fontsize=6.6, ncol=2, loc="upper right")
    ax4.grid(axis="y", color="#EEF1F4"); ax4.set_axisbelow(True)
    guardar(fig, "fig09_dashboard_gerencial.png")


# ------------------------------------------ Fig 10: vista operativa (PBI)
def fig10():
    fig = lienzo("Vista Operativa — ¿qué despachamos y qué está retenido?",
                 "Detalle por categoría, componente y antigüedad FIFO del stock")
    mtz = K["matriz_tpp_categoria_mes"]
    cats = list(mtz.keys())
    meses = sorted({int(m) for c in cats for m in mtz[c]})
    datos = np.array([[mtz[c].get(str(m), np.nan) for m in meses] for c in cats])
    ax1 = panel(fig, [0.055, 0.405, 0.40, 0.40], "Mapa de calor: TPP (días) por categoría y mes")
    im = ax1.imshow(datos, cmap="YlOrRd", aspect="auto")
    ax1.set_xticks(range(len(meses))); ax1.set_xticklabels(MESES[:len(meses)], fontsize=7)
    ax1.set_yticks(range(len(cats))); ax1.set_yticklabels(cats, fontsize=7)
    for i in range(len(cats)):
        for j in range(len(meses)):
            ax1.text(j, i, f"{datos[i, j]:.1f}", ha="center", va="center", fontsize=6,
                     color="white" if datos[i, j] > np.nanmax(datos) * 0.6 else "#333")
    ax1.spines[:].set_visible(False)
    ax1.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax1, fraction=0.03, pad=0.02)
    cb.ax.tick_params(labelsize=6)

    ax2 = panel(fig, [0.545, 0.405, 0.425, 0.40], "Antigüedad del lote consumido por componente (días)")
    import csv
    fact = list(csv.DictReader(open(RAIZ / "powerbi" / "respaldo" / "Fact_Movimiento.csv",
                                    encoding="utf-8-sig"), delimiter=";"))
    prod = {p["Id_Producto"]: p for p in csv.DictReader(
        open(RAIZ / "powerbi" / "respaldo" / "Dim_Producto.csv", encoding="utf-8-sig"), delimiter=";")}
    vals = {}
    for f in fact:
        if f["Dias_Permanencia"]:
            cod = prod[f["Id_Producto"]]["Cod_Componente"]
            vals.setdefault(cod, []).append(float(f["Dias_Permanencia"]))
    prom = sorted(((k, sum(v) / len(v)) for k, v in vals.items()), key=lambda kv: -kv[1])
    ax2.barh([k for k, _ in prom][::-1], [v for _, v in prom][::-1], color=CELESTE, height=0.7)
    ax2.set_yticklabels([k for k, _ in prom][::-1], fontsize=5.6)
    ax2.tick_params(labelsize=6)
    ax2.axvline(3.87, color=AZUL, ls="--", lw=0.9)
    ax2.text(3.95, 0.4, "TPP global 3.87", fontsize=6.2, color=AZUL)
    ax2.grid(axis="x", color="#EEF1F4"); ax2.set_axisbelow(True)
    ax2.set_xlabel("Días", fontsize=7)

    s = K["serie_mensual"]
    ax3 = panel(fig, [0.055, 0.085, 0.40, 0.205], "Lecturas fuera de rango por mes")
    ax3.bar(MESES[:len(s)], [s[m]["anomalias"] for m in sorted(s, key=int)], color=ROJO, width=0.55)
    ax3.set_xticklabels(MESES[:len(s)], fontsize=7); ax3.tick_params(labelsize=6.8)
    ax3.grid(axis="y", color="#EEF1F4"); ax3.set_axisbelow(True)

    ax4 = panel(fig, [0.545, 0.085, 0.425, 0.205], "Estado del stock frente al stock mínimo")
    inv = list(csv.DictReader(open(RAIZ / "powerbi" / "respaldo" / "stg_Inventario_Actual.csv",
                                    encoding="utf-8-sig"), delimiter=";"))
    bajo = [r for r in inv if float(r["Stock_Disponible"]) < float(r["Stock_Minimo"])]
    ax4.axis("off")
    ax4.text(0.02, 0.62, f"{len(bajo)} de {len(inv)} componentes", fontsize=13, fontweight="bold",
             color=ROJO if bajo else VERDE, transform=ax4.transAxes)
    ax4.text(0.02, 0.38, "por debajo del stock mínimo de seguridad al 30/09/2026.",
             fontsize=7, color=GRIS, transform=ax4.transAxes)
    ax4.text(0.02, 0.14, "Exactitud de conteos cíclicos: " +
             f"{K['exactitud_global']*100:.2f} % ({K['conteos_conformes']}/{K['conteos']} conformes)",
             fontsize=7.2, color=AZUL, transform=ax4.transAxes)
    guardar(fig, "fig10_dashboard_operativa.png")


# ------------------------------------------ Fig 11: vista proyectos (PBI)
def fig11():
    fig = lienzo("Vista Proyectos — ¿hay disponibilidad para comprometer?",
                 "Consumo por proyecto, criticidad del catálogo y exactitud de inventario")
    cons = K["consumo_por_proyecto"]
    import csv
    proy = {p["Codigo_Proyecto"]: p["Nombre_Proyecto"] for p in csv.DictReader(
        open(RAIZ / "powerbi" / "respaldo" / "Dim_Proyecto.csv", encoding="utf-8-sig"), delimiter=";")}
    ax1 = panel(fig, [0.055, 0.40, 0.42, 0.40], "Unidades consumidas por proyecto")
    claves = list(cons.keys())
    ax1.barh([k for k in claves][::-1], [cons[k] for k in claves][::-1], color=AZUL2, height=0.55)
    for i, k in enumerate(claves[::-1]):
        ax1.text(cons[k] + 60, i, f"{cons[k]:,}".replace(",", " "), va="center", fontsize=7, color=AZUL)
    ax1.set_xlim(0, max(cons.values()) * 1.2)
    ax1.tick_params(labelsize=7)
    ax1.set_xlabel("Unidades despachadas (ene–sep 2026)", fontsize=7)
    ax1.grid(axis="x", color="#EEF1F4"); ax1.set_axisbelow(True)

    ax2 = panel(fig, [0.545, 0.40, 0.425, 0.40], "Catálogo por criticidad")
    prod = list(csv.DictReader(open(RAIZ / "powerbi" / "respaldo" / "Dim_Producto.csv",
                                    encoding="utf-8-sig"), delimiter=";"))
    crit = {}
    for p in prod:
        crit[p["Criticidad"]] = crit.get(p["Criticidad"], 0) + 1
    orden = ["ALTA", "MEDIA", "BAJA"]
    col = {"ALTA": ROJO, "MEDIA": AMBAR, "BAJA": VERDE}
    ax2.bar([k for k in orden if k in crit], [crit[k] for k in orden if k in crit],
            color=[col[k] for k in orden if k in crit], width=0.5)
    for i, k in enumerate([k for k in orden if k in crit]):
        ax2.text(i, crit[k] + 0.3, f"{crit[k]} componentes", ha="center", fontsize=7.4, color=GRIS)
    ax2.set_ylim(0, max(crit.values()) * 1.35)
    ax2.tick_params(labelsize=7)
    ax2.text(0.02, 0.9, "Los componentes de criticidad ALTA concentran\nla mayor superficie de riesgo operativo.",
             transform=ax2.transAxes, fontsize=6.8, color=GRIS)
    ax2.spines[["top", "right"]].set_visible(False)

    ax3 = panel(fig, [0.055, 0.09, 0.42, 0.22], "Exactitud por conteo cíclico (%)")
    con = list(csv.DictReader(open(RAIZ / "powerbi" / "respaldo" / "stg_Conteos.csv",
                                   encoding="utf-8-sig"), delimiter=";"))
    vals = [float(c["Exactitud_Linea"]) * 100 for c in con]
    ax3.plot(range(len(vals)), vals, color=AZUL, lw=1.1, marker="o", ms=2.4)
    ax3.axhline(95, color=ROJO, ls="--", lw=0.9)
    ax3.set_ylim(60, 104)
    ax3.set_xlabel("Conteo cíclico (ene–set 2026)", fontsize=7)
    ax3.tick_params(labelsize=6.8)
    ax3.grid(axis="y", color="#EEF1F4"); ax3.set_axisbelow(True)
    ax3.text(1, 96.4, "umbral 95 %", fontsize=6.2, color=ROJO)

    ax4 = panel(fig, [0.545, 0.09, 0.425, 0.22], "Decisiones que habilita esta vista")
    ax4.axis("off")
    for i, t in enumerate([
            "• Comprometer despachos solo con stock verificado.",
            "• Reasignar componentes retenidos en proyectos pausados.",
            "• Priorizar el conteo cíclico de los CMP de criticidad ALTA.",
            "• Escalar a Gerencia las diferencias de inventario > 1 unidad."]):
        ax4.text(0.02, 0.78 - i * 0.24, t, fontsize=7, color="#374151", transform=ax4.transAxes)
    guardar(fig, "fig11_dashboard_proyectos.png")


if __name__ == "__main__":
    print("Generando figuras en", EVID)
    for f in (fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10, fig11):
        f()
    print("Listo.")
