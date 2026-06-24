STATUS_TONES = {
    "connected": "success",
    "syncing": "warning",
    "error": "danger",
}


def get_connected_sources():
    sources = [
        {
            "name": "Mexar Pharma — Producción",
            "subtitle": "mexar_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": "11 tablas",
            "volume_label": "842k filas · 128 MB",
            "icon": "database",
            "color": "#336791",
        },
        {
            "name": "Inteligencia de Mercado — Precios Competencia",
            "subtitle": "mexar_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": "2 tablas",
            "volume_label": "18.4k filas · 6 MB",
            "icon": "database",
            "color": "#29b5e8",
        },
    ]
    for source in sources:
        source["status_tone"] = STATUS_TONES.get(source["status"], "neutral")
        source["last_sync"] = "< 1 minuto"
    return sources
