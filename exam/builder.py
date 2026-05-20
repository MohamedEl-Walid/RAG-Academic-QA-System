from utils.llm_client import call_llm_json


def generate_exam(topic: str, context: str, num_questions: int = 10) -> dict:
    system = (
        "You are an academic exam generator. Create a structured exam based on the topic and context.\n"
        f"Generate exactly {num_questions} questions with a mix of types.\n"
        "Return a JSON object with:\n"
        '  "title": "Exam: <topic>",\n'
        '  "total_points": number,\n'
        '  "time_limit_minutes": number,\n'
        '  "questions": [\n'
        "    {\n"
        '      "id": int,\n'
        '      "type": "mcq" | "true_false" | "short_answer" | "essay",\n'
        '      "question": string,\n'
        '      "options": [...] (only for mcq),\n'
        '      "correct_answer": string,\n'
        '      "points": number,\n'
        '      "difficulty": "easy" | "medium" | "hard"\n'
        "    }\n"
        "  ],\n"
        '  "scoring": {\n'
        '    "pass_threshold": 60,\n'
        '    "grade_boundaries": {"A": 90, "B": 80, "C": 70, "D": 60}\n'
        "  }\n"
        "Return ONLY valid JSON."
    )
    prompt = f"Topic: {topic}\n\nContext:\n{context}"
    try:
        return call_llm_json(system, prompt, max_tokens=4000)
    except Exception:
        return {"title": f"Exam: {topic}", "questions": [], "error": "Generation failed"}
