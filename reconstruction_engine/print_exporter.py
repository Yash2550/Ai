"""
High-Resolution Print Master Exporter for GOMZI BOB.
Supports configurable physical dimensions (mm), 300/600 DPI, bleed (mm),
PNG, Transparent PNG, JPEG, and lossless print TIFF.
Honestly reports RGB/RGBA vs ICC-profile CMYK color space.
"""
from __future__ import annotations

import io
import os
from typing import Optional, Tuple

from PIL import Image, ImageCms


SUPPORTED_PRINT_FORMATS = {"png", "png_transparent", "jpg", "jpeg", "tiff", "tif"}


def _clamp_edge_bleed(img: Image.Image, bleed_px: int) -> Image.Image:
    """Extends outer edge pixels into the bleed margin without scaling trim artwork."""
    if bleed_px <= 0:
        return img
    w, h = img.size
    canvas = Image.new(img.mode, (w + 2 * bleed_px, h + 2 * bleed_px))
    canvas.paste(img, (bleed_px, bleed_px))

    # Top and bottom edge strips
    top_strip = img.crop((0, 0, w, 1)).resize((w, bleed_px), Image.Resampling.NEAREST)
    bot_strip = img.crop((0, h - 1, w, h)).resize((w, bleed_px), Image.Resampling.NEAREST)
    canvas.paste(top_strip, (bleed_px, 0))
    canvas.paste(bot_strip, (bleed_px, bleed_px + h))

    # Left and right edge strips (including corners)
    left_strip = canvas.crop((bleed_px, 0, bleed_px + 1, h + 2 * bleed_px)).resize(
        (bleed_px, h + 2 * bleed_px), Image.Resampling.NEAREST
    )
    right_strip = canvas.crop((bleed_px + w - 1, 0, bleed_px + w, h + 2 * bleed_px)).resize(
        (bleed_px, h + 2 * bleed_px), Image.Resampling.NEAREST
    )
    canvas.paste(left_strip, (0, 0))
    canvas.paste(right_strip, (bleed_px + w, 0))
    return canvas


def render_print_export(
    raw_bytes: bytes,
    fmt: str = "png",
    stem: str = "GOMZI_Print_Master",
    width_mm: float = 160.0,
    height_mm: float = 65.0,
    dpi: int = 300,
    bleed_mm: float = 0.0,
    safe_margin_mm: float = 3.0,
    icc_profile_path: Optional[str] = None,
) -> Tuple[bytes, str, str, dict]:
    """
    Renders a print-ready raster export at exact physical mm + DPI + bleed.
    Returns (file_bytes, mimetype, download_filename, metadata).
    """
    norm_fmt = (fmt or "png").strip().lower()
    if norm_fmt == "jpeg":
        norm_fmt = "jpg"
    if norm_fmt == "tif":
        norm_fmt = "tiff"
    if norm_fmt not in {"png", "png_transparent", "jpg", "tiff"}:
        raise ValueError(f"Unsupported print format: {fmt}")

    dpi_val = max(72, min(600, int(dpi or 300)))
    w_mm = max(10.0, float(width_mm or 160.0))
    h_mm = max(10.0, float(height_mm or 65.0))
    bleed_val = max(0.0, min(25.0, float(bleed_mm or 0.0)))
    safe_val = max(0.0, min(25.0, float(safe_margin_mm or 3.0)))

    with Image.open(io.BytesIO(raw_bytes)) as src:
        # Preserve aspect if caller did not supply height_mm explicitly
        if height_mm is None or float(height_mm) <= 0:
            h_mm = w_mm * (src.height / max(1, src.width))

        trim_w = max(16, round(w_mm * dpi_val / 25.4))
        trim_h = max(16, round(h_mm * dpi_val / 25.4))
        bleed_px = max(0, round(bleed_val * dpi_val / 25.4))

        # Safety cap to prevent excessive memory allocation on very large banners
        max_dim = 12000
        total_w = trim_w + 2 * bleed_px
        total_h = trim_h + 2 * bleed_px
        if max(total_w, total_h) > max_dim:
            scale = max_dim / float(max(total_w, total_h))
            trim_w = max(16, round(trim_w * scale))
            trim_h = max(16, round(trim_h * scale))
            bleed_px = max(0, round(bleed_px * scale))

        if norm_fmt == "png_transparent":
            base = src.convert("RGBA")
        elif norm_fmt == "tiff" and src.mode in ("RGBA", "LA"):
            base = src.convert("RGBA")
        else:
            if src.mode in ("RGBA", "LA", "P"):
                rgba = src.convert("RGBA")
                white = Image.new("RGB", rgba.size, (255, 255, 255))
                white.paste(rgba, mask=rgba.split()[3])
                base = white
            else:
                base = src.convert("RGB")

        resized = base.resize((trim_w, trim_h), Image.Resampling.LANCZOS)
        final_img = _clamp_edge_bleed(resized, bleed_px)

    color_space = final_img.mode
    cmyk_applied = False
    cmyk_note = "sRGB/RGBA print master (browser canvas is RGB; supply an ICC profile for true CMYK separation)."

    if (
        icc_profile_path
        and os.path.isfile(icc_profile_path)
        and norm_fmt in ("jpg", "tiff")
    ):
        try:
            srgb_prof = ImageCms.createProfile("sRGB")
            cmyk_prof = ImageCms.getOpenProfile(icc_profile_path)
            rgb_src = final_img.convert("RGB")
            final_img = ImageCms.profileToProfile(rgb_src, srgb_prof, cmyk_prof, outputMode="CMYK")
            color_space = "CMYK"
            cmyk_applied = True
            cmyk_note = f"Converted to CMYK via ICC profile: {os.path.basename(icc_profile_path)}"
        except Exception as exc:
            cmyk_note = f"ICC CMYK conversion skipped ({exc}); exported as {final_img.mode}."

    out_io = io.BytesIO()
    if norm_fmt in ("png", "png_transparent"):
        final_img.save(out_io, format="PNG", dpi=(dpi_val, dpi_val), optimize=True)
        mime = "image/png"
        suffix = "_transparent" if norm_fmt == "png_transparent" else ""
        dl_name = f"{stem}_{dpi_val}dpi{suffix}.png"
    elif norm_fmt == "jpg":
        final_img.save(out_io, format="JPEG", dpi=(dpi_val, dpi_val), quality=96, subsampling=0)
        mime = "image/jpeg"
        dl_name = f"{stem}_{dpi_val}dpi.jpg"
    else:
        final_img.save(out_io, format="TIFF", dpi=(dpi_val, dpi_val), compression="tiff_lzw")
        mime = "image/tiff"
        dl_name = f"{stem}_{dpi_val}dpi.tiff"

    meta = {
        "format": norm_fmt,
        "dpi": dpi_val,
        "width_mm": round(w_mm, 2),
        "height_mm": round(h_mm, 2),
        "bleed_mm": round(bleed_val, 2),
        "safe_margin_mm": round(safe_val, 2),
        "pixel_width": final_img.width,
        "pixel_height": final_img.height,
        "color_space": color_space,
        "cmyk_applied": cmyk_applied,
        "cmyk_note": cmyk_note,
    }
    return out_io.getvalue(), mime, dl_name, meta
