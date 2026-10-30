import cv2
import numpy as np

# Let's inspect video_frame_3, 4, 5, 6, 7
for idx in [2, 3, 4, 5, 6, 7]:
    img = cv2.imread(f'video_frame_{idx}.png')
    h, w = img.shape[:2]
    # Crop canvas area
    # In full screen 1920x1080, canvas is centered
    cv2.imwrite(f'crop_vf_{idx}.png', img[150:850, 300:1650])
    print(f"Cropped vf_{idx}: {img.shape}")

