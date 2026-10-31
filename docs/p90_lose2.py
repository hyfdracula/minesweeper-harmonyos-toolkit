# -*- coding: utf-8 -*-
"""
p90_lose2.py —— 新版式 build：踩雷出结束框，然后点中间那个按钮（换个难度(D)）。
用法: python p90_lose2.py [要点的按钮序号 0/1/2]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p90_driver as d  # noqa: E402
from PIL import Image  # noqa: E402

VER = d.VER


def shot_probe(tag):
    p = os.path.join(VER, "P90_%s.jpeg" % tag)
    d.shot(tag)
    return p


def red_x(path):
    im = Image.open(path).convert("RGB")
    px = im.load()
    pts = [(x, y) for y in range(900, 1500) for x in range(800, 1280)
           if px[x, y][0] - px[x, y][1] > 60 and px[x, y][0] - px[x, y][2] > 60]
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


# 1) 踩雷：初级 9x9，格边 108px，棋盘原点(154,754)画布 -> 屏幕(154,892)
cells = []
for c in range(9):
    for r in range(9):
        cells.append((154 + 108 * c + 54, 892 + 108 * r + 54))
path = None
for i, (x, y) in enumerate(cells):
    d.click(x, y)
    if i % 6 == 5:
        path = shot_probe("loseprobe")
        rx = red_x(path)
        if rx:
            print("lose dialog found after %d clicks, red x=%s" % (i + 1, rx))
            break
if not red_x(path or shot_probe("loseprobe")):
    print("lose dialog NOT found")
    sys.exit(1)

im = Image.open(path).convert("RGB")
px = im.load()
# 2) 按钮行：结束框下半部 y 1400..1750 里的深色文字簇
rows = {}
for y in range(1400, 1750):
    xs = [x for x in range(140, 1160)
          if px[x, y][0] < 120 and px[x, y][1] < 120 and px[x, y][2] < 120]
    if len(xs) > 12:
        rows.setdefault(y, xs)
if not rows:
    print("no button text rows")
    sys.exit(1)
y = max(rows, key=lambda yy: len(rows[yy]))
xs = rows[y]
clusters = []
cur = [xs[0], xs[0]]
for x in xs[1:]:
    if x - cur[1] <= 30:
        cur[1] = x
    else:
        clusters.append(tuple(cur))
        cur = [x, x]
clusters.append(tuple(cur))
clusters = [c for c in clusters if c[1] - c[0] > 15]
print("button row y=%d clusters=%s" % (y, clusters))
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
cx = (clusters[idx][0] + clusters[idx][1]) // 2
cy = y + 8
print("click cluster %d at (%d,%d)" % (idx, cx, cy))
d.click(cx, cy)
print(d.shot("R77_after_middle_btn"))
