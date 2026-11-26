import cv2
import numpy as np

img = cv2.imread("static/fixtures/user_screenshot_biotin.jpg")
h, w = img.shape[:2]

# The label is the light purple/white rectangular box in the center
# Let's crop x: 260 to 790, y: 240 to 475
label_crop = img[248:472, 266:786]
cv2.imwrite("static/fixtures/biotin_sample_label.png", label_crop)
print(f"Biotin sample label created: {label_crop.shape[1]}x{label_crop.shape[0]} px")
