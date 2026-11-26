import sys
import os
import shutil

print("=== PYTHON PACKAGES ===")
for pkg in ['fitz', 'pypdf', 'pdfplumber', 'reportlab', 'cv2', 'PIL', 'rembg', 'torch', 'easyocr', 'trimesh', 'scipy', 'numpy']:
    try:
        m = __import__(pkg)
        print(f"{pkg}: available ({getattr(m, '__version__', 'ok')})")
    except Exception as e:
        print(f"{pkg}: NOT available ({e})")

print("\n=== SYSTEM BINARIES IN PATH ===")
for b in ['blender', 'inkscape', 'soffice', 'libreoffice', 'cdr2svg', 'pdftoppm', 'mutool']:
    path = shutil.which(b)
    print(f"{b}: {path if path else 'NOT FOUND'}")

print("\n=== CHECKING COMMON LOCATIONS ===")
common_paths = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    r"C:\Program Files\Inkscape\bin\inkscape.exe",
    r"C:\Program Files\Inkscape\inkscape.exe",
    r"C:\Program Files\Blender Foundation",
    r"C:\Program Files\Corel",
]
for cp in common_paths:
    exists = os.path.exists(cp)
    print(f"{cp}: {'EXISTS' if exists else 'NOT FOUND'}")
