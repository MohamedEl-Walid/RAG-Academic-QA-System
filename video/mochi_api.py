from gradio_client import Client
import os

SPACE_NAME = "genmo/mochi-1-preview"

print("Connecting to Mochi...")
client = Client(SPACE_NAME)


def generate_video(prompt: str, output_path: str = "output.mp4"):
    print("Generating video... (may take time)")

    result = client.predict(
        prompt=prompt,
        negative_prompt="low quality, blurry, bad anatomy",
        api_name="/generate_video"
    )

    print("Video saved at:", result)

    if os.path.exists(result):
        os.rename(result, output_path)

    return output_path