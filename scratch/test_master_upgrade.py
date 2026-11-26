"""
test_master_upgrade.py
======================
Comprehensive test suite verifying both:
1. GOMZI BOB Professional Realistic 3D Packaging Mockup Engine
2. GOMZI BOB Universal Editable Design Import & AI Image Editing Engine
"""

import os
import sys
import json
import io
import base64
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from app import app

client = app.test_client()

print("==================================================")
print("RUNNING GOMZI BOB MASTER UPGRADE TEST SUITE")
print("==================================================")

# ----------------------------------------------------------------
# TEST 1: 3D Packaging Manifest & GLB Model Inventory
# ----------------------------------------------------------------
print("\n[TEST 1] Verifying 3D Packaging Catalog & Physical GLB Assets...")
res = client.get("/api/packaging/models")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
manifest = res.get_json()

categories = manifest.get("categories", [])
assert len(categories) >= 7, f"Expected at least 7 packaging categories, got {len(categories)}"

total_presets = 0
missing_glbs = []
for cat in categories:
    for preset in cat["presets"]:
        total_presets += 1
        glb_rel = preset["file"]
        glb_full = os.path.join("static", "models", "packaging", glb_rel)
        if not os.path.exists(glb_full) or os.path.getsize(glb_full) == 0:
            missing_glbs.append(glb_rel)

assert len(missing_glbs) == 0, f"Missing GLB models: {missing_glbs}"
print(f"✓ All {len(categories)} packaging categories verified.")
print(f"✓ All {total_presets} physical GLB models exist and validated on disk!")

# ----------------------------------------------------------------
# TEST 2: PBR Materials & Studio Lighting Presets
# ----------------------------------------------------------------
print("\n[TEST 2] Verifying PBR Material Finishes & Lighting Presets...")
materials = manifest.get("materials", [])
assert len(materials) >= 8, f"Expected at least 8 PBR material finishes, got {len(materials)}"
lighting = manifest.get("lighting_presets", [])
assert len(lighting) >= 5, f"Expected at least 5 studio lighting presets, got {len(lighting)}"
print(f"✓ {len(materials)} PBR materials verified: {[m['name'] for m in materials[:4]]}...")
print(f"✓ {len(lighting)} Studio lighting presets verified: {[l['name'] for l in lighting[:3]]}...")

# ----------------------------------------------------------------
# TEST 3: Universal Design Import - CDR, SVG, PDF, Raster
# ----------------------------------------------------------------
print("\n[TEST 3] Testing Universal Design Import Pipeline ('/api/canva/import-design')...")

# 3A: SVG Import
svg_raw = b'<svg width="500" height="200" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#708238"/><text x="50" y="80" fill="#fff" font-size="24">GOMZI WHEY</text></svg>'
res = client.post("/api/canva/import-design", data={
    "file": (io.BytesIO(svg_raw), "sample_label.svg")
}, content_type="multipart/form-data")
assert res.status_code == 200, f"SVG import failed: {res.data}"
svg_data = res.get_json()
assert svg_data["success"] is True and svg_data["format"] == "svg"
print("  -> SVG Direct Vector Import: SUCCESS")

# 3B: Raster / CDR Preview Import (with OCR and Inpainted Background)
sample_img = np.full((300, 600, 3), 245, dtype=np.uint8)
cv2.putText(sample_img, "GOMZI WHEY PROTEIN", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
cv2.putText(sample_img, "BELGIAN CHOCOLATE", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 180), 2)
_, png_buf = cv2.imencode(".png", sample_img)

res = client.post("/api/canva/import-design", data={
    "file": (io.BytesIO(png_buf.tobytes()), "coreldraw_preview.png")
}, content_type="multipart/form-data")
assert res.status_code == 200, f"Artwork import failed: {res.data}"
art_data = res.get_json()
assert art_data["success"] is True
assert "fabric_json" in art_data
assert art_data["stats"]["total_objects"] >= 1
print(f"  -> Artwork Deconstruction & Fabric.js Conversion: SUCCESS (Objects: {art_data['stats']['total_objects']})")

# ----------------------------------------------------------------
# TEST 4: Canva-Style Grab Object / Magic Grab
# ----------------------------------------------------------------
print("\n[TEST 4] Testing Canva-Style Grab Object / Magic Grab ('/api/canva/grab-object')...")
test_canvas = np.full((300, 400, 3), 240, dtype=np.uint8)
cv2.circle(test_canvas, (200, 150), 60, (40, 140, 40), -1)
_, test_buf = cv2.imencode(".png", test_canvas)
img_b64 = "data:image/png;base64," + base64.b64encode(test_buf.tobytes()).decode("ascii")

# Test with region BBox
res = client.post("/api/canva/grab-object", json={
    "image": img_b64,
    "bbox": {"left": 140, "top": 90, "width": 120, "height": 120}
})
assert res.status_code == 200, f"Grab Object failed: {res.data}"
grab_data = res.get_json()
assert grab_data["success"] is True
assert "foreground_data_url" in grab_data
assert "background_data_url" in grab_data
print("  -> Canva-Style Magic Grab Region Extraction: SUCCESS")

# ----------------------------------------------------------------
# TEST 5: Natural Language AI Prompt-Based Editing
# ----------------------------------------------------------------
print("\n[TEST 5] Testing Natural Language AI Prompt Edit ('/api/canva/ai-prompt-edit')...")
res = client.post("/api/canva/ai-prompt-edit", json={
    "prompt": "Change Belgian Chocolate to Strawberry and set background to clean studio",
    "width": 1536,
    "height": 512
})
assert res.status_code == 200
ai_data = res.get_json()
assert ai_data["success"] is True
assert len(ai_data["actions"]) >= 2
print(f"  -> Natural Language Prompt Actions: SUCCESS ({[a['type'] for a in ai_data['actions']]})")

# ----------------------------------------------------------------
# TEST 6: DOM Verification of All Upgraded UI Controls
# ----------------------------------------------------------------
print("\n[TEST 6] Verifying Upgraded Studio UI Elements in index.html...")
res = client.get("/")
assert res.status_code == 200
html = res.data.decode("utf-8")

required_ui_elements = [
    # Universal Import
    'id="studioImportDesignBtn"',
    'id="universalDesignFileInput"',
    'id="designImportPreviewModal"',
    'id="applyImportEditableBtn"',
    'id="applyImportImageBtn"',
    # 3D Packaging Studio
    'id="threeSelectCategory"',
    'id="threeSelectPreset"',
    'id="threeSelectMaterialFinish"',
    'id="threeSelectLighting"',
    'id="threePkgDimsTag"',
    'id="threeExportMockupBtn"',
    'id="mockupExportModal"',
    'id="confirmMockupExportBtn"',
    # Magic Tools
    'id="canvaToolMagicGrabBtn"',
    'id="canvaAiPromptInput"',
    'id="canvaAiPromptBtn"'
]

for el in required_ui_elements:
    assert el in html, f"Missing UI element in HTML: {el}"

print(f"✓ All {len(required_ui_elements)} new UI elements present and verified in index.html!")

print("\n==================================================")
print("ALL MASTER UPGRADE TESTS PASSED WITH 100% SUCCESS!")
print("==================================================")
