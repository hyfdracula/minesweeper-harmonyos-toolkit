# -*- coding: utf-8 -*-
"""
tablet_check.py —— MatePad Pro 12.2 平板的适配验证。

干什么：
  1. 启动「MatePad 12_2」模拟器实例（2800x1840 / density 360 / 12.2 寸）
  2. 等 hdc 认到设备
  3. 装 HAP、起应用
  4. 读应用自己的布局日志，核对这个设备上的适配档/格边/棋盘原点
  5. 截一张图存到 docs\verify\
  6. 读状态条上的计时与雷数（七段数码管），确认渲染正常

用法：
    python tools/tablet_check.py                 # 全套
    python tools/tablet_check.py --no-emulator   # 不启动模拟器（模拟器已经在跑时用）

实测口径（2026-11-03）：
  画布 2800x1840，densityPixels = 360/160 = 2.25
  预期：初级 9x9 适配档 n=4、格边 144 px；高级 16x30 与自定义 24x30 是 n=2、格边 72 px
  （数值以 docs/LAYOUT-MATRIX.md 第 9 节和 tools/check_layout.py 断言 10 为准）
"""
import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

EMU = r'D:\software\DevEco Studio\tools\emulator\Emulator.exe'
HDC = r'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
INSTANCE = 'MatePad 12_2'
DEVICE = '127.0.0.1:5555'
BUNDLE = 'com.example.saolei'
HAP = r'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def sh(*args, timeout=120):
    return run([HDC, '-t', DEVICE, 'shell', *args], timeout=timeout).stdout


def wait_device(deadline_s=300):
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        out = run([HDC, 'list', 'targets'], timeout=60).stdout
        if DEVICE in out:
            return True
        time.sleep(3)
    return False


def main():
    ap = argparse.ArgumentParser(description='MatePad Pro 12.2 适配验证')
    ap.add_argument('--no-emulator', action='store_true',
                    help='模拟器已经在跑时用这个（不重复启动）')
    ap.add_argument('--out', default=os.path.join(REPO, 'docs', 'verify'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    if not args.no_emulator:
        print('[tablet] 启动模拟器实例 %s …' % INSTANCE)
        # **不要等它退出**：`Emulator.exe -start` 是个常驻的 GUI 进程，
        # 不会自己返回（早先这里用 subprocess.run 等它，600 秒后超时，
        # 还把模拟器一起杀了）。改成分离启动，然后靠「等 hdc 认到设备」来判断。
        # CREATE_NO_WINDOW：别让控制台黑框弹出来（模拟器自己的 GUI 窗口照常显示）。
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        subprocess.Popen([EMU, '-start', INSTANCE,
                          '-instancePath', 'C:/Users/19161/AppData/Local/Huawei/Emulator/deployed',
                          '-imageRoot', r'C:\Users\19161\AppData\Local\Huawei\Sdk'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags)

    print('[tablet] 等 hdc 认到设备 %s …' % DEVICE)
    if not wait_device():
        print('[tablet] 设备没上线，退出')
        return 1

    print('[tablet] 装 HAP …')
    out = run([HDC, '-t', DEVICE, 'install', '-r', HAP], timeout=600).stdout
    print(out.strip()[-200:])
    if 'successfully' not in out:
        print('[tablet] 安装失败')
        return 1

    sh('aa', 'force-stop', BUNDLE)
    time.sleep(1.0)
    sh('aa', 'start', '-a', 'EntryAbility', '-b', BUNDLE)
    time.sleep(6.0)

    logs = sh('hilog', '-x')
    layout_lines = [ln for ln in logs.splitlines() if '[GameController] 布局' in ln]
    if not layout_lines:
        print('[tablet] 没读到布局日志')
        return 1
    line = layout_lines[-1]
    print('[tablet] 布局日志：')
    print('   ' + line[line.find('[GameController]'):].strip())

    m = re.search(r'画布=(\d+)x(\d+)px 密度换算=([\d.]+) 适配档n=(\d+) '
                  r'当前档n=(\d+) unit=(\d+) 格边=(\d+)px '
                  r'棋盘原点=\((-?\d+),(-?\d+)\) HUD=(\d)', line)
    ok = True
    if not m:
        print('[tablet] 布局日志解析失败')
        return 1
    cw, ch, px_scale, fit, cur, unit, tile, bx, by, hud = m.groups()
    print('[tablet] 画布 %sx%s px，密度换算 %s，适配档 n=%s，格边 %s px，原点 (%s,%s)，HUD=%s'
          % (cw, ch, px_scale, fit, tile, bx, by, hud))

    # 期望值（与 docs/LAYOUT-MATRIX.md 第 9 节、tools/check_layout.py 断言 10 一致）
    exp = {'初级': (4, 144), '高级': (2, 72), '自定义': (2, 72)}
    board = re.search(r'盘面=(\d+)x(\d+)', line)
    key = None
    if board:
        rows, cols = int(board.group(1)), int(board.group(2))
        key = {(9, 9): '初级', (16, 16): '中级', (16, 30): '高级', (24, 30): '自定义'}.get((rows, cols))
    if key and key in exp:
        e_fit, e_tile = exp[key]
        if int(fit) != e_fit or int(tile) != e_tile:
            print('[tablet] 不符合预期：%s 应为 n=%s 格边 %s，实际 n=%s 格边 %s'
                  % (key, e_fit, e_tile, fit, tile))
            ok = False
        else:
            print('[tablet] %s 的适配档 n=%s、格边 %s px 与预期一致 ✓' % (key, fit, tile))
    else:
        print('[tablet] 盘面 %s 不在预期表里（不判）' % (key or board.group(0)))

    # 截图
    shot = os.path.join(args.out, 'TABLET_12_2_play.jpeg')
    remote = '/data/local/tmp/tablet_shot.jpeg'
    sh('snapshot_display', '-f', remote, timeout=90)
    if os.path.exists(shot):
        os.remove(shot)
    run([HDC, '-t', DEVICE, 'file', 'recv', remote, shot], timeout=180)
    print('[tablet] 截图：%s' % shot)
    im_h = 0
    try:
        from PIL import Image
        im_h = Image.open(shot).size[1]
    except Exception:
        im_h = int(ch)

    # 状态条读数（七段数码管）
    #
    # 坑：不能直接 `read_counters(path)` 全图搜索 ——
    # 棋盘上的蓝砖和计数器面板会被并成同一段列区间，面板就找不到了。
    # 必须**限定在状态条那一条横带里**找（跟跑测器 click_matrix 的做法一致）。
    try:
        import sevenseg_read
        counters = []
        m2 = re.search(r'状态条上沿=(\d+)px', line)
        if m2:
            # 状态条上沿是**画布内**的坐标；截图是**屏幕**坐标。
            # 差着一段画布顶偏移（模拟器顶部有系统状态栏），
            # 少算了这一段，面板就会落在搜索带外面，一个都找不到。
            canvas_top = int(im_h) - int(ch)      # 画布顶在屏幕上的位置
            strip_top = canvas_top + int(m2.group(1))
            strip_box = (0, strip_top, int(cw), max(1, int(im_h) - strip_top))
            counters = sevenseg_read.read_counters(shot, strip_box=strip_box)
        for panel, digits in counters:
            print('[tablet] 状态条读数：%s' % (''.join(
                d if d else '?' for d in digits),))
        if not counters:
            print('[tablet] 状态条面板没认出来 —— 不影响版式结论')
    except Exception as exc:
        print('[tablet] 状态条读数没读出来（%s）—— 不影响版式结论' % exc)

    print('[tablet] 结果：%s' % ('通过' if ok else '不通过'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
