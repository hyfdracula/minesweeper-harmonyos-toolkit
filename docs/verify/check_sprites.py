# -*- coding: utf-8 -*-
"""
Sprite reference completeness / out-of-bounds audit for the HarmonyOS minesweeper app.

Read-only against:
  C:\\Users\\19161\\saolei\\entry\\src\\main\\resources\\rawfile\\*.png   (runtime atlases)
  C:\\Users\\19161\\saolei\\entry\\src\\main\\ets\\common\\*.ets          (constant sources)

Writes only into:
  D:\\software\\harmony\\projects\\minesweeper\\docs\\verify\\sprites\\
"""
import os
import sys
import struct
import json

OUT = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
RAW = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile'
ETS = r'C:\Users\19161\saolei\entry\src\main\ets\common'

try:
    from PIL import Image
    import numpy as np
    HAVE = True
except Exception as e:            # pragma: no cover
    print('PIL/numpy unavailable:', e)
    raise SystemExit(2)

S = 2  # SPRITE_SCALE from Theme.ets

os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- atlases
def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(33)
    w, h = struct.unpack('>II', head[16:24])
    return w, h

ATLAS = {
    'blueSheet.png':   os.path.join(RAW, 'blueSheet.png'),
    'minesweeperSheet.png': os.path.join(RAW, 'minesweeperSheet.png'),
    'otherSheet.png':  os.path.join(RAW, 'otherSheet.png'),
}
SIZE = {}
for name, p in ATLAS.items():
    SIZE[name] = png_size(p)
    print('atlas %-22s %s' % (name, SIZE[name]))

IMG = {n: Image.open(p).convert('RGBA') for n, p in ATLAS.items()}

# ---------------------------------------------------------------- the table
# rect = (x, y, w, h) in LOGICAL units (Theme.ets convention); *2 = stored pixels.
# kind: 'one'  single crop
#       'fam'  parametric family -> sample frames cropped individually + contact sheet
#       'blk'  a contiguous block of the sheet (used for coverage only)

REFS = [
    # ---- blueSheet ----------------------------------------------------
    dict(id='normalTileRect', sheet='blueSheet.png', file='Theme.ets:28',
         kind='fam', logical=(0, 0, 18, 18),
         family='normal', count=720, pitch=(18, 18), cols=25,
         use='未揭开的凸起方砖（720 帧渐变，25 帧/行）'),
    dict(id='pressedTileRect', sheet='blueSheet.png', file='Theme.ets:35',
         kind='fam', logical=(500, 0, 18, 18),
         family='pressed', count=720, pitch=(18, 18), cols=25,
         use='已翻开的凹陷地板砖（720 帧渐变，= normalTileRect + 500 逻辑单位）'),
    dict(id='RECT_FLAG', sheet='blueSheet.png', file='Theme.ets:41',
         kind='one', logical=(400, 560, 18, 18), use='红旗'),
    dict(id='RECT_QUESTION', sheet='blueSheet.png', file='Theme.ets:43',
         kind='one', logical=(420, 560, 18, 18), use='问号'),
    dict(id='RECT_HILITE', sheet='blueSheet.png', file='Theme.ets:45',
         kind='one', logical=(440, 560, 18, 18), use='悬停高亮（相加混合）'),
    dict(id='RECT_MISFLAG', sheet='blueSheet.png', file='Theme.ets:47',
         kind='one', logical=(460, 560, 18, 18), use='错旗红叉'),
    dict(id='RECT_SHADOW_U', sheet='blueSheet.png', file='Theme.ets:49',
         kind='one', logical=(480, 560, 18, 3), use='上边黑边（18×3）'),
    dict(id='RECT_SHADOW_L', sheet='blueSheet.png', file='Theme.ets:51',
         kind='one', logical=(1012, 0, 3, 18), use='左边黑边（3×18）'),
    dict(id='INLINE_SHADOW_L_LOW', sheet='blueSheet.png', file='GameController.ets:436',
         kind='one', logical=(1012, 3, 3, 15),
         use='内联字面量：角落时从黑边下方开始的左黑边'),
    dict(id='RECT_COUNTER', sheet='blueSheet.png', file='Theme.ets:53',
         kind='one', logical=(0, 580, 40, 21), use='计数器凹槽面板'),
    dict(id='digitRect(1..8)', sheet='blueSheet.png', file='Theme.ets:56',
         kind='fam', logical=(1000, 0, 12, 15),
         family='digit', count=8, pitch=(0, 15), cols=8,
         use='彩色数字 1..8（12×15 逻辑槽）'),

    # ---- minesweeperSheet ----------------------------------------------
    dict(id='RECT_MINE', sheet='minesweeperSheet.png', file='Theme.ets:63',
         kind='one', logical=(27, 0, 18, 18), use='格下地雷'),
    dict(id='RECT_PANEL_MINE', sheet='minesweeperSheet.png', file='Theme.ets:65',
         kind='one', logical=(0, 0, 25, 25), use='状态条「雷图标」圆钮'),
    dict(id='WinDialog.win.icon', sheet='minesweeperSheet.png', file='WinDialog.ets:303',
         kind='one', logical=(0, 0, 25, 25), use='胜利对话框里的雷图标（字面量）'),

    # ---- otherSheet -----------------------------------------------------
    dict(id='RECT_CLOCK', sheet='otherSheet.png', file='Theme.ets:70',
         kind='one', logical=(905, 425, 25, 25), use='状态条时钟图标'),
    dict(id='Anim.explodeRect', sheet='otherSheet.png', file='Anim.ets:55',
         kind='fam', logical=(728, 0, 57, 57),
         family='explode', count=23, pitch=(59, 59), cols=3,
         use='踩雷爆炸动画 23 帧'),
    dict(id='Anim.disarmRect', sheet='otherSheet.png', file='Anim.ets:115',
         kind='fam', logical=(0, 0, 50, 150),
         family='disarm', count=38, pitch=(52, 152), cols=7,
         use='胜利拆雷光束 38 帧'),
    dict(id='Anim.SCAN_BAR', sheet='otherSheet.png', file='Anim.ets:85',
         kind='one', logical=(0, 912, 275, 62), use='胜利扫描条'),

    # ---- dead duplicates (still exported by Theme.ets) -------------------
    dict(id='Theme.tripRect(DEAD)', sheet='otherSheet.png', file='Theme.ets:74',
         kind='fam', logical=(728, 0, 57, 57),
         family='explode', count=23, pitch=(59, 59), cols=3,
         use='未引用：与 Anim.explodeRect 完全相同'),
    dict(id='Theme.disarmRect(DEAD)', sheet='otherSheet.png', file='Theme.ets:82',
         kind='fam', logical=(0, 0, 50, 150),
         family='disarm', count=38, pitch=(52, 152), cols=7,
         use='未引用：与 Anim.disarmRect 完全相同'),
    dict(id='Theme.RECT_SCAN_BAR(DEAD)', sheet='otherSheet.png', file='Theme.ets:89',
         kind='one', logical=(0, 912, 275, 62),
         use='未引用：与 Anim.SCAN_BAR 完全相同'),
]

# unreferenced-but-present constant scalars (no rect of their own)
SCALARS = [
    ('Theme.TRIP_FRAMES', 'Theme.ets:73', '23', 'Anim.EXPLODE_FRAMES 同值，未引用'),
    ('Theme.TRIP_OFFSET', 'Theme.ets:78', '[-18,-18]', 'Anim.EXPLODE_OFFSET 同值，未引用'),
    ('Theme.DISARM_FRAMES', 'Theme.ets:81', '38', 'Anim.DISARM_FRAMES 同值，未引用'),
    ('Theme.DISARM_OFFSET', 'Theme.ets:86', '[-18,-69]', 'Anim.DISARM_OFFSET 同值，未引用'),
    ('SpriteAtlas.frameSheet', 'SpriteAtlas.ets:27', 'PixelMap|null',
     '声明了但从不赋值、从不使用（Frame.png 也没进 rawfile）'),
]

# ---------------------------------------------------------------- helpers
def to_px(logical):
    x, y, w, h = logical
    return (x * S, y * S, w * S, h * S)

def over_bounds(px, sheet):
    W, H = SIZE[sheet]
    x, y, w, h = px
    ox = max(0, -x) + max(0, (x + w) - W)
    oy = max(0, -y) + max(0, (y + h) - H)
    over = 0
    if ox > 0 and oy > 0:
        over = ox * oy
    elif ox > 0:
        over = ox * min(h, H)
    elif oy > 0:
        over = oy * min(w, W)
    return ox, oy, over

def crop_save(sheet, px, outname, scale=1, label=None):
    im = IMG[sheet]
    W, H = SIZE[sheet]
    x, y, w, h = px
    # clip for display, but record the true rect
    cx0, cy0 = max(0, x), max(0, y)
    cx1, cy1 = min(W, x + w), min(H, y + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return None
    sub = im.crop((cx0, cy0, cx1, cy1))
    if scale > 1:
        sub = sub.resize((sub.width * scale, sub.height * scale), Image.NEAREST)
    p = os.path.join(OUT, outname)
    sub.save(p)
    return p

# ---------------------------------------------------------------- coverage
cov = {n: np.zeros((SIZE[n][1], SIZE[n][0]), dtype=np.uint8) for n in SIZE}

def mark(sheet, px):
    W, H = SIZE[sheet]
    x, y, w, h = px
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 > x0 and y1 > y0:
        cov[sheet][y0:y1, x0:x1] = 1

# ---------------------------------------------------------------- run
rows = []
oob = []
dup_pairs = []
seen = {}
family_px = {}

for r in REFS:
    sheet = r['sheet']
    if r['kind'] == 'one':
        px = to_px(r['logical'])
        ox, oy, over = over_bounds(px, sheet)
        mark(sheet, px)
        crop = crop_save(sheet, px, '%s.png' % r['id'].replace('.', '_').replace('(', '_').replace(')', ''))
        rows.append(dict(ref=r['id'], sheet=sheet, where=r['file'], px=px,
                         size=SIZE[sheet], over=over, ox=ox, oy=oy,
                         use=r['use'], crop=os.path.basename(crop) if crop else None))
        if over > 0 or ox or oy:
            oob.append(rows[-1])
        key = (sheet, px)
        if key in seen:
            dup_pairs.append((seen[key], r['id'], sheet, px))
        else:
            seen[key] = r['id']
    else:
        fam = r['family']
        L = r['logical']
        pw, ph = r['pitch']
        cols = r['cols']
        n = r['count']
        worst = None
        for i in range(n):
            if fam == 'digit':
                px = (L[0] * S, (L[1] + i * ph) * S, L[2] * S, L[3] * S)
            else:
                px = ((L[0] + pw * (i % cols)) * S, (L[1] + ph * (i // cols)) * S,
                      L[2] * S, L[3] * S)
            ox, oy, over = over_bounds(px, sheet)
            if worst is None or over > worst[3]:
                worst = (i, px, (ox, oy), over)
            mark(sheet, px)
            key = (sheet, px)
            if key in seen:
                dup_pairs.append((seen[key], r['id'], sheet, px))
            else:
                seen[key] = r['id']
        family_px[r['id']] = (sheet, fam, L, pw, ph, cols, n, worst)
        rows.append(dict(ref=r['id'], sheet=sheet, where=r['file'],
                         px=worst[1], size=SIZE[sheet],
                         over=worst[3], ox=worst[2][0], oy=worst[2][1],
                         use=r['use'], crop=None, frames=n,
                         worst_frame=worst[0]))

# ---------------------------------------------------------------- crops for families
SAMPLES = {
    'normal': [0, 1, 24, 25, 100, 349, 699, 718, 719],
    'pressed': [0, 1, 24, 25, 100, 349, 699, 718, 719],
    'digit': list(range(1, 9)),
    'explode': list(range(23)),
    'disarm': list(range(38)),
}
CONTACT = {
    'explode': ('explode_frames_contact.png', 6),
    'disarm': ('disarm_frames_contact.png', 8),
    'normal': ('normal_tiles_contact.png', 25),
    'pressed': ('pressed_tiles_contact.png', 25),
    'digit': ('digits_contact.png', 8),
}

for rid, (sheet, fam, L, pw, ph, cols, n, worst) in family_px.items():
    base = rid.split('(')[0]
    for i in SAMPLES.get(fam, []):
        if i >= n:
            continue
        if fam == 'digit':
            px = (L[0] * S, (L[1] + i * ph) * S, L[2] * S, L[3] * S)
            nm = '%s_%d.png' % (base, i)
        else:
            px = ((L[0] + pw * (i % cols)) * S, (L[1] + ph * (i // cols)) * S,
                  L[2] * S, L[3] * S)
            nm = '%s_f%02d.png' % (base, i)
        crop_save(sheet, px, nm, scale=2 if fam != 'disarm' else 1)
    # contact sheet
    if fam in CONTACT:
        cn, per = CONTACT[fam]
        frames = list(range(n))
        cw, ch = L[2] * S, L[3] * S
        sc = 1
        if fam == 'disarm':
            sc = 1
        cols2 = per
        rows2 = (len(frames) + cols2 - 1) // cols2
        sheet_im = Image.new('RGBA', (cols2 * cw * sc + (cols2 + 1) * 4,
                                      rows2 * ch * sc + (rows2 + 1) * 4),
                             (255, 0, 255, 255))
        for k, i in enumerate(frames):
            if fam == 'digit':
                px = (L[0] * S, (L[1] + i * ph) * S, L[2] * S, L[3] * S)
            else:
                px = ((L[0] + pw * (i % cols)) * S, (L[1] + ph * (i // cols)) * S,
                      L[2] * S, L[3] * S)
            cx0, cy0 = max(0, px[0]), max(0, px[1])
            cx1, cy1 = min(SIZE[sheet][0], px[0] + px[2]), min(SIZE[sheet][1], px[1] + px[3])
            if cx1 <= cx0 or cy1 <= cy0:
                continue
            sub = IMG[sheet].crop((cx0, cy0, cx1, cy1))
            if sc > 1:
                sub = sub.resize((sub.width * sc, sub.height * sc), Image.NEAREST)
            gx = 4 + (k % cols2) * (cw * sc + 4)
            gy = 4 + (k // cols2) * (ch * sc + 4)
            sheet_im.alpha_composite(sub, (gx, gy))
        sheet_im.convert('RGB').save(os.path.join(OUT, cn))

# ---------------------------------------------------------------- unreferenced regions
def uncovered_blocks(sheet, min_area=256):
    """Free (unreferenced) pixels, decomposed into clean rectangles.

    Row-run decomposition: for every row find the runs of free pixels, then
    merge identical runs vertically into bands, then merge horizontally
    adjacent bands with the same vertical extent.
    """
    a = cov[sheet]
    H, W = a.shape
    free = (a == 0)

    # row runs
    row_runs = []
    for y in range(H):
        r = free[y]
        if not r.any():
            row_runs.append([])
            continue
        idx = np.flatnonzero(np.diff(np.concatenate(([0], r.view(np.int8), [0]))))
        runs = []
        for k in range(0, len(idx), 2):
            runs.append((int(idx[k]), int(idx[k + 1]) - 1))
        row_runs.append(runs)

    # merge identical runs vertically
    bands = []           # (x0, x1, y0, y1)
    open_bands = {}
    for y, runs in enumerate(row_runs):
        cur = set(runs)
        for key in list(open_bands):
            if key not in cur:
                x0, x1, y0 = open_bands.pop(key)
                bands.append((x0, x1, y0, y - 1))
        for run in runs:
            if run in open_bands:
                continue
            open_bands[run] = (run[0], run[1], y)
    for key, (x0, x1, y0) in open_bands.items():
        bands.append((x0, x1, y0, H - 1))

    # merge horizontally adjacent bands sharing the same vertical extent
    bands.sort(key=lambda b: (b[2], b[0]))
    merged = []
    for b in bands:
        if merged:
            m = merged[-1]
            if m[2] == b[2] and m[3] == b[3] and m[1] + 1 >= b[0]:
                merged[-1] = (m[0], max(m[1], b[1]), m[2], m[3])
                continue
        merged.append(b)

    out = []
    for x0, x1, y0, y1 in merged:
        w = x1 - x0 + 1
        h = y1 - y0 + 1
        area = w * h
        if area < min_area:
            continue
        out.append((x0, y0, w, h, area))
    out.sort(key=lambda b: -b[4])
    return out

UNREF = {}
for sheet in SIZE:
    blocks = uncovered_blocks(sheet)
    UNREF[sheet] = blocks
    print('\n%s unreferenced blocks (top 14):' % sheet)
    for b in blocks[:14]:
        print('   x %4d..%-4d y %4d..%-4d  w=%4d h=%4d  area=%d' %
              (b[0], b[0] + b[2] - 1, b[1], b[1] + b[3] - 1, b[2], b[3], b[4]))

# ---------------------------------------------------------------- dump
with open(os.path.join(OUT, '_audit.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(rows=rows, oob=oob, dup=dup_pairs, unref=UNREF,
                   scalars=SCALARS), f, ensure_ascii=False, indent=1)

print('\n=== SUMMARY ===')
print('reference entries : %d' % len(rows))
print('out of bounds     : %d' % len(oob))
for o in oob:
    print('   %s -> px%s  over=%d px (ox=%d, oy=%d)' % (o['ref'], o['px'], o['over'], o['ox'], o['oy']))

# collapse duplicates into (refA, refB, sheet, count, pixels)
agg = {}
for a, b, sheet, px in dup_pairs:
    k = (a, b, sheet, px)
    agg[k] = agg.get(k, 0) + 1
by_pair = {}
for (a, b, sheet, px), n in agg.items():
    key = (a, b, sheet)
    e = by_pair.setdefault(key, {'count': 0, 'px': set()})
    e['count'] += n
    e['px'].add(px)
print('duplicate groups  : %d' % len(by_pair))
for (a, b, sheet), e in sorted(by_pair.items()):
    print('   %-28s == %-30s (%s)  %d rect(s)' % (a, b, sheet, len(e['px'])))
print('unreferenced consts: %d' % len(SCALARS))
print('crops written to  : %s' % OUT)
