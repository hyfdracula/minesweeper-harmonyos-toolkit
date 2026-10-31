# -*- coding: utf-8 -*-
"""
probe_dialogs.py —— 探测三张参考图（loss.jpg / win.jpg / about.jpg）的版式。

方法（对抗 JPEG 压缩噪点）：
  * 不做单点阈值判断，改为「按行 / 按列的亮度跳变」：
      - 行剖面：取每行所有像素的最小亮度与中位亮度；最小亮度远低于邻行 => 该行是深色横线
      - 列剖面：同法找深色竖线
  * 文字行：用「行内深色像素个数」的直方图找连续文字带（text band），
    再在带内按列切出每个字符的 x 范围与该字形的上下边界（字高）。
  * 颜色：取该行/列附近的中位色，避免 JPEG 色度噪声。

用法: python probe_dialogs.py
输出: stdout（人读），供人工核对。
"""
import os
import sys

from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dialog_layout.md")


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def to_gray(im):
    return im.convert("L")


def row_dark_rows(im, thresh=140, minfrac=0.45):
    """返回 [(y, min_lum, frac_dark)] —— 整行明显偏暗（横线）。"""
    g = to_gray(im)
    w, h = g.size
    px = g.load()
    out = []
    for y in range(h):
        row = [px[x, y] for x in range(w)]
        mn = min(row)
        med = sorted(row)[w // 2]
        frac = sum(1 for v in row if v < thresh) / float(w)
        if med < thresh and frac >= minfrac:
            out.append((y, mn, med, frac))
    return out


def col_dark_cols(im, thresh=140, minfrac=0.45):
    g = to_gray(im)
    w, h = g.size
    px = g.load()
    out = []
    for x in range(w):
        col = [px[x, y] for y in range(h)]
        mn = min(col)
        med = sorted(col)[h // 2]
        frac = sum(1 for v in col if v < thresh) / float(h)
        if med < thresh and frac >= minfrac:
            out.append((x, mn, med, frac))
    return out


def text_bands(im, thresh=150, min_pix=2):
    """找出文字带：每行暗像素数 >= min_pix 的连续行段。返回 [(y0, y1, ...)]"""
    g = to_gray(im)
    w, h = g.size
    px = g.load()
    counts = []
    for y in range(h):
        c = sum(1 for x in range(w) if px[x, y] < thresh)
        counts.append(c)
    bands = []
    y = 0
    while y < h:
        if counts[y] >= min_pix:
            y0 = y
            while y < h and counts[y] >= min_pix:
                y += 1
            bands.append((y0, y - 1, max(counts[y0:y])))
        else:
            y += 1
    return bands, counts


def glyph_boxes(im, y0, y1, thresh=150, gap=1):
    """在 [y0,y1] 行带内按列找字符块。返回 [(x0,x1,top,bottom)]"""
    g = to_gray(im)
    w, h = g.size
    px = g.load()
    cols = []
    for x in range(w):
        dark = [y for y in range(y0, y1 + 1) if px[x, y] < thresh]
        cols.append((min(dark), max(dark)) if dark else None)
    boxes = []
    x = 0
    while x < w:
        if cols[x]:
            x0 = x
            tops = []
            bots = []
            while x < w and cols[x]:
                tops.append(cols[x][0])
                bots.append(cols[x][1])
                x += 1
            boxes.append((x0, x - 1, min(tops), max(bots)))
        else:
            x += 1
    return boxes


def dom_color(im, x0, y0, x1, y1):
    """区域众数颜色（量化到 8 级后取中位，避免 JPEG 噪点）。"""
    r = im.crop((x0, y0, x1 + 1, y1 + 1)).convert("RGB")
    q = r.quantize(colors=16, method=Image.MEDIANCUT).convert("RGB")
    from collections import Counter
    c = Counter(q.getdata())
    return c.most_common(3)


def main():
    lines = []

    def p(s=""):
        print(s)
        lines.append(s)

    for name in ("loss.jpg", "win.jpg"):
        im = Image.open(os.path.join(REF, name)).convert("RGB")
        w, h = im.size
        p("=" * 70)
        p("FILE %s  size=%dx%d" % (name, w, h))
        p("=" * 70)
        p("-- dark horizontal rows (median<%d & frac>=.45)" % 140)
        for r in row_dark_rows(im):
            p("   y=%3d min=%3d med=%3d frac=%.2f" % r)
        p("-- dark vertical cols")
        for c in col_dark_cols(im):
            p("   x=%3d min=%3d med=%3d frac=%.2f" % c)
        bands, counts = text_bands(im)
        p("-- text bands (dark pixel count >= 2 per row)")
        for (y0, y1, mx) in bands:
            boxes = glyph_boxes(im, y0, y1)
            p("   band y=%3d..%3d (h=%d) maxcount=%d  nglyph=%d" % (y0, y1, y1 - y0 + 1, mx, len(boxes)))
        p("-- corner colors")
        p("   top-left 4x4  %s" % (dom_color(im, 0, 0, 3, 3),))
        p("   title row1  %s" % (dom_color(im, w // 2, 2, w // 2 + 3, 2),))
        p("   title row15 %s" % (dom_color(im, w // 2, 15, w // 2 + 3, 15),))
        p("   title row19 %s" % (dom_color(im, w // 2, 19, w // 2 + 3, 19),))
        p("   title row21 %s" % (dom_color(im, w // 2, 21, w // 2 + 3, 21),))
        p("   client mid  %s" % (dom_color(im, 5, h // 2, 8, h // 2),))
        p()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nwrote", OUT)


if __name__ == "__main__":
    main()
