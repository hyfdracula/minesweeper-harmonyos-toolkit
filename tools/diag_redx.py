# -*- coding: utf-8 -*-
"""复现「结算弹窗点红色关闭键没反应」。

在已经有失败框的屏幕上：
  1. 截屏，**量出红块（标题栏右上角那个红叉）的真实像素位置**；
  2. 点它，读应用日志看有没有 `[Dialog] 点击按钮 close`；
  3. 再点棋盘别处，看棋盘还动不动（用户说「点完按钮以后再点别处也卡住」）。

用法：python tools\diag_redx.py <设备号>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import click_matrix as cm  # noqa: E402

DEV = sys.argv[1] if len(sys.argv) > 1 else '3KQYD25331202962'
OUT = os.path.join(HERE, '..', 'docs', 'verify', 'diag_redx.jpeg')

hdc = cm.Hdc(DEV)


def red_pixels(img):
    """标题栏上的红块：偏红、且不是纯白。"""
    r = img[:, :, 0].astype(int)
    g = img[:, :, 1].astype(int)
    b = img[:, :, 2].astype(int)
    return (r > 120) & (r - g > 45) & (r - b > 45)


def find_red_block(img):
    ys, xs = np.nonzero(red_pixels(img))
    if len(xs) == 0:
        return None
    # 取最靠右的一簇（标题栏右上角的红叉），排除图标里的雷
    x0 = xs.min()
    # 按 x 分箱，取最右的一箱
    bins = {}
    for x in xs:
        bins[x // 20] = bins.get(x // 20, 0) + 1
    right = max(bins)
    sel = (xs // 20) == right
    return int(xs[sel].min()), int(xs[sel].max()), int(ys[sel].min()), int(ys[sel].max())


def log_tail(marker_len=0):
    raw = hdc.hilog()
    return [ln for ln in raw.splitlines() if '[Dialog]' in ln or '[Touch]' in ln or '[GameController]' in ln]


hdc.screenshot(OUT)
img = np.array(Image.open(OUT).convert('RGB'))
print('截图', img.shape[1], 'x', img.shape[0])

blk = find_red_block(img)
if blk is None:
    print('没找到红块（屏幕上可能没有失败框）')
    sys.exit(1)
x0, x1, y0, y1 = blk
print('红块像素范围 x=%d..%d y=%d..%d（宽 %d 高 %d）' % (x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1))

# 清一下日志，只看这次点击之后发生了什么
hdc.shell('hilog', '-r', timeout=30, check=False)

cx = (x0 + x1) // 2
cy = (y0 + y1) // 2
print('点红块中心 (%d,%d)' % (cx, cy))
hdc.click(cx, cy)
import time
time.sleep(2.0)
print('=== 点击后的日志 ===')
for ln in log_tail():
    print('   ', ln.strip()[:160])

# 再点棋盘别处，看还动不动
hdc.screenshot(OUT)
img2 = np.array(Image.open(OUT).convert('RGB'))
changed = int((np.abs(img.astype(int) - img2.astype(int)).max(axis=2) > 12).sum())
print('点完红块后画面变化像素 =', changed)
