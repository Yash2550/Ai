import os
import cv2
import numpy as np

# Initialize EasyOCR Reader globally so it doesn't reload on every request
READER = None

def get_reader():
    global READER
    if READER is None:
        import easyocr
        # Use GPU if available, fallback to CPU
        READER = easyocr.Reader(['en'], gpu=True)
    return READER

def extract_text_color(crop):
    """
    Extract the dominant foreground text color from an image crop using Otsu thresholding.
    """
    if crop is None or crop.size == 0 or crop.shape[0] < 3 or crop.shape[1] < 3:
        return "#ffffff"
    try:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Foreground text typically occupies fewer pixels than the local background
        if np.sum(thresh == 255) < np.sum(thresh == 0):
            mask = (thresh == 255)
        else:
            mask = (thresh == 0)
        text_pixels = crop[mask]
        if len(text_pixels) > 0:
            b, g, r = np.mean(text_pixels, axis=0)
            return '#{:02x}{:02x}{:02x}'.format(int(r), int(g), int(b))
    except Exception:
        pass
    return "#ffffff"

def digitize_image(image_path: str, output_path: str):
    """
    Extracts all text from the image using EasyOCR, detects text colors,
    and cleanly inpaints only the text strokes (preserving background graphics,
    gradients, and artwork with zero smudging).
    Returns a tuple of (list of detected text elements, svg content, (width, height)).
    """
    reader = get_reader()
    
    # Read image using OpenCV
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    h, w = img.shape[:2]
    
    # EasyOCR expects RGB
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Detect text
    results = reader.readtext(rgb_img)
    
    text_elements = []
    clean_bg = img.copy()
    
    for (bbox, text, prob) in results:
        text = text.strip()
        if not text:
            continue
            
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        box_x = max(0, int(min(x_coords)))
        box_y = max(0, int(min(y_coords)))
        box_w = min(w - box_x, int(max(x_coords) - box_x))
        box_h = min(h - box_y, int(max(y_coords) - box_y))
        
        if box_w <= 3 or box_h <= 3:
            continue
            
        crop = img[box_y:box_y + box_h, box_x:box_x + box_w]
        color = extract_text_color(crop)
        
        # Estimate font size (roughly 85-90% of the bounding box height)
        font_size = max(12, int(box_h * 0.88))
        
        text_elements.append({
            "text": text,
            "left": box_x,
            "top": box_y,
            "width": box_w,
            "height": box_h,
            "fontSize": font_size,
            "color": color,
            "prob": round(float(prob), 3)
        })
        
        # Precision stroke-level inpainting on each text box so background graphics never smudge
        try:
            pad_x = 2
            pad_y = 2
            x1 = max(0, box_x - pad_x)
            y1 = max(0, box_y - pad_y)
            x2 = min(w, box_x + box_w + pad_x)
            y2 = min(h, box_y + box_h + pad_y)
            
            roi = img[y1:y2, x1:x2]
            if roi.shape[0] >= 4 and roi.shape[1] >= 4:
                border_pixels = np.concatenate([
                    roi[:2, :].reshape(-1, 3),
                    roi[-2:, :].reshape(-1, 3),
                    roi[:, :2].reshape(-1, 3),
                    roi[:, -2:].reshape(-1, 3)
                ], axis=0)
                bg_color = np.median(border_pixels, axis=0)
                
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                bg_gray = int(cv2.cvtColor(np.array([[bg_color]], dtype=np.uint8), cv2.COLOR_BGR2GRAY)[0, 0])
                
                _, th1 = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                diff1 = abs(np.mean(gray_roi[th1 == 255]) - bg_gray) if np.any(th1 == 255) else 0
                diff0 = abs(np.mean(gray_roi[th1 == 0]) - bg_gray) if np.any(th1 == 0) else 0
                
                text_mask_roi = (th1 == 255) if diff1 > diff0 else (th1 == 0)
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                text_mask_dil = cv2.dilate(text_mask_roi.astype(np.uint8) * 255, k, iterations=1)
                
                inpainted_roi = cv2.inpaint(roi, text_mask_dil, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                clean_bg[y1:y2, x1:x2] = inpainted_roi
        except Exception:
            pass
            
    # Save the clean background with preserved graphics
    cv2.imwrite(output_path, clean_bg)
    
    svg_content = None
    return text_elements, svg_content, (w, h)
