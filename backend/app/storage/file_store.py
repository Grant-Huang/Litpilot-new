"""File-based session and artifact storage."""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from app.config.paths import ensure_dir

_log = logging.getLogger(__name__)


class FileStore:
    def __init__(self, data_dir: Path | None = None):
        self._dir = data_dir
        ensure_dir(self._dir)

    def _sessions_dir(self) -> Path:
        p = self._dir / "sessions"
        ensure_dir(p)
        return p

    def _session_path(self, session_id: str) -> Path:
        return self._sessions_dir() / session_id

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: Any) -> None:
        ensure_dir(path.parent)
        lock = FileLock(str(path) + ".lock")
        with lock:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)

    # ── Sessions ─────────────────────────────────────────────

    def list_sessions(self) -> list[dict]:
        sessions = []
        for d in sorted(self._sessions_dir().iterdir()):
            if d.is_dir():
                meta = self._read_json(d / "meta.json")
                if meta:
                    sessions.append(meta)
        pinned = [s for s in sessions if s.get("pinned")]
        unpinned = [s for s in sessions if not s.get("pinned")]
        return pinned + unpinned

    def create_session(self, title: str = "") -> dict:
        sid = secrets.token_hex(8)
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "id": sid,
            "title": title or "新会话",
            "created_at": now,
            "updated_at": now,
            "pinned": False,
            "user_turns": 0,
            "initial_query": "",
            "review_versions": [],
            "last_intent": None,
            "pending_gate": None,
            "resume_mode": None,
            "outline_mode": "lite",
        }
        sp = self._session_path(sid)
        ensure_dir(sp)
        self._write_json(sp / "meta.json", meta)
        return meta

    def get_meta(self, session_id: str) -> dict | None:
        path = self._session_path(session_id) / "meta.json"
        return self._read_json(path)

    def update_meta(self, session_id: str, **patch: Any) -> dict:
        path = self._session_path(session_id) / "meta.json"
        meta = self._read_json(path) or {}
        meta.update(patch)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_json(path, meta)
        return meta

    def delete_session(self, session_id: str) -> None:
        import shutil

        sp = self._session_path(session_id)
        if sp.exists():
            shutil.rmtree(sp, ignore_errors=True)

    # ── Messages ─────────────────────────────────────────────

    def read_messages(self, session_id: str) -> list[dict]:
        path = self._session_path(session_id) / "messages.jsonl"
        if not path.exists():
            return []
        msgs = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    msgs.append(json.loads(line))
        return msgs

    def append_message(self, session_id: str, msg: dict) -> dict:
        path = self._session_path(session_id) / "messages.jsonl"
        ensure_dir(path.parent)
        lock = FileLock(str(path) + ".lock")
        with lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return msg

    # ── Corpus ───────────────────────────────────────────────

    def read_corpus(self, session_id: str) -> dict:
        path = self._session_path(session_id) / "corpus.json"
        data = self._read_json(path)
        if data is None:
            return {"version": 2, "papers": []}
        return data

    def write_corpus(self, session_id: str, corpus: dict) -> None:
        path = self._session_path(session_id) / "corpus.json"
        self._write_json(path, corpus)

    # ── Outline ──────────────────────────────────────────────

    def read_outline(self, session_id: str) -> dict | None:
        path = self._session_path(session_id) / "outline.json"
        return self._read_json(path)

    def write_outline(self, session_id: str, outline: dict) -> None:
        path = self._session_path(session_id) / "outline.json"
        self._write_json(path, outline)

    # ── Review ───────────────────────────────────────────────

    def read_review(self, session_id: str, version: str = "latest") -> str:
        if version == "latest":
            path = self._session_path(session_id) / "review-latest.md"
        else:
            path = self._session_path(session_id) / f"review-{version}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_review(self, session_id: str, markdown: str) -> str:
        versions = self.list_review_versions(session_id)
        n = max((int(v[1:]) for v in versions), default=0) + 1
        version = f"v{n}"
        sp = self._session_path(session_id)
        ensure_dir(sp)
        (sp / f"review-{version}.md").write_text(markdown, encoding="utf-8")
        (sp / "review-latest.md").write_text(markdown, encoding="utf-8")
        self.update_meta(
            session_id,
            review_versions=versions + [version],
        )
        return version

    def list_review_versions(self, session_id: str) -> list[str]:
        sp = self._session_path(session_id)
        if not sp.exists():
            return []
        versions = []
        for f in sp.iterdir():
            name = f.name
            if name.startswith("review-v") and name.endswith(".md"):
                v = name[7:-3]  # "v1", "v2", etc.
                if v and len(v) > 1 and v[0] == "v" and v[1:].isdigit():
                    versions.append(v)
        versions.sort(key=lambda x: int(x[1:]))
        return versions

    # ── Matrix ───────────────────────────────────────────────

    def read_matrix(self, session_id: str) -> str:
        path = self._session_path(session_id) / "matrix-latest.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_matrix(self, session_id: str, markdown: str) -> None:
        path = self._session_path(session_id) / "matrix-latest.md"
        ensure_dir(path.parent)
        path.write_text(markdown, encoding="utf-8")

    # ── Ref-list (compat, used by citation_extractor) ─────────

    def read_ref_list(self) -> str:
        path = self._dir / "refs" / "ref-list.txt"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_ref_list(self, text: str) -> None:
        path = self._dir / "refs" / "ref-list.txt"
        ensure_dir(path.parent)
        path.write_text(text, encoding="utf-8")


_store_instance: FileStore | None = None


def get_store() -> FileStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = FileStore()
    return _store_instance
