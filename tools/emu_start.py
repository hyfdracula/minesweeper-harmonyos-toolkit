# -*- coding: utf-8 -*-
"""启动 DevEco 模拟器（脱离本进程，独立存活）。

用法：python tools\emu_start.py "Mate 90 Pro" ["Mate X7"]

坑（2026-11-01 踩了一小时）：
1) `-instancePath` 要给**父目录**（.../Emulator/deployed），不是 AVD 自己那一层；
   给成 AVD 目录时 CLI 直接回 "Unable to start the emulator"，
   而且**一条日志都不写**（Emulator.log / qemu.log 全无新行），非常难查。
2) 启动是**前台阻塞**的：必须用 DETACHED_PROCESS 把它甩出去，
   否则父进程一退出（或者 subprocess 超时被 kill），模拟器跟着死。
3) 模拟器崩过之后，机器内存会被吃光（两个 4GB 的），再启动会失败；
   先看可用内存，不够就只起一个。
"""
import subprocess
import sys
import time

EXE = r"D:\software\DevEco Studio\tools\emulator\Emulator.exe"
INSTANCE_PATH = r"C:/Users/19161/AppData/Local/Huawei/Emulator/deployed"
IMAGE_ROOT = r"C:\Users\19161\AppData\Local\Huawei\Sdk"

DETACHED = 0x00000008 | 0x00200000   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def start(name: str) -> int:
    argv = [EXE, "-start", name, "-instancePath", INSTANCE_PATH, "-imageRoot", IMAGE_ROOT]
    p = subprocess.Popen(argv, creationflags=DETACHED, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    print("已拉起 %s（pid %d）" % (name, p.pid))
    return p.pid


if __name__ == "__main__":
    names = sys.argv[1:] or ["Mate 90 Pro"]
    for n in names:
        start(n)
        time.sleep(8)
