import re
from enum import Enum


class DeliverableIntent(str, Enum):
    CREATE_HTML = "create_html"
    CREATE_DOCX = "create_docx"
    UPDATE_FILE = "update_file"
    NONE = "none"


_UPDATE_VERB_RE = re.compile(
    r"\b(actualiza|actualizar|modifica|modificar|edita|editar|update|modify|edit)\b",
    re.IGNORECASE,
)
_FILE_REF_RE = re.compile(
    r"\b(informe|reporte|dashboard|documento|document|report|archivo|file)\b",
    re.IGNORECASE,
)
_DOCX_RE = re.compile(
    r"\b(word|docx|memo|carta|documento\s+word)\b",
    re.IGNORECASE,
)
_HTML_DELIVERABLE_RE = re.compile(
    r"\b("
    r"informe|reporte|dashboard|resumen\s+exportable|exportable|"
    r"exporta(?:r)?|pdf|brief|postmortem|status\s+report|"
    r"genera(?:r)?\s+(?:un\s+)?(?:informe|reporte|dashboard)"
    r")\b",
    re.IGNORECASE,
)
_ANALYTICAL_ONLY_RE = re.compile(
    r"^\s*(?:¿|cu[aá]nto|cu[aá]les|cu[aá]l|qu[eé]\s+(?:es|son)|top\s+\d+|lista(?:r)?|mu[eé]strame|dime)\b",
    re.IGNORECASE,
)

REQUIRED_TOOLS: dict[DeliverableIntent, frozenset[str]] = {
    DeliverableIntent.CREATE_HTML: frozenset(
        {"create_html_report", "publish_html_report"}
    ),
    DeliverableIntent.CREATE_DOCX: frozenset({"create_document"}),
    DeliverableIntent.UPDATE_FILE: frozenset({"update_html_report", "update_document"}),
}


def detect_deliverable_intent(user_message: str) -> DeliverableIntent:
    text = (user_message or "").strip()
    if not text:
        return DeliverableIntent.NONE

    if _UPDATE_VERB_RE.search(text) and _FILE_REF_RE.search(text):
        return DeliverableIntent.UPDATE_FILE

    if _DOCX_RE.search(text):
        return DeliverableIntent.CREATE_DOCX

    if _HTML_DELIVERABLE_RE.search(text):
        return DeliverableIntent.CREATE_HTML

    if _ANALYTICAL_ONLY_RE.search(text) and not _HTML_DELIVERABLE_RE.search(text):
        return DeliverableIntent.NONE

    return DeliverableIntent.NONE


def required_tools_for_intent(intent: DeliverableIntent) -> frozenset[str]:
    return REQUIRED_TOOLS.get(intent, frozenset())


def format_deliverable_prompt_block(intent: DeliverableIntent) -> str:
    if intent == DeliverableIntent.CREATE_HTML:
        return """\
## Entregable de este turno: reporte o dashboard HTML

El usuario pidió un archivo compartible (informe, dashboard o reporte HTML).

1. Planifica con `write_todos` antes de consultar datos. El último paso debe ser \
**Generar archivo** (`create_html_report` o flujo incremental + `publish_html_report`).
2. Consulta datos con SQL si hace falta; `show_data_table` y `show_chart` son pasos \
intermedios, no sustituyen el archivo.
3. Lee la skill `html-reports` y `GUIDELINES.md` antes de escribir HTML.
4. Dashboards pequeños: `create_html_report` con todo el contenido en una invocación.
5. Dashboards grandes: `create_html_report(..., build_mode="incremental")` → \
`append_html_report_block` por sección → `publish_html_report` al final.
6. No des por terminada la tarea hasta publicar o crear el archivo completo (`"ok": true`, sin `"draft": true`).
7. Tras entregar el archivo, no repitas su contenido en el chat."""

    if intent == DeliverableIntent.CREATE_DOCX:
        return """\
## Entregable de este turno: documento Word (.docx)

El usuario pidió un documento Word descargable.

1. Planifica con `write_todos` antes de consultar datos. El último paso debe ser \
**Generar archivo con create_document**.
2. Consulta datos con SQL si hace falta; tablas y gráficos del chat son pasos \
intermedios, no sustituyen el documento.
3. Lee la skill `docx-documents` antes de estructurar secciones.
4. Llama `create_document` con `title`, `sections` y opcionalmente `subtitle`.
5. No des por terminada la tarea hasta que `create_document` devuelva `"ok": true`.
6. Tras crear el documento, no repitas su contenido en el chat."""

    if intent == DeliverableIntent.UPDATE_FILE:
        return """\
## Entregable de este turno: actualizar archivo existente

El usuario pidió modificar un informe, dashboard o documento ya generado.

1. Planifica con `write_todos`. El último paso debe ser **Actualizar archivo** con \
`update_html_report` o `update_document` según el formato del `file_id`.
2. Usa el índice de archivos de la conversación o `list_conversation_files` para \
obtener el `file_id` correcto.
3. Si necesitas el contenido actual, llama `get_html_report` o `get_document`.
4. No llames `create_*` de nuevo para el mismo entregable; usa `update_*`.
5. No des por terminada la tarea hasta que la tool de actualización devuelva `"ok": true`.
6. Tras actualizar, no repitas el contenido en el chat."""

    return ""


def format_deliverable_nudge(intent: DeliverableIntent) -> str:
    if intent == DeliverableIntent.CREATE_HTML:
        return (
            "Aún no generaste el entregable. El usuario pidió un informe o dashboard HTML. "
            "Llama a create_html_report (completo) o publica el borrador con publish_html_report. "
            "No respondas solo en texto."
        )
    if intent == DeliverableIntent.CREATE_DOCX:
        return (
            "Aún no generaste el entregable. El usuario pidió un documento Word. "
            "Llama a create_document con el contenido ya analizado. No respondas solo en texto."
        )
    if intent == DeliverableIntent.UPDATE_FILE:
        return (
            "Aún no actualizaste el entregable. El usuario pidió modificar un archivo existente. "
            "Llama a update_html_report o update_document con el file_id correcto. "
            "No respondas solo en texto."
        )
    return ""
