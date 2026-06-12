"""REST API — library CRUD."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.library.store import LibraryStore

router = APIRouter(prefix="/api/library", tags=["library"])


def _store() -> LibraryStore:
    return LibraryStore()


@router.get("")
async def list_library(search: str = "", tags: str = ""):
    store = _store()
    items = store.all_items()
    if search:
        s = search.lower()
        items = [
            it for it in items
            if s in (it.get("title", "")).lower()
            or s in (it.get("authors", "")).lower()
            or s in (it.get("doi", "")).lower()
        ]
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if tag_list:
            items = [
                it for it in items
                if any(t.lower() in [tg.lower() for tg in it.get("tags", [])]
                       for t in tag_list)
            ]
    return {"status": "success", "data": {"items": items}}


@router.get("/{key:path}")
async def get_library_item(key: str):
    store = _store()
    item = store.get_by_key(key) or store.get(key)
    if not item:
        raise HTTPException(404, "Item not found")
    return {"status": "success", "data": item}


@router.patch("/{key:path}")
async def update_library_item(key: str, body: dict):
    store = _store()
    item = store.get_by_key(key) or store.get(key)
    if not item:
        raise HTTPException(404, "Item not found")
    allowed = {"doi", "tags", "title", "authors"}
    patch = {k: v for k, v in body.items() if k in allowed}
    if "tags" in patch and isinstance(patch["tags"], str):
        patch["tags"] = [t.strip() for t in patch["tags"].split(",") if t.strip()]
    item.update(patch)
    store.put(item)
    return {"status": "success", "data": item}


@router.post("/{key:path}/refresh")
async def refresh_metadata(key: str):
    store = _store()
    item = store.get_by_key(key) or store.get(key)
    if not item:
        raise HTTPException(404, "Item not found")
    return {"status": "success", "data": item}
