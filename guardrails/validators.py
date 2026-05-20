"""Input/output validation and safety guardrails.

Catches:
  - Empty or trivially short inputs
  - Excessively long inputs (potential abuse)
  - Prompt injection attempts in user queries
  - HTML/script injection in outputs
  - Path traversal in user IDs
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 2000
MIN_QUERY_LENGTH = 2

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"\[INST\]",
    r"```system",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE
)

# Characters not allowed in user IDs (prevents path traversal)
_SAFE_USER_ID = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def validate_question(question: str) -> tuple[bool, str]:
    """Validate a user question. Returns (is_valid, error_message)."""
    if not question or not question.strip():
        return False, "Question cannot be empty."

    question = question.strip()

    if len(question) < MIN_QUERY_LENGTH:
        return False, f"Question too short (min {MIN_QUERY_LENGTH} characters)."

    if len(question) > MAX_QUERY_LENGTH:
        return False, f"Question too long (max {MAX_QUERY_LENGTH} characters)."

    if _INJECTION_RE.search(question):
        logger.warning("Potential prompt injection detected: %r", question[:100])
        return False, "Your question contains disallowed patterns."

    return True, ""


def sanitize_user_id(user_id: str) -> str:
    """Sanitize user_id to prevent path traversal. Returns 'default' if invalid."""
    if not user_id or not _SAFE_USER_ID.match(user_id):
        logger.warning("Invalid user_id sanitized: %r -> 'default'", user_id[:50])
        return "default"
    return user_id


def validate_answer(answer: str) -> tuple[bool, str]:
    """Validate an LLM answer for safety. Returns (is_valid, warning)."""
    if not answer or not answer.strip():
        return False, "Empty answer generated."

    # Check for suspicious HTML/script injection in LLM output
    if re.search(r"<script", answer, re.IGNORECASE):
        logger.warning("Script tag detected in LLM output")
        return False, "Answer contains potentially unsafe HTML."

    if re.search(r"javascript:", answer, re.IGNORECASE):
        return False, "Answer contains potentially unsafe javascript: URI."

    return True, ""


def sanitize_mermaid_output(mermaid_code: str) -> str:
    """Strip dangerous patterns from Mermaid diagram output."""
    if not mermaid_code:
        return ""

    # Remove any embedded HTML tags from mermaid
    sanitized = re.sub(r"<[^>]+>", "", mermaid_code)
    # Remove javascript: URIs
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
    # Remove click callbacks (mermaid feature that can run JS)
    sanitized = re.sub(r"click\s+\w+\s+\"[^\"]*\"", "", sanitized)
    sanitized = re.sub(r"click\s+\w+\s+call\s+", "", sanitized)

    return sanitized
