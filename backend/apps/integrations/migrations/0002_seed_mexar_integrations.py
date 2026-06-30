from django.db import migrations


PRODUCTION_TABLES = [
    "comercial_areas_terapeuticas",
    "comercial_productos",
    "comercial_instituciones",
    "comercial_pedidos",
    "comercial_pedido_lineas",
    "comercial_inventario",
    "crm_ejecutivos",
    "crm_cuentas",
    "crm_contactos",
    "crm_oportunidades",
    "crm_actividades",
]

COMPETENCIA_TABLES = [
    "competencia_precios",
    "competencia_resumen",
]


def seed_mexar_integrations(apps, schema_editor):
    Integration = apps.get_model("integrations", "Integration")
    integrations = [
        {
            "slug": "mexar-demo",
            "name": "Mexar Pharma — Producción",
            "type": "postgres",
            "config": {
                "database": "mexar_demo",
                "display": {
                    "subtitle": "mexar_demo · PostgreSQL",
                    "type_label": "SQL",
                    "status": "connected",
                    "status_label": "Conectada",
                    "structure_label": "11 tablas",
                    "volume_label": "842k filas · 128 MB",
                    "icon": "database",
                    "color": "#336791",
                    "last_sync": "< 1 minuto",
                },
            },
            "schema_cache": {"tables": PRODUCTION_TABLES},
            "is_active": True,
        },
        {
            "slug": "mexar-competencia",
            "name": "Inteligencia de Mercado — Precios Competencia",
            "type": "postgres",
            "config": {
                "database": "mexar_demo",
                "display": {
                    "subtitle": "mexar_demo · PostgreSQL",
                    "type_label": "SQL",
                    "status": "connected",
                    "status_label": "Conectada",
                    "structure_label": "2 tablas",
                    "volume_label": "18.4k filas · 6 MB",
                    "icon": "database",
                    "color": "#29b5e8",
                    "last_sync": "< 1 minuto",
                },
            },
            "schema_cache": {"tables": COMPETENCIA_TABLES},
            "is_active": True,
        },
    ]
    for item in integrations:
        Integration.objects.update_or_create(slug=item["slug"], defaults=item)


def unseed_mexar_integrations(apps, schema_editor):
    Integration = apps.get_model("integrations", "Integration")
    Integration.objects.filter(slug__in=["mexar-demo", "mexar-competencia"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_mexar_integrations, unseed_mexar_integrations),
    ]
