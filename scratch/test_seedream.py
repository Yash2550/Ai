import requests

url = "https://api.inference.sh/apps/run"
headers = {
    "Authorization": "Bearer 1nfsh-1ebkjap2k7mng0p7zg2a2sw66n",
    "Content-Type": "application/json",
    "X-API-Version": "2"
}
payload = {
    "app": "bytedance/seedream-5-pro",
    "input": {
        "prompt": "A modern sleek protein powder container product label design"
    }
}
resp = requests.post(url, headers=headers, json=payload, timeout=60)
print("Status:", resp.status_code)
print("Response:", resp.text[:500])
