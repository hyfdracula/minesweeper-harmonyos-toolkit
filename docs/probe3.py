# -*- coding: utf-8 -*-
"""probe3.py —— 细粒度测量：列剖面、文字带、按钮矩形、标题栏渐变、关闭按钮。

原则：JPEG 有压缩噪点，判断边缘用「按行/按列的跳变」而不是单点阈值。
"""
import os
from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUTDIR = os.path.dirname(os.path.abspath(__file__))


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def col_med(im, x, y0, y1):
    g = im.convert("L")
    px = g.load()
    vals = sorted(px[x, y] for y in range(y0, y1 + 1))
    return vals[len(vals) // 2]


def row_med(im, y, x0, x1):
    g = im.convert("L")
    px = g.load()
    vals = sorted(px[x, y] for x in range(x0, x1 + 1))
    return vals[len(vals) // 2]


def find_rects(im, x0, x1, y0, y1, bg=240, tol=10, minrun=50):
    """在客户区里找矩形边框行：连续 >=minrun 个像素亮度偏离 bg 超过 tol。"""
    g = im.convert("L")
    px = g.load()
    rows = []
    for y in range(y0, y1 + 1):
        run = 0
        best = 0
        for x in range(x0, x1 + 1):
            if abs(px[x, y] - bg) > tol:
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= minrun:
            rows.append((y, best))
    return rows


def bands_in(im, x0, x1, y0, y1, thresh=170, minpix=2):
    g = im.convert("L")
    px = g.load()
    counts = []
    for y in range(y0, y1 + 1):
        counts.append(sum(1 for x in range(x0, x1 + 1) if px[x, y] < thresh))
    res = []
    y = y0
    while y <= y1:
        if counts[y - y0] >= minpix:
            s = y
            while y <= y1 and counts[y - y0] >= minpix:
                y += 1
            res.append((s, y - 1))
        else:
            y += 1
    return res


def glyph_runs(im, y0, y1, x0, x1, thresh=170):
    g = im.convert("L")
    px = g.load()
    runs = []
    x = x0
    while x <= x1:
        dark = [y for y in range(y0, y1 + 1) if px[x, y] < thresh]
        if dark:
            x0r = x
            tops, bots = [], []
            while x <= x1:
                d = [y for y in range(y0, y1 + 1) if px[x, y] < thresh]
                if d:
                    tops.append(min(d))
                    bots.append(max(d))
                    x += 1
                else:
                    break
            runs.append((x0r, x - 1, min(tops), max(bots)))
        else:
            x += 1
    return runs


def main():
    for name in ("loss.jpg", "win.jpg"):
        im = Image.open(os.path.join(REF, name)).convert("RGB")
        w, h = im.size
        print("=" * 72)
        print(name, w, "x", h)
        print("=" * 72)
        print("-- column median profile (client rows 30..h-8) --")
        prof = [(x, col_med(im, x, 30, h - 8)) for x in range(0, 22)]
        prof += [(x, col_med(im, x, 30, h - 8)) for x in range(w - 22, w)]
        for (x, m) in prof:
            print("   x=%3d med=%3d" % (x, m))
        print("-- rows with long non-background runs in client --")
        for r in find_rects(im, 9, w - 10, 30, h - 8):
            print("   y=%3d run=%d" % r)
        print("-- text bands in client (x 10..w-10) --")
        for (b0, b1) in bands_in(im, 10, w - 10, 30, h - 8):
            runs = glyph_runs(im, b0, b1, 10, w - 10)
            print("   band y=%3d..%3d  h=%2d  runs=%s" % (b0, b1, b1 - b0 + 1, runs))
        print()


if __name__ == "__main__":
    main()
