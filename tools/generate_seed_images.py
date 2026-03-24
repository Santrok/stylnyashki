from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "media" / "products"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 900, 900
COUNT = 12

colors = [
    (201, 66, 132),   # purple
    (230, 69, 69),    # red
    (74, 159, 222),   # blue
    (248, 197, 69),   # yellow
]

def try_load_font(size: int):
    # Попытка взять системный шрифт; если не получится — Pillow дефолт
    for p in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        fp = Path(p)
        if fp.exists():
            return ImageFont.truetype(str(fp), size=size)
    return ImageFont.load_default()

font1 = try_load_font(52)
font2 = try_load_font(38)

for i in range(1, COUNT + 1):
    c1 = random.choice(colors)
    c2 = random.choice(colors)

    img = Image.new("RGB", (W, H), c1)
    draw = ImageDraw.Draw(img)

    # простая "диагональная" заливка блоками
    draw.rectangle([0, 0, W, H//2], fill=c1)
    draw.rectangle([0, H//2, W, H], fill=c2)

    # кружочки
    draw.ellipse([W-220, 80, W-60, 240], fill=(255, 255, 255))
    draw.ellipse([120, H-280, 340, H-60], fill=(255, 255, 255))

    # текст
    text1 = "Стильняшки"
    text2 = f"seed-{i:02d}"

    # центрирование
    tw1, th1 = draw.textbbox((0, 0), text1, font=font1)[2:]
    tw2, th2 = draw.textbbox((0, 0), text2, font=font2)[2:]

    draw.text(((W - tw1) / 2, (H - th1) / 2 - 20), text1, fill=(17, 24, 39), font=font1)
    draw.text(((W - tw2) / 2, (H - th2) / 2 + 50), text2, fill=(17, 24, 39), font=font2)

    out = OUT_DIR / f"seed-{i:02d}.png"
    img.save(out, "PNG")

print(f"Generated {COUNT} images in: {OUT_DIR}")