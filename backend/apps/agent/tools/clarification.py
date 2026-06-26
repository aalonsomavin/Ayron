import json
import re
from typing import Annotated, Literal

from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.deliverable_intent import DeliverableIntent, detect_deliverable_intent
from apps.agent.tools.errors import build_tool_error_response

_SCOPE_SIGNAL_RE = re.compile(
    r"\b("
    r"este mes|mes actual|trimestre|q[1-4]|año|anual|ytd|"
    r"últimos?\s+\d+|ultimos?\s+\d+|histórico|historico|"
    r"por regi[oó]n|por producto|por canal|por instituci[oó]n|"
    r"desglose|solo\s+\w+|únicamente|unicamente|solamente"
    r")\b",
    re.IGNORECASE,
)


def needs_deliverable_clarification(user_message: str) -> bool:
    text = (user_message or "").strip()
    if not text:
        return False
    if _SCOPE_SIGNAL_RE.search(text):
        return False
    intent = detect_deliverable_intent(text)
    return intent != DeliverableIntent.NONE


_CLARIFICATION_DISPLAY_REGISTRY: dict[str, dict] = {}

MAX_QUESTIONS = 6
MAX_OPTIONS = 8
MAX_TITLE_LEN = 120
MAX_HINT_LEN = 200
MAX_SUBMIT_LABEL_LEN = 60
MAX_OPTION_LABEL_LEN = 80
MAX_TEXT_ANSWER_LEN = 500
OTHER_OPTION_ID = "other"
OTHER_OPTION_LABEL = "Otro:"
QUESTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
OPTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

AGENT_INSTRUCTION_AFTER_CLARIFICATION = (
    "Las preguntas de aclaración ya están visibles para el usuario. "
    "No escribas más texto ni invoques otras tools hasta recibir sus respuestas."
)


def pop_clarification_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _CLARIFICATION_DISPLAY_REGISTRY.pop(tool_call_id, None)


def _normalize_option(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Option {index + 1} must be an object with id and label")
    option_id = str(raw.get("id", "")).strip()
    label = str(raw.get("label", "")).strip()
    if not option_id or not OPTION_ID_PATTERN.match(option_id):
        raise ValueError(f"Option {index + 1} id must be a lowercase slug")
    if not label:
        raise ValueError(f"Option {index + 1} label cannot be empty")
    if len(label) > MAX_OPTION_LABEL_LEN:
        raise ValueError(f"Option {index + 1} label exceeds {MAX_OPTION_LABEL_LEN} characters")
    return {"id": option_id, "label": label}


def _inject_other_option(options: list[dict]) -> list[dict]:
    filtered = [option for option in options if option["id"] != OTHER_OPTION_ID]
    return [
        *filtered,
        {"id": OTHER_OPTION_ID, "label": OTHER_OPTION_LABEL},
    ]


def _normalize_question(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Question {index + 1} must be an object")

    question_id = str(raw.get("id", "")).strip()
    title = str(raw.get("title", "")).strip()
    hint = str(raw.get("hint", "")).strip()
    kind = str(raw.get("kind", "choice")).strip().lower()
    selection = str(raw.get("selection", "single")).strip().lower()
    optional = bool(raw.get("optional", False))
    options_raw = raw.get("options", [])

    if not question_id or not QUESTION_ID_PATTERN.match(question_id):
        raise ValueError(f"Question {index + 1} id must be a lowercase slug")
    if not title:
        raise ValueError(f"Question {index + 1} title cannot be empty")
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"Question {index + 1} title exceeds {MAX_TITLE_LEN} characters")
    if len(hint) > MAX_HINT_LEN:
        raise ValueError(f"Question {index + 1} hint exceeds {MAX_HINT_LEN} characters")
    if kind not in {"choice", "text"}:
        raise ValueError(f"Question {index + 1} kind must be choice or text")
    if selection not in {"single", "multiple"}:
        raise ValueError(f"Question {index + 1} selection must be single or multiple")

    if kind == "text":
        if options_raw:
            raise ValueError(f"Question {index + 1} text kind cannot include options")
        selection = "single"
        options = []
    else:
        if not isinstance(options_raw, list):
            raise ValueError(f"Question {index + 1} options must be a list")
        if len(options_raw) < 2:
            raise ValueError(f"Question {index + 1} requires at least 2 options")
        if len(options_raw) > MAX_OPTIONS:
            raise ValueError(f"Question {index + 1} exceeds {MAX_OPTIONS} options")
        options = [_normalize_option(item, opt_idx) for opt_idx, item in enumerate(options_raw)]
        option_ids = [item["id"] for item in options]
        if len(set(option_ids)) != len(option_ids):
            raise ValueError(f"Question {index + 1} option ids must be unique")
        options = _inject_other_option(options)

    return {
        "id": question_id,
        "title": title,
        "hint": hint,
        "kind": kind,
        "selection": selection,
        "optional": optional,
        "options": options,
    }


def validate_clarification_input(
    questions: list,
    allow_skip: bool = True,
    submit_label: str = "Analizar con esto",
) -> dict:
    if not isinstance(questions, list):
        raise ValueError("questions must be a list")
    if not questions:
        raise ValueError("At least one question is required")
    if len(questions) > MAX_QUESTIONS:
        raise ValueError(f"Maximum {MAX_QUESTIONS} questions allowed")

    normalized_questions = [
        _normalize_question(item, index) for index, item in enumerate(questions)
    ]
    question_ids = [item["id"] for item in normalized_questions]
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("Question ids must be unique")

    label = str(submit_label or "Analizar con esto").strip()
    if not label:
        label = "Analizar con esto"
    if len(label) > MAX_SUBMIT_LABEL_LEN:
        raise ValueError(f"submit_label exceeds {MAX_SUBMIT_LABEL_LEN} characters")

    return {
        "questions": normalized_questions,
        "allow_skip": bool(allow_skip),
        "submit_label": label,
        "submitted": False,
        "skipped": False,
        "answers": None,
    }


def format_clarification_payload(payload: dict) -> dict:
    return {
        "questions": payload.get("questions", []),
        "allow_skip": bool(payload.get("allow_skip", True)),
        "submit_label": payload.get("submit_label", "Analizar con esto"),
        "submitted": bool(payload.get("submitted", False)),
        "skipped": bool(payload.get("skipped", False)),
        "answers": payload.get("answers"),
    }


def _answer_labels(question: dict, answer: dict) -> list[str]:
    if question["kind"] == "text":
        text = str((answer or {}).get("text", "")).strip()
        return [text] if text else []

    selected = (answer or {}).get("selected") or []
    if not isinstance(selected, list):
        return []
    labels_by_id = {option["id"]: option["label"] for option in question["options"]}
    other_text = str((answer or {}).get("text", "")).strip()
    labels = []
    for item in selected:
        if item == OTHER_OPTION_ID:
            if other_text:
                labels.append(other_text)
        elif item in labels_by_id:
            labels.append(labels_by_id[item])
    return labels


def format_clarification_summary(payload: dict, answers: dict | None, skipped: bool) -> str:
    if skipped:
        return "Sin aclarar"

    parts = []
    for question in payload.get("questions", []):
        labels = _answer_labels(question, (answers or {}).get(question["id"]))
        if labels:
            parts.append(", ".join(labels))
    return " · ".join(parts) if parts else "Sin aclarar"


def format_clarification_tool_result(
    payload: dict,
    answers: dict | None,
    *,
    skipped: bool,
) -> str:
    if skipped:
        return (
            "El usuario prefirió continuar sin aclarar. "
            "Usa criterios razonables por defecto y sigue con la tarea."
        )

    lines = ["Respuestas del usuario:"]
    for question in payload.get("questions", []):
        qid = question["id"]
        answer = (answers or {}).get(qid, {})
        if question["kind"] == "text":
            text = str(answer.get("text", "")).strip()
            if text:
                if len(text) > MAX_TEXT_ANSWER_LEN:
                    text = text[: MAX_TEXT_ANSWER_LEN - 3] + "..."
                lines.append(f"- {question['title']}: {text}")
            elif not question.get("optional"):
                lines.append(f"- {question['title']}: (sin respuesta)")
            continue

        labels = _answer_labels(question, answer)
        if labels:
            lines.append(f"- {question['title']}: {', '.join(labels)}")
        elif not question.get("optional"):
            lines.append(f"- {question['title']}: (sin respuesta)")

    return "\n".join(lines)


def validate_step_answer(question: dict, answer: dict | None) -> dict:
    if question["kind"] == "text":
        text = str((answer or {}).get("text", "")).strip()
        if not text and not question.get("optional"):
            raise ValueError("Este paso requiere una respuesta")
        if len(text) > MAX_TEXT_ANSWER_LEN:
            raise ValueError(f"La respuesta no puede superar {MAX_TEXT_ANSWER_LEN} caracteres")
        return {"text": text}

    selected = (answer or {}).get("selected") or []
    if not isinstance(selected, list):
        selected = []
    selected = [str(item).strip() for item in selected if str(item).strip()]
    valid_ids = {option["id"] for option in question["options"]}
    selected = [item for item in selected if item in valid_ids]

    if question["selection"] == "single":
        if len(selected) > 1:
            selected = selected[:1]
        if not selected and not question.get("optional"):
            raise ValueError("Selecciona una opción para continuar")
    elif not selected and not question.get("optional"):
        raise ValueError("Selecciona al menos una opción para continuar")

    text = str((answer or {}).get("text", "")).strip()
    if OTHER_OPTION_ID in selected:
        if not text:
            raise ValueError("Especifica tu respuesta en Otro")
        if len(text) > MAX_TEXT_ANSWER_LEN:
            raise ValueError(f"La respuesta no puede superar {MAX_TEXT_ANSWER_LEN} caracteres")

    return {"selected": selected, "text": text if OTHER_OPTION_ID in selected else ""}


def merge_step_answer(answers: dict, question_id: str, step_answer: dict) -> dict:
    merged = dict(answers or {})
    merged[question_id] = step_answer
    return merged


def parse_answers_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_step_answer_from_post(question: dict, post_data) -> dict:
    qid = question["id"]
    if question["kind"] == "text":
        return {"text": str(post_data.get(f"answer_{qid}", "")).strip()}

    other_text = str(post_data.get(f"answer_{qid}_other_text", "")).strip()
    if question["selection"] == "single":
        value = str(post_data.get(f"answer_{qid}", "")).strip()
        return {"selected": [value] if value else [], "text": other_text}

    values = post_data.getlist(f"answer_{qid}")
    return {
        "selected": [str(item).strip() for item in values if str(item).strip()],
        "text": other_text,
    }


@tool
def ask_clarification(
    questions: list[dict],
    allow_skip: bool = True,
    submit_label: str = "Analizar con esto",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Ask the user clarifying questions before proceeding when important details are missing or ambiguous.

    Use when missing or ambiguous details would materially change how you complete the task
    (scope, filters, audience, format, exclusions, priorities, etc.) and you cannot infer
    reasonable defaults. Formulate only the questions you need (1-6), tailored to the request.
    Do not use for simple factual questions answerable from data alone, or when reasonable
    defaults are enough.

    Pass 1-6 questions. Each question needs a stable lowercase id, title, and either:
    - kind=choice with selection single|multiple and at least 2 options (id + label), or
    - kind=text for free-text input (set optional=true if the note is not required).

    Choice questions automatically include an "Otro:" option for free-text input; do not add it.

    After calling this tool, stop — do not write more text or call other tools.
    """
    try:
        payload = validate_clarification_input(questions, allow_skip, submit_label)
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    if tool_call_id:
        _CLARIFICATION_DISPLAY_REGISTRY[tool_call_id] = payload

    return AGENT_INSTRUCTION_AFTER_CLARIFICATION
