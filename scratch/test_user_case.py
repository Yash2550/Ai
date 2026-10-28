import cv2
import numpy as np
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from canva_pro_tools import group_ocr_detections

ocr_data = [
    ([ [100, 100], [200, 100], [200, 120], [100, 120] ], 'Serving Size:', 0.95),
    ([ [220, 104], [380, 104], [380, 126], [220, 126] ], 'Total Carbohydrates: 0.0', 0.94),
    ([ [100, 124], [180, 124], [180, 144], [100, 144] ], 'Sachet [6 g]', 0.92),
    ([ [100, 148], [160, 148], [160, 168], [100, 168] ], 'g Fat:', 0.90),
]

res = group_ocr_detections(ocr_data, 1024, 1536)
print(f"Grouped into {len(res)} blocks:")
for r in res:
    print(f"  * text='{r['text']}' top={r['top']} h={r['height']} w={r['width']}")
