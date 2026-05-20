"""Level-aware diagram generator using Mermaid.

Diagram complexity scales with learning_level:
  beginner     → simple, annotated flowcharts
  intermediate → standard diagrams
  expert       → detailed architectural diagrams
"""

import re
from typing import Dict, Any
from utils.llm_client import call_llm

DIAGRAM_TYPES = {
    "flowchart": (
        "Convert the explanation into a flowchart using Mermaid 'graph TD' or 'graph LR'.\n"
        "Use standard node shapes. Ensure all arrows and connections are valid."
    ),
    "concept_map": (
        "Convert the explanation into a concept map using Mermaid 'graph TD'.\n"
        "Connect concepts with labeled arrows."
    ),
    "mind_map": (
        "Convert the explanation into a mindmap using Mermaid 'mindmap'.\n"
        "Ensure correct indentation for hierarchy."
    ),
    "architecture": (
        "Convert the explanation into an architecture diagram using Mermaid 'graph TD'.\n"
        "Use subgraphs to group related components."
    ),
}

_LEVEL_OVERLAY = {
    "beginner": (
        "Keep the diagram VERY simple. Use at most 5-6 nodes. "
        "Add short, educational labels explaining each step. "
        "A beginner with no background should understand this at a glance."
    ),
    "intermediate": (
        "Create a moderately detailed diagram. Include the main components "
        "and their interactions. Balance clarity with completeness."
    ),
    "expert": (
        "Create a detailed, information-dense diagram. Include sub-components, "
        "data flows, feedback loops, and edge cases. "
        "Show architectural layers and cross-cutting concerns using subgraphs where relevant."
    ),
}


def sanitize_mermaid(raw: str) -> str:
    """Extract and sanitize mermaid syntax from LLM output."""
    # Find ```mermaid block if it exists
    match = re.search(r"```(?:mermaid)?\n(.*?)\n```", raw, re.DOTALL)
    if match:
        code = match.group(1).strip()
    else:
        code = raw.strip()

    # Basic sanitization
    # Remove any trailing garbage that isn't part of mermaid syntax
    lines = code.split("\n")
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith("```"):
            continue
        cleaned_lines.append(line)
        
    return "\n".join(cleaned_lines)


def generate_diagram(answer_text: str, diagram_type: str = "flowchart",
                     level: str = "beginner") -> Dict[str, Any]:
    instruction = DIAGRAM_TYPES.get(diagram_type, DIAGRAM_TYPES["flowchart"])
    level_note = _LEVEL_OVERLAY.get(level, _LEVEL_OVERLAY["intermediate"])
    system = (
        "You are an expert Mermaid diagram generator for educational content.\n"
        f"{instruction}\n"
        f"{level_note}\n"
        "Rules for Mermaid:\n"
        "1. Output ONLY valid Mermaid syntax.\n"
        "2. Do NOT wrap the output in markdown backticks (```) or add any explanation text.\n"
        "3. Ensure node IDs do not contain spaces or special characters (e.g., use A[Label] not A B[Label]).\n"
        "4. Avoid special characters like quotes or brackets inside node labels unless escaped properly.\n"
        "5. For graphs, always start with 'graph TD' or 'graph LR'."
    )
    
    raw_output = call_llm(system, answer_text, temperature=0.1, max_tokens=1500)
    sanitized_mermaid = sanitize_mermaid(raw_output)
    
    return {
        "type": diagram_type,
        "mermaid": sanitized_mermaid
    }
