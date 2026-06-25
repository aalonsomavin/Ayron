CREATE TABLE agricola_establecimientos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    provincia VARCHAR(100) NOT NULL,
    superficie_total_ha NUMERIC(10, 2) NOT NULL
);

CREATE TABLE ganaderia_establecimientos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    provincia VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    cabezas_nominales INTEGER NOT NULL
);

CREATE TABLE yivtol_vuelos (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    aeronave VARCHAR(100) NOT NULL DEFAULT 'YIVTOL S-ZERO',
    dominio VARCHAR(20) NOT NULL,
    hectareas_cubiertas NUMERIC(10, 2),
    duracion_min INTEGER NOT NULL,
    piloto VARCHAR(100) NOT NULL,
    hash_certificado VARCHAR(64) NOT NULL,
    agricola_establecimiento_id INTEGER REFERENCES agricola_establecimientos(id),
    ganaderia_establecimiento_id INTEGER REFERENCES ganaderia_establecimientos(id)
);

CREATE TABLE agricola_lotes (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES agricola_establecimientos(id),
    codigo VARCHAR(50) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    cultivo VARCHAR(50) NOT NULL,
    superficie_ha NUMERIC(10, 2) NOT NULL,
    UNIQUE (establecimiento_id, codigo)
);

CREATE TABLE agricola_mediciones (
    id SERIAL PRIMARY KEY,
    vuelo_id INTEGER NOT NULL REFERENCES yivtol_vuelos(id),
    lote_id INTEGER NOT NULL REFERENCES agricola_lotes(id),
    ndvi_promedio NUMERIC(5, 3) NOT NULL,
    ndre_promedio NUMERIC(5, 3) NOT NULL,
    pct_estres_hidrico NUMERIC(5, 2) NOT NULL,
    temp_foliar_promedio_c NUMERIC(5, 2) NOT NULL,
    temp_foliar_delta_c NUMERIC(5, 2) NOT NULL,
    biomasa_t_ha NUMERIC(8, 2) NOT NULL,
    rinde_proyectado_kg_ha NUMERIC(8, 2) NOT NULL,
    pct_zona_alta NUMERIC(5, 2) NOT NULL,
    pct_zona_media NUMERIC(5, 2) NOT NULL,
    pct_zona_baja NUMERIC(5, 2) NOT NULL
);

CREATE TABLE agricola_zonas (
    id SERIAL PRIMARY KEY,
    medicion_id INTEGER NOT NULL REFERENCES agricola_mediciones(id),
    zona VARCHAR(50) NOT NULL,
    clasificacion VARCHAR(20) NOT NULL,
    superficie_ha NUMERIC(10, 2) NOT NULL,
    ndvi NUMERIC(5, 3),
    accion_recomendada TEXT
);

CREATE TABLE agricola_alertas (
    id SERIAL PRIMARY KEY,
    vuelo_id INTEGER NOT NULL REFERENCES yivtol_vuelos(id),
    lote_id INTEGER NOT NULL REFERENCES agricola_lotes(id),
    tipo VARCHAR(50) NOT NULL,
    severidad VARCHAR(20) NOT NULL,
    mensaje TEXT NOT NULL,
    ha_afectadas NUMERIC(10, 2),
    fecha_deteccion DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa'
);

CREATE TABLE ganaderia_corrales (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES ganaderia_establecimientos(id),
    codigo VARCHAR(50) NOT NULL,
    capacidad INTEGER NOT NULL,
    cabezas_actuales INTEGER NOT NULL,
    UNIQUE (establecimiento_id, codigo)
);

CREATE TABLE ganaderia_animales (
    id SERIAL PRIMARY KEY,
    corral_id INTEGER NOT NULL REFERENCES ganaderia_corrales(id),
    vuelo_id INTEGER NOT NULL REFERENCES yivtol_vuelos(id),
    codigo_animal VARCHAR(50) NOT NULL,
    peso_kg NUMERIC(8, 2) NOT NULL,
    bcs NUMERIC(3, 1) NOT NULL,
    temperatura_c NUMERIC(4, 2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'normal',
    lat NUMERIC(10, 6),
    lon NUMERIC(10, 6)
);

CREATE TABLE ganaderia_mediciones_corral (
    id SERIAL PRIMARY KEY,
    vuelo_id INTEGER NOT NULL REFERENCES yivtol_vuelos(id),
    corral_id INTEGER NOT NULL REFERENCES ganaderia_corrales(id),
    total_cabezas INTEGER NOT NULL,
    peso_promedio_kg NUMERIC(8, 2) NOT NULL,
    bcs_promedio NUMERIC(3, 1) NOT NULL,
    varianza_peso NUMERIC(10, 2),
    temperatura_promedio_c NUMERIC(4, 2) NOT NULL
);

CREATE TABLE ganaderia_potreros (
    id SERIAL PRIMARY KEY,
    establecimiento_id INTEGER NOT NULL REFERENCES ganaderia_establecimientos(id),
    vuelo_id INTEGER REFERENCES yivtol_vuelos(id),
    codigo VARCHAR(50) NOT NULL,
    superficie_ha NUMERIC(10, 2) NOT NULL,
    biomasa_pct NUMERIC(5, 2) NOT NULL,
    dias_rotacion_sugeridos INTEGER,
    UNIQUE (establecimiento_id, codigo)
);

CREATE TABLE ganaderia_alertas (
    id SERIAL PRIMARY KEY,
    vuelo_id INTEGER NOT NULL REFERENCES yivtol_vuelos(id),
    corral_id INTEGER REFERENCES ganaderia_corrales(id),
    potrero_id INTEGER REFERENCES ganaderia_potreros(id),
    tipo VARCHAR(50) NOT NULL,
    severidad VARCHAR(20) NOT NULL,
    mensaje TEXT NOT NULL,
    animales_afectados INTEGER,
    estado VARCHAR(20) NOT NULL DEFAULT 'activa'
);

CREATE INDEX idx_yivtol_vuelos_fecha ON yivtol_vuelos(fecha);
CREATE INDEX idx_agricola_mediciones_vuelo ON agricola_mediciones(vuelo_id);
CREATE INDEX idx_agricola_mediciones_lote ON agricola_mediciones(lote_id);
CREATE INDEX idx_agricola_alertas_estado ON agricola_alertas(estado);
CREATE INDEX idx_ganaderia_animales_corral ON ganaderia_animales(corral_id);
CREATE INDEX idx_ganaderia_animales_vuelo ON ganaderia_animales(vuelo_id);
CREATE INDEX idx_ganaderia_alertas_estado ON ganaderia_alertas(estado);
