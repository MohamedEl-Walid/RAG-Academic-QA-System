"""Level-aware code generator.

Code complexity scales with learning_level:
  beginner     → heavily commented, simple, educational
  intermediate → production-aware but readable
  expert       → advanced patterns, optimized, scalable
"""

from utils.llm_client import call_llm

_CODE_SYSTEM = {
    "beginner": (
        "You are a coding tutor for absolute beginners. "
        "Generate a simple, working Python code example that demonstrates the concept.\n"
        "The code MUST be:\n"
        "- Very simple with short functions\n"
        "- Heavily commented (comment almost every line)\n"
        "- Use basic constructs only (no decorators, generators, or metaclasses)\n"
        "- Include a print statement showing output\n"
        "- Educational — prioritize clarity over efficiency\n"
        "Return ONLY the code, no explanation."
    ),
    "intermediate": (
        "You are a coding tutor. Generate a clear, working Python code example "
        "that demonstrates the given concept.\n"
        "The code should be:\n"
        "- Complete and runnable\n"
        "- Well-structured with meaningful variable names\n"
        "- Include docstrings and moderate comments\n"
        "- Production-aware but readable\n"
        "- Focused on illustrating the concept\n"
        "Return ONLY the code, no explanation."
    ),
    "expert": (
        "You are a senior software engineer. Generate an advanced Python code example "
        "that demonstrates the given concept with production-quality patterns.\n"
        "The code should be:\n"
        "- Architecturally sound (SOLID, clean code)\n"
        "- Use advanced features where appropriate (type hints, dataclasses, "
        "context managers, generators)\n"
        "- Include error handling and edge cases\n"
        "- Consider performance and scalability\n"
        "- Minimal comments — the code should be self-documenting\n"
        "Return ONLY the code, no explanation."
    ),
}

_EXPLAIN_SYSTEM = {
    "beginner": (
        "You are a coding tutor for beginners. Explain the given code line by line "
        "in very simple language. Assume the reader has never programmed before.\n"
        "Format: for each significant line or block, write:\n"
        "  Line N: <the code line>\n"
        "  → <simple explanation>\n"
        "Explain everything — even basic constructs like loops and variables."
    ),
    "intermediate": (
        "You are a coding tutor. Explain the given code line by line.\n"
        "Format: for each significant line or block, write:\n"
        "  Line N: <the code line>\n"
        "  → <explanation>\n"
        "Be concise but clear. Skip trivial lines like blank lines or imports "
        "unless they are relevant to the concept."
    ),
    "expert": (
        "You are a senior engineer doing a code review. Provide a concise "
        "architectural explanation of the code.\n"
        "Focus on: design patterns used, time/space complexity, trade-offs, "
        "and potential improvements. Skip trivial line-by-line explanations."
    ),
}


def generate_code(concept: str, language: str = "python",
                  level: str = "beginner") -> str:
    system = _CODE_SYSTEM.get(level, _CODE_SYSTEM["intermediate"])
    return call_llm(system, f"Concept: {concept}", temperature=0.2)


def explain_code(code: str, level: str = "beginner") -> str:
    system = _EXPLAIN_SYSTEM.get(level, _EXPLAIN_SYSTEM["intermediate"])
    return call_llm(system, code, temperature=0.2)
