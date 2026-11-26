import cv2
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from cdr_import_engine import convert_artwork_to_editable_fabric

with open("static/fixtures/biotin_sample_label.png", "rb") as f:
    img_bytes = f.read()

res = convert_artwork_to_editable_fabric(img_bytes, width_mm=162.0, height_mm=65.0)

print("Biotin conversion result:")
print(f"Canvas size: {res['canvas_width']} x {res['canvas_height']}")
print(f"Detected text elements: {res['text_count']}")
for obj in res["fabric_json"]["objects"]:
    if obj["type"] == "textbox":
        print(f"  -> Text: '{obj['text']}', color: {obj['fill']}, fontSize: {obj['fontSize']}")
