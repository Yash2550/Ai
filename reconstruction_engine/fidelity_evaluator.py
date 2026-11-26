"""
Visual Fidelity & Vector Quality Evaluator.
Compares reconstructed label canvas renders against original artwork via SSIM,
pixel color difference, text fidelity, and vector-to-raster ratio.
"""

import io
import cv2
import numpy as np
from PIL import Image

try:
    from skimage.metrics import structural_similarity as compute_ssim
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


def evaluate_visual_fidelity(original_bytes: bytes, rendered_bytes: bytes, stats: dict | None = None) -> dict:
    """Computes SSIM, PSNR/MAE, and color consistency between original and reconstructed preview."""
    arr1 = np.frombuffer(original_bytes, np.uint8)
    arr2 = np.frombuffer(rendered_bytes, np.uint8)
    im1 = cv2.imdecode(arr1, cv2.IMREAD_COLOR)
    im2 = cv2.imdecode(arr2, cv2.IMREAD_COLOR)
    if im1 is None or im2 is None:
        return {"ssim": None, "mae": None, "status": "unavailable"}

    h, w = im1.shape[:2]
    if im2.shape[:2] != (h, w):
        im2 = cv2.resize(im2, (w, h), interpolation=cv2.INTER_AREA)

    g1 = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)

    ssim_val = float(compute_ssim(g1, g2)) if HAS_SKIMAGE else 0.0
    mae = float(np.mean(np.abs(im1.astype(np.float32) - im2.astype(np.float32))))
    psnr = float(cv2.PSNR(im1, im2)) if mae > 0.01 else 99.0

    # Grid 3x1 (Left, Center, Right) regional fidelity check
    thirds = [(0, w // 3, "left"), (w // 3, (2 * w) // 3, "center"), ((2 * w) // 3, w, "right")]
    region_ssim = {}
    for x0, x1, name in thirds:
        if HAS_SKIMAGE and (x1 - x0) >= 16:
            region_ssim[name] = round(float(compute_ssim(g1[:, x0:x1], g2[:, x0:x1])), 3)

    return {
        "ssim": round(ssim_val, 4),
        "psnr_db": round(psnr, 2),
        "mean_rgb_delta": round(mae, 2),
        "region_ssim": region_ssim,
        "editable_objects": (stats or {}).get("text_objects", 0) + (stats or {}).get("vector_objects", 0),
        "retained_rasters": (stats or {}).get("retained_rasters", 0),
        "status": "good" if ssim_val >= 0.72 else "review_recommended",
    }
