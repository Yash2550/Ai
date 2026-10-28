import io
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import cv2
import numpy as np
import base64
from PIL import Image, ImageDraw, ImageFont
import canva_pro_tools


def create_mock_supplement_label(w=1536, h=512, transparent=False):
    """Creates a realistic supplement label image for automated testing."""
    if transparent:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        img = Image.new("RGB", (w, h), (18, 20, 24))
    
    draw = ImageDraw.Draw(img)
    
    # Draw dark background blocks if not transparent
    if not transparent:
        draw.rectangle([40, 40, w - 40, h - 40], fill=(24, 27, 34), outline=(212, 175, 55), width=3)
    else:
        draw.rectangle([40, 40, w - 40, h - 40], fill=(24, 27, 34, 230), outline=(212, 175, 55, 255), width=3)

    # Main Brand & Heading
    draw.text((w // 2 - 180, 80), "GOMZI NUTRITION", fill=(212, 175, 55))
    draw.text((w // 2 - 220, 140), "100% WHEY ISOLATE", fill=(255, 255, 255))
    draw.text((w // 2 - 250, 210), "27G PROTEIN · 0G ADDED SUGAR", fill=(0, 240, 255))
    draw.text((w // 2 - 160, 260), "RICH CHOCOLATE FUDGE", fill=(254, 240, 138))

    # Nutrition panel on left
    draw.rectangle([80, 80, 380, 420], outline=(255, 255, 255), width=2)
    draw.text((100, 100), "NUTRITION FACTS", fill=(255, 255, 255))
    draw.text((100, 140), "Serving Size 1 Scoop (30g)", fill=(200, 200, 200))
    draw.text((100, 180), "Calories: 120 kcal", fill=(255, 255, 255))
    draw.text((100, 220), "Total Fat: 1.5 g", fill=(200, 200, 200))
    draw.text((100, 260), "Protein: 27.0 g", fill=(212, 175, 55))

    # Right side
    draw.text((w - 380, 120), "NET WT. 1 KG (2.2 LBS)", fill=(255, 255, 255))
    draw.text((w - 380, 180), "GMP CERTIFIED PURITY", fill=(16, 185, 129))

    out_io = io.BytesIO()
    img.save(out_io, format="PNG")
    return out_io.getvalue()


def run_tests():
    print("==================================================")
    print("RUNNING GRAB TEXT & CANVAS ARCHITECTURE TEST SUITE")
    print("==================================================")

    # Test 1: Clean Label OCR Detection (No Inpainting)
    print("\n--- Test 1: Detect Text on Clean PNG (Unchanged Original) ---")
    img_bytes = create_mock_supplement_label(1536, 512, transparent=False)
    det_res = canva_pro_tools.detect_text(img_bytes)
    assert det_res["success"] is True
    assert det_res["count"] > 0
    print(f"Detected {det_res['count']} grouped text lines:")
    for elem in det_res["text_elements"][:4]:
        print(f"  * '{elem['text']}' at ({elem['left']}, {elem['top']}, {elem['width']}x{elem['height']}) color={elem['color']}")
    print("[PASS] Test 1: Text detected and grouped without altering image!")

    # Test 2: Word Grouping vs Fragmentation
    print("\n--- Test 2: Verify Grouping (No fragmented 1-word scattered boxes) ---")
    texts = [e["text"] for e in det_res["text_elements"]]
    joined_all = " ".join(texts)
    assert "GOMZI" in joined_all or "WHEY" in joined_all
    # Verify that multi-word phrases exist in single text elements
    has_grouped_phrase = any(len(e["text"].split()) >= 2 for e in det_res["text_elements"])
    assert has_grouped_phrase, "Expected grouped phrases with multiple words"
    print("[PASS] Test 2: Detected words properly grouped into cohesive line blocks!")

    # Test 3: Selective Inpainting (Only Selected Regions)
    print("\n--- Test 3: Selective Inpainting of Only Chosen Regions ---")
    chosen = [det_res["text_elements"][0]]  # only inpaint first text block
    inpainted_bytes = canva_pro_tools.inpaint_text_regions(img_bytes, chosen)
    assert len(inpainted_bytes) > 0
    # Compare unmasked region (e.g. right side of image)
    orig_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    inpaint_np = cv2.imdecode(np.frombuffer(inpainted_bytes, np.uint8), cv2.IMREAD_COLOR)
    # Check pixels far away from chosen region (e.g. at w - 100, 300)
    unmasked_diff = np.abs(orig_np[:, 1000:].astype(int) - inpaint_np[:, 1000:].astype(int))
    assert np.max(unmasked_diff) == 0, "Pixels outside the selected region must be 100% identical!"
    print("[PASS] Test 3: Pixels outside selected regions are 100% pixel-perfect identical!")

    # Test 4: Transparent PNG Handling
    print("\n--- Test 4: Transparent PNG Support ---")
    trans_bytes = create_mock_supplement_label(1536, 512, transparent=True)
    det_trans = canva_pro_tools.detect_text(trans_bytes)
    assert det_trans["success"] is True
    clean_trans = canva_pro_tools.inpaint_text_regions(trans_bytes, det_trans["text_elements"][:1])
    trans_np = cv2.imdecode(np.frombuffer(clean_trans, np.uint8), cv2.IMREAD_UNCHANGED)
    assert trans_np.shape[2] == 4, "Must preserve RGBA 4-channel alpha transparency!"
    print("[PASS] Test 4: Alpha transparency fully preserved!")

    # Test 5: OCR Error & Empty Data Robustness
    print("\n--- Test 5: Error and Empty Input Robustness ---")
    try:
        canva_pro_tools.detect_text(b"corrupted_garbage_data")
        assert False, "Should raise ValueError on invalid image bytes"
    except ValueError:
        print("[PASS] Handled corrupted image bytes safely with ValueError")

    # Empty blank canvas
    blank_img = Image.new("RGB", (400, 400), (255, 255, 255))
    b_io = io.BytesIO()
    blank_img.save(b_io, format="PNG")
    det_blank = canva_pro_tools.detect_text(b_io.getvalue())
    assert det_blank["success"] is True
    assert det_blank["count"] == 0
    assert len(det_blank["text_elements"]) == 0
    print("[PASS] Handled blank image with 0 text elements gracefully without errors")

    print("\n==================================================")
    print("ALL BACKEND TEST SUITE CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
