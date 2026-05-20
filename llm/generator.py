"""
Main LLM answer generator.

Improvements over v1:
- All print() calls replaced with structured logger calls
- LLM client is imported from the shared utils singleton (no duplicate client)
- Relevance check now also uses rerank_score where available
- Dead code removed
- Token estimation is more conservative to avoid truncation
"""

from __future__ import annotations

import logging
import re

from services.config import RequestConfig
from services.prompts import build_system_prompt, build_user_prompt, build_expansion_prompt
from utils.llm_client import call_llm, LLMError

logger = logging.getLogger(__name__)

REJECT_MESSAGE = "This question is outside the provided academic materials."
MIN_ANSWER_WORDS = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def check_relevance(query: str, chunks: list[dict]) -> bool:
    """Return True if any chunk has a reasonable similarity score."""
    for chunk in chunks:
        # Prefer rerank_score (more reliable) if available, fall back to raw score
        score = chunk.get("rerank_score", chunk.get("score", 0))
        if score >= 0.70:
            return True
    return False


def _deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for chunk in chunks:
        key = chunk["content"].strip()
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    return unique


def _build_facts(chunks: list[dict]) -> list[dict]:
    facts = []
    for i, chunk in enumerate(chunks, 1):
        # Truncate cleanly at word boundary
        text = chunk["content"][:500]
        last_space = text.rfind(" ")
        if last_space > 300:
            text = text[:last_space]
        facts.append({
            "id": i,
            "text": text,
            "source": chunk.get("source", "unknown"),
            "page": chunk.get("page_start", "?"),
        })
    return facts


def _format_facts(facts: list[dict]) -> str:
    return "\n\n".join(
        f"[{f['id']}] (Source: {f['source']}, Page {f['page']})\n{f['text']}"
        for f in facts
    )


def _estimate_max_tokens(query: str, chunks: list[dict], config: RequestConfig) -> int:
    q_len = len(query.split())
    context_len = sum(len(c["content"].split()) for c in chunks)
    total = q_len + context_len

    if total < 500:
        base = 900
    elif total < 1000:
        base = 1200
    elif total < 1500:
        base = 1600
    else:
        base = 2000

    if config.depth_mode == "fast":
        return min(base, 400)
    if config.depth_mode == "deep":
        return min(base + 1000, 3000)

    q_lower = query.lower()
    if any(x in q_lower for x in ["what is", "define", "definition"]):
        return min(base, 800)
    if any(x in q_lower for x in ["how", "why", "explain"]):
        return min(base, 1400)
    if any(x in q_lower for x in ["deep", "detailed", "in depth"]):
        return min(base, 1800)
    return base


def _extract_used_citations(text: str, total: int) -> set[int]:
    found: set[int] = set()
    for match in re.findall(r"\[(\d+)\]", text):
        idx = int(match)
        if 1 <= idx <= total:
            found.add(idx)
    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_answer(
    query: str,
    chunks: list[dict],
    config: RequestConfig | None = None,
    history: list[dict] | None = None,
) -> str:
    if not chunks:
        logger.info("No chunks provided — returning reject message")
        return REJECT_MESSAGE

    if not check_relevance(query, chunks):
        logger.info("Relevance check failed — returning reject message")
        return REJECT_MESSAGE

    if config is None:
        config = RequestConfig()

    chunks = _deduplicate_chunks(chunks)
    facts = _build_facts(chunks)
    facts_text = _format_facts(facts)

    logger.info(
        "Generating answer  query=%r  depth=%s  level=%s  facts=%d",
        query[:80],
        config.depth_mode,
        config.learning_level,
        len(facts),
    )

    system_prompt = build_system_prompt(config)
    user_prompt = build_user_prompt(query, facts_text, config)
    max_tokens = _estimate_max_tokens(query, chunks, config)

    logger.debug("Estimated max_tokens=%d  prompt_words=%d", max_tokens, len(user_prompt.split()))

    try:
        explanation = call_llm(system_prompt, user_prompt, max_tokens=max_tokens)
    except LLMError as exc:
        logger.error("LLM generation failed: %s", exc)
        return f"Generation failed: {exc}"

    # Expand if answer is too short and not in fast mode
    word_count = len(explanation.split())
    if config.depth_mode != "fast" and word_count < MIN_ANSWER_WORDS:
        logger.info(
            "Answer too short (%d words) — expanding (depth=%s)",
            word_count,
            config.depth_mode,
        )
        expand_prompt = build_expansion_prompt(query, explanation, facts_text, config)
        try:
            explanation = call_llm(system_prompt, expand_prompt, max_tokens=max_tokens)
        except LLMError as exc:
            logger.warning("Expansion failed: %s — using original", exc)

    used = _extract_used_citations(explanation, len(chunks))
    logger.info("Citations used: %s", sorted(used))

    source_lines = [
        f"[{f['id']}] {f['text'][:300]}...\n    — {f['source']}, Page {f['page']}"
        for f in facts
        if f["id"] in used
    ]
    source_text = "\n\n".join(source_lines) if source_lines else "(No sources cited)"

    return f"=== SOURCE TEXT ===\n{source_text}\n\n=== EXPLANATION ===\n{explanation}"
