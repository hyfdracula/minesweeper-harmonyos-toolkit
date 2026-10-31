# -*- coding: utf-8 -*-
"""Status-strip evidence: crop the strip-related regions and hunt the atlases
for a smiley (yellow disc) sprite. Writes docs/analysis/strip_*.png.

Read-only against the reference assets.
"""
import os
import numpy as np
from PIL import Image

REF = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images'
OUT = r'D:\software\harmony\projects\minesweeper\docs\analysis'
os.makedirs(OUT, exist_ok=True)

blue = Image.open(os.path.join(REF, 'blueSheet.png')).convert('RGBA')
mini = Image.open(os.path.join(REF, 'minesweeperSheet.png')).convert('RGBA')
other = Image.open(os.path.join(REF, 'otherSheet.png')).convert('RGBA')
helpb = Image.open(os.path.join(REF, 'helpBoard.png')).convert('RGB')
msbmp = Image.open(os.path.join(REF, 'Minesweeper.bmp')).convert('RGB')
frame = Image.open(os.path.join(REF, 'png', 'Frame.png')).convert('RGB')

def save(im, name, scale=1):
    if scale > 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.convert('RGB').save(os.path.join(OUT, name))
    print('  %-42s %dx%d' % (name, im.width, im.height))

print('cropping:')
# 1. the whole game sheet (94x54) at 8x -- the two 25x25 panel icons live here
save(mini, 'strip_minesweeperSheet_8x.png', 8)
# 2. the clock icon out of otherSheet (logical 905,425 -> px 1810,850)
save(other.crop((1810, 850, 1860, 900)), 'strip_otherSheet_clock_10x.png', 10)
# 3. the panel mine icon out of the game sheet
save(mini.crop((0, 0, 50, 50)), 'strip_panelMine_10x.png', 10)
save(mini.crop((54, 0, 90, 36)), 'strip_bareMine_10x.png', 10)
# 4. helpBoard's two round buttons at 14x (Microsoft's own Win7 help window)
save(helpb.crop((24, 166, 50, 192)), 'strip_helpboard_leftBtn_14x.png', 14)
save(helpb.crop((204, 166, 230, 192)), 'strip_helpboard_rightBtn_14x.png', 14)
# 5. the whole helpBoard (the status strip is at the bottom)
save(helpb, 'strip_helpboard_full.png', 3)
# 6. otherSheet bottom band (px 1948..2015): the second digit copy + gradient bar
save(other.crop((0, 1948, 460, 2016)), 'strip_otherSheet_bottomBand.png', 2)
# 7. the blueSheet sprite row (px 1104..1160): flag/question/hilite/misflag/shadow
save(blue.crop((780, 1104, 1010, 1160)), 'strip_blueSheet_spriteRow_4x.png', 4)
# 8. Minesweeper.bmp + Frame.png (other candidates for a smiley)
save(msbmp, 'strip_Minesweeper_bmp_full.png', 3)
save(frame, 'strip_Frame_png_full.png', 2)

# ---------------------------------------------------------------- yellow hunt
print('\nyellow-disc hunt (a Win7 smiley would be a yellow circle):')
CAND = [
    ('blueSheet.png', blue),
    ('minesweeperSheet.png', mini),
    ('otherSheet.png', other),
]
for name, im in CAND:
    a = np.asarray(im)
    r = a[:, :, 0].astype(int); g = a[:, :, 1].astype(int); b = a[:, :, 2].astype(int)
    al = a[:, :, 3]
    yellow = (r > 170) & (g > 130) & (b < 130) & (al > 100)
    n = int(yellow.sum())
    print('  %-22s yellow-ish pixels: %d  (%.4f%% of sheet)' % (name, n, 100.0 * n / yellow.size))
    if n:
        ys, xs = np.where(yellow)
        print('       bbox x %d..%d  y %d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
        # crop the neighbourhood of the biggest cluster
        x0 = max(0, xs.min() - 40); x1 = min(im.width, xs.max() + 41)
        y0 = max(0, ys.min() - 40); y1 = min(im.height, ys.max() + 41)
        save(im.crop((x0, y0, x1, y1)), 'strip_YELLOW_%s.png' % name.replace('.png', ''), 4)

# grey/white disc hunt: a smiley could be monochrome; look for circular blobs
# in the two places a status-strip button would live
print('\n25x25 panel-icon hunt in otherSheet (rows 400..460 logical):')
a = np.asarray(other)
for ly in range(400, 460, 5):
    row = a[ly * 2:(ly + 25) * 2, :, :]
    op = (row[:, :, 3] > 40).sum()
    if op:
        cols = np.where((row[:, :, 3] > 40).any(axis=0))[0]
        print('   logical y %d..%d : opaque cols %d..%d (%d px)' %
              (ly, ly + 25, cols.min(), cols.max(), op))
