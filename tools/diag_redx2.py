# -*- coding: utf-8 -*-
"""精确点红叉上的**白叉本体**，并观察关框之后棋盘还有没有反应。

用法：python tools\diag_redx2.py <设备号>
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import click_matrix as cm  # noqa: E402

DEV = sys.argv[1] if len(sys.argv) > 1 else '3KQYD25331202962'
OUT = os.path.join(HERE, '..', 'docs', 'verify', 'diag_redx2.jpeg')

hdc = cm.Hdc(DEV)


def load():
    hdc.screenshot(OUT)
    return np.array(Image.open(OUT).convert('RGB'))


def red_mask(img):
    r = img[:, :, 0].astype(int)
    g = img[:, :, 1].astype(int)
    b = img[:, :, 2].astype(int)
    return (r > 120) & (r - g > 45) & (r - b > 45)


def red_block(img):
    ys, xs = np.nonzero(red_mask(img))
    if len(xs) == 0:
        return None
    # 红块 = 连通的一簇：取 x 最大的一批（标题栏右上角），再放宽到相邻列
    xmax = xs.max()
    sel = xs >= xmax - 100
    x0, x1 = int(xs[sel].min()), int(xs[sel].max())
    y0, y1 = int(ys[sel].min()), int(ys[sel].max())
    return x0, x1, y0, y1


def white_x_in(img, blk):
    """红块里那块白色（白叉）。"""
    x0, x1, y0, y1 = blk
    sub = img[y0:y1 + 1, x0:x1 + 1]
    w = (sub[:, :, 0] > 225) & (sub[:, :, 1] > 225) & (sub[:, :, 2] > 225)
    ys, xs = np.nonzero(w)
    if len(xs) == 0:
        return None
    return x0 + int(xs.mean()), y0 + int(ys.mean()), len(xs)


def tail(tag):
    raw = hdc.hilog()
    lines = [ln.strip() for ln in raw.splitlines() if '[Dialog]' in ln or '[Touch]' in ln]
    print('--- %s ---' % tag)
    for ln in lines[-6:]:
        print('   ', ln[-140:])


img = load()
blk = red_block(img)
if blk is None:
    print('屏幕上没有红块（失败框不在？）')
    sys.exit(1)
x0, x1, y0, y1 = blk
print('红块 x=%d..%d y=%d..%d（宽 %d 高 %d）' % (x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1))

wx = white_x_in(img, blk)
print('白叉像素:', wx)
if wx:
    cx, cy = wx[0], wx[1]
else:
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
print('点白叉 (%d,%d)' % (cx, cy))

hdc.shell('hilog', '-r', timeout=30, check=False)
hdc.click(cx, cy)
time.sleep(2.0)
tail('点白叉之后')

img2 = load()
changed = int((np.abs(img.astype(int) - img2.astype(int)).max(axis=2) > 12).sum())
print('点白叉后画面变化像素 =', changed, '（关框的话是几十万）')

# 关框之后再点棋盘：看看有没有反应
if changed > 50000:
    hdc.shell('hilog', '-r', timeout=30, check=False)
    print('--- 现在点棋盘中央 (920,900) ---')
    hdc.click(920, 900)
    time.sleep(2.0)
    tail('点棋盘之后')
    img3 = load()
    changed2 = int((np.abs(img2.astype(int) - img3.astype(int)).max(axis=2) > 12).sum())
    print('点棋盘后画面变化像素 =', changed2)
    # 再看能不能用菜单重开
    hdc.shell('hilog', '-r', timeout=30, check=False)
    print('--- 点菜单栏「游戏」 ---')
    hdc.click(60, 108)
    time.sleep(1.5)
    tail('点游戏菜单')
