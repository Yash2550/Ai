import cv2
import numpy as np
import canva_pro_tools

img_path = r"C:/Users/yashm/.gemini/antigravity/brain/f2c8165e-4c1c-4b8e-9e81-840977aaf3eb/.user_uploaded/media_1793339412295_2e8af37b.jpg"
with open(img_path, "rb") as f:
    b = f.read()

img = cv2.imread(img_path)
print("Image shape:", img.shape if img is not None else "None")

det = canva_pro_tools.detect_text(b)
print("Detected text count:", len(det.get("text_elements", [])))
for e in det.get("text_elements", [])[:15]:
    print(f"'{e['text']}': left={e['left']}, top={e['top']}, w={e['width']}, h={e['height']}")

