# -*- coding: utf-8 -*-
"""probe2.py —— 逐行/逐列剖面，打印前若干行的中位色，找标题栏边界。"""
import os
from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"


def row_profile(im, x0, x1, y0, y1):
    g = im.convert("L")
    px = g.load()
    out = []
    for y in range(y0, y1):
        row = sorted(px[x, y] for x in range(x0, x1 + 1))
        med = row[len(row) // 2]
        mn = row[0]
        out.append((y, mn, med))
    return out


def main():
    for name, xr in (("loss.jpg", (12, 470)), ("win.jpg", (12, 383))):
        im = Image.open(os.path.join(REF, name)).convert("RGB")
        print("=== %s  rows 0..40 (x %s) ===" % (name, xr))
        for (y, mn, med) in row_profile(im, xr[0], xr[1], 0, 40):
            c = im.getpixel((xr[0] + 5, y))
            print("  y=%3d min=%3d med=%3d  px@x17=%s" % (y, mn, med, c))
        print()

    # about.jpg: find the dialog inside the full-window shot
    im = Image.open(os.path.join(REF, "about.jpg")).convert("RGB")
    w, h = im.size
    print("=== about.jpg %dx%d ===" % (w, h))
    g = im.convert("L")
    px = g.load()
    # print row medians to spot the dialog region (dialog is a bright rect on the board)
    for y in range(80, 320, 4):
        row = sorted(px[x, y] for x in range(140, 480))
        print("  y=%3d med=%3d min=%3d" % (y, row[len(row) // 2], row[0]))


if __name__ == "__main__":
    main()
