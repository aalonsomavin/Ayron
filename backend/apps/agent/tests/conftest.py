import pytest
from langgraph.checkpoint.memory import MemorySaver

from apps.agent.checkpoint import reset_checkpointer, set_checkpointer


@pytest.fixture(autouse=True)
def memory_checkpointer():
    saver = MemorySaver()
    set_checkpointer(saver)
    yield saver
    reset_checkpointer()
