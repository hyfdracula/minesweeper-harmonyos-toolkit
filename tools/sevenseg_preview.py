# -*- coding: utf-8 -*-
"""把 SevenSeg.ets 的七段几何离线画成字符图。

用途（2026-11-02）：真机上「1」被读成「0 的右半边」，一轮轮改常量试太慢，
先在这里把 0-9 和负号全画出来，看哪个字形会误读，再回头改 .ets。

几何必须与 entry/src/main/ets/common/SevenSeg.ets 的常量一致。
"""
import sys

CELL_W = 9
CELL_H = 11
TV = 1
TH = 1
HL = 4

SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = 1, 2, 4, 8, 16, 32, 64
SEG_FLAG = 128
SEG_BASE1 = 256
SEG_ONEBAR = 512

# (x, y, w, h) 相对格子左上角，和 SevenSeg.ets 的 rect() 调用一致
SEGS = {
    'a': (TV, 0, CELL_W - 2 * TV, TH),
    'b': (CELL_W - TV, TH, TV, HL),
    'c': (CELL_W - TV, TH + HL + TH, TV, HL),
    'd': (TV, CELL_H - TH, CELL_W - 2 * TV, TH),
    'e': (0, TH + HL + TH, TV, HL),
    'f': (0, TH, TV, HL),
    'g': (TV, TH + HL, CELL_W - 2 * TV, TH),
}

# 与 SevenSeg.ets 的 MASKS 相同的七段编码
MASKS = {
    0: SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F,
    1: SEG_ONEBAR | SEG_FLAG | SEG_BASE1,
    2: SEG_A | SEG_B | SEG_G | SEG_E | SEG_D,
    3: SEG_A | SEG_B | SEG_G | SEG_C | SEG_D,
    4: SEG_F | SEG_G | SEG_B | SEG_C,
    5: SEG_A | SEG_F | SEG_G | SEG_C | SEG_D,
    6: SEG_A | SEG_F | SEG_G | SEG_E | SEG_C | SEG_D,
    7: SEG_A | SEG_B | SEG_C,
    8: SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F | SEG_G,
    9: SEG_A | SEG_B | SEG_C | SEG_D | SEG_F | SEG_G,
}
# 「1」= 标准七段的 b + c 两根小竖杠（中间有缝），不加任何装饰
ONE_FLAGGED = SEG_B | SEG_C


def draw(mask):
    """返回 CELL_H 行 x CELL_W 列的字符矩阵。"""
    grid = [[' '] * CELL_W for _ in range(CELL_H)]

    def put(x, y, w, h):
        for yy in range(y, min(y + h, CELL_H)):
            for xx in range(x, min(x + w, CELL_W)):
                if 0 <= xx < CELL_W and 0 <= yy < CELL_H:
                    grid[yy][xx] = '#'

    for name, (x, y, w, h) in SEGS.items():
        bit = {'a': SEG_A, 'b': SEG_B, 'c': SEG_C, 'd': SEG_D,
               'e': SEG_E, 'f': SEG_F, 'g': SEG_G}[name]
        if mask & bit:
            put(x, y, w, h)
    if mask & SEG_FLAG:
        # 「1」左上角的小旗：只留 1 个单位的小方点（贴竖笔左上）。
        # 原版的楔形旗在 Win7 面板尺度上只是一根小斜杠，但我们的面板放大 8 倍后
        # 同比例会变成一条 24 像素的横杠，和竖笔、底横一起正好是「0」的右半边。
        put(CELL_W - TV - 1, 0, 1, 1)
    if mask & SEG_BASE1:
        put(CELL_W - TV - 1, CELL_H - TH, 2, TH)
    return [''.join(row) for row in grid]


def draw_variant(mask, flag_mode='wedge'):
    """flag_mode: 'wedge'（原版楔形）/ 'dot'（只留 1 单位的小方点）/ 'none'（没有旗）。"""
    grid = [[' '] * CELL_W for _ in range(CELL_H)]

    def put(x, y, w, h):
        for yy in range(y, min(y + h, CELL_H)):
            for xx in range(x, min(x + w, CELL_W)):
                if 0 <= xx < CELL_W and 0 <= yy < CELL_H:
                    grid[yy][xx] = '#'

    for name, (x, y, w, h) in SEGS.items():
        bit = {'a': SEG_A, 'b': SEG_B, 'c': SEG_C, 'd': SEG_D,
               'e': SEG_E, 'f': SEG_F, 'g': SEG_G}[name]
        if mask & bit:
            put(x, y, w, h)
    if mask & SEG_ONEBAR:
        put(CELL_W - TV, 0, TV, CELL_H)
    if mask & SEG_FLAG:
        if flag_mode == 'wedge':
            put(CELL_W - TV - 1, 0, 1, 1)
            put(CELL_W - TV - 3, 1, 3, 1)
        elif flag_mode == 'dot':
            put(CELL_W - TV - 1, 0, 1, 1)
    if mask & SEG_BASE1:
        put(CELL_W - TV - 1, CELL_H - TH, 2, TH)
    return [''.join(row) for row in grid]


def show(title, mask):
    print('--- %s ---' % title)
    for row in draw(mask):
        print('   |%s|' % row)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if which in ('all', 'digits'):
        for d in range(10):
            show(str(d), MASKS[d])
    if which in ('all', 'one'):
        show('1  整根竖笔+小方点旗+衬线底横（现在用的）', ONE_FLAGGED)
        show('1  旧版：七段 b+c（中间断成两截）', SEG_B | SEG_C)
    if which in ('all', 'ten'):
        print()
        for label, m1 in (('整根竖笔（现在用的）', ONE_FLAGGED), ('旧版 b+c（断开）', SEG_B | SEG_C)):
            print('--- 10（1 = %s）---' % label)
            a = draw(m1)
            b = draw(MASKS[0])
            for r1, r0 in zip(a, b):
                print('   |%s| |%s|' % (r1, r0))
