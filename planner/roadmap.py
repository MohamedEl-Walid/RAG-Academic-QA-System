"""Level-aware study plan generator.

Plan rigor scales with learning_level:
  beginner     → gentle progression, more hours, foundational
  intermediate → balanced pacing
  expert       → accelerated, rigorous, advanced topics
"""

from utils.llm_client import call_llm_json

_LEVEL_OVERLAY = {
    "beginner": (
        "Design the plan for a complete beginner. Start from absolute fundamentals. "
        "Use gentle progression with plenty of review modules. "
        "Estimate generous time (beginners need more hours). "
        "Include prerequisite knowledge in early modules."
    ),
    "intermediate": (
        "Design the plan for someone with basic knowledge. "
        "Skip absolute basics but include review where needed. "
        "Balance theory and practice."
    ),
    "expert": (
        "Design the plan for an advanced learner. "
        "Skip fundamentals entirely — focus on advanced topics, edge cases, "
        "research directions, and optimization techniques. "
        "Use an accelerated pace with fewer, denser modules. "
        "Include references to papers or advanced resources where relevant."
    ),
}


def generate_study_plan(topic: str, num_modules: int = 5,
                        level: str = "beginner") -> list[dict]:
    level_note = _LEVEL_OVERLAY.get(level, _LEVEL_OVERLAY["intermediate"])
    system = (
        "You are an academic study planner. Generate a structured learning roadmap.\n"
        f"Create {num_modules} study modules ordered from easiest to hardest.\n"
        f"{level_note}\n"
        "Return a JSON array where each item has:\n"
        '  "module": int (1-based),\n'
        '  "title": string,\n'
        '  "description": string (what the student will learn),\n'
        '  "subtopics": [string, string, ...],\n'
        '  "difficulty": "easy" | "medium" | "hard",\n'
        '  "estimated_hours": number\n'
        "Return ONLY valid JSON."
    )
    try:
        return call_llm_json(system, f"Topic: {topic}")
    except Exception:
        return []
