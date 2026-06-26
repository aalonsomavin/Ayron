from langchain_core.messages import AIMessage

from apps.agent.clarification_interrupt import (
    find_clarification_tool_call,
    has_clarification_interrupt,
)


class _FakeInterrupt:
    def __init__(self, value):
        self.value = value


class _FakeState:
    def __init__(self, interrupts=(), values=None):
        self.interrupts = interrupts
        self.values = values or {}


def test_has_clarification_interrupt_detects_hitl_request():
    state = _FakeState(
        interrupts=[
            _FakeInterrupt(
                {
                    "action_requests": [
                        {"name": "ask_clarification", "args": {"questions": []}},
                    ],
                    "review_configs": [],
                }
            )
        ]
    )

    assert has_clarification_interrupt(state) is True


def test_has_clarification_interrupt_ignores_other_tools():
    state = _FakeState(
        interrupts=[
            _FakeInterrupt(
                {
                    "action_requests": [{"name": "run_sql_query", "args": {}}],
                    "review_configs": [],
                }
            )
        ]
    )

    assert has_clarification_interrupt(state) is False


def test_find_clarification_tool_call_from_messages():
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "ask_clarification",
                    "args": {
                        "questions": [
                            {
                                "id": "periodo",
                                "title": "Periodo",
                                "kind": "choice",
                                "selection": "single",
                                "options": [
                                    {"id": "q1", "label": "Q1"},
                                    {"id": "q2", "label": "Q2"},
                                ],
                            }
                        ]
                    },
                }
            ],
        )
    ]

    match = find_clarification_tool_call(messages)

    assert match == ("call_1", messages[0].tool_calls[0]["args"])
