def get_connected_sources():
    return [
        {
            "name": "Mexar Pharma — Producción",
            "type": "PostgreSQL",
            "status": "connected",
            "status_label": "Conectada",
            "database": "mexar_demo",
            "table_count": 11,
            "last_sync": "Hace 3 min",
            "domains": [
                {
                    "name": "ERP Comercial",
                    "prefix": "comercial_*",
                    "description": (
                        "Productos, pedidos, instituciones e inventario "
                        "de la operación comercial."
                    ),
                    "tables": [
                        {
                            "name": "comercial_areas_terapeuticas",
                            "description": "Áreas terapéuticas del catálogo.",
                        },
                        {
                            "name": "comercial_productos",
                            "description": (
                                "SKUs, marcas comerciales, moléculas y precios de lista."
                            ),
                        },
                        {
                            "name": "comercial_instituciones",
                            "description": (
                                "Hospitales, farmacias y distribuidores por región."
                            ),
                        },
                        {
                            "name": "comercial_pedidos",
                            "description": "Pedidos por institución, canal y monto total.",
                        },
                        {
                            "name": "comercial_pedido_lineas",
                            "description": "Líneas de pedido con cantidad y precio unitario.",
                        },
                        {
                            "name": "comercial_inventario",
                            "description": "Stock por almacén, lote y fecha de caducidad.",
                        },
                    ],
                },
                {
                    "name": "CRM Licenciamiento",
                    "prefix": "crm_*",
                    "description": (
                        "Cuentas, contactos, oportunidades y actividades "
                        "del pipeline de licenciamiento."
                    ),
                    "tables": [
                        {
                            "name": "crm_ejecutivos",
                            "description": "Ejecutivos comerciales por oficina.",
                        },
                        {
                            "name": "crm_cuentas",
                            "description": (
                                "Cuentas vinculadas a instituciones, tier y segmento."
                            ),
                        },
                        {
                            "name": "crm_contactos",
                            "description": "Contactos por cuenta con rol y email.",
                        },
                        {
                            "name": "crm_oportunidades",
                            "description": (
                                "Oportunidades de licenciamiento por etapa y valor estimado."
                            ),
                        },
                        {
                            "name": "crm_actividades",
                            "description": "Actividades de seguimiento por cuenta.",
                        },
                    ],
                },
            ],
        }
    ]
