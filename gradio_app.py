"""
Label Editor AI — Gradio Interface for Hugging Face Spaces
==========================================================
Wraps the core processing logic from app.py into a clean Gradio UI.
Set RECRAFT_API_KEY and/or NANOBANANA_API_KEY in the HF Space Secrets.
"""

import os
import base64
import time
import uuid
import zipfile
import tempfile
import requests
import urllib.parse
import re
import io

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from dotenv import load_dotenv

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
RESULTS_DIR = "gradio_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
RECRAFT_API_KEY = os.getenv("RECRAFT_API_KEY", "").strip("'\"")
NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY", "").strip("'\"")
NANOBANANA_BASE_URL = os.getenv("NANOBANANA_BASE_URL", "https://api.nanobananaapi.dev").rstrip("/")

# ---------------------------------------------------------------------------
# Font helpers (same as app.py)
# ---------------------------------------------------------------------------
_FONT_PATHS = [
    "C:/Windows/Fonts/bahnschrift.ttf",
    "C:/Windows/Fonts/seguibl.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

def _get_font(size: int):
    for fp in _FONT_PATHS:
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def image_to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def pil_from_data_uri(data_uri: str) -> Image.Image:
    _, b64 = data_uri.split(",", 1)
    return Image.open(io.BytesIO(base64.b64decode(b64)))

# ---------------------------------------------------------------------------
# Auto-translation (Google Translate free endpoint)
# ---------------------------------------------------------------------------
def translate_prompt(text: str) -> str:
    if not text:
        return ""
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl=en&dt=t&q={urllib.parse.quote(text)}"
        )
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            return "".join(s[0] for s in result[0] if s[0]).strip()
    except Exception:
        pass
    return text

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

try:
    # pyrefly: ignore [missing-import]
    import spaces
except ImportError:
    class spaces:
        @staticmethod
        def GPU(func):
            return func

# ---------------------------------------------------------------------------
# CLIPSeg mask generation
# ---------------------------------------------------------------------------
_clipseg_processor = None
_clipseg_model = None

@spaces.GPU
def generate_mask_with_clipseg(pil_img: Image.Image, prompt: str) -> Image.Image:
    global _clipseg_processor, _clipseg_model
    try:
        import torch
        # pyrefly: ignore [missing-import]
        from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation
        img = pil_img.convert("RGB")
        w, h = img.size
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if _clipseg_model is None:
            _clipseg_processor = CLIPSegProcessor.from_pretrained("CIDAS/clipseg-rd64-refined")
            _clipseg_model = CLIPSegForImageSegmentation.from_pretrained("CIDAS/clipseg-rd64-refined").to(device)
        else:
            _clipseg_model = _clipseg_model.to(device)
        inputs = _clipseg_processor(text=[prompt], images=[img], padding="max_length", return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = _clipseg_model(**inputs)
        import numpy as np
        preds = torch.sigmoid(outputs.logits)
        mask_array = (preds[0].cpu().numpy() * 255).astype("uint8")
        mask_img = Image.fromarray(mask_array).resize((w, h), Image.Resampling.LANCZOS)
        return mask_img.point(lambda p: 255 if p > 100 else 0)
    except Exception:
        pass
    # Fallback: centre region mask
    w, h = pil_img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([int(w*0.3), int(h*0.3), int(w*0.7), int(h*0.7)], fill=255)
    return mask

# ---------------------------------------------------------------------------
# Background colour sampling
# ---------------------------------------------------------------------------
def _sample_bg_color(img_rgb: Image.Image, mask_l: Image.Image) -> tuple:
    import numpy as np
    bbox = mask_l.getbbox()
    if not bbox:
        return (240, 240, 240)
    left, top, right, bottom = bbox
    w_img, h_img = img_rgb.size
    pad_x = max(10, int((right - left) * 0.15))
    pad_y = max(10, int((bottom - top) * 0.15))
    x0, y0 = max(0, left-pad_x), max(0, top-pad_y)
    x1, y1 = min(w_img, right+pad_x), min(h_img, bottom+pad_y)
    region_img  = np.array(img_rgb.crop((x0, y0, x1, y1)))
    region_mask = np.array(mask_l.crop((x0, y0, x1, y1)))
    outside = region_img[region_mask < 128]
    if len(outside) > 10:
        return tuple(int(v) for v in np.median(outside, axis=0))
    inside = region_img[region_mask >= 128]
    if len(inside) > 0:
        return tuple(int(v) for v in np.median(inside, axis=0))
    return (240, 240, 240)

def _pick_text_color(bg: tuple) -> tuple:
    r, g, b = bg
    return (10,10,10) if (0.299*r + 0.587*g + 0.114*b)/255 > 0.55 else (245,245,245)

# ---------------------------------------------------------------------------
# PIL text replacement
# ---------------------------------------------------------------------------
def professional_text_replace(base_img: Image.Image, mask_l: Image.Image,
                               new_text: str) -> Image.Image:
    base = base_img.convert("RGB")
    w_img, h_img = base.size
    mask_l = mask_l.resize((w_img, h_img), Image.Resampling.LANCZOS)
    bbox = mask_l.getbbox()
    if not bbox:
        return base
    left, top, right, bottom = bbox
    box_w, box_h = right-left, bottom-top
    bg_color = _sample_bg_color(base, mask_l)
    result = base.copy()
    draw_fill = ImageDraw.Draw(result)
    pad = max(2, int(min(box_w, box_h) * 0.03))
    draw_fill.rectangle((max(0,left-pad), max(0,top-pad),
                          min(w_img,right+pad), min(h_img,bottom+pad)), fill=bg_color)
    mask_blur = mask_l.filter(ImageFilter.GaussianBlur(radius=max(2, pad)))
    result = Image.composite(result, base, mask_blur)

    # Clean instruction words from text
    display_text = new_text.upper().strip()
    instruction_words = {"remove","delete","erase","replace","add","put","insert","change","with"}
    if any(w in display_text.lower().split() for w in instruction_words):
        for trigger in ["add","with","insert","replace","put"]:
            idx = display_text.lower().rfind(trigger)
            if idx >= 0:
                remainder = display_text[idx+len(trigger):].strip()
                if remainder:
                    display_text = remainder
                    break

    target_h = int(box_h * 0.70)
    font_size = max(12, target_h)
    font = _get_font(font_size)
    draw_tmp = ImageDraw.Draw(Image.new("RGB",(1,1)))
    tb = draw_tmp.textbbox((0,0), display_text, font=font)
    text_w, text_h = tb[2]-tb[0], tb[3]-tb[1]
    max_text_w = int(box_w * 0.76)
    if text_w > max_text_w and text_w > 0:
        font_size = max(8, int(font_size * max_text_w / text_w))
        font = _get_font(font_size)
        tb = draw_tmp.textbbox((0,0), display_text, font=font)
        text_w, text_h = tb[2]-tb[0], tb[3]-tb[1]

    text_x = left + (box_w - text_w)//2 - tb[0]
    text_y = top  + (box_h - text_h)//2 - tb[1]
    text_color = _pick_text_color(bg_color)
    draw = ImageDraw.Draw(result)
    shadow_offset = max(1, font_size//30)
    shadow_color = (0,0,0) if text_color != (10,10,10) else (200,200,200)
    draw.text((text_x+shadow_offset, text_y+shadow_offset), display_text,
              font=font, fill=(*shadow_color, 120))
    draw.text((text_x, text_y), display_text, font=font, fill=text_color)
    return result

# ---------------------------------------------------------------------------
# Recraft API calls
# ---------------------------------------------------------------------------
def run_recraft_inpainting(image_path, mask_path, prompt, negative_prompt=None):
    if not RECRAFT_API_KEY:
        raise RuntimeError("RECRAFT_API_KEY is not set in Secrets.")
    url = "https://external.api.recraft.ai/v1/images/inpaint"
    headers = {"Authorization": f"Bearer {RECRAFT_API_KEY}"}
    with open(image_path,"rb") as img_f, open(mask_path,"rb") as mask_f:
        files = {
            "image": (os.path.basename(image_path), img_f, "image/png"),
            "mask":  (os.path.basename(mask_path),  mask_f, "image/png"),
        }
        data = {"prompt": prompt, "response_format": "url"}
        if negative_prompt:
            data["negative_prompt"] = negative_prompt
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Recraft API error {resp.status_code}: {resp.text}")
    return resp.json()["data"][0]["url"]

def crop_to_aspect_ratio(img: Image.Image, target_ratio: float) -> Image.Image:
    w, h = img.size
    current_ratio = w / h
    if abs(current_ratio - target_ratio) < 1e-4:
        return img
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))

def run_recraft_generations(prompt, image_size="1:1"):
    if not RECRAFT_API_KEY:
        raise RuntimeError("RECRAFT_API_KEY is not set in Secrets.")
    size_map = {"1:1":"1024x1024","16:9":"1280x720","9:16":"720x1280",
                "4:3":"1024x768","3:4":"768x1024","2:1":"1024x512"}
    resolution = size_map.get(image_size, "1024x1024")
    url = "https://external.api.recraft.ai/v1/images/generations"
    headers = {"Authorization": f"Bearer {RECRAFT_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers,
                         json={"prompt": prompt, "n": 1, "size": resolution}, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Recraft API error {resp.status_code}: {resp.text}")
    return resp.json()["data"][0]["url"]

# ---------------------------------------------------------------------------
# Nano Banana API calls
# ---------------------------------------------------------------------------
def run_nanobanana_inpainting(image_data_uri, prompt, image_size="1:1"):
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY is not set in Secrets.")
    url = f"{NANOBANANA_BASE_URL}/v1/images/edits"
    headers = {"Authorization": f"Bearer {NANOBANANA_API_KEY}", "Content-Type": "application/json"}
    payload = {"image": image_data_uri, "prompt": prompt,
               "model": "gemini-3.1-flash-lite-image", "n": 1, "size": image_size}
    for attempt in range(3):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code in (500,502,503,504):
            time.sleep(2); continue
        if resp.status_code != 200:
            raise RuntimeError(f"Nano Banana error {resp.status_code}: {resp.text}")
        data = resp.json().get("data", {})
        url_val = data[0].get("url") if isinstance(data, list) else data.get("url")
        if not url_val:
            raise RuntimeError("Unexpected response from Nano Banana")
        return url_val
    raise RuntimeError("Nano Banana API failed after 3 attempts")

def run_nanobanana_generations(prompt, image_size="1:1"):
    if not NANOBANANA_API_KEY:
        raise RuntimeError("NANOBANANA_API_KEY is not set in Secrets.")
    url = f"{NANOBANANA_BASE_URL}/v1/images/generations"
    headers = {"Authorization": f"Bearer {NANOBANANA_API_KEY}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "model": "gemini-3.1-flash-lite-image", "n": 1, "size": image_size}
    for attempt in range(3):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code in (500,502,503,504):
            time.sleep(2); continue
        if resp.status_code != 200:
            raise RuntimeError(f"Nano Banana error {resp.status_code}: {resp.text}")
        data = resp.json().get("data", {})
        url_val = data[0].get("url") if isinstance(data, list) else data.get("url")
        if not url_val:
            raise RuntimeError("Unexpected response from Nano Banana")
        return url_val
    raise RuntimeError("Nano Banana API failed after 3 attempts")

# ---------------------------------------------------------------------------
# Download format builders
# ---------------------------------------------------------------------------
def build_pdf(img: Image.Image) -> bytes:
    px_w, px_h = img.size
    dpi_x = float(img.info.get("dpi", (300,300))[0]) or 300.0
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas as rl_canvas
        pt_w, pt_h = px_w*72/dpi_x, px_h*72/dpi_x
        out = io.BytesIO()
        c = rl_canvas.Canvas(out, pagesize=(pt_w, pt_h))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG"); buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=pt_w, height=pt_h)
        c.showPage(); c.save()
        return out.getvalue()
    except ImportError:
        pass
    out = io.BytesIO()
    img.convert("RGB").save(out, "PDF", resolution=dpi_x)
    return out.getvalue()

def build_svg(img: Image.Image) -> bytes:
    w, h = img.size
    
    # --- Attempt true vector tracing via vtracer ---
    try:
        import vtracer
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            tmp_in_path = tmp_in.name
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_out:
            tmp_out_path = tmp_out.name

        try:
            img.convert("RGB").save(tmp_in_path, "PNG")
            vtracer.convert_image_to_svg_py(
                tmp_in_path,
                tmp_out_path,
                colormode="color",
                hierarchical="stacked",
                mode="spline",
                filter_speckle=4,
                color_precision=8,
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
                try: os.remove(p)
                except OSError: pass
    except Exception:
        pass  # Fall through to embedded-image SVG

    # --- Fallback: embed the raster image as base64 in an SVG wrapper ---
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>'
           f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<image x="0" y="0" width="{w}" height="{h}" '
           f'xlink:href="data:image/png;base64,{b64}"/>'
           f'</svg>')
    return svg.encode("utf-8")

def build_cdrx(img: Image.Image, stem: str) -> bytes:
    svg_bytes = build_svg(img)
    png_buf = io.BytesIO(); img.convert("RGB").save(png_buf, "PNG")
    meta = (f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<cdrx-metadata xmlns="http://www.corel.com/coreldraw/2019/cdrx">'
            f'<title>{stem}</title><application>CorelDRAW</application>'
            f'<version>24.0</version><document>document.svg</document>'
            f'<preview>preview.png</preview></cdrx-metadata>').encode("utf-8")
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("document.svg", svg_bytes)
        zf.writestr("preview.png", png_buf.getvalue())
        zf.writestr("metadata.xml", meta)
    return zb.getvalue()

def build_gms(img: Image.Image, stem: str) -> bytes:
    buf = io.BytesIO(); img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    chunks = [b64[i:i+72] for i in range(0, len(b64), 72)]
    b64_lines = '\n        & '.join(f'"{c}"' for c in chunks)
    script = f"""' CorelDRAW Macro (.gms) — Label Editor AI
Attribute VB_Name = "LabelEditorImport"
Sub ImportEditedLabel()
    Dim sBase64 As String
    sBase64 = {b64_lines}
    Dim sTempPath As String
    sTempPath = Environ("TEMP") & "\\{stem}_label.png"
    Dim iFile As Integer: iFile = FreeFile()
    Open sTempPath For Binary As #iFile
        Dim decoded() As Byte: decoded = DecodeBase64(sBase64)
        Put #iFile, , decoded
    Close #iFile
    Dim importedObj As Shape
    Set importedObj = ActiveLayer.Import(sTempPath)
    If Not importedObj Is Nothing Then
        importedObj.SetPositionEx cdrCenter, cdrCenter, ActivePage.SizeWidth/2, ActivePage.SizeHeight/2
        MsgBox "Label imported!", vbInformation, "Label Editor AI"
    End If
End Sub
Private Function DecodeBase64(s As String) As Byte()
    Dim o As Object: Set o = CreateObject("MSXML2.DOMDocument")
    Dim n As Object: Set n = o.createElement("b64")
    n.DataType = "bin.base64": n.Text = s: DecodeBase64 = n.nodeTypedValue
End Function"""
    return script.encode("utf-8")

def build_cgs(img: Image.Image, stem: str) -> bytes:
    w, h = img.size
    buf = io.BytesIO(); img.convert("RGB").save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    cgs = (f'<?xml version="1.0" encoding="UTF-8"?>'
           f'<cgs-styles xmlns="http://www.corel.com/coreldraw/styles/2015">'
           f'<style name="{stem}" id="label-editor-ai">'
           f'<fill type="bitmap" tiling="none">'
           f'<bitmap width="{w}" height="{h}" format="png">'
           f'<data encoding="base64">{b64}</data>'
           f'</bitmap></fill><outline none="true"/></style></cgs-styles>')
    return cgs.encode("utf-8")

# ---------------------------------------------------------------------------
# Save result PIL image to a temp file and return the path for Gradio File
# ---------------------------------------------------------------------------
def _save_temp(data: bytes, ext: str, stem: str) -> str:
    path = os.path.join(RESULTS_DIR, f"{stem}.{ext}")
    with open(path, "wb") as f:
        f.write(data)
    return path

# ---------------------------------------------------------------------------
# Core processing function (called by Gradio)
# ---------------------------------------------------------------------------
def process(
    image,          # PIL Image or None
    prompt,
    mode,           # "Remove", "Add/Replace", "Text Replace", "Generate (no image)"
    api_provider,   # "Recraft.ai", "Nano Banana"
    negative_prompt,
    overlay_image,  # PIL Image or None
    aspect_ratio="4:1",
):
    if not prompt or not prompt.strip():
        return None, "❌ Please enter a prompt."

    prompt = translate_prompt(prompt.strip())
    provider = "recraft" if "Recraft" in api_provider else "nanobanana"
    stem = str(uuid.uuid4())[:8]

    # Validate keys
    if provider == "recraft" and not RECRAFT_API_KEY:
        return None, "❌ RECRAFT_API_KEY not set. Add it in Space Secrets."
    if provider == "nanobanana" and not NANOBANANA_API_KEY:
        return None, "❌ NANOBANANA_API_KEY not set. Add it in Space Secrets."

    try:
        # ── Text-to-Image (Generate) ─────────────────────────────────────────
        if mode == "Generate (no image)" or image is None:
            status = "⏳ Generating image…"
            enhanced = enhance_prompt_layout(prompt)
            # Map aspect ratio for the API
            api_aspect = aspect_ratio
            if aspect_ratio == "4:1":
                api_aspect = "2:1"
            
            if provider == "recraft":
                url = run_recraft_generations(enhanced, api_aspect)
            else:
                nanobanana_aspect = "16:9" if api_aspect in ("2:1", "16:9") else api_aspect
                url = run_nanobanana_generations(enhanced, nanobanana_aspect)
            img_bytes = requests.get(url, timeout=30).content
            result_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            
            # Crop to target aspect ratio
            ratio_map = {"1:1": 1.0, "16:9": 16/9, "2:1": 2.0, "4:1": 4.0}
            target_val = ratio_map.get(aspect_ratio, 1.0)
            result_img = crop_to_aspect_ratio(result_img, target_val)
            
            return result_img, "✅ Image generated!"

        # ── Inpainting modes ─────────────────────────────────────────────────
        pil_img = image.convert("RGB")
        original_w, original_h = pil_img.size

        # Derive mask prompt
        if mode == "Text Replace":
            p_lower = prompt.lower()
            for pat in [r'remove\s+(.*?)\s+(and|to|with|add)',
                        r'replace\s+(.*?)\s+(with|by|to)',
                        r'change\s+(.*?)\s+(to|with)']:
                m = re.search(pat, p_lower)
                if m:
                    mask_prompt = m.group(1).strip(); break
            else:
                mask_prompt = prompt
        else:
            mask_prompt = prompt

        # ── Text Replace: PIL-based ──────────────────────────────────────────
        if mode == "Text Replace":
            mask_l = generate_mask_with_clipseg(pil_img, mask_prompt)
            result_img = professional_text_replace(pil_img, mask_l, prompt)
            return result_img, "✅ Text replaced!"

        # ── Overlay / Add with uploaded image ───────────────────────────────
        if overlay_image is not None:
            mask_l = generate_mask_with_clipseg(pil_img, mask_prompt)
            overlay = overlay_image.convert("RGBA")
            base_rgba = pil_img.convert("RGBA")
            bbox = mask_l.getbbox() or (int(original_w*0.3), int(original_h*0.3),
                                         int(original_w*0.7), int(original_h*0.7))
            left, upper, right, lower = bbox
            bw, bh = right-left, lower-upper
            ow, oh = overlay.size
            aspect = ow/oh
            if bw/aspect <= bh:
                nw, nh = bw, int(bw/aspect)
            else:
                nh, nw = bh, int(bh*aspect)
            nw, nh = max(1,nw), max(1,nh)
            overlay_resized = overlay.resize((nw, nh), Image.Resampling.LANCZOS)
            ox, oy = left+(bw-nw)//2, upper+(bh-nh)//2
            layer = Image.new("RGBA", base_rgba.size, (0,0,0,0))
            layer.paste(overlay_resized, (ox, oy))
            final_overlay = Image.composite(layer, Image.new("RGBA", base_rgba.size, (0,0,0,0)), mask_l)
            result_img = Image.alpha_composite(base_rgba, final_overlay).convert("RGB")
            return result_img, "✅ Overlay applied!"

        # ── API inpainting (Remove / Add-Replace) ───────────────────────────
        if provider == "recraft":
            mask_l = generate_mask_with_clipseg(pil_img, mask_prompt)
            # Save tmp files for Recraft multipart upload
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                img_tmp = tf.name
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                mask_tmp = tf.name
            try:
                pil_img.save(img_tmp, "PNG")
                mask_l.save(mask_tmp, "PNG")
                if mode == "Remove":
                    inpaint_prompt = ("seamless product label background, clean surface, "
                                      "high resolution, no logo, no text, smooth texture")
                else:
                    inpaint_prompt = (f"{prompt}, product label style, high resolution, "
                                      "professional graphic design, seamlessly integrated")
                url = run_recraft_inpainting(img_tmp, mask_tmp, inpaint_prompt, negative_prompt)
            finally:
                for p in (img_tmp, mask_tmp):
                    try: os.remove(p)
                    except OSError: pass
        else:
            data_uri = image_to_data_uri(pil_img)
            inpaint_prompt = (f"Edit this product label image: {prompt}. "
                              "Keep all other elements exactly the same. "
                              "Only change what was requested.")
            url = run_nanobanana_inpainting(data_uri, inpaint_prompt, "1:1")

        img_bytes = requests.get(url, timeout=30).content
        result = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        rw, rh = result.size
        if rh >= original_h * 1.7:
            result = result.crop((0, 0, rw, original_h))
        if result.size != (original_w, original_h):
            result = result.resize((original_w, original_h), Image.Resampling.LANCZOS)
        return result, "✅ Done!"

    except Exception as exc:
        return None, f"❌ Error: {exc}"

# ---------------------------------------------------------------------------
# Download handler — returns a file path for Gradio gr.File output
# ---------------------------------------------------------------------------
def download_result(result_img, fmt):
    if result_img is None:
        return None
    if not isinstance(result_img, Image.Image):
        result_img = Image.fromarray(result_img)
    stem = str(uuid.uuid4())[:8]

    if fmt == "PNG":
        buf = io.BytesIO(); result_img.save(buf, "PNG")
        return _save_temp(buf.getvalue(), "png", stem)
    elif fmt == "JPG":
        buf = io.BytesIO(); result_img.convert("RGB").save(buf, "JPEG", quality=100, subsampling=0)
        return _save_temp(buf.getvalue(), "jpg", stem)
    elif fmt == "PDF":
        return _save_temp(build_pdf(result_img), "pdf", stem)
    elif fmt == "SVG":
        return _save_temp(build_svg(result_img), "svg", stem)
    elif fmt == "CDR":
        return _save_temp(build_svg(result_img), "cdr", stem)
    elif fmt == "CDRx":
        return _save_temp(build_cdrx(result_img, stem), "cdrx", stem)
    elif fmt == "GMS":
        return _save_temp(build_gms(result_img, stem), "gms", stem)
    elif fmt == "CGS":
        return _save_temp(build_cgs(result_img, stem), "cgs", stem)
    return None

# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
# pyrefly: ignore [missing-import]
import gradio as gr

CSS = """
#title { text-align: center; }
#title h1 { background: linear-gradient(135deg,#7c3aed,#0891b2);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.download-row { display: flex; flex-wrap: wrap; gap: 8px; }
footer { display: none !important; }
"""

MODES = ["Remove", "Add/Replace", "Text Replace", "Generate (no image)"]
PROVIDERS = ["Recraft.ai", "Nano Banana"]
FORMATS = ["PNG", "JPG", "PDF", "SVG", "CDR", "CDRx", "GMS", "CGS"]

with gr.Blocks(css=CSS, title="Label Editor AI") as demo:

    # ── Header ────────────────────────────────────────────────────────────
    with gr.Column(elem_id="title"):
        gr.Markdown("# 🎨 Label Editor AI\n"
                    "### Remove · Add · Replace · Generate — powered by Recraft.ai & Nano Banana")

    with gr.Row():
        # ── Left column: inputs ──────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### 📥 Input")

            input_image = gr.Image(
                label="Upload product label image (leave empty for Generate mode)",
                type="pil", sources=["upload","clipboard"], height=280
            )
            overlay_image = gr.Image(
                label="Overlay image (optional — for Add mode with a custom graphic)",
                type="pil", sources=["upload","clipboard"], height=160
            )
            prompt_box = gr.Textbox(
                label="Prompt / Instruction",
                placeholder='e.g. "Remove Gomzi Nutrition and add Maxlife" or '
                            '"Replace brand name with NutriFit"',
                lines=3,
            )
            with gr.Row():
                mode_dd = gr.Dropdown(MODES, value="Remove", label="Mode")
                provider_dd = gr.Dropdown(PROVIDERS, value="Recraft.ai", label="API Provider")
                aspect_dd = gr.Dropdown(["1:1", "16:9", "2:1", "4:1"], value="4:1", label="Aspect Ratio (Generate)")

            with gr.Accordion("⚙️ Advanced Options", open=False):
                neg_prompt = gr.Textbox(
                    label="Negative Prompt",
                    value="blurry, low quality, distorted text, watermark, artifacts",
                    lines=2,
                )

            run_btn = gr.Button("🚀 Run", variant="primary", size="lg")
            status_box = gr.Textbox(label="Status", interactive=False, lines=1)

        # ── Right column: result + download ──────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Result")

            result_image = gr.Image(
                label="Edited / Generated Image",
                type="pil", interactive=False, height=360
            )

            gr.Markdown("#### ⬇️ Download As")
            with gr.Row(elem_classes="download-row"):
                fmt_dd = gr.Dropdown(
                    FORMATS, value="PNG", label="Format",
                    info="CDR/CDRx/GMS/CGS are CorelDRAW-compatible formats"
                )
                dl_btn = gr.Button("⬇️ Download", variant="secondary")

            dl_file = gr.File(label="Your file is ready", visible=False)

    # ── Examples ─────────────────────────────────────────────────────────
    gr.Markdown("---\n### 💡 Example Prompts")
    gr.Examples(
        examples=[
            [None, "A bright orange energy drink product label with bold typography", "Generate (no image)", "Recraft.ai", "4:1"],
            [None, "Professional whey protein supplement label, chocolate flavour", "Generate (no image)", "Recraft.ai", "4:1"],
        ],
        inputs=[input_image, prompt_box, mode_dd, provider_dd, aspect_dd],
        label="Text-to-Image examples (no upload needed)",
    )

    # ── How to use CorelDRAW formats ─────────────────────────────────────
    with gr.Accordion("ℹ️ How to use CorelDRAW formats", open=False):
        gr.Markdown("""
| Format | How to use |
|--------|-----------|
| **CDR** | Open directly in CorelDRAW 2019+ via File → Import |
| **CDRx** | ZIP package — extract and open `document.svg` in CorelDRAW |
| **GMS** | Tools → Macros → Run Macro inside CorelDRAW (embeds image) |
| **CGS** | Object Styles panel → Import Styles in CorelDRAW |
| **SVG** | Universal vector — works in CorelDRAW, Illustrator, Inkscape |
| **PDF** | Print-ready, 300 DPI page — open in any CorelDRAW version |
        """)

    # ── Event wiring ─────────────────────────────────────────────────────
    _result_state = gr.State(None)

    def run_and_store(img, prompt, mode, provider, neg, overlay, aspect):
        result, status = process(img, prompt, mode, provider, neg, overlay, aspect)
        return result, result, status

    run_btn.click(
        fn=run_and_store,
        inputs=[input_image, prompt_box, mode_dd, provider_dd, neg_prompt, overlay_image, aspect_dd],
        outputs=[result_image, _result_state, status_box],
    )

    def do_download(result, fmt):
        path = download_result(result, fmt)
        if path:
            return gr.update(value=path, visible=True)
        return gr.update(visible=False)

    dl_btn.click(
        fn=do_download,
        inputs=[_result_state, fmt_dd],
        outputs=[dl_file],
    )

if __name__ == "__main__":
    demo.launch()
