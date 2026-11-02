#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_layout.py —— 扫雷应用「版式数学推演」离线检查脚本（v3.0）

把 GameController 的版式几何公式**原样翻译**成 Python，然后对若干块画布 × 若干盘面
逐个算：适配档 n、格边、棋盘/状态条/菜单栏矩形、上下左右留白、是否溢出、溢出后
能不能拖到头（limX/limY）、状态条是否还在可视区、整数像素。

真值来源（C:\\Users\\19161\\saolei，读的是 2026-10-31 13:51 的工作区状态）：
  Theme.ets:11             TILE = 18
  Theme.ets:13             MAX_SCALE_INDEX = 8
  Theme.ets:149            MIN_CELL_PX = 48      （最小可点格边）
  Theme.ets:140-157        STRIP_BAND=32 STRIP_CLOCK_SIZE=25 STRIP_PANEL_W=40
                           STRIP_PANEL_H=21 STRIP_GAP=6
  Theme.ets:169-171        stripMargin(cols) = max(0, round((cols-12.5)*TILE/7))
  WinMenu.ets:84-90,163    MENU_BAR_H = 18 * (14/12) = 21 (vp)
  GameController.ets:237-276   layout()        —— 适配档 fit + 最小可点格边抬档
  GameController.ets:311-333   applyGeometry() —— 各矩形 + 顶对齐
  GameController.ets:337-341   menuBarPx()    —— round(MENU_BAR_H / pxScale)
  GameController.ets:345-355   clampPan()      —— limX / limY
  GameController.ets:1125-1131 computeDialogScale(refW, refH)
  GameController.ets:696-728   drawStatusStrip()

用法：  python tools/check_layout.py            （人读的报告）
        python tools/check_layout.py --md       （额外输出 markdown 表格）
"""

import math
import sys

# ---------------------------------------------------------------------------
# 常量（与 Theme.ets / WinMenu.ets / WinDialog.ets 一一对应）
# ---------------------------------------------------------------------------
TILE = 18
MAX_SCALE_INDEX = 8
MIN_CELL_PX = 48                 # 最小可点格边（设备像素）

STRIP_BAND = 32
STRIP_CLOCK_SIZE = 25
STRIP_PANEL_W = 40
STRIP_PANEL_H = 21
STRIP_GAP = 6

REF_FONT_PX = 12
APP_FONT_VP = 14
BAR_H_REF = 18
MENU_BAR_H = BAR_H_REF * (APP_FONT_VP / REF_FONT_PX)   # 21 vp

DLG_SIDE_MARGIN = 32            # 对话框左右各留 32 px

# WinDialog.ets 的五个对话框（参考像素）
DLGS = [
    ('结束(负)', 483, 288),
    ('结束(胜)', 396, 340),
    ('最高分', 400, 320),
    ('关于', 314, 197),
    ('帮助', 584, 280),
]
STATS_W, STATS_H = 702, 254     # StatsWindow.ets
DLG_W, DLG_H = 280, 200         # CustomField.ets
KEY_W, KEY_H, KEY_GAP = 34, 30, 4   # NumKeypad.ets
NUMKEY_W = 3 * KEY_W + 2 * KEY_GAP   # 110
NUMKEY_H = 4 * KEY_H + 3 * KEY_GAP   # 132


def js_round(x):
    """JavaScript Math.round 的语义（半数向上）。Python 内置 round 是银行家舍入。"""
    return math.floor(x + 0.5)


def strip_margin(cols):
    """Theme.ets stripMargin()"""
    return max(0, js_round((cols - 12.5) * TILE / 7))


# ---------------------------------------------------------------------------
# 画布
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, name, w_px, h_px, density, note):
        self.name = name
        self.w = w_px
        self.h = h_px
        self.density = density
        self.note = note

    @property
    def px_scale(self):
        return 1.0 / self.density

    @property
    def w_vp(self):
        return self.w / self.density

    @property
    def h_vp(self):
        return self.h / self.density

    @property
    def menu_px(self):
        """menuBarPx() = Math.round(MENU_BAR_H / pxScale) —— 整数设备像素"""
        return js_round(MENU_BAR_H / self.px_scale)

    @property
    def avail_h(self):
        """菜单栏下方的可用高度"""
        return max(1, self.h - self.menu_px)


CANVASES = [
    Canvas('Pura X Max 典藏版 内屏', 2584, 1824, 2.75, '用户真机 · 横屏'),
    Canvas('Pura X Max 典藏版 外屏', 1323, 1936, 2.75, '折起来 · 竖屏'),
    Canvas('Mate X7 模拟器内屏', 2210, 2208, 3.125, '折叠屏 · 近方形'),
    Canvas('Mate 90 Pro 模拟器', 1280, 2598, 3.5, '又窄又长'),
    # 平板（用户 2026-11-03 追加）。分辨率取自华为官方规格页：
    #   MatePad Pro 12.2  2800x1840  274ppi  3:2
    #   MatePad Pro 13    2880x1920（模拟器镜像，实测画布见 docs/LAYOUT-MATRIX.md）
    # 密度：HarmonyOS 的 densityPixels = 屏 density / 160。
    #   DevEco 模拟器「MatePad Pro 12」屏配置给的 density=360 -> densityPixels=2.25，
    #   这正是 MatePad Pro 12.2 精确镜像用的那一档（screen 2800x1840）。
    #   真机上系统可能给 2.0；274ppi/160 ≈ 1.71 是纯换算值。几种都推演一遍。
    Canvas('MatePad Pro 12.2 (2800x1840)', 2800, 1840, 2.0, '平板 · 3:2 · 官方分辨率'),
    Canvas('MatePad Pro 12.2 密度2.25', 2800, 1840, 2.25, '平板 · DevEco 屏配置 density=360'),
    Canvas('MatePad Pro 12.2 密度1.75', 2800, 1840, 1.75, '平板 · 换算密度 274ppi/160≈1.71'),
    Canvas('MatePad Pro 13 (2880x1920)', 2880, 1920, 2.0, '平板 · 3:2 · 模拟器镜像'),
    # 平板竖屏（用户把平板竖着拿是常态）
    Canvas('MatePad Pro 12.2 竖屏', 1840, 2800, 2.0, '平板 · 竖屏 3:2'),
    Canvas('MatePad Pro 12.2 竖屏 密度2.25', 1840, 2800, 2.25, '平板 · 竖屏 · density=360'),
]

# 三个内置难度 + 一个 30 列自定义局（最大尺寸 24 行 x 30 列）
BOARDS = [
    ('初级', 9, 9, 10),
    ('中级', 16, 16, 40),
    ('高级', 16, 30, 99),
    ('自定义', 24, 30, 200),
]


# ---------------------------------------------------------------------------
# 几何（与当前 GameController 一一对应）
# ---------------------------------------------------------------------------
def fit_scale(canvas, rows, cols):
    """GameController.layout() 第 1 步 + 最小可点格边抬档。

    1) 整盘刚好放下的档位：
         横向  bw = cols*TILE*u <= canvasW
         纵向  menuBarPx + (rows*TILE + 32) * u <= canvasH
    2) 装得下的那一档若格边 < MIN_CELL_PX(48)，抬一档，但有前提：
         - 抬完纵向仍装得下 → 抬
         - 否则只有「横向本来就装不下」才抬（反正要平移）
         - 否则不抬（别把完全看得见的盘面变成纵向溢出）
    """
    menu = canvas.menu_px
    fit = 1
    for n in range(1, MAX_SCALE_INDEX + 1):
        u = 2 * n
        bw = cols * TILE * u
        bh = rows * TILE * u + STRIP_BAND * u
        if bw <= canvas.w and menu + bh <= canvas.h:
            fit = n
        else:
            break
    raised = False
    reason = ''
    if TILE * 2 * fit < MIN_CELL_PX and fit < MAX_SCALE_INDEX:
        # 「整块装得下」优先；但整块装得下的那一档格边 < 48 px 时，**宁可溢出也要够大**：
        # 抬到格边 >= 48 的那一档，允许棋盘纵向溢出（顶对齐 + 状态条钉画布底边当 HUD）。
        min_touch_n = int(math.ceil(MIN_CELL_PX / float(TILE * 2)))
        old_fit = fit
        fit = min(MAX_SCALE_INDEX, max(fit + 1, min_touch_n))
        raised = True
        u2 = 2 * fit
        fits_v = menu + rows * TILE * u2 + STRIP_BAND * u2 <= canvas.h
        reason = ('抬档：整块装得下的是 n=%d（格边 %d px < %d），抬到 n=%d（格边 %d px）%s'
                  % (old_fit, TILE * 2 * old_fit, MIN_CELL_PX, fit, TILE * 2 * fit,
                     '，抬完纵向仍装得下' if fits_v else '，**允许纵向溢出**（顶对齐 + 状态条钉画布底边）'))
    return fit, raised, reason


def fit_limits(canvas, rows, cols):
    """分别算「只受宽度限制」「只受高度限制」时的最大档位，用于定位瓶颈。"""
    n_by_w = 0
    n_by_h = 0
    menu = canvas.menu_px
    for n in range(1, MAX_SCALE_INDEX + 1):
        u = 2 * n
        if cols * TILE * u <= canvas.w:
            n_by_w = n
        if menu + rows * TILE * u + STRIP_BAND * u <= canvas.h:
            n_by_h = n
    return n_by_w, n_by_h


def geometry(canvas, rows, cols, n, pan_x=0.0, pan_y=0.0):
    """applyGeometry()；panX/panY 默认 0（新局、未手动缩放）。"""
    u = 2 * n
    tile = TILE * u
    board_w = cols * tile
    board_h = rows * tile
    frame_w = board_w
    frame_h = board_h + STRIP_BAND * u
    frame_x = js_round((canvas.w - frame_w) / 2) + pan_x
    avail_h = canvas.avail_h
    strip_h = STRIP_BAND * u
    # 状态条：竖向装得下就贴在棋盘下沿；装不下就**钉在画布底边**（HUD）
    group_fits = canvas.menu_px + board_h + strip_h <= canvas.h
    hud_top = canvas.h - strip_h
    board_area_h = avail_h if group_fits else max(1, hud_top - canvas.menu_px)
    if group_fits:
        # 整组（棋盘 + 状态条）在剩余空间里居中
        frame_y_base = canvas.menu_px + js_round((avail_h - board_h - strip_h) / 2)
    else:
        frame_y_base = canvas.menu_px          # 装不下 → 顶对齐菜单栏下沿
    frame_y = frame_y_base + pan_y
    board_x = frame_x
    board_y = frame_y
    strip_top = (board_y + board_h) if group_fits else hud_top

    board_bottom = board_y + board_h
    board_right = board_x + board_w
    margin = strip_margin(cols) * u

    # 状态条内容自己的缩放档 su + 贴边留白（2026-11-01，Codex 对抗性复审 P2）
    #
    # 一组计数器 = 时钟 25 + 间隙 6 + 面板 40 = 71 个参考单位；两组就是 142u。
    # 画布只有 1280 px 时 u 一旦超过 8 就放不下两组了，而状态条原来跟着棋盘档位放大，
    # 于是两个计数都跑出屏幕（实测 n=8、30 列：计时面板从 x=1216 起、雷数面板整个在屏外）。
    # 状态条是「窗口边框」性质的元素，原版里它本来就不随棋盘缩放，
    # 所以内容单独一档 su = min(u, 两组放得下的最大档)；su 必须偶数（图集是 2 倍存储像素）。
    group_ref = STRIP_CLOCK_SIZE + STRIP_GAP + STRIP_PANEL_W
    max_su = 2 * (canvas.w // (2 * group_ref) // 2)
    su = max(2, min(u, max_su))
    group_w = group_ref * su
    # 贴边留白：棋盘侧的 margin 也随 u 放大（30 列时 margin = 45u），
    # 必须按「两组放得下」夹住，否则两组会挤在一起甚至互相压。
    anchor_margin = min(margin, max(0, (canvas.w - 2 * group_w) // 2))

    # 两端「贴住画布沿」：棋盘比画布宽时（30 列的局在窄屏上棋盘 2160px、屏 1280px），
    # 原来钟钉在棋盘左沿 = 屏外 440px、雷图标钉在棋盘右沿 = 屏外 440px，两个计数都看不见。
    # 主线程已改成锚画布左右沿并夹在画布内（GameController.drawStatusStrip）：
    #   clockX = clamp(max(boardX + margin, anchorMargin), 0, canvasW - groupW - anchorMargin)
    #   iconX  = clamp(..., clockX + groupW + 面板+间隙宽, canvasW - 25*su)
    clock_x = max(0, min(max(board_x + margin, anchor_margin),
                         canvas.w - group_w - anchor_margin))
    if su == u:
        content_top = strip_top + js_round((STRIP_BAND - STRIP_CLOCK_SIZE) / 2) * u
    else:
        content_top = strip_top + js_round((STRIP_BAND * u - STRIP_CLOCK_SIZE * su) / 2)
    clock_y = content_top
    time_x = clock_x + (STRIP_CLOCK_SIZE + STRIP_GAP) * su
    time_y = content_top + js_round((STRIP_CLOCK_SIZE - STRIP_PANEL_H) * su / 2)
    icon_x = min(board_right - margin - STRIP_CLOCK_SIZE * su,
                 canvas.w - anchor_margin - STRIP_CLOCK_SIZE * su)
    icon_x = max(icon_x, clock_x + group_w + (STRIP_GAP + STRIP_PANEL_W) * su)
    icon_x = min(icon_x, canvas.w - STRIP_CLOCK_SIZE * su)
    icon_y = content_top
    mine_x = icon_x - (STRIP_GAP + STRIP_PANEL_W) * su
    mine_y = time_y

    strip = {
        'band': (board_x, strip_top, board_w, STRIP_BAND * u),
        'clock': (clock_x, clock_y, STRIP_CLOCK_SIZE * su, STRIP_CLOCK_SIZE * su),
        'time': (time_x, time_y, STRIP_PANEL_W * su, STRIP_PANEL_H * su),
        'mine_panel': (mine_x, mine_y, STRIP_PANEL_W * su, STRIP_PANEL_H * su),
        'mine_icon': (icon_x, icon_y, STRIP_CLOCK_SIZE * su, STRIP_CLOCK_SIZE * su),
    }
    return {
        'n': n, 'u': u, 'tile': tile,
        'board': (board_x, board_y, board_w, board_h),
        'frame': (frame_x, frame_y, frame_w, frame_h),
        'strip': strip,
        'menu': (0, 0, canvas.w, canvas.menu_px),
        'top_aligned': board_h > board_area_h,
        'strip_top': strip_top,
        'board_area_h': board_area_h,
        'hud': not group_fits,
        'strip_unit': su,
        'anchor_margin': anchor_margin,
    }


def clamp_pan(canvas, frame_w, board_h, board_area_h):
    """GameController.clampPan() 的 limX / limY。

    纵向按**棋盘**与「菜单栏下沿 ~ 状态条上沿」这块可视区比：状态条钉在画布底边
    （HUD）时，可视区要减去状态条那条带子。返回的第二个值是**单向**的纵向溢出量
    （panY ∈ [-溢出量, 0]），不是对称范围。
    """
    lim_x = (frame_w - canvas.w) / 2.0 if frame_w > canvas.w else 0.0
    # 纵向是**单向**的：只能往上推（panY ∈ [-溢出量, 0]）。
    # 对称范围（±溢出量/2）会让最后一行永远缺一截：棋盘只比可视区高 90 px 时，
    # 居中那个位置上下各露 45 px，最后一行被 HUD 吃掉 45 px，点不准。
    over_v = (board_h - board_area_h) if board_h > board_area_h else 0.0
    return lim_x, over_v


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x = max(ax, bx)
    y = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    if x2 <= x or y2 <= y:
        return None
    return (x, y, x2 - x, y2 - y)


def visible_x(canvas, rect):
    """元素在横向是否落在画布可视区（0..canvasW）内，并返回可见宽度。"""
    x, _y, w, _h = rect
    vis = max(0, min(x + w, canvas.w) - max(x, 0))
    return vis > 0, vis


def is_int(v):
    return isinstance(v, int) or float(v).is_integer()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def analyze(canvas):
    rows_out = []
    for bname, rows, cols, mines in BOARDS:
        fit, raised, reason = fit_scale(canvas, rows, cols)
        n_by_w, n_by_h = fit_limits(canvas, rows, cols)
        g = geometry(canvas, rows, cols, fit)
        frame = g['frame']
        board = g['board']
        lim_x, lim_y = clamp_pan(canvas, frame[2], board[3], g['board_area_h'])

        # 留白（棋盘相对画布；负数 = 越界多少）
        m_left = board[0]
        m_right = canvas.w - (board[0] + board[2])
        m_top = board[1] - canvas.menu_px          # 相对菜单栏下沿
        m_bottom = canvas.h - (board[1] + board[3])
        group_top = frame[1]
        group_bottom = frame[1] + frame[3]
        gm_top = group_top - canvas.menu_px
        gm_bottom = canvas.h - group_bottom

        # 状态条四个元素：默认视图是否可见 / 拖到两端是否可见
        strip_vis = {}
        for key in ('clock', 'time', 'mine_panel', 'mine_icon'):
            ok, vis = visible_x(canvas, g['strip'][key])
            strip_vis[key] = (ok, vis)
        g_left = geometry(canvas, rows, cols, fit, pan_x=lim_x, pan_y=0)
        g_right = geometry(canvas, rows, cols, fit, pan_x=-lim_x, pan_y=0)
        reach = {}
        for key in ('clock', 'time', 'mine_panel', 'mine_icon'):
            reach[key] = (visible_x(canvas, g_left['strip'][key])[0],
                          visible_x(canvas, g_right['strip'][key])[0])
        # 计数器里的数字是**居中**画在面板上的（fillText(..., x + 40u/2, ...)），
        # 所以"面板露出一条边"不等于"数字看得见"——要单独看数字中心。
        text_x = {
            'time': g['strip']['time'][0] + STRIP_PANEL_W * g['u'] / 2.0,
            'mine': g['strip']['mine_panel'][0] + STRIP_PANEL_W * g['u'] / 2.0,
        }
        text_vis = {k: (0 <= v <= canvas.w) for k, v in text_x.items()}

        over_x = max(0, frame[2] - canvas.w)
        over_y = max(0, frame[3] - canvas.avail_h)

        fill_w = frame[2] * 100.0 / canvas.w
        fill_h = frame[3] * 100.0 / canvas.avail_h
        fill_area = (frame[2] * frame[3]) * 100.0 / (canvas.w * canvas.avail_h)

        non_int = []
        for key in ('board', 'frame'):
            for i, v in enumerate(g[key]):
                if not is_int(v):
                    non_int.append('%s[%d]=%s' % (key, i, v))
        for key, rect in g['strip'].items():
            for i, v in enumerate(rect):
                if not is_int(v):
                    non_int.append('strip.%s[%d]=%s' % (key, i, v))
        for r in range(rows):
            for c in range(cols):
                cx = board[0] + c * g['tile']
                cy = board[1] + r * g['tile']
                if not is_int(cx) or not is_int(cy):
                    non_int.append('cell(%d,%d)' % (r, c))
                if not is_int(cx + 3 * g['u']) or not is_int(cy + 1.5 * g['u']):
                    non_int.append('digit(%d,%d)' % (r, c))

        rows_out.append({
            'bname': bname, 'rows': rows, 'cols': cols, 'mines': mines,
            'fit': fit, 'raised': raised, 'reason': reason,
            'n_by_w': n_by_w, 'n_by_h': n_by_h,
            'g': g, 'lim_x': lim_x, 'lim_y': lim_y,
            'm_left': m_left, 'm_right': m_right, 'm_top': m_top, 'm_bottom': m_bottom,
            'gm_top': gm_top, 'gm_bottom': gm_bottom,
            'over_x': over_x, 'over_y': over_y,
            'fill_w': fill_w, 'fill_h': fill_h, 'fill_area': fill_area,
            'strip_vis': strip_vis, 'reach': reach,
            'text_x': text_x, 'text_vis': text_vis,
            'top_aligned': g['top_aligned'],
            'non_int': non_int,
            'binding': '宽' if n_by_w < n_by_h else ('高' if n_by_h < n_by_w else '两者同时'),
        })
    return rows_out


def fmt_rect(r):
    return '(%d,%d %dx%d)' % (r[0], r[1], r[2], r[3])


def report(cv, res):
    out = []
    w = out.append
    w('=' * 110)
    w('画布：%s  %d x %d px  (%.4f x %.4f vp)  density=%.4g  pxScale=%.4f  [%s]'
      % (cv.name, cv.w, cv.h, cv.w_vp, cv.h_vp, cv.density, cv.px_scale, cv.note))
    w('菜单栏 menuBarPx = round(21vp x density) = %d px；菜单栏下方可用高度 = %d px'
      % (cv.menu_px, cv.avail_h))
    w('=' * 110)
    w('%-8s %-9s %3s %6s %8s %-20s %-20s %-18s %-12s %s'
      % ('盘面', 'n', '档', '格边px', '格边vp', '棋盘矩形', '棋盘+状态条包围盒',
         '留白 左/右/上/下', '溢出 横/纵', '状态条 钟时雷图'))
    w('-' * 110)
    for r in res:
        g = r['g']
        vis = ''.join('Y' if r['strip_vis'][k][0] else 'n' for k in ('clock', 'time', 'mine_panel', 'mine_icon'))
        w('%-8s %-9s %3d %6d %8.2f %-20s %-20s %-18s %-12s %s'
          % (r['bname'], '%d(%s)' % (r['fit'], r['binding']), r['fit'], g['tile'],
             g['tile'] / cv.density, fmt_rect(g['board']), fmt_rect(g['frame']),
             '%d/%d/%d/%d' % (r['m_left'], r['m_right'], r['m_top'], r['m_bottom']),
             '%d/%d' % (r['over_x'], r['over_y']), vis))
    w('')
    return '\n'.join(out)


def details(cv, res):
    out = []
    w = out.append
    w('')
    w('【%s】逐项细节' % cv.name)
    w('-' * 110)
    for r in res:
        g = r['g']
        b = g['board']
        fr = g['frame']
        w('')
        w('%s %dx%d / %d 雷' % (r['bname'], r['rows'], r['cols'], r['mines']))
        w('  适配档 n=%d (u=%d, 格边=%d px = %.4f vp)  瓶颈=%s%s'
          % (r['fit'], g['u'], g['tile'], g['tile'] / cv.density, r['binding'],
             '  ←已抬档' if r['raised'] else ''))
        w('    %s' % r['reason'])
        w('    只看宽度最多 n=%d；只看高度最多 n=%d' % (r['n_by_w'], r['n_by_h']))
        w('  棋盘 = %s' % fmt_rect(b))
        w('  棋盘+状态条包围盒 = %s%s'
          % (fmt_rect(fr), '（纵向装不下 → 顶对齐菜单栏下沿）' if r['top_aligned'] else '（纵向居中）'))
        w('  状态条带 = %s%s' % (fmt_rect(g['strip']['band']),
                                 '  ←**钉在画布底边（HUD）**，棋盘纵向溢出' if g['hud'] else ''))
        w('  状态条带下沿 = %d（画布高 %d，%s）；棋盘可视区高 = %d'
          % (g['strip']['band'][1] + g['strip']['band'][3], cv.h,
             '在画布内' if g['strip']['band'][1] + g['strip']['band'][3] <= cv.h else '**出画布**',
             g['board_area_h']))
        for k in ('clock', 'time', 'mine_panel', 'mine_icon'):
            ok, vis = r['strip_vis'][k]
            lft, rgt = r['reach'][k]
            w('    %-11s = %-20s 默认视图 %s%s，拖到最左 %s / 最右 %s'
              % (k, fmt_rect(g['strip'][k]), '可见' if ok else '**在屏外**',
                 ('(可见 %d px)' % vis) if ok else '',
                 '可见' if lft else '屏外', '可见' if rgt else '屏外'))
        w('    计数器数字中心 x：计时 %+.1f（%s）、雷数 %+.1f（%s）'
          % (r['text_x']['time'], '在屏内' if r['text_vis']['time'] else '**在屏外**',
             r['text_x']['mine'], '在屏内' if r['text_vis']['mine'] else '**在屏外**'))
        w('  留白（棋盘相对画布）左%d 右%d 上%d 下%d；整组相对菜单栏下沿 上%d 下%d'
          % (r['m_left'], r['m_right'], r['m_top'], r['m_bottom'],
             r['gm_top'], r['gm_bottom']))
        w('  溢出：横向 %d px，纵向 %d px；拖动余量 limX=%.1f（对称），纵向 panY ∈ [-%.1f, 0]%s'
          % (r['over_x'], r['over_y'], r['lim_x'], r['lim_y'],
             '（横向两端都能拖到）' if r['lim_x'] > 0 else '（横向不许拖）'))
        w('  用满：宽度 %.1f%%、高度 %.1f%%、面积 %.1f%%'
          % (r['fill_w'], r['fill_h'], r['fill_area']))
        w('  整数像素：' + ('全部落点为整数设备像素'
                            if not r['non_int'] else ','.join(r['non_int'][:6])))
    return '\n'.join(out)


def compute_dialog_scale(cv, ref_w, ref_h):
    """GameController.computeDialogScale(refWidth, refHeight)

    2026-10-31 18:26 起下限是 **0.5**（不是 1）：画布窄到放不下时宁可整体缩小，
    也要完整可见——被截断的按钮是点不到的。
    """
    density = 1.0 / cv.px_scale
    max_by_w = (cv.w - DLG_SIDE_MARGIN) / ref_w
    max_by_h = (cv.h - DLG_SIDE_MARGIN) / ref_h
    return max(0.5, min(2.0, density, max_by_w, max_by_h))


def dialog_checks(cv):
    out = []
    w = out.append
    w('')
    w('【%s】对话框 / 统计窗口 / 自定义框' % cv.name)
    w('-' * 110)
    w('  s = max(0.5, min(2, density, (canvasW-32)/refW, (canvasH-32)/refH))')
    for nm, dw, dh in DLGS:
        s = compute_dialog_scale(cv, dw, dh)
        wpx, hpx = dw * s, dh * s
        fits = (wpx <= cv.w and hpx <= cv.h)
        w('    %-8s 参考 %3dx%-3d → %6.0fx%-6.0f px（s=%.3f%s）  %s'
          % (nm, dw, dh, wpx, hpx, s, '' if is_int(s) else ' ← 小数',
             '装得下' if fits else '× 超出画布'))
    s = compute_dialog_scale(cv, STATS_W, STATS_H)
    w('    %-8s 参考 %3dx%-3d → %6.0fx%-6.0f px（s=%.3f%s）  %s'
      % ('统计窗口', STATS_W, STATS_H, STATS_W * s, STATS_H * s, s,
         '' if is_int(s) else ' ← 小数',
         '装得下' if (STATS_W * s <= cv.w and STATS_H * s <= cv.h) else '× 超出画布'))
    s = compute_dialog_scale(cv, DLG_W + 12 + NUMKEY_W, max(DLG_H, NUMKEY_H))
    w('    %-8s 参考 %3dx%-3d → %6.0fx%-6.0f px（s=%.3f%s）  %s'
      % ('自定义框', DLG_W + 12 + NUMKEY_W, max(DLG_H, NUMKEY_H),
         (DLG_W + 12 + NUMKEY_W) * s, max(DLG_H, NUMKEY_H) * s, s,
         '' if is_int(s) else ' ← 小数',
         '装得下' if ((DLG_W + 12 + NUMKEY_W) * s <= cv.w
                      and max(DLG_H, NUMKEY_H) * s <= cv.h) else '× 超出画布'))
    return '\n'.join(out)


def summary_table(all_res):
    out = []
    w = out.append
    w('| 画布 | 盘面 | n | 瓶颈 | 格边 px | 格边 vp | 棋盘原点 | 棋盘+状态条包围盒 | 留白 左/右/上/下 | 溢出 横/纵 | limX/limY | 用满 宽/高/面积 | 状态条默认可见 |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for cv, res in all_res:
        for r in res:
            g = r['g']
            b = g['board']
            fr = g['frame']
            vis = ''.join('Y' if r['strip_vis'][k][0] else 'n'
                          for k in ('clock', 'time', 'mine_panel', 'mine_icon'))
            w('| %s | %s %dx%d | %d | %s | %d | %.2f | (%d,%d) | %s | %d/%d/%d/%d | %d/%d | %.1f/%.1f | %.1f%%/%.1f%%/%.1f%% | %s |'
              % (cv.name, r['bname'], r['rows'], r['cols'], r['fit'], r['binding'],
                 g['tile'], g['tile'] / cv.density, b[0], b[1], fmt_rect(fr),
                 r['m_left'], r['m_right'], r['m_top'], r['m_bottom'],
                 r['over_x'], r['over_y'], r['lim_x'], r['lim_y'],
                 r['fill_w'], r['fill_h'], r['fill_area'], vis))
    return '\n'.join(out)


def strip_table(all_res):
    out = []
    w = out.append
    w('| 画布 | 盘面 | 棋盘宽 | 画布宽 | 状态条带 | 钟 | 时 | 雷数 | 雷图标 | 计时数字 | 雷数数字 | 默认视图可见 | 拖到最左 | 拖到最右 |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for cv, res in all_res:
        for r in res:
            g = r['g']
            s = g['strip']
            keys = ('clock', 'time', 'mine_panel', 'mine_icon')
            cnt = sum(1 for k in keys if r['strip_vis'][k][0])
            left = ''.join(k[0] for k in keys if r['reach'][k][0])
            right = ''.join(k[0] for k in keys if r['reach'][k][1])
            w('| %s | %s %dx%d | %d | %d | %s | %s | %s | %s | %s | %s | %s | %d/4 | %s | %s |'
              % (cv.name, r['bname'], r['rows'], r['cols'], g['board'][2], cv.w,
                 fmt_rect(s['band']),
                 'Y' if r['strip_vis']['clock'][0] else 'n',
                 'Y' if r['strip_vis']['time'][0] else 'n',
                 'Y' if r['strip_vis']['mine_panel'][0] else 'n',
                 'Y' if r['strip_vis']['mine_icon'][0] else 'n',
                 ('%+.0f Y' % r['text_x']['time']) if r['text_vis']['time']
                 else ('%+.0f n' % r['text_x']['time']),
                 ('%+.0f Y' % r['text_x']['mine']) if r['text_vis']['mine']
                 else ('%+.0f n' % r['text_x']['mine']),
                 cnt, left or '—', right or '—'))
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# v4.0 断言：把新规则钉死，别以后又被改回去
# ---------------------------------------------------------------------------

# v3.0 的 16 组基线（画布名 -> {盘面名: (n, 格边px, 棋盘原点x, 棋盘原点y, 溢出x, 溢出y)}）。
# v4.0 之后**只有**「Pura X Max 典藏版 内屏 · 自定义 24x30」这一行允许变，
# 其余 15 行必须一字不差（见 docs/LAYOUT-MATRIX.md §5.4）。
V3_BASELINE = {
    'Pura X Max 典藏版 内屏': {
        '初级': (4, 144, 644, 165, 0, 0),
        '中级': (2, 72, 716, 301, 0, 0),
        '高级': (2, 72, 212, 301, 0, 0),
        '自定义': (1, 36, 752, 477, 0, 0),      # v4.0 这一行变了
    },
    'Pura X Max 典藏版 外屏': {
        '初级': (4, 144, 14, 221, 0, 0),
        '中级': (2, 72, 86, 357, 0, 0),
        '高级': (2, 72, -418, 357, 837, 0),
        '自定义': (2, 72, -418, 69, 837, 0),
    },
    'Mate X7 模拟器内屏': {
        '初级': (5, 180, 295, 167, 0, 0),
        '中级': (3, 108, 241, 177, 0, 0),
        '高级': (2, 72, 25, 497, 0, 0),
        '自定义': (2, 72, 25, 209, 0, 0),
    },
    'Mate 90 Pro 模拟器': {
        '初级': (3, 108, 154, 754, 0, 0),
        '中级': (2, 72, 64, 696, 0, 0),
        '高级': (2, 72, -440, 696, 880, 0),
        '自定义': (2, 72, -440, 408, 880, 0),
    },
}

# v4.0 内屏 24×30 的期望值（§4.3.2 那张表）
INNER_CUSTOM_EXPECT = {
    'n': 2,
    'tile_px': 72,
    'board_x': 212,
    'board_y': 58,          # 顶对齐菜单栏下沿
    'board_w': 2160,
    'board_h': 1728,
    'over_y': 90,           # 纵向溢出 90 px
    'board_area_h': 1638,   # 菜单栏下沿 ~ HUD 顶
    'strip_top': 1696,      # 钉在画布底边
    'strip_band_h': 128,
}


def assert_rules(all_res):
    """把 v4.0 的新规则钉死。返回失败条数。"""
    fails = []

    def ck(cond, msg):
        if not cond:
            fails.append(msg)

    lookup = {}
    for cv, res in all_res:
        for r in res:
            lookup[(cv.name, r['bname'])] = (cv, r)

    # --- 断言 1：除内屏 24×30 外，其余 15 行与 v3.0 基线一字不差 ---
    for cv_name, boards in V3_BASELINE.items():
        for board_name, exp in boards.items():
            key = (cv_name, board_name)
            if key not in lookup:
                fails.append('断言1：缺少 %s / %s' % (cv_name, board_name))
                continue
            cv, r = lookup[key]
            g = r['g']
            got = (r['fit'], g['tile'], g['board'][0], g['board'][1], r['over_x'], r['over_y'])
            if cv_name == 'Pura X Max 典藏版 内屏' and board_name == '自定义':
                continue          # 这一行允许变
            ck(got == exp, '断言1：%s / %s 与 v3.0 不一致：新 %s 旧 %s'
               % (cv_name, board_name, got, exp))

    # --- 断言 2：内屏 24×30 的新数字 ---
    cv, r = lookup[('Pura X Max 典藏版 内屏', '自定义')]
    g = r['g']
    e = INNER_CUSTOM_EXPECT
    ck(r['fit'] == e['n'], '断言2：内屏 24×30 的 n = %s，应为 %s' % (r['fit'], e['n']))
    ck(g['tile'] == e['tile_px'], '断言2：内屏 24×30 的格边 = %s，应为 %s'
       % (g['tile'], e['tile_px']))
    ck(g['board'][0] == e['board_x'] and g['board'][1] == e['board_y'],
       '断言2：内屏 24×30 的棋盘原点 = (%s,%s)，应为 (%s,%s)'
       % (g['board'][0], g['board'][1], e['board_x'], e['board_y']))
    ck(g['board'][2] == e['board_w'] and g['board'][3] == e['board_h'],
       '断言2：内屏 24×30 的棋盘尺寸 = %sx%s，应为 %sx%s'
       % (g['board'][2], g['board'][3], e['board_w'], e['board_h']))
    ck(r['over_y'] == e['over_y'], '断言2：内屏 24×30 的纵向溢出 = %s，应为 %s'
       % (r['over_y'], e['over_y']))
    ck(r['over_x'] == 0, '断言2：内屏 24×30 不该有横向溢出（%s）' % r['over_x'])
    ck(g['board_area_h'] == e['board_area_h'],
       '断言2：内屏 24×30 的棋盘可视区高 = %s，应为 %s'
       % (g['board_area_h'], e['board_area_h']))
    ck(g['strip_top'] == e['strip_top'],
       '断言2：内屏 24×30 的状态条顶 = %s，应为 %s（钉画布底边）'
       % (g['strip_top'], e['strip_top']))
    ck(g['hud'], '断言2：内屏 24×30 应进入 HUD 模式（状态条钉画布底边）')
    ck(g['top_aligned'], '断言2：内屏 24×30 的棋盘应顶对齐菜单栏下沿')

    # --- 断言 3：16 组一律格边 >= 48 设备像素（新抬档规则的后果） ---
    for (cv_name, board_name), (cv, r) in lookup.items():
        ck(r['g']['tile'] >= MIN_CELL_PX,
           '断言3：%s / %s 的格边 %s px < %s（点不准）'
           % (cv_name, board_name, r['g']['tile'], MIN_CELL_PX))

    # --- 断言 4：16 组的状态条带与四个元素都在画布内 ---
    for (cv_name, board_name), (cv, r) in lookup.items():
        band = r['g']['strip']['band']
        ck(band[1] >= 0 and band[1] + band[3] <= cv.h + 1,
           '断言4：%s / %s 的状态条带 %s 出画布（画布高 %s）'
           % (cv_name, board_name, band, cv.h))
        for el in ('clock', 'time', 'mine_panel', 'mine_icon'):
            x, y, w, h = r['g']['strip'][el]
            ck(x >= 0 and x + w <= cv.w and y >= 0 and y + h <= cv.h,
               '断言4：%s / %s 的 %s %s 出画布（画布 %dx%d）'
               % (cv_name, board_name, el, r['g']['strip'][el], cv.w, cv.h))

    # --- 断言 5：HUD 模式只出现在「纵向溢出」的局，其余状态条贴在棋盘下沿 ---
    #
    # 2026-11-03 改写：原来这里是**画布白名单**（只认 Pura X Max 内屏 24×30），
    # 加了平板画布之后立刻误报。正确的判据是**溢出事实**：
    #   v4.0 规则：整块装得下的那档格边 < 48 设备像素时，宁可**纵向溢出**也要够大，
    #   纵向装不下时顶对齐菜单栏下沿，状态条钉画布底边当 HUD。
    # 所以：纵向溢出 ⇒ 必须是 HUD 且状态条钉画布底边；不溢出 ⇒ 不许是 HUD，
    # 状态条贴在棋盘下沿。这与 v4.0 之前的 15 组基线**完全等价**
    # （那 15 组溢出都是 0），但对新画布自动成立，不必再维护白名单。
    for (cv_name, board_name), (cv, r) in lookup.items():
        band = r['g']['strip']['band']
        if r['over_y'] > 0:
            ck(r['g']['hud'],
               '断言5：%s / %s 纵向溢出 %s px，应是 HUD 模式'
               % (cv_name, board_name, r['over_y']))
            ck(band[1] + band[3] == cv.h,
               '断言5：%s / %s 的状态条带下沿 %s，应等于画布高 %s（HUD 钉底边）'
               % (cv_name, board_name, band[1] + band[3], cv.h))
            ck(r['g']['board'][1] + r['g']['board'][3] > r['g']['strip_top'],
               '断言5：%s / %s 的状态条应当压在棋盘下沿上（否则用不着排除命中）'
               % (cv_name, board_name))
        else:
            ck(not r['g']['hud'], '断言5：%s / %s 不该是 HUD 模式' % (cv_name, board_name))
            ck(band[1] == r['g']['board'][1] + r['g']['board'][3],
               '断言5：%s / %s 的状态条应贴在棋盘下沿 %s，实际 %s'
               % (cv_name, board_name, r['g']['board'][1] + r['g']['board'][3], band[1]))

    # --- 断言 5b： Pura X Max 内屏 24×30 仍然是唯一的**基准** HUD 局，数值不许变 ---
    cv, r = lookup[('Pura X Max 典藏版 内屏', '自定义')]
    ck(r['g']['hud'], '断言5b：内屏 24×30 应是 HUD 模式')
    ck(r['g']['strip']['band'][1] + r['g']['strip']['band'][3] == cv.h,
       '断言5b：内屏 24×30 的状态条带下沿 %s，应等于画布高 %s'
       % (r['g']['strip']['band'][1] + r['g']['strip']['band'][3], cv.h))

    # --- 断言 6：纵向平移上限 = 整个溢出量（Codex P1），且不溢出时为 0 ---
    for (cv_name, board_name), (cv, r) in lookup.items():
        if r['over_y'] > 0:
            ck(r['lim_y'] == r['over_y'],
               '断言6：%s / %s 的纵向平移上限 %s，应等于整个溢出量 %s（Codex P1）'
               % (cv_name, board_name, r['lim_y'], r['over_y']))
        else:
            ck(r['lim_y'] == 0,
               '断言6：%s / %s 不该有纵向平移量（%s）' % (cv_name, board_name, r['lim_y']))

    # --- 断言 7：HUD 模式向上拖到头时，棋盘下沿与状态条上沿齐平（Codex P1 的目的） ---
    cv, r = lookup[('Pura X Max 典藏版 内屏', '自定义')]
    ck(r['g']['board'][1] + r['g']['board'][3] - r['lim_y'] == r['g']['strip_top'],
       '断言7：内屏 24×30 向上拖到头时棋盘下沿 %s 应与状态条上沿 %s 齐平'
       % (r['g']['board'][1] + r['g']['board'][3] - r['lim_y'], r['g']['strip_top']))

    # --- 断言 8：HUD 模式下棋盘可视区 = 菜单栏下沿 ~ HUD 上沿 ---
    cv, r = lookup[('Pura X Max 典藏版 内屏', '自定义')]
    ck(r['g']['board_area_h'] == r['g']['strip_top'] - cv.menu_px,
       '断言8：内屏 24×30 的棋盘可视区高 %s 应等于 HUD 上沿 %s 减菜单栏 %s'
       % (r['g']['board_area_h'], r['g']['strip_top'], cv.menu_px))

    # --- 断言 9：极限缩放（n = MAX_SCALE_INDEX）时两个计数仍要看得见、且两组不重叠 ---
    #
    # 坑（Codex 对抗性复审 P2，2026-11-01）：状态条原来跟着棋盘档位放大，
    # 30 列的局缩到 n=8 时 margin=720px，计时面板从 x=1216 起（大半在屏外），
    # 雷数面板整个跑到屏幕外 —— **两个计数都看不见**。
    # 现在状态条内容有自己的一档 su（两组放得下的最大档），留白也按「放得下」夹住。
    for cv in CANVASES:
        for bname, rows, cols, _mines in BOARDS:
            g = geometry(cv, rows, cols, MAX_SCALE_INDEX)
            for el in ('clock', 'time', 'mine_panel', 'mine_icon'):
                x, y, w, h = g['strip'][el]
                ck(x >= 0 and x + w <= cv.w,
                   '断言9：%s / %s 极限缩放时 %s %s 出画布（画布宽 %s，su=%s）'
                   % (cv.name, bname, el, g['strip'][el], cv.w, g['strip_unit']))
                ck(y >= 0 and y + h <= cv.h,
                   '断言9：%s / %s 极限缩放时 %s %s 出画布（画布高 %s）'
                   % (cv.name, bname, el, g['strip'][el], cv.h))
            left_end = g['strip']['time'][0] + g['strip']['time'][2]
            right_start = g['strip']['mine_panel'][0]
            ck(left_end <= right_start,
               '断言9：%s / %s 极限缩放时两组计数器重叠（左组到 %s，右组从 %s 起）'
               % (cv.name, bname, left_end, right_start))

    # --- 断言 10：平板（MatePad Pro 12.2）的期望值钉死（用户 2026-11-03 追加）---
    #
    # 平板的屏参数来自华为官方规格（2800x1840 / 274ppi / 3:2）与 DevEco 模拟器的
    # 「MatePad Pro 12」屏配置（density=360 -> densityPixels=2.25）。
    # 这里把横竖两种朝向、四个盘面的关键数字钉住，别以后又被改回去。
    #
    # 期望值取自 2026-11-03 的推演输出（check_layout.py --md 可复现）。
    TABLET_EXPECT = {
        # 画布名: {盘面名: (适配档n, 格边px, 棋盘x, 棋盘y, 横向溢出, 纵向溢出, HUD)}
        'MatePad Pro 12.2 (2800x1840)': {
            '初级': (4, 144, 752, 165, 0, 0, False),
            '中级': (2, 72, 824, 301, 0, 0, False),
            '高级': (2, 72, 320, 301, 0, 0, False),
            '自定义': (2, 72, 320, 42, 0, 58, True),
        },
        'MatePad Pro 12.2 竖屏': {
            '初级': (5, 180, 110, 451, 0, 0, False),
            '中级': (3, 108, 56, 461, 0, 0, False),
            '高级': (2, 72, -160, 781, 320, 0, False),
            '自定义': (2, 72, -160, 493, 320, 0, False),
        },
    }
    for cv_name, boards in TABLET_EXPECT.items():
        for board_name, exp in boards.items():
            key = (cv_name, board_name)
            if key not in lookup:
                fails.append('断言10：缺少 %s / %s' % (cv_name, board_name))
                continue
            cv, r = lookup[key]
            g = r['g']
            got = (r['fit'], g['tile'], g['board'][0], g['board'][1],
                   r['over_x'], r['over_y'], bool(g['hud']))
            ck(got == exp, '断言10：%s / %s 新 %s 旧 %s' % (cv_name, board_name, got, exp))

    # 平板的三条硬要求（不依赖具体数字，改了版式也不许破）：
    for cv_name in TABLET_EXPECT:
        for board_name in TABLET_EXPECT[cv_name]:
            cv, r = lookup[(cv_name, board_name)]
            g = r['g']
            # ① 任何盘面的状态条四个元素都必须在画布内（横向溢出时也要能拖到看全）
            for el in ('clock', 'time', 'mine_panel', 'mine_icon'):
                x, y, w, h = g['strip'][el]
                ck(x >= 0 and x + w <= cv.w,
                   '断言10：%s / %s 的 %s %s 出画布（宽 %s）' % (cv_name, board_name, el, g['strip'][el], cv.w))
            # ② 格边不能小于最小可点尺寸
            ck(g['tile'] >= MIN_CELL_PX,
               '断言10：%s / %s 的格边 %s px < %s' % (cv_name, board_name, g['tile'], MIN_CELL_PX))
            # ③ 横向溢出时必须留得下拖动的余量。
            #    lim_x = 溢出量的一半（棋盘居中，左右各溢出 over_x/2，
            #    所以往一边拖 over_x/2 就能把另一侧拉进画布），
            #    lim_y = 整个纵向溢出量（顶对齐，往上拖一个身位就齐平）。
            if r['over_x'] > 0:
                ck(abs(r['lim_x'] - r['over_x'] / 2.0) < 0.51,
                   '断言10：%s / %s 的横向平移上限 %s，应等于溢出量的一半 %s'
                   % (cv_name, board_name, r['lim_x'], r['over_x'] / 2.0))

    return fails


def main():
    as_md = '--md' in sys.argv
    all_res = []
    for cv in CANVASES:
        res = analyze(cv)
        all_res.append((cv, res))
        print(report(cv, res))
        print(details(cv, res))
        print(dialog_checks(cv))
    if as_md:
        print()
        print('<!-- ===== markdown 主表 ===== -->')
        print(summary_table(all_res))
        print()
        print('<!-- ===== markdown 状态条表 ===== -->')
        print(strip_table(all_res))

    fails = assert_rules(all_res)
    print()
    print('== 断言 ==')
    if fails:
        for f in fails:
            print('  FAIL: ' + f)
        print('  断言失败 %d 条' % len(fails))
        return 1
    print('  9 组断言全部通过（v3.0 基线 15 行不变 / 内屏 24×30 新数字 / 格边>=48 / '
          '状态条在画布内 / HUD 只在竖向溢出时出现 / 纵向平移上限=溢出量 / '
          '拖到底齐平 / 可视区=菜单栏到 HUD 顶 / 极限缩放时两个计数仍在屏内且不重叠）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
