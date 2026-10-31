# -*- coding: utf-8 -*-
"""dlg_measure2.py —— 补充测量：about.jpg 对话框的边距/红按钮/图标/文字/确定按钮，
以及 loss/win 标题栏右上角红色关闭按钮的精确矩形。"""
import os
from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
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


ab = Image.open(os.path.join(REF, "about.jpg")).convert("RGB")
p("=== about.jpg 右侧边框（列中位, y 140..280）===")
for x in range(450, 480):
    col = sorted(sum(ab.getpixel((x, y))) / 3 for y in range(140, 281))
    p("  x=%3d med=%3d rgb=%s" % (x, col[len(col) // 2], hx(med_rgb(ab, x, 140, x, 280))))

p("=== about.jpg 底部边框（行中位, x 200..400）===")
for y in range(284, 302):
    row = sorted(sum(ab.getpixel((x, y))) / 3 for x in range(200, 401))
    p("  y=%3d med=%3d rgb=%s" % (y, row[len(row) // 2], hx(med_rgb(ab, 200, y, 400, y))))

p("=== about.jpg 左侧边框（列中位, y 140..280）===")
for x in range(146, 166):
    col = sorted(sum(ab.getpixel((x, y))) / 3 for y in range(140, 281))
    p("  x=%3d med=%3d rgb=%s" % (x, col[len(col) // 2], hx(med_rgb(ab, x, 140, x, 280))))

p("=== about.jpg 红色关闭按钮细扫（x 405..465, y 98..126）===")
for y in range(98, 127):
    line = []
    for x in range(405, 466):
        c = ab.getpixel((x, y))
        line.append('R' if (c[0] > 120 and c[0] - c[1] > 40) else ('W' if min(c) > 200 else '.'))
    p("  y=%3d %s" % (y, ''.join(line)))
p("  (x 从 405 起，每字符 1px)")

p("=== about.jpg 雷图标（x 180..225, y 170..215）灰度点阵 ===")
for y in range(172, 212):
    line = []
    for x in range(182, 224):
        c = ab.getpixel((x, y))
        v = sum(c) / 3
        line.append('#' if v < 100 else ('+' if v < 180 else ('.' if v < 235 else ' ')))
    p("  y=%3d %s" % (y, ''.join(line)))
p("  (x 从 182 起，每字符 1px)")

p("=== about.jpg 「确定」按钮（蓝框）细扫 ===")
for y in range(248, 284):
    line = []
    for x in range(352, 452):
        c = ab.getpixel((x, y))
        line.append('B' if (c[2] - c[0] > 25) else ('#' if sum(c) / 3 < 120 else '.'))
    p("  y=%3d %s" % (y, ''.join(line)))
p("  (x 从 352 起，每字符 1px)")

p("=== about.jpg 三行文字的左右墨迹范围 ===")
for (y0, y1) in ((165, 176), (193, 203), (221, 232)):
    xs = []
    for x in range(230, 460):
        for yy in range(y0, y1 + 1):
            if sum(ab.getpixel((x, yy))) / 3 < 150:
                xs.append(x)
                break
    p("  行 y=%d..%d  墨迹 x=%d..%d" % (y0, y1, min(xs), max(xs)))

for nm, xr in (("loss.jpg", (400, 483)), ("win.jpg", (320, 396))):
    im = Image.open(os.path.join(REF, nm)).convert("RGB")
    p("=== %s 标题栏右上角红按钮细扫（x %d..%d, y 0..26）===" % (nm, xr[0], xr[1] - 1))
    for y in range(0, 26):
        line = []
        for x in range(xr[0], xr[1]):
            c = im.getpixel((x, y))
            line.append('R' if (c[0] > 110 and c[0] - c[1] > 40) else ('W' if min(c) > 200 else '.'))
        p("  y=%3d %s" % (y, ''.join(line)))
    p("  (x 从 %d 起，每字符 1px)" % xr[0])

with open(os.path.join(OUT, "dialog_layout_detail.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("\nwrote dialog_layout_detail.md")
