"""End-to-end pipeline: answer text → scenes → visual prompts → video clips."""

from video.prompt_builder import extract_scenes, build_prompts
from video.video_generator import generate_clips


def generate_video_from_answer(answer: str) -> list[str]:
    """Convert a RAG answer into a list of short video clips.

    Steps:
        1. Split the answer into 2-3 meaningful visual scenes.
        2. Convert each scene into a short visual prompt.
        3. Send each prompt to the HuggingFace video generation Space.

    Returns:
        List of file paths to the generated .mp4 clips.
    """
    scenes = extract_scenes(answer)
    if not scenes:
        return []

    prompts = build_prompts(scenes)
    if not prompts:
        return []

    return generate_clips(prompts)
