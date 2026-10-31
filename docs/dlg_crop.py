# -*- coding: utf-8 -*-
"""dlg_crop.py —— 裁剪参考图的局部并放大，叠加坐标网格，供人工核对。"""
import os
import sys
from PIL import Image, ImageDraw

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUTDIR = os.path.dirname(os.path.abspath(__file__))


def crop(name, box, scale, out, grid=5, label_every=5):
    im = Image.open(os.path.join(REF, name)).convert("RGB")
    x0, y0, x1, y1 = box
    c = im.crop(box)
    w = (x1 - x0 + 1) * scale
    h = (y1 - y0 + 1) * scale
    g = c.resize((w, h), Image.NEAREST)
    d = ImageDraw.Draw(g)
    gx = x0 - (x0 % grid)
    gy = y0 - (y0 % grid)
    for x in range(gx, x1 + 1, grid):
        px = (x - x0) * scale
        major = (x % label_every == 0)
        d.line([(px, 0), (px, h)], fill=(255, 0, 0) if major else (255, 170, 170), width=1)
        if major:
            d.text((px + 2, 2), str(x), fill=(200, 0, 0))
    for y in range(gy, y1 + 1, grid):
        py = (y - y0) * scale
        major = (y % label_every == 0)
        d.line([(0, py), (w, py)], fill=(0, 130, 255) if major else (170, 210, 255), width=1)
        if major:
            d.text((2, py + 2), str(y), fill=(0, 90, 200))
    path = os.path.join(OUTDIR, out)
    g.save(path)
    print("saved", path, g.size)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "about"):
        crop("about.jpg", (145, 92, 475, 300), 3, "crop_about.png", grid=5, label_every=10)
    if which in ("all", "closeloss"):
        crop("loss.jpg", (415, 0, 483, 30), 8, "crop_closeloss.png", grid=2, label_every=10)
    if which in ("all", "closewin"):
        crop("win.jpg", (330, 0, 396, 30), 8, "crop_closewin.png", grid=2, label_every=10)
    if which in ("all", "btnloss"):
        crop("loss.jpg", (10, 230, 200, 268), 4, "crop_btnloss.png", grid=2, label_every=10)
