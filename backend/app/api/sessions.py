"""REST API — session CRUD."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.storage.file_store import get_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions():
    store = get_store()
    sessions = store.list_sessions()
    return {"status": "success", "data": {"sessions": sessions}}


@router.post("", status_code=201)
async def create_session(body: dict | None = None):
    store = get_store()
    title = (body or {}).get("title", "")
    meta = store.create_session(title)
    return {"status": "success", "data": meta}


@router.get("/{session_id}")
async def get_session(session_id: str):
    store = get_store()
    meta = store.get_meta(session_id)
    if not meta:
        raise HTTPException(404, "Session not found")
    return {"status": "success", "data": meta}


@router.patch("/{session_id}")
async def update_session(session_id: str, body: dict):
    store = get_store()
    meta = store.get_meta(session_id)
    if not meta:
        raise HTTPException(404, "Session not found")
    allowed = {"title", "pinned"}
    patch = {k: v for k, v in body.items() if k in allowed}
    updated = store.update_meta(session_id, **patch)
    return {"status": "success", "data": updated}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    store = get_store()
    store.delete_session(session_id)
    return {"status": "success"}


# ── Messages ────────────────────────────────────────────


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    store = get_store()
    msgs = store.read_messages(session_id)
    return {"status": "success", "data": {"messages": msgs}}


@router.post("/{session_id}/messages", status_code=201)
async def append_message(session_id: str, body: dict):
    store = get_store()
    msg = store.append_message(session_id, body)
    return {"status": "success", "data": msg}


# ── Artifacts ───────────────────────────────────────────


@router.get("/{session_id}/review")
async def get_review(session_id: str):
    store = get_store()
    content = store.read_review(session_id)
    versions = store.list_review_versions(session_id)
    version = versions[-1] if versions else ""
    return {
        "status": "success",
        "data": {"version": version, "content": content},
    }


@router.get("/{session_id}/matrix")
async def get_matrix(session_id: str):
    store = get_store()
    content = store.read_matrix(session_id)
    return {"status": "success", "data": {"content": content}}


@router.get("/{session_id}/outline")
async def get_outline(session_id: str):
    store = get_store()
    outline = store.read_outline(session_id)
    return {"status": "success", "data": outline or {}}
