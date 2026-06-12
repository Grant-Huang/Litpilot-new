"""Literature turn finalize — persist review, matrix, corpus, outline, meta."""
from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


async def finalize_turn(
    *,
    session_id: str,
    store: Any,
    intent: str,
    review_text: str = "",
    matrix_text: str = "",
    corpus: dict[str, Any] | None = None,
    outline: dict[str, Any] | None = None,
    citations: list[str] | None = None,
) -> dict[str, Any]:
    """Persist all artifacts from a turn.

    Returns a summary dict with saved versions.
    """
    saved: dict[str, Any] = {"intent": intent}

    # Save corpus
    if corpus is not None:
        store.write_corpus(session_id, corpus)
        saved["corpus_version"] = corpus.get("version", 0)

    # Save outline
    if outline is not None:
        store.write_outline(session_id, outline)
        saved["has_outline"] = True

    # Save review (only for new_topic / append_urls)
    if intent in ("new_topic", "append_urls") and review_text:
        version = store.write_review(session_id, review_text)
        saved["review_version"] = version

    # Save matrix
    if matrix_text:
        store.write_matrix(session_id, matrix_text)
        saved["has_matrix"] = True

    # Update meta
    meta_updates: dict[str, Any] = {}
    if intent in ("new_topic", "append_urls"):
        meta_updates["has_review"] = bool(review_text)
        meta_updates["has_matrix"] = bool(matrix_text)
    if corpus:
        meta_updates["paper_count"] = len(corpus.get("papers", []))
    if meta_updates:
        store.update_meta(session_id, **meta_updates)

    _log.info(
        "finalize_turn session=%s intent=%s saved=%s",
        session_id[:8], intent, list(saved.keys()),
    )

    return saved
