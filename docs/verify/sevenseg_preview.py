# -*- coding: utf-8 -*-
"""Preview of the FINAL SevenSeg geometry, composited onto the real counter panel sprite.

Mirrors entry/src/main/ets/common/SevenSeg.ets exactly:
  SLOT_X0=0, SLOT_PITCH=13, CELL_W=12, CELL_H=16, CELL_Y=2, TV=3, TH=2, HL=5
  SEG_FLAG=128, digit 1 = 0x8E (b + c + d + flag)
  flag rect = (cellX + TV - 2, cellY + TH, 2, 2)
"""
import os
from PIL import Image, ImageDraw

OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
REF = r'C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png'
RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'

# ---- final geometry (mirrors SevenSeg.ets) ----
PANEL_W, PANEL_H = 40, 21
SLOT_COUNT, SLOT_X0, SLOT_PITCH = 3, 0, 13
CELL_W, CELL_H, CELL_Y = 12, 16, 2
TV, TH, HL = 3, 2, 5
MIN_V, MAX_V = -99, 999
LIT = (250, 250, 252)

SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G, SEG_FLAG, SEG_BASE1 = \
    1, 2, 4, 8, 16, 32, 64, 128, 256
DIGITS = [0x3F, 0x186, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]


def slots_for(value):
    out = [0, 0, 0]
    if value != value or value in (float('inf'), float('-inf')):
        return out
    n = int(value)
    if n > MAX_V:
        n = MAX_V
    elif n < MIN_V:
        n = MIN_V
    neg = n < 0
    n = -n if neg else n
    ds = [0] if n == 0 else []
    while n > 0:
        ds.append(n % 10)
        n //= 10
    text = ds[::-1]
    start, count = 0, len(text)
    if neg and count >= SLOT_COUNT:
        count = SLOT_COUNT - 1
        start = len(text) - count
    elif count > SLOT_COUNT:
        start = len(text) - SLOT_COUNT
        count = SLOT_COUNT
    for i in range(count):
        out[SLOT_COUNT - count + i] = DIGITS[text[start + i]]
    if neg:
        slot = SLOT_COUNT - count - 1
        out[slot if slot >= 0 else 0] = SEG_G
    return out


def draw_value(d, value, ox, oy, k):
    """k = 缩放倍数（参考像素 -> 画布像素）。"""
    for i, mask in enumerate(slots_for(value)):
        if not mask:
            continue
        cx = (ox + SLOT_X0 + i * SLOT_PITCH) * k
        cy = (oy + CELL_Y) * k
        tv, th, hl = TV * k, TH * k, HL * k
        hw = (CELL_W - 2 * TV) * k
        w, h = CELL_W * k, CELL_H * k
        if mask & SEG_A:
            d.rectangle([cx + tv, cy, cx + tv + hw - 1, cy + th - 1], fill=LIT)
        if mask & SEG_B:
            d.rectangle([cx + w - tv, cy + th, cx + w - 1, cy + th + hl - 1], fill=LIT)
        if mask & SEG_C:
            d.rectangle([cx + w - tv, cy + 2 * th + hl, cx + w - 1, cy + 2 * th + 2 * hl - 1], fill=LIT)
        if mask & SEG_D:
            d.rectangle([cx + tv, cy + h - th, cx + tv + hw - 1, cy + h - 1], fill=LIT)
        if mask & SEG_E:
            d.rectangle([cx, cy + 2 * th + hl, cx + tv - 1, cy + 2 * th + 2 * hl - 1], fill=LIT)
        if mask & SEG_F:
            d.rectangle([cx, cy + th, cx + tv - 1, cy + th + hl - 1], fill=LIT)
        if mask & SEG_G:
            d.rectangle([cx + tv, cy + th + hl, cx + tv + hw - 1, cy + 2 * th + hl - 1], fill=LIT)
        if mask & SEG_FLAG:
            # 与 SevenSeg.ets 一致：旗 = (cellX + CELL_W - TV - 2, cellY + TH, 2, 2)
            # 即紧挨 b 竖段（x 9..11）左沿的 x 7..8，高度对齐 b 的上端
            fx = (CELL_W - TV - 2) * k
            d.rectangle([cx + fx, cy + th, cx + fx + 2 * k - 1, cy + th + 2 * k - 1], fill=LIT)
        if mask & SEG_BASE1:
            # 与 SevenSeg.ets 一致：底横 = (cellX + CELL_W - TV - 2, cellY + CELL_H - TH, TV + 2, TH)
            # 即以竖笔（x 9..11）为中心向两侧伸出的 x 7..11，在最下一行
            bx = (CELL_W - TV - 2) * k
            d.rectangle([cx + bx, cy + h - th, cx + bx + (TV + 2) * k - 1, cy + h - 1], fill=LIT)


def on_real_panel(value, scale):
    """Composite the digits onto the real RECT_COUNTER sprite (stored 80x42 px = logical 40x21)."""
    im = Image.open(os.path.join(RAW, 'blueSheet.png')).convert('RGB')
    panel = im.crop((0, 1160, 80, 1202)).copy()
    draw_value(ImageDraw.Draw(panel), value, 0, 0, 2)
    return panel.resize((80 * scale, 42 * scale), Image.NEAREST)


Z = 6
hb = Image.open(REF).convert('RGB')
orig = [hb.crop((52, 178, 81, 189)).resize((29 * Z, 11 * Z), Image.NEAREST),
        hb.crop((174, 178, 203, 189)).resize((29 * Z, 11 * Z), Image.NEAREST)]

rows = [('Microsoft original (helpBoard.png): "18" / "-40"', orig),
        ('SevenSeg on the real RECT_COUNTER sprite: 18 / -40',
         [on_real_panel(18, 6), on_real_panel(-40, 6)])]

extra = list(range(0, 10)) + [-1, -4, -40, 99, 123, -99, 999]
rows.append(('on the real panel: 0..9, -1, -4, -40, 99, 123, -99, 999',
             [on_real_panel(v, 3) for v in extra]))

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
canvas.save(os.path.join(OUT, 'sevenseg_preview.png'))
print('sevenseg_preview.png  %dx%d' % canvas.size)
