# -*- coding: utf-8 -*-
"""Which atlas actually holds the trip / disarm / scan-bar frames?

The code draws them from otherSheet. linux Theme.h places trip/disarm on the
BOARD sheet (blueSheet) and only the scan bar on otherSheet. This crops the
same logical rect out of every candidate sheet so a human can see which one
holds the real artwork.

NOTE: PIL crop takes (left, upper, right, lower).
"""
import os
from PIL import Image

RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
S = 2

os.makedirs(OUT, exist_ok=True)
blue = Image.open(os.path.join(RAW, 'blueSheet.png')).convert('RGBA')
other = Image.open(os.path.join(RAW, 'otherSheet.png')).convert('RGBA')
mini = Image.open(os.path.join(RAW, 'minesweeperSheet.png')).convert('RGBA')

SHEETS = [('blueSheet', blue), ('otherSheet', other)]

CANDS = [
    ((728, 0, 57, 57), 'tripf0'),
    ((787, 0, 57, 57), 'tripf1'),
    ((728, 59, 57, 57), 'tripf3'),
    ((0, 0, 50, 150), 'disarmf0_blue'),
    ((364, 0, 50, 150), 'disarmf0_green'),
    ((52, 0, 50, 150), 'disarmf1'),
    ((0, 912, 275, 62), 'scanbar'),
    ((905, 425, 25, 25), 'clock'),
]

for (lx, ly, lw, lh), tag in CANDS:
    box = (lx * S, ly * S, (lx + lw) * S, (ly + lh) * S)
    tiles = []
    for sname, im in SHEETS:
        fits = box[2] <= im.width and box[3] <= im.height
        tiles.append((sname, im.crop(box) if fits else None, fits))
    tile_h = max(t[1].height for t in tiles if t[1] is not None)
    strip = Image.new('RGBA', (sum((t[1].width if t[1] else 60) + 8 for t in tiles), tile_h),
                      (255, 0, 255, 255))
    x = 0
    for sname, sub, fits in tiles:
        if sub is not None:
            strip.alpha_composite(sub, (x, 0))
        x += (sub.width if sub else 60) + 8
    fn = 'cmp_%s.png' % tag
    strip.convert('RGB').save(os.path.join(OUT, fn))
    print('%-14s logical=(%d,%d,%d,%d)  blue:%s  other:%s  -> %s' % (
        tag, lx, ly, lw, lh,
        'fit' if tiles[0][2] else 'OOB',
        'fit' if tiles[1][2] else 'OOB', fn))

mini.resize((mini.width * 4, mini.height * 4), Image.NEAREST).convert('RGB') \
    .save(os.path.join(OUT, 'cmp_minesweeperSheet_full4x.png'))
print('wrote cmp_minesweeperSheet_full4x.png')
