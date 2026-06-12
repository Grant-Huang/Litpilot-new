"""SSE stream generator — Meso v1.0 envelope, reconnection, heartbeat."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

_log = logging.getLogger(__name__)


def _frame(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def parse_frame(text: str) -> list[dict]:
    """Parse SSE text into frames (for testing)."""
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


async def event_stream(
    tm: Any,
    task_id: str,
    since: int = 0,
) -> Any:
    """Generate SSE frames for a task, supporting reconnection.

    Yields SSE formatted strings.
    """
    rec = tm.get(task_id)
    if rec is None:
        yield _frame("error", {"message": "task not found", "seq": 0})
        return

    # Phase 1: Replay buffered events with seq > since
    for env in rec.events:
        if env["data"]["seq"] > since:
            yield _frame(env["event"], env["data"])
            since = env["data"]["seq"]

    # Phase 2: Wait for new events while task is running
    while rec.status in ("running", "pending"):
        try:
            await asyncio.wait_for(rec._new_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            # Heartbeat to keep connection alive
            since += 1
            yield _frame("extension", {
                "name": "heartbeat",
                "version": "1.0",
                "data": {},
                "seq": since,
            })
            continue

        for env in rec.events:
            if env["data"]["seq"] > since:
                yield _frame(env["event"], env["data"])
                since = env["data"]["seq"]

    # Phase 3: Final catch-up after task completed
    for env in rec.events:
        if env["data"]["seq"] > since:
            yield _frame(env["event"], env["data"])
            since = env["data"]["seq"]
