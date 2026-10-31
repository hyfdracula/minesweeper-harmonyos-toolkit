# -*- coding: utf-8 -*-
"""Measure the original Win7 counter panels in helpBoard.png, pixel-exact.

Prints an ASCII map of the glyph area of both LED panels so the seven-segment
geometry can be read off directly.
"""
import numpy as np
from PIL import Image

P = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png'
im = Image.open(P).convert('RGB')
a = np.asarray(im).astype(int)
H, W, _ = a.shape
print('helpBoard %dx%d' % (W, H))

r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
lum = 0.299 * r + 0.587 * g + 0.114 * b

# navy LED panel: blue dominant and fairly dark
navy = (b > 90) & (b < 190) & (r < 90) & (g < 130) & (b - r > 50)
ys, xs = np.where(navy)
print('navy pixels: %d  x %d..%d  y %d..%d' % (len(xs), xs.min(), xs.max(), ys.min(), ys.max()))

# cluster navy pixels into horizontal runs to find the two panels
rows = {}
for y in range(H):
    row = np.flatnonzero(navy[y])
    if len(row):
        rows[y] = (row.min(), row.max(), len(row))
print('\nnavy rows (y: xmin..xmax count):')
for y in sorted(rows):
    print('   y=%3d  x %3d..%3d  n=%d' % (y, rows[y][0], rows[y][1], rows[y][2]))

# find the panels as column groups with many navy rows
colcount = navy.sum(axis=0)
groups, cur = [], None
for x in range(W):
    if colcount[x] >= 6:
        if cur is None:
            cur = [x, x]
        else:
            cur[1] = x
    else:
        if cur is not None:
            groups.append(tuple(cur)); cur = None
if cur is not None:
    groups.append(tuple(cur))
print('\nnavy column groups (>=6 rows):', groups)


def ascii_panel(x0, x1, y0, y1, title):
    print('\n=== %s  x %d..%d  y %d..%d ===' % (title, x0, x1, y0, y1))
    # glyph = bright pixels inside the navy area
    for y in range(y0, y1 + 1):
        line = ''
        for x in range(x0, x1 + 1):
            px = a[y, x]
            L = 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]
            if L > 175:
                line += '#'      # lit segment
            elif L > 120:
                line += '+'      # anti-aliased edge
            elif px[2] - px[0] > 40:
                line += '.'      # navy panel
            else:
                line += ' '
        print('%3d |%s|' % (y, line))
    print('    ' + ''.join(str((x % 10)) for x in range(x0, x1 + 1)))
    # column brightness profile of lit pixels
    print('    lit-pixel column counts:',
          [int(((lum[y0:y1 + 1, x] > 175)).sum()) for x in range(x0, x1 + 1)])
    print('    lit-pixel row counts:   ',
          [int(((lum[y, x0:x1 + 1] > 175)).sum()) for y in range(y0, y1 + 1)])


for i, (gx0, gx1) in enumerate(groups):
    yy = [y for y in rows if gx0 <= rows[y][0] and rows[y][1] <= gx1 + 2]
    if not yy:
        continue
    ascii_panel(gx0, gx1, min(yy), max(yy), 'panel %d' % i)
