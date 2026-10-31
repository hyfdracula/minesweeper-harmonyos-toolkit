# -*- coding: utf-8 -*-
"""
p90_endbtn.py —— 在结束对话框底部找到 3 个按钮的文字簇，点击其中第 n 个（0=退出 1=换个难度 2=再玩一局）。

用法: python p90_endbtn.py <序号0/1/2>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p90_driver as d  # noqa: E402
from PIL import Image  # noqa: E402

VER = d.VER
shot = os.path.join(VER, "P90_endprobe.jpeg")
d.shot("endprobe")
im = Image.open(shot).convert("RGB")
px = im.load()
w, h = im.size

best = None
for y in range(h // 2, h):
    n = sum(1 for x in range(300, 1000)
            if abs(px[x, y][0] - 240) < 4 and abs(px[x, y][1] - 240) < 4
            and abs(px[x, y][2] - 240) < 4)
    if n > 300 and (best is None or n > best[1]):
        best = (y, n)
bottom = best[0] if best else h

rows = {}
for y in range(max(0, bottom - 70), min(h, bottom + 40)):
    xs = [x for x in range(320, 1000)
          if px[x, y][0] < 120 and px[x, y][1] < 120 and px[x, y][2] < 120]
    if len(xs) > 8:
        rows.setdefault(y, xs)

ys = sorted(rows)
if not ys:
    print("no button text found; dialog bottom=%d" % bottom)
    sys.exit(1)
y = max(ys, key=lambda yy: len(rows[yy]))
xs = rows[y]
clusters = []
cur = [xs[0], xs[0]]
for x in xs[1:]:
    if x - cur[1] <= 25:
        cur[1] = x
    else:
        clusters.append(tuple(cur))
        cur = [x, x]
clusters.append(tuple(cur))
print("button row y=%d  clusters=%s" % (y, clusters))
if len(clusters) < 3:
    print("expected 3 clusters, got %d" % len(clusters))
    sys.exit(1)
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
cx = (clusters[idx][0] + clusters[idx][1]) // 2
cy = y + 6
print("clicking cluster %d at (%d,%d)" % (idx, cx, cy))
d.click(cx, cy)
