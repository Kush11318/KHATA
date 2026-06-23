import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

keys = [
    os.environ.get("GEMINI_API_KEY"),
    os.environ.get("GEMINI_API_KEY_2")
]

for i, key in enumerate(keys):
    if not key:
        continue
    print(f"--- Key {i+1} (prefix: {key[:8]}) ---")
    try:
        client = genai.Client(api_key=key.strip())
        print("Successfully created client.")
        # List models
        models = client.models.list()
        for m in models:
            if "flash" in m.name or "pro" in m.name:
                print(f"Model: {m.name}")
    except Exception as e:
        print(f"Error listing models with key {i+1}: {e}")
