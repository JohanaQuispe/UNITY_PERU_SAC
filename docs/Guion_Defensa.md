# Guion de defensa — Unity Perú SAC (BI)

5 min de presentación + 10 min de demostración.
Cifras oficiales: 5,348 movimientos · 0 rechazados · 100 % completitud · 3,685 lotes ·
TPP 3.87 d · rotación 0.98 · S/ 812,060 · VM +0.77 %/−0.75 % · 297 anomalías (1.15 %) ·
exactitud 96.55 % · ETL 0.4 s + 14.2 s.

---

## PARTE 1 — PRESENTACIÓN (5:00) — 10 diapositivas, ~30 s cada una

> Habla lento. Una idea por diapositiva. Si te trabas, vuelve a la tabla de KPI (diapo 5).

### Diapo 1 — Portada (0:00–0:20)
"Buenos días, somos el equipo de Unity Perú SAC. Presentamos una solución de Inteligencia
de Negocios para el almacén de componentes tecnológicos. Los cinco integramos el equipo
con 20 % de participación cada uno. Docente: Víctor Chávez. El alcance de esta entrega es
el componente de BI."

### Diapo 2 — Contexto (0:20–0:55)
"Unity Perú es una empresa peruana de misión crítica: diseña y certifica data centers
TIA-942. Su almacén guarda componentes críticos —SSD, memorias ECC, transceptores, PDU,
UPS— que sostienen proyectos, mantenimientos y los SLA con los clientes. Si el componente
no está disponible cuando se necesita, se incumple el SLA. Trabajamos con datos reales
autorizados por el CEO y anonimizados."

### Diapo 3 — Problemática (0:55–1:35)
"El problema no es que falte información, es que está dispersa: la base operacional, un
Excel de plan, las lecturas de sensores y los conteos en texto plano. Consolidarla a mano
tomaba de 4 a 6 horas por reporte, con 15 a 20 % de error en la estimación de
disponibilidad. Y peor: no existía ningún reporte del stock retenido en estados
intermedios. La decisión de compra se tomaba a ciegas."

### Diapo 4 — Solución y arquitectura (1:35–2:15)
"La solución tiene tres piezas. Un datamart en modelo estrella en SQL Server: una tabla
de hechos y nueve dimensiones. Un ETL en Python de cinco fases que integra las cuatro
fuentes y aplica calidad. Y un dashboard en Power BI con tres vistas y doce medidas DAX.
La metodología es Kimball. El detalle está en el capítulo III del informe."

### Diapo 5 — Entendimiento del negocio y KPIs (2:15–3:00)
"Definimos seis KPI con fórmula, meta y decisión asociada. Los seis cumplen:
permanencia 3.87 días frente a una meta de 45; rotación 0.98 dentro de la banda
0.95 a 1.05; cumplimiento del plan en +0.77 y −0.75 por ciento, dentro de ±10;
24 de 24 componentes sobre su stock mínimo; exactitud de inventario 96.55 %, sobre la
meta de 95; y 1.15 % de anomalías ambientales, bajo el 2 % permitido."

### Diapo 6 — Toma de decisiones (3:00–3:40)
"Cada indicador habilita una decisión concreta. Permanencia alta: priorizar el despacho de
lo retenido. Desviación del plan: reprogramar compras. Componente bajo mínimo: emitir
orden de reposición. Exactitud baja: investigar y ajustar inventario. Anomalías: programar
mantenimiento de climatización. El tablero traduce el dato en una acción, no solo en un
gráfico."

### Diapo 7 — ETL y calidad (3:40–4:20)
"El ETL hace cinco fases en un solo comando: extracción, perfilado, limpieza,
transformación y carga. La calidad está en la fase 3: seis reglas que validan nulos,
cantidades, producto existente, duplicados, integridad referencial y conciliación. Lo que
no cumple no se borra: se aparta en un archivo con su motivo. La carga completa va en una
sola transacción: si algo falla, revierte todo."

### Diapo 8 — Dashboard (4:20–4:45)
"El tablero tiene tres vistas y cada una responde una decisión: Gerencial para comprar,
Operativa para despachar, Proyectos para comprometer disponibilidad. Las tres comparten
filtros, así que se pasa del indicador global al detalle sin perder contexto."

### Diapo 9 — Resultados (4:45–5:00, se puede fusionar con la 10)
"Cinco mil trescientos cuarenta y ocho movimientos conciliados al cien por ciento, cero
rechazados y los seis KPI en meta. El proceso completo tarda catorce coma seis segundos."

### Diapo 10 — Cierre y pase a la demo (5:00)
"Y esto no es una maqueta: se ejecuta en vivo. Pasamos a la demostración."

---

## PARTE 2 — DEMOSTRACIÓN (10:00)

> Regla de oro: **la demo ES el procedimiento de replicación**. Ten `REPLICACION.md`
> abierto en GitHub y ve tachando pasos. Así el docente ve que el documento funciona.

| Min | Qué haces | Qué dices |
|---|---|---|
| 0:00–0:40 | Abres el repo en GitHub y `REPLICACION.md` | "Este es el repositorio y este es el procedimiento. Los pasos 2 y 3 ya están ejecutados; los muestro como evidencia." |
| 0:40–1:10 | Abres `scripts/03_DM_ALMACEN_ANONIMO.sql` (**no lo ejecutes**) | "Catorce tablas: una de hechos, nueve dimensiones y cuatro de staging. El hecho tiene once llaves foráneas." |
| 1:10–3:00 | **ETL en vivo** (flecha arriba, no teclear): `python etl\etl_almacen_unity.py --datos datos --log logs` | Mientras corre: "Cinco fases, cuatro fuentes, seis reglas de calidad. Tarda unos quince segundos." Al terminar, lees la línea: **"5348 cargados, 0 rechazados, completitud 100 %, reconciliación True"** |
| 3:00–4:00 | Abres el log JSON nuevo y `movimientos_rechazados.csv` | "Aquí está la evidencia: conteos antes y después, cero rechazos, conciliación correcta. Si algo entrara mal, se apartaría aquí con su motivo; lo probamos con cien defectos y rechazó los cien." |
| 4:00–4:50 | **Automatización** | "Las credenciales están en variables de entorno, no en el código. La carga es transaccional y el proceso es idempotente: se puede programar diario con el Programador de tareas sin intervención." |
| 4:50–6:30 | **SQL** (pestañas ya preparadas): conteo, TPP, lotes | "5,348 movimientos. Permanencia promedio 3.868701 días. 3,685 lotes FIFO. Y los ingresos tienen permanencia nula: solo las salidas tienen edad, porque un lote recién llegado tiene cero días." |
| 6:30–9:00 | **Power BI**: tres páginas + dos filtros | Página 1: "Gerencial: los cinco KPI con su meta, el flujo mensual y el cumplimiento del plan. Aquí Gerencia decide si repone." Página 2: "Operativa: el mapa de calor muestra que la permanencia sube de enero a agosto; y aquí están las anomalías, concentradas en marzo y julio: 229 de 297." Página 3: "Proyectos: solo tres proyectos consumen; con esto se compromete disponibilidad." |
| 9:00–9:40 | Un hallazgo propio | "Energía concentra el 45 % del valor con apenas el 13 % de las unidades. Eso cambia la política: el inventario se gestiona por valor, no solo por cantidad." |
| 9:40–10:00 | Vuelves a `REPLICACION.md` | "Procedimiento ejecutado de punta a punta. La versión está congelada en el tag v1.0." |

---

## PARTE 3 — PREGUNTAS PROBABLES (respuestas de 15 segundos)

**1. ¿Por qué el TPP no es un promedio de fechas?**
"Cada salida consume los lotes más antiguos y calculamos la edad promedio ponderada de las
unidades que realmente salieron. Los ingresos tienen permanencia nula. Así medimos cuánto
tiempo estuvo físicamente almacenada la unidad, y sirve para auditar el FIFO."

**2. ¿Rotación 0.98 no es muy baja?**
"Ese 0.98 es el índice de flujo del periodo: salidas entre entradas. La rotación anualizada
en veces por año requiere saldo inicial de inventario, y el periodo arranca en enero con
stock cero. Por eso reportamos el flujo, que sí responde a la decisión de compra; cargar el
saldo inicial está como recomendación en §7.3."

**3. ¿Cómo sé que los números no están inventados?**
"Tres verificaciones independientes: el log de cada corrida, un script que reconstruye el
datamart sin usar el código del ETL y da los mismos KPI, y las consultas SQL del capítulo
VI. Cualquiera de las tres se repite en un minuto."

**4. ¿Qué pasa si un registro llega mal?**
"Se aparta a un CSV con el motivo y la corrida continúa. Lo probamos inyectando cien
defectos: rechazó los cien y cargó el resto sin abortar."

**5. ¿Cómo se automatiza?**
"Credenciales en variables de entorno, un solo comando y el Programador de tareas o cron.
Es idempotente: vacía y recarga en una transacción, así que se puede repetir sin miedo."

**6. ¿Por qué no hay Big Data?**
"Lo evaluamos en §3.2 y §3.5. Son 31,307 registros y el proceso completo tarda 14.6
segundos en un equipo. Un clúster no aportaría mejora medible y sí costo y complejidad.
Quedó documentado con criterios de activación: más de diez millones de lecturas o una
segunda sede."

**7. ¿Por qué modelo estrella y no copo de nieve?**
"Power BI comprime y consulta mejor las dimensiones desnormalizadas, y el usuario necesita
atributos legibles. Además cada pregunta se resuelve con una unión al hecho."

**8. ¿Qué limitaciones tiene el trabajo?**
"Nueve meses de historia, sin saldo inicial; exactitud de 96.55 % que revela diferencias de
una y dos unidades en 16 líneas; y datos anonimizados que impiden comparar contra la
operación real. Todo está declarado en §4.7."

**9. ¿El tablero decide solo?**
"No. Publica indicadores con su meta y el juicio queda en el usuario. Es apoyo a la
decisión, no automatización."

**10. ¿Usaron IA?**
"Sí, como apoyo, y está declarado en §5.7 y en el anexo. Cada cifra la recalculamos y
verificamos contra el log; la responsabilidad del contenido es del equipo."

---

## PARTE 4 — ANTES DE EXPONER (checklist de 5 minutos)

- [ ] Power BI abierto y **minimizado** (que no cargue en frío delante del docente).
- [ ] PowerShell con `OLTP_URL` y `DM_URL` definidas y el comando del ETL en el historial.
- [ ] SSMS con las tres consultas ya escritas en pestañas.
- [ ] Una corrida previa del ETL (calienta la caché de SQL Server: 15 s en vez de 40).
- [ ] Repo abierto en GitHub, en `REPLICACION.md`.
- [ ] Los cinco integrantes saben quién dice qué (si el docente elige, cualquiera responde).

**No ejecutar en vivo:** scripts 01, 02 ni 03 (el 01 borra la base, el 02 son 12,520 INSERT).

**Plan B:** si falla SQL Server → los CSV de `powerbi/respaldo/` y el log JSON.
Si falla Power BI → Figuras 9, 10 y 11 de `evidencias/`.

---

## PARTE 5 — VERSIÓN DE 60 SEGUNDOS (si te cortan el tiempo)

"Unity Perú pierde visibilidad de su almacén porque la información está en cuatro fuentes
dispersas. Construimos un datamart en estrella en SQL Server, cargado por un ETL en Python
con seis reglas de calidad y carga transaccional, y un dashboard en Power BI con tres vistas
y doce medidas. Resultado: 5,348 movimientos conciliados al 100 %, cero rechazados, los seis
KPI en meta y el reporte pasó de seis horas a menos de un segundo. Se replica con un
procedimiento de quince pasos que está en el repositorio."