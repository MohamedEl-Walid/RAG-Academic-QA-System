"""Generate video clips via the HuggingFace Space API."""

import os
import shutil

from gradio_client import Client

SPACE_NAME = "xxx4playxxx/ai-video-creator"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "clips")

# Default generation parameters
_DEFAULTS = {
    "height": 480,
    "width": 832,
    "negative_prompt": "blurry, low quality, distorted, ugly, bad anatomy, grainy",
    "duration_seconds": 3,
    "guidance_scale": 5.0,
    "steps": 20,
    "seed": 42,
    "randomize_seed": True,
}


def _get_client() -> Client:
    """Lazy-connect to the HuggingFace Space."""
    return Client(SPACE_NAME)


def generate_clip(prompt: str, output_path: str, **overrides) -> str:
    """Generate a single video clip from a visual prompt.

    Args:
        prompt: Visual description for the video model.
        output_path: Where to save the resulting .mp4 file.
        **overrides: Override any default generation parameter.

    Returns:
        Path to the saved video file.
    """
    params = {**_DEFAULTS, **overrides}
    client = _get_client()

    result = client.predict(
        prompt=prompt,
        height=params["height"],
        width=params["width"],
        negative_prompt=params["negative_prompt"],
        duration_seconds=params["duration_seconds"],
        guidance_scale=params["guidance_scale"],
        steps=params["steps"],
        seed=params["seed"],
        randomize_seed=params["randomize_seed"],
        api_name="/generate_video",
    )

    # result is (dict(video=filepath, subtitles=...), seed)
    video_info = result[0] if isinstance(result, tuple) else result
    source_path = video_info["video"] if isinstance(video_info, dict) else video_info

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copy2(source_path, output_path)
    return output_path


def generate_clips(prompts: list[str], output_dir: str = None) -> list[str]:
    """Generate one clip per prompt and return the list of saved paths."""
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    paths = []
    for i, prompt in enumerate(prompts):
        filename = os.path.join(output_dir, f"scene_{i}.mp4")
        path = generate_clip(prompt, filename)
        paths.append(path)
    return paths
