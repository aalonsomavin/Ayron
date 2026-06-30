from apps.agent.tools.sql import DEMO_TABLES
from apps.integrations.models import Integration

STATUS_TONES = {
    "connected": "success",
    "syncing": "warning",
    "error": "danger",
}

INTEGRATION_TYPE_LABELS = {
    Integration.Type.POSTGRES: "SQL",
}

INTEGRATION_TYPE_COLORS = {
    Integration.Type.POSTGRES: "#336791",
}


def _table_groups():
    competencia_tables = {"competencia_precios", "competencia_resumen"}
    production_tables = [name for name in DEMO_TABLES if name not in competencia_tables]
    return production_tables, list(competencia_tables)


def _integration_display(integration: Integration) -> dict:
    display = integration.config.get("display", {})
    integration_type = integration.type
    status = display.get("status", "connected")
    return {
        "name": integration.name,
        "subtitle": display.get("subtitle", integration.slug),
        "type_label": display.get("type_label", INTEGRATION_TYPE_LABELS.get(integration_type, integration_type)),
        "status": status,
        "status_label": display.get("status_label", "Conectada"),
        "structure_label": display.get("structure_label", ""),
        "volume_label": display.get("volume_label", ""),
        "icon": display.get("icon", "database"),
        "color": display.get("color", INTEGRATION_TYPE_COLORS.get(integration_type, "#336791")),
        "status_tone": STATUS_TONES.get(status, "neutral"),
        "last_sync": display.get("last_sync", "< 1 minuto"),
    }


def get_connected_sources():
    integrations = Integration.objects.filter(is_active=True).order_by("name")
    if integrations.exists():
        return [_integration_display(integration) for integration in integrations]
    production_tables, competencia_tables = _table_groups()
    return [
        {
            "name": "Mexar Pharma — Producción",
            "subtitle": "mexar_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": f"{len(production_tables)} tablas",
            "volume_label": "842k filas · 128 MB",
            "icon": "database",
            "color": "#336791",
            "status_tone": "success",
            "last_sync": "< 1 minuto",
        },
        {
            "name": "Inteligencia de Mercado — Precios Competencia",
            "subtitle": "mexar_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": f"{len(competencia_tables)} tablas",
            "volume_label": "18.4k filas · 6 MB",
            "icon": "database",
            "color": "#29b5e8",
            "status_tone": "success",
            "last_sync": "< 1 minuto",
        },
    ]
