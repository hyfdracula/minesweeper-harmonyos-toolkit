# -*- coding: utf-8 -*-
"""dlg_stats2.py —— information.jpg 分区细测（右栏 / 左列表 / 中表 / 按钮标签）。"""
import os
from PIL import Image, ImageDraw

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
L = []


def p(s=""):
    print(s)
    L.append(s)


def text_bands(im, x0, x1, y0, y1, thresh=170, minpix=1):
    px = im.convert("L").load()
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
    px = im.convert("L").load()
    runs = []
    x = x0
    while x <= x1:
        if any(px[x, y] < thresh for y in range(y0, y1 + 1)):
            xa = x
            tops, bots = [], []
            while x <= x1:
                d = [y for y in range(y0, y1 + 1) if px[x, y] < thresh]
                if d:
                    tops.append(min(d)); bots.append(max(d)); x += 1
                else:
                    break
            runs.append((xa, x - 1, min(tops), max(bots)))
        else:
            x += 1
    return runs


def merge(runs, gap=3):
    if not runs:
        return []
    out = [[runs[0][0], runs[0][1]]]
    for r in runs[1:]:
        if r[0] - out[-1][1] <= gap + 1:
            out[-1][1] = r[1]
        else:
            out.append([r[0], r[1]])
    return [tuple(o) for o in out]


def hx(c):
    return '#%02x%02x%02x' % c


def med_rgb(im, x0, y0, x1, y1):
    r = []; g = []; b = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = im.getpixel((x, y))
            r.append(c[0]); g.append(c[1]); b.append(c[2])
    r.sort(); g.sort(); b.sort()
    return (r[len(r) // 2], g[len(g) // 2], b[len(b) // 2])


im = Image.open(os.path.join(REF, "information.jpg")).convert("RGB")
W, H = im.size


def region(title, x0, x1, y0, y1, thresh=170):
    p("")
    p("## %s   (x %d..%d, y %d..%d)" % (title, x0, x1, y0, y1))
    for (b0, b1) in text_bands(im, x0, x1, y0, y1, thresh=thresh):
        runs = glyph_runs(im, b0, b1, x0, x1, thresh=thresh)
        if not runs:
            continue
        p("   行 y=%3d..%3d (字高 %2d) 段: %s" % (b0, b1, b1 - b0 + 1, merge(runs, 4)))


region("右栏", 436, 700, 34, 180)
region("左列表框", 22, 178, 36, 124)
region("中表", 190, 435, 34, 155)
region("按钮标签", 330, 660, 200, 236)

# --- 左列表框 / 中表的边框矩形 ---
p("")
p("## 列表框与表格的边框（行/列上的暗线）")
for y in range(34, 160):
    px = im.convert("L").load()
    dark = [x for x in range(15, 440) if px[x, y] < 215]
    if len(dark) > 40:
        p("   y=%3d 暗像素 x=%d..%d (n=%d)" % (y, dark[0], dark[-1], len(dark)))
for x in range(15, 440):
    px = im.convert("L").load()
    dark = [y for y in range(34, 160) if px[x, y] < 215]
    if len(dark) > 25:
        p("   x=%3d 暗像素 y=%d..%d (n=%d)" % (x, dark[0], dark[-1], len(dark)))

# --- 颜色 ---
p("")
p("## 颜色")
p("   列表框内部        %s" % hx(med_rgb(im, 40, 90, 60, 100)))
p("   表格内部          %s" % hx(med_rgb(im, 210, 100, 240, 120)))
p("   客户区            %s" % hx(med_rgb(im, 460, 190, 480, 200)))
p("   选中项高亮(初级行) %s" % hx(med_rgb(im, 30, 44, 60, 50)))
p("   关闭按钮内部      %s" % hx(med_rgb(im, 345, 210, 400, 214)))
p("   重置按钮内部      %s" % hx(med_rgb(im, 510, 210, 560, 214)))
p("   关闭按钮边框      %s" % hx(med_rgb(im, 340, 205, 340, 231)))
p("   重置按钮边框      %s" % hx(med_rgb(im, 506, 205, 506, 231)))
p("   标题文字区        %s" % hx(med_rgb(im, 12, 6, 60, 12)))

# --- 标题栏文字 ---
p("")
p("## 标题栏文字（x 6..200, y 1..28, 近黑阈值 120）")
for (b0, b1) in text_bands(im, 6, 200, 1, 28, thresh=120):
    runs = glyph_runs(im, b0, b1, 6, 200, thresh=120)
    if runs:
        p("   y=%d..%d (字高 %d) x=%d..%d  字符块=%s" %
          (b0, b1, b1 - b0 + 1, runs[0][0], runs[-1][1], runs))

# --- 放大图 ---
for box, sc, out in (((436, 150, 560, 176), 8, "crop_stats_streak.png"),
                      ((18, 34, 182, 124), 4, "crop_stats_list.png"),
                      ((190, 34, 435, 158), 3, "crop_stats_table.png")):
    im.crop(box).resize(((box[2] - box[0] + 1) * sc, (box[3] - box[1] + 1) * sc),
                         Image.LANCZOS).save(os.path.join(OUT, out))
    p("crop: " + out)

with open(os.path.join(OUT, "stats_layout_detail.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("\nwrote stats_layout_detail.md")
