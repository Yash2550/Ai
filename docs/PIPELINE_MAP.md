# docs/PIPELINE_MAP.md

# Pipeline Map: AI Packaging Studio Text Pipeline

## Overview
This document maps every function in the text detection, inpainting, textbox creation, and save/flatten pipeline across `app.py`, `canva_pro_tools.py`, `digitizer.py`, and `templates/index.html`.

---

## 1. End-to-End Pipeline Functions

### Function 1: `canva_detect_text()`
- **Location:** [app.py](file:///d:/NEWWWW - Copy - Copy/app.py#L2811-L2830)
- **HTTP Endpoint:** `POST /api/canva/detect-text`
- **Inputs:** JSON `{"image_data": "<base64 data-URI>"}`
- **Outputs:** JSON structured dictionary from `canva_pro_tools.detect_text`:
  ```json
  {
    "text_elements": [
      {
        "id": "text_block_0_0",
        "text": "CREATINE",
        "left": 450,
        "top": 120,
        "width": 380,
        "height": 95,
        "fontSize": 80,
        "conf": 0.88,
        "color": "#ffffff"
      }
    ],
    "count": 1,
    "image_width": 1800,
    "image_height": 600,
    "success": true
  }
  ```
- **Called by:** [templates/index.html](file:///d:/NEWWWW - Copy - Copy/templates/index.html#L4597) (`toolGrabTextBtn.onclick`)

### Function 2: `detect_text(image_bytes: bytes, conf_threshold: float = 0.20)`
- **Location:** [canva_pro_tools.py](file:///d:/NEWWWW - Copy - Copy/canva_pro_tools.py#L811-L870)
- **Inputs:** Raw binary image bytes (`bytes`), optional confidence threshold (`float`).
- **Calls:**
  - `get_easyocr_reader()`: initializes shared EasyOCR reader.
  - `group_ocr_detections()`: aggregates words into coherent line boxes.
  - `extract_robust_text_color()`: samples dominant foreground text color via Otsu thresholding.
- **Outputs:** Dict with keys `text_elements`, `count`, `image_width`, `image_height`, `success`.

### Function 3: `group_ocr_detections(ocr_results, img_w, img_h, conf_threshold)`
- **Location:** [canva_pro_tools.py](file:///d:/NEWWWW - Copy - Copy/canva_pro_tools.py#L688-L808)
- **Inputs:** Raw EasyOCR output tuples `(bbox, text, conf)`, image dimensions, confidence threshold.
- **Outputs:** List of line element dictionaries with `left`, `top`, `width`, `height`, `fontSize`, `conf`, `text`.

### Function 4: `canva_inpaint_text()`
- **Location:** [app.py](file:///d:/NEWWWW - Copy - Copy/app.py#L2832-L2858)
- **HTTP Endpoint:** `POST /api/canva/inpaint-text`
- **Inputs:** JSON `{"image_data": "<base64 data-URI>", "regions": [...]}`
- **Outputs:** JSON `{"clean_background_url": "data:image/png;base64,...", "success": true}`
- **Called by:** [templates/index.html](file:///d:/NEWWWW - Copy - Copy/templates/index.html#L4740) (`applyGrabBtn.onclick`)

### Function 5: `inpaint_text_regions(image_bytes: bytes, regions: list) -> bytes`
- **Location:** [canva_pro_tools.py](file:///d:/NEWWWW - Copy - Copy/canva_pro_tools.py#L872-L960)
- **Inputs:** Source image bytes, list of bounding box regions `[{"left", "top", "width", "height", ...}]`.
- **Outputs:** Inpainted PNG bytes (`bytes`).
- **Processing steps:**
  1. For each ROI, compute local background color by border median sampling.
  2. Compute delta color distance from background + Otsu luminance thresholding.
  3. Dilate mask with structuring element to cover anti-aliased font fringes.
  4. Run `cv2.inpaint(..., inpaintRadius=4, flags=cv2.INPAINT_TELEA)`.

### Function 6: Frontend Canvas & Textbox Creation (`applyGrabBtn.onclick`)
- **Location:** [templates/index.html](file:///d:/NEWWWW - Copy - Copy/templates/index.html#L4727-L4980)
- **Inputs:** `selected` regions array from user checklist or manual box drawer.
- **Actions:**
  1. Calls `/api/canva/inpaint-text` with active image and selected regions.
  2. Updates `cleanBgUrl` and calls `setCanvasBg(clean_background_url)`.
  3. Locks background image (`selectable: false, evented: false, lockMovementX: true, lockMovementY: true`).
  4. For each selected region, instantiates `fabric.Textbox(elem.text)` with:
     - `left: elem.left * scale`
     - `top: elem.top * scale`
     - `width: safeWidth`
     - `fontSize: calculatedFontSize`
     - `lineHeight: 1.0`
     - `fill: elem.color`
     - `lockScalingFlip: true`
     - `splitByGrapheme: false`

### Function 7: `save_editor_result()`
- **Location:** [app.py](file:///d:/NEWWWW - Copy - Copy/app.py#L2404-L2442)
- **HTTP Endpoint:** `POST /save-editor-result`
- **Inputs:** JSON `{"filename": "result_xyz.png", "image_data": "<base64 data-URI>"}`
- **Outputs:** JSON `{"result_image": "/static/results/result_xyz.png?t=...", "success": true}`
- **Actions:**
  1. Writes decoded PNG bytes directly to `static/results/<filename>`.
  2. Invalidates cache file `static/results/<stem>_ultrahd_8000.png`.
- **Called by:** [templates/index.html](file:///d:/NEWWWW - Copy - Copy/templates/index.html#L7226) (`applyBtn.onclick`)

---

## 2. Identified Bugs & Root Cause Locations

| Bug ID | File | Function | Line Range | Precise Mechanism |
|---|---|---|---|---|
| **BUG-1** | `canva_pro_tools.py` | `group_ocr_detections` | L745–L755 | Center-Y alignment tolerance (`min_h * 0.38`) combined with height ratio (`0.55 .. 1.8`) splits large capital letters on textured/slanted backgrounds. |
| **BUG-2** | `canva_pro_tools.py` | `inpaint_text_regions` | L903–L925 | Fallback check `mask_ratio > 0.45` activates adaptive thresholding which fails on solid bold fonts, leaving character centers unmasked (causing ghost text). |
| **BUG-3** | `templates/index.html` | `applyGrabBtn.onclick` | L4936–L4964 | `fabric.Textbox` `splitByGrapheme: false` wraps text if width is tightly bounded without explicit `noWrap: true` or adequate padding. |
| **BUG-4** | `templates/index.html` | `setCanvasBg` | L5558–L5575 | If canvas scaling is recalculated during window resize without re-scaling text layers, positions desynchronize. |
| **BUG-5** | `app.py` | `save_editor_result` | L2420–L2428 | Invalidation only deletes `_ultrahd_8000.png`, but other potential resolution caches (`_ultrahd_4000.png` or `_master_300dpi.png`) must also be cleared. |

