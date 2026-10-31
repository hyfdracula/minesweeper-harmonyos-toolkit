# -*- coding: utf-8 -*-
"""Compare candidate SevenSeg geometries against Microsoft's own LED drawing."""
import os
from PIL import Image, ImageDraw

OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
REF = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png'

LIT = (250, 250, 252)
NAVY = (45, 79, 146)
SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = 1, 2, 4, 8, 16, 32, 64
DIGITS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]


def slots_for(value, slots_n=3):
    out = [0] * slots_n
    n = int(value)
    neg = n < 0
    n = -n if neg else n
    ds = [0] if n == 0 else []
    while n > 0:
        ds.append(n % 10)
        n //= 10
    text = ds[::-1]
    start, count = 0, len(text)
    if neg and count >= slots_n:
        count = slots_n - 1
        start = len(text) - count
    elif count > slots_n:
        start = len(text) - slots_n
        count = slots_n
    for i in range(count):
        out[slots_n - count + i] = DIGITS[text[start + i]]
    if neg:
        slot = slots_n - count - 1
        out[slot if slot >= 0 else 0] = SEG_G
    return out


def draw_value(d, value, ox, oy, cell_w, cell_h, tv, th, hl, slot_x0, pitch, slots_n):
    for i, mask in enumerate(slots_for(value, slots_n)):
        if not mask:
            continue
        cx = ox + slot_x0 + i * pitch
        if mask & SEG_A:
            d.rectangle([cx + tv, oy, cx + cell_w - tv, oy + th - 1], fill=LIT)
        if mask & SEG_B:
            d.rectangle([cx + cell_w - tv, oy + th, cx + cell_w - 1, oy + th + hl - 1], fill=LIT)
        if mask & SEG_C:
            d.rectangle([cx + cell_w - tv, oy + 2 * th + hl, cx + cell_w - 1,
                         oy + 2 * th + 2 * hl - 1], fill=LIT)
        if mask & SEG_D:
            d.rectangle([cx + tv, oy + cell_h - th, cx + cell_w - tv, oy + cell_h - 1], fill=LIT)
        if mask & SEG_E:
            d.rectangle([cx, oy + 2 * th + hl, cx + tv - 1, oy + 2 * th + 2 * hl - 1], fill=LIT)
        if mask & SEG_F:
            d.rectangle([cx, oy + th, cx + tv - 1, oy + th + hl - 1], fill=LIT)
        if mask & SEG_G:
            d.rectangle([cx + tv, oy + th + hl, cx + cell_w - tv, oy + 2 * th + hl - 1], fill=LIT)


# (label, cell_w, cell_h, tv, th, hl, slot_x0, pitch, slots, y_off)
VARIANTS = [
    ('V1 13x21 tv3 th3 hl6 (fills panel)', 13, 21, 3, 3, 6, 1, 13, 3, 0),
    ('V2 13x18 tv3 th2 hl6 (illus. aspect)', 13, 18, 3, 2, 6, 1, 13, 3, 1),
    ('V3 13x18 tv2 th2 hl6 (thin bars)', 13, 18, 2, 2, 6, 1, 13, 3, 1),
    ('V4 13x16 tv3 th2 hl5 (tight)', 13, 16, 3, 2, 5, 1, 13, 3, 2),
]

PANEL_W, PANEL_H = 40, 21
Z = 6

hb = Image.open(REF).convert('RGB')
orig = [hb.crop((52, 178, 81, 189)).resize((29 * Z, 11 * Z), Image.NEAREST),
        hb.crop((174, 178, 203, 189)).resize((29 * Z, 11 * Z), Image.NEAREST)]

rows = [('Microsoft original (helpBoard.png)', orig)]
for label, cw, ch, tv, th, hl, sx0, pitch, slots, yoff in VARIANTS:
    ims = []
    for v in (18, -40):
        im = Image.new('RGB', (PANEL_W, PANEL_H), NAVY)
        d = ImageDraw.Draw(im)
        draw_value(d, v, 0, yoff, cw, ch, tv, th, hl, sx0, pitch, slots)
        ims.append(im.resize((PANEL_W * Z, PANEL_H * Z), Image.NEAREST))
    rows.append((label, ims))

W = max(sum(i.width for i in g) + 20 * (len(g) - 1) for _, g in rows)
H = sum(max(i.height for i in g) + 26 for _, g in rows)
canvas = Image.new('RGB', (W, H), (240, 240, 240))
d = ImageDraw.Draw(canvas)
y = 0
for label, g in rows:
    x = 0
    for im in g:
        canvas.paste(im, (x, y))
        x += im.width + 20
    d.text((4, y + max(i.height for i in g) + 6), label, fill=(0, 0, 0))
    y += max(i.height for i in g) + 26
canvas.save(os.path.join(OUT, 'sevenseg_variants.png'))
print('sevenseg_variants.png  %dx%d' % canvas.size)
