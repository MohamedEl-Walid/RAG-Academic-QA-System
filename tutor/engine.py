from utils.llm_client import call_llm


LEVEL_PROMPTS = {
    "beginner": (
        "Explain this to a complete beginner with no technical background. "
        "Use simple language, analogies, and everyday examples. Avoid jargon."
    ),
    "intermediate": (
        "Explain this to someone with basic knowledge of the field. "
        "Use proper terminology but still provide clear definitions. Include examples."
    ),
    "advanced": (
        "Explain this to an advanced student or practitioner. "
        "Use precise technical language, reference related concepts, "
        "discuss edge cases and nuances."
    ),
}


def generate_adaptive_explanation(query: str, context: str, user_level: str = "beginner") -> str:
    level_instruction = LEVEL_PROMPTS.get(user_level, LEVEL_PROMPTS["beginner"])
    system = f"You are an adaptive academic tutor. {level_instruction}"
    prompt = f"Based on this context:\n\n{context}\n\nAnswer this question: {query}"
    return call_llm(system, prompt, temperature=0.4)


def generate_multi_level(query: str, context: str) -> dict[str, str]:
    levels = {}
    for level, instruction in LEVEL_PROMPTS.items():
        system = f"You are an academic tutor. {instruction}"
        prompt = f"Based on this context:\n\n{context}\n\nExplain: {query}"
        levels[level] = call_llm(system, prompt, temperature=0.4, max_tokens=800)
    return levels
