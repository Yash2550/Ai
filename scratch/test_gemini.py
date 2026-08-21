import os, json, requests
from dotenv import load_dotenv

load_dotenv()
url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent?key=' + os.getenv("GEMINI_API_KEY")
payload = {
    "contents": [{"parts": [{"text": "a cute cat"}]}],
}
resp = requests.post(url, json=payload)
print(resp.status_code)
print(resp.text[:500])
