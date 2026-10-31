# -*- coding: utf-8 -*-
"""
p90_driver.py —— 设备 B(127.0.0.1:5557) 的点击/截图小驱动。

只做三件事：点一下、截一张图、问一句「某个对话框在不在」。
子进程一律带 CREATE_NO_WINDOW（见 ~/.dsh/AGENTS.md）。

用法:
    python p90_driver.py click X Y
    python p90_driver.py shot 名称            # 存到 docs/verify/P90_<名称>.jpeg
    python p90_driver.py redx                 # 打印结束对话框红色 X 的坐标（没有就打印 none）
    python p90_driver.py dialog               # 打印对话框区域的白像素占比
    python p90_driver.py seq "cmd;cmd;cmd"    # 依次执行
    python p90_driver.py lose X Y [次数]      # 反复点棋盘直到结束对话框出现
"""
import os
import subprocess
import sys
import time

HDC = r"D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
DEV = "127.0.0.1:5557"
VER = r"D:\software\harmony\projects\minesweeper\docs\verify"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def hdc(*args, timeout=60):
    cmd = [HDC, "-t", DEV] + list(args)
    return subprocess.run(cmd, capture_output=True, timeout=timeout,
                          creationflags=NO_WINDOW)


def click(x, y):
    hdc("shell", "uitest", "uiInput", "click", str(x), str(y))
    time.sleep(0.45)


def shot(name):
    remote = "/data/local/tmp/%s.jpeg" % name
    hdc("shell", "snapshot_display", "-f", remote)
    dst = os.path.join(VER, "P90_%s.jpeg" % name)
    hdc("file", "recv", remote, dst)
    return dst


def pixels(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    return im.load(), im.size


def find_red_x(path):
    px, (w, h) = pixels(path)
    pts = [(x, y) for y in range(1200, 1400) for x in range(700, 1000)
           if px[x, y][0] - px[x, y][1] > 60 and px[x, y][0] - px[x, y][2] > 60]
    if not pts:
        return None
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def white_ratio(path):
    px, (w, h) = pixels(path)
    n = 0
    tot = 0
    for y in range(1250, 1580):
        for x in range(400, 880):
            tot += 1
            p = px[x, y]
            if p[0] > 230 and p[1] > 230 and p[2] > 228:
                n += 1
    return n, tot


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    if a[0] == "click":
        click(int(a[1]), int(a[2]))
        print("clicked", a[1], a[2])
    elif a[0] == "shot":
        print(shot(a[1]))
    elif a[0] == "redx":
        p = os.path.join(VER, "P90_probe.jpeg")
        shot("probe")
        print(find_red_x(p))
    elif a[0] == "dialog":
        p = os.path.join(VER, "P90_probe.jpeg")
        shot("probe")
        print(white_ratio(p))
    elif a[0] == "lose":
        # 在棋盘范围内轮换着点，直到结束对话框出现
        cells = [(x, y) for x in (250, 350, 450, 550, 650, 750, 850, 950, 1050)
                 for y in (1200, 1300, 1400, 1500, 1600)]
        tries = int(a[3]) if len(a) > 3 else 12
        for i in range(min(tries, len(cells))):
            x, y = cells[i]
            click(x, y)
            p = os.path.join(VER, "P90_probe.jpeg")
            shot("probe")
            r = find_red_x(p)
            if r:
                print("lose dialog after %d clicks, red x=%s" % (i + 1, r))
                return
        print("lose dialog NOT found after %d clicks" % tries)
    elif a[0] == "seq":
        for cmd in a[1].split(";"):
            cmd = cmd.strip()
            if not cmd:
                continue
            parts = cmd.split()
            if parts[0] == "click":
                click(int(parts[1]), int(parts[2]))
            elif parts[0] == "shot":
                print(shot(parts[1]))
            elif parts[0] == "sleep":
                time.sleep(float(parts[1]))
            else:
                print("unknown", cmd)
    else:
        print("unknown cmd", a[0])


if __name__ == "__main__":
    main()
