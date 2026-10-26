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
    and cleanly inpaints (erases) text from the background.
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
    
    # Create an empty mask for inpainting
    mask = np.zeros((h, w), dtype=np.uint8)
    text_elements = []
    
    for (bbox, text, prob) in results:
        text = text.strip()
        if not text:
            continue
            
        pts = np.array(bbox, np.int32)
        cv2.fillPoly(mask, [pts], 255)
        
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        box_x = max(0, int(min(x_coords)))
        box_y = max(0, int(min(y_coords)))
        box_w = min(w - box_x, int(max(x_coords) - box_x))
        box_h = min(h - box_y, int(max(y_coords) - box_y))
        
        if box_w <= 0 or box_h <= 0:
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
        
    # Dilate mask to ensure text boundaries are completely erased
    kernel = np.ones((7, 7), np.uint8)
    dilated_mask = cv2.dilate(mask, kernel, iterations=2)
    
    # 2. Inpaint the background to remove text cleanly
    clean_bg = cv2.inpaint(img, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    
    # Save the clean background
    cv2.imwrite(output_path, clean_bg)
    
    svg_content = None
    return text_elements, svg_content, (w, h)
