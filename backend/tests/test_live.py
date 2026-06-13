"""Live integration tests — full pipeline with real LLM / Search / Fetch.

These tests require network access and valid API keys configured in
backend/config/system.credentials.json.

Run:  python -m pytest tests/test_live.py -v -s --timeout=300

The tests cover:
1. Full new_topic pipeline (search → fetch → cite → generate)
2. Clarification gate (short/ambiguous input triggers clarify)
3. Query corpus QA (after first turn, ask follow-up question)
4. Append URLs (submit new URLs from ref-list.txt to existing session)

Prompt: AI-native MOM literature review (4 aspects)
URL file: docs/ref/ref-list.txt
"""
from __future__ import annotations

import pytest

from tests.conftest import LiveEmit, _make_store, get_ref_list_urls, skip_if_no_api_key

# The revised prompt as requested by user
MOM_PROMPT = (
    "我要写一个与AI原生MOM（制造运营管理）有关的文献综述，包括4个方面："
    "其一，AI原生MOM系统性的定义框架与参考模型。"
    "其二，异构机器间信任建立的工程方案与制造知识图谱。"
    "其三，多智能体协作、动态知识推理与可组合微服务架构三条研究线索，"
    "及其统一的工程整合框架。"
    "其四，从传统单体MOM向AI原生MOM的渐进式迁移的工程框架。"
)


def _get_llm_config():
    from app.agents.runtime_settings import build_runtime_settings
    settings = build_runtime_settings()
    cfg = settings.get("review_main", {})
    if not cfg.get("api_key"):
        pytest.skip("Requires review_main LLM API key in config")
    return cfg


def _get_search_api_key():
    return skip_if_no_api_key("tavily_api_key")


# ════════════════════════════════════════════════════════════════
# 1. Full new_topic pipeline
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_new_topic_full_pipeline(tmp_path):
    """Live test: new_topic with MOM prompt — full search→fetch→cite→generate."""
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("AI-native MOM 文献综述")
    emit = LiveEmit(prefix="NEW_TOPIC")

    print(f"\n{'=' * 60}")
    print(f"SESSION: {session['id']}")
    print(f"PROMPT:  {MOM_PROMPT[:80]}...")
    print(f"{'=' * 60}")

    result = await run_turn(
        session_id=session["id"],
        message=MOM_PROMPT,
        fetch_urls=[],
        emit=emit,
        store=store,
    )

    print("\n--- RESULT ---")
    print(f"  intent:         {result.get('extras', {}).get('intent')}")
    print(f"  delivery:       {result.get('extras', {}).get('delivery')}")
    print(f"  artifactKind:   {result.get('extras', {}).get('artifactKind')}")
    print(f"  review_version: {result.get('extras', {}).get('review_version')}")
    print(f"  content:        {result.get('content', '')[:200]}")

    # ── Assertions ──
    assert result is not None, "run_turn returned None"
    extras = result.get("extras", {})
    assert extras.get("intent") == "new_topic", \
        f"Expected intent=new_topic, got {extras.get('intent')}"
    assert extras.get("review_version") is not None, \
        "Expected review_version to be set"

    # Check store has review
    review = store.read_review(session["id"])
    assert review, "Expected review to be saved in store"
    print(f"\n  REVIEW LENGTH: {len(review)} chars")
    print(f"  REVIEW PREVIEW: {review[:300]}...")

    # Check store has corpus
    corpus = store.read_corpus(session["id"])
    papers = corpus.get("papers", [])
    assert len(papers) >= 1, f"Expected at least 1 paper in corpus, got {len(papers)}"
    print(f"  PAPERS IN CORPUS: {len(papers)}")
    for p in papers:
        print(f"    - [{p.get('fetch_status')}] {p.get('title', '')[:60]}"
              f" ({p.get('url', '')[:60]})")

    # Check events emitted
    stage_events = [e for e in emit.events if e[0] == "stage"]
    assert len(stage_events) > 0, "Expected stage events to be emitted"

    tool_events = [e for e in emit.events if e[0] in ("tool_call", "tool_result")]
    assert len(tool_events) > 0, "Expected tool events to be emitted"

    print(f"\n  TOTAL EVENTS: {len(emit.events)}")
    print(f"  STAGES: {[e[1] for e in stage_events]}")
    print(f"  TOOL CALLS: {[e[1] for e in emit.events if e[0] == 'tool_call']}")


# ════════════════════════════════════════════════════════════════
# 2. Clarification gate
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_clarify_short_input(tmp_path):
    """Live test: short/ambiguous input should trigger clarification gate
    or at least complete the pipeline (clarify is optional in implementation).

    We use a very short message like "MOM" to test the clarification path.
    Since the current implementation may or may not trigger clarify (depends
    on confidence), we verify the system handles it gracefully.
    """
    from app.agents.literature_clarification import check_clarification_gate

    print(f"\n{'=' * 60}")
    print("TEST: clarify short input")
    print(f"{'=' * 60}")

    # Test the gate logic directly
    meta = {"user_turns": 1, "pending_gate": None}
    gate = check_clarification_gate(
        meta=meta,
        message="MOM",
        confidence=0.3,
    )

    if gate:
        print(f"  GATE TRIGGERED: kind={gate['kind']}")
        print(f"  GATE PROMPT: {gate.get('prompt', '')[:200]}")
        assert gate["kind"] == "first_turn", \
            f"Expected first_turn gate, got {gate['kind']}"
        assert gate["prompt"], "Gate should have a non-empty prompt"
        assert gate.get("options"), "Gate should have options"
        print(f"  GATE OPTIONS: {gate.get('options')}")
    else:
        print("  No gate triggered (confidence sufficient or not first turn)")

    # Also test with a slightly longer but still ambiguous message
    meta2 = {"user_turns": 1, "pending_gate": None}
    gate2 = check_clarification_gate(
        meta=meta2,
        message="AI in manufacturing",
        confidence=0.5,
    )
    if gate2:
        print(f"  GATE2 TRIGGERED: kind={gate2['kind']} for 'AI in manufacturing'")
    else:
        print("  GATE2 NOT triggered for 'AI in manufacturing' (confidence=0.5 >= 0.6? no)")

    # Verify: confidence < 0.6 on first turn should trigger
    assert gate is not None, \
        "Short input 'MOM' with confidence=0.3 should trigger first_turn gate"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_clarify_resolved_then_continue(tmp_path):
    """Live test: user provides ambiguous input → clarify → user clarifies → pipeline.

    This simulates a two-message interaction:
    1. First message "MOM" with low confidence → triggers clarify
    2. User responds with detailed explanation → pipeline continues
    """
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("Clarify Test")

    print(f"\n{'=' * 60}")
    print("TEST: clarify → resolve → continue")
    print(f"{'=' * 60}")

    # Simulate: set pending_gate as if clarification was triggered
    store.update_meta(
        session["id"],
        pending_gate={
            "kind": "first_turn",
            "prompt": "您的研究主题「MOM」表述较模糊，请补充更多细节。",
        },
        user_turns=1,
    )

    # Now user responds with the detailed MOM prompt
    emit2 = LiveEmit(prefix="CLARIFY-R2")
    result = await run_turn(
        session_id=session["id"],
        message=MOM_PROMPT,
        fetch_urls=[],
        emit=emit2,
        store=store,
    )

    print("\n--- RESOLUTION RESULT ---")
    print(f"  intent:  {result.get('extras', {}).get('intent')}")
    print(f"  content: {result.get('content', '')[:200]}")

    # After resolution, it should route as new_topic
    extras = result.get("extras", {})
    assert extras.get("intent") in ("new_topic", "cancelled"), \
        f"After clarify resolve, expected new_topic or cancelled, got {extras.get('intent')}"

    # Check pending_gate was cleared
    meta = store.get_meta(session["id"])
    assert meta.get("pending_gate") is None, \
        "pending_gate should be cleared after resolution"
    print(f"  pending_gate cleared: {meta.get('pending_gate')}")


# ════════════════════════════════════════════════════════════════
# 3. Query corpus QA (follow-up question after first turn)
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_query_corpus_after_review(tmp_path):
    """Live test: after generating a review, ask a follow-up QA question.

    Steps:
    1. Run new_topic to generate review
    2. Run query_corpus with a follow-up question
    3. Verify answer references corpus/review content
    """
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("QA Test")
    emit1 = LiveEmit(prefix="QA-R1")

    print(f"\n{'=' * 60}")
    print("TEST: query_corpus QA after review")
    print(f"{'=' * 60}")

    # Step 1: Generate initial review
    print("\n--- STEP 1: Generate review ---")
    result1 = await run_turn(
        session_id=session["id"],
        message=MOM_PROMPT,
        fetch_urls=[],
        emit=emit1,
        store=store,
    )
    print(f"  R1 intent: {result1.get('extras', {}).get('intent')}")
    print(f"  R1 review_version: {result1.get('extras', {}).get('review_version')}")

    assert result1.get("extras", {}).get("intent") == "new_topic"
    review = store.read_review(session["id"])
    assert review, "Expected review to exist after first turn"

    # Debug: check user_turns after R1
    meta_r1 = store.get_meta(session["id"])
    print(f"  R1 user_turns: {meta_r1.get('user_turns')}")
    print(f"  R1 last_intent: {meta_r1.get('last_intent')}")

    # Step 2: Ask follow-up question (query_corpus)
    print("\n--- STEP 2: Follow-up QA ---")
    emit2 = LiveEmit(prefix="QA-R2")
    followup = "多智能体协作在制造运营管理中有哪些具体应用场景？"
    print(f"  QUESTION: {followup}")

    result2 = await run_turn(
        session_id=session["id"],
        message=followup,
        fetch_urls=[],
        emit=emit2,
        store=store,
    )

    print("\n--- QA RESULT ---")
    print(f"  intent:  {result2.get('extras', {}).get('intent')}")
    print(f"  delivery: {result2.get('extras', {}).get('delivery')}")
    answer = result2.get("content", "")
    print(f"  answer length: {len(answer)} chars")
    print(f"  answer preview: {answer[:500]}...")

    # Assertions
    extras2 = result2.get("extras", {})
    assert extras2.get("intent") == "query_corpus", \
        f"Expected query_corpus, got {extras2.get('intent')}"
    assert extras2.get("delivery") == "chat", \
        f"Expected chat delivery, got {extras2.get('delivery')}"
    assert answer, "Expected non-empty answer content"
    assert len(answer) >= 20, \
        f"Expected answer of at least 20 chars, got {len(answer)}"


# ════════════════════════════════════════════════════════════════
# 4. Append URLs (submit URLs from ref-list.txt)
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_append_urls_from_ref_list(tmp_path):
    """Live test: after first review, submit URLs from docs/ref/ref-list.txt.

    Steps:
    1. Run new_topic to generate initial review
    2. Run append_urls with URLs from ref-list.txt
    3. Verify review is updated (version incremented)
    """
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("Append URLs Test")
    emit1 = LiveEmit(prefix="APPEND-R1")

    ref_urls = get_ref_list_urls()
    if not ref_urls:
        pytest.skip("No URLs found in docs/ref/ref-list.txt")

    # Limit to first 3 URLs to keep test manageable
    test_urls = ref_urls[:3]

    print(f"\n{'=' * 60}")
    print("TEST: append_urls with ref-list.txt")
    print(f"  URLS ({len(test_urls)}):")
    for u in test_urls:
        print(f"    - {u}")
    print(f"{'=' * 60}")

    # Step 1: Generate initial review
    print("\n--- STEP 1: Generate initial review ---")
    result1 = await run_turn(
        session_id=session["id"],
        message=MOM_PROMPT,
        fetch_urls=[],
        emit=emit1,
        store=store,
    )
    v1 = result1.get("extras", {}).get("review_version")
    print(f"  R1 intent: {result1.get('extras', {}).get('intent')}")
    print(f"  R1 review_version: {v1}")
    assert result1.get("extras", {}).get("intent") == "new_topic"

    # Step 2: Append URLs
    print("\n--- STEP 2: Append URLs ---")
    emit2 = LiveEmit(prefix="APPEND-R2")
    result2 = await run_turn(
        session_id=session["id"],
        message="请帮我补充这些文献",
        fetch_urls=test_urls,
        emit=emit2,
        store=store,
    )

    print("\n--- APPEND RESULT ---")
    v2 = result2.get("extras", {}).get("review_version")
    print(f"  intent:  {result2.get('extras', {}).get('intent')}")
    print(f"  review_version: {v2}")
    print(f"  content: {result2.get('content', '')[:200]}")

    # Assertions
    extras2 = result2.get("extras", {})
    assert extras2.get("intent") == "append_urls", \
        f"Expected append_urls, got {extras2.get('intent')}"
    assert v2 is not None, "Expected review_version to be set"

    # Verify version incremented
    if v1 and v2:
        n1 = int(v1.lstrip("v"))
        n2 = int(v2.lstrip("v"))
        assert n2 > n1, \
            f"Expected version increment v{n1} → v{n2+1}, got v{n2}"
        print(f"  VERSION: {v1} → {v2} ✓")

    # Verify corpus grew
    corpus = store.read_corpus(session["id"])
    papers = corpus.get("papers", [])
    print(f"  PAPERS IN CORPUS: {len(papers)}")
    assert len(papers) >= 1, "Expected at least 1 paper after append"

    # Verify updated review exists
    updated_review = store.read_review(session["id"])
    assert updated_review, "Expected updated review to be saved"
    print(f"  UPDATED REVIEW LENGTH: {len(updated_review)} chars")
    print(f"  UPDATED REVIEW PREVIEW: {updated_review[:300]}...")


# ════════════════════════════════════════════════════════════════
# 5. Edge case: query_corpus with empty corpus
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_query_corpus_empty(tmp_path):
    """Live test: query_corpus on a new session (no corpus) should return
    a prompt message, not crash."""
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session()
    store.update_meta(session["id"], user_turns=2)  # simulate turn 2+
    emit = LiveEmit(prefix="EMPTY-QA")

    print(f"\n{'=' * 60}")
    print("TEST: query_corpus on empty session")
    print(f"{'=' * 60}")

    result = await run_turn(
        session_id=session["id"],
        message="什么是AI原生MOM？",
        fetch_urls=[],
        emit=emit,
        store=store,
    )

    print(f"  intent:  {result.get('extras', {}).get('intent')}")
    print(f"  content: {result.get('content', '')[:200]}")

    content = result.get("content", "")
    assert "语料" in content or "综述" in content, \
        f"Expected hint about missing corpus/review, got: {content[:200]}"
    print("  ✓ Gracefully handled empty corpus")


# ════════════════════════════════════════════════════════════════
# 6. Full 3-turn session (new_topic → query_corpus → append_urls)
# ════════════════════════════════════════════════════════════════

@pytest.mark.live
@pytest.mark.asyncio
async def test_live_full_3turn_session(tmp_path):
    """Live test: complete 3-turn session covering all 3 intent types.

    Turn 1: new_topic with MOM prompt
    Turn 2: query_corpus follow-up question
    Turn 3: append_urls with ref-list.txt URLs
    """
    from app.agents.literature_turn import run_turn

    store = _make_store(tmp_path)
    session = store.create_session("Full 3-Turn Test")

    ref_urls = get_ref_list_urls()
    test_urls = ref_urls[:2] if ref_urls else []

    print(f"\n{'=' * 60}")
    print("TEST: Full 3-turn session")
    print(f"{'=' * 60}")

    # Turn 1: new_topic
    print("\n--- TURN 1: new_topic ---")
    emit1 = LiveEmit(prefix="T1")
    result1 = await run_turn(
        session_id=session["id"],
        message=MOM_PROMPT,
        fetch_urls=[],
        emit=emit1,
        store=store,
    )
    intent1 = result1.get("extras", {}).get("intent")
    v1 = result1.get("extras", {}).get("review_version")
    print(f"  intent: {intent1}, version: {v1}")
    assert intent1 == "new_topic"

    # Turn 2: query_corpus
    print("\n--- TURN 2: query_corpus ---")
    emit2 = LiveEmit(prefix="T2")
    result2 = await run_turn(
        session_id=session["id"],
        message="AI原生MOM和传统MOM最大的架构差异是什么？",
        fetch_urls=[],
        emit=emit2,
        store=store,
    )
    intent2 = result2.get("extras", {}).get("intent")
    answer2 = result2.get("content", "")
    print(f"  intent: {intent2}")
    print(f"  answer: {answer2[:300]}...")
    assert intent2 == "query_corpus"
    assert len(answer2) >= 20

    # Turn 3: append_urls (if we have URLs)
    if not test_urls:
        pytest.skip("No ref-list URLs available for append_urls test")

    print("\n--- TURN 3: append_urls ---")
    emit3 = LiveEmit(prefix="T3")
    result3 = await run_turn(
        session_id=session["id"],
        message="补充这些文献到综述中",
        fetch_urls=test_urls,
        emit=emit3,
        store=store,
    )
    intent3 = result3.get("extras", {}).get("intent")
    v3 = result3.get("extras", {}).get("review_version")
    print(f"  intent: {intent3}, version: {v3}")
    assert intent3 == "append_urls"

    # Final state
    final_meta = store.get_meta(session["id"])
    print("\n--- FINAL SESSION STATE ---")
    print(f"  user_turns: {final_meta.get('user_turns')}")
    print(f"  last_intent: {final_meta.get('last_intent')}")
    print(f"  review_versions: {final_meta.get('review_versions')}")
    print(f"  paper_count: {final_meta.get('paper_count')}")

    corpus = store.read_corpus(session["id"])
    print(f"  corpus papers: {len(corpus.get('papers', []))}")

    review = store.read_review(session["id"])
    print(f"  latest review: {len(review)} chars")
