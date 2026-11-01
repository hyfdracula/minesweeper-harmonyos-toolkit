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
    1: SEG_B | SEG_C,
    2: SEG_A | SEG_B | SEG_G | SEG_E | SEG_D,
    3: SEG_A | SEG_B | SEG_G | SEG_C | SEG_D,
    4: SEG_F | SEG_G | SEG_B | SEG_C,
    5: SEG_A | SEG_F | SEG_G | SEG_C | SEG_D,
    6: SEG_A | SEG_F | SEG_G | SEG_E | SEG_C | SEG_D,
    7: SEG_A | SEG_B | SEG_C,
    8: SEG_A | SEG_B | SEG_C | SEG_D | SEG_E | SEG_F | SEG_G,
    9: SEG_A | SEG_B | SEG_C | SEG_D | SEG_F | SEG_G,
}
# 「1」在 Win7 里带小旗（SEG_FLAG）和衬线底横（SEG_BASE1）
ONE_FLAGGED = SEG_B | SEG_C | SEG_FLAG | SEG_BASE1


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
        # 两行楔形：上行 1 单位（贴竖笔），下行 3 单位（向左展开）
        put(CELL_W - TV - 1, 0, 1, 1)
        put(CELL_W - TV - 3, 1, 3, 1)
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
        show('1  带旗+衬线（原版样式）', ONE_FLAGGED)
        show('1  纯竖笔（不带旗/衬线）', SEG_B | SEG_C)
    if which in ('all', 'ten'):
        show('10  纯竖笔版', MASKS[1] | 0)
        print()
        for label, m1 in (('带旗+衬线', ONE_FLAGGED), ('纯竖笔', SEG_B | SEG_C)):
            print('--- 10（1 = %s）---' % label)
            a = draw(m1)
            b = draw(MASKS[0])
            for r1, r0 in zip(a, b):
                print('   |%s| |%s|' % (r1, r0))
