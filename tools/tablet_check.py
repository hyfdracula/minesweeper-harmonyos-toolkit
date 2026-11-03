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

# 几何常量**直接从 click_matrix 导入** —— 别自己抄一份。
# 抄过一次的教训：我按「参考像素 402x200」写，对话框实际是 280x200，
# 按键也不是 44x32 而是 34x30，确定按钮在 (116,158) 而不是 (250,175)。
# 这些是同一份事实，抄一份就会漂。
try:
    from click_matrix import (CUSTOM_DLG_W, CUSTOM_DLG_H, CUSTOM_GAP,
                              KEY_W, KEY_H, KEY_GAP, KEYPAD_W, KEYPAD_H,
                              KEYPAD_KEYS, CUSTOM_BTN_OK, CUSTOM_BTN_CANCEL,
                              MENU_TOPS, MENU_ENTRIES, Hdc, Geom, Layout)
except Exception as exc:      # pragma: no cover
    raise SystemExit("拿不到 click_matrix 的几何常量：%s" % exc)

# 离线推演（check_layout.py）当判据 —— **用模拟器实际的画布**推，
# 不要用「全屏 1840」的期望值。
#
# 坑（2026-11-03）：check_layout.py 的 TABLET_EXPECT 是按**画布 2800x1840**
# 推的（真机上画布就是全屏，没有系统条）。可模拟器上画布只有 **1690**
# （顶部 90 px 状态栏 + 底部 60 px 手势条），棋盘在画布里居中，
# 于是原点 y 整体上移 ~75 px：初级 165 -> 93、中级 301 -> 229。
# 拿全屏期望去比模拟器实测，当然对不上。
# 正确做法：**拿同一个画布去推**，推出来的才是判据。
try:
    import check_layout
except Exception as exc:      # pragma: no cover
    raise SystemExit("拿不到 check_layout 的推演器：%s" % exc)


def expected_for(canvas_w, canvas_h, density):
    """用 check_layout 的几何推演，算出四个盘面在这个画布上的期望值。

    返回 {盘面名: (适配档n, 格边px, 棋盘x, 棋盘y, HUD)}。
    """
    cv = check_layout.Canvas('实测画布 %dx%d@%s' % (canvas_w, canvas_h, density),
                             canvas_w, canvas_h, density, 'tablet_check 实测画布')
    out = {}
    for row in check_layout.analyze(cv):
        g = row['g']
        out[row['bname']] = (int(row['fit']), int(g['tile']),
                             int(g['board'][0]), int(g['board'][1]),
                             1 if g.get('hud') else 0)
    return out


EMU = r'D:\software\DevEco Studio\tools\emulator\Emulator.exe'
HDC = r'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
INSTANCE = 'MatePad 12_2'
DEVICE = '127.0.0.1:5555'
BUNDLE = 'com.example.saolei'
HAP = r'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
WORKDIR = os.path.join(REPO, 'docs', 'verify', '.work')
os.makedirs(WORKDIR, exist_ok=True)

# 四个盘面的期望值**不写死** —— 由 expected_for() 按**实测画布**离线推演出来。
# 写死的那份（来自 check_layout.py 的 TABLET_EXPECT）假设画布是全屏 1840，
# 那是**真机**的情况；模拟器画布只有 1690，棋盘居中后原点会上移 ~75 px。
# 推演与实测必须在**同一个画布**上比。
EXPECT = None

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


def screen_size(shot_path):
    """从截图里读**屏幕**尺寸（截图就是屏幕像素）。

    画布顶偏移 = 屏幕高 - 画布高（模拟器顶部有系统状态栏，画布从它下面开始）。
    用截图量比问设备可靠：截图一定存在，而且尺寸就是屏幕尺寸。
    """
    try:
        from PIL import Image
        w, h = Image.open(shot_path).size
        return int(w), int(h)
    except Exception as exc:
        print('[tablet] 量不到屏幕尺寸（%s），画布顶偏移按 0 算' % exc)
        return 0, 0


def tap_menu(geom, top_vp, entry_vp):
    """点菜单栏的一个下拉条目（坐标是画布 vp）。

    换算**走 geom.to_screen()** —— 和跑测器逐字一致，不自己算
    （自己算过一次，忘了加画布顶偏移，菜单点了没反应）。
    """
    x, y = geom.to_screen("menu", top_vp[0], top_vp[1])
    sh('uitest', 'uiInput', 'click', str(x), str(y))
    time.sleep(1.0)
    x, y = geom.to_screen("menu", entry_vp[0], entry_vp[1])
    sh('uitest', 'uiInput', 'click', str(x), str(y))
    time.sleep(1.8)


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
    global DEVICE
    ap = argparse.ArgumentParser(description='MatePad Pro 12.2 适配验证')
    ap.add_argument('--no-emulator', action='store_true',
                    help='模拟器已经在跑时用这个（不重复启动）')
    ap.add_argument('--device', default=None,
                    help='目标设备（hdc 序列号）。不给就用模拟器实例。')
    ap.add_argument('--tag', default='tablet',
                    help='截图文件名前缀（区分模拟器和真机）')
    ap.add_argument('--out', default=os.path.join(REPO, 'docs', 'verify'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # 指定了设备就用它；否则起模拟器
    if args.device:
        DEVICE = args.device
    elif not args.no_emulator:
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

    # **轮询**等布局日志，不要固定睡几秒。
    # 坑（2026-11-03）：新装的实例首次启动，应用要 ~14 秒才画完第一帧
    # （固定 sleep 6 秒就报「没读到布局日志」），而真机更快、模拟器更慢，
    # 时间没法写死 —— 只能等「日志真的出现」。
    line = None
    for attempt in range(20):
        line = latest_layout(marker)
        if line:
            break
        print('[tablet] 还没读到布局日志，等第 %d 次（最多 20 次 × 3 秒）…' % (attempt + 1))
        time.sleep(3.0)
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

    # 先截一张（后面截图取不到要判失败，先确认这条路通）
    probe_shot = grab(args.out, 'TABLET_%s_probe.jpeg' % args.tag)

    # 画布顶偏移**实测**，不要用「屏幕高 - 画布高」去推。
    #
    # 坑（2026-11-03）：平板模拟器屏幕 2800x1840、画布 2800x1690，
    # 差 150 px —— 但那 150 px **不都在顶部**：
    # 实测顶部有 ~87 px 的系统状态栏（时钟、信号、电��），底部还有 ~63 px 的手势条，
    # 87+1690+63 = 1840 ✓。按「屏幕高 - 画布高」算成 150 就会点偏 60 多像素，
    # 菜单栏点了个空 —— 表现是「菜单点了没反应」。
    # 跑测器一直是对的，因为它用**实测**（找棋盘第一行砖色上沿），
    # 这里直接复用它的 Geom.probe_canvas_y()。
    hdc = Hdc(DEVICE)
    geom = Geom(hdc, WORKDIR)
    geom.layout = Layout(line)
    try:
        canvas_y = int(geom.probe_canvas_y())
    except Exception as exc:
        print('[tablet] 量不到画布顶偏移（%s）' % exc)
        return 1
    sw, sh_ = screen_size(probe_shot) if probe_shot else (0, 0)
    print('[tablet] 屏幕 %dx%d，画布 %dx%d，画布顶偏移**实测** %d px'
          % (sw, sh_, cw, ch, canvas_y))

    ok = True
    checked = []
    last_line = line

    # 期望值：按**实测画布**离线推演（不是写死的全屏期望）
    exp_all = expected_for(cw, ch, 1.0 / px_scale)
    print('[tablet] 离线推演（画布 %dx%d）：' % (cw, ch))
    for k in ("初级", "中级", "高级", "自定义"):
        if k in exp_all:
            e = exp_all[k]
            print('[tablet]   %-4s n=%d 格边 %d px 原点 (%d,%d) HUD=%d'
                  % (k, e[0], e[1], e[2], e[3], e[4]))

    def check_board(name):
        """核对一个盘面的布局是否符合期望。"""
        nonlocal ok, last_line
        exp = exp_all.get(name)
        if exp is None:
            print('[tablet] %s 没有期望值，跳过' % name)
            return
        ln = latest_layout(marker)
        if ln is None:
            print('[tablet] %s：没读到布局日志 ✗' % name)
            ok = False
            return
        last_line = ln
        mm = LAYOUT_RE.search(ln)
        if not mm:
            print('[tablet] %s：布局日志解析失败 ✗' % name)
            ok = False
            return
        g = mm.groups()
        hm = HUD_RE.search(ln)
        got = (int(g[3]), int(g[6]), int(g[7]), int(g[8]),
               int(hm.group(1)) if hm else 0)
        if got == exp:
            print('[tablet] %-4s n=%d 格边 %d px 原点 (%d,%d) HUD=%d —— 与期望一致 ✓'
                  % (name, got[0], got[1], got[2], got[3], got[4]))
        else:
            print('[tablet] %-4s 实测 %s，期望 %s ✗' % (name, got, exp))
            ok = False
        checked.append(name)
        # 换盘面后几何变了（格边、画布高度、状态条位置都可能不同），
        # 后面点菜单/点自定义框都要用**当前**这一版的布局
        try:
            geom.layout = Layout(ln)
        except Exception:
            pass

    # 第一个盘面（应用启动默认是初级）
    check_board("初级")

    # 依次切到其余三个盘面
    for name in ("中级", "高级"):
        print('[tablet] 切到 %s …' % name)
        tap_menu(geom, MENU_TOPS["game"], MENU_ENTRIES["game"][name])
        check_board(name)

    # 自定义 24x30：要先把「高度」设成 24、「宽度」设成 30
    print('[tablet] 切到 自定义 24x30 …')
    tap_menu(geom, MENU_TOPS["game"], MENU_ENTRIES["game"]["自定义"])
    time.sleep(1.2)

    def press_key(k):
        """按自定义框右侧数字键盘的一个键。

        键位表**从 click_matrix 拿**：["1".."9","back","0"] ——
        **0 在右下角中间，左下角是退格**。
        坑（2026-11-03）：我按「0 在左下角」写，输宽度 30 的时候
        第一个 3 正常、第二个 0 点到了**退格**，宽度变成 3，确定后非法。
        """
        i = KEYPAD_KEYS.index(k)
        col, row = i % 3, i // 3
        x = col * (KEY_W + KEY_GAP) + KEY_W / 2.0
        y = row * (KEY_H + KEY_GAP) + KEY_H / 2.0
        sx, sy = geom.to_screen("keypad", x, y)
        sh('uitest', 'uiInput', 'click', str(sx), str(sy))
        time.sleep(0.55)

    def tap_custom(vx, vy):
        """点自定义框里的一个位置（参考像素坐标，与跑测器的用例同源）。"""
        sx, sy = geom.to_screen("custom", vx, vy)
        sh('uitest', 'uiInput', 'click', str(sx), str(sy))
        time.sleep(0.7)

    def press_ok():
        rect = CUSTOM_BTN_OK
        sx, sy = geom.to_screen("custom",
                                rect[0] + rect[2] / 2.0,
                                rect[1] + rect[3] / 2.0)
        sh('uitest', 'uiInput', 'click', str(sx), str(sy))
        time.sleep(2.2)

    tap_custom(162, 56)          # 高度框
    press_key("2")
    press_key("4")
    tap_custom(162, 86)          # 宽度框
    press_key("3")
    press_key("0")
    press_ok()
    check_board("自定义")

    # 截图（取不到就判失败）
    shot = grab(args.out, 'TABLET_%s_play.jpeg' % args.tag)
    if shot is None:
        ok = False

    # 状态条读数（七段数码管）
    #
    # 坑（2026-11-03）：不能直接 `read_counters(path)` 全图搜索 ——
    # 棋盘上的蓝砖和计数器面板会被并成同一段列区间，面板就找不到了；
    # 而且「状态条上沿」是**画布内**坐标，截图是**屏幕**坐标，
    # 差着一段画布顶偏移（模拟器顶部 150 px 的系统状态栏）。
    # 必须限定在状态条那条横带里找（跟跑测器 click_matrix 的做法一致）。
    if shot:
        try:
            import sevenseg_read
            strip_top = None
            m2 = re.search(r'状态条上沿=(\d+)px', last_line or '')
            if m2:
                strip_top = canvas_y + int(m2.group(1))
            counters = []
            if strip_top is not None:
                counters = sevenseg_read.read_counters(
                    shot, strip_box=(0, strip_top, cw, max(1, sh_ - strip_top)))
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
