import json

from dotenv import load_dotenv

load_dotenv()

from pipeline import process_question


def main():
    print("=== AI Learning Platform (CLI) ===")
    print("Commands: quit, mode <name>, level, plan <topic>, exam <topic>")
    print("Modes: explain, why, how, example, deep_dive\n")

    user_id = "cli_user"
    current_mode = "explain"
    history = []

    while True:
        query = input(">> ").strip()
        if not query:
            continue

        if query.lower() == "quit":
            print("Goodbye!")
            break

        if query.lower().startswith("mode "):
            current_mode = query.split(maxsplit=1)[1].strip()
            print(f"Mode set to: {current_mode}\n")
            continue

        options = {
            "levels": True,
            "quiz": True,
            "concept_graph": True,
            "diagram": True,
            "code": False,
            "study_plan": False,
            "exam": False,
            "mode": current_mode,
        }

        if query.lower().startswith("plan "):
            topic = query.split(maxsplit=1)[1]
            options = {"levels": False, "quiz": False, "concept_graph": False,
                       "diagram": False, "study_plan": True, "mode": None}
            query = topic

        if query.lower().startswith("exam "):
            topic = query.split(maxsplit=1)[1]
            options = {"levels": False, "quiz": False, "concept_graph": False,
                       "diagram": False, "exam": True, "mode": None}
            query = topic

        print("\nProcessing...\n")
        result = process_question(query, user_id=user_id, options=options, history=history)

        print(json.dumps(result, indent=2, default=str))
        history.append({"question": query, "answer": result.get("answer", "")})
        print()


if __name__ == "__main__":
    main()
