import requests
import os

HF_API_KEY = os.getenv("HF_API_KEY")

MODEL = "stabilityai/stable-diffusion-2"

def generate_image(prompt: str, filename: str):
    url = f"https://api-inference.huggingface.co/models/{MODEL}"

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    payload = {
        "inputs": prompt
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(response.text)

    with open(filename, "wb") as f:
        f.write(response.content)

    return filename