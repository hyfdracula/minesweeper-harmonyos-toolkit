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

    def app_alive(self) -> bool:
        return self.pidof().strip() != ""

    def stop_app(self) -> None:
        self.shell("aa", "force-stop", BUNDLE, timeout=60, check=True)
        time.sleep(1.0)

    def start_app(self) -> None:
        self.shell("aa", "start", "-a", "EntryAbility", "-b", BUNDLE, timeout=90, check=True)
        time.sleep(3.0)


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

    # ---- 日志 -------------------------------------------------------------
    def read_log(self) -> list[str]:
        raw = self.hdc.hilog()
        self._log_lines = raw.splitlines()
        return self._log_lines

    def refresh_layout(self) -> Layout:
        """从 hilog 里取**最后一条**布局日志。"""
        lines = self.read_log()
        last = None
        for ln in lines:
            if "[GameController] 布局" in ln:
                last = ln
        if last is None:
            raise RuntimeError("hilog 里没有布局日志")
        self.layout = Layout(last)
        return self.layout

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
        self.workdir = os.path.join(os.environ.get("TEMP", "."), "click_matrix_run")
        os.makedirs(self.workdir, exist_ok=True)
        os.makedirs(VERIFY_DIR, exist_ok=True)
        self.geom = Geom(self.hdc, self.workdir)
        self.seen_log: set[str] = set()
        self.checkpoint = None            # 基准：上一个**动作**之前的画面（numpy 数组）
        self.before = None                # 最后一个改动动作之前的画面（cell_opened 用）
        self.img = None                   # 最近一次抓的画面
        self.dirty = True                 # 画面是否已过期
        self.last_layout: Layout | None = None
        self.shot_seq = 0

    # ---- 画面 -------------------------------------------------------------
    def capture(self, path: str | None = None) -> str:
        if self.dirty or path is not None:
            p = path or os.path.join(self.workdir, "cur.jpeg")
            self.hdc.screenshot(p)
            self.img = load_rgb(p)
            self.dirty = False
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

    # ---- 动作 -------------------------------------------------------------
    def act_reset(self, step: dict) -> None:
        self.hdc.stop_app()
        self.hdc.start_app()
        self.geom.refresh_layout()
        # 顺序要紧：**先等画面稳定（发牌动画结束），再量画布顶偏移**。
        # 发牌动画是从右下往左上报的，动画期间量到的偏移是错的（实测 239 vs 真值 125）。
        self.wait_board_stable()
        if self.geom.canvas_y is None:
            self.geom.probe_canvas_y()
        diff = step.get("difficulty")
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
        self._mkstate("lose")

    def act_win_game(self, step: dict) -> None:
        self._mkstate("win")

    def _mkstate(self, state: str) -> None:
        cmd = [sys.executable, MKSTATE, "--device", self.hdc.device, "--state", state]
        proc = run(cmd, capture_output=True, text=True, errors="replace", timeout=600)
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
        self.geom.refresh_layout()

    # ---- 断言 -------------------------------------------------------------
    def expect_changed(self, step: dict, want_change: bool) -> tuple[bool, str]:
        region = step.get("region")
        if not region:
            return False, "changed/unchanged 必须给 region（整屏一直在变：状态条时钟每秒跳）"
        rect = self.geom.region_to_screen(region)
        if self.checkpoint is None:
            return False, "没有检查点（前面没有 reset / expect）"
        cur = self.current()
        n = diff_count(self.checkpoint, cur, rect)
        area = max(1, rect[2] * rect[3])
        ratio = n / float(area)
        changed = n >= max(6, 0.0008 * area)
        ok = changed if want_change else (not changed)
        return ok, "差异像素 %d / %d (%.3f%%) -> %s" % (
            n, area, ratio * 100, "有变化" if changed else "无变化")

    def expect_layout_changed(self, step: dict) -> tuple[bool, str]:
        cur = self.geom.refresh_layout()
        prev = self.last_layout
        self.last_layout = cur
        if prev is None:
            return True, "第一次取布局（无基准）"
        ok = prev.key() != cur.key()
        return ok, ("%s -> %s" % (prev, cur))

    def expect_layout_regex(self, step: dict) -> tuple[bool, str]:
        pat = step.get("re", "")
        cur = self.geom.refresh_layout()
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
        cell = step.get("cell")
        if cell is None:
            return False, "cell_opened 必须给 cell"
        lay = self.geom.layout
        cur = self.current()
        r, c = int(cell[0]), int(cell[1])
        cy = self.geom.canvas_y or 0
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
        return False, "第(%d,%d)格没有被翻开" % (r, c)

    def run_expect(self, step: dict) -> tuple[bool, str]:
        t = step.get("type")
        if t == "changed":
            ok, msg = self.expect_changed(step, True)
        elif t == "unchanged":
            ok, msg = self.expect_changed(step, False)
        elif t == "layout_changed":
            ok, msg = self.expect_layout_changed(step)
        elif t == "layout_regex":
            ok, msg = self.expect_layout_regex(step)
        elif t == "hilog_regex":
            ok, msg = self.expect_hilog_regex(step)
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
                elif act == "wait":
                    time.sleep(float(step.get("ms", 500)) / 1000.0)
                elif act == "shot":
                    name = self.save_shot(step.get("name", "shot%d" % i))
                    res.shots.append(name)
                elif act == "expect":
                    ok, msg = self.run_expect(step)
                    if not ok:
                        res.fail("第%d步 %s: %s" % (i + 1, step.get("type"), msg))
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
def load_cases(domains: list[str], only: str | None) -> list[tuple[str, dict]]:
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
            out.append((dom, case))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="扫雷复刻点击矩阵跑测器")
    ap.add_argument("--device", default="127.0.0.1:5557", help="hdc 设备地址")
    ap.add_argument("--cases", default="", help="要跑的域，逗号分隔（默认全部）")
    ap.add_argument("--only", default="", help="只跑用例 id 含这个子串的")
    ap.add_argument("--tag", default="", help="证据图名前缀（CM_<tag>_<name>.jpeg）")
    ap.add_argument("--verbose", action="store_true", help="打印每一步的细节")
    args = ap.parse_args()

    domains = [d.strip() for d in args.cases.split(",") if d.strip()]
    cases = load_cases(domains, args.only or None)
    if not cases:
        print("没有匹配的用例（--cases %s --only %s）" % (args.cases, args.only))
        return 2

    runner = Runner(args.device, args.tag, args.verbose)
    # 跑测开始前把缓冲区里已有的日志行都算成「已见过」，
    # 这样 hilog_regex 不会匹配到上一轮遗留的同名日志。
    runner.mark_log_seen()
    print("设备 %s ；用例 %d 条（域: %s）" %
          (args.device, len(cases), ",".join(sorted(set(d for d, _ in cases)))))

    results = []
    t0 = time.time()
    for n, (dom, case) in enumerate(cases, 1):
        print("[%d/%d] %-28s %s" % (n, len(cases), case.get("id", "?"),
                                   case.get("desc", "")[:56]))
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
