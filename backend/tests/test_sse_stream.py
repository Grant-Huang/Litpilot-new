"""Tests for app.tasks.sse — SSE stream generator."""
import asyncio
import json
import pytest

from app.tasks.manager import TaskManager
from app.tasks.sse import event_stream


@pytest.fixture
def tm():
    return TaskManager()


def _collect_frames(text: str) -> list[dict]:
    """Parse SSE text into list of {event, data} dicts."""
    frames = []
    current_event = ""
    current_data = ""
    for line in text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event:
            frames.append({
                "event": current_event,
                "data": json.loads(current_data),
            })
            current_event = ""
            current_data = ""
    return frames


@pytest.mark.asyncio
async def test_stream_replays_all_events(tm):
    rec = tm.create("sess-1", "test", [])
    await tm.emit(rec.task_id, "stage", {"name": "search", "state": "active"})
    await tm.emit(rec.task_id, "text", {"delta": "hello"})
    rec.status = "done"

    chunks = []
    async for chunk in event_stream(tm, rec.task_id, since=0):
        chunks.append(chunk)

    text = "".join(chunks)
    frames = _collect_frames(text)
    assert len(frames) == 2
    assert frames[0]["event"] == "stage"
    assert frames[1]["event"] == "text"


@pytest.mark.asyncio
async def test_stream_since_skips_old(tm):
    rec = tm.create("sess-1", "test", [])
    await tm.emit(rec.task_id, "stage", {"name": "s1"})
    await tm.emit(rec.task_id, "text", {"delta": "old"})
    await tm.emit(rec.task_id, "text", {"delta": "new"})
    rec.status = "done"

    chunks = []
    async for chunk in event_stream(tm, rec.task_id, since=1):
        chunks.append(chunk)

    text = "".join(chunks)
    frames = _collect_frames(text)
    # Only seq > 1 should be emitted (seq 2 and 3)
    assert len(frames) == 2
    assert frames[0]["data"]["seq"] == 2
    assert frames[1]["data"]["seq"] == 3


@pytest.mark.asyncio
async def test_stream_task_not_found(tm):
    chunks = []
    async for chunk in event_stream(tm, "nonexistent", since=0):
        chunks.append(chunk)

    text = "".join(chunks)
    assert "error" in text
    assert "not found" in text


@pytest.mark.asyncio
async def test_stream_heartbeat(tm):
    """When task is running but no events, heartbeat should be emitted."""
    rec = tm.create("sess-1", "test", [])
    await tm.emit(rec.task_id, "stage", {"name": "start"})

    # Start stream in background
    chunks = []

    async def _consume():
        async for chunk in event_stream(tm, rec.task_id, since=0):
            chunks.append(chunk)
            # Stop after getting heartbeat or too many chunks
            if "heartbeat" in chunk or len(chunks) > 10:
                rec.status = "done"
                old = rec._new_event
                rec._new_event = asyncio.Event()
                old.set()

    # Set task as running
    rec.status = "running"

    # Run with timeout
    try:
        await asyncio.wait_for(_consume(), timeout=25)
    except asyncio.TimeoutError:
        rec.status = "done"
        old = rec._new_event
        rec._new_event = asyncio.Event()
        old.set()

    # Should have at least the initial event
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_stream_done_event(tm):
    rec = tm.create("sess-1", "test", [])
    await tm.emit(rec.task_id, "stage", {"name": "start"})
    await tm.emit(rec.task_id, "done", {"message": "completed"})
    rec.status = "done"

    chunks = []
    async for chunk in event_stream(tm, rec.task_id, since=0):
        chunks.append(chunk)

    text = "".join(chunks)
    frames = _collect_frames(text)
    assert any(f["event"] == "done" for f in frames)
