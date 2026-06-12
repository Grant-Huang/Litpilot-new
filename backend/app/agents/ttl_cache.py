"""TTL cache for search/fetch deduplication."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    def __init__(
        self,
        ttl_sec: float = 900,
        maxsize: int = 512,
        max_entries: int | None = None,
    ):
        self._ttl = ttl_sec
        # Support both maxsize and max_entries (ref code uses max_entries)
        self._maxsize = max_entries if max_entries is not None else maxsize
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, val = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return val

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            del self._store[key]
        self._store[key] = (time.monotonic(), value)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)


search_cache = TTLCache(ttl_sec=900)
fetch_cache = TTLCache(ttl_sec=3600)


def normalize_cache_key(
    provider: str, key: str, extra: dict | None = None
) -> str:
    blob = json.dumps(
        {"p": provider, "k": key, "e": extra or {}},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode()).hexdigest()
