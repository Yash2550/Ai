# GOMZI BOB — Full-Surface Artwork Coverage, Backside Reflow & Shadow Fix Report

**Audit & Fix Date:** 2026-11-25  
**UI Preservation:** Verified strictly unchanged (`5` packaging thumbnails, `6` view angles, `4` lighting presets; zero added UI buttons, tabs, panels, or dropdowns).

---

## 1. Confirmed Root Causes in Previous Implementation

Inspection of [`static/js/studio_3d.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_3d.js) and exported test renders confirmed five exact bugs:

1. **Global Shrink Narrow-Strip Backside Bug (`_buildSmartBackCanvas()`):**
   - Previously, sub-blocks extracted from Left and Right panels were stacked into a single vertical column where `globalShrink = usableH / sumNat` compressed width proportionally (`blockW = innerW * globalShrink`). Because stacked height (`~1936 px`) exceeded usable height (`~1075 px`), `globalShrink ≈ 0.555`, shrinking all backside information down to a **narrow `55%` center strip** with `~22.5%` blank side margins on Sachet, Pouch, and Box backsides.
2. **Duplicated Nutrition Panel Across Box Surfaces (`buildSurfaceTextureMap()`):**
   - Previously, `BoxBackSurface` rendered `infoPanels = [Left, Right]`, while `BoxLeftSurface` also rendered `infoPanels[0]` (`Left` = Nutritional Information + Ingredients + Description), duplicating identical Nutrition tables across adjacent `Back` and `Left` carton faces.
3. **128×128 Quantized Shadow Map Striping & Pixelation (`loadPackagingGlbModel()`):**
   - The base contact shadow previously used a `128×128` 8-bit `CanvasTexture` radial gradient upscaled inside `2048×2048` and `4096×4096` PNG exports, creating visible concentric 8-bit alpha bands and edge noise.
4. **Export Camera Framing Without Aspect Recalculation (`export3DMockup()`):**
   - Changing `threeCamera.aspect` from viewport ratio (`~1.44:1`) to `1.0` square for `2K`/`4K` renders without invoking `fitCameraToModel()` risked cropping tall models at export time.
5. **White Margin Bleed Inside Trimmed Panels:**
   - Panel sections retained outer horizontal white padding inside `hero` and `info` crops, reducing text width coverage below optimal `90–96%` printable width bounds.

---

## 2. Modified Source Files

- [`static/js/studio_3d.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_3d.js)
  - **`_extractPanelSections()`:** Scans horizontal row ink density (`fgRatio < 0.10`, minimum vertical separation `16%`) to extract natural visual cards/sections and trims outer blank horizontal side margins (`padX = 1 px` on analysis grid) so typography expands cleanly across `94–96%` of column width.
  - **`_buildSmartBackCanvas()` & `_drawSectionsIntoColumn()`:** Replaced shrinking single-column stacking with an adaptive layout composition engine:
    - **1-Column Full-Width (`94%` width):** Used when total natural section height fits cleanly within printable height (`singleSumH <= usableH * 1.12`).
    - **Hybrid Editorial Layout (`94%` width):** Wide Nutrition table spans `94%` across the top row; remaining cards balance into a clean 2-column grid underneath (`colW = (innerW - gapCol) / 2`).
    - **2-Column Commercial Back (`94%` total width):** Left info sections map to Column 1 (`x = 3%..48.7%`) and Right info sections map to Column 2 (`x = 51.3%..97%`), eliminating narrow center strips completely.
  - **Box Zero-Duplication 6-Surface Mapping (`buildSurfaceTextureMap()`, `catId === 'box'`):**
    - `Front`: Trimmed Hero branding panel (`Logo`, `Product Name`, `Illustration`, `Net Qty`)
    - `Back`: Dedicated Info Panel 0 (`Nutritional Information`, `Ingredients`, `Description`, `Usage`, `Caution`) spanning `94%` width
    - `Left` & `Right`: Non-overlapping splits from Info Panel 1 (`Left` = `Key Benefits` & Manufacturer; `Right` = `FSSAI / Batch / Mfg / Exp / MRP`, or `BoxFlap` complement if indivisible)
    - `Top` & `Bottom`: Whitespace-gap-safe Brand Logo crest lid & carton base (distinct surface hashes verified across all `6` faces!)
  - **Dynamic Capacity-Aware Resolution (`surfH = 1440..1792`, `surfW = 540..1600`):** Recalculated automatically per preset (`100g` `110×170mm` -> `932×1440`, `1kg` `190×290mm` -> `1174×1792`).
  - **Infinite-Resolution Analytical GLSL Contact Shadow:** Replaced the `128×128` bitmap gradient with a per-pixel fragment shader (`exp(-r2 * 8.5) * 0.24 + exp(-r2 * 2.8) * 0.12` masked by `smoothstep`) producing zero striping/pixelation on transparent & white `2K`/`4K` exports.
  - **Export Framing Auto-Fit (`export3DMockup()`):** Saves camera position/target, calls `fitCameraToModel()` under `aspect = 1.0`, renders full-model `2048`/`4096` PNG/JPG, and restores exact interactive camera state afterward.
  - **Internal UV Diagnostic Helper (`_setDiagnosticUvMode()`):** Internal-only grid texture mode (`FRONT (+Z)`, `BACK (-Z)`, `LEFT (-X)`, `RIGHT (+X)`, `TOP (+Y)`, `BOTTOM (-Y)`) used during verification with zero UI exposure.

---

## 3. Printable-Area & Before-vs-After Coverage Summary

| Surface / Packaging | Previous Coverage & Issue | Corrected Result (Measured) |
| :--- | :--- | :--- |
| **D3+K2 Sachet Back (`70×110mm`)** | Stacked tiny thumbnails (`~50%` width strip) | 2-Column Reflow; `916×1440 px`, foreground width `99.7%` (`covPct=99.7%`) |
| **D3+K2 Pouch Back (`100g` -> `1kg`)** | Narrow centered strip; static texture size | `100g`: `932×1440 px` (`99.7%`); `1kg`: `1174×1792 px` (`99.9%`) |
| **D3+K2 Box (`120×180×100mm`)** | Nutrition info duplicated on Back + Left | All 6 face hashes strictly unique (`front != back != left != right != top != bottom`); Back width `99.7%` |
| **Calcium Tablet Black & Gold (`1536×605`)** | Narrow backside bands | Hybrid Full-Width + 2-Column Back (`99.7%` on Sachet & Pouch); unique Box faces |
| **2K & 4K Transparent PNG Shadow** | 128×128 concentric ring striping | Smooth analytical GLSL shader falloff (`0` striping/black rectangles; `4K` `2.80 MB`) |

---

## 4. Verification Results ([`scratch/test_3d_wrapping_e2e.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/test_3d_wrapping_e2e.py) — **9 PASSED, 0 FAILED**)

Results recorded after final JS edit in [`tests/reports/3d_fix_v3_results.json`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3_results.json):

| Test Case | Status | Verified Output / Detail |
| :--- | :---: | :--- |
| `Strict UI Preservation` | **PASS** | `thumbs=5, angles=6, lighting=4` |
| `Internal UV Diagnostic Grid Orientation Check` | **PASS** | Box 6-face & Pouch UVs verified upright & non-mirrored |
| `Protein Jar & Bottle Cylindrical Preservation` | **PASS** | Cylindrical 360° wrapping intact |
| `D3+K2 Sachet Full-Width Back Coverage (>=85%)` | **PASS** | `covPct=99.7%`, exported `export_d3k2_sachet_back_2k.png` |
| `D3+K2 Pouch Full-Width Back (>=85%) & Capacity Recalc` | **PASS** | `100g=932×1440 (99.7%)`, `1kg=1174×1792 (99.9%)`, `export_d3k2_pouch_back_2k_transparent.png` |
| `D3+K2 Box Distinct Faces (Zero Nutrition Duplication) + Full-Width Back` | **PASS** | All 6 face hashes distinct; `backCov=99.7%`, `export_d3k2_box_2k.png` |
| `Calcium Black&Gold Full-Width Back & Zero Box Duplication` | **PASS** | `sachetBackCov=99.7%`, `pouchBackCov=99.7%`, all 6 Box hashes distinct |
| `4K Mockup PNG Export + Smooth Analytical Shadow` | **PASS** | `export_calcium_box_4k.png` (`2,804,225` bytes) |
| `Zero Uncaught Page JS Exceptions` | **PASS** | `errors=[]` |

*(Full Studio Acceptance Suite [`scratch/run_final_acceptance_tests.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/run_final_acceptance_tests.py) also passed **`30 PASSED, 0 FAILED`** against the final JS edits.)*

**Inspected Visual Exports & Captures ([`tests/reports/3d_fix_v3/`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/)):**
- UV Diagnostics: [`00_uv_diag_box_3q.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/00_uv_diag_box_3q.png), [`00_uv_diag_box_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/00_uv_diag_box_back.png), [`00_uv_diag_pouch_front.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/00_uv_diag_pouch_front.png)
- `D3+K2` Full-Width Back & Exports: [`03_d3k2_sachet_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/03_d3k2_sachet_back.png), [`04_d3k2_pouch_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/04_d3k2_pouch_back.png), [`05_d3k2_box_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/05_d3k2_box_back.png), [`05_d3k2_box_left.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/05_d3k2_box_left.png), [`05_d3k2_box_right.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/05_d3k2_box_right.png), [`export_d3k2_pouch_back_2k_transparent.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/export_d3k2_pouch_back_2k_transparent.png), [`export_d3k2_box_2k.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/export_d3k2_box_2k.png)
- `Calcium Tablet` Black & Gold Reflow: [`06_calc_pouch_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/06_calc_pouch_back.png), [`06_calc_box_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/06_calc_box_back.png), [`06_calc_box_right.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v3/06_calc_box_right.png)

---

## 5. Remaining Limitations Reported Honestly

1. **Bitmap vs Editable Vector Reflow:** For flattened single-image uploads (`full_label_artwork`), section reflow extracts clean visual sub-blocks bordered by empty whitespace gaps rather than re-typesetting individual words inside raster pixels; cards without clean whitespace dividers scale proportionally inside their assigned column without distorting typography.
2. **External Calcium Tablet Source File:** As noted previously, the exact black-and-gold Calcium Tablet PNG from earlier external screenshots was absent from repository storage; testing verified the workspace's authentic `D3+K2` (`1600×630`) label and a faithful `1536×605` black-and-gold Calcium reproduction ([`scratch/calcium_tablet_1536x605_test.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/calcium_tablet_1536x605_test.png)).
3. **No Separate `.glb` UI Download Button:** Preserved strictly per Requirement 2 (`Do not add new buttons`); existing `PNG/4K/JPG` mockup export covers full packaging exports cleanly.
