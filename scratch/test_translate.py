import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def test_translation(text: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"Translate the following text to English. If it is already in English, just output it exactly as is. Output ONLY the translated English text without quotes or explanations.\n\nText: {text}"}]}]
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    try:
        translated = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"Original: {text}")
        print(f"Translated: {translated}")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_translation("mane ek navi image banavi aapo")
    test_translation("मुझे एक नया लेबल चाहिए")
    test_translation("A new professional label with chocolate flavor")
