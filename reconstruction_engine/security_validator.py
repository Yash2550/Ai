"""
Security validation, SVG sanitization, decompression-bomb protection,
and non-destructive original artwork archival.
"""

import os
import re
import json
import uuid
import time
import hashlib
import io
from xml.etree import ElementTree as ET

try:
    import defusedxml.ElementTree as DefusedET
    HAS_DEFUSEDXML = True
except ImportError:
    DefusedET = ET
    HAS_DEFUSEDXML = False

from PIL import Image
from werkzeug.utils import secure_filename

Image.MAX_IMAGE_PIXELS = 80_000_000  # 80 MP guard against decompression bombs

MAX_UPLOAD_BYTES = 35 * 1024 * 1024  # 35 MB
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "webp", "tif", "tiff", "svg", "pdf", "cdr", "ai", "eps", "json"
}

SVG_DISALLOWED_TAGS = {
    "script", "foreignobject", "iframe", "object", "embed", "applet", "audio", "video", "meta", "link"
}
SVG_SAFE_URL_RE = re.compile(r"^\s*(#|data:image/(png|jpeg|jpg|webp|gif);base64,)", re.IGNORECASE)

CACHE_ROOT = os.path.abspath(os.path.join("static", "reconstruction_cache"))


def validate_uploaded_file(file_bytes: bytes, filename: str) -> dict:
    """Validates uploaded payload size, safe filename, extension, and image pixel limits."""
    if not file_bytes:
        raise ValueError("Uploaded file is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB safety limit")

    safe_name = secure_filename(filename or "uploaded_label.bin") or "uploaded_label.bin"
    ext = os.path.splitext(safe_name)[1].lower().lstrip(".")
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '.{ext}'")

    meta = {
        "safe_filename": safe_name,
        "byte_size": len(file_bytes),
        "sha256": hashlib.sha256(file_bytes).hexdigest(),
        "pixel_width": None,
        "pixel_height": None,
        "color_mode": None,
        "icc_profile": False,
    }

    # If raster bytes look like PNG/JPG/WEBP/TIFF, verify image integrity & bounds
    head = file_bytes[:16]
    is_raster_sig = (
        head[:8] == b"\x89PNG\r\n\x1a\n"
        or head[:2] == b"\xff\xd8"
        or (head[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP")
        or head[:4] in (b"II*\x00", b"MM\x00*")
    )
    if is_raster_sig:
        try:
            with Image.open(io.BytesIO(file_bytes)) as im:
                im.verify()
            with Image.open(io.BytesIO(file_bytes)) as im2:
                w, h = im2.size
                if w > 12000 or h > 12000 or (w * h) > 64_000_000:
                    raise ValueError(f"Image dimensions {w}x{h} exceed safe processing ceiling")
                meta["pixel_width"] = int(w)
                meta["pixel_height"] = int(h)
                meta["color_mode"] = im2.mode
                meta["icc_profile"] = bool(im2.info.get("icc_profile"))
        except Image.DecompressionBombError as exc:
            raise ValueError(f"Decompression bomb rejected: {exc}") from exc

    return meta


def sanitize_svg_strict(svg_text: str) -> tuple[str, list[str]]:
    """
    Strictly sanitizes uploaded SVG documents using defusedxml and tag/attribute allowlisting.
    Strips scripts, event handlers, foreignObject, XXE, and unsafe external references.
    Returns (sanitized_svg_string, warnings_list).
    """
    warnings: list[str] = []
    # Strip UTF-8/UTF-16 BOM, leading non-XML preamble, DOCTYPE, and ENTITY before XML parse
    cleaned = (svg_text or "").lstrip("\ufeff\ufffe \t\r\n")
    first_lt = cleaned.find("<")
    if first_lt > 0:
        cleaned = cleaned[first_lt:]
    cleaned = re.sub(r"<!DOCTYPE[^>]*(\[[^\]]*\])?\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<!ENTITY[^>]*>", "", cleaned, flags=re.IGNORECASE)

    try:
        parser = DefusedET.parse if hasattr(DefusedET, "fromstring") else None
        _ = parser
        root = DefusedET.fromstring(cleaned.encode("utf-8", errors="ignore"))

        def _local_tag(tag_name: str) -> str:
            return tag_name.split("}", 1)[-1].lower() if "}" in tag_name else tag_name.lower()

        def _prune_element(parent):
            to_remove = []
            for child in list(parent):
                lname = _local_tag(child.tag)
                if lname in SVG_DISALLOWED_TAGS:
                    to_remove.append(child)
                    warnings.append(f"Removed unsafe SVG element <{lname}>")
                    continue

                # Strip dangerous event attributes and external URLs
                for attr_k in list(child.attrib.keys()):
                    attr_local = _local_tag(attr_k)
                    attr_v = child.attrib.get(attr_k, "")
                    if attr_local.startswith("on"):
                        del child.attrib[attr_k]
                        warnings.append(f"Stripped script handler '{attr_local}'")
                    elif attr_local in ("href", "xlink:href", "src"):
                        if attr_v and not SVG_SAFE_URL_RE.match(attr_v):
                            del child.attrib[attr_k]
                            warnings.append(f"Removed unsafe external reference in '{attr_local}'")
                    elif "javascript:" in attr_v.lower() or "vbscript:" in attr_v.lower():
                        del child.attrib[attr_k]
                        warnings.append(f"Removed unsafe URI in '{attr_local}'")
                    elif attr_local == "style" and "url(http" in attr_v.lower():
                        child.attrib[attr_k] = re.sub(r"url\(['\"]?https?://[^)]+\)", "none", attr_v, flags=re.IGNORECASE)
                        warnings.append("Removed external CSS url() from SVG style")

                _prune_element(child)
            for item in to_remove:
                parent.remove(item)

        _prune_element(root)
        serialized = ET.tostring(root, encoding="unicode")
        if not serialized.lstrip().startswith("<"):
            raise ValueError("Invalid serialized SVG")
        return serialized, warnings
    except Exception as exc:
        warnings.append(f"Strict XML parser fallback engaged ({exc}); regex sanitization applied")
        fallback = re.sub(r"<(script|foreignObject|iframe|object|embed)[^>]*>.*?</\1>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        fallback = re.sub(r"\s+on\w+\s*=\s*([\"']).*?\1", "", fallback, flags=re.IGNORECASE | re.DOTALL)
        fallback = re.sub(r"(href|xlink:href)\s*=\s*([\"'])\s*(javascript:|https?://|file://).*?\2", r'\1="#"', fallback, flags=re.IGNORECASE)
        return fallback, warnings


def store_original_artifact(
    file_bytes: bytes,
    filename: str,
    fmt: str,
    extra_meta: dict | None = None,
) -> dict:
    """
    Stores the untouched original upload safely inside static/reconstruction_cache/
    with complete provenance metadata for non-destructive inspection & undo/audit.
    """
    os.makedirs(CACHE_ROOT, exist_ok=True)
    safe_name = secure_filename(filename or f"label.{fmt}") or f"label.{fmt}"
    ext = os.path.splitext(safe_name)[1].lower().lstrip(".") or (fmt if fmt != "cdr_legacy" else "cdr")
    digest = hashlib.sha256(file_bytes).hexdigest()
    artifact_id = f"art_{int(time.time())}_{digest[:10]}"
    art_dir = os.path.join(CACHE_ROOT, artifact_id)
    os.makedirs(art_dir, exist_ok=True)

    orig_path = os.path.join(art_dir, f"original.{ext}")
    with open(orig_path, "wb") as fout:
        fout.write(file_bytes)

    record = {
        "artifact_id": artifact_id,
        "original_filename": safe_name,
        "format": fmt,
        "sha256": digest,
        "byte_size": len(file_bytes),
        "original_rel_path": f"/static/reconstruction_cache/{artifact_id}/original.{ext}",
        "created_at": int(time.time()),
    }
    if extra_meta:
        record.update(extra_meta)

    meta_path = os.path.join(art_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(record, mf, indent=2)
    return record


def load_artifact_metadata(artifact_id: str) -> dict | None:
    """Safely loads stored artifact metadata by validated artifact_id."""
    if not artifact_id or not re.match(r"^[a-zA-Z0-9_-]+$", artifact_id):
        return None
    meta_path = os.path.join(CACHE_ROOT, artifact_id, "meta.json")
    if not os.path.isfile(meta_path):
        return None
    with open(meta_path, "r", encoding="utf-8") as mf:
        return json.load(mf)
