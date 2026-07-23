"""
Label Inpainter - Flask Application (Recraft.ai version)
=====================================
A local Flask web server that connects to the Recraft.ai API to perform
high-quality generative in-painting (object removal & reconstruction) on
product label images.

Workflow:
  1. User uploads an image and provides a text prompt.
  2. Flask auto-generates a mask using a local CLIPSeg model.
  3. The mask + image are uploaded to Recraft.ai In-Painting for reconstruction.
  4. The finished image is returned and displayed in the browser.
"""

import os
import base64
import time
import uuid
import requests
import urllib.parse
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
import io
from dotenv import load_dotenv
from database import init_db, db
from models import UploadedImage, JobHistory

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv(override=True)  # reads updated values from .env file (auto-reloaded)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Database init
# ---------------------------------------------------------------------------
init_db(app)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER = os.path.join("static", "uploads")
RESULTS_FOLDER = os.path.join("static", "results")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB upload limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULTS_FOLDER"] = RESULTS_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
RECRAFT_API_KEY = os.getenv("RECRAFT_API_KEY")
if RECRAFT_API_KEY:
    RECRAFT_API_KEY = RECRAFT_API_KEY.strip("'\"")

NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY")
if NANOBANANA_API_KEY:
    NANOBANANA_API_KEY = NANOBANANA_API_KEY.strip("'\"")

# Base URL for Nano Banana API — override via NANOBANANA_BASE_URL in .env if the domain changes
NANOBANANA_BASE_URL = os.getenv("NANOBANANA_BASE_URL", "https://api.nanobananaapi.dev").rstrip("/")

REVE_API_KEY = os.getenv("REVE_API_KEY")
if REVE_API_KEY:
    REVE_API_KEY = REVE_API_KEY.strip("'\"")
REVE_BASE_URL = os.getenv("REVE_BASE_URL", "https://api.reve.com/v2").rstrip("/")



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
import difflib
import re

def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def image_to_data_uri(path: str) -> str:
    """Read an image from disk and return a data URI (base64 encoded)."""
    ext = path.rsplit(".", 1)[1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def extract_mask_target_from_prompt(prompt: str) -> str:
    """
    Parse prompt to identify what text/element we want to locate on the image.
    e.g., 'Remove Gomzi Nutrition and add Maxlife' -> 'Gomzi Nutrition'
          'Replace brand name with Maxlife' -> 'brand name'
    """
    p_lower = prompt.lower()
    
    # 1. Matches "remove X and add Y", "remove X and replace with Y", etc.
    remove_pattern = re.search(r'remove\s+(.*?)\s+(and|to|with|add)\s+', p_lower)
    if remove_pattern:
        return remove_pattern.group(1).strip()
        
    # 2. Matches "replace X with Y" / "replace X by Y" / "replace X to Y"
    replace_pattern = re.search(r'replace\s+(.*?)\s+(with|by|to)\s+', p_lower)
    if replace_pattern:
        return replace_pattern.group(1).strip()
        
    # 3. Matches "change X to Y" / "change X with Y"
    change_pattern = re.search(r'change\s+(.*?)\s+(to|with)\s+', p_lower)
    if change_pattern:
        return change_pattern.group(1).strip()

    # Fallback to the original prompt
    return prompt


# ---------------------------------------------------------------------------
# CLIPSeg Local Mask Generation
# ---------------------------------------------------------------------------
_clipseg_processor = None
_clipseg_model = None

def generate_mask_with_clipseg(image_data_uri: str, prompt: str) -> str:
    """
    Use CLIPSeg locally via transformers to generate a binary mask from a text prompt.
    Returns the mask as a data URI string.

    If CLIPSeg is unavailable or fails, we generate a simple centre-region
    mask as a graceful fallback (useful during development without credits).
    """
    global _clipseg_processor, _clipseg_model
    try:
        import torch
        # pyrefly: ignore [missing-import]
        from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation
        
        # Decode image to get dimensions and raw PIL image
        header, b64data = image_data_uri.split(",", 1)
        img_bytes = base64.b64decode(b64data)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size

        # Lazy load model and processor to speed up startup time
        if _clipseg_model is None:
            app.logger.info("Loading local CLIPSeg model (CIDAS/clipseg-rd64-refined) on CPU...")
            _clipseg_processor = CLIPSegProcessor.from_pretrained("CIDAS/clipseg-rd64-refined")
            _clipseg_model = CLIPSegForImageSegmentation.from_pretrained("CIDAS/clipseg-rd64-refined")
            app.logger.info("CLIPSeg model loaded successfully.")

        # Run inference
        inputs = _clipseg_processor(text=[prompt], images=[img], padding="max_length", return_tensors="pt")
        with torch.no_grad():
            outputs = _clipseg_model(**inputs)
        
        # Post-process logits
        logits = outputs.logits
        preds = torch.sigmoid(logits)
        
        # Convert prediction to numpy array (values 0..255)
        mask_array = (preds[0].cpu().numpy() * 255).astype("uint8")
        mask_img = Image.fromarray(mask_array)
        
        # Resize mask back to original image size
        mask_img = mask_img.resize((w, h), Image.Resampling.LANCZOS)
        
        # Binarize the mask: values > threshold are white (255), rest black (0)
        # 100 out of 255 represents a threshold of ~0.4 confidence
        mask_img = mask_img.point(lambda p: 255 if p > 100 else 0)

        # Save mask as PNG to memory buffer
        buf = io.BytesIO()
        mask_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    except Exception as exc:
        app.logger.warning(
            "Local CLIPSeg mask generation failed (%s). Using fallback mask.", exc
        )
        return _generate_fallback_mask(image_data_uri)


def _generate_fallback_mask(image_data_uri: str) -> str:
    """
    Generate a simple white center-region mask as a Pillow-created PNG  .
    This is used when CLIPSeg is unavailable so the pipeline can still run.
    """
    # Decode image to get dimensions
    header, b64data = image_data_uri.split(",", 1)
    img_bytes = base64.b64decode(b64data)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
        
    # Create a black mask with a white rectangle in the center 40%
    mask = Image.new("L", (w, h), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    x0, y0 = int(w * 0.3), int(h * 0.3)
    x1, y1 = int(w * 0.7), int(h * 0.7)
    draw.rectangle([x0, y0, x1, y1], fill=255)

    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# PIL-based Professional Text Replacement
# ---------------------------------------------------------------------------
# Font candidates (best → fallback) for brand text rendering
_FONT_PATHS = [
    "C:/Windows/Fonts/bahnschrift.ttf",   # Modern, clean sans-serif
    "C:/Windows/Fonts/seguibl.ttf",       # Segoe UI Black — very bold
    "C:/Windows/Fonts/arialbd.ttf",       # Arial Bold
    "C:/Windows/Fonts/impact.ttf",        # Impact — wide/heavy
    "C:/Windows/Fonts/verdanab.ttf",      # Verdana Bold
]

def _get_font(size: int):
    """Load the best available bold font at the given size."""
    from PIL import ImageFont
    for fp in _FONT_PATHS:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _sample_bg_color(img_rgb: "Image.Image", mask_l: "Image.Image") -> tuple:
    """
    Sample the dominant background color just outside the masked region.
    Expands the bounding box by ~15% and samples pixels that are NOT in the mask.
    Falls back to the median color inside the mask if nothing useful found outside.
    """
    import numpy as np
    bbox = mask_l.getbbox()
    if not bbox:
        return (240, 240, 240)

    left, top, right, bottom = bbox
    w_img, h_img = img_rgb.size
    pad_x = max(10, int((right - left) * 0.15))
    pad_y = max(10, int((bottom - top) * 0.15))

    # Expand outward region
    x0 = max(0, left - pad_x)
    y0 = max(0, top - pad_y)
    x1 = min(w_img, right + pad_x)
    y1 = min(h_img, bottom + pad_y)

    region_img  = np.array(img_rgb.crop((x0, y0, x1, y1)))
    region_mask = np.array(mask_l.crop((x0, y0, x1, y1)))

    # Pixels outside the mask (background)
    outside = region_img[region_mask < 128]
    if len(outside) > 10:
        median_color = tuple(int(v) for v in np.median(outside, axis=0))
        return median_color

    # Fallback: median inside mask
    inside = region_img[region_mask >= 128]
    if len(inside) > 0:
        return tuple(int(v) for v in np.median(inside, axis=0))

    return (240, 240, 240)


def _pick_text_color(bg: tuple) -> tuple:
    """Pick black or white text color for best contrast against bg."""
    r, g, b = bg
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return (10, 10, 10) if luminance > 0.55 else (245, 245, 245)


def professional_text_replace(
    image_path: str,
    mask_data_uri: str,
    new_text: str,
    output_path: str,
    bold: bool = True,
    uppercase: bool = True,
    padding_ratio: float = 0.12,
) -> None:
    """
    Replace the masked region with a clean background fill and render new_text
    in a bold professional font perfectly centred in the bounding box.

    Steps:
      1. Decode mask, find bounding box of the brand/logo region.
      2. Sample background color from pixels just outside the masked area.
      3. Fill the mask area with that background (seamless erase).
      4. Auto-size a bold font to fill ~80% of the box height.
      5. Render the new brand text centred, with a subtle drop-shadow for depth.
      6. Save result.
    """
    from PIL import ImageDraw, ImageFilter
    import numpy as np

    # Load images
    base = Image.open(image_path).convert("RGB")
    w_img, h_img = base.size

    # Decode mask
    _, b64data = mask_data_uri.split(",", 1)
    mask_bytes = base64.b64decode(b64data)
    mask_l = Image.open(io.BytesIO(mask_bytes)).convert("L")
    mask_l = mask_l.resize((w_img, h_img), Image.Resampling.LANCZOS)

    bbox = mask_l.getbbox()
    if not bbox:
        # Nothing to mask — just save original
        base.save(output_path, "PNG")
        return

    left, top, right, bottom = bbox
    box_w = right - left
    box_h = bottom - top

    # ── 1. Sample background color ──────────────────────────────────────────
    bg_color = _sample_bg_color(base, mask_l)

    # ── 2. Fill masked region with background (feathered edges) ────────────
    result = base.copy()
    draw_fill = ImageDraw.Draw(result)

    # Slightly expand fill to cover anti-aliased edges
    pad = max(2, int(min(box_w, box_h) * 0.03))
    fill_box = (
        max(0, left - pad),
        max(0, top - pad),
        min(w_img, right + pad),
        min(h_img, bottom + pad),
    )
    draw_fill.rectangle(fill_box, fill=bg_color)

    # Soft feather: blend the sharp fill edges into the original
    mask_blur = mask_l.filter(ImageFilter.GaussianBlur(radius=max(2, pad)))
    result = Image.composite(result, base, mask_blur)

    # ── 3. Prepare text ──────────────────────────────────────────────────────
    display_text = new_text.upper().strip() if uppercase else new_text.strip()

    # Remove common instruction words that aren't the brand name
    # e.g. "Remove Gomzi Nutrition and add Maxlife" → extract "Maxlife"
    # Only do this if text contains common instruction words
    instruction_words = {"remove", "delete", "erase", "replace", "add", "put", "insert", "change", "with"}
    words = display_text.lower().split()
    if any(w in instruction_words for w in words):
        # Heuristic: take the last word/words after "add", "with", "insert", "replace"
        triggers = ["add", "with", "insert", "replace", "put"]
        best_idx = -1
        for trigger in triggers:
            idx = display_text.lower().rfind(trigger)
            if idx > best_idx:
                best_idx = idx
                trigger_len = len(trigger)
        if best_idx >= 0:
            remainder = display_text[best_idx + trigger_len:].strip()
            if remainder:
                display_text = remainder

    # ── 4. Auto-size font to fill ~80 % of box height (max width clamp) ────
    target_h = int(box_h * 0.70)
    font_size = max(12, target_h)

    font = _get_font(font_size)
    draw_tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox_text = draw_tmp.textbbox((0, 0), display_text, font=font)
    text_w = bbox_text[2] - bbox_text[0]
    text_h = bbox_text[3] - bbox_text[1]

    # Shrink if text overflows box width (with padding)
    max_text_w = int(box_w * (1 - 2 * padding_ratio))
    if text_w > max_text_w and text_w > 0:
        font_size = int(font_size * max_text_w / text_w)
        font_size = max(8, font_size)
        font = _get_font(font_size)
        bbox_text = draw_tmp.textbbox((0, 0), display_text, font=font)
        text_w = bbox_text[2] - bbox_text[0]
        text_h = bbox_text[3] - bbox_text[1]

    # ── 5. Render text centred in bounding box ───────────────────────────────
    text_x = left + (box_w - text_w) // 2 - bbox_text[0]
    text_y = top  + (box_h - text_h) // 2 - bbox_text[1]

    text_color = _pick_text_color(bg_color)
    draw = ImageDraw.Draw(result)

    # Drop shadow for depth (2–4 px offset)
    shadow_offset = max(1, font_size // 30)
    shadow_color = (0, 0, 0) if text_color != (10, 10, 10) else (200, 200, 200)
    draw.text(
        (text_x + shadow_offset, text_y + shadow_offset),
        display_text,
        font=font,
        fill=(*shadow_color, 120),
    )

    # Main text
    draw.text((text_x, text_y), display_text, font=font, fill=text_color)

    # ── 6. Save ─────────────────────────────────────────────────────────────
    result.save(output_path, "PNG")
    app.logger.info(
        "PIL text replace: '%s' → rendered at font_size=%d in box %s bg=%s",
        display_text, font_size, bbox, bg_color,
    )


# Recraft.ai In-Painting API Call
# ---------------------------------------------------------------------------
def run_recraft_inpainting(
    image_path: str,
    mask_path: str,
    prompt: str,
    negative_prompt: str = None,
) -> str:
    """
    Call Recraft.ai inpainting API with the image, mask, and prompt.
    Returns the URL of the final inpainted image.
    """
    if not RECRAFT_API_KEY:
        raise RuntimeError("RECRAFT_API_KEY is not configured.")

    url = "https://external.api.recraft.ai/v1/images/inpaint"
    headers = {
        "Authorization": f"Bearer {RECRAFT_API_KEY}",
    }

    # Open files for multipart upload
    with open(image_path, "rb") as img_file, open(mask_path, "rb") as mask_file:
        files = {
            "image": (os.path.basename(image_path), img_file, "image/png"),
            "mask": (os.path.basename(mask_path), mask_file, "image/png"),
        }
        data = {
            "prompt": prompt,
            "response_format": "url",
        }
        if negative_prompt:
            data["negative_prompt"] = negative_prompt

        app.logger.info("Sending request to Recraft.ai API...")
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        
        if resp.status_code != 200:
            error_msg = f"Recraft.ai API returned error {resp.status_code}: {resp.text}"
            app.logger.error(error_msg)
            raise RuntimeError(error_msg)

        result = resp.json()
        data_list = result.get("data", [])
        if not data_list or "url" not in data_list[0]:
            raise RuntimeError(f"Unexpected response structure from Recraft: {result}")

        return data_list[0]["url"]


def composite_image_addition(image_path: str, mask_path: str, overlay_path: str, output_path: str):
    """
    Composite the overlay image onto the original image inside the masked region.
    """
    # Load images
    base_img = Image.open(image_path).convert("RGBA")
    mask_img = Image.open(mask_path).convert("L")
    overlay_img = Image.open(overlay_path).convert("RGBA")
    
    # Find bounding box of the mask (non-zero pixels)
    bbox = mask_img.getbbox()
    if not bbox:
        # Fallback: paste in center if mask is empty
        w_base, h_base = base_img.size
        bbox = (int(w_base * 0.3), int(h_base * 0.3), int(w_base * 0.7), int(h_base * 0.7))
        
    left, upper, right, lower = bbox
    box_width = right - left
    box_height = lower - upper
    
    # Resize overlay to fit the bounding box while maintaining aspect ratio
    w_over, h_over = overlay_img.size
    aspect = w_over / h_over
    
    if box_width / aspect <= box_height:
        new_w = box_width
        new_h = int(box_width / aspect)
    else:
        new_h = box_height
        new_w = int(box_height * aspect)
        
    # Ensure dimensions are at least 1px
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    
    resized_overlay = overlay_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Center the resized overlay in the bounding box
    offset_x = left + (box_width - new_w) // 2
    offset_y = upper + (box_height - new_h) // 2
    
    # Create transparent layer same size as base image
    overlay_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    overlay_layer.paste(resized_overlay, (offset_x, offset_y))
    
    # Composite: overlay_layer is only kept where mask_img is non-zero
    final_overlay = Image.composite(overlay_layer, Image.new("RGBA", base_img.size, (0, 0, 0, 0)), mask_img)
    
    # Composite final_overlay onto base_img
    result = Image.alpha_composite(base_img, final_overlay)
    
    # Save result as RGB
    result.convert("RGB").save(output_path, "PNG")


def compute_image_size_ratio(width: int, height: int) -> str:
    """
    Map actual pixel dimensions to the closest aspect ratio string supported by
    Nano Banana API. Supported sizes: 1:1, 16:9, 9:16, 4:3, 3:4, 2:3, 3:2,
    4:5, 5:4, 21:9, 1:4, 4:1, 8:1, 1:8. Max wide = 8:1.
    """
    ratio = width / height
    candidates = {
        "8:1":  8.0,
        "4:1":  4.0,
        "21:9": 21/9,
        "16:9": 16/9,
        "3:2":  3/2,
        "4:3":  4/3,
        "5:4":  5/4,
        "1:1":  1.0,
        "4:5":  4/5,
        "3:4":  3/4,
        "2:3":  2/3,
        "9:16": 9/16,
        "1:4":  1/4,
        "1:8":  1/8,
    }
    best = min(candidates, key=lambda k: abs(candidates[k] - ratio))
    return best


def run_nanobanana_inpainting(
    image_data_uri: str,
    mask_data_uri: str,
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "8:1",
) -> str:
    """
    Call Nano Banana API (image edit endpoint) with the base64 image and prompt as JSON.
    Endpoint: POST /v1/images/edit
    Supports automatic retries for transient server errors.
    """
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY is not configured.")

    url = f"{NANOBANANA_BASE_URL}/v1/images/edits"
    headers = {
        "Authorization": f"Bearer {NANOBANANA_API_KEY}",
        "Content-Type": "application/json",
    }
    # Map unsupported aspect ratios to nearest supported ones
    nb_size_map = {
        "3:1": "21:9",
    }
    nb_size = nb_size_map.get(image_size, image_size)

    payload = {
        "image": image_data_uri,
        "prompt": prompt,
        "model": "gemini-3.1-flash-lite-image",
        "n": 1,
        "size": nb_size,
    }

    last_error = None
    for attempt in range(3):
        try:
            app.logger.info("Sending JSON request to Nano Banana edit API (attempt %d)...", attempt + 1)
            resp = requests.post(url, headers=headers, json=payload, timeout=120)

            # Retry on transient server errors only
            if resp.status_code in (500, 502, 503, 504):
                app.logger.warning("Attempt %d returned status %d. Retrying...", attempt + 1, resp.status_code)
                last_error = f"Status {resp.status_code}: {resp.text}"
                time.sleep(2)
                continue

            if resp.status_code != 200:
                last_error = f"Error {resp.status_code}: {resp.text}"
                break  # Don't retry client errors (400, 401, 404, etc.)

            result = resp.json()
            # Pixapi returns {"created": ..., "data": [{"url": "..."}]}
            # Legacy API returned {"code": 0, "message": "ok", "data": {"url": "..."}}
            if result.get("code", 0) != 0:
                raise RuntimeError(f"Nano Banana error: {result.get('message', result)}")

            data = result.get("data", {})
            # Pixapi format: data is a list of {"url": "..."}
            if isinstance(data, list) and len(data) > 0:
                url_val = data[0].get("url")
            elif isinstance(data, dict):
                url_val = data.get("url")
                if isinstance(url_val, list):
                    url_val = url_val[0] if url_val else None
            else:
                url_val = None

            if not url_val:
                raise RuntimeError(f"Unexpected response structure from Nano Banana: {result}")

            return url_val

        except RuntimeError:
            raise
        except Exception as e:
            app.logger.warning("Connection error during attempt %d: %s", attempt + 1, e)
            last_error = str(e)
            time.sleep(2)
            continue

    raise RuntimeError(f"Nano Banana API request failed. Last error: {last_error}")


def run_recraft_generations(
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "1:1",
) -> str:
    """
    Call Recraft.ai Text-to-Image generations endpoint.
    Returns the URL of the generated image.
    """
    if not RECRAFT_API_KEY:
        raise RuntimeError("RECRAFT_API_KEY is not configured.")

    size_map = {
        "1:1": "1024x1024",
        "16:9": "1280x720",
        "9:16": "720x1280",
        "4:3": "1024x768",
        "3:4": "768x1024",
        "3:1": "1280x720",
        "4:1": "1280x720",
        "8:1": "1280x720",
    }
    resolution = size_map.get(image_size, "1024x1024")

    url = "https://external.api.recraft.ai/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {RECRAFT_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": resolution,
    }

    app.logger.info("Sending text-to-image request to Recraft API (size=%s)...", resolution)
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if resp.status_code != 200:
        error_msg = f"Recraft.ai API returned error {resp.status_code}: {resp.text}"
        app.logger.error(error_msg)
        raise RuntimeError(error_msg)

    result = resp.json()
    data_list = result.get("data", [])
    if not data_list or "url" not in data_list[0]:
        raise RuntimeError(f"Unexpected response structure from Recraft: {result}")

    return data_list[0]["url"]


def run_nanobanana_generations(
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "1:1",
) -> str:
    """
    Call Nano Banana Text-to-Image generate endpoint.
    Endpoint: POST /v1/images/generate
    Supports automatic retries for transient server errors.
    """
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY is not configured.")

    url = f"{NANOBANANA_BASE_URL}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {NANOBANANA_API_KEY}",
        "Content-Type": "application/json",
    }
    # Map unsupported aspect ratios to nearest supported ones
    nb_size_map = {
        "3:1": "21:9",
    }   
    nb_size = nb_size_map.get(image_size, image_size)

    payload = {
        "prompt": prompt,
        "model": "gemini-3.1-flash-lite-image",
        "n": 1,
        "size": nb_size,
    }

    last_error = None
    for attempt in range(3):
        try:
            app.logger.info("Sending text-to-image request to Nano Banana generate API (attempt %d, size=%s)...", attempt + 1, nb_size)
            resp = requests.post(url, headers=headers, json=payload, timeout=120)

            # Retry on transient server errors only
            if resp.status_code in (500, 502, 503, 504):
                app.logger.warning("Attempt %d returned status %d. Retrying...", attempt + 1, resp.status_code)
                last_error = f"Status {resp.status_code}: {resp.text}"
                time.sleep(2)
                continue

            if resp.status_code != 200:
                last_error = f"Error {resp.status_code}: {resp.text}"
                break  # Don't retry client errors (400, 401, 404, etc.)

            result = resp.json()
            # Pixapi returns {"created": ..., "data": [{"url": "..."}]}
            # Legacy API returned {"code": 0, "message": "ok", "data": {"url": "..."}}
            if result.get("code", 0) != 0:
                raise RuntimeError(f"Nano Banana error: {result.get('message', result)}")

            data = result.get("data", {})
            # Pixapi format: data is a list of {"url": "..."}
            if isinstance(data, list) and len(data) > 0:
                url_val = data[0].get("url")
            elif isinstance(data, dict):
                url_val = data.get("url")
                if isinstance(url_val, list):
                    url_val = url_val[0] if url_val else None
            else:
                url_val = None

            if not url_val:
                raise RuntimeError(f"Unexpected response structure from Nano Banana: {result}")

            return url_val

        except RuntimeError:
            raise
        except Exception as e:
            app.logger.warning("Connection error during attempt %d: %s", attempt + 1, e)
            last_error = str(e)
            time.sleep(2)
            continue

    raise RuntimeError(f"Nano Banana API request failed. Last error: {last_error}")


def _run_inferencesh_app(app_id: str, input_payload: dict, headers: dict) -> str:
    """Helper to launch and poll an inference.sh app task."""
    url = "https://api.inference.sh/apps/run"
    payload = {"app": app_id, "input": dict(input_payload)}
    
    # Sanitize size parameter for apps expecting 1K/2K (e.g. seedream)
    if "size" in payload["input"] and payload["input"]["size"] not in ("1K", "2K"):
        payload["input"]["size"] = "1K"

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"inference.sh status {resp.status_code}: {resp.text}")
    
    res = resp.json()
    task_id = res.get("id")
    output = res.get("output")
    
    # If async task launched, poll for result up to 60s
    if not output and task_id:
        app.logger.info("Polling inference.sh task %s...", task_id)
        for _ in range(30):
            time.sleep(2)
            check_resp = requests.get(f"https://api.inference.sh/tasks/{task_id}", headers=headers)
            if check_resp.status_code == 200:
                check = check_resp.json()
                if check.get("output"):
                    output = check.get("output")
                    break
                if check.get("status_text") in ("failed", "error"):
                    raise RuntimeError(f"inference.sh task failed: {check}")
                    
    if not output:
        raise RuntimeError(f"No output returned from inference.sh task: {res}")
        
    if isinstance(output, dict):
        # Support all image key variants: image, url, uri, image_url, images list
        uri = output.get("image") or output.get("url") or output.get("uri") or output.get("image_url")
        if uri and isinstance(uri, str):
            return uri
        imgs = output.get("images", [])
        if imgs and isinstance(imgs, list):
            uri = imgs[0].get("uri") or imgs[0].get("url") or imgs[0].get("image")
            if uri: return uri
    elif isinstance(output, str) and output.startswith("http"):
        return output

    raise RuntimeError(f"Could not parse image URL from inference.sh output: {output}")


def run_reve_inpainting(
    image_data_uri: str,
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "1:1",
) -> str:
    """
    Call Reve 2.0 API (layout-first edit endpoint) with image data URI and prompt.
    Supports native Reve endpoints, Pixapi (papi), and inference.sh (1nfsh) apps/run API.
    """
    if not REVE_API_KEY:
        raise RuntimeError("REVE_API_KEY is not configured.")

    if REVE_API_KEY.startswith("1nfsh-") or "inference.sh" in REVE_BASE_URL:
        headers = {
            "Authorization": f"Bearer {REVE_API_KEY}",
            "Content-Type": "application/json",
            "X-API-Version": "2",
        }
        apps_to_try = ["falai/reve", "bytedance/seedream-5-pro"]
        last_error = None

        for app_id in apps_to_try:
            inp = {"prompt": prompt, "image": image_data_uri, "mode": "edit", "output_format": "png"}
            if negative_prompt:
                inp["negative_prompt"] = negative_prompt
            try:
                app.logger.info("Executing inference.sh app %s...", app_id)
                return _run_inferencesh_app(app_id, inp, headers)
            except Exception as e:
                last_error = str(e)
                app.logger.warning("inference.sh app %s failed: %s", app_id, e)

        raise RuntimeError(last_error or "inference.sh execution failed.")

    elif REVE_API_KEY.startswith("papi.") or "pixapi" in REVE_BASE_URL:
        url = "https://api.pixapi.ai/v1/images/edits"
        models_to_try = ["reve-2.0-layout", "gemini-3.1-flash-lite-image"]
    else:
        url = f"{REVE_BASE_URL.rstrip('/')}/image/edit"
        models_to_try = ["reve-2.0-layout", "reve-2-0"]

    headers = {
        "Authorization": f"Bearer {REVE_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = None
    for model_name in models_to_try:
        if REVE_API_KEY.startswith("papi.") or "pixapi" in REVE_BASE_URL:
            payload = {
                "image": image_data_uri,
                "prompt": prompt,
                "model": model_name,
                "n": 1,
                "size": image_size,
            }
        else:
            payload = {
                "image": image_data_uri,
                "prompt": prompt,
                "model": model_name,
                "size": image_size,
                "response_format": "url",
            }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        app.logger.info("Sending JSON request to Reve 2.0 edit API (%s, model=%s)...", url, model_name)
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            data = result.get("data")
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("url")
            elif isinstance(data, dict):
                return data.get("url")
            elif result.get("url"):
                return result.get("url")
            elif result.get("image_url"):
                return result.get("image_url")
        
        last_error = f"Reve 2.0 API returned error {resp.status_code}: {resp.text}"
        app.logger.warning("Attempt with model %s failed: %s", model_name, last_error)

    raise RuntimeError(last_error or "Reve 2.0 API request failed.")


def run_reve_generations(
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "1:1",
) -> str:
    """
    Call Reve 2.0 Text-to-Image creation endpoint.
    Supports native Reve endpoints, Pixapi (papi), and inference.sh (1nfsh) apps/run API.
    """
    if not REVE_API_KEY:
        raise RuntimeError("REVE_API_KEY is not configured.")

    if REVE_API_KEY.startswith("1nfsh-") or "inference.sh" in REVE_BASE_URL:
        headers = {
            "Authorization": f"Bearer {REVE_API_KEY}",
            "Content-Type": "application/json",
            "X-API-Version": "2",
        }
        apps_to_try = ["falai/reve", "bytedance/seedream-5-pro"]
        last_error = None

        for app_id in apps_to_try:
            inp = {"prompt": prompt, "mode": "text-to-image", "output_format": "png"}
            if negative_prompt:
                inp["negative_prompt"] = negative_prompt
            try:
                app.logger.info("Executing inference.sh generation app %s...", app_id)
                return _run_inferencesh_app(app_id, inp, headers)
            except Exception as e:
                last_error = str(e)
                app.logger.warning("inference.sh app %s failed: %s", app_id, e)

        raise RuntimeError(last_error or "inference.sh generation failed.")
        last_error = None

        for app_id in apps_to_try:
            inp = {"prompt": prompt, "size": image_size}
            if negative_prompt:
                inp["negative_prompt"] = negative_prompt
            try:
                app.logger.info("Executing inference.sh generation app %s...", app_id)
                return _run_inferencesh_app(app_id, inp, headers)
            except Exception as e:
                last_error = str(e)
                app.logger.warning("inference.sh app %s failed: %s", app_id, e)

        raise RuntimeError(last_error or "inference.sh generation failed.")

    elif REVE_API_KEY.startswith("papi.") or "pixapi" in REVE_BASE_URL:
        url = "https://api.pixapi.ai/v1/images/generations"
        models_to_try = ["reve-2.0-layout", "gemini-3.1-flash-lite-image"]
    else:
        url = f"{REVE_BASE_URL.rstrip('/')}/image/create"
        models_to_try = ["reve-2.0-layout", "reve-2-0"]

    headers = {
        "Authorization": f"Bearer {REVE_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = None
    for model_name in models_to_try:
        if REVE_API_KEY.startswith("papi.") or "pixapi" in REVE_BASE_URL:
            payload = {
                "prompt": prompt,
                "model": model_name,
                "n": 1,
                "size": image_size,
            }
        else:
            payload = {
                "prompt": prompt,
                "model": model_name,
                "size": image_size,
                "response_format": "url",
            }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        app.logger.info("Sending request to Reve 2.0 Text-to-Image API (%s, model=%s)...", url, model_name)
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            data = result.get("data")
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("url")
            elif isinstance(data, dict):
                return data.get("url")
            elif result.get("url"):
                return result.get("url")
            elif result.get("image_url"):
                return result.get("image_url")
        
        last_error = f"Reve 2.0 API returned error {resp.status_code}: {resp.text}"
        app.logger.warning("Attempt with model %s failed: %s", model_name, last_error)

    raise RuntimeError(last_error or "Reve 2.0 API request failed.")




def enhance_prompt_layout(prompt: str) -> str:
    """
    Enhance the prompt with smart, premium layout instructions and context-based descriptors:
    categorizes the product type, injects relevant styling parameters, prevents distortion,
    and formats for offset-print retail packaging.
    """
    if not prompt:
        return ""
    
    p_lower = prompt.lower()
    enhancements = []
    
    # 1. Product Type Recognition
    if any(k in p_lower for k in ["protein", "whey", "supplement", "creatine", "nutrition", "amino", "bcaa", "gym", "workout"]):
        enhancements.append("ultra-premium commercial sports nutrition supplement container label, fitness-focused luxury branding, pharmaceutical-grade packaging aesthetic, bold modern sans-serif typography, clean layout divisions")
    elif any(k in p_lower for k in ["drink", "energy", "soda", "can", "bottle", "juice", "beverage", "beer", "wine", "cola", "water"]):
        enhancements.append("commercial retail beverage packaging label, vibrant dynamic color palette, refreshing clean graphics, high-end soda branding, modern typography, glossy metallic finish")
    elif any(k in p_lower for k in ["cream", "lotion", "serum", "shampoo", "cosmetic", "beauty", "soap", "skincare", "perfume", "oil"]):
        enhancements.append("minimalist luxury cosmetic skincare label, elegant clean serif typography, organic aesthetic, soft pastel colors, premium matte finish, high-end retail presentation")
    elif any(k in p_lower for k in ["coffee", "tea", "mocha", "latte", "cappuccino", "cafe"]):
        enhancements.append("gourmet premium coffee packaging label, rich warm color tones, packaging design, clean modern typography, high-end cafe style")
    elif any(k in p_lower for k in ["chocolate", "candy", "cookie", "food", "sauce", "honey", "snack", "syrup"]):
        enhancements.append("gourmet food packaging design, appetizing commercial food illustration, clean professional layout, premium retail branding")
    else:
        enhancements.append("ultra-premium commercial retail product packaging label, high-end branding aesthetic, modern clean layout")

    # 2. Ingredient / Flavor enhancements
    if "chocolate" in p_lower:
        enhancements.append("rich chocolate color palette, chocolate drizzle details, luxury finish")
    if "coffee" in p_lower or "mocha" in p_lower:
        enhancements.append("coffee brown gradients, roasted coffee bean details, warm aromatic tones")
    if any(k in p_lower for k in ["mango", "orange", "citrus", "lemon", "lime", "peach"]):
        enhancements.append("vibrant citrus gradients, fresh fruit illustrations, bright energetic color scheme")
    if any(k in p_lower for k in ["berry", "strawberry", "blueberry", "raspberry"]):
        enhancements.append("deep berry red and purple gradients, delicious fruit graphic details")
    if "vanilla" in p_lower:
        enhancements.append("warm cream color palette, gold accent borders, elegant soft tones")

    # 3. Structural elements
    if any(k in p_lower for k in ["serving", "servings", "nutrition", "fact", "facts"]):
        enhancements.append("with a clearly separated servings table and nutritional facts section on the side panel")
    
    # 4. Standard Quality & Print requirements
    enhancements.append("flat print layout, symmetrical wrap-around template design, no image distortion, vector-sharp edges, crisp typography, realistic lighting and soft drop shadows, print-ready 300 DPI quality, premium retail shelf-ready presentation")

    # Combine
    enhanced = prompt.strip()
    if not enhanced.endswith("."):
        enhanced += ","
    else:
        enhanced = enhanced[:-1] + ","
        
    enhanced += " " + ", ".join(enhancements)
    return enhanced


def translate_prompt(text: str) -> str:
    """
    Returns the prompt text directly without external translation.
    """
    return text.strip() if text else ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_image():
    """
    Main processing endpoint.

    Expects multipart/form-data with:
      - image           : the uploaded image file
      - mode            : 'remove' | 'add' | 'replace' (default: 'remove')
      - prompt          : text description of the edit target or what to add
      - mask_prompt     : (optional) separate description of what region to mask
      - negative_prompt : (optional) things to avoid in the fill
    """
    # ---- Check if base image is uploaded ----
    has_image = "image" in request.files and request.files["image"].filename != ""
    
    raw_prompt   = request.form.get("prompt", "").strip()
    prompt = translate_prompt(raw_prompt)
    
    if not prompt:
        return jsonify({"error": "A text prompt is required."}), 400
        
    api_provider = request.form.get("api_provider", "recraft").strip().lower()
    image_size = request.form.get("image_size", "8:1").strip()
    negative_prompt = request.form.get(
        "negative_prompt",
        "blurry, low quality, distorted text, watermark, artifacts",
    ).strip()

    # ---- Validate API keys based on provider ----
    if api_provider == "recraft":
        if not RECRAFT_API_KEY or RECRAFT_API_KEY.startswith("your_recraft_"):
            return jsonify(
                {
                    "error": (
                        "RECRAFT_API_KEY is not configured. "
                        "Create a .env file with your key from your Recraft.ai profile."
                    )
                }
            ), 500
    elif api_provider == "reve":
        if not REVE_API_KEY or REVE_API_KEY.startswith("your_reve_"):
            return jsonify(
                {
                    "error": (
                        "REVE_API_KEY is not configured. "
                        "Please add your REVE_API_KEY to your .env file."
                    )
                }
            ), 500
    else:
        if not NANOBANANA_API_KEY or NANOBANANA_API_KEY.startswith("your_nanobanana_"):
            return jsonify(
                {
                    "error": (
                        "NANOBANANA_API_KEY is not configured. "
                        "Create a .env file with your key from your Nano Banana dashboard."
                    )
                }
            ), 500

    # ---- Handle Text-to-Image Generation (No Image Uploaded) ----
    if not has_image:
        unique_stem = str(uuid.uuid4())[:8]
        try:
            enhanced_prompt = enhance_prompt_layout(prompt)
            if api_provider == "recraft":
                app.logger.info("Running Recraft.ai Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_recraft_generations(enhanced_prompt, negative_prompt, image_size)
            elif api_provider == "reve":
                app.logger.info("Running Reve 2.0 Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_reve_generations(enhanced_prompt, negative_prompt, image_size)
            else:
                app.logger.info("Running Nano Banana Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_nanobanana_generations(enhanced_prompt, negative_prompt, image_size)
                
            # Download result
            result_resp = requests.get(final_image_url, timeout=30)
            result_resp.raise_for_status()
            img_bytes = result_resp.content

            output_filename = f"result_{unique_stem}.png"
            output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)

            with Image.open(io.BytesIO(img_bytes)) as img:
                img.save(output_path, "PNG")

            # ---- Save text-to-image job to database (no source image) ----
            job = JobHistory(
                image_id=None,  
                prompt=prompt,
                result_filename=output_filename,
                api_provider=api_provider,
                mode="generate",
            )
            db.session.add(job)
            db.session.commit()

            return jsonify(
                {
                    "result_image": f"/static/results/{output_filename}",
                    "original_image": "",  # Empty indicates text-to-image
                }
            )
        except Exception as exc:
            app.logger.exception("Unexpected error during text-to-image generation.")
            return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500

    # ---- Handle Inpainting (Image Uploaded) ----
    image_file = request.files["image"]
    mode         = request.form.get("mode", "remove").strip().lower()
    if mode not in ("remove", "add", "replace", "text_replace"):
        mode = "remove"

    raw_mask_prompt = request.form.get("mask_prompt", "").strip()
    if not raw_mask_prompt:
        if mode == "text_replace":
            raw_mask_prompt = extract_mask_target_from_prompt(raw_prompt)
        else:
            raw_mask_prompt = raw_prompt
    mask_prompt = translate_prompt(raw_mask_prompt)

    if not allowed_file(image_file.filename):
        return jsonify({"error": "Unsupported file format. Use PNG, JPG, or WEBP."}), 400

    # ---- Save uploaded image ----
    original_name = secure_filename(image_file.filename)
    unique_stem = str(uuid.uuid4())[:8]
    ext = original_name.rsplit(".", 1)[1].lower()
    save_name = f"{unique_stem}_{original_name}"
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
    image_file.save(input_path)

    # ---- Record upload in database ----
    db_image = UploadedImage(
        filename=save_name,
        original_name=original_name,
        file_path=input_path,
        description=prompt,
    )
    db.session.add(db_image)
    db.session.commit()
    db_image_id = db_image.id

    # ---- Pre-process: normalise colour mode only, capture exact original dimensions ----
    with Image.open(input_path) as img:
        original_w, original_h = img.size
        img = img.convert("RGBA" if ext == "png" else "RGB")
        img.save(input_path)

    # ---- Update dimensions in DB now that we know them ----
    db_image.width = original_w
    db_image.height = original_h
    db.session.commit()

    app.logger.info("Original image dimensions: %dx%d", original_w, original_h)

    # ---- Encode image as data URI ----
    image_data_uri = image_to_data_uri(input_path)

    try:
        # ---- Step 1: Generate mask via CLIPSeg (only needed for Recraft) ----
        mask_data_uri = None
        mask_path = None

        if api_provider == "recraft":
            app.logger.info("Generating segmentation mask (mode=%s) for: %r", mode, mask_prompt)
            mask_data_uri = generate_mask_with_clipseg(image_data_uri, mask_prompt)

            # Save mask to disk as file since Recraft API needs it as a multipart file upload
            mask_header, mask_b64data = mask_data_uri.split(",", 1)
            mask_bytes = base64.b64decode(mask_b64data)
            mask_path = os.path.join(app.config["UPLOAD_FOLDER"], f"mask_{unique_stem}.png")
            with open(mask_path, "wb") as f:
                f.write(mask_bytes)
        else:
            app.logger.info("Skipping CLIPSeg mask — Pixapi Gemini model uses text-based editing")

        # ---- text_replace: always needs CLIPSeg mask ----
        if mode == "text_replace" and mask_data_uri is None:
            app.logger.info("Generating CLIPSeg mask for text_replace mode...")
            mask_data_uri = generate_mask_with_clipseg(image_data_uri, mask_prompt)

        # Check if an overlay image is uploaded for direct image addition
        if "overlay" in request.files and request.files["overlay"].filename:
            # For overlay composition, we do need a mask regardless of provider
            if mask_path is None:
                app.logger.info("Generating CLIPSeg mask for overlay composition...")
                mask_data_uri = generate_mask_with_clipseg(image_data_uri, mask_prompt)
                mask_header, mask_b64data = mask_data_uri.split(",", 1)
                mask_bytes = base64.b64decode(mask_b64data)
                mask_path = os.path.join(app.config["UPLOAD_FOLDER"], f"mask_{unique_stem}.png")
                with open(mask_path, "wb") as f:
                    f.write(mask_bytes)

            overlay_file = request.files["overlay"]
            overlay_path = os.path.join(app.config["UPLOAD_FOLDER"], f"overlay_{unique_stem}.png")
            overlay_file.save(overlay_path)
            
            output_filename = f"result_{unique_stem}.png"
            output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)
            
            app.logger.info("Performing local image addition / overlay composition...")
            composite_image_addition(input_path, mask_path, overlay_path, output_path)

            # Restore exact original dimensions
            with Image.open(output_path) as img:
                if img.size != (original_w, original_h):
                    img.resize((original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")

            # ---- Save job to database ----
            job = JobHistory(
                image_id=db_image_id,
                prompt=prompt,
                result_filename=output_filename,
                api_provider=api_provider,
                mode="add",
            )
            db.session.add(job)
            db.session.commit()

            return jsonify(
                {
                    "result_image": f"/static/results/{output_filename}",
                    "original_image": f"/static/uploads/{save_name}",
                }
            )

        # ---- Step 2: text_replace mode → PIL-based professional rendering ----
        if mode == "text_replace":
            app.logger.info("Running PIL professional text replacement for: %r", prompt)
            output_filename = f"result_{unique_stem}.png"
            output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)

            professional_text_replace(
                image_path=input_path,
                mask_data_uri=mask_data_uri,
                new_text=prompt,
                output_path=output_path,
            )

            # Restore exact original dimensions
            with Image.open(output_path) as img:
                if img.size != (original_w, original_h):
                    img.resize((original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")

            job = JobHistory(
                image_id=db_image_id,
                prompt=prompt,
                result_filename=output_filename,
                api_provider="local_pil",
                mode="text_replace",
            )
            db.session.add(job)
            db.session.commit()

            return jsonify({
                "result_image": f"/static/results/{output_filename}",
                "original_image": f"/static/uploads/{save_name}",
            })

        # ---- Step 3: Build mode-aware inpainting prompt ----
        if api_provider == "recraft":
            # Recraft uses mask-based inpainting — needs descriptive fill prompts
            if mode == "remove":
                inpaint_prompt = (
                    f"seamless product label background, clean surface, "
                    f"high resolution, professional print design, "
                    f"no logo, no text, smooth texture matching surroundings"
                )
            elif mode == "add":
                enhanced_inpaint = enhance_prompt_layout(prompt)
                inpaint_prompt = (
                    f"{enhanced_inpaint}, product label style, high resolution, "
                    f"professional graphic design, sharp edges, "
                    f"colour-matched to surrounding label"
                )
            else:  # replace
                enhanced_inpaint = enhance_prompt_layout(prompt)
                inpaint_prompt = (
                    f"{enhanced_inpaint}, replacing existing element, "
                    f"product label style, high resolution, professional design, "
                    f"seamlessly integrated into label"
                )
        elif api_provider == "reve":
            inpaint_prompt = (
                f"Modify this product label design according to instruction: {prompt}. "
                f"Preserve structural 4K layout, typography quality, and overall color harmony."
            )
        else:
            # Pixapi uses Gemini models that understand direct edit instructions
            # Send the user's original prompt as a clear editing instruction
            inpaint_prompt = (
                f"Edit this product label image: {prompt}. "
                f"Keep all other elements, layout, colors, and text exactly the same. "
                f"Only change what was requested. Maintain the same style and quality."
            )

        if api_provider == "recraft":
            app.logger.info("Running Recraft.ai In-Painting (mode=%s) ...", mode)
            final_image_url = run_recraft_inpainting(
                input_path, mask_path, inpaint_prompt, negative_prompt
            )
        elif api_provider == "reve":
            app.logger.info("Running Reve 2.0 Image Edit (mode=%s) ...", mode)
            reve_size = compute_image_size_ratio(original_w, original_h)
            final_image_url = run_reve_inpainting(
                image_data_uri, inpaint_prompt, negative_prompt, reve_size
            )
        else:
            app.logger.info("Running Pixapi Gemini Image Edit (mode=%s) ...", mode)
            nb_size = compute_image_size_ratio(original_w, original_h)
            app.logger.info("Using size=%s for %dx%d input", nb_size, original_w, original_h)
            final_image_url = run_nanobanana_inpainting(
                image_data_uri, mask_data_uri, inpaint_prompt, negative_prompt, nb_size
            )

        # ---- Step 4: Download result ----
        result_resp = requests.get(final_image_url, timeout=30)
        result_resp.raise_for_status()
        img_bytes = result_resp.content

        output_filename = f"result_{unique_stem}.png"
        output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)

        with Image.open(io.BytesIO(img_bytes)) as img:
            result_w, result_h = img.size

            # If the API returned a vertically stacked multi-variant image
            # (height is ~2x or more the original), crop to the top original_h rows first
            if result_h >= original_h * 1.7:
                app.logger.info(
                    "Result height %d is ~%dx original %d — cropping to top variant only",
                    result_h, round(result_h / original_h), original_h
                )
                img = img.crop((0, 0, result_w, original_h))

            # Now restore exact original pixel dimensions
            if img.size != (original_w, original_h):
                app.logger.info(
                    "Resizing result from %dx%d to original %dx%d",
                    img.size[0], img.size[1], original_w, original_h
                )
                img = img.resize((original_w, original_h), Image.Resampling.LANCZOS)

            img.save(output_path, "PNG")

        # ---- Save job to database ----
        job = JobHistory(
            image_id=db_image_id,
            prompt=prompt,
            result_filename=output_filename,
            api_provider=api_provider,
            mode=mode,
        )
        db.session.add(job)
        db.session.commit()

        return jsonify(
            {
                "result_image": f"/static/results/{output_filename}",
                "original_image": f"/static/uploads/{save_name}",
            }
        )


    except requests.exceptions.HTTPError as exc:
        app.logger.error("HTTP error from Recraft.ai: %s", exc)
        if exc.response is not None and exc.response.status_code == 429:
            return jsonify({
                "error": "rate_limit",
                "detail": (
                    "Recraft.ai rate limit reached. "
                    "Please check your API key credits or billing status."
                )
            }), 429
        return jsonify({"error": f"API HTTP error: {exc.response.status_code} – {exc.response.text}"}), 502
    except requests.exceptions.RequestException as exc:
        app.logger.error("Network error: %s", exc)
        return jsonify({"error": f"Network error: {str(exc)}"}), 503
    except RuntimeError as exc:
        app.logger.error("Processing error: %s", exc)
        err_msg = str(exc)
        if "payment_required" in err_msg.lower() or "insufficient balance" in err_msg.lower() or "402" in err_msg:
            return jsonify({
                "error": (
                    "Your inference.sh / Reve account has run out of credits (Error 402: Payment Required). "
                    "Please top up your credit balance on app.inference.sh, or change the API Provider in 'Advanced Options' to Recraft.ai."
                )
            }), 400
        if "Insufficient credits" in err_msg:
            return jsonify({
                "error": (
                    "Your Nano Banana API key has insufficient credits. "
                    "Please check your Nano Banana developer dashboard to top up your balance, "
                    "or change the API Provider in 'Advanced Options' to Reve 2.0 (4K Layout AI) or Recraft.ai."
                )
            }), 400
        return jsonify({"error": err_msg}), 500
    except Exception as exc:
        app.logger.exception("Unexpected error during processing.")
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


@app.route("/static/results/<filename>")
def serve_result(filename: str):
    return send_from_directory(app.config["RESULTS_FOLDER"], filename)


@app.route("/static/uploads/<filename>")
def serve_upload(filename: str):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "recraft_api_key_set": bool(RECRAFT_API_KEY and not RECRAFT_API_KEY.startswith("your_recraft_")),
        "nanobanana_api_key_set": bool(NANOBANANA_API_KEY and not NANOBANANA_API_KEY.startswith("your_nanobanana_"))
    })



@app.route("/history")
def get_history():
    """Return the last 50 job results in reverse-chronological order."""
    jobs = JobHistory.query.order_by(JobHistory.created_at.desc()).limit(50).all()
    return jsonify([j.to_dict() for j in jobs])


@app.route("/uploads")
def get_uploads():
    """Return the last 50 uploaded images in reverse-chronological order."""
    images = UploadedImage.query.order_by(UploadedImage.created_at.desc()).limit(50).all()
    return jsonify([img.to_dict() for img in images])


# ---------------------------------------------------------------------------
# Smart Image Search Helper
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set:
    """Lowercase, strip punctuation, return set of words (≥3 chars)."""
    text = text.lower()
    words = re.findall(r"[a-z0-9]+", text)
    return {w for w in words if len(w) >= 3}


def smart_search_images(prompt: str, threshold: float = 0.28):
    """
    Search the UploadedImage table for the best match to `prompt`.

    Strategy:
      1. Tokenize both prompt and stored descriptions/filenames.
      2. Compute Jaccard token overlap (shared / total unique).
      3. Also compute difflib sequence similarity on the raw strings.
      4. Take the max of both scores.
      5. Return the best-scoring image if score >= threshold, else None.

    Returns: (UploadedImage | None, float score, str reason)
    """
    all_images = UploadedImage.query.order_by(UploadedImage.created_at.desc()).all()
    if not all_images:
        return None, 0.0, "no images in database"

    prompt_tokens = _tokenize(prompt)
    prompt_lower  = prompt.lower()

    best_img   = None
    best_score = 0.0
    best_reason = ""

    for img in all_images:
        # Combine description + original filename into one searchable text
        combined = f"{img.description} {img.original_name}".strip()
        combined_tokens = _tokenize(combined)
        combined_lower  = combined.lower()

        # Jaccard similarity on token sets
        if prompt_tokens or combined_tokens:
            shared   = len(prompt_tokens & combined_tokens)
            total    = len(prompt_tokens | combined_tokens)
            jaccard  = shared / total if total > 0 else 0.0
        else:
            jaccard = 0.0

        # Sequence similarity on raw strings
        seq_score = difflib.SequenceMatcher(None, prompt_lower, combined_lower).ratio()

        score = max(jaccard, seq_score)

        app.logger.debug(
            "smart_search: img=%s desc=%r jaccard=%.2f seq=%.2f final=%.2f",
            img.filename, combined[:60], jaccard, seq_score, score
        )

        if score > best_score:
            best_score  = score
            best_img    = img
            best_reason = f"jaccard={jaccard:.2f} seq={seq_score:.2f}"

    if best_score >= threshold:
        return best_img, best_score, best_reason
    return None, best_score, "below threshold"


# ---------------------------------------------------------------------------
# Smart Process Route
# ---------------------------------------------------------------------------

@app.route("/smart-process", methods=["POST"])
def smart_process():
    """
    Smart AI endpoint — no manual image upload needed.

    Accepts JSON or form data:
      prompt       : what the user wants (required)
      api_provider : "recraft" | "nanobanana" (optional, default nanobanana)

    Flow:
      1. Translate prompt to English.
      2. Search DB for best matching uploaded image.
      3a. Match found  → run AI inpainting on that image.
      3b. No match     → run text-to-image generation.
    """
    # --- Parse input (support both JSON and form) ---
    if request.is_json:
        data = request.get_json(force=True)
        raw_prompt   = (data.get("prompt") or "").strip()
        api_provider = (data.get("api_provider") or "nanobanana").lower()
    else:
        raw_prompt   = request.form.get("prompt", "").strip()
        api_provider = request.form.get("api_provider", "nanobanana").lower()

    if not raw_prompt:
        return jsonify({"error": "A prompt is required."}), 400

    # Translate if needed
    prompt = translate_prompt(raw_prompt)

    # Validate API keys
    if api_provider == "recraft":
        if not RECRAFT_API_KEY or RECRAFT_API_KEY.startswith("your_recraft_"):
            return jsonify({"error": "RECRAFT_API_KEY is not configured."}), 500
    else:
        api_provider = "nanobanana"
        if not NANOBANANA_API_KEY or NANOBANANA_API_KEY.startswith("your_nanobanana_"):
            return jsonify({"error": "NANOBANANA_API_KEY is not configured."}), 500

    unique_stem = str(uuid.uuid4())[:8]
    negative_prompt = (
        "3d jar container mockup, bottle model, packaging mockup, perspective mockup, "
        "photographic background, studio background, wrinkled paper, blurry, low quality, "
        "distorted text, watermark, artifacts"
    )

    # ----------------------------------------------------------------
    # Step 1: Search database for a matching image
    # ----------------------------------------------------------------
    matched_img, score, reason = smart_search_images(prompt)
    app.logger.info(
        "smart_search result: match=%s score=%.2f reason=%s",
        matched_img.filename if matched_img else None, score, reason
    )

    # ----------------------------------------------------------------
    # Step 2a: Match found → inpaint / edit that image
    # ----------------------------------------------------------------
    if matched_img:
        input_path  = matched_img.file_path
        original_w  = matched_img.width or 1024
        original_h  = matched_img.height or 1024

        # Verify the file still exists on disk
        if not os.path.exists(input_path):
            app.logger.warning("Matched image file missing from disk: %s", input_path)
            matched_img = None  # fall through to generation

    if matched_img:
        try:
            image_data_uri = image_to_data_uri(input_path)

            p_lower = prompt.lower()
            is_text_replacement = (
                ("remove" in p_lower and "add" in p_lower) or
                ("replace" in p_lower and "with" in p_lower) or
                ("change" in p_lower and "to" in p_lower)
            )

            if is_text_replacement:
                app.logger.info("smart_process: Detected text replacement instruction. Using professional_text_replace.")
                mask_prompt = extract_mask_target_from_prompt(prompt)
                mask_data_uri = generate_mask_with_clipseg(image_data_uri, mask_prompt)
                
                output_filename = f"result_{unique_stem}.png"
                output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)
                
                professional_text_replace(
                    image_path=input_path,
                    mask_data_uri=mask_data_uri,
                    new_text=prompt,
                    output_path=output_path,
                )
                
                # Restore exact dimensions
                with Image.open(output_path) as img:
                    if img.size != (original_w, original_h):
                        img.resize((original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")
                        
                # We skip downloading from API since it's processed locally
                final_url = None
            elif api_provider == "recraft":
                # Recraft needs CLIPSeg mask + descriptive fill prompt
                mask_data_uri = generate_mask_with_clipseg(image_data_uri, prompt)
                enhanced_inpaint = enhance_prompt_layout(prompt)
                inpaint_prompt = (
                    f"{enhanced_inpaint}, replacing existing element, "
                    f"product label style, high resolution, professional design, "
                    f"seamlessly integrated into label"
                )
                # Save mask to disk for multipart upload
                mask_header, mask_b64data = mask_data_uri.split(",", 1)
                mask_bytes  = base64.b64decode(mask_b64data)
                mask_path   = os.path.join(app.config["UPLOAD_FOLDER"], f"mask_{unique_stem}.png")
                with open(mask_path, "wb") as f:
                    f.write(mask_bytes)
                final_url = run_recraft_inpainting(input_path, mask_path, inpaint_prompt, negative_prompt)
            elif api_provider == "reve":
                inpaint_prompt = (
                    f"Modify this product label design according to instruction: {prompt}. "
                    f"Preserve structural 4K layout, typography quality, and overall color harmony."
                )
                reve_size = compute_image_size_ratio(original_w, original_h)
                final_url = run_reve_inpainting(
                    image_data_uri, inpaint_prompt, negative_prompt, reve_size
                )
            else:
                # Pixapi Gemini — skip CLIPSeg, use direct edit instruction
                inpaint_prompt = (
                    f"Edit this product label image: {prompt}. "
                    f"Keep all other elements, layout, colors, and text exactly the same. "
                    f"Only change what was requested. Maintain the same style and quality."
                )
                nb_size   = compute_image_size_ratio(original_w, original_h)
                final_url = run_nanobanana_inpainting(
                    image_data_uri, None, inpaint_prompt, negative_prompt, nb_size
                )

            # Download result (if processed via API)
            if final_url:
                result_resp = requests.get(final_url, timeout=30)
                result_resp.raise_for_status()
                img_bytes = result_resp.content
     
                output_filename = f"result_{unique_stem}.png"
                output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)
                with Image.open(io.BytesIO(img_bytes)) as img:
                    if img.size != (original_w, original_h):
                        img = img.resize((original_w, original_h), Image.Resampling.LANCZOS)
                    img.save(output_path, "PNG")

            # Save job to DB
            job = JobHistory(
                image_id=matched_img.id,
                prompt=prompt,
                result_filename=output_filename,
                api_provider=api_provider,
                mode="replace",
            )
            db.session.add(job)
            db.session.commit()

            return jsonify({
                "result_image":   f"/static/results/{output_filename}",
                "original_image": f"/static/uploads/{matched_img.filename}",
                "matched":        True,
                "matched_name":   matched_img.original_name,
                "match_score":    round(score, 2),
            })

        except Exception as exc:
            app.logger.exception("Smart inpainting failed, falling back to generation.")
            if "Insufficient credits" in str(exc):
                return jsonify({
                    "error": (
                        "Your Nano Banana API key has insufficient credits. "
                        "Please check your Nano Banana developer dashboard to top up your balance, "
                        "or change the API Provider to Recraft.ai or Reve 2.0 (4K Layout AI)."
                    )
                }), 400
            # Fall through to generation below

    # ----------------------------------------------------------------
    # Step 2b: No match (or inpainting failed) → generate new image
    # ----------------------------------------------------------------
    try:
        # Use size of the most-recently uploaded image in DB, else 1:1
        ref_img = UploadedImage.query.order_by(UploadedImage.created_at.desc()).first()
        if ref_img and ref_img.width and ref_img.height:
            gen_size = compute_image_size_ratio(ref_img.width, ref_img.height)
        else:
            gen_size = "8:1"  # Widest label ratio supported by Nano Banana API

        enhanced_prompt = enhance_prompt_layout(prompt)

        if api_provider == "recraft":
            final_url = run_recraft_generations(enhanced_prompt, negative_prompt, gen_size)
        elif api_provider == "reve":
            final_url = run_reve_generations(enhanced_prompt, negative_prompt, gen_size)
        else:
            final_url = run_nanobanana_generations(enhanced_prompt, negative_prompt, gen_size)

        result_resp = requests.get(final_url, timeout=30)
        result_resp.raise_for_status()
        img_bytes = result_resp.content

        output_filename = f"result_{unique_stem}.png"
        output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)
        with Image.open(io.BytesIO(img_bytes)) as img:
            img.save(output_path, "PNG")

        # Save job to DB (no source image)
        job = JobHistory(
            image_id=None,
            prompt=prompt,
            result_filename=output_filename,
            api_provider=api_provider,
            mode="generate",
        )
        db.session.add(job)
        db.session.commit()

        return jsonify({
            "result_image":   f"/static/results/{output_filename}",
            "original_image": "",
            "matched":        False,
            "matched_name":   None,
            "match_score":    round(score, 2),
        })

    except Exception as exc:
        app.logger.exception("Smart generation also failed.")
        err_msg = str(exc)
        if "payment_required" in err_msg.lower() or "insufficient balance" in err_msg.lower() or "402" in err_msg:
            return jsonify({
                "error": (
                    "Your inference.sh / Reve account has run out of credits (Error 402: Payment Required). "
                    "Please top up your credit balance on app.inference.sh, or change the API Provider in 'Advanced Options' to Recraft.ai."
                )
            }), 400
        if "Insufficient credits" in err_msg:
            return jsonify({
                "error": (
                    "Your Nano Banana API key has insufficient credits. "
                    "Please check your Nano Banana developer dashboard to top up your balance, "
                    "or change the API Provider to Recraft.ai or Reve 2.0 (4K Layout AI)."
                )
            }), 400
        return jsonify({"error": f"Smart process failed: {err_msg}"}), 500


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------
def _build_svg_from_image(filepath: str) -> bytes:
    """
    Build a vector SVG that embeds the raster image as a base64 data URI.
    If vtracer is available, produce full traced vector paths first; otherwise
    fall back to an embedded-image SVG (fully supported by CorelDRAW import).
    Returns raw SVG bytes.
    """
    with Image.open(filepath) as img:
        img_rgb = img.convert("RGB")
        w, h = img_rgb.size

    # --- Attempt true vector tracing via vtracer ---
    try:
        import vtracer
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            tmp_in_path = tmp_in.name
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_out:
            tmp_out_path = tmp_out.name

        try:
            with Image.open(filepath) as img:
                img.convert("RGB").save(tmp_in_path, "PNG")

            vtracer.convert_image_to_svg_py(
                tmp_in_path,
                tmp_out_path,
                colormode="color",
                hierarchical="stacked",
                mode="spline",
                filter_speckle=4,
                color_precision=8,
                layer_difference=16,
                corner_threshold=60,
                length_threshold=4.0,
                max_iterations=10,
                splice_threshold=45,
                path_precision=8,
            )

            with open(tmp_out_path, "rb") as f:
                return f.read()
        finally:
            for p in (tmp_in_path, tmp_out_path):
                try:
                    os.remove(p)
                except OSError:
                    pass

    except Exception:
        pass  # Fall through to embedded-image SVG

    # --- Fallback: embed the raster image as base64 in an SVG wrapper ---
    buf = io.BytesIO()
    with Image.open(filepath) as img:
        img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    svg_content = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <title>Edited Label</title>\n'
        f'  <image x="0" y="0" width="{w}" height="{h}" '
        f'xlink:href="data:image/png;base64,{b64}" />\n'
        f'</svg>\n'
    )
    return svg_content.encode("utf-8")


def _build_pdf_from_image(filepath: str) -> bytes:
    """
    Generate a PDF that contains the edited image at its natural DPI, using
    reportlab if available or falling back to Pillow's built-in PDF writer.
    Returns raw PDF bytes.
    """
    with Image.open(filepath) as img:
        img_rgb = img.convert("RGB")
        px_w, px_h = img_rgb.size
        dpi = img_rgb.info.get("dpi", (300, 300))
        if isinstance(dpi, (int, float)):
            dpi = (dpi, dpi)
        dpi_x, dpi_y = float(dpi[0]) or 300.0, float(dpi[1]) or 300.0

    # Try reportlab first for better quality
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas as rl_canvas

        pt_w = px_w * 72.0 / dpi_x
        pt_h = px_h * 72.0 / dpi_y

        out_io = io.BytesIO()
        c = rl_canvas.Canvas(out_io, pagesize=(pt_w, pt_h))

        # Load the image into reportlab
        img_buf = io.BytesIO()
        with Image.open(filepath) as img:
            img.convert("RGB").save(img_buf, "PNG")
        img_buf.seek(0)

        c.drawImage(ImageReader(img_buf), 0, 0, width=pt_w, height=pt_h)
        c.showPage()
        c.save()
        return out_io.getvalue()

    except ImportError:
        pass  # reportlab not installed, use Pillow fallback

    # Pillow fallback — save as PDF directly
    out_io = io.BytesIO()
    with Image.open(filepath) as img:
        img.convert("RGB").save(out_io, "PDF", resolution=dpi_x)
    return out_io.getvalue()


def _build_cdrx_zip(filepath: str, stem: str) -> bytes:
    """
    Build a .cdrx ZIP package (CorelDRAW X/2019+ exchange format).
    The package contains:
      - document.svg   — the vector/embedded-image SVG
      - preview.png    — a full-quality PNG preview
      - metadata.xml   — minimal CorelDRAW metadata
    CorelDRAW 2019 and later can import .cdrx packages directly.
    """
    import zipfile

    svg_bytes = _build_svg_from_image(filepath)

    png_buf = io.BytesIO()
    with Image.open(filepath) as img:
        img.convert("RGB").save(png_buf, "PNG")
    png_bytes = png_buf.getvalue()

    metadata_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cdrx-metadata xmlns="http://www.corel.com/coreldraw/2019/cdrx">\n'
        f'  <title>{stem}</title>\n'
        '  <application>CorelDRAW</application>\n'
        '  <version>24.0</version>\n'
        '  <document>document.svg</document>\n'
        '  <preview>preview.png</preview>\n'
        '</cdrx-metadata>\n'
    ).encode("utf-8")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("document.svg", svg_bytes)
        zf.writestr("preview.png", png_bytes)
        zf.writestr("metadata.xml", metadata_xml)

    return zip_buf.getvalue()


def _build_gms_script(filepath: str, stem: str) -> bytes:
    """
    Build a CorelDRAW VBA macro script (.gms) that, when run inside CorelDRAW,
    imports the edited image and places it on the active document.
    The image is embedded as a base64 string and decoded at runtime.
    """
    buf = io.BytesIO()
    with Image.open(filepath) as img:
        img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Split b64 into chunks so the VBA string literal stays manageable
    chunk_size = 72
    chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
    b64_lines = "\n        & ".join(f'"{c}"' for c in chunks)

    script = f"""' CorelDRAW Macro Script (.gms) — Generated by Label Editor AI
' To use: Open CorelDRAW → Tools → Macros → Run Macro → Select this file
'         Or copy into the VBA editor (Alt+F11) and press F5

Attribute VB_Name = "LabelEditorImport"

Sub ImportEditedLabel()
    Dim sBase64 As String
    Dim sTempPath As String
    Dim iFile As Integer

    ' Base64-encoded PNG image data
    sBase64 = {b64_lines}

    ' Write decoded PNG to a temp file
    sTempPath = Environ("TEMP") & "\\{stem}_label.png"
    iFile = FreeFile()
    Open sTempPath For Binary As #iFile
        Dim decoded() As Byte
        decoded = DecodeBase64(sBase64)
        Put #iFile, , decoded
    Close #iFile

    ' Import the image into the active CorelDRAW document
    If ActiveDocument Is Nothing Then
        Dim newDoc As Document
        Set newDoc = CreateDocument()
    End If

    Dim importedObj As Shape
    Set importedObj = ActiveLayer.Import(sTempPath)

    If Not importedObj Is Nothing Then
        ' Centre the image on the page
        importedObj.SetPositionEx cdrCenter, cdrCenter, _
            ActivePage.SizeWidth / 2, ActivePage.SizeHeight / 2
        MsgBox "Label imported successfully!", vbInformation, "Label Editor AI"
    Else
        MsgBox "Import failed. Check that the temp file exists: " & sTempPath, _
            vbExclamation, "Label Editor AI"
    End If
End Sub

' ── Base64 decoder helper ─────────────────────────────────────────────────
Private Function DecodeBase64(sBase64 As String) As Byte()
    Dim oXML As Object
    Dim oNode As Object
    Set oXML  = CreateObject("MSXML2.DOMDocument")
    Set oNode = oXML.createElement("b64")
    oNode.DataType = "bin.base64"
    oNode.Text = sBase64
    DecodeBase64 = oNode.nodeTypedValue
End Function
"""
    return script.encode("utf-8")


def _build_cgs_xml(filepath: str, stem: str) -> bytes:
    """
    Build a CorelDRAW Custom Graphic Style (.cgs) XML file.
    This wraps the image as an embedded fill style that can be applied
    to objects inside CorelDRAW via the Object Styles panel.
    """
    buf = io.BytesIO()
    with Image.open(filepath) as img:
        img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    with Image.open(filepath) as img:
        w, h = img.size

    cgs_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cgs-styles xmlns="http://www.corel.com/coreldraw/styles/2015">\n'
        f'  <style name="{stem}" id="label-editor-ai-style">\n'
        '    <fill type="bitmap" tiling="none">\n'
        f'      <bitmap width="{w}" height="{h}" format="png">\n'
        f'        <data encoding="base64">{b64}</data>\n'
        '      </bitmap>\n'
        '    </fill>\n'
        '    <outline none="true"/>\n'
        '  </style>\n'
        '</cgs-styles>\n'
    )
    return cgs_xml.encode("utf-8")


@app.route("/download/<filename>/<fmt>")
def download_image(filename, fmt):
    # Ensure secure filename to prevent path traversal
    filename = secure_filename(filename)
    filepath = os.path.join(app.config["RESULTS_FOLDER"], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    stem = filename.rsplit(".", 1)[0]

    # Upscale the image to 2K resolution (longest side at least 2560 pixels)
    # We will save the upscaled image to a temporary file during the duration of the request.
    import tempfile
    
    # 2K/QHD Target: we upscale the longest side to 2560 pixels to guarantee 2K print quality
    TARGET_MAX_DIM = 2560
    
    temp_filepath = None
    active_filepath = filepath
    try:
        with Image.open(filepath) as img:
            w, h = img.size
            if max(w, h) < TARGET_MAX_DIM:
                scale = TARGET_MAX_DIM / float(max(w, h))
                new_w = int(round(w * scale))
                new_h = int(round(h * scale))
                
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.ANTIALIAS
                
                img_upscaled = img.resize((new_w, new_h), resample_filter)
                
                # Create a temporary file to store the upscaled version
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                    temp_filepath = tmp_file.name
                
                img_upscaled.save(temp_filepath, "PNG", dpi=(300, 300))
                active_filepath = temp_filepath
    except Exception as e:
        app.logger.warning("Failed to upscale image for download: %s. Using original quality.", e)
        active_filepath = filepath

    try:
        # ── PNG ──────────────────────────────────────────────────────────────────
        if fmt == "png":
            if active_filepath != filepath:
                with open(active_filepath, "rb") as f:
                    file_data = f.read()
                out_io = io.BytesIO(file_data)
                return send_file(
                    out_io,
                    mimetype="image/png",
                    as_attachment=True,
                    download_name=stem + ".png",
                )
            else:
                return send_from_directory(app.config["RESULTS_FOLDER"], filename, as_attachment=True)
    
        # ── JPEG ─────────────────────────────────────────────────────────────────
        elif fmt in ("jpg", "jpeg"):
            out_io = io.BytesIO()
            with Image.open(active_filepath) as img:
                img.convert("RGB").save(out_io, "JPEG", quality=100, subsampling=0)
            out_io.seek(0)
            return send_file(
                out_io,
                mimetype="image/jpeg",
                as_attachment=True,
                download_name=stem + ".jpg",
            )
    
        # ── PDF ──────────────────────────────────────────────────────────────────
        elif fmt == "pdf":
            try:
                pdf_bytes = _build_pdf_from_image(active_filepath)
                out_io = io.BytesIO(pdf_bytes)
                return send_file(
                    out_io,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=stem + ".pdf",
                )
            except Exception as exc:
                app.logger.error("PDF export failed: %s", exc)
                return f"PDF export failed: {exc}", 500
    
        # ── SVG ──────────────────────────────────────────────────────────────────
        elif fmt == "svg":
            try:
                svg_bytes = _build_svg_from_image(active_filepath)
                out_io = io.BytesIO(svg_bytes)
                return send_file(
                    out_io,
                    mimetype="image/svg+xml",
                    as_attachment=True,
                    download_name=stem + ".svg",
                )
            except Exception as exc:
                app.logger.error("SVG export failed: %s", exc)
                return f"SVG export failed: {exc}", 500
    
        # ── CDR (CorelDRAW — SVG-compatible import) ───────────────────────────────
        elif fmt == "cdr":
            try:
                svg_bytes = _build_svg_from_image(active_filepath)
                out_io = io.BytesIO(svg_bytes)
                return send_file(
                    out_io,
                    mimetype="application/octet-stream",
                    as_attachment=True,
                    download_name=stem + ".cdr",
                )
            except Exception as exc:
                app.logger.error("CDR export failed: %s", exc)
                return f"CDR export failed: {exc}", 500
    
        # ── CDRx (CorelDRAW X ZIP exchange package) ──────────────────────────────
        elif fmt == "cdrx":
            try:
                zip_bytes = _build_cdrx_zip(active_filepath, stem)
                out_io = io.BytesIO(zip_bytes)
                return send_file(
                    out_io,
                    mimetype="application/octet-stream",
                    as_attachment=True,
                    download_name=stem + ".cdrx",
                )
            except Exception as exc:
                app.logger.error("CDRx export failed: %s", exc)
                return f"CDRx export failed: {exc}", 500
    
        # ── GMS (CorelDRAW VBA macro script) ────────────────────────────────────
        elif fmt == "gms":
            try:
                gms_bytes = _build_gms_script(active_filepath, stem)
                out_io = io.BytesIO(gms_bytes)
                return send_file(
                    out_io,
                    mimetype="application/octet-stream",
                    as_attachment=True,
                    download_name=stem + ".gms",
                )
            except Exception as exc:
                app.logger.error("GMS export failed: %s", exc)
                return f"GMS export failed: {exc}", 500
    
        # ── CGS (CorelDRAW Custom Graphic Style) ────────────────────────────────
        elif fmt == "cgs":
            try:
                cgs_bytes = _build_cgs_xml(active_filepath, stem)
                out_io = io.BytesIO(cgs_bytes)
                return send_file(
                    out_io,
                    mimetype="application/octet-stream",
                    as_attachment=True,
                    download_name=stem + ".cgs",
                )
            except Exception as exc:
                app.logger.error("CGS export failed: %s", exc)
                return f"CGS export failed: {exc}", 500
        
        else:
            return "Unsupported format", 400
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
# auto-reload trigger - refreshed env keys - v3

