"""Scene extraction and visual prompt generation.

Takes a long answer text, splits it into meaningful visual scenes,
and converts each scene into a short prompt suitable for text-to-video models.
"""

import os
import re
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
_MODEL = "openai/gpt-4o-mini"

MIN_SCENE_LENGTH = 40
MAX_SCENES = 3

VISUAL_STYLES = [
    "clean infographic animation with smooth transitions",
    "3D animated diagram with arrows and labels",
    "cinematic educational animation with flowing visuals",
]


# ---------------------------------------------------------------------------
# Scene extraction
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Strip source blocks, citations, and noisy formatting from RAG output."""
    text = re.sub(r"=== SOURCE TEXT ===.*?=== EXPLANATION ===", "", text, flags=re.DOTALL)
    text = re.sub(r"\[?\d+\]?\s*\(Source:.*?\)", "", text)
    text = re.sub(r"—\s*.*?,\s*Page\s*\d+", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _split_scenes_llm(text: str) -> list[str]:
    """Use LLM to split text into 2-4 meaningful visual scenes."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You split educational text into 2-4 visual scenes for a short video. "
                    "Each scene should capture ONE clear concept or idea. "
                    "Return a JSON array of strings, each string is one scene's text. "
                    "Keep each scene concise (1-3 sentences). "
                    "Return ONLY valid JSON, nothing else."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=1000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _split_scenes_fallback(text: str) -> list[str]:
    """Split by paragraphs or sentence groups when LLM is unavailable."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= MIN_SCENE_LENGTH]
    if paragraphs:
        return paragraphs

    sentences = re.split(r"(?<=[.!?])\s+", text)
    scenes = []
    for i in range(0, len(sentences), 3):
        chunk = " ".join(sentences[i : i + 3]).strip()
        if len(chunk) >= MIN_SCENE_LENGTH:
            scenes.append(chunk)
    return scenes or [text]


def extract_scenes(text: str) -> list[str]:
    """Extract clean, filtered scenes from answer text."""
    text = _clean_text(text)
    if not text:
        return []

    try:
        scenes = _split_scenes_llm(text)
    except Exception:
        scenes = _split_scenes_fallback(text)

    # Filter short/noisy scenes, cap at MAX_SCENES
    scenes = [s.strip() for s in scenes if isinstance(s, str) and len(s.strip()) >= MIN_SCENE_LENGTH]
    return scenes[:MAX_SCENES]


# ---------------------------------------------------------------------------
# Visual prompt generation
# ---------------------------------------------------------------------------

def _scene_to_prompt_llm(scene: str, style: str) -> str:
    """Use LLM to convert a scene description into a short visual prompt."""
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Convert the following educational text into a SHORT visual prompt "
                    "for a text-to-video AI model. "
                    "The prompt must describe a VISUAL SCENE, not explain a concept. "
                    "Use concrete imagery: objects, colors, motion, layout. "
                    f"Style: {style}. "
                    "Max 30 words. Return ONLY the prompt text, nothing else."
                ),
            },
            {"role": "user", "content": scene},
        ],
        temperature=0.7,
        max_tokens=80,
    )
    return response.choices[0].message.content.strip().strip('"')


def _scene_to_prompt_fallback(scene: str, style: str) -> str:
    """Build a visual prompt without LLM."""
    words = scene.split()[:12]
    summary = " ".join(words)
    return f"{summary}, {style}"


def build_prompts(scenes: list[str]) -> list[str]:
    """Convert a list of scene texts into visual video prompts."""
    prompts = []
    for i, scene in enumerate(scenes):
        style = VISUAL_STYLES[i % len(VISUAL_STYLES)]
        try:
            prompt = _scene_to_prompt_llm(scene, style)
        except Exception:
            prompt = _scene_to_prompt_fallback(scene, style)
        prompts.append(prompt)
    return prompts
