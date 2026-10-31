# -*- coding: utf-8 -*-
"""measure_custom.py —— 量自定义难度对话框与数字键盘的精确位置。"""
import sys
from PIL import Image

path = sys.argv[1]
im = Image.open(path).convert('RGB')
px = im.load()
w, h = im.size
print("size", w, h)

X0, X1, Y0, Y1 = 400, 880, 1300, 1540


def ch(p):
    r, g, b = p
    if r < 90 and g < 90 and b < 90:
        return '#'          # 深色（文字/边框）
    if abs(r - g) < 12 and abs(g - b) < 12:
        if r > 245:
            return '.'      # 近白
        if r > 225:
            return ':'      # 浅灰
        if r > 195:
            return '-'      # 中灰
        return '='          # 暗灰
    if b - r > 25:
        return 'R'          # 蓝
    if r - b > 40 and r - g > 40:
        return 'r'          # 红
    return '+'


print("== ASCII 图（x %d..%d, y %d..%d，每 4px 一格）==" % (X0, X1, Y0, Y1))
hdr = '     ' + ''.join(str((x // 10) % 10) for x in range(X0, X1, 4))
print(hdr)
print('     ' + ''.join(str((x // 1) % 10) for x in range(X0, X1, 4)))
for y in range(Y0, Y1, 4):
    print('%4d ' % y + ''.join(ch(px[x, y]) for x in range(X0, X1, 4)))


def bounds(x0, y0, x1, y1, pred):
    xs = []
    ys = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pred(px[x, y]):
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


print()
print("== 红色 X（标题栏关闭）==")
b = bounds(600, 1300, 760, 1360, lambda p: p[0] - p[1] > 60 and p[0] - p[2] > 60)
print("   红色块:", b)
print("== 键盘区域深色文字块 ==")
for y in range(1310, 1470):
    xs = [x for x in range(700, 880) if px[x, y][0] < 100 and px[x, y][1] < 100 and px[x, y][2] < 100]
    if xs:
        print("   y=%4d 深色 x=%d..%d n=%d" % (y, xs[0], xs[-1], len(xs)))
