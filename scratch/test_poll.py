import requests
import time

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
resp = requests.post(url, headers=headers, json=payload, timeout=60).json()
task_id = resp.get("id")
print("Task launched:", task_id)

for i in range(15):
    time.sleep(2)
    check = requests.get(f"https://api.inference.sh/tasks/{task_id}", headers=headers).json()
    print(f"Poll {i+1}: status={check.get('status_text')}, output={check.get('output')}")
    if check.get("status_text") == "completed" or check.get("output"):
        break
