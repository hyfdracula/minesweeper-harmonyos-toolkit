# -*- coding: utf-8 -*-
r"""从截图里读出状态条两个七段计数器（计时 / 剩余雷）的数字。

为什么要自己写：状态条上的数字不是字体，是**程序画的七段数码管**
（见 entry/src/main/ets/common/SevenSeg.ets），没有 OCR 可用，
所以这里按同一套几何反解。

几何（参考像素，与 SevenSeg.ets 一一对应）：
    面板 40×21（**外框**）；面板精灵四周有 1 个逻辑像素的边框，
    所以截图里量到的**绿色区域是面板内区 38×19** —— 换算比例必须按 38 算，
    槽位原点还要往外挪 1 个参考像素，否则采样点整体偏移（Codex 复审 P2）。
    槽位 x = 0 / 13 / 26；每槽 12 宽 × 16 高，槽内 y = 2
    a: (3, 2, 6, 2)   b: (9, 4, 3, 5)   c: (9, 11, 3, 5)
    d: (3, 16, 6, 2)  e: (0, 11, 3, 5)  f: (0, 4, 3, 5)
    g: (3, 9, 6, 2)

做法：先**只在状态条那一条横带里**找绿色面板（不限定的话，棋盘上的绿砖
也会被算进来，量出来的框全是错的 —— Codex 复审 P2），
再在面板里按几何采样每段的中心点是否发白 → 还原数字
（槽位从右往左读，右对齐不补零）。

用法：python tools\sevenseg_read.py <截图路径> [状态条矩形 x,y,w,h]
      → 打印每个面板读出来的数字
"""
import sys

import numpy as np

# 段位掩码（位序 a,b,c,d,e,f,g）与 SevenSeg.ets 的 DIGIT_MASKS 一致
SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = 1, 2, 4, 8, 16, 32, 64
SEG_FLAG, SEG_BASE1 = 128, 256

MASKS = [
    0x3F, 0x186, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
]

# 负号段：单独一根中横（g），掩码 0x40。
# 剩余雷数可以是负的（插的旗比雷还多，SPEC §3.3），原版负号占**紧挨数字左边**的那一槽。
# 0x40 不是任何数字的合法掩码，所以不会和数字混淆（Codex 复审 P2）。
MASK_MINUS = 0x40

# 「1」的标准写法：只亮 b、c 两段（0x06）。
# 原版那个「1」还带一面小旗和一道衬线（掩码 0x186），但旗和衬线**不是标准七段**，
# 反解时只采样标准七段就只会得到 0x06（b+c）；若把衬线底横画在 d 段的位置上，
# 采样到的是 0x0E（b+c+d）。两个都要认成「1」（Codex 复审 P2）。
MASK_ONE_STD = 0x06
MASK_ONE_BASE = 0x0E

# (段名, x, y, w, h) —— 参考像素，相对槽位左上角。
# 定义挪到几何常量之后（见文件下方），因为它要用 CELL_W / CELL_H。
BIT = {'a': SEG_A, 'b': SEG_B, 'c': SEG_C, 'd': SEG_D,
       'e': SEG_E, 'f': SEG_F, 'g': SEG_G}

# 面板（外框）参考像素
PANEL_W, PANEL_H = 40, 21
# 2026-11-02 真机实测：面板精灵的**彩色内区**只占 x=3..36、y=2..19（33x17），
# 外面那圈是斜角高光/暗边。find_panels 量到的是这个内区，
# 所以下面所有槽位几何都**相对内区左上角**算，不再减边框。
PANEL_BORDER = 0
INNER_W, INNER_H = 33, 17
SLOT_COUNT = 3
# 与 SevenSeg.ets 的常量对齐（内区坐标）：
#   SLOT_X0=3 / CELL_Y=2 是相对**面板外框**的，减掉内区原点就都是 0
SLOT_X0 = 0
SLOT_PITCH = 12
CELL_W, CELL_H = 9, 11
CELL_Y = 5

# (段名, x, y, w, h) —— 相对槽位左上角，**按格宽/格高算，不要写死**
# （2026-11-02：格宽从 12 改成 10 再改成 9、笔画从 3 改成 1，
#   写死的表会把每段采样点全带偏，真机上「0」被读成「1」/「?」）。
_TV, _TH, _HL = 1, 1, 4          # 与 SevenSeg.ets 的 TV / TH / HL 一致
SEGS = [
    ('a', _TV, 0, CELL_W - 2 * _TV, _TH),
    ('b', CELL_W - _TV, _TH, _TV, _HL),
    ('c', CELL_W - _TV, _TH + _HL + _TH, _TV, _HL),
    ('d', _TV, CELL_H - _TH, CELL_W - 2 * _TV, _TH),
    ('e', 0, _TH + _HL + _TH, _TV, _HL),
    ('f', 0, _TH, _TV, _HL),
    ('g', _TV, _TH + _HL, CELL_W - 2 * _TV, _TH),
]


def _green_mask(im):
    """计数器面板的「内区」掩码。

    **不只看绿色**（2026-11-02 真机实测纠正）：面板精灵来自 boardSheet，
    外观是「绿」时面板是绿的（greenSheet: 98,185,91），
    外观是「蓝」时面板是深蓝的（blueSheet: 99,138,229）—— 玩家把外观切成蓝，
    真机上就一个「绿色面板」都找不到，跑测器报「状态条上找不到绿色面板」，
    看起来像应用坏了，其实是反解脚本只认一种颜色。

    改成「高饱和 + 偏蓝或偏绿」（背景是浅灰蓝 198,205,221，饱和很低，不会误判）。
    """
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    green = (g > 90) & (g > r + 25) & (g > b + 25)
    blue = (b > 120) & (b > r + 60) & (g < 150) & (sat > 60)
    return green | blue


def _white_mask(im):
    return im.min(axis=2) > 185


def find_panels(im, strip_box=None):
    """在图里找绿色计数器面板，返回 [(x0, y0, w, h), ...]（按 x 排序）。

    `strip_box` = (x, y, w, h)：**只在状态条那一条横带里找**。
    不限定的话，棋盘上的绿砖会被并进同一段列区间，量出来的框全是错的。
    """
    green = _green_mask(im)
    if strip_box is not None:
        sx, sy, sw, sh = [int(v) for v in strip_box]
        region = np.zeros_like(green)
        y1 = min(im.shape[0], sy + sh)
        x1 = min(im.shape[1], sx + sw)
        region[max(0, sy):y1, max(0, sx):x1] = green[max(0, sy):y1, max(0, sx):x1]
        green = region
    cols = np.where(green.any(axis=0))[0]
    if len(cols) == 0:
        return []
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
    for x0, x1 in runs:
        if x1 - x0 < 30:          # 太窄的不是面板（棋盘上的绿砖等）
            continue
        ys = np.where(green[:, x0:x1 + 1].any(axis=1))[0]
        if len(ys) == 0:
            continue
        panels.append((int(x0), int(ys.min()), int(x1 - x0 + 1),
                       int(ys.max() - ys.min() + 1)))
    panels.sort()
    return panels


def _sample_slots(im, outer_x, outer_y, s):
    """按几何采样三个槽位的七段掩码。"""
    white = _white_mask(im)
    digits = []
    for i in range(SLOT_COUNT):
        sx = outer_x + (SLOT_X0 + i * SLOT_PITCH) * s
        sy = outer_y + CELL_Y * s
        mask = 0
        for name, rx, ry, rw, rh in SEGS:
            cx = int(round(sx + (rx + rw / 2.0) * s))
            cy = int(round(sy + (ry + rh / 2.0) * s))
            # 采 3x3 小块取多数：真机截图的框边会差 1~3 个像素，
            # 单点采样时刚好点在段边界上就会把整段读丢（「0」被读成「1」或「?」）。
            hit = 0
            tot = 0
            for ddy in (-1, 0, 1):
                for ddx in (-1, 0, 1):
                    yy = cy + ddy
                    xx = cx + ddx
                    if 0 <= yy < im.shape[0] and 0 <= xx < im.shape[1]:
                        tot += 1
                        if white[yy, xx]:
                            hit += 1
            if tot and hit * 2 > tot:
                mask |= BIT[name]
        digits.append(mask)
    return digits


def read_panel(im, panel):
    """读一个面板里的数字（三个槽的掩码列表；空槽为 0）。

    `panel` = (x0, y0, w, h)：绿色**内区**的矩形（见 find_panels）。

    纵向原点有 ±1 个参考像素的不确定（面板精灵的边框上、下不一样厚，
    而数字是按**外框**原点画的），所以这里沿纵向试几个偏移，
    取「三个槽都能解成合法数字」的那一个；实在分不出来就取合法槽最多的。
    """
    x0, y0, pw, ph = panel
    if pw < 30 or ph < 10:
        return None
    # 比例 s（设备像素 / 参考单位）：
    #   应用里的状态条内容档 su **永远是偶数**（SevenSeg 注释：偶数档图集才不会糊），
    #   而量到的矩形会把斜角高光多算进来几个像素（真机实测 276 而不是 264），
    #   直接拿 pw/INNER_W 当 s 会偏 4%，三个槽位越往右越偏，左边的竖段就采不到 ——
    #   表现是「0」被读成「1」（只剩 b、c 两段）。
    #   所以先按高度估（高度受高光影响小），再吸附到最近的偶数。
    s_raw = ph / float(INNER_H)
    s = max(2.0, float(round(s_raw / 2.0) * 2))
    outer_x = x0
    base_y = y0
    # 纵向也锚到**内区的中心**，不用内区顶边：
    # 内区顶边会随高光/文字被多算或少算几个像素（真机实测两张截图差 3 px），
    # 而数字格在面板里是垂直居中的（CELL_Y=2、CELL_H=16、面板 21 → 中心重合），
    # 用中心锚更稳。
    base_y = y0 + ph / 2.0 - CELL_H * s / 2.0
    best = None
    best_score = -1
    for dy in (-2, -1, 0, 1, 2):
        digits = _sample_slots(im, outer_x, base_y + dy * s, s)
        score = 0
        for m in digits:
            if m == 0:
                score += 1                      # 空槽（右对齐、不补零）也算合法
            elif m == MASK_ONE_STD or m == MASK_ONE_BASE:
                score += 2
            elif m == MASK_MINUS:
                score += 2                      # 负号段也是合法的一槽
            elif m in MASKS:
                score += 2
        if score > best_score:
            best_score = score
            best = digits
    return best


def decode(digits):
    """把三个槽位的掩码还原成数字串；读不出的槽位跳过（不补零，右对齐）。"""
    text = []
    for m in digits:
        if m == 0:
            text.append(None)
            continue
        if m == MASK_MINUS:
            text.append('-')          # 负号段（只剩中横）
        elif m == MASK_ONE_STD or m == MASK_ONE_BASE:
            text.append('1')          # 标准七段的「1」：只亮 b、c（带衬线底横时多一段 d）
        elif m in MASKS:
            text.append(str(MASKS.index(m)))
        else:
            text.append('?')
    return text


def read_counters(path, strip_box=None):
    im = np.array(_load(path)).astype(int)
    panels = find_panels(im, strip_box)
    out = []
    for p in panels:
        d = read_panel(im, p)
        if d is not None:
            out.append((p, decode(d)))
    return out


def _load(path):
    from PIL import Image
    return Image.open(path).convert('RGB')


if __name__ == '__main__':
    args = sys.argv[1:]
    path = args[0] if args else None
    if path is None:
        print('用法: python tools\\sevenseg_read.py <截图路径> [状态条矩形 x,y,w,h]')
        sys.exit(2)
    box = None
    if len(args) >= 5:
        box = tuple(int(v) for v in args[1:5])
    for i, (p, txt) in enumerate(read_counters(path, box)):
        print('面板 %d %s: %s' % (i, p, ' '.join(str(t) for t in txt)))
