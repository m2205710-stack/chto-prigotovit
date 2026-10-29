"""Сводная картинка всех значков продуктов по категориям (для проверки).
Запуск: python tools/icon_sheet.py <файл.png>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from data import products as P  # noqa: E402

FONT = os.path.join(ROOT, "assets", "fonts", "Nunito-SemiBold.ttf")
BOLD = os.path.join(ROOT, "assets", "fonts", "Lora-SemiBold.ttf")


def main(out):
    groups = list(P.PRODUCTS.items()) + [("Базовые продукты", P.BASIC)]
    cols, cell_w, cell_h, head = 12, 118, 112, 34
    rows = sum((len(ps) + cols - 1) // cols for _, ps in groups)
    H = rows * cell_h + len(groups) * head + 10
    sheet = Image.new("RGB", (cols * cell_w + 20, H), "#FBF6EE")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 12)
    fb = ImageFont.truetype(BOLD, 18)
    y = 6
    for cat, ps in groups:
        d.text((12, y + 6), cat, font=fb, fill="#3A2E26")
        y += head
        for i, (name, _, icon) in enumerate(ps):
            x = 10 + (i % cols) * cell_w
            yy = y + (i // cols) * cell_h
            d.rounded_rectangle([x + 4, yy, x + cell_w - 4, yy + cell_h - 8], radius=12, fill="white", outline="#E8DCCB")
            im = Image.open(os.path.join(ROOT, "assets", "icons", icon + ".png")).convert("RGBA").resize((64, 64), Image.LANCZOS)
            sheet.paste(im, (x + (cell_w - 64) // 2, yy + 6), im)
            words, line, lines = name.split(), "", []
            for w in words:
                t = (line + " " + w).strip()
                if d.textlength(t, font=f) > cell_w - 14 and line:
                    lines.append(line)
                    line = w
                else:
                    line = t
            lines.append(line)
            for k, ln in enumerate(lines[:2]):
                d.text((x + cell_w / 2, yy + 76 + k * 14), ln, font=f, fill="#3A2E26", anchor="ma")
        y += ((len(ps) + cols - 1) // cols) * cell_h
    sheet.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
