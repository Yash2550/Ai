import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = 'https://api.openai.com/v1/images/generations'
headers = {'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'}
payload = {'model': 'dall-e-3', 'prompt': 'test', 'n': 1, 'size': '1024x1024'}
resp = requests.post(url, headers=headers, json=payload)
print(resp.status_code)
print(resp.text)
