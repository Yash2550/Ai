import requests
import json

h = {"Authorization": "Bearer 1nfsh-1ebkjap2k7mng0p7zg2a2sw66n"}
r = requests.get("https://api.inference.sh/v1/store/apps", headers=h).json()
items = r.get("data", {}).get("items", [])
print(f"Total fetched: {len(items)}")
for item in items:
    app_id = f"{item.get('namespace')}/{item.get('name')}"
    category = item.get("category")
    print(f"App: {app_id} | Category: {category}")
