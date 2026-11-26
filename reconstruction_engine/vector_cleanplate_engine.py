"""
Hybrid Clean-Plate Background Reconstruction, Geometric Vector Primitive Extraction,
VTracer Illustration/Icon/Wave Vectorization, Nutrition Table & Regulatory Reconstruction.
"""

import io
import os
import re
import math
import base64
import tempfile
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image

try:
    import vtracer
    HAS_VTRACER = True
except ImportError:
    HAS_VTRACER = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from .hybrid_ocr_layout import analyze_label_text_and_structure


def _bgr_to_hex(bgr) -> str:
    b, g, r = [int(max(0, min(255, round(c)))) for c in bgr[:3]]
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_precision_text_stroke_mask(img_bgr: np.ndarray, text_blocks: list[dict]) -> np.ndarray:
    """Builds a tight character-stroke mask across detected text boxes for clean plate repair."""
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for blk in text_blocks:
        bx = max(0, int(blk["left"]))
        by = max(0, int(blk["top"]))
        bw = max(2, min(w - bx, int(blk["width"])))
        bh = max(2, min(h - by, int(blk["height"])))
        pad = 2
        x1, y1 = max(0, bx - pad), max(0, by - pad)
        x2, y2 = min(w, bx + bw + pad), min(h, by + bh + pad)
        roi = img_bgr[y1:y2, x1:x2]
        if roi.shape[0] < 3 or roi.shape[1] < 3:
            continue

        border = np.concatenate([
            roi[:1, :].reshape(-1, 3),
            roi[-1:, :].reshape(-1, 3),
            roi[:, :1].reshape(-1, 3),
            roi[:, -1:].reshape(-1, 3),
        ], axis=0)
        bg_col = np.median(border, axis=0)
        diff = np.linalg.norm(roi.astype(np.float32) - bg_col.astype(np.float32), axis=2)

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        bg_gray = int(0.114 * bg_col[0] + 0.587 * bg_col[1] + 0.299 * bg_col[2])
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        m_hi = float(np.mean(gray[th == 255])) if np.any(th == 255) else bg_gray
        m_lo = float(np.mean(gray[th == 0])) if np.any(th == 0) else bg_gray
        otsu_fg = (th == 255) if abs(m_hi - bg_gray) > abs(m_lo - bg_gray) else (th == 0)

        stroke = otsu_fg & (diff > 20.0)
        ratio = float(np.sum(stroke)) / max(1, stroke.size)
        if ratio < 0.03 or ratio > 0.72:
            stroke = diff > max(18.0, float(np.percentile(diff, 65)))

        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        stroke_dil = cv2.dilate(stroke.astype(np.uint8) * 255, k, iterations=1)
        mask[y1:y2, x1:x2] = np.maximum(mask[y1:y2, x1:x2], stroke_dil)

    return mask


def _is_background_fill(fill_hex: str, bg_hex: str) -> bool:
    if not fill_hex or fill_hex.lower() == "none":
        return True
    try:
        r1, g1, b1 = int(fill_hex[1:3], 16), int(fill_hex[3:5], 16), int(fill_hex[5:7], 16)
        r2, g2, b2 = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
        return math.hypot(r1 - r2, g1 - g2, b1 - b2) < 28
    except Exception:
        return False


def _trace_rgba_to_clean_svg(
    rgba_crop: np.ndarray,
    bg_hex: str = "#ffffff",
    filter_speckle: int = 6,
    max_paths: int = 80,
    posterize_colors: int = 0,
) -> tuple[str | None, int]:
    """
    Runs VTracer on a tight RGBA cutout and strips redundant bounding background paths.
    Optionally applies K-means palette quantization on smooth gradient artwork so VTracer
    emits clean editable Bezier shapes without path explosion.
    """
    if not HAS_VTRACER or rgba_crop.size == 0:
        return None, 0

    ch, cw = rgba_crop.shape[:2]
    # Upscale tiny icons before tracing so splines stay silky smooth
    scale = min(4.0, max(1.0, 260.0 / float(max(cw, ch))))
    if scale > 1.05:
        trace_im = cv2.resize(rgba_crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)
    else:
        trace_im = rgba_crop.copy()
    th, tw = trace_im.shape[:2]

    if posterize_colors >= 2:
        # Clean K-means color quantization on opaque pixels for crisp editable vector regions
        alpha_ch = trace_im[:, :, 3]
        fg_idx = alpha_ch > 40
        if np.sum(fg_idx) > posterize_colors * 8:
            pts = trace_im[:, :, :3][fg_idx].astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
            _, labels, centers = cv2.kmeans(pts, posterize_colors, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            q_rgb = centers[labels.flatten()].astype(np.uint8)
            trace_im[:, :, :3][fg_idx] = q_rgb
            trace_im[:, :, 3] = np.where(alpha_ch > 65, 255, 0).astype(np.uint8)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_in, \
         tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f_out:
        in_p, out_p = f_in.name, f_out.name

    try:
        Image.fromarray(trace_im, mode="RGBA").save(in_p, format="PNG")
        vtracer.convert_image_to_svg_py(in_p, out_p)
        with open(out_p, "r", encoding="utf-8") as sf:
            svg_raw = sf.read()

        root = ET.fromstring(svg_raw.encode("utf-8", errors="ignore"))
        kept_paths = []
        for elem in root.iter():
            tag = elem.tag.split("}", 1)[-1].lower()
            if tag != "path":
                continue
            d_str = elem.attrib.get("d", "")
            fill = elem.attrib.get("fill", "#000000")
            if not d_str or _is_background_fill(fill, bg_hex):
                continue
            transform = elem.attrib.get("transform", "")
            # Reject full-frame background rects VTracer emits at path 0
            nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+", d_str[:80])]
            if len(d_str) < 42 and len(nums) >= 4 and "M 0 0" in d_str[:12] and max(nums) >= max(tw, th) * 0.92:
                continue
            t_attr = f' transform="{transform}"' if transform else ""
            kept_paths.append(f'<path d="{d_str}" fill="{fill}"{t_attr} />')

        if not kept_paths or len(kept_paths) > max_paths * 2:
            return None, len(kept_paths)

        # Keep largest/most expressive paths if slightly above cap
        kept_paths = kept_paths[:max_paths]
        clean_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="{th}" viewBox="0 0 {tw} {th}">'
            + "".join(kept_paths)
            + "</svg>"
        )
        return clean_svg, len(kept_paths)
    except Exception:
        return None, 0
    finally:
        for p in (in_p, out_p):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


def _extract_foreground_rgba_cutout(img_bgr: np.ndarray, bx: int, by: int, bw: int, bh: int) -> tuple[np.ndarray, np.ndarray, str, bool]:
    """
    Separates foreground graphics inside ROI from local background color.
    Detects whether the cutout looks like a continuous-tone photograph vs clean illustration/icon.
    Returns (rgba_cutout, binary_fg_mask_roi, local_bg_hex, is_photographic).
    """
    h, w = img_bgr.shape[:2]
    x1, y1 = max(0, bx), max(0, by)
    x2, y2 = min(w, bx + bw), min(h, by + bh)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size < 16:
        return np.zeros((4, 4, 4), dtype=np.uint8), np.zeros((4, 4), dtype=np.uint8), "#ffffff", False

    # Sample perimeter of ROI (plus 2px outside if available) for exact local background
    ox1, oy1 = max(0, x1 - 2), max(0, y1 - 2)
    ox2, oy2 = min(w, x2 + 2), min(h, y2 + 2)
    outer = img_bgr[oy1:oy2, ox1:ox2]
    border = np.concatenate([
        outer[:2, :].reshape(-1, 3),
        outer[-2:, :].reshape(-1, 3),
        outer[:, :2].reshape(-1, 3),
        outer[:, -2:].reshape(-1, 3),
    ], axis=0)
    bg_col = np.median(border, axis=0)
    bg_hex = _bgr_to_hex(bg_col)

    diff = np.linalg.norm(roi.astype(np.float32) - bg_col.astype(np.float32), axis=2)
    fg_bool = diff > 22.0
    alpha = np.clip((diff - 14.0) * (255.0 / 24.0), 0.0, 255.0).astype(np.uint8)
    rgba = cv2.cvtColor(roi, cv2.COLOR_BGR2RGBA)
    # Pillow/Fabric expects RGB order inside RGBA data URL, so swap BGR->RGB!
    b, g, r = cv2.split(roi)
    rgba = cv2.merge([r, g, b, alpha])

    # Check color entropy / photographic complexity on foreground pixels
    # Monochromatic/duotone stylized graphics (e.g. purple/red female silhouette) stay vectorizable!
    fg_pixels = roi[fg_bool]
    is_photo = False
    if len(fg_pixels) > 120:
        quant = (fg_pixels // 32).astype(np.int32)
        unique_bins = len(np.unique(quant[:, 0] * 100 + quant[:, 1] * 10 + quant[:, 2]))
        hsv_fg = cv2.cvtColor(fg_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
        chrom_px = hsv_fg[hsv_fg[:, 1] > 30]
        hue_span = float(np.std(chrom_px[:, 0])) if len(chrom_px) > 25 else 0.0
        # Real multi-object photos span multiple distinct hues & wide value bins
        if unique_bins >= 55 and hue_span > 28.0:
            is_photo = True

    return rgba, fg_bool.astype(np.uint8) * 255, bg_hex, is_photo


def _detect_veg_symbol(img_bgr: np.ndarray, region_hint: list[int] | None) -> tuple[dict | None, tuple[int, int, int, int] | None]:
    """Detects green Veg / brown Non-Veg regulatory box+dot symbol cleanly."""
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Green hue ~ 30..95
    green_mask = cv2.inRange(hsv, np.array([30, 28, 25]), np.array([96, 255, 240]))

    if region_hint:
        rx, ry, rw, rh = region_hint
        pad = max(6, int(max(rw, rh) * 0.35))
        sx1, sy1 = max(0, rx - pad), max(0, ry - pad)
        sx2, sy2 = min(w, rx + rw + pad), min(h, ry + rh + pad)
        sub_mask = np.zeros_like(green_mask)
        sub_mask[sy1:sy2, sx1:sx2] = green_mask[sy1:sy2, sx1:sx2]
        green_mask = sub_mask

    cnts, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best_box = None
    best_score = 0.0
    min_dim = max(6, int(h * 0.025))
    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw < min_dim or bh < min_dim or bw > h * 0.25 or bh > h * 0.25:
            continue
        aspect = bw / float(bh)
        if not (0.72 <= aspect <= 1.32):
            continue
        area = cv2.contourArea(c)
        score = bw * bh
        if region_hint and area > 12:
            best_box = (bx, by, bw, bh)
            break
        if score > best_score and area / float(bw * bh) > 0.35:
            best_score = score
            best_box = (bx, by, bw, bh)

    if not best_box and region_hint:
        best_box = tuple(region_hint)

    if not best_box:
        return None, None

    bx, by, bw, bh = best_box
    roi = img_bgr[max(0, by):min(h, by + bh), max(0, bx):min(w, bx + bw)]
    roi_g = green_mask[max(0, by):min(h, by + bh), max(0, bx):min(w, bx + bw)]
    fg_px = roi[roi_g > 0]
    veg_hex = _bgr_to_hex(np.median(fg_px, axis=0)) if len(fg_px) > 5 else "#16803c"
    return {"hex": veg_hex, "bbox": best_box}, best_box


def _detect_pills_and_bars(text_clean_bgr: np.ndarray, mask_exclude: np.ndarray) -> list[dict]:
    """Detects solid filled rounded pills, header bars, table box & dividers cleanly."""
    h, w = text_clean_bgr.shape[:2]
    gray = cv2.cvtColor(text_clean_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(text_clean_bgr, cv2.COLOR_BGR2HSV)

    # Find colored or dark solid UI shapes against light panels (excluding already claimed areas)
    sat_or_dark = ((hsv[:, :, 1] > 42) | (gray < 195)).astype(np.uint8) * 255
    sat_or_dark[mask_exclude > 0] = 0

    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean = cv2.morphologyEx(sat_or_dark, cv2.MORPH_CLOSE, k, iterations=1)
    cnts, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    shapes = []
    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw < 10 or bh < 3:
            continue
        # Skip huge waves (> 40% width at bottom/top) — handled separately by wave vectorizer
        if bw > w * 0.45 and bh > h * 0.10:
            continue
        area = cv2.contourArea(c)
        rect_area = float(bw * bh)
        solidity = area / max(1.0, rect_area)

        # Thin horizontal or vertical divider rule
        if (bh <= max(4, h * 0.015) and bw >= 16) or (bw <= max(4, w * 0.008) and bh >= 10):
            roi = text_clean_bgr[by:by+bh, bx:bx+bw]
            col = _bgr_to_hex(np.median(roi.reshape(-1, 3), axis=0))
            shapes.append({
                "kind": "divider",
                "bbox": (bx, by, bw, bh),
                "fill": col,
            })
            continue

        # Solid filled horizontal pill / header bar (`UNFLAVOURED`, `15 mg`, Table header)
        if solidity > 0.72 and bw >= 26 and 8 <= bh <= h * 0.16 and (bw / float(bh)) >= 1.8:
            roi = text_clean_bgr[by:by+bh, bx:bx+bw]
            # Sample center strip for rich fill color
            cy1, cy2 = max(0, bh // 4), max(1, (3 * bh) // 4)
            cx1, cx2 = max(0, bw // 6), max(1, (5 * bw) // 6)
            center_px = roi[cy1:cy2, cx1:cx2].reshape(-1, 3)
            col = _bgr_to_hex(np.median(center_px, axis=0)) if len(center_px) else "#4b165d"
            # Skip near-white empty frames
            r_v, g_v, b_v = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
            if min(r_v, g_v, b_v) > 225:
                continue
            shapes.append({
                "kind": "pill",
                "bbox": (bx, by, bw, bh),
                "fill": col,
                "rx": min(bh * 0.48, bh * 0.38) if solidity < 0.94 else 4.0,
            })

    return shapes


def _detect_decorative_waves(text_clean_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detects sweeping bottom/top colored decorative gradient wave banners."""
    h, w = text_clean_bgr.shape[:2]
    hsv = cv2.cvtColor(text_clean_bgr, cv2.COLOR_BGR2HSV)
    # Colored saturated bands near top/bottom (> 18% width)
    band = ((hsv[:, :, 1] > 34) & (hsv[:, :, 2] < 240)).astype(np.uint8) * 255
    # Restrict search to bottom 22% or top 16%
    band_roi = np.zeros_like(band)
    band_roi[int(h * 0.78):, :] = band[int(h * 0.78):, :]
    band_roi[:int(h * 0.14), :] = band[:int(h * 0.14), :]

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    band_roi = cv2.morphologyEx(band_roi, cv2.MORPH_CLOSE, k, iterations=2)
    cnts, _ = cv2.findContours(band_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    min_wave_h = max(5, int(h * 0.025))
    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        if bw >= w * 0.22 and bh >= min_wave_h and cv2.contourArea(c) > max(120, w * 0.25):
            boxes.append((bx, by, bw, bh))
    return boxes


def _role_to_layer_category(role: str, text_str: str) -> str:
    r = (role or "").lower()
    t = (text_str or "").lower()
    if r == "product_title":
        return "Product Title"
    if r in ("product_subtitle", "tagline", "flavour_badge"):
        return "Product Subtitle"
    if r in ("strength_badge", "quantity_badge"):
        return "Product Strength"
    if r in ("nutrition_header", "nutrition_cell") or "nutritional information" in t or "serving basis" in t:
        return "Nutrition Table"
    if r in ("product_description", "product_form", "packaging_type"):
        return "Product Description"
    if r == "caution":
        return "Caution"
    if r in ("key_benefit", "key_benefit_heading"):
        return "Key Benefits"
    if r == "manufacturer":
        return "Manufacturer Information"
    if r == "marketed_by":
        return "Marketing Information"
    if r == "batch_info":
        return "Batch Information"
    return "Typography"


def reconstruct_flattened_label(
    image_bytes: bytes,
    width_mm: float | None = None,
    height_mm: float | None = None,
    use_vision: bool = True,
) -> dict:
    """
    Full Hybrid AI + Computer Vision + VTracer Reconstruction Pipeline:
      - High-res Tiled OCR + Vision structure (zero silent edits, flags low-conf)
      - Geometric Vector Reconstruction (Pills, Dividers, Table Header & Frame, Veg Symbol)
      - VTracer Vectorization (Bottom Curves/Waves, Female Illustration, Key Benefit Icons)
      - Clean Plate Inpainting underneath extracted elements (zero duplicate text/graphics)
      - Pure Vector Background + Gradient detection when background is vector-clean!
    """
    arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode uploaded artwork image")
    h, w = img_bgr.shape[:2]

    if not width_mm or not height_mm:
        width_mm = round(max(60.0, w * 25.4 / 150.0), 1)
        height_mm = round(max(40.0, width_mm * (h / float(w))), 1)

    target_w = 1536
    scale = target_w / float(w)
    target_h = max(120, int(round(h * scale)))

    # 1. Hybrid OCR & Document Understanding
    ocr_res = analyze_label_text_and_structure(image_bytes, use_vision=use_vision)
    text_blocks = ocr_res["text_blocks"]
    regions = ocr_res.get("regions") or {}
    label_bounds = ocr_res.get("label_bounds")
    warnings = list(ocr_res.get("warnings") or [])

    # 2. Stroke-Level Text Mask -> Text-Free Working Image
    text_mask = _build_precision_text_stroke_mask(img_bgr, text_blocks)
    text_clean_bgr = cv2.inpaint(img_bgr, text_mask, 4, cv2.INPAINT_TELEA) if np.any(text_mask > 0) else img_bgr.copy()

    # Track non-text vector/raster extractions so they are removed cleanly from base plate
    fg_erased_mask = np.zeros((h, w), dtype=np.uint8)

    objects: list[dict] = []
    counts = {
        "text_objects": 0,
        "vector_shapes": 0,
        "vector_paths": 0,
        "table_cells": 0,
        "icons_vectorized": 0,
        "illustrations_vectorized": 0,
        "retained_rasters": 0,
        "low_conf_texts": 0,
    }

    # 3. Prepare Background & Label Artboard Panel Vectors (emitted only if Clean Plate confirms smooth/vector background)
    top_row_col = _bgr_to_hex(np.median(img_bgr[:max(2, h // 40), :].reshape(-1, 3), axis=0))
    panel_bg_hex = "#ffffff"
    bg_vector_panels: list[dict] = []
    if label_bounds:
        lx0, ly0, lx1, ly1 = label_bounds
        panel_roi = text_clean_bgr[min(h - 4, ly0 + 8):max(ly0 + 12, ly1 - 16), lx0:lx1]
        flat_px = panel_roi.reshape(-1, 3)
        if len(flat_px) > 10:
            lum = flat_px.mean(axis=1)
            if float(np.median(lum)) > 170.0:
                light_px = flat_px[lum >= np.percentile(lum, 70)]
                if len(light_px):
                    panel_bg_hex = _bgr_to_hex(np.median(light_px, axis=0))
            else:
                panel_bg_hex = _bgr_to_hex(np.median(flat_px, axis=0))

        # Outer canvas frame rect (e.g., cream frame if present outside label bounds)
        if top_row_col.lower() != panel_bg_hex.lower():
            bg_vector_panels.append({
                "type": "rect",
                "left": 0,
                "top": 0,
                "width": target_w,
                "height": target_h,
                "fill": top_row_col,
                "stroke": None,
                "strokeWidth": 0,
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": "Background",
                "name": "Artboard Background Frame",
            })

        # Main label base panel vector rect
        bg_vector_panels.append({
            "type": "rect",
            "left": round(lx0 * scale, 2),
            "top": round(ly0 * scale, 2),
            "width": round((lx1 - lx0) * scale, 2),
            "height": round((ly1 - ly0) * scale, 2),
            "fill": panel_bg_hex,
            "stroke": None,
            "strokeWidth": 0,
            "selectable": True,
            "assetType": "reconstructed_vector",
            "layerCategory": "Background",
            "name": "Label Base Background",
        })

        # Center Panel subtle radial/linear metallic highlight panel if center 1/3 differs subtly
        c_mid = text_clean_bgr[min(h - 4, ly0 + 10):max(ly0 + 14, ly1 - 24), int(w * 0.36):int(w * 0.64)]
        if c_mid.size > 20:
            c_edge_col = _bgr_to_hex(np.percentile(c_mid.reshape(-1, 3), 35, axis=0))
            if not _is_background_fill(c_edge_col, panel_bg_hex):
                bg_vector_panels.append({
                    "type": "rect",
                    "left": round(w * 0.345 * scale, 2),
                    "top": round(ly0 * scale, 2),
                    "width": round(w * 0.31 * scale, 2),
                    "height": round((ly1 - ly0) * scale, 2),
                    "fill": {
                        "type": "linear",
                        "coords": {"x1": 0, "y1": 0, "x2": 1, "y2": 0},
                        "gradientUnits": "percentage",
                        "colorStops": [
                            {"offset": 0.0, "color": c_edge_col},
                            {"offset": 0.5, "color": panel_bg_hex},
                            {"offset": 1.0, "color": c_edge_col},
                        ],
                    },
                    "stroke": None,
                    "strokeWidth": 0,
                    "opacity": 0.65,
                    "selectable": True,
                    "assetType": "reconstructed_vector",
                    "layerCategory": "Background Gradients",
                    "name": "Center Panel Soft Gradient",
                })

    # 4. Decorative Bottom/Top Curved Waves (VTracer smooth vector curves)
    wave_boxes = _detect_decorative_waves(text_clean_bgr)
    for w_idx, (wx, wy, ww, wh) in enumerate(wave_boxes):
        # Sample clean interior background color (top edge for bottom waves; bottom edge for top waves)
        roi_w = text_clean_bgr[wy:wy + wh, wx:wx + ww]
        is_bottom_wave = (wy + wh * 0.5) > (h * 0.5)
        ref_y = max(0, wy - 3) if is_bottom_wave else min(h - 1, wy + wh + 2)
        interior_col = np.median(text_clean_bgr[ref_y:ref_y + 2, wx:wx + ww].reshape(-1, 3), axis=0)
        diff_w = np.linalg.norm(roi_w.astype(np.float32) - interior_col.astype(np.float32), axis=2)
        w_mask = (diff_w > 22.0).astype(np.uint8) * 255
        alpha_w = np.clip((diff_w - 14.0) * (255.0 / 22.0), 0.0, 255.0).astype(np.uint8)
        bw_c, gw_c, rw_c = cv2.split(roi_w)
        rgba_w = cv2.merge([rw_c, gw_c, bw_c, alpha_w])
        svg_w, p_cnt = _trace_rgba_to_clean_svg(rgba_w, bg_hex=_bgr_to_hex(interior_col), filter_speckle=10, max_paths=36, posterize_colors=5)
        if svg_w and p_cnt > 0:
            objects.append({
                "type": "svg_group_raw",
                "svg_snippet": svg_w,
                "left": round(wx * scale, 2),
                "top": round(wy * scale, 2),
                "targetWidth": round(ww * scale, 2),
                "targetHeight": round(wh * scale, 2),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": "Decorative Shapes",
                "name": f"Decorative Wave Curve {w_idx + 1}",
            })
            counts["vector_paths"] += p_cnt
            fg_erased_mask[wy:wy + wh, wx:wx + ww] = np.maximum(fg_erased_mask[wy:wy + wh, wx:wx + ww], w_mask)

    # 5. Vegetarian / Non-Veg Regulatory Vector Symbol
    veg_info, veg_box = _detect_veg_symbol(text_clean_bgr, regions.get("veg_symbol"))
    if veg_info and veg_box:
        vx, vy, vw, vh = veg_box
        v_col = veg_info["hex"]
        sw = max(1.5, min(vw, vh) * 0.08 * scale)
        vw_s, vh_s = max(12.0, vw * scale), max(12.0, vh * scale)
        dot_r = min(vw_s, vh_s) * 0.24
        veg_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{vw_s:.1f}" height="{vh_s:.1f}" viewBox="0 0 {vw_s:.1f} {vh_s:.1f}">'
            f'<rect x="{sw*0.5:.1f}" y="{sw*0.5:.1f}" width="{vw_s-sw:.1f}" height="{vh_s-sw:.1f}" '
            f'rx="2" fill="#ffffff" stroke="{v_col}" stroke-width="{sw:.1f}" />'
            f'<circle cx="{vw_s*0.5:.1f}" cy="{vh_s*0.5:.1f}" r="{dot_r:.1f}" fill="{v_col}" />'
            f'</svg>'
        )
        objects.append({
            "type": "svg_group_raw",
            "svg_snippet": veg_svg,
            "left": round(vx * scale, 2),
            "top": round(vy * scale, 2),
            "targetWidth": round(vw_s, 2),
            "targetHeight": round(vh_s, 2),
            "selectable": True,
            "assetType": "reconstructed_vector",
            "layerCategory": "Regulatory Symbols",
            "name": "Vegetarian Symbol (Vector)",
        })
        counts["vector_shapes"] += 2
        fg_erased_mask[max(0, vy - 2):min(h, vy + vh + 2), max(0, vx - 2):min(w, vx + vw + 2)] = 255

    # 6. Barcode & QR Decoding Verification
    try:
        qr = cv2.QRCodeDetector()
        qr_val, qr_pts, _ = qr.detectAndDecode(img_bgr)
        if qr_val and qr_pts is not None and HAS_QRCODE:
            qxs = [p[0] for p in qr_pts[0]]
            qys = [p[1] for p in qr_pts[0]]
            qx, qy = int(min(qxs)), int(min(qys))
            qw, qh = max(16, int(max(qxs) - qx)), max(16, int(max(qys) - qy))
            import qrcode.image.svg
            qfactory = qrcode.image.svg.SvgPathImage
            qimg = qrcode.make(qr_val, image_factory=qfactory, border=1)
            qbuf = io.BytesIO()
            qimg.save(qbuf)
            qr_svg = qbuf.getvalue().decode("utf-8", errors="ignore")
            objects.append({
                "type": "svg_group_raw",
                "svg_snippet": qr_svg,
                "left": round(qx * scale, 2),
                "top": round(qy * scale, 2),
                "targetWidth": round(qw * scale, 2),
                "targetHeight": round(qh * scale, 2),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": "Barcode and QR Code",
                "name": f"QR Vector ({qr_val[:18]})",
            })
            counts["vector_paths"] += 1
            fg_erased_mask[max(0, qy - 2):min(h, qy + qh + 2), max(0, qx - 2):min(w, qx + qw + 2)] = 255
    except Exception:
        pass

    # 7. Female Illustration / Center Hero Illustration Vectorization
    if regions.get("illustration"):
        ix, iy, iw, ih = regions["illustration"]
        rgba_il, il_mask, _, is_photo = _extract_foreground_rgba_cutout(text_clean_bgr, ix, iy, iw, ih)
        if not is_photo:
            svg_il, p_cnt = _trace_rgba_to_clean_svg(rgba_il, bg_hex=panel_bg_hex, filter_speckle=5, max_paths=95, posterize_colors=5)
            if svg_il and p_cnt > 0:
                objects.append({
                    "type": "svg_group_raw",
                    "svg_snippet": svg_il,
                    "left": round(ix * scale, 2),
                    "top": round(iy * scale, 2),
                    "targetWidth": round(iw * scale, 2),
                    "targetHeight": round(ih * scale, 2),
                    "selectable": True,
                    "assetType": "reconstructed_vector",
                    "layerCategory": "Product Illustration",
                    "name": "Product Illustration (Vector)",
                })
                counts["illustrations_vectorized"] += 1
                counts["vector_paths"] += p_cnt
                fg_erased_mask[iy:iy + ih, ix:ix + iw] = np.maximum(fg_erased_mask[iy:iy + ih, ix:ix + iw], il_mask)
            else:
                is_photo = True
        if is_photo:
            # Retain transparent RGBA PNG asset when complex photographic artwork cannot trace cleanly
            pil_cut = Image.fromarray(rgba_il, mode="RGBA")
            c_io = io.BytesIO()
            pil_cut.save(c_io, format="PNG")
            cut_b64 = "data:image/png;base64," + base64.b64encode(c_io.getvalue()).decode("ascii")
            objects.append({
                "type": "image",
                "src": cut_b64,
                "left": round(ix * scale, 2),
                "top": round(iy * scale, 2),
                "width": round(iw * scale, 2),
                "height": round(ih * scale, 2),
                "selectable": True,
                "assetType": "retained_raster",
                "layerCategory": "Retained Raster Assets",
                "name": "Retained Illustration Asset",
            })
            counts["retained_rasters"] += 1
            fg_erased_mask[iy:iy + ih, ix:ix + iw] = np.maximum(fg_erased_mask[iy:iy + ih, ix:ix + iw], il_mask)
            warnings.append("Complex photographic illustration preserved as high-resolution transparent raster asset.")

    # 8. Key Benefit Icons Vectorization (VTracer)
    for b_idx, b_box in enumerate(regions.get("benefit_icons") or []):
        bx, by, bw, bh = b_box
        rgba_ic, ic_mask, _, is_photo = _extract_foreground_rgba_cutout(text_clean_bgr, bx, by, bw, bh)
        svg_ic, p_cnt = _trace_rgba_to_clean_svg(rgba_ic, bg_hex=panel_bg_hex, filter_speckle=4, max_paths=45)
        if svg_ic and p_cnt > 0:
            objects.append({
                "type": "svg_group_raw",
                "svg_snippet": svg_ic,
                "left": round(bx * scale, 2),
                "top": round(by * scale, 2),
                "targetWidth": round(bw * scale, 2),
                "targetHeight": round(bh * scale, 2),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": "Key Benefits",
                "name": f"Benefit Icon {b_idx + 1} (Vector)",
            })
            counts["icons_vectorized"] += 1
            counts["vector_paths"] += p_cnt
            fg_erased_mask[by:by + bh, bx:bx + bw] = np.maximum(fg_erased_mask[by:by + bh, bx:bx + bw], ic_mask)

    # 9. Geometric Pills, Badges, Table Box/Header Bar & Dividers
    # Emit Nutrition Table container/header FIRST and claim mask before generic pill detection
    nt_box = regions.get("nutrition_table")

    # Emit Nutrition Table outer white rounded container & colored header bar if detected
    if nt_box:
        nx, ny, nw, nh = nt_box
        # Tighten table top ny so external subtitles (e.g. 'Serving basis...') stay outside the table frame
        scan_roi = img_bgr[ny:min(h, ny + nh), nx:min(w, nx + nw)]
        if scan_roi.size > 16:
            hsv_sc = cv2.cvtColor(scan_roi, cv2.COLOR_BGR2HSV)
            # Require high horizontal continuity (>58%) so sparse dark text lines like 'Serving basis...' never count as header bars
            row_colored = np.mean((hsv_sc[:, :, 1] > 40) | (hsv_sc[:, :, 2] < 135), axis=1)
            colored_rows = np.where(row_colored > 0.58)[0]
            if len(colored_rows) > 0:
                shift_y = int(colored_rows[0])
                if 0 < shift_y < int(nh * 0.45):
                    ny = ny + shift_y
                    nh = max(12, nh - shift_y)
                hdr_h_px = max(8, int(colored_rows[-1]) - shift_y + 2) if len(colored_rows) > 1 else max(8, int(nh * 0.44))
                hdr_h_px = min(hdr_h_px, int(nh * 0.56))
            else:
                hdr_h_px = max(8, int(nh * 0.45))
        else:
            hdr_h_px = max(8, int(nh * 0.45))

        nt_body_roi = text_clean_bgr[min(h, ny + int(nh * 0.25)):min(h, ny + nh), nx:min(w, nx + nw)]
        nt_is_light = True
        if nt_body_roi.size > 16:
            nt_is_light = float(np.median(cv2.cvtColor(nt_body_roi, cv2.COLOR_BGR2GRAY))) > 165.0

        objects.append({
            "type": "rect",
            "left": round(nx * scale, 2),
            "top": round(ny * scale, 2),
            "width": round(nw * scale, 2),
            "height": round(nh * scale, 2),
            "rx": 10,
            "ry": 10,
            "fill": "#ffffff" if nt_is_light else "rgba(0,0,0,0.0)",
            "stroke": "#cbd5e1" if nt_is_light else "#475569",
            "strokeWidth": 1.5,
            "selectable": True,
            "assetType": "reconstructed_vector",
            "layerCategory": "Nutrition Table",
            "name": "Nutrition Table Frame",
        })
        counts["vector_shapes"] += 1
        hdr_roi = img_bgr[ny:min(h, ny + hdr_h_px), nx:min(w, nx + nw)]
        if hdr_roi.size > 16:
            hsv_hdr = cv2.cvtColor(hdr_roi, cv2.COLOR_BGR2HSV)
            dark_hdr = hdr_roi[(hsv_hdr[:, :, 1] > 40)]
            if len(dark_hdr) == 0 and nt_is_light:
                dark_hdr = hdr_roi[(hsv_hdr[:, :, 1] > 35) | (hsv_hdr[:, :, 2] < 150)]
            if len(dark_hdr) > 10:
                hdr_hex = _bgr_to_hex(np.percentile(dark_hdr, 30, axis=0))
                objects.append({
                    "type": "rect",
                    "left": round(nx * scale, 2),
                    "top": round(ny * scale, 2),
                    "width": round(nw * scale, 2),
                    "height": round(hdr_h_px * scale, 2),
                    "rx": 8,
                    "ry": 8,
                    "fill": hdr_hex,
                    "stroke": None,
                    "strokeWidth": 0,
                    "selectable": True,
                    "assetType": "reconstructed_vector",
                    "layerCategory": "Nutrition Table",
                    "name": "Nutrition Table Header Bar",
                })
                counts["vector_shapes"] += 1
        if nt_is_light:
            fg_erased_mask[max(0, ny - 2):min(h, ny + nh + 2), max(0, nx - 2):min(w, nx + nw + 2)] = 255
        else:
            # On dark transparent tables (e.g. black carbon fiber), only erase header bar if solid colored
            if len(hdr_roi) > 0 and len(hdr_roi[cv2.cvtColor(hdr_roi, cv2.COLOR_BGR2HSV)[:, :, 1] > 40]) > 10:
                fg_erased_mask[max(0, ny - 2):min(h, ny + hdr_h_px + 2), max(0, nx - 2):min(w, nx + nw + 2)] = 255
        nt_box = [nx, ny, nw, nh]

    shapes = _detect_pills_and_bars(text_clean_bgr, fg_erased_mask)

    # Text-guided badge/pill reconstruction & contrasting ink verification
    for tb_i, tb in enumerate(text_blocks):
        bx, by, bw, bh = tb["left"], tb["top"], tb["width"], tb["height"]
        if tb.get("role") in ("flavour_badge", "strength_badge", "quantity_badge"):
            pad_x, pad_y = max(4, int(bw * 0.10)), max(2, int(bh * 0.14))
            px1, py1 = max(0, bx - pad_x), max(0, by - pad_y)
            px2, py2 = min(w, bx + bw + pad_x), min(h, by + bh + pad_y)
            core_roi = img_bgr[by:min(h, by + bh), bx:min(w, bx + bw)]
            has_colored_pill = False
            has_white_pill = False
            med_col = "#ffffff"
            if core_roi.size > 9:
                hsv_c = cv2.cvtColor(core_roi, cv2.COLOR_BGR2HSV)
                dark_sat = core_roi[(hsv_c[:, :, 1] > 35) | (hsv_c[:, :, 2] < 165)]
                ratio_c = len(dark_sat) / max(1, core_roi.shape[0] * core_roi.shape[1])
                sat_ratio = float(np.mean(hsv_c[:, :, 1] > 42))
                white_ratio = float(np.mean(hsv_c[:, :, 2] > 205))
                if ratio_c > 0.28 and len(dark_sat) > 4:
                    l_strip = img_bgr[by:min(h, by + bh), max(0, bx - 4):max(1, bx)]
                    r_strip = img_bgr[by:min(h, by + bh), min(w - 1, bx + bw):min(w, bx + bw + 4)]
                    edge_band = np.concatenate([l_strip.reshape(-1, 3), r_strip.reshape(-1, 3)], axis=0)
                    edge_colored = 0.0
                    edge_sat = 0.0
                    if len(edge_band) > 0:
                        hsv_e = cv2.cvtColor(edge_band.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
                        edge_colored = float(np.mean((hsv_e[:, 1] > 35) | (hsv_e[:, 2] < 165)))
                        edge_sat = float(np.mean(hsv_e[:, 1] > 42))
                    has_colored_pill = (edge_sat > 0.30) or (sat_ratio > 0.28)
                    if has_colored_pill:
                        sat_only = core_roi[hsv_c[:, :, 1] > 42]
                        sample_src = sat_only if len(sat_only) > 10 else dark_sat
                        med_col = _bgr_to_hex(np.percentile(sample_src, 35, axis=0))
                    elif white_ratio > 0.45 and edge_colored <= 0.35:
                        has_white_pill = True
                elif white_ratio > 0.45:
                    has_white_pill = True
            if has_colored_pill:
                tb["color"] = "#ffffff"
            elif has_white_pill:
                tb["color"] = "#1e293b" if _is_background_fill(tb.get("color", ""), "#ffffff") else tb["color"]
            if has_colored_pill or has_white_pill:
                objects.append({
                    "type": "rect",
                    "left": round(px1 * scale, 2),
                    "top": round(py1 * scale, 2),
                    "width": round((px2 - px1) * scale, 2),
                    "height": round((py2 - py1) * scale, 2),
                    "rx": round((py2 - py1) * scale * 0.45, 2),
                    "ry": round((py2 - py1) * scale * 0.45, 2),
                    "fill": med_col,
                    "stroke": "#cbd5e1" if not has_colored_pill else None,
                    "strokeWidth": 1.2 if not has_colored_pill else 0,
                    "selectable": True,
                    "assetType": "reconstructed_vector",
                    "layerCategory": _role_to_layer_category(tb.get("role", ""), tb["text"]),
                    "name": f"Badge Pill: {tb['text'][:16]}",
                })
                counts["vector_shapes"] += 1
                fg_erased_mask[py1:py2, px1:px2] = 255
        elif nt_box and (nt_box[0] - 4 <= bx + bw * 0.5 <= nt_box[0] + nt_box[2] + 4):
            ny, nh = nt_box[1], nt_box[3]
            if ny - 2 <= by + bh * 0.5 <= ny + nh * 0.48 and (nt_is_light or len(img_bgr[by:min(h, by+bh), bx:min(w, bx+bw)]) > 0):
                if nt_is_light:
                    tb["color"] = "#ffffff"
            elif nt_is_light and by + bh * 0.5 > ny + nh * 0.48 and by + bh * 0.5 <= ny + nh + 4:
                if _is_background_fill(tb.get("color", ""), "#ffffff"):
                    tb["color"] = "#1e293b"

    for s_idx, sh in enumerate(shapes):
        sx, sy, sw, sh_h = sh["bbox"]
        in_table = bool(nt_box and (sx + sw * 0.5) >= nt_box[0] and (sx + sw * 0.5) <= (nt_box[0] + nt_box[2]) and (sy + sh_h * 0.5) >= nt_box[1] and (sy + sh_h * 0.5) <= (nt_box[1] + nt_box[3]))
        layer_cat = "Nutrition Table" if in_table else "Decorative Shapes"
        if sh["kind"] == "pill":
            rx_s = round(sh.get("rx", 8.0) * scale, 2)
            objects.append({
                "type": "rect",
                "left": round(sx * scale, 2),
                "top": round(sy * scale, 2),
                "width": round(sw * scale, 2),
                "height": round(sh_h * scale, 2),
                "rx": rx_s,
                "ry": rx_s,
                "fill": sh["fill"],
                "stroke": None,
                "strokeWidth": 0,
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": layer_cat,
                "name": "Nutrition Table Header" if in_table else f"Vector Pill {s_idx + 1}",
            })
            counts["vector_shapes"] += 1
            fg_erased_mask[sy:sy + sh_h, sx:sx + sw] = 255
        elif sh["kind"] == "divider":
            objects.append({
                "type": "rect",
                "left": round(sx * scale, 2),
                "top": round(sy * scale, 2),
                "width": round(max(1.5, sw * scale), 2),
                "height": round(max(1.5, sh_h * scale), 2),
                "rx": 0,
                "ry": 0,
                "fill": sh["fill"],
                "stroke": None,
                "strokeWidth": 0,
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": layer_cat,
                "name": f"Accent Rule {s_idx + 1}",
            })
            counts["vector_shapes"] += 1
            fg_erased_mask[sy:sy + sh_h, sx:sx + sw] = 255

    # 10. Finalize Clean Plate Background & Check Vector vs Clean-Plate Raster Necessity
    full_erased = np.maximum(text_mask, fg_erased_mask)
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dil_erased = cv2.dilate(full_erased, k5, iterations=1)
    clean_plate_bgr = cv2.inpaint(img_bgr, dil_erased, 6, cv2.INPAINT_TELEA) if np.any(dil_erased > 0) else img_bgr.copy()

    # Check if clean plate background already has residual photographic textures inside label bounds
    need_clean_plate_raster = True
    if label_bounds:
        lx0, ly0, lx1, ly1 = label_bounds
        sub_cp = clean_plate_bgr[min(h - 4, ly0 + 12):max(ly0 + 16, int(h * 0.78)), lx0:lx1]
        if sub_cp.size > 50 and float(np.std(cv2.cvtColor(sub_cp, cv2.COLOR_BGR2GRAY))) < 18.0:
            # Clean gradient/white background — pure SVG/Fabric vector background stays razor-sharp at 1600%!
            need_clean_plate_raster = False

    cp_resized = cv2.resize(clean_plate_bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    _, cp_buf = cv2.imencode(".png", cp_resized)
    clean_plate_b64 = "data:image/png;base64," + base64.b64encode(cp_buf.tobytes()).decode("ascii")

    if need_clean_plate_raster:
        # Place clean plate raster base cleanly at z-index 0 (behind vector shapes and text)
        objects.insert(0, {
            "type": "image",
            "src": clean_plate_b64,
            "left": 0,
            "top": 0,
            "width": target_w,
            "height": target_h,
            "selectable": False,
            "evented": True,
            "assetType": "clean_plate_base",
            "layerCategory": "Background",
            "name": "Clean Plate Background Base",
        })
    elif bg_vector_panels:
        for bp in reversed(bg_vector_panels):
            objects.insert(0, bp)
            counts["vector_shapes"] += 1

    # 11. Editable Text Objects (Top Z-Order above shapes/icons/tables)
    for idx, tb in enumerate(text_blocks):
        role = tb.get("role", "other")
        layer_cat = _role_to_layer_category(role, tb["text"])
        if role in ("nutrition_header", "nutrition_cell"):
            counts["table_cells"] += 1
        if tb.get("needs_review"):
            counts["low_conf_texts"] += 1

        # Give multi-line or paragraph boxes generous horizontal breathing room to avoid vertical wrap collisions
        w_mult = 1.18 if "\n" in tb["text"] or len(tb["text"]) > 24 else 1.22
        fs_scaled = max(9, int(round(tb["fontSize"] * scale)))
        box_w_scaled = max(36.0, round(tb["width"] * scale * w_mult, 2))
        box_left = round(tb["left"] * scale, 2)
        if tb.get("align") == "center":
            # Expand symmetrically slightly around center for crisp centered headings
            extra = box_w_scaled - tb["width"] * scale
            box_left = max(0.0, round(box_left - extra * 0.5, 2))

        objects.append({
            "type": "textbox",
            "text": tb["text"],
            "left": box_left,
            "top": round(tb["top"] * scale, 2),
            "width": box_w_scaled,
            "fontSize": fs_scaled,
            "fontFamily": tb.get("fontFamily", "Montserrat"),
            "fontWeight": tb.get("fontWeight", "700"),
            "fontStyle": tb.get("fontStyle", "normal"),
            "fill": tb.get("color", "#1e293b"),
            "textAlign": tb.get("align", "left"),
            "lineHeight": tb.get("lineHeight", 1.14),
            "charSpacing": tb.get("charSpacing", 0),
            "editable": True,
            "isImportedText": True,
            "ocrConfidence": tb.get("conf", 0.8),
            "ocrSource": tb.get("source", "easyocr"),
            "needsReview": bool(tb.get("needs_review")),
            "semanticRole": role,
            "assetType": "editable_text",
            "layerCategory": layer_cat,
            "name": f"{layer_cat}: {tb['text'].splitlines()[0][:24]}",
        })
        counts["text_objects"] += 1

    # Original image data URL for comparison modal
    _, orig_buf = cv2.imencode(".png", img_bgr)
    orig_b64 = "data:image/png;base64," + base64.b64encode(orig_buf.tobytes()).decode("ascii")

    avg_conf = float(np.mean([tb["conf"] for tb in text_blocks])) if text_blocks else 0.0

    return {
        "success": True,
        "native_vector_mode": False,
        "canvas_width": target_w,
        "canvas_height": target_h,
        "dimensions_mm": {"width": float(width_mm), "height": float(height_mm)},
        "background_color": top_row_col,
        "vector_only_background": not need_clean_plate_raster,
        "preview_url": orig_b64,
        "clean_background_data_url": clean_plate_b64,
        "raw_objects": objects,
        "text_elements": text_blocks,
        "vision_provider": ocr_res.get("vision_provider"),
        "confidence_score": round(avg_conf, 3),
        "stats": {
            "total_objects": len(objects),
            "text_objects": counts["text_objects"],
            "vector_objects": counts["vector_shapes"] + counts["vector_paths"],
            "geometric_shapes": counts["vector_shapes"],
            "vector_paths": counts["vector_paths"],
            "table_cells": counts["table_cells"],
            "icons_vectorized": counts["icons_vectorized"],
            "illustrations_vectorized": counts["illustrations_vectorized"],
            "image_objects": counts["retained_rasters"] + (1 if need_clean_plate_raster else 0),
            "retained_rasters": counts["retained_rasters"],
            "low_conf_texts": counts["low_conf_texts"],
            "vector_only_background": not need_clean_plate_raster,
        },
        "warnings": list(dict.fromkeys(warnings)),
    }
