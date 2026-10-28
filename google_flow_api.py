"""
google_flow_api.py - Google Flow Image API Integration (via useapi.net)
========================================================================
Supports:
  - Nano Banana 2 Lite ('nano-banana-2-lite', Gemini 3.1 Flash-Lite Image) [Fastest & 0 credits / free on Google Flow]
  - Nano Banana 2.1 ('nano-banana-2')
  - Nano Banana Pro ('nano-banana-pro', Gemini 3 Pro Image)
Features:
  - Text-to-Image high-definition packaging generation
  - Image-to-Image generation using reference assets
  - Automatic download and base64/data-URI conversion
"""

import os
import io
import sys
import time
import json
import base64
import urllib.parse
import urllib.request
import urllib.error
import requests
from typing import Optional, List, Dict, Any, Union
from PIL import Image

URL_ACCOUNTS = "https://api.useapi.net/v1/google-flow/accounts"
URL_IMAGES = "https://api.useapi.net/v1/google-flow/images"
URL_ASSETS = "https://api.useapi.net/v1/google-flow/assets/"

DEFAULT_MODEL = "nano-banana-2-lite"
USER_AGENT = "google-flow-images.py"


def get_credentials(api_token: Optional[str] = None, email: Optional[str] = None) -> tuple:
    """Retrieves Google Flow / useapi.net credentials from arguments or environment."""
    token = api_token or os.getenv("GOOGLE_FLOW_API_TOKEN") or os.getenv("USEAPI_TOKEN")
    acc_email = email or os.getenv("GOOGLE_FLOW_EMAIL")
    return token, acc_email


def check_account_health(api_token: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    """Checks the health and status of connected Google Flow accounts."""
    token, acc_email = get_credentials(api_token, email)
    if not token:
        raise ValueError("GOOGLE_FLOW_API_TOKEN or USEAPI_TOKEN is not configured in .env")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }
    resp = requests.get(URL_ACCOUNTS, headers=headers, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Error fetching accounts (HTTP {resp.status_code}): {resp.text}")

    accounts = resp.json()
    if acc_email:
        if acc_email not in accounts:
            raise RuntimeError(f"Account {acc_email} not found in configured Google Flow accounts.")
        return accounts[acc_email]
    return accounts


def upload_reference_asset(image_data: Union[bytes, str], email: str, api_token: str) -> str:
    """
    Uploads a reference image to Google Flow asset storage and returns mediaGenerationId.
    image_data can be raw bytes, a local filepath, or a base64 data URI.
    """
    if isinstance(image_data, str):
        if image_data.startswith("data:"):
            _, b64data = image_data.split(",", 1)
            raw_bytes = base64.b64decode(b64data)
            content_type = "image/png"
        elif os.path.exists(image_data):
            ext = image_data.split(".").pop().lower()
            content_type = "image/png" if ext == "png" else "image/webp" if ext == "webp" else "image/jpeg"
            with open(image_data, "rb") as f:
                raw_bytes = f.read()
        else:
            try:
                raw_bytes = base64.b64decode(image_data)
                content_type = "image/png"
            except Exception:
                raise ValueError(f"Invalid image file or data provided for upload: {image_data}")
    elif isinstance(image_data, bytes):
        raw_bytes = image_data
        content_type = "image/png"
    else:
        raise ValueError("Unsupported image data type for asset upload.")

    encoded_email = urllib.parse.quote(email, safe="")
    url = f"{URL_ASSETS}{encoded_email}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_token}",
        "Content-Type": content_type,
        "User-Agent": USER_AGENT,
    }

    resp = requests.post(url, headers=headers, data=raw_bytes, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Asset upload failed (HTTP {resp.status_code}): {resp.text}")

    res_json = resp.json()
    media_gen_id = (res_json or {}).get("mediaGenerationId", {})
    if isinstance(media_gen_id, dict):
        media_id = media_gen_id.get("mediaGenerationId")
    else:
        media_id = str(media_gen_id)

    if not media_id:
        raise RuntimeError(f"Could not extract mediaGenerationId from response: {res_json}")

    return media_id


def map_aspect_ratio(ratio: str) -> str:
    """Maps custom aspect ratios to Google Flow supported values."""
    ratio_str = str(ratio).lower().strip()
    mapping = {
        "1:1": "1:1",
        "16:9": "16:9",
        "9:16": "9:16",
        "4:3": "4:3",
        "3:4": "3:4",
        "21:9": "16:9",
        "3:1": "16:9",
        "4:1": "16:9",
        "8:1": "16:9",
        "11:31.5": "9:16",
        "31.5:11": "16:9",
        "14.2:45.2": "9:16",
        "45.2:14.2": "16:9",
        "auto": "auto",
    }
    return mapping.get(ratio_str, "1:1")


def generate_google_flow_image(
    prompt: str,
    model: str = "nano-banana-2-lite",
    aspect_ratio: str = "1:1",
    count: int = 1,
    seed: Optional[int] = None,
    reference_images: Optional[List[Union[str, bytes]]] = None,
    api_token: Optional[str] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates images using Google Flow Image API (via useapi.net).
    Returns dict containing list of images as bytes and data-URIs.
    """
    token, acc_email = get_credentials(api_token, email)
    if not token or token.startswith("your_"):
        raise ValueError(
            "Google Flow API token is missing. Please set GOOGLE_FLOW_API_TOKEN (or USEAPI_TOKEN) in your .env file."
        )
    if not acc_email:
        raise ValueError(
            "Google Flow account email is missing. Please set GOOGLE_FLOW_EMAIL in your .env file."
        )

    allowed_models = ["nano-banana-2-lite", "nano-banana-2", "nano-banana-pro"]
    use_model = model if model in allowed_models else DEFAULT_MODEL
    mapped_ar = map_aspect_ratio(aspect_ratio)

    body: Dict[str, Any] = {
        "model": use_model,
        "email": acc_email,
        "prompt": prompt.strip(),
        "aspectRatio": mapped_ar,
        "count": min(4, max(1, count)),
    }

    if seed is not None:
        body["seed"] = int(seed)

    # Handle reference images (up to 10 accepted)
    if reference_images:
        for idx, ref in enumerate(reference_images[:10]):
            ref_key = f"reference_{idx + 1}"
            media_id = upload_reference_asset(ref, email=acc_email, api_token=token)
            body[ref_key] = media_id

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT,
    }

    resp = requests.post(URL_IMAGES, headers=headers, json=body, timeout=120)

    if resp.status_code == 402:
        raise RuntimeError("Google Flow API error (HTTP 402): Insufficient credits or subscription required.")
    if resp.status_code == 429:
        raise RuntimeError("Google Flow API rate limit exceeded (HTTP 429). Please retry in a few moments.")
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Google Flow API failed (HTTP {resp.status_code}): {resp.text}")

    res_json = resp.json()
    media_list = (res_json or {}).get("media") or []
    if not media_list:
        raise RuntimeError(f"Google Flow returned 200 OK but media list is empty: {res_json}")

    results = []
    for item in media_list:
        gen_img = ((item or {}).get("image") or {}).get("generatedImage") or {}
        fife_url = gen_img.get("fifeUrl")
        encoded_image = gen_img.get("encodedImage")

        img_bytes = None
        if fife_url:
            dl_resp = requests.get(fife_url, timeout=40)
            if dl_resp.status_code == 200:
                img_bytes = dl_resp.content

        if not img_bytes and encoded_image:
            img_bytes = base64.b64decode(encoded_image)

        if img_bytes:
            b64_str = base64.b64encode(img_bytes).decode("ascii")
            data_uri = f"data:image/jpeg;base64,{b64_str}"
            results.append({
                "bytes": img_bytes,
                "data_uri": data_uri,
                "fife_url": fife_url,
            })

    if not results:
        raise RuntimeError("Could not download or decode any generated images from Google Flow response.")

    return {
        "success": True,
        "images": results,
        "primary_data_uri": results[0]["data_uri"],
        "primary_bytes": results[0]["bytes"],
        "primary_url": results[0]["fife_url"] or results[0]["data_uri"],
        "model": use_model,
        "prompt": prompt,
        "count": len(results),
    }
