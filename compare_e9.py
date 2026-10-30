import cv2, numpy as np

img = cv2.imread('static/uploads/canva_e926c887eb.png')
# Check user's uploaded screenshot vs canva_e926c887eb
user_screen = cv2.imread(r'C:/Users/yashm/.gemini/antigravity/brain/f2c8165e-4c1c-4b8e-9e81-840977aaf3eb/.user_uploaded/media_1793339412295_2e8af37b.jpg')

print("e9 shape:", img.shape)
print("user_screen shape:", user_screen.shape)

# Let's check color in the area above ESSENIIAL / WHEY in canva_e926c887eb
# in user_screen there is a huge white blob where N GOMZI was, and between WHEY and NUTRITION FACTS
print("e9 center patch min/max:", np.min(img[200:400, 800:1200]), np.max(img[200:400, 800:1200]))

