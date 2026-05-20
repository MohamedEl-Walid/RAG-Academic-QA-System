from gradio_client import Client

print("Connecting...")

client = Client("xxx4playxxx/ai-video-creator")

print("Generating video... (this may take time ⏳)")

result = client.predict(
    prompt="AI expert system explaining knowledge base and inference engine, clean infographic animation",
    height=480,
    width=832,
    negative_prompt="blurry, low quality, distorted",
    duration_seconds=3,
    guidance_scale=5,
    steps=20,
    seed=42,
    randomize_seed=True,
    api_name="/generate_video"
)

print("Result:", result)