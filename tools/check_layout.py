#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_layout.py —— 扫雷应用「版式数学推演」离线检查脚本

把 GameController.layout() / applyGeometry() / clampPan() / drawStatusStrip()
的几何公式**原样翻译**成 Python，然后对若干块画布 × 三种难度逐个算：
缩放档 n、格边、棋盘/状态条/菜单栏矩形、越界与重叠、整数像素。

公式来源（读的是 C:\\Users\\19161\\saolei 的当前源码，行号以 2026-10-31 为准）：
  Theme.ets:11           TILE = 18
  Theme.ets:13           MAX_SCALE_INDEX = 8
  Theme.ets:94-98        FRAME_W/H 与 FRAME_GAP_L/T/R/B = 30 / 30 / 29 / 32
  Theme.ets:125-133      STRIP_BAND=32 STRIP_CLOCK_SIZE=25 STRIP_PANEL_W=40
                         STRIP_PANEL_H=21 STRIP_GAP=6
  Theme.ets:145-147      stripMargin(cols) = max(0, round((cols-12.5)*TILE/7))
  WinMenu.ets:84-90      REF_FONT_PX=12 APP_FONT_VP=14 BAR_H_REF=18
  WinMenu.ets:163        MENU_BAR_H = 18 * (14/12) = 21 (vp)
  GameController.ets:216-246   layout()      —— 适配档 fit 的循环
  GameController.ets:249-262   applyGeometry() —— 各矩形
  GameController.ets:271-278   clampPan()
  GameController.ets:650-682   drawStatusStrip()

用法：  python tools/check_layout.py            （人读的报告）
        python tools/check_layout.py --md       （额外输出 markdown 表格）
"""

import math
import sys

# ---------------------------------------------------------------------------
# 常量（与 Theme.ets / WinMenu.ets 一一对应）
# ---------------------------------------------------------------------------
TILE = 18
MAX_SCALE_INDEX = 8
FRAME_GAP_L = 30
FRAME_GAP_T = 30
FRAME_GAP_R = 29
FRAME_GAP_B = 32
FRAME_GAP_X = FRAME_GAP_L + FRAME_GAP_R   # 59
FRAME_GAP_Y = FRAME_GAP_T + FRAME_GAP_B   # 62

STRIP_BAND = 32
STRIP_CLOCK_SIZE = 25
STRIP_PANEL_W = 40
STRIP_PANEL_H = 21
STRIP_GAP = 6

REF_FONT_PX = 12
APP_FONT_VP = 14
BAR_H_REF = 18
MENU_BAR_H = BAR_H_REF * (APP_FONT_VP / REF_FONT_PX)   # 21 vp


def js_round(x):
    """JavaScript Math.round 的语义（四舍五入，半数向上；-0.5 → 0）。
    Python 内置 round 是「银行家舍入」，语义不同，必须自己写。"""
    return math.floor(x + 0.5)


def strip_margin(cols):
    """Theme.ets stripMargin()"""
    return max(0, js_round((cols - 12.5) * TILE / 7))


# ---------------------------------------------------------------------------
# 画布清单（来自任务书）
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
        """GameController.pxScale = 1 / density"""
        return 1.0 / self.density

    @property
    def w_vp(self):
        return self.w / self.density

    @property
    def h_vp(self):
        return self.h / self.density

    @property
    def menu_h_px(self):
        """菜单栏高（设备像素）= 21 vp * density"""
        return MENU_BAR_H * self.density


CANVASES = [
    Canvas('Pura X Max 内屏', 2584, 1644, 2.75, '用户真机'),
    Canvas('Pura X Max 外屏', 1323, 1936, 2.75, '折起来后的竖屏 481x704vp'),
    Canvas('Mate X7 模拟器内屏', 2210, 2208, 3.125, '折叠屏'),
    Canvas('Mate 90 Pro 模拟器', 1280, 2598, 3.5, '又窄又长'),
]

DIFFICULTIES = [
    ('初级', 9, 9, 10),
    ('中级', 16, 16, 40),
    ('高级', 16, 30, 99),
]


# ---------------------------------------------------------------------------
# 几何计算：与 GameController 一一对应
# ---------------------------------------------------------------------------
def fit_scale(canvas, rows, cols):
    """GameController.layout() 第 1 步：算「整盘刚好放下」的档位。

    约束用的是 **frame**（棋盘 + 四周 59x62 单位的留白），不是棋盘本身。
    """
    fit = 1
    for n in range(1, MAX_SCALE_INDEX + 1):
        u = 2 * n
        fw = cols * TILE * u + FRAME_GAP_X * u
        fh = rows * TILE * u + FRAME_GAP_Y * u
        if fw <= canvas.w and fh <= canvas.h:
            fit = n
        else:
            break
    return fit


def fit_limits(canvas, rows, cols):
    """分别算「只受宽度限制」和「只受高度限制」时的最大档位，用于定位瓶颈。"""
    n_by_w = 0
    n_by_h = 0
    for n in range(1, MAX_SCALE_INDEX + 1):
        u = 2 * n
        fw = cols * TILE * u + FRAME_GAP_X * u
        fh = rows * TILE * u + FRAME_GAP_Y * u
        if fw <= canvas.w:
            n_by_w = n
        if fh <= canvas.h:
            n_by_h = n
    return n_by_w, n_by_h


def geometry(canvas, rows, cols, n):
    """applyGeometry()（panX = panY = 0）+ clampPan() 后的全部矩形（设备像素）。"""
    u = 2 * n
    tile = TILE * u
    board_w = cols * tile
    board_h = rows * tile
    frame_w = board_w + FRAME_GAP_X * u
    frame_h = board_h + FRAME_GAP_Y * u
    frame_x = js_round((canvas.w - frame_w) / 2)
    frame_y = js_round((canvas.h - frame_h) / 2)
    board_x = frame_x + FRAME_GAP_L * u
    board_y = frame_y + FRAME_GAP_T * u

    board_bottom = board_y + board_h
    board_right = board_x + board_w
    margin = strip_margin(cols) * u

    clock_x = board_x + margin
    clock_y = board_bottom + js_round((STRIP_BAND - STRIP_CLOCK_SIZE) / 2) * u
    time_x = clock_x + (STRIP_CLOCK_SIZE + STRIP_GAP) * u
    time_y = board_bottom + js_round((STRIP_BAND - STRIP_PANEL_H) / 2) * u
    icon_x = board_right - margin - STRIP_CLOCK_SIZE * u
    icon_y = board_bottom + js_round((STRIP_BAND - STRIP_CLOCK_SIZE) / 2) * u
    mine_x = icon_x - (STRIP_GAP + STRIP_PANEL_W) * u
    mine_y = board_bottom + js_round((STRIP_BAND - STRIP_PANEL_H) / 2) * u

    strip = {
        'band': (board_x, board_bottom, board_w, STRIP_BAND * u),
        'clock': (clock_x, clock_y, STRIP_CLOCK_SIZE * u, STRIP_CLOCK_SIZE * u),
        'time': (time_x, time_y, STRIP_PANEL_W * u, STRIP_PANEL_H * u),
        'mine_panel': (mine_x, mine_y, STRIP_PANEL_W * u, STRIP_PANEL_H * u),
        'mine_icon': (icon_x, icon_y, STRIP_CLOCK_SIZE * u, STRIP_CLOCK_SIZE * u),
    }
    menu = (0, 0, canvas.w, canvas.menu_h_px)
    return {
        'n': n, 'u': u, 'tile': tile,
        'board': (board_x, board_y, board_w, board_h),
        'frame': (frame_x, frame_y, frame_w, frame_h),
        'strip': strip, 'menu': menu,
    }


def overlaps(a, b):
    """两个矩形 (x, y, w, h) 的重叠区；无重叠返回 None。"""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x = max(ax, bx)
    y = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    if x2 <= x or y2 <= y:
        return None
    return (x, y, x2 - x, y2 - y)


def margins(canvas, rect):
    """矩形相对画布四边的余量（负数 = 越界）。"""
    x, y, w, h = rect
    return {
        'left': x,
        'right': canvas.w - (x + w),
        'top': y,
        'bottom': canvas.h - (y + h),
    }


def is_int(v):
    return isinstance(v, int) or float(v).is_integer()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def analyze(canvas):
    rows_out = []
    for dname, rows, cols, mines in DIFFICULTIES:
        fit = fit_scale(canvas, rows, cols)
        n_by_w, n_by_h = fit_limits(canvas, rows, cols)
        g = geometry(canvas, rows, cols, fit)

        board_m = margins(canvas, g['board'])
        frame_m = margins(canvas, g['frame'])
        strip_band = g['strip']['band']
        strip_m = margins(canvas, strip_band)
        menu_m = margins(canvas, g['menu'])

        board = g['board']
        frame = g['frame']

        # 越界判定
        board_over = [k for k, v in board_m.items() if v < 0]
        frame_over = [k for k, v in frame_m.items() if v < 0]
        strip_over = [k for k, v in strip_m.items() if v < 0]
        menu_over = [k for k, v in menu_m.items() if v < 0]

        # 重叠判定
        ov_strip_board = overlaps(strip_band, board)
        ov_menu_board = overlaps(g['menu'], board)
        ov_menu_strip = overlaps(g['menu'], strip_band)
        # 状态条四个元素互相压？
        elems = ['clock', 'time', 'mine_panel', 'mine_icon']
        elem_over = []
        for i in range(len(elems)):
            for j in range(i + 1, len(elems)):
                if overlaps(g['strip'][elems[i]], g['strip'][elems[j]]) is not None:
                    elem_over.append((elems[i], elems[j]))

        # 整数像素检查（设备像素）
        non_int = []
        for key in ('board', 'frame'):
            for i, v in enumerate(g[key]):
                if not is_int(v):
                    non_int.append('%s[%d]=%s' % (key, i, v))
        for key, rect in g['strip'].items():
            for i, v in enumerate(rect):
                if not is_int(v):
                    non_int.append('strip.%s[%d]=%s' % (key, i, v))
        # 每一格的左上角 + 数字原点 + 阴影条原点
        for r in range(rows):
            for c in range(cols):
                cx = board[0] + c * g['tile']
                cy = board[1] + r * g['tile']
                if not is_int(cx) or not is_int(cy):
                    non_int.append('cell(%d,%d)' % (r, c))
                # GameController.ets:430 数字：x + 3*u, y + 1.5*u
                if not is_int(cx + 3 * g['u']) or not is_int(cy + 1.5 * g['u']):
                    non_int.append('digit(%d,%d)' % (r, c))
                # GameController.ets:431/437 阴影条：y + 3*u
                if not is_int(cy + 3 * g['u']):
                    non_int.append('shadow(%d,%d)' % (r, c))
        # 状态条文字原点：timeX + STRIP_PANEL_W*u/2
        for k in ('time', 'mine_panel'):
            rect = g['strip'][k]
            if not is_int(rect[0] + STRIP_PANEL_W * g['u'] / 2):
                non_int.append('strip.%s.text' % k)

        # 缩放档用满程度
        board_w_frac = board[2] / canvas.w
        frame_w_frac = frame[2] / canvas.w
        # 若不计 frame 留白（只按棋盘本身），最大能到几档
        n_board_only = 0
        for n in range(1, MAX_SCALE_INDEX + 1):
            u = 2 * n
            if cols * TILE * u <= canvas.w and rows * TILE * u <= canvas.h:
                n_board_only = n
        # 「差多少像素就能再上一档」：按当前 fit 的下一档算，frame 需要多大
        n_next = fit + 1
        u_next = 2 * n_next
        need_w = cols * TILE * u_next + FRAME_GAP_X * u_next
        need_h = rows * TILE * u_next + FRAME_GAP_Y * u_next
        short_w = need_w - canvas.w          # >0 表示宽度差这么多
        short_h = need_h - canvas.h
        # 去掉 59x62 留白后，下一档差多少
        need_w0 = cols * TILE * u_next
        need_h0 = rows * TILE * u_next
        short_w0 = need_w0 - canvas.w
        short_h0 = need_h0 - canvas.h

        rows_out.append({
            'dname': dname, 'rows': rows, 'cols': cols, 'mines': mines,
            'fit': fit, 'n_by_w': n_by_w, 'n_by_h': n_by_h, 'n_board_only': n_board_only,
            'short_w': short_w, 'short_h': short_h,
            'short_w0': short_w0, 'short_h0': short_h0,
            'need_w': need_w, 'need_h': need_h,
            'g': g,
            'board_m': board_m, 'frame_m': frame_m, 'strip_m': strip_m, 'menu_m': menu_m,
            'board_over': board_over, 'frame_over': frame_over,
            'strip_over': strip_over, 'menu_over': menu_over,
            'ov_strip_board': ov_strip_board, 'ov_menu_board': ov_menu_board,
            'ov_menu_strip': ov_menu_strip, 'elem_over': elem_over,
            'non_int': non_int,
            'board_w_frac': board_w_frac, 'frame_w_frac': frame_w_frac,
            'binding': '宽' if n_by_w < n_by_h else ('高' if n_by_h < n_by_w else '两者同时'),
        })
    return rows_out


def fmt_rect(r):
    return '(%d,%d %dx%d)' % (r[0], r[1], r[2], r[3])


def report(cv, res, as_md=False):
    out = []
    w = out.append
    w('=' * 78)
    w('画布：%s  %d x %d px  (%.4f x %.4f vp)  density=%.4g  pxScale=%.4f  [%s]'
      % (cv.name, cv.w, cv.h, cv.w_vp, cv.h_vp, cv.density, cv.px_scale, cv.note))
    w('菜单栏高 = MENU_BAR_H %g vp = %.2f 设备像素' % (MENU_BAR_H, cv.menu_h_px))
    w('=' * 78)
    hdr = ('%-4s %-9s %3s %5s %6s %-22s %-22s %-22s %-24s %s'
           % ('难度', 'n(瓶颈)', '档', '格边', 'u',
              '棋盘矩形', '状态条带', '菜单栏', '余量(左/右/上/下, 棋盘)', '标记'))
    w(hdr)
    w('-' * 150)
    for r in res:
        g = r['g']
        b = g['board']
        strip = g['strip']['band']
        menu = g['menu']
        bm = r['board_m']
        flags = []
        if r['board_over']:
            flags.append('棋盘越界:' + ','.join(r['board_over']))
        if r['frame_over']:
            flags.append('底板越界:' + ','.join(r['frame_over']))
        if r['strip_over']:
            flags.append('状态条越界:' + ','.join(r['strip_over']))
        if r['ov_strip_board']:
            flags.append('状态条压棋盘')
        if r['ov_menu_board']:
            flags.append('菜单压棋盘')
        if r['ov_menu_strip']:
            flags.append('菜单压状态条')
        if r['elem_over']:
            flags.append('状态条元素互压')
        if r['non_int']:
            flags.append('非整数像素 x%d' % len(r['non_int']))
        if not flags:
            flags.append('OK')
        w('%-4s %-9s %3d %5d %6d %-22s %-22s %-22s %-24s %s'
          % (r['dname'], '%d(%s)' % (r['fit'], r['binding']),
             r['fit'], g['tile'], g['u'],
             fmt_rect(b), fmt_rect(strip),
             '(%d,%d %dx%d)' % (menu[0], menu[1], menu[2], round(menu[3], 2)),
             '%d/%d/%d/%d' % (bm['left'], bm['right'], bm['top'], bm['bottom']),
             '; '.join(flags)))
    w('')
    return '\n'.join(out)


def details(cv, res):
    """每格的详细数据 + 诊断。"""
    out = []
    w = out.append
    w('')
    w('【%s】逐项细节' % cv.name)
    w('-' * 78)
    for r in res:
        g = r['g']
        b = g['board']
        fr = g['frame']
        st = g['strip']
        w('')
        w('%s %dx%d / %d 雷' % (r['dname'], r['rows'], r['cols'], r['mines']))
        w('  适配档 n=%d (u=%d, 格边=%d px = %.4f vp)  瓶颈=%s'
          % (r['fit'], g['u'], g['tile'], g['tile'] / cv.density, r['binding']))
        w('    只看宽度最多 n=%d；只看高度最多 n=%d；若完全不计 59x62 留白最多 n=%d'
          % (r['n_by_w'], r['n_by_h'], r['n_board_only']))
        w('    再上一档（n=%d）需要 frame %dx%d px：宽差 %+d px，高差 %+d px'
          % (r['fit'] + 1, r['need_w'], r['need_h'], r['short_w'], r['short_h']))
        w('    不计留白时同一档需要 %dx%d px：宽差 %+d px，高差 %+d px'
          % (r['cols'] * TILE * 2 * (r['fit'] + 1), r['rows'] * TILE * 2 * (r['fit'] + 1),
             r['short_w0'], r['short_h0']))
        w('  底板 frame = %s   棋盘 = %s' % (fmt_rect(fr), fmt_rect(b)))
        w('  棋盘宽占画布 %.1f%%；底板宽占画布 %.1f%%' % (r['board_w_frac'] * 100, r['frame_w_frac'] * 100))
        w('  状态条带 = %s（紧贴棋盘下沿，落在 frame 的下留白里）' % fmt_rect(st['band']))
        for k in ('clock', 'time', 'mine_panel', 'mine_icon'):
            w('    %-11s = %s' % (k, fmt_rect(st[k])))
        w('  菜单栏 = (0,0 %dx%.2f px)  下沿 %.2f px' % (cv.w, cv.menu_h_px, cv.menu_h_px))
        w('  余量：棋盘 左%d 右%d 上%d 下%d ；底板 左%d 右%d 上%d 下%d'
          % (r['board_m']['left'], r['board_m']['right'], r['board_m']['top'], r['board_m']['bottom'],
             r['frame_m']['left'], r['frame_m']['right'], r['frame_m']['top'], r['frame_m']['bottom']))
        probs = []
        if r['frame_over']:
            probs.append('底板越界 ' + ','.join(r['frame_over']))
        if r['board_over']:
            probs.append('棋盘越界 ' + ','.join(r['board_over']))
        if r['strip_over']:
            probs.append('状态条越界 ' + ','.join(r['strip_over']))
        if r['ov_menu_board']:
            probs.append('菜单栏压住棋盘 %.1f px' % r['ov_menu_board'][3])
        if r['ov_strip_board']:
            probs.append('状态条压住棋盘')
        if r['elem_over']:
            probs.append('状态条元素互压 ' + str(r['elem_over']))
        if r['non_int']:
            probs.append('非整数像素 ' + ','.join(r['non_int'][:6]))
        w('  判定：' + ('；'.join(probs) if probs else '无越界、无重叠、全部整数像素'))
    return '\n'.join(out)


def summary_table(all_res):
    """markdown 大表：画布 x 难度。"""
    out = []
    w = out.append
    w('| 画布 | 难度 | n | 瓶颈 | 格边 px | 棋盘矩形 | 状态条带 | 底板矩形 | 余量 左/右/上/下 | 越界/重叠 |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    for cv, res in all_res:
        for r in res:
            g = r['g']
            b = g['board']
            fr = g['frame']
            st = g['strip']['band']
            bm = r['board_m']
            flags = []
            if r['frame_over']:
                flags.append('底板越界(' + ','.join(r['frame_over']) + ')')
            if r['board_over']:
                flags.append('棋盘越界')
            if r['strip_over']:
                flags.append('状态条越界')
            if r['ov_menu_board']:
                flags.append('菜单压棋盘')
            if r['ov_strip_board']:
                flags.append('状态条压棋盘')
            if r['elem_over']:
                flags.append('条内互压')
            if not flags:
                flags.append('无')
            w('| %s | %s %dx%d | %d | %s | %d | %s | %s | %s | %d/%d/%d/%d | %s |'
              % (cv.name, r['dname'], r['rows'], r['cols'], r['fit'], r['binding'],
                 g['tile'], fmt_rect(b), fmt_rect(st), fmt_rect(fr),
                 bm['left'], bm['right'], bm['top'], bm['bottom'],
                 '；'.join(flags)))
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# 对话框 / 统计窗口 / 自定义框 的缩放与是否装得下
# ---------------------------------------------------------------------------
# WinDialog.ets：lose 483x288 / win 396x340 / about 400x320 / help 314x197
DLG_SIZES = [('结束(负)', 483, 288), ('结束(胜)', 396, 340), ('关于', 400, 320), ('帮助', 314, 197)]
# StatsWindow.ets：702x254
STATS_W, STATS_H = 702, 254
# CustomField.ets: DLG_W=280 DLG_H=200；NumKeypad.ets: 3*34+2*4=110, 4*30+3*4=132
DLG_W, DLG_H = 280, 200
KEY_W, KEY_H = 110, 132


def dialog_checks(cv):
    out = []
    w = out.append
    w('')
    w('【%s】对话框 / 统计窗口 / 自定义框' % cv.name)
    w('-' * 78)
    s_dlg = max(1, min(2, cv.w / 1400.0))
    s_stats = max(1, min(2, cv.w / 1500.0))
    w('  结束对话框缩放 s = max(1, min(2, canvasW/1400)) = %.4f  %s'
      % (s_dlg, '整数' if is_int(s_dlg) else '← 小数，对话框内部按参考像素×小数缩放，按钮/文字落在非整数设备像素上'))
    for nm, dw, dh in DLG_SIZES:
        wpx, hpx = dw * s_dlg, dh * s_dlg
        ox = js_round((cv.w - wpx) / 2)
        oy = js_round((cv.h - hpx) / 2)
        fits = (ox >= 0 and oy >= 0 and ox + wpx <= cv.w and oy + hpx <= cv.h)
        w('    %-8s 参考 %dx%d → %dx%d px，原点 (%d,%d)  %s'
          % (nm, dw, dh, round(wpx, 2), round(hpx, 2), ox, oy,
             '装得下' if fits else '× 装不下'))
    w('  统计窗口缩放 s = max(1, min(2, canvasW/1500)) = %.4f  %s'
      % (s_stats, '整数' if is_int(s_stats) else '← 小数'))
    wpx, hpx = STATS_W * s_stats, STATS_H * s_stats
    ox = js_round((cv.w - wpx) / 2)
    oy = js_round((cv.h - hpx) / 2)
    fits = (ox >= 0 and oy >= 0 and ox + wpx <= cv.w and oy + hpx <= cv.h)
    w('    统计窗口 %dx%d → %dx%d px，原点 (%d,%d)  %s'
      % (STATS_W, STATS_H, round(wpx, 2), round(hpx, 2), ox, oy,
         '装得下' if fits else '× 装不下'))
    # 自定义框：customLayout() 用的 this.dialogScale 只有 drawDialog() 才会赋值，
    # 而 draw() 里 drawCustom() 排在 drawDialog() 之前 → 首次打开时用的是陈旧值。
    total_w = DLG_W * s_dlg + 12 * s_dlg + KEY_W * s_dlg
    total_h = max(DLG_H * s_dlg, KEY_H * s_dlg)
    fits = total_w <= cv.w and total_h <= cv.h
    w('  自定义框 + 数字键盘：宽 %d×s=%s px，高 %d×s=%s px  %s'
      % (DLG_W + 12 + KEY_W, round(total_w, 2), max(DLG_H, KEY_H), round(total_h, 2),
         '装得下' if fits else '× 装不下'))
    w('    注意：dialogScale 只在 drawDialog()→dialogLayout() 里赋值，而 draw() 中 drawCustom() 排在 drawDialog() 之前，')
    w('      且打开自定义框时 this.dialog=null → drawDialog() 直接 return → 自定义框永远用陈旧的 dialogScale。')
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# 建议版 fit：把「画出来但看不见」的 59x62 留白从预算里去掉
# ---------------------------------------------------------------------------
def recommended_scale(cv, rows, cols):
    """建议的适配档：
       横向：棋盘本身 <= 画布宽（左右留白在手机版不画）
       纵向：棋盘 + 状态条带(32u) + 菜单栏(21vp) <= 画布高
    """
    best = 1
    for n in range(1, MAX_SCALE_INDEX + 1):
        u = 2 * n
        w_ok = cols * TILE * u <= cv.w
        h_ok = rows * TILE * u + STRIP_BAND * u + cv.menu_h_px <= cv.h
        if w_ok and h_ok:
            best = n
        else:
            break
    return best


def recommendation(cv, res):
    out = []
    w = out.append
    w('')
    w('【%s】缩放档改进测算（建议口径：横向只算棋盘，纵向算 棋盘+状态条带+菜单栏）' % cv.name)
    w('-' * 78)
    w('  %-4s %-8s %-12s %-12s %-8s' % ('难度', '现状 n', '现状格边px', '建议 n', '建议格边px'))
    for r in res:
        rn = recommended_scale(cv, r['rows'], r['cols'])
        w('  %-4s %-8d %-12d %-12d %-8d  %s'
          % (r['dname'], r['fit'], r['g']['tile'], rn, TILE * 2 * rn,
             '不变' if rn == r['fit'] else '↑ 格边 ×%.2f' % ((TILE * 2 * rn) / r['g']['tile'])))
    return '\n'.join(out)


def gap_table(all_res):
    """markdown 表：每格「再上一档差多少像素」。手工誊写容易串行，直接由脚本生成。"""
    out = []
    w = out.append
    w('| 画布 | 难度 | 当前 n | 再上一档需要的 frame | 宽差 | 高差 | 不计 59x62 留白时同一档需要 | 宽差 | 高差 |')
    w('|---|---|---|---|---|---|---|---|---|')
    for cv, res in all_res:
        for r in res:
            w('| %s | %s | %d | %dx%d | %+d | %+d | %dx%d | %+d | %+d |'
              % (cv.name, r['dname'], r['fit'], r['need_w'], r['need_h'],
                 r['short_w'], r['short_h'],
                 r['cols'] * TILE * 2 * (r['fit'] + 1), r['rows'] * TILE * 2 * (r['fit'] + 1),
                 r['short_w0'], r['short_h0']))
    return '\n'.join(out)


def main():
    as_md = '--md' in sys.argv
    all_res = []
    for cv in CANVASES:
        res = analyze(cv)
        all_res.append((cv, res))
        print(report(cv, res))
        print(details(cv, res))
        print(dialog_checks(cv))
        print(recommendation(cv, res))
    if as_md:
        print()
        print('<!-- ===== markdown 大表 ===== -->')
        print(summary_table(all_res))
        print()
        print('<!-- ===== markdown 差值表 ===== -->')
        print(gap_table(all_res))
    return 0


if __name__ == '__main__':
    sys.exit(main())
