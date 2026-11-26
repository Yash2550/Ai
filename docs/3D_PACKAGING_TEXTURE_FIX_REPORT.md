# GOMZI BOB — 3D Packaging Texture, UV Mapping & Realism Fix Report

**Correction Date:** 2026-11-25  
**Strict UI Preservation:** Verified (`5` packaging thumbnails, `6` view angles, `4` lighting cards; zero UI controls, tabs, panels, or dropdowns added or removed).

---

## 1. Confirmed Root Causes in Source Code

1. **Sticker-Like Artwork Cutout & Empty Borders ([`scripts/generate_packaging_models.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/generate_packaging_models.py) & [`static/js/studio_3d.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_3d.js)):**
   - `build_sachet_model()` previously placed an inset `FrontSurface` / `BackSurface` belly patch inside a bare metallic `FoilSealRim` shell, causing any full-bleed artwork to look like a small rectangle surrounded by a gold border.
   - Texture composition previously applied fixed container padding (`topPad`, `botPad`, `padX`) + `_drawCroppedContain()`, shrinking artwork into a floating center rectangle surrounded by solid margins instead of extending edge strips and gradients full-bleed across the packaging skin.
2. **Tiny Vertical Stacked Back Panels:**
   - `_buildBackCompositeCanvas()` placed portrait `~0.8:1` Left and Right information panels inside wide landscape upper/lower halves using `contain`, shrinking information blocks to `~50%` width with large blank borders on left, right, top, and bottom.
3. **Milky Gray Washout Over Black & Gold Prints (`studio_3d.js`):**
   - `createStudioEnvironmentTexture()` used an all-white/pale-gray `0xECEFF2` environment skybox paired with `envMapIntensity = 0.72..0.92` on printed labels, reflecting diffuse gray glare across dark `#0E0F12` inks.
   - Naive corner-pixel backdrop sampling could sample narrow bright trim strokes instead of the dominant interior background cluster.
4. **Hardcoded Equal `1/3` Panel Cropping & Async Stale Races:**
   - Rigid equal cropping risked misaligning asymmetric 3-panel labels, lacked Fabric.js hero-region verification, and risked clipping top headline pixels when extracting the Box Top logo crest.
   - Rapid switching between `.glb` presets had no async load token guard (`_activeGlbLoadId`) and did not recalculate `fitCameraToModel()` on resize/fullscreen changes.

---

## 2. Modified Source Files

- [`scripts/generate_packaging_models.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/generate_packaging_models.py)
  - Upgraded `build_sachet_model()` so `FrontSurface` and `BackSurface` span the full `[0..1] × [0..1]` UV face right across crimped top/bottom/side heat seals (`56×68` smooth normal grid, `d * 0.68` pillow swell, deeper diagonal foil tension wrinkles, V tear-notches, `1.8mm` edge thickness rim).
  - Deepened Stand-Up Doypack Pouch folds, top zipper rib relief, crimped top seal ribs, and oval bottom standing gusset in `build_pouch_or_sachet()`.
- [`static/js/studio_3d.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_3d.js)
  - **`createStudioEnvironmentTexture()` & Print PBR (`loadPackagingGlbModel`, `applyPbrMaterialFinish`):** Switched PMREM surround to dark studio cyclorama (`0x1C2026`) with calibrated softboxes and tuned matte print `envMapIntensity = 0.20` (`roughness = 0.74`) vs foil `envMapIntensity = 0.58` (`metalness <= 0.36`) so dark black/graphite packaging remains rich ink-black and metallic gold shimmers crisply.
  - **`analyzeArtworkLayout()`:** Auto-trims accidental pure-white outer scan margins, computes quantized gradient-weighted interior background clusters + gradient stops + accent tone, locates structural vertical 3-panel gutters, and inspects active Fabric.js hero/logo objects (`heroSlot`) so main product branding always targets `Front`.
  - **Full-Bleed Composer (`_drawSeamlessEdgeExtendedRegion()`, `_drawFullWidthPreservedRegion()`):** Eliminates rectangular sticker boundaries by extending outer non-text backdrop pixels & gradients edge-to-edge while keeping typography unstretched.
  - **Smart Backside Layout (`_buildSmartBackCanvas()` & `_findCleanHorizontalSplitY()`):** Automatically detects clean horizontal whitespace gaps (`<14%` foreground ink) inside Left & Right info panels so sub-sections stack wide across `~95%` printable width at legible scale without cutting lines or fabricating content.
  - **Clean Box Lid Crest (`_buildBoxFlapCanvas()`):** Scans for the whitespace row below the brand logo (`y ∈ [12%..26%]`) so headline letters below are never clipped on `BoxTopSurface`.
  - **Camera & Sync (`fitCameraToModel()`, `resizeThreeViewport()`, `_activeGlbLoadId`):** Dynamic `1.48×` bounding-box framing across model switch, capacity switch, resize, fullscreen, and view resets; async load cancellation token; and `60ms` debounced Live Sync with GPU texture `.dispose()`.
- [`scripts/render_3d_thumbnails.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/render_3d_thumbnails.py)
  - Regenerated studio `.glb` thumbnails in [`static/models/packaging/thumbnails/`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/models/packaging/thumbnails/).

---

## 3. Actual Browser Regression Results & Screenshots

Executed against live Flask + SQLite in Playwright Chromium (`1440×900`):

### Suite A: [`scratch/test_3d_wrapping_e2e.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/test_3d_wrapping_e2e.py) — **9 PASSED, 0 FAILED** ([`tests/reports/3d_fix_v2_results.json`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2_results.json))

| Test Case | Result | Verified Measurement / Output |
| :--- | :---: | :--- |
| `Strict UI Preservation` | **PASS** | `thumbs=5, angles=6, lighting=4` |
| `Protein Jar & Bottle Non-Regression` | **PASS** | Cylindrical 360° wrapping preserved |
| `Calcium Sachet Black&Gold Full-Bleed + Foil + Back Coverage` | **PASS** | `topEdgeRGB=[214,173,82]`, `blackBodyRGB=[14,15,17]`, `slots=['front','back']` |
| `Calcium Pouch Stand-up Doypack Full-Bleed Black&Gold + Front Branding + Back Info` | **PASS** | `topEdgeRGB=[214,173,82]`, `blackBodyRGB=[14,15,17]`, `gusset=True` |
| `Calcium Box 6-Surface Black&Gold Mapping` | **PASS** | `['front', 'back', 'left', 'right', 'top', 'bottom']` |
| `Real 2.54:1 D3+K2 Tablet Label Across Sachet, Pouch & Box` | **PASS** | Verified against workspace [`canva_a9be6749e8.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/uploads/canva_a9be6749e8.png) (`1600×630`) |
| `Live Sync Rebuilds Textures on Canvas Edit` | **PASS** | Distinct texture UUID generated automatically on edit |
| `Export 3D Mockup Download` | **PASS** | `D3_K2_Tablet_Wrap_3D_2048px.png` |
| `Zero Uncaught Page JS Exceptions` | **PASS** | `errors=[]` |

### Suite B: [`scratch/run_final_acceptance_tests.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/run_final_acceptance_tests.py) — **30 PASSED, 0 FAILED**
Confirmed zero regressions across default Whey Protein template, AI provider/model selection, Gujarati prompt enhancement, Full Label import, Save status persistence, SVG export, and all 10 sidebar views.

### Visual Proof Gallery ([`tests/reports/3d_fix_v2/`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/))
- **Calcium Tablet Black & Gold (`1536×605`) — Sachet:** [`03_calcium_sachet_front.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/03_calcium_sachet_front.png), [`03_calcium_sachet_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/03_calcium_sachet_back.png), [`03_calcium_sachet_right.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/03_calcium_sachet_right.png)
- **Calcium Tablet Black & Gold (`1536×605`) — Stand-Up Pouch:** [`04_calcium_pouch_front.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/04_calcium_pouch_front.png), [`04_calcium_pouch_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/04_calcium_pouch_back.png), [`04_calcium_pouch_side.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/04_calcium_pouch_side.png)
- **Calcium Tablet Black & Gold (`1536×605`) — 6-Surface Box:** [`05_calcium_box_3q.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/05_calcium_box_3q.png), [`05_calcium_box_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/05_calcium_box_back.png), [`05_calcium_box_right.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/05_calcium_box_right.png), [`05_calcium_box_top.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/05_calcium_box_top.png)
- **Real Workspace `D3+K2 Tablet` (`1600×630`):** [`06_d3k2_sachet_front.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/06_d3k2_sachet_front.png), [`06_d3k2_pouch_front.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/06_d3k2_pouch_front.png), [`06_d3k2_pouch_back.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/06_d3k2_pouch_back.png), [`06_d3k2_box_3q.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/tests/reports/3d_fix_v2/06_d3k2_box_3q.png)

---

## 4. Remaining Limitations Stated Honestly

1. **External Calcium Tablet Source File Availability (Requirement 24):** The exact `1536×605` black-and-gold Calcium Tablet PNG from the user's screenshots was not stored inside `static/` or session uploads (`static/uploads/` contained its sister `1600×630` `2.54:1` tablet wrap `canva_a9be6749e8.png`). Therefore, regression testing verified BOTH the real workspace `2.54:1` `D3+K2 Tablet` label AND a faithful `1536×605` black-and-gold synthetic Calcium Tablet reproduction ([`scratch/calcium_tablet_1536x605_test.png`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scratch/calcium_tablet_1536x605_test.png)).
2. **No Separate `.glb` Download UI Button (Requirement 22):** Under Strict UI Preservation (Requirement 1), no extra UI export button was added; `threeExportMockupBtn` handles `PNG/4K/JPG` mockup downloads cleanly.
3. **Asymmetric Freeform Graphic Dielines:** Automated texture composition handles 3-panel wraps, 4-panel carton strips, 2-panel spreads, and single front-only artworks without UI changes; non-rectangular custom die-cut CAD outlines with disconnected bleed islands remain constrained by rectangular sub-panel slicing.
