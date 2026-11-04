# -*- coding: utf-8 -*-
"""
click_mkstate.py —— 给 tools/click_matrix.py 造出「失败框」「胜利框」两种局面。

它就是 click_matrix.py 用例表里两个语义动作的实现：

    lose_game -> win_probe.py --phase explode   （脚本自己重启应用、开一局、故意踩雷）
    win_game  -> win_probe.py --phase win      （脚本自己重启应用、推理解盘、赢一局）

跑完 win_probe 之后，对话框不是立刻就有的：
  * 失败框要先播完爆炸动画（约 2~3 秒）才弹出来；
  * 胜利框要先播完扫描条 + 拆雷光束动画（约 3 秒）才弹出来。
所以本脚本在 win_probe 返回之后会**轮询截图**，直到客户区变亮（#f0f0f0）为止。

用法:
    python tools\\click_mkstate.py --device 127.0.0.1:5557 --state lose
    python tools\\click_mkstate.py --device 127.0.0.1:5557 --state win

退出码: 0 = 对话框已出现；1 = 超时/失败；2 = 参数错。

**只读依赖**: 本脚本不改 win_probe.py，只调用它。子进程一律 CREATE_NO_WINDOW。
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, r"C:\Users\19161\.dsh\lib")
from nowindow import run  # noqa: E402  (带 CREATE_NO_WINDOW 的 subprocess.run)

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

HDC = r"D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
WIN_PROBE = os.path.join(HERE, "win_probe.py")

# ---------------------------------------------------------------------------
#  各对话框的**参考像素**几何（照抄 GameController / WinDialog 的公式，不另发明）
#    s   = max(0.5, min(2, 密度, (画布宽-32)/参考宽, (画布高-32)/参考高))
#    ox  = round((画布宽 - 参考宽*s)/2)
#    oy  = 参考高*s > 画布高 ? 0 : round((画布高 - 参考高*s)/2)
#    客户区 = 参考像素 (8, 30, 宽-16, 高-30-8-1)
#
#  **不要**再把「客户区在屏幕像素里的矩形」写死成某一台设备的值 ——
#  写死的话换设备（Mate X7 / Mate 90 Pro）就量不到框，轮询一直超时，
#  而失败会被记成「对话框没出现」。Codex 复审 2026-11-01 的 P1 就是这条。
#  现在改成：**用跑测器自己的几何算**（click_matrix.Geom），单一事实源。
# ---------------------------------------------------------------------------
DIALOGS = {
    "lose": (483, 288),
    "win": (396, 340),
}

# 客户区在对话框参考像素里的位置（WinDialog.ets 的版式：标题栏高 30，左右留 8）
CLIENT_X, CLIENT_Y = 8, 30


def _hdc(device, *args, timeout=90):
    cmd = [HDC, "-t", device] + list(args)
    return run(cmd, capture_output=True, timeout=timeout)


def _shot(device, path):
    """截一张全屏图到本机 path。

    坑（Codex 复审 2026-11-01 的 P2）：`hdc file recv` 在**目标已存在**时会失败，
    而之前这里既不删旧文件、也不看返回码，于是轮询时一直读到**第一次**那张
    （框还没出现时）的旧图，判成「框没出现」——假超时。
    现在：先删旧文件 + 检查返回码。
    """
    remote = "/data/local/tmp/cm_mkstate.jpeg"
    r = _hdc(device, "shell", "snapshot_display", "-f", remote)
    if r.returncode != 0:
        raise RuntimeError("snapshot_display 失败: %s" % (r.stderr or r.stdout)[-200:])
    if os.path.exists(path):
        os.remove(path)
    r = _hdc(device, "file", "recv", remote, path)
    if r.returncode != 0 or not os.path.exists(path):
        raise RuntimeError("file recv 失败: %s" % (r.stderr or r.stdout)[-200:])
    return path


def _measure_canvas_offset(device, outdir):
    """在**还没开局**（格子都盖着）的棋盘上量画布顶偏移。

    为什么必须先量（Codex 复审 2026-11-01 的 P1）：
    赢局之后 `win_probe` 把安全格全翻开、把雷全插旗 —— 棋盘里**一个没翻开的砖块都没有了**，
    这时候 `probe_canvas_y()`（找第一列的连续砖块行）要么直接报错，要么量到的是**下面某一行**
    的砖块，算出来的偏移偏大，胜利框的检测框就整个错位，轮询永远超时。
    所以顺序是：**先量偏移（未开局）→ 再让 win_probe 去赢**。
    画布在屏幕上的位置只跟窗口尺寸有关，跟难度/盘面无关，所以先量的值后面照样用。
    """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import click_matrix as cm

    hdc = cm.Hdc(device)
    # 只认**这一次启动之后**的布局日志：hilog 是环形缓冲，里面可能还留着
    # 上一次运行（甚至另一个方向）的布局行，拿到旧行就等于按错的画布尺寸算坐标。
    # （2026-11-03 真平板实测）
    marker = hdc.device_now_marker()
    hdc.stop_app()
    hdc.start_app()
    geom = cm.Geom(hdc, outdir)
    lay = geom.refresh_layout(retries=30, gap_s=1.5, marker=marker)
    # 等发牌动画结束再量（动画期间左上角还没翻上来，量到的是错值）
    for _ in range(12):
        time.sleep(0.5)
        hdc.screenshot(os.path.join(outdir, "pre.jpeg"))
        time.sleep(0.2)
        hdc.screenshot(os.path.join(outdir, "pre2.jpeg"))
        try:
            from PIL import Image as _I
            import numpy as _np
            a = _np.asarray(_I.open(os.path.join(outdir, "pre.jpeg")).convert("RGB")).astype(int)
            b = _np.asarray(_I.open(os.path.join(outdir, "pre2.jpeg")).convert("RGB")).astype(int)
            d = int((_np.abs(a - b).max(axis=2) > 12).sum())
            if d <= max(6, 0.0008 * a.shape[0] * a.shape[1]):
                break
        except Exception:
            pass
    cy = geom.probe_canvas_y()
    print("[mkstate] 未开局时量到画布顶偏移 = %d px（画布 %dx%d）"
          % (cy, lay.canvas_w, lay.canvas_h))
    return geom, cy


def _client_rect(device, state, outdir, geom, canvas_y):
    """算这个对话框的**客户区**在屏幕像素里的矩形（按当前设备的画布算）。

    复用 click_matrix.Geom 的几何（它已经照抄了 GameController 的公式），
    避免两边各写一份、慢慢走偏。
    """
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import click_matrix as cm

    geom.canvas_y = canvas_y
    ref_w, ref_h = DIALOGS[state]
    region = {
        "space": "dialog",
        "dialog": state,
        "x": CLIENT_X,
        "y": CLIENT_Y,
        "w": ref_w - 2 * CLIENT_X,
        "h": ref_h - CLIENT_Y - 9,
    }
    rect = geom.region_to_screen(region)
    print("[mkstate] %s 客户区（屏幕像素）= %s" % (state, rect))
    return rect


def _client_light(path, rect):
    """客户区里接近 #f0f0f0 的像素占比。"""
    if Image is None:
        return -1.0
    x, y, w, h = rect
    im = Image.open(path).convert("RGB")
    im = im.crop((x, y, x + w, y + h))
    px = im.load()
    total = im.width * im.height
    light = 0
    for j in range(im.height):
        for i in range(im.width):
            r, g, b = px[i, j]
            if abs(r - 240) <= 4 and abs(g - 240) <= 4 and abs(b - 240) <= 4:
                light += 1
    return float(light) / float(total)


def _bright_box(path, hint_rect, pad=80):
    """在提示矩形附近找出对话框**客户区**（#f0f0f0）的实际外接框。

    为什么要有这个（2026-11-01 晚踩到）：
    `win_probe` 的「赢一局」偶尔会**踩到雷**（它按解算结果点，设备慢的时候节奏会乱）。
    于是屏幕上弹的是**失败框**，而用例还在按**胜利框**的坐标点按钮 ——
    点空 → 对话框不关 → 用例报「按钮坏了」，锅全甩给被测代码。
    失败框 483×288、胜利框 396×340，**客户区的长宽比差得很远**
    （1.86 vs 1.24），量一下外接框就能分出来。
    """
    if Image is None:
        return None
    x, y, w, h = hint_rect
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    minx, miny, maxx, maxy = None, None, None, None
    for j in range(y0, y1):
        for i in range(x0, x1):
            r, g, b = px[i, j]
            if abs(r - 240) <= 4 and abs(g - 240) <= 4 and abs(b - 240) <= 4:
                if minx is None or i < minx:
                    minx = i
                if miny is None or j < miny:
                    miny = j
                if maxx is None or i > maxx:
                    maxx = i
                if maxy is None or j > maxy:
                    maxy = j
    if minx is None:
        return None
    return (minx, miny, maxx - minx + 1, maxy - miny + 1)


def _dialog_matches(path, state, hint_rect):
    """屏幕上的这个框，是不是**要的那个**框（胜利框 / 失败框）。

    判据：客户区外接框的长宽比。胜利框 396×340、失败框 483×288，
    参考比例 1.165 / 1.677，差得开；允许 ±12 % 的余量（缩放取整的误差）。
    """
    box = _bright_box(path, hint_rect)
    if box is None:
        return False, "画面里找不到客户区（#f0f0f0）"
    ref_w, ref_h = DIALOGS[state]
    want = (ref_w - 2 * CLIENT_X) / float(ref_h - CLIENT_Y - 9)
    got = box[2] / float(max(1, box[3]))
    ok = abs(got - want) / want <= 0.12
    return ok, "客户区外接框 %s，长宽比 %.3f（要的是 %.3f，%s框）" % (
        (box[2], box[3]), got, want, state)


def _run_win_probe(device, phase, outdir):
    # `--burst 1`：win_probe 默认连拍 16 帧爆炸动画，那是给**动画分析**用的。
    # 这里只需要「框弹出来了」，那一帧纯属白花时间（每帧一次截图 ~500ms）。
    cmd = [sys.executable, WIN_PROBE, "--device", device, "--phase", phase,
           "--out", outdir, "--burst", "1"]
    print("[mkstate] 执行:", " ".join(cmd))
    proc = run(cmd, capture_output=True, timeout=900)
    out = (proc.stdout or b"")
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    tail = [ln for ln in out.splitlines() if ln.strip()][-12:]
    for ln in tail:
        print("[win_probe]", ln)
    if proc.returncode != 0:
        err = (proc.stderr or b"")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        print("[mkstate] win_probe 退出码", proc.returncode, err[-800:])
    return proc.returncode


def _now_marker(device):
    """设备当前时间，做成和 hilog 行一样格式的时间戳（当"本轮起点"）。"""
    out = _hdc(device, "shell", "date", "+%m-%d %H:%M:%S")
    if out.returncode != 0:
        return None
    data = out.stdout or b""
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    lines = [ln.strip() for ln in data.splitlines() if ln.strip()]
    if not lines:
        return None
    ts = lines[-1]
    if len(ts) == 14:            # "MM-DD HH:MM:SS" -> 补到毫秒精度
        ts += ".000"
    return ts


def _dialog_log_type(device, outdir, marker=None):
    """问**应用自己**：屏幕上弹的是胜利框还是失败框。

    应用在打开结束框时打一条 `[Dialog] 打开 胜利` / `[Dialog] 打开 失败`
    （2026-11-01 加）。靠这条日志而不是靠像素猜 —— 像素猜会把失败框
    认成胜利框（两个框的长宽比只差 12 %，而且亮度分布也不一样）。
    返回 'win' / 'lose' / None（读不到）。

    `marker` = 本轮的起点时间戳（"MM-DD HH:MM:SS.mmm"）。
    只认**时间戳不早于 marker** 的行。
    坑（2026-11-03）：hilog 是**环形缓冲**，跑久了旧行被挤掉，
    「取最后一条」的数法会把**上一轮**的「[Dialog] 打开 失败」当成本轮的结果 ——
    明明赢了的局被判成失败，白白重来二十多分钟。
    """
    out = _hdc(device, "shell", "hilog", "-x")
    if out.returncode != 0:
        return None
    data = out.stdout or b""
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    last = None
    for ln in data.splitlines():
        if "[Dialog] 打开 " not in ln:
            continue
        if marker:
            ts = ln[:18]
            if len(ts) != 18 or ts < marker:
                continue
        last = ln
    if last is None:
        return None
    if "胜利" in last:
        return "win"
    if "失败" in last:
        return "lose"
    return None


def make_state(device, state, timeout=120.0, attempts=2):
    """造出指定局面；返回 True 表示对话框已经出现在屏幕上。

    会**重试**（默认 2 遍）：设备负载重的时候，win_probe 自己解算/点击的过程会被拖慢，
    偶尔一次没走通（没踩到雷、框没弹出来）。一次失败就判用例失败的话，
    失败的是**设备状态**而不是被测代码 —— 所以重来一遍（attempts）。
    """
    if state not in ("lose", "win"):
        raise ValueError("state 只能是 lose / win，收到 " + repr(state))
    phase = "explode" if state == "lose" else "win"
    for attempt in range(1, attempts + 1):
        outdir = tempfile.mkdtemp(prefix="cm_mkstate_")
        print("[mkstate] 第 %d/%d 遍造 %s 局面" % (attempt, attempts, state))
        # 本轮的起点时间戳：之后只认这个时间之后出现的对话框日志行
        # （hilog 是环形缓冲，旧行会被挤掉，取「最后一条」会拿到上一轮的）。
        marker = _now_marker(device)
        # 先在**未开局**的棋盘上量画布顶偏移（赢局之后棋盘全翻开，量不到砖块了）
        geom, canvas_y = _measure_canvas_offset(device, outdir)
        rc = _run_win_probe(device, phase, outdir)
        if rc != 0:
            print("[mkstate] win_probe 失败（退出码 %d）" % rc)
            if attempt < attempts:
                continue
            return False

        rect = _client_rect(device, state, outdir, geom, canvas_y)
        if _wait_dialog(device, state, rect, outdir, timeout):
            # 框是出现了，但**未必是要的那个框**：win_probe 的「赢一局」偶尔会踩到雷，
            # 弹出来的是失败框；后面按胜利框的坐标点按钮就全是空点。
            # 判据用**应用自己的日志**（[Dialog] 打开 胜利/失败）。
            got = _dialog_log_type(device, outdir, marker=marker)
            if got == state:
                print("[mkstate] %s 框核对通过（应用日志确认）" % state)
                return True
            if got is None:
                print("[mkstate] 读不到应用的对话框日志，按**像素**的长宽比再核一次")
                shot = os.path.join(outdir, "probe.jpeg")
                ok, why = _dialog_matches(shot, state, rect)
                if ok:
                    print("[mkstate] %s 框核对通过（%s）" % (state, why))
                    return True
                print("[mkstate] %s 框核对**不通过**：%s —— 重来" % (state, why))
            else:
                print("[mkstate] 应用日志说弹的是**%s框**，要的是 %s框 —— 重来"
                      % (got, state))
        print("[mkstate] 第 %d 遍没等到 %s 框" % (attempt, state))
    return False


def _wait_dialog(device, state, rect, outdir, timeout):
    """轮询截图，等对话框出现（客户区里接近 #f0f0f0 的像素过半）。"""
    shot = os.path.join(outdir, "probe.jpeg")
    deadline = time.time() + timeout
    best = -1.0
    while time.time() < deadline:
        time.sleep(1.5)
        try:
            _shot(device, shot)
            ratio = _client_light(shot, rect)
        except Exception as exc:  # 截图失败就再等一轮
            print("[mkstate] 截图失败:", exc)
            continue
        best = max(best, ratio)
        print("[mkstate] 客户区亮像素占比 = %.3f" % ratio)
        if ratio > 0.5:
            print("[mkstate] %s 框已出现" % state)
            return True
    print("[mkstate] 超时：%s 框没出现（最高占比 %.3f）" % (state, best))
    return False


def main():
    ap = argparse.ArgumentParser(description="造出失败框/胜利框局面")
    ap.add_argument("--device", default="127.0.0.1:5557")
    ap.add_argument("--state", choices=["lose", "win"], required=True)
    ap.add_argument("--timeout", type=float, default=120.0,
                    help="等对话框出现的秒数（默认 120）")
    ap.add_argument("--attempts", type=int, default=6,
                    help="最多造几遍（默认 3；设备负载重的时候 win_probe 会偶发失手，"
                         "偶尔会踩到雷、弹出的是失败框，这时按长宽比核对会发现并重来）")
    args = ap.parse_args()
    ok = make_state(args.device, args.state, args.timeout, args.attempts)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
