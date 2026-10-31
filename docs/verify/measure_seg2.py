# -*- coding: utf-8 -*-
"""Measure ONLY the status-strip LED panels of helpBoard.png (bottom strip)."""
import numpy as np
from PIL import Image

P = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png'
im = Image.open(P).convert('RGB')
a = np.asarray(im).astype(int)
H, W, _ = a.shape
r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = 0.299 * r + 0.587 * g + 0.114 * b

# the status strip of the illustration is the bottom band
Y0, Y1 = 160, 191

# a navy LED panel pixel: saturated blue, mid-dark
navy = (b - r > 45) & (b > 80) & (lum < 130)

print('=== navy runs per row, y %d..%d ===' % (Y0, Y1))
for y in range(Y0, Y1 + 1):
    row = navy[y]
    runs = []
    x = 0
    while x < W:
        if row[x]:
            s = x
            while x < W and row[x]:
                x += 1
            runs.append((s, x - 1))
        else:
            x += 1
    if runs:
        print('  y=%3d  %s' % (y, ' '.join('%d-%d' % r0 for r0 in runs)))

# union of navy in the strip -> connected column bands
cols = np.flatnonzero(navy[Y0:Y1 + 1].any(axis=0))
groups = []
if len(cols):
    s = cols[0]; p = cols[0]
    for c in cols[1:]:
        if c > p + 1:
            groups.append((s, p)); s = c
        p = c
    groups.append((s, p))
print('\nnavy column bands in strip:', groups)

for gi, (gx0, gx1) in enumerate(groups):
    rws = np.flatnonzero(navy[Y0:Y1 + 1, gx0:gx1 + 1].any(axis=1))
    if len(rws) == 0:
        continue
    gy0, gy1 = Y0 + int(rws.min()), Y0 + int(rws.max())
    if (gx1 - gx0) < 10 or (gy1 - gy0) < 5:
        continue
    print('\n================ PANEL %d : x %d..%d  y %d..%d ================' %
          (gi, gx0, gx1, gy0, gy1))
    for y in range(gy0, gy1 + 1):
        line = ''
        for x in range(gx0, gx1 + 1):
            px = a[y, x]
            L = 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]
            if L > 165:
                line += '#'
            elif L > 110:
                line += '+'
            elif px[2] - px[0] > 40:
                line += '.'
            else:
                line += ' '
        print('%3d |%s|' % (y, line))
    print('    ' + ''.join(str((x % 10)) for x in range(gx0, gx1 + 1)))
    print('    lit columns:', [int((lum[gy0:gy1 + 1, x] > 165).sum()) for x in range(gx0, gx1 + 1)])
    print('    lit rows   :', [int((lum[y, gx0:gx1 + 1] > 165).sum()) for y in range(gy0, gy1 + 1)])
    # colours
    lits = [(a[y, x]) for y in range(gy0, gy1 + 1) for x in range(gx0, gx1 + 1)
            if lum[y, x] > 165]
    navs = [(a[y, x]) for y in range(gy0, gy1 + 1) for x in range(gx0, gx1 + 1)
            if lum[y, x] <= 110 and a[y, x][2] - a[y, x][0] > 40]
    if lits:
        arr = np.array(lits)
        print('    lit  colour: mean RGB %s  min %s  max %s' %
              (arr.mean(axis=0).round(1), arr.min(axis=0), arr.max(axis=0)))
    if navs:
        arr = np.array(navs)
        print('    navy colour: mean RGB %s  min %s  max %s' %
              (arr.mean(axis=0).round(1), arr.min(axis=0), arr.max(axis=0)))
