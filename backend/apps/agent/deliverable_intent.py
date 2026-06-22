import re
from enum import Enum


class DeliverableIntent(str, Enum):
    CREATE_HTML = "create_html"
    CREATE_DOCX = "create_docx"
    UPDATE_FILE = "update_file"
    NONE = "none"


_UPDATE_VERB_RE = re.compile(
    r"\b("
    r"actualiza|actualizar|modifica|modificar|edita|editar|update|modify|edit|"
    r"transforma|transformar|convierte|convertir|rediseña|rediseñar|mejora|mejorar|"
    r"amplía|amplia|amplificar|agrega|añade|incorpora|cambia|adapta|refina|"
    r"extend|convert|transform|redesign|enhance|refine"
    r")\b",
    re.IGNORECASE,
)
_IMPLICIT_UPDATE_RE = re.compile(
    r"\b("
    r"transforma(?:lo|la|le|los|las)?|"
    r"convierte(?:lo|la|le|los|las)?|"
    r"conviértelo|"
    r"rediseña(?:lo|la|le|los|las)?|"
    r"hazlo|hazla|"
    r"mejora(?:lo|la|le|los|las)?"
    r")\b",
    re.IGNORECASE,
)
_IMPLICIT_FILE_REF_RE = re.compile(
    r"\b(este|ese|el|la|lo)\s+(dashboard|informe|reporte|artifact|archivo)\b|"
    r"\b(el mismo|existente|anterior|previo)\b",
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
    DeliverableIntent.CREATE_HTML: frozenset({"publish_html_artifact"}),
    DeliverableIntent.CREATE_DOCX: frozenset({"create_document"}),
    DeliverableIntent.UPDATE_FILE: frozenset({"publish_html_artifact", "update_document"}),
}


def _is_update_intent(text: str) -> bool:
    if _UPDATE_VERB_RE.search(text) and _FILE_REF_RE.search(text):
        return True
    if _IMPLICIT_UPDATE_RE.search(text):
        return True
    if _IMPLICIT_FILE_REF_RE.search(text) and _FILE_REF_RE.search(text):
        return True
    return False


def detect_deliverable_intent(user_message: str) -> DeliverableIntent:
    text = (user_message or "").strip()
    if not text:
        return DeliverableIntent.NONE

    if _is_update_intent(text):
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
**Publicar artifact** (`validate_html_artifact` + `publish_html_artifact`).
2. Consulta datos con SQL si hace falta; `show_data_table` y `show_chart` son pasos \
intermedios, no sustituyen el archivo.
3. Lee la skill `html-reports` y `GUIDELINES.md` antes de escribir HTML.
4. Escribe el HTML en `/workspace/artifacts/_draft.html` con `write_file` o `edit_file` \
(copia desde `/skills/html-reports/starter-dashboard.html` si aplica).
5. Llama `validate_html_artifact` y luego `publish_html_artifact` con `title` y `filename`.
6. No des por terminada la tarea hasta que `publish_html_artifact` devuelva `"ok": true`.
7. Tras publicar, no repitas el contenido en el chat."""

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

1. Planifica con `write_todos`. El último paso debe ser **Publicar artifact** con \
`hydrate_html_artifact` → editar en workspace → `validate_html_artifact` → \
`publish_html_artifact(file_id=...)` para HTML, o `update_document` para Word.
2. Usa el índice de archivos de la conversación o `list_conversation_files` para \
obtener el `file_id` correcto.
3. Para HTML: `hydrate_html_artifact(file_id)` carga el markup al workspace; edita con \
`read_file` / `grep` / `edit_file`; no crees otro archivo.
4. No publiques sin `file_id` cuando el usuario pidió modificar un artifact existente.
5. No des por terminada la tarea hasta que la tool de publicación/actualización devuelva `"ok": true`.
6. Tras actualizar, no repitas el contenido en el chat."""

    return ""


def format_deliverable_nudge(intent: DeliverableIntent) -> str:
    if intent == DeliverableIntent.CREATE_HTML:
        return (
            "Aún no generaste el entregable. El usuario pidió un informe o dashboard HTML. "
            "Escribe el HTML en el workspace, valida con validate_html_artifact y publica "
            "con publish_html_artifact. No respondas solo en texto."
        )
    if intent == DeliverableIntent.CREATE_DOCX:
        return (
            "Aún no generaste el entregable. El usuario pidió un documento Word. "
            "Llama a create_document con el contenido ya analizado. No respondas solo en texto."
        )
    if intent == DeliverableIntent.UPDATE_FILE:
        return (
            "Aún no actualizaste el entregable. El usuario pidió modificar un archivo existente. "
            "Para HTML: hydrate_html_artifact, edita en workspace, validate_html_artifact y "
            "publish_html_artifact con file_id. Para Word: update_document. "
            "No respondas solo en texto."
        )
    return ""
