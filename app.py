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
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, make_response
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
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
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ---------------------------------------------------------------------------
# API settings
# ---------------------------------------------------------------------------
RECRAFT_API_KEY = os.getenv("RECRAFT_API_KEY")
if RECRAFT_API_KEY:
    RECRAFT_API_KEY = RECRAFT_API_KEY.strip("'\"")

NANOBANANA_API_KEY = os.getenv("ATLASCLOUD_API_KEY") or os.getenv("NANOBANANA_API_KEY")
if NANOBANANA_API_KEY:
    NANOBANANA_API_KEY = NANOBANANA_API_KEY.strip("'\"")

# Base URL for Nano Banana / PixAPI

NANOBANANA_BASE_URL = (os.getenv("ATLASCLOUD_BASE_URL") or os.getenv("NANOBANANA_BASE_URL") or "https://api.pixapi.ai").rstrip("/")
if "pixapi.ai" in NANOBANANA_BASE_URL and "api.pixapi.ai" not in NANOBANANA_BASE_URL:
    NANOBANANA_BASE_URL = NANOBANANA_BASE_URL.replace("pixapi.ai", "api.pixapi.ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY: OPENAI_API_KEY = OPENAI_API_KEY.strip("'\"")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY: GEMINI_API_KEY = GEMINI_API_KEY.strip("'\"")

EDENAI_API_KEY = os.getenv("EDENAI_API_KEY")
if EDENAI_API_KEY: EDENAI_API_KEY = EDENAI_API_KEY.strip("'\"")

GOOGLE_FLOW_API_TOKEN = os.getenv("GOOGLE_FLOW_API_TOKEN") or os.getenv("USEAPI_TOKEN")
if GOOGLE_FLOW_API_TOKEN: GOOGLE_FLOW_API_TOKEN = GOOGLE_FLOW_API_TOKEN.strip("'\"")

GOOGLE_FLOW_EMAIL = os.getenv("GOOGLE_FLOW_EMAIL")
if GOOGLE_FLOW_EMAIL: GOOGLE_FLOW_EMAIL = GOOGLE_FLOW_EMAIL.strip("'\"")


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
        "31.5:11": 31.5/11.0,
        "45.2:14.2": 45.2/14.2,
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
        "11:31.5": 11.0/31.5,
        "14.2:45.2": 14.2/45.2,
        "1:4":  1/4,
        "1:8":  1/8,
    }
    best = min(candidates, key=lambda k: abs(candidates[k] - ratio))
    return best


def _format_pixapi_size(image_size: str) -> str:
    """
    Format aspect ratio or size string to PixAPI GPT Image compatible size.
    PixAPI accepts WIDTHxHEIGHT (e.g. 1024x1024) or 'auto'.
    """
    if not image_size:
        return "1536x512"
    s = str(image_size).strip()
    if "x" in s.lower() and ":" not in s:
        return s

    ratio_to_px = {
        "1:1": "1024x1024",
        "16:9": "1344x768",
        "9:16": "768x1344",
        "4:3": "1152x864",
        "3:4": "864x1152",
        "3:2": "1200x800",
        "2:3": "800x1200",
        "21:9": "1536x656",
        "3:1": "1536x512",
        "4:1": "1536x512",
        "8:1": "1536x512",
        "31.5:11": "1536x512",
        "45.2:14.2": "1536x512",
        "11:31.5": "512x1536",
        "14.2:45.2": "512x1536",
        "1:4": "512x1536",
        "1:8": "512x1536",
    }
    if s in ratio_to_px:
        return ratio_to_px[s]

    try:
        if ":" in s:
            w_str, h_str = s.split(":", 1)
            ratio = float(w_str) / float(h_str)
        else:
            ratio = float(s)
            
        ratio = max(1/3.0, min(3.0, ratio))
        target_area = 1024 * 768
        w = int(round((target_area * ratio) ** 0.5))
        h = int(round(w / ratio))
        w = max(512, min(2048, int(round(w / 16.0) * 16)))
        h = max(512, min(2048, int(round(h / 16.0) * 16)))
        while w * h < 655360:
            if ratio >= 1:
                w += 16
            else:
                h += 16
        if w / h > 3.0:
            w = int(h * 3.0 // 16 * 16)
        elif h / w > 3.0:
            h = int(w * 3.0 // 16 * 16)
        return f"{w}x{h}"
    except Exception:
        return "1536x512"


def _ensure_public_image_url(image_input: str) -> str:
    """
    Ensure the image is a public http(s) URL for PixAPI GPT Image endpoints.
    If it's already an http(s) URL, return it directly.
    If it's a base64 data URI or file path, upload to temporary host (tmpfiles.org) and return the public URL.
    """
    if not image_input:
        return image_input
    if isinstance(image_input, str) and (image_input.startswith("http://") or image_input.startswith("https://")):
        return image_input

    try:
        if isinstance(image_input, str) and image_input.startswith("data:"):
            header, b64_str = image_input.split(",", 1)
            ext = "png"
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "webp" in header:
                ext = "webp"
            img_bytes = base64.b64decode(b64_str)
        elif isinstance(image_input, str) and os.path.exists(image_input):
            ext = os.path.splitext(image_input)[1].lstrip(".") or "png"
            with open(image_input, "rb") as f:
                img_bytes = f.read()
        else:
            return image_input

        filename = f"image_{uuid.uuid4().hex[:8]}.{ext}"
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
        up_resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": (filename, img_bytes, mime)},
            timeout=15,
        )
        if up_resp.status_code == 200:
            up_data = up_resp.json()
            raw_url = up_data.get("data", {}).get("url")
            if raw_url:
                return raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception as e:
        app.logger.warning("Could not upload image to public URL for PixAPI: %s", e)

    return image_input


def _run_atlascloud_prediction(payload: dict, max_wait: int = 180) -> str:
    """
    Submit and poll prediction task for Atlas Cloud API (api.atlascloud.ai).
    """
    api_key = os.getenv("ATLASCLOUD_API_KEY") or NANOBANANA_API_KEY
    if not api_key:
        raise RuntimeError("ATLASCLOUD_API_KEY or NANOBANANA_API_KEY is not configured.")

    base_url = "https://api.atlascloud.ai"
    if NANOBANANA_BASE_URL and "atlascloud" in NANOBANANA_BASE_URL:
        base_url = NANOBANANA_BASE_URL.rstrip("/")

    url = f"{base_url}/api/v1/model/generateImage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    app.logger.info("Sending request to Atlas Cloud API (model=%s)...", payload.get("model"))
    resp = requests.post(url, headers=headers, json=payload, timeout=120)

    if resp.status_code == 402 or "insufficient balance" in resp.text.lower():
        raise RuntimeError("Your Atlas Cloud API key has insufficient balance. Please top up your credits at https://console.atlascloud.ai.")
    if resp.status_code == 401 or "unauthorized" in resp.text.lower():
        raise RuntimeError("Invalid Atlas Cloud API key. Please check your ATLASCLOUD_API_KEY at https://console.atlascloud.ai.")

    if resp.status_code != 200:
        raise RuntimeError(f"Atlas Cloud API returned error {resp.status_code}: {resp.text}")

    res_json = resp.json()
    data = res_json.get("data") or {}
    prediction_id = data.get("id")

    if not prediction_id:
        outputs = data.get("outputs") or []
        if outputs:
            return outputs[0]
        raise RuntimeError(f"No prediction ID or outputs in Atlas Cloud response: {res_json}")

    # Poll prediction result
    poll_url = f"{base_url}/api/v1/model/prediction/{prediction_id}"
    poll_headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.time() + max_wait

    while time.time() < deadline:
        time.sleep(2)
        try:
            poll_resp = requests.get(poll_url, headers=poll_headers, timeout=30)
            if poll_resp.status_code != 200:
                app.logger.warning("Atlas Cloud poll status %d for %s", poll_resp.status_code, prediction_id)
                continue

            poll_json = poll_resp.json()
            poll_data = poll_json.get("data") or {}
            status = (poll_data.get("status") or "").lower()

            if status in ("completed", "succeeded"):
                outputs = poll_data.get("outputs") or []
                if outputs:
                    return outputs[0]
                raise RuntimeError(f"Atlas Cloud prediction completed but output list empty: {poll_json}")
            elif status == "failed":
                err_msg = poll_data.get("error") or "Generation failed"
                raise RuntimeError(f"Atlas Cloud task failed: {err_msg}")
            else:
                app.logger.info("Atlas Cloud task %s status=%s, waiting...", prediction_id, status)
        except RuntimeError:
            raise
        except Exception as e:
            app.logger.warning("Atlas Cloud poll error: %s", e)

    raise RuntimeError(f"Atlas Cloud task {prediction_id} timed out after {max_wait}s")


def run_nanobanana_inpainting(
    image_data_uri: str,
    mask_data_uri: str,
    prompt: str,
    negative_prompt: str = None,
    image_size: str = "8:1",
) -> str:
    """
    Call Nano Banana Image Edit endpoint (Atlas Cloud API or Pixapi).
    """
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY or ATLASCLOUD_API_KEY is not configured.")

    if "pixapi" in NANOBANANA_BASE_URL:
        url = f"{NANOBANANA_BASE_URL}/v1/images/edits"
        headers = {
            "Authorization": f"Bearer {NANOBANANA_API_KEY}",
            "Content-Type": "application/json",
        }
        px_size = _format_pixapi_size(image_size)
        quality = os.getenv("PIXAPI_QUALITY", "low")
        models_to_try = ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2"]
        
        pub_image = _ensure_public_image_url(image_data_uri)
        pub_mask = _ensure_public_image_url(mask_data_uri) if mask_data_uri else None

        last_error = None
        for model_name in models_to_try:
            payload = {
                "image": pub_image,
                "prompt": prompt,
                "model": model_name,
                "n": 1,
                "size": px_size,
                "quality": quality,
            }
            if pub_mask:
                payload["providerOptions"] = {"mask_url": pub_mask}
            for attempt in range(2):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=120)
                    if resp.status_code in (500, 502, 503, 504):
                        last_error = f"Status {resp.status_code}: {resp.text}"
                        time.sleep(2)
                        continue
                    if resp.status_code != 200:
                        if "insufficient" in resp.text.lower() and "credit" in resp.text.lower():
                            raise RuntimeError(f"Your Nano Banana (PixAPI) account has insufficient credits: {resp.text}. Please top up your balance at https://pixapi.ai or switch the API Provider in the UI to Google Gemini or OpenAI.")
                        last_error = f"Error {resp.status_code}: {resp.text}"
                        break
                    result = resp.json()
                    data = result.get("data", {})
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
                    last_error = str(e)
                    time.sleep(2)
                    continue
        raise RuntimeError(f"Nano Banana API request failed. Last error: {last_error}")
    else:
        # Atlas Cloud API
        nb_size_map = {"3:1": "4:1", "11:31.5": "1:4", "31.5:11": "4:1", "45.2:14.2": "4:1", "14.2:45.2": "1:4"}
        nb_size = nb_size_map.get(image_size, image_size)
        payload = {
            "model": "google/nano-banana-2-lite/edit-developer",
            "prompt": prompt,
            "images": [image_data_uri],
            "aspect_ratio": nb_size,
            "enable_sync_mode": False,
            "enable_base64_output": False,
            "resolution": "1k",
        }
        return _run_atlascloud_prediction(payload)



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
        "11:31.5": "720x1280",
        "31.5:11": "1280x720",
        "8:1": "1280x720",
        "45.2:14.2": "1280x720",
        "14.2:45.2": "720x1280",
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
    Call Nano Banana Text-to-Image generate endpoint (Atlas Cloud API or Pixapi).
    """
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY or ATLASCLOUD_API_KEY is not configured.")

    if "pixapi" in NANOBANANA_BASE_URL:
        url = f"{NANOBANANA_BASE_URL}/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {NANOBANANA_API_KEY}",
            "Content-Type": "application/json",
        }
        px_size = _format_pixapi_size(image_size)
        quality = os.getenv("PIXAPI_QUALITY", "low")
        models_to_try = ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2"]
        last_error = None
        for model_name in models_to_try:
            payload = {
                "prompt": prompt,
                "model": model_name,
                "n": 1,
                "size": px_size,
                "quality": quality,
            }
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            for attempt in range(2):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=120)
                    if resp.status_code in (500, 502, 503, 504):
                        last_error = f"Status {resp.status_code}: {resp.text}"
                        time.sleep(2)
                        continue
                    if resp.status_code != 200:
                        if "insufficient" in resp.text.lower() and "credit" in resp.text.lower():
                            raise RuntimeError(f"Your Nano Banana (PixAPI) account has insufficient credits: {resp.text}. Please top up your balance at https://pixapi.ai or switch the API Provider in the UI to Google Gemini or OpenAI.")
                        last_error = f"Error {resp.status_code}: {resp.text}"
                        break
                    result = resp.json()
                    data = result.get("data", {})
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
                    last_error = str(e)
                    time.sleep(2)
                    continue
        raise RuntimeError(f"Nano Banana API request failed. Last error: {last_error}")
    else:
        # Atlas Cloud API
        nb_size_map = {"3:1": "4:1", "11:31.5": "1:4", "31.5:11": "4:1", "45.2:14.2": "4:1", "14.2:45.2": "1:4"}
        nb_size = nb_size_map.get(image_size, image_size)
        payload = {
            "model": "google/nano-banana-2-lite/text-to-image",
            "prompt": prompt,
            "aspect_ratio": nb_size,
            "enable_sync_mode": False,
            "enable_base64_output": False,
            "resolution": "1k",
            "thinking_level": "default",
        }
        return _run_atlascloud_prediction(payload)



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
    Translates the prompt text to English using Gemini (or OpenAI as fallback) 
    to support multi-language input (Hindi, Gujarati, etc).
    """
    if not text:
        return ""
    text = text.strip()
    
    # Try Gemini first for translation (Fast and cheap)
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_gemini_"):
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"Translate the following text to English. If it is already in English, output it exactly as is. Output ONLY the translated English text, nothing else.\n\nText: {text}"}]}]
            }
            headers = {"Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            translated = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            app.logger.info(f"Translated prompt via Gemini: '{text}' -> '{translated}'")
            return translated
        except Exception as e:
            app.logger.error(f"Gemini translation failed: {e}")

    # Fallback to OpenAI if Gemini fails or is missing
    if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("your_openai_"):
        try:
            import requests
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a translator. Translate the user's text to English. If it is already in English, return it unchanged. Output ONLY the translated English text, without quotes or explanation."},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            translated = resp.json()["choices"][0]["message"]["content"].strip()
            app.logger.info(f"Translated prompt via OpenAI: '{text}' -> '{translated}'")
            return translated
        except Exception as e:
            app.logger.error(f"OpenAI translation failed: {e}")

    # Fallback to returning original text if all APIs fail
    return text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def run_openai_generations(prompt: str, image_size: str = "1:1") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    size_map = {
        "1:1": "1024x1024", "16:9": "1792x1024", "9:16": "1024x1792",
        "4:3": "1792x1024", "3:4": "1024x1792", "3:1": "1792x1024",
        "11:31.5": "1024x1792", "31.5:11": "1792x1024",
        "45.2:14.2": "1792x1024", "14.2:45.2": "1024x1792"
    }
    size_str = size_map.get(image_size, "1024x1024")
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size_str,
        "response_format": "b64_json"
    }
    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    b64 = resp.json()["data"][0]["b64_json"]
    return f"data:image/png;base64,{b64}"

def run_gemini_generations(prompt: str, image_size: str = "1:1") -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent?key={GEMINI_API_KEY}"
    size_map = {
        "1:1": "1:1", "16:9": "16:9", "9:16": "9:16",
        "4:3": "4:3", "3:4": "3:4",
        "11:31.5": "9:16", "31.5:11": "16:9",
        "45.2:14.2": "16:9", "14.2:45.2": "9:16"
    }
    aspect_ratio = size_map.get(image_size, "1:1")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "image/jpeg"
        }
    }
    headers = {"Content-Type": "application/json"}
    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    # The new API returns the base64 image differently based on the new spec
    try:
        # Assuming the new response structure
        b64 = resp.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except KeyError:
        raise RuntimeError(f"Unexpected response format from Gemini: {resp.text}")
    return f"data:image/jpeg;base64,{b64}"

def run_edenai_generations(prompt: str, image_size: str = "1:1") -> str:
    if not EDENAI_API_KEY:
        raise RuntimeError("EDENAI_API_KEY is not configured.")
    url = "https://api.edenai.run/v2/image/generation"
    headers = {
        "Authorization": f"Bearer {EDENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    size_map = {
        "1:1": "1024x1024", "16:9": "1024x1024", "9:16": "1024x1024",
        "4:3": "1024x1024", "3:4": "1024x1024",
        "11:31.5": "1024x1024", "31.5:11": "1024x1024",
        "45.2:14.2": "1024x1024", "14.2:45.2": "1024x1024"
    }
    size_str = size_map.get(image_size, "1024x1024")
    payload = {
        "providers": "openai",
        "text": prompt,
        "resolution": size_str
    }
    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    try:
        provider_key = next((k for k in data.keys() if "openai" in k), "openai")
        item = data[provider_key]["items"][0]
        if "image_b64" in item and item["image_b64"]:
            return f"data:image/png;base64,{item['image_b64']}"
        elif "image" in item and item["image"]:
            return f"data:image/png;base64,{item['image']}"
        else:
            return item["image_resource_url"]
    except (KeyError, IndexError, StopIteration):
        raise RuntimeError(f"Unexpected response format from Eden AI: {resp.text}")

def run_openai_inpainting(*args, **kwargs):
    raise RuntimeError("OpenAI (DALL-E 3) does not support inpainting. Please use Recraft or Nano Banana.")

def run_gemini_inpainting(*args, **kwargs):
    raise RuntimeError("Google Gemini (Imagen 3) does not support inpainting. Please use Recraft or Nano Banana.")

def run_googleflow_generations(prompt: str, image_size: str = "1:1", model: str = "nano-banana-2-lite") -> str:
    """Generate image via Google Flow API (Nano Banana 2 Lite / 2.1 / Pro)."""
    import google_flow_api
    res = google_flow_api.generate_google_flow_image(
        prompt=prompt,
        model=model,
        aspect_ratio=image_size,
        count=1
    )
    return res["primary_data_uri"]

def run_googleflow_inpainting(image_path: str, mask_path: str = None, prompt: str = "", negative_prompt: str = None, image_size: str = "1:1", model: str = "nano-banana-2-lite") -> str:
    """Inpaint / image-to-image edit via Google Flow API with reference asset."""
    import google_flow_api
    res = google_flow_api.generate_google_flow_image(
        prompt=prompt,
        model=model,
        aspect_ratio=image_size or "auto",
        reference_images=[image_path],
        count=1
    )
    return res["primary_data_uri"]


@app.route("/")
def index():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


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
    image_size = request.form.get("image_size", "3:1").strip()
    negative_prompt = request.form.get(
        "negative_prompt",
        "blurry, low quality, distorted text, watermark, artifacts",
    ).strip()

    # ---- Validate API keys based on provider ----
    if api_provider == "recraft":
        if not RECRAFT_API_KEY or RECRAFT_API_KEY.startswith("your_recraft_"):
            return jsonify({"error": "RECRAFT_API_KEY is not configured. Create a .env file with your key from your Recraft.ai profile."}), 500
    elif api_provider == "openai":
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your_openai_"):
            return jsonify({"error": "OPENAI_API_KEY is not configured."}), 500
    elif api_provider == "gemini":
        if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your_gemini_"):
            return jsonify({"error": "GEMINI_API_KEY is not configured."}), 500
    elif api_provider == "edenai":
        if not EDENAI_API_KEY or EDENAI_API_KEY.startswith("your_edenai_"):
            return jsonify({"error": "EDENAI_API_KEY is not configured."}), 500
    elif api_provider in ("googleflow", "google-flow"):
        if not GOOGLE_FLOW_API_TOKEN or GOOGLE_FLOW_API_TOKEN.startswith("your_"):
            return jsonify({"error": "GOOGLE_FLOW_API_TOKEN is not configured in .env."}), 500
        if not GOOGLE_FLOW_EMAIL or GOOGLE_FLOW_EMAIL.startswith("your_"):
            return jsonify({"error": "GOOGLE_FLOW_EMAIL is not configured in .env."}), 500
    else:
        if not NANOBANANA_API_KEY or NANOBANANA_API_KEY.startswith("your_nanobanana_"):
            return jsonify({"error": "NANOBANANA_API_KEY is not configured. Create a .env file with your key from your Nano Banana dashboard."}), 500
            

    # ---- Handle Text-to-Image Generation (No Image Uploaded) ----
    if not has_image:
        unique_stem = str(uuid.uuid4())[:8]
        try:
            enhanced_prompt = enhance_prompt_layout(prompt)
            if api_provider == "recraft":
                app.logger.info("Running Recraft.ai Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_recraft_generations(enhanced_prompt, negative_prompt, image_size)
            elif api_provider == "openai":
                app.logger.info("Running OpenAI DALL-E 3 Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_openai_generations(enhanced_prompt, image_size)
            elif api_provider == "gemini":
                app.logger.info("Running Google Gemini Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_gemini_generations(enhanced_prompt, image_size)
            elif api_provider == "edenai":
                app.logger.info("Running Eden AI Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_edenai_generations(enhanced_prompt, image_size)
            elif api_provider in ("googleflow", "google-flow"):
                app.logger.info("Running Google Flow Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_googleflow_generations(enhanced_prompt, image_size)
            else:
                app.logger.info("Running Nano Banana Text-to-Image Generation (size=%s)...", image_size)
                final_image_url = run_nanobanana_generations(enhanced_prompt, negative_prompt, image_size)
            
            # Download result or decode base64
            if final_image_url.startswith("data:image"):
                import base64
                b64_data = final_image_url.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_data)
            else:
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
                    ImageOps.fit(img, (original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")

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
                    ImageOps.fit(img, (original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")

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

        else:
            # Pixapi uses GPT (ChatGPT) models that understand direct edit instructions
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
            
        elif api_provider == "openai":
            final_image_url = run_openai_inpainting(input_path, mask_path, inpaint_prompt, negative_prompt)
        elif api_provider == "gemini":
            final_image_url = run_gemini_inpainting(input_path, mask_path, inpaint_prompt, negative_prompt)
        elif api_provider in ("googleflow", "google-flow"):
            app.logger.info("Running Google Flow Image Edit (mode=%s)...", mode)
            nb_size = compute_image_size_ratio(original_w, original_h)
            final_image_url = run_googleflow_inpainting(input_path, None, inpaint_prompt, negative_prompt, nb_size)
        elif api_provider == "edenai":
            raise RuntimeError("Eden AI (DALL-E 3) does not support inpainting. Please use Recraft or Nano Banana.")
        else:
            app.logger.info("Running Pixapi GPT Image Edit (mode=%s) ...", mode)
            nb_size = compute_image_size_ratio(original_w, original_h)
            app.logger.info("Using size=%s for %dx%d input", nb_size, original_w, original_h)
            final_image_url = run_nanobanana_inpainting(
                image_data_uri, mask_data_uri, inpaint_prompt, negative_prompt, nb_size
            )

        # ---- Step 4: Download result or decode base64 ----
        if final_image_url.startswith("data:image"):
            import base64
            b64_data = final_image_url.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
        else:
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

            # Maintain max sharpness & high resolution (ensure at least 2048px on max side)
            min_target_dim = max(2048, original_w, original_h)
            cur_max = max(img.size[0], img.size[1])
            if cur_max < min_target_dim:
                scale = min_target_dim / float(cur_max)
                new_w = int(round(img.size[0] * scale))
                new_h = int(round(img.size[1] * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            img.save(output_path, "PNG", dpi=(300, 300))

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
        if api_provider == "nanobanana":
            if "payment_required" in err_msg.lower() or "insufficient" in err_msg.lower() or "402" in err_msg or "credit" in err_msg.lower():
                return jsonify({
                    "error": (
                        f"Nano Banana / PixAPI error: {err_msg}. "
                        "Please check your Nano Banana / PixAPI credit balance or API key."
                    )
                }), 400
        return jsonify({"error": err_msg}), 500
    except Exception as exc: 
        app.logger.exception("Unexpected error during processing.")
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


# The static routes below have been removed because they conflict with Flask's built-in 
# static file handler, which already serves files from the `static` directory automatically.
# This prevents broken images in the browser on Windows.



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
        raw_prompt      = (data.get("prompt") or "").strip()
        api_provider    = (data.get("api_provider") or "nanobanana").lower()
        user_image_size = (data.get("image_size") or "").strip()
        negative_prompt = (data.get("negative_prompt") or "blurry, low quality, distorted text, watermark, artifacts").strip()
    else:
        raw_prompt      = request.form.get("prompt", "").strip()
        api_provider    = request.form.get("api_provider", "nanobanana").lower()
        user_image_size = request.form.get("image_size", "").strip()
        negative_prompt = request.form.get(
            "negative_prompt",
            "blurry, low quality, distorted text, watermark, artifacts",
        ).strip()
        
    uploaded_files = request.files.getlist("images")
    if uploaded_files:
        for file in uploaded_files:
            if file and file.filename:
                original_name = secure_filename(file.filename)
                unique_stem_file = str(uuid.uuid4())[:8]
                ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "png"
                save_name = f"{unique_stem_file}_{original_name}"
                input_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
                file.save(input_path)
                
                db_image = UploadedImage(
                    filename=save_name,
                    original_name=original_name,
                    file_path=input_path,
                    description=raw_prompt,
                )
                db.session.add(db_image)
                db.session.commit()
                
                try:
                    with Image.open(input_path) as img:
                        original_w, original_h = img.size
                        img = img.convert("RGBA" if ext == "png" else "RGB")
                        img.save(input_path)
                    db_image.width = original_w
                    db_image.height = original_h
                    db.session.commit()
                except Exception as e:
                    app.logger.warning(f"Could not process image dimensions for {original_name}: {e}")

    if not raw_prompt:
        return jsonify({"error": "A prompt is required."}), 400

    # Translate if needed
    prompt = translate_prompt(raw_prompt)

    # Validate API keys
    if api_provider == "recraft":
        if not RECRAFT_API_KEY or RECRAFT_API_KEY.startswith("your_recraft_"):
            return jsonify({"error": "RECRAFT_API_KEY is not configured."}), 500
    elif api_provider == "openai":
        if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("your_openai_"):
            return jsonify({"error": "OPENAI_API_KEY is not configured."}), 500
    elif api_provider == "gemini":
        if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your_gemini_"):
            return jsonify({"error": "GEMINI_API_KEY is not configured."}), 500
    elif api_provider in ("googleflow", "google-flow"):
        if not GOOGLE_FLOW_API_TOKEN or GOOGLE_FLOW_API_TOKEN.startswith("your_"):
            return jsonify({"error": "GOOGLE_FLOW_API_TOKEN (or USEAPI_TOKEN) is not configured in .env."}), 500
        if not GOOGLE_FLOW_EMAIL or GOOGLE_FLOW_EMAIL.startswith("your_"):
            return jsonify({"error": "GOOGLE_FLOW_EMAIL is not configured in .env."}), 500
    else:
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
                        ImageOps.fit(img, (original_w, original_h), Image.Resampling.LANCZOS).save(output_path, "PNG")
                        
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
            elif api_provider == "openai":
                final_url = run_openai_inpainting(input_path, None, prompt, negative_prompt)
            elif api_provider == "gemini":
                final_url = run_gemini_inpainting(input_path, None, prompt, negative_prompt)
            elif api_provider in ("googleflow", "google-flow"):
                nb_size = compute_image_size_ratio(original_w, original_h)
                final_url = run_googleflow_inpainting(input_path, None, prompt, negative_prompt, nb_size)
            else:
                # Pixapi GPT - skip CLIPSeg, use direct edit instruction
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
                if final_url.startswith("data:image"):
                    import base64
                    b64_data = final_url.split(",", 1)[1]
                    img_bytes = base64.b64decode(b64_data)
                else:
                    result_resp = requests.get(final_url, timeout=30)
                    result_resp.raise_for_status()
                    img_bytes = result_resp.content

                output_filename = f"result_{unique_stem}.png"
                output_path = os.path.join(app.config["RESULTS_FOLDER"], output_filename)
                with Image.open(io.BytesIO(img_bytes)) as img:
                    if img.size != (original_w, original_h):
                        img = ImageOps.fit(img, (original_w, original_h), Image.Resampling.LANCZOS)
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
                        "or change the API Provider to Recraft.ai."
                    )
                }), 400
            # Fall through to generation below

    # ----------------------------------------------------------------
    # Step 2b: No match (or inpainting failed) → generate new image
    # ----------------------------------------------------------------
    try:
        # Prioritize explicitly chosen aspect ratio if provided by user
        if user_image_size:
            gen_size = user_image_size
        else:
            ref_img = UploadedImage.query.order_by(UploadedImage.created_at.desc()).first()
            if ref_img and ref_img.width and ref_img.height:
                gen_size = compute_image_size_ratio(ref_img.width, ref_img.height)
            else:
                gen_size = "3:1"

        enhanced_prompt = enhance_prompt_layout(prompt)

        if api_provider == "recraft":
            final_url = run_recraft_generations(enhanced_prompt, negative_prompt, gen_size)
        elif api_provider == "openai":
            final_url = run_openai_generations(enhanced_prompt, gen_size)
        elif api_provider == "gemini":
            final_url = run_gemini_generations(enhanced_prompt, gen_size)
        elif api_provider == "edenai":
            final_url = run_edenai_generations(enhanced_prompt, gen_size)
        elif api_provider in ("googleflow", "google-flow"):
            final_url = run_googleflow_generations(enhanced_prompt, gen_size)
        else:
            final_url = run_nanobanana_generations(enhanced_prompt, negative_prompt, gen_size)

        if final_url.startswith("data:image"):
            import base64
            b64_data = final_url.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
        else:
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
        if api_provider == "nanobanana":
            if "payment_required" in err_msg.lower() or "insufficient" in err_msg.lower() or "402" in err_msg or "credit" in err_msg.lower():
                return jsonify({
                    "error": (
                        f"Nano Banana / PixAPI error: {err_msg}. "
                        "Please check your Nano Banana / PixAPI credit balance or API key."
                    )
                }), 400
        return jsonify({"error": f"Smart process failed: {err_msg}"}), 500


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------
def _build_svg_from_image(filepath: str) -> bytes:
    """
    Build a high-resolution lossless SVG container.
    This guarantees 100% crisp photo quality, sharp text, and zero distortion
    when opened in CorelDRAW, Canva, Illustrator, or exported to PDF.
    It embeds the exact original AI-generated image perfectly.
    """
    import base64
    from PIL import Image
    import io
    import os

    try:
        buf = io.BytesIO()
        with Image.open(filepath) as img:
            w, h = img.size
            # Convert to RGBA to ensure perfect color fidelity and transparency
            img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB").save(buf, "PNG", dpi=(300, 300))
        
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        # We use a standard SVG wrapper. CorelDRAW imports this perfectly.
        # This keeps colors and text exactly as generated (zero issues/vandho).
        svg_content = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}px" height="{h}px" viewBox="0 0 {w} {h}">\n'
            f'  <title>Edited Label</title>\n'
            f'  <g id="Original_Image_Layer">\n'
            f'    <image x="0" y="0" width="{w}" height="{h}" '
            f'preserveAspectRatio="none" xlink:href="data:image/png;base64,{b64}" />\n'
            f'  </g>\n'
        )
        
        # We skip adding vector paths because vector tracing ruins photo quality 
        # ("fati jay") and user just wants the raster image embedded with editable text.
        svg_content += f'</svg>\n'
        return svg_content.encode("utf-8")

    except Exception as e:
        app.logger.error("Failed to build SVG: %s", e)
        raise



def _get_ultra_hd_cache_path(filepath: str, target_max_dim: int = 7600) -> str:
    """
    Returns path to cached Ultra-HD version of the image at 300 DPI.
    Produces a master image around 15-18 MB (PNG) with Lanczos resampling,
    edge unsharp-masking, and contrast micro-tuning so text, fine details,
    and barcodes remain crystal clear when zoomed in to 1000%.
    """
    stem, _ = os.path.splitext(filepath)
    cache_path = f"{stem}_ultrahd_{target_max_dim}.png"

    # Return cached file if valid and newer than source
    if os.path.exists(cache_path):
        try:
            if os.path.getmtime(cache_path) >= os.path.getmtime(filepath):
                return cache_path
        except OSError:
            pass

    # Generate the Ultra-HD version
    with Image.open(filepath) as img:
        im = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
        w, h = im.size
        scale = max(1.0, target_max_dim / float(max(w, h)))
        if scale > 1.0:
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Edge typography unsharp-masking
            im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=160, threshold=2))
            enh = ImageEnhance.Contrast(im)
            im = enh.enhance(1.03)
        # compress_level=1 preserves lossless raw pixel master at ~15-18 MB
        im.save(cache_path, format="PNG", dpi=(300, 300), compress_level=1)

    return cache_path


def _get_ultra_hd_image(filepath: str, target_max_dim: int = 7600) -> Image.Image:
    """
    Load an Ultra-HD image, using disk cache for instant retrieval.
    """
    cache_path = _get_ultra_hd_cache_path(filepath, target_max_dim)
    return Image.open(cache_path)


def _build_pdf_from_image(filepath: str) -> bytes:
    """
    Generate an Ultra-HD 300 DPI PDF (~15-18 MB) that preserves crystal-clear
    details, text, and graphics when zoomed in.
    """
    with _get_ultra_hd_image(filepath, target_max_dim=7600) as hd_img:
        img_rgb = hd_img.convert("RGB")
        px_w, px_h = img_rgb.size
        dpi_val = 300.0

        # Try reportlab first for true 300 DPI print canvas
        try:
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas as rl_canvas

            pt_w = px_w * 72.0 / dpi_val
            pt_h = px_h * 72.0 / dpi_val

            out_io = io.BytesIO()
            c = rl_canvas.Canvas(out_io, pagesize=(pt_w, pt_h))

            img_buf = io.BytesIO()
            img_rgb.save(img_buf, format="PNG", dpi=(300, 300), compress_level=1)
            img_buf.seek(0)

            c.drawImage(ImageReader(img_buf), 0, 0, width=pt_w, height=pt_h)
            c.showPage()
            c.save()
            return out_io.getvalue()

        except ImportError:
            pass  # reportlab not installed, use Pillow fallback

        # Pillow high-res fallback — save as PDF directly with 300 DPI and maximum quality
        out_io = io.BytesIO()
        img_rgb.save(out_io, "PDF", resolution=dpi_val, quality=100, subsampling=0)
        return out_io.getvalue()


def _build_cdrx_zip(filepath: str, stem: str) -> bytes:
    """
    Build a CorelDRAW compatible ZIP package containing SVG, Ultra-HD PDF,
    and Ultra-HD PNG.
    """
    import zipfile

    svg_bytes = _build_svg_from_image(filepath)
    pdf_bytes = _build_pdf_from_image(filepath)

    cache_path = _get_ultra_hd_cache_path(filepath, target_max_dim=8000)
    with open(cache_path, "rb") as f:
        png_bytes = f.read()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # We give them a cleanly embedded SVG that Corel imports 100% perfectly
        zf.writestr(f"{stem}_coreldraw_import.svg", svg_bytes)
        # We also include an Ultra-HD PDF as an alternative vector wrapper
        zf.writestr(f"{stem}_coreldraw_import.pdf", pdf_bytes)
        # And the pure Ultra-HD image (~20MB)
        zf.writestr(f"{stem}_ultra_hd.png", png_bytes)
        
        # Write a readme to guide the user
        readme = (
            "How to open in CorelDRAW 2020 without text/color issues:\n"
            "----------------------------------------------------------\n"
            "1. Open CorelDRAW.\n"
            "2. Create a new document.\n"
            "3. Go to File -> Import (Ctrl+I).\n"
            f"4. Select '{stem}_coreldraw_import.svg' or '{stem}_coreldraw_import.pdf'.\n"
            "5. Both formats contain the exact original picture embedded so NO color or text will be lost or distorted!\n"
            "Note: A 'hidden' vector layer is also included in the SVG if you want the traced vector paths.\n"
        )
        zf.writestr("Instructions.txt", readme.encode("utf-8"))

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
# ---------------------------------------------------------------------------
# OCR Digitizer Route
# ---------------------------------------------------------------------------

@app.route("/digitize-label", methods=["POST"])
def digitize_label():
    try:
        data = request.get_json(force=True)
        filename = data.get("filename")
        if not filename:
            return jsonify({"error": "No filename provided"}), 400
            
        filename = secure_filename(filename)
        # Check in results folder first, then uploads
        filepath = os.path.join(app.config["RESULTS_FOLDER"], filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if not os.path.exists(filepath):
                return jsonify({"error": "File not found"}), 404
                
        stem = filename.rsplit(".", 1)[0]
        clean_filename = f"{stem}_clean.png"
        clean_filepath = os.path.join(app.config["RESULTS_FOLDER"], clean_filename)
        
        # Run digitizer logic
        import digitizer
        text_elements, svg_content, dims = digitizer.digitize_image(filepath, clean_filepath)
        
        clean_url = f"/static/results/{clean_filename}"
        orig_url = f"/static/results/{filename}" if os.path.exists(os.path.join(app.config["RESULTS_FOLDER"], filename)) else f"/static/uploads/{filename}"
        
        return jsonify({
            "clean_image_url": clean_url,
            "original_image_url": orig_url,
            "text_elements": text_elements,
            "svg_content": svg_content,
            "image_width": dims[0],
            "image_height": dims[1]
        })
    except Exception as e:
        app.logger.error("Digitizer failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/save-editor-result", methods=["POST"])
def save_editor_result():
    """
    Saves the edited canvas from the Canva Studio directly as the active result image,
    updating the project and regenerating print/raster assets.
    """
    try:
        data = request.get_json(force=True)
        filename = data.get("filename")
        image_data = data.get("image_data")
        if not filename or not image_data:
            return jsonify({"error": "Missing filename or image data"}), 400
            
        filename = secure_filename(filename)
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        decoded = base64.b64decode(image_data)
        
        target_path = os.path.join(app.config["RESULTS_FOLDER"], filename)
        with open(target_path, "wb") as f:
            f.write(decoded)
            
        # Invalidate Ultra-HD cache so subsequent downloads generate from the edited image
        stem, _ = os.path.splitext(target_path)
        cache_path = f"{stem}_ultrahd_8000.png"
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass
                
        return jsonify({
            "success": True,
            "result_image": f"/static/results/{filename}?t={int(time.time())}"
        })
    except Exception as e:
        app.logger.error("Failed to save editor result: %s", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Canva Pro AI Tools Routes
# ---------------------------------------------------------------------------

@app.route("/api/canva/upload-image", methods=["POST"])
def canva_upload_image():
    """
    Direct upload endpoint for Canva Packaging Studio:
    Accepts an uploaded image file (or base64 data), saves it to UPLOAD_FOLDER,
    and returns dimensions, aspect ratio, clean preview, and URL.
    """
    try:
        image_file = request.files.get("image") or request.files.get("file")
        image_b64 = None

        if not image_file and request.is_json:
            data = request.get_json(silent=True) or {}
            image_b64 = data.get("image_data")

        if not image_file and not image_b64:
            return jsonify({"error": "No image file or image_data provided"}), 400

        unique_stem = f"canva_{uuid.uuid4().hex[:10]}"
        save_name = f"{unique_stem}.png"
        input_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)

        if image_file:
            orig_filename = secure_filename(image_file.filename) or "upload.png"
            image_file.save(input_path)
        else:
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            raw_bytes = base64.b64decode(image_b64)
            with open(input_path, "wb") as f:
                f.write(raw_bytes)
            orig_filename = "pasted_image.png"

        # Determine dimensions and aspect ratio with PIL
        with Image.open(input_path) as pil_img:
            w, h = pil_img.size
            if pil_img.mode not in ("RGB", "RGBA"):
                pil_img = pil_img.convert("RGBA" if "transparency" in pil_img.info else "RGB")
                pil_img.save(input_path)

        # Detect approximate aspect ratio name
        ratio = w / float(h)
        if 2.6 <= ratio <= 3.5:
            aspect_name = "3:1 (Ultra-Wide Packaging Label)"
        elif 3.5 < ratio:
            aspect_name = "4:1 (Panoramic Wrap Label)"
        elif 1.6 <= ratio <= 2.0:
            aspect_name = "16:9 (Landscape Banner)"
        elif 0.85 <= ratio <= 1.15:
            aspect_name = "1:1 (Square Product Box)"
        elif ratio < 0.85:
            aspect_name = "Vertical Packaging"
        else:
            aspect_name = f"{round(ratio, 2)}:1 Custom Label"

        app.logger.info("Canva direct image uploaded: %s (%dx%d, %s)", save_name, w, h, aspect_name)

        return jsonify({
            "success": True,
            "filename": save_name,
            "original_name": orig_filename,
            "image_url": f"/static/uploads/{save_name}?t={int(time.time())}",
            "width": w,
            "height": h,
            "aspect_name": aspect_name,
            "aspect_ratio": ratio
        })
    except Exception as e:
        app.logger.error("Canva direct image upload failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/bg-remover", methods=["POST"])
def canva_bg_remover():
    """Removes background from an image or layer, returning transparent PNG."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.remove_background(raw_bytes)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva BG Remover error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/magic-eraser", methods=["POST"])
def canva_magic_eraser():
    """Erases brushed objects or imperfections cleanly using Telea inpainting."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        mask_b64 = data.get("mask_data", "")
        radius = int(data.get("radius", 7))

        if not img_b64 or not mask_b64:
            return jsonify({"error": "Missing image or mask data"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        if "," in mask_b64:
            mask_b64 = mask_b64.split(",", 1)[1]

        raw_img = base64.b64decode(img_b64)
        raw_mask = base64.b64decode(mask_b64)

        erased_bytes = canva_pro_tools.magic_erase(raw_img, raw_mask, radius=radius)
        out_b64 = "data:image/png;base64," + base64.b64encode(erased_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Magic Eraser error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/upscale", methods=["POST"])
def canva_upscale():
    """Upscales image to Ultra-HD 300 DPI super-resolution."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        scale = float(data.get("scale", 2.0))

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        upscaled_bytes = canva_pro_tools.upscale_super_res(raw_bytes, scale_factor=scale)
        out_b64 = "data:image/png;base64," + base64.b64encode(upscaled_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Upscale error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/bg-generator", methods=["POST"])
def canva_bg_generator():
    """Generates designer product packaging background."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        preset = data.get("preset", "carbon_dark")
        width = int(data.get("width", 1536))
        height = int(data.get("height", 512))

        bg_bytes = canva_pro_tools.generate_preset_background(preset, width=width, height=height)
        out_b64 = "data:image/png;base64," + base64.b64encode(bg_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva BG Generator error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/vectorify", methods=["POST"])
def canva_vectorify():
    """Converts a raster image or logo into scalable SVG vectors using vtracer."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        svg_str = canva_pro_tools.vectorify_image(raw_bytes)
        return jsonify({"svg_content": svg_str, "success": True})
    except Exception as e:
        app.logger.error("Canva Vectorify error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/texture", methods=["POST"])
def canva_texture():
    """Overlays realistic packaging textures (crumpled paper, foil, screen, carbon)."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        texture_name = data.get("texture", "paper")
        opacity = float(data.get("opacity", 0.35))

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_packaging_texture(raw_bytes, texture_name=texture_name, opacity=opacity)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Texture error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/style-match", methods=["POST"])
def canva_style_match():
    """Applies artistic styles: Etching, Scrapbook, Line Art."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        style_name = data.get("style", "etching")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400

        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_artistic_style(raw_bytes, style_name=style_name)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")

        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Style Match error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/blur", methods=["POST"])
def canva_blur():
    """Applies blur to the image."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        blur_radius = int(data.get("radius", 15))
        blur_type = data.get("type", "gaussian")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_blur(raw_bytes, blur_radius=blur_radius, blur_type=blur_type)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")
        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Blur error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/auto-focus", methods=["POST"])
def canva_auto_focus():
    """Depth-of-field portrait/product blur keeping subject sharp."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        blur_strength = int(data.get("blur_strength", 25))

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_auto_focus(raw_bytes, blur_strength=blur_strength)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")
        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Auto Focus error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/face-retouch", methods=["POST"])
def canva_face_retouch():
    """Model/Face skin smoothing and radiance retouching."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        smoothness = float(data.get("smoothness", 0.6))

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_face_retouch(raw_bytes, smoothness=smoothness)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")
        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Face Retouch error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/magic-expand", methods=["POST"])
def canva_magic_expand():
    """Expands canvas outward (e.g. 1:1 to 3:1 packaging wrap) using mirror inpainting."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        aspect = data.get("aspect", "3:1")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes = canva_pro_tools.apply_magic_expand(raw_bytes, target_aspect=aspect)
        out_b64 = "data:image/png;base64," + base64.b64encode(result_bytes).decode("ascii")
        return jsonify({"image_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Magic Expand error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/magic-grab", methods=["POST"])
def canva_magic_grab():
    """Extracts foreground subject into a movable layer and inpaints background."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result = canva_pro_tools.magic_grab(raw_bytes)
        fg_b64 = "data:image/png;base64," + base64.b64encode(result["foreground_bytes"]).decode("ascii")
        bg_b64 = "data:image/png;base64," + base64.b64encode(result["background_bytes"]).decode("ascii")

        return jsonify({
            "foreground_url": fg_b64,
            "background_url": bg_b64,
            "bbox": result["bbox"],
            "success": True
        })
    except Exception as e:
        app.logger.error("Canva Magic Grab error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/detect-text", methods=["POST"])
def canva_detect_text():
    """Detects text elements on canvas image without modifying or inpainting the image."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result = canva_pro_tools.detect_text(raw_bytes)
        return jsonify(result)
    except Exception as e:
        app.logger.error("Canva Detect Text error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/inpaint-text", methods=["POST"])
def canva_inpaint_text():
    """Selectively inpaints only specified text regions, leaving all other pixels 100% intact."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        regions = data.get("regions", [])

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        clean_bytes = canva_pro_tools.inpaint_text_regions(raw_bytes, regions)
        bg_b64 = "data:image/png;base64," + base64.b64encode(clean_bytes).decode("ascii")

        return jsonify({
            "clean_background_url": bg_b64,
            "success": True
        })
    except Exception as e:
        app.logger.error("Canva Inpaint Text error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/grab-text", methods=["POST"])
def canva_grab_text():
    """Detects text boxes, erases raster text, and returns editable text elements."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result = canva_pro_tools.grab_text(raw_bytes)
        bg_b64 = "data:image/png;base64," + base64.b64encode(result["clean_background_bytes"]).decode("ascii")

        return jsonify({
            "clean_background_url": bg_b64,
            "text_elements": result["text_elements"],
            "count": len(result["text_elements"]),
            "image_width": result.get("image_width"),
            "image_height": result.get("image_height"),
            "success": True
        })
    except Exception as e:
        app.logger.error("Canva Grab Text error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/image-to-video", methods=["POST"])
def canva_image_to_video():
    """Generates 3D turntable spin preview animation."""
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        gif_bytes = canva_pro_tools.generate_spin_preview_gif(raw_bytes)
        out_b64 = "data:image/gif;base64," + base64.b64encode(gif_bytes).decode("ascii")
        return jsonify({"video_url": out_b64, "success": True})
    except Exception as e:
        app.logger.error("Canva Image to Video error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/google-flow-generate", methods=["POST"])
def canva_google_flow_generate():
    """
    Generates images using Google Flow API (Nano Banana 2 Lite / 2.1 / Pro via useapi.net).
    Can be used for text-to-image or image-to-image styling directly onto Canva canvas.
    """
    try:
        import google_flow_api
        data = request.get_json(force=True)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "Prompt description is required."}), 400

        model = data.get("model", "nano-banana-2-lite")
        aspect_ratio = data.get("aspect_ratio", "1:1")
        count = int(data.get("count", 1))
        seed = data.get("seed")

        ref_image = data.get("reference_image")
        refs = [ref_image] if ref_image else None

        res = google_flow_api.generate_google_flow_image(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            count=count,
            seed=seed,
            reference_images=refs
        )

        return jsonify({
            "image_url": res["primary_data_uri"],
            "images": [img["data_uri"] for img in res["images"]],
            "model": res["model"],
            "success": True
        })
    except Exception as e:
        app.logger.error("Canva Google Flow Generate error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/canva/export-master", methods=["POST"])
def canva_export_master():
    """
    Renders and downloads full Ultra-HD 300 DPI Master file (PNG / JPG / PDF)
    at 15-18 MB directly from the user's active Canva editor design.
    """
    try:
        import canva_pro_tools
        data = request.get_json(force=True)
        img_b64 = data.get("image_data", "")
        fmt = data.get("format", "png").lower()
        stem = data.get("filename", "edited_label").rsplit(".", 1)[0]

        if not img_b64:
            return jsonify({"error": "No image data provided"}), 400
        if "," in img_b64:
            img_b64 = img_b64.split(",", 1)[1]
        raw_bytes = base64.b64decode(img_b64)

        result_bytes, mimetype, out_filename = canva_pro_tools.render_master_export(
            raw_bytes, fmt=fmt, target_max_dim=7600, stem=stem
        )

        out_io = io.BytesIO(result_bytes)
        return send_file(
            out_io,
            mimetype=mimetype,
            as_attachment=True,
            download_name=out_filename
        )
    except Exception as e:
        app.logger.error("Canva Export Master error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/download/<filename>/<fmt>")
def download_image(filename, fmt):
    # Ensure secure filename to prevent path traversal
    filename = secure_filename(filename)
    filepath = os.path.join(app.config["RESULTS_FOLDER"], filename)
    if not os.path.exists(filepath):
        return "File not found", 404

    stem = filename.rsplit(".", 1)[0]
    
    # We do NOT upscale the image here using basic filters (like Lanczos), 
    # because that causes blurriness which ruins the SVG vector tracing.
    # The native crisp image is passed to the SVG/CDR vectorizer, which creates
    # infinitely scalable, high-quality vector paths.
    active_filepath = filepath
    temp_filepath = None

    try:
        # ── PNG ──────────────────────────────────────────────────────────────────
        if fmt == "png":
            cache_path = _get_ultra_hd_cache_path(active_filepath, target_max_dim=8000)
            return send_file(
                cache_path,
                mimetype="image/png",
                as_attachment=True,
                download_name=stem + ".png",
            )
    
        # ── JPEG ─────────────────────────────────────────────────────────────────
        elif fmt in ("jpg", "jpeg"):
            with _get_ultra_hd_image(active_filepath, target_max_dim=8000) as hd_img:
                out_io = io.BytesIO()
                hd_img.convert("RGB").save(out_io, "JPEG", quality=100, subsampling=0, dpi=(300, 300))
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
                    mimetype="image/svg+xml",
                    as_attachment=True,
                    download_name=stem + "_coreldraw.svg",
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
                    mimetype="application/x-coreldraw",
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


@app.route("/api/digitize-reve", methods=["POST"])
def digitize_label_reve():
    """Route for sending the label to the official Reve API."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
        
    try:
        import uuid
        import reve_api
        
        # Save uploaded file
        ext = os.path.splitext(file.filename)[1]
        if not ext:
            ext = ".png"
            
        unique_id = uuid.uuid4().hex[:8]
        filename = f"reve_upload_{unique_id}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Call Official API
        fabric_json = reve_api.digitize_image_via_reve(filepath)
        
        return jsonify({
            "status": "success",
            "fabric_json": fabric_json
        })
    except Exception as e:
        app.logger.error("Reve API Digitizer failed: %s", e)
        return jsonify({"error": str(e)}), 500
