import os
import json
import pytest
from canva_pro_tools import detect_text

def test_textbox_geometry_and_color():
    img_path = os.path.join("tests", "fixtures", "label_synth_gradient.jpg")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    res = detect_text(img_bytes)
    assert res["success"] is True
    elements = res["text_elements"]
    assert len(elements) > 0

    for elem in elements:
        # 1. Height must be positive and fontSize must be reasonably scaled
        assert elem["height"] > 0
        assert elem["fontSize"] > 8
        # 2. Color must be valid hex code
        assert elem["color"].startswith("#")
        assert len(elem["color"]) == 7
        # 3. Bounding box coordinates must be within image bounds
        assert elem["left"] >= 0
        assert elem["top"] >= 0
        assert elem["left"] + elem["width"] <= res["image_width"]
        assert elem["top"] + elem["height"] <= res["image_height"]

