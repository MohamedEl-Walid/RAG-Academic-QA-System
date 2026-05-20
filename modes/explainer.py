from utils.llm_client import call_llm

MODE_INSTRUCTIONS = {
    "explain": "Provide a clear, structured explanation of the topic.",
    "why": "Focus on WHY this concept exists, its motivation, and the problems it solves.",
    "how": "Focus on HOW this works mechanically. Describe the process step by step.",
    "example": "Explain primarily through concrete, real-world examples. Give at least 2-3 examples.",
    "deep_dive": (
        "Provide an in-depth, advanced analysis. Cover edge cases, limitations, "
        "related concepts, historical context, and current research directions."
    ),
}


def explain(query: str, context: str, mode: str = "explain") -> str:
    instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain"])
    system = f"You are an academic tutor. {instruction}"
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    return call_llm(system, prompt, temperature=0.4, max_tokens=1500)


def list_modes() -> list[str]:
    return list(MODE_INSTRUCTIONS.keys())
