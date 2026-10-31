# -*- coding: utf-8 -*-
"""
离线分析连拍帧：扫描条位置（在不在棋盘内）、拆雷光束、爆炸帧号。

用法：
  python tools\anim_analyze.py win   <前缀> <gx> <gy> <pitch> <unit> <rows> <cols>
  python tools\anim_analyze.py boom  <前缀> <gx> <gy> <pitch> <unit> <rows> <cols>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_probe as wp
from PIL import Image
import numpy as np

mode = sys.argv[1]
prefix = sys.argv[2]
gx, gy, pitch, unit = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
rows, cols = int(sys.argv[7]), int(sys.argv[8])
d = os.path.dirname(prefix) or '.'
base = os.path.basename(prefix)
files = sorted(f for f in os.listdir(d) if f.startswith(base) and f.lower().endswith('.jpeg'))
board_top = gy
board_bottom = gy + rows * pitch
print('棋盘屏幕区间 y = %d .. %d' % (board_top, board_bottom))
prev = None
for f in files:
    p = os.path.join(d, f)
    im = Image.open(p).convert('RGB')
    a = np.asarray(im.convert('L'), dtype=np.int16)
    diff = 0 if prev is None else int((np.abs(a - prev) > 18).sum())
    prev = a
    if mode == 'win':
        bar = wp.locate_scan_bar(im, gx, gy, pitch, unit, rows, cols)
        bar_any = wp.locate_scan_bar(im, gx, gy, pitch, unit, rows, cols, search_above=True)
        beams = wp.analyse_disarm(im, gx, gy, pitch, unit, rows, cols)
        inside = '-' if bar is None else ('在棋盘内' if board_top <= bar[0] <= board_bottom else '在棋盘外')
        print('%-22s 条(盘内)=%-18s 条(全域)=%-18s %-6s 光束=%-26s diff=%d'
              % (f, '无' if bar is None else 'y=%d %.3f' % bar,
                 '无' if bar_any is None else 'y=%d %.3f' % bar_any,
                 inside, str(beams)[:24], diff))
    else:
        ex = wp.analyse_explode(im, gx, gy, pitch, unit, rows, cols)
        print('%-22s 爆炸帧=%-30s diff=%d' % (f, str(ex)[:28], diff))
