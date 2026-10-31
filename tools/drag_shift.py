#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drag_shift.py —— 量「纵向拖动」到底把棋盘挪了多少、状态条有没有跟着动。

用法：python tools/drag_shift.py --before <图A> --after <图B> \
          --board-top 212 --strip-top 1908 --strip-bottom 2036

判据（全部来自实测像素，不是推断）：
  1. 棋盘区：找出让两张图最匹配的纵向位移 shift（棋盘内容整体**上移** shift px）
  2. 状态条区：条子的底边（最后一条深色边框线）位置在两张图里必须一致，
     差得多就说明状态条跟着棋盘走了；差得少说明它钉在画布底边没动。
"""

import argparse
import os
import sys

from PIL import Image, ImageChops


def diff_count(a, b, y0, y1, x0=0, x1=None):
    if x1 is None:
        x1 = a.size[0]
    box = (max(0, x0), max(0, y0), min(a.size[0], x1), min(a.size[1], y1))
    d = ImageChops.difference(a.crop(box), b.crop(box)).convert('L')
    return sum(d.histogram()[1:])


def best_shift_up(a, b, y0, y1, x0=0, x1=None, max_shift=80):
    """找 shift，使「前图整体上移 shift」后与后图最匹配。

    配对关系：after[y] == before[y + shift]（棋盘上移 → 同一个内容出现在更小的 y）。
    """
    if x1 is None:
        x1 = a.size[0]
    results = []
    for s in range(0, max_shift + 1):
        # 配对：a[y + s] 对 b[y]（棋盘上移 s ⇒ after[y] == before[y + s]）
        d = ImageChops.difference(
            a.crop((x0, y0 + s, x1, y1)),
            b.crop((x0, y0, x1, y1 - s))).convert('L')
        results.append((sum(d.histogram()[1:]), s))
    results.sort()
    return results[0][1], results[:5]


def last_dark_row(img, y0, y1, x=100, thr=330):
    """在列 x 上找 [y0, y1) 里最后一条深色行的 y（状态条底边）。"""
    px = img.load()
    found = None
    for y in range(max(0, y0), min(img.size[1], y1)):
        r, g, b = px[x, y]
        if r + g + b < thr:
            found = y
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--strip-top', type=int, required=True)
    ap.add_argument('--strip-bottom', type=int, required=True)
    ap.add_argument('--board-top', type=int, default=0)
    ap.add_argument('--x0', type=int, default=0)
    ap.add_argument('--x1', type=int, default=None)
    args = ap.parse_args()

    a = Image.open(args.before).convert('RGB')
    b = Image.open(args.after).convert('RGB')
    print('  前图 %dx%d  后图 %dx%d' % (a.size[0], a.size[1], b.size[0], b.size[1]))

    shift, top5 = best_shift_up(a, b, args.board_top, args.strip_top,
                                 args.x0, args.x1)
    print('  棋盘区最佳纵向位移 = 上移 %d px' % shift)
    print('  最接近的 5 个候选（差异像素, 位移）: %s' % top5)

    # 状态条：钉在画布底边 ⇒ 它**最下面那一条**在两张图里必须一模一样。
    # （状态条上沿会被棋盘最后一行盖住，棋盘一动那部分就变，不能拿来判。）
    n_edge = diff_count(a, b, args.strip_bottom - 16, args.strip_bottom, args.x0, args.x1)
    print('  状态条最下 16 px 的差异像素 = %d（应为 0 ⇒ 状态条没动）' % n_edge)
    n_strip = diff_count(a, b, args.strip_top, args.strip_bottom, args.x0, args.x1)
    print('  状态条整条带子的差异像素 = %d（其中大部分是计时器在跳）' % n_strip)

    if n_edge == 0:
        print('  结论：状态条钉在画布底边，没有跟着棋盘走')
    else:
        print('  结论：状态条跟着棋盘动了（有问题）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
