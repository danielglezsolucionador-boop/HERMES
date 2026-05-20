import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

payload = {
    "model": "google/gemini-3.5-flash",
    "max_tokens": 10,
    "messages": [
        {
            "role": "user",
            "content": "hola"
        }
    ]
}

print(payload)

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    json=payload
)

print(response.status_code)
print(response.text)