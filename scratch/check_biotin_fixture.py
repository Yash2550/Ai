import cv2
import os

path = r"C:\Users\yashm\.gemini\antigravity\brain\f2c8165e-4c1c-4b8e-9e81-840977aaf3eb\.user_uploaded\media_1795505206276_7b8e68ca.jpg"
img = cv2.imread(path)
print("Shape:", img.shape)
# Save test copy into static/fixtures/biotin_label.png for testing
os.makedirs("static/fixtures", exist_ok=True)
# The image shows Pacdora screen with Biotin label. Let's crop the actual label from the center canvas!
# In 1024x576 or 1920x1080:
h, w = img.shape[:2]
print(f"Dimensions: {w} x {h}")
cv2.imwrite("static/fixtures/user_screenshot_biotin.jpg", img)
