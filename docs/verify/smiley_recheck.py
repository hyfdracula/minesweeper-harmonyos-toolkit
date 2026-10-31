# -*- coding: utf-8 -*-
"""INDEPENDENT re-verification of the smiley question, from the sprite bodies.

1) dump a full-sheet overview of every image asset (downscaled) for eyeballing
2) count "yellow disc" pixels (a Win7 smiley is a yellow circle)
3) structural face search: a 25x25 window with two symmetric dark blobs in the
   upper half (eyes) plus a dark blob in the lower half (mouth)
"""
import os
import numpy as np
from PIL import Image

REF = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
os.makedirs(OUT, exist_ok=True)

ASSETS = [
    ('images/blueSheet.png', 'blueSheet'),
    ('images/minesweeperSheet.png', 'minesweeperSheet'),
    ('images/otherSheet.png', 'otherSheet'),
    ('images/flowerGardenSheet.png', 'flowerGardenSheet'),
    ('images/greenSheet.png', 'greenSheet'),
    ('images/helpBoard.png', 'helpBoard'),
    ('images/thumbBlue.png', 'thumbBlue'),
    ('images/thumbGreen.png', 'thumbGreen'),
    ('images/thumbMines.png', 'thumbMines'),
    ('images/thumbFlowers.png', 'thumbFlowers'),
    ('icons/MineSweeper-32.png', 'icon32'),
    ('icons/MineSweeper-48.png', 'icon48'),
    ('icons/MineSweeper-64.png', 'icon64'),
    ('icons/MineSweeper-128.png', 'icon128'),
]

print('%-22s %-12s %8s %9s %8s' % ('asset', 'size', 'yellow', 'facehit', 'overview'))
summary = []
for rel, tag in ASSETS:
    p = os.path.join(REF, rel.replace('/', os.sep))
    im = Image.open(p).convert('RGBA')
    a = np.asarray(im).astype(int)
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    yellow = ((r > 170) & (g > 130) & (b < 130) & (al > 100)).sum()

    # ---- structural face search on a luminance channel -----------------------
    lum = (0.299 * r + 0.587 * g + 0.114 * b)
    dark = (lum < 110) & (al > 100)
    H, W = dark.shape
    hits = []
    step = 1 if max(H, W) <= 1200 else 2
    win = 25
    for y in range(0, H - win, step):
        for x in range(0, W - win, step):
            if not dark[y:y + win, x:x + win].any():
                continue
            top = dark[y + 4:y + 15, x:x + win]
            bot = dark[y + 15:y + win, x:x + win]
            if not top.any() or not bot.any():
                continue
            # column profile of the top half -> look for two separated lobes
            prof = top.sum(axis=0)
            nz = np.flatnonzero(prof)
            if len(nz) < 4:
                continue
            # split into runs
            runs, s = [], nz[0]
            p0 = nz[0]
            for c in nz[1:]:
                if c > p0 + 2:
                    runs.append((s, p0)); s = c
                p0 = c
            runs.append((s, p0))
            if len(runs) < 2:
                continue
            # two runs of comparable size, roughly symmetric about the centre
            r1, r2 = runs[-2], runs[-1]
            if (r2[0] - r1[1]) < 3:
                continue
            c1 = (r1[0] + r1[1]) / 2.0
            c2 = (r2[0] + r2[1]) / 2.0
            mid = (c1 + c2) / 2.0
            if abs((mid - (win - 1) / 2.0)) > 5:
                continue
            if (r2[1] - r2[0]) > 3 * max(1, r1[1] - r1[0]):
                continue
            hits.append((x, y))
    # ---- overview -----------------------------------------------------------
    ov = im.convert('RGB')
    ov.thumbnail((900, 900), Image.LANCZOS)
    fn = 'recheck_overview_%s.png' % tag
    ov.save(os.path.join(OUT, fn))
    print('%-22s %-12s %8d %9d %8s' % (tag, '%dx%d' % (im.width, im.height),
                                        yellow, len(hits), fn))
    summary.append((tag, im.width, im.height, int(yellow), len(hits)))
    if hits:
        # crop the first few candidates
        for k, (x, y) in enumerate(hits[:6]):
            im.crop((max(0, x - 12), max(0, y - 12),
                     min(im.width, x + win + 12), min(im.height, y + win + 12))) \
                .resize((49 * 6, 49 * 6), Image.NEAREST).convert('RGB') \
                .save(os.path.join(OUT, 'recheck_face_%s_%d.png' % (tag, k)))

print()
print('summary:')
for t, w, h, y, f in summary:
    print('  %-22s %5dx%-5d yellow=%-6d face-candidates=%d' % (t, w, h, y, f))
