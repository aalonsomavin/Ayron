from __future__ import annotations

import hashlib
import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

ESTABLECIMIENTO_PATH = Path(__file__).resolve().parent / "establecimiento.json"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

DEMO_TABLES = [
    "agricola_establecimientos",
    "ganaderia_establecimientos",
    "yivtol_vuelos",
    "agricola_lotes",
    "agricola_mediciones",
    "agricola_zonas",
    "agricola_alertas",
    "ganaderia_corrales",
    "ganaderia_animales",
    "ganaderia_mediciones_corral",
    "ganaderia_potreros",
    "ganaderia_alertas",
]


def load_establecimiento() -> dict:
    with ESTABLECIMIENTO_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def schema_is_ready(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'yivtol_vuelos'
            """
        )
        return cur.fetchone() is not None


def ensure_schema(conn: psycopg.Connection) -> bool:
    if schema_is_ready(conn):
        return False
    try:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    except psycopg.errors.InsufficientPrivilege as exc:
        raise RuntimeError(
            "Cannot create YIVTOL demo schema. Set DEMO_DB_URL to the local demo database "
            "(postgres://demo:demo@demo-db:5432/yivtol_demo); read-only URLs cannot be seeded."
        ) from exc
    conn.commit()
    return True


def is_seeded(conn: psycopg.Connection) -> bool:
    if not schema_is_ready(conn):
        return False
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM yivtol_vuelos")
        return cur.fetchone()[0] > 0


def clear_demo_data(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        for table in reversed(DEMO_TABLES):
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")


def _flight_hash(fecha: date, dominio: str, pilot: str) -> str:
    payload = f"{fecha.isoformat()}|{dominio}|{pilot}|YIVTOL-S-ZERO"
    return hashlib.sha256(payload.encode()).hexdigest()


def _insert_vuelo(
    cur,
    *,
    fecha: date,
    dominio: str,
    hectareas: float,
    duracion_min: int,
    piloto: str,
    agricola_est_id: int | None,
    ganaderia_est_id: int | None,
) -> int:
    cur.execute(
        """
        INSERT INTO yivtol_vuelos
            (fecha, aeronave, dominio, hectareas_cubiertas, duracion_min, piloto,
             hash_certificado, agricola_establecimiento_id, ganaderia_establecimiento_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            fecha,
            "YIVTOL S-ZERO",
            dominio,
            Decimal(str(hectareas)),
            duracion_min,
            piloto,
            _flight_hash(fecha, dominio, piloto),
            agricola_est_id,
            ganaderia_est_id,
        ),
    )
    return cur.fetchone()[0]


def _seed_agricola_medicion(
    cur,
    *,
    vuelo_id: int,
    lote_id: int,
    ndvi: float,
    ndre: float,
    estres: float,
    temp_prom: float,
    temp_delta: float,
    biomasa: float,
    rinde: float,
    pct_alta: float,
    pct_media: float,
    pct_baja: float,
) -> int:
    cur.execute(
        """
        INSERT INTO agricola_mediciones
            (vuelo_id, lote_id, ndvi_promedio, ndre_promedio, pct_estres_hidrico,
             temp_foliar_promedio_c, temp_foliar_delta_c, biomasa_t_ha,
             rinde_proyectado_kg_ha, pct_zona_alta, pct_zona_media, pct_zona_baja)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            vuelo_id,
            lote_id,
            Decimal(str(ndvi)),
            Decimal(str(ndre)),
            Decimal(str(estres)),
            Decimal(str(temp_prom)),
            Decimal(str(temp_delta)),
            Decimal(str(biomasa)),
            Decimal(str(rinde)),
            Decimal(str(pct_alta)),
            Decimal(str(pct_media)),
            Decimal(str(pct_baja)),
        ),
    )
    return cur.fetchone()[0]


def seed_yivtol_demo(conn_url: str, *, force: bool = False, random_seed: int = 42) -> dict:
    rng = random.Random(random_seed)
    data = load_establecimiento()
    schema_applied = False

    with psycopg.connect(conn_url) as conn:
        schema_applied = ensure_schema(conn)

        if is_seeded(conn) and not force:
            return {"skipped": True, "reason": "already_seeded"}

        if force and schema_is_ready(conn):
            clear_demo_data(conn)

        today = date.today()
        pilotos = data["pilotos"]
        lote_ids: dict[str, int] = {}
        corral_ids: dict[str, int] = {}
        vuelo_count = 0
        medicion_count = 0
        animal_count = 0
        alerta_ag_count = 0
        alerta_gan_count = 0

        with conn.cursor() as cur:
            agr = data["agricola_establecimiento"]
            cur.execute(
                """
                INSERT INTO agricola_establecimientos (nombre, provincia, superficie_total_ha)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (agr["nombre"], agr["provincia"], Decimal(str(agr["superficie_total_ha"]))),
            )
            agricola_est_id = cur.fetchone()[0]

            gan = data["ganaderia_establecimiento"]
            cur.execute(
                """
                INSERT INTO ganaderia_establecimientos
                    (nombre, provincia, tipo, cabezas_nominales)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (gan["nombre"], gan["provincia"], gan["tipo"], gan["cabezas_nominales"]),
            )
            ganaderia_est_id = cur.fetchone()[0]

            for lote in data["lotes"]:
                cur.execute(
                    """
                    INSERT INTO agricola_lotes
                        (establecimiento_id, codigo, nombre, cultivo, superficie_ha)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        agricola_est_id,
                        lote["codigo"],
                        lote["nombre"],
                        lote["cultivo"],
                        Decimal(str(lote["superficie_ha"])),
                    ),
                )
                lote_ids[lote["codigo"]] = cur.fetchone()[0]

            for corral in data["corrales"]:
                cur.execute(
                    """
                    INSERT INTO ganaderia_corrales
                        (establecimiento_id, codigo, capacidad, cabezas_actuales)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ganaderia_est_id,
                        corral["codigo"],
                        corral["capacidad"],
                        corral["cabezas_actuales"],
                    ),
                )
                corral_ids[corral["codigo"]] = cur.fetchone()[0]

            vuelo_reciente_ag = _insert_vuelo(
                cur,
                fecha=today - timedelta(days=2),
                dominio="agricola",
                hectareas=4200,
                duracion_min=420,
                piloto=pilotos[0],
                agricola_est_id=agricola_est_id,
                ganaderia_est_id=None,
            )
            vuelo_count += 1

            vuelo_abril_norte = _insert_vuelo(
                cur,
                fecha=date(today.year, 4, 12),
                dominio="agricola",
                hectareas=580,
                duracion_min=95,
                piloto=pilotos[1],
                agricola_est_id=agricola_est_id,
                ganaderia_est_id=None,
            )
            vuelo_count += 1

            vuelo_mayo_norte = _insert_vuelo(
                cur,
                fecha=date(today.year, 5, 18),
                dominio="agricola",
                hectareas=580,
                duracion_min=98,
                piloto=pilotos[1],
                agricola_est_id=agricola_est_id,
                ganaderia_est_id=None,
            )
            vuelo_count += 1

            vuelo_reciente_gan = _insert_vuelo(
                cur,
                fecha=today - timedelta(days=1),
                dominio="ganaderia",
                hectareas=120,
                duracion_min=180,
                piloto=pilotos[2],
                agricola_est_id=None,
                ganaderia_est_id=ganaderia_est_id,
            )
            vuelo_count += 1

            for offset in (45, 90, 135, 180, 240, 300):
                flight_date = today - timedelta(days=offset)
                if flight_date.month in (4, 5) and flight_date.day in (12, 18):
                    continue
                _insert_vuelo(
                    cur,
                    fecha=flight_date,
                    dominio=rng.choice(["agricola", "ganaderia"]),
                    hectareas=rng.uniform(400, 1200),
                    duracion_min=rng.randint(120, 480),
                    piloto=rng.choice(pilotos),
                    agricola_est_id=agricola_est_id if rng.random() > 0.4 else None,
                    ganaderia_est_id=ganaderia_est_id if rng.random() > 0.4 else None,
                )
                vuelo_count += 1

            lote7_id = lote_ids["Lote 7"]
            medicion_lote7 = _seed_agricola_medicion(
                cur,
                vuelo_id=vuelo_reciente_ag,
                lote_id=lote7_id,
                ndvi=0.62,
                ndre=0.48,
                estres=18.5,
                temp_prom=31.2,
                temp_delta=4.0,
                biomasa=4.8,
                rinde=3200,
                pct_alta=35.0,
                pct_media=40.0,
                pct_baja=25.0,
            )
            medicion_count += 1

            cur.execute(
                """
                INSERT INTO agricola_zonas
                    (medicion_id, zona, clasificacion, superficie_ha, ndvi, accion_recomendada)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    medicion_lote7,
                    "Norte",
                    "critica",
                    Decimal("42"),
                    Decimal("0.41"),
                    "Riego diferencial en las próximas 48 hs",
                ),
            )
            cur.execute(
                """
                INSERT INTO agricola_zonas
                    (medicion_id, zona, clasificacion, superficie_ha, ndvi, accion_recomendada)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    medicion_lote7,
                    "Centro",
                    "media",
                    Decimal("210"),
                    Decimal("0.65"),
                    "Monitoreo semanal",
                ),
            )
            cur.execute(
                """
                INSERT INTO agricola_zonas
                    (medicion_id, zona, clasificacion, superficie_ha, ndvi, accion_recomendada)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    medicion_lote7,
                    "Sur",
                    "alta",
                    Decimal("248"),
                    Decimal("0.78"),
                    "Sin intervención",
                ),
            )

            cur.execute(
                """
                INSERT INTO agricola_alertas
                    (vuelo_id, lote_id, tipo, severidad, mensaje, ha_afectadas,
                     fecha_deteccion, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_ag,
                    lote7_id,
                    "estres_hidrico",
                    "alta",
                    "Lote 7 — Zona Norte — Estrés hídrico detectado en 42 ha. "
                    "Temperatura foliar 4°C sobre promedio. Riego recomendado en las próximas 48 hs.",
                    Decimal("42"),
                    today - timedelta(days=2),
                    "activa",
                ),
            )
            alerta_ag_count += 1

            lote_norte_id = lote_ids["Lote Norte"]
            _seed_agricola_medicion(
                cur,
                vuelo_id=vuelo_abril_norte,
                lote_id=lote_norte_id,
                ndvi=0.71,
                ndre=0.52,
                estres=6.0,
                temp_prom=27.5,
                temp_delta=0.8,
                biomasa=5.2,
                rinde=3500,
                pct_alta=55.0,
                pct_media=30.0,
                pct_baja=15.0,
            )
            medicion_count += 1
            _seed_agricola_medicion(
                cur,
                vuelo_id=vuelo_mayo_norte,
                lote_id=lote_norte_id,
                ndvi=0.74,
                ndre=0.61,
                estres=4.5,
                temp_prom=28.1,
                temp_delta=0.5,
                biomasa=5.6,
                rinde=3680,
                pct_alta=62.0,
                pct_media=28.0,
                pct_baja=10.0,
            )
            medicion_count += 1

            for codigo, lote_id in lote_ids.items():
                if codigo in ("Lote 7", "Lote Norte"):
                    continue
                ndvi = rng.uniform(0.55, 0.82)
                ndre = rng.uniform(0.40, 0.70)
                _seed_agricola_medicion(
                    cur,
                    vuelo_id=vuelo_reciente_ag,
                    lote_id=lote_id,
                    ndvi=round(ndvi, 3),
                    ndre=round(ndre, 3),
                    estres=round(rng.uniform(2, 12), 1),
                    temp_prom=round(rng.uniform(26, 30), 1),
                    temp_delta=round(rng.uniform(-0.5, 2.5), 1),
                    biomasa=round(rng.uniform(3.5, 6.0), 1),
                    rinde=round(rng.uniform(2800, 4000), 0),
                    pct_alta=round(rng.uniform(30, 60), 1),
                    pct_media=round(rng.uniform(25, 45), 1),
                    pct_baja=round(rng.uniform(5, 25), 1),
                )
                medicion_count += 1

            corral5_id = corral_ids["Corral 5"]
            corral3_id = corral_ids["Corral 3"]
            temp_prom_corral5 = Decimal("38.20")
            cur.execute(
                """
                INSERT INTO ganaderia_mediciones_corral
                    (vuelo_id, corral_id, total_cabezas, peso_promedio_kg, bcs_promedio,
                     varianza_peso, temperatura_promedio_c)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_gan,
                    corral5_id,
                    495,
                    Decimal("445.50"),
                    Decimal("3.2"),
                    Decimal("820.40"),
                    temp_prom_corral5,
                ),
            )

            cur.execute(
                """
                INSERT INTO ganaderia_mediciones_corral
                    (vuelo_id, corral_id, total_cabezas, peso_promedio_kg, bcs_promedio,
                     varianza_peso, temperatura_promedio_c)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_gan,
                    corral3_id,
                    510,
                    Decimal("462.30"),
                    Decimal("3.4"),
                    Decimal("910.20"),
                    Decimal("38.50"),
                ),
            )

            for corral_codigo, corral_id in corral_ids.items():
                if corral_codigo in ("Corral 3", "Corral 5"):
                    continue
                cabezas_corral = next(
                    c["cabezas_actuales"] for c in data["corrales"] if c["codigo"] == corral_codigo
                )
                cur.execute(
                    """
                    INSERT INTO ganaderia_mediciones_corral
                        (vuelo_id, corral_id, total_cabezas, peso_promedio_kg, bcs_promedio,
                         varianza_peso, temperatura_promedio_c)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        vuelo_reciente_gan,
                        corral_id,
                        cabezas_corral,
                        Decimal(str(round(rng.uniform(420, 470), 2))),
                        Decimal(str(round(rng.uniform(2.8, 3.5), 1))),
                        Decimal(str(round(rng.uniform(600, 950), 2))),
                        Decimal(str(round(rng.uniform(37.5, 38.8), 2))),
                    ),
                )

            alert_animal_codes = ["YIV-C5-0142", "YIV-C5-0287", "YIV-C5-0411"]
            alert_temp = temp_prom_corral5 + Decimal("1.80")
            for idx in range(495):
                codigo_animal = f"YIV-C5-{idx + 1:04d}"
                peso = Decimal(str(round(rng.uniform(410, 470), 2)))
                bcs = Decimal(str(round(rng.uniform(2.8, 3.6), 1)))
                if codigo_animal in alert_animal_codes:
                    temp = alert_temp
                    estado = "alerta"
                else:
                    temp = Decimal(str(round(rng.uniform(37.2, 38.5), 2)))
                    estado = "normal"
                cur.execute(
                    """
                    INSERT INTO ganaderia_animales
                        (corral_id, vuelo_id, codigo_animal, peso_kg, bcs, temperatura_c,
                         estado, lat, lon)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        corral5_id,
                        vuelo_reciente_gan,
                        codigo_animal,
                        peso,
                        bcs,
                        temp,
                        estado,
                        Decimal(str(round(-34.6 + rng.uniform(-0.01, 0.01), 6))),
                        Decimal(str(round(-58.4 + rng.uniform(-0.01, 0.01), 6))),
                    ),
                )
                animal_count += 1

            venta_count = 0
            for idx in range(510):
                codigo_animal = f"YIV-C3-{idx + 1:04d}"
                if venta_count < 12:
                    peso = Decimal(str(round(rng.uniform(482, 510), 2)))
                    venta_count += 1
                else:
                    peso = Decimal(str(round(rng.uniform(380, 475), 2)))
                cur.execute(
                    """
                    INSERT INTO ganaderia_animales
                        (corral_id, vuelo_id, codigo_animal, peso_kg, bcs, temperatura_c,
                         estado, lat, lon)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        corral3_id,
                        vuelo_reciente_gan,
                        codigo_animal,
                        peso,
                        Decimal(str(round(rng.uniform(3.0, 3.8), 1))),
                        Decimal(str(round(rng.uniform(37.5, 38.9), 2))),
                        "normal",
                        Decimal(str(round(-34.61 + rng.uniform(-0.01, 0.01), 6))),
                        Decimal(str(round(-58.41 + rng.uniform(-0.01, 0.01), 6))),
                    ),
                )
                animal_count += 1

            for corral_codigo, corral_id in corral_ids.items():
                if corral_codigo in ("Corral 3", "Corral 5"):
                    continue
                cabezas = next(c["cabezas_actuales"] for c in data["corrales"] if c["codigo"] == corral_codigo)
                prefix = corral_codigo.replace(" ", "-").upper()
                for idx in range(min(cabezas, 80)):
                    cur.execute(
                        """
                        INSERT INTO ganaderia_animales
                            (corral_id, vuelo_id, codigo_animal, peso_kg, bcs, temperatura_c,
                             estado, lat, lon)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            corral_id,
                            vuelo_reciente_gan,
                            f"YIV-{prefix}-{idx + 1:04d}",
                            Decimal(str(round(rng.uniform(390, 480), 2))),
                            Decimal(str(round(rng.uniform(2.7, 3.5), 1))),
                            Decimal(str(round(rng.uniform(37.0, 39.0), 2))),
                            "normal",
                            Decimal(str(round(-34.62 + rng.uniform(-0.02, 0.02), 6))),
                            Decimal(str(round(-58.42 + rng.uniform(-0.02, 0.02), 6))),
                        ),
                    )
                    animal_count += 1

            cur.execute(
                """
                INSERT INTO ganaderia_alertas
                    (vuelo_id, corral_id, potrero_id, tipo, severidad, mensaje,
                     animales_afectados, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_gan,
                    corral5_id,
                    None,
                    "sanitaria",
                    "alta",
                    "Corral 5 — 3 animales con temperatura 1.8°C sobre promedio del lote. "
                    "Se recomienda revisión veterinaria en las próximas 6 horas.",
                    3,
                    "activa",
                ),
            )
            alerta_gan_count += 1

            cur.execute(
                """
                INSERT INTO ganaderia_alertas
                    (vuelo_id, corral_id, potrero_id, tipo, severidad, mensaje,
                     animales_afectados, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_gan,
                    corral3_id,
                    None,
                    "venta",
                    "media",
                    "12 animales en Corral 3 superaron el umbral de 480 kg. "
                    "Ventana óptima de comercialización: próximos 10 días.",
                    12,
                    "activa",
                ),
            )
            alerta_gan_count += 1

            potrero_ids: dict[str, int] = {}
            for potrero in data["potreros"]:
                biomasa = 38.0 if potrero["codigo"] == "Potrero A" else round(rng.uniform(45, 72), 1)
                dias_rot = 7 if potrero["codigo"] == "Potrero A" else rng.randint(10, 21)
                cur.execute(
                    """
                    INSERT INTO ganaderia_potreros
                        (establecimiento_id, vuelo_id, codigo, superficie_ha, biomasa_pct,
                         dias_rotacion_sugeridos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        ganaderia_est_id,
                        vuelo_reciente_gan,
                        potrero["codigo"],
                        Decimal(str(potrero["superficie_ha"])),
                        Decimal(str(biomasa)),
                        dias_rot,
                    ),
                )
                potrero_ids[potrero["codigo"]] = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO ganaderia_alertas
                    (vuelo_id, corral_id, potrero_id, tipo, severidad, mensaje,
                     animales_afectados, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vuelo_reciente_gan,
                    None,
                    potrero_ids["Potrero A"],
                    "pastura",
                    "media",
                    "Potrero A con 38% de biomasa disponible — rotar en 7 días.",
                    None,
                    "activa",
                ),
            )
            alerta_gan_count += 1

        conn.commit()

    return {
        "skipped": False,
        "schema_applied": schema_applied,
        "vuelos": vuelo_count,
        "mediciones": medicion_count,
        "lotes": len(lote_ids),
        "corrales": len(corral_ids),
        "animales": animal_count,
        "alertas_agricola": alerta_ag_count,
        "alertas_ganaderia": alerta_gan_count,
    }


if __name__ == "__main__":
    import os
    import sys

    url = os.environ.get("DEMO_DB_URL", "postgres://demo:demo@localhost:5433/yivtol_demo")
    force = "--force" in sys.argv
    result = seed_yivtol_demo(url, force=force)
    print(result)
