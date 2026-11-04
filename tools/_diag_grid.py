# -*- coding: utf-8 -*-
"""离线诊断：拿一张真机截图 + 布局，看 grid 识别卡在哪一步。

用法：python tools/_diag_grid.py <截图.jpeg>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_probe as wp  # noqa: E402
from PIL import Image  # noqa: E402

shot = sys.argv[1]
img = Image.open(shot).convert('RGB')
print('截图尺寸', img.size)

layout = {
    'canvas_w': 2800, 'canvas_h': 1690, 'unit': 8,
    'tile': 144, 'board_x': 752, 'board_y': 93,
    'hud': 0, 'rows': 9, 'cols': 9, 'mines': 10,
}

cands = wp.find_grid_candidates(img, layout['tile'])
print('候选数 = %d，前 5 条：' % len(cands))
for c in cands[:5]:
    print('   ', c)

g = wp.validate_grid(img, layout)
print('validate_grid ->', g)
if g is not None:
    gx, gy, nc, nr = g
    print('  dx=%d dy=%d  %dx%d' % (gx - layout['board_x'], gy - layout['board_y'], nc, nr))
    print('  detect_theme ->', wp.detect_theme(img, gx, gy, layout['tile'], nr, nc))
