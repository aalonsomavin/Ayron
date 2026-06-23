CREATE TABLE comercial_areas_terapeuticas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE comercial_productos (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    marca_comercial VARCHAR(100) NOT NULL,
    molecula VARCHAR(200) NOT NULL,
    presentacion VARCHAR(100),
    area_id INTEGER NOT NULL REFERENCES comercial_areas_terapeuticas(id),
    precio_lista NUMERIC(12, 2) NOT NULL
);

CREATE TABLE comercial_instituciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    estado VARCHAR(100) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL
);

CREATE TABLE comercial_pedidos (
    id SERIAL PRIMARY KEY,
    institucion_id INTEGER NOT NULL REFERENCES comercial_instituciones(id),
    fecha DATE NOT NULL,
    canal VARCHAR(50) NOT NULL,
    monto_total NUMERIC(14, 2) NOT NULL
);

CREATE TABLE comercial_pedido_lineas (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES comercial_pedidos(id),
    producto_id INTEGER NOT NULL REFERENCES comercial_productos(id),
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(12, 2) NOT NULL
);

CREATE TABLE comercial_inventario (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES comercial_productos(id),
    almacen VARCHAR(50) NOT NULL,
    stock INTEGER NOT NULL,
    lote VARCHAR(50),
    fecha_caducidad DATE
);

CREATE TABLE crm_ejecutivos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    oficina VARCHAR(50) NOT NULL
);

CREATE TABLE crm_cuentas (
    id SERIAL PRIMARY KEY,
    institucion_id INTEGER NOT NULL REFERENCES comercial_instituciones(id),
    ejecutivo_id INTEGER NOT NULL REFERENCES crm_ejecutivos(id),
    tier VARCHAR(20) NOT NULL,
    segmento VARCHAR(50) NOT NULL
);

CREATE TABLE crm_contactos (
    id SERIAL PRIMARY KEY,
    cuenta_id INTEGER NOT NULL REFERENCES crm_cuentas(id),
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(50) NOT NULL,
    email VARCHAR(100)
);

CREATE TABLE crm_oportunidades (
    id SERIAL PRIMARY KEY,
    cuenta_id INTEGER NOT NULL REFERENCES crm_cuentas(id),
    producto_id INTEGER REFERENCES comercial_productos(id),
    molecula VARCHAR(200),
    etapa VARCHAR(50) NOT NULL,
    valor_estimado NUMERIC(14, 2),
    fecha_inicio DATE,
    fecha_cierre_esperada DATE,
    fecha_cierre_real DATE
);

CREATE TABLE crm_actividades (
    id SERIAL PRIMARY KEY,
    cuenta_id INTEGER NOT NULL REFERENCES crm_cuentas(id),
    tipo VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL,
    notas TEXT
);

CREATE INDEX idx_pedidos_fecha ON comercial_pedidos(fecha);
CREATE INDEX idx_pedidos_institucion ON comercial_pedidos(institucion_id);
CREATE INDEX idx_pedido_lineas_producto ON comercial_pedido_lineas(producto_id);
CREATE INDEX idx_instituciones_region ON comercial_instituciones(region);
CREATE INDEX idx_oportunidades_cierre ON crm_oportunidades(fecha_cierre_esperada);
