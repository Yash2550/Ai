# GOMZI BOB — Protein Jar 3D Upgrade Report

## Overview
Upgraded the **Protein Jar** (`jar`) 3D procedural `.glb` geometry, screw-cap rib normal generation, capacity-specific body proportions, HDPE plastic PBR materials, and studio thumbnail renders while preserving the UI layout, 360-degree cylindrical label wrapping (`LabelSurface`), and all other packaging categories (**Pouch**, **Sachet**, **Bottle**, **Box**).

## Asset Origin & Modified Files
- **`scripts/generate_packaging_models.py`** (In-house procedural Python glTF/GLB geometry engine — `copyright: "GOMZI BOB In-House Asset"`):
  - Upgraded `_revolve_profile()` to compute true 3D central-difference vertex normals across `theta` and `y` whenever `ridge_fn` modulates radius, giving fluted screw-cap grip ribs crisp directional highlights.
  - Added `_jar_capacity_specs(preset_id)` and `build_protein_jar(preset_id, dia_mm, h_mm, label_h_mm)` producing dedicated meshes:
    - `BottomRing` — recessed bottom punt, standing foot ring, rounded base heel fillet, and lower label bumper ridge.
    - `JarBody` — subtly recessed cylindrical wall (`0.995 * r_body`) seating the label cleanly inside the mold bay.
    - `JarShoulder` — upper label bumper ridge + multi-step curved blow-molded shoulder ending at a neck step shelf.
    - `JarNeck` — visible shadow-gap reveal collar + molded inner neck cylinder.
    - `CapGripRibs` — chamfered lower cap skirt flange, shadow recess groove, and clamped-trapezoidal (`tanh(2.45 * cos(N * theta))`) vertical grip ribs.
    - `CapCrown` — beveled upper shoulder and shallow recessed tamper-seal top deck.
    - `LabelSurface` — 5-ring (`96` radial segments) cylindrical sleeve preserving exact `u=0.5` at `+Z` alignment without mirroring.
  - Configured capacity-specific proportions across compact jars (`100g`, `250g`, `300g`), `500g`, `1kg`, wide-body muscular tubs (`2kg`, `2.5kg`, `3kg`), and `5kg` mega tub. Dimensions follow representative mockup catalog specifications in `static/models/packaging/manifest.json`.
- **`static/models/packaging/whey/*.glb`** and **`static/models/packaging/thumbnails/jar.png`**:
  - Regenerated all 9 Whey Protein Jar `.glb` assets (`whey_100g.glb` through `whey_5kg.glb`) and `jar.png` studio thumbnail.
- **`static/js/studio_3d.js`**:
  - Added `'hdpe'` subtle injection/blow-molded micro-pebble tangent-space `CanvasTexture` normal map in `getPackagingNormalMap('hdpe')`.
  - Updated `_normalMapForMaterial()`, `_buildPlasticScale()`, `loadPackagingGlbModel()`, and `applyPbrMaterialFinish()` so HDPE jar/bottle bodies and injection-molded caps display realistic soft reflections (`Matte`, `Glossy`, `Satin`, `Soft Touch`, `Frosted`) without flat gray washout on black plastic.
- **`static/js/studio_core.js`**:
  - Adjusted `openImageAsFullLabel()` auto-category threshold from `aspect < 2.2` to `aspect < 1.65` so importing horizontal `~2.1:1` whey labels stays on the selected **Protein Jar** instead of switching to **Bottle**.
- **`scratch/test_protein_jar_upgrade.py`**:
  - Added automated Playwright + WebGL verification suite (`tests/reports/jar_upgrade/`).

## Verified Test Results
- `python scratch/test_protein_jar_upgrade.py`: **10/10 PASSED** (verified mesh anatomy `BottomRing`, `JarBody`, `JarShoulder`, `JarNeck`, `CapGripRibs`, `CapCrown`, `LabelSurface`; default `GOMZI Whey 1kg` + `tests/fixtures/label_essential_whey.jpg`; Black+Red, Black+Black, White+White HDPE; Matte vs Glossy PBR; Front/Back/Left/Right/Top/`360°`; `250g`–`5kg` independent proportions & framing; Live Sync texture UUID refresh; 2K/4K PNG export; zero JS page errors).
- `python scratch/test_3d_wrapping_e2e.py`: **9 PASSED, 0 FAILED** (Sachet, Pouch, Box, Bottle non-regression, UI preservation).
- `python scratch/run_final_acceptance_tests.py`: **30 PASSED, 0 FAILED** (full studio acceptance suite).

## Known Behavior / Notes
- Existing dimensions (`dia`, `h`, `label_w`, `label_h`) follow representative mockup catalog specs in `static/models/packaging/manifest.json` rather than physical CAD caliper measurements of a third-party mold.
- Full-bleed uploads with pre-existing vertical margin borders inside the source raster image (such as the outer black border artifact at the edges of `tests/fixtures/label_essential_whey.jpg`) appear verbatim at the back `theta = ±pi` seam when wrapped `360°` around the cylinder.
