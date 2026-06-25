STATUS_TONES = {
    "connected": "success",
    "syncing": "warning",
    "error": "danger",
}


def get_connected_sources():
    sources = [
        {
            "name": "YIVTOL S-ZERO — Vuelos Aéreos",
            "subtitle": "yivtol_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": "12 tablas",
            "volume_label": "18.2k filas · 96 MB",
            "icon": "database",
            "color": "#336791",
        },
        {
            "name": "AyronOne — Agricultura y Ganadería",
            "subtitle": "yivtol_demo · PostgreSQL",
            "type_label": "SQL",
            "status": "connected",
            "status_label": "Conectada",
            "structure_label": "11 tablas",
            "volume_label": "2.4k filas · 14 MB",
            "icon": "database",
            "color": "#29b5e8",
        },
    ]
    for source in sources:
        source["status_tone"] = STATUS_TONES.get(source["status"], "neutral")
        source["last_sync"] = "< 1 minuto"
    return sources
