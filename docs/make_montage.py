# -*- coding: utf-8 -*-
"""
make_montage.py —— 把多张截图拼成一张对照图（带标题），便于一次看全。

用法:
    python make_montage.py <输出png> <裁剪x0,y0,x1,y1> <缩放> <标题1=文件1> <标题2=文件2> ...
    python make_montage.py <输出png> full 0.5 <标题=文件> ...
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"


def f(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except Exception:
        return ImageFont.load_default()


def main():
    out = sys.argv[1]
    box = sys.argv[2]
    sc = float(sys.argv[3])
    items = []
    for a in sys.argv[4:]:
        t, p = a.split('=', 1)
        items.append((t, p))
    if box == 'full':
        crop = None
    else:
        crop = tuple(int(v) for v in box.split(','))
    cells = []
    for t, p in items:
        im = Image.open(p).convert("RGB")
        if crop:
            im = im.crop(crop)
        w = int(im.width * sc)
        h = int(im.height * sc)
        cells.append((t, im.resize((w, h), Image.LANCZOS)))
    cw = max(c[1].width for c in cells)
    ch = max(c[1].height for c in cells) + 26
    cols = 2
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new("RGB", (cw * cols + 8, ch * rows + 8), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(cells):
        x = 4 + (i % cols) * (cw + 8)
        y = 4 + (i // cols) * (ch + 8)
        d.rectangle([x, y, x + cw, y + 24], fill=(30, 30, 30))
        d.text((x + 6, y + 4), t, font=f(16), fill=(255, 255, 255))
        sheet.paste(im, (x, y + 26))
    sheet.save(out)
    print("saved", out, sheet.size)


if __name__ == "__main__":
    main()
