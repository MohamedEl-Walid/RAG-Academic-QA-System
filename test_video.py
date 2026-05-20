import replicate

print("Generating video...")

output = replicate.run(
    "cerspense/zeroscope-v2-xl",
    input={
        "prompt": "a futuristic AI system explaining expert systems, clean infographic animation",
        "num_frames": 24,
        "fps": 8,
        "guidance_scale": 7.5
    }
)

print(output)