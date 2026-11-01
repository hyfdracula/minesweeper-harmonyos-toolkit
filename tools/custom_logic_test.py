#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
custom_logic_test.py —— 「自定义」难度对话框**纯逻辑**的离线自测（2026-11-01）

为什么要有这个脚本
------------------
`CustomField.ets` 是 ArkTS，本机没有 ArkTS 运行时，跑不了单元测试。于是把它的
**纯逻辑**（不含画布绘制）翻成一份 Python 镜像，逐条断言行为；**同时从 .ets 源码里
抠出常量与关键代码片段**，用来校验镜像 —— 源码一改（比如把某个上限改掉），脚本立刻红，
不会出现「镜像还在按旧规则跑、测试却全绿」的假绿。

覆盖（本轮补齐后的逻辑）
------------------------
  1. 常量与标签：LABELS 由常量拼出来，三个标签原文是「高度(9-24):」这种
  2. maxMines()：按盘面算 + 668 封顶
  3. maxOfField()：三个框的**输入**上限（高度 24 / 宽度 30 / 雷数 668 全局）
  4. clampSpec()：下限、上限、按盘面收雷数（= 确定时真正生效的值）
  5. inputChar()：替换 vs 追加、越界拒绝、只收 0-9、**改行列不动雷数框**
  6. backspace()：退成 0、不会变负
  7. focusField()：切焦点 → 下一位替换
  8. hintText()：三种提示文案 + **不能超出对话框宽度**
  9. 源码级护栏：inputChar 里不许再有「输入期回收雷数」的代码

用法
----
    python tools/custom_logic_test.py          # 跑全部断言
    python tools/custom_logic_test.py -v       # 每条都打印
退出码：0 = 全过，1 = 有失败。

依据（结论都有出处，见 docs/CUSTOM-DIALOG-AUDIT.md §9）
------------------------------------------------------
  原版 Win7 的自定义框：三个编辑框 + 三个标签 + 确定/取消，**没有键盘、没有最佳成绩列表**
    ReversingMinesweeper/resource.h:67-76（原版 XP 二进制逆向重建）
  范围写在标签里：
    Lmy0217 Minesweeper.rc:106-108 / linux-minesweeper OptionsDialog.cpp:89-91
  三个框互相独立、盘面收只在确定时：
    原版 XP windowing.c:220-223 + 905-918（GetDlgIntOfRange 在 IDOK 时才调）
"""

import math
import os
import re
import sys

# ---------------------------------------------------------------------------
# 被测源码（只读）
# ---------------------------------------------------------------------------
SRC = r"C:\Users\19161\saolei\entry\src\main\ets\common\CustomField.ets"

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def js_round(x):
    """JavaScript Math.round：半数向上。Python 内置 round 是银行家舍整。"""
    return math.floor(x + 0.5)


def clamp_int(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


class Spec(object):
    """对应 ArkTS 的 CustomSpec 接口。"""
    __slots__ = ("height", "width", "mines", "focus")

    def __init__(self, height=9, width=9, mines=10, focus=0):
        self.height = height
        self.width = width
        self.mines = mines
        self.focus = focus

    def copy(self):
        return Spec(self.height, self.width, self.mines, self.focus)

    def as_tuple(self):
        return (self.height, self.width, self.mines, self.focus)

    def __repr__(self):
        return "Spec(h=%s, w=%s, m=%s, focus=%s)" % self.as_tuple()


# ---------------------------------------------------------------------------
# 从 .ets 源码里抠常量 + 抠函数体（防止镜像与实现跑偏）
# ---------------------------------------------------------------------------
def read_source():
    if not os.path.exists(SRC):
        raise SystemExit("找不到源码：%s" % SRC)
    with open(SRC, encoding="utf-8") as f:
        return f.read()


def const_of(src, name):
    m = re.search(r"export const %s\s*:\s*number\s*=\s*(-?\d+)\s*;" % name, src)
    if not m:
        raise SystemExit("源码里找不到常量 %s" % name)
    return int(m.group(1))


def body_of(src, marker):
    """取某个 static 方法的函数体（从标记到下一个 '  static ' 之前）。"""
    i = src.find(marker)
    if i < 0:
        raise SystemExit("源码里找不到 %s" % marker)
    j = src.find("\n  static ", i + len(marker))
    if j < 0:
        j = len(src)
    return src[i:j]


# ---------------------------------------------------------------------------
# Python 镜像（严格照 CustomField.ets 的实现翻译）
# ---------------------------------------------------------------------------
class Mirror(object):
    def __init__(self, src):
        self.MIN_ROWS = const_of(src, "MIN_ROWS")
        self.MAX_ROWS = const_of(src, "MAX_ROWS")
        self.MIN_COLS = const_of(src, "MIN_COLS")
        self.MAX_COLS = const_of(src, "MAX_COLS")
        self.MIN_MINES = const_of(src, "MIN_MINES")
        self.MAX_MINES = const_of(src, "MAX_MINES")
        self.LABEL_RIGHT = const_of(src, "LABEL_RIGHT")
        self.EDIT_X = const_of(src, "EDIT_X")
        self.EDIT_W = const_of(src, "EDIT_W")
        self.EDIT_H = const_of(src, "EDIT_H")
        self.DLG_W = const_of(src, "DLG_W")
        self.HINT_X = const_of(src, "HINT_X")
        self.HINT_SIZE = const_of(src, "HINT_SIZE")
        # 模块级状态（ArkTS 里是文件级 let）
        self.lastFocus = -1
        self.replaceNext = True

    # ---- 标签（.ets 里由常量拼出来） ----
    def labels(self):
        return [
            "高度(%d-%d):" % (self.MIN_ROWS, self.MAX_ROWS),
            "宽度(%d-%d):" % (self.MIN_COLS, self.MAX_COLS),
            "雷数(%d-%d):" % (self.MIN_MINES, self.MAX_MINES),
        ]

    # ---- maxMines ----
    def max_mines(self, height, width):
        h = clamp_int(js_round(height), self.MIN_ROWS, self.MAX_ROWS)
        w = clamp_int(js_round(width), self.MIN_COLS, self.MAX_COLS)
        by_size = (h - 1) * (w - 1) + 1
        return by_size if by_size < self.MAX_MINES else self.MAX_MINES

    # ---- maxOfField：三个框的**输入**上限 ----
    def max_of_field(self, s, index):
        if index == 0:
            return self.MAX_ROWS
        if index == 1:
            return self.MAX_COLS
        if index == 2:
            return self.MAX_MINES
        return 0

    # ---- valueOf / setValue ----
    def value_of(self, s, index):
        if index == 0:
            return s.height
        if index == 1:
            return s.width
        if index == 2:
            return s.mines
        return 0

    def set_value(self, s, index, v):
        if index == 0:
            s.height = v
        elif index == 1:
            s.width = v
        elif index == 2:
            s.mines = v

    # ---- clampSpec：确定时真正生效的值 ----
    def clamp_spec(self, s):
        s.height = clamp_int(js_round(s.height), self.MIN_ROWS, self.MAX_ROWS)
        s.width = clamp_int(js_round(s.width), self.MIN_COLS, self.MAX_COLS)
        max_m = self.max_mines(s.height, s.width)
        s.mines = clamp_int(js_round(s.mines), self.MIN_MINES, max_m)
        s.focus = clamp_int(js_round(s.focus), 0, 2)
        return s

    # ---- specOf / defaultSpec ----
    def spec_of(self, rows, cols, mines):
        self.lastFocus = -1
        self.replaceNext = True
        return self.clamp_spec(Spec(rows, cols, mines, 0))

    def default_spec(self):
        self.lastFocus = -1
        self.replaceNext = True
        return Spec(9, 9, 10, 0)

    # ---- focusField ----
    def focus_field(self, s, field_id):
        idx = {"height": 0, "width": 1, "mines": 2}.get(field_id, -1)
        if idx < 0:
            return
        s.focus = idx
        self.replaceNext = True

    # ---- inputChar ----
    def input_char(self, s, ch):
        if len(ch) != 1:
            return False
        code = ord(ch)
        if code < 48 or code > 57:
            return False
        idx = s.focus
        if idx < 0 or idx > 2:
            return False
        digit = code - 48
        replace = self.replaceNext or idx != self.lastFocus
        cur = 0 if replace else self.value_of(s, idx)
        nxt = cur * 10 + digit
        if nxt > self.max_of_field(s, idx):
            return False
        self.set_value(s, idx, nxt)
        # 改了高度/宽度**不动**雷数框（盘面收统一在确定时做）
        self.lastFocus = idx
        self.replaceNext = False
        return True

    # ---- backspace ----
    def backspace(self, s):
        idx = s.focus
        if idx < 0 or idx > 2:
            return
        cur = self.value_of(s, idx)
        self.set_value(s, idx, math.floor(cur / 10))
        self.lastFocus = idx
        self.replaceNext = False

    # ---- hintText ----
    def hint_text(self, s):
        max_m = self.max_mines(s.height, s.width)
        rows_bad = s.height < self.MIN_ROWS or s.height > self.MAX_ROWS
        cols_bad = s.width < self.MIN_COLS or s.width > self.MAX_COLS
        hint = "高度/宽度超范围，最多 " if (rows_bad or cols_bad) else "本盘面最多 "
        hint += "%d 雷" % max_m
        if s.mines > max_m:
            hint += "，当前 %d 将按 %d 布雷" % (s.mines, max_m)
        return hint


# ---------------------------------------------------------------------------
# 断言小框架
# ---------------------------------------------------------------------------
class Runner(object):
    def __init__(self, verbose=False):
        self.passed = 0
        self.failed = []
        self.verbose = verbose

    def check(self, name, got, want):
        if got == want:
            self.passed += 1
            if self.verbose:
                print("  [PASS] %-52s %s" % (name, got))
        else:
            self.failed.append((name, got, want))
            print("  [FAIL] %-52s got=%r want=%r" % (name, got, want))

    def truth(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            if self.verbose:
                print("  [PASS] %s %s" % (name, detail))
        else:
            self.failed.append((name, detail, True))
            print("  [FAIL] %s %s" % (name, detail))

    def report(self):
        print("")
        print("断言 %d 条，通过 %d 条，失败 %d 条" % (self.passed + len(self.failed),
                                                   self.passed, len(self.failed)))
        if self.failed:
            print("失败明细：")
            for name, got, want in self.failed:
                print("  - %s: got=%r want=%r" % (name, got, want))
            return 1
        return 0


# ---------------------------------------------------------------------------
# 文本宽度估算（提示行不能溢出对话框）
# ---------------------------------------------------------------------------
def text_width(s, font_size):
    """粗略估算一行文字的参考像素宽度：CJK 按字号，ASCII 按 0.55 字号。"""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o > 0x2E80:          # CJK / 全角标点
            w += font_size
        else:
            w += font_size * 0.55
    return w


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    verbose = "-v" in sys.argv
    src = read_source()
    m = Mirror(src)
    r = Runner(verbose)

    print("被测源码：%s" % SRC)
    print("常量：行 %d-%d / 列 %d-%d / 雷 %d-%d"
          % (m.MIN_ROWS, m.MAX_ROWS, m.MIN_COLS, m.MAX_COLS, m.MIN_MINES, m.MAX_MINES))
    print("")

    # ---- 1. 常量与标签 ----
    print("[1] 常量与标签")
    r.check("标签原文（照抄 Win7：范围写在标签里）", m.labels(),
            ["高度(9-24):", "宽度(9-30):", "雷数(10-668):"])
    r.truth("源码里 LABELS 由常量拼出（不是写死的字符串）",
            "'高度(' + MIN_ROWS.toString()" in src)
    # 只看 LABELS 的**声明块**（注释里会提到旧写法，不能算）
    m_labels = re.search(r"export const LABELS[^;]*?\];", src, re.S)
    r.truth("LABELS 声明块找得到", m_labels is not None)
    r.truth("LABELS 声明块里不再有旧的短标签 ['高度:', '宽度:', '雷数:']",
            m_labels is not None and "['高度:', '宽度:', '雷数:']" not in m_labels.group(0))
    r.truth("标签右对齐线 LABEL_RIGHT < 输入框左边界 EDIT_X（标签不会压到输入框）",
            m.LABEL_RIGHT < m.EDIT_X,
            "LABEL_RIGHT=%d EDIT_X=%d" % (m.LABEL_RIGHT, m.EDIT_X))
    r.truth("最长的标签也还在框内（左边界 > 0）",
            m.LABEL_RIGHT - text_width(m.labels()[2], 12) > 0,
            "「%s」宽 %.1f，右对齐线 %d" % (m.labels()[2],
                                        text_width(m.labels()[2], 12), m.LABEL_RIGHT))

    # ---- 2. maxMines ----
    print("[2] maxMines（按盘面算 + 668 封顶）")
    r.check("maxMines(9, 9)", m.max_mines(9, 9), 65)
    r.check("maxMines(16, 16)", m.max_mines(16, 16), 226)
    r.check("maxMines(16, 30)", m.max_mines(16, 30), 436)
    r.check("maxMines(24, 30)", m.max_mines(24, 30), 668)
    # 行列先被夹到合法区间（30 行不合法 → 24），所以 30x24 等于 24x24
    r.check("maxMines(30, 24)（30 行先夹到 24）", m.max_mines(30, 24), 530)
    r.check("maxMines(1, 9)（非法中间值先夹到 9 行）", m.max_mines(1, 9), 65)
    r.check("maxMines(9, 9) = min(668, (9-1)*(9-1)+1)", m.max_mines(9, 9),
            min(668, (9 - 1) * (9 - 1) + 1))

    # ---- 3. maxOfField ----
    print("[3] maxOfField（三个框的输入上限）")
    s0 = Spec()
    r.check("高度框输入上限", m.max_of_field(s0, 0), 24)
    r.check("宽度框输入上限", m.max_of_field(s0, 1), 30)
    r.check("雷数框输入上限（全局 668，不按盘面）", m.max_of_field(s0, 2), 668)

    # ---- 4. clampSpec（确定时生效） ----
    print("[4] clampSpec（确定时真正生效的值）")
    s = m.clamp_spec(Spec(1, 1, 1, 0))
    r.check("全越界 → 下限 9/9/10", s.as_tuple(), (9, 9, 10, 0))
    s = m.clamp_spec(Spec(99, 99, 999, 5))
    r.check("全超上限 → 24/30/668，焦点夹到 2", s.as_tuple(), (24, 30, 668, 2))
    s = m.clamp_spec(Spec(24, 30, 500, 0))
    r.check("雷数在盘面上限之内 → 不动", s.as_tuple(), (24, 30, 500, 0))
    s = m.clamp_spec(Spec(9, 9, 500, 0))
    r.check("雷数超本盘面上限 → 收到 65（9x9）", s.as_tuple(), (9, 9, 65, 0))
    s = m.clamp_spec(Spec(16, 30, 999, 0))
    r.check("雷数超本盘面上限 → 收到 436（16x30）", s.as_tuple(), (16, 30, 436, 0))

    # ---- 5. inputChar ----
    print("[5] inputChar（替换/追加/越界拒绝/改行列不动雷数）")
    s = m.default_spec()
    m.focus_field(s, "height")
    r.check("只收单个 0-9：字母被拒", m.input_char(s, "a"), False)
    r.check("只收单个 0-9：空串被拒", m.input_char(s, ""), False)
    r.check("只收单个 0-9：两位被拒", m.input_char(s, "12"), False)
    r.check("被拒后值不变", s.height, 9)

    s = m.default_spec()
    m.focus_field(s, "height")
    m.input_char(s, "1")
    r.check("刚获得焦点 → 首位替换旧值（9 → 1）", s.height, 1)
    m.input_char(s, "9")
    r.check("同一框第二位 → 追加（1 → 19）", s.height, 19)

    s = m.default_spec()
    m.focus_field(s, "height")
    m.input_char(s, "1")
    m.focus_field(s, "width")
    m.input_char(s, "2")
    r.check("切到宽度框 → 宽度替换成 2", s.width, 2)
    m.focus_field(s, "height")
    m.input_char(s, "5")
    r.check("切回高度框 → 替换成 5（不是 195）", s.height, 5)

    s = m.default_spec()
    m.focus_field(s, "height")
    m.input_char(s, "2")
    ok = m.input_char(s, "5")
    r.check("高度越界：25 > 24 → 按键被拒", ok, False)
    r.check("高度越界：值保持 2", s.height, 2)

    s = m.default_spec()
    m.focus_field(s, "width")
    m.input_char(s, "3")
    ok = m.input_char(s, "1")
    r.check("宽度越界：31 > 30 → 按键被拒", ok, False)
    r.check("宽度越界：值保持 3", s.width, 3)

    s = m.default_spec()
    m.focus_field(s, "mines")
    m.input_char(s, "6")
    m.input_char(s, "6")
    r.check("雷数 6 → 66（同框追加）", s.mines, 66)
    ok = m.input_char(s, "9")
    r.check("雷数越界：669 > 668 → 按键被拒", ok, False)
    r.check("雷数越界：值保持 66", s.mines, 66)

    s = m.default_spec()
    m.focus_field(s, "mines")
    m.input_char(s, "5")
    m.input_char(s, "0")
    m.input_char(s, "0")
    r.check("雷数框输入上限是全局的：9x9 也能填 500", s.mines, 500)
    m.focus_field(s, "height")
    m.input_char(s, "9")
    r.check("改高度不动雷数框（盘面收只在确定时）", s.mines, 500)
    m.focus_field(s, "width")
    m.input_char(s, "9")
    r.check("改宽度也不动雷数框", s.mines, 500)
    s2 = m.clamp_spec(s.copy())
    r.check("确定时才收：9x9 的 500 雷 → 65", (s2.height, s2.width, s2.mines), (9, 9, 65))

    # ---- 6. backspace ----
    print("[6] backspace（退成 0、不会变负）")
    s = m.default_spec()
    m.focus_field(s, "height")
    m.backspace(s)
    r.check("9 退一格 → 0（不是空）", s.height, 0)
    m.backspace(s)
    r.check("0 再退 → 还是 0（不会变负）", s.height, 0)
    s = m.default_spec()
    m.focus_field(s, "height")
    m.input_char(s, "2")
    m.input_char(s, "4")
    m.backspace(s)
    r.check("24 退一格 → 2", s.height, 2)
    m.backspace(s)
    r.check("2 退一格 → 0", s.height, 0)
    m.input_char(s, "5")
    r.check("退格后下一位是追加（0 + 5 → 5）", s.height, 5)

    # ---- 7. focusField ----
    print("[7] focusField（切焦点 → 下一位替换）")
    s = m.default_spec()
    m.focus_field(s, "mines")
    r.check("focus 切到雷数框", s.focus, 2)
    r.check("切焦点后 replaceNext 置位", m.replaceNext, True)
    s.focus = 0
    m.focus_field(s, "不存在的框")
    r.check("未知框名 → 焦点不动", s.focus, 0)

    # ---- 8. hintText ----
    print("[8] hintText（三种文案 + 不溢出）")
    r.check("正常盘面", m.hint_text(Spec(9, 9, 10, 0)), "本盘面最多 65 雷")
    r.check("雷数超上限", m.hint_text(Spec(9, 9, 500, 0)),
            "本盘面最多 65 雷，当前 500 将按 65 布雷")
    r.check("高度正在输入（中间值 1）→ 说明超范围",
            m.hint_text(Spec(1, 9, 10, 0)), "高度/宽度超范围，最多 65 雷")
    r.check("行列超范围 + 雷数超上限",
            m.hint_text(Spec(1, 9, 500, 0)),
            "高度/宽度超范围，最多 65 雷，当前 500 将按 65 布雷")
    r.check("24x30 盘面", m.hint_text(Spec(24, 30, 10, 0)), "本盘面最多 668 雷")
    hint_cases = [Spec(9, 9, 10, 0), Spec(9, 9, 500, 0), Spec(1, 9, 10, 0),
                  Spec(1, 9, 500, 0), Spec(24, 30, 668, 0), Spec(30, 24, 10, 0)]
    avail = m.DLG_W - m.HINT_X
    worst = max(text_width(m.hint_text(c), m.HINT_SIZE) for c in hint_cases)
    r.truth("最长提示行不超出对话框（%.1f ≤ %d 参考像素）" % (worst, avail),
            worst <= avail)
    r.truth("提示行不再重复静态范围（范围在标签里）",
            all("9-24" not in m.hint_text(c) and "10-668" not in m.hint_text(c)
                for c in hint_cases))

    # ---- 9. 源码级护栏 ----
    print("[9] 源码级护栏")
    body_input = body_of(src, "static inputChar")
    r.truth("inputChar 里没有「输入期回收雷数」的赋值",
            "s.mines =" not in body_input,
            "（找到 %r）" % ("s.mines =" if "s.mines =" in body_input else None))
    r.truth("inputChar 里仍然按 maxOfField 拒绝越界输入",
            "maxOfField" in body_input)
    body_clamp = body_of(src, "static clampSpec")
    r.truth("clampSpec 里按盘面收雷数（maxMines）",
            "maxMines" in body_clamp)
    body_hint = body_of(src, "static hintText")
    r.truth("有 hintText（提示行文案抽成函数）",
            "static hintText" in src)
    r.truth("hintText 里有「将按」生效值说明",
            "将按" in body_hint)
    r.truth("旧的提示行写法（带范围的整句）已经不在了",
            "（本盘面最多 " not in src)
    r.truth("draw() 用的是 hintText()",
            "CustomField.hintText(s)" in src)

    # ---- 汇总 ----
    print("")
    print("对照依据：原版自定义框只有 三个编辑框 + 三个标签 + 确定/取消"
          "（ReversingMinesweeper/resource.h:67-76）；"
          "范围写在标签里（Lmy Minesweeper.rc:106-108 / linux OptionsDialog.cpp:89-91）；"
          "三个框互相独立、盘面收只在确定时（原版 XP windowing.c:220-223, 905-918）。")
    return r.report()


if __name__ == "__main__":
    sys.exit(main())
