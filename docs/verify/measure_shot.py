# -*- coding: utf-8 -*-
"""
measure_shot.py —— 量截图里的界面元素边界（棋盘、状态条、对话框、菜单）。

用法:
    python measure_shot.py <截图路径> [选项]

选项:
    --board        量棋盘（蓝色格子块）外框 + 状态条
    --dialog       量非背景矩形（对话框）外框
    --menu         菜单栏文字行
所有坐标都是**原始像素**。
"""
import sys
from PIL import Image


def load(path):
    im = Image.open(path).convert("RGB")
    return im


def is_board(p):
    # 蓝格子：蓝通道明显高于红通道，且不太暗
    r, g, b = p
    return b - r > 40 and b > 110 and r < 140


def is_bg(p):
    # 客户区浅蓝灰背景
    r, g, b = p
    return abs(r - g) < 12 and abs(g - b) < 18 and 195 < r < 245


def report_board(im):
    w, h = im.size
    px = im.load()
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(0, h):
        for x in range(0, w):
            if is_board(px[x, y]):
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    print("棋盘(含状态条方块)外框 x=%d..%d y=%d..%d" % (minx, maxx, miny, maxy))
    # 逐行统计蓝色像素数，找出棋盘区与状态条区的分界
    rows = []
    for y in range(0, h):
        n = 0
        for x in range(0, w):
            if is_board(px[x, y]):
                n += 1
        rows.append(n)
    prev = 0
    for y in range(h):
        if (rows[y] > 0) != (prev > 0):
            print("   行变化 y=%d  bluecount %d -> %d" % (y, prev, rows[y]))
        prev = rows[y]
    # 画布高度 = 菜单栏(60px) + 剩余；画布顶在屏幕 y=138
    canvas_top = 138
    canvas_h = 2598
    print("   棋盘顶(屏幕) = %d" % (miny if miny < canvas_top + 200 else miny))
    print("   棋盘/状态条底(屏幕) = %d" % maxy)
    print("   画布 y=%d..%d，状态条底距画布底 = %d px" %
          (canvas_top, canvas_top + canvas_h, canvas_top + canvas_h - maxy))


def report_dialog(im, bg_tol=12):
    """找与客户区背景明显不同的矩形区域（对话框）"""
    w, h = im.size
    px = im.load()
    # 以画布左上附近的背景色为基准
    base = px[20, 400]
    print("背景基准色 =", base)
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(150, h):
        for x in range(0, w):
            p = px[x, y]
            d = abs(p[0] - base[0]) + abs(p[1] - base[1]) + abs(p[2] - base[2])
            if d > 60:
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
                if y < miny:
                    miny = y
                if y > maxy:
                    maxy = y
    print("非背景区域外框 x=%d..%d y=%d..%d" % (minx, maxx, miny, maxy))
    print("   距屏幕左边 %d px，距屏幕右边 %d px，距屏幕顶 %d px，距屏幕底 %d px" %
          (minx, w - 1 - maxx, miny, h - 1 - maxy))


def report_rows(im, y0, y1, x0=0, x1=None, label=""):
    """打印指定行范围内的深色像素段（文字行）"""
    w, h = im.size
    px = im.load()
    if x1 is None:
        x1 = w - 1
    print("== %s ==" % label)
    for y in range(y0, min(y1, h - 1) + 1):
        segs = []
        run = None
        for x in range(x0, x1 + 1):
            r, g, b = px[x, y]
            if r < 140 and g < 140:
                if run is None:
                    run = [x, x]
                else:
                    run[1] = x
            else:
                if run is not None:
                    segs.append(tuple(run))
                    run = None
        if run is not None:
            segs.append(tuple(run))
        segs = [s for s in segs if s[1] - s[0] >= 2]
        if segs:
            print("   y=%4d  %s" % (y, segs))


if __name__ == "__main__":
    path = sys.argv[1]
    im = load(path)
    print("图片 %s  %dx%d" % (path, im.size[0], im.size[1]))
    for opt in sys.argv[2:]:
        if opt == "--board":
            report_board(im)
        elif opt == "--dialog":
            report_dialog(im)
