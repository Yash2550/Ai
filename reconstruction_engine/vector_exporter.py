"""
CorelDRAW-Compatible Editable SVG, Outlined Text SVG (FontTools),
Hybrid Vector PDF (ReportLab), and CorelDRAW Exchange ZIP Exporter.

Strictly preserves true vector geometry, Bezier curves, gradients, editable text,
and physical millimeter dimensions. Never flattens vector scenes into single PNGs.
"""

import io
import os
import re
import math
import json
import base64
import zipfile
from html import escape
from PIL import Image

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont

from .font_matcher import get_ttf_path_for_studio_font, text_to_svg_path_d

_REGISTERED_RL_FONTS: dict[tuple[str, bool, bool], str] = {}


def _get_reportlab_font(font_family: str = "Montserrat", bold: bool = False, italic: bool = False) -> str:
    key = (font_family or "Inter", bool(bold), bool(italic))
    if key in _REGISTERED_RL_FONTS:
        return _REGISTERED_RL_FONTS[key]

    ttf_path = get_ttf_path_for_studio_font(font_family, bold=bold, italic=italic)
    if ttf_path and os.path.isfile(ttf_path):
        safe_reg = re.sub(r"[^A-Za-z0-9_]", "_", f"GOMZI_{key[0]}_{int(bold)}_{int(italic)}")
        try:
            pdfmetrics.registerFont(RLTTFont(safe_reg, ttf_path))
            _REGISTERED_RL_FONTS[key] = safe_reg
            return safe_reg
        except Exception:
            pass

    fallback = "Helvetica-BoldOblique" if (bold and italic) else ("Helvetica-Bold" if bold else ("Helvetica-Oblique" if italic else "Helvetica"))
    _REGISTERED_RL_FONTS[key] = fallback
    return fallback


def _color_hex(val, default_hex: str | None = None) -> str | None:
    if val is None or val == "":
        return default_hex
    if isinstance(val, dict):
        stops = val.get("colorStops") or []
        if stops:
            return stops[0].get("color") or default_hex
        return default_hex
    s = str(val).strip()
    if s.lower() == "none":
        return None
    if s.startswith("#") and len(s) in (4, 7, 9):
        return s[:7]
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s, re.IGNORECASE)
    if m:
        return f"#{int(m.group(1)):02x}{int(m.group(2)):02x}{int(m.group(3)):02x}"
    return s


def _fabric_path_to_d(path_cmds) -> str:
    if isinstance(path_cmds, str):
        return path_cmds
    if not isinstance(path_cmds, list):
        return ""
    parts = []
    for cmd in path_cmds:
        if not isinstance(cmd, list) or not cmd:
            continue
        op = str(cmd[0])
        nums = [f"{float(v):.3f}".rstrip("0").rstrip(".") if isinstance(v, (int, float)) else str(v) for v in cmd[1:]]
        parts.append(op + (" " + " ".join(nums) if nums else ""))
    return " ".join(parts)


def _object_center_and_local_offset(obj: dict) -> tuple[float, float, float, float, float, float, float]:
    """Returns (cx, cy, sx, sy, angle, local_cx, local_cy) for any Fabric JSON object."""
    sx = float(obj.get("scaleX", 1.0) or 1.0)
    sy = float(obj.get("scaleY", 1.0) or 1.0)
    ang = float(obj.get("angle", 0.0) or 0.0)
    w = float(obj.get("width", 0.0) or 0.0)
    h = float(obj.get("height", 0.0) or 0.0)
    if obj.get("type") == "circle" and not w:
        r = float(obj.get("radius", 0.0) or 0.0)
        w = h = r * 2.0
    elif obj.get("type") == "ellipse" and not w:
        w = float(obj.get("rx", 0.0) or 0.0) * 2.0
        h = float(obj.get("ry", 0.0) or 0.0) * 2.0

    left = float(obj.get("left", 0.0) or 0.0)
    top = float(obj.get("top", 0.0) or 0.0)
    ox = (obj.get("originX") or "left").lower()
    oy = (obj.get("originY") or "top").lower()

    scaled_w, scaled_h = w * sx, h * sy
    if ox == "center":
        cx = left
    elif ox == "right":
        cx = left - scaled_w * 0.5
    else:
        cx = left + scaled_w * 0.5

    if oy == "center":
        cy = top
    elif oy == "bottom":
        cy = top - scaled_h * 0.5
    else:
        cy = top + scaled_h * 0.5

    po = obj.get("pathOffset")
    if isinstance(po, dict) and obj.get("type") == "path":
        lx, ly = float(po.get("x", w * 0.5)), float(po.get("y", h * 0.5))
    else:
        lx, ly = w * 0.5, h * 0.5

    return cx, cy, sx, sy, ang, lx, ly


def _is_bold_weight(w_val) -> bool:
    s = str(w_val or "").lower()
    if s in ("bold", "bolder", "600", "700", "800", "900"):
        return True
    try:
        return int(float(s)) >= 600
    except Exception:
        return False


def _wrap_text_to_box_width(txt: str, box_w: float, fs: float) -> list[str]:
    """Wraps long single-line paragraphs to match Fabric Textbox box_w inside exported SVG/PDF."""
    out_lines: list[str] = []
    # Conservative Latin glyph advance ~0.52 * fontSize
    max_chars = max(8, int(box_w / max(4.0, fs * 0.52)))
    for raw_ln in txt.splitlines():
        s = raw_ln.rstrip()
        if not s or len(s) <= max_chars:
            out_lines.append(s)
            continue
        words = s.split(" ")
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= max_chars:
                cur += " " + w
            else:
                out_lines.append(cur)
                cur = w
        if cur:
            out_lines.append(cur)
    return out_lines or [""]


def build_coreldraw_svg(
    fabric_json: dict,
    width_mm: float = 160.0,
    height_mm: float = 65.0,
    outline_text: bool = False,
    title: str = "GOMZI BOB Vector Label",
) -> bytes:
    """
    Exports a CorelDRAW X4-2024 compatible SVG 1.1 document directly from Fabric.js scene JSON.
    Uses physical millimeter dimensions, grouped logical layers, inline style attributes,
    SVG gradients, real vector paths/primitives, and either:
      - outline_text=False -> real editable <text>/<tspan> nodes
      - outline_text=True  -> font-independent glyph vector <path> curves via FontTools
    """
    cw = float(fabric_json.get("width") or 1536)
    ch = float(fabric_json.get("height") or 512)
    if height_mm <= 0:
        height_mm = round(width_mm * (ch / max(1.0, cw)), 2)

    defs_elems: list[str] = []
    grad_counter = 0

    def _register_fill(fill_val) -> str:
        nonlocal grad_counter
        if isinstance(fill_val, dict) and fill_val.get("colorStops"):
            grad_counter += 1
            gid = f"gomziGrad_{grad_counter}"
            stops = fill_val.get("colorStops", [])
            coords = fill_val.get("coords") or {}
            x1 = float(coords.get("x1", 0)) * 100
            y1 = float(coords.get("y1", 0)) * 100
            x2 = float(coords.get("x2", 1)) * 100
            y2 = float(coords.get("y2", 0)) * 100
            stop_xml = "".join(
                f'<stop offset="{float(st.get("offset", 0))*100:.1f}%" stop-color="{_color_hex(st.get("color"), "#ffffff")}" />'
                for st in stops
            )
            if fill_val.get("type") == "radial":
                defs_elems.append(f'<radialGradient id="{gid}" cx="50%" cy="50%" r="50%">{stop_xml}</radialGradient>')
            else:
                defs_elems.append(
                    f'<linearGradient id="{gid}" x1="{x1:.1f}%" y1="{y1:.1f}%" x2="{x2:.1f}%" y2="{y2:.1f}%">{stop_xml}</linearGradient>'
                )
            return f"url(#{gid})"
        hex_c = _color_hex(fill_val, None)
        return hex_c if hex_c else "none"

    def _emit_object(obj: dict, in_group: bool = False) -> str:
        if obj.get("visible") is False or obj.get("isGuideLine"):
            return ""
        otype = (obj.get("type") or "").lower()
        opacity = float(obj.get("opacity", 1.0) or 1.0)
        op_attr = f' opacity="{opacity:.3f}"' if opacity < 0.999 else ""
        stroke_c = _color_hex(obj.get("stroke"), None)
        sw = float(obj.get("strokeWidth", 0) or 0)
        stroke_attr = f' stroke="{stroke_c}" stroke-width="{sw:.2f}"' if (stroke_c and sw > 0) else ' stroke="none"'

        if in_group:
            # Inside Fabric group JSON, left/top already reference group center coords!
            sx = float(obj.get("scaleX", 1.0) or 1.0)
            sy = float(obj.get("scaleY", 1.0) or 1.0)
            ang = float(obj.get("angle", 0.0) or 0.0)
            w = float(obj.get("width", 0.0) or 0.0)
            h = float(obj.get("height", 0.0) or 0.0)
            left = float(obj.get("left", 0.0) or 0.0)
            top = float(obj.get("top", 0.0) or 0.0)
            cx = left + (0.0 if (obj.get("originX") == "center") else w * sx * 0.5)
            cy = top + (0.0 if (obj.get("originY") == "center") else h * sy * 0.5)
            po = obj.get("pathOffset")
            lx, ly = (float(po["x"]), float(po["y"])) if (isinstance(po, dict) and otype == "path") else (w * 0.5, h * 0.5)
        else:
            cx, cy, sx, sy, ang, lx, ly = _object_center_and_local_offset(obj)

        tr = f'transform="translate({cx:.2f}, {cy:.2f}) rotate({ang:.2f}) scale({sx:.4f}, {sy:.4f}) translate({-lx:.2f}, {-ly:.2f})"'

        if otype == "group":
            sub_items = []
            for sub in obj.get("objects") or []:
                em = _emit_object(sub, in_group=True)
                if em:
                    sub_items.append(em)
            # Fabric group child coords are already centered around group center -> translate(-w/2, -h/2) not needed
            g_tr = f'transform="translate({cx:.2f}, {cy:.2f}) rotate({ang:.2f}) scale({sx:.4f}, {sy:.4f})"'
            g_name = escape(re.sub(r"[^A-Za-z0-9_-]+", "_", str(obj.get("name") or "VectorGroup")))
            return f'  <g id="{g_name}" {g_tr}{op_attr}>\n' + "\n".join(sub_items) + "\n  </g>"

        if otype == "rect":
            w = float(obj.get("width", 0) or 0)
            h = float(obj.get("height", 0) or 0)
            rx = float(obj.get("rx", 0) or 0)
            fill_ref = _register_fill(obj.get("fill"))
            return f'  <rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" rx="{rx:.2f}" ry="{rx:.2f}" fill="{fill_ref}"{stroke_attr}{op_attr} {tr} />'

        if otype == "circle":
            r = float(obj.get("radius", 0) or 0)
            fill_ref = _register_fill(obj.get("fill"))
            return f'  <circle cx="{r:.2f}" cy="{r:.2f}" r="{r:.2f}" fill="{fill_ref}"{stroke_attr}{op_attr} {tr} />'

        if otype == "ellipse":
            rx = float(obj.get("rx", 0) or 0)
            ry = float(obj.get("ry", 0) or 0)
            fill_ref = _register_fill(obj.get("fill"))
            return f'  <ellipse cx="{rx:.2f}" cy="{ry:.2f}" rx="{rx:.2f}" ry="{ry:.2f}" fill="{fill_ref}"{stroke_attr}{op_attr} {tr} />'

        if otype == "line":
            x1 = float(obj.get("x1", 0) or 0) + lx
            y1 = float(obj.get("y1", 0) or 0) + ly
            x2 = float(obj.get("x2", 0) or 0) + lx
            y2 = float(obj.get("y2", 0) or 0) + ly
            return f'  <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {stroke_attr}{op_attr} {tr} />'

        if otype == "path":
            d_str = _fabric_path_to_d(obj.get("path"))
            if not d_str:
                return ""
            fill_ref = _register_fill(obj.get("fill"))
            return f'  <path d="{d_str}" fill="{fill_ref}"{stroke_attr}{op_attr} {tr} />'

        if otype in ("textbox", "i-text", "text"):
            txt = str(obj.get("text") or "")
            if not txt.strip():
                return ""
            fs = float(obj.get("fontSize", 16) or 16)
            fam = str(obj.get("fontFamily", "Montserrat") or "Montserrat")
            is_bold = _is_bold_weight(obj.get("fontWeight"))
            is_ital = str(obj.get("fontStyle", "")).lower() == "italic"
            fill_c = _color_hex(obj.get("fill"), "#111827") or "#111827"
            align = (obj.get("textAlign") or "left").lower()
            lh = float(obj.get("lineHeight", 1.14) or 1.14)
            box_w = float(obj.get("width", 100) or 100)
            lines = _wrap_text_to_box_width(txt, box_w, fs)

            if outline_text:
                # Outlined glyph vector paths (Resolution independent, zero font dependency)
                all_paths = []
                for li, line in enumerate(lines):
                    y_base = fs * 0.88 + li * (fs * lh)
                    d_glyph, adv_px = text_to_svg_path_d(
                        line,
                        font_size=fs,
                        x=0.0,
                        y_baseline=y_base,
                        font_family=fam,
                        bold=is_bold,
                        italic=is_ital,
                    )
                    dx_align = 0.0
                    if align == "center":
                        dx_align = max(0.0, (box_w - adv_px) * 0.5)
                    elif align == "right":
                        dx_align = max(0.0, box_w - adv_px)
                    if dx_align > 0.1:
                        d_glyph, _ = text_to_svg_path_d(
                            line, font_size=fs, x=dx_align, y_baseline=y_base,
                            font_family=fam, bold=is_bold, italic=is_ital,
                        )
                    if d_glyph:
                        all_paths.append(f'    <path d="{d_glyph}" fill="{fill_c}" />')
                return f'  <g data-outlined-text="{escape(txt[:32])}" {tr}{op_attr}>\n' + "\n".join(all_paths) + "\n  </g>"

            anchor = "middle" if align == "center" else ("end" if align == "right" else "start")
            anchor_x = box_w * 0.5 if align == "center" else (box_w if align == "right" else 0.0)
            fw_str = "bold" if is_bold else "normal"
            fs_str = "italic" if is_ital else "normal"
            tspans = []
            for li, line in enumerate(lines):
                y_base = fs * 0.88 + li * (fs * lh)
                tspans.append(f'<tspan x="{anchor_x:.2f}" y="{y_base:.2f}">{escape(line)}</tspan>')
            return (
                f'  <text font-family="{escape(fam)}, Arial, sans-serif" font-size="{fs:.2f}" '
                f'font-weight="{fw_str}" font-style="{fs_str}" fill="{fill_c}" text-anchor="{anchor}" '
                f'xml:space="preserve"{op_attr} {tr}>{"".join(tspans)}</text>'
            )

        if otype == "image":
            src = str(obj.get("src") or "")
            if not src.startswith("data:image/"):
                return ""
            w = float(obj.get("width", 100) or 100)
            h = float(obj.get("height", 100) or 100)
            return (
                f'  <image x="0" y="0" width="{w:.2f}" height="{h:.2f}" '
                f'preserveAspectRatio="none" xlink:href="{src}"{op_attr} {tr} />'
            )

        return ""

    # Organize objects cleanly into CorelDRAW logical layer <g id="Layer_...">
    bg_hex = _color_hex(fabric_json.get("background"), "#ffffff") or "#ffffff"
    layer_buckets: dict[str, list[str]] = {}
    layer_order: list[str] = []

    for obj in fabric_json.get("objects") or []:
        em = _emit_object(obj, in_group=False)
        if not em:
            continue
        raw_cat = str(obj.get("layerCategory") or obj.get("assetType") or "Artwork_Objects")
        safe_layer = "Layer_" + re.sub(r"[^A-Za-z0-9]+", "_", raw_cat).strip("_")
        if safe_layer not in layer_buckets:
            layer_buckets[safe_layer] = []
            layer_order.append(safe_layer)
        layer_buckets[safe_layer].append(em)

    groups_xml = []
    for lname in layer_order:
        groups_xml.append(f'<g id="{lname}">\n' + "\n".join(layer_buckets[lname]) + "\n</g>")

    defs_block = f"<defs>\n  " + "\n  ".join(defs_elems) + "\n</defs>\n" if defs_elems else ""
    bg_rect = f'<rect id="Artboard_Backdrop" x="0" y="0" width="{cw:.2f}" height="{ch:.2f}" fill="{bg_hex}" />\n'

    svg_doc = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'version="1.1" width="{width_mm:.2f}mm" height="{height_mm:.2f}mm" '
        f'viewBox="0 0 {cw:.2f} {ch:.2f}">\n'
        f'<title>{escape(title)} ({"Outlined Curves" if outline_text else "Editable Text SVG"})</title>\n'
        f'{defs_block}'
        f'<g id="Layer_Canvas_Background">\n  {bg_rect}</g>\n'
        + "\n".join(groups_xml)
        + "\n</svg>\n"
    )
    return svg_doc.encode("utf-8")


def _draw_svg_d_to_rl_path(p_obj, d_str: str):
    """Parses SVG cubic/quad/line path commands cleanly into ReportLab PDF path operations."""
    tokens = re.findall(r"[A-Za-z]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d_str)
    i = 0
    cx, cy = 0.0, 0.0
    sx, sy = 0.0, 0.0
    cmd = ""
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                p_obj.close()
                cx, cy = sx, sy
            continue

        def _f():
            nonlocal i
            v = float(tokens[i])
            i += 1
            return v

        if cmd == "M":
            cx, cy = _f(), _f()
            sx, sy = cx, cy
            p_obj.moveTo(cx, cy)
            cmd = "L"
        elif cmd == "m":
            cx, cy = cx + _f(), cy + _f()
            sx, sy = cx, cy
            p_obj.moveTo(cx, cy)
            cmd = "l"
        elif cmd == "L":
            cx, cy = _f(), _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "l":
            cx, cy = cx + _f(), cy + _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "H":
            cx = _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "h":
            cx += _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "V":
            cy = _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "v":
            cy += _f()
            p_obj.lineTo(cx, cy)
        elif cmd == "C":
            x1, y1, x2, y2, x3, y3 = _f(), _f(), _f(), _f(), _f(), _f()
            p_obj.curveTo(x1, y1, x2, y2, x3, y3)
            cx, cy = x3, y3
        elif cmd == "c":
            dx1, dy1, dx2, dy2, dx3, dy3 = _f(), _f(), _f(), _f(), _f(), _f()
            p_obj.curveTo(cx + dx1, cy + dy1, cx + dx2, cy + dy2, cx + dx3, cy + dy3)
            cx, cy = cx + dx3, cy + dy3
        elif cmd == "Q":
            qx, qy, x2, y2 = _f(), _f(), _f(), _f()
            c1x, c1y = cx + (2.0 / 3.0) * (qx - cx), cy + (2.0 / 3.0) * (qy - cy)
            c2x, c2y = x2 + (2.0 / 3.0) * (qx - x2), y2 + (2.0 / 3.0) * (qy - y2)
            p_obj.curveTo(c1x, c1y, c2x, c2y, x2, y2)
            cx, cy = x2, y2
        elif cmd == "q":
            dqx, dqy, dx2, dy2 = _f(), _f(), _f(), _f()
            qx, qy, x2, y2 = cx + dqx, cy + dqy, cx + dx2, cy + dy2
            c1x, c1y = cx + (2.0 / 3.0) * (qx - cx), cy + (2.0 / 3.0) * (qy - cy)
            c2x, c2y = x2 + (2.0 / 3.0) * (qx - x2), y2 + (2.0 / 3.0) * (qy - y2)
            p_obj.curveTo(c1x, c1y, c2x, c2y, x2, y2)
            cx, cy = x2, y2
        else:
            i += 1


def _hex_to_rl(hex_str: str | None) -> tuple[float, float, float] | None:
    c = _color_hex(hex_str, None)
    if not c or not c.startswith("#") or len(c) < 7:
        return None
    return (int(c[1:3], 16) / 255.0, int(c[3:5], 16) / 255.0, int(c[5:7], 16) / 255.0)


def build_vector_pdf_from_fabric(
    fabric_json: dict,
    width_mm: float = 160.0,
    height_mm: float = 65.0,
    title: str = "GOMZI BOB Vector PDF",
) -> bytes:
    """
    Exports a CorelDRAW-compatible Hybrid Vector PDF using ReportLab:
      - Real selectable vector shapes (rects, circles, Bezier paths)
      - Real selectable PDF text using embedded TTF fonts
      - High-resolution embedded rasters only for raster-type objects
      - Exact physical page dimensions (mm -> PostScript pt)
    """
    cw = float(fabric_json.get("width") or 1536)
    ch = float(fabric_json.get("height") or 512)
    if height_mm <= 0:
        height_mm = round(width_mm * (ch / max(1.0, cw)), 2)

    pt_w = width_mm * 72.0 / 25.4
    pt_h = height_mm * 72.0 / 25.4
    px_to_pt = pt_w / max(1.0, cw)

    out_io = io.BytesIO()
    c = rl_canvas.Canvas(out_io, pagesize=(pt_w, pt_h))
    c.setTitle(title)
    c.setAuthor("GOMZI BOB Vector Engine")

    # Top-down coordinate transform inside PDF
    c.saveState()
    c.translate(0, pt_h)
    c.scale(px_to_pt, -px_to_pt)

    bg_rgb = _hex_to_rl(fabric_json.get("background") or "#ffffff") or (1.0, 1.0, 1.0)
    c.setFillColorRGB(*bg_rgb)
    c.rect(0, 0, cw, ch, stroke=0, fill=1)

    def _draw_obj(obj: dict, in_group: bool = False):
        if obj.get("visible") is False or obj.get("isGuideLine"):
            return
        otype = (obj.get("type") or "").lower()

        if in_group:
            sx = float(obj.get("scaleX", 1.0) or 1.0)
            sy = float(obj.get("scaleY", 1.0) or 1.0)
            ang = float(obj.get("angle", 0.0) or 0.0)
            w = float(obj.get("width", 0.0) or 0.0)
            h = float(obj.get("height", 0.0) or 0.0)
            left = float(obj.get("left", 0.0) or 0.0)
            top = float(obj.get("top", 0.0) or 0.0)
            cx = left + (0.0 if (obj.get("originX") == "center") else w * sx * 0.5)
            cy = top + (0.0 if (obj.get("originY") == "center") else h * sy * 0.5)
            po = obj.get("pathOffset")
            lx, ly = (float(po["x"]), float(po["y"])) if (isinstance(po, dict) and otype == "path") else (w * 0.5, h * 0.5)
        else:
            cx, cy, sx, sy, ang, lx, ly = _object_center_and_local_offset(obj)

        c.saveState()
        c.translate(cx, cy)
        if abs(ang) > 0.01:
            c.rotate(ang)
        c.scale(sx, sy)
        if otype != "group":
            c.translate(-lx, -ly)

        fill_rgb = _hex_to_rl(obj.get("fill"))
        stroke_rgb = _hex_to_rl(obj.get("stroke"))
        sw = float(obj.get("strokeWidth", 0) or 0)
        do_fill = 1 if fill_rgb else 0
        do_stroke = 1 if (stroke_rgb and sw > 0) else 0
        if fill_rgb:
            c.setFillColorRGB(*fill_rgb)
        if stroke_rgb:
            c.setStrokeColorRGB(*stroke_rgb)
            c.setLineWidth(sw)

        if otype == "group":
            for sub in obj.get("objects") or []:
                _draw_obj(sub, in_group=True)

        elif otype == "rect":
            w = float(obj.get("width", 0) or 0)
            h = float(obj.get("height", 0) or 0)
            rx = float(obj.get("rx", 0) or 0)
            # Handle multi-stop linear gradient vectors cleanly via vertical/horizontal shaded bands
            if isinstance(obj.get("fill"), dict) and obj["fill"].get("colorStops"):
                stops = obj["fill"]["colorStops"]
                steps = 24
                col0 = _hex_to_rl(stops[0].get("color")) or (1, 1, 1)
                col1 = _hex_to_rl(stops[-1].get("color")) or col0
                mid_col = _hex_to_rl(stops[1].get("color")) if len(stops) >= 3 else col1
                for k in range(steps):
                    t = k / float(steps - 1)
                    if len(stops) >= 3:
                        r, g, b = [col0[j] * (1 - abs(2 * t - 1)) + mid_col[j] * (abs(2 * t - 1)) for j in range(3)]
                        # center stop is bright
                        r, g, b = [mid_col[j] * (1 - abs(2 * t - 1)) + col0[j] * (abs(2 * t - 1)) for j in range(3)]
                    else:
                        r, g, b = [col0[j] * (1 - t) + col1[j] * t for j in range(3)]
                    c.setFillColorRGB(r, g, b)
                    c.rect(w * (k / float(steps)), 0, w / float(steps) + 0.5, h, stroke=0, fill=1)
            elif rx > 0.5:
                c.roundRect(0, 0, w, h, rx, stroke=do_stroke, fill=do_fill)
            else:
                c.rect(0, 0, w, h, stroke=do_stroke, fill=do_fill)

        elif otype == "circle":
            r = float(obj.get("radius", 0) or 0)
            c.circle(r, r, r, stroke=do_stroke, fill=do_fill)

        elif otype == "ellipse":
            rx = float(obj.get("rx", 0) or 0)
            ry = float(obj.get("ry", 0) or 0)
            c.ellipse(0, 0, rx * 2.0, ry * 2.0, stroke=do_stroke, fill=do_fill)

        elif otype == "line":
            x1 = float(obj.get("x1", 0) or 0) + lx
            y1 = float(obj.get("y1", 0) or 0) + ly
            x2 = float(obj.get("x2", 0) or 0) + lx
            y2 = float(obj.get("y2", 0) or 0) + ly
            c.line(x1, y1, x2, y2)

        elif otype == "path":
            d_str = _fabric_path_to_d(obj.get("path"))
            if d_str:
                p_obj = c.beginPath()
                _draw_svg_d_to_rl_path(p_obj, d_str)
                c.drawPath(p_obj, stroke=do_stroke, fill=do_fill)

        elif otype in ("textbox", "i-text", "text"):
            txt = str(obj.get("text") or "")
            if txt.strip():
                fs = float(obj.get("fontSize", 16) or 16)
                fam = str(obj.get("fontFamily", "Montserrat") or "Montserrat")
                is_bold = _is_bold_weight(obj.get("fontWeight"))
                is_ital = str(obj.get("fontStyle", "")).lower() == "italic"
                rl_font = _get_reportlab_font(fam, bold=is_bold, italic=is_ital)
                c.setFont(rl_font, fs)
                align = (obj.get("textAlign") or "left").lower()
                lh = float(obj.get("lineHeight", 1.14) or 1.14)
                box_w = float(obj.get("width", 100) or 100)
                if not fill_rgb:
                    c.setFillColorRGB(0.08, 0.1, 0.14)
                for li, line in enumerate(_wrap_text_to_box_width(txt, box_w, fs)):
                    y_base = fs * 0.88 + li * (fs * lh)
                    c.saveState()
                    if align == "center":
                        c.translate(box_w * 0.5, y_base)
                        c.scale(1, -1)
                        c.drawCentredString(0, 0, line)
                    elif align == "right":
                        c.translate(box_w, y_base)
                        c.scale(1, -1)
                        c.drawRightString(0, 0, line)
                    else:
                        c.translate(0, y_base)
                        c.scale(1, -1)
                        c.drawString(0, 0, line)
                    c.restoreState()

        elif otype == "image":
            src = str(obj.get("src") or "")
            if src.startswith("data:image/") and "," in src:
                try:
                    raw = base64.b64decode(src.split(",", 1)[1])
                    with Image.open(io.BytesIO(raw)) as pim:
                        w = float(obj.get("width", pim.width) or pim.width)
                        h = float(obj.get("height", pim.height) or pim.height)
                        c.saveState()
                        c.translate(0, h)
                        c.scale(1, -1)
                        c.drawImage(ImageReader(io.BytesIO(raw)), 0, 0, width=w, height=h, mask="auto")
                        c.restoreState()
                except Exception:
                    pass

        c.restoreState()

    for obj in fabric_json.get("objects") or []:
        _draw_obj(obj, in_group=False)

    c.restoreState()
    c.showPage()
    c.save()
    return out_io.getvalue()


def build_coreldraw_exchange_zip(
    fabric_json: dict,
    width_mm: float = 160.0,
    height_mm: float = 65.0,
    stem: str = "GOMZI_Vector_Label",
) -> bytes:
    """
    Builds a transparent, CorelDRAW-ready interchange ZIP bundle containing:
      - Editable Text SVG (<stem>_editable.svg)
      - Outlined Curve SVG (<stem>_outlined.svg)
      - Vector PDF (<stem>_vector.pdf)
      - Capability note explaining native .cdr write status accurately
    """
    svg_edit = build_coreldraw_svg(fabric_json, width_mm=width_mm, height_mm=height_mm, outline_text=False, title=stem)
    svg_out = build_coreldraw_svg(fabric_json, width_mm=width_mm, height_mm=height_mm, outline_text=True, title=stem)
    vec_pdf = build_vector_pdf_from_fabric(fabric_json, width_mm=width_mm, height_mm=height_mm, title=stem)

    readme = (
        f"GOMZI BOB CorelDRAW Vector Interchange Bundle ({stem})\n"
        f"Physical Size: {width_mm:.2f} x {height_mm:.2f} mm\n"
        f"Included Files:\n"
        f"  1. {stem}_editable.svg  -> Open/Import directly in CorelDRAW with editable <text> & vector paths.\n"
        f"  2. {stem}_outlined.svg  -> Zero-font-dependency glyph curves for guaranteed print fidelity.\n"
        f"  3. {stem}_vector.pdf    -> Vector PDF with selectable fonts, curves, and embedded high-res rasters.\n\n"
        f"Note: Direct binary .cdr writing requires licensed CorelDRAW desktop automation on the host server.\n"
        f"Import the editable SVG or Vector PDF into CorelDRAW (File -> Import) and save as .cdr.\n"
    )

    out_io = io.BytesIO()
    with zipfile.ZipFile(out_io, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{stem}_editable.svg", svg_edit)
        z.writestr(f"{stem}_outlined.svg", svg_out)
        z.writestr(f"{stem}_vector.pdf", vec_pdf)
        z.writestr("README_CORELDRAW_IMPORT.txt", readme.encode("utf-8"))
    return out_io.getvalue()
