"""Task API endpoints — POST create, GET status, GET stream, DELETE cancel."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.tasks.sse import event_stream

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    session_id: str
    message: str
    fetch_urls: list[str] = []


def _get_tm(request: Request) -> Any:
    return request.app.state.task_manager


@router.post("", status_code=201)
async def create_task(body: CreateTaskRequest, request: Request):
    """Create and start a new task."""
    tm = _get_tm(request)
    rec = tm.create(
        session_id=body.session_id,
        message=body.message,
        fetch_urls=body.fetch_urls,
    )
    # Start execution in background
    asyncio.create_task(tm.run(rec.task_id))
    return {"task_id": rec.task_id, "status": rec.status}


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request):
    """Get task status."""
    tm = _get_tm(request)
    rec = tm.get(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "task_id": rec.task_id,
        "status": rec.status,
        "error": rec.error,
    }


@router.get("/{task_id}/stream")
async def stream_task(
    task_id: str, request: Request, since: int = 0,
):
    """SSE stream for task events."""
    tm = _get_tm(request)
    return StreamingResponse(
        event_stream(tm, task_id, since=since),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.delete("/{task_id}")
async def cancel_task(task_id: str, request: Request):
    """Cancel a running task."""
    tm = _get_tm(request)
    rec = tm.get(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    tm.cancel(task_id)
    return {"task_id": task_id, "status": "cancelled"}
