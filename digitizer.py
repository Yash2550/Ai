import os
import cv2
import numpy as np

# Initialize EasyOCR Reader globally so it doesn't reload on every request
# We'll initialize it lazily when the function is first called.
READER = None

def get_reader():
    global READER
    if READER is None:
        import easyocr
        # Use GPU if available, fallback to CPU
        READER = easyocr.Reader(['en'], gpu=True)
    return READER

def digitize_image(image_path: str, output_path: str) -> list:
    """
    Extracts all text from the image using EasyOCR, then uses cv2.inpaint
    to erase the text from the background.
    Returns a list of detected text elements.
    """
    reader = get_reader()
    
    # Read image using OpenCV
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # EasyOCR expects RGB
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Detect text
    results = reader.readtext(rgb_img)
    
    # Create an empty mask for inpainting
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    
    text_elements = []
    
    for (bbox, text, prob) in results:
        # bbox is a list of 4 points: [top_left, top_right, bottom_right, bottom_left]
        # Calculate bounding box for the mask
        pts = np.array(bbox, np.int32)
        
        # Fill the mask with white (255) where text is
        cv2.fillPoly(mask, [pts], 255)
        
        # Calculate attributes for frontend Canvas
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x = min(x_coords)
        y = min(y_coords)
        w = max(x_coords) - x
        h = max(y_coords) - y
        
        # Estimate font size (roughly the height of the bounding box)
        font_size = h
        
        text_elements.append({
            "text": text,
            "left": int(x),
            "top": int(y),
            "width": int(w),
            "height": int(h),
            "fontSize": int(font_size),
            "prob": float(prob)
        })
        
    # Dilate the mask to ensure text edges are completely covered
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    
    # 2. Inpaint the background to remove the text
    # INPAINT_TELEA is generally good for removing text
    clean_bg = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    
    # Save the clean background
    cv2.imwrite(output_path, clean_bg)
    
    # 3. Vectorize the clean background
    svg_content = None
    try:
        import vtracer
        import tempfile
        from PIL import Image
        
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            tmp_svg_path = tmp_svg.name
            
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
            tmp_png_path = tmp_png.name
            
        # Resize image to prevent vtracer from crashing on large files
        MAX_DIM = 1200
        original_w, original_h = 1, 1
        with Image.open(output_path) as cln_img:
            original_w, original_h = cln_img.size
            w, h = cln_img.size
            if w > MAX_DIM or h > MAX_DIM:
                ratio = min(MAX_DIM / w, MAX_DIM / h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                cln_img = cln_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            cln_img.convert("RGBA" if cln_img.mode in ("RGBA", "LA", "P") else "RGB").save(tmp_png_path, "PNG")
            
        # Convert the raster image into a true vector SVG file
        vtracer.convert_image_to_svg_py(
            tmp_png_path,
            tmp_svg_path,
            colormode="color",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=8
        )
        
        with open(tmp_svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
            
        # Fix viewBox and width/height to match original dimensions
        if f'width="{new_w}"' in svg_content:
            svg_content = svg_content.replace(f'width="{new_w}"', f'width="{original_w}"')
            svg_content = svg_content.replace(f'height="{new_h}"', f'height="{original_h}"')
            
        try:
            os.remove(tmp_svg_path)
            os.remove(tmp_png_path)
        except:
            pass
    except Exception as e:
        print("Vectorization failed:", e)
        
    return text_elements, svg_content
