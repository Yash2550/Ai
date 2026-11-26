import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from reconstruction_engine import (
    probe_system_capabilities,
    reconstruct_flattened_label,
)

print("CAPS:", json.dumps(probe_system_capabilities(), indent=2))
with open("static/fixtures/biotin_sample_label.png", "rb") as f:
    b = f.read()

res = reconstruct_flattened_label(b, width_mm=162.0, height_mm=65.0, use_vision=True)
print("STATS:", json.dumps(res["stats"], indent=2))
print("VISION PROVIDER:", res.get("vision_provider"))
print("VECTOR ONLY BG:", res.get("vector_only_background"))
print("WARNINGS:", res.get("warnings"))
print("OBJECTS COUNT:", len(res["raw_objects"]))
for o in res["raw_objects"]:
    if o["type"] == "textbox":
        t_clean = o["text"].replace("\n", " / ")
        print(f"  TEXT [{o['layerCategory']}] '{t_clean}' size={o['fontSize']} col={o['fill']} font={o['fontFamily']}/{o['fontWeight']} conf={o.get('ocrConfidence')}")
    else:
        print(f"  SHAPE/VEC [{o['layerCategory']}] type={o['type']} name={o['name']} fill={o.get('fill') if isinstance(o.get('fill'), str) else type(o.get('fill')).__name__}")
