# -*- coding: utf-8 -*-
"""
Generates official GOMZI NUTRITION logo assets in static/assets/
"""
import os
from PIL import Image, ImageDraw, ImageFont

def generate_logo():
    os.makedirs("static/assets", exist_ok=True)
    
    # 1. Official SVG Logo
    svg_code = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" width="400" height="120">
  <defs>
    <style>
      .gomzi-text { font-family: 'Montserrat', 'Inter', sans-serif; font-weight: 900; font-style: italic; font-size: 58px; fill: #708238; letter-spacing: 1px; }
      .nutrition-text { font-family: 'Montserrat', 'Inter', sans-serif; font-weight: 800; font-size: 20px; fill: #334155; letter-spacing: 7px; }
    </style>
  </defs>
  <text x="200" y="62" text-anchor="middle" class="gomzi-text">GOMZI</text>
  <text x="204" y="98" text-anchor="middle" class="nutrition-text">NUTRITION</text>
</svg>'''
    with open("static/assets/gomzi_logo.svg", "w", encoding="utf-8") as f:
        f.write(svg_code)
    print("Generated static/assets/gomzi_logo.svg")

    # 2. Crisp PNG Logo (400x120 transparent)
    img = Image.new("RGBA", (600, 180), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Simple clean draw for crisp fallback
    try:
        font_large = ImageFont.truetype("arialbd.ttf", 80)
        font_sub = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    draw.text((300, 20), "GOMZI", fill=(112, 130, 56, 255), anchor="mt", font=font_large)
    draw.text((300, 115), "N U T R I T I O N", fill=(51, 65, 85, 255), anchor="mt", font=font_sub)
    img.save("static/assets/gomzi_logo.png", "PNG")
    print("Generated static/assets/gomzi_logo.png")

if __name__ == "__main__":
    generate_logo()
