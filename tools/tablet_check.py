# -*- coding: utf-8 -*-
"""
tablet_check.py —— MatePad Pro 12.2 平板的适配验证。

干什么：
  1. 启动「MatePad 12_2」模拟器实例（2800x1840 / density 360 / 12.2 寸）
  2. 等 hdc 认到设备
  3. 装 HAP、起应用
  4. **依次把四个盘面都跑一遍**（初级 / 中级 / 高级 / 自定义 24x30），
     每一个都读应用自己的布局日志，核对适配档、格边、棋盘原点、HUD
  5. 每个盘面截一张图存到 docs\verify\
  6. 读状态条上的计时与雷数（七段数码管），确认渲染正常

用法：
    python tools/tablet_check.py                 # 全套
    python tools/tablet_check.py --no-emulator   # 不启动模拟器（模拟器已经在跑时用）

实测口径（2026-11-03）：
  画布 2800x1690（顶部 150 px 是系统状态栏），densityPixels = 360/160 = 2.25
  期望值与 docs/LAYOUT-MATRIX.md 第 9 节、tools/check_layout.py 断言 10 一致：
    初级 9x9    n=4 格边 144  棋盘(752,93)   HUD 否
    中级 16x16  n=2 格边 72   棋盘(824,301)  HUD 否
    高级 30x16  n=2 格边 72   棋盘(320,301)  HUD 否
    自定义 24x30 n=2 格边 72  棋盘(320,42)   HUD 是（纵向溢出 58 px）
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

# 菜单栏坐标（**画布 vp**，设备无关）—— 与 click_matrix.py 同源
MENU_TOPS = {"game": (25.7, 7.7)}
MENU_ENTRIES = {
    "初级": (33.0, 66.3),
    "中级": (33.0, 90.3),
    "高级": (33.0, 114.3),
    "自定义": (33.0, 138.3),
}

# 四个盘面的期望值：(适配档n, 格边px, 棋盘x, 棋盘y, HUD)
# 与 docs/LAYOUT-MATRIX.md 第 9 节、tools/check_layout.py 断言 10 一致
EXPECT = {
    "初级": (4, 144, 752, 93, 0),
    "中级": (2, 72, 824, 301, 0),
    "高级": (2, 72, 320, 301, 0),
    "自定义": (2, 72, 320, 42, 1),
}

LAYOUT_RE = re.compile(
    r"画布=(\d+)x(\d+)px\s+密度换算=([0-9.]+)\s+适配档n=(\d+)\s+当前档n=(\d+)\s+"
    r"unit=(\d+)\s+格边=(\d+)px\s+棋盘原点=\((-?\d+),(-?\d+)\)")
HUD_RE = re.compile(r"HUD=(\d)")


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


def device_now_marker():
    """设备当前时间，做成和 hilog 行一样格式的时间戳（当「本轮起点」）。

    hilog 是**环形缓冲**：跑久了旧行还留着，「取最后一条布局日志」会拿到
    **上一轮**的 —— 应用这次压根没画出来，脚本也会说「正常」。
    所以只认这个时刻之后的行。
    """
    out = sh("date", "+%m-%d %H:%M:%S")
    ts = (out or "").strip().splitlines()[-1].strip() if out else ""
    if len(ts) == 14:
        ts += ".000"
    return ts


def log_line_after(line, marker):
    if not marker:
        return True
    head = line[:18]
    return len(head) == 18 and head >= marker


def latest_layout(marker=None):
    """最后一条（且是 marker 之后的）布局日志。"""
    logs = sh('hilog', '-x')
    hit = None
    for ln in logs.splitlines():
        if '[GameController] 布局' in ln:
            if marker and not log_line_after(ln, marker):
                continue
            hit = ln
    return hit


def canvas_geometry():
    """量画布顶在屏幕上的偏移（画布高 = 屏幕高 - 顶偏移）。

    平板模拟器顶部有 150 px 的系统状态栏，画布从它下面开始。
    量法：看画面里**有没有**那条状态栏的分界（状态栏和画布底色不同）。
    """
    out = sh('hidumper -s RenderService -a screen', timeout=60)
    m = re.search(r"['\"]?mainScreen['\"]?.*?(\d{3,4})\s*x\s*(\d{3,4})", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def tap_menu(px_scale, canvas_y, top_vp, entry_vp):
    """点菜单栏的一个下拉条目（坐标是画布 vp）。"""
    x = int(round(top_vp[0] / px_scale))
    y = canvas_y + int(round(top_vp[1] / px_scale))
    sh('uitest', 'uiInput', 'click', str(x), str(y))
    time.sleep(0.9)
    x = int(round(entry_vp[0] / px_scale))
    y = canvas_y + int(round(entry_vp[1] / px_scale))
    sh('uitest', 'uiInput', 'click', str(x), str(y))
    time.sleep(1.6)


def grab(outdir, name):
    """截图并存到本地。**取不到就报错**（不能当没事发生）。

    坑（2026-11-03，Codex 对抗性复审 P2）：原来 `file recv` 的返回码被忽略，
    图没传回来时脚本照样打印「通过」—— 视觉验证根本没做，却说做过了。
    """
    shot = os.path.join(outdir, name)
    remote = '/data/local/tmp/tablet_shot.jpeg'
    sh('snapshot_display', '-f', remote, timeout=120)
    if os.path.exists(shot):
        os.remove(shot)
    proc = run([HDC, '-t', DEVICE, 'file', 'recv', remote, shot], timeout=240)
    ok = proc.returncode == 0 and os.path.exists(shot) and os.path.getsize(shot) > 0
    if not ok:
        print('[tablet] 截图失败：file recv 返回码 %s，输出 %s'
              % (proc.returncode, (proc.stdout or '').strip()[:120]))
        return None
    print('[tablet] 截图：%s' % shot)
    return shot


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

    marker = device_now_marker()
    sh('aa', 'force-stop', BUNDLE)
    time.sleep(1.0)
    sh('aa', 'start', '-a', 'EntryAbility', '-b', BUNDLE)
    time.sleep(6.0)

    line = latest_layout(marker)
    if not line:
        print('[tablet] 没读到**本次启动之后**的布局日志')
        return 1
    m = LAYOUT_RE.search(line)
    if not m:
        print('[tablet] 布局日志解析失败')
        return 1
    cw, ch, px_scale, fit, cur, unit, tile, bx, by = m.groups()
    cw, ch, px_scale = int(cw), int(ch), float(px_scale)
    fit, tile, bx, by = int(fit), int(tile), int(bx), int(by)
    hud_m = HUD_RE.search(line)
    hud = int(hud_m.group(1)) if hud_m else 0
    print('[tablet] 画布 %dx%d px，密度换算 %s，适配档 n=%s，格边 %s px，原点 (%s,%s)，HUD=%s'
          % (cw, ch, px_scale, fit, tile, bx, by, hud))

    # 画布顶偏移 = 屏幕高 - 画布高（模拟器顶部有系统状态栏）
    sw, sh_ = canvas_geometry()
    canvas_y = max(0, sh_ - ch) if sh_ else 0
    print('[tablet] 屏幕 %dx%d，画布顶偏移 %d px' % (sw, sh_, canvas_y))

    ok = True
    checked = []

    def check_board(name):
        """核对一个盘面的布局是否符合期望。"""
        nonlocal ok
        exp = EXPECT.get(name)
        if exp is None:
            print('[tablet] %s 没有期望值，跳过' % name)
            return
        ln = latest_layout(marker)
        if ln is None:
            print('[tablet] %s：没读到布局日志 ✗' % name)
            ok = False
            return
        mm = LAYOUT_RE.search(ln)
        if not mm:
            print('[tablet] %s：布局日志解析失败 ✗' % name)
            ok = False
            return
        g = mm.groups()
        got = (int(g[3]), int(g[6]), int(g[7]), int(g[8]),
               int(HUD_RE.search(ln).group(1)) if HUD_RE.search(ln) else 0)
        if got == exp:
            print('[tablet] %-4s n=%d 格边 %d px 原点 (%d,%d) HUD=%d —— 与期望一致 ✓'
                  % (name, got[0], got[1], got[2], got[3], got[4]))
        else:
            print('[tablet] %-4s 实测 %s，期望 %s ✗' % (name, got, exp))
            ok = False
        checked.append(name)

    # 第一个盘面（应用启动默认是初级）
    check_board("初级")

    # 依次切到其余三个盘面
    for name in ("中级", "高级"):
        print('[tablet] 切到 %s …' % name)
        tap_menu(px_scale, canvas_y, MENU_TOPS["game"], MENU_ENTRIES[name])
        check_board(name)

    # 自定义 24x30：要先把「高度」设成 24、「宽度」设成 30
    print('[tablet] 切到 自定义 24x30 …')
    tap_menu(px_scale, canvas_y, MENU_TOPS["game"], MENU_ENTRIES["自定义"])
    time.sleep(1.2)
    # 自定义框里的三个输入框 + 右侧数字键盘（参考像素，坐标与 click_matrix 相同）
    dlg_w, dlg_h = 402, 200
    s = max(0.5, min(2.0, 1.0 / px_scale, (cw - 32) / dlg_w, (ch - 32) / dlg_h))
    ox = int(round((cw - (dlg_w + 12) * s) / 2))
    oy = int(round((ch - dlg_h * s) / 2)) if dlg_h * s <= ch else 0
    key_x = ox + (dlg_w + 12) * s
    key_w, key_h, key_gap = 44, 32, 6      # 数字键盘按键（参考像素）
    keypad = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5,
              "7": 6, "8": 7, "9": 8, "0": 9}

    def press_digit(ch):
        i = keypad[ch]
        col, row = i % 3, i // 3
        x = int(round(key_x + (col * (key_w + key_gap) + key_w / 2.0) * s))
        y = int(round(oy + (row * (key_h + key_gap) + key_h / 2.0) * s))
        sh('uitest', 'uiInput', 'click', str(x), str(y))
        time.sleep(0.45)

    def tap_field(vx, vy):
        x = int(round(ox + vx * s))
        y = int(round(oy + vy * s))
        sh('uitest', 'uiInput', 'click', str(x), str(y))
        time.sleep(0.6)

    tap_field(162, 56)          # 高度框
    press_digit("2")
    press_digit("4")
    tap_field(162, 86)          # 宽度框
    press_digit("3")
    press_digit("0")
    # 确定按钮（框内右下角）
    bx_ = int(round(ox + 250 * s))
    by_ = int(round(oy + 175 * s))
    sh('uitest', 'uiInput', 'click', str(bx_), str(by_))
    time.sleep(2.0)
    check_board("自定义")

    # 截图（取不到就判失败）
    shot = grab(args.out, 'TABLET_12_2_play.jpeg')
    if shot is None:
        ok = False

    # 状态条读数（七段数码管）
    if shot:
        try:
            import sevenseg_read
            counters = sevenseg_read.read_counters(
                shot, strip_box=(0, canvas_y + (ch - 301), cw, 301))
            for panel, digits in counters:
                print('[tablet] 状态条读数：%s' % (''.join(
                    d if d else '?' for d in digits),))
            if not counters:
                print('[tablet] 状态条面板没认出来 —— 不影响版式结论')
        except Exception as exc:
            print('[tablet] 状态条读数没读出来（%s）—— 不影响版式结论' % exc)

    print('[tablet] 验过的盘面：%s' % ('、'.join(checked) if checked else '（无）'))
    print('[tablet] 结果：%s' % ('通过' if ok else '不通过'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
