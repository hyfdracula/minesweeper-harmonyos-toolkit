# -*- coding: utf-8 -*-
"""dlg_stats3.py —— information.jpg 第三轮细测：右栏文字、列表框条目、表格边框、按钮标签。"""
import os
from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
L = []


def p(s=""):
    print(s)
    L.append(s)


im = Image.open(os.path.join(REF, "information.jpg")).convert("RGB")
W, H = im.size
PX = im.convert("L").load()


def is_dark_gray(x, y, th=150):
    c = im.getpixel((x, y))
    if c[2] - c[0] > 40 or c[2] - c[1] > 40:
        return False
    return sum(c) / 3.0 < th


def bands(x0, x1, y0, y1, th=150, minpix=2, gray=True):
    counts = []
    for y in range(y0, y1 + 1):
        n = 0
        for x in range(x0, x1 + 1):
            if (is_dark_gray(x, y, th) if gray else PX[x, y] < th):
                n += 1
        counts.append(n)
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


def runs_in(y0, y1, x0, x1, th=150, gray=True):
    out = []
    x = x0
    while x <= x1:
        hit = False
        for y in range(y0, y1 + 1):
            if (is_dark_gray(x, y, th) if gray else PX[x, y] < th):
                hit = True
                break
        if hit:
            xa = x
            while x <= x1:
                hit = False
                for y in range(y0, y1 + 1):
                    if (is_dark_gray(x, y, th) if gray else PX[x, y] < th):
                        hit = True
                        break
                if not hit:
                    break
                x += 1
            out.append((xa, x - 1))
        else:
            x += 1
    return out


def merge(rs, gap=4):
    if not rs:
        return []
    out = [[rs[0][0], rs[0][1]]]
    for r in rs[1:]:
        if r[0] - out[-1][1] <= gap + 1:
            out[-1][1] = r[1]
        else:
            out.append([r[0], r[1]])
    return [tuple(o) for o in out]


def report(title, x0, x1, y0, y1, th=150, minpix=2, gray=True):
    p("")
    p("## %s  (x %d..%d, y %d..%d)" % (title, x0, x1, y0, y1))
    for (b0, b1) in bands(x0, x1, y0, y1, th, minpix, gray):
        rs = merge(runs_in(b0, b1, x0, x1, th, gray), 4)
        p("   行 y=%3d..%3d (字高 %2d) 段: %s" % (b0, b1, b1 - b0 + 1, rs))


report("右栏（排除右侧边框 x=694）", 438, 690, 34, 185)
report("左列表框（排除框线，灰度字）", 22, 175, 36, 121)
report("表格区", 196, 430, 38, 155)
report("按钮标签", 340, 490, 206, 231)
report("按钮标签2", 505, 650, 206, 231)

p("")
p("## 列表框：蓝色选中条的行")
for y in range(30, 130):
    n = 0
    for x in range(22, 176):
        c = im.getpixel((x, y))
        if c[2] - c[0] > 40:
            n += 1
    if n > 50:
        p("   y=%3d 蓝色像素 %d" % (y, n))

p("")
p("## 列表框 / 表格 的竖直边框（列暗像素数）")
for x in range(15, 440):
    n = sum(1 for y in range(30, 160) if PX[x, y] < 225)
    if n >= 20:
        p("   x=%3d n=%d" % (x, n))

p("")
p("## 中表 group box 边框（行）")
for y in range(30, 165):
    n = sum(1 for x in range(190, 435) if PX[x, y] < 235)
    if n >= 40:
        p("   y=%3d n=%d" % (y, n))

p("")
p("## 关键取样色")
def med(c):
    c = sorted(c)
    return '#%02x%02x%02x' % tuple(c[i][len(c) // 2] for i in range(3))


def sample(x0, y0, x1, y1):
    return med([im.getpixel((x, y)) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)])


p("   选中条颜色        %s" % sample(30, 38, 170, 41))
p("   选中条上的文字    %s" % sample(24, 40, 45, 45))
p("   列表框白底        %s" % sample(60, 90, 170, 110))
p("   列表框边框        %s" % sample(20, 70, 20, 100))
p("   表格边框          %s" % sample(193, 60, 193, 140))
p("   表格底色          %s" % sample(210, 120, 420, 145))
p("   右栏底色          %s" % sample(450, 190, 600, 200))
p("   关闭按钮内        %s" % sample(345, 208, 480, 212))
p("   关闭按钮边框      %s" % sample(336, 205, 336, 231))
p("   关闭按钮蓝框      %s" % sample(338, 206, 338, 230))
p("   重置按钮内        %s" % sample(508, 208, 648, 212))
p("   重置按钮边框      %s" % sample(503, 205, 503, 231))

with open(os.path.join(OUT, "stats_layout_detail3.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("\nwrote stats_layout_detail3.md")
