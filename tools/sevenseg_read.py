# -*- coding: utf-8 -*-
r"""从截图里读出状态条两个七段计数器（计时 / 剩余雷）的数字。

为什么要自己写：状态条上的数字不是字体，是**程序画的七段数码管**
（见 entry/src/main/ets/common/SevenSeg.ets），没有 OCR 可用，
所以这里按同一套几何反解。

几何（参考像素，槽位/格子/段位与 SevenSeg.ets 一一对应）：
    面板 40×21；槽位 x = 0 / 13 / 26；每槽 12 宽 × 16 高，槽内 y = 2
    a: (3, 2, 6, 2)   b: (9, 4, 3, 5)   c: (9, 11, 3, 5)
    d: (3, 16, 6, 2)  e: (0, 11, 3, 5)  f: (0, 4, 3, 5)
    g: (3, 9, 6, 2)

做法：先在状态条那一条横带上**找出绿色面板**，再在面板里找出三个槽位，
最后按每段的中心点是否发白来判段 → 还原数字（槽位从右往左读，右对齐不补零）。

用法：python tools\sevenseg_read.py <截图路径>
      → 打印 {"panels": [[10, 0], []], ...]}，读不出来会说原因
"""
import sys

import numpy as np

# 段位掩码（位序 a,b,c,d,e,f,g）与 SevenSeg.ets 的 DIGIT_MASKS 一致
SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = 1, 2, 4, 8, 16, 32, 64
SEG_FLAG, SEG_BASE1 = 128, 256

MASKS = [
    0x3F, 0x186, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
]

# (段名, x, y, w, h) —— 参考像素，相对槽位左上角
SEGS = [
    ('a', 3, 2, 6, 2), ('b', 9, 4, 3, 5), ('c', 9, 11, 3, 5),
    ('d', 3, 16, 6, 2), ('e', 0, 11, 3, 5), ('f', 0, 4, 3, 5),
    ('g', 3, 9, 6, 2),
]
BIT = {'a': SEG_A, 'b': SEG_B, 'c': SEG_C, 'd': SEG_D,
       'e': SEG_E, 'f': SEG_F, 'g': SEG_G}
EXTRA = {0x186: ('flag', 'base1')}


def _green_mask(im):
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    return (g > 90) & (g > r + 25) & (g > b + 25)


def _white_mask(im):
    return im.min(axis=2) > 185


def find_panels(im):
    """在图里找绿色计数器面板，返回 [(x0, x1, y0, y1), ...]（按 x 排序）。"""
    green = _green_mask(im)
    cols = np.where(green.any(axis=0))[0]
    if len(cols) == 0:
        return []
    runs = []
    start = prev = cols[0]
    for c in cols[1:]:
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
        panels.append((int(x0), int(x1), int(ys.min()), int(ys.max())))
    return panels


def read_panel(im, panel):
    """读一个面板里的数字（右对齐，最多三位；带负号时第一位是负号）。"""
    x0, x1, y0, y1 = panel
    pw = x1 - x0 + 1
    ph = y1 - y0 + 1
    if pw < 30 or ph < 10:
        return None
    # 参考像素 → 设备像素的比例：面板 40×21 参考像素
    s = pw / 40.0
    white = _white_mask(im)
    # 槽位：x = 0 / 13 / 26（相对面板左边），槽宽 12
    slots = []
    for i in range(3):
        sx = x0 + (0 if s < 1 else 0) + i * 13 * s
        slots.append(sx)
    # 面板内可能有 1~2 像素的斜角高光，槽位要按右边对齐：三个槽占 0..37
    digits = []
    for sx in slots:
        mask = 0
        for name, rx, ry, rw, rh in SEGS:
            cx = int(round(sx + (rx + rw / 2.0) * s))
            cy = int(round(y0 + (ry + rh / 2.0) * s))
            if 0 <= cy < im.shape[0] and 0 <= cx < im.shape[1] and white[cy, cx]:
                mask |= BIT[name]
        digits.append(mask)
    return digits


def decode(digits):
    """把三个槽位的掩码还原成数值；读不出的槽位跳过（不补零，右对齐）。"""
    text = []
    for m in digits:
        if m == 0:
            text.append(None)
            continue
        if m in MASKS:
            text.append(str(MASKS.index(m)))
        elif m in EXTRA:
            text.append('1')          # 「1」带旗与衬线
        else:
            text.append('?')
    return text


def read_counters(path, strip_box=None):
    im = np.array(_load(path)).astype(int)
    panels = find_panels(im)
    out = []
    for p in panels:
        d = read_panel(im, p)
        if d is not None:
            out.append(decode(d))
    return out


def _load(path):
    from PIL import Image
    return Image.open(path).convert('RGB')


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path is None:
        print('用法: python tools\\sevenseg_read.py <截图路径>')
        sys.exit(2)
    for i, txt in enumerate(read_counters(path)):
        print('面板 %d: %s' % (i, ' '.join(str(t) for t in txt)))
