# -*- coding: utf-8 -*-
r"""从截图里读出状态条两个七段计数器（计时 / 剩余雷）的数字。

为什么要自己写：状态条上的数字不是字体，是**程序画的七段数码管**
（见 entry/src/main/ets/common/SevenSeg.ets），没有 OCR 可用，
所以这里按同一套几何反解。

几何（参考像素，与 SevenSeg.ets 一一对应）：
    面板 40×21（**外框**）；面板精灵四周有 1 个逻辑像素的边框，
    所以截图里量到的**绿色区域是面板内区 38×19** —— 换算比例必须按 38 算，
    槽位原点还要往外挪 1 个参考像素，否则采样点整体偏移（Codex 复审 P2）。
    槽位 x = 0 / 13 / 26；每槽 12 宽 × 16 高，槽内 y = 2
    a: (3, 2, 6, 2)   b: (9, 4, 3, 5)   c: (9, 11, 3, 5)
    d: (3, 16, 6, 2)  e: (0, 11, 3, 5)  f: (0, 4, 3, 5)
    g: (3, 9, 6, 2)

做法：先**只在状态条那一条横带里**找绿色面板（不限定的话，棋盘上的绿砖
也会被算进来，量出来的框全是错的 —— Codex 复审 P2），
再在面板里按几何采样每段的中心点是否发白 → 还原数字
（槽位从右往左读，右对齐不补零）。

用法：python tools\sevenseg_read.py <截图路径> [状态条矩形 x,y,w,h]
      → 打印每个面板读出来的数字
"""
import sys

import numpy as np

# 段位掩码（位序 a,b,c,d,e,f,g）与 SevenSeg.ets 的 DIGIT_MASKS 一致
SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = 1, 2, 4, 8, 16, 32, 64
SEG_FLAG, SEG_BASE1 = 128, 256

MASKS = [
    0x3F, 0x186, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
]

# 负号段：单独一根中横（g），掩码 0x40。
# 剩余雷数可以是负的（插的旗比雷还多，SPEC §3.3），原版负号占**紧挨数字左边**的那一槽。
# 0x40 不是任何数字的合法掩码，所以不会和数字混淆（Codex 复审 P2）。
MASK_MINUS = 0x40

# 「1」的标准写法：只亮 b、c 两段（0x06）。
# 原版那个「1」还带一面小旗和一道衬线（掩码 0x186），但旗和衬线**不是标准七段**，
# 反解时只采样标准七段就只会得到 0x06（b+c）；若把衬线底横画在 d 段的位置上，
# 采样到的是 0x0E（b+c+d）。两个都要认成「1」（Codex 复审 P2）。
MASK_ONE_STD = 0x06
MASK_ONE_BASE = 0x0E

# (段名, x, y, w, h) —— 参考像素，相对槽位左上角
SEGS = [
    ('a', 3, 2, 6, 2), ('b', 9, 4, 3, 5), ('c', 9, 11, 3, 5),
    ('d', 3, 16, 6, 2), ('e', 0, 11, 3, 5), ('f', 0, 4, 3, 5),
    ('g', 3, 9, 6, 2),
]
BIT = {'a': SEG_A, 'b': SEG_B, 'c': SEG_C, 'd': SEG_D,
       'e': SEG_E, 'f': SEG_F, 'g': SEG_G}

# 面板（外框）参考像素
PANEL_W, PANEL_H = 40, 21
PANEL_BORDER = 2              # 面板精灵四周的边框厚度（逻辑像素）
INNER_W = PANEL_W - 2 * PANEL_BORDER   # 36：截图里量到的绿色内区宽度
INNER_H = PANEL_H - 2 * PANEL_BORDER   # 17
SLOT_COUNT = 3
SLOT_X0 = 0
SLOT_PITCH = 13
CELL_W, CELL_H = 12, 16
CELL_Y = 2


def _green_mask(im):
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    return (g > 90) & (g > r + 25) & (g > b + 25)


def _white_mask(im):
    return im.min(axis=2) > 185


def find_panels(im, strip_box=None):
    """在图里找绿色计数器面板，返回 [(x0, y0, w, h), ...]（按 x 排序）。

    `strip_box` = (x, y, w, h)：**只在状态条那一条横带里找**。
    不限定的话，棋盘上的绿砖会被并进同一段列区间，量出来的框全是错的。
    """
    green = _green_mask(im)
    if strip_box is not None:
        sx, sy, sw, sh = [int(v) for v in strip_box]
        region = np.zeros_like(green)
        y1 = min(im.shape[0], sy + sh)
        x1 = min(im.shape[1], sx + sw)
        region[max(0, sy):y1, max(0, sx):x1] = green[max(0, sy):y1, max(0, sx):x1]
        green = region
    cols = np.where(green.any(axis=0))[0]
    if len(cols) == 0:
        return []
    runs = []
    start = prev = int(cols[0])
    for c in cols[1:]:
        c = int(c)
        if c > prev + 3:
            runs.append((start, prev))
            start = c
        prev = c
    runs.append((start, prev))
    panels = []
    for x0, x1 in runs:
        if x1 - x0 < 30:          # 太窄的不是面板（棋盘上的绿砖等）
            continue
        ys = np.where(green[:, x0:x1 + 1].any(axis=1))[0]
        if len(ys) == 0:
            continue
        panels.append((int(x0), int(ys.min()), int(x1 - x0 + 1),
                       int(ys.max() - ys.min() + 1)))
    panels.sort()
    return panels


def _sample_slots(im, outer_x, outer_y, s):
    """按几何采样三个槽位的七段掩码。"""
    white = _white_mask(im)
    digits = []
    for i in range(SLOT_COUNT):
        sx = outer_x + (SLOT_X0 + i * SLOT_PITCH) * s
        sy = outer_y + CELL_Y * s
        mask = 0
        for name, rx, ry, rw, rh in SEGS:
            cx = int(round(sx + (rx + rw / 2.0) * s))
            cy = int(round(sy + (ry + rh / 2.0) * s))
            if 0 <= cy < im.shape[0] and 0 <= cx < im.shape[1] and white[cy, cx]:
                mask |= BIT[name]
        digits.append(mask)
    return digits


def read_panel(im, panel):
    """读一个面板里的数字（三个槽的掩码列表；空槽为 0）。

    `panel` = (x0, y0, w, h)：绿色**内区**的矩形（见 find_panels）。

    纵向原点有 ±1 个参考像素的不确定（面板精灵的边框上、下不一样厚，
    而数字是按**外框**原点画的），所以这里沿纵向试几个偏移，
    取「三个槽都能解成合法数字」的那一个；实在分不出来就取合法槽最多的。
    """
    x0, y0, pw, ph = panel
    if pw < 30 or ph < 10:
        return None
    # 内区 36 参考像素宽 → 比例；面板外框比内区每边多 2 个参考像素
    s = pw / float(INNER_W)
    outer_x = x0 - PANEL_BORDER * s
    base_y = y0 - PANEL_BORDER * s
    best = None
    best_score = -1
    for dy in (-2, -1, 0, 1, 2):
        digits = _sample_slots(im, outer_x, base_y + dy * s, s)
        score = 0
        for m in digits:
            if m == 0:
                score += 1                      # 空槽（右对齐、不补零）也算合法
            elif m == MASK_ONE_STD or m == MASK_ONE_BASE:
                score += 2
            elif m in MASKS:
                score += 2
        if score > best_score:
            best_score = score
            best = digits
    return best


def decode(digits):
    """把三个槽位的掩码还原成数字串；读不出的槽位跳过（不补零，右对齐）。"""
    text = []
    for m in digits:
        if m == 0:
            text.append(None)
            continue
        if m == MASK_MINUS:
            text.append('-')          # 负号段（只剩中横）
        elif m == MASK_ONE_STD or m == MASK_ONE_BASE:
            text.append('1')          # 标准七段的「1」：只亮 b、c（带衬线底横时多一段 d）
        elif m in MASKS:
            text.append(str(MASKS.index(m)))
        else:
            text.append('?')
    return text


def read_counters(path, strip_box=None):
    im = np.array(_load(path)).astype(int)
    panels = find_panels(im, strip_box)
    out = []
    for p in panels:
        d = read_panel(im, p)
        if d is not None:
            out.append((p, decode(d)))
    return out


def _load(path):
    from PIL import Image
    return Image.open(path).convert('RGB')


if __name__ == '__main__':
    args = sys.argv[1:]
    path = args[0] if args else None
    if path is None:
        print('用法: python tools\\sevenseg_read.py <截图路径> [状态条矩形 x,y,w,h]')
        sys.exit(2)
    box = None
    if len(args) >= 5:
        box = tuple(int(v) for v in args[1:5])
    for i, (p, txt) in enumerate(read_counters(path, box)):
        print('面板 %d %s: %s' % (i, p, ' '.join(str(t) for t in txt)))
