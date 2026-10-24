# Unity Perú SAC — Solución de Inteligencia de Negocios

Proyecto de **Base de Datos Avanzadas y Big Data** (2026-2).
Solución de BI para el almacén de componentes tecnológicos: datamart en estrella en SQL Server,
ETL en Python con control de calidad y dashboard en Power BI.

## Integrantes

- Quispe Ruiz, Johana Carolina — 20 %
- Sotelo Espinoza, Leoneld Mathias — 20 %
- Montalvo Abrego, Camila Nadine — 20 %
- Arroyo Julca, Mishell Alexandra Belen — 20 %
- Cordova Paz, Diego Jason — 20 %

Docente: Víctor Isaac Chávez Bardales · NRC 26055

## Entregables

| Entregable | Dónde está |
|---|---|
| Informe del proyecto | `docs/Informe_Proyecto_BI_UnityPeru.docx` |
| Presentación (5 min) | `docs/Presentacion_BI.pptx` |
| Procedimiento de replicación | `REPLICACION.md` |
| Guion de la demostración (10 min) | `REPLICACION.md`, sección 8 |
| Dashboard construido | `powerbi/Dashboard_Almacen_BI.pbix` |

## Contenido del repositorio

| Carpeta | Qué contiene |
|---|---|
| `scripts/` | Scripts SQL: 01 base operacional, 02 datos, 03 datamart |
| `etl/` | `etl_almacen_unity.py` (ETL v2.0) y `requirements.txt` |
| `datos/` | Plan de demanda (Excel), sensores (TXT) y conteos cíclicos (TXT) |
| `logs/` | Log de la corrida verificada (evidencia de calidad) |
| `powerbi/` | Medidas DAX, guía del tablero y respaldo del datamart en CSV |
| `evidencias/` | Figuras del informe y capturas del dashboard |
| `analisis/` | Scripts de verificación de KPI y de escalamiento |
| `docs/` | Informe, presentación y guion de defensa |

## Resultados del proyecto

| Indicador | Valor | Meta |
|---|---|---|
| Movimientos cargados | 5,348 | — |
| Registros rechazados | 0 | 0 |
| Completitud | 100 % | ≥ 98 % |
| Tiempo de permanencia (TPP) | 3.87 días | ≤ 45 días |
| Rotación de existencias | 0.98 | 0.95 – 1.05 |
| Cumplimiento del plan | +0.77 % / −0.75 % | ±10 % |
| Componentes sobre stock mínimo | 24 de 24 | 100 % |
| Exactitud de conteos | 96.55 % | ≥ 95 % |
| Anomalías ambientales | 297 de 25,824 (1.15 %) | ≤ 2 % |
| Inversión retenida | S/ 812,060 | — |

## Cómo ejecutarlo

Ver [`REPLICACION.md`](REPLICACION.md). Resumen:

1. Ejecutar `scripts/01`, `scripts/02` y `scripts/03` en SQL Server (en ese orden).
2. Definir las variables de entorno `OLTP_URL` y `DM_URL`.
3. Ejecutar el ETL.
4. Abrir el dashboard en Power BI.

Versión evaluada: **v1.0**