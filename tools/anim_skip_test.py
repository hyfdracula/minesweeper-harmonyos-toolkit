# -*- coding: utf-8 -*-
"""
anim_skip_test.py —— 验证「结算动画期间点一下，立刻跳过动画直接弹结算框」。

这是原版 Win7 的行为，依据在参考实现里：
    linux-minesweeper/src/ui/BoardWidget.cpp:783-793
        if (m_board->over()) {
            finishExplosionNow();   // a click skips the cascade, like Win7
            finishWinNow();
            return;                 // 这次点击被吃掉，不会开格
        }

## 怎么测

两条路径各测一次，都是 **应用自己的毫秒日志**说了算：

  判负（爆炸级联）：[Anim] 爆炸级联开始 -> [Dialog] 打开 失败
  判胜（拆雷光幕）：[Anim] 胜利扫描条开始 -> [Dialog] 打开 胜利

判据：
  - 判负不点：级联开始 -> 弹框 要 **1.5 秒以上**（证明级联真的在放）；
  - 判负补一刀：[Anim] 点击跳过结算动画 -> [Dialog] 打开 **300 毫秒以内**；
  - 判胜补一刀：同上（光幕比级联长得多，差得更明显）。

## 为什么不用外部时钟

设备端 `date +%H:%M:%S` 只有**秒级精度**，而且里面混着
`uitest uiInput click` 的投递延迟（真机一次点击 ~0.5-1 秒）——
那不是应用的响应速度。2026-11-03 实测：外部时钟算出「补一刀到弹框 1.43 秒」，
而应用日志里「跳过 -> 弹框」只有 -2 毫秒，差两个数量级。

而且爆炸级联的**总时长随雷位随机变化**（冲击波环按最远那颗雷算），
同一台设备上「不点」那组实测在 2.68 ~ 3.56 秒之间跳，
两个外部时钟的差值会被这些噪声淹没（实测出现过只差 0.91 秒的）。

## hilog 的两个坑

1. 裸 `hilog` 是**流式输出**，会一直挂着不返回 —— 必须用 `hilog -x`。
2. `hilog -x` 会**清空缓冲**。所以：
   - 每轮动作前用 `hilog -r` 清一次；
   - 需要「检测到某个时刻」时，**整块读一次**就够 ——
     那一读里既有检测到的那行，也有后面几毫秒内的其它行；
   - 检测到之后再清一次，避免下一轮的旧行混进来。

用法：
    python tools\\anim_skip_test.py --device <序列号>
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import win_probe as wp  # noqa: E402

HDC = r"D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"

# 日志行形如： 11-03 14:05:27.422  3964  3964 I A03d00/JSAPP: [Dialog] 打开 失败
LOG_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Dialog\] 打开 (\S+)")
# 跳过动画时应用自己打的日志（毫秒时间戳，和 [Dialog] 是同一个时钟）
SKIP_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Anim\] 点击跳过结算动画")
# 两种结算动画各自开始的时刻（应用自己打的）
WIN_START_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Anim\] 胜利扫描条开始")
TRIP_START_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Anim\] 爆炸级联开始")


def hdc(device, *args, timeout=90):
    cmd = [HDC, "-t", device] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.stdout


def _ts(m):
    """把 "MM-DD HH:MM:SS.mmm" 的时分秒转成「当天零点起的秒数」。"""
    _, hh, mm, ss, ms = m.groups()
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def read_log(device):
    """读一次 hilog（**会清缓冲**），返回关键时间戳。

    同一种日志可能出现多次（上一轮残留 + 本轮），一律留**最后**一条。
    """
    out = hdc(device, "shell", "hilog", "-x")
    res = {'trip_start': None, 'win_start': None, 'skip_at': None,
           'dialog_at': None, 'dialog_kind': None}
    for line in (out or "").splitlines():
        line = line.strip()
        for key, rx in (('trip_start', TRIP_START_RE), ('win_start', WIN_START_RE),
                        ('skip_at', SKIP_RE)):
            m = rx.match(line)
            if m:
                res[key] = _ts(m)
        m = LOG_RE.match(line)
        if m:
            _, hh, mm, ss, ms, kind = m.groups()
            res['dialog_at'] = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
            res['dialog_kind'] = kind
    return res


def clear_log(device):
    """清空 hilog 缓冲（hilog -r）。"""
    hdc(device, "shell", "hilog", "-r")


def wait_layout(device):
    """轮询等布局日志（真平板重启应用后要 ~14 秒才出来）。"""
    for attempt in range(20):
        layout = wp.read_layout(device, required=False)
        if layout is not None:
            return layout
        print('[skip] 还没读到布局日志，等第 %d 次（最多 20 次 × 1.5 秒）…' % (attempt + 1))
        time.sleep(1.5)
    raise RuntimeError("40 秒内没读到布局日志")


def fresh_board(device, outdir):
    """重开一局并返回 (屏幕格边信息, 布局)。

    只调 `restart_app`，**不要再调 `dismiss_dialogs`**：
    `restart_app` 自己就会一直轮询到「认得出网格、而且格子里是真的扫雷砖块
    （不是桌面壁纸花纹）」为止，所以棋盘已经是干净的。
    而 `dismiss_dialogs` 在没有对话框时会**按返回键**，那会把应用直接退出到桌面
    （2026-11-03 实测踩到：按了 4 次返回键，应用没了，只剩桌面）。
    """
    img, layout, rows, cols = wp.restart_app(device, outdir)
    layout = wait_layout(device)
    gx, gy, pitch = wp.grid_from_layout(img, layout, rows, cols)
    return (gx, gy, pitch, rows, cols), layout


def find_mine(device, outdir):
    """开一局、推理出「确定是雷」的格子，返回 (屏幕 x, 屏幕 y, 几何信息)。"""
    geo, layout = fresh_board(device, outdir)
    gx, gy, pitch, rows, cols = geo
    unit = layout['unit']
    mm = re.search(r'雷=(\d+)', layout.get('raw') or '')
    mines = int(mm.group(1)) if mm else 10
    templates = wp.load_templates()
    mine_tmpl = wp.load_mine_template()
    # 首点安全：先点一下把雷布下
    wp.click(device, gx + cols // 2 * pitch + pitch / 2.0, gy + rows // 2 * pitch + pitch / 2.0)
    time.sleep(1.8)
    img = wp.pull_screenshot(device, os.path.join(outdir, 'skip_first.jpeg'))
    board = wp.read_board(img, gx, gy, pitch, unit, templates, rows, cols, mine_tmpl)
    res, mine_certain = wp.solve(board, rows, cols, mines)
    if not mine_certain:
        raise RuntimeError("推理不出哪格是雷")
    r, c = sorted(mine_certain)[0]
    return gx + c * pitch + pitch / 2.0, gy + r * pitch + pitch / 2.0, geo


def run_lose(device, outdir, skip_click):
    """踩雷；skip_click=True 时在 0.4 秒后补一刀。返回日志时间戳字典。"""
    x, y, geo = find_mine(device, outdir)
    gx, gy, pitch, rows, cols = geo
    clear_log(device)
    wp.click(device, x, y)                       # 踩雷 -> 级联开始
    if skip_click:
        time.sleep(0.4)
        # 补一刀：点棋盘上另一个位置（原版是任何一次按下都能跳）
        wp.click(device, gx + (cols - 1) * pitch + pitch / 2.0, gy + pitch / 2.0)
        time.sleep(1.5)
    else:
        time.sleep(6.0)                           # 等级联放完
    return read_log(device)


def run_win(device, outdir):
    """玩到赢，然后补一刀打断光幕。返回日志时间戳字典。"""
    geo, layout = fresh_board(device, outdir)
    gx, gy, pitch, rows, cols = geo
    unit = layout['unit']
    mm = re.search(r'雷=(\d+)', layout.get('raw') or '')
    mines = int(mm.group(1)) if mm else 10
    templates = wp.load_templates()
    mine_tmpl = wp.load_mine_template()
    img = wp.pull_screenshot(device, os.path.join(outdir, 'win_start.jpeg'))
    for step in range(40):
        clear_log(device)
        board = wp.read_board(img, gx, gy, pitch, unit, templates, rows, cols, mine_tmpl)
        res, mine_certain = wp.solve(board, rows, cols, mines)
        if res is None:
            if step == 0:
                res = (rows // 2, cols // 2)
            elif mine_certain:
                r, c = sorted(mine_certain)[0]
                wp.flag(device, gx + c * pitch + pitch / 2.0, gy + r * pitch + pitch / 2.0)
                time.sleep(1.1)
                img = wp.pull_screenshot(device, os.path.join(outdir, 'win_%02d.jpeg' % step))
                continue
            else:
                raise RuntimeError("推不出下一步了")
        r, c = res
        wp.click(device, gx + c * pitch + pitch / 2.0, gy + r * pitch + pitch / 2.0)
        # 点完立刻看日志：扫描条开始了没有？
        time.sleep(0.6)
        log = read_log(device)
        if log['win_start'] is not None:
            print('[skip] 胜利扫描条开始了（step=%d），补一刀…' % step)
            clear_log(device)
            # 补一刀：原版是任何一次按下都能跳
            wp.click(device, gx + (cols - 1) * pitch + pitch / 2.0, gy + pitch / 2.0)
            time.sleep(1.5)
            log = read_log(device)
            log['win_start_detected'] = True
            return log
        time.sleep(0.5)
        img = wp.pull_screenshot(device, os.path.join(outdir, 'win_%02d.jpeg' % step))
    raise RuntimeError("40 步之内没赢")


def main():
    ap = argparse.ArgumentParser(description="验证「点一下跳过结算动画」")
    ap.add_argument('--device', required=True)
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'docs', 'verify'))
    ap.add_argument('--skip-win', action='store_true', help='只测判负那一路')
    args = ap.parse_args()
    outdir = tempfile.mkdtemp(prefix='anim_skip_')
    ok = True

    # ---------------- 判负：爆炸级联 ----------------
    print('=== 判负 A 组：不点，等爆炸级联自己放完 ===')
    a = run_lose(args.device, outdir, skip_click=False)
    if a['trip_start'] is None or a['dialog_at'] is None:
        print('[skip] **失败**：没读到「爆炸级联开始」或「Dialog 打开」日志：%s' % a)
        ok = False
    else:
        cascade = a['dialog_at'] - a['trip_start']
        print('[skip] A 组：级联开始 -> 弹框 %.2f 秒' % cascade)
        if cascade <= 1.5:
            print('[skip] **失败**：级联只放了 %.2f 秒就弹框了，测法有问题' % cascade)
            ok = False

    print('=== 判负 B 组：踩雷后 0.4 秒补一刀 ===')
    b = run_lose(args.device, outdir, skip_click=True)
    if b['skip_at'] is None or b['dialog_at'] is None:
        print('[skip] **失败**：没读到「点击跳过结算动画」或「Dialog 打开」日志：%s' % b)
        ok = False
    else:
        gap = b['dialog_at'] - b['skip_at']
        print('[skip] B 组：跳过 -> 弹框 相隔 %.0f 毫秒' % (gap * 1000))
        if gap >= 0.3:
            print('[skip] **失败**：跳过之后用了 %.0f 毫秒才弹框，不是「立刻」' % (gap * 1000))
            ok = False

    # ---------------- 判胜：拆雷光幕 ----------------
    if not args.skip_win:
        print('=== 判胜：赢下来后补一刀打断光幕 ===')
        w = run_win(args.device, outdir)
        if w['skip_at'] is None or w['dialog_at'] is None:
            print('[skip] **失败**：没读到「点击跳过结算动画」或「Dialog 打开 胜利」日志：%s' % w)
            ok = False
        else:
            gap = w['dialog_at'] - w['skip_at']
            print('[skip] 判胜：跳过 -> 弹框 相隔 %.0f 毫秒（框是 %s）'
                  % (gap * 1000, w['dialog_kind']))
            if gap >= 0.3:
                print('[skip] **失败**：光幕跳过后用了 %.0f 毫秒才弹框' % (gap * 1000))
                ok = False

    print('')
    if ok:
        print('[skip] **全部通过**：两条结算动画（爆炸级联、拆雷光幕）都能被一次点击立即跳过。')
        return 0
    print('[skip] **有失败项**，见上面。')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
