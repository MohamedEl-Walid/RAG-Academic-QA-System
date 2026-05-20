"""Level-aware concept graph extractor.

Graph complexity scales with learning_level:
  beginner     → 3-5 core concepts, simple relationships
  intermediate → 4-8 concepts, standard relationships
  expert       → 6-12 concepts, dense cross-cutting relationships
"""

from utils.llm_client import call_llm_json

_LEVEL_CONFIG = {
    "beginner": {
        "node_range": "3-5",
        "instruction": (
            "Extract only the most fundamental concepts. "
            "Use simple labels and short descriptions. "
            "Stick to basic relationship types like 'is_a' and 'part_of'."
        ),
    },
    "intermediate": {
        "node_range": "4-8",
        "instruction": (
            "Extract key concepts and their relationships. "
            "Use clear relationship types like: "
            "'is_a', 'part_of', 'uses', 'leads_to', 'depends_on', 'contrasts_with'."
        ),
    },
    "expert": {
        "node_range": "6-12",
        "instruction": (
            "Extract a rich, densely connected concept graph. "
            "Include advanced sub-concepts, cross-cutting concerns, and nuanced "
            "relationships like 'optimizes', 'generalizes', 'specializes', "
            "'competes_with', 'enables', 'constrains'. "
            "Capture architectural and theoretical interconnections."
        ),
    },
}


def extract_concept_graph(answer_text: str, level: str = "beginner") -> dict:
    cfg = _LEVEL_CONFIG.get(level, _LEVEL_CONFIG["intermediate"])
    system = (
        "You are a knowledge graph extractor. From the given academic text, "
        "extract key concepts and their relationships.\n"
        "Return a JSON object with:\n"
        '  "nodes": [{"id": "concept_name", "label": "Concept Name", '
        '"description": "one-line description"}],\n'
        '  "edges": [{"source": "concept_a", "target": "concept_b", '
        '"relation": "relationship type"}]\n'
        f"Extract {cfg['node_range']} concepts. {cfg['instruction']}\n"
        "Return ONLY valid JSON."
    )
    try:
        graph = call_llm_json(system, answer_text)
        if "nodes" not in graph:
            graph = {"nodes": [], "edges": []}
        return graph
    except Exception:
        return {"nodes": [], "edges": []}
