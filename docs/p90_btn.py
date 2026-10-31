# -*- coding: utf-8 -*-
"""p90_btn.py —— 结束对话框：找 3 个按钮文字簇并点第 n 个。用法: python p90_btn.py 0|1|2"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p90_driver as d  # noqa: E402
from PIL import Image  # noqa: E402

path = os.path.join(d.VER, "P90_btnprobe.jpeg")
d.shot("btnprobe")
im = Image.open(path).convert("RGB")
px = im.load()
pts = [(x, y) for y in range(1000, 1400) for x in range(900, 1280)
       if px[x, y][0] - px[x, y][1] > 60 and px[x, y][0] - px[x, y][2] > 60]
if not pts:
    print("no red X -> no end dialog")
    sys.exit(1)
top = min(p[1] for p in pts)
print("red X top y=%d" % top)
clusters_all = []
for y in range(top + 380, top + 560):
    xs = [x for x in range(140, 1160)
          if px[x, y][0] < 120 and px[x, y][1] < 120 and px[x, y][2] < 120]
    if len(xs) < 6:
        continue
    cl = []
    cur = [xs[0], xs[0]]
    for x in xs[1:]:
        if x - cur[1] <= 30:
            cur[1] = x
        else:
            cl.append(tuple(cur))
            cur = [x, x]
    cl.append(tuple(cur))
    cl = [c for c in cl if 20 <= c[1] - c[0] <= 260]
    if len(cl) == 3:
        clusters_all.append((y, cl))
if not clusters_all:
    print("no row with exactly 3 clusters")
    sys.exit(1)
y, clusters = max(clusters_all, key=lambda t: t[0])
print("button row y=%d clusters=%s" % (y, clusters))
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
cx = (clusters[idx][0] + clusters[idx][1]) // 2
cy = y + 6
print("click (%d,%d)" % (cx, cy))
d.click(cx, cy)
print(d.shot("R77_after_middle_btn"))
