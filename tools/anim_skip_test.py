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

做法是 **A/B 对照**，不看「有没有框」，看**框是什么时候出现的**：

    A 组（不点）  ：踩雷 → 等结算框自己弹出来   → 记下耗时 ΔA
    B 组（补一刀） ：踩雷 → 等 0.4 秒 → 再点一下 → 记下耗时 ΔB

    ΔB 应该 ≪ ΔA：
      - 判负的爆炸级联在 9x9 上要 ~2.5 秒（冲击波环按距离错开起爆）；
      - 跳过后应该 **立刻**（一次点击的延迟内）弹出框。

两次都判负，唯一的差别就是「中途有没有补那一刀」，
所以 ΔB 明显小于 ΔA 就是「点击跳过动画」生效了。

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
BUNDLE = "com.example.saolei"

# 日志行形如： 11-03 14:05:27.422  3964  3964 I A03d00/JSAPP: [Dialog] 打开 失败
LOG_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Dialog\] 打开 (\S+)")
# 跳过动画时应用自己打的日志（毫秒时间戳，和 [Dialog] 是同一个时钟）
SKIP_RE = re.compile(r"^(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}).*\[Anim\] 点击跳过结算动画")


def hdc(device, *args, timeout=90):
    cmd = [HDC, "-t", device] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    return r.stdout


def log_seconds(device):
    """把 hilog 里的对话框时间戳转成「当天零点起的秒数」，取**最新**一条。

    同时也取**跳过动画**那条日志的时间（应用自己打的，毫秒精度）。

    注意：hilog 是环形缓冲，里面留着**上一轮**的对话框日志行，
    所以必须取最后一条（最新的），不能取第一条 —— 否则会读到旧局的框，
    时间差算出来是负的（2026-11-03 实测踩过这个坑）。
    """
    out = hdc(device, "shell", "hilog", "-x")
    stamps = {}
    skip_at = None
    for line in (out or "").splitlines():
        line = line.strip()
        m = LOG_RE.match(line)
        if m:
            _, hh, mm, ss, ms, kind = m.groups()
            t = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
            stamps[kind] = t          # 后出现的覆盖先出现的 → 留最新的
            continue
        m = SKIP_RE.match(line)
        if m:
            _, hh, mm, ss, ms = m.groups()
            skip_at = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
    return stamps, skip_at


def clear_log(device):
    """清空 hilog 缓冲（hilog -r），免得读到上一轮的旧日志。"""
    hdc(device, "shell", "hilog", "-r")


def now_seconds(device):
    """设备当前时刻（当天零点起的秒数）。"""
    out = hdc(device, "shell", "date", "+%H:%M:%S")
    m = re.search(r"(\d{2}):(\d{2}):(\d{2})", out or "")
    if not m:
        return None
    hh, mm, ss = m.groups()
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def find_mine(device, outdir):
    """开一局、推理出「确定是雷」的格子，返回 (屏幕 x, 屏幕 y, 几何信息)。"""
    img, layout, rows, cols = wp.restart_app(device, outdir)
    img, layout = wp.dismiss_dialogs(device, outdir, layout, rows, cols)
    if img is None:
        raise RuntimeError("棋盘上有盖不住的对话框")
    # 重启应用后布局日志要等一会儿才出来（真平板首次启动要 ~14 秒），
    # 所以这里轮询等，不能只读一次就报错。
    layout = None
    for attempt in range(20):
        layout = wp.read_layout(device, required=False)
        if layout is not None:
            break
        print('[skip] 还没读到布局日志，等第 %d 次（最多 20 次 × 1.5 秒）…' % (attempt + 1))
        time.sleep(1.5)
    if layout is None:
        raise RuntimeError("40 秒内没读到布局日志")
    gx, gy, pitch = wp.grid_from_layout(img, layout, rows, cols)
    unit = layout['unit']
    # 雷数从布局日志的原始行里取（read_layout 不解析这个字段）
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
    return gx + c * pitch + pitch / 2.0, gy + r * pitch + pitch / 2.0, (gx, gy, pitch, rows, cols)


def run_once(device, outdir, skip_click):
    """踩雷；skip_click=True 时在 0.4 秒后补一刀。返回 (弹框时刻-踩雷时刻)。"""
    x, y, geo = find_mine(device, outdir)
    gx, gy, pitch, rows, cols = geo
    clear_log(device)                      # 清掉上一轮留下的旧对话框日志
    t_mine = now_seconds(device)
    wp.click(device, x, y)
    t_click = None
    if skip_click:
        time.sleep(0.4)
        # 补一刀：点棋盘上另一个位置（原版是任何一次按下都能跳）
        t_click = now_seconds(device)
        wp.click(device, gx + (cols - 1) * pitch + pitch / 2.0, gy + pitch / 2.0)
    # 等对话框出现（最多 20 秒）
    deadline = time.time() + 20.0
    t_dialog = None
    t_skip = None
    while time.time() < deadline:
        stamps, skip_at = log_seconds(device)
        if '失败' in stamps:
            t_dialog = stamps['失败']
            t_skip = skip_at
            break
        if '胜利' in stamps:
            t_dialog = stamps['胜利']
            t_skip = skip_at
            break
        time.sleep(0.2)
    if t_dialog is None:
        raise RuntimeError("20 秒内没等到结算框")
    # 应用自己的两条日志之间：跳过 -> 弹框（毫秒级，最硬的证据）
    inner = None if t_skip is None else (t_dialog - t_skip)
    return t_dialog - t_mine, (None if t_click is None else t_dialog - t_click), inner


def main():
    ap = argparse.ArgumentParser(description="验证「点一下跳过结算动画」")
    ap.add_argument('--device', required=True)
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'docs', 'verify'))
    args = ap.parse_args()
    outdir = tempfile.mkdtemp(prefix='anim_skip_')

    print('=== A 组：不点，等爆炸级联自己放完 ===')
    dA, _, _ = run_once(args.device, outdir, skip_click=False)
    print('[skip] A 组：踩雷到弹框 %.2f 秒' % dA)

    print('=== B 组：踩雷后 0.4 秒补一刀 ===')
    dB, dB2, inner = run_once(args.device, outdir, skip_click=True)
    print('[skip] B 组：踩雷到弹框 %.2f 秒（补的那一刀到弹框 %.2f 秒）' % (dB, dB2))
    if inner is not None:
        print('[skip] 应用日志：跳过动画 -> 弹框 相隔 %.0f 毫秒' % (inner * 1000))

    print('')
    print('[skip] A(不点) = %.2f 秒   B(补一刀) = %.2f 秒' % (dA, dB))
    # 判据：
    #  1) 补一刀后弹框**明显更快**（比爆炸级联短 1 秒以上）—— 用外部时钟粗判；
    #  2) **应用自己的日志**里「跳过动画 -> 弹框」间隔在 300 毫秒以内 —— 这是硬证据。
    #
    # 为什么不用「补那一刀到弹框」那个数当判据：
    #   那是用设备的 `date +%H:%M:%S`（**秒级精度**）量的，
    #   里面还混着 `uitest uiInput click` 的投递延迟（真机上一次点击 ~0.5-1 秒）——
    #   那不是应用的响应速度。2026-11-03 实测：B 组外部时钟算出 1.43 秒，
    #   而应用日志里「跳过 -> 弹框」只有 -2 毫秒。所以判据用应用自己的毫秒日志。
    ok_fast = (dB + 1.0) < dA
    ok_log = inner is not None and inner < 0.3
    if ok_fast and ok_log:
        print('[skip] **通过**：不点要 %.2f 秒（爆炸级联放完才弹框）；'
              '补一刀后应用日志里「跳过 -> 弹框」只隔 %.0f 毫秒 —— '
              '点击跳过动画生效了' % (dA, (inner or 0) * 1000))
        return 0
    if not ok_fast:
        print('[skip] **失败**：补一刀并没有让弹框提前（差 %.2f 秒）' % (dA - dB))
    if not ok_log:
        print('[skip] **失败**：应用日志里没有「跳过 -> 弹框」这条链（inner=%s）' % inner)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
