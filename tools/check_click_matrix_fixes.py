#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_click_matrix_fixes.py —— 拿 2026-11-03 真平板那一轮的**证据截图**，
离线验证跑测器新加的几处判断是不是真的成立（不用连设备）。

验证的东西：
  1) cell_state()：长按那两条用例的失败画面上，第 (0,0) 格是「被翻开了」
     而不是「插上了旗」→ 证明真机上长按被当成了单击；
  2) verify_fresh_board()：board.cell.04 的 base 帧**不是**一块全新棋盘
     → 证明那一局在用例点 (0,4) 之前就已经是「输掉、失败框开着」的状态；
  3) layout_fits_screen()：横屏布局（2800x1690）在竖屏（1840x2800）上被判为
     「放不进屏幕」→ 证明另一方向的旧布局行会被挡掉；
  4) canvas_top_from_shot()：从竖屏截图里量出的画布顶在合理范围。

用法：
    python tools\\check_click_matrix_fixes.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import click_matrix as cm  # noqa: E402

VERIFY = os.path.join(os.path.dirname(HERE), "docs", "verify")

#: 真平板竖屏那一轮的实测几何（从截图里量的：网格线在 x=109/285/465…，y=466/646/…）
TAB_X0, TAB_Y0, TAB_TILE = 109, 466, 180
TAB_CY = 61                      # 画布顶在屏幕上的纵向偏移（系统状态栏下面）
TAB_ROWS, TAB_COLS = 9, 9


class FakeLayout(cm.Layout):
    """直接按实测几何造一条布局（不解析日志）。"""

    def __init__(self, canvas_w=1840, canvas_h=2650, board_x=TAB_X0,
                 board_y=TAB_Y0 - TAB_CY, tile=TAB_TILE, rows=TAB_ROWS,
                 cols=TAB_COLS):
        self.raw = "（实测几何）"
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.px_scale = 1.0
        self.fit = 1
        self.cur_fit = 1
        self.unit = TAB_TILE // 18
        self.tile = tile
        self.board_x = board_x
        self.board_y = board_y
        self.strip_top = canvas_h - 200
        self.rows = rows
        self.cols = cols
        self.mines = 10


def load(name):
    return np.asarray(Image.open(os.path.join(VERIFY, name)).convert("RGB")).astype(np.int16)


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "!!", label, ("  —— " + detail) if detail else ""))
    return bool(ok)


def main() -> int:
    lay = FakeLayout()
    allok = True

    print("1) 长按被当成了单击（board.counter.flag 的失败画面）")
    img = load("CM_1430tabreal_FAIL_board_counter_flag_step5_cur.jpeg")
    st00 = cm.cell_state(img, lay, 0, 0, TAB_CY)
    st11 = cm.cell_state(img, lay, 1, 1, TAB_CY)
    st88 = cm.cell_state(img, lay, 8, 8, TAB_CY)
    allok &= check("第(0,0)格 = %s（期望 opened：长按被当成了单击，格子被翻开）" % st00,
                   st00 == "opened")
    allok &= check("第(1,1)格 = %s（期望 opened：洪水填充的一部分）" % st11, st11 == "opened")
    allok &= check("第(8,8)格 = %s（期望 closed：没被点到的砖）" % st88, st88 == "closed")
    allok &= check("画面上**没有红旗**（旗是红色的；真机上插旗根本没成功）",
                   not _has_red_flag(img, lay, TAB_CY))

    print("2) board.cell.04 那一局在点 (0,4) 之前就已经输了")
    base = load("CM_1430tabreal_FAIL_board_cell_04_step4_base.jpeg")
    cur = load("CM_1430tabreal_FAIL_board_cell_04_step4_cur.jpeg")
    diff = int((np.abs(base - cur).max(axis=2) > 12).sum())
    allok &= check("base 与 cur 相差 %d 像素（期望 0：点 (0,4) 之前画面就没再变过）" % diff,
                   diff == 0)
    fresh = _verify_fresh(base, lay, TAB_CY)
    allok &= check("verify_fresh_board(base) = %s（期望 False：不是全新棋盘）" % fresh,
                   fresh is False)

    print("3) 另一个方向的旧布局行会被挡掉")
    geo = cm.Geom.__new__(cm.Geom)
    geo.screen_size = (1840, 2800)
    land = FakeLayout(canvas_w=2800, canvas_h=1690)
    port = FakeLayout(canvas_w=1840, canvas_h=2650)
    allok &= check("横屏布局 2800x1690 在竖屏 1840x2800 上 = %s（期望 False）"
                   % geo.layout_fits_screen(land), geo.layout_fits_screen(land) is False)
    allok &= check("竖屏布局 1840x2650 在竖屏 1840x2800 上 = %s（期望 True）"
                   % geo.layout_fits_screen(port), geo.layout_fits_screen(port) is True)

    print("4) 从截图量画布顶")
    cy = _canvas_top(base)
    allok &= check("canvas_top_from_shot = %s（期望在 40..120 之间：系统状态栏下面）" % cy,
                   cy is not None and 40 <= cy <= 120)

    print("")
    allok &= _logic_tests()
    print("")
    print("全部通过" if allok else "有不通过的项")
    return 0 if allok else 1


def _has_red_flag(img, lay, cy) -> bool:
    for r in range(lay.rows):
        for c in range(lay.cols):
            if cm.cell_state(img, lay, r, c, cy) == "flag":
                return True
    return False


def _verify_fresh(img, lay, cy) -> bool:
    for r in range(lay.rows):
        for c in range(lay.cols):
            if cm.cell_state(img, lay, r, c, cy) != "closed":
                return False
    return True


def _canvas_top(img) -> int | None:
    h, w = img.shape[0], img.shape[1]
    x0, x1 = int(w * 0.2), int(w * 0.8)
    for y in range(0, min(600, h)):
        seg = img[y, x0:x1, :].astype(float)
        if float(seg.mean()) > 120.0:
            return int(y)
    return None


class _FakeHdc:
    """给「校准/重开」这两个流程做逻辑自测用的假设备。"""

    def __init__(self, runner):
        self.runner = runner
        self.longpress_calls = []
        self.restarts = 0

    def long_press(self, x, y, variant=None):
        self.longpress_calls.append(variant)

    def device_now_marker(self):
        return "11-03 00:00:00.000"


class _FakeGeom:
    def __init__(self):
        self.layout = FakeLayout()
        self.canvas_y = TAB_CY
        self.screen_size = (1840, 2800)
        self.refresh_calls = 0

    def refresh_layout(self, **kw):
        self.refresh_calls += 1
        return self.layout

    def to_screen(self, space, x, y, dialog=None, cell=None):
        if space == "board" and cell:
            r, c = int(cell[0]), int(cell[1])
            return (self.layout.board_x + c * self.layout.tile + self.layout.tile // 2,
                    self.layout.board_y + r * self.layout.tile + self.layout.tile // 2
                    + (self.canvas_y or 0))
        return (100, 100)


def _logic_tests() -> bool:
    """用假的设备/几何，验证「校准」「重开重试」两条流程的逻辑。"""
    print("5) 校准流程：第一个手势变成单击 → 重开一局 → 试下一种手势")
    ok = True
    runner = cm.Runner.__new__(cm.Runner)
    runner.hdc = _FakeHdc(runner)
    runner.geom = _FakeGeom()
    runner.longpress_variant = None
    runner.dirty = False
    runner.img = None
    runner.verbose = False
    runner.workdir = os.path.join(VERIFY, "_tmp_calib")   # 只用文件名，不会真的写
    runner.capture = lambda *a, **k: ""
    runner.launches = 0
    runner._launch_fresh_app = lambda: setattr(runner, "launches", runner.launches + 1)

    seq = ["opened", "flag"]          # 第一个手势变单击，第二个手势插上旗
    calls = {"n": 0}

    def fake_cell_state(img, lay, r, c, cy=0):
        calls["n"] += 1
        return seq[min(calls["n"] - 1, len(seq) - 1)]

    real_state = cm.cell_state
    cm.cell_state = fake_cell_state
    try:
        got = runner.calibrate_longpress()
    finally:
        cm.cell_state = real_state
    ok &= check("校准结果 = %s（期望 ('swipe', (1, 1))：第一个手势 longClick 变成单击，"
                "第二个手势才插上旗）" % (got,),
                got == ("swipe", (1, 1)))
    ok &= check("重开了 %d 次（期望 1：第一个手势变成单击之后重开）" % runner.launches,
                runner.launches == 1)
    ok &= check("试了 %d 种手势（期望 2）" % len(runner.hdc.longpress_calls),
                len(runner.hdc.longpress_calls) == 2)

    print("6) 重开流程：前两遍棋盘不是全新的 → 第三遍才干净 → 不报错")
    runner2 = cm.Runner.__new__(cm.Runner)
    runner2.geom = _FakeGeom()
    runner2.launches = 0
    runner2._launch_fresh_app = lambda: setattr(runner2, "launches", runner2.launches + 1)
    states = {"n": 0}

    def fake_fresh():
        states["n"] += 1
        return states["n"] >= 3

    runner2.verify_fresh_board = fake_fresh
    runner2.act_menu = lambda step: None
    runner2.capture = lambda *a, **k: ""
    runner2.img = None
    runner2.dirty = True
    try:
        runner2.act_reset({})
        ok &= check("act_reset 没有抛异常，且重开了 3 次", runner2.launches == 3)
    except Exception as exc:
        ok &= check("act_reset 抛异常：%s" % exc, False)

    print("7) 重开流程：一直不干净 → 明确报错（不静默放过）")
    runner3 = cm.Runner.__new__(cm.Runner)
    runner3.geom = _FakeGeom()
    runner3.launches = 0
    runner3._launch_fresh_app = lambda: setattr(runner3, "launches", runner3.launches + 1)
    runner3.verify_fresh_board = lambda: False
    runner3.act_menu = lambda step: None
    runner3.capture = lambda *a, **k: ""
    runner3.img = None
    runner3.dirty = True
    try:
        runner3.act_reset({})
        ok &= check("应该报错但没有", False)
    except RuntimeError as exc:
        ok &= check("重开 3 次后报错：%s" % exc, True)
    return ok


if __name__ == "__main__":
    sys.exit(main())
