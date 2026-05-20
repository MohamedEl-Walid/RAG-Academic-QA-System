"""Central pipeline: adapter layer between frontends and the orchestrator."""

import logging
from dotenv import load_dotenv

load_dotenv()

from services.config import RequestConfig
from services.orchestrator import process_pipeline
from memory.tracker import load_user, save_user, record_question, get_memory_update

logger = logging.getLogger(__name__)

DEFAULT_OPTIONS = {
    "quiz": True,
    "concept_graph": True,
    "diagram": True,
    "code": False,
    "study_plan": False,
    "mode": "explain",
    "depth": "balanced",
    "learning_level": "beginner",
}


def _extract_topic(query: str) -> str:
    stop = {"what", "is", "are", "the", "a", "an", "how", "why", "does", "do", "can", "explain", "describe"}
    keywords = [w for w in query.lower().split() if w not in stop and len(w) > 2]
    return " ".join(keywords[:3]) if keywords else "general"


def process_question(
    query: str,
    user_id: str = "default",
    options: dict | None = None,
    history: list[dict] | None = None,
) -> dict:
    opts = {**DEFAULT_OPTIONS, **(options or {})}
    profile = load_user(user_id)

    config = RequestConfig(
        depth_mode=opts.get("depth", "balanced"),
        explanation_mode=opts.get("mode", "explain"),
        learning_level=opts.get("learning_level", "beginner"),
        user_query=query,
        user_id=user_id,
        subject=_extract_topic(query),
        enabled_features={
            "quiz": opts.get("quiz", False),
            "concept_graph": opts.get("concept_graph", False),
            "diagram": opts.get("diagram", False),
            "code": opts.get("code", False),
            "study_plan": opts.get("study_plan", False),
        },
    )

    result = process_pipeline(config, history)

    # Memory tracking
    topic = _extract_topic(query)
    record_question(profile, query, topic)
    save_user(user_id, profile)
    result["memory_update"] = get_memory_update(profile)

    return result


def run_heavy_feature(
    feature: str,
    query: str,
    context: str = "",
    chunks: list[dict] | None = None,
) -> dict:
    """Deprecated — kept for backward compatibility only.
    Features are now dispatched automatically by the orchestrator."""
    from coding.generator import generate_code, explain_code
    from planner.roadmap import generate_study_plan

    if feature == "code":
        code = generate_code(query)
        return {"code": code, "code_explanation": explain_code(code)}

    if feature == "study_plan":
        return {"study_plan": generate_study_plan(query)}

    return {}


if __name__ == "__main__":
    import json

    result = process_question("What is expert system?")
    output = {k: v for k, v in result.items() if k != "meta"}
    print(json.dumps(output, indent=2, default=str))
