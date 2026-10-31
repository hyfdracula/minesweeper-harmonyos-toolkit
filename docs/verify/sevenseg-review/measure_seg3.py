# -*- coding: utf-8 -*-
"""Exact glyph geometry of the Win7 counter digits in helpBoard.png:
   - recess (panel) bounds
   - connected components of lit pixels -> per-glyph bboxes
   - the literal RGB of the segment cores
"""
import numpy as np
from PIL import Image
from scipy import ndimage

P = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png'
im = Image.open(P).convert('RGB')
a = np.asarray(im).astype(int)
H, W, _ = a.shape
r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = 0.299 * r + 0.587 * g + 0.114 * b

print('=== RGB along row 183 (x 45..95) : left counter ===')
for x in range(45, 96):
    print('   x=%3d  rgb=%s lum=%6.1f' % (x, tuple(a[183, x]), lum[183, x]))

print('\n=== RGB along row 183 (x 168..210) : right counter ===')
for x in range(168, 210):
    print('   x=%3d  rgb=%s lum=%6.1f' % (x, tuple(a[183, x]), lum[183, x]))

# lit pixels inside the strip band
Y0, Y1 = 177, 190
band = lum[Y0:Y1 + 1]
lit = band > 150
print('\nlit map, threshold lum>150, y %d..%d, x 45..210' % (Y0, Y1))
for y in range(Y0, Y1 + 1):
    print('%3d |%s|' % (y, ''.join('#' if lit[y - Y0, x - 45] else ' ' for x in range(45, 211))))

lab, n = ndimage.label(lit)
print('\nconnected components (lit):')
for i, sl in enumerate(ndimage.find_objects(lab)):
    ys, xs = sl
    h = ys.stop - ys.start
    w = xs.stop - xs.start
    area = int((lab[sl] == (i + 1)).sum())
    if area < 2:
        continue
    print('   comp %2d: x %3d..%3d (w=%d)  y %3d..%3d (h=%d)  area=%d'
          % (i + 1, xs.start, xs.stop - 1, w, ys.start + Y0, ys.stop - 1 + Y0, h, area))

# core colours of the lit pixels
ys, xs = np.where(lit)
cols = a[ys + Y0, xs]
print('\nlit pixel colour stats (n=%d):' % len(cols))
print('   mean %s  median %s' % (cols.mean(axis=0).round(1), np.median(cols, axis=0)))
bright = cols[lum[ys + Y0, xs] > 200]
if len(bright):
    print('   brightest (>200) mean %s  min %s  max %s  n=%d'
          % (bright.mean(axis=0).round(1), bright.min(axis=0), bright.max(axis=0), len(bright)))
# per-component core colour
print('\nper-component core colour (pixels with lum>200):')
for i, sl in enumerate(ndimage.find_objects(lab)):
    ys2, xs2 = sl
    m = (lab[sl] == (i + 1))
    if m.sum() < 3:
        continue
    yy = ys2.start + Y0 + np.where(m)[0]
    xx = xs2.start + np.where(m)[1]
    cc = a[yy, xx]
    l2 = lum[yy, xx]
    core = cc[l2 > 195]
    print('   comp %2d x %3d..%3d y %3d..%3d : core mean %s  (n core %d)'
          % (i + 1, xs2.start, xs2.stop - 1, ys2.start + Y0, ys2.stop - 1 + Y0,
             core.mean(axis=0).round(1) if len(core) else 'n/a', len(core)))
