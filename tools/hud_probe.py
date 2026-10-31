#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hud_probe.py —— 真机/模拟器上验证「纵向溢出 + 状态条钉画布底边（HUD）」。

做四件事：
  1. 装 HAP、起应用、自标定（画布尺寸 / 密度 / 画布在屏幕上的纵向偏移）
  2. 切到高级（16×30）→ 截图（格边与状态条）
  3. 开自定义（预填高级的 16/30/99）→ 数字键盘敲 24 行 → 确定 → 截图
  4. 纵向拖动 → 截图（棋盘能拖到最后一行，状态条钉在画布底边）

坐标一律用画布 vp，再按实测密度换算成设备像素；画布在屏幕上的纵向偏移
用 tools/probe_canvas.py 从截图量出来。

用法：python tools/hud_probe.py --device 127.0.0.1:5555
"""

import argparse
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, r'C:\Users\19161\.dsh\lib')
from nowindow import run  # noqa: E402

HDC = r'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
HAP = r'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
PKG = 'com.example.saolei'
OUT = r'D:\software\harmony\projects\minesweeper\docs\verify'

# CustomField.ets / NumKeypad.ets 的参考像素常量
DLG_W, DLG_H = 280, 200
KEY_W, KEY_H, KEY_GAP = 34, 30, 4
BTN_OK_X, BTN_Y, BTN_W, BTN_H = 116, 158, 70, 25

# WinMenu.ets 的菜单坐标（vp）
X_GAME, Y_TOP = 36, 10.5
X_DROP_GAME = 40
Y_EXPERT, Y_CUSTOM = 120, 144

D = ''
CANVAS_Y = 0
DENS = 1.0
CANVAS_W = 0
CANVAS_H = 0


def sh(*args):
    return run([HDC, '-t', D] + list(args), capture_output=True, text=True,
               encoding='utf-8', errors='replace')


def shell(cmd):
    return sh('shell', cmd)


def shot(name):
    os.makedirs(OUT, exist_ok=True)
    remote = '/data/local/tmp/%s.jpeg' % name
    shell('snapshot_display -f ' + remote)
    local = os.path.join(OUT, 'hud_%s.jpeg' % name)
    if os.path.exists(local):
        os.remove(local)
    sh('file', 'recv', remote, local)
    print('  截图: %s' % local)
    return local


def S(vp_x, vp_y):
    """画布 vp → 屏幕设备像素"""
    return (int(round(vp_x * DENS)), int(CANVAS_Y + round(vp_y * DENS)))


def tap(vp_x, vp_y, ms=800):
    x, y = S(vp_x, vp_y)
    print('    tap vp(%.1f, %.1f) -> 屏幕 px(%d, %d)' % (vp_x, vp_y, x, y))
    shell('uitest uiInput click %d %d' % (x, y))
    time.sleep(ms / 1000.0)
    return (x, y)


def last_layout():
    out = shell('hilog -x').stdout
    ls = [ln for ln in out.split('\n') if 'GameController] 布局' in ln]
    return ls[-1] if ls else ''


def layout_fields():
    """从最后一条布局日志里抠出 (画布宽, 画布高, 密度换算, 档n, 格边, 原点x, 原点y)"""
    m = re.search(r'画布=(\d+)x(\d+)px 密度换算=([0-9.]+).*适配档n=(\d+).*格边=(\d+)px '
                  r'棋盘原点=\((-?\d+),(-?\d+)\)', last_layout())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), float(m.group(3)), int(m.group(4)),
            int(m.group(5)), int(m.group(6)), int(m.group(7)))


def pick_menu(y_vp, label, check_log=True):
    """打开游戏菜单，点某个条目。

    check_log=True 时用布局日志核对**确实变了**（换难度会重新布局）；
    开「自定义」对话框不会触发布局，所以那一步用 check_log=False，
    靠后面截图核对。
    """
    before = last_layout()
    for attempt in range(3):
        tap(X_GAME, Y_TOP, 700)
        tap(X_DROP_GAME, y_vp, 1500)
        after = last_layout()
        if not check_log:
            print('  %s：已点（用截图核对）' % label)
            return True
        if after and after != before:
            print('  %s 生效：%s' % (label, after.split('布局 ')[-1]))
            return True
        print('  %s：第 %d 次没生效（布局日志没变），再试' % (label, attempt + 1))
        before = after
    return False



def detect_canvas_y(img_path, board_x, tile):
    """量画布顶在屏幕上的纵向偏移（设备像素）。

    不用 tools/probe_canvas.py：那个脚本靠「蓝砖」判定，而应用的外观可以换成
    绿砖等其它配色，判据一换就探不到。这里改成**彩色度**判据：棋盘格子是
    饱和色，菜单栏/背景都是接近灰的低饱和色。
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    px = im.load()
    x = max(0, min(w - 1, board_x + tile // 2))
    run = 0
    for y in range(h):
        r, g, b = px[x, y]
        if max(r, g, b) - min(r, g, b) > 25:
            run += 1
            if run >= 6:
                return y - run + 1
        else:
            run = 0
    return None

def main():
    global D, CANVAS_Y, DENS, CANVAS_W, CANVAS_H
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='127.0.0.1:5555')
    ap.add_argument('--skip-install', action='store_true')
    args = ap.parse_args()
    D = args.device

    print('== 0. 设备 ==')
    print('  targets: ' + run([HDC, 'list', 'targets'], capture_output=True, text=True,
                               encoding='utf-8', errors='replace').stdout.strip().replace('\n', ' '))

    if not args.skip_install:
        print('== 1. 安装 ==')
        r = sh('install', '-r', HAP)
        print('  rc=%s %s' % (r.returncode, (r.stdout or '').strip().split('\n')[-1]))

    print('== 2. 起应用 ==')
    shell('aa force-stop ' + PKG)
    shell('hilog -r')
    shell('aa start -a EntryAbility -b ' + PKG)
    time.sleep(6.0)
    shot('00_launch')

    f = layout_fields()
    if not f:
        print('  !! 没读到布局日志')
        print('  ' + last_layout())
        return 3
    CANVAS_W, CANVAS_H, px_scale = f[0], f[1], f[2]
    DENS = 1.0 / px_scale
    tile, bx, by = f[4], f[5], f[6]
    print('  画布=%dx%d px 密度=%.4f 格边=%d 棋盘原点=(%d,%d)'
          % (CANVAS_W, CANVAS_H, DENS, tile, bx, by))

    CANVAS_Y = 0
    for attempt in range(6):
        probe_img = shot('01_probe')
        top = detect_canvas_y(probe_img, bx, tile)
        if top is not None:
            CANVAS_Y = top - by
            print('  画布顶在屏幕上的纵向偏移 = %d px（棋盘顶边在屏幕 y=%d）'
                  % (CANVAS_Y, top))
            break
        print('  第 %d 次没探到棋盘（可能还在启动画面），重试' % (attempt + 1))
        time.sleep(2.0)
    else:
        print('  !! 一直探不到棋盘顶边，偏移按 0 处理')

    # 预热：起应用后第一下点击有时会被窗口管理器吃掉，先点一下菜单栏再点掉
    tap(X_GAME, Y_TOP, 700)
    tap(X_GAME, Y_TOP, 700)

    # ------------------------------------------------------------ 高级 16×30
    print('== 3. 切到高级（16×30）==')
    pick_menu(Y_EXPERT, '高级')
    print('  布局: %s' % last_layout().split('布局 ')[-1])
    shot('02_expert_16x30')

    # ------------------------------------------------------------ 自定义 24×30
    print('== 4. 开自定义（预填高级 16/30/99），敲 24 行 ==')
    pick_menu(Y_CUSTOM, '自定义', check_log=False)
    shot('03_custom_dialog')

    s = max(0.5, min(2.0, DENS, (CANVAS_W - 32) / float(DLG_W + 12 + 110),
                     (CANVAS_H - 32) / float(max(DLG_H, 132))))
    total_w = (DLG_W + 12 + 110) * s
    total_h = max(DLG_H, 132) * s
    custom_ox = int(round((CANVAS_W - total_w) / 2))
    custom_oy = int(round((CANVAS_H - total_h) / 2))
    ox_vp = round(custom_ox) * px_scale
    oy_vp = round(custom_oy) * px_scale
    s_vp = s * px_scale
    key_x = ox_vp + (DLG_W + 12) * s_vp
    print('  自定义框缩放 s=%.2f 原点=(%d,%d) px' % (s, custom_ox, custom_oy))

    # 注意：这里返回的是**画布 vp**，由 tap() 统一换算成屏幕像素。
    # （早先这里直接返回屏幕像素，被 tap() 又乘了一次密度，点到了屏幕外面。）
    def key_center(col, row):
        x_vp = key_x + col * (KEY_W + KEY_GAP) * s_vp + KEY_W * s_vp / 2
        y_vp = oy_vp + row * (KEY_H + KEY_GAP) * s_vp + KEY_H * s_vp / 2
        return (x_vp, y_vp)

    def ok_button():
        x_vp = ox_vp + BTN_OK_X * s_vp + BTN_W * s_vp / 2
        y_vp = oy_vp + BTN_Y * s_vp + BTN_H * s_vp / 2
        return (x_vp, y_vp)

    time.sleep(1.5)
    tap(*key_center(1, 0), 1500)   # '2'
    tap(*key_center(0, 1), 1500)   # '4'
    shot('04_custom_24')
    time.sleep(1.0)
    tap(*ok_button(), 2500)
    print('  布局: %s' % last_layout().split('布局 ')[-1])
    shot('05_custom_24x30_board')

    # ------------------------------------------------------------ 纵向拖动
    print('== 5. 纵向拖动 ==')
    x = int(CANVAS_W / 2)
    shell('uitest uiInput drag %d %d %d %d' % (x, CANVAS_Y + 500, x, CANVAS_Y + 150))
    time.sleep(1.0)
    shot('06_panned')
    print('  布局: %s' % last_layout().split('布局 ')[-1])
    return 0


if __name__ == '__main__':
    sys.exit(main())
