import pytest
from django.http import QueryDict

from apps.agent.tools.clarification import (
    OTHER_OPTION_ID,
    OTHER_OPTION_LABEL,
    ask_clarification,
    format_clarification_summary,
    format_clarification_tool_result,
    parse_step_answer_from_post,
    validate_clarification_input,
    validate_step_answer,
)


def test_validate_clarification_input_accepts_valid_questions():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            },
            {
                "id": "notas",
                "title": "Notas adicionales",
                "kind": "text",
                "optional": True,
            },
        ]
    )
    assert len(payload["questions"]) == 2
    assert payload["allow_skip"] is True
    periodo_options = payload["questions"][0]["options"]
    assert periodo_options[-1]["id"] == OTHER_OPTION_ID
    assert periodo_options[-1]["label"] == OTHER_OPTION_LABEL


def test_validate_clarification_input_replaces_agent_other_option():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "other", "label": "Custom other"},
                ],
            }
        ]
    )
    options = payload["questions"][0]["options"]
    assert options[-1] == {"id": OTHER_OPTION_ID, "label": OTHER_OPTION_LABEL}
    assert sum(1 for option in options if option["id"] == OTHER_OPTION_ID) == 1


def test_validate_clarification_input_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="unique"):
        validate_clarification_input(
            [
                {
                    "id": "periodo",
                    "title": "Periodo",
                    "kind": "choice",
                    "selection": "single",
                    "options": [
                        {"id": "a", "label": "A"},
                        {"id": "b", "label": "B"},
                    ],
                },
                {
                    "id": "periodo",
                    "title": "Otro",
                    "kind": "choice",
                    "selection": "single",
                    "options": [
                        {"id": "c", "label": "C"},
                        {"id": "d", "label": "D"},
                    ],
                },
            ]
        )


def test_ask_clarification_returns_instruction():
    result = ask_clarification.func(
        questions=[
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ],
        tool_call_id="call-123",
    )

    assert "respuestas" in result.lower()


def test_format_clarification_tool_result_skip():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )
    result = format_clarification_tool_result(payload, None, skipped=True)
    assert "continuar sin aclarar" in result


def test_format_clarification_tool_result_with_answers():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )
    result = format_clarification_tool_result(
        payload,
        {"periodo": {"selected": ["year"]}},
        skipped=False,
    )
    assert "Periodo a analizar: Este año" in result


def test_format_clarification_summary():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )
    summary = format_clarification_summary(
        payload,
        {"periodo": {"selected": ["year"]}},
        skipped=False,
    )
    assert summary == "Este año"


def test_validate_step_answer_requires_single_selection():
    question = {
        "id": "periodo",
        "kind": "choice",
        "selection": "single",
        "optional": False,
        "options": [{"id": "last_30d", "label": "30d"}, {"id": "year", "label": "year"}],
    }
    with pytest.raises(ValueError):
        validate_step_answer(question, {"selected": []})


def test_validate_step_answer_requires_other_text():
    question = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )["questions"][0]
    with pytest.raises(ValueError, match="Otro"):
        validate_step_answer(question, {"selected": [OTHER_OPTION_ID], "text": ""})


def test_validate_step_answer_accepts_other_with_text():
    question = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )["questions"][0]
    answer = validate_step_answer(
        question,
        {"selected": [OTHER_OPTION_ID], "text": "Q3 2024"},
    )
    assert answer == {"selected": [OTHER_OPTION_ID], "text": "Q3 2024"}


def test_format_clarification_tool_result_with_other_answer():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )
    result = format_clarification_tool_result(
        payload,
        {"periodo": {"selected": [OTHER_OPTION_ID], "text": "Q3 2024"}},
        skipped=False,
    )
    assert "Periodo a analizar: Q3 2024" in result


def test_format_clarification_summary_with_other_answer():
    payload = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )
    summary = format_clarification_summary(
        payload,
        {"periodo": {"selected": [OTHER_OPTION_ID], "text": "Q3 2024"}},
        skipped=False,
    )
    assert summary == "Q3 2024"


def test_format_clarification_summary_with_multiple_including_other():
    payload = validate_clarification_input(
        [
            {
                "id": "canales",
                "title": "Canales",
                "kind": "choice",
                "selection": "multiple",
                "options": [
                    {"id": "online", "label": "Online"},
                    {"id": "retail", "label": "Retail"},
                ],
            }
        ]
    )
    summary = format_clarification_summary(
        payload,
        {
            "canales": {
                "selected": ["online", OTHER_OPTION_ID],
                "text": "solo marketplace",
            }
        },
        skipped=False,
    )
    assert summary == "Online, solo marketplace"


def test_parse_step_answer_from_post_with_other_text():
    question = validate_clarification_input(
        [
            {
                "id": "periodo",
                "title": "Periodo a analizar",
                "kind": "choice",
                "selection": "single",
                "options": [
                    {"id": "last_30d", "label": "Últimos 30 días"},
                    {"id": "year", "label": "Este año"},
                ],
            }
        ]
    )["questions"][0]
    post_data = QueryDict(mutable=True)
    post_data["answer_periodo"] = OTHER_OPTION_ID
    post_data["answer_periodo_other_text"] = "Q3 2024"
    answer = parse_step_answer_from_post(question, post_data)
    assert answer == {"selected": [OTHER_OPTION_ID], "text": "Q3 2024"}


def test_needs_deliverable_clarification_for_dashboard_without_scope():
    from apps.agent.tools.clarification import needs_deliverable_clarification

    assert needs_deliverable_clarification("Genera un dashboard de ventas") is True
    assert needs_deliverable_clarification("Genera un dashboard de ventas del Q2 2025") is False
    assert needs_deliverable_clarification("Cuánto vendimos este mes") is False
