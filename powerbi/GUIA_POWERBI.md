# Guía de construcción del dashboard (.pbix) — 15 minutos

> El archivo `.pbix` es un formato binario que **solo Power BI Desktop puede generar**; por eso el
> repositorio entrega todo lo necesario para construirlo en minutos: el modelo en CSV, las 12 medidas
> DAX, el tema visual y la maqueta de cada página. Al terminar, guarda el archivo como
> `powerbi/Dashboard_Almacen_BI.pbix` y con eso queda completo el entregable.

Tiempo estimado: **15–20 min**. Requisito: Power BI Desktop actualizado (Microsoft Store).

---

## Paso 0. Elegir el origen de datos

Tienes dos caminos; ambos producen el mismo modelo.

| Camino | Cuándo usarlo | Cómo |
|---|---|---|
| **A. SQL Server (recomendado para la demo)** | Ya ejecutaste el ETL y tienes el datamart cargado | Inicio → Obtener datos → SQL Server → servidor `localhost`, base `DM_ALMACEN_ANONIMO`, modo **Importación** → seleccionar las 14 tablas |
| **B. Carpeta de CSV (sin SQL Server)** | Cambiaste de equipo o la conexión falla | Inicio → Obtener datos → Carpeta → ruta `powerbi/respaldo` → Combinar y transformar → **Expandir** cada archivo… ver Paso 1B |

---

## Paso 1B. Cargar desde los CSV (solo si elegiste el camino B)

1. Obtener datos → **Carpeta** → examinar `powerbi/respaldo` → Aceptar.
2. En Power Query verás una fila por archivo. Clic en **Transformar datos**.
3. Selecciona la columna `Content` → botón derecho → **Quitar otras columnas**.
4. Con `Content` seleccionada: Inicio → **Combinar archivos** → Aceptar (elige el primer archivo como plantilla y confirma el delimitador **punto y coma**, codificación **UTF-8**).
5. En la consulta combinada, agrega una columna `Tabla` con el nombre del archivo:
   Agregar columna → Columna personalizada → `= [Source.Name]` → quitar la extensión con
   Transformar → **Columna de ejemplo** → reemplazar `.csv` por vacío (o usar
   `= Text.BeforeDelimiter([Source.Name], ".csv")`).
6. Inicio → **Cerrar y aplicar**. Se cargan 14 consultas.
7. Renombra cada consulta con el nombre de su tabla (`Dim_Tiempo`, `Dim_Producto`, …, `Fact_Movimiento`,
   `stg_*`) y verifica que cada una tenga exactamente las columnas de la Tabla 6 del informe.

---

## Paso 2. Crear las relaciones (vista Modelo)

Vista **Modelo** → arrastra de `Fact_Movimiento` a cada dimensión:

| Desde (hecho) | Hacia (dimensión) | Cardinalidad | Activa |
|---|---|---|---|
| Id_Fecha | Dim_Tiempo[Id_Fecha] | * → 1 | Sí |
| Id_Producto | Dim_Producto[Id_Producto] | * → 1 | Sí |
| Id_TipoMovimiento | Dim_TipoMovimiento[Id_TipoMovimiento] | * → 1 | Sí |
| Id_Almacen_Origen | Dim_Almacen[Id_Almacen] | * → 1 | Sí |
| Id_Almacen_Destino | Dim_Almacen[Id_Almacen] | * → 1 | **No** (relación inactiva) |
| Id_Proyecto | Dim_Proyecto[Id_Proyecto] | * → 1 | Sí |
| Id_Responsable | Dim_Responsable[Id_Responsable] | * → 1 | Sí |
| Id_Proveedor | Dim_Proveedor[Id_Proveedor] | * → 1 | Sí |
| Id_Estado_Anterior | Dim_Estado[Id_Estado] | * → 1 | **No** (relación inactiva) |
| Id_Estado_Nuevo | Dim_Estado[Id_Estado] | * → 1 | Sí |
| Id_Lote | Dim_Lote[Id_Lote] | * → 1 | Sí |

Relaciones adicionales para que el cumplimiento del plan (VM) funcione **por mes y por categoría**
(sin ellas, `SUM(stg_Plan_Mensual[...])` devuelve siempre el total del periodo):

| Desde | Hacia | Cardinalidad | Dirección del filtro |
|---|---|---|---|
| stg_Plan_Mensual[Mes] | Dim_Tiempo[Mes] | * a * | Única |
| stg_Plan_Mensual[Categoria] | Dim_Producto[Categoria] | * a * | Única |

Ajustes finales del modelo:

- `Dim_Tiempo[Nombre_Mes]` → Herramientas de tabla → **Ordenar por columna** → `Mes`.
- `Dim_Tiempo[Mes]` y `Dim_Producto[Categoria]` deben ser **únicas** para la relación * a *: si Power BI
  las marca como ambiguas, crea `Dim_Categoria` (tabla calculada `SUMMARIZE(Dim_Producto, Dim_Producto[Categoria])`)
  y relaciona el plan con ella y con `Dim_Tiempo[Mes]`; el resultado de VM es el mismo.
- Selecciona las 4 tablas `stg_*` → botón derecho → **Ocultar en la vista de informe**.
- `Fact_Movimiento[Dias_Permanencia]` → Formato → 2 decimales. `Costo_Total` → moneda S/.
- Tema visual: Ver → Temas → **Examinar temas** → `powerbi/Tema_Almacen_Unity.json`.

---

## Paso 3. Pegar las 12 medidas

Inicio → **Escribir datos** no; usar: clic derecho en `Fact_Movimiento` → **Nueva medida** y pegar una por una
(o pegar todo el bloque de `powerbi/medidas_DAX.txt` en el editor de DAX con **Nueva medida** repetido).

```
Unidades_Entradas = CALCULATE(SUM(Fact_Movimiento[Cantidad]), Dim_TipoMovimiento[Es_Entrada] = TRUE())
Unidades_Salidas  = CALCULATE(SUM(Fact_Movimiento[Cantidad]), Dim_TipoMovimiento[Es_Salida_Real] = TRUE())
Costo_Entradas    = CALCULATE(SUM(Fact_Movimiento[Costo_Total]), Dim_TipoMovimiento[Es_Entrada] = TRUE())
Costo_Salidas     = CALCULATE(SUM(Fact_Movimiento[Costo_Total]), Dim_TipoMovimiento[Es_Salida_Real] = TRUE())
Inversion_Retenida = [Costo_Entradas] - [Costo_Salidas]
Rotacion_Global   = DIVIDE([Unidades_Salidas], [Unidades_Entradas])
TPP               = AVERAGE(Fact_Movimiento[Dias_Permanencia])
Stock_Neto        = [Unidades_Entradas] - [Unidades_Salidas]
VM_Entradas       = DIVIDE([Unidades_Entradas] - SUM(stg_Plan_Mensual[Entradas_Plan]), SUM(stg_Plan_Mensual[Entradas_Plan]))
VM_Salidas        = DIVIDE([Unidades_Salidas] - SUM(stg_Plan_Mensual[Salidas_Plan]), SUM(stg_Plan_Mensual[Salidas_Plan]))
N_Anomalias       = COUNTROWS(FILTER(stg_Sensores, stg_Sensores[Es_Anomalia] = TRUE()))
Exactitud_Global  = AVERAGE(stg_Conteos[Exactitud_Linea])
```

Formato: `TPP` 2 decimales · `Rotacion_Global` 2 decimales · `VM_*` porcentaje con 2 decimales ·
`Inversion_Retenida` moneda.

**Valores que deben aparecer (no continúes si no coinciden):** TPP **3.87** · Entradas **15,425** ·
Salidas **15,078** · Inversión retenida **S/ 812,060** · Rotación **0.98** · VM **+0.77 % / −0.75 %** ·
Anomalías **297** · Exactitud **96.55 %**. Si un valor difiere, revisa la relación del tipo de movimiento
y que no haya duplicados por haber cargado dos veces las tablas.

---

## Paso 4. Página 1 — «Gerencial» (¿compramos o esperamos?)

Fondo `#F4F6F8`. Título de texto: **Vista Gerencial — ¿compramos o esperamos?**

| Zona | Visual | Campos |
|---|---|---|
| Fila superior (5 tarjetas) | **Tarjeta** ×5 | `TPP`, `Rotacion_Global`, `Inversion_Retenida`, `VM_Entradas`, `N_Anomalias` |
| Abajo izquierda | **Gráfico de columnas agrupadas** | Eje: `Dim_Tiempo[Nombre_Mes]` · Valores: `Unidades_Entradas`, `Unidades_Salidas` |
| Abajo derecha | **Gráfico de líneas** + línea de meta | Eje: `Dim_Tiempo[Nombre_Mes]` · Valores: `TPP` · Línea constante en 45 (Analytics → Línea Y) |
| Franja inferior izquierda | **Barras horizontales** | Eje: `Dim_Producto[Categoria]` · Valores: `Costo_Entradas`, ordenado descendente |
| Franja inferior derecha | **Columnas agrupadas** | Eje: `Dim_Tiempo[Nombre_Mes]` · Valores: `VM_Entradas`, `VM_Salidas` |

Segmentadores (arriba, alineados): `Dim_Tiempo[Fecha]` (entre fechas) · `Dim_Producto[Categoria]` ·
`Dim_Producto[Criticidad]`. Formato → **Modo de selección** = único para categoría y criticidad.

---

## Paso 5. Página 2 — «Operativa» (¿qué despachamos y qué está retenido?)

| Zona | Visual | Campos |
|---|---|---|
| Izquierda | **Matriz** con formato condicional (escala de color) | Filas: `Dim_Producto[Categoria]` · Columnas: `Dim_Tiempo[Nombre_Mes]` · Valores: `TPP` |
| Derecha | **Barras horizontales** | Eje: `Dim_Producto[Cod_Componente]` · Valores: `TPP` · ordenado descendente · línea constante en 3.87 |
| Abajo izquierda | **Columnas** | Eje: `Dim_Tiempo[Nombre_Mes]` · Valores: `N_Anomalias` |
| Abajo derecha | **Tarjeta / texto** | `Exactitud_Global` + conteo de componentes sobre stock mínimo (ver DAX opcional) |

Para la matriz: clic en el visual → Formato → **Celdas** → Color de fuente → ficha **Formato condicional**
→ Escala de colores (mínimo amarillo claro, máximo rojo).

**Medida opcional (alerta de stock):**

```
Componentes_Bajo_Minimo =
VAR stock = SUMMARIZE(Dim_Producto, Dim_Producto[Cod_Componente],
              "neto", [Stock_Neto], "minimo", MAX(Dim_Producto[Stock_Minimo]))
RETURN COUNTROWS(FILTER(stock, [neto] < [minimo]))
```

---

## Paso 6. Página 3 — «Proyectos» (¿hay disponibilidad para comprometer?)

| Zona | Visual | Campos |
|---|---|---|
| Izquierda | **Barras horizontales** | Eje: `Dim_Proyecto[Nombre_Proyecto]` · Valores: `Unidades_Salidas` |
| Derecha | **Columnas** | Eje: `Dim_Producto[Criticidad]` · Valores: `COUNTROWS(Dim_Producto)` |
| Abajo izquierda | **Gráfico de líneas** | Eje: `stg_Conteos[Fecha]` · Valores: `Exactitud_Global` · línea constante en 0.95 |
| Abajo derecha | **Cuadro de texto** con las 4 acciones recomendadas | — |

Segmentadores compartidos: `Dim_Proyecto[Nombre_Proyecto]` y `Dim_Producto[Criticidad]`.

---

## Paso 7. Detalles que el docente suele revisar

1. **Título de cada página** con la decisión que responde (no «Página 1»).
2. **Unidades y metas visibles**: toda tarjeta con su meta al lado (texto o etiqueta del visual).
3. **Filtros compartidos**: usa *Sincronizar segmentadores* (Ver → Sincronizar segmentadores) para fecha y categoría en las tres páginas.
4. **Sin tablas de staging visibles**: deben estar ocultas en la vista de informe.
5. **Nombres limpios**: renombra las páginas a `Gerencial`, `Operativa`, `Proyectos`.
6. **Actualizar**: Inicio → Actualizar y confirmar que las cifras siguen iguales.
7. Guarda como `powerbi/Dashboard_Almacen_BI.pbix` y **súbelo al repositorio** (es el entregable E-13).

## Paso 8. Verificación final (30 segundos)

| Verificación | Valor esperado |
|---|---|
| Filas en `Fact_Movimiento` (vista Datos) | 5,348 |
| `TPP` | 3.87 |
| `Unidades_Entradas` / `Unidades_Salidas` | 15,425 / 15,078 |
| `Inversion_Retenida` | 812,060 |
| `VM_Entradas` / `VM_Salidas` | 0.77 % / −0.75 % |
| `N_Anomalias` | 297 |
| `Exactitud_Global` | 0.9655 (96.55 %) |

Si el archivo `.pbix` no se puede guardar en el repositorio por tamaño, usa Git LFS o comprime el proyecto
como plantilla `.pbit` (Archivo → Exportar → Plantilla de Power BI), que conserva el modelo y las medidas.
