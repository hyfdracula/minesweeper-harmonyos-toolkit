# -*- coding: utf-8 -*-
"""Locate the second (unused) copy of the coloured digits that the coverage map
found in otherSheet's bottom band, and confirm blueSheet's digitRect(n) is right."""
import os
import numpy as np
from PIL import Image

RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
S = 2

blue = Image.open(os.path.join(RAW, 'blueSheet.png')).convert('RGBA')
other = Image.open(os.path.join(RAW, 'otherSheet.png')).convert('RGBA')
b = np.asarray(blue)
o = np.asarray(other)

def nonwhite(a, box):
    x0, y0, x1, y1 = box
    sub = a[y0:y1, x0:x1]
    # "coloured" = saturated or clearly non-white/non-transparent
    rgb = sub[:, :, :3].astype(int)
    alpha = sub[:, :, 3]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    sat = mx - mn
    coloured = (sat > 40) & (alpha > 40)
    if not coloured.any():
        return None
    ys, xs = np.where(coloured)
    return (x0 + int(xs.min()), y0 + int(ys.min()),
            x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1, int(coloured.sum()))

print('otherSheet bottom band  (0,1948)-(2048,2016):')
bb = nonwhite(o, (0, 1948, 2048, 2016))
print('   coloured-pixel bbox  =', bb)

print('blueSheet digit column  (1990,0)-(2034,240):')
bb2 = nonwhite(b, (1990, 0, 2034, 240))
print('   coloured-pixel bbox  =', bb2)

# per-digit boxes in otherSheet
print('\notherSheet per-digit vertical segments (saturated pixels, x<1200):')
sub = o[1948:2016, 0:1200]
rgb = sub[:, :, :3].astype(int); al = sub[:, :, 3]
mask = ((rgb.max(axis=2) - rgb.min(axis=2)) > 40) & (al > 40)
rows = np.where(mask.any(axis=1))[0]
if len(rows):
    groups, start = [], rows[0]
    prev = rows[0]
    for y in rows[1:]:
        if y > prev + 1:
            groups.append((start, prev)); start = y
        prev = y
    groups.append((start, prev))
    for k, (y0, y1) in enumerate(groups):
        seg = mask[y0:y1 + 1]
        xs = np.where(seg.any(axis=0))[0]
        print('   digit %d: px x %d..%d  y %d..%d   (logical x %d..%d y %d..%d)'
              % (k + 1, xs.min(), xs.max(), 1948 + y0, 1948 + y1,
                 xs.min() // S, xs.max() // S, (1948 + y0) // S, (1948 + y1) // S))
        other.crop((xs.min(), 1948 + y0, xs.max() + 1, 1948 + y1 + 1)) \
            .resize(((xs.max() - xs.min() + 1) * 3, (y1 - y0 + 1) * 3), Image.NEAREST) \
            .convert('RGB').save(os.path.join(OUT, 'unused_otherSheet_digit%d.png' % (k + 1)))

# are the two digit sets identical pixels?
print('\ncompare blueSheet digitRect(n) vs otherSheet copy:')
for n in range(1, 9):
    bx = (2000, 30 * (n - 1), 2024, 30 * n)
    sub_o = o[1948:2016, 0:1200]
    # locate the n-th otherSheet digit
    rgb = sub_o[:, :, :3].astype(int); al = sub_o[:, :, 3]
    mask = ((rgb.max(axis=2) - rgb.min(axis=2)) > 40) & (al > 40)
    rows = np.where(mask.any(axis=1))[0]
    groups, start, prev = [], rows[0], rows[0]
    for y in rows[1:]:
        if y > prev + 1:
            groups.append((start, prev)); start = y
        prev = y
    groups.append((start, prev))
    if n - 1 >= len(groups):
        continue
    y0, y1 = groups[n - 1]
    xs = np.where(mask[y0:y1 + 1].any(axis=0))[0]
    crop_o = np.asarray(other.crop((xs.min(), 1948 + y0, xs.max() + 1, 1948 + y1 + 1)).resize((24, 30), Image.NEAREST))
    crop_b = np.asarray(blue.crop(bx).resize((24, 30), Image.NEAREST))
    diff = float(np.abs(crop_o[:, :, :3].astype(int) - crop_b[:, :, :3].astype(int)).mean())
    print('   digit %d: otherSheet copy vs blueSheet digitRect -> mean abs diff %.1f %s'
          % (n, diff, '(SAME ART)' if diff < 12 else '(different)'))
