"""
Canva Official REST API Integration Module
===========================================
Handles OAuth2 authentication, image asset upload, design creation,
and asynchronous image-to-design conversion using Canva's Official REST API v1.
Ref: Canva REST APIs version 2024-06-18
"""

import os
import time
import requests
import base64
from typing import Dict, Any, Optional

CANVA_API_BASE = "https://api.canva.com/rest"
CANVA_CLIENT_ID = os.environ.get("CANVA_CLIENT_ID", "")
CANVA_CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET", "")
CANVA_ACCESS_TOKEN = os.environ.get("CANVA_ACCESS_TOKEN", "")

def get_auth_headers(token: Optional[str] = None) -> Dict[str, str]:
    auth_token = token or CANVA_ACCESS_TOKEN or os.environ.get("CANVA_ACCESS_TOKEN", "")
    if not auth_token:
        raise ValueError("Canva Access Token is not configured. Set CANVA_ACCESS_TOKEN in .env.")
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

def upload_asset_to_canva(image_path: str, name: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Uploads an image file to Canva as an asset.
    POST /v1/assets
    """
    headers = {
        "Authorization": f"Bearer {token or CANVA_ACCESS_TOKEN}",
        "Asset-Upload-Metadata": f'{{"name_base64":"{base64.b64encode((name or os.path.basename(image_path)).encode("utf-8")).decode("ascii")}"}}'
    }
    with open(image_path, "rb") as f:
        file_bytes = f.read()

    url = f"{CANVA_API_BASE}/v1/assets"
    res = requests.post(url, headers=headers, data=file_bytes, timeout=60)
    if res.status_code not in (200, 201):
        raise RuntimeError(f"Canva Asset Upload failed: {res.status_code} - {res.text}")
    return res.json()

def create_image_to_design_job(asset_id: str, title: str = "Imported Label Design", token: Optional[str] = None) -> Dict[str, Any]:
    """
    Starts an asynchronous job to import an image asset into an editable Canva Design.
    POST /v1/image-to-design-imports
    """
    headers = get_auth_headers(token)
    payload = {
        "asset_id": asset_id,
        "title": title
    }
    url = f"{CANVA_API_BASE}/v1/image-to-design-imports"
    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code not in (200, 201, 202):
        raise RuntimeError(f"Canva Image-To-Design Job failed: {res.status_code} - {res.text}")
    return res.json()

def get_image_to_design_job_status(job_id: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the status of an image-to-design import job.
    GET /v1/image-to-design-imports/{jobId}
    """
    headers = get_auth_headers(token)
    url = f"{CANVA_API_BASE}/v1/image-to-design-imports/{job_id}"
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Canva Job Query failed: {res.status_code} - {res.text}")
    return res.json()

def get_design_url(design_id: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets design metadata and edit URL.
    GET /v1/designs/{designId}
    """
    headers = get_auth_headers(token)
    url = f"{CANVA_API_BASE}/v1/designs/{design_id}"
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != 200:
        raise RuntimeError(f"Canva Get Design failed: {res.status_code} - {res.text}")
    return res.json()

