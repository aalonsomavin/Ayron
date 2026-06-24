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
            "name": "Resumen mensual de ventas por área terapéutica",
            "description": (
                "Consulta ingresos del mes por oncología, diabetes y cardiología; "
                "genera reporte HTML y Excel para dirección comercial."
            ),
            "frequency_label": "Mensual",
            "last_run_label": "1/6/2026",
            "next_run_label": "1/7/2026",
            "is_active": True,
        },
        {
            "name": "Monitoreo diario de precios vs competencia",
            "description": (
                "Revisa brechas de precio de Argliptin-D, Bitam y línea oncología "
                "frente a genéricos; alerta por email si el desvío supera el 5%."
            ),
            "frequency_label": "Diario",
            "last_run_label": "23/6/2026",
            "next_run_label": "24/6/2026",
            "is_active": False,
        },
        {
            "name": "Pipeline CRM — oportunidades por vencer",
            "description": (
                "Lista oportunidades de licenciamiento que cierran en los próximos 60 días "
                "y envía resumen semanal al equipo comercial."
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
