"""Post-run export sync — ref-list.txt and index.json."""
from __future__ import annotations

import json
import logging

from app.config.paths import ensure_dir
from app.library.store import LibraryStore

_log = logging.getLogger(__name__)


def _sync_exports(lib: LibraryStore) -> None:
    """Sync ref-list.txt and index.json after library changes."""
    items = lib.all_items()
    if not items:
        return

    refs_dir = lib._dir / "refs"
    ensure_dir(refs_dir)

    # ref-list.txt
    lines = []
    for item in items:
        apa = (item.get("citations") or {}).get("apa", "")
        if apa:
            lines.append(apa)
    ref_path = refs_dir / "ref-list.txt"
    ref_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # index.json (legacy)
    index = [
        {
            "id": item.get("id"),
            "display_index": item.get("display_index"),
            "title": item.get("title"),
            "url": item.get("url"),
            "doi": item.get("doi"),
        }
        for item in items
    ]
    idx_path = refs_dir / "index.json"
    idx_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
