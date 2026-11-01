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
#  各对话框在画布上的几何（照抄 GameController 的公式，不另发明）
#    s   = max(0.5, min(2, 密度, (画布宽-32)/参考宽, (画布高-32)/参考高))
#    ox  = round((画布宽 - 参考宽*s)/2)
#    oy  = 参考高*s > 画布高 ? 0 : round((画布高 - 参考高*s)/2)
#    客户区 = 参考像素 (8, 30, 宽-16, 高-30-8-1)
#  下面是 **5557（Mate 90 Pro 模拟器）** 的实测值：画布 1280x2598、密度 3.5、
#  画布顶在屏幕上的纵向偏移 138 px。换设备要用 tools\\probe_canvas.py 重量。
# ---------------------------------------------------------------------------
CANVAS_W = 1280
CANVAS_H = 2598
CANVAS_TOP = 138

#: 对话框名 -> (参考宽, 参考高, 缩放 s, 客户区在**屏幕**像素里的矩形 x,y,w,h)
DIALOGS = {
    "lose": (483, 288, 2.0, (173, 1209, 934, 500)),
    "win": (396, 340, 2.0, (260, 1157, 760, 618)),
}


def _hdc(device, *args, timeout=90):
    cmd = [HDC, "-t", device] + list(args)
    return run(cmd, capture_output=True, timeout=timeout)


def _shot(device, path):
    """截一张全屏图到本机 path。"""
    remote = "/data/local/tmp/cm_mkstate.jpeg"
    _hdc(device, "shell", "snapshot_display", "-f", remote)
    _hdc(device, "file", "recv", remote, path)
    return path


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


def _run_win_probe(device, phase, outdir):
    cmd = [sys.executable, WIN_PROBE, "--device", device, "--phase", phase, "--out", outdir]
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


def make_state(device, state, timeout=45.0):
    """造出指定局面；返回 True 表示对话框已经出现在屏幕上。"""
    if state not in ("lose", "win"):
        raise ValueError("state 只能是 lose / win，收到 " + repr(state))
    phase = "explode" if state == "lose" else "win"
    outdir = tempfile.mkdtemp(prefix="cm_mkstate_")
    _run_win_probe(device, phase, outdir)

    rect = DIALOGS[state][3]
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
    ap.add_argument("--timeout", type=float, default=45.0,
                    help="等对话框出现的秒数（默认 45）")
    args = ap.parse_args()
    ok = make_state(args.device, args.state, args.timeout)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
