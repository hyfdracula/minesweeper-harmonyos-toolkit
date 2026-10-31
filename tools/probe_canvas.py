# probe_canvas.py —— 从截图 + 应用日志算出「画布顶在屏幕上的偏移」
#
# 为什么需要它：真机（2584x1824, density 2.75）、Mate X7 模拟器（2210x2416, 3.125）、
# Mate 90 Pro 模拟器（1280x2832, 3.5）三种设备的画布顶偏移和密度都不一样，
# 以前 verify.ps1 把 2.75 和 107 写死了，换设备就点不准。
#
# 用法：
#   python probe_canvas.py <截图路径> <棋盘原点x> <棋盘原点y>
#   输出: CANVAS_Y=<数字>
#
# 原理：未开局的棋盘左上角那格是「凸起的蓝砖」，颜色明显偏蓝。
# 从上往下扫 boardX 那一列，第一行「砖色」像素就是棋盘第一行的顶边；
# 棋盘顶边(屏幕) - 棋盘原点(画布) = 画布顶在屏幕上的偏移。

import sys


def is_tile(r, g, b):
    # 砖块蓝：蓝通道明显高于红通道，且不是纯白（那是翻开的格子）
    return b > 110 and (b - r) > 45


def main():
    if len(sys.argv) < 4:
        print('usage: probe_canvas.py <img> <boardX> <boardY>', file=sys.stderr)
        return 2
    path = sys.argv[1]
    bx = int(sys.argv[2])
    by = int(sys.argv[3])

    try:
        from PIL import Image
    except ImportError:
        print('NO_PIL', file=sys.stderr)
        return 3

    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    x = max(0, min(w - 1, bx + 4))
    for y in range(h):
        r, g, b = px[x, y]
        if is_tile(r, g, b):
            print('CANVAS_Y=%d' % (y - by))
            return 0
    print('CANVAS_Y=NOT_FOUND', file=sys.stderr)
    return 4


if __name__ == '__main__':
    sys.exit(main())
