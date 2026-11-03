import os
import cv2
import numpy as np
from canva_pro_tools import inpaint_text_regions

def test_inpainting_untouched_background():
    img_path = os.path.join("tests", "fixtures", "label_synth_gradient.jpg")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    orig_bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    h, w = orig_bgr.shape[:2]

    # Test inpainting one single line in center
    regions = [
        {"left": 650, "top": 120, "width": 500, "height": 80}
    ]

    inpainted_bytes = inpaint_text_regions(img_bytes, regions)
    inpainted_bgr = cv2.imdecode(np.frombuffer(inpainted_bytes, np.uint8), cv2.IMREAD_COLOR)

    # 1. Background outside bounding box MUST be identical (difference <= 1.0)
    mask_box = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(mask_box, (640, 110), (640 + 520, 110 + 100), 255, -1)
    
    outside_orig = orig_bgr[mask_box == 0]
    outside_inp = inpainted_bgr[mask_box == 0]
    mean_abs_diff = np.mean(np.abs(outside_orig.astype(float) - outside_inp.astype(float)))

    print(f"Mean absolute difference outside box: {mean_abs_diff:.4f}")
    assert mean_abs_diff <= 1.0, f"Background was touched! Diff={mean_abs_diff}"

def test_inpainting_no_flat_blob():
    img_path = os.path.join("tests", "fixtures", "label_synth_gradient.jpg")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    regions = [
        {"left": 650, "top": 120, "width": 500, "height": 80}
    ]
    inpainted_bytes = inpaint_text_regions(img_bytes, regions)
    inpainted_bgr = cv2.imdecode(np.frombuffer(inpainted_bytes, np.uint8), cv2.IMREAD_COLOR)

    # Inpainted region should preserve texture/gradient: std dev must not collapse to 0
    roi = inpainted_bgr[120:200, 650:1150]
    std_dev = np.std(roi)
    print(f"Inpainted ROI standard deviation: {std_dev:.2f}")
    assert std_dev > 5.0, f"Inpainted region is a flat uniform blob! std_dev={std_dev}"

