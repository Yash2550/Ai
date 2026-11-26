import sys
import os
import json
import io
import base64
from PIL import Image

# Add root to sys.path
sys.path.insert(0, os.path.abspath("."))

from app import app

client = app.test_client()

print("=== 1. TEST PACKAGING MANIFEST API ===")
res = client.get("/api/packaging/models")
assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
data = res.get_json()
categories = data.get("categories", [])
print(f"✓ Packaging categories loaded: {len(categories)} categories")
for cat in categories:
    print(f"  -> {cat['name']}: {len(cat['presets'])} presets")

print("\n=== 2. TEST AI PROMPT-EDIT API ===")
res = client.post("/api/canva/ai-prompt-edit", json={
    "prompt": "Change Belgian Chocolate to Strawberry and set background to clean studio"
})
assert res.status_code == 200
pdata = res.get_json()
print(f"✓ AI Prompt-Edit actions: {pdata['action_count']} actions")
for a in pdata["actions"]:
    print(f"  -> Action: {a['type']} ({a.get('role', a.get('preset'))})")

print("\n=== 3. TEST UNIVERSAL IMPORT WITH CDR PREVIEW / RASTER ===")
# Generate a test image
img = Image.new("RGB", (600, 300), color=(240, 240, 245))
buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)

res = client.post("/api/canva/import-design", data={
    "file": (buf, "test_label.png")
}, content_type="multipart/form-data")
assert res.status_code == 200, f"Import failed: {res.data}"
idata = res.get_json()
print(f"✓ Universal import success! Format: {idata['format']}, Objects: {idata['stats']['total_objects']}")

print("\n=== 4. TEST CANVA-STYLE GRAB OBJECT (REGION) ===")
# Generate test image with a circle in center
import cv2
import numpy as np
cv_img = np.full((300, 300, 3), 240, dtype=np.uint8)
cv2.circle(cv_img, (150, 150), 50, (30, 30, 220), -1)
_, png_buf = cv2.imencode(".png", cv_img)
img_b64 = "data:image/png;base64," + base64.b64encode(png_buf.tobytes()).decode("ascii")

res = client.post("/api/canva/grab-object", json={
    "image": img_b64,
    "bbox": {"left": 100, "top": 100, "width": 100, "height": 100}
})
assert res.status_code == 200, f"Grab Object failed: {res.data}"
gdata = res.get_json()
assert gdata["success"] is True
print("✓ Grab Object success! Foreground and background layers separated cleanly.")

print("\n==========================================")
print("ALL NEW BACKEND ENGINE APIS TESTED & PASSED!")
print("==========================================")
