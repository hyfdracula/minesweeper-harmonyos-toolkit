# -*- coding: utf-8 -*-
"""Sprite out-of-bounds re-check, including the new 1:1 helpBoard atlas.

Read-only against C:\\Users\\19161\\saolei. Writes only into docs\\verify\\sprites.
"""
import os
import struct
import json
from PIL import Image
import numpy as np

RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
S = 2  # SPRITE_SCALE
os.makedirs(OUT, exist_ok=True)

def png_size(p):
    with open(p, 'rb') as f:
        h = f.read(33)
    return struct.unpack('>II', h[16:24])

ATLAS = {}
for n in ('blueSheet.png', 'minesweeperSheet.png', 'otherSheet.png', 'helpBoard.png'):
    ATLAS[n] = os.path.join(RAW, n)
SIZE = {n: png_size(p) for n, p in ATLAS.items()}
IMG = {n: Image.open(p).convert('RGBA') for n, p in ATLAS.items()}
print('atlas sizes:', {k: '%dx%d' % v for k, v in SIZE.items()})

# ref = (name, sheet, source_file, logical_rect_or_None, frames, pitch, cols, use, times2)
REFS = [
    ('normalTileRect', 'blueSheet.png', 'Theme.ets:28', (0, 0, 18, 18), 720, (18, 18), 25,
     '未揭开的凸起方砖（720 帧渐变，25 帧/行）', True),
    ('pressedTileRect', 'blueSheet.png', 'Theme.ets:35', (500, 0, 18, 18), 720, (18, 18), 25,
     '已翻开的凹陷地板砖（= normalTileRect + 500 逻辑单位）', True),
    ('RECT_FLAG', 'blueSheet.png', 'Theme.ets:41', (400, 560, 18, 18), 1, None, 1, '红旗', True),
    ('RECT_QUESTION', 'blueSheet.png', 'Theme.ets:43', (420, 560, 18, 18), 1, None, 1, '问号', True),
    ('RECT_HILITE', 'blueSheet.png', 'Theme.ets:45', (440, 560, 18, 18), 1, None, 1, '悬停高亮（相加混合）', True),
    ('RECT_MISFLAG', 'blueSheet.png', 'Theme.ets:47', (460, 560, 18, 18), 1, None, 1, '错旗红叉', True),
    ('RECT_SHADOW_U', 'blueSheet.png', 'Theme.ets:49', (480, 560, 18, 3), 1, None, 1, '上边黑边 18×3', True),
    ('RECT_SHADOW_L', 'blueSheet.png', 'Theme.ets:51', (1012, 0, 3, 18), 1, None, 1, '左边黑边 3×18', True),
    ('INLINE_SHADOW_L_LOW', 'blueSheet.png', 'GameController.ets:510', (1012, 3, 3, 15), 1, None, 1,
     '内联字面量 [1012,3,3,15]：角落时从黑边下方开始的左黑边', True),
    ('RECT_COUNTER', 'blueSheet.png', 'Theme.ets:53', (0, 580, 40, 21), 1, None, 1, '计数器凹槽面板', True),
    ('digitRect(1..8)', 'blueSheet.png', 'Theme.ets:56', (1000, 0, 12, 15), 8, (0, 15), 8,
     '彩色数字 1..8（12×15 逻辑槽）', True),
    ('RECT_MINE', 'minesweeperSheet.png', 'Theme.ets:63', (27, 0, 18, 18), 1, None, 1, '格下地雷', True),
    ('RECT_PANEL_MINE', 'minesweeperSheet.png', 'Theme.ets:65', (0, 0, 25, 25), 1, None, 1,
     '状态条「雷图标」银钮', True),
    ('WinDialog.win.icon', 'minesweeperSheet.png', 'WinDialog.ets:323', (0, 0, 25, 25), 1, None, 1,
     '胜利/失败对话框的雷图标（字面量）', True),
    ('RECT_CLOCK', 'otherSheet.png', 'Theme.ets:70', (905, 425, 25, 25), 1, None, 1, '状态条时钟图标', True),
    ('Anim.explodeRect', 'otherSheet.png', 'Anim.ets:55', (728, 0, 57, 57), 23, (59, 59), 3,
     '踩雷爆炸动画 23 帧', True),
    ('Anim.disarmRect', 'otherSheet.png', 'Anim.ets:115', (0, 0, 50, 150), 38, (52, 152), 7,
     '胜利拆雷光束 38 帧', True),
    ('Anim.SCAN_BAR', 'otherSheet.png', 'Anim.ets:85', (0, 912, 275, 62), 1, None, 1, '胜利扫描条', True),
    ('SpriteAtlas.drawWhole(helpBoard)', 'helpBoard.png', 'SpriteAtlas.ets:147 / WinDialog.ets:463',
     (0, 0, 256, 192), 1, None, 1,
     '帮助窗口整图（1:1 图，源坐标不乘 SPRITE_SCALE；源矩形 = 256×pxScale vp）', False),
]

def to_px(logical, times2):
    x, y, w, h = logical
    return (x * S, y * S, w * S, h * S) if times2 else (x, y, w, h)

def over(px, sheet):
    W, H = SIZE[sheet]
    x, y, w, h = px
    ox = max(0, -x) + max(0, (x + w) - W)
    oy = max(0, -y) + max(0, (y + h) - H)
    n = ox * oy if (ox and oy) else (ox * min(h, H) if ox else (oy * min(w, W) if oy else 0))
    return ox, oy, n

cov = {n: np.zeros((SIZE[n][1], SIZE[n][0]), np.uint8) for n in SIZE}
rows, oob, dups = [], [], []
seen = {}

for name, sheet, src, L, n, pitch, cols, use, t2 in REFS:
    worst = None
    for i in range(n):
        if n == 1:
            px = to_px(L, t2)
        elif pitch[0] == 0:
            px = (L[0] * S, (L[1] + i * pitch[1]) * S, L[2] * S, L[3] * S)
        else:
            px = ((L[0] + pitch[0] * (i % cols)) * S, (L[1] + pitch[1] * (i // cols)) * S,
                  L[2] * S, L[3] * S)
        ox, oy, o = over(px, sheet)
        if worst is None or o > worst[3]:
            worst = (i, px, (ox, oy), o)
        W, H = SIZE[sheet]
        x0, y0 = max(0, px[0]), max(0, px[1])
        x1, y1 = min(W, px[0] + px[2]), min(H, px[1] + px[3])
        if x1 > x0 and y1 > y0:
            cov[sheet][y0:y1, x0:x1] = 1
        k = (sheet, px)
        if k in seen:
            dups.append((seen[k], name, sheet, px))
        else:
            seen[k] = name
    rows.append(dict(ref=name, sheet=sheet, src=src, worst_px=worst[1], worst_frame=worst[0],
                     size=SIZE[sheet], over=worst[3], ox=worst[2][0], oy=worst[2][1],
                     frames=n, use=use, times2=t2))
    if worst[3] or worst[2][0] or worst[2][1]:
        oob.append(rows[-1])

# crop every reference's first frame + helpBoard itself
for r in rows:
    sheet, px = r['sheet'], r['worst_px']
    im = IMG[sheet]
    W, H = SIZE[sheet]
    x0, y0 = max(0, px[0]), max(0, px[1])
    x1, y1 = min(W, px[0] + px[2]), min(H, px[1] + px[3])
    if x1 > x0 and y1 > y0:
        fn = 'v2_%s.png' % r['ref'].split('(')[0].replace('.', '_').replace('[', '').replace(']', '')
        im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST) \
            .convert('RGB').save(os.path.join(OUT, fn))

print()
print('%-34s %-22s %-22s %s' % ('reference', 'source px (worst frame)', 'atlas', 'over'))
for r in rows:
    print('%-34s %-22s %-22s over=%d px (ox=%d oy=%d) frames=%d' % (
        r['ref'], str(r['worst_px']), '%dx%d' % r['size'], r['over'], r['ox'], r['oy'], r['frames']))

print()
print('=== OUT OF BOUNDS: %d ===' % len(oob))
for o in oob:
    print('   %s -> %s over=%d' % (o['ref'], o['worst_px'], o['over']))
print('duplicate groups: %d' % len(set((a, b, s) for a, b, s, _ in dups)))
for a, b, s, px in dups:
    print('   %s == %s (%s %s)' % (a, b, s, px))
print('total source rects: %d' % sum(r['frames'] for r in rows))

# ---- helpBoard specific: prove the vp source rect maps back to the bitmap ----
print()
print('--- helpBoard drawWhole unit proof ---')
for density in (1.0, 2.0, 3.125, 3.5):
    pxScale = 1.0 / density
    src_vp = (256 * pxScale, 192 * pxScale)
    back_px = (src_vp[0] * density, src_vp[1] * density)
    dst_dev = (256 * pxScale * density, 192 * pxScale * density)
    print('   density=%-6s pxScale=%.4f  source rect vp=(%.3f, %.3f) -> bitmap px=(%.1f, %.1f) %s'
          '  dest dev px=(%.1f, %.1f)' % (
              density, pxScale, src_vp[0], src_vp[1], back_px[0], back_px[1],
              'OK 256x192' if (abs(back_px[0] - 256) < .01 and abs(back_px[1] - 192) < .01) else 'MISMATCH',
              dst_dev[0], dst_dev[1]))

json.dump(dict(rows=rows, oob=oob, dups=dups), open(os.path.join(OUT, '_audit_v2.json'), 'w'),
          ensure_ascii=False, indent=1)
