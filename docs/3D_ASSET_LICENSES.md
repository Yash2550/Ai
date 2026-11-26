# GOMZI BOB — 3D Asset & Dependency Licenses

## 1. Locally Generated Packaging `.glb` Models

All 3D packaging geometry assets located under [`static/models/packaging/`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/static/models/packaging/) (33 `.glb` files and 5 rendered PNG thumbnails in `static/models/packaging/thumbnails/`) are **100% original procedural glTF 2.0 assets** generated deterministically inside this repository by:

- [`scripts/generate_packaging_models.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/generate_packaging_models.py)
- [`scripts/render_3d_thumbnails.py`](file:///d:/NEWWWW%20-%20Copy%20-%20Copy/scripts/render_3d_thumbnails.py)

**License & Provenance:**
- **Origin:** Authored directly in-house in pure Python (`struct` / `json` glTF 2.0 binary packer) using exact physical dimensions matching GOMZI NUTRITION packaging specifications.
- **Commercial Rights:** Full unrestricted internal & commercial usage, modification, and redistribution as part of the GOMZI BOB application.
- **External Model URLs:** **Zero external runtime 3D model URLs** or unverified third-party downloads are used.

---

## 2. Frontend Rendering & Graphics Libraries (Runtime CDN / Local)

| Library | Version | Purpose | License |
| :--- | :--- | :--- | :--- |
| **Three.js** (`three.min.js`, `OrbitControls.js`, `GLTFLoader.js`) | `r128` | WebGL 3D scene, GLB parsing, PBR materials, PMREM environment | MIT License |
| **Fabric.js** (`fabric.min.js`) | `5.3.1` | 2D interactive label canvas, layers, textboxes, vector groups | MIT License |
| **JsBarcode** (`JsBarcode.all.min.js`) | `3.11.5` | Real barcode rendering on packaging labels | MIT License |
| **Lucide Icons** (`lucide.min.js`) | `0.460.0` | UI SVG iconography | ISC License |
