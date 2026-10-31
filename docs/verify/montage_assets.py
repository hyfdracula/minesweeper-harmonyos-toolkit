# -*- coding: utf-8 -*-
"""Montage the assets that could plausibly hold a face, so one image answers it."""
import os
from PIL import Image

REF = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'

ITEMS = [
    ('images/flowerGardenSheet.png', 'flowerGardenSheet (94x54)', 8),
    ('images/thumbMines.png', 'thumbMines', 4),
    ('images/thumbFlowers.png', 'thumbFlowers', 4),
    ('images/thumbBlue.png', 'thumbBlue', 3),
    ('images/thumbGreen.png', 'thumbGreen', 3),
    ('icons/MineSweeper-128.png', 'app icon 128', 2),
    ('icons/Minesweeper.ico', 'app icon .ico (largest frame)', 2),
]

tiles = []
for rel, label, sc in ITEMS:
    p = os.path.join(REF, rel.replace('/', os.sep))
    im = Image.open(p).convert('RGBA')
    if im.size != (256, 256) and max(im.size) < 200:
        pass
    im = im.resize((im.width * sc, im.height * sc), Image.NEAREST)
    tiles.append((label, im))

W = max(t[1].width for t in tiles) + 24
H = sum(t[1].height + 30 for t in tiles)
canvas = Image.new('RGBA', (W, H), (250, 250, 250, 255))
y = 0
for label, im in tiles:
    canvas.alpha_composite(im, (12, y + 22))
    y += im.height + 30
canvas.convert('RGB').save(os.path.join(OUT, 'recheck_montage_assets.png'))
print('recheck_montage_assets.png  %dx%d' % canvas.size)
for label, im in tiles:
    print('   %-34s %dx%d' % (label, im.width, im.height))
