#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_escalamiento.py — Experimento de escalamiento del proceso de
transformación del ETL v2.0 (fases 4 y 5 sin escritura en el motor).

Replica el hecho ×1, ×5 y ×10 (5,348 / 26,740 / 53,480 movimientos) manteniendo
la distribución por componente, tipo y mes, y mide:
  - tiempo de transformación (lotes FIFO + Dias_Permanencia + agregados de KPI)
  - throughput (movimientos por segundo)
  - estabilidad del KPI (TPP y rotación deben permanecer idénticos)

Uso:
    python analisis/benchmark_escalamiento.py [repeticiones]

Salidas:
    analisis/salidas/benchmark_escalamiento.json
"""
import csv
import json
import statistics
import sys
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDAS = RAIZ / "analisis" / "salidas"
SALIDAS.mkdir(exist_ok=True)
RESPALDO = RAIZ / "powerbi" / "respaldo"


def cargar_movimientos():
    fact = list(csv.DictReader(open(RESPALDO / "Fact_Movimiento.csv", encoding="utf-8-sig"),
                               delimiter=";"))
    movs = []
    for f in fact:
        movs.append({
            "fecha": datetime.fromisoformat(f["Fecha"]),
            "Cod_Componente": f["Id_Producto"],
            "cantidad": int(float(f["Cantidad"])),
            "es_entrada": f["Id_TipoMovimiento"] == "1",
            "n": 1,
        })
    movs.sort(key=lambda m: m["fecha"])
    return movs


def transformar(movs):
    """Réplica de la fase 4: lotes FIFO, edad de salida y agregados de KPI."""
    lotes = defaultdict(deque)
    for m in movs:
        if m["es_entrada"]:
            lotes[m["Cod_Componente"]].append([m["fecha"], m["cantidad"]])

    suma_dias = 0.0
    n_salidas = 0
    u_ent = u_sal = 0
    for m in movs:
        if m["es_entrada"]:
            u_ent += m["cantidad"]
            continue
        u_sal += m["cantidad"]
        qq = m["cantidad"]
        total = 0.0
        tomadas = 0
        while qq > 0 and lotes[m["Cod_Componente"]]:
            lote = lotes[m["Cod_Componente"]][0]
            toma = min(qq, lote[1])
            total += (m["fecha"] - lote[0]).days * toma
            tomadas += toma
            lote[1] -= toma
            qq -= toma
            if lote[1] == 0:
                lotes[m["Cod_Componente"]].popleft()
        if tomadas:
            suma_dias += total / tomadas
            n_salidas += 1
    return {"tpp": suma_dias / n_salidas, "salidas": n_salidas,
            "unidades_entradas": u_ent, "unidades_salidas": u_sal,
            "rotacion": u_sal / u_ent}


def main():
    repeticiones = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    base = cargar_movimientos()
    print(f"Base: {len(base)} movimientos · repeticiones por escala: {repeticiones}\n")
    resultados = []
    for escala in (1, 5, 10):
        # cada réplica es una copia íntegra e independiente del histórico: conserva la
        # secuencia entrada->salida y, por tanto, el TPP y la rotación del periodo
        copias = [[dict(m) for m in base] for _ in range(escala)]
        tiempos, salida = [], None
        for _ in range(repeticiones):
            t0 = time.perf_counter()
            for copia in copias:
                salida = transformar(copia)
            tiempos.append(time.perf_counter() - t0)
        mediana = statistics.median(tiempos)
        fila = {
            "escala": f"x{escala}",
            "movimientos": len(base) * escala,
            "repeticiones": repeticiones,
            "tiempo_mediana_s": round(mediana, 3),
            "tiempo_min_s": round(min(tiempos), 3),
            "tiempo_max_s": round(max(tiempos), 3),
            "throughput_mov_s": round(len(base) * escala / mediana, 0),
            "tpp": round(salida["tpp"], 4),
            "rotacion": round(salida["rotacion"], 4),
            "salidas_con_permanencia": salida["salidas"] * escala,
        }
        resultados.append(fila)
        print(f"  {fila['escala']:>3} | {fila['movimientos']:>6} mov | "
              f"mediana {fila['tiempo_mediana_s']:>6} s | "
              f"{fila['throughput_mov_s']:>9.0f} mov/s | TPP {fila['tpp']}")

    salida_json = {
        "proceso": "transformación ETL v2.0 (FIFO + Dias_Permanencia + agregados KPI)",
        "entorno": {
            "cpu": "2 vCPU",
            "ram": "4 GB",
            "sistema_operativo": "Debian GNU/Linux 12",
            "python": sys.version.split()[0],
        },
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "repeticiones": repeticiones,
        "resultados": resultados,
        "nota": "Cada escala replica el hecho completo N veces como copias independientes, de modo "
                "que cada entrada conserva sus salidas FIFO y los KPI permanecen constantes entre "
                "escalas; solo cambia el volumen procesado.",
    }
    (SALIDAS / "benchmark_escalamiento.json").write_text(
        json.dumps(salida_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  -> {SALIDAS / 'benchmark_escalamiento.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
