"""User memory and progress tracking.

Improvements:
- Path traversal protection via sanitize_user_id
- Fixed level mismatch: update_level now uses 'expert' (was 'advanced')
- Added logging instead of silent failures
- Questions list is capped to prevent unbounded file growth
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "memory")
MAX_STORED_QUESTIONS = 200  # cap to prevent file bloat

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def _sanitize_id(user_id: str) -> str:
    """Ensure user_id is safe for filesystem use."""
    if not user_id or not _SAFE_ID_RE.match(user_id):
        logger.warning("Invalid user_id %r — falling back to 'default'", user_id[:50] if user_id else "")
        return "default"
    return user_id


def _user_path(user_id: str) -> str:
    safe_id = _sanitize_id(user_id)
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{safe_id}.json")


def _default_profile() -> dict:
    return {
        "level": "beginner",
        "questions": [],
        "weak_areas": [],
        "topic_counts": {},
        "quiz_scores": [],
    }


def load_user(user_id: str) -> dict:
    path = _user_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.error("Corrupt profile for %s: %s — resetting", user_id, exc)
            return _default_profile()
    return _default_profile()


def save_user(user_id: str, profile: dict) -> None:
    path = _user_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    except IOError as exc:
        logger.error("Failed to save profile for %s: %s", user_id, exc)


def record_question(profile: dict, query: str, topic: str = "general") -> dict:
    profile["questions"].append({
        "query": query,
        "topic": topic,
        "timestamp": time.time(),
    })
    # Cap the question history to prevent unbounded growth
    if len(profile["questions"]) > MAX_STORED_QUESTIONS:
        profile["questions"] = profile["questions"][-MAX_STORED_QUESTIONS:]

    profile["topic_counts"][topic] = profile["topic_counts"].get(topic, 0) + 1
    return profile


def record_quiz_score(profile: dict, topic: str, score: float) -> dict:
    profile["quiz_scores"].append({
        "topic": topic,
        "score": score,
        "timestamp": time.time(),
    })
    if score < 0.5 and topic not in profile["weak_areas"]:
        profile["weak_areas"].append(topic)
    elif score >= 0.8 and topic in profile["weak_areas"]:
        profile["weak_areas"].remove(topic)
    return profile


def update_level(profile: dict) -> dict:
    """Auto-adjust level based on recent quiz scores.
    
    BUG FIX: was setting 'advanced' which is not a valid level.
    Valid levels: beginner, intermediate, expert
    """
    scores = profile["quiz_scores"]
    if len(scores) < 3:
        return profile
    recent = [s["score"] for s in scores[-5:]]
    avg = sum(recent) / len(recent)
    if avg >= 0.8:
        profile["level"] = "expert"       # was incorrectly 'advanced'
    elif avg >= 0.5:
        profile["level"] = "intermediate"
    else:
        profile["level"] = "beginner"
    return profile


def get_memory_update(profile: dict) -> dict:
    return {
        "level": profile.get("level", "beginner"),
        "total_questions": len(profile.get("questions", [])),
        "weak_areas": profile.get("weak_areas", []),
        "top_topics": sorted(
            profile.get("topic_counts", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5],
    }
