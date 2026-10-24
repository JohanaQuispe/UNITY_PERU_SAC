# Procedimiento de replicación paso a paso

Este documento permite reconstruir la solución completa en una **computadora distinta**
a la del equipo original, desde cero y sin ayuda de los autores.

- Tiempo total: **30 a 40 minutos** (la mayor parte es instalar programas).
- Si algo falla, ir directo a la sección **12. Problemas frecuentes**.
- Todos los valores entre **negrita** son los que deben aparecer; si no coinciden, detenerse
  y revisar el paso anterior antes de continuar.

---

## 0. Qué hay que instalar (una sola vez)

| # | Programa | Dónde se descarga | Cómo saber que quedó bien |
|---|---|---|---|
| 1 | SQL Server Express | https://www.microsoft.com/es-es/sql-server/sql-server-downloads → "Express" | Aparece el servicio **SQL Server (SQLEXPRESS)** en Servicios de Windows |
| 2 | SQL Server Management Studio (SSMS) | https://aka.ms/ssmsfullsetup | Abre la ventana "Conectar al servidor" |
| 3 | Python 3.10 o superior | https://www.python.org/downloads/ | En PowerShell: `python --version` responde `Python 3.1x.x` |
| 4 | ODBC Driver 17 u 18 for SQL Server (**64 bits**) | https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server | Aparece en **Orígenes de datos ODBC (64 bits) → Controladores** |
| 5 | Power BI Desktop | Microsoft Store (buscar "Power BI Desktop") | Abre la ventana de inicio de Power BI |
| 6 | Git (opcional) | https://git-scm.com/download/win | `git --version` responde `git version 2.x` |

> **Importante:** Python y el driver ODBC deben ser **los dos de 64 bits**.
> Si Python es 32 bits y el driver 64 bits, el ETL fallará con `Data source name not found`.

Al instalar Python, marcar la casilla **"Add python.exe to PATH"** en la primera pantalla.

---

## 1. Descargar el proyecto

### Opción A — con Git (recomendada)

```powershell
git clone https://github.com/JohanaQuispe/UNITY_PERU_SAC.git
cd UNITY_PERU_SAC
git checkout v1.0
```

### Opción B — sin Git

1. Abrir https://github.com/JohanaQuispe/UNITY_PERU_SAC
2. Botón verde **Code → Download ZIP**
4. Descomprimir en una ruta **sin espacios ni tildes**, por ejemplo `C:\proyecto\UNITY_PERU_SAC`

   <img width="606" height="615" alt="image" src="https://github.com/user-attachments/assets/a2a6ae0b-87f8-4dd0-a967-15f0f13ff7eb" />

**Verificación:** dentro de la carpeta deben existir `scripts`, `etl`, `datos`, `logs`,
`powerbi`, `evidencias`, `analisis` y `docs`.

> **Todas las instrucciones siguientes se ejecutan desde la raíz de esa carpeta.**
> En PowerShell, la ruta debe terminar en `\UNITY_PERU_SAC>`.

---

## 2. Verificar que Python ve las librerías

```powershell
python --version
pip --version
```
<img width="1508" height="176" alt="image" src="https://github.com/user-attachments/assets/3a8dd65a-a923-4730-84e6-6085e43a22f2" />

Debe responder `Python 3.10` o superior y una ruta de `pip` que contenga la misma versión.
Si `python` no se reconoce, reinstalar marcando **"Add python.exe to PATH"**.

---

## 3. Crear la base operacional (script 01)

1. Abrir **SQL Server Management Studio**.
2. En "Conectar al servidor":
   - **Tipo de servidor:** Motor de base de datos
   - **Nombre del servidor:** `localhost\SQLEXPRESS`
     (si no conecta, probar `.\SQLEXPRESS` o el nombre que muestra `SELECT @@SERVERNAME`)
   - **Autenticación:** *Autenticación de Windows* (viene por defecto)
3. **Conectar**.
4. Menú **Archivo → Abrir → Archivo…** y seleccionar `scripts\01_OLTP_ALMACEN_ANONIMIZADO.sql`.
   (También sirve arrastrar el archivo a la ventana.)
5. Presionar **F5** (Ejecutar).

> Este script **borra y recrea** la base `ALMACEN_ANONIMO` si ya existía. Es seguro ejecutarlo
> varias veces. Crea 21 tablas.

**Verificación:**

```sql
SELECT name FROM sys.databases WHERE name = 'ALMACEN_ANONIMO';
```
<img width="278" height="114" alt="image" src="https://github.com/user-attachments/assets/3a85803d-edeb-478a-9903-4aa768348b20" />

Debe devolver una fila: `ALMACEN_ANONIMO`.

---

## 4. Cargar los datos operacionales (script 02)

1. **Archivo → Abrir → Archivo…** → `scripts\02_DATOS_ANONIMOS_ALMACEN.sql`
2. **F5**. Tarda entre 20 y 60 segundos (son 12.520 líneas de INSERT).
3. Esperar hasta que la barra de estado diga **"Consulta ejecutada correctamente"**.

**Verificación (ejecutar en una pestaña nueva):**

```sql
SELECT COUNT(*) AS Movimientos FROM ALMACEN_ANONIMO.dbo.movimiento_componente;
```

Debe devolver **5348**.

<img width="231" height="105" alt="image" src="https://github.com/user-attachments/assets/840edf5a-9a43-490e-a667-50304ecfc25c" />

> Si SSMS muestra `5348.00`, es porque la columna es DECIMAL: el número real es 5348.

---

## 5. Crear el datamart (script 03)

1. **Archivo → Abrir → Archivo…** → `scripts\03_DM_ALMACEN_ANONIMO.sql`
2. **F5**.

> Este script crea la base `DM_ALMACEN_ANONIMO` con **14 tablas vacías**:
> 1 tabla de hechos, 9 dimensiones y 4 de staging.
> **Es obligatorio ejecutarlo antes del ETL**: el ETL no crea tablas en SQL Server.

**Verificación:**

```sql
SELECT COUNT(*) AS Tablas FROM DM_ALMACEN_ANONIMO.sys.tables;
```

<img width="229" height="99" alt="image" src="https://github.com/user-attachments/assets/9df73191-f826-479f-8c3c-354b4beed05a" />

Debe devolver **14**.

---

## 6. Definir las credenciales

El ETL **no tiene contraseñas en el código**: las lee de dos variables de entorno.
Abrir **PowerShell** y ejecutar las dos líneas de la opción que corresponda.

### Opción A — Autenticación de Windows (la más simple, recomendada)

```powershell
$env:OLTP_URL = "mssql+pyodbc://localhost\SQLEXPRESS/ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
$env:DM_URL   = "mssql+pyodbc://localhost\SQLEXPRESS/DM_ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
```

### Opción B — Usuario y contraseña

```powershell
$env:OLTP_URL = "mssql+pyodbc://sa:TU_CLAVE@localhost\SQLEXPRESS/ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server"
$env:DM_URL   = "mssql+pyodbc://sa:TU_CLAVE@localhost\SQLEXPRESS/DM_ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server"
```

Reemplazar `TU_CLAVE` por la contraseña real.

**Ajustes según el equipo:**

| Situación | Qué cambiar |
|---|---|
| Tienen ODBC Driver **18** en vez de 17 | Cambiar `ODBC+Driver+17` por `ODBC+Driver+18` |
| El servidor se llama distinto | Cambiar `localhost\SQLEXPRESS` por el nombre real |
| Es una instancia por defecto (no Express) | Usar solo `localhost` |

**Verificación:** las variables deben seguir cargadas en **esa misma ventana**:

```powershell
$env:OLTP_URL = "mssql+pyodbc://localhost/ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
$env:DM_URL   = "mssql+pyodbc://localhost/DM_ALMACEN_ANONIMO?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
```

> ⚠️ Si se cierra PowerShell, las variables se pierden. Hay que repetir este paso.

---

## 7. Instalar las librerías de Python

Desde la raíz del proyecto:

```powershell
pip install -r etl\requirements.txt
```

Instala `pandas`, `sqlalchemy`, `pyodbc` y `openpyxl`. Tarda 1–2 minutos.

**Verificación:**

```powershell
python -c "import pandas, sqlalchemy, pyodbc, openpyxl; print('librerias OK')"
```

<img width="1553" height="57" alt="image" src="https://github.com/user-attachments/assets/056c423e-d42f-4652-89a3-e6620bdb06e6" />

Debe responder `librerias OK`.

---

## 8. Ejecutar el ETL

Desde la raíz del proyecto y **en la misma ventana de PowerShell** del paso 6:

```powershell
python etl\etl_almacen_unity.py --datos datos --log logs
```
<img width="1242" height="107" alt="image" src="https://github.com/user-attachments/assets/b9ec9774-f9e2-4f42-9ecf-ac44cb4ce032" />

**Salida esperada (una línea + la ruta del log):**

```
ETL v2.0 OK: 5348 cargados, 0 rechazados, completitud 100.0%, reconciliacion=True
Log: logs\etl_log_AAAAMMDD_HHMMSS.json
```

Tiempo esperado: **15 a 40 segundos**. En la primera corrida puede tardar más.

**Qué hace el ETL, en orden:**

1. **Extracción** — lee la base operacional y los 3 archivos de `datos/`.
2. **Perfilado** — cuenta nulos, duplicados, cantidades ≤ 0 y productos inexistentes.
3. **Limpieza** — aplica las 6 reglas de calidad y aparta lo inválido en
   `logs\movimientos_rechazados.csv` con el motivo.
4. **Transformación** — arma los lotes FIFO, calcula la permanencia, marca las anomalías
   ambientales y calcula la exactitud de los conteos.
5. **Carga** — vacía y recarga las 14 tablas dentro de **una sola transacción**.
   Si algo falla, revierte todo y el datamart queda como estaba.

**Si aparece el mensaje esperado, la replicación ya está completa.** Los pasos 9 y 10 son la verificación.

---

## 9. Verificar el datamart en SQL Server

Abrir una pestaña nueva en SSMS y ejecutar:

```sql
USE DM_ALMACEN_ANONIMO;

-- 1. Filas del hecho
SELECT COUNT(*) AS Filas_Hecho FROM dbo.Fact_Movimiento;            -- 5348

-- 2. Permanencia promedio
SELECT AVG(Dias_Permanencia) AS TPP FROM dbo.Fact_Movimiento;       -- 3.868701

-- 3. Lotes FIFO
SELECT COUNT(*) AS Lotes FROM dbo.Dim_Lote;                         -- 3685

-- 4. Salidas con permanencia (los ingresos deben ser NULL)
SELECT COUNT(*) AS Salidas_Con_Permanencia
FROM dbo.Fact_Movimiento WHERE Dias_Permanencia IS NOT NULL;        -- 1663

-- 5. Ingresos NO deben tener permanencia
SELECT COUNT(*) AS Ingresos_Con_Permanencia
FROM dbo.Fact_Movimiento f
JOIN dbo.Dim_TipoMovimiento t ON f.Id_TipoMovimiento = t.Id_TipoMovimiento
WHERE t.Es_Entrada = 1 AND f.Dias_Permanencia IS NOT NULL;          -- 0

-- 6. Unidades conciliadas con el origen
SELECT
  SUM(CASE WHEN t.Es_Entrada = 1 THEN f.Cantidad ELSE 0 END) AS Unidades_Entrada,  -- 15425
  SUM(CASE WHEN t.Es_Salida_Real = 1 THEN f.Cantidad ELSE 0 END) AS Unidades_Salida -- 15078
FROM dbo.Fact_Movimiento f
JOIN dbo.Dim_TipoMovimiento t ON f.Id_TipoMovimiento = t.Id_TipoMovimiento;
```

**Tabla de resultados esperados:**

| Consulta | Valor esperado |
|---|---|
| Filas del hecho | **5348** |
| TPP | **3.868701** |
| Lotes | **3685** |
| Salidas con permanencia | **1663** |
| Ingresos con permanencia | **0** |
| Unidades de entrada | **15425** |
| Unidades de salida | **15078** |

**Revisar también el log generado:** abrir `logs\etl_log_AAAAMMDD_HHMMSS.json` y confirmar
`"registros_cargados": 5348`, `"completitud_pct": 100.0` y `"reconciliacion_ok": true`.

---

## 10. Verificación independiente (opcional, 1 minuto)

Comprueba los KPI con un script que **no** usa el código del ETL:

```powershell
pip install openpyxl
python analisis\calcular_kpis.py
```

**Salida esperada:**

```
TPP = 3.868701 | filas = 5348 | rechazados = 0 | conciliación = True
```

Genera `analisis\salidas\kpis.json` y 14 archivos CSV en `powerbi\respaldo\`.

---

## 11. Abrir el dashboard en Power BI

1. Abrir **Power BI Desktop**.
2. **Archivo → Abrir** → `powerbi\Dashboard_Almacen_BI.pbix`.
3. Si pide credenciales, elegir *Base de datos → Autenticación de Windows* y **Conectar**.
4. Menú **Inicio → Actualizar**. Esperar 20–40 segundos.
5. Si el origen apunta a otro servidor: **Inicio → Transformar datos → Configuración de origen**
   → cambiar el servidor → **Actualizar**.

**Verificar las 5 tarjetas de la página 1:**

| Indicador | Valor esperado |
|---|---|
| TPP | **3.87** |
| Rotación global | **0.98** |
| Inversión retenida | **S/ 812 mil** |
| Cumplimiento del plan | **0.77 %** |
| Anomalías ambientales | **297** |

Y en las páginas 2 y 3: **0 de 24** componentes bajo el mínimo y **96.55 %** de exactitud.

**Si no hay `.pbix` disponible**, construirlo en 15 minutos siguiendo
`powerbi/GUIA_POWERBI.md` (relaciones, 12 medidas DAX, tema visual y maqueta de las 3 páginas).

---

## 12. Plan B: el dashboard sin SQL Server

Si el equipo de exposición no tiene SQL Server o falla la conexión:

1. Abrir Power BI Desktop → **Obtener datos → Carpeta**.
2. Seleccionar la carpeta `powerbi\respaldo\` (14 archivos CSV).
3. **Combinar y transformar** → expandir → **Cerrar y aplicar**.
4. Aplicar las relaciones y medidas de `powerbi\GUIA_POWERBI.md` (pasos 2 a 4).

Los CSV son el contenido exacto del datamart, así que los KPI dan idénticos.

---

## 13. Problemas frecuentes en una máquina nueva

| Error | Causa | Solución |
|---|---|---|
| `python no se reconoce como comando` | No se marcó "Add to PATH" | Reinstalar Python marcando esa casilla |
| `ERROR: defina OLTP_URL y DM_URL` | Variables no definidas en esa ventana | Repetir el paso 6 **en la misma** PowerShell |
| `Data source name not found` | Falta el driver ODBC o es de 32 bits | Instalar ODBC Driver 17 **64 bits** |
| `Login failed for user 'sa'` | `sa` deshabilitado o clave distinta | Usar la Opción A (autenticación de Windows) del paso 6 |
| `No se puede abrir la base de datos` / timeout | Nombre del servidor incorrecto | Probar `localhost`, `.\SQLEXPRESS` o `SELECT @@SERVERNAME` |
| `Invalid object name 'Fact_Movimiento'` | No se ejecutó el script 03 | Ejecutar `scripts\03_DM_ALMACEN_ANONIMO.sql` |
| `FileNotFoundError: Plan_Demanda_2026.xlsx` | Se ejecutó desde otra carpeta | Situarse en la raíz del proyecto (paso 1) |
| `Sheet 'Plan_Mensual' not found` | Se modificó o renombró el Excel | Restaurar el archivo original de `datos\` |
| Tablas vacías después de "ETL OK" | Se apuntó a otra base | Revisar que `DM_URL` diga `DM_ALMACEN_ANONIMO` |
| Power BI muestra cifras distintas | Modelo desactualizado | **Inicio → Actualizar** |
| Power BI no abre el `.pbix` | Versión antigua de Power BI | Actualizar Power BI Desktop desde Microsoft Store |

---

## 14. Demostración funcional (10 minutos)

El procedimiento anterior **es** la demostración: se ejecuta en vivo y se van mostrando los pasos.

| Min | Paso | Acción | Frase clave |
|---|---|---|---|
| 0:00–0:45 | 1 | Mostrar el repositorio y este archivo | "El procedimiento es este y ya se ejecutó completo" |
| 0:45–1:15 | 5 | Abrir `scripts\03_DM_ALMACEN_ANONIMO.sql` (**sin ejecutar**) | "14 tablas: 1 hecho, 9 dimensiones y 4 de staging" |
| 1:15–3:15 | 8 | Ejecutar el ETL en vivo | "Un comando, cinco fases, 5.348 filas" |
| 3:15–4:30 | 8 y 9 | Abrir el log JSON y `movimientos_rechazados.csv` | "0 rechazados, 100 % completitud, reconciliación OK" |
| 4:30–5:30 | 6 | Mostrar las variables de entorno | "Credenciales fuera del código; carga transaccional y re-ejecutable" |
| 5:30–7:00 | 9 | 3 consultas en pestañas de SSMS | "5.348 / 3,868701 / ingresos NULL / 3.685 lotes" |
| 7:00–9:30 | 11 | Las 3 páginas del dashboard + 2 filtros | Una decisión por vista: compras, despachos, proyectos |
| 9:30–10:00 | — | Volver a este archivo | "Procedimiento ejecutado; versión congelada v1.0" |

**Antes de exponer (5 minutos antes):**

- Power BI abierto y minimizado (para que no cargue en frío).
- PowerShell con las variables del paso 6 ya definidas y el comando del ETL en el historial.
- SSMS con las consultas del paso 9 ya escritas en pestañas.
- Una corrida previa del ETL, para calentar la caché de SQL Server.

**Qué NO hacer en vivo:** ejecutar los scripts 01, 02 ni 03 (el 01 borra la base y el 02 son
12.520 INSERT). Se muestran como archivos, no se ejecutan.

**Plan de contingencia:** si falla SQL Server → usar el plan B del paso 12 con los CSV.
Si falla Power BI → mostrar las Figuras 9 a 11 de `evidencias\`, que son las capturas del tablero.

---

## 15. Checklist final

- [ ] SQL Server y SSMS instalados
- [ ] Python 3.10+ con PATH y ODBC Driver 64 bits
- [ ] Repositorio descargado (tag `v1.0`)
- [ ] `scripts\01` ejecutado → base `ALMACEN_ANONIMO`
- [ ] `scripts\02` ejecutado → **5348** movimientos
- [ ] `scripts\03` ejecutado → **14** tablas
- [ ] Variables `OLTP_URL` y `DM_URL` definidas
- [ ] `pip install -r etl\requirements.txt` sin errores
- [ ] ETL ejecutado → `5348 cargados, 0 rechazados, reconciliacion=True`
- [ ] TPP en SQL = **3.868701**
- [ ] Log JSON con `reconciliacion_ok: true`
- [ ] Dashboard abierto y actualizado con los 5 KPI correctos

Si las 12 casillas están marcadas, la replicación es exitosa y la demostración puede ejecutarse.
