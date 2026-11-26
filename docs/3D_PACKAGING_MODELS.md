# GOMZI BOB — 3D Packaging Models & PBR Visualization Architecture

**Asset Manifest:** [`static/models/packaging/manifest.json`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/models/packaging/manifest.json)  
**Procedural GLB Builder:** [`scripts/generate_packaging_models.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/generate_packaging_models.py)  
**Studio Thumbnail Renderer:** [`scripts/render_3d_thumbnails.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/render_3d_thumbnails.py)  
**WebGL Engine:** [`static/js/studio_3d.js`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/js/studio_3d.js)

---

## 1. WebGL Rendering Pipeline (`studio_3d.js`)

- **Loader & Scene:** Uses `THREE.GLTFLoader` to load local binary glTF 2.0 (`.glb`) models inside `#threeCanvasHost` with `THREE.OrbitControls` (damped orbit, zoom, pan).
- **Color Management & Lighting:**
  - Configured with `THREE.ACESFilmicToneMapping` (`toneMappingExposure = 1.05`) and `THREE.sRGBEncoding`.
  - All `THREE.Color` hex values passed to materials pass through `.convertSRGBToLinear()` via `_makeSrgbColor()` so dark HDPE black, forest olive, and cream finishes maintain rich saturation instead of washing out.
  - Procedural studio environment map generated via `THREE.PMREMGenerator` (`createStudioEnvironmentTexture()`) with warm/cool studio lightboxes.
- **UV Orientation:** Dynamic label `THREE.CanvasTexture` sets `flipY = false` and `encoding = THREE.sRGBEncoding`, matching glTF 2.0 top-down UV coordinates (`[0..1]`), with `Live Sync` reflecting every Fabric.js text/logo/artwork change onto the 3D `LabelSleeve` mesh in real time.

---

## 2. Packaging Categories & 25 Active Capacity Presets

| Category (`id`) | Active Presets (`25`) | Representative Physical Geometry & Specs |
| :--- | :--- | :--- |
| **Protein Jar (`jar`)** | `9` (`jar_100g`, `jar_250g`, `jar_300g`, `jar_500g`, `jar_1kg`, `jar_2kg`, `jar_2_5kg`, `jar_3kg`, `jar_5kg`) | Smooth 6-step spline shoulders, waisted base contour, 72-ridge ribbed screw lid, neck collar (`1kg`: `Dia 144mm × H 215mm`, `Label 452×142mm`) |
| **Pouch (`pouch`)** | `5` (`pouch_100g`, `pouch_250g`, `pouch_500g`, `pouch_1kg`, `pouch_2kg`) | Stand-up gusseted foil/laminate pouch with heat-sealed side/top crimp seams and offset non-z-fighting `ZipperSeal` (`100g`: `110×170×60mm`) |
| **Sachet (`sachet`)** | `3` (`sachet_70x110`, `sachet_protein`, `stickpack_5g`) | 3-side / 4-side crimped single-serve sachet & stickpack (`70×110×16mm`, `80×130×18mm`, `30×125×12mm`) |
| **Bottle (`bottle`)** | `5` (`capsule_30`, `capsule_60`, `capsule_90`, `capsule_120`, `capsule_180`) | Rounded supplement capsule bottles with smooth shoulder curve & tamper-evident ribbed cap (`30 caps`: `Dia 46mm × H 82mm`, `Label 144×48mm`) |
| **Box (`box`)** | `3` (`box_supplement`, `box_square`, `box_cosmetic`) | True 24-vertex UV-mapped 6-face outer carton sleeves & fold-flap crease accents (`Standard`: `120×180×100mm`) |

> Note: `static/models/packaging/` contains **33 total `.glb` files** across subdirectories (25 active presets referenced in `manifest.json` + 8 legacy/extra format variants retained in disk storage) and **5 studio PNG thumbnails** under `static/models/packaging/thumbnails/` (`jar.png`, `pouch.png`, `sachet.png`, `bottle.png`, `box.png`).

---

## 3. Material Finishes, Lighting & Export

- **11 PBR Materials (`MeshPhysicalMaterial` / `MeshStandardMaterial`):** `matte`, `glossy`, `satin`, `soft_touch`, `transparent`, `frosted`, `metallic_foil`, `matte_foil`, `glossy_foil`, `kraft_paper`, `cardboard`.
- **4 Studio Lighting Presets:** `studio`, `soft`, `natural`, `dramatic`.
- **Camera Angle Controls & 360° Auto-Spin:** Instant camera transitions for `Front`, `Back`, `Left`, `Right`, `Top`, `360°`, plus `Reset` and Fullscreen.
- **High-Res Mockup Export (`export3DMockup()`):** Renders offscreen up to **4K (`4096×4096 px`)** in Transparent PNG, Studio Floor PNG, or Commercial JPG.
