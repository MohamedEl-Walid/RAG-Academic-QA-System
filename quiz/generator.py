"""Level-aware quiz generator.

Difficulty scales with learning_level:
  beginner     → easy questions, simple language
  intermediate → medium questions, balanced
  expert       → hard analytical questions
"""

from utils.llm_client import call_llm_json

_LEVEL_DIFFICULTY = {
    "beginner": "easy",
    "intermediate": "medium",
    "expert": "hard",
}

_LEVEL_INSTRUCTIONS = {
    "beginner": (
        "Questions must be simple and test basic understanding. "
        "Use clear, everyday language. Avoid tricky wording."
    ),
    "intermediate": (
        "Questions should test practical understanding and application. "
        "Use proper terminology. Include some 'why' and 'how' questions."
    ),
    "expert": (
        "Questions must be analytically challenging. Test deep reasoning, "
        "edge cases, and ability to compare/contrast concepts. "
        "Include questions that require synthesis of multiple ideas."
    ),
}


def _system_prompt(level: str) -> str:
    difficulty = _LEVEL_DIFFICULTY.get(level, "medium")
    instruction = _LEVEL_INSTRUCTIONS.get(level, _LEVEL_INSTRUCTIONS["intermediate"])
    return (
        f"You are an academic quiz generator creating {difficulty}-difficulty questions. "
        f"{instruction}\n"
        "Generate questions ONLY from the provided answer text. "
        "Every question must be directly answerable from the given content. "
        "Do not invent external facts. Return valid JSON only."
    )


def generate_mcq(answer_text: str, num: int = 3, level: str = "beginner") -> list[dict]:
    difficulty = _LEVEL_DIFFICULTY.get(level, "medium")
    prompt = f"""From this text, generate {num} multiple-choice questions.

Text: {answer_text}

Return JSON array where each item has exactly this structure:
{{
    "type": "mcq",
    "difficulty": "{difficulty}",
    "question": "the question string",
    "options": ["option 1", "option 2", "option 3", "option 4"],
    "answer": "the exact string of the correct option",
    "explanation": "brief explanation of the correct answer"
}}"""
    try:
        return call_llm_json(_system_prompt(level), prompt)
    except Exception:
        return []


def generate_true_false(answer_text: str, num: int = 3, level: str = "beginner") -> list[dict]:
    difficulty = _LEVEL_DIFFICULTY.get(level, "medium")
    prompt = f"""From this text, generate {num} true/false questions.

Text: {answer_text}

Return JSON array where each item has exactly this structure:
{{
    "type": "true_false",
    "difficulty": "{difficulty}",
    "question": "the statement to evaluate",
    "options": ["True", "False"],
    "answer": "True or False",
    "explanation": "brief explanation"
}}"""
    try:
        return call_llm_json(_system_prompt(level), prompt)
    except Exception:
        return []


def generate_short_answer(answer_text: str, num: int = 2, level: str = "beginner") -> list[dict]:
    difficulty = _LEVEL_DIFFICULTY.get(level, "medium")
    prompt = f"""From this text, generate {num} short-answer questions.

Text: {answer_text}

Return JSON array where each item has exactly this structure:
{{
    "type": "short_answer",
    "difficulty": "{difficulty}",
    "question": "the question",
    "answer": "the correct answer (1-3 sentences)",
    "explanation": "keywords or criteria for a good answer"
}}"""
    try:
        return call_llm_json(_system_prompt(level), prompt)
    except Exception:
        return []


def generate_quiz(answer_text: str, level: str = "beginner") -> dict:
    """Generate a full quiz adapted to the learner's level."""
    questions = []
    questions.extend(generate_mcq(answer_text, level=level))
    questions.extend(generate_true_false(answer_text, level=level))
    questions.extend(generate_short_answer(answer_text, level=level))
    
    return {
        "title": "Knowledge Check",
        "questions": questions
    }

