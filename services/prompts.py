"""Centralized, config-driven prompt engineering.

Every prompt adapts to three orthogonal signals:
  1. explanation_mode  (explain, summarize, teach, revise)
  2. depth_mode        (fast, balanced, deep)
  3. learning_level    (beginner, intermediate, expert)
"""

from services.config import RequestConfig

# ── Explanation-mode instructions ─────────────────────────────────────────

MODE_PROMPTS = {
    "explain": (
        "You are an academic tutor. Provide a clear, detailed, and structured explanation. "
        "Use educational language, break down complex concepts, and ensure clarity."
    ),
    "summarize": (
        "You are an expert summarizer. Provide a concise, compressed overview. "
        "Focus only on the absolute core points without fluff."
    ),
    "teach": (
        "You are an interactive teacher. Teach this step-by-step. "
        "Use analogies, relatable real-world examples, and beginner-friendly language."
    ),
    "revise": (
        "You are an exam prep assistant. Provide concise revision notes. "
        "Use bullet points, highlight key facts, and focus on examinable material."
    ),
}

# ── Depth instructions ────────────────────────────────────────────────────

DEPTH_INSTRUCTIONS = {
    "fast": "Keep your answer brief and to the point. Avoid lengthy exposition.",
    "balanced": "Provide a moderate level of detail with a balanced structure.",
    "deep": (
        "Provide an extensive, in-depth analysis. Use a chain-of-thought internal reasoning approach. "
        "Cover edge cases, underlying mechanisms, and advanced implications."
    ),
}

# ── Learning-level instructions (first-class orchestration signal) ────────

LEVEL_INSTRUCTIONS = {
    "beginner": (
        "The reader is a complete beginner with NO prior knowledge of this topic. "
        "Use simple, everyday language. Avoid jargon — if you must use a technical "
        "term, define it immediately. Use analogies to familiar concepts. "
        "Explain step-by-step as if teaching a child. Keep sentences short."
    ),
    "intermediate": (
        "The reader has basic knowledge of the field. Use proper terminology "
        "but still provide clear definitions for advanced terms. Include practical "
        "examples. Balance depth and clarity."
    ),
    "expert": (
        "The reader is an advanced practitioner or researcher. Use precise "
        "technical language freely. Reference related concepts, discuss edge cases, "
        "nuances, architectural trade-offs, and optimization strategies. "
        "Be concise and information-dense — do not over-explain fundamentals."
    ),
}

# ── RAG strictness suffix (always appended) ───────────────────────────────

_RAG_SUFFIX = (
    "\n\nYou MUST build your answer ONLY from the provided facts. "
    "Every paragraph MUST include at least one citation [N]. "
    "Do NOT introduce external knowledge. "
    "Do NOT write general statements without grounding them in a fact. "
    "Cite sources using [N] notation matching the fact number."
)

# ── Builders ──────────────────────────────────────────────────────────────

def build_system_prompt(config: RequestConfig) -> str:
    """Compose a system prompt from mode + depth + level."""
    mode_sys = MODE_PROMPTS.get(config.explanation_mode, MODE_PROMPTS["explain"])
    depth_sys = DEPTH_INSTRUCTIONS.get(config.depth_mode, DEPTH_INSTRUCTIONS["balanced"])
    level_sys = LEVEL_INSTRUCTIONS.get(config.learning_level, LEVEL_INSTRUCTIONS["beginner"])

    return f"{mode_sys}\n\n{depth_sys}\n\n{level_sys}{_RAG_SUFFIX}"


def build_user_prompt(query: str, facts_text: str, config: RequestConfig) -> str:
    prompt = f"FACTS:\n{facts_text}\n\n---\n\nQuestion: {query}\n\n"

    mode_tail = {
        "revise": "Provide revision notes grounded ONLY in the facts above.",
        "summarize": "Provide a short summary grounded ONLY in the facts above.",
        "teach": "Teach this concept step-by-step grounded ONLY in the facts above.",
    }
    prompt += mode_tail.get(config.explanation_mode,
                            "Provide a detailed explanation grounded ONLY in the facts above.")
    return prompt


def build_expansion_prompt(query: str, current_answer: str, facts_text: str,
                           config: RequestConfig) -> str:
    prompt = (
        "The following answer is too short. Expand it using ONLY the provided facts.\n"
        "Keep all existing citations. Add more detail and explanation from the facts.\n"
        "Every paragraph MUST include at least one citation [N].\n\n"
        f"FACTS:\n{facts_text}\n\n"
        f"CURRENT ANSWER:\n{current_answer}\n\n"
        f"Question: {query}\n\n"
        "Provide an expanded, detailed answer grounded in the facts above."
    )
    return prompt
