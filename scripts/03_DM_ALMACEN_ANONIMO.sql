/* ====================================================================
   DATAMART DM_ALMACEN_ANONIMO (v2: + Dias_Permanencia en el hecho)
   9 dimensiones + 1 hecho + 4 tablas staging (el staging NO es
   parte de la estrella: es el área de paso del ETL).
   Ejecutar en SQL Server. El ETL Python lo carga (ver §3.4.3).
   ==================================================================== */
USE master;
GO
IF DB_ID('DM_ALMACEN_ANONIMO') IS NOT NULL
BEGIN
    ALTER DATABASE DM_ALMACEN_ANONIMO SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE DM_ALMACEN_ANONIMO;
END
GO
CREATE DATABASE DM_ALMACEN_ANONIMO;
GO
USE DM_ALMACEN_ANONIMO;
GO

CREATE TABLE dbo.Dim_Tiempo (
    Id_Fecha       INT PRIMARY KEY,   /* AAAAMMDD */
    Fecha          DATE NOT NULL,
    Anio           INT NOT NULL,
    Trimestre      INT NOT NULL,
    Mes            INT NOT NULL,
    Nombre_Mes     VARCHAR(20) NOT NULL,
    Dia_Semana     INT NOT NULL,
    Nombre_Dia     VARCHAR(20) NOT NULL,
    Es_Fin_Semana  BIT NOT NULL
);
GO
CREATE TABLE dbo.Dim_Producto (
    Id_Producto     INT IDENTITY(1,1) PRIMARY KEY,
    Cod_Componente  VARCHAR(20) NOT NULL UNIQUE,
    Descripcion     VARCHAR(180) NOT NULL,
    Categoria       VARCHAR(80) NOT NULL,
    Marca           VARCHAR(80) NOT NULL,
    Modelo          VARCHAR(100) NOT NULL,
    Criticidad      VARCHAR(20) NOT NULL,
    Stock_Minimo    DECIMAL(12,2) NOT NULL,
    Precio_Unitario DECIMAL(12,2) NOT NULL
);
GO
CREATE TABLE dbo.Dim_Almacen (
    Id_Almacen        INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Ubicacion  VARCHAR(30) NOT NULL UNIQUE,
    Nombre_Ubicacion  VARCHAR(100) NOT NULL,
    Tipo_Ubicacion    VARCHAR(40) NOT NULL
);
GO
CREATE TABLE dbo.Dim_TipoMovimiento (
    Id_TipoMovimiento INT IDENTITY(1,1) PRIMARY KEY,
    Codigo            VARCHAR(30) NOT NULL UNIQUE,
    Nombre            VARCHAR(80) NOT NULL,
    Signo_Stock       SMALLINT NOT NULL,
    Es_Entrada        BIT NOT NULL,
    Es_Salida_Real    BIT NOT NULL
);
GO
CREATE TABLE dbo.Dim_Proyecto (
    Id_Proyecto     INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Proyecto VARCHAR(20) NOT NULL UNIQUE,
    Nombre_Proyecto VARCHAR(150) NOT NULL,
    Tipo_Proyecto   VARCHAR(60) NOT NULL,
    Estado          VARCHAR(30) NOT NULL
);
GO
CREATE TABLE dbo.Dim_Responsable (
    Id_Responsable     INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Responsable VARCHAR(20) NOT NULL UNIQUE,
    Nombre             VARCHAR(150) NOT NULL,
    Cargo              VARCHAR(80) NULL
);
GO
CREATE TABLE dbo.Dim_Proveedor (
    Id_Proveedor  INT IDENTITY(1,1) PRIMARY KEY,
    Ruc_Proveedor CHAR(11) NOT NULL UNIQUE,
    Nombre        VARCHAR(150) NOT NULL
);
GO
CREATE TABLE dbo.Dim_Estado (
    Id_Estado        INT IDENTITY(1,1) PRIMARY KEY,
    Nombre_Estado    VARCHAR(30) NOT NULL UNIQUE,
    Disponible_Stock BIT NOT NULL
);
GO
CREATE TABLE dbo.Dim_Lote (
    Id_Lote          INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Lote      VARCHAR(45) NOT NULL UNIQUE,
    Cod_Componente   VARCHAR(20) NOT NULL,
    Id_Entrada       VARCHAR(20) NOT NULL,
    Fecha_Ingreso    DATE NOT NULL,
    Cantidad_Lote    DECIMAL(12,2) NOT NULL,
    Codigo_Ubicacion VARCHAR(30) NOT NULL
);
GO
CREATE TABLE dbo.Fact_Movimiento (
    Id_Movimiento_NK  BIGINT PRIMARY KEY,  /* Id del OLTP */
    Id_Fecha          INT NOT NULL,
    Id_Producto       INT NOT NULL,
    Id_TipoMovimiento INT NOT NULL,
    Id_Almacen_Origen INT NULL,
    Id_Almacen_Destino INT NULL,
    Id_Proyecto       INT NULL,
    Id_Responsable    INT NULL,
    Id_Proveedor      INT NULL,
    Id_Estado_Anterior INT NULL,
    Id_Estado_Nuevo   INT NULL,
    Id_Lote           INT NULL,
    Cantidad          DECIMAL(12,2) NOT NULL,
    Costo_Total       DECIMAL(14,2) NOT NULL,
    Dias_Permanencia  DECIMAL(8,2) NULL,   /* solo salidas: edad promedio (FIFO) de las unidades al salir */
    CONSTRAINT FK_fact_tiempo FOREIGN KEY (Id_Fecha)
        REFERENCES dbo.Dim_Tiempo(Id_Fecha),
    CONSTRAINT FK_fact_producto FOREIGN KEY (Id_Producto)
        REFERENCES dbo.Dim_Producto(Id_Producto),
    CONSTRAINT FK_fact_tipo FOREIGN KEY (Id_TipoMovimiento)
        REFERENCES dbo.Dim_TipoMovimiento(Id_TipoMovimiento),
    CONSTRAINT FK_fact_alm_ori FOREIGN KEY (Id_Almacen_Origen)
        REFERENCES dbo.Dim_Almacen(Id_Almacen),
    CONSTRAINT FK_fact_alm_des FOREIGN KEY (Id_Almacen_Destino)
        REFERENCES dbo.Dim_Almacen(Id_Almacen),
    CONSTRAINT FK_fact_proyecto FOREIGN KEY (Id_Proyecto)
        REFERENCES dbo.Dim_Proyecto(Id_Proyecto),
    CONSTRAINT FK_fact_responsable FOREIGN KEY (Id_Responsable)
        REFERENCES dbo.Dim_Responsable(Id_Responsable),
    CONSTRAINT FK_fact_proveedor FOREIGN KEY (Id_Proveedor)
        REFERENCES dbo.Dim_Proveedor(Id_Proveedor),
    CONSTRAINT FK_fact_est_ant FOREIGN KEY (Id_Estado_Anterior)
        REFERENCES dbo.Dim_Estado(Id_Estado),
    CONSTRAINT FK_fact_est_nuevo FOREIGN KEY (Id_Estado_Nuevo)
        REFERENCES dbo.Dim_Estado(Id_Estado),
    CONSTRAINT FK_fact_lote FOREIGN KEY (Id_Lote)
        REFERENCES dbo.Dim_Lote(Id_Lote)
);
GO

/* ---- Staging (área de paso, sin FK) ---- */
CREATE TABLE dbo.stg_Plan_Mensual (
    Anio INT NOT NULL, Mes INT NOT NULL, Categoria VARCHAR(80) NOT NULL,
    Entradas_Plan DECIMAL(12,2) NOT NULL, Salidas_Plan DECIMAL(12,2) NOT NULL
);
GO
CREATE TABLE dbo.stg_Sensores (
    Timestamp DATETIME NOT NULL, Sensor_Id VARCHAR(20) NOT NULL,
    Codigo_Ubicacion VARCHAR(30) NOT NULL,
    Temperatura DECIMAL(5,1) NOT NULL, Humedad DECIMAL(5,1) NOT NULL,
    Es_Anomalia BIT NOT NULL
);
GO
CREATE TABLE dbo.stg_Conteos (
    Fecha DATE NOT NULL, Cod_Componente VARCHAR(20) NOT NULL,
    Codigo_Ubicacion VARCHAR(30) NOT NULL,
    Stock_Sistema DECIMAL(12,2) NOT NULL, Stock_Fisico DECIMAL(12,2) NOT NULL,
    Diferencia DECIMAL(12,2) NOT NULL, Responsable VARCHAR(20) NOT NULL,
    Resultado VARCHAR(20) NOT NULL, Exactitud_Linea DECIMAL(6,4) NOT NULL
);
GO
CREATE TABLE dbo.stg_Inventario_Actual (
    Cod_Componente VARCHAR(20) NOT NULL, Id_Ubicacion INT NOT NULL,
    Stock_Disponible DECIMAL(12,2) NOT NULL,
    Stock_Minimo DECIMAL(12,2) NOT NULL, Criticidad VARCHAR(20) NOT NULL
);
GO

SELECT name AS Tabla FROM sys.tables ORDER BY name;
GO
