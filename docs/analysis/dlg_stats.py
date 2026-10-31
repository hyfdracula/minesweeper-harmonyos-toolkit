# -*- coding: utf-8 -*-
"""
dlg_stats.py —— 实测 information.jpg（扫雷统计信息窗口，702x254）的版式。

量法与 dlg_measure.py 一致：不用单点阈值，用「按行/按列的亮度跳变」。
输出：人读报告 + dialog_stats_grid.png（网格标注图）+ 若干局部放大图。
"""
import os
from PIL import Image, ImageDraw

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
NAME = "information.jpg"
L = []


def p(s=""):
    print(s)
    L.append(s)


def med_rgb(im, x0, y0, x1, y1):
    r = []; g = []; b = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = im.getpixel((x, y))
            r.append(c[0]); g.append(c[1]); b.append(c[2])
    r.sort(); g.sort(); b.sort()
    return (r[len(r) // 2], g[len(g) // 2], b[len(b) // 2])


def hx(c):
    return '#%02x%02x%02x' % c


def text_bands(im, x0, x1, y0, y1, thresh=170, minpix=2):
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


def merge_runs(runs, gap=3):
    if not runs:
        return []
    out = [[runs[0][0], runs[0][1]]]
    for r in runs[1:]:
        if r[0] - out[-1][1] <= gap + 1:
            out[-1][1] = r[1]
        else:
            out.append([r[0], r[1]])
    return [tuple(o) for o in out]


def pure_white(im, x, y):
    c = im.getpixel((x, y))
    return c[0] > 250 and c[1] > 250 and c[2] > 250


im = Image.open(os.path.join(REF, NAME)).convert("RGB")
W, H = im.size
p("=== %s  %dx%d ===" % (NAME, W, H))

# ---------- 外框 / 标题栏 ----------
p("")
p("## 顶部：逐行（x=200..600 中位）")
for y in range(0, 34):
    p("   y=%3d rgb=%s" % (y, hx(med_rgb(im, 200, y, 600, y))))

p("## 左侧：逐列（y=60..200 中位）")
for x in range(0, 14):
    p("   x=%3d rgb=%s" % (x, hx(med_rgb(im, x, 60, x, 200))))

p("## 右侧：逐列（y=60..200 中位）")
for x in range(W - 14, W):
    p("   x=%3d rgb=%s" % (x, hx(med_rgb(im, x, 60, x, 200))))

p("## 底部：逐行（x=200..600 中位）")
for y in range(H - 14, H):
    p("   y=%3d rgb=%s" % (y, hx(med_rgb(im, 200, y, 600, y))))

# ---------- 纯白区域（列表框 / 表格）----------
p("")
p("## 纯白(255)像素的行列范围")
for y in range(20, H - 10):
    xs = [x for x in range(0, W) if pure_white(im, x, y)]
    if len(xs) > 30:
        p("   y=%3d  纯白 x=%d..%d (n=%d)" % (y, xs[0], xs[-1], len(xs)))

# ---------- 文字带 ----------
p("")
p("## 客户区文字带（x=6..%d, y=20..%d）" % (W - 7, H - 7))
for (b0, b1) in text_bands(im, 6, W - 7, 20, H - 7):
    runs = glyph_runs(im, b0, b1, 6, W - 7)
    if not runs:
        continue
    p("   行 y=%3d..%3d (字高 %2d) 段: %s" % (b0, b1, b1 - b0 + 1, merge_runs(runs, 4)))

# ---------- 红色关闭按钮 ----------
p("")
p("## 关闭按钮（红）逐行红段")
allx = []
ally = []
for y in range(0, 24):
    seg = []
    run = None
    for x in range(W - 100, W):
        c = im.getpixel((x, y))
        red = c[0] > 120 and c[0] - c[1] > 45 and c[0] - c[2] > 35
        if red:
            if run is None:
                run = [x, x]
            else:
                run[1] = x
        else:
            if run is not None and run[1] - run[0] >= 4:
                seg.append(tuple(run))
            run = None
    if run is not None and run[1] - run[0] >= 4:
        seg.append(tuple(run))
    if seg:
        p("   y=%3d %s" % (y, seg))
        for (a, b) in seg:
            allx += [a, b]
            ally.append(y)
if allx:
    p("   -> 红按钮 x=%d..%d (w=%d) y=%d..%d (h=%d)" %
      (min(allx), max(allx), max(allx) - min(allx) + 1,
       min(ally), max(ally), max(ally) - min(ally) + 1))
    p("   -> 红色 %s" % hx(med_rgb(im, min(allx) + 2, min(ally) + 2, max(allx) - 2, max(ally) - 2)))

# ---------- 按钮（底部长条边框）----------
p("")
p("## 按钮行（客户区内偏离底色的长段）")
for y in range(190, H - 10):
    px = im.convert("L").load()
    run = None
    segs = []
    for x in range(6, W - 6):
        if abs(px[x, y] - 240) > 9:
            if run is None:
                run = [x, x]
            else:
                run[1] = x
        else:
            if run is not None and run[1] - run[0] >= 60:
                segs.append(tuple(run))
            run = None
    if run is not None and run[1] - run[0] >= 60:
        segs.append(tuple(run))
    if segs:
        p("   y=%3d %s" % (y, segs))

# ---------- 网格图 + 局部放大 ----------
g = im.resize((W * 2, H * 2), Image.NEAREST)
d = ImageDraw.Draw(g)
for x in range(0, W, 10):
    d.line([(x * 2, 0), (x * 2, H * 2)], fill=(255, 0, 0), width=1)
    d.text((x * 2 + 2, 2), str(x), fill=(200, 0, 0))
for y in range(0, H, 10):
    d.line([(0, y * 2), (W * 2, y * 2)], fill=(0, 130, 255), width=1)
    d.text((2, y * 2 + 2), str(y), fill=(0, 90, 200))
g.save(os.path.join(OUT, "dialog_stats_grid.png"))
p("")
p("grid: dialog_stats_grid.png")


def crop(box, scale, out):
    c = im.crop(box)
    c = c.resize(((box[2] - box[0] + 1) * scale, (box[3] - box[1] + 1) * scale), Image.LANCZOS)
    c.save(os.path.join(OUT, out))
    p("crop: " + out)


crop((430, 30, 700, 175), 3, "crop_stats_right.png")
crop((15, 30, 440, 130), 2, "crop_stats_left.png")
crop((320, 195, 650, 240), 3, "crop_stats_btn.png")

with open(os.path.join(OUT, "stats_layout.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("\nwrote stats_layout.md")
