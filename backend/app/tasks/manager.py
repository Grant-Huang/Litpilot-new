"""TaskManager — in-memory task lifecycle, event buffering, execution."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class TaskRecord:
    task_id: str
    session_id: str
    message: str
    fetch_urls: list[str]
    status: str = "pending"
    events: list[dict] = field(default_factory=list)
    error: str | None = None
    result: dict | None = None
    _seq: int = 0
    _new_event: asyncio.Event = field(default_factory=asyncio.Event)
    _cancel: asyncio.Event = field(default_factory=asyncio.Event)


class TaskEmit:
    """Adapter: engine emit protocol → TaskManager event buffer."""

    def __init__(self, tm: TaskManager, task_id: str):
        self.tm = tm
        self.id = task_id

    async def stage(self, name: str, state: str) -> None:
        await self.tm.emit(self.id, "stage", {
            "name": name, "state": state,
        })

    async def text(self, delta: str, **kw: Any) -> None:
        await self.tm.emit(self.id, "text", {
            "delta": delta,
            "delivery": kw.get("delivery", "process"),
        })

    async def think(self, delta: str) -> None:
        await self.tm.emit(self.id, "think", {"delta": delta})

    async def artifact(
        self, id: str, lang: str, delta: str, **kw: Any
    ) -> None:
        await self.tm.emit(self.id, "artifact", {
            "id": id, "lang": lang, "delta": delta,
            "done": kw.get("done", False),
        })

    async def tool_call(self, name: str, args: dict) -> None:
        await self.tm.emit(self.id, "tool_call", {
            "name": name, "args": args,
        })

    async def tool_result(self, name: str, summary: str) -> None:
        await self.tm.emit(self.id, "tool_result", {
            "name": name, "summary": summary,
        })

    async def extension(self, name: str, data: dict) -> None:
        await self.tm.emit(self.id, "extension", {
            "name": name, "version": "1.0", "data": data,
        })

    def cancelled(self) -> bool:
        rec = self.tm.get(self.id)
        return rec._cancel.is_set() if rec else True


class TaskManager:
    """In-memory task management with event buffering."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    def create(
        self,
        session_id: str,
        message: str,
        fetch_urls: list[str],
    ) -> TaskRecord:
        task_id = uuid.uuid4().hex[:16]
        rec = TaskRecord(
            task_id=task_id,
            session_id=session_id,
            message=message,
            fetch_urls=fetch_urls,
        )
        self._tasks[task_id] = rec
        return rec

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    async def emit(
        self, task_id: str, event_type: str, data: dict
    ) -> None:
        rec = self.get(task_id)
        if rec is None:
            return
        rec._seq += 1
        envelope = {
            "event": event_type,
            "data": {**data, "seq": rec._seq},
        }
        rec.events.append(envelope)
        old_event = rec._new_event
        rec._new_event = asyncio.Event()
        old_event.set()

    async def run(self, task_id: str) -> None:
        """Execute run_turn in background, buffering events."""
        rec = self.get(task_id)
        if rec is None:
            return

        rec.status = "running"
        emit = TaskEmit(self, task_id)

        try:
            from app.agents.literature_turn import run_turn
            from app.storage.file_store import FileStore
            from app.config.paths import data_dir

            store = FileStore(data_dir=data_dir())
            result = await run_turn(
                session_id=rec.session_id,
                message=rec.message,
                fetch_urls=rec.fetch_urls,
                emit=emit,
                store=store,
            )
            rec.result = result
            await self.emit(task_id, "done", {
                "message": result.get("content", ""),
                "extras": result.get("extras", {}),
            })
            rec.status = "done"
        except Exception as e:
            _log.exception("Task %s failed", task_id)
            rec.error = str(e)
            await self.emit(task_id, "error", {"message": str(e)})
            rec.status = "error"

    def cancel(self, task_id: str) -> bool:
        rec = self.get(task_id)
        if rec is None:
            return False
        rec._cancel.set()
        rec.status = "cancelled"
        old = rec._new_event
        rec._new_event = asyncio.Event()
        old.set()
        return True
