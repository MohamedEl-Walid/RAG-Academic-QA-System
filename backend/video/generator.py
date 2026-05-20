"""Video generation via OpenRouter Video API with automatic model fallback."""

import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)

_BASE_URL = "https://openrouter.ai/api/v1/videos"
_POLL_INTERVAL = 5
_TIMEOUT = 120
_MAX_RETRIES = 1

FALLBACK_MODELS = [
    "google/veo-3.1-lite",
    "minimax/hailuo-2.3",
]


def _get_api_key() -> str:
    key = os.getenv("OPENROUTER_API_videogen")
    logger.info("Video API key loaded: %s", bool(key))
    if not key:
        raise RuntimeError("OPENROUTER_API_videogen is not set")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def submit_video(prompt: str, model: str) -> dict:
    """Submit a video generation request for a specific model.

    Returns {"job_id": str, "polling_url": str}.
    Raises on HTTP errors so the caller can catch and fallback.
    """
    payload = {"model": model, "prompt": prompt}
    resp = requests.post(_BASE_URL, headers=_headers(), json=payload, timeout=30)

    if not resp.ok:
        logger.error(
            "submit_video failed for %s [HTTP %d]: %s",
            model, resp.status_code, resp.text,
        )
        resp.raise_for_status()

    data = resp.json()
    job_id = data.get("id") or data.get("job_id") or data.get("generation_id", "")
    polling_url = (
        data.get("polling_url")
        or data.get("url")
        or f"{_BASE_URL}/{job_id}"
    )

    logger.info("Video job submitted: model=%s  job_id=%s", model, job_id)
    return {"job_id": job_id, "polling_url": polling_url}


def poll_video(polling_url: str) -> dict:
    """Poll until completed, failed, or timeout.

    Returns {"status": str, "video_urls": list[str]}.
    """
    deadline = time.time() + _TIMEOUT

    while time.time() < deadline:
        try:
            resp = requests.get(polling_url, headers=_headers(), timeout=15)
            if not resp.ok:
                logger.warning("Poll HTTP %d: %s", resp.status_code, resp.text)
                time.sleep(_POLL_INTERVAL)
                continue
            data = resp.json()
        except requests.RequestException as exc:
            logger.warning("Poll request error: %s", exc)
            time.sleep(_POLL_INTERVAL)
            continue

        status = data.get("status", "unknown")
        logger.info("Poll status: %s", status)

        if status == "completed":
            urls = (
                data.get("video_urls")
                or data.get("urls")
                or data.get("output", {}).get("video_urls", [])
            )
            if isinstance(urls, str):
                urls = [urls]
            return {"status": "completed", "video_urls": urls}

        if status == "failed":
            error = data.get("error", "unknown error")
            logger.error("Job failed: %s", error)
            return {"status": "failed", "video_urls": []}

        time.sleep(_POLL_INTERVAL)

    logger.error("Polling timed out after %ds", _TIMEOUT)
    return {"status": "timeout", "video_urls": []}


def _try_model(prompt: str, model: str) -> dict | None:
    """Try a single model with up to _MAX_RETRIES retries.

    Returns a success dict or None on failure.
    """
    for attempt in range(_MAX_RETRIES + 1):
        label = f"{model} attempt {attempt + 1}/{_MAX_RETRIES + 1}"
        try:
            logger.info("[%s] Submitting...", label)
            job = submit_video(prompt, model)

            logger.info("[%s] Polling job_id=%s", label, job["job_id"])
            result = poll_video(job["polling_url"])

            if result["status"] == "completed":
                logger.info("[%s] Success", label)
                return {"status": "success", "model": model, "video_urls": result["video_urls"]}

            logger.warning("[%s] Ended with status=%s", label, result["status"])

        except requests.HTTPError as exc:
            logger.warning("[%s] HTTP error: %s", label, exc)
        except Exception as exc:
            logger.warning("[%s] Unexpected error: %s", label, exc)

    return None


def generate_video_with_fallback(
    prompt: str,
    models: list[str] | None = None,
) -> dict:
    """Try each model in order; return on first success.

    Returns {"status": "success", "model": ..., "video_urls": [...]}
    or     {"status": "failed",  "errors": [...]}.
    """
    models = models or FALLBACK_MODELS
    errors: list[str] = []

    for model in models:
        logger.info("Trying model: %s", model)
        result = _try_model(prompt, model)
        if result:
            return result
        errors.append(f"{model}: failed after {_MAX_RETRIES + 1} attempt(s)")

    logger.error("All models exhausted: %s", errors)
    return {"status": "failed", "errors": errors}


def _build_cinematic_prompt(text: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    resp = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Convert the following explanation text into a short cinematic video prompt. "
                    "Max 2 sentences. Describe a visual scene, not a concept. "
                    "Use concrete imagery: objects, motion, lighting, camera angle. "
                    "Return ONLY the prompt text."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0.7,
        max_tokens=100,
    )
    return resp.choices[0].message.content.strip().strip('"')


def generate_video_from_text(text: str) -> dict:
    """Public entry point used by the /video endpoint."""
    logger.info("Converting text to cinematic prompt...")
    prompt = _build_cinematic_prompt(text)
    logger.info("Cinematic prompt: %s", prompt)

    result = generate_video_with_fallback(prompt)

    if result["status"] == "success":
        return {"status": "completed", "video_urls": result["video_urls"]}
    return {"status": "failed", "video_urls": [], "errors": result.get("errors", [])}
