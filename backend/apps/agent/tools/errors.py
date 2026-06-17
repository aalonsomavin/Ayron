import json

AGENT_INSTRUCTION_ON_TOOL_ERROR = (
    "La tool falló. Corrige el problema (parámetros, SQL, markup, etc.) "
    "e invoca la misma tool de nuevo. No des por terminada la tarea "
    "hasta resolver el error o agotar 2-3 intentos razonables."
)

AGENT_INSTRUCTION_ON_QUERY_ERROR = (
    "La consulta falló. Corrige el SQL o los parámetros e invoca la tool de nuevo. "
    "No menciones al usuario este error ni los reintentos; responde solo cuando "
    "obtengas datos válidos o agotes 2-3 intentos razonables."
)


def build_tool_error_response(error: str, **extra) -> str:
    return json.dumps(
        {
            "ok": False,
            "error": error,
            "agent_instruction": AGENT_INSTRUCTION_ON_TOOL_ERROR,
            **extra,
        }
    )


def build_query_error_response(error: str, **extra) -> str:
    return build_tool_error_response(
        error,
        agent_instruction=AGENT_INSTRUCTION_ON_QUERY_ERROR,
        **extra,
    )
