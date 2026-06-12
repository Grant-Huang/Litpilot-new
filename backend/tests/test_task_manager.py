"""Tests for app.tasks.manager — TaskManager."""
import pytest
from unittest.mock import patch

from app.tasks.manager import TaskManager, TaskEmit


@pytest.fixture
def tm():
    return TaskManager()


def test_create_task(tm):
    rec = tm.create("sess-1", "AI review", [])
    assert rec.task_id
    assert rec.session_id == "sess-1"
    assert rec.message == "AI review"
    assert rec.status == "pending"
    assert rec.events == []


def test_get_task(tm):
    rec = tm.create("sess-1", "test", [])
    found = tm.get(rec.task_id)
    assert found is rec
    assert tm.get("nonexistent") is None


@pytest.mark.asyncio
async def test_emit_increments_seq(tm):
    rec = tm.create("sess-1", "test", [])
    await tm.emit(rec.task_id, "stage", {"name": "search", "state": "active"})
    await tm.emit(rec.task_id, "text", {"delta": "hello", "delivery": "process"})
    assert len(rec.events) == 2
    assert rec.events[0]["data"]["seq"] == 1
    assert rec.events[1]["data"]["seq"] == 2


@pytest.mark.asyncio
async def test_run_marks_done(tm):
    rec = tm.create("sess-1", "test", [])

    async def fake_run_turn(**kw):
        await kw["emit"].text("done", delivery="chat")
        return {"content": "ok", "extras": {}}

    with patch(
        "app.agents.literature_turn.run_turn", side_effect=fake_run_turn,
    ), patch("app.storage.file_store.FileStore"):
        await tm.run(rec.task_id)

    assert rec.status == "done"
    assert any(e["event"] == "done" for e in rec.events)


@pytest.mark.asyncio
async def test_run_marks_error(tm):
    rec = tm.create("sess-1", "test", [])

    async def fake_run_turn(**kw):
        raise ValueError("LLM failed")

    with patch(
        "app.agents.literature_turn.run_turn", side_effect=fake_run_turn,
    ), patch("app.storage.file_store.FileStore"):
        await tm.run(rec.task_id)

    assert rec.status == "error"
    assert rec.error is not None
    assert "LLM failed" in rec.error


def test_cancel_task(tm):
    rec = tm.create("sess-1", "test", [])
    assert tm.cancel(rec.task_id) is True
    assert rec.status == "cancelled"
    assert tm.cancel("nonexistent") is False


@pytest.mark.asyncio
async def test_task_emit_adapter(tm):
    rec = tm.create("sess-1", "test", [])
    emit = TaskEmit(tm, rec.task_id)

    await emit.stage("search", "active")
    await emit.text("hello", delivery="process")
    await emit.think("thinking...")
    await emit.artifact("review", "markdown", "# Review", done=False)
    await emit.artifact("review", "markdown", "", done=True)
    await emit.tool_call("web_search", {"query": "AI"})
    await emit.tool_result("web_search", "Found 5")
    await emit.extension("literature_intent", {"intent": "new_topic"})

    assert len(rec.events) == 8
    assert rec.events[0]["event"] == "stage"
    assert rec.events[0]["data"]["name"] == "search"
    assert rec.events[1]["event"] == "text"
    assert rec.events[2]["event"] == "think"
    assert rec.events[3]["event"] == "artifact"
    assert rec.events[5]["event"] == "tool_call"
    assert rec.events[6]["event"] == "tool_result"
    assert rec.events[7]["event"] == "extension"


@pytest.mark.asyncio
async def test_emit_sets_event_flag(tm):
    """emit should set _new_event so SSE consumers wake up."""
    rec = tm.create("sess-1", "test", [])
    old_event = rec._new_event
    await tm.emit(rec.task_id, "stage", {"name": "x", "state": "y"})
    assert old_event.is_set()
    # New event should be created for next wait
    assert rec._new_event is not old_event
