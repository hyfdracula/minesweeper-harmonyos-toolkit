# -*- coding: utf-8 -*-
"""
p90_pick.py —— 在屏幕某个 y 带里找到一行文字，按 x 聚成若干簇，点第 index 簇的中心。

用法: python p90_pick.py <y0> <y1> <x0> <x1> <index> [截图名]
例:   python p90_pick.py 150 195 0 1280 0        # 点菜单栏第一项（游戏(G)）
      python p90_pick.py 200 1100 0 600 4 C130_menu_custom
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p90_driver as d  # noqa: E402
from PIL import Image  # noqa: E402


def main():
    y0, y1, x0, x1, idx = (int(v) for v in sys.argv[1:6])
    name = sys.argv[6] if len(sys.argv) > 6 else "pickprobe"
    path = os.path.join(d.VER, "P90_%s.jpeg" % name)
    d.shot(name)
    im = Image.open(path).convert("RGB")
    px = im.load()
    rows = {}
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1)
              if px[x, y][0] < 120 and px[x, y][1] < 120 and px[x, y][2] < 120]
        if len(xs) >= 3:
            rows.setdefault(y, xs)
    if not rows:
        print("no dark text in band")
        return
    # 取文字最密的连续行段
    ys = sorted(rows)
    segs = []
    for y in ys:
        if segs and y - segs[-1][1] <= 4:
            segs[-1][1] = y
        else:
            segs.append([y, y])
    seg = max(segs, key=lambda s: sum(len(rows[y]) for y in range(s[0], s[1] + 1)))
    xs = []
    for y in range(seg[0], seg[1] + 1):
        xs += rows[y]
    xs = sorted(xs)
    cl = []
    cur = [xs[0], xs[0]]
    for x in xs[1:]:
        if x - cur[1] <= 30:
            cur[1] = x
        else:
            cl.append(tuple(cur))
            cur = [x, x]
    cl.append(tuple(cur))
    print("row y=%d..%d  clusters=%s" % (seg[0], seg[1], cl))
    if idx < 0 or idx >= len(cl):
        print("index out of range")
        return
    cx = (cl[idx][0] + cl[idx][1]) // 2
    cy = (seg[0] + seg[1]) // 2
    print("click cluster %d -> (%d,%d)" % (idx, cx, cy))
    d.click(cx, cy)


main()
