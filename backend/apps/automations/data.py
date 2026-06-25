STATUS_TONES = {
    True: "success",
    False: "neutral",
}

STATUS_LABELS = {
    True: "Activa",
    False: "Inactiva",
}


def get_automations():
    automations = [
        {
            "name": "Reporte de rodeo semanal para banco",
            "description": (
                "Conteo certificado, peso promedio y BCS por corral del Feedlot Cliente Cero; "
                "genera PDF con hash RTK del último vuelo YIVTOL."
            ),
            "frequency_label": "Semanal",
            "last_run_label": "23/6/2026",
            "next_run_label": "30/6/2026",
            "is_active": True,
        },
        {
            "name": "Alerta sanitaria — temperatura animal > 39.5°C",
            "description": (
                "Monitorea termografía del último vuelo; notifica si algún animal supera "
                "el umbral o está 1.5°C sobre el promedio del corral."
            ),
            "frequency_label": "Tiempo real",
            "last_run_label": "26/6/2026",
            "next_run_label": "Continuo",
            "is_active": True,
        },
        {
            "name": "Alerta biomasa de potrero bajo umbral",
            "description": (
                "Revisa LiDAR de pasturas; avisa si la biomasa disponible cae por debajo "
                "del 40% y sugiere rotación."
            ),
            "frequency_label": "Diario",
            "last_run_label": "25/6/2026",
            "next_run_label": "26/6/2026",
            "is_active": False,
        },
        {
            "name": "Resumen semanal de lotes en estrés hídrico",
            "description": (
                "Lista lotes con alertas activas, ha afectadas y prescripción de riego; "
                "envía reporte HTML al gerente de campo."
            ),
            "frequency_label": "Semanal",
            "last_run_label": "16/6/2026",
            "next_run_label": "23/6/2026",
            "is_active": False,
        },
    ]
    for automation in automations:
        automation["status_tone"] = STATUS_TONES[automation["is_active"]]
        automation["status_label"] = STATUS_LABELS[automation["is_active"]]
    return automations
