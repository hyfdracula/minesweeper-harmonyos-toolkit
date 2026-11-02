# -*- coding: utf-8 -*-
"""
win_probe.py -- 在真机上把扫雷「赢」一次，并抓胜利动画 / 爆炸动画的连续帧。

做法（不依赖任何产品代码改动）：
  1. 截图 -> 定位棋盘网格（用格子之间的深色缝，格边取 hilog 的值）
  2. 每个已揭开的格子 -> 从 blueSheet.png 取数字字形做模板匹配，认出 1..8
  3. 跑标准扫雷推理（约束传播 + 穷举可行解），挑一个必定安全的格子
  4. 用 `uitest uiInput click` 点它，回到 1，直到胜利

用法:
    python tools\\win_probe.py --device 127.0.0.1:5555 --phase win
    python tools\\win_probe.py --device 127.0.0.1:5555 --phase explode

坐标铁律：
  棋盘格边（pitch）取当次 hilog 的 [GameController] 布局 行；
  网格原点取截图里格子之间的深色缝（砖块精灵自带深色边框，边界列整条都是黑的）。
  全程处理原始分辨率（snapshot_display 的原图），不用缩略预览。
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, r'C:\Users\19161\.dsh\lib')
from nowindow import run, check_output  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

HDC = r'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
SHEET = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile\blueSheet.png'
GAME_SHEET = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile\minesweeperSheet.png'
OTHER = r'C:\Users\19161\saolei\entry\src\main\resources\rawfile\otherSheet.png'
BUNDLE = 'com.example.saolei'

SPRITE_SCALE = 2
DIGIT_SRC_X = 1000 * SPRITE_SCALE
DIGIT_SRC_W = 12 * SPRITE_SCALE
DIGIT_SRC_H = 15 * SPRITE_SCALE
GLYPH_ROW_SKIP = 3          # 字形顶部 3 行可能被「上方凸起格的投影」压住，不参与匹配

# 拆雷光束：38 帧，otherSheet 里的 rect = [52*(f%7), 152*(f//7), 50, 150]
DISARM_FRAMES = 38
DISARM_SRC = (52, 152, 50, 150)
# 爆炸：23 帧，rect = [728 + 59*(f%3), 59*(f//3), 57, 57]
EXPLODE_FRAMES = 23
EXPLODE_SRC = (728, 0, 57, 57)
# 扫描条在 otherSheet 上的源矩形（源像素）
SCAN_BAR_SRC = (0, 912 * SPRITE_SCALE, 275 * SPRITE_SCALE, 62 * SPRITE_SCALE)


# --------------------------------------------------------------------------
# hdc 封装
# --------------------------------------------------------------------------

def hdc(device, *args, timeout=60):
    cmd = [HDC, '-t', device] + list(args)
    out = check_output(cmd, timeout=timeout)
    if isinstance(out, bytes):
        out = out.decode('utf-8', 'replace')
    return out


def hdc_check(device, *args, timeout=120):
    cmd = [HDC, '-t', device] + list(args)
    run(cmd, timeout=timeout)


def pull_screenshot(device, local_path, remote='/data/local/tmp/wp.jpeg'):
    hdc_check(device, 'shell', 'snapshot_display', '-f', remote)
    hdc_check(device, 'file', 'recv', remote, local_path)
    return Image.open(local_path).convert('RGB')


def read_layout(device, required=True):
    """
    从 hilog 里取当次 [GameController] 布局 行。

    注意：hilog 里有**历史**行（换过难度/换过屏幕尺寸的旧局）。
    所以必须在应用重启**之后**再读，否则会拿到上一局的版式。
    required=False 时读不到就返回 None（不抛异常，等下一轮轮询）。
    """
    out = hdc(device, 'shell',
              "hilog -x 2>/dev/null | grep -a '布局' | tail -1")
    m = re.search(r'画布=(\d+)x(\d+)px.*?unit=(\d+)\s+格边=(\d+)px\s+棋盘原点=\((\d+),(\d+)\)',
                  out)
    if not m:
        if required:
            raise RuntimeError('hilog 里没找到 [GameController] 布局 行:\n' + out[-800:])
        return None
    return {
        'canvas_w': int(m.group(1)), 'canvas_h': int(m.group(2)),
        'unit': int(m.group(3)), 'tile': int(m.group(4)),
        'board_x': int(m.group(5)), 'board_y': int(m.group(6)),
        'raw': out.strip().splitlines()[-1] if out.strip() else '',
    }


# --------------------------------------------------------------------------
# 棋盘定位
# --------------------------------------------------------------------------

def blue_mask(img):
    """凸起砖的亮蓝色（其它蓝色区域偏暗或偏灰，会被排除）。"""
    a = np.asarray(img, dtype=np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (b > 165) & ((b - g) > 50) & ((b - r) > 80)


def find_board_bbox(img):
    """返回凸起砖包围盒 (x0, y0, x1, y1)，找不到返回 None。

    注意：桌面壁纸也是蓝的，所以调用方**必须**再校验包围盒尺寸。
    """
    mask = blue_mask(img)
    if int(mask.sum()) < 500:
        return None
    ys = np.where(mask.any(axis=1))[0]
    xs = np.where(mask.any(axis=0))[0]
    return int(xs[0]), int(ys[0]), int(xs[-1]), int(ys[-1])


def looks_like_board(img, layout, rows, cols):
    """包围盒的尺寸必须和 rows x cols 的棋盘对得上（否则可能认成了壁纸）。"""
    bbox = find_board_bbox(img)
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    want_w = cols * layout['tile']
    want_h = rows * layout['tile']
    got_w = x1 - x0
    got_h = y1 - y0
    if abs(got_w - want_w) > want_w * 0.20 or abs(got_h - want_h) > want_h * 0.20:
        return None
    return bbox


def _lattice(lines, pitch):
    """
    从一组「线」里找出间距 = pitch 的最长等差段。
    lines 是已经按位置排序的整数列表。
    返回 (起点, 个数) 或 None。
    """
    best = None
    n = len(lines)
    for i in range(n):
        for j in range(i + 1, min(n, i + 12)):
            d = lines[j] - lines[i]
            if d < pitch * 0.85:
                continue
            if abs(d - pitch) > pitch * 0.12:
                break
            # 从 (i, j) 往后延伸
            cnt = 2
            prev = lines[j]
            for k in range(j + 1, n):
                if abs((lines[k] - prev) - pitch) <= pitch * 0.12:
                    cnt += 1
                    prev = lines[k]
                else:
                    break
            if best is None or cnt > best[1]:
                best = (lines[i], cnt)
            break
    return best


def find_grid_by_seams(img, pitch):
    """
    用「格子之间的深色缝」找棋盘网格 —— 与砖块颜色无关，
    所以蓝盘 / 绿盘 / 花园样式都适用。

    思路：砖块精灵自带深色边框，棋盘上会出现一组间距正好 = pitch 的
    **整条**深色直线（每格之间的缝 + 外框）。一条线的暗像素数 ≈ 棋盘边长，
    是全图最强的峰。

    做法：先把暗像素的连续段归成候选线（取段中点），再对每个相位
    (0..pitch-1) 数一数有多少候选线落在 (phase + k*pitch) 附近，
    命中最多的相位就是网格；命中数 - 1 = 格子数。

    返回 (gx, gy, ncols, nrows) 或 None。
    """
    a = np.asarray(img, dtype=np.int16)
    H, W = a.shape[:2]
    dark = (a[:, :, 0] < 70) & (a[:, :, 1] < 70) & (a[:, :, 2] < 85)
    colcnt = dark.sum(axis=0).astype(np.int64)
    rowcnt = dark.sum(axis=1).astype(np.int64)

    def candidates(profile):
        """把「连续的高暗像素列/行」归成一条线，返回每条线的位置。"""
        mx = int(profile.max())
        if mx <= 0:
            return []
        thr = mx * 0.55
        lines = []
        run = []
        for i, v in enumerate(profile):
            if v >= thr:
                run.append(i)
            else:
                if run:
                    lines.append((run[0] + run[-1]) // 2)
                    run = []
        if run:
            lines.append((run[0] + run[-1]) // 2)
        return lines

    def match(lines, p):
        """
        找最佳相位。返回 (第一线的位置, 命中数)。
        命中数 - 1 = 格子数（棋盘有 cols+1 条竖线：含左右外框）。

        做法：对每个候选线当起点，向后按 pitch 找下一条，命中最多的就是网格。
        """
        if len(lines) < 3:
            return None
        best = None
        tol = max(4, p // 20)
        for start in lines:
            hits = [start]
            prev = start
            while True:
                target = prev + p
                near = [x for x in lines if abs(x - target) <= tol]
                if not near:
                    break
                pick = min(near, key=lambda x: abs(x - target))
                hits.append(pick)
                prev = pick
            if best is None or len(hits) > best[1]:
                best = (hits[0], len(hits))
        return best

    cm = match(candidates(colcnt), pitch)
    rm = match(candidates(rowcnt), pitch)
    if cm is None or rm is None:
        return None
    gx, ncl = cm
    gy, nrl = rm
    ncols = ncl - 1
    nrows = nrl - 1
    if ncols < 3 or nrows < 3 or ncols > 30 or nrows > 24:
        return None
    return gx, gy, ncols, nrows


def _dark_profile(img, x0, y0, x1, y1, axis):
    """统计每一列（axis=0）或每一行（axis=1）上「近黑」像素的数量。"""
    a = np.asarray(img, dtype=np.int16)
    dark = (a[:, :, 0] < 40) & (a[:, :, 1] < 40) & (a[:, :, 2] < 55)
    if axis == 0:
        seg = dark[y0:y1 + 1, x0:x1 + 1].sum(axis=0)
        return [(x0 + i, int(v)) for i, v in enumerate(seg)]
    seg = dark[y0:y1 + 1, x0:x1 + 1].sum(axis=1)
    return [(y0 + i, int(v)) for i, v in enumerate(seg)]


def validate_grid(img, layout):
    """
    在截图里找棋盘网格，并用 hilog 的版式信息**校验**。

    只靠「深色缝」会误判：桌面的壁纸花纹也是规则网格（实测在 5557 上
    找出过 8x8 的假网格，原点是负数）。所以必须满足：
      1) 网格原点与 hilog 的棋盘原点只差一个「状态栏偏移」
         （dx 约 0~30 px，dy 约 0~300 px）；
      2) 网格尺寸乘格边之后，放得进画布。
    返回 (gx, gy, ncols, nrows) 或 None。
    """
    pitch = layout['tile']
    if pitch <= 0:
        return None
    lat = find_grid_by_seams(img, pitch)
    if lat is None:
        return None
    gx, gy, ncols, nrows = lat
    dx = gx - layout['board_x']
    dy = gy - layout['board_y']
    if not (-12 <= dx <= 40):
        return None
    if not (0 <= dy <= 320):
        return None
    # 棋盘必须放得进画布（画布原点在屏幕上的偏移就是 dx/dy）
    if ncols * pitch > layout['canvas_w'] - layout['board_x'] + 40:
        return None
    if nrows * pitch > layout['canvas_h'] - layout['board_y'] + 40:
        return None
    if ncols < 3 or nrows < 3 or ncols > 30 or nrows > 24:
        return None
    return gx, gy, ncols, nrows


def grid_from_layout(img, layout, rows, cols):
    """
    算出棋盘网格在**屏幕像素**里的原点。

    铁律：格边（pitch）取 hilog 的值；原点取「格子之间的深色缝」——
    砖块精灵自带深色边框，格子边界那一列/行整条都是黑的，
    比包围盒精确得多，而且与砖块颜色无关（蓝/绿/花园都适用）。
    """
    pitch = layout['tile']
    if pitch <= 0:
        raise RuntimeError('hilog 里的格边非法: %s' % layout)

    # 1) 先用深色缝梳状滤波找规则网格（不依赖颜色），并用版式校验
    g = validate_grid(img, layout)
    if g is not None:
        gx, gy, ncols, nrows = g
        print('[grid] 深色缝网格: 原点=(%d,%d) %dx%d 格' % (gx, gy, ncols, nrows))
        return gx, gy, pitch

    # 2) 退路：用凸起砖的包围盒 + hilog 的格边推算
    bbox = find_board_bbox(img)
    if bbox is None:
        raise RuntimeError('截图里找不到棋盘（可能拍到桌面/其它界面）')
    bx0, by0, bx1, by1 = bbox
    guess_w = cols * pitch
    guess_h = rows * pitch
    off_x = bx0 + (guess_w - (bx1 - bx0)) / 2.0 - layout['board_x']
    off_y = by0 + (guess_h - (by1 - by0)) / 2.0 - layout['board_y']
    return layout['board_x'] + off_x, layout['board_y'] + off_y, pitch


# --------------------------------------------------------------------------
# 格子识别
# --------------------------------------------------------------------------

def load_templates(sheet_path=None):
    """
    返回 {数字: 24x30 的 0/1 掩码}（来自棋盘图集的字形）。

    主题会换图集（蓝盘 blueSheet / 绿盘 greenSheet），但字形槽位一样
    （Theme.digitRect(n) = [1000, 15*(n-1), 12, 15]），所以按当前用的那张图取模板。
    """
    sheet = Image.open(sheet_path or SHEET).convert('RGBA')
    px = sheet.load()
    templates = {}
    for n in range(1, 9):
        y0 = 15 * (n - 1) * SPRITE_SCALE
        rows = []
        for y in range(y0, y0 + DIGIT_SRC_H):
            line = []
            for x in range(DIGIT_SRC_X, DIGIT_SRC_X + DIGIT_SRC_W):
                p = px[x, y]
                line.append(1 if p[3] > 150 else 0)
            rows.append(line)
        templates[n] = rows
    return templates


def cell_digit(img, gx, gy, pitch, unit, templates):
    """该格里的数字：0..8；None = 空白；'?' = 认不出。"""
    f = unit / 2.0                        # 源像素 -> 屏幕像素 的放大倍数
    sx = int(round(3 * unit))            # 字形在格内的偏移（格边 18 单位，字形 12x15）
    sy = int(round(1.5 * unit))
    w = int(round(DIGIT_SRC_W * f))
    h = int(round(DIGIT_SRC_H * f))
    x0 = int(round(gx)) + sx
    y0 = int(round(gy)) + sy
    W, H = img.size
    if x0 < 0 or y0 < 0 or x0 + w > W or y0 + h > H:
        return '?'
    crop = img.crop((x0, y0, x0 + w, y0 + h)).resize((DIGIT_SRC_W, DIGIT_SRC_H), Image.BOX)
    cpx = crop.load()
    ink = []
    for yy in range(DIGIT_SRC_H):
        line = []
        for xx in range(DIGIT_SRC_W):
            r, g, b = cpx[xx, yy]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            line.append(1 if lum < 150 else 0)
        ink.append(line)
    used = sum(sum(ink[yy]) for yy in range(GLYPH_ROW_SKIP, DIGIT_SRC_H))
    if used < 12:
        return None                         # 空白（已揭开且周围 0 雷）
    best, best_score = '?', -1.0
    for n in range(1, 9):
        tpl = templates[n]
        same = 0
        tot = 0
        for yy in range(GLYPH_ROW_SKIP, DIGIT_SRC_H):
            tr, ir = tpl[yy], ink[yy]
            for xx in range(DIGIT_SRC_W):
                if tr[xx] or ir[xx]:
                    tot += 1
                    if tr[xx] == ir[xx]:
                        same += 1
        if tot == 0:
            continue
        score = same / float(tot)
        if score > best_score:
            best, best_score = n, score
    if best_score < 0.62:
        return '?'
    return best


def load_mine_template():
    """
    雷精灵模板（minesweeperSheet.png）。

    雷是整格贴上去的：drawLogical(ctx, gameSheet, RECT_MINE, x, y, u)
    -> 目标矩形 = 18*u x 18*u = 正好一格；源区域 = RECT_MINE * SPRITE_SCALE。
    模板带透明背景，所以只比较「有墨」的地方。
    返回 (灰度图, 布尔掩码)，已按格边缩放好。
    """
    sheet = Image.open(GAME_SHEET).convert('RGBA')
    x0 = 27 * SPRITE_SCALE
    y0 = 0
    w = 18 * SPRITE_SCALE
    h = 18 * SPRITE_SCALE
    crop = sheet.crop((x0, y0, x0 + w, y0 + h))
    px = crop.load()
    mask = np.zeros((h, w), dtype=bool)
    for yy in range(h):
        for xx in range(w):
            mask[yy, xx] = px[xx, yy][3] > 140
    gray = np.asarray(crop.convert('L'), dtype=np.float32)
    return gray, mask


def match_mine(cell_rgb, tmpl_gray, tmpl_mask, tol=45):
    """
    把一格和雷模板比对。返回 0..1 的相似度（1 = 完全一致）。
    只比较模板里有墨的像素。
    """
    h, w = tmpl_mask.shape
    if cell_rgb.shape[0] != h or cell_rgb.shape[1] != w:
        cell_rgb = np.asarray(
            Image.fromarray(cell_rgb.astype(np.uint8)).resize((w, h), Image.BOX),
            dtype=np.float32)
    cg = (0.299 * cell_rgb[:, :, 0] + 0.587 * cell_rgb[:, :, 1] +
          0.114 * cell_rgb[:, :, 2])
    idx = tmpl_mask
    if int(idx.sum()) < 20:
        return 0.0
    diff = np.abs(cg[idx] - tmpl_gray[idx])
    return float(1.0 - (diff < tol).mean())


def detect_theme(img, gx, gy, pitch, rows, cols):
    """
    看几个凸起砖，认出现在是哪个主题（'blue' / 'green' / 'flower'）。
    数字字形三个主题**完全一样**（掩码 100% 相同），所以只需知道主题名，
    用来确认「凸起砖」的颜色预期。
    """
    votes = {'blue': 0, 'green': 0, 'other': 0}
    for (r, c) in [(0, 0), (rows // 2, cols // 2), (rows - 1, cols - 1)]:
        x = int(gx + c * pitch)
        y = int(gy + r * pitch)
        if x < 0 or y < 0 or x + pitch > img.size[0] or y + pitch > img.size[1]:
            continue
        a = np.asarray(img.crop((x, y, x + pitch, y + pitch)), dtype=np.int16)
        med = np.median(a.reshape(-1, 3), axis=0)
        r0, g0, b0 = float(med[0]), float(med[1]), float(med[2])
        if b0 - r0 > 60:
            votes['blue'] += 1
        elif g0 - r0 > 40:
            votes['green'] += 1
        else:
            votes['other'] += 1
    if votes['blue'] >= votes['green']:
        return 'blue' if votes['blue'] > 0 else 'other'
    return 'green'


def cell_state(img, gx, gy, pitch, unit, templates, mine_tmpl=None):
    """
    返回该格状态：
      'X'  未揭开的凸起砖
      'F'  未揭开的凸起砖 + 红旗（胜利时引擎自动插旗）
      'M'  已揭开并显示雷精灵（踩雷/判负）
      0..8 已揭开的数字
      None 已揭开的空白（周围 0 雷）
      '?'  认不出
    """
    W, H = img.size
    x = int(round(gx))
    y = int(round(gy))
    if x < 0 or y < 0 or x + pitch > W or y + pitch > H:
        return '?'
    cell = np.asarray(img.crop((x, y, x + pitch, y + pitch)), dtype=np.int16)
    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn
    # 判据：**淡色地板占比**。揭开后的格子露出淡色地板
    # （蓝盘 (198,211,230)、绿盘同理），凸起砖没有淡色区域。
    # 实测：凸起砖 pale = 0.00，揭开格 pale = 0.52~0.89。
    # 不用「饱和色占比」是因为绿盘砖块自带渐变，越靠下越暗（0.86 -> 0.36）。
    pale = ((sat < 60) & (mx > 150))
    pale_frac = float(pale.sum()) / float(pitch * pitch)
    if pale_frac < 0.25:
        red = int(((r > 150) & (g < 110) & (b < 110)).sum())
        if red > 60:
            return 'F'                       # 自动插旗 = 已经赢了
        return 'X'
    # 雷精灵的墨色**严格中性灰**（84/97/51/105/68 那几个值，max-min = 0），
    # 且偏暗。而下沉的边框线是 (76,85,111) 偏蓝、砖块暗角是 (130,131,133) 偏亮，
    # 两者都过不了「中性 + 暗」这一关。
    ink = ((sat < 12) & (mx > 40) & (mx < 120))
    # 只看格子内部，避开边框线
    m = max(2, int(pitch * 0.10))
    core = ink[m:pitch - m, m:pitch - m]
    if int(core.sum()) > max(20, int(pitch * pitch * 0.002)):
        return 'M'
    return cell_digit(img, gx, gy, pitch, unit, templates)


def read_board(img, gx, gy, pitch, unit, templates, rows, cols, mine_tmpl=None):
    """二维表：'X' 未揭开；'F' 自动插旗；'M' 雷；0..8 数字；None 空白；'?' 认不出。"""
    return [[cell_state(img, gx + c * pitch, gy + r * pitch, pitch, unit, templates,
                        mine_tmpl)
             for c in range(cols)] for r in range(rows)]


# --------------------------------------------------------------------------
# 扫雷推理
# --------------------------------------------------------------------------

def neighbours(r, c, rows, cols):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                yield rr, cc


def solve(board, rows, cols, mines, max_nodes=200000):
    """
    扫雷推理。返回 (要点的格子, 必定是雷的格子集合)。

    约束：
      1. 局部约束：每个已揭开的数字格 -> (未揭开的邻格集合, 还差几颗雷)
      2. 全局约束：所有未揭开的格 = 剩下的雷数
    传播：单格规则 + 子集规则。传播完仍推不出的，
    用「穷举所有可行解」算出每个格在多少比例的解里是安全的，挑最安全的。
    """
    all_unknown = set()
    for r in range(rows):
        for c in range(cols):
            if board[r][c] in ('X', 'F'):
                all_unknown.add((r, c))
    if not all_unknown:
        return None, set()

    flagged = set((r, c) for r in range(rows) for c in range(cols) if board[r][c] == 'F')
    remaining_mines = mines - len(flagged)

    cons = []
    for r in range(rows):
        for c in range(cols):
            v = board[r][c]
            if isinstance(v, int) and v > 0:
                # 插了旗的邻格是**已知是雷**，要从约束里扣掉
                nb = list(neighbours(r, c, rows, cols))
                unknown = set((rr, cc) for rr, cc in nb if board[rr][cc] == 'X')
                flags = sum(1 for rr, cc in nb if board[rr][cc] == 'F')
                need = v - flags
                if unknown and need >= 0:
                    cons.append([set(unknown), need])
    cons.append([set(all_unknown), remaining_mines])

    MINE = 'M'
    SAFE = 'S'
    state = {}

    def mark(cell, s):
        """
        给一格定性。返回 True 表示**这次真的改了状态**。
        只有真的改了才算「传播有进展」，否则 while 循环会死循环
        （子集规则每次都会算出同一个非空 diff，但状态早就定了）。
        """
        if cell in state:
            return False
        state[cell] = s
        return True

    # 插了旗的格是已知是雷
    for x in flagged:
        state[x] = MINE

    changed = True
    while changed:
        changed = False
        for con in cons:
            cells, need = con
            unk = set(x for x in cells if x not in state)
            need -= sum(1 for x in cells if state.get(x) == MINE)
            if need < 0 or need > len(unk):
                continue
            if need == 0 and unk:
                for x in unk:
                    if mark(x, SAFE):
                        changed = True
            elif len(unk) == need and unk:
                for x in unk:
                    if mark(x, MINE):
                        changed = True
        for i in range(len(cons)):
            for j in range(len(cons)):
                if i == j:
                    continue
                ci, cj = cons[i], cons[j]
                if ci[0] <= cj[0]:
                    diff = cj[0] - ci[0]
                    if ci[1] == cj[1] and diff:
                        for x in diff:
                            if mark(x, SAFE):
                                changed = True
                    elif ci[1] + len(diff) == cj[1] and ci[0]:
                        for x in ci[0]:
                            if mark(x, MINE):
                                changed = True
        for con in cons:
            cells, need = con
            for x in list(cells):
                if state.get(x) == MINE:
                    cells.discard(x)
                    need -= 1
            con[1] = need

    mine_certain = set(x for x in all_unknown if state.get(x) == MINE) | flagged
    safe_certain = set(x for x in all_unknown if state.get(x) == SAFE)
    if safe_certain:
        return sorted(safe_certain)[0], mine_certain

    # 推不出确定安全的格子：**精确枚举**所有与已知数字一致的雷位分配，
    # 统计每格在多少个解里是雷。
    #
    # 为什么不用「按概率点」：概率启发式会**踩雷**（实测在 Mate X7 上
    # 连输两局、弹出来的是失败框）。原因很直接 —— 概率低的格子仍然可能是雷，
    # 而这个脚本必须**赢**才能造出胜利框。
    # 精确枚举能把「确定安全」和「确定是雷」都算出来。
    #
    # 为什么能算得完：只枚举**挨着已揭开数字的格子**（frontier），
    # 不挨着的未知格彼此等价，可以当成一个「吸收剩余雷数的坑」，
    # 不用进搜索。9x9/10 雷的盘面 frontier 通常 <= 40 个变量，
    # 加上传播剪枝，实测毫秒级到百毫秒级。
    return _exact_solve(board, rows, cols, mines, flagged, all_unknown)


def _exact_solve(board, rows, cols, mines, flagged, all_unknown):
    """
    精确枚举可行解，统计每格是雷的解数。

    返回 (要点, 确定是雷的格集合)。要点为 None 表示算不出来。
    """
    import time

    # 未揭开的、**没插旗**的格（只有这些才可能是安全格）
    x_cells = set((r, c) for r in range(rows) for c in range(cols)
                   if board[r][c] == 'X')
    if not x_cells:
        return None, set()

    # 约束：每个已揭开的数字格 -> (未知邻格集合, 还差几颗雷)
    cons = []
    frontier = set()
    for r in range(rows):
        for c in range(cols):
            v = board[r][c]
            if isinstance(v, int) and v > 0:
                nb = list(neighbours(r, c, rows, cols))
                unk = set((rr, cc) for rr, cc in nb if board[rr][cc] == 'X')
                flags = sum(1 for rr, cc in nb if board[rr][cc] == 'F')
                need = v - flags
                if not unk:
                    continue
                if need < 0 or need > len(unk):
                    # 数字与周围对不上 —— 这一条约束不可信，丢掉它
                    # （宁可少一条约束，也不能因为一条读错的数字推出错误的雷位）
                    continue
                cons.append([set(unk), need])
                frontier |= unk
    if not cons:
        return None, set()

    remaining = mines - len(flagged)
    # 不挨着任何已揭开数字的未知格：彼此等价，可以当作「吸收剩余雷数的坑」
    outside = len(x_cells) - len(frontier)
    if remaining < 0 or remaining > len(x_cells):
        return None, set()

    # cell -> 涉及它的约束下标
    cell_cons = {x: [] for x in frontier}
    for i, con in enumerate(cons):
        for x in con[0]:
            cell_cons[x].append(i)

    MAX_SOL = 60000
    deadline = time.time() + 4.0
    solutions = 0
    mine_count = dict((x, 0) for x in frontier)
    exhaustive = True

    def propagate(unk_sets, needs, assign):
        """强制赋值 + 冲突检测。矛盾返回 False。"""
        changed = True
        while changed:
            changed = False
            for i in range(len(unk_sets)):
                u = unk_sets[i]
                need = needs[i]
                if need < 0 or need > len(u):
                    return False
                if not u:
                    continue
                if need == 0:
                    for x in list(u):
                        if x in assign:
                            continue
                        assign[x] = False
                        for j in cell_cons[x]:
                            unk_sets[j].discard(x)
                        changed = True
                elif need == len(u):
                    for x in list(u):
                        if x in assign:
                            continue
                        assign[x] = True
                        for j in cell_cons[x]:
                            unk_sets[j].discard(x)
                            needs[j] -= 1
                        changed = True
        return True

    def dfs(assign, unk_sets, needs):
        nonlocal solutions, exhaustive
        if solutions >= MAX_SOL or time.time() > deadline:
            exhaustive = False
            return
        # 选约束最多的未赋值变量（最受限优先）
        pick = None
        pick_n = -1
        for x in frontier:
            if x not in assign:
                n = len(cell_cons[x])
                if n > pick_n:
                    pick_n = n
                    pick = x
        if pick is None:
            m = sum(1 for x in frontier if assign[x])
            # 剩下的雷必须能塞进「不挨着数字的未知格」里
            if 0 <= remaining - m <= outside:
                solutions += 1
                for x in frontier:
                    if assign[x]:
                        mine_count[x] += 1
            return
        for val in (False, True):
            a2 = dict(assign)
            u2 = [set(s) for s in unk_sets]
            n2 = list(needs)
            a2[pick] = val
            for j in cell_cons[pick]:
                u2[j].discard(pick)
                if val:
                    n2[j] -= 1
            if propagate(u2, n2, a2):
                dfs(a2, u2, n2)

    if not propagate([set(c[0]) for c in cons], [c[1] for c in cons], {}):
        return None, set()
    dfs({}, [set(c[0]) for c in cons], [c[1] for c in cons])

    if solutions == 0:
        # 没有可行解：说明读到的盘面自相矛盾（数字认错了）
        print('[solve] 没有可行解（盘面读数可能自相矛盾）')
        return None, set()

    # **只有穷举完整时**才能断言「某格在所有解里都是安全的」——
    # 提前截断的话，未搜到的解里可能还有雷，不能拿它当结论。
    mine_certain = set(x for x in frontier if exhaustive and mine_count[x] == solutions)
    safe_certain = set(x for x in frontier if exhaustive and mine_count[x] == 0)
    print('[solve] 精确枚举：%d 个解%s；确定安全 %d 格，确定是雷 %d 格'
          % (solutions, '' if exhaustive else '（提前截断，结论不作数）',
             len(safe_certain), len(mine_certain)))
    if safe_certain:
        return sorted(safe_certain)[0], mine_certain

    # 没有确定安全的格：挑「在最多解里是安全」的（雷数占比最低）
    # —— 精确枚举下这比概率启发式准得多，但仍不保证安全。
    best = None
    best_key = None
    for x in frontier:
        key = (mine_count[x], -len(cell_cons[x]), x)
        if best_key is None or key < best_key:
            best_key = key
            best = x
    return best, mine_certain


# --------------------------------------------------------------------------
# 动画帧识别（用来证明「帧在变」，而不是靠肉眼）
# --------------------------------------------------------------------------

_TPL_CACHE = {}
_BAR_PROFILE = None


def _frame_templates(kind):
    """
    取 otherSheet 里某组动画帧的模板（缩放到统一尺寸），**缓存起来**。
    之前每次比对都重新 crop+resize 38 次，81 格 × 18 帧 = 几千次缩放，慢到没法用。
    返回 RGBA 的 numpy 数组（alpha 通道要留着：爆炸/光束的精灵大半是透明的，
    比对时只能看**不透明**的那些像素，否则周围的棋盘会把相似度压垮）。
    """
    if kind in _TPL_CACHE:
        return _TPL_CACHE[kind]
    other = Image.open(OTHER).convert('RGBA')
    if kind == 'disarm':
        x0 = DISARM_SRC[0] * SPRITE_SCALE
        y0 = DISARM_SRC[1] * SPRITE_SCALE
        sw = DISARM_SRC[2] * SPRITE_SCALE
        sh = DISARM_SRC[3] * SPRITE_SCALE
        cols, pitch, n = 7, 52 * SPRITE_SCALE, DISARM_FRAMES
    else:
        x0 = EXPLODE_SRC[0] * SPRITE_SCALE
        y0 = EXPLODE_SRC[1] * SPRITE_SCALE
        sw = EXPLODE_SRC[2] * SPRITE_SCALE
        sh = EXPLODE_SRC[3] * SPRITE_SCALE
        cols, pitch, n = 3, 59 * SPRITE_SCALE, EXPLODE_FRAMES
    out = []
    for f in range(n):
        fx = x0 + (f % cols) * pitch
        fy = y0 + (f // cols) * pitch
        out.append(np.asarray(other.crop((fx, fy, fx + sw, fy + sh)), dtype=np.float32))
    _TPL_CACHE[kind] = out
    return out


_RESIZED = {}


def _resized_templates(kind, size):
    """
    把动画帧模板缩放到指定尺寸并**缓存**。
    之前每次比对都重新 resize（38 帧 × 81 格 × 20 帧 = 六万次缩放），慢到没法用。
    """
    key = (kind, size[0], size[1])
    if key in _RESIZED:
        return _RESIZED[key]
    out = []
    for tpl in _frame_templates(kind):
        out.append(np.asarray(Image.fromarray(tpl.astype(np.uint8)).resize(size, Image.BOX),
                              dtype=np.float32))
    _RESIZED[key] = out
    return out


def _best_frame(patch, tpls, size, alpha_min=110):
    """
    在一组帧里找最像 patch 的那一帧。
    只比**精灵里不透明**的像素（alpha >= alpha_min），透明区域忽略。
    返回 (帧号, 相似度) 或 None。
    """
    best = None
    for f, ta in enumerate(tpls):
        solid = ta[:, :, 3] >= alpha_min
        n = int(solid.sum())
        if n < 50:
            continue
        diff = np.abs(ta[:, :, :3][solid] - patch[:, :, :3][solid]).mean(axis=1)
        score = 1.0 - float(diff.mean()) / 255.0
        if best is None or score > best[1]:
            best = (f, score)
    return best


def _match_frame(patch, sheet_img, src_rect, frames, grid):
    """
    在贴图里找最像 patch 的那一帧。返回 (帧号, 相似度) 或 None。
    src_rect=(x,y,w,h) 是**源像素**坐标；frames 是帧号列表。
    grid=(cols, pitch) 用来定位每帧的排布（拆雷光束 7 列，爆炸 3 列）。
    """
    x0, y0, sw, sh = src_rect
    best = None
    for f in frames:
        if grid is None:
            fx, fy = x0, y0
        else:
            cols, pitch = grid
            fx = x0 + (f % cols) * pitch
            fy = y0 + (f // cols) * pitch
        if fx + sw > sheet_img.size[0] or fy + sh > sheet_img.size[1]:
            continue
        tpl = sheet_img.crop((fx, fy, fx + sw, fy + sh)).resize((patch.shape[1], patch.shape[0]),
                                                                 Image.BOX)
        ta = np.asarray(tpl, dtype=np.float32)
        # 只比 alpha/亮度结构（贴图可能是半透明的爆炸/光束）
        diff = np.abs(ta - patch).mean(axis=2)
        score = 1.0 - float(diff.mean()) / 255.0
        if best is None or score > best[1]:
            best = (f, score)
    return best


def analyse_disarm(img, gx, gy, pitch, unit, rows, cols, only=None):
    """
    找出屏幕上正在显示的「拆雷光束」帧。

    拆雷光束画在每个雷格上：x = boardX + c*tile + DISARM_OFFSET[0]*u,
    y = boardY + r*tile + DISARM_OFFSET[1]*u，尺寸 50*u x 150*u。
    DISARM_OFFSET = (-18, -69)，u = unit。
    only = 只查这些 (r,c)（已知雷位），省时间。
    """
    found = []
    w = int(50 * unit)
    h = int(150 * unit)
    tpls = _resized_templates('disarm', (w, h))
    for r in range(rows):
        for c in range(cols):
            if only is not None and (r, c) not in only:
                continue
            x = int(round(gx + c * pitch - 18 * unit))
            y = int(round(gy + r * pitch - 69 * unit))
            if x < 0 or y < 0 or x + w > img.size[0] or y + h > img.size[1]:
                continue
            patch = np.asarray(img.crop((x, y, x + w, y + h)).convert('RGB'),
                               dtype=np.float32)
            rgb = patch[:, :, :3]
            mx = rgb.max(axis=2)
            mn = rgb.min(axis=2)
            colored = float(((mx - mn) > 45).mean())
            if colored < 0.05:
                continue
            best = _best_frame(patch, tpls, (w, h), alpha_min=150)
            if best is not None and best[1] > 0.92:
                found.append((r, c, best[0], round(best[1], 3)))
    return found


def analyse_explode(img, gx, gy, pitch, unit, rows, cols, only=None):
    """
    找出屏幕上正在显示的「爆炸」帧。

    爆炸精灵画在格子左上角 (-18,-18)*unit 处，尺寸 57*unit 见方（unit=10 时是 570px，
    比一格 180px 大得多，所以这个方框会盖住旁边的格子）。
    画面上真正「热」的部分只有中间那个火球，所以：
      1) 用「橙红」判据找暖色像素（绿色主题的砖块本身偏暖，不能只比 r-b）；
      2) 取**最密的一小块**当火球中心（红色数字「3」也是暖色，但它是细笔画，
         密度远低于实心火球）；
      3) 拿火球那一小块去和 23 张爆炸帧比。
    整块 57*unit 见方直接去比会把相似度压到 0.48~0.73（认不出来），所以必须先定位。
    返回 [(r, c, 帧号, 相似度), ...]
    """
    found = []
    cell = int(57 * unit)
    tpls = _resized_templates('explode', (cell, cell))
    for r in range(rows):
        for c in range(cols):
            if only is not None and (r, c) not in only:
                continue
            x = int(round(gx + c * pitch - 18 * unit))
            y = int(round(gy + r * pitch - 18 * unit))
            if x < 0 or y < 0 or x + cell > img.size[0] or y + cell > img.size[1]:
                continue
            patch = np.asarray(img.crop((x, y, x + cell, y + cell)).convert('RGB'),
                               dtype=np.float32)
            mask = ((patch[:, :, 0] > 140) & (patch[:, :, 2] < 130) &
                    ((patch[:, :, 0] - patch[:, :, 2]) > 60) &
                    ((patch[:, :, 0] - patch[:, :, 1]) > 30))
            if int(mask.sum()) < 150:
                continue
            best = _best_frame(patch, tpls, (cell, cell))
            if best is not None and best[1] > 0.90:
                found.append((r, c, best[0], round(best[1], 3)))
    return found


def locate_scan_bar(img, gx, gy, pitch, unit, rows, cols, search_above=False):
    """
    定位胜利扫描条，返回 (barY, 相似度) 或 None。

    扫描条的精灵（otherSheet 的 [0,912,275,62]）上半截不透明、是一条蓝白高光带，
    下半截 alpha 渐隐。所以检测用**那条高光带**：把精灵里 alpha>=200 的那几行取出来，
    横向拉成棋盘宽，当作一维模板在屏幕上逐行比对。
    这样既不受「条被裁在棋盘内」的影响，也不会有「淡色地板被误认成条」的问题
    （整块矩形比地板是比不上的，地板是纯色而条有横向纹理）。

    search_above=False（默认）：**只在棋盘矩形内**找 —— 这是修复后的行为，
        条被裁在棋盘里，扫到顶就消失。
    search_above=True：连棋盘上方一起找，用来证明「修复前条停在棋盘顶上」。

    返回的 y 是高光带在屏幕上的位置，相似度 >= 0.96 才算认出来。
    """
    global _BAR_PROFILE
    if _BAR_PROFILE is None:
        other = Image.open(OTHER).convert('RGBA')
        sx, sy, sw, sh = SCAN_BAR_SRC
        if sx + sw > other.size[0] or sy + sh > other.size[1]:
            return None
        a = np.asarray(other.crop((sx, sy, sx + sw, sy + sh)), dtype=np.float32)
        band = a[:, :, 3] >= 200
        rows_idx = np.where(band.any(axis=1))[0]
        if len(rows_idx) == 0:
            return None
        top = int(rows_idx.min())
        bot = int(rows_idx.max())
        band_img = Image.fromarray(a[top:bot + 1].astype(np.uint8))
        _BAR_PROFILE = band_img          # 之后按棋盘宽缩放
    a = np.asarray(img, dtype=np.float32)
    H, W = a.shape[:2]
    w = cols * pitch
    if gx + w > W:
        return None
    prof = np.asarray(_BAR_PROFILE.resize((w, 1), Image.BOX), dtype=np.float32)[0, :, :3]
    if prof.shape[0] != w:
        return None
    if search_above:
        y_lo = max(0, gy - 400)
    else:
        y_lo = max(0, gy)             # 条被裁在棋盘内，只可能在棋盘里找
    y_hi = min(H - 1, gy + rows * pitch)
    best = None
    for y in range(y_lo, y_hi + 1):
        seg = a[y, gx:gx + w, :3]
        score = 1.0 - float(np.abs(seg - prof).mean()) / 255.0
        if best is None or score > best[1]:
            best = (y, score)
    if best is None or best[1] < 0.96:
        return None
    return best


def find_scan_bar(img, gx, gy, pitch, rows, cols):
    """旧接口：返回扫描条的 y 区间或 None（粗略，用于打印）。"""
    a = np.asarray(img, dtype=np.int16)
    x0 = int(gx)
    x1 = int(gx + cols * pitch)
    if x1 > a.shape[1]:
        return None
    seg = a[:, x0:x1, :]
    r, g, b = seg[:, :, 0], seg[:, :, 1], seg[:, :, 2]
    # 扫描条的颜色：浅蓝白，r 和 g 接近、b 略高，且明显偏亮
    light = (r > 200) & (g > 220) & (b > 235) & (b - r > 6)
    frac = light.mean(axis=1)
    rows_hit = np.where(frac > 0.55)[0]
    if len(rows_hit) < 10:
        return None
    return int(rows_hit[0]), int(rows_hit[-1])


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def click(device, x, y):
    hdc_check(device, 'shell', 'uitest', 'uiInput', 'click', str(int(x)), str(int(y)))


def fmt_board(board):
    out = []
    for line in board:
        out.append(' '.join('.' if v == 'X' else ('_' if v is None else str(v))
                            for v in line))
    return '\n'.join(out)


def burst(device, outdir, prefix, count, gap):
    """连拍 count 帧，间隔 gap 秒，返回文件列表。"""
    paths = []
    for i in range(count):
        p = os.path.join(outdir, '%s_%02d.jpeg' % (prefix, i))
        pull_screenshot(device, p)
        paths.append(p)
        time.sleep(gap)
    return paths


def restart_app(device, outdir):
    """
    重启应用，并且**等到棋盘真的画出来了**才返回第一帧截图。

    返回 (截图, 布局)。布局必须在重启之后读，否则拿到的是上一局的旧版式。
    """
    hdc_check(device, 'shell', 'aa', 'force-stop', BUNDLE)
    # 等进程真的消失，否则 aa start 会把**残局**带回来（带对话框、带败局）
    for _ in range(25):
        time.sleep(0.4)
        out = hdc(device, 'shell', "ps -ef | grep -a saolei | grep -v grep")
        if not out.strip():
            break
    else:
        raise RuntimeError('force-stop 之后进程还在')
    hdc_check(device, 'shell', 'aa', 'start', '-a', 'EntryAbility', '-b', BUNDLE)
    time.sleep(2.0)

    # 冷启动要几秒；轮询到能读出**当次**的布局行，并且能用深色缝找到网格
    for i in range(40):
        time.sleep(0.8)
        layout = read_layout(device, required=False)
        if layout is None or layout['tile'] <= 0:
            continue
        img = pull_screenshot(device, os.path.join(outdir, 'ANIM_wait_%02d.jpeg' % i))
        g = validate_grid(img, layout)
        if g is None:
            # 可能是残留的对话框盖住了棋盘：按一次返回键再试。
            # 但**不能多按**：屏幕上没有对话框时，返回键会把应用退出到桌面。
            if i in (6, 14):
                print('[app] 没找到棋盘网格，试一次返回键（第 %d 次轮询）' % (i + 1))
                hdc_check(device, 'shell', 'uitest', 'uiInput', 'keyEvent', 'Back')
                time.sleep(0.8)
            continue
        gx, gy, cols, rows = g
        print('[app] 棋盘已就绪：%dx%d 格边=%d 屏幕原点=(%d,%d) 画布原点=(%d,%d)（第 %d 次轮询）'
              % (rows, cols, layout['tile'], gx, gy,
                 layout['board_x'], layout['board_y'], i + 1))
        return img, layout, rows, cols
    raise RuntimeError('应用启动后 32 秒内没找到棋盘网格')


def dismiss_dialogs(device, outdir, layout, rows, cols):
    """
    屏幕上可能还有残留的对话框（「自定义」「最佳成绩」等）。

    判据用**深色缝网格**（与主题无关），不是颜色包围盒。
    按返回键**最多两次**，而且每次按完都确认应用还活着 ——
    屏幕上没有对话框时返回键会把应用退出到桌面。
    """
    img = None
    for attempt in range(4):
        img = pull_screenshot(device, os.path.join(outdir, 'ANIM_dlg_%02d.jpeg' % attempt))
        g = validate_grid(img, layout)
        if g is not None and g[2] == cols and g[3] == rows:
            return img          # 干净的
        alive = hdc(device, 'shell', "ps -ef | grep -a saolei | grep -v grep")
        if not alive.strip():
            print('[dlg] 应用已经不在了（可能刚才的返回键退出了它）')
            return None
        print('[dlg] 棋盘上还有东西，按一次返回键（第 %d 次）' % (attempt + 1))
        hdc_check(device, 'shell', 'uitest', 'uiInput', 'keyEvent', 'Back')
        time.sleep(0.8)
    return img


def play_to_win(args, templates, mine_tmpl):
    """
    一直点到赢。返回 (是否赢, 最后一屏, 网格信息, 用了几步)。

    终局的判据：**雷都被算出来了**（红旗 + 已露出的雷 == 雷数）。
    赢还是输，由**动画本身**分辨：
      胜利 -> 扫描条 + 拆雷光束在跑
      判负 -> 踩雷那格在跑爆炸
    这两者在棋盘截图上分不开 —— 胜利时引擎给所有雷插旗，而拆雷光束的精灵
    自带一份该格的方砖副本，光束扫过时那一格看起来像「已揭开的雷」，
    很容易被误读成判负。
    """
    device = args.device
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    img, layout, rows, cols = restart_app(device, outdir)
    img = dismiss_dialogs(device, outdir, layout, rows, cols)
    if img is None:
        print('[play] 应用被关掉了，重新启动一次')
        img, layout, rows, cols = restart_app(device, outdir)
        img = dismiss_dialogs(device, outdir, layout, rows, cols)
        if img is None:
            raise RuntimeError('棋盘上有盖不住的对话框')
    gx, gy, pitch = grid_from_layout(img, layout, rows, cols)
    mines = args.mines
    theme = detect_theme(img, gx, gy, pitch, rows, cols)
    print('[play] 屏幕网格原点=(%.1f, %.1f) 格边=%d 盘面=%dx%d 雷数=%d 主题=%s'
          % (gx, gy, pitch, rows, cols, mines, theme))

    for step in range(args.max_steps):
        board = read_board(img, gx, gy, pitch, layout['unit'], templates, rows, cols,
                           mine_tmpl)
        unknown = sum(1 for line in board for v in line if v == 'X')
        flagged = sum(1 for line in board for v in line if v == 'F')
        shown = sum(1 for line in board for v in line if v == 'M')
        unsure = sum(1 for line in board for v in line if v == '?')
        print('[play] step=%d 未揭开=%d 自动插旗=%d 露出雷=%d 认不出=%d'
              % (step, unknown, flagged, shown, unsure))
        print(fmt_board(board))
        if unsure > 0:
            # 认不出来的格子通常是被**动画**盖住了（扫描条横贯整盘、
            # 拆雷光束有 300x900 像素那么大）。这本身就是「刚到终局」的信号。
            print('[play] 有 %d 格认不出来（多半是动画盖住了），按终局处理' % unsure)
            return True, img, (gx, gy, pitch, rows, cols, theme), step
        # 终局：所有雷都算出来了（插旗的 + 已露出的）
        if flagged + shown >= mines and mines > 0:
            print('[play] 终局：红旗 %d + 已露出的雷 %d == 雷数 %d'
                  % (flagged, shown, mines))
            return True, img, (gx, gy, pitch, rows, cols, theme), step
        if shown > 0 and flagged + shown < mines:
            print('[play] 中途露出雷但没到终局，判负')
            return False, img, (gx, gy, pitch, rows, cols, theme), step

        res, mine_certain = solve(board, rows, cols, mines)
        if res is None:
            # 一条约束都没有 = 还没布雷。引擎保证「首点安全」，
            # 所以首点随便点（这里点中间，洪泛能开出最大的一片）。
            if step == 0:
                res = (rows // 2, cols // 2)
                print('[play] 还没有任何约束 -> 首点（引擎保证安全）')
            else:
                print('[play] 没有确定安全的格子了（这一局到此为止）')
                return False, img, (gx, gy, pitch, rows, cols, theme), step
        r, c = res
        x = gx + c * pitch + pitch / 2.0
        y = gy + r * pitch + pitch / 2.0
        print('[play] 点 (r=%d,c=%d) 屏幕(%.0f,%.0f)' % (r, c, x, y))
        click(device, x, y)
        time.sleep(args.click_wait)
        img = pull_screenshot(device, os.path.join(outdir, 'ANIM_play_%02d.jpeg' % step))
    return False, img, (gx, gy, pitch, rows, cols, theme), -1


def run_phase_win(args, templates, mine_tmpl):
    device = args.device
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    ended, img, grid, step = play_to_win(args, templates, mine_tmpl)
    if not ended:
        print('[win] 没到终局')
        return []
    gx, gy, pitch, rows, cols, theme = grid
    print('[win] 到终局了（用了 %d 步）！连拍终局动画' % step)
    paths = burst(device, outdir, 'ANIM_win', args.burst, args.burst_gap)
    print('[win] 抓到 %d 帧' % len(paths))
    unit = pitch / 18.0
    win = False
    for p in paths:
        im = Image.open(p).convert('RGB')
        bar = locate_scan_bar(im, gx, gy, pitch, unit, rows, cols)
        beams = analyse_disarm(im, gx, gy, pitch, unit, rows, cols)
        ex = analyse_explode(im, gx, gy, pitch, unit, rows, cols)
        if bar or beams:
            win = True
        print('  %s  扫描条=%s  光束=%s  爆炸=%s'
              % (os.path.basename(p),
                 '无' if bar is None else 'y=%d (相似度 %.3f)' % bar,
                 beams, ex))
    print('[win] 判定：%s' % ('胜利动画（扫描条/拆雷光束）' if win else '没有看到胜利动画'))
    return paths


def run_phase_explode(args, templates, mine_tmpl):
    """故意踩雷，连拍爆炸动画的 23 帧。"""
    device = args.device
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    img, layout, rows, cols = restart_app(device, outdir)
    img = dismiss_dialogs(device, outdir, layout, rows, cols)
    if img is None:
        img, layout, rows, cols = restart_app(device, outdir)
        img = dismiss_dialogs(device, outdir, layout, rows, cols)
        if img is None:
            raise RuntimeError('棋盘上有盖不住的对话框')
    gx, gy, pitch = grid_from_layout(img, layout, rows, cols)
    mines = args.mines
    print('[exp] 屏幕网格原点=(%.1f, %.1f) 格边=%d' % (gx, gy, pitch))

    board = read_board(img, gx, gy, pitch, layout['unit'], templates, rows, cols, mine_tmpl)
    print(fmt_board(board))
    # 先开一枪把雷布下（首点安全），再用推理找一颗「必定是雷」的格子踩上去
    click(device, gx + cols // 2 * pitch + pitch / 2.0, gy + rows // 2 * pitch + pitch / 2.0)
    time.sleep(1.8)
    img = pull_screenshot(device, os.path.join(outdir, 'ANIM_exp_first.jpeg'))
    board = read_board(img, gx, gy, pitch, layout['unit'], templates, rows, cols, mine_tmpl)
    print(fmt_board(board))
    res, mine_certain = solve(board, rows, cols, mines)
    if not mine_certain:
        print('[exp] 还推不出哪格是雷')
        return []
    r, c = sorted(mine_certain)[0]
    print('[exp] 踩雷格 (r=%d,c=%d)（推理确定是雷）' % (r, c))
    x = gx + c * pitch + pitch / 2.0
    y = gy + r * pitch + pitch / 2.0
    print('[exp] 踩 (r=%d,c=%d) 屏幕(%.0f,%.0f)' % (r, c, x, y))
    click(device, x, y)
    # 爆炸只有 1 秒（23 帧），而设备端一次截图要 ~500ms，
    # 所以「点击 -> 第一张截图」之间隔多少，直接决定我们落在第几帧。
    # --first-delay 就是用来**扫**这个落点的：多跑几轮、给不同的延时，
    # 就能把 23 帧里的好几帧分别拍下来。
    time.sleep(args.first_delay)
    paths = burst(device, outdir, args.tag, args.burst, args.burst_gap)
    print('[exp] 抓到 %d 帧' % len(paths))
    for p in paths:
        im = Image.open(p).convert('RGB')
        ex = analyse_explode(im, gx, gy, pitch, layout['unit'], rows, cols)
        print('  %s  爆炸帧=%s' % (os.path.basename(p), ex))
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='127.0.0.1:5557')
    ap.add_argument('--phase', default='win', choices=['win', 'explode'])
    ap.add_argument('--out', default=r'D:\software\harmony\projects\minesweeper\docs\verify')
    ap.add_argument('--rows', type=int, default=9)
    ap.add_argument('--cols', type=int, default=9)
    ap.add_argument('--mines', type=int, default=10)
    ap.add_argument('--max-steps', type=int, default=60)
    ap.add_argument('--burst', type=int, default=16)
    ap.add_argument('--burst-gap', type=float, default=0.15)
    ap.add_argument('--click-wait', type=float, default=1.1)
    ap.add_argument('--first-delay', type=float, default=0.0,
                    help='爆炸：点击之后到第一张截图之间等多久（用来扫不同的动画帧）')
    ap.add_argument('--tag', default='ANIM_explode', help='输出文件名前缀')
    args = ap.parse_args()

    templates = load_templates()
    mine_tmpl = load_mine_template()
    if args.phase == 'win':
        run_phase_win(args, templates, mine_tmpl)
    else:
        run_phase_explode(args, templates, mine_tmpl)


if __name__ == '__main__':
    main()
