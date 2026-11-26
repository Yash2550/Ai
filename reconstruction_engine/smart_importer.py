"""
Smart Format-Specific Design Importer (SVG, Native PDF, PDF-Compatible AI, CDR, EPS, Raster).
Preserves native vectors and editable text whenever available; delegates flattened rasters
only when native editable primitives are absent.
"""

import io
import os
import re
import math
import base64
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import cv2
from PIL import Image

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from .security_validator import sanitize_svg_strict
from .capability_probe import probe_system_capabilities


def detect_file_type_strict(file_bytes: bytes, filename: str = "") -> str:
    """Identifies actual file type using magic bytes rather than trusting extensions alone."""
    if len(file_bytes) < 8:
        return "unknown"
    header = file_bytes[:16]
    lower_name = (filename or "").lower()

    if header[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                names = z.namelist()
                if any("content/" in n or "metadata/metadata.xml" in n or "previews/" in n for n in names):
                    return "cdr"
        except Exception:
            pass
        return "cdr" if lower_name.endswith(".cdr") else "zip"

    if header[:4] == b"RIFF" and b"CDR" in file_bytes[:16]:
        return "cdr_legacy"

    if header[:5] == b"%PDF-":
        return "ai" if lower_name.endswith(".ai") else "pdf"

    if header[:4] == b"\xc5\xd0\xd3\xc6" or header[:4] == b"%!PS":
        return "eps" if lower_name.endswith(".eps") else "postscript"

    stripped = file_bytes[:1024].lstrip()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<svg") or b"<svg" in stripped.lower():
        return "svg"

    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:2] == b"\xff\xd8":
        return "jpg"
    if header[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "webp"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"

    try:
        dec = file_bytes[:200].decode("utf-8", errors="ignore").strip()
        if dec.startswith("{") and ("objects" in dec or "version" in dec):
            return "project_json"
    except Exception:
        pass

    ext = os.path.splitext(lower_name)[1].lstrip(".")
    return ext if ext in ("cdr", "svg", "pdf", "ai", "eps", "png", "jpg", "jpeg", "webp") else "unknown"


def _parse_len_mm(val: str, default_mm: float = 150.0, px_dpi: float = 96.0) -> float:
    if not val:
        return default_mm
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([a-z%]*)\s*$", str(val), re.IGNORECASE)
    if not m:
        return default_mm
    num = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "mm":
        return num
    if unit == "cm":
        return num * 10.0
    if unit == "in":
        return num * 25.4
    if unit == "pt":
        return num * 25.4 / 72.0
    if unit in ("", "px"):
        return num * 25.4 / px_dpi
    return default_mm


def _parse_svg_transform(tr_str: str) -> tuple[float, float, float, float, float, float]:
    """Parses basic SVG translate/scale/matrix transforms into affine (a,b,c,d,e,f)."""
    a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    if not tr_str:
        return a, b, c, d, e, f
    for kind, args_s in re.findall(r"(translate|scale|matrix)\s*\(([^)]+)\)", tr_str, re.IGNORECASE):
        nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", args_s)]
        k = kind.lower()
        if k == "translate" and len(nums) >= 1:
            e += nums[0] * a
            f += (nums[1] if len(nums) > 1 else 0.0) * d
        elif k == "scale" and len(nums) >= 1:
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            a *= sx
            d *= sy
        elif k == "matrix" and len(nums) == 6:
            na, nb, nc, nd, ne, nf = nums
            a, b, c, d, e, f = na, nb, nc, nd, ne, nf
    return a, b, c, d, e, f


def _mul_affine(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_pt(m, x, y):
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _parse_style_dict(elem) -> dict:
    st = {}
    raw = elem.attrib.get("style", "")
    for part in raw.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            st[k.strip().lower()] = v.strip()
    for k in ("fill", "stroke", "stroke-width", "opacity", "fill-opacity", "font-family", "font-size", "font-weight", "font-style", "text-anchor"):
        if k in elem.attrib:
            st[k] = elem.attrib[k]
    return st


def _resolve_color(val: str | None, gradients: dict, default_col: str | None = None):
    if not val:
        return default_col
    v = val.strip()
    if v.lower() == "none":
        return None
    if v.startswith("url(#"):
        gid = v[5:].rstrip(")")
        g = gradients.get(gid)
        if g:
            return g
        return default_col or "#74883D"
    return v


def _svg_points_to_path(pts_str: str, closed: bool) -> str:
    nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+", pts_str or "")]
    if len(nums) < 4:
        return ""
    segs = [f"M {nums[0]:.2f} {nums[1]:.2f}"]
    for i in range(2, len(nums) - 1, 2):
        segs.append(f"L {nums[i]:.2f} {nums[i+1]:.2f}")
    if closed:
        segs.append("Z")
    return " ".join(segs)


def import_native_svg(file_bytes: bytes, filename: str = "artwork.svg") -> dict:
    """
    Imports SVG natively into editable Fabric.js JSON layers without flattening vectors
    into a bitmap. Preserves paths, geometric shapes, gradients, text, groups, and embedded rasters.
    """
    if file_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        raw_svg = file_bytes.decode("utf-16", errors="ignore")
    else:
        raw_svg = file_bytes.decode("utf-8-sig", errors="ignore")
    raw_svg = raw_svg.lstrip("\ufeff\ufffe \t\r\n")
    first_lt = raw_svg.find("<")
    if first_lt > 0:
        raw_svg = raw_svg[first_lt:]
    clean_svg, warnings = sanitize_svg_strict(raw_svg)
    clean_svg = clean_svg.lstrip("\ufeff\ufffe \t\r\n")
    root = ET.fromstring(clean_svg.encode("utf-8", errors="ignore"))

    vb_str = root.attrib.get("viewBox", "")
    vb_nums = [float(x) for x in re.findall(r"[-+]?[0-9]*\.?[0-9]+", vb_str)]
    if len(vb_nums) == 4 and vb_nums[2] > 0 and vb_nums[3] > 0:
        vx, vy, vw, vh = vb_nums
    else:
        vx, vy = 0.0, 0.0
        vw = float(re.findall(r"[0-9]+(?:\.[0-9]+)?", root.attrib.get("width", "1000"))[0])
        vh = float(re.findall(r"[0-9]+(?:\.[0-9]+)?", root.attrib.get("height", "500"))[0])

    width_mm = round(_parse_len_mm(root.attrib.get("width", ""), vw * 25.4 / 96.0), 2)
    height_mm = round(_parse_len_mm(root.attrib.get("height", ""), vh * 25.4 / 96.0), 2)

    target_w = 1536
    scale = target_w / max(1.0, vw)
    target_h = max(120, int(round(vh * scale)))

    def _lname(t):
        return t.split("}", 1)[-1].lower() if "}" in t else t.lower()

    # Collect gradients in <defs>
    gradients = {}
    for elem in root.iter():
        ln = _lname(elem.tag)
        if ln in ("lineargradient", "radialgradient") and elem.attrib.get("id"):
            gid = elem.attrib["id"]
            stops = []
            for st in elem:
                if _lname(st.tag) == "stop":
                    st_style = _parse_style_dict(st)
                    off_raw = st.attrib.get("offset", "0").strip()
                    off = float(off_raw.rstrip("%")) / (100.0 if "%" in off_raw else 1.0)
                    col = st_style.get("stop-color") or st.attrib.get("stop-color") or "#74883D"
                    stops.append({"offset": max(0.0, min(1.0, off)), "color": col})
            if stops:
                gradients[gid] = stops[0]["color"]  # fallback solid color if Fabric gradient coords ambiguous
                if len(stops) >= 2:
                    gradients[gid] = {
                        "type": "linear" if ln == "lineargradient" else "radial",
                        "coords": {"x1": 0, "y1": 0, "x2": 1, "y2": 0},
                        "gradientUnits": "percentage",
                        "colorStops": stops,
                    }
        elif ln in ("filter", "pattern"):
            warnings.append(f"SVG <{ln}> effect approximated or skipped for CorelDRAW interchange")

    objects = []
    stats = {"text": 0, "vectors": 0, "rasters": 0}

    def _walk(node, parent_m, group_label="Imported Layer"):
        ln = _lname(node.tag)
        if ln in ("defs", "title", "desc", "metadata"):
            return
        local_m = _parse_svg_transform(node.attrib.get("transform", ""))
        cur_m = _mul_affine(parent_m, local_m)
        st = _parse_style_dict(node)
        name_hint = node.attrib.get("id") or node.attrib.get("inkscape:label") or group_label

        if ln == "g":
            for ch in node:
                _walk(ch, cur_m, node.attrib.get("id") or group_label)
            return

        if ln == "rect":
            x = float(node.attrib.get("x", 0)) - vx
            y = float(node.attrib.get("y", 0)) - vy
            rw = float(node.attrib.get("width", 0))
            rh = float(node.attrib.get("height", 0))
            if rw <= 0 or rh <= 0:
                return
            px, py = _apply_pt(cur_m, x, y)
            sx = math.hypot(cur_m[0], cur_m[1])
            sy = math.hypot(cur_m[2], cur_m[3])
            rx = float(node.attrib.get("rx", node.attrib.get("ry", 0))) * sx * scale
            sw_px = float(re.findall(r"[0-9.]+", st.get("stroke-width", "0"))[0]) * sx * scale if st.get("stroke") and st.get("stroke") != "none" else 0
            objects.append({
                "type": "rect",
                "left": round(px * scale, 2),
                "top": round(py * scale, 2),
                "width": round(rw * sx * scale, 2),
                "height": round(rh * sy * scale, 2),
                "rx": round(rx, 2),
                "ry": round(rx, 2),
                "fill": _resolve_color(st.get("fill"), gradients, "#000000"),
                "stroke": _resolve_color(st.get("stroke"), gradients, None),
                "strokeWidth": round(sw_px, 2),
                "opacity": float(st.get("opacity", 1.0)),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": group_label,
                "name": name_hint if name_hint != group_label else f"Vector Rect ({group_label})",
            })
            stats["vectors"] += 1

        elif ln in ("circle", "ellipse"):
            cx = float(node.attrib.get("cx", 0)) - vx
            cy = float(node.attrib.get("cy", 0)) - vy
            rx = float(node.attrib.get("r", node.attrib.get("rx", 0)))
            ry = float(node.attrib.get("r", node.attrib.get("ry", rx)))
            if rx <= 0 or ry <= 0:
                return
            px, py = _apply_pt(cur_m, cx - rx, cy - ry)
            sx = math.hypot(cur_m[0], cur_m[1])
            sy = math.hypot(cur_m[2], cur_m[3])
            sw_px = float(re.findall(r"[0-9.]+", st.get("stroke-width", "0"))[0]) * sx * scale if st.get("stroke") and st.get("stroke") != "none" else 0
            objects.append({
                "type": "ellipse",
                "left": round(px * scale, 2),
                "top": round(py * scale, 2),
                "rx": round(rx * sx * scale, 2),
                "ry": round(ry * sy * scale, 2),
                "fill": _resolve_color(st.get("fill"), gradients, "#000000"),
                "stroke": _resolve_color(st.get("stroke"), gradients, None),
                "strokeWidth": round(sw_px, 2),
                "opacity": float(st.get("opacity", 1.0)),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": group_label,
                "name": name_hint if name_hint != group_label else f"Vector Ellipse ({group_label})",
            })
            stats["vectors"] += 1

        elif ln == "line":
            x1, y1 = _apply_pt(cur_m, float(node.attrib.get("x1", 0)) - vx, float(node.attrib.get("y1", 0)) - vy)
            x2, y2 = _apply_pt(cur_m, float(node.attrib.get("x2", 0)) - vx, float(node.attrib.get("y2", 0)) - vy)
            sx = math.hypot(cur_m[0], cur_m[1])
            sw_px = max(1.0, float(re.findall(r"[0-9.]+", st.get("stroke-width", "1"))[0]) * sx * scale)
            objects.append({
                "type": "path",
                "path": [["M", round(x1 * scale, 2), round(y1 * scale, 2)], ["L", round(x2 * scale, 2), round(y2 * scale, 2)]],
                "fill": None,
                "stroke": _resolve_color(st.get("stroke"), gradients, "#1e293b"),
                "strokeWidth": round(sw_px, 2),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": group_label,
                "name": f"Vector Line ({group_label})",
            })
            stats["vectors"] += 1

        elif ln in ("path", "polygon", "polyline"):
            d_str = node.attrib.get("d", "") if ln == "path" else _svg_points_to_path(node.attrib.get("points", ""), closed=(ln == "polygon"))
            if not d_str.strip():
                return
            sx = math.hypot(cur_m[0], cur_m[1]) * scale
            sy = math.hypot(cur_m[2], cur_m[3]) * scale
            # Preserve exact vector path via Fabric raw svg path descriptor
            objects.append({
                "type": "svg_path_raw",
                "svg_d": d_str,
                "offsetX": round((cur_m[4] - vx * cur_m[0]) * scale, 2),
                "offsetY": round((cur_m[5] - vy * cur_m[3]) * scale, 2),
                "scaleX": round(sx, 4),
                "scaleY": round(sy, 4),
                "fill": _resolve_color(st.get("fill"), gradients, "#000000"),
                "stroke": _resolve_color(st.get("stroke"), gradients, None),
                "strokeWidth": round(float(re.findall(r"[0-9.]+", st.get("stroke-width", "0"))[0]) * sx, 2) if st.get("stroke") and st.get("stroke") != "none" else 0,
                "opacity": float(st.get("opacity", 1.0)),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": group_label,
                "name": name_hint if name_hint != group_label else f"Vector Path ({group_label})",
            })
            stats["vectors"] += 1

        elif ln == "text":
            tx = float(re.findall(r"[-+]?[0-9.]+", node.attrib.get("x", "0"))[0]) - vx
            ty = float(re.findall(r"[-+]?[0-9.]+", node.attrib.get("y", "0"))[0]) - vy
            px, py = _apply_pt(cur_m, tx, ty)
            sy = math.hypot(cur_m[2], cur_m[3])
            fs_raw = float(re.findall(r"[0-9.]+", st.get("font-size", "16"))[0]) * sy * scale
            text_pieces = []
            if node.text and node.text.strip():
                text_pieces.append(node.text.strip())
            for ts in node:
                if _lname(ts.tag) == "tspan" and ts.text and ts.text.strip():
                    text_pieces.append(ts.text.strip())
            txt_full = "\n".join(text_pieces).strip()
            if not txt_full:
                return
            anchor = (st.get("text-anchor") or "start").lower()
            align = "center" if anchor == "middle" else ("right" if anchor == "end" else "left")
            est_w = max(80.0, fs_raw * 0.62 * max(len(l) for l in txt_full.splitlines()) * 1.08)
            adj_left = px * scale - (est_w * 0.5 if align == "center" else (est_w if align == "right" else 0.0))
            objects.append({
                "type": "textbox",
                "text": txt_full,
                "left": round(max(0.0, adj_left), 2),
                "top": round(max(0.0, py * scale - fs_raw * 0.9), 2),
                "width": round(est_w, 2),
                "fontSize": max(10, int(round(fs_raw))),
                "fontFamily": (st.get("font-family", "Montserrat").split(",")[0].strip().strip("'\"")) or "Montserrat",
                "fontWeight": st.get("font-weight", "normal"),
                "fontStyle": st.get("font-style", "normal"),
                "fill": _resolve_color(st.get("fill"), gradients, "#111827") if isinstance(_resolve_color(st.get("fill"), gradients, "#111827"), str) else "#111827",
                "textAlign": align,
                "editable": True,
                "isImportedText": True,
                "assetType": "editable_text",
                "layerCategory": group_label,
                "name": f"SVG Text: {txt_full[:24]}",
            })
            stats["text"] += 1

        elif ln == "image":
            href = node.attrib.get("{http://www.w3.org/1999/xlink}href") or node.attrib.get("href") or ""
            if href.startswith("data:image/"):
                ix, iy = _apply_pt(cur_m, float(node.attrib.get("x", 0)) - vx, float(node.attrib.get("y", 0)) - vy)
                sx = math.hypot(cur_m[0], cur_m[1]) * scale
                sy = math.hypot(cur_m[2], cur_m[3]) * scale
                iw = float(node.attrib.get("width", 100)) * sx
                ih = float(node.attrib.get("height", 100)) * sy
                objects.append({
                    "type": "image",
                    "src": href,
                    "left": round(ix * scale, 2),
                    "top": round(iy * scale, 2),
                    "width": round(iw, 2),
                    "height": round(ih, 2),
                    "selectable": True,
                    "assetType": "retained_raster",
                    "layerCategory": "Retained Raster Assets",
                    "name": f"Embedded Raster ({group_label})",
                })
                stats["rasters"] += 1

        for ch in node:
            if ln == "svg":
                _walk(ch, cur_m, ch.attrib.get("id") or "SVG Layer")

    _walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), "SVG Root")

    needs_recon = (stats["text"] == 0 and stats["vectors"] == 0 and stats["rasters"] > 0)
    raster_fallback_bytes = None
    if needs_recon and stats["rasters"] == 1:
        for obj in objects:
            if obj.get("type") == "image" and isinstance(obj.get("src"), str) and "," in obj["src"]:
                try:
                    raw_r = base64.b64decode(obj["src"].split(",", 1)[1])
                    with Image.open(io.BytesIO(raw_r)) as pim:
                        out_io = io.BytesIO()
                        pim.convert("RGB").save(out_io, format="PNG")
                        raster_fallback_bytes = out_io.getvalue()
                except Exception:
                    raster_fallback_bytes = None
                break

    return {
        "success": True,
        "format": "svg",
        "filename": filename,
        "svg_content": clean_svg,
        "native_vector_mode": not needs_recon,
        "needs_hybrid_reconstruction": needs_recon,
        "raster_fallback_bytes": raster_fallback_bytes,
        "dimensions_mm": {"width": width_mm, "height": height_mm},
        "canvas_width": target_w,
        "canvas_height": target_h,
        "raw_objects": objects,
        "stats": {
            "total_objects": len(objects),
            "text_objects": stats["text"],
            "vector_objects": stats["vectors"],
            "image_objects": stats["rasters"],
            "format_type": "Raster-Wrapped SVG Container" if needs_recon else "Native SVG Vector Document",
        },
        "warnings": list(dict.fromkeys(warnings)),
    }


def _fitz_color_to_hex(col_val) -> str | None:
    if col_val is None:
        return None
    if isinstance(col_val, int):
        r = (col_val >> 16) & 255
        g = (col_val >> 8) & 255
        b = col_val & 255
        return f"#{r:02x}{g:02x}{b:02x}"
    if isinstance(col_val, (tuple, list)) and len(col_val) >= 3:
        r = int(round(max(0.0, min(1.0, float(col_val[0]))) * 255))
        g = int(round(max(0.0, min(1.0, float(col_val[1]))) * 255))
        b = int(round(max(0.0, min(1.0, float(col_val[2]))) * 255))
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def import_native_pdf_or_ai(file_bytes: bytes, filename: str = "artwork.pdf", fmt: str = "pdf") -> dict:
    """
    Imports PDF / PDF-compatible .ai via PyMuPDF without rasterizing vector pages prematurely.
    Extracts exact page dimensions (mm), native vector drawings, native text spans, and embedded rasters.
    Delegates flattened/scanned pages automatically to the Hybrid AI Reconstruction Engine.
    """
    if not HAS_PYMUPDF:
        return {
            "success": False,
            "error": "PyMuPDF (fitz) is not installed for PDF parsing",
            "needs_hybrid_reconstruction": True,
        }

    warnings = []
    if fmt == "ai":
        warnings.append("Adobe Illustrator (.ai) imported via PDF-compatible stream; proprietary AI live effects outside PDF stream may not be present.")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    if len(doc) == 0:
        raise ValueError("PDF/AI file has zero pages")
    if len(doc) > 1:
        warnings.append(f"Multi-page document ({len(doc)} pages); imported Page 1 artwork.")

    page = doc[0]
    w_pt, h_pt = float(page.rect.width), float(page.rect.height)
    width_mm = round(w_pt * 25.4 / 72.0, 2)
    height_mm = round(h_pt * 25.4 / 72.0, 2)

    target_w = 1536
    scale = target_w / max(1.0, w_pt)
    target_h = max(120, int(round(h_pt * scale)))

    # Reference bitmap for modal preview & SSIM comparison (NOT placed under vectors!)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    ref_png_bytes = pix.tobytes("png")
    preview_b64 = "data:image/png;base64," + base64.b64encode(ref_png_bytes).decode("ascii")

    objects = []
    vec_count = 0
    txt_count = 0
    img_count = 0

    # 1. Extract native vector drawings
    for drw in page.get_drawings():
        fill_hex = _fitz_color_to_hex(drw.get("fill"))
        stroke_hex = _fitz_color_to_hex(drw.get("color"))
        sw_pt = float(drw.get("width") or 0.0)
        if not fill_hex and not stroke_hex:
            continue
        d_cmds = []
        for it in drw.get("items", []):
            op = it[0]
            if op == "l":
                p1, p2 = it[1], it[2]
                d_cmds.append(f"M {p1.x*scale:.2f} {p1.y*scale:.2f} L {p2.x*scale:.2f} {p2.y*scale:.2f}")
            elif op == "c":
                p1, p2, p3, p4 = it[1], it[2], it[3], it[4]
                d_cmds.append(
                    f"M {p1.x*scale:.2f} {p1.y*scale:.2f} "
                    f"C {p2.x*scale:.2f} {p2.y*scale:.2f} {p3.x*scale:.2f} {p3.y*scale:.2f} {p4.x*scale:.2f} {p4.y*scale:.2f}"
                )
            elif op == "re":
                r = it[1]
                x, y, rw, rh = r.x0 * scale, r.y0 * scale, r.width * scale, r.height * scale
                if rw > 0.5 and rh > 0.5:
                    d_cmds.append(f"M {x:.2f} {y:.2f} L {x+rw:.2f} {y:.2f} L {x+rw:.2f} {y+rh:.2f} L {x:.2f} {y+rh:.2f} Z")
            elif op == "qu":
                q = it[1]
                d_cmds.append(
                    f"M {q.ul.x*scale:.2f} {q.ul.y*scale:.2f} L {q.ur.x*scale:.2f} {q.ur.y*scale:.2f} "
                    f"L {q.lr.x*scale:.2f} {q.lr.y*scale:.2f} L {q.ll.x*scale:.2f} {q.ll.y*scale:.2f} Z"
                )
        if d_cmds:
            if drw.get("closePath"):
                d_cmds.append("Z")
            objects.append({
                "type": "svg_path_raw",
                "svg_d": " ".join(d_cmds),
                "offsetX": 0.0,
                "offsetY": 0.0,
                "scaleX": 1.0,
                "scaleY": 1.0,
                "fill": fill_hex,
                "stroke": stroke_hex,
                "strokeWidth": round(sw_pt * scale, 2) if stroke_hex else 0,
                "opacity": float(drw.get("fill_opacity") or drw.get("stroke_opacity") or 1.0),
                "selectable": True,
                "assetType": "reconstructed_vector",
                "layerCategory": "Native PDF Vector Shapes",
                "name": f"PDF Vector {vec_count + 1}",
            })
            vec_count += 1

    # 2. Extract embedded raster images
    for img_info in page.get_image_info(xrefs=True):
        xref = img_info.get("xref")
        bbox = img_info.get("bbox")
        if not xref or not bbox:
            continue
        try:
            raw_img = doc.extract_image(xref)
            raw_bytes = raw_img.get("image")
            ext = raw_img.get("ext", "png")
            if raw_bytes:
                ix0, iy0, ix1, iy1 = [float(v) * scale for v in bbox]
                b64_uri = f"data:image/{ext};base64," + base64.b64encode(raw_bytes).decode("ascii")
                objects.append({
                    "type": "image",
                    "src": b64_uri,
                    "left": round(ix0, 2),
                    "top": round(iy0, 2),
                    "width": round(max(4.0, ix1 - ix0), 2),
                    "height": round(max(4.0, iy1 - iy0), 2),
                    "selectable": True,
                    "assetType": "retained_raster",
                    "layerCategory": "Retained Raster Assets",
                    "name": f"PDF Embedded Image {img_count + 1}",
                })
                img_count += 1
        except Exception:
            pass

    # 3. Extract native text spans
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            merged_text = "".join(s["text"] for s in spans).strip()
            if not merged_text:
                continue
            first = spans[0]
            bx0 = min(s["bbox"][0] for s in spans) * scale
            by0 = min(s["bbox"][1] for s in spans) * scale
            bx1 = max(s["bbox"][2] for s in spans) * scale
            by1 = max(s["bbox"][3] for s in spans) * scale
            font_name = first.get("font", "Montserrat")
            is_bold = ("bold" in font_name.lower()) or bool(first.get("flags", 0) & 16)
            is_italic = ("italic" in font_name.lower() or "oblique" in font_name.lower()) or bool(first.get("flags", 0) & 2)
            col_hex = _fitz_color_to_hex(first.get("color")) or "#111827"
            fs_px = max(10, int(round(float(first.get("size", 12.0)) * scale)))
            objects.append({
                "type": "textbox",
                "text": merged_text,
                "left": round(bx0, 2),
                "top": round(by0, 2),
                "width": round(max(60.0, (bx1 - bx0) * 1.12), 2),
                "fontSize": fs_px,
                "fontFamily": "Montserrat" if is_bold else "Inter",
                "originalPdfFont": font_name,
                "fontWeight": "700" if is_bold else "400",
                "fontStyle": "italic" if is_italic else "normal",
                "fill": col_hex,
                "textAlign": "left",
                "editable": True,
                "isImportedText": True,
                "assetType": "editable_text",
                "layerCategory": "Native PDF Text",
                "name": f"PDF Text: {merged_text[:24]}",
            })
            txt_count += 1

    is_flattened_raster_pdf = (txt_count == 0 and vec_count <= 2)
    if is_flattened_raster_pdf:
        warnings.append("PDF page contains flattened raster artwork with no native text objects; running Hybrid AI Reconstruction.")

    return {
        "success": True,
        "format": fmt,
        "filename": filename,
        "native_vector_mode": not is_flattened_raster_pdf,
        "needs_hybrid_reconstruction": is_flattened_raster_pdf,
        "raster_fallback_bytes": ref_png_bytes,
        "dimensions_mm": {"width": width_mm, "height": height_mm},
        "canvas_width": target_w,
        "canvas_height": target_h,
        "preview_url": preview_b64,
        "raw_objects": objects,
        "stats": {
            "total_objects": len(objects),
            "text_objects": txt_count,
            "vector_objects": vec_count,
            "image_objects": img_count,
            "format_type": "Native PDF Vector Document" if not is_flattened_raster_pdf else "Flattened Raster PDF",
        },
        "warnings": warnings,
    }


def extract_cdr_smart(file_bytes: bytes, filename: str = "design.cdr", fmt: str = "cdr") -> dict:
    """
    Truthfully handles CorelDRAW (.cdr) imports:
      - Inspects installed native converters (CorelDRAW / LibreOffice / Inkscape)
      - Extracts physical dimensions + embedded high-res preview from modern ZIP CDR
      - Reports honest limitations for proprietary binary RIFF CDR or absent converters
    """
    caps = probe_system_capabilities()
    warnings = []
    width_mm, height_mm = 160.0, 220.0
    preview_bytes = None

    if not caps["cdr_legacy_riff_converter"]:
        warnings.append(
            "Direct binary .cdr path converter (LibreOffice Draw / libcdr / licensed CorelDRAW) is not installed on this server; "
            "using CDR embedded page preview + Hybrid AI Vector Reconstruction where available."
        )

    if fmt == "cdr_legacy":
        # Legacy RIFF CDR binary lacks ZIP preview unless CorelDRAW/soffice is installed
        return {
            "success": False,
            "format": "cdr_legacy",
            "error": (
                "Legacy binary CorelDRAW (RIFF CDR) requires LibreOffice/libcdr or licensed CorelDRAW installed to decode binary curves. "
                "Please export as SVG or PDF from CorelDRAW, or save as CorelDRAW X6+ compressed format with preview."
            ),
            "warnings": warnings,
            "capabilities": caps,
        }

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            names = z.namelist()
            for candidate in (
                "previews/page1.png",
                "previews/thumbnail.png",
                "previews/page1.bmp",
                "previews/thumbnail.bmp",
                "previews/page1.jpg",
            ):
                if candidate in names:
                    preview_bytes = z.read(candidate)
                    break
            if not preview_bytes:
                for n in names:
                    if n.startswith("previews/") and n.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                        preview_bytes = z.read(n)
                        break

            # Normalize BMP/JPG preview to PNG bytes for OpenCV/PIL uniformity
            if preview_bytes:
                with Image.open(io.BytesIO(preview_bytes)) as pim:
                    out_io = io.BytesIO()
                    pim.convert("RGBA" if pim.mode in ("RGBA", "LA", "P") else "RGB").save(out_io, format="PNG")
                    preview_bytes = out_io.getvalue()

            if "metadata/metadata.xml" in names:
                meta_xml = z.read("metadata/metadata.xml").decode("utf-8", errors="ignore")
                root = ET.fromstring(meta_xml)
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if "width" in tag and elem.text:
                        try:
                            width_mm = float(elem.text.lower().replace("mm", "").strip())
                        except ValueError:
                            pass
                    elif "height" in tag and elem.text:
                        try:
                            height_mm = float(elem.text.lower().replace("mm", "").strip())
                        except ValueError:
                            pass
    except Exception as exc:
        warnings.append(f"CDR container inspection warning: {exc}")

    if not preview_bytes:
        return {
            "success": False,
            "format": "cdr",
            "error": "No embedded preview image found inside CorelDRAW .cdr archive and native libcdr/LibreOffice converter is not installed.",
            "warnings": warnings,
            "capabilities": caps,
        }

    return {
        "success": True,
        "format": "cdr",
        "filename": filename,
        "dimensions_mm": {"width": width_mm, "height": height_mm},
        "raster_fallback_bytes": preview_bytes,
        "needs_hybrid_reconstruction": True,
        "warnings": warnings,
    }
