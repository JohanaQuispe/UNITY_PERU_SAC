/*
====================================================================
 PROYECTO: Análisis del ciclo de vida y disponibilidad de
           componentes críticos mediante BI y Big Data
 EMPRESA:  EMPRESA COMERCIAL ANÓNIMA S.A.C. (nombre ficticio)
 BD:       ALMACEN_ANONIMO
 VERSIÓN:  3.0 (anonimizada para uso académico)

 NOTA ACADÉMICA:
 Los datos incluidos son SINTÉTICOS y sirven para desarrollar,
 probar y experimentar con la solución. No representan información
 real ni confidencial de la empresa en estudio. Los nombres de
 personas, proveedores, RUC, teléfonos, direcciones y correos
 electrónicos son ficticios (se usa el dominio reservado "example"
 según RFC 2606) y cualquier coincidencia con datos reales es
 casualidad.

 PROPÓSITO:
 - Registrar componentes críticos y su ciclo de vida.
 - Registrar movimientos: ingreso, salida, asignación, devolución,
   traslado, mantenimiento, reemplazo y baja/obsolescencia.
 - Analizar disponibilidad, rotación, permanencia y criticidad.
 - Servir como fuente para el modelo dimensional de BI.
 - Servir como fuente para generar datasets históricos de Big Data.
====================================================================
*/

USE master;
GO

IF DB_ID('ALMACEN_ANONIMO') IS NOT NULL
BEGIN
    ALTER DATABASE ALMACEN_ANONIMO SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ALMACEN_ANONIMO;
END
GO

CREATE DATABASE ALMACEN_ANONIMO;
GO

USE ALMACEN_ANONIMO;
GO

/* ================================================================
   1. CATÁLOGOS / TABLAS MAESTRAS
   ================================================================ */

CREATE TABLE categoria_componente (
    Id_Categoria       INT IDENTITY(1,1) PRIMARY KEY,
    Nombre_Categoria   VARCHAR(80) NOT NULL UNIQUE,
    Descripcion        VARCHAR(250) NULL,
    Activo              BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE marca (
    Id_Marca           INT IDENTITY(1,1) PRIMARY KEY,
    Nombre_Marca       VARCHAR(80) NOT NULL UNIQUE,
    Activo              BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE modelo_componente (
    Id_Modelo          INT IDENTITY(1,1) PRIMARY KEY,
    Id_Categoria       INT NOT NULL,
    Id_Marca            INT NOT NULL,
    Nombre_Modelo      VARCHAR(100) NOT NULL,
    Descripcion        VARCHAR(250) NULL,
    Vida_Util_Meses    INT NULL,
    Activo              BIT NOT NULL DEFAULT 1,

    CONSTRAINT UQ_modelo UNIQUE (Id_Marca, Nombre_Modelo),
    CONSTRAINT CK_modelo_vida CHECK (Vida_Util_Meses IS NULL OR Vida_Util_Meses > 0),

    CONSTRAINT FK_modelo_categoria
        FOREIGN KEY (Id_Categoria) REFERENCES categoria_componente(Id_Categoria),

    CONSTRAINT FK_modelo_marca
        FOREIGN KEY (Id_Marca) REFERENCES marca(Id_Marca)
);
GO

CREATE TABLE nivel_criticidad (
    Id_Criticidad      INT IDENTITY(1,1) PRIMARY KEY,
    Nivel_Criticidad   VARCHAR(20) NOT NULL UNIQUE,
    Puntaje             INT NOT NULL,
    Descripcion        VARCHAR(250) NULL,

    CONSTRAINT CK_criticidad_puntaje CHECK (Puntaje BETWEEN 1 AND 3)
);
GO

CREATE TABLE estado_componente (
    Id_Estado          INT IDENTITY(1,1) PRIMARY KEY,
    Nombre_Estado      VARCHAR(30) NOT NULL UNIQUE,
    Descripcion        VARCHAR(250) NULL,
    Disponible_Stock   BIT NOT NULL DEFAULT 0,
    Es_Estado_Final    BIT NOT NULL DEFAULT 0
);
GO

CREATE TABLE unidad_medida (
    Id_Unidad          INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Unidad      VARCHAR(10) NOT NULL UNIQUE,
    Nombre_Unidad      VARCHAR(50) NOT NULL UNIQUE
);
GO

CREATE TABLE ubicacion (
    Id_Ubicacion       INT IDENTITY(1,1) PRIMARY KEY,
    Codigo_Ubicacion   VARCHAR(30) NOT NULL UNIQUE,
    Nombre_Ubicacion   VARCHAR(100) NOT NULL,
    Tipo_Ubicacion     VARCHAR(40) NOT NULL,
    Capacidad_Maxima   DECIMAL(12,2) NULL,
    Activo              BIT NOT NULL DEFAULT 1,

    CONSTRAINT CK_ubicacion_capacidad
        CHECK (Capacidad_Maxima IS NULL OR Capacidad_Maxima >= 0)
);
GO

CREATE TABLE proveedor (
    Ruc_Proveedor      CHAR(11) PRIMARY KEY,
    Nom_Proveedor      VARCHAR(150) NOT NULL,
    Direccion          VARCHAR(150) NULL,
    Telefono           VARCHAR(20) NULL,
    Email              VARCHAR(100) NULL,
    Activo              BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE responsable (
    Id_Responsable     VARCHAR(20) PRIMARY KEY,
    Nom_Responsable    VARCHAR(150) NOT NULL,
    Cargo              VARCHAR(80) NULL,
    Email              VARCHAR(100) NULL,
    Activo              BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE proyecto_servicio (
    Id_Proyecto        VARCHAR(20) PRIMARY KEY,
    Nombre_Proyecto    VARCHAR(150) NOT NULL,
    Tipo_Proyecto      VARCHAR(60) NOT NULL,
    Estado              VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    Fecha_Inicio       DATE NULL,
    Fecha_Fin          DATE NULL,
    Activo              BIT NOT NULL DEFAULT 1,

    CONSTRAINT CK_proyecto_estado
        CHECK (Estado IN ('PLANIFICADO','ACTIVO','CERRADO','CANCELADO'))
);
GO

/* ================================================================
   2. CATÁLOGO PRINCIPAL DE COMPONENTES
   ================================================================ */

CREATE TABLE componente (
    Cod_Componente          VARCHAR(20) PRIMARY KEY,
    Descripcion             VARCHAR(180) NOT NULL,
    Id_Modelo               INT NOT NULL,
    Id_Unidad               INT NOT NULL,
    Id_Criticidad           INT NOT NULL,
    Stock_Minimo            DECIMAL(12,2) NOT NULL DEFAULT 0,
    Stock_Maximo            DECIMAL(12,2) NULL,
    Tiempo_Reposicion_Dias  INT NULL,
    Precio_Unitario         DECIMAL(12,2) NOT NULL DEFAULT 0,
    Fecha_Alta              DATE NOT NULL,
    Activo                  BIT NOT NULL DEFAULT 1,

    CONSTRAINT CK_componente_stock_min
        CHECK (Stock_Minimo >= 0),

    CONSTRAINT CK_componente_stock_max
        CHECK (Stock_Maximo IS NULL OR Stock_Maximo >= Stock_Minimo),

    CONSTRAINT CK_componente_reposicion
        CHECK (Tiempo_Reposicion_Dias IS NULL OR Tiempo_Reposicion_Dias >= 0),

    CONSTRAINT CK_componente_precio
        CHECK (Precio_Unitario >= 0),

    CONSTRAINT FK_componente_modelo
        FOREIGN KEY (Id_Modelo) REFERENCES modelo_componente(Id_Modelo),

    CONSTRAINT FK_componente_unidad
        FOREIGN KEY (Id_Unidad) REFERENCES unidad_medida(Id_Unidad),

    CONSTRAINT FK_componente_criticidad
        FOREIGN KEY (Id_Criticidad) REFERENCES nivel_criticidad(Id_Criticidad)
);
GO

/* ================================================================
   3. INVENTARIO / EXISTENCIA ACTUAL
   Una fila por componente y ubicación.
   La disponibilidad histórica NO depende de esta tabla:
   se reconstruye mediante movimientos.
   ================================================================ */

CREATE TABLE inventario (
    Cod_Componente      VARCHAR(20) NOT NULL,
    Id_Ubicacion        INT NOT NULL,
    Cantidad_Disponible DECIMAL(12,2) NOT NULL DEFAULT 0,
    Cantidad_Reservada  DECIMAL(12,2) NOT NULL DEFAULT 0,
    Fecha_Ultimo_Conteo DATETIME NULL,

    CONSTRAINT PK_inventario
        PRIMARY KEY (Cod_Componente, Id_Ubicacion),

    CONSTRAINT CK_inventario_disponible
        CHECK (Cantidad_Disponible >= 0),

    CONSTRAINT CK_inventario_reservada
        CHECK (Cantidad_Reservada >= 0),

    CONSTRAINT FK_inventario_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_inventario_ubicacion
        FOREIGN KEY (Id_Ubicacion) REFERENCES ubicacion(Id_Ubicacion)
);
GO

/* ================================================================
   4. DOCUMENTOS DE ENTRADA
   ================================================================ */

CREATE TABLE entrada (
    Id_Entrada          VARCHAR(20) PRIMARY KEY,
    Fecha_Recepcion     DATE NOT NULL,
    Hora_Ingreso        TIME NOT NULL,
    Tipo_Documento      VARCHAR(50) NULL,
    Numero_Documento    VARCHAR(40) NULL,
    Fecha_Documento     DATE NULL,
    Ruc_Proveedor       CHAR(11) NULL,
    Id_Responsable      VARCHAR(20) NULL,
    Estado               VARCHAR(30) NOT NULL DEFAULT 'PROCESADO',
    Fecha_Registro      DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_entrada_proveedor
        FOREIGN KEY (Ruc_Proveedor) REFERENCES proveedor(Ruc_Proveedor),

    CONSTRAINT FK_entrada_responsable
        FOREIGN KEY (Id_Responsable) REFERENCES responsable(Id_Responsable),

    CONSTRAINT CK_entrada_estado
        CHECK (Estado IN ('PENDIENTE','PROCESADO','OBSERVADO','ANULADO'))
);
GO

CREATE TABLE detalle_entrada (
    Id_Entrada              VARCHAR(20) NOT NULL,
    Cod_Componente          VARCHAR(20) NOT NULL,
    Cantidad_Documentada    DECIMAL(12,2) NOT NULL,
    Cantidad_Recibida       DECIMAL(12,2) NOT NULL,
    Cantidad_Danada         DECIMAL(12,2) NOT NULL DEFAULT 0,
    Id_Ubicacion_Destino    INT NULL,
    Observaciones           VARCHAR(300) NULL,

    CONSTRAINT PK_detalle_entrada
        PRIMARY KEY (Id_Entrada, Cod_Componente),

    CONSTRAINT CK_detalle_entrada_documentada
        CHECK (Cantidad_Documentada >= 0),

    CONSTRAINT CK_detalle_entrada_recibida
        CHECK (Cantidad_Recibida >= 0),

    CONSTRAINT CK_detalle_entrada_danada
        CHECK (Cantidad_Danada >= 0 AND Cantidad_Danada <= Cantidad_Recibida),

    CONSTRAINT FK_detalle_entrada
        FOREIGN KEY (Id_Entrada) REFERENCES entrada(Id_Entrada),

    CONSTRAINT FK_detalle_entrada_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_detalle_entrada_ubicacion
        FOREIGN KEY (Id_Ubicacion_Destino) REFERENCES ubicacion(Id_Ubicacion)
);
GO

/* ================================================================
   5. DOCUMENTOS DE SALIDA / ASIGNACIÓN
   ================================================================ */

CREATE TABLE salida (
    Id_Salida           VARCHAR(20) PRIMARY KEY,
    Fecha_Solicitud     DATE NOT NULL,
    Fecha_Despacho      DATE NULL,
    Motivo              VARCHAR(80) NOT NULL,
    Id_Proyecto         VARCHAR(20) NULL,
    Id_Responsable      VARCHAR(20) NULL,
    Estado               VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    Observaciones       VARCHAR(300) NULL,
    Fecha_Registro      DATETIME NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_salida_proyecto
        FOREIGN KEY (Id_Proyecto) REFERENCES proyecto_servicio(Id_Proyecto),

    CONSTRAINT FK_salida_responsable
        FOREIGN KEY (Id_Responsable) REFERENCES responsable(Id_Responsable),

    CONSTRAINT CK_salida_estado
        CHECK (Estado IN ('PENDIENTE','DESPACHADO','ENTREGADO','ANULADO'))
);
GO

CREATE TABLE detalle_salida (
    Id_Salida              VARCHAR(20) NOT NULL,
    Cod_Componente         VARCHAR(20) NOT NULL,
    Cantidad_Solicitada    DECIMAL(12,2) NOT NULL,
    Cantidad_Despachada    DECIMAL(12,2) NOT NULL DEFAULT 0,
    Id_Ubicacion_Origen    INT NULL,
    Observaciones          VARCHAR(300) NULL,

    CONSTRAINT PK_detalle_salida
        PRIMARY KEY (Id_Salida, Cod_Componente),

    CONSTRAINT CK_detalle_salida_solicitada
        CHECK (Cantidad_Solicitada >= 0),

    CONSTRAINT CK_detalle_salida_despachada
        CHECK (Cantidad_Despachada >= 0),

    CONSTRAINT FK_detalle_salida
        FOREIGN KEY (Id_Salida) REFERENCES salida(Id_Salida),

    CONSTRAINT FK_detalle_salida_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_detalle_salida_ubicacion
        FOREIGN KEY (Id_Ubicacion_Origen) REFERENCES ubicacion(Id_Ubicacion)
);
GO

/* ================================================================
   6. MOVIMIENTO DE CICLO DE VIDA
   Esta es la tabla central para trazabilidad e histórico.
   ================================================================ */

CREATE TABLE tipo_movimiento (
    Id_Tipo_Movimiento INT IDENTITY(1,1) PRIMARY KEY,
    Codigo             VARCHAR(30) NOT NULL UNIQUE,
    Nombre             VARCHAR(80) NOT NULL UNIQUE,
    Signo_Stock        SMALLINT NOT NULL,
    Descripcion        VARCHAR(250) NULL,

    CONSTRAINT CK_tipo_movimiento_signo
        CHECK (Signo_Stock IN (-1,0,1))
);
GO

CREATE TABLE movimiento_componente (
    Id_Movimiento          BIGINT IDENTITY(1,1) PRIMARY KEY,
    Fecha_Movimiento       DATETIME NOT NULL,
    Cod_Componente         VARCHAR(20) NOT NULL,
    Id_Tipo_Movimiento     INT NOT NULL,
    Cantidad               DECIMAL(12,2) NOT NULL,
    Id_Estado_Anterior     INT NULL,
    Id_Estado_Nuevo        INT NULL,
    Id_Ubicacion_Origen    INT NULL,
    Id_Ubicacion_Destino   INT NULL,
    Id_Responsable         VARCHAR(20) NULL,
    Id_Proyecto            VARCHAR(20) NULL,
    Id_Entrada              VARCHAR(20) NULL,
    Id_Salida               VARCHAR(20) NULL,
    Observaciones          VARCHAR(300) NULL,

    CONSTRAINT CK_movimiento_cantidad
        CHECK (Cantidad > 0),

    CONSTRAINT FK_movimiento_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_movimiento_tipo
        FOREIGN KEY (Id_Tipo_Movimiento) REFERENCES tipo_movimiento(Id_Tipo_Movimiento),

    CONSTRAINT FK_movimiento_estado_anterior
        FOREIGN KEY (Id_Estado_Anterior) REFERENCES estado_componente(Id_Estado),

    CONSTRAINT FK_movimiento_estado_nuevo
        FOREIGN KEY (Id_Estado_Nuevo) REFERENCES estado_componente(Id_Estado),

    CONSTRAINT FK_movimiento_ubicacion_origen
        FOREIGN KEY (Id_Ubicacion_Origen) REFERENCES ubicacion(Id_Ubicacion),

    CONSTRAINT FK_movimiento_ubicacion_destino
        FOREIGN KEY (Id_Ubicacion_Destino) REFERENCES ubicacion(Id_Ubicacion),

    CONSTRAINT FK_movimiento_responsable
        FOREIGN KEY (Id_Responsable) REFERENCES responsable(Id_Responsable),

    CONSTRAINT FK_movimiento_proyecto
        FOREIGN KEY (Id_Proyecto) REFERENCES proyecto_servicio(Id_Proyecto),

    CONSTRAINT FK_movimiento_entrada
        FOREIGN KEY (Id_Entrada) REFERENCES entrada(Id_Entrada),

    CONSTRAINT FK_movimiento_salida
        FOREIGN KEY (Id_Salida) REFERENCES salida(Id_Salida)
);
GO

/* ================================================================
   7. ASIGNACIÓN / DEVOLUCIÓN
   Permite analizar el ciclo de vida operativo.
   ================================================================ */

CREATE TABLE asignacion_componente (
    Id_Asignacion        BIGINT IDENTITY(1,1) PRIMARY KEY,
    Cod_Componente       VARCHAR(20) NOT NULL,
    Fecha_Asignacion     DATETIME NOT NULL,
    Fecha_Devolucion     DATETIME NULL,
    Cantidad_Asignada    DECIMAL(12,2) NOT NULL,
    Id_Proyecto          VARCHAR(20) NULL,
    Id_Responsable       VARCHAR(20) NULL,
    Motivo               VARCHAR(150) NULL,
    Estado               VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',

    CONSTRAINT CK_asignacion_cantidad
        CHECK (Cantidad_Asignada > 0),

    CONSTRAINT CK_asignacion_fechas
        CHECK (Fecha_Devolucion IS NULL OR Fecha_Devolucion >= Fecha_Asignacion),

    CONSTRAINT CK_asignacion_estado
        CHECK (Estado IN ('ACTIVA','DEVUELTA','CANCELADA')),

    CONSTRAINT FK_asignacion_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_asignacion_proyecto
        FOREIGN KEY (Id_Proyecto) REFERENCES proyecto_servicio(Id_Proyecto),

    CONSTRAINT FK_asignacion_responsable
        FOREIGN KEY (Id_Responsable) REFERENCES responsable(Id_Responsable)
);
GO

/* ================================================================
   8. MANTENIMIENTO / REEMPLAZO
   ================================================================ */

CREATE TABLE mantenimiento_componente (
    Id_Mantenimiento      BIGINT IDENTITY(1,1) PRIMARY KEY,
    Cod_Componente        VARCHAR(20) NOT NULL,
    Fecha_Inicio          DATETIME NOT NULL,
    Fecha_Fin             DATETIME NULL,
    Tipo_Mantenimiento    VARCHAR(60) NOT NULL,
    Motivo                VARCHAR(200) NULL,
    Resultado             VARCHAR(200) NULL,
    Estado                VARCHAR(30) NOT NULL DEFAULT 'EN PROCESO',

    CONSTRAINT CK_mantenimiento_fechas
        CHECK (Fecha_Fin IS NULL OR Fecha_Fin >= Fecha_Inicio),

    CONSTRAINT CK_mantenimiento_estado
        CHECK (Estado IN ('EN PROCESO','FINALIZADO','NO RECUPERABLE')),

    CONSTRAINT FK_mantenimiento_componente
        FOREIGN KEY (Cod_Componente) REFERENCES componente(Cod_Componente)
);
GO

CREATE TABLE reemplazo_componente (
    Id_Reemplazo          BIGINT IDENTITY(1,1) PRIMARY KEY,
    Cod_Componente_Origen VARCHAR(20) NOT NULL,
    Cod_Componente_Nuevo  VARCHAR(20) NOT NULL,
    Fecha_Reemplazo       DATETIME NOT NULL,
    Motivo                VARCHAR(200) NOT NULL,
    Id_Proyecto           VARCHAR(20) NULL,
    Observaciones         VARCHAR(300) NULL,

    CONSTRAINT FK_reemplazo_origen
        FOREIGN KEY (Cod_Componente_Origen) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_reemplazo_nuevo
        FOREIGN KEY (Cod_Componente_Nuevo) REFERENCES componente(Cod_Componente),

    CONSTRAINT FK_reemplazo_proyecto
        FOREIGN KEY (Id_Proyecto) REFERENCES proyecto_servicio(Id_Proyecto),

    CONSTRAINT CK_reemplazo_componentes
        CHECK (Cod_Componente_Origen <> Cod_Componente_Nuevo)
);
GO

/* ================================================================
   9. ÍNDICES OPERACIONALES
   ================================================================ */

CREATE INDEX IX_componente_modelo
    ON componente(Id_Modelo);

CREATE INDEX IX_componente_criticidad
    ON componente(Id_Criticidad);

CREATE INDEX IX_movimiento_fecha
    ON movimiento_componente(Fecha_Movimiento);

CREATE INDEX IX_movimiento_componente_fecha
    ON movimiento_componente(Cod_Componente, Fecha_Movimiento);

CREATE INDEX IX_movimiento_tipo_fecha
    ON movimiento_componente(Id_Tipo_Movimiento, Fecha_Movimiento);

CREATE INDEX IX_movimiento_proyecto
    ON movimiento_componente(Id_Proyecto);

CREATE INDEX IX_asignacion_componente_fecha
    ON asignacion_componente(Cod_Componente, Fecha_Asignacion);

CREATE INDEX IX_mantenimiento_componente_fecha
    ON mantenimiento_componente(Cod_Componente, Fecha_Inicio);
GO

/* ================================================================
   10. DATOS MAESTROS SINTÉTICOS (todos los valores son ficticios)
   ================================================================ */

INSERT INTO categoria_componente (Nombre_Categoria, Descripcion)
VALUES
('Almacenamiento','Componentes para almacenamiento de datos'),
('Memoria','Módulos de memoria para servidores'),
('Procesamiento','Componentes asociados al procesamiento'),
('Redes','Componentes de conectividad de red'),
('Energía','Componentes para suministro y distribución eléctrica'),
('Refrigeración','Componentes de ventilación y control térmico'),
('Infraestructura','Componentes físicos de infraestructura tecnológica');
GO

INSERT INTO marca (Nombre_Marca)
VALUES
('Dell'),
('HPE'),
('Cisco'),
('APC'),
('Intel'),
('Samsung'),
('Schneider Electric');
GO

INSERT INTO nivel_criticidad (Nivel_Criticidad, Puntaje, Descripcion)
VALUES
('BAJA',1,'El componente cuenta con sustitutos y su indisponibilidad tiene bajo impacto'),
('MEDIA',2,'La indisponibilidad puede afectar determinadas operaciones'),
('ALTA',3,'La indisponibilidad puede afectar operaciones críticas y requiere atención prioritaria');
GO

INSERT INTO estado_componente
    (Nombre_Estado, Descripcion, Disponible_Stock, Es_Estado_Final)
VALUES
('DISPONIBLE','Disponible para asignación o utilización',1,0),
('RESERVADO','Reservado para un proyecto o servicio',0,0),
('ASIGNADO','Asignado a un proyecto o servicio',0,0),
('EN_MANTENIMIENTO','En proceso de revisión o reparación',0,0),
('DEVUELTO','Devuelto al almacén pendiente de revisión',0,0),
('OBSOLETO','Fuera de uso por obsolescencia',0,1),
('BAJA','Retirado definitivamente del inventario',0,1),
('DANADO','No disponible por daño',0,0);
GO

INSERT INTO unidad_medida (Codigo_Unidad, Nombre_Unidad)
VALUES
('UND','Unidad'),
('KIT','Kit'),
('PAQ','Paquete');
GO

INSERT INTO ubicacion
    (Codigo_Ubicacion, Nombre_Ubicacion, Tipo_Ubicacion, Capacidad_Maxima)
VALUES
('ALM-CEN-A01','Almacén Central - Rack A01','ALMACEN',500),
('ALM-CEN-A02','Almacén Central - Rack A02','ALMACEN',500),
('ALM-CEN-B01','Almacén Central - Rack B01','ALMACEN',500),
('ALM-CEN-C01','Almacén Central - Rack C01','ALMACEN',500),
('MANT-01','Zona de mantenimiento','MANTENIMIENTO',100),
('TRANSITO','Zona de tránsito','TRANSITO',200);
GO

-- Proveedores ficticios (razón social, RUC, teléfono y correo sintéticos)
INSERT INTO proveedor
    (Ruc_Proveedor, Nom_Proveedor, Direccion, Telefono, Email)
VALUES
('20300000001','Proveedor Tecnológico Andino SAC','Lima','014567801','ventas@pta.example'),
('20300000002','Suministros Data Center SAC','Callao','014567802','ventas@sdc.example'),
('20300000003','Distribuidora InfraTech SAC','Lima','014567803','ventas@infratech.example'),
('20300000004','Soluciones Energéticas Perú SAC','Lima','014567804','ventas@sep.example');
GO

-- Responsables ficticios (nombres y correos sintéticos)
INSERT INTO responsable
    (Id_Responsable, Nom_Responsable, Cargo, Email)
VALUES
('RESP001','Rosa Mendoza','Jefe de Almacén','r.mendoza@example'),
('RESP002','Luis Paredes','Supervisor de Logística','l.paredes@example'),
('RESP003','Elena Quispe','Almacenera','e.quispe@example'),
('RESP004','Marco Salazar','Coordinador de Operaciones','m.salazar@example');
GO

INSERT INTO proyecto_servicio
    (Id_Proyecto, Nombre_Proyecto, Tipo_Proyecto, Estado, Fecha_Inicio, Fecha_Fin)
VALUES
('PRY001','Mantenimiento preventivo Data Center Norte','MANTENIMIENTO','ACTIVO','2026-01-05',NULL),
('PRY002','Implementación de infraestructura de red','IMPLEMENTACION','CERRADO','2026-01-10','2026-03-20'),
('PRY003','Renovación de servidores críticos','RENOVACION','ACTIVO','2026-02-01',NULL),
('PRY004','Mantenimiento de infraestructura eléctrica','MANTENIMIENTO','ACTIVO','2026-02-15',NULL),
('PRY005','Actualización de almacenamiento','ACTUALIZACION','PLANIFICADO','2026-04-01',NULL);
GO

INSERT INTO modelo_componente
    (Id_Categoria, Id_Marca, Nombre_Modelo, Descripcion, Vida_Util_Meses)
VALUES
(1,6,'PM893','SSD empresarial para servidores',60),
(2,2,'DDR4-ECC-32','Memoria ECC de 32 GB',72),
(4,3,'SFP-10G-SR','Transceptor óptico 10Gb',60),
(4,3,'C9200-NIC','Tarjeta/interfaz de red empresarial',72),
(5,4,'APC-PDU-32','PDU para infraestructura crítica',84),
(5,7,'PDU-3PH-32','PDU trifásica para Data Center',96),
(6,1,'FAN-R740','Ventilador para servidor',48),
(3,5,'XEON-GOLD','Procesador para servidor',84),
(1,1,'HDD-ENT-4TB','Disco empresarial de 4 TB',60),
(5,4,'APC-UPS-10K','UPS para infraestructura crítica',96);
GO

INSERT INTO componente
    (Cod_Componente, Descripcion, Id_Modelo, Id_Unidad, Id_Criticidad,
     Stock_Minimo, Stock_Maximo, Tiempo_Reposicion_Dias,
     Precio_Unitario, Fecha_Alta)
VALUES
('CMP001','SSD empresarial 1.92 TB',1,1,3,8,40,15,1850.00,'2025-01-10'),
('CMP002','Memoria ECC 32 GB',2,1,3,10,50,20,950.00,'2025-01-15'),
('CMP003','Transceptor óptico 10Gb SFP+',3,1,3,12,60,25,720.00,'2025-02-01'),
('CMP004','Interfaz de red empresarial',4,1,2,6,30,30,1450.00,'2025-02-05'),
('CMP005','PDU empresarial 32A',5,1,3,3,15,35,4200.00,'2025-02-20'),
('CMP006','PDU trifásica 32A',6,1,3,2,10,45,6800.00,'2025-03-01'),
('CMP007','Ventilador para servidor',7,1,2,8,40,18,380.00,'2025-03-10'),
('CMP008','Procesador para servidor',8,1,3,4,20,40,5600.00,'2025-03-15'),
('CMP009','Disco empresarial 4 TB',9,1,2,6,30,20,1250.00,'2025-04-01'),
('CMP010','UPS 10KVA',10,1,3,1,5,60,18500.00,'2025-04-15');
GO

INSERT INTO tipo_movimiento
    (Codigo, Nombre, Signo_Stock, Descripcion)
VALUES
('INGRESO','Ingreso al almacén',1,'Ingreso por compra, devolución o recepción'),
('SALIDA','Salida del almacén',-1,'Salida para proyecto, servicio o despacho'),
('ASIGNACION','Asignación a proyecto o servicio',-1,'Reserva o entrega de componente para uso'),
('DEVOLUCION','Devolución al almacén',1,'Retorno de componente previamente asignado'),
('TRASLADO_SALIDA','Traslado de salida',-1,'Salida de una ubicación'),
('TRASLADO_ENTRADA','Traslado de entrada',1,'Ingreso a una nueva ubicación'),
('MANTENIMIENTO_SALIDA','Ingreso a mantenimiento',-1,'Retiro temporal de disponibilidad'),
('MANTENIMIENTO_ENTRADA','Retorno de mantenimiento',1,'Retorno del componente al stock'),
('REEMPLAZO','Reemplazo de componente',0,'Evento de reemplazo sin movimiento directo de stock'),
('BAJA','Baja definitiva',-1,'Retiro definitivo'),
('OBSOLESCENCIA','Retiro por obsolescencia',-1,'Retiro por fin de vida o incompatibilidad');
GO

/* ================================================================
   11. EXISTENCIA INICIAL
   ================================================================ */

INSERT INTO inventario
    (Cod_Componente, Id_Ubicacion, Cantidad_Disponible, Cantidad_Reservada, Fecha_Ultimo_Conteo)
VALUES
('CMP001',1,18,2,'2026-04-30 08:00:00'),
('CMP002',1,22,3,'2026-04-30 08:00:00'),
('CMP003',2,14,4,'2026-04-30 08:00:00'),
('CMP004',2,8,1,'2026-04-30 08:00:00'),
('CMP005',3,4,1,'2026-04-30 08:00:00'),
('CMP006',3,2,0,'2026-04-30 08:00:00'),
('CMP007',4,16,2,'2026-04-30 08:00:00'),
('CMP008',4,5,1,'2026-04-30 08:00:00'),
('CMP009',1,11,2,'2026-04-30 08:00:00'),
('CMP010',3,1,0,'2026-04-30 08:00:00');
GO

/* ================================================================
   12. ENTRADAS SINTÉTICAS
   ================================================================ */

INSERT INTO entrada
    (Id_Entrada, Fecha_Recepcion, Hora_Ingreso, Tipo_Documento,
     Numero_Documento, Fecha_Documento, Ruc_Proveedor,
     Id_Responsable, Estado)
VALUES
('ENT001','2026-01-05','08:30','ORDEN_COMPRA','OC-001','2026-01-03','20300000001','RESP001','PROCESADO'),
('ENT002','2026-01-20','09:10','ORDEN_COMPRA','OC-002','2026-01-18','20300000002','RESP002','PROCESADO'),
('ENT003','2026-02-10','10:00','ORDEN_COMPRA','OC-003','2026-02-08','20300000003','RESP003','PROCESADO'),
('ENT004','2026-03-05','08:45','ORDEN_COMPRA','OC-004','2026-03-02','20300000004','RESP001','PROCESADO'),
('ENT005','2026-04-12','09:30','ORDEN_COMPRA','OC-005','2026-04-10','20300000001','RESP002','PROCESADO'),
('ENT006','2026-05-03','11:00','ORDEN_COMPRA','OC-006','2026-04-30','20300000002','RESP003','PROCESADO');
GO

INSERT INTO detalle_entrada
    (Id_Entrada, Cod_Componente, Cantidad_Documentada, Cantidad_Recibida,
     Cantidad_Danada, Id_Ubicacion_Destino, Observaciones)
VALUES
('ENT001','CMP001',20,20,0,1,'Recepción conforme'),
('ENT001','CMP002',25,24,1,1,'Una unidad dañada'),
('ENT002','CMP003',30,30,0,2,'Recepción conforme'),
('ENT002','CMP004',12,12,0,2,'Recepción conforme'),
('ENT003','CMP005',5,5,0,3,'Recepción conforme'),
('ENT003','CMP006',3,3,0,3,'Recepción conforme'),
('ENT004','CMP007',20,20,0,4,'Recepción conforme'),
('ENT004','CMP008',8,8,0,4,'Recepción conforme'),
('ENT005','CMP009',15,14,1,1,'Una unidad dañada'),
('ENT005','CMP010',2,2,0,3,'Recepción conforme'),
('ENT006','CMP001',10,10,0,1,'Recepción conforme'),
('ENT006','CMP003',20,20,0,2,'Recepción conforme');
GO

/* ================================================================
   13. SALIDAS SINTÉTICAS
   ================================================================ */

INSERT INTO salida
    (Id_Salida, Fecha_Solicitud, Fecha_Despacho, Motivo,
     Id_Proyecto, Id_Responsable, Estado, Observaciones)
VALUES
('SAL001','2026-01-12','2026-01-13','MANTENIMIENTO','PRY001','RESP002','ENTREGADO','Atención programada'),
('SAL002','2026-01-25','2026-01-26','IMPLEMENTACION','PRY002','RESP001','ENTREGADO','Implementación de red'),
('SAL003','2026-02-18','2026-02-19','MANTENIMIENTO','PRY004','RESP003','ENTREGADO','Mantenimiento eléctrico'),
('SAL004','2026-03-15','2026-03-16','RENOVACION','PRY003','RESP002','ENTREGADO','Renovación de servidores'),
('SAL005','2026-04-08','2026-04-09','MANTENIMIENTO','PRY001','RESP001','ENTREGADO','Reemplazo preventivo'),
('SAL006','2026-05-10','2026-05-11','ACTUALIZACION','PRY003','RESP003','ENTREGADO','Actualización de almacenamiento');
GO

INSERT INTO detalle_salida
    (Id_Salida, Cod_Componente, Cantidad_Solicitada, Cantidad_Despachada,
     Id_Ubicacion_Origen, Observaciones)
VALUES
('SAL001','CMP001',5,5,1,'Atención completa'),
('SAL001','CMP007',4,4,4,'Atención completa'),
('SAL002','CMP003',10,10,2,'Atención completa'),
('SAL002','CMP004',4,4,2,'Atención completa'),
('SAL003','CMP005',2,2,3,'Atención completa'),
('SAL003','CMP006',1,1,3,'Atención completa'),
('SAL004','CMP002',8,8,1,'Atención completa'),
('SAL004','CMP008',3,3,4,'Atención completa'),
('SAL005','CMP001',3,3,1,'Atención completa'),
('SAL005','CMP009',4,4,1,'Atención completa'),
('SAL006','CMP001',7,7,1,'Atención completa'),
('SAL006','CMP003',8,8,2,'Atención completa');
GO

/* ================================================================
   14. ASIGNACIONES Y DEVOLUCIONES
   ================================================================ */

INSERT INTO asignacion_componente
    (Cod_Componente, Fecha_Asignacion, Fecha_Devolucion, Cantidad_Asignada,
     Id_Proyecto, Id_Responsable, Motivo, Estado)
VALUES
('CMP001','2026-01-13','2026-01-20',2,'PRY001','RESP002','Prueba y mantenimiento','DEVUELTA'),
('CMP007','2026-01-13','2026-01-20',2,'PRY001','RESP002','Prueba y mantenimiento','DEVUELTA'),
('CMP003','2026-01-26',NULL,4,'PRY002','RESP001','Implementación de red','ACTIVA'),
('CMP004','2026-01-26',NULL,2,'PRY002','RESP001','Implementación de red','ACTIVA'),
('CMP005','2026-02-19',NULL,1,'PRY004','RESP003','Mantenimiento eléctrico','ACTIVA'),
('CMP002','2026-03-16','2026-03-30',2,'PRY003','RESP002','Pruebas de servidor','DEVUELTA');
GO

/* ================================================================
   15. MANTENIMIENTOS
   ================================================================ */

INSERT INTO mantenimiento_componente
    (Cod_Componente, Fecha_Inicio, Fecha_Fin, Tipo_Mantenimiento,
     Motivo, Resultado, Estado)
VALUES
('CMP001','2026-01-13','2026-01-20','PREVENTIVO','Prueba de integridad','Operativo','FINALIZADO'),
('CMP007','2026-01-13','2026-01-20','PREVENTIVO','Limpieza y revisión','Operativo','FINALIZADO'),
('CMP005','2026-02-19',NULL,'PREVENTIVO','Revisión eléctrica','Pendiente de cierre','EN PROCESO'),
('CMP009','2026-04-09','2026-04-14','CORRECTIVO','Componente con comportamiento irregular','Operativo','FINALIZADO');
GO

/* ================================================================
   16. REEMPLAZOS
   ================================================================ */

INSERT INTO reemplazo_componente
    (Cod_Componente_Origen, Cod_Componente_Nuevo, Fecha_Reemplazo,
     Motivo, Id_Proyecto, Observaciones)
VALUES
('CMP009','CMP001','2026-04-09','Actualización de almacenamiento','PRY001',
 'Reemplazo de unidad con menor capacidad'),
('CMP007','CMP008','2026-03-20','Mantenimiento preventivo','PRY001',
 'Registro de referencia operativa');
GO

/* ================================================================
   17. MOVIMIENTOS HISTÓRICOS
   ================================================================ */

-- INGRESOS
INSERT INTO movimiento_componente
    (Fecha_Movimiento, Cod_Componente, Id_Tipo_Movimiento, Cantidad,
     Id_Estado_Anterior, Id_Estado_Nuevo, Id_Ubicacion_Destino,
     Id_Responsable, Id_Entrada, Observaciones)
VALUES
('2026-01-05 08:30','CMP001',1,20,NULL,1,1,'RESP001','ENT001','Ingreso inicial'),
('2026-01-05 08:30','CMP002',1,24,NULL,1,1,'RESP001','ENT001','Ingreso inicial'),
('2026-01-20 09:10','CMP003',1,30,NULL,1,2,'RESP002','ENT002','Ingreso inicial'),
('2026-01-20 09:10','CMP004',1,12,NULL,1,2,'RESP002','ENT002','Ingreso inicial'),
('2026-02-10 10:00','CMP005',1,5,NULL,1,3,'RESP003','ENT003','Ingreso inicial'),
('2026-02-10 10:00','CMP006',1,3,NULL,1,3,'RESP003','ENT003','Ingreso inicial'),
('2026-03-05 08:45','CMP007',1,20,NULL,1,4,'RESP001','ENT004','Ingreso inicial'),
('2026-03-05 08:45','CMP008',1,8,NULL,1,4,'RESP001','ENT004','Ingreso inicial'),
('2026-04-12 09:30','CMP009',1,14,NULL,1,1,'RESP002','ENT005','Ingreso inicial'),
('2026-04-12 09:30','CMP010',1,2,NULL,1,3,'RESP002','ENT005','Ingreso inicial'),
('2026-05-03 11:00','CMP001',1,10,NULL,1,1,'RESP003','ENT006','Reposición'),
('2026-05-03 11:00','CMP003',1,20,NULL,1,2,'RESP003','ENT006','Reposición');
GO

-- SALIDAS
INSERT INTO movimiento_componente
    (Fecha_Movimiento, Cod_Componente, Id_Tipo_Movimiento, Cantidad,
     Id_Estado_Anterior, Id_Estado_Nuevo, Id_Ubicacion_Origen,
     Id_Responsable, Id_Proyecto, Id_Salida, Observaciones)
VALUES
('2026-01-13 09:00','CMP001',2,5,1,3,1,'RESP002','PRY001','SAL001','Salida a mantenimiento'),
('2026-01-13 09:00','CMP007',2,4,1,3,4,'RESP002','PRY001','SAL001','Salida a mantenimiento'),
('2026-01-26 09:00','CMP003',2,10,1,3,2,'RESP001','PRY002','SAL002','Implementación de red'),
('2026-01-26 09:00','CMP004',2,4,1,3,2,'RESP001','PRY002','SAL002','Implementación de red'),
('2026-02-19 09:00','CMP005',2,2,1,3,3,'RESP003','PRY004','SAL003','Mantenimiento eléctrico'),
('2026-02-19 09:00','CMP006',2,1,1,3,3,'RESP003','PRY004','SAL003','Mantenimiento eléctrico'),
('2026-03-16 09:00','CMP002',2,8,1,3,1,'RESP002','PRY003','SAL004','Renovación de servidores'),
('2026-03-16 09:00','CMP008',2,3,1,3,4,'RESP002','PRY003','SAL004','Renovación de servidores'),
('2026-04-09 09:00','CMP001',2,3,1,3,1,'RESP001','PRY001','SAL005','Reemplazo preventivo'),
('2026-04-09 09:00','CMP009',2,4,1,3,1,'RESP001','PRY001','SAL005','Reemplazo preventivo'),
('2026-05-11 09:00','CMP001',2,7,1,3,1,'RESP003','PRY003','SAL006','Actualización'),
('2026-05-11 09:00','CMP003',2,8,1,3,2,'RESP003','PRY003','SAL006','Actualización');
GO

-- DEVOLUCIONES / RETORNOS
INSERT INTO movimiento_componente
    (Fecha_Movimiento, Cod_Componente, Id_Tipo_Movimiento, Cantidad,
     Id_Estado_Anterior, Id_Estado_Nuevo, Id_Ubicacion_Destino,
     Id_Responsable, Id_Proyecto, Observaciones)
VALUES
('2026-01-20 16:00','CMP001',4,2,3,1,1,'RESP002','PRY001','Devolución posterior a prueba'),
('2026-01-20 16:00','CMP007',4,2,3,1,4,'RESP002','PRY001','Devolución posterior a prueba'),
('2026-03-30 16:00','CMP002',4,2,3,1,1,'RESP002','PRY003','Devolución posterior a pruebas');
GO

-- MANTENIMIENTO
INSERT INTO movimiento_componente
    (Fecha_Movimiento, Cod_Componente, Id_Tipo_Movimiento, Cantidad,
     Id_Estado_Anterior, Id_Estado_Nuevo, Id_Ubicacion_Origen,
     Id_Ubicacion_Destino, Id_Responsable, Observaciones)
VALUES
('2026-01-13 10:00','CMP001',7,2,1,4,1,5,'RESP002','Ingreso a mantenimiento'),
('2026-01-13 10:00','CMP007',7,2,1,4,4,5,'RESP002','Ingreso a mantenimiento'),
('2026-01-20 15:00','CMP001',8,2,4,1,5,1,'RESP002','Retorno de mantenimiento'),
('2026-01-20 15:00','CMP007',8,2,4,1,5,4,'RESP002','Retorno de mantenimiento'),
('2026-02-19 10:00','CMP005',7,1,1,4,3,5,'RESP003','Ingreso a mantenimiento'),
('2026-04-09 10:00','CMP009',7,1,1,4,1,5,'RESP001','Revisión correctiva'),
('2026-04-14 15:00','CMP009',8,1,4,1,5,1,'RESP001','Retorno de mantenimiento');
GO

/* ================================================================
   18. VISTAS ANALÍTICAS
   ================================================================ */

CREATE VIEW vw_catalogo_componentes AS
SELECT
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria AS Categoria,
    m.Nombre_Marca AS Marca,
    mc.Nombre_Modelo AS Modelo,
    nc.Nivel_Criticidad AS Criticidad,
    nc.Puntaje AS Puntaje_Criticidad,
    u.Nombre_Unidad AS Unidad_Medida,
    c.Stock_Minimo,
    c.Stock_Maximo,
    c.Tiempo_Reposicion_Dias,
    c.Precio_Unitario,
    c.Fecha_Alta,
    c.Activo
FROM componente c
INNER JOIN modelo_componente mc ON c.Id_Modelo = mc.Id_Modelo
INNER JOIN categoria_componente cat ON mc.Id_Categoria = cat.Id_Categoria
INNER JOIN marca m ON mc.Id_Marca = m.Id_Marca
INNER JOIN nivel_criticidad nc ON c.Id_Criticidad = nc.Id_Criticidad
INNER JOIN unidad_medida u ON c.Id_Unidad = u.Id_Unidad;
GO

CREATE VIEW vw_movimientos_componente AS
SELECT
    mov.Id_Movimiento,
    mov.Fecha_Movimiento,
    mov.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria AS Categoria,
    nc.Nivel_Criticidad AS Criticidad,
    tm.Codigo AS Tipo_Movimiento,
    tm.Nombre AS Movimiento,
    tm.Signo_Stock,
    mov.Cantidad,
    ea.Nombre_Estado AS Estado_Anterior,
    en.Nombre_Estado AS Estado_Nuevo,
    uo.Nombre_Ubicacion AS Ubicacion_Origen,
    ud.Nombre_Ubicacion AS Ubicacion_Destino,
    r.Nom_Responsable AS Responsable,
    p.Nombre_Proyecto AS Proyecto,
    mov.Observaciones
FROM movimiento_componente mov
INNER JOIN componente c ON mov.Cod_Componente = c.Cod_Componente
INNER JOIN modelo_componente mc ON c.Id_Modelo = mc.Id_Modelo
INNER JOIN categoria_componente cat ON mc.Id_Categoria = cat.Id_Categoria
INNER JOIN nivel_criticidad nc ON c.Id_Criticidad = nc.Id_Criticidad
INNER JOIN tipo_movimiento tm ON mov.Id_Tipo_Movimiento = tm.Id_Tipo_Movimiento
LEFT JOIN estado_componente ea ON mov.Id_Estado_Anterior = ea.Id_Estado
LEFT JOIN estado_componente en ON mov.Id_Estado_Nuevo = en.Id_Estado
LEFT JOIN ubicacion uo ON mov.Id_Ubicacion_Origen = uo.Id_Ubicacion
LEFT JOIN ubicacion ud ON mov.Id_Ubicacion_Destino = ud.Id_Ubicacion
LEFT JOIN responsable r ON mov.Id_Responsable = r.Id_Responsable
LEFT JOIN proyecto_servicio p ON mov.Id_Proyecto = p.Id_Proyecto;
GO

CREATE VIEW vw_disponibilidad_componentes AS
SELECT
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria AS Categoria,
    nc.Nivel_Criticidad AS Criticidad,
    c.Stock_Minimo,
    ISNULL(SUM(i.Cantidad_Disponible),0) AS Stock_Disponible,
    ISNULL(SUM(i.Cantidad_Reservada),0) AS Stock_Reservado,
    ISNULL(SUM(i.Cantidad_Disponible),0)
        - c.Stock_Minimo AS Diferencia_Stock_Minimo,
    CASE
        WHEN ISNULL(SUM(i.Cantidad_Disponible),0) < c.Stock_Minimo
            THEN 'BAJO_MINIMO'
        WHEN ISNULL(SUM(i.Cantidad_Disponible),0) = c.Stock_Minimo
            THEN 'EN_MINIMO'
        ELSE 'DISPONIBLE'
    END AS Situacion_Disponibilidad
FROM componente c
INNER JOIN modelo_componente mc ON c.Id_Modelo = mc.Id_Modelo
INNER JOIN categoria_componente cat ON mc.Id_Categoria = cat.Id_Categoria
INNER JOIN nivel_criticidad nc ON c.Id_Criticidad = nc.Id_Criticidad
LEFT JOIN inventario i ON c.Cod_Componente = i.Cod_Componente
GROUP BY
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria,
    nc.Nivel_Criticidad,
    c.Stock_Minimo;
GO

CREATE VIEW vw_rotacion_componentes AS
SELECT
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria AS Categoria,
    nc.Nivel_Criticidad AS Criticidad,
    SUM(CASE WHEN tm.Signo_Stock = -1 THEN mov.Cantidad ELSE 0 END) AS Cantidad_Salida,
    SUM(CASE WHEN tm.Signo_Stock = 1 THEN mov.Cantidad ELSE 0 END) AS Cantidad_Entrada,
    COUNT(*) AS Cantidad_Eventos,
    MIN(mov.Fecha_Movimiento) AS Primer_Movimiento,
    MAX(mov.Fecha_Movimiento) AS Ultimo_Movimiento
FROM movimiento_componente mov
INNER JOIN componente c ON mov.Cod_Componente = c.Cod_Componente
INNER JOIN modelo_componente mc ON c.Id_Modelo = mc.Id_Modelo
INNER JOIN categoria_componente cat ON mc.Id_Categoria = cat.Id_Categoria
INNER JOIN nivel_criticidad nc ON c.Id_Criticidad = nc.Id_Criticidad
INNER JOIN tipo_movimiento tm ON mov.Id_Tipo_Movimiento = tm.Id_Tipo_Movimiento
GROUP BY
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria,
    nc.Nivel_Criticidad;
GO

CREATE VIEW vw_permanencia_componentes AS
SELECT
    c.Cod_Componente,
    c.Descripcion,
    cat.Nombre_Categoria AS Categoria,
    nc.Nivel_Criticidad AS Criticidad,
    DATEDIFF(DAY, c.Fecha_Alta, CAST(GETDATE() AS DATE)) AS Dias_Desde_Alta,
    c.Tiempo_Reposicion_Dias
FROM componente c
INNER JOIN modelo_componente mc ON c.Id_Modelo = mc.Id_Modelo
INNER JOIN categoria_componente cat ON mc.Id_Categoria = cat.Id_Categoria
INNER JOIN nivel_criticidad nc ON c.Id_Criticidad = nc.Id_Criticidad;
GO

/* ================================================================
   19. CONSULTAS DE VALIDACIÓN PARA EL PROYECTO
   ================================================================ */

-- 1. Catálogo de componentes
SELECT * FROM vw_catalogo_componentes
ORDER BY Criticidad DESC, Categoria, Cod_Componente;
GO

-- 2. Disponibilidad actual
SELECT * FROM vw_disponibilidad_componentes
ORDER BY Criticidad DESC, Situacion_Disponibilidad;
GO

-- 3. Componentes por debajo del stock mínimo
SELECT *
FROM vw_disponibilidad_componentes
WHERE Situacion_Disponibilidad = 'BAJO_MINIMO'
ORDER BY Criticidad DESC;
GO

-- 4. Movimientos históricos
SELECT *
FROM vw_movimientos_componente
ORDER BY Fecha_Movimiento, Id_Movimiento;
GO

-- 5. Rotación y actividad
SELECT *
FROM vw_rotacion_componentes
ORDER BY Cantidad_Salida DESC;
GO

-- 6. Componentes críticos de alta prioridad
SELECT *
FROM vw_disponibilidad_componentes
WHERE Criticidad = 'ALTA'
ORDER BY Situacion_Disponibilidad, Cod_Componente;
GO

/* ================================================================
   FIN DEL SCRIPT (versión anonimizada para uso académico)
==================================================================== */
