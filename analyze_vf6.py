import cv2

# Let's inspect video_frame_3 (before/during grab) and video_frame_6 (after moving text)
vf3 = cv2.imread('video_frame_3.png')
vf6 = cv2.imread('video_frame_6.png')

# In vf6, where is the text box that was moved?
# Let's find out what text was moved:
# Crop the upper-left, center, and sidebar of vf6
cv2.imwrite('vf6_sidebar.png', vf6[:, :400])
cv2.imwrite('vf6_canvas.png', vf6[120:900, 400:1850])
print("Saved vf6_sidebar.png and vf6_canvas.png")

