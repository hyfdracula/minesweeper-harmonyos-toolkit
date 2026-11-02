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
SEG_FLAG, SEG_BASE1, SEG_ONEBAR = 128, 256, 512

MASKS = [
    0x3F, 0x586, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F,
]

# 负号段：单独一根中横（g），掩码 0x40。
# 剩余雷数可以是负的（插的旗比雷还多，SPEC §3.3），原版负号占**紧挨数字左边**的那一槽。
# 0x40 不是任何数字的合法掩码，所以不会和数字混淆（Codex 复审 P2）。
MASK_MINUS = 0x40

# 「1」的标准写法：只亮 b、c 两段（0x06）。
# 2026-11-02：原版的「1」是一根**从格顶连到格底、中间不断**的竖笔
# （画成标准七段的 b+c 会在中横那一行断开，真机上每个「1」都断成两截），
# 所以反解时 b 和 c 都会采样到 —— 得到的仍是 0x06 ✓。
# 旗（小方点）和衬线底横都不落在标准七段的采样点上，所以不参与判定。
# 若把衬线底横画在 d 段的位置上，采样到的是 0x0E（b+c+d），也要认成「1」。
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
        w = int(x1 - x0 + 1)
        h = int(ys.max() - ys.min() + 1)
        # 计数面板是 40×21 的横长条（内区 33×17，宽高比 ≈1.9）。
        # 时钟图标和雷图标是方的，灰蓝色也被掩码捞进来，
        # 用宽高比把它们剔掉（2026-11-02 模拟器上实测：图标被当成面板了）。
        if h <= 0 or not (1.45 <= w / float(h) <= 2.6):
            continue
        panels.append((int(x0), int(ys.min()), w, h))
    panels.sort()
    return panels


def _sample_slots(im, outer_x, outer_y, s):
    """按几何采样三个槽位的七段掩码。

    返回 (掩码列表, 亮段包围盒)：
    包围盒是**亮起来的那些段**的并集范围（设备像素）。
    有了它才能判断「这组采样是不是正好把墨迹全占了」——
    见 read_panel 里的包围盒吻合判据。
    """
    white = _white_mask(im)
    digits = []
    bx0 = None
    by0 = None
    bx1 = None
    by1 = None
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
                x0 = int(round(sx + rx * s))
                y0 = int(round(sy + ry * s))
                x1 = int(round(sx + (rx + rw) * s))
                y1 = int(round(sy + (ry + rh) * s))
                bx0 = x0 if bx0 is None else min(bx0, x0)
                by0 = y0 if by0 is None else min(by0, y0)
                bx1 = x1 if bx1 is None else max(bx1, x1)
                by1 = y1 if by1 is None else max(by1, y1)
        digits.append(mask)
    bbox = None if bx0 is None else (bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1)
    return digits, bbox


def read_panel(im, panel):
    """读一个面板里的数字（三个槽的掩码列表；空槽为 0）。

    `panel` = (x0, y0, w, h)：**面板的矩形**（可以含外沿斜角高光）。

    定位方式（2026-11-02 改）：**不拿这个框当内区**，而是用框里的**白色数字**
    反推格位 —— 面板外沿的斜角高光也会被颜色掩码捞进来，量到的框比真正的
    内区宽 12 像素（真机实测 276 而内区是 264），
    拿框当内区会让三个槽位整体偏 1.5 个单位，采样点全落在段外 → 读出「?」。

    两个锚点都能从数字本身拿到，且和显示的是哪个数字无关：
    - **横向**：最后一格数字的**右边缘**就是格的右边界
      （「0」的右竖笔、「1」的 b/c 竖笔都在格的右沿），
      格的右边界 = 内区左沿 + (SLOT_X0 + 2*SLOT_PITCH + CELL_W) 单位
      = 内区左沿 + 36 单位 → 内区左沿 = 墨迹右边缘 - 36*s
    - **纵向**：数字在格子里是垂直居中的 → 墨迹的**竖直中心**就是格子的中心
      → 格子顶边 = 墨迹中心 - CELL_H*s/2
    """
    x0, y0, pw, ph = panel
    if pw < 30 or ph < 10:
        return None

    # 框里的白色墨迹 = 数字本身。
    # 注意要**避开面板外沿的白色高光**（斜角那圈有一侧是高光色），
    # 否则墨迹的包围盒就是整个框，锚点全废 —— 先往里收一圈再找。
    inset_x = max(3, int(pw * 0.06))
    inset_y = max(3, int(ph * 0.10))
    sub = im[y0 + inset_y:y0 + ph - inset_y, x0 + inset_x:x0 + pw - inset_x]
    white = _white_mask(sub)
    ys = np.where(white.any(axis=1))[0]
    xs = np.where(white.any(axis=0))[0]
    if len(ys) == 0 or len(xs) == 0:
        return None
    ink_x1 = x0 + inset_x + int(xs.max())     # 墨迹右边缘（设备像素）
    ink_cy = y0 + inset_y + (int(ys.min()) + int(ys.max())) / 2.0   # 墨迹竖直中心

    # 比例 s 的候选：面板内区高 17 单位，用墨迹高度先估一档（多数数字满高），
    # 再把上下两档都试一遍。
    ink_h = int(ys.max()) - int(ys.min()) + 1
    s_raw = ink_h / float(CELL_H)
    s0 = max(2.0, float(round(s_raw / 2.0) * 2))
    # 内区左沿 = 墨迹右边缘 - 36 单位
    span = SLOT_X0 + (SLOT_COUNT - 1) * SLOT_PITCH + CELL_W      # = 3 + 24 + 9 = 36

    best = None
    best_score = -1
    best_lit = -1
    for s in [s0 - 2, s0, s0 + 2]:
        if s < 2:
            continue
        outer_x = ink_x1 - span * s          # 面板精灵的左沿
        # 精灵的上沿：墨迹中心 = 精灵顶 + CELL_Y 单位（数字格的下沿）+ 格高的一半
        base_y = ink_cy - CELL_Y * s - CELL_H * s / 2.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                digits, bbox = _sample_slots(im, outer_x + dx * s, base_y + dy * s, s)
                # 评分：解出合法数字的槽位 +2；**读不出（非法掩码）的槽位 -3**；
                # 空槽（右边补零前的空位）算 0 分。
                # 不能给空槽加分 —— 采样整体偏掉时三个槽位全是空的，
                # 那样反而会「赢过」真正读对的那一档。
                score = 0
                lit = 0
                for m in digits:
                    lit += bin(m).count('1') if m else 0
                    if m == 0:
                        score += 0                  # 空槽（右对齐、不补零）
                    elif m == MASK_ONE_STD or m == MASK_ONE_BASE:
                        score += 2
                    elif m == MASK_MINUS:
                        score += 2                  # 负号段也是合法的一槽
                    elif m in MASKS:
                        score += 2
                    else:
                        score -= 3                  # 非法掩码 = 没采样对
                # **包围盒吻合判据**（2026-11-02 折叠屏实测加的）：
                # 光靠「掩码合法与否」不够 —— 采样偏掉一档时，
                # 有时也能凑出一个**合法**的数字掩码（实测 s=4 时把「3」读成
                # 一个不存在的组合，却因为在 MASKS 表里而被判成合法 ✗）。
                # 正确的那一档有个硬特征：**亮起来的段的并集范围，
                # 必须和墨迹的实际范围吻合**（差不超过 1 个参考单位）。
                # 采样偏了，亮的段要么盖不住墨迹、要么比墨迹多出一块 ✗。
                if bbox is not None:
                    ix0 = x0 + inset_x + int(xs.min())
                    iy0 = y0 + inset_y + int(ys.min())
                    iw = int(xs.max()) - int(xs.min()) + 1
                    ih = int(ys.max()) - int(ys.min()) + 1
                    tol = max(1.0, s * 0.35)
                    if (abs(bbox[0] - ix0) <= tol and abs(bbox[1] - iy0) <= tol
                            and abs(bbox[2] - iw) <= tol and abs(bbox[3] - ih) <= tol):
                        score += 4               # 严丝合缝
                    else:
                        score -= 4               # 对不上墨迹，基本是采样偏了
                if score > best_score or (score == best_score and best is not None
                                          and lit > best_lit):
                    best_score = score
                    best_lit = lit
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
