"""
Font analysis, studio font matching, system TTF lookup, and FontTools glyph-to-SVG outlining.
Never claims exact proprietary font identification when using closest available matches.
"""

import os
from functools import lru_cache
import cv2
import numpy as np

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    _HAS_FONTTOOLS = True
except ImportError:
    TTFont = None  # type: ignore
    SVGPathPen = None  # type: ignore
    TransformPen = None  # type: ignore
    _HAS_FONTTOOLS = False

WIN_FONTS_DIR = r"C:\Windows\Fonts"

# Closest local TTF equivalents on Windows for Studio webfont families
STUDIO_TO_LOCAL_TTF = {
    "Montserrat": {
        "regular": ["montserrat-regular.ttf", "segoeui.ttf", "calibri.ttf", "arial.ttf"],
        "bold": ["montserrat-bold.ttf", "segoeuib.ttf", "calibrib.ttf", "arialbd.ttf"],
        "italic": ["segoeuii.ttf", "calibrii.ttf", "ariali.ttf"],
        "bold_italic": ["segoeuiz.ttf", "calibriz.ttf", "arialbi.ttf"],
    },
    "Inter": {
        "regular": ["inter-regular.ttf", "segoeui.ttf", "calibri.ttf", "arial.ttf"],
        "bold": ["inter-bold.ttf", "segoeuib.ttf", "calibrib.ttf", "arialbd.ttf"],
        "italic": ["segoeuii.ttf", "calibrii.ttf", "ariali.ttf"],
        "bold_italic": ["segoeuiz.ttf", "calibriz.ttf", "arialbi.ttf"],
    },
    "Oswald": {
        "regular": ["bahnschrift.ttf", "arialn.ttf", "arial.ttf"],
        "bold": ["impact.ttf", "bahnschrift.ttf", "arialnb.ttf", "arialbd.ttf"],
        "italic": ["arialni.ttf", "ariali.ttf"],
        "bold_italic": ["arialnbi.ttf", "arialbi.ttf"],
    },
    "Bebas Neue": {
        "regular": ["impact.ttf", "bahnschrift.ttf", "arialbd.ttf"],
        "bold": ["impact.ttf", "bahnschrift.ttf", "arialbd.ttf"],
        "italic": ["arialbi.ttf"],
        "bold_italic": ["arialbi.ttf"],
    },
    "Anton": {
        "regular": ["impact.ttf", "ariblk.ttf", "arialbd.ttf"],
        "bold": ["impact.ttf", "ariblk.ttf", "arialbd.ttf"],
        "italic": ["arialbi.ttf"],
        "bold_italic": ["arialbi.ttf"],
    },
    "Cinzel": {
        "regular": ["georgia.ttf", "times.ttf", "palab.ttf"],
        "bold": ["georgiab.ttf", "timesbd.ttf"],
        "italic": ["georgiai.ttf", "timesi.ttf"],
        "bold_italic": ["georgiaz.ttf", "timesbi.ttf"],
    },
}


@lru_cache(maxsize=1)
def _list_win_fonts_lower() -> dict[str, str]:
    if not os.path.isdir(WIN_FONTS_DIR):
        return {}
    out = {}
    for fname in os.listdir(WIN_FONTS_DIR):
        if fname.lower().endswith((".ttf", ".otf")):
            out[fname.lower()] = os.path.join(WIN_FONTS_DIR, fname)
    return out


def get_ttf_path_for_studio_font(font_family: str = "Montserrat", bold: bool = False, italic: bool = False) -> str | None:
    """Resolves the closest authorized local TTF file for outlining & ReportLab embedding."""
    fonts = _list_win_fonts_lower()
    if not fonts:
        return None
    fam = font_family if font_family in STUDIO_TO_LOCAL_TTF else "Inter"
    style_key = "bold_italic" if (bold and italic) else ("bold" if bold else ("italic" if italic else "regular"))
    candidates = STUDIO_TO_LOCAL_TTF.get(fam, STUDIO_TO_LOCAL_TTF["Inter"]).get(style_key, [])
    for c in candidates + ["arialbd.ttf" if bold else "arial.ttf", "calibri.ttf", "segoeui.ttf"]:
        if c.lower() in fonts:
            return fonts[c.lower()]
    return next(iter(fonts.values()), None)


@lru_cache(maxsize=16)
def _load_cached_ttfont(ttf_path: str) -> TTFont:
    return TTFont(ttf_path)


def match_font_for_region(
    img_bgr: np.ndarray,
    bx: int,
    by: int,
    bw: int,
    bh: int,
    text_str: str,
    role: str = "",
) -> dict:
    """
    Estimates font family, bold weight, condensed proportions, and confidence
    from stroke ink density and aspect metrics inside the crop.
    Honest estimation: marks confidence < 1.0 when approximate studio webfont is chosen.
    """
    h, w = img_bgr.shape[:2]
    x1 = max(0, bx)
    y1 = max(0, by)
    x2 = min(w, bx + max(1, bw))
    y2 = min(h, by + max(1, bh))
    roi = img_bgr[y1:y2, x1:x2]

    ink_ratio = 0.25
    is_bold = False
    is_condensed = False

    if roi.size >= 16:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Foreground ink usually has smaller pixel area in a tight word box
        fg_cnt = min(int(np.sum(th == 255)), int(np.sum(th == 0)))
        ink_ratio = fg_cnt / float(th.size)
        is_bold = ink_ratio > 0.31 or bh >= 22 or role in ("product_title", "strength_badge", "section_heading")

    clean_len = max(1, len(text_str.strip()))
    avg_char_w = bw / float(clean_len)
    char_ratio = avg_char_w / max(1.0, float(bh))
    is_condensed = char_ratio < 0.56

    is_upper = text_str.strip().isupper() and len(text_str.strip()) >= 3
    if role == "product_title" or (is_upper and bh >= 26):
        family = "Bebas Neue" if is_condensed else "Montserrat"
        conf = 0.78
    elif role in ("section_heading", "nutrition_header", "strength_badge") or (is_bold and is_upper):
        family = "Oswald" if is_condensed else "Montserrat"
        conf = 0.76
    else:
        family = "Inter"
        conf = 0.72

    return {
        "fontFamily": family,
        "fontWeight": "800" if (role == "product_title" or ink_ratio > 0.36) else ("700" if is_bold else "400"),
        "fontStyle": "normal",
        "charSpacing": int(round(max(0, (char_ratio - 0.65) * 140))) if char_ratio > 0.78 else 0,
        "fontMatchConfidence": round(conf, 2),
        "fontMatchNote": f"Closest studio font '{family}' estimated from stroke density ({ink_ratio:.2f}) & glyph width ratio ({char_ratio:.2f})",
    }


def text_to_svg_path_d(
    text: str,
    font_size: float,
    x: float,
    y_baseline: float,
    font_family: str = "Montserrat",
    bold: bool = False,
    italic: bool = False,
    letter_spacing: float = 0.0,
) -> tuple[str, float]:
    """
    Converts a text string into true cubic/quadratic SVG glyph vector <path d="...">
    using FontTools SVGPathPen and an authorized local TTF file.
    Returns (path_d, total_advance_px).
    """
    if not _HAS_FONTTOOLS:
        return "", 0.0
    ttf_path = get_ttf_path_for_studio_font(font_family, bold=bold, italic=italic)
    if not ttf_path:
        return "", 0.0

    font = _load_cached_ttfont(ttf_path)
    upem = float(font["head"].unitsPerEm or 1000)
    scale = float(font_size) / upem
    cmap = font.getBestCmap() or {}
    hmtx = font["hmtx"]
    glyph_set = font.getGlyphSet()

    parts = []
    cursor_x = float(x)
    for ch in text:
        code = ord(ch)
        gname = cmap.get(code)
        if not gname:
            gname = ".notdef"
        try:
            adv_units, _ = hmtx[gname]
        except Exception:
            adv_units = upem * 0.5

        if gname in glyph_set and not ch.isspace():
            pen = SVGPathPen(glyph_set)
            tpen = TransformPen(pen, (scale, 0, 0, -scale, cursor_x, y_baseline))
            glyph_set[gname].draw(tpen)
            d_str = pen.getCommands()
            if d_str:
                parts.append(d_str)

        cursor_x += adv_units * scale + letter_spacing

    return " ".join(parts), cursor_x - float(x)
