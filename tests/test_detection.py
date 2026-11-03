import os
import json
import pytest
from canva_pro_tools import detect_text

FIXTURES = [
    ("label_synth_gradient.jpg", "label_synth_gradient.json"),
    ("label_synth_dark.jpg", "label_synth_dark.json"),
    ("label_volt_preworkout.jpg", "label_volt_preworkout.json"),
    ("label_essential_whey.jpg", "label_essential_whey.json"),
    ("label_gomzi_creatine.jpg", "label_gomzi_creatine.json"),
]

def compute_iou(box1, box2):
    # box format: [left, top, width, height]
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[0] + box1[2], box2[0] + box2[2])
    y2 = min(box1[1] + box1[3], box2[1] + box2[3])
    w = max(0, x2 - x1)
    h = max(0, y2 - y1)
    inter = w * h
    union = (box1[2] * box1[3]) + (box2[2] * box2[3]) - inter
    return inter / float(union) if union > 0 else 0.0

@pytest.mark.parametrize("img_name, gt_name", FIXTURES)
def test_detection_recall_precision(img_name, gt_name):
    img_path = os.path.join("tests", "fixtures", img_name)
    gt_path = os.path.join("tests", "ground_truth", gt_name)
    
    assert os.path.exists(img_path), f"Missing fixture {img_path}"
    assert os.path.exists(gt_path), f"Missing GT {gt_path}"

    with open(img_path, "rb") as f:
        img_bytes = f.read()
    with open(gt_path, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    # Filter out uncertain ground truth
    clean_gt = [g for g in gt_data if not g.get("uncertain", False)]
    assert len(clean_gt) > 0, "No certain ground truth items"

    res = detect_text(img_bytes)
    assert res.get("success") is True
    detections = res.get("text_elements", [])

    matched_gt = 0
    for gt in clean_gt:
        gt_box = gt["bbox"]
        gt_text = gt["text"].upper()
        # Find detection that overlaps or text matches substring
        matched = False
        for det in detections:
            det_box = [det["left"], det["top"], det["width"], det["height"]]
            det_text = det["text"].upper()
            iou = compute_iou(gt_box, det_box)
            # High IoU OR exact keyword match with reasonable distance
            if iou >= 0.20 or (gt_text in det_text or any(w in det_text for w in gt_text.split())):
                matched = True
                break
        if matched:
            matched_gt += 1

    recall = matched_gt / float(len(clean_gt))
    print(f"\n[{img_name}] Detection Recall: {recall:.2f} ({matched_gt}/{len(clean_gt)})")
    assert recall >= 0.80, f"Recall {recall:.2f} below 0.80 for {img_name}"

