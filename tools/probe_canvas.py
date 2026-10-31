# probe_canvas.py —— 从截图 + 应用日志算出「画布顶在屏幕上的纵向偏移」
#
# 为什么需要它：真机（2584x1824, density 2.75）、Mate X7 模拟器（2210x2416, 3.125）、
# Mate 90 Pro 模拟器（1280x2832, 3.5）三种设备的画布顶偏移和密度都不一样，
# 以前 verify.ps1 把 2.75 和 107 写死了，换设备就点不准。
#
# 用法：
#   python probe_canvas.py <截图路径> <棋盘原点x> <棋盘原点y> <格边px>
#   输出: CANVAS_Y=<数字>
#
# 原理：未开局的棋盘是「凸起的蓝砖」。从 x=棋盘原点+格边/2 那一列往下扫，
# 第一段连续够长的「砖色」像素就是棋盘第一行的顶边；
# 棋盘顶边(屏幕) - 棋盘原点(画布) = 画布顶在屏幕上的偏移。
#
# 坑（2026-10-31）：采样点原来取 boardX+4，正好落在砖块左缘那道暗边上
# （RGB 31,56,97，b=97 不过阈值），于是扫到的是砖块中间才命中的位置，
# 偏移算成 225（实际 121），后面的点击全偏。必须取**格边中心**。

import sys


def is_tile(r, g, b):
    # 砖块蓝：蓝通道明显高于红通道
    return b > 110 and (b - r) > 45


def main():
    if len(sys.argv) < 5:
        print('usage: probe_canvas.py <img> <boardX> <boardY> <tile>', file=sys.stderr)
        return 2
    path = sys.argv[1]
    bx = int(sys.argv[2])
    by = int(sys.argv[3])
    tile = int(sys.argv[4])

    try:
        from PIL import Image
    except ImportError:
        print('NO_PIL', file=sys.stderr)
        return 3

    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    x = max(0, min(w - 1, bx + tile // 2))
    need = max(8, min(40, tile // 4))   # 连续命中的行数下限
    run = 0
    for y in range(h):
        r, g, b = px[x, y]
        if is_tile(r, g, b):
            run += 1
            if run >= need:
                top = y - run + 1
                print('CANVAS_Y=%d' % (top - by))
                return 0
        else:
            run = 0
    print('CANVAS_Y=NOT_FOUND', file=sys.stderr)
    return 4


if __name__ == '__main__':
    sys.exit(main())
