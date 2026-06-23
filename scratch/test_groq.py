import os
from dotenv import load_dotenv
load_dotenv()

import requests
import base64

groq_key = os.environ.get("GROQ_API_KEY")
if not groq_key:
    print("GROQ_API_KEY not found in environment.")
    exit(1)

print("GROQ_API_KEY found:", groq_key[:8])

# Test 1: Chat Completion / Text model
def test_text():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Output a JSON object with a key 'reply'."},
            {"role": "user", "content": "Hello! Say hi."}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        print("Text response:", response.json())
    except Exception as e:
        print("Text failed:", e)

# Test 2: Vision Model
def test_vision():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    # Create a tiny 1x1 red PNG base64
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    payload = {
        "model": "llama-3.2-11b-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Identify the color of this image. Return a JSON object with 'color'."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{tiny_png_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        print("Vision response:", response.json())
    except Exception as e:
        print("Vision failed:", e)
        if hasattr(e, 'response') and e.response is not None:
            print("Response details:", e.response.text)

if __name__ == "__main__":
    print("Testing Groq Text...")
    test_text()
    print("Testing Groq Vision...")
    test_vision()
