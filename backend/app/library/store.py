"""Library store — read/write refs/library.json with FileLock."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from filelock import FileLock

from app.config.paths import ensure_dir

_log = logging.getLogger(__name__)

_LIBRARY_FILE = "refs/library.json"
_SOURCES_DIR = "sources"


class LibraryStore:
    def __init__(self, data_dir: Path | None = None):
        if data_dir is None:
            from app.config.paths import data_dir as get_data_dir
            data_dir = get_data_dir()
        self._dir = data_dir
        self._lib_path = data_dir / _LIBRARY_FILE

    def _load(self) -> dict:
        if not self._lib_path.exists():
            return {"version": 1, "next_display_index": 1, "items": {}, "keys": {}}
        return json.loads(self._lib_path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        ensure_dir(self._lib_path.parent)
        lock = FileLock(str(self._lib_path) + ".lock")
        with lock:
            tmp = self._lib_path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._lib_path)

    def get(self, item_id: str) -> dict | None:
        data = self._load()
        item = data.get("items", {}).get(item_id)
        return dict(item) if item else None

    def get_by_key(self, canonical_key: str) -> dict | None:
        data = self._load()
        item_id = data.get("keys", {}).get(canonical_key)
        if item_id:
            return self.get(item_id)
        return None

    def all_items(self) -> list[dict]:
        data = self._load()
        items = list(data.get("items", {}).values())
        items.sort(key=lambda x: x.get("display_index", 0))
        return items

    def put(self, item: dict) -> dict:
        data = self._load()
        item_id = item.get("id", "")
        data.setdefault("items", {})[item_id] = item
        self._rebuild_keys(data)
        self._save(data)
        return item

    def delete(self, item_id: str) -> bool:
        data = self._load()
        items = data.get("items", {})
        if item_id not in items:
            return False
        del items[item_id]
        self._rebuild_keys(data)
        self._save(data)
        return True

    def alloc_display_index(self) -> int:
        data = self._load()
        items = data.get("items", {})
        max_idx = max(
            (i.get("display_index", 0) for i in items.values()), default=0
        )
        current_next = data.get("next_display_index", 1)
        idx = max(max_idx + 1, current_next)
        data["next_display_index"] = idx + 1
        self._save(data)
        return idx

    def _rebuild_keys(self, data: dict) -> None:
        keys: dict[str, str] = {}
        for item_id, item in data.get("items", {}).items():
            doi = (item.get("doi") or "").strip().lower()
            if doi:
                keys[f"doi:{doi}"] = item_id
            from app.library.canonical import normalize_url
            url_norm = normalize_url(item.get("url", ""))
            if url_norm:
                keys[f"url:{url_norm}"] = item_id
        data["keys"] = keys
