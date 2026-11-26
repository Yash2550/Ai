"""
Honest runtime probe of installed OCR, vectorization, PDF, CDR, font, and CorelDRAW capabilities.
"""

import os
import shutil

_CACHED_CAPS = None


def _has_mod(mod_name: str) -> bool:
    try:
        __import__(mod_name)
        return True
    except Exception:
        return False


def _has_coreldraw_com() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg
        for key in (r"SOFTWARE\Corel\CorelDRAW", r"SOFTWARE\WOW6432Node\Corel\CorelDRAW"):
            try:
                winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key)
                return True
            except OSError:
                continue
    except Exception:
        pass
    return False


def probe_system_capabilities(force_refresh: bool = False) -> dict:
    """Inspects and returns actual installed tools without overclaiming unavailable converters."""
    global _CACHED_CAPS
    if _CACHED_CAPS is not None and not force_refresh:
        return _CACHED_CAPS

    import cv2
    has_inkscape = bool(shutil.which("inkscape") or os.path.exists(r"C:\Program Files\Inkscape\bin\inkscape.exe"))
    has_soffice = bool(shutil.which("soffice") or shutil.which("libreoffice") or os.path.exists(r"C:\Program Files\LibreOffice\program\soffice.exe"))
    has_potrace = bool(shutil.which("potrace"))
    has_corel = _has_coreldraw_com()

    has_fitz = _has_mod("fitz")
    has_pypdf = _has_mod("pypdf")
    has_vtracer = _has_mod("vtracer")
    has_easyocr = _has_mod("easyocr")
    has_fonttools = _has_mod("fontTools")
    has_reportlab = _has_mod("reportlab")
    has_skimage = _has_mod("skimage")

    win_fonts_dir = r"C:\Windows\Fonts"
    font_count = 0
    if os.path.isdir(win_fonts_dir):
        font_count = sum(1 for f in os.listdir(win_fonts_dir) if f.lower().endswith((".ttf", ".otf")))

    # Check configured AI Vision providers
    vision_providers = []
    try:
        import ai_provider_service as aps
        for p in aps.get_provider_status():
            if p.get("is_configured") and p.get("is_enabled") and p["id"] in ("gemini", "openai"):
                vision_providers.append(p["id"])
    except Exception:
        pass

    _CACHED_CAPS = {
        "svg_native_import": True,
        "pdf_native_import": bool(has_fitz),
        "pdf_metadata": bool(has_fitz or has_pypdf),
        "ai_pdf_compatible_import": bool(has_fitz),
        "cdr_modern_zip_preview": True,
        "cdr_legacy_riff_converter": bool(has_soffice or has_inkscape or has_corel),
        "coreldraw_installed": bool(has_corel),
        "libreoffice_installed": bool(has_soffice),
        "inkscape_installed": bool(has_inkscape),
        "ocr_engines": {
            "easyocr_tiled": bool(has_easyocr),
            "ai_vision": vision_providers,
        },
        "vectorizers": {
            "vtracer": bool(has_vtracer),
            "opencv_contour_bezier": True,
            "potrace_cli": bool(has_potrace),
        },
        "font_tools": bool(has_fonttools),
        "system_fonts_count": font_count,
        "barcode_detector": bool(hasattr(cv2, "barcode") or hasattr(cv2, "barcode_BarcodeDetector")),
        "qr_detector": bool(hasattr(cv2, "QRCodeDetector")),
        "visual_ssim": bool(has_skimage),
        "exports": {
            "editable_text_svg": True,
            "outlined_text_svg": bool(has_fonttools and font_count > 0),
            "vector_pdf": bool(has_reportlab),
            "native_cdr_write": bool(has_corel),
            "coreldraw_interchange": ["svg_editable", "svg_outlined", "vector_pdf"],
        },
    }
    return _CACHED_CAPS
