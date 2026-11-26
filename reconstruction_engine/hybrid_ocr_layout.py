"""
Hybrid Multi-Scale Tiled OCR + AI Vision Document Understanding Engine.

Combines:
1. High-resolution upscaled overlapping tiled EasyOCR + inverted pill pass (works offline).
2. Optional configured Multimodal Vision JSON readout (Gemini 2.5 Flash / GPT-4o-mini)
   strictly grounded against OpenCV ink/edge bounding boxes (zero hallucinated elements).
3. Exact foreground text color sampling, line/column merging, multi-line paragraph preservation,
   font matching, and explicit low-confidence flagging.
"""

import os
import json
import re
import math
import time
import hashlib
import base64
from functools import lru_cache
from dotenv import load_dotenv

import cv2
import numpy as np

load_dotenv(override=False)

from canva_pro_tools import get_easyocr_reader, extract_robust_text_color
from .font_matcher import match_font_for_region

_OCR_CACHE: dict[str, dict] = {}
_GEMINI_EXHAUSTED_UNTIL: dict[str, float] = {}
_OPENAI_DISABLED: bool = False
_VISION_DISK_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "reconstruction_cache", "vision_cache",
)


def _sample_text_ink_color(img_bgr: np.ndarray, bx: int, by: int, bw: int, bh: int) -> str:
    """Extracts true ink color by picking the Otsu cluster farthest from local border background."""
    h, w = img_bgr.shape[:2]
    x1, y1 = max(0, bx), max(0, by)
    x2, y2 = min(w, bx + max(1, bw)), min(h, by + max(1, bh))
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size < 9:
        return "#1e293b"

    # Outer 2px border estimate (or immediate margin around tight glyph bbox)
    ox1, oy1 = max(0, x1 - 4), max(0, y1 - 4)
    ox2, oy2 = min(w, x2 + 4), min(h, y2 + 4)
    outer = img_bgr[oy1:oy2, ox1:ox2]
    top_strip = outer[:2, :].reshape(-1, 3)
    bot_strip = outer[-2:, :].reshape(-1, 3)
    left_strip = outer[:, :2].reshape(-1, 3)
    right_strip = outer[:, -2:].reshape(-1, 3)
    border_px = np.concatenate([top_strip, bot_strip, left_strip, right_strip], axis=0)
    bg_col = np.median(border_px, axis=0)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    px_hi = roi[th == 255]
    px_lo = roi[th == 0]
    if len(px_hi) == 0 or len(px_lo) == 0:
        return extract_robust_text_color(img_bgr, bx, by, bw, bh)

    med_hi = np.median(px_hi, axis=0)
    med_lo = np.median(px_lo, axis=0)
    d_hi = float(np.linalg.norm(med_hi - bg_col))
    d_lo = float(np.linalg.norm(med_lo - bg_col))
    fg_med = med_hi if d_hi >= d_lo else med_lo

    # If the outer box itself sits inside a colored pill/header bar (`bg_col` dark/saturated),
    # prefer the high-contrast lighter glyph pixels if d_hi and d_lo are close.
    bg_luma = float(0.114 * bg_col[0] + 0.587 * bg_col[1] + 0.299 * bg_col[2])
    if bg_luma < 140 and float(np.linalg.norm(med_hi - bg_col)) > 45:
        fg_med = med_hi
    elif bg_luma >= 180 and min(d_hi, d_lo) < 25 and max(d_hi, d_lo) >= 35:
        fg_med = med_hi if d_hi >= d_lo else med_lo

    b, g, r = [int(max(0, min(255, round(c)))) for c in fg_med]
    return f"#{r:02x}{g:02x}{b:02x}"


def _estimate_visual_line_count(img_bgr: np.ndarray, bx: int, by: int, bw: int, bh: int, explicit_lines: int, txt: str = "") -> int:
    """Counts visual horizontal text rows in crop via ink projection + geometric fallback for tight paragraphs."""
    if explicit_lines > 1:
        return explicit_lines
    h, w = img_bgr.shape[:2]
    x1, y1 = max(0, bx), max(0, by)
    x2, y2 = min(w, bx + max(1, bw)), min(h, by + max(1, bh))
    roi = img_bgr[y1:y2, x1:x2]
    if roi.shape[0] < 10:
        return 1
    up_h = max(roi.shape[0], roi.shape[0] * 4)
    up = cv2.resize(roi, (max(16, roi.shape[1] * 2), up_h), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    row_density = np.mean(th == 0, axis=1)
    if np.mean(th == 255) < np.mean(th == 0):
        row_density = np.mean(th == 255, axis=1)
    active = row_density > max(0.06, float(np.max(row_density)) * 0.28)
    transitions = int(np.sum((active[1:] & (~active[:-1])).astype(np.int32)))
    if active[0]:
        transitions += 1
    clean_len = len((txt or "").strip())
    if clean_len > 36 and bw > 0 and bh > 0:
        # Geometric wrap estimate prevents tiny-leading low-res paragraphs from merging into 1-2 tall lines
        geo_lines = int(round(math.sqrt(clean_len * 0.50 * 1.12 * (float(bh) / float(max(1, bw))))))
        transitions = max(transitions, min(10, max(2, geo_lines)))
    return max(1, min(12, transitions))
def _verify_ink_presence(img_bgr: np.ndarray, bx: int, by: int, bw: int, bh: int) -> tuple[bool, float]:
    h, w = img_bgr.shape[:2]
    x1, y1 = max(0, bx), max(0, by)
    x2, y2 = min(w, bx + max(1, bw)), min(h, by + max(1, bh))
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size < 9:
        return False, 0.0
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    std_val = float(np.std(gray))
    rng_val = float(np.max(gray) - np.min(gray))
    return (std_val >= 8.5 and rng_val >= 28.0), round(std_val, 2)


def _snap_box_to_ink(img_bgr: np.ndarray, bx: int, by: int, bw: int, bh: int, pad: int = 3) -> tuple[int, int, int, int]:
    """Tightens a coarse box cleanly onto local Otsu foreground pixels."""
    h, w = img_bgr.shape[:2]
    x1 = max(0, bx - pad)
    y1 = max(0, by - pad)
    x2 = min(w, bx + bw + pad)
    y2 = min(h, by + bh + pad)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.shape[0] < 4 or roi.shape[1] < 4:
        return bx, by, bw, bh

    border = np.concatenate([roi[:2, :].reshape(-1, 3), roi[-2:, :].reshape(-1, 3)], axis=0)
    bg_med = np.median(border, axis=0)
    diff = np.linalg.norm(roi.astype(np.float32) - bg_med.astype(np.float32), axis=2)
    mask = diff > max(20.0, float(np.percentile(diff, 60)) * 0.85)
    ys, xs = np.where(mask)
    if len(xs) < 6:
        return bx, by, bw, bh
    nx1 = max(0, x1 + int(xs.min()) - 1)
    ny1 = max(0, y1 + int(ys.min()) - 1)
    nx2 = min(w, x1 + int(xs.max()) + 2)
    ny2 = min(h, y1 + int(ys.max()) + 2)
    if (nx2 - nx1) >= 4 and (ny2 - ny1) >= 4:
        return nx1, ny1, nx2 - nx1, ny2 - ny1
    return bx, by, bw, bh


def _run_tiled_easyocr(img_bgr: np.ndarray, fast_mode: bool = False) -> list[dict]:
    """Runs CPU-friendly upscaled EasyOCR (single high-res pass when Vision succeeded, tiled offline)."""
    h, w = img_bgr.shape[:2]
    reader = get_easyocr_reader()

    # Keep work resolution crisp yet fast on CPU laptops (~4s fast / ~12s offline tiled)
    target_max = 920.0 if fast_mode else 980.0
    max_up = 2.6 if (not fast_mode and max(w, h) < 750) else 2.2
    up_scale = min(max_up, max(1.0, target_max / float(max(w, h))))
    work_w = int(round(w * up_scale))
    work_h = int(round(h * up_scale))
    work_img = cv2.resize(img_bgr, (work_w, work_h), interpolation=cv2.INTER_LANCZOS4) if abs(up_scale - 1.0) > 0.05 else img_bgr

    blur = cv2.GaussianBlur(work_img, (0, 0), 1.0)
    sharp_work = cv2.addWeighted(work_img, 1.30, blur, -0.30, 0)

    raw_detections = []

    def _collect(sub_img, off_x: int, off_y: int, sc: float):
        res = reader.readtext(sub_img, text_threshold=0.20, low_text=0.18, link_threshold=0.18)
        for poly, txt, conf in res:
            clean = str(txt).strip()
            if not clean or float(conf) < 0.16:
                continue
            xs = [(pt[0] + off_x) / sc for pt in poly]
            ys = [(pt[1] + off_y) / sc for pt in poly]
            bx = max(0, int(round(min(xs))))
            by = max(0, int(round(min(ys))))
            bw = max(2, min(w - bx, int(round(max(xs) - min(xs)))))
            bh = max(2, min(h - by, int(round(max(ys) - min(ys)))))
            raw_detections.append({
                "text": clean,
                "left": bx,
                "top": by,
                "width": bw,
                "height": bh,
                "conf": float(conf),
                "source": "easyocr",
            })

    # Pass 1: Upscaled Frame
    _collect(sharp_work, 0, 0, up_scale)

    if not fast_mode:
        # Pass 2: Single bounded inverted CLAHE pass for white/light text inside dark/colored pills & bands
        inv_max = 820.0
        inv_sc = min(up_scale, max(1.0, inv_max / float(max(w, h))))
        if abs(inv_sc - up_scale) < 0.05:
            inv_src = sharp_work
        else:
            inv_src = cv2.resize(img_bgr, (int(round(w * inv_sc)), int(round(h * inv_sc))), interpolation=cv2.INTER_AREA)
        inv_gray = 255 - cv2.cvtColor(inv_src, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        _collect(cv2.cvtColor(clahe.apply(inv_gray), cv2.COLOR_GRAY2BGR), 0, 0, inv_sc)

    # Deduplicate overlapping boxes: prefer full multi-char words/phrases over tiny fragments!
    raw_detections.sort(
        key=lambda d: (len(d["text"].strip()) >= 3, round(d["conf"], 2), len(d["text"].strip()), d["width"]),
        reverse=True,
    )
    kept = []
    for cand in raw_detections:
        cx1, cy1 = cand["left"], cand["top"]
        cx2, cy2 = cx1 + cand["width"], cy1 + cand["height"]
        cand_area = max(1, cand["width"] * cand["height"])
        dup = False
        for k in kept:
            kx1, ky1 = k["left"], k["top"]
            kx2, ky2 = kx1 + k["width"], ky1 + k["height"]
            ix = max(0, min(cx2, kx2) - max(cx1, kx1))
            iy = max(0, min(cy2, ky2) - max(cy1, ky1))
            inter = ix * iy
            if inter > 0:
                k_area = max(1, k["width"] * k["height"])
                if (inter / float(cand_area) > 0.45) or (inter / float(max(cand_area, k_area)) > 0.35):
                    dup = True
                    break
        if not dup:
            kept.append(cand)
    return kept


def _run_ai_vision_label_structure(image_bytes: bytes, w: int, h: int) -> dict | None:
    """
    Uses configured Gemini Flash (or OpenAI Vision) strictly for JSON layout & verbatim text audit.
    Persists validated JSON structure by SHA-256 so duplicate uploads/CDR previews don't re-burn quota.
    """
    global _GEMINI_EXHAUSTED_UNTIL, _OPENAI_DISABLED
    img_sha = hashlib.sha256(image_bytes).hexdigest()
    # Compress large PNGs into a fast ~120 KB 1280px JPEG for Vision layout JSON & cache deduplication
    vis_bytes, vis_mime = image_bytes, ("image/png" if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg")
    if max(w, h) > 1280 or len(image_bytes) > 300_000:
        try:
            arr_v = np.frombuffer(image_bytes, np.uint8)
            im_v = cv2.imdecode(arr_v, cv2.IMREAD_COLOR)
            if im_v is not None:
                v_sc = min(1.0, 1280.0 / float(max(w, h)))
                if v_sc < 0.99:
                    im_v = cv2.resize(im_v, (int(round(w * v_sc)), int(round(h * v_sc))), interpolation=cv2.INTER_AREA)
                ok_j, j_buf = cv2.imencode(".jpg", im_v, [cv2.IMWRITE_JPEG_QUALITY, 86])
                if ok_j:
                    vis_bytes = j_buf.tobytes()
                    vis_mime = "image/jpeg"
        except Exception:
            pass
    vis_sha = hashlib.sha256(vis_bytes).hexdigest()
    cache_path = os.path.join(_VISION_DISK_CACHE_DIR, f"{img_sha}.json")
    vis_cache_path = os.path.join(_VISION_DISK_CACHE_DIR, f"{vis_sha}.json")
    for cp in (cache_path, vis_cache_path):
        if os.path.isfile(cp):
            try:
                with open(cp, "r", encoding="utf-8") as cf:
                    cached = json.load(cf)
                if isinstance(cached, dict) and len(cached.get("text_blocks") or []) >= 4:
                    return cached
            except Exception:
                pass

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            from concurrent.futures import ThreadPoolExecutor as _VisPool
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=gemini_key,
                http_options=types.HttpOptions(
                    timeout=14_000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
            prompt = (
                "Analyze this flat product packaging label image and return ONLY strict JSON matching this schema:\n"
                "{\n"
                '  "label_bounds_norm": [ymin, xmin, ymax, xmax],\n'
                '  "regions": {\n'
                '    "nutrition_table": [ymin, xmin, ymax, xmax] or null,\n'
                '    "illustration": [ymin, xmin, ymax, xmax] or null,\n'
                '    "veg_symbol": [ymin, xmin, ymax, xmax] or null,\n'
                '    "benefit_icons": [[ymin, xmin, ymax, xmax], ...]\n'
                "  },\n"
                '  "text_blocks": [\n'
                "    {\n"
                '      "text": "exact verbatim text (multi-line with \\n for paragraphs/address blocks)",\n'
                '      "box_2d": [ymin, xmin, ymax, xmax],\n'
                '      "role": "product_title|product_subtitle|flavour_badge|strength_badge|quantity_badge|tagline|section_heading|nutrition_header|nutrition_cell|product_description|product_form|packaging_type|caution|key_benefit|manufacturer|marketed_by|batch_info|other",\n'
                '      "align": "left|center|right",\n'
                '      "bold": true/false\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "CRITICAL RULES:\n"
                "- Coordinates use normalized 0..1000 scale relative to the full uploaded image.\n"
                "- Transcribe ALL visible text verbatim, including small dosage, nutrition values, description, cautions, benefits, manufacturer, marketed by, batch/mfg/exp/MRP.\n"
                "- Keep separate table cells as separate items (e.g. 'Biotin' separate from '15 mg' inside nutrition table; '15 mg' and '60 CAPSULES' bottom pill separate).\n"
                "- Never invent text, SKU numbers, or values that are not visually printed on the label."
            )
            resp = None
            used_model = None
            now_ts = time.time()
            tried = 0
            for cand_model in ("gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-3-flash-preview", "gemini-3.5-flash"):
                if now_ts < _GEMINI_EXHAUSTED_UNTIL.get(cand_model, 0.0):
                    continue
                if tried >= 2:
                    break
                tried += 1
                try:
                    def _call_vis(m_id=cand_model):
                        return client.models.generate_content(
                            model=m_id,
                            contents=[
                                types.Part.from_bytes(data=vis_bytes, mime_type=vis_mime),
                                prompt,
                            ],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0,
                            ),
                        )
                    with _VisPool(max_workers=1) as vpool:
                        fut = vpool.submit(_call_vis)
                        resp = fut.result(timeout=15)
                    if resp and (resp.text or "").strip():
                        used_model = cand_model
                        break
                except Exception as m_exc:
                    err_s = str(m_exc)
                    print(f"[HybridOCR] Gemini model {cand_model} skipped: {err_s}")
                    if "429" in err_s or "RESOURCE_EXHAUSTED" in err_s or "404" in err_s or "NOT_FOUND" in err_s:
                        _GEMINI_EXHAUSTED_UNTIL[cand_model] = time.time() + 300.0
                    elif "503" in err_s or "UNAVAILABLE" in err_s or "504" in err_s:
                        _GEMINI_EXHAUSTED_UNTIL[cand_model] = time.time() + 90.0
                    continue
            if not resp:
                raise RuntimeError("No active Gemini flash model responded")
            raw_json = (resp.text or "").strip()
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict) and isinstance(parsed.get("text_blocks"), list):
                parsed["_provider"] = used_model or "gemini-flash"
                if len(parsed["text_blocks"]) >= 4:
                    try:
                        os.makedirs(_VISION_DISK_CACHE_DIR, exist_ok=True)
                        with open(cache_path, "w", encoding="utf-8") as cf:
                            json.dump(parsed, cf, ensure_ascii=False)
                    except Exception:
                        pass
                return parsed
        except Exception as exc:
            print(f"[HybridOCR] Gemini Vision skipped cleanly: {exc}")

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key and not _OPENAI_DISABLED:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key, timeout=15.0, max_retries=0)
            b64 = base64.b64encode(image_bytes).decode("ascii")
            mime = "image/png" if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": (
                            "Extract every visible text block & region bbox from this packaging label as strict JSON with keys: "
                            "label_bounds_norm [ymin,xmin,ymax,xmax], regions (nutrition_table, illustration, veg_symbol, benefit_icons), "
                            "and text_blocks [{text, box_2d:[ymin,xmin,ymax,xmax], role, align, bold}]. Normalize 0..1000. Transcribe verbatim."
                        )},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }],
            )
            parsed = json.loads(resp.choices[0].message.content)
            if isinstance(parsed, dict) and isinstance(parsed.get("text_blocks"), list):
                parsed["_provider"] = "gpt-4o-mini"
                return parsed
        except Exception as exc:
            err_s = str(exc)
            if "insufficient_quota" in err_s or "429" in err_s:
                _OPENAI_DISABLED = True
            print(f"[HybridOCR] OpenAI Vision skipped cleanly: {err_s}")

    return None


def _normalize_box_2d(box) -> list[float] | None:
    """Normalizes flat [ymin,xmin,ymax,xmax] or nested [[ymin,xmin,ymax,xmax], ...] into [ymin,xmin,ymax,xmax]."""
    if not isinstance(box, (list, tuple)) or not box:
        return None
    if len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
        return [float(v) for v in box]
    nested = [b for b in box if isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b)]
    if not nested:
        return None
    return [
        min(float(b[0]) for b in nested),
        min(float(b[1]) for b in nested),
        max(float(b[2]) for b in nested),
        max(float(b[3]) for b in nested),
    ]


def analyze_label_text_and_structure(image_bytes: bytes, use_vision: bool = True) -> dict:
    """
    Main hybrid OCR & document layout analyzer.
    Caches results by image SHA-256 so repeat inspections are instant.
    """
    digest = hashlib.sha256(image_bytes).hexdigest() + f"_v{int(use_vision)}"
    if digest in _OCR_CACHE:
        return _OCR_CACHE[digest]

    arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image for label OCR analysis")
    h, w = img_bgr.shape[:2]

    # Overlap lazy EasyOCR model init with remote Vision call so CPU startup doesn't double latency
    from concurrent.futures import ThreadPoolExecutor as _PrepPool
    if use_vision:
        with _PrepPool(max_workers=2) as ppool:
            f_warm = ppool.submit(get_easyocr_reader)
            f_vis = ppool.submit(_run_ai_vision_label_structure, image_bytes, w, h)
            vision_data = f_vis.result()
            try:
                f_warm.result(timeout=30)
            except Exception:
                pass
    else:
        vision_data = None
    has_rich_vision = bool(vision_data and len(vision_data.get("text_blocks") or []) >= 4)
    ocr_boxes = _run_tiled_easyocr(img_bgr, fast_mode=has_rich_vision)

    final_blocks = []
    warnings = []
    matched_ocr_indices = set()

    if vision_data:
        for vb in vision_data.get("text_blocks", []):
            txt = str(vb.get("text") or "").strip()
            box = _normalize_box_2d(vb.get("box_2d"))
            if not txt or not box:
                continue
            ymin, xmin, ymax, xmax = [float(v) for v in box]
            bx = max(0, int(round((xmin / 1000.0) * w)))
            by = max(0, int(round((ymin / 1000.0) * h)))
            bw = max(4, min(w - bx, int(round(((xmax - xmin) / 1000.0) * w))))
            bh = max(4, min(h - by, int(round(((ymax - ymin) / 1000.0) * h))))

            has_ink, std_val = _verify_ink_presence(img_bgr, bx, by, bw, bh)
            if not has_ink:
                continue

            # Snap coarse Vision box tightly to real OpenCV glyph pixels
            sbx, sby, sbw, sbh = _snap_box_to_ink(img_bgr, bx, by, bw, bh, pad=4)

            # Cross-check with overlapping EasyOCR detections
            overlapping_ocr = []
            for idx, ob in enumerate(ocr_boxes):
                ix = max(0, min(sbx + sbw, ob["left"] + ob["width"]) - max(sbx, ob["left"]))
                iy = max(0, min(sby + sbh, ob["top"] + ob["height"]) - max(sby, ob["top"]))
                inter = ix * iy
                if inter > 0:
                    area_min = min(sbw * sbh, ob["width"] * ob["height"])
                    if inter / float(max(1, area_min)) > 0.30:
                        overlapping_ocr.append((idx, ob))
                        matched_ocr_indices.add(idx)

            conf = 0.88 if overlapping_ocr else 0.78
            source_tag = "hybrid_ocr_vision" if overlapping_ocr else "vision_ink_verified"

            # Verify numeric stability when EasyOCR has high-confidence numbers
            nums_vision = re.findall(r"\d+(?:\.\d+)?", txt)
            for _, ob in overlapping_ocr:
                if ob["conf"] >= 0.85:
                    nums_ocr = re.findall(r"\d+(?:\.\d+)?", ob["text"])
                    if nums_vision and nums_ocr and set(nums_ocr) != set(nums_vision) and len(txt.splitlines()) == 1:
                        conf = min(conf, 0.62)
                        warnings.append(f"Low-confidence numeric verification between OCR ('{ob['text']}') and Vision ('{txt}'); please review.")

            lines = [ln for ln in txt.splitlines() if ln.strip()]
            num_lines = _estimate_visual_line_count(img_bgr, sbx, sby, sbw, sbh, len(lines), txt=txt)
            line_h = sbh / float(num_lines)
            role = str(vb.get("role") or "other")
            cap_fill_factor = 0.86 if role == "product_title" else (0.58 if num_lines >= 2 else 0.68)
            font_px = max(5, int(round(line_h * cap_fill_factor)))
            align = str(vb.get("align") or "left")
            color_hex = _sample_text_ink_color(img_bgr, sbx, sby, sbw, sbh)
            fmeta = match_font_for_region(img_bgr, sbx, sby, sbw, sbh, lines[0], role=role)
            if vb.get("bold") is True:
                fmeta["fontWeight"] = "800" if role == "product_title" else "700"
            elif vb.get("bold") is False or (num_lines >= 2 and role in ("product_description", "caution", "key_benefit", "manufacturer", "marketed_by")):
                fmeta["fontWeight"] = "400"

            final_blocks.append({
                "text": txt,
                "left": int(sbx),
                "top": int(sby),
                "width": int(sbw),
                "height": int(sbh),
                "fontSize": font_px,
                "color": color_hex,
                "align": align if align in ("left", "center", "right") else "left",
                "role": role,
                "conf": round(conf, 3),
                "needs_review": conf < 0.65,
                "source": source_tag,
                "lineHeight": 1.07 if num_lines > 1 else 1.05,
                **fmeta,
            })

    # Reject unmatched single/two-char noise that overlaps detected graphic/icon/illustration regions
    graphic_boxes_norm = []
    if vision_data and isinstance(vision_data.get("regions"), dict):
        reg = vision_data["regions"]
        for k in ("illustration", "veg_symbol"):
            b = _normalize_box_2d(reg.get(k))
            if b:
                ymin, xmin, ymax, xmax = b
                graphic_boxes_norm.append((xmin / 1000 * w, ymin / 1000 * h, xmax / 1000 * w, ymax / 1000 * h))
        for raw_b in reg.get("benefit_icons") or []:
            b = _normalize_box_2d(raw_b)
            if b:
                ymin, xmin, ymax, xmax = b
                graphic_boxes_norm.append((xmin / 1000 * w, ymin / 1000 * h, xmax / 1000 * w, ymax / 1000 * h))

    # Add any genuine EasyOCR detections not already covered by Vision (handles offline mode 100%)
    unmatched_ocr = []
    vision_parsed_rich = has_rich_vision and len(final_blocks) >= 10
    for idx, ob in enumerate(ocr_boxes):
        if idx in matched_ocr_indices:
            continue
        # When Vision already parsed >=10 structured blocks, suppress low-confidence OCR garble or overlapping boxes
        if vision_parsed_rich:
            if ob["conf"] < 0.72 or len(ob["text"].strip()) <= 3:
                continue
            ob_area = max(1, ob["width"] * ob["height"])
            overlaps_vision = False
            for fb in final_blocks:
                ix = max(0, min(ob["left"] + ob["width"], fb["left"] + fb["width"]) - max(ob["left"], fb["left"]))
                iy = max(0, min(ob["top"] + ob["height"], fb["top"] + fb["height"]) - max(ob["top"], fb["top"]))
                if (ix * iy) / float(min(ob_area, max(1, fb["width"] * fb["height"]))) > 0.15:
                    overlaps_vision = True
                    break
            if overlaps_vision:
                continue
        # Drop tiny isolated OCR noise inside graphic/illustration icons or very short low-conf punctuation
        if len(ob["text"]) <= 2 and ob["conf"] < 0.65 and not ob["text"].isdigit():
            continue
        ocx = ob["left"] + ob["width"] * 0.5
        ocy = ob["top"] + ob["height"] * 0.5
        inside_graphic = any((gx0 <= ocx <= gx1 and gy0 <= ocy <= gy1) for (gx0, gy0, gx1, gy1) in graphic_boxes_norm)
        if inside_graphic:
            continue
        unmatched_ocr.append(ob)
    if unmatched_ocr:
        # Group unmatched OCR detections by baseline & gap cleanly
        unmatched_ocr.sort(key=lambda b: (b["top"], b["left"]))
        used = set()
        for i, anchor in enumerate(unmatched_ocr):
            if i in used:
                continue
            line_items = [anchor]
            used.add(i)
            acy = anchor["top"] + anchor["height"] * 0.5
            for j in range(i + 1, len(unmatched_ocr)):
                if j in used:
                    continue
                cand = unmatched_ocr[j]
                ccy = cand["top"] + cand["height"] * 0.5
                min_h = min(anchor["height"], cand["height"])
                if abs(ccy - acy) <= min_h * 0.40 and 0.55 <= (cand["height"] / max(1.0, anchor["height"])) <= 1.8:
                    line_items.append(cand)
                    used.add(j)
            line_items.sort(key=lambda b: b["left"])
            clusters = []
            cur = [line_items[0]]
            for prev_b, curr_b in zip(line_items, line_items[1:]):
                gap = curr_b["left"] - (prev_b["left"] + prev_b["width"])
                avg_h = (prev_b["height"] + curr_b["height"]) * 0.5
                if gap > max(14.0, avg_h * 1.15):
                    clusters.append(cur)
                    cur = [curr_b]
                else:
                    cur.append(curr_b)
            clusters.append(cur)

            for cl in clusters:
                txt = " ".join(c["text"] for c in cl).strip()
                if not txt:
                    continue
                bx = min(c["left"] for c in cl)
                by = min(c["top"] for c in cl)
                bx2 = max(c["left"] + c["width"] for c in cl)
                by2 = max(c["top"] + c["height"] for c in cl)
                bw, bh = max(2, bx2 - bx), max(2, by2 - by)
                conf = float(np.mean([c["conf"] for c in cl]))
                col_hex = extract_robust_text_color(img_bgr, bx, by, bw, bh)
                role = "product_title" if (bh >= h * 0.12 and bx > w * 0.25 and bx < w * 0.70) else "other"
                fmeta = match_font_for_region(img_bgr, bx, by, bw, bh, txt, role=role)
                final_blocks.append({
                    "text": txt,
                    "left": int(bx),
                    "top": int(by),
                    "width": int(bw),
                    "height": int(bh),
                    "fontSize": max(8, int(round(bh * 0.82))),
                    "color": col_hex,
                    "align": "left",
                    "role": role,
                    "conf": round(conf, 3),
                    "needs_review": conf < 0.65,
                    "source": "easyocr_tiled",
                    "lineHeight": 1.12,
                    **fmeta,
                })

    # Convert detected semantic region hints from 0..1000 into pixels
    regions_px = {}
    if vision_data and isinstance(vision_data.get("regions"), dict):
        reg = vision_data["regions"]
        for key in ("nutrition_table", "illustration", "veg_symbol"):
            b = _normalize_box_2d(reg.get(key))
            if b:
                ymin, xmin, ymax, xmax = b
                regions_px[key] = [
                    max(0, int(round(xmin / 1000.0 * w))),
                    max(0, int(round(ymin / 1000.0 * h))),
                    max(4, min(w, int(round((xmax - xmin) / 1000.0 * w)))),
                    max(4, min(h, int(round((ymax - ymin) / 1000.0 * h)))),
                ]
        icons_px = []
        for raw_b in reg.get("benefit_icons") or []:
            b = _normalize_box_2d(raw_b)
            if b:
                ymin, xmin, ymax, xmax = b
                icons_px.append([
                    max(0, int(round(xmin / 1000.0 * w))),
                    max(0, int(round(ymin / 1000.0 * h))),
                    max(4, min(w, int(round((xmax - xmin) / 1000.0 * w)))),
                    max(4, min(h, int(round((ymax - ymin) / 1000.0 * h)))),
                ])
        if icons_px:
            regions_px["benefit_icons"] = icons_px

    label_bounds_px = None
    lb_norm = _normalize_box_2d(vision_data.get("label_bounds_norm")) if vision_data else None
    if lb_norm:
        ymin, xmin, ymax, xmax = lb_norm
        if (xmax - xmin) > 400 and (ymax - ymin) > 300:
            label_bounds_px = [
                max(0, int(round(xmin / 1000.0 * w))),
                max(0, int(round(ymin / 1000.0 * h))),
                min(w, int(round(xmax / 1000.0 * w))),
                min(h, int(round(ymax / 1000.0 * h))),
            ]

    out = {
        "image_width": w,
        "image_height": h,
        "text_blocks": final_blocks,
        "regions": regions_px,
        "label_bounds": label_bounds_px,
        "vision_provider": vision_data.get("_provider") if vision_data else None,
        "warnings": warnings,
    }
    _OCR_CACHE[digest] = out
    return out
