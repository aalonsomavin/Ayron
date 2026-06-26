import pytest

from apps.agent.tools.clarification import (
    ask_clarification,
    format_clarification_summary,
    format_clarification_tool_result,
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


def test_needs_deliverable_clarification_for_dashboard_without_scope():
    from apps.agent.tools.clarification import needs_deliverable_clarification

    assert needs_deliverable_clarification("Genera un dashboard de ventas") is True
    assert needs_deliverable_clarification("Genera un dashboard de ventas del Q2 2025") is False
    assert needs_deliverable_clarification("Cuánto vendimos este mes") is False
