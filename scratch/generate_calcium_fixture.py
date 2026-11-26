"""
Generates a faithful 1536x605 (2.54:1) Black & Metallic Gold Calcium Tablet test fixture
matching Requirement 4 structure for automated visual & pixel regression verification.
Note: Explicitly documented in the final report as a synthetic reproduction since the
user's external PNG source file is not saved in the workspace.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT_PATH = os.path.abspath("scratch/calcium_tablet_1536x605_test.png")


def _font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    W, H = 1536, 605
    img = Image.new("RGB", (W, H), (14, 15, 18))
    dr = ImageDraw.Draw(img)

    # Rich black & dark graphite vertical gradient + metallic gold wave accents
    for y in range(H):
        t = y / H
        c = int(12 + 16 * (0.5 - abs(t - 0.5)))
        dr.line([(0, y), (W, y)], fill=(c, c + 1, c + 3))

    gold = (214, 173, 82)
    gold_soft = (170, 134, 58)
    cream = (242, 238, 224)

    # Top & Bottom continuous metallic gold border bands across entire wrap
    dr.rectangle([0, 0, W, 12], fill=gold)
    dr.rectangle([0, H - 12, W, H], fill=gold)

    # Subtle vertical panel dividers at 32.0% and 68.5%
    sL, sR = int(W * 0.32), int(W * 0.685)
    dr.line([(sL, 20), (sL, H - 20)], fill=gold_soft, width=3)
    dr.line([(sR, 20), (sR, H - 20)], fill=gold_soft, width=3)

    # LEFT PANEL: Nutritional Information, Ingredients, Usage, Caution
    dr.rectangle([28, 30, sL - 26, 72], fill=gold)
    dr.text((42, 39), "NUTRITIONAL INFORMATION", font=_font(24, True), fill=(15, 15, 18))
    dr.rectangle([28, 76, sL - 26, 260], outline=gold_soft, width=2, fill=(22, 24, 29))
    dr.text((42, 92), "Serving Size: 1 Tablet | Servings: 60\nCalcium Citrate Malate      1000 mg\nVitamin D3                      400 IU\nMagnesium                       100 mg", font=_font(18), fill=cream)

    dr.rectangle([28, 286, sL - 26, 322], fill=gold_soft)
    dr.text((42, 293), "INGREDIENTS & USAGE", font=_font(20, True), fill=(15, 15, 18))
    dr.rectangle([28, 326, sL - 26, 565], outline=gold_soft, width=2, fill=(22, 24, 29))
    dr.text((42, 342), "Ingredients: Calcium Citrate,\nVitamin D3, Zinc, Magnesium.\n\nRecommended Usage:\nTake 1-2 tablets daily with water.\nCaution: Store in cool dry place.", font=_font(18), fill=cream)

    # CENTER PANEL: Hero Calcium Tablet Branding + Tablet Illustration + Net Qty
    dr.text((sL + 150, 42), "GOMZI NUTRITION", font=_font(28, True), fill=gold)
    dr.text((sL + 78, 122), "CALCIUM", font=_font(82, True), fill=cream)
    dr.text((sL + 115, 212), "TABLETS", font=_font(58, True), fill=gold)
    dr.rounded_rectangle([sL + 85, 295, sR - 85, 342], radius=16, fill=gold)
    dr.text((sL + 118, 306), "BONE & JOINT STRENGTH", font=_font(22, True), fill=(15, 15, 18))

    # Crisp tablet oval illustrations in gold/ivory
    dr.ellipse([sL + 170, 375, sL + 310, 455], fill=(238, 234, 222), outline=gold, width=4)
    dr.ellipse([sL + 265, 400, sL + 405, 480], fill=(250, 248, 242), outline=gold, width=4)
    dr.text((sL + 175, 512), "60 TABLETS", font=_font(36, True), fill=gold)

    # RIGHT PANEL: Key Benefits, Manufacturer & Batch
    dr.rectangle([sR + 26, 30, W - 28, 72], fill=gold)
    dr.text((sR + 44, 39), "KEY BENEFITS", font=_font(24, True), fill=(15, 15, 18))
    dr.rectangle([sR + 26, 76, W - 28, 295], outline=gold_soft, width=2, fill=(22, 24, 29))
    dr.text((sR + 44, 96), "• Supports Strong Bones & Teeth\n• Enhances Muscle Function\n• High Absorption Citrate Form\n• Daily Mineral Support", font=_font(20), fill=cream)

    dr.rectangle([sR + 26, 320, W - 28, 565], outline=gold_soft, width=2, fill=(22, 24, 29))
    dr.text((sR + 44, 340), "MANUFACTURED & MARKETED BY:\nGOMZI LIFE SCIENCE LLP\nSurat, Gujarat - India\n\nBatch No. : GC-2026\nNet Qty.  : 60 Tablets", font=_font(18), fill=cream)

    img.save(OUT_PATH)
    print(f"OK fixture: {OUT_PATH} ({img.size})")


if __name__ == "__main__":
    main()
