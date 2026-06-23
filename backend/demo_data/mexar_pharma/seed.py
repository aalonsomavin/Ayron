from __future__ import annotations

import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

CATALOG_PATH = Path(__file__).resolve().parent / "catalog.json"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

INSTITUCIONES_PUBLICAS = [
    ("Hospital Civil de Guadalajara", "Jalisco", "Guadalajara", "Jalisco"),
    ("Hospital General de México", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("IMSS HGZ 46 Zapopan", "Jalisco", "Zapopan", "Jalisco"),
    ("IMSS UMAE Colonia Roma", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("ISSSTE Clínica La Raza", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Hospital Regional de Alta Especialidad de Oaxaca", "Oaxaca", "Oaxaca", "Sur"),
    ("Hospital General de Tijuana", "Baja California", "Tijuana", "Norte"),
    ("Hospital Universitario Dr. José Eleuterio González", "Nuevo León", "Monterrey", "Norte"),
    ("Hospital General de Puebla", "Puebla", "Puebla", "Centro"),
    ("Hospital General de Querétaro", "Querétaro", "Querétaro", "Centro"),
    ("Hospital General de León", "Guanajuato", "León", "Centro"),
    ("Hospital General de Mérida", "Yucatán", "Mérida", "Sur"),
    ("Hospital General de Aguascalientes", "Aguascalientes", "Aguascalientes", "Centro"),
    ("Hospital General de Morelia", "Michoacán", "Morelia", "Occidente"),
    ("Hospital General de Culiacán", "Sinaloa", "Culiacán", "Occidente"),
]

INSTITUCIONES_PRIVADAS = [
    ("Hospital Ángeles del Carmen", "Jalisco", "Guadalajara", "Jalisco"),
    ("Hospital Ángeles Pedregal", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Hospital San Javier", "Jalisco", "Guadalajara", "Jalisco"),
    ("Hospital ABC Santa Fe", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Médica Sur", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Hospital Puerta de Hierro", "Jalisco", "Zapopan", "Jalisco"),
    ("Hospital Zambrano Hellion", "Nuevo León", "Monterrey", "Norte"),
    ("Star Médica Puebla", "Puebla", "Puebla", "Centro"),
    ("Hospital Christus Muguerza", "Nuevo León", "Monterrey", "Norte"),
    ("Hospital Ángeles Tijuana", "Baja California", "Tijuana", "Norte"),
]

FARMACIAS = [
    ("Farmacia del Ahorro Guadalajara Centro", "Jalisco", "Guadalajara", "Jalisco"),
    ("Farmacias Similares Insurgentes", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Farmacia Benavides Zapopan", "Jalisco", "Zapopan", "Jalisco"),
    ("Farmacia Guadalajara Polanco", "Ciudad de México", "Ciudad de México", "CDMX"),
    ("Farmacia San Pablo Monterrey", "Nuevo León", "Monterrey", "Norte"),
    ("Farmacia del Ahorro León", "Guanajuato", "León", "Centro"),
    ("Farmacias Similares Puebla Centro", "Puebla", "Puebla", "Centro"),
    ("Farmacia Guadalajara Tijuana", "Baja California", "Tijuana", "Norte"),
]

EJECUTIVOS = [
    ("Ana Rodríguez", "ana.rodriguez@mexarpharma.com", "Guadalajara"),
    ("Carlos Mendoza", "carlos.mendoza@mexarpharma.com", "Guadalajara"),
    ("Laura Vega", "laura.vega@mexarpharma.com", "Ciudad de México"),
    ("Miguel Torres", "miguel.torres@mexarpharma.com", "Ciudad de México"),
    ("Patricia Solís", "patricia.solis@mexarpharma.com", "Guadalajara"),
    ("Roberto Núñez", "roberto.nunez@mexarpharma.com", "Ciudad de México"),
]

CONTACTOS_ROLES = ["compras", "medico", "farmacovigilancia", "director_medico"]
CANALES = ["directo", "distribuidor", "gobierno"]
ETAPAS = ["prospeccion", "negociacion", "firmado", "perdido"]
ACTIVIDAD_TIPOS = ["visita", "llamada", "email"]

ONCOLOGY_SKUS = {"ASGEN", "IRIASPE", "KEBIRAS", "DEGEHN"}
DIABETES_SKUS = {"ARGLIPTIN-D", "BITAM"}
WEIGHT_BY_SKU = {
    "ASGEN": 8.0,
    "KEBIRAS": 7.5,
    "IRIASPE": 6.5,
    "DEGEHN": 5.0,
    "ARGLIPTIN-D": 6.0,
    "BITAM": 4.5,
    "FIBCORIF": 3.0,
    "KAMEDIX": 2.5,
    "SELENCOR": 3.5,
    "VARPHARM": 3.0,
    "DACROLEM": 2.5,
}


def load_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def schema_is_ready(conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'comercial_productos'
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
            "Cannot create Mexar demo schema. Set DEMO_DB_URL to the local demo database "
            "(postgres://demo:demo@demo-db:5432/mexar_demo); read-only URLs cannot be seeded."
        ) from exc
    conn.commit()
    return True


def is_seeded(conn: psycopg.Connection) -> bool:
    if not schema_is_ready(conn):
        return False
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM comercial_productos")
        return cur.fetchone()[0] > 0


def clear_demo_data(conn: psycopg.Connection) -> None:
    tables = [
        "crm_actividades",
        "crm_oportunidades",
        "crm_contactos",
        "crm_cuentas",
        "crm_ejecutivos",
        "comercial_inventario",
        "comercial_pedido_lineas",
        "comercial_pedidos",
        "comercial_instituciones",
        "comercial_productos",
        "comercial_areas_terapeuticas",
    ]
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")


def seed_mexar_demo(conn_url: str, *, force: bool = False, random_seed: int = 42) -> dict:
    rng = random.Random(random_seed)
    catalog = load_catalog()
    schema_applied = False

    with psycopg.connect(conn_url) as conn:
        schema_applied = ensure_schema(conn)

        if is_seeded(conn) and not force:
            return {"skipped": True, "reason": "already_seeded"}

        if force and schema_is_ready(conn):
            clear_demo_data(conn)

        area_ids: dict[str, int] = {}
        product_ids: dict[str, int] = {}
        institucion_ids: list[int] = []
        cuenta_ids: list[int] = []

        with conn.cursor() as cur:
            for nombre in catalog["areas_terapeuticas"]:
                cur.execute(
                    "INSERT INTO comercial_areas_terapeuticas (nombre) VALUES (%s) RETURNING id",
                    (nombre,),
                )
                area_ids[nombre] = cur.fetchone()[0]

            for producto in catalog["productos"]:
                cur.execute(
                    """
                    INSERT INTO comercial_productos
                        (sku, marca_comercial, molecula, presentacion, area_id, precio_lista)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        producto["sku"],
                        producto["marca_comercial"],
                        producto["molecula"],
                        producto["presentacion"],
                        area_ids[producto["area"]],
                        Decimal(str(producto["precio_lista"])),
                    ),
                )
                product_ids[producto["sku"]] = cur.fetchone()[0]

            instituciones: list[tuple[str, str, str, str, str]] = []
            for nombre, estado, ciudad, region in INSTITUCIONES_PUBLICAS:
                instituciones.append((nombre, "hospital_publico", estado, ciudad, region))
            for nombre, estado, ciudad, region in INSTITUCIONES_PRIVADAS:
                instituciones.append((nombre, "hospital_privado", estado, ciudad, region))
            for nombre, estado, ciudad, region in FARMACIAS:
                instituciones.append((nombre, "farmacia", estado, ciudad, region))

            for idx in range(120):
                region = rng.choice(["Jalisco", "CDMX", "Centro", "Norte", "Occidente", "Sur"])
                if region == "Jalisco":
                    estado, ciudad = "Jalisco", rng.choice(["Guadalajara", "Zapopan", "Tlaquepaque"])
                elif region == "CDMX":
                    estado, ciudad = "Ciudad de México", "Ciudad de México"
                else:
                    estado = rng.choice(["Puebla", "Nuevo León", "Guanajuato", "Michoacán"])
                    ciudad = rng.choice(["Puebla", "Monterrey", "León", "Morelia"])
                tipo = rng.choice(["hospital_publico", "hospital_privado", "farmacia", "distribuidor"])
                nombre = f"Instituto {rng.choice(['Nacional', 'Regional', 'Central'])} {ciudad} {idx}"
                instituciones.append((nombre, tipo, estado, ciudad, region))

            for nombre, tipo, estado, ciudad, region in instituciones:
                cur.execute(
                    """
                    INSERT INTO comercial_instituciones (nombre, tipo, estado, ciudad, region)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (nombre, tipo, estado, ciudad, region),
                )
                institucion_ids.append(cur.fetchone()[0])

            ejecutivo_ids: list[int] = []
            for nombre, email, oficina in EJECUTIVOS:
                cur.execute(
                    "INSERT INTO crm_ejecutivos (nombre, email, oficina) VALUES (%s, %s, %s) RETURNING id",
                    (nombre, email, oficina),
                )
                ejecutivo_ids.append(cur.fetchone()[0])

            product_weights = []
            product_skus = []
            for producto in catalog["productos"]:
                sku = producto["sku"]
                product_skus.append(sku)
                product_weights.append(WEIGHT_BY_SKU.get(sku, 1.5))

            start_date = date.today() - timedelta(days=730)
            pedido_count = 0
            linea_count = 0

            for day_offset in range(730):
                order_date = start_date + timedelta(days=day_offset)
                daily_orders = rng.randint(4, 12)
                for _ in range(daily_orders):
                    institucion_id = rng.choice(institucion_ids)
                    canal = rng.choices(CANALES, weights=[0.5, 0.3, 0.2])[0]
                    line_count = rng.randint(1, 5)
                    line_items = []
                    monto_total = Decimal("0")

                    for _ in range(line_count):
                        sku = rng.choices(product_skus, weights=product_weights)[0]
                        producto_id = product_ids[sku]
                        base_price = Decimal(
                            str(next(p["precio_lista"] for p in catalog["productos"] if p["sku"] == sku))
                        )
                        discount = Decimal(str(rng.uniform(0.92, 1.0)))
                        precio = (base_price * discount).quantize(Decimal("0.01"))
                        if sku in ONCOLOGY_SKUS:
                            cantidad = rng.randint(2, 24)
                        elif sku in DIABETES_SKUS:
                            cantidad = rng.randint(5, 40)
                        else:
                            cantidad = rng.randint(1, 20)
                        subtotal = precio * cantidad
                        monto_total += subtotal
                        line_items.append((producto_id, cantidad, precio))

                    cur.execute(
                        """
                        INSERT INTO comercial_pedidos (institucion_id, fecha, canal, monto_total)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (institucion_id, order_date, canal, monto_total),
                    )
                    pedido_id = cur.fetchone()[0]
                    pedido_count += 1

                    for producto_id, cantidad, precio in line_items:
                        cur.execute(
                            """
                            INSERT INTO comercial_pedido_lineas
                                (pedido_id, producto_id, cantidad, precio_unitario)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (pedido_id, producto_id, cantidad, precio),
                        )
                        linea_count += 1

            for sku, producto_id in product_ids.items():
                for almacen in ("Guadalajara", "CDMX"):
                    stock = rng.randint(80, 600) if sku in ONCOLOGY_SKUS else rng.randint(150, 1200)
                    cur.execute(
                        """
                        INSERT INTO comercial_inventario
                            (producto_id, almacen, stock, lote, fecha_caducidad)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            producto_id,
                            almacen,
                            stock,
                            f"LOT-{sku}-{rng.randint(1000, 9999)}",
                            date.today() + timedelta(days=rng.randint(180, 900)),
                        ),
                    )

            for institucion_id in institucion_ids[:160]:
                ejecutivo_id = rng.choice(ejecutivo_ids)
                tier = rng.choices(["A", "B", "C"], weights=[0.2, 0.45, 0.35])[0]
                cur.execute(
                    "SELECT tipo FROM comercial_instituciones WHERE id = %s",
                    (institucion_id,),
                )
                tipo = cur.fetchone()[0]
                segmento = (
                    "publico"
                    if tipo == "hospital_publico"
                    else "privado"
                    if tipo == "hospital_privado"
                    else "retail"
                )
                cur.execute(
                    """
                    INSERT INTO crm_cuentas (institucion_id, ejecutivo_id, tier, segmento)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (institucion_id, ejecutivo_id, tier, segmento),
                )
                cuenta_id = cur.fetchone()[0]
                cuenta_ids.append(cuenta_id)

                for idx in range(rng.randint(1, 3)):
                    rol = CONTACTOS_ROLES[idx % len(CONTACTOS_ROLES)]
                    cur.execute(
                        """
                        INSERT INTO crm_contactos (cuenta_id, nombre, rol, email)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            cuenta_id,
                            f"Contacto {rng.choice(['Dr.', 'Lic.', 'Ing.'])} {rng.choice(['García', 'López', 'Hernández', 'Martínez', 'Ruiz'])}",
                            rol,
                            f"contacto{institucion_id}_{idx}@institucion.mx",
                        ),
                    )

            oncology_products = [p for p in catalog["productos"] if p["sku"] in ONCOLOGY_SKUS]
            for cuenta_id in cuenta_ids[:80]:
                producto = rng.choice(oncology_products + catalog["productos"])
                producto_id = product_ids[producto["sku"]]
                etapa = rng.choices(ETAPAS, weights=[0.25, 0.35, 0.3, 0.1])[0]
                valor = Decimal(str(producto["precio_lista"] * rng.randint(50, 400)))
                fecha_inicio = date.today() - timedelta(days=rng.randint(30, 400))
                fecha_cierre = date.today() + timedelta(days=rng.randint(-60, 120))
                fecha_cierre_real = fecha_cierre if etapa == "firmado" else None
                cur.execute(
                    """
                    INSERT INTO crm_oportunidades
                        (cuenta_id, producto_id, molecula, etapa, valor_estimado,
                         fecha_inicio, fecha_cierre_esperada, fecha_cierre_real)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        cuenta_id,
                        producto_id,
                        producto["molecula"],
                        etapa,
                        valor,
                        fecha_inicio,
                        fecha_cierre,
                        fecha_cierre_real,
                    ),
                )

            for cuenta_id in cuenta_ids:
                for _ in range(rng.randint(0, 3)):
                    cur.execute(
                        """
                        INSERT INTO crm_actividades (cuenta_id, tipo, fecha, notas)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            cuenta_id,
                            rng.choice(ACTIVIDAD_TIPOS),
                            date.today() - timedelta(days=rng.randint(1, 90)),
                            rng.choice(
                                [
                                    "Seguimiento de pedido trimestral",
                                    "Presentación de portafolio oncología",
                                    "Revisión de contrato de licenciamiento",
                                    "Visita a comité de compras",
                                ]
                            ),
                        ),
                    )

        conn.commit()

    return {
        "skipped": False,
        "schema_applied": schema_applied,
        "pedidos": pedido_count,
        "lineas": linea_count,
        "instituciones": len(institucion_ids),
        "productos": len(product_ids),
        "cuentas": len(cuenta_ids),
    }


if __name__ == "__main__":
    import os
    import sys

    url = os.environ.get("DEMO_DB_URL", "postgres://demo:demo@localhost:5433/mexar_demo")
    force = "--force" in sys.argv
    result = seed_mexar_demo(url, force=force)
    print(result)
