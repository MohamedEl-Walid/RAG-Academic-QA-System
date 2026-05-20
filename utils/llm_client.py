"""
Shared LLM client utility.

Improvements:
- Retry logic with exponential backoff (3 attempts)
- JSON extraction is more robust: handles nested ```json blocks
- call_llm_json raises descriptive LLMJSONError instead of raw json.JSONDecodeError
- Singleton client to avoid re-creating on every module import
- Logging for every LLM call (model, token counts)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIConnectionError, APIStatusError

load_dotenv()

logger = logging.getLogger(__name__)

# Singleton client
_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")

_MAX_RETRIES = 3
_RETRY_BACKOFF = [1.0, 2.0, 4.0]  # seconds between retries


class LLMError(Exception):
    """Raised when the LLM call fails after all retries."""


class LLMJSONError(LLMError):
    """Raised when the LLM returns non-parseable JSON."""


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """
    Call the LLM with retry logic. Returns the response text.
    Raises LLMError after _MAX_RETRIES failures.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t0 = time.perf_counter()
            response = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            usage = response.usage
            logger.info(
                "LLM call ok  model=%s  attempt=%d  time=%.1fms  "
                "prompt_tokens=%s  completion_tokens=%s",
                MODEL,
                attempt,
                elapsed,
                usage.prompt_tokens if usage else "?",
                usage.completion_tokens if usage else "?",
            )
            return response.choices[0].message.content.strip()

        except RateLimitError as exc:
            last_exc = exc
            logger.warning("LLM rate limit hit (attempt %d/%d)", attempt, _MAX_RETRIES)
        except APIConnectionError as exc:
            last_exc = exc
            logger.warning("LLM connection error (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)
        except APIStatusError as exc:
            last_exc = exc
            logger.warning("LLM API status error %d (attempt %d/%d)", exc.status_code, attempt, _MAX_RETRIES)
            if exc.status_code < 500:
                # Client errors (4xx) won't benefit from retries
                raise LLMError(f"LLM API error {exc.status_code}: {exc.message}") from exc
        except Exception as exc:
            last_exc = exc
            logger.error("LLM unexpected error (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)

        if attempt < _MAX_RETRIES:
            sleep_secs = _RETRY_BACKOFF[attempt - 1]
            logger.info("Retrying LLM call in %.1fs...", sleep_secs)
            time.sleep(sleep_secs)

    raise LLMError(f"LLM call failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 3000,
) -> dict | list:
    """
    Call the LLM and parse the result as JSON.
    Strips markdown code fences before parsing.
    Raises LLMJSONError if parsing fails.
    """
    raw = call_llm(system_prompt, user_prompt, temperature, max_tokens)

    # Strip outer markdown fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM returned invalid JSON. Raw (first 500 chars): %s", raw[:500]
        )
        raise LLMJSONError(f"LLM JSON parse failed: {exc}. Raw: {raw[:200]}") from exc
