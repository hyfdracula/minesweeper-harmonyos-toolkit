# -*- coding: utf-8 -*-
"""量画布顶偏移，并看 cell_state 在两种偏移下的判定。

只读设备，不改任何东西。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import click_matrix as cm  # noqa: E402

DEV = sys.argv[1] if len(sys.argv) > 1 else '3KQYD25331202962'
OUT = os.path.join(HERE, '..', 'docs', 'verify', 'diag_fresh.jpeg')

hdc = cm.Hdc(DEV)
geom = cm.Geom(hdc, os.path.join(HERE, '..', 'docs', 'verify'))
hdc.screenshot(OUT)
im = Image.open(OUT).convert('RGB')
img = np.array(im)
H, W = img.shape[:2]
print('截图 %dx%d（宽x高）' % (W, H))

lay = geom.refresh_layout()
print('布局:', lay)
print('棋盘原点(canvas px) =', lay.board_x, lay.board_y, ' 格边 =', lay.tile)

# 1) 竖着扫 x = board_x + tile/2 这一列，把「是砖」的行段打出来
x = lay.board_x + lay.tile // 2
runs = []
start = None
for y in range(H):
    r, g, b = im.getpixel((x, y))
    if cm.is_tile(r, g, b):
        if start is None:
            start = y
    else:
        if start is not None:
            runs.append((start, y - 1))
            start = None
if start is not None:
    runs.append((start, H - 1))
print('x=%d 这一列的砖色行段:' % x, runs[:6])
if runs:
    top = runs[0][0]
    print('=> 第一行砖的屏幕 y = %d；按 board_y=%d 算，画布顶偏移 = %d'
          % (top, lay.board_y, top - lay.board_y))

# 2) 第一条「不是深色」的行（canvas_top_from_shot 的算法）
first_light = None
for y in range(H):
    r, g, b = im.getpixel((x, y))
    if r + g + b > 260:
        first_light = y
        break
print('第一条亮行 y =', first_light, '（canvas_top_from_shot 用的是这个）')

# 3) 两种偏移下 cell_state 的判定
for cy in {top - lay.board_y, first_light, geom.canvas_y}:
    if cy is None:
        continue
    states = [cm.cell_state(img, lay, r, c, cy)
              for r in range(lay.rows or 9) for c in range(lay.cols or 9)]
    from collections import Counter
    print('偏移 %4d -> %s' % (cy, dict(Counter(states))))
