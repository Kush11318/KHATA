import os
import requests
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {key}"}

try:
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    models = res.json()["data"]
    for m in models:
        print(m["id"])
except Exception as e:
    print("Error listing Groq models:", e)
