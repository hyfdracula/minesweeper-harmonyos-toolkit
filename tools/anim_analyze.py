# -*- coding: utf-8 -*-
"""
离线分析连拍帧：找出扫描条的位置、拆雷光束、爆炸帧。
用法：python tools\anim_analyze.py <帧前缀> <gx> <gy> <pitch> <unit> <rows> <cols>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_probe as wp
from PIL import Image
import numpy as np

prefix = sys.argv[1]
gx, gy, pitch, unit = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
rows, cols = int(sys.argv[6]), int(sys.argv[7])

d = os.path.dirname(prefix) or '.'
base = os.path.basename(prefix)
files = sorted(f for f in os.listdir(d) if f.startswith(base) and f.lower().endswith('.jpeg'))
prev = None
print('%-22s %-18s %-34s %-16s %s' % ('frame', 'scan_bar(y,score)', 'beams', 'explode', 'diff'))
for f in files:
    p = os.path.join(d, f)
    im = Image.open(p).convert('RGB')
    bar = wp.locate_scan_bar(im, gx, gy, pitch, unit, rows, cols)
    beams = wp.analyse_disarm(im, gx, gy, pitch, unit, rows, cols)
    ex = wp.analyse_explode(im, gx, gy, pitch, unit, rows, cols)
    a = np.asarray(im.convert('L'), dtype=np.int16)
    diff = 0 if prev is None else int((np.abs(a - prev) > 18).sum())
    prev = a
    print('%-22s %-18s %-34s %-16s diff=%d' % (
        f,
        'None' if bar is None else 'y=%d (%.3f)' % bar,
        str(beams)[:32],
        str(ex)[:14],
        diff))
