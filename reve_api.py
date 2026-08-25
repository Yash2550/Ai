import os
import requests
import base64

def digitize_image_via_reve(image_path: str) -> dict:
    """
    Sends an image to the official REVE API for perfect layout digitization.
    Returns a Fabric.js compatible JSON structure.
    """
    # Replace this with the actual REVE API endpoint you have
    REVE_API_ENDPOINT = os.environ.get("REVE_API_ENDPOINT", "https://api.reve.com/v1/digitize")
    REVE_API_KEY = os.environ.get("REVE_API_KEY")
    
    if not REVE_API_KEY:
        raise ValueError("REVE_API_KEY is not configured in environment variables.")
        
    headers = {
        "Authorization": f"Bearer {REVE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Read image as base64
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "image": f"data:image/png;base64,{b64_image}",
        "task": "digitize_to_fabric"
    }
    
    try:
        response = requests.post(REVE_API_ENDPOINT, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            # Assuming the API returns a JSON object directly usable by Fabric.js
            return response.json()
        else:
            raise RuntimeError(f"Reve API Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to connect to Reve API: {e}")
