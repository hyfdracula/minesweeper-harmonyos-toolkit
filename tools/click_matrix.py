#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
click_matrix.py —— 扫雷复刻（HarmonyOS）的**点击矩阵自动跑测器**。

把以前手点的「每一个按钮都点一遍」变成可重跑的机器检查。

用法：
    python tools\\click_matrix.py --device 127.0.0.1:5557
    python tools\\click_matrix.py --device 127.0.0.1:5557 --cases menu,board
    python tools\\click_matrix.py --device 127.0.0.1:5557 --only menu.game
    python tools\\click_matrix.py --device 127.0.0.1:5557 --tag 1101

用例表：tools\\click_cases\\<域>.json，跑测器 glob 这个目录。
格式见本文件末尾的「用例表格式」一节，或 docs\\CLICK-MATRIX-AUTO.md。

================================================================================
坐标系（照抄 GameController.ets 的算法，不另发明）
================================================================================
屏幕 → 画布：   画布设备像素 = 屏幕 y - CANVAS_Y（CANVAS_Y 是画布顶在屏幕上的纵向偏移，
              用 tools\\probe_canvas.py 那套办法量：未开局的棋盘第一行砖色上沿 - 棋盘原点 y）
画布 vp → 屏幕： x = round(vp_x / pxScale)，y = CANVAS_Y + round(vp_y / pxScale)
              （日志里的「密度换算」就是 pxScale，密度是它的倒数）
对话框：        s  = max(0.5, min(2, 密度, (画布宽-32)/参考宽, (画布高-32)/参考高))
              ox = round((画布宽 - 参考宽*s)/2)
              oy = 参考高*s > 画布高 ? 0 : round((画布高 - 参考高*s)/2)
              参考像素 → 画布设备像素 = (ox + refX*s, oy + refY*s)
自定义框：      s  = computeDialogScale(280+12+键盘宽, max(200, 键盘高))
              customOx = round((画布宽 - (280*s + 12*s + 键盘宽*s))/2)
              customOy = 总高 > 画布高 ? 0 : round((画布高 - 总高)/2)
              键盘原点 = customOx + (280+12)*s

================================================================================
检查点（checkpoint）语义
================================================================================
`changed` / `unchanged` 跟**上一个 expect 的检查点**比，不是跟用例开头比。
每个 expect 执行完把当前截图存成新检查点；`reset` 会重置检查点。
（custom-agent 明确要求：越界输入那几条是「expect changed → 按键 → expect unchanged」，
 基准如果做成「用例开头」就会误判。）

================================================================================
断言类型
================================================================================
changed / unchanged   必给 region（整屏永远在变——状态条时钟每秒跳）
layout_changed        布局日志与上一次不同
layout_regex          布局日志匹配正则
hilog_regex           hilog 出现匹配的新行（只看本次跑测期间新出现的行）
cell_opened           被翻开的正好是被点的那一格（触摸路由对位）
region_dark/light     区域平均亮度偏暗/偏亮（粗判「框在不在」）
app_alive             应用进程还在不在（alive: false = 被终止了）

================================================================================
子进程纪律
================================================================================
Windows 上一律 CREATE_NO_WINDOW：统一走 C:\\Users\\19161\\.dsh\\lib\\nowindow.py。
不 pip install（PIL / numpy 运行时已有）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, r"C:\Users\19161\.dsh\lib")
from nowindow import run  # noqa: E402  （带 CREATE_NO_WINDOW 的 subprocess.run）

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(HERE, "click_cases")
DOCS_DIR = os.path.join(os.path.dirname(HERE), "docs")
VERIFY_DIR = os.path.join(DOCS_DIR, "verify")
HDC = r"D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe"
BUNDLE = "com.example.saolei"
MKSTATE = os.path.join(HERE, "click_mkstate.py")

# ---------------------------------------------------------------------------
#  各对话框的参考尺寸（原版 1 倍像素），照抄源码
#    WinDialog.loseSpec  483x288 / winSpec 396x340 / helpSpec 584x280 / aboutSpec 314x197
#    StatsWindowPainter.width()/height()  702x254
#    Appearance.ets DLG_W/DLG_H  420x340
# ---------------------------------------------------------------------------
DIALOG_REF = {
    "lose": (483, 288),
    "win": (396, 340),
    "help": (584, 280),
    "about": (314, 197),
    "stats": (702, 254),
    "appearance": (420, 340),
}

# ---------------------------------------------------------------------------
#  自定义难度框与数字键盘（照抄 CustomField.ets / NumKeypad.ets）
# ---------------------------------------------------------------------------
CUSTOM_DLG_W = 280
CUSTOM_DLG_H = 200
CUSTOM_GAP = 12
KEY_W, KEY_H, KEY_GAP = 34, 30, 4
KEYPAD_W = 3 * KEY_W + 2 * KEY_GAP          # 110
KEYPAD_H = 4 * KEY_H + 3 * KEY_GAP          # 132
#: 键序（照抄 NumKeypad.ets 的 KEYS）：1..9、⌫、0
KEYPAD_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "back", "0"]
#: 框内两个按钮（参考像素，左上角）：确定 / 取消
CUSTOM_BTN_OK = (116, 158, 70, 25)
CUSTOM_BTN_CANCEL = (194, 158, 70, 25)

# ---------------------------------------------------------------------------
#  长按（插旗）的手势候选
#
#  首选 **uitest uiInput longClick x y** —— uitest 自带的长按命令
#  （tools/win_probe.py 的插旗就是用它，见 win_probe.py:1093）。
#  备选是「极慢的 swipe」顶替：
#      uitest uiInput swipe x1 y1 x2 y2 <第5个参数>
#  第 5 个参数**不同设备解释不一样**：
#    * 模拟器上是**速度**（px/s）：1 px / 1 px·s⁻¹ = 按住约 1 秒 → 应用收到长按；
#    * 真平板上是**时长**（ms）：1 px / 1 = 只按 1 ms → 应用收到的是**单击**。
#  2026-11-03 在 MatePad Pro MRO-W00（API 26）上实测就是后者：
#  「插旗」变成了「点开那一格」，棋面被翻开、计时器开始走，
#  那一局还因此踩雷输掉（证据：docs/verify/CM_1430tabreal_FAIL_board_counter_flag_step5_cur.jpeg，
#  画面上第 (0,0) 格是翻开的，没有旗）。
#
#  所以：**哪种手势对只能在设备上试**，而且必须**用画面验证**
#  （试完看那一格到底插上旗了没有）。见 Runner.calibrate_longpress。
#
#  格式：(名字, 方式, 参数)
#  swipe 的位移都控制在 10 vp 以内 —— 应用的平移阈值是 MOVE_THRESHOLD_VP = 10 vp
#  （MinefieldCanvas.ets:39），超过就变成「拖动棋盘」而不是长按。
# ---------------------------------------------------------------------------
LONGPRESS_VARIANTS = [
    ("longClick", "longClick", None),
    ("swipe 1px/1", "swipe", (1, 1)),
    ("swipe 1px/600", "swipe", (1, 600)),
    ("swipe 3px/1", "swipe", (3, 1)),
    ("swipe 3px/800", "swipe", (3, 800)),
    ("swipe 8px/40", "swipe", (8, 40)),
]

# ---------------------------------------------------------------------------
#  菜单栏坐标（**画布 vp**）
#
#  为什么不给屏幕坐标：条目位置由字体推进量决定，代码算不准，只能实测；
#  而实测的屏幕坐标换设备就不能用了。vp 是设备无关的，所以：
#      vp_x = 屏幕x / 密度
#      vp_y = (屏幕y - 画布顶偏移) / 密度
#
#  实测来源：Mate 90 Pro 模拟器（127.0.0.1:5557，密度 3.5，画布顶偏移 139），
#  2026-11-01 从截图里量出每个下拉条目的文字墨迹 bbox 中心，换算成 vp。
#  文字墨迹中心 = 点击点，落在字上最稳。
# ---------------------------------------------------------------------------
MENU_TOPS = {
    "game": (25.7, 7.7),      # 游戏(G)
    "help": (90.0, 7.7),      # 帮助(H)
}
MENU_ENTRIES = {
    "game": {
        "新建": (33.0, 35.1),
        "初级": (33.0, 66.3),
        "中级": (33.0, 90.3),
        "高级": (33.0, 114.3),
        "自定义": (33.0, 138.3),
        "标记(?)": (33.0, 162.3),
        "声音": (33.0, 193.1),
        "最佳成绩": (33.0, 224.3),
        "颜色(C)": (33.0, 248.6),
        "退出": (33.0, 279.1),
    },
    "help": {
        "帮助(H)": (100.0, 35.4),
        "关于扫雷": (100.0, 66.3),
    },
}

#: 布局日志的正则
LAYOUT_RE = re.compile(
    r"画布=(\d+)x(\d+)px\s+密度换算=([0-9.]+)\s+适配档n=(\d+)\s+当前档n=(\d+)\s+"
    r"unit=(\d+)\s+格边=(\d+)px\s+棋盘原点=\((-?\d+),(-?\d+)\)"
)
# 状态条上沿（HUD 时是画布底边那条），可选
STRIP_RE = re.compile(r"状态条上沿=(\d+)px")
# 盘面规格（2026-11-01 加进应用日志的），可选
BOARD_RE = re.compile(r"盘面=(\d+)x(\d+)\s+雷=(\d+)")


def log_line_after(line: str, marker: str) -> bool:
    """这条 hilog 行是不是在 `marker` 之后？（marker 是 "MM-DD HH:MM:SS.mmm"）

    取行首 18 个字符当时间戳，和 marker 逐字符比（格式相同，直接比字符串即可）。
    **取不到时间戳的行一律当作「不是之后的」** —— 宁可漏，不可把旧行当新的。
    """
    if not marker:
        return True
    head = line[:18]
    if len(head) != 18:
        return False
    return head >= marker


# ===========================================================================
#  设备
# ===========================================================================
class HdcError(RuntimeError):
    """hdc 命令失败（超时或非零退出）。

    为什么要单独抛：以前失败时只返回空串，于是
      * `app_alive` 会把「pidof 超时」当成「进程没了」→ 断言假通过；
      * 一次没发出去的点击，会让后面的 `unchanged` 断言假通过。
    命令失败必须当错误，不能当成「没变化」。
    """


class Hdc:
    """hdc 命令行封装（所有子进程都走 nowindow.run，带 CREATE_NO_WINDOW）。"""

    def __init__(self, device: str):
        self.device = device
        self._shot_no = 0
        # 上次唤醒屏幕的时刻（节流用，见 wake_screen）
        self._last_wake = 0.0

    def run(self, *args, timeout: int = 120, check: bool = False) -> str:
        """跑一条 hdc 命令，返回它的输出。

        check=True 时，**超时或非零退出都会抛 HdcError**；
        check=False 时只抛超时（非零退出算合法答案，例如 pidof 查无此进程）。
        """
        cmd = [HDC, "-t", self.device] + [str(a) for a in args]
        try:
            proc = run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise HdcError("hdc %s 超时（%ds）" % (" ".join(cmd[2:6]), timeout)) from exc
        out = proc.stdout or ""
        err = proc.stderr or ""
        if check and proc.returncode != 0:
            raise HdcError("hdc %s 退出码 %d：%s" % (
                " ".join(cmd[2:6]), proc.returncode, (out + err).strip()[:200]))
        return out + err

    def shell(self, *args, timeout: int = 120, check: bool = False) -> str:
        return self.run("shell", *args, timeout=timeout, check=check)

    def click(self, x: float, y: float) -> None:
        """点一下。点不出去要报错，不能悄悄当成「点了但没反应」。"""
        self.shell("uitest", "uiInput", "click", int(round(x)), int(round(y)),
                   timeout=60, check=True)

    def long_press(self, x: float, y: float, variant: tuple | None = None) -> None:
        """长按（用来插旗）。

        首选 **uitest uiInput longClick x y**（uitest 自带的长按命令，
        tools\\win_probe.py 的插旗就是用它）。

        备选是「极慢的 swipe」顶替：起终点只差几个像素、速度给得很低，
        设备就当成「按住不动」，触发的正是应用的 onLongPress。
        **但 swipe 的第 5 个参数不同设备解释不一样**（速度 px/s 还是时长 ms），
        解释错了这个手势就变成**单击**（真平板上实测过：格子被翻开、旗没插上）。

        所以 `variant` = (方式, 参数)，由调用方**在设备上试出来**，
        见 LONGPRESS_VARIANTS 与 Runner.calibrate_longpress。
        """
        xi = int(round(x))
        yi = int(round(y))
        kind, params = variant if variant else ("swipe", (1, 1))
        if kind == "longClick":
            self.shell("uitest", "uiInput", "longClick", xi, yi, timeout=60, check=True)
            return
        dx, arg = params
        self.shell("uitest", "uiInput", "swipe", xi, yi, xi + dx, yi, arg,
                   timeout=60, check=True)

    def screenshot(self, path: str) -> str:
        """截一张全屏图到本机 path（先删旧的，否则 file recv 会失败）。

        超时收紧到 40/60 秒（原来 120/180）：设备端 hdc 偶尔会变慢
        （实测 snapshot_display 从 0.5 s 劣化到 3.7 s），一个卡住的调用
        拖 3 分钟会让整轮跑测看起来像挂死。失败重试一次。
        """
        self._shot_no += 1
        remote = "/data/local/tmp/cm_shot_%d.jpeg" % self._shot_no
        last = None
        for attempt in range(2):
            try:
                self.shell("snapshot_display", "-f", remote, timeout=40, check=True)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                self.run("file", "recv", remote, path, timeout=60, check=True)
                return path
            except HdcError as exc:
                last = exc
                time.sleep(2.0)
        raise last if last else HdcError("截图失败")

    def hilog(self) -> str:
        return self.shell("hilog", "-x", timeout=60)

    def pidof(self) -> str:
        """应用进程的 PID 字符串（空 = 进程没了）。

        设备上 pidof 查无此进程时**退出码仍是 0、输出为空**；
        非零退出 = hdc/设备出问题了，那要当错误抛，不能当成「进程没了」。
        """
        return self.shell("pidof", BUNDLE, timeout=60, check=True).strip()

    def pidof_quiet(self) -> str:
        """查 PID，**查不到不算错**（有些设备上 pidof 查无此进程会退出码非 0）。"""
        try:
            out = self.shell("pidof", BUNDLE, timeout=30, check=False)
        except HdcError:
            return ""
        return (out or "").strip()

    def app_alive(self) -> bool:
        return self.pidof().strip() != ""

    def stop_app(self) -> None:
        """停掉应用，并且**等它真的死了**再返回。

        为什么必须等（2026-11-03 真平板 MRO-W00 实测）：
        `aa force-stop` 是**异步**的 —— 命令返回了，进程可能还活着一两秒。
        真机上紧接着 `aa start`，系统会把**还活着的那个实例**重新拉到前台，
        于是「重开一局」其实**没有重开**：上一局的棋盘、已经弹出来的
        「游戏失败」对话框原封不动地留着。实测就是这样：
        board.cell.04 这条用例的 base 帧和 cur 帧**一个像素都没差**，
        两个画面上都是那个失败框（docs/verify/CM_1430tabreal_FAIL_board_cell_04_step4_base.jpeg）
        —— 说明「游戏失败」框在用例点 (0,4) 之前就已经开着了，
        点哪儿都没反应（有对话框时应用只让点击穿过、不开格）。
        模拟器上进程死得快，所以一直没暴露这个坑。
        """
        self.shell("aa", "force-stop", BUNDLE, timeout=60, check=True)
        deadline = time.time() + 20.0
        while time.time() < deadline:
            if not self.pidof_quiet():
                return
            time.sleep(0.5)
        # 没死干净就别接着往下跑：后面每一条用例都会莫名其妙地失败
        raise HdcError("aa force-stop 之后应用进程还在（pidof=%s）" % self.pidof_quiet())

    def device_now_marker(self) -> str:
        """取设备当前时间，做成和 hilog 行一样格式的时间戳（当「本轮起点」）。

        hilog 是**环形缓冲**：跑久了旧行会被挤掉/留着。
        「取最后一条 `[Dialog] 打开 …`」会拿到**上一轮**留下的行，
        于是把明明赢了的一局判成失败（2026-11-03 踩过）。
        所以凡是「认这一轮的行」的地方，都得带上这个起点标记。

        两个坑（2026-11-03）：
        ① 不要取输出的**最后一行**。设备启动那一瞬间，hdc 的输出里会混进
           别的内容（实测混进过一行 hilog），取最后一行就取到了一个
           根本不是日期的字符串。这里**按格式找**第一行匹配的。
        ② 时间戳往前**挪 1 秒**。设备给的秒级时间戳，毫秒位只能补 .000，
           而日志行是 .xxx —— 同一秒内的日志会被判成「之前的」，
           于是刚启动的应用布局日志被误杀。
        """
        out = self.shell("date '+%m-%d %H:%M:%S'", timeout=60)
        m = re.search(r"(\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})", out or "")
        if not m:
            return ""
        mon, hh, mm, ss = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        # 往前挪 1 秒（时分秒进位）
        ss -= 1
        if ss < 0:
            ss, mm = 59, mm - 1
        if mm < 0:
            mm, hh = 59, hh - 1
        if hh < 0:
            hh = 23
        return "%s %02d:%02d:%02d.000" % (mon, hh, mm, ss)

    def wake_screen(self, force: bool = False) -> None:
        """把设备屏幕点亮（**不负责解锁**），并把息屏超时拉到 2 小时。

        为什么必须有（2026-11-04 真平板实测）：
        平板的**熄屏超时是 10 分钟**（`hidumper -s PowerManagerService` 里
        `ScreenOffTime: Timeout=600000ms`）。一轮 86 条要跑一个多小时，
        中间没人碰它，屏幕就灭了 —— 这时候 `aa start` 会**静默失败**
        （屏幕关着时起应用不行），于是工具等 45 秒等布局日志，等到超时，
        报「hilog 里没有布局日志」，看着像布局日志的 bug，其实是**设备睡着了**。
        （2026-11-04 那轮真平板 86 条里的唯一一条失败 `dialogs.win.exit`，
        以及单独跑 `click_mkstate.py` 造失败局面时的失败，都是这个原因。）

        **单位是毫秒**：`power-shell timeout -o 7200` 实测只保了 7.2 秒
        （设备照样很快睡过去），要 2 小时得填 `7200000`。

        **点亮 ≠ 解锁**：设备从休眠唤醒后会弹**锁屏（keyguard）**，
        `aa start` 照样报 `Error Code:10106102 The device screen is locked`。
        解锁只能由用户手动做（开发者模式下自动解锁会被拒），
        这里只负责把「屏幕灭了/设备睡着了」这个状态排除掉。

        `force=False` 时按**节流**调用（2 分钟内不重复唤醒），
        跑长测时可以随手调用，不会刷屏。
        """
        now = time.time()
        if not force and (now - self._last_wake) < 120.0:
            return
        self._last_wake = now
        try:
            self.shell("power-shell", "wakeup", timeout=30, check=False)
            self.shell("power-shell", "timeout", "-o", "7200000", timeout=30, check=False)
        except HdcError:
            pass

    def start_app(self) -> str:
        """起应用，返回命令输出。

        返回输出是给**前置检查**用的：`aa start` 对没装的 ability
        也是退出码 0，只有输出里带错误（见 preflight）。

        起来之前先把屏幕点亮（见 wake_screen 的说明：屏幕灭着的时候
        `aa start` 会静默失败，后面表现为「hilog 里没有布局日志」）。
        """
        self.wake_screen()
        out = self.shell("aa", "start", "-a", "EntryAbility", "-b", BUNDLE,
                         timeout=90, check=True)
        # `aa start` 出错时**退出码仍然是 0**，错误只在输出里
        # （实测：屏幕锁着时输出 `Error Code:10106102 The device screen is locked
        # during the application launch, unlock screen failed.`）。
        # 不检查的话，这次失败会一路伪装成「hilog 里没有布局日志」。
        if out and "Error" in out:
            raise HdcError("aa start 失败：" + out.strip()[:200]
                           + "（屏幕锁着时要用户手动解锁；`power-shell wakeup` 只能点亮）")
        time.sleep(3.0)
        return out


# ===========================================================================
#  几何
# ===========================================================================
class Layout:
    """一条布局日志解析出来的结果。"""

    def __init__(self, raw: str):
        self.raw = raw
        m = LAYOUT_RE.search(raw)
        if m is None:
            raise ValueError("布局日志解析失败: " + raw[:200])
        self.canvas_w = int(m.group(1))
        self.canvas_h = int(m.group(2))
        self.px_scale = float(m.group(3))
        self.fit = int(m.group(4))
        self.cur_fit = int(m.group(5))
        self.unit = int(m.group(6))
        self.tile = int(m.group(7))
        self.board_x = int(m.group(8))
        self.board_y = int(m.group(9))
        ms = STRIP_RE.search(raw)
        self.strip_top = int(ms.group(1)) if ms else None
        mb = BOARD_RE.search(raw)
        # 盘面规格是**设备无关**的（格边/原点会随画布尺寸变），用例断言盘面时用它
        self.rows = int(mb.group(1)) if mb else None
        self.cols = int(mb.group(2)) if mb else None
        self.mines = int(mb.group(3)) if mb else None

    @property
    def density(self) -> float:
        return 1.0 / self.px_scale

    def key(self) -> tuple:
        return (self.canvas_w, self.canvas_h, self.px_scale, self.tile,
                self.board_x, self.board_y)

    def __str__(self) -> str:
        return ("画布=%dx%d 密度=%.4f 格边=%d 棋盘原点=(%d,%d)"
                % (self.canvas_w, self.canvas_h, self.density, self.tile,
                   self.board_x, self.board_y))


class Geom:
    """坐标换算。所有公式照抄 GameController.ets。"""

    def __init__(self, hdc: Hdc, workdir: str):
        self.hdc = hdc
        self.workdir = workdir
        self.layout: Layout | None = None
        self.canvas_y: int | None = None      # 画布顶在屏幕上的纵向偏移
        self._log_lines: list[str] = []
        #: 最近的截图尺寸（宽, 高）——用来判断一条布局日志是不是**另一个方向**的旧行
        self.screen_size: tuple[int, int] | None = None

    # ---- 日志 -------------------------------------------------------------
    def read_log(self) -> list[str]:
        raw = self.hdc.hilog()
        self._log_lines = raw.splitlines()
        return self._log_lines

    def layout_fits_screen(self, lay: Layout) -> bool:
        """这条布局日志描述的画布**放得进当前屏幕**吗？

        为什么要有（2026-11-03 真平板实测）：
        应用只在**画布尺寸变化**时打一条布局日志（GameController.ets:328），
        所以「最后一条布局日志」可能是**上一个实例**、甚至**另一个方向**的。
        横屏那台平板早上的布局是 2800x1690，下午转成竖屏后画布是 1840x2650 ——
        拿到旧行就等于按**另一个方向的画布**算坐标，点哪儿都是错的。

        判据：**画布比屏幕还大，就不可能是当前这一屏的布局**。
        画布一般比屏幕略小（系统状态栏/导航栏），所以用「不超过屏幕」来卡。
        截图尺寸还不知道时（第一次读布局）一律放行 —— 那时还没有可比对的基准。
        """
        if self.screen_size is None:
            return True
        sw, sh = self.screen_size
        return lay.canvas_w <= sw + 2 and lay.canvas_h <= sh + 2

    def refresh_layout(self, retries: int = 24, gap_s: float = 2.0,
                       marker: str | None = None,
                       allow_cached: bool = True) -> Layout:
        """从 hilog 里取**最后一条**布局日志。

        重试几遍：应用刚起来时布局日志可能还没写进 hilog 缓冲区
        （缓冲区也会被刷掉），一次读不到就报「hilog 里没有布局日志」——
        那是**设备状态**问题，不是被测代码的问题（2026-11-01 下午实测到一次）。
        真机比模拟器慢得多（2026-11-01 晚实测：Pura X Max 上 8 次×1.5 秒不够，
        会偶发「第 1 步 reset 执行异常: hilog 里没有布局日志」），所以重试给到
        24 次×2 秒 ≈ 48 秒。

        `marker` = 「只认这个时刻之后的日志行」。**重开应用时必须有**。
        hilog 是环形缓冲，里面可能还留着**上一轮**的布局日志；
        不看时间的话，应用这次压根没画出来，前置检查也会说「正常」，
        然后整套用例在一个没起来的应用上白跑。
        （Codex 对抗性复审 2026-11-03 的 P2）

        `allow_cached` = 实在找不到新行时，**退回上一次记住的布局**。
        为什么需要（2026-11-03 真平板实测）：
        应用**只在画布尺寸变化时**才打布局日志，所以「造完一局失败局面」之后
        再去要布局，真机上那条日志早就被环形缓冲挤掉了（或被前一次
        `hilog -x` 清掉了），于是报「hilog 里没有布局日志」——
        其实布局**根本没变**，手上那份还是对的。
        退路之前会先用 `layout_fits_screen()` 验一遍尺寸还对不对得上。
        """
        last_err = ""
        for _ in range(max(1, retries)):
            lines = self.read_log()
            last = None
            for ln in lines:
                if "[GameController] 布局" not in ln:
                    continue
                if marker and not log_line_after(ln, marker):
                    continue        # 上一轮留下的旧行，不要
                last = ln
            if last is not None:
                try:
                    lay = Layout(last)
                except ValueError as exc:
                    last_err = str(exc)
                    lay = None
                if lay is not None:
                    if self.layout_fits_screen(lay):
                        self.layout = lay
                        return lay
                    # 画布比屏幕还大 → 这是**另一个方向/上一次**的旧行，继续等
                    last_err = ("拿到的布局行画布 %dx%d 比屏幕 %s 还大，"
                                "不是当前这一屏的（多半是另一个方向的旧行）"
                                % (lay.canvas_w, lay.canvas_h, self.screen_size))
            time.sleep(gap_s)
        # 退路：用上一次记住的布局（先验尺寸还对不对）
        if allow_cached and self.layout is not None and self.layout_fits_screen(self.layout):
            return self.layout
        raise RuntimeError("hilog 里没有布局日志" + (("：" + last_err) if last_err else "")
                           + "（设备屏幕灭着会让 `aa start` 静默失败，"
                             "工具已经会先 `power-shell wakeup` 点亮；"
                             "如果还是这样，多半是屏幕**锁**着，要手动解锁）")

    # ---- 画布顶偏移 -------------------------------------------------------
    def probe_canvas_y(self, retries: int = 3) -> int:
        """量画布顶在屏幕上的纵向偏移（未开局的棋盘第一行砖色上沿 - 棋盘原点 y）。

        砖色判定用本文件的 `is_tile`（蓝盘 + 绿盘都认），**不要**去 import
        `probe_canvas.is_tile` —— 那个只认蓝色，遇到「绿色棋盘」外观会量不到。

        坑（2026-11-01，lead 在 Mate X7 上做跨设备校验时踩到）：发牌动画是**从右下角往
        左上报**的（`DealIn.dealInSequence` 的种子在中间偏右下），所以动画期间**左上角
        那一块还没翻上来**，这时候量到的「第一行砖色上沿」是错的 —— 实测量到 239 而真值
        是 125，整套用例的点击全部偏移 114 px。
        所以：量之前必须等发牌结束（`act_reset` 里先等稳定），这里再叠一层重试。
        """
        lay = self.layout
        if lay is None:
            raise RuntimeError("还没有布局信息")
        path = os.path.join(self.workdir, "probe_canvas.jpeg")
        last_err = ""
        for attempt in range(max(1, retries)):
            self.hdc.screenshot(path)
            im = Image.open(path).convert("RGB")
            w, h = im.size
            px = im.load()
            x = max(0, min(w - 1, lay.board_x + lay.tile // 2))
            need = max(8, min(40, lay.tile // 4))
            run_len = 0
            for y in range(h):
                r, g, b = px[x, y]
                if is_tile(r, g, b):
                    run_len += 1
                    if run_len >= need:
                        top = y - run_len + 1
                        self.canvas_y = int(top - lay.board_y)
                        return self.canvas_y
                else:
                    run_len = 0
            last_err = ("在 x=%d 那一列找不到连续 %d 行砖块（棋盘可能被翻开了？"
                        "或者发牌动画还没结束）" % (x, need))
            time.sleep(0.8)
        raise RuntimeError("量不到画布顶偏移：" + last_err)

    # ---- 对话框 -----------------------------------------------------------
    def dialog_scale(self, ref_w: int, ref_h: int) -> float:
        lay = self.layout
        s = max(0.5, min(2.0, lay.density,
                         (lay.canvas_w - 32) / ref_w,
                         (lay.canvas_h - 32) / ref_h))
        return s

    def dialog_origin(self, ref_w: int, ref_h: int) -> tuple[int, int]:
        lay = self.layout
        s = self.dialog_scale(ref_w, ref_h)
        ox = int(round((lay.canvas_w - ref_w * s) / 2))
        oy = 0 if ref_h * s > lay.canvas_h else int(round((lay.canvas_h - ref_h * s) / 2))
        return ox, oy

    # ---- 自定义框 ---------------------------------------------------------
    def custom_scale(self) -> float:
        lay = self.layout
        s = max(0.5, min(2.0, lay.density,
                         (lay.canvas_w - 32) / (CUSTOM_DLG_W + CUSTOM_GAP + KEYPAD_W),
                         (lay.canvas_h - 32) / max(CUSTOM_DLG_H, KEYPAD_H)))
        return s

    def custom_origin(self) -> tuple[int, int]:
        lay = self.layout
        s = self.custom_scale()
        total_w = CUSTOM_DLG_W * s + CUSTOM_GAP * s + KEYPAD_W * s
        total_h = max(CUSTOM_DLG_H * s, KEYPAD_H * s)
        ox = int(round((lay.canvas_w - total_w) / 2))
        oy = 0 if total_h > lay.canvas_h else int(round((lay.canvas_h - total_h) / 2))
        return ox, oy

    # ---- 坐标换算 ---------------------------------------------------------
    def to_screen(self, space: str, x: float, y: float,
                  dialog: str | None = None, cell: list | None = None) -> tuple[int, int]:
        """把某个坐标系里的点换算成屏幕像素。"""
        lay = self.layout
        if lay is None:
            raise RuntimeError("还没有布局信息")
        cy = self.canvas_y or 0
        if space == "screen":
            return int(round(x)), int(round(y))
        if space == "canvas":
            # 画布**设备像素**
            return int(round(x)), int(round(y)) + cy
        if space == "canvas_frac":
            # 画布**比例坐标**（0..1）：与画布实际尺寸无关。
            #
            # 为什么需要它（2026-11-03 平板四域回归）：
            # 「点统计窗口外面关窗」那条用例原来写的是 canvas 像素 (640, 2000)。
            # 那个点在 Mate X7（画布 2210x2208）上确实在画布内的空白处，
            # 可平板的画布只有 2800x**1690**（顶部 150 px 是系统状态栏）——
            # y=2000 直接点到画布外面去了，点名不副实，窗口自然关不掉。
            # 写死画布像素的坐标**换个设备就废**，比例坐标不会。
            if lay is None:
                raise RuntimeError("还没有布局信息")
            return (int(round(lay.canvas_w * x)),
                    int(round(lay.canvas_h * y)) + cy)
        if space == "menu":
            # 菜单栏的**画布 vp**
            return (int(round(x / lay.px_scale)),
                    cy + int(round(y / lay.px_scale)))
        if space == "board":
            if cell is None:
                raise ValueError("board 空间必须给 cell")
            r, c = int(cell[0]), int(cell[1])
            bx = lay.board_x + c * lay.tile + lay.tile / 2.0
            by = lay.board_y + r * lay.tile + lay.tile / 2.0
            return int(round(bx)), int(round(by)) + cy
        if space == "outside_stats":
            # 统计窗**外面**的一个点（设备无关）。
            #
            # 必须**按窗的实际边界**挑点，不能假设「菜单栏和棋盘之间的空隙」
            # 一定在窗外 —— Codex 对抗性复审 2026-11-03 的 P2 给的反例：
            # 画布 1280x484、密度 3.5 时，缩放后的统计窗占 x=16..1264、y=16..468
            # （几乎占满整屏），而「棋盘上方的空隙」算出来是 (26, 80) ——
            # **正好落在窗内**，于是「点窗外关窗」那条用例又挂了。
            #
            # 窗是居中的，所以窗外只可能在它的左/右/上/下；
            # 按「左 → 右 → 上 → 下」的顺序挑第一个够得着的位置。
            lay = self.layout
            ref_w, ref_h = DIALOG_REF["stats"]
            s = self.dialog_scale(ref_w, ref_h)
            ox, oy = self.dialog_origin(ref_w, ref_h)
            dw, dh = ref_w * s, ref_h * s
            menu_px = 21.0 / lay.px_scale          # MENU_BAR_H = 21 vp
            cands = []
            if ox - 8 >= 4:
                cands.append((ox - 8, oy + dh / 2.0))                  # 左侧留白
            if ox + dw + 8 <= lay.canvas_w - 4:
                cands.append((ox + dw + 8, oy + dh / 2.0))              # 右侧留白
            if oy - 8 >= menu_px + 4:
                cands.append((ox + dw / 2.0, oy - 8))                   # 上方
            if oy + dh + 8 <= lay.canvas_h - 4:
                cands.append((ox + dw / 2.0, oy + dh + 8))              # 下方
            if not cands:
                raise RuntimeError(
                    "画布 %dx%d 太窄，统计窗外没有可点的位置（窗 %dx%d）"
                    % (lay.canvas_w, lay.canvas_h, dw, dh))
            fx, fy = cands[0]
            return int(round(fx)), int(round(fy)) + cy
        if space == "dialog":
            name = dialog
            if name is None:
                raise ValueError("dialog 空间必须给 dialog 名字")
            ref_w, ref_h = DIALOG_REF[name]
            ox, oy = self.dialog_origin(ref_w, ref_h)
            s = self.dialog_scale(ref_w, ref_h)
            return int(round(ox + x * s)), int(round(oy + y * s)) + cy
        if space == "custom":
            ox, oy = self.custom_origin()
            s = self.custom_scale()
            return int(round(ox + x * s)), int(round(oy + y * s)) + cy
        if space == "keypad":
            ox, oy = self.custom_origin()
            s = self.custom_scale()
            kx = ox + (CUSTOM_DLG_W + CUSTOM_GAP) * s
            return int(round(kx + x * s)), int(round(oy + y * s)) + cy
        raise ValueError("未知坐标系: " + space)

    def region_to_screen(self, region: dict) -> tuple[int, int, int, int]:
        """把 region 描述换算成屏幕像素矩形 (x, y, w, h)。"""
        space = region.get("space", "screen")
        lay = self.layout
        cy = self.canvas_y or 0
        if space == "board":
            # board 空间：cell 定位，w/h 的单位是**格**
            cell = region.get("cell")
            if cell is None:
                raise ValueError("board 区域必须给 cell")
            r, c = int(cell[0]), int(cell[1])
            x0 = lay.board_x + c * lay.tile
            y0 = lay.board_y + r * lay.tile
            w = int(region.get("w", 1)) * lay.tile
            h = int(region.get("h", 1)) * lay.tile
            return int(x0), int(y0) + cy, w, h
        # 其余空间：w/h 的单位跟该空间的坐标单位一致
        #   screen / canvas = 设备像素（不缩放）
        #   menu            = 画布 vp（→ 设备像素要除 pxScale）
        #   dialog/custom/keypad = 参考像素（→ 设备像素要乘缩放 s）
        if space == "dialog":
            name = region.get("dialog")
            if name is None:
                raise ValueError("dialog 区域必须给 dialog 名字")
            ref_w, ref_h = DIALOG_REF[name]
            s = self.dialog_scale(ref_w, ref_h)
        elif space in ("custom", "keypad"):
            s = self.custom_scale()
        elif space == "menu":
            s = 1.0 / lay.px_scale
        elif space == "canvas_frac":
            # 比例坐标：x/y/w/h 都是画布的 0..1，w/h 要乘画布实际尺寸
            s = 1.0
            x, y = self.to_screen(space, region.get("x", 0), region.get("y", 0),
                                   dialog=region.get("dialog"), cell=region.get("cell"))
            w = int(round(lay.canvas_w * int(region.get("w", 0))))
            h = int(round(lay.canvas_h * int(region.get("h", 0))))
            return x, y, w, h
        else:
            s = 1.0
        x, y = self.to_screen(space, region.get("x", 0), region.get("y", 0),
                               dialog=region.get("dialog"), cell=region.get("cell"))
        w = int(round(int(region.get("w", 0)) * s))
        h = int(round(int(region.get("h", 0)) * s))
        return x, y, w, h


# ===========================================================================
#  像素工具
# ===========================================================================
def load_rgb(path: str):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.int16)


def diff_count(a, b, rect) -> int:
    """矩形区域内「明显不同」的像素数（每通道差 > 12 算不同）。"""
    x, y, w, h = rect
    if w <= 0 or h <= 0:
        return 0
    ha, hb = a.shape[0], b.shape[0]
    x2 = min(x + w, a.shape[1], hb and b.shape[1] or a.shape[1])
    y2 = min(y + h, ha, b.shape[0])
    if x2 <= x or y2 <= y:
        return 0
    ra = a[y:y2, x:x2]
    rb = b[y:y2, x:x2]
    d = np.max(np.abs(ra - rb), axis=2)
    return int((d > 12).sum())


def is_tile(r: int, g: int, b: int) -> bool:
    """未翻开的砖块：**蓝盘**（b 明显高于 r）或**绿盘**（饱和的绿）。

    坑（2026-11-01，lead 在 Mate X7 上做跨设备校验时踩到）：原实现只认蓝色。
    而棋盘样式是**用户偏好**、存在 preferences 里、跨重启保留（`Appearance.ets` 的
    「绿色棋盘」）。设备上只要留着绿盘，画布顶偏移就量不到、`cell_opened` 恒为真，
    整套用例全红 —— 而且与被测代码无关，是跑测器自己的口径太窄。

    绿盘的口径是照**实测像素**定的（Mate X7 的绿棋盘，列 x=board_x+tile/2 上逐行量过）：
      未翻开的砖块 ≈ (107,207,108) / (117,213,106) / (73,179,81) / (69,141,60)
        —— 饱和的绿，**g 比 r、b 都高出 70~100**；
      翻开后的地板 ≈ (185,227,186) / (190,232,191)
        —— 淡绿，g 很高但接近白，**g 只比 r、b 高 41**。
    所以判据取「g - max(r,b) > 60」：砖块 70~100 判真、地板 41 判假，两边都留了余量。
    （中途试过「g < 205」那种亮度判据，**不行**：砖块面本身 g≈207、地板 g≈227，
      亮度上分不开；而砖块顶上的高光斜面 g≈213 又会让「整块连续 40 行」的探测断掉。）
    """
    if b > 110 and (b - r) > 45:
        return True
    if g > 100 and (g - max(r, b)) > 60:
        return True
    return False


def cell_opened(img, lay: Layout, r: int, c: int, canvas_y: int = 0) -> bool:
    """这一格是不是已经翻开了（中心区域不是砖块蓝）。

    注意：棋盘原点在**画布**坐标里，图是**屏幕**截图，所以 y 要加画布顶偏移。
    """
    x0 = lay.board_x + c * lay.tile
    y0 = lay.board_y + r * lay.tile + canvas_y
    t = lay.tile
    # 取中心 50% 区域，数一下还剩多少砖块蓝
    m = max(1, t // 4)
    xs = range(x0 + m, x0 + t - m)
    ys = range(y0 + m, y0 + t - m)
    total = 0
    tile_px = 0
    for y in ys:
        for x in xs:
            if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                r0, g0, b0 = int(img[y][x][0]), int(img[y][x][1]), int(img[y][x][2])
                total += 1
                if is_tile(r0, g0, b0):
                    tile_px += 1
    if total == 0:
        return False
    return (tile_px / total) < 0.5


def cell_state(img, lay: Layout, r: int, c: int, canvas_y: int = 0) -> str:
    """这一格现在是什么状态。

    返回：
      * ``closed`` —— 还是没翻开的砖
      * ``flag``   —— 插了旗（旗是**红色**的，砖是蓝/绿、数字是蓝/绿/黑）
      * ``opened`` —— 其它（翻开的空白、数字、雷、被对话框盖住…）
      * ``unknown`` —— 这一格在截图里取不到（越界）

    为什么要有（2026-11-03 真平板实测）：
    长按在真平板上**被当成了单击**，格子被翻开而不是插上旗。
    光看「计数器有没有变」只能知道结果不对，看不出**错在哪一步**；
    有了这一格的状态，才能分辨：
      * 格子还是砖   → 手势压根没送到（换一种手势再试）
      * 格子插上了旗 → 手势对了
      * 格子被翻开了 → 手势被当成了单击（**这一局已经脏了**，必须报错退出）
    """
    x0 = lay.board_x + c * lay.tile
    y0 = lay.board_y + r * lay.tile + canvas_y
    t = lay.tile
    m = max(1, t // 4)
    xs0, xs1 = max(0, x0 + m), min(img.shape[1], x0 + t - m)
    ys0, ys1 = max(0, y0 + m), min(img.shape[0], y0 + t - m)
    if xs1 <= xs0 or ys1 <= ys0:
        return "unknown"
    blk = img[ys0:ys1, xs0:xs1].astype(int)
    R = blk[:, :, 0]
    G = blk[:, :, 1]
    B = blk[:, :, 2]
    total = blk.shape[0] * blk.shape[1]
    # 旗是红色的（blueSheet 里 RECT_FLAG 区域均色约 (197,128,143)，最红处 255）
    red = int(((R > 140) & (R > G + 55) & (R > B + 55)).sum())
    if red >= max(3, total // 60):
        return "flag"
    tile = int((((B > 110) & (B - R > 45)) |
                ((G > 100) & (G - np.maximum(R, B) > 60))).sum())
    if tile / float(total) >= 0.5:
        return "closed"
    return "opened"


# ===========================================================================
#  跑测器
# ===========================================================================
class CaseResult:
    def __init__(self, cid: str, desc: str, domain: str):
        self.cid = cid
        self.desc = desc
        self.domain = domain
        self.ok = True
        self.messages: list[str] = []
        self.shots: list[str] = []

    def fail(self, msg: str) -> None:
        self.ok = False
        self.messages.append("失败：" + msg)


class Runner:
    def __init__(self, device: str, tag: str, verbose: bool):
        self.hdc = Hdc(device)
        self.tag = tag
        self.verbose = verbose
        # 临时目录**按设备+tag 分开**：两个跑测器进程同时跑（模拟器一台、真机一台）
        # 会共用同一个目录，其中一个清目录就把另一个的 stable.jpeg 弄没了，
        # 报成「[Errno 2] No such file or directory: ...\click_matrix_run\stable.jpeg」
        # —— 看起来像用例失败，其实是两个进程互相踩（2026-11-01 晚踩到）。
        safe_dev = "".join(c if (c.isalnum() or c in "-_") else "_" for c in device)
        self.workdir = os.path.join(os.environ.get("TEMP", "."),
                                    "click_matrix_run_%s_%s" % (safe_dev, tag))
        os.makedirs(self.workdir, exist_ok=True)
        os.makedirs(VERIFY_DIR, exist_ok=True)
        self.geom = Geom(self.hdc, self.workdir)
        self.seen_log: set[str] = set()
        self.checkpoint = None            # 基准：上一个**动作**之前的画面（numpy 数组）
        self.hold = None                  # 参照：hold 动作存下来的画面
        self.before = None                # 最后一个改动动作之前的画面（cell_opened 用）
        self.img = None                   # 最近一次抓的画面
        self.dirty = True                 # 画面是否已过期
        self.last_layout: Layout | None = None
        self.shot_seq = 0
        #: 校准出来的长按手势 (位移, 第5参数)；None = 这台设备上还没校准 / 校准失败
        self.longpress_variant: tuple | None = None

    # ---- 画面 -------------------------------------------------------------
    def capture(self, path: str | None = None) -> str:
        if self.dirty or path is not None:
            p = path or os.path.join(self.workdir, "cur.jpeg")
            self.hdc.screenshot(p)
            self.img = load_rgb(p)
            self.dirty = False
            # 记下屏幕尺寸：后面判断「一条布局日志是不是另一个方向的旧行」要用
            self.geom.screen_size = (self.img.shape[1], self.img.shape[0])
        return ""

    def current(self):
        self.capture()
        return self.img

    def save_shot(self, name: str) -> str:
        self.shot_seq += 1
        fn = "CM_%s%s.jpeg" % (self.tag + "_" if self.tag else "", name)
        path = os.path.join(VERIFY_DIR, fn)
        self.capture(path)
        return fn

    # ---- 日志 -------------------------------------------------------------
    def log_new_lines(self) -> list[str]:
        raw = self.hdc.hilog()
        lines = raw.splitlines()
        new = [ln for ln in lines if ln not in self.seen_log]
        self.seen_log.update(lines)
        return new

    def mark_log_seen(self) -> None:
        """把当前缓冲区里已有的行都算成「已见过」（跑测开始时调一次）。"""
        self.seen_log.update(self.hdc.hilog().splitlines())

    # ---- 前置检查（2026-11-03 新增）----------------------------------------
    def preflight(self) -> tuple[bool, str]:
        """
        开跑前验三件事：应用**装上了没有**、**能不能起来**、起来后**有没有布局日志**。

        为什么要有（2026-11-03）：
        那一轮 86 条用例全死在第 1 步「hilog 里没有布局日志」，根因是
        **应用根本没装在模拟器上**。同样的报错会让每一条用例都失败，
        白白烧一个多小时，最后才看得出是环境问题。
        这里把它提到最前面，几秒钟就知道。
        """
        # 1) 装没装
        #
        # 坑（2026-11-03，Codex 对抗性复审 P2）：
        # 原来用 `ls /data/app/el1/bundle/public/<bundle>` 判断。
        # 那个办法**不可靠**：`hdc shell ls` 对不存在的路径也是**退出码 0**，
        # 只是输出里带着「No such file or directory」；对**存在**的路径，
        # 设备上还可能回「Permission denied」（目录不可读）。
        # 两种情况输出都非空，于是「输出为空 = 没装」这个判据**永远不成立**，
        # 前置检查形同虚设 —— 这正是它当初该抓的那一类失败。
        #
        # 现在用 `bm dump -n <bundle>`：包不存在时它明确回
        # 「error: failed to get information and the parameters may be wrong.」
        probe = self.hdc.shell("bm", "dump", "-n", BUNDLE, timeout=90, check=False)
        low = (probe or "").strip().lower()
        if not low or "error" in low or "failed to get information" in low:
            return False, ("设备 %s 上没装 %s（bm dump 说：%s）"
                           % (self.hdc.device, BUNDLE,
                              (probe or "").strip()[:160] or "没有输出"))
        # 2) 起不起来
        #
        # `aa start` 对**没装的** ability 也是**退出码 0**（只是输出里带错误），
        # 所以光靠异常抓不住 —— 要看输出内容。
        #
        # 关键：**先记下时间戳**。hilog 是环形缓冲，里面可能还留着**上一轮**
        # 的布局日志；第 3 步去捞日志时要是把那条旧行当成了这次的，
        # 应用其实没画出来，前置检查也会说「正常」，然后整套用例在
        # 一个没起来的应用上白跑一个小时。
        # （Codex 对抗性复审 2026-11-03 的 P2）
        marker = self.hdc.device_now_marker()
        try:
            self.hdc.stop_app()
            out = self.hdc.start_app()
        except Exception as exc:
            return False, "应用起不来：%s" % exc
        low = (out or "").strip().lower()
        if low and ("error" in low or "not exist" in low or "not found" in low
                    or "not installed" in low or "ability not" in low):
            return False, ("应用起不来（aa start 说：%s）" % (out or "").strip()[:160])
        # 3) 起来之后有没有布局日志（**必须是这一次启动之后**的）
        try:
            self.geom.refresh_layout(retries=30, gap_s=1.5, marker=marker)
        except Exception as exc:
            return False, ("应用起来了但拿不到布局日志：%s\n"
                           "   （装了但没画界面，或者装的不是最新那版）" % exc)
        lay = self.geom.layout
        # 4) 校准长按手势（要一块**空白**棋盘：等画面稳定、量出画布顶偏移）
        #
        # 为什么放在这里：长按在真平板上被当成了单击（见 calibrate_longpress），
        # 插旗类用例全废。哪种手势能用**只能在设备上试**，而且要**用画面验证**。
        # 校准用的这块棋盘是一次性的：每条用例开头都会 reset。
        try:
            self.geom.canvas_y = None
            self.wait_board_stable(timeout_ms=20000)
            if self.geom.canvas_y is None:
                try:
                    self.geom.probe_canvas_y()
                except Exception:
                    pass
            if self.geom.canvas_y is None:
                self.geom.canvas_y = self.canvas_top_from_shot()
            self.poke()
            self.wait_board_stable(timeout_ms=20000)
            self.longpress_variant = self.calibrate_longpress()
        except Exception as exc:
            self.longpress_variant = None
            print("   [preflight] 长按手势校准没跑成：%s" % exc)
        lp = self.longpress_variant
        # 长按手势的标法有两种：
        #   ("longClick", None)          -> uitest 自带的长按命令
        #   ("swipe", (位移px, 时长/速度)) -> swipe 变通写法
        # 两种的第一个字段都是**字符串**，不能按 %d 格式化
        # （2026-11-03 实测踩到：这里原本写的是 "%dpx/%s"，
        #   校准出的是 ('swipe', (1, 1))，于是 preflight 直接 TypeError 崩掉）。
        if lp is None:
            lp_txt = "**没校准出来（插旗类用例跑不了）**"
        elif lp[0] == "longClick":
            lp_txt = "longClick"
        else:
            lp_txt = "swipe %dpx/%s" % (lp[1][0], lp[1][1])
        sw = self.geom.screen_size
        return True, ("应用已装、已启动，布局正常：画布 %dx%d px，适配档 n=%d，格边 %d px；"
                      "屏幕 %s；长按手势 %s"
                      % (lay.canvas_w, lay.canvas_h, lay.fit, lay.tile,
                         ("%dx%d" % sw) if sw else "未知", lp_txt))

    # ---- 动作 -------------------------------------------------------------
    def _launch_fresh_app(self) -> None:
        """真正重开一局：停应用（**等进程真死**）→ 起应用 →
        **只认本次启动之后的布局日志** → 量画布顶偏移 → 戳醒应用 → 等画面稳定。

        少了任何一步都会在真机上出错（2026-11-03 真平板 MRO-W00 实测）：
        旧实例没被杀掉 → 上一局的失败对话框还开着 → 后面那条用例点哪儿都没反应。

        「画布顶偏移」**每次都重量**：设备转屏 / 折叠屏展开之后，
        上一次量的偏移就是错的了（2026-11-03 真平板：上午横屏、下午竖屏，
        画布从 2800x1690 变成 1840x2650）。
        """
        marker = self.hdc.device_now_marker()
        self.hdc.stop_app()
        self.hdc.start_app()
        self.geom.refresh_layout(retries=40, gap_s=1.5, marker=marker)
        # 顺序要紧：**等画面稳定（发牌动画结束）→ 量画布顶偏移 → 戳醒应用 → 再等稳定**。
        #
        # 坑（2026-11-01 晚，四个外观用例稳定复现 19859 px 的差异才查出来）：
        # 模拟器窗口被别的窗口盖住时，应用会**完全冻结** —— 界面不重绘、
        # setInterval 也不跑（连状态条上的秒数都不跳）。这时候截到的图是
        # 「冻结前那一帧」，跑测器把它当基准帧；等后面任何一次点击把应用唤醒、
        # 待办的发牌动画补完，棋盘的砖块就弹起来了 —— 「棋盘没变」的断言必然失败，
        # 而且每次失败的像素数一模一样（19859）。这不是被测代码的毛病。
        #
        # 唤醒办法：戳一下。戳**菜单栏最右边的空白**（菜单项都在左边）——
        # 应用被唤醒、开始渲染、把发牌动画跑完，而棋盘/状态条一个像素都不变。
        self.geom.canvas_y = None
        self.wait_board_stable()
        if self.geom.canvas_y is None:
            try:
                self.geom.probe_canvas_y()
            except Exception as exc:
                print("   [reset] 量画布顶偏移失败（%s），改用截图量" % exc)
        if self.geom.canvas_y is None:
            # 退路：从截图里量（系统状态栏是黑的，画布是浅色的）。
            # 这时候应用**一定已经画过界面**了（上面 refresh_layout 带 marker，
            # 拿到的是本次启动之后的布局行），所以量到的确实是应用窗口。
            self.geom.canvas_y = self.canvas_top_from_shot()
        if self.geom.canvas_y is None:
            raise RuntimeError("量不到画布顶偏移")
        self.poke()
        self.wait_board_stable()

    def act_reset(self, step: dict) -> None:
        diff = step.get("difficulty")
        # 「重开」要真的重开：起完还得**看一眼画面**确认这一局是全新的。
        for attempt in range(1, 4):
            self._launch_fresh_app()
            if self.verify_fresh_board():
                break
            print("   [reset] 第 %d 遍重开之后棋盘不是全新的（多半是旧实例没被杀干净），"
                  "再重开一遍" % attempt)
        else:
            raise RuntimeError("重开应用之后棋盘始终不是全新的"
                               "（旧实例没被杀掉，或应用没有正常启动）")
        if diff:
            name = {"beginner": "初级", "intermediate": "中级",
                    "expert": "高级"}.get(diff)
            if name is None:
                raise ValueError("未知难度: " + str(diff))
            self.act_menu({"top": "game", "entry": name})
            self.geom.refresh_layout()
        self.dirty = True
        self.capture()
        self.checkpoint = self.img.copy() if self.img is not None else None
        self.before = None
        self.last_layout = self.geom.layout

    def verify_fresh_board(self) -> bool:
        """这一局是不是**全新的**：每一格都还是砖，没有翻开的格子、没有插着旗，
        也没有对话框盖在上面。

        为什么要有（2026-11-03 真平板 MRO-W00 实测）：
        那台平板上 `aa force-stop` 之后进程没立刻死，`aa start` 又把**还活着的
        旧实例**拉回前台 —— 「reset」于是根本没有重开：上一局输掉的棋盘和
        「游戏失败」对话框原封不动地留着。实测证据：
        board.cell.04 的 base 帧与 cur 帧**一个像素都没差**，两个画面上都是
        那个失败框（docs/verify\\CM_1430tabreal_FAIL_board_cell_04_step4_base.jpeg），
        说明框在用例点 (0,4) **之前**就已经开着 —— 有对话框时应用只让点击穿过、
        不开格，于是那条用例必然失败。

        所以「重开」不能只看命令返回，**得看一眼画面**。
        """
        lay = self.geom.layout
        if lay is None:
            return False
        # **必须重新截一张**：current() 只在 self.dirty 为真时才重截，
        # 而 _launch_fresh_app 刚把应用重启过、没人把 dirty 置真 ——
        # 于是这里拿到的是**重启之前那一帧**的旧图，拿旧图判「棋盘是不是全新的」
        # 当然是「不是」，于是每条用例都在第 1 步 reset 上失败
        # （2026-11-03 23:10 真平板整轮实测：86 条全死在 reset）。
        self.dirty = True
        img = self.current()
        if img is None:
            return False
        cy = self.geom.canvas_y or 0
        rows = lay.rows or 9
        cols = lay.cols or 9
        for r in range(rows):
            for c in range(cols):
                if cell_state(img, lay, r, c, cy) != "closed":
                    return False
        return True

    def wait_board_stable(self, timeout_ms: int = 25000, gap_ms: int = 450) -> bool:
        """等到**画面稳定**再继续（发牌 / 涟漪动画结束）。

        超时给 25 秒（原来 9 秒）：设备端截图会随负载劣化（实测 0.5 s → 3.7 s），
        一轮「截两张比一比」要 8 秒，9 秒只够跑一轮 —— 比不到就没结论，
        于是用例在发牌动画还没结束时就点了下去，判成「格子没翻开」。
        超时后返回 False（不抛），调用方照常继续，但那时画面确实可能还没稳。

        为什么必须等（2026-11-01，lead 在 Mate X7 上做跨设备校验时踩到）：
        开局有 **1100ms 的发牌动画**（`DealIn.TOTAL_MS`），期间格子是一块块翻上来的。
        在动画没结束时点击，点是**点了**（输入没被锁），但动画会把那一格重新画成砖块，
        于是 `cell_opened` 判「没翻开」；「点棋盘外不许翻格」那条也会因为画面一直在变而失败。
        画布越大（X7 2210px 宽）渲染越慢，动画尾巴越长 —— 5557 上碰巧等过了。

        盯的区域是**状态条以上的那一片**（画布内）：
        状态条的时钟每秒跳一下，整屏永远不会「稳定」，所以要把状态条排除掉。
        画布顶偏移还没量出来时（第一次 reset）就盯**整屏** ——
        发牌动画一格一格翻上来，变化量是几十万像素，远大于门限；
        时钟那一跳只有几百像素，在门限以下。
        """
        lay = self.geom.layout
        if lay is None:
            return False
        cy = self.geom.canvas_y or 0
        bottom = lay.strip_top if lay.strip_top else lay.canvas_h
        path = os.path.join(self.geom.workdir, "stable.jpeg")
        deadline = time.time() + timeout_ms / 1000.0
        prev = None
        rect = None
        # 要**连续两次**比一比都没变化才算稳。
        # 只比一次是不够的：设备负载重时应用自己的定时器会被拖慢（截图要 1~3 秒），
        # 发牌动画是「一阵一阵」地跳格 —— 两张截图恰好落在两阵之间就会看起来「没变」，
        # 于是判定成稳定，其实动画还没结束（表现就是棋盘边框的砖忽然变色）。
        streak = 0
        while time.time() < deadline:
            self.hdc.screenshot(path)
            cur = load_rgb(path)
            if rect is None:
                if self.geom.canvas_y is None:
                    rect = (0, 0, cur.shape[1], cur.shape[0])
                else:
                    rect = (0, cy, lay.canvas_w, max(1, bottom - cy))
            if prev is not None:
                d = diff_count(prev, cur, rect)
                area = max(1, rect[2] * rect[3])
                if d <= max(6, 0.0008 * area):
                    streak += 1
                    if streak >= 2:
                        return True
                else:
                    streak = 0
            prev = cur
            time.sleep(gap_ms / 1000.0)
        return False

    def act_menu(self, step: dict) -> None:
        top = step.get("top")
        if top not in MENU_TOPS:
            raise ValueError("未知菜单栏项: " + str(top))
        entry = step.get("entry")
        lay = self.geom.layout
        if lay is None:
            self.geom.refresh_layout()
        # 先点菜单栏空白处，确保任何已展开的下拉都收起来
        # 注意：菜单栏坐标是**画布 vp**，画布宽的 vp 数 = 画布宽(设备px) * pxScale
        #      （v(px) = px * pxScale，见 GameController.v()；别写成除）
        blank_vp = (lay.canvas_w * lay.px_scale - 16.0, 8.0)
        bx, by = self.geom.to_screen("menu", blank_vp[0], blank_vp[1])
        self.hdc.click(bx, by)
        time.sleep(0.35)
        tx, ty = self.geom.to_screen("menu", MENU_TOPS[top][0], MENU_TOPS[top][1])
        self.hdc.click(tx, ty)
        time.sleep(0.55)
        if entry:
            table = MENU_ENTRIES.get(top, {})
            if entry not in table:
                raise ValueError("菜单条目位置未登记: %s/%s" % (top, entry))
            ex, ey = self.geom.to_screen("menu", table[entry][0], table[entry][1])
            self.hdc.click(ex, ey)
            time.sleep(0.7)
        self.dirty = True

    def act_tap(self, step: dict) -> None:
        space = step.get("space", "screen")
        x = step.get("x", 0)
        y = step.get("y", 0)
        sx, sy = self.geom.to_screen(space, x, y,
                                     dialog=step.get("dialog"),
                                     cell=step.get("cell"))
        self.hdc.click(sx, sy)
        time.sleep(0.6)
        self.dirty = True

    def poke(self) -> None:
        """戳一下应用，把它从「后台冻结」里唤醒。

        坑（2026-11-01 晚）：模拟器窗口被别的窗口盖住时，应用会**完全冻结** ——
        界面不重绘、setInterval 也不跑（连状态条上的秒数都不跳，实测 5 秒内
        整屏 0 像素变化）。这时候截到的图是「冻结前那一帧」，跑测器把它当基准帧；
        等后面任何一次点击把应用唤醒、待办的发牌动画补完，棋盘的砖块就弹起来了 ——
        「棋盘没变」的断言必然失败，而且每次失败的像素数一模一样（19859）。

        戳哪儿：**菜单栏那一行的空白处**（菜单项都在左边）——
        应用被唤醒、开始渲染、把发牌动画跑完，而棋盘/状态条一个像素都不变。

        位置**由布局算出来**（画布 vp 的菜单栏空白处），不写死屏幕像素：
        原来这里写死「y=130 像素」（90 Pro 的实测值），换一台设备就可能戳到
        **棋盘上** —— 那一格就被点开了（甚至因此踩雷输掉）。
        菜单栏在棋盘**上面**，所以这个点在任何设备上都不可能点到棋盘。
        画布顶偏移还没量出来时，用**截图量出来的**画布顶（也不猜）。
        """
        lay = self.geom.layout
        if lay is None:
            return
        cy = self.geom.canvas_y
        if cy is None:
            cy = self.canvas_top_from_shot()
        if cy is None:
            return                      # 量不到画布顶就不戳（宁可不动，也别戳到棋盘）
        try:
            bx = int(round(lay.canvas_w - 16.0 / lay.px_scale))
            by = int(round(cy + 8.0 / lay.px_scale))
            self.hdc.click(bx, by)
        except Exception:
            pass
        time.sleep(0.6)

    def canvas_top_from_shot(self) -> int | None:
        """从截图里量画布顶（系统状态栏是黑的，画布是浅色的）。

        为什么需要：画布顶偏移 `canvas_y` 是所有屏幕 y 坐标的原点，
        量错了**整张图的所有点击都会偏**。老办法是拿棋盘上沿反推
        （`Geom.probe_canvas_y`），但发牌动画期间左上角那几行还没翻上来，
        量到的是错值（实测 239 vs 真值 125）。这一条**不受发牌动画影响**：
        画布顶就是系统状态栏下面那一行，跟棋盘翻没翻没关系。

        判据：从上往下找第一行「中间 60% 不是深色」的行 ——
        状态栏中间是黑的（时间、信号在两端），画布整片是浅色的。
        """
        img = self.current()
        if img is None:
            return None
        h, w = img.shape[0], img.shape[1]
        x0, x1 = int(w * 0.2), int(w * 0.8)
        for y in range(0, min(600, h)):
            seg = img[y, x0:x1, :].astype(float)
            if float(seg.mean()) > 120.0:
                return int(y)
        return None

    def act_longpress(self, step: dict) -> None:
        """长按一格（插旗）。

        实现走 Hdc.long_press()：uitest 没有长按命令，用极慢的 swipe 顶替。

        **手势在设备上校准过**（见 calibrate_longpress）：真平板上
        「1 px @ 1」被当成了单击，格子直接被翻开而不是插上旗。
        这里用校准出来的手势，并且**做完必须验证**：
          * 插上了旗 → 对了；
          * 格子被翻开了 → 手势被当成了单击，**这一局已经脏了**，
            必须报错退出，不能接着往下断言（不然失败会被记到别的地方）；
          * 格子没变 → 手势没送到，报告出来，别假装插上了。
        """
        space = step.get("space", "board")
        x = step.get("x", 0)
        y = step.get("y", 0)
        cell = step.get("cell")
        sx, sy = self.geom.to_screen(space, x, y,
                                     dialog=step.get("dialog"), cell=cell)
        variant = self.longpress_variant
        if variant is None:
            raise RuntimeError("这台设备上没能找到能用的长按手势（插旗没法测）")
        self.hdc.long_press(sx, sy, variant=variant)
        time.sleep(1.2)
        self.dirty = True
        if space == "board" and cell is not None:
            lay = self.geom.layout
            if lay is None:
                raise RuntimeError("还没有布局信息")
            st = cell_state(self.current(), lay, int(cell[0]), int(cell[1]),
                            self.geom.canvas_y or 0)
            if st == "flag":
                return
            if st == "opened":
                raise RuntimeError(
                    "长按被设备当成了**单击**：第(%d,%d)格被翻开了，没有插上旗。"
                    "这一局已经不可信，停止这条用例"
                    % (int(cell[0]), int(cell[1])))
            raise RuntimeError("长按之后第(%d,%d)格还是砖（%s），旗没插上"
                               % (int(cell[0]), int(cell[1]), st))

    def calibrate_longpress(self) -> tuple | None:
        """找出这台设备上**能真的插上旗**的长按手势。

        为什么必须有（2026-11-03 真平板 MRO-W00 实测）：
        `uitest uiInput swipe` 的第 5 个参数，模拟器当**速度**（px/s），
        真平板当**时长**（ms）—— 「1 px @ 1」在平板上是一次 1 ms 的滑动，
        **被应用当成单击**：格子被翻开、旗没插上、计时器开始走，
        那一局还因此踩雷输掉（证据：docs/verify\\CM_1430tabreal_FAIL_board_counter_flag_step5_cur.jpeg，
        画面上第 (0,0) 格是翻开的，没有旗；board.counter.negative 那条更明显：
        十来次「长按」把棋盘点开了一大片，最后一脚踩雷，失败框弹出来，
        后面所有点击都被对话框挡住 —— base 与 cur 两个画面**一个像素都没差**）。

        哪种解释对，只能**在设备上试**：挨个手势试，**用画面验证**
        （看那一格到底插上旗了没有）。

        试的时候**只用第 (0,0) 格**：某个手势要是变成了单击，洪水填充会把
        **一大片**格子翻开（9x9 初级盘上空区本来就大），后面再试别的格子
        就没有「干净的砖」可试了 —— 所以变成单击之后就**重开一局**再试下一种手势。

        校准用的是**一次性的**那块棋盘：每条用例开头都会 reset，
        所以校准留下的痕迹下一条用例就看不到了。
        """
        for _name, kind, params in LONGPRESS_VARIANTS:
            lay = self.geom.layout
            if lay is None or self.geom.canvas_y is None:
                return None
            sx, sy = self.geom.to_screen("board", 0, 0, cell=[0, 0])
            try:
                self.hdc.long_press(sx, sy, variant=(kind, params))
            except Exception:
                continue
            time.sleep(1.5)
            self.dirty = True
            lay = self.geom.layout
            st = cell_state(self.current(), lay, 0, 0, self.geom.canvas_y)
            if st == "flag":
                return (kind, params)
            if st == "opened":
                # 这个手势变成了单击：棋盘已经脏了（洪水填充还翻开了一大片），
                # 重开一局再来试下一种手势。
                try:
                    self._launch_fresh_app()
                except Exception as exc:
                    print("   [calibrate] 重开失败：%s" % exc)
                    return None
        return None

    def act_key(self, step: dict) -> None:
        """数字键盘的一个键（自定义难度框用）。

        '0'..'9' / 'back' → 键盘上的对应键
        'ok' / 'cancel'   → 框内的确定 / 取消按钮
        （键盘本身只有 11 个键，没有确定/取消，所以这两个映射到框内按钮。）
        """
        k = str(step.get("key", ""))
        if k in ("ok", "cancel"):
            rect = CUSTOM_BTN_OK if k == "ok" else CUSTOM_BTN_CANCEL
            cx = rect[0] + rect[2] / 2.0
            cy = rect[1] + rect[3] / 2.0
            sx, sy = self.geom.to_screen("custom", cx, cy)
        else:
            name = "back" if k in ("back", "del", "⌫") else k
            if name not in KEYPAD_KEYS:
                raise ValueError("未知按键: " + str(k))
            i = KEYPAD_KEYS.index(name)
            col = i % 3
            row = i // 3
            x = col * (KEY_W + KEY_GAP) + KEY_W / 2.0
            y = row * (KEY_H + KEY_GAP) + KEY_H / 2.0
            sx, sy = self.geom.to_screen("keypad", x, y)
        self.hdc.click(sx, sy)
        time.sleep(0.5)
        self.dirty = True

    def act_lose_game(self, step: dict) -> None:
        self.reset_appearance()
        self._mkstate("lose")

    def act_win_game(self, step: dict) -> None:
        self.reset_appearance()
        self._mkstate("win")

    def reset_appearance(self) -> None:
        """把外观**恢复成扫雷 + 银蓝**，再开始造赢/输的局。

        为什么必须做（2026-11-01 晚实测）：外观是**存到 preferences 里、重启也保留**的，
        而颜色框那几条用例会把棋盘切成「花园」玩法。花园玩法里**未翻开的格子是花、
        雷是一朵炸开的花**，`tools/win_probe.py` 靠读画面判断哪格是雷——
        它读不懂花园的棋盘，就把雷当成了安全格去点，于是「赢一局」脚本一局都赢不了
        （实测连续 3 遍都踩雷，弹出来的是失败框）。
        所以造局面之前先把外观摆回标准样式。
        """
        try:
            self.act_menu({"top": "game", "entry": "颜色(C)"})
            time.sleep(0.5)
            for x, y in ((72, 84), (78, 214)):     # 扫雷 / 银蓝
                sx, sy = self.geom.to_screen("dialog", x, y, dialog="appearance")
                self.hdc.click(sx, sy)
                time.sleep(0.5)
            sx, sy = self.geom.to_screen("dialog", 255, 315, dialog="appearance")  # 确定
            self.hdc.click(sx, sy)
            time.sleep(0.8)
            self.dirty = True
        except Exception as exc:      # 恢复失败也别中断：造局面失败会报设备状态问题
            print("   [reset_appearance] 恢复外观失败（忽略）：%s" % exc)

    def _mkstate(self, state: str) -> None:
        cmd = [sys.executable, MKSTATE, "--device", self.hdc.device, "--state", state]
        # 超时预算必须**大于** click_mkstate 自己要花的时间，否则用例会被
        # 记成「造局面失败」，而实际上只是跑测器的预算不够。
        #
        # 一遍造 win 局要多久（2026-11-02 在 Mate X7 模拟器上实测）：
        #   重启应用 + 量画布偏移 ≈ 20 s
        #   win_probe 一步步解算+点击+截图 ≈ 90~200 s
        #     （每步一次截图：X7 是 2210x2416，snapshot_display + file recv
        #      实测合计 0.7~8 s —— 模拟器负载高时明显变慢）
        #   等对话框出现 ≈ 3~30 s
        # click_mkstate 默认 attempts=6（造不出就重来），6 遍最坏 ≈ 1500 s。
        # 所以这里给 1800 s：够 6 遍跑完，也留了余量。
        proc = run(cmd, capture_output=True, text=True, errors="replace", timeout=1800)
        if self.verbose:
            print("   [mkstate %s] rc=%d" % (state, proc.returncode))
            for ln in (proc.stdout or "").splitlines()[-4:]:
                print("     " + ln)
        if proc.returncode != 0:
            # 造局面失败就**抛**：不能接着往下点、接着断言 ——
            # 否则失败会被记成「对话框的按钮坏了」，把锅甩给被测代码。
            # （Codex 复审 2026-11-01 的 P2）
            raise RuntimeError(
                "造局面失败（click_mkstate %s 退出码 %d）：%s"
                % (state, proc.returncode, (proc.stderr or proc.stdout or "")[-400:]))
        self.dirty = True
        # 造完局面之后再要一次布局：**不强制要新的**。
        #
        # 坑（2026-11-03 真平板 MRO-W00 实测）：
        # 应用**只在画布尺寸变化时**才打一条布局日志（GameController.ets:328），
        # 造完一局失败局面之后画布根本没变 → 那条日志要么被 hilog 的环形缓冲
        # 挤掉、要么被前面的 `hilog -x` 清掉了 → 「hilog 里没有布局日志」→
        # 这条用例报「第 2 步 lose_game 执行异常」，而**被测代码一点问题都没有**。
        # refresh_layout() 现在会**退回上一次记住的布局**（先验尺寸还对不对得上），
        # 所以这里拿到的还是对的布局。
        self.geom.refresh_layout(retries=12, gap_s=1.5, allow_cached=True)

    # ---- 断言 -------------------------------------------------------------
    def _strip_panel_rect(self, region: dict) -> tuple[int, int, int, int]:
        """状态条上两个绿色计数器面板的屏幕矩形（panel 0=计时，1=雷数）。

        位置**不写死**：面板的横向位置随棋盘宽度/锚点变（SPEC §5.5），
        所以从**当前这一帧**里找绿色块 —— 宽超过 150 设备像素的才是面板，
        棋盘上的绿砖只有 108 像素（18 参考像素 × 6），天然分得开。
        """
        img = self.current()
        if img is None:
            raise RuntimeError("还没有截图")
        lay = self.geom.layout
        if lay is None:
            raise RuntimeError("还没有布局信息")
        cy = self.geom.canvas_y or 0
        y0 = int(cy + lay.strip_top)
        band = img[y0:, :, :]
        if band.shape[0] < 10:
            raise RuntimeError("状态条那一带太矮，量不到")
        r = band[:, :, 0].astype(int)
        g = band[:, :, 1].astype(int)
        b = band[:, :, 2].astype(int)
        # 面板**不一定是绿的**：外观是「绿」时面板是绿的（greenSheet 98,185,91），
        # 外观是「蓝」时面板是深蓝的（blueSheet 99,138,229）。
        # 这里两种都认（2026-11-02：蓝主题下「状态条上找不到绿色面板」，
        # 三条 counter 用例全挂在这里）。
        is_green = (g > 90) & (g > r + 25) & (g > b + 25)
        is_blue = (b > 120) & (b > r + 60) & (g < 150) & ((b - r) > 60)
        green = is_green | is_blue
        cols = np.where(green.any(axis=0))[0]
        if len(cols) == 0:
            raise RuntimeError("状态条上找不到计数面板（绿/蓝都没找到）")
        runs = []
        start = prev = int(cols[0])
        for c in cols[1:]:
            c = int(c)
            if c > prev + 3:
                runs.append((start, prev))
                start = c
            prev = c
        runs.append((start, prev))
        panels = []
        # 面板的最小宽度要跟着**状态条自己的缩放档**走，不能写死 150 像素：
        # 状态条内容另有一档 su（su = min(u, 两组放得下的最大档)），
        # 中级/高级局 u 只有 4，su 也是 4 → 面板绿色内区只有 36×4 = 144 像素宽，
        # 写死 150 会把两个面板全丢掉（Codex 复审 P2）。
        # 这里照抄 GameController.drawStatusStrip 的算法把 su 算出来。
        unit = max(1, int(round(float(lay.tile) / 18.0)))
        group_ref = 25 + 6 + 40                      # 时钟 25 + 间隙 6 + 面板 40
        max_su = 2 * int(lay.canvas_w / (2 * group_ref) / 2)
        su = max(2, min(unit, max_su))
        min_panel_w = max(40, 30 * su)          # 面板彩色内区 33 参照像素宽
        # 这里原来写的是 36*su-6 —— 把**含外沿斜角高光**的整块面板当成了内区宽度。
        # 面板彩色内区只有 33 个参照单位宽（外沿高光另算），
        # 实测 Mate 90 Pro（su=6）彩色段宽 208 像素，而 36*6-6 = 210，
        # **差 2 像素就被这个下限滤掉**，于是「只找到 0 个计数器面板」。
        # 30 个单位仍远大于棋盘绿砖（18 个单位），不会误收砖块。
        for x0, x1 in runs:
            if x1 - x0 < min_panel_w:
                continue
            ys = np.where(green[:, x0:x1 + 1].any(axis=1))[0]
            if len(ys) == 0:
                continue
            # 面板的**绿色内区**在状态条上沿之上还会露出来一截
            # （HUD 模式下状态条内容压在棋盘下沿，计时面板比状态条上沿高），
            # 所以这里从状态条上沿**往上**找连续的绿色行，找到面板真正的顶边。
            top = int(ys.min())
            j = top - 1
            while j >= 0 and green[j, x0:x1 + 1].sum() > (x1 - x0) * 0.6:
                top = j
                j -= 1
            panels.append((int(x0), top + y0, int(x1 - x0 + 1),
                           int(ys.max() - top + 1)))
        panels.sort()
        idx = int(region.get("panel", 0))
        if idx >= len(panels):
            raise RuntimeError("状态条上只找到 %d 个计数器面板，要第 %d 个" % (len(panels), idx))
        return panels[idx]

    def expect_counter(self, step: dict) -> tuple[bool, str]:
        """断言状态条上某个计数器**显示的是哪个数字**（不是「有没有变」）。

        「变了」这种断言太弱：数字从 10 变成 11 也是「变了」（Codex 复审 P2）。
        这里用 tools/sevenseg_read.py 按七段几何**反解**出数字，直接比对。

        **轮询**：真机上应用收到点击之后重画要 0.5~2 秒（模拟器几乎立刻）。
        读一次就下结论会把「还没来得及画」当成「数字不对」
        （2026-11-03 真平板实测：插旗那两条用例读到的还是 10）。
        """
        region = step.get("region") or {"space": "strip", "panel": 0}
        want = str(step.get("value", "")).strip()
        timeout_ms = float(step.get("timeout_ms", 8000))
        deadline = time.time() + timeout_ms / 1000.0
        last = ""
        while True:
            # 现截一张（不要用可能过期的缓存帧）：布局刚变的那一瞬间，缓存帧里的
            # 状态条还在老位置，照着老位置采样会读到一片「全亮」的假读数。
            self.dirty = True
            self.capture()
            try:
                rect = self._strip_panel_rect(region)
                import sevenseg_read as ss
                img = self.current()
                if img is None:
                    return False, "还没有截图"
                box = (rect[0], rect[1], rect[2], rect[3])
                digits = ss.read_panel(img, box)
                if digits is None:
                    last = "面板 %s 量不出来" % (box,)
                else:
                    got = "".join(str(d) for d in ss.decode(digits) if d is not None)
                    if got == want:
                        return True, "计数器读数 %r（要 %r），掩码 %s，面板 %s" % (
                            got, want, digits, box)
                    last = "计数器读数 %r（要 %r），掩码 %s，面板 %s" % (got, want, digits, box)
            except Exception as exc:
                # 面板还没画出来 / 截图失败 → 当成「还没到」，继续等
                last = "读计数器出错：%s" % exc
            if time.time() >= deadline:
                return False, last + "（等了 %.1f 秒仍是这个读数）" % (timeout_ms / 1000.0)
            time.sleep(0.6)

    def expect_changed(self, step: dict, want_change: bool) -> tuple[bool, str]:
        region = step.get("region")
        if not region:
            return False, "changed/unchanged 必须给 region（整屏一直在变：状态条时钟每秒跳）"
        if region.get("space") == "strip":
            rect = self._strip_panel_rect(region)
        else:
            rect = self.geom.region_to_screen(region)
        base = self.hold if step.get("type", "").endswith("_vs_hold") else self.checkpoint
        if base is None:
            return False, "没有基准画面（前面没有 hold / reset / expect）"
        # 断言要**等画面稳定**再判，别拿动画中间帧说事。
        #
        # 坑（2026-11-03）：`dialogs.lose.menu` 在 Mate X7 上偶发失败 ——
        # 点「换个难度(D)」后框是关了，可下拉菜单**还没画出来**，
        # 断言就说「没变化」（0/8272 像素）。紧接着的截图里菜单又好好开着。
        # 应用侧的 openGameMenu() 是同步的（置 menuOpenId + draw()），
        # 所以这是**截图与重绘之间的时序**，不是应用的毛病。
        #
        # 判据不放松：最终状态必须真的变了/没变；这里只是**多等几拍**再看。
        # 同样的机制治过另一条偶发失败（Mate X7 的 custom.focus.replace）。
        n = diff_count(base, self.current(), rect)
        area = max(1, rect[2] * rect[3])
        thr = max(6, 0.0008 * area)
        # 重试 6 拍（约 5 秒）：真机上应用收到点击之后重画要 0.5~2 秒，
        # 模拟器几乎立刻 —— 4 拍（3.2 秒）在真机上不够（2026-11-03 真平板实测）。
        for attempt in range(6):
            changed = n >= thr
            if changed == want_change:
                ratio = n / float(area)
                return True, "差异像素 %d / %d (%.3f%%) -> %s" % (
                    n, area, ratio * 100, "有变化" if changed else "无变化")
            # 不符合预期：等一拍，**强制重截**再判
            time.sleep(0.8)
            self.dirty = True          # 让 current() 真的重新截图
            n = diff_count(base, self.current(), rect)
        ratio = n / float(area)
        changed = n >= thr
        return False, "差异像素 %d / %d (%.3f%%) -> %s（等了 6 拍仍不符）" % (
            n, area, ratio * 100, "有变化" if changed else "无变化")

    def expect_layout_changed(self, step: dict) -> tuple[bool, str]:
        # allow_cached=False：这条断言要的是**新的**布局行。
        # 退路（用上一次记住的布局）会让「没变」永远成立 —— 那是自欺欺人。
        cur = self.geom.refresh_layout(retries=12, gap_s=1.5, allow_cached=False)
        prev = self.last_layout
        self.last_layout = cur
        if prev is None:
            return True, "第一次取布局（无基准）"
        ok = prev.key() != cur.key()
        return ok, ("%s -> %s" % (prev, cur))

    def expect_layout_regex(self, step: dict) -> tuple[bool, str]:
        pat = step.get("re", "")
        # 同上：要的是**新的**布局行（应用每开一局都会重打一条，GameController.ets:215→266→328）
        cur = self.geom.refresh_layout(retries=12, gap_s=1.5, allow_cached=False)
        self.last_layout = cur
        ok = re.search(pat, cur.raw) is not None
        return ok, ("匹配 %r 于 %s" % (pat, cur.raw[-160:]))

    def expect_hilog_regex(self, step: dict) -> tuple[bool, str]:
        pat = step.get("re", "")
        new = self.log_new_lines()
        for ln in new:
            if re.search(pat, ln):
                return True, "命中: " + ln.strip()[-140:]
        tail = " / ".join(x.strip()[-60:] for x in new[-3:]) if new else "(没有新日志)"
        return False, "未命中 %r；最近的新日志: %s" % (pat, tail)

    def expect_hilog_absent(self, step: dict) -> tuple[bool, str]:
        """断言**不该出现**的日志（比「像素没变」更硬）。

        用处：颜色框这类对话框会把棋盘整个盖住，「外观到底生效没有」靠像素
        比不出来（比到的是框里的选中框），靠日志里的「[Dialog] 应用外观」最准。
        """
        pat = step.get("re", "")
        new = self.log_new_lines()
        for ln in new:
            if re.search(pat, ln):
                return False, "不该出现的日志却出现了: " + ln.strip()[-140:]
        return True, "没有出现 %r（新日志 %d 行）" % (pat, len(new))

    def expect_hilog_checks(self, step: dict) -> tuple[bool, str]:
        """在**同一个日志窗口**里做多条断言。

        为什么需要这个（2026-11-04，音效回归）：
        `log_new_lines()` 每调一次就把读到的行都标成「已见过」，
        所以**连续两个 expect 看不到同一批日志** ——
        第二个 expect 只会看到第一个之后新产生的行。
        于是「X 要出现」和「Y 不该出现」这种成对的断言，
        分成两个 expect 时，第二个会**空跑通过**（假的绿灯）。

        这里一次读完窗口，然后对这一批日志做**全部**检查：
        - `present`: true/false —— 该正则该不该命中（默认 present=true）
        - `re`: 正则
        - `min_count` / `max_count`: 命中次数的下限/上限（可选）
        """
        checks = step.get("checks")
        if not checks:
            return False, "hilog_checks 必须给 checks"
        new = self.log_new_lines()
        failed = []
        detail = []
        for chk in checks:
            pat = chk.get("re", "")
            want_present = bool(chk.get("present", True))
            hits = [ln for ln in new if re.search(pat, ln)]
            n = len(hits)
            detail.append("%r 命中 %d 次" % (pat, n))
            if want_present and n == 0:
                failed.append("应当出现 %r，但没有" % pat)
            if not want_present and n > 0:
                failed.append("不应出现 %r，却出现了 %d 次：%s"
                              % (pat, n, hits[0].strip()[-100:]))
            lo = chk.get("min_count")
            if lo is not None and n < int(lo):
                failed.append("%r 命中 %d 次，少于要求的 %s 次" % (pat, n, lo))
            hi = chk.get("max_count")
            if hi is not None and n > int(hi):
                failed.append("%r 命中 %d 次，多于要求的 %s 次" % (pat, n, hi))
        if failed:
            return False, "；".join(failed) + "（本窗口 %d 行：%s）" % (len(new), " / ".join(detail))
        return True, "同一窗口 %d 行全部符合：%s" % (len(new), " / ".join(detail))

    def expect_app_alive(self, step: dict) -> tuple[bool, str]:
        want = step.get("alive", True)
        alive = self.hdc.app_alive()
        ok = (alive == bool(want))
        return ok, "进程%s（pidof=%r）" % ("在" if alive else "没了", self.hdc.pidof())

    def expect_region_light(self, step: dict, want_light: bool) -> tuple[bool, str]:
        region = step.get("region")
        if not region:
            return False, "region_light/region_dark 必须给 region"
        rect = self.geom.region_to_screen(region)
        cur = self.current()
        x, y, w, h = rect
        x2 = min(x + w, cur.shape[1])
        y2 = min(y + h, cur.shape[0])
        if x2 <= x or y2 <= y:
            return False, "区域越界: %r" % (rect,)
        sub = cur[y:y2, x:x2]
        lum = float((sub[:, :, 0] * 0.299 + sub[:, :, 1] * 0.587 + sub[:, :, 2] * 0.114).mean())
        hi = step.get("min", 170.0)
        lo = step.get("max", 110.0)
        ok = (lum >= hi) if want_light else (lum <= lo)
        return ok, "平均亮度 %.1f（期望 %s）" % (lum, "亮" if want_light else "暗")

    def expect_cell_opened(self, step: dict) -> tuple[bool, str]:
        """断言某一格被翻开了（触摸路由对位）。

        **轮询**：真机上应用点完到重画要 0.5~2 秒（模拟器几乎立刻），
        读一次就下结论会把「还没画完」当成「没翻开」
        （2026-11-03 真平板实测：board.cell.04 在 (0,4) 上点完 1.5 秒后
        那一格还没翻开 —— 那一局其实早就输了、失败框挡着，点哪儿都没用）。
        """
        cell = step.get("cell")
        if cell is None:
            return False, "cell_opened 必须给 cell"
        lay = self.geom.layout
        r, c = int(cell[0]), int(cell[1])
        cy = self.geom.canvas_y or 0
        timeout_ms = float(step.get("timeout_ms", 8000))
        deadline = time.time() + timeout_ms / 1000.0
        while True:
            self.dirty = True
            cur = self.current()
            if cur is None:
                return False, "还没有截图"
            now = cell_opened(cur, lay, r, c, cy)
            was = None
            if self.before is not None:
                was = cell_opened(self.before, lay, r, c, cy)
            if now and (was is False):
                return True, "第(%d,%d)格从砖块变成已翻开" % (r, c)
            if now and was is None:
                return True, "第(%d,%d)格已翻开（无改动前画面可比）" % (r, c)
            if not now and was is True:
                return False, "第(%d,%d)格本来是翻开的，现在反而盖上了" % (r, c)
            if time.time() >= deadline:
                return False, "第(%d,%d)格没有被翻开（等了 %.1f 秒）" % (r, c, timeout_ms / 1000.0)
            time.sleep(0.6)

    def run_expect(self, step: dict) -> tuple[bool, str]:
        t = step.get("type")
        if t == "changed":
            ok, msg = self.expect_changed(step, True)
        elif t == "unchanged":
            ok, msg = self.expect_changed(step, False)
        elif t == "changed_vs_hold":
            ok, msg = self.expect_changed(step, True)
        elif t == "unchanged_vs_hold":
            ok, msg = self.expect_changed(step, False)
        elif t == "layout_changed":
            ok, msg = self.expect_layout_changed(step)
        elif t == "layout_regex":
            ok, msg = self.expect_layout_regex(step)
        elif t == "hilog_regex":
            ok, msg = self.expect_hilog_regex(step)
        elif t == "hilog_absent":
            ok, msg = self.expect_hilog_absent(step)
        elif t == "hilog_checks":
            ok, msg = self.expect_hilog_checks(step)
        elif t == "counter":
            ok, msg = self.expect_counter(step)
        elif t == "app_alive":
            ok, msg = self.expect_app_alive(step)
        elif t == "region_light":
            ok, msg = self.expect_region_light(step, True)
        elif t == "region_dark":
            ok, msg = self.expect_region_light(step, False)
        elif t == "cell_opened":
            ok, msg = self.expect_cell_opened(step)
        else:
            return False, "未知断言类型: " + str(t)
        # 检查点**不由断言推进**：基准永远是「上一个**动作**之前的画面」。
        # 理由（两个 agent 的用例表都要求这个语义）：
        #   * custom.key.emptycell：reset → menu → tap(键盘空格) → 三条连续的
        #     unchanged（三个不同的值区）。基准必须是「点空格之前」（对话框已开、
        #     值还是 9/9/10），若拿「用例开头」或「上一条断言的检查点」，
        #     就会跟「棋盘画面」比，误判成「变了」。
        #   * custom.limit.height：reset → … → key(2) → expect changed →
        #     key(5)（越界被拒）→ expect unchanged。基准是「按 5 之前」，
        #     值区仍是 2 → 没变 √。
        # 所以：动作（reset/menu/tap/key/lose_game/win_game）之前的画面 = 基准，
        # 断言只读不动。
        return ok, msg

    # ---- 用例 -------------------------------------------------------------
    def run_case(self, case: dict, domain: str) -> CaseResult:
        res = CaseResult(case.get("id", "?"), case.get("desc", ""), domain)
        steps = case.get("steps", [])
        for i, step in enumerate(steps):
            act = step.get("act")
            try:
                if act == "reset":
                    self.act_reset(step)
                elif act == "menu":
                    self._before_capture()
                    self.act_menu(step)
                elif act == "tap":
                    self._before_capture()
                    self.act_tap(step)
                elif act == "key":
                    self._before_capture()
                    self.act_key(step)
                elif act == "longpress":
                    self._before_capture()
                    self.act_longpress(step)
                elif act == "wait":
                    time.sleep(float(step.get("ms", 500)) / 1000.0)
                elif act == "hold":
                    # 存一张「参照画面」，给 changed_vs_hold / unchanged_vs_hold 用。
                    # 用处：对话框会把棋盘整个盖住时，「棋盘有没有变」只能拿
                    # **对话框关掉之后**的画面跟**打开之前**的画面比。
                    self.capture()
                    self.hold = self.img.copy() if self.img is not None else None
                elif act == "shot":
                    name = self.save_shot(step.get("name", "shot%d" % i))
                    res.shots.append(name)
                elif act == "expect":
                    ok, msg = self.run_expect(step)
                    if not ok:
                        res.fail("第%d步 %s: %s" % (i + 1, step.get("type"), msg))
                        # 断言失败时把**基准帧**和**当前帧**都存下来 ——
                        # 只看「差异像素 0」这类数字猜不出原因，得有图。
                        # 2026-11-03 平板回归里就栽在这：菜单面板明明开着，
                        # 断言却说「没变化」，看图才发现**基准帧**里那块已经是面板了。
                        self._dump_frames(res.cid, i + 1)
                    elif self.verbose:
                        print("      ok %s: %s" % (step.get("type"), msg))
                elif act == "lose_game":
                    self._before_capture()
                    self.act_lose_game(step)
                elif act == "win_game":
                    self._before_capture()
                    self.act_win_game(step)
                else:
                    res.fail("第%d步：未知动作 %r" % (i + 1, act))
            except Exception as exc:  # 单条用例失败不该拖垮整轮
                res.fail("第%d步 %s 执行异常: %s" % (i + 1, act, exc))
                # **这条用例到此为止**（下一条用例照跑）。
                # 坑（Codex 复审 2026-11-01 的 P2）：造局面失败时如果还往下点、往下断言，
                # 那些断言是在一个**根本没造出来的局面**上做的，失败会被记成
                # 「对话框按钮坏了」——把锅甩给被测代码。出错就停。
                break
        return res

    def _dump_frames(self, case_id: str, step_no: int) -> None:
        """断言失败时把基准帧 / 当前帧存成图，便于事后看图定位。

        存到 docs/verify\\，名字 `<tag>_FAIL_<用例>_<步号>_base|cur.jpeg`。
        存不了就算了 —— 不能因为存图失败把用例判成别的错。
        """
        try:
            from PIL import Image
            base = self.checkpoint
            cur = self.current()
            stem = "CM_%sFAIL_%s_step%d" % (self.tag + "_" if self.tag else "",
                                            case_id.replace(".", "_"), step_no)
            for arr, suffix in ((base, "base"), (cur, "cur")):
                if arr is None:
                    continue
                path = os.path.join(VERIFY_DIR, "%s_%s.jpeg" % (stem, suffix))
                Image.fromarray(arr.astype("uint8")).save(path, quality=92)
        except Exception:
            pass

    def _before_capture(self) -> None:
        """改动动作之前先把画面存下来。

        这一张同时是**两**样东西：
          * cell_opened 断言要的「改动前的样子」；
          * changed / unchanged 的**基准**（上一个动作之前的画面）。
        """
        self.capture()
        if self.img is not None:
            self.before = self.img.copy()
            self.checkpoint = self.img.copy()


# ===========================================================================
#  主流程
# ===========================================================================
def load_cases(domains: list[str], only: str | None,
               critical_only: bool = False) -> list[tuple[str, dict]]:
    """读用例表。

    @param critical_only 只收标了 `"critical": true` 的用例（见 --critical）。
    """
    out = []
    if not os.path.isdir(CASES_DIR):
        return out
    for fn in sorted(os.listdir(CASES_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(CASES_DIR, fn)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        dom = data.get("domain") or os.path.splitext(fn)[0]
        if domains and dom not in domains:
            continue
        for case in data.get("cases", []):
            cid = case.get("id", "")
            if only and only not in cid:
                continue
            if critical_only and not case.get("critical"):
                continue
            out.append((dom, case))
    return out


class _Tee:
    """把 stdout 同时写到屏幕和一个日志文件。

    为什么要有（2026-11-04，Codex 对抗性复审第 8 轮的 P2）：
    跑测器以前**只往 stdout 打**，成绩单不留档 ——
    于是文档里写「整轮重跑 86 条」时，别人在仓里**找不到任何能核对的产物**
    （那轮复审的原话：*"the updated handover relies on a nonexistent log as evidence"*）。
    现在每轮自动写一份 `docs/verify/CM_<tag>.log`，成绩单和证据截图放在一起。
    """

    def __init__(self, stream, path: str):
        self.stream = stream
        self.path = path
        self.fh = open(path, "w", encoding="utf-8", newline="\n")

    def write(self, s: str) -> int:
        self.stream.write(s)
        self.fh.write(s)
        # **每写一行就落盘**：不刷的话 Python 的缓冲会攒着，
        # 跑测进行中去看那个日志文件是 0 字节（没法看进度），
        # 中途被掐掉的话更是什么都留不下。
        self.fh.flush()
        return len(s)

    def flush(self) -> None:
        self.stream.flush()
        self.fh.flush()

    def isatty(self) -> bool:
        return bool(getattr(self.stream, "isatty", lambda: False)())

    def close(self) -> None:
        try:
            self.fh.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="扫雷复刻点击矩阵跑测器")
    ap.add_argument("--device", default="127.0.0.1:5557", help="hdc 设备地址")
    ap.add_argument("--cases", default="", help="要跑的域，逗号分隔（默认全部）")
    ap.add_argument("--only", default="", help="只跑用例 id 含这个子串的")
    ap.add_argument("--tag", default="", help="证据图名前缀（CM_<tag>_<name>.jpeg）")
    ap.add_argument("--critical", action="store_true",
                    help="只跑标了 \"critical\": true 的用例（每个域的关键几条，分钟级）")
    ap.add_argument("--verbose", action="store_true", help="打印每一步的细节")
    args = ap.parse_args()

    domains = [d.strip() for d in args.cases.split(",") if d.strip()]
    cases = load_cases(domains, args.only or None, args.critical)
    if not cases:
        print("没有匹配的用例（--cases %s --only %s --critical %s）"
              % (args.cases, args.only, args.critical))
        return 2

    # 成绩单同时写进 docs\verify\CM_<tag>.log（见 _Tee 的说明）。
    # 开着它跑之前先把这个 tag 的旧日志清掉，免得两轮混在一起。
    os.makedirs(VERIFY_DIR, exist_ok=True)
    log_path = os.path.join(VERIFY_DIR, "CM_%s.log" % (args.tag or "run"))
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except OSError:
            pass
    tee = _Tee(sys.stdout, log_path)
    sys.stdout = tee
    try:
        return _run(args, cases)
    finally:
        sys.stdout = tee.stream
        tee.close()


def _run(args, cases) -> int:
    runner = Runner(args.device, args.tag, args.verbose)
    # 跑测开始前把缓冲区里已有的日志行都算成「已见过」，
    # 这样 hilog_regex 不会匹配到上一轮遗留的同名日志。
    runner.mark_log_seen()
    print("设备 %s ；用例 %d 条（域: %s）" %
          (args.device, len(cases), ",".join(sorted(set(d for d, _ in cases)))))

    # --- 前置检查（2026-11-03 新增）------------------------------------
    #
    # 坑：2026-11-03 01:5x 这一轮 86 条用例**全部**死在第 1 步，
    # 报错都是「hilog 里没有布局日志」—— 根因是**应用根本没装在模拟器上**
    # （模拟器里 /data/app/el1/bundle/public/com.example.saolei 不存在）。
    # 这种失败会白白烧掉一个多小时才看得出是环境问题，不是被测代码的问题。
    # 所以开跑前先验三件事：应用在不在、能不能起来、起��来有没有布局日志。
    # 任何一条不满足就**立刻退出**并说清楚怎么办。
    ok_pre, pre_msg = runner.preflight()
    if not ok_pre:
        print("")
        print("!! 前置检查没通过，%d 条用例一条都没跑：" % len(cases))
        print("   %s" % pre_msg)
        print("   处理办法：")
        print("   1) 把 HAP 装上去：")
        print("      hdc -t %s install -r <hap 路径>" % args.device)
        print("   2) 确认能起来：hdc -t %s shell aa start -a EntryAbility -b %s"
              % (args.device, BUNDLE))
        print("   3) 再跑本套件。")
        return 3

    results = []
    t0 = time.time()
    for n, (dom, case) in enumerate(cases, 1):
        print("[%d/%d] %-28s %s" % (n, len(cases), case.get("id", "?"),
                                   case.get("desc", "")[:56]))
        # 周期性把设备唤醒（内部 2 分钟节流）：一轮 86 条要跑一个多小时，
        # 设备中途熄屏会让后面的 `aa start` 静默失败。
        # **点亮不解锁** —— 锁屏(keyguard)还得用户手动解。
        runner.hdc.wake_screen()
        res = runner.run_case(case, dom)
        results.append(res)
        print("      -> %s%s" % ("通过" if res.ok else "失败",
                                "" if res.ok else "：" + "；".join(res.messages)))
    dt = time.time() - t0

    ok = sum(1 for r in results if r.ok)
    bad = [r for r in results if not r.ok]
    print("")
    print("=" * 78)
    print("总计 %d 条：通过 %d，失败 %d（用时 %.0f 秒）" %
          (len(results), ok, len(bad), dt))
    if bad:
        print("")
        print("失败明细：")
        for r in bad:
            print("  %-28s %s" % (r.cid, "；".join(r.messages)))
    print("=" * 78)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
