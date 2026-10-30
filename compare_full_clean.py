import cv2
import numpy as np

orig = cv2.imread('static/uploads/canva_2b11e372be.png')
clean = cv2.imread('test_full_clean.png')

# In user image, there's a big white washed out patch around x=700..1200, y=100..300
print("Orig patch mean:", np.mean(orig[100:300, 700:1200]))
print("Clean patch mean:", np.mean(clean[100:300, 700:1200]))

# Check if there are huge pure-white blobs in clean
diff = np.abs(orig.astype(float) - clean.astype(float))
print("Diff mean across full label:", np.mean(diff))
print("Changed pixels:", np.sum(diff > 0) / diff.size * 100)

