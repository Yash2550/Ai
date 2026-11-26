# GOMZI BOB — Full Label Import, CDR/SVG/PDF Parsing & Print Export Report

**Import Engine:** [`cdr_import_engine.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/cdr_import_engine.py)  
**Export Master Renderer:** [`canva_pro_tools.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/canva_pro_tools.py) (`render_master_export`)  
**Flask Endpoints:** `POST /api/canva/import-design`, `POST /api/canva/export-master`, `GET /download/<filename>/<fmt>` in [`app.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/app.py)  
**Frontend Handlers:** `openImageAsFullLabel()`, `addStickerToCanvas()`, `processUniversalDesignFile()`, `initExportControls()` in [`static/js/studio_core.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_core.js)

---

## 1. Strict Separation: Full Label Replacement vs. Sticker/Logo Insertion

Previously, uploading a full packaging label (e.g., a complete `BIOTIN` label image) dropped a tiny floating thumbnail on top of the active Whey template. This is cleanly resolved into distinct workflows:

| Workflow | Trigger Control | Canvas Behavior | 3D Packaging Sync |
| :--- | :--- | :--- | :--- |
| **Upload Full Label (Replace Artwork)** | `Import` rail -> **Upload Full Label** (`openImageAsFullLabel()`) | Clears previous template objects, preserves or adapts artboard dimensions proportionally (`max 1536 px`), places artwork at `(0, 0)` spanning `100%` artboard width/height, sets document title | Immediately updates 3D `LabelSleeve` `CanvasTexture` |
| **Insert Image / Logo / Sticker** | `Uploads` / `Images` rail (`addStickerToCanvas()`) | Appends a movable, scalable graphic object onto existing artwork without replacing the background label | Updates live overlay on 3D preview |

---

## 2. Universal Design Importer (`POST /api/canva/import-design`)

`detect_file_type()` inspects file magic bytes and filenames across supported formats:
- **SVG (`fmt == "svg"`):** Sanitizes scripts/dangerous tags (`sanitize_svg()`) and loads editable Fabric vector objects (`fabric.loadSVGFromString`).
- **CorelDRAW (`cdr` / `cdr_legacy`):**
  - `extract_cdr_package()` parses modern ZIP-based `.cdr` containers for embedded preview rasters (`previews/thumbnail.png`, `metadata/thumbnails/page1.png`, etc.) and physical XML document dimensions (`width_mm`, `height_mm`).
  - `convert_artwork_to_editable_fabric()` extracts detected text regions via EasyOCR, repairs the background cleanly with OpenCV Telea inpainting, and returns editable Fabric.js `Textbox` JSON alongside the preserved background image.
  - **Honest Capability Note:** Legacy proprietary RIFF binary-only `.cdr` files that do not embed a preview raster cannot have proprietary closed binary vector curves natively parsed without an external CorelDRAW COM/CDR decoder; warnings from `extract_cdr_package()` are returned transparently to the UI.
- **PDF / AI / EPS / Raster (`png`, `jpg`, `jpeg`, `webp`):** Processed via `processUniversalDesignFile()` and converted cleanly for full-artwork editing or object decomposition.

---

## 3. Print-Ready & Exchange Export Formats (`initExportControls()`)

Triggered from the top bar **Export** dropdown (`#canvaExportDropdown`), excluding non-artwork guides (`isGuideLine`, `isTempOcrBox`, `excludeFromExport`):

1. **PNG Print Master (`canvaExportPngBtn`)** — Calls `POST /api/canva/export-master` (`format='png'`, `target_max_dim=9600`, `300 DPI`).
2. **JPG High Resolution (`canvaExportJpgBtn`)** — Calls `POST /api/canva/export-master` (`format='jpg'`, `300 DPI`).
3. **SVG Vector Artwork (`canvaExportSvgBtn`)** — Generates clean scalable SVG via `canvaCanvas.toSVG()` and downloads `<title>.svg`.
4. **PDF Print Package (`canvaExportPdfBtn`)** — Calls `POST /api/canva/export-master` (`format='pdf'`).
5. **CorelDRAW Exchange (`canvaExportCdrBtn`)** — Calls `POST /api/canva/export-master` (`format='cdr'`) and delivers a CorelDRAW-importable bundle (`.zip` containing vector SVG + 300 DPI PDF/raster print files).
6. **Editable Project JSON (`canvaExportJsonBtn`)** — Exports lossless `toDatalessJSON()` preserving custom object properties (`assetType`, `isBrandLogo`, `name`, etc.).
7. **3D Mockup Export (`Export 3D Mockup (PNG / 4K)`)** — Captures offscreen WebGL renders at `1024×1024`, `2048×2048`, or `4096×4096` px in Transparent PNG, Studio Floor PNG, or Commercial JPG.
