"""Response assembler — merges the main explanation and all text-based feature
results into a single, coherent markdown document.

The assembled output adapts its formatting based on the learning level.
NOTE: Diagrams and Quizzes are NOT assembled into the markdown. They are returned
as structured objects in the feature_results array to be rendered by the frontend UI.
"""

from services.config import PipelineContext


def assemble_response(context: PipelineContext) -> str:
    level = context.config.learning_level
    parts: list[str] = []

    # ── 1. Main explanation ───────────────────────────────────────────────
    if context.main_response:
        if "=== EXPLANATION ===" in context.main_response:
            explanation = context.main_response.split("=== EXPLANATION ===")[1].strip()
            sources = (
                context.main_response
                .split("=== EXPLANATION ===")[0]
                .replace("=== SOURCE TEXT ===", "")
                .strip()
            )
            if level == "beginner":
                parts.append(f"# 📖 Explanation\n\n{explanation}")
            elif level == "expert":
                parts.append(f"# Explanation\n\n{explanation}")
            else:
                parts.append(f"# Explanation\n\n{explanation}")

            parts.append(f"## Sources\n\n{sources}")
        else:
            parts.append(f"# Explanation\n\n{context.main_response}")

    # ── 2. Text-based Feature results (ordered) ───────────────────────────
    for result in context.feature_results:
        # We skip diagrams and quizzes because the frontend renders them natively
        if result.type in ("quiz", "diagram", "concept_graph"):
            continue
            
        parts.append(f"# {result.title}\n")

        if result.type == "code":
            parts.append(
                f"```python\n{result.content.get('code', '')}\n```\n\n"
                f"{result.content.get('code_explanation', '')}"
            )
        elif result.type == "study_plan":
            parts.append(_format_study_plan(result.content))
        else:
            parts.append(str(result.content))

    return "\n\n---\n\n".join(parts)


# ── Formatters ────────────────────────────────────────────────────────────

def _format_study_plan(plan_data: list) -> str:
    lines: list[str] = []
    for mod in plan_data:
        lines.append(f"### Module {mod.get('module', '')}: {mod.get('title', '')}")
        lines.append(
            f"_{mod.get('difficulty', '')}_ — ~{mod.get('estimated_hours', '?')}h"
        )
        lines.append(f"{mod.get('description', '')}\n")
        for sub in mod.get("subtopics", []):
            lines.append(f"  - {sub}")
        lines.append("")
    return "\n".join(lines)
