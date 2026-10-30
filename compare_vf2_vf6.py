import cv2
import numpy as np

vf2 = cv2.imread('vf2_canvas.png')
vf6 = cv2.imread('vf6_canvas.png')

# In vf2, is the text already in the center?
# Let's crop x=500..1000, y=100..400 in vf2 and vf6
cv2.imwrite('vf2_center.png', vf2[100:400, 500:1000])
cv2.imwrite('vf6_center_compare.png', vf6[100:400, 500:1000])

diff = cv2.absdiff(vf2, vf6)
print("Canvas diff sum between vf2 and vf6:", np.sum(diff))
cv2.imwrite('diff_vf2_vf6.png', diff)
print("Saved comparison images")

