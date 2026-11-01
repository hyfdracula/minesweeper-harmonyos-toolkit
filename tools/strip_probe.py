# -*- coding: utf-8 -*-
r"""状态条计数器面板探针：为什么「状态条上找不到绿色面板」。

背景
----
tools/click_matrix.py 的 _strip_panel_rect() 靠**绿色像素**找状态条上那两个
计数器面板（绿色判定与 tools/sevenseg_read.py 的 _green_mask() 一样：
``g > 90 and g > r+25 and g > b+25``）。

真机 Pura X Max（1201pd 那轮）报「状态条上找不到绿色面板」，模拟器 Mate 90 Pro
（1201a 那轮）同批用例全过。差别在**外观**：真机那轮跑的是**蓝**外观（布局日志
``外观=蓝/扫雷``），模拟器那轮跑的是**绿**外观。

而计数器面板的精灵 RECT_COUNTER 是画在 **boardSheet**（蓝/绿两套图集）里的：

    原版 blueSheet  [0..79, 1155..1210]  绿判定像素 = 0      （蓝灰凹槽）
    原版 greenSheet [0..79, 1155..1210]  绿判定像素 = 2521   （LED 绿 61,147,46）

原版 Win7 就是这样：**蓝外观的计数器是蓝灰凹槽，不是绿面板**；绿外观才是 LED 绿。
本仓 rawfile 与原版逐字节相同（blueSheet sha256 c2ce51fd…，greenSheet a480cc06…），
所以这不是移植走样，是**工具的「找绿」假设只对绿外观成立**。

这个脚本只读截图，不碰设备、不碰应用仓。

用法
----
    python tools\strip_probe.py <截图路径>
    python tools\strip_probe.py <截图路径> --strip-top 1371 --canvas-y 0 --tile 144 --canvas-w 2584
    python tools\strip_probe.py <截图路径> --layout phone|emu
    python tools\strip_probe.py <截图路径> --thumb docs\verify\PHONE_STRIP_xxx.png

输出：绿口径（复现报错）+ 饱和色口径（找到真正的面板）+ 与应用算法预期几何的差值。
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

# 两轮已知的布局（来源：真机 hilog 布局日志 / 模拟器同批截图量出来的）
KNOWN_LAYOUTS = {
    'phone': {
        'label': '真机 Pura X Max (CM_1201pd_*)',
        'canvas_w': 2584, 'canvas_h': 1644,
        'strip_top': 1371, 'canvas_y': 110,
        'tile': 144, 'unit': 8,
        'board_x': 644, 'board_y': 75,
        'shot': 'CM_1201pd_board_statusbar_no_open.jpeg',
    },
    'emu': {
        'label': '模拟器 Mate 90 Pro (CM_1201a_*)',
        'canvas_w': 1280, 'canvas_h': 2598,
        'strip_top': 1864, 'canvas_y': -3,
        'tile': 108, 'unit': 6,
        'board_x': 156, 'board_y': 892,
        'shot': 'CM_1201a_board_statusbar_no_open.jpeg',
    },
}

# 面板/七段的几何（与 entry/src/main/ets/common/SevenSeg.ets、Theme.ets 一致）
PANEL_W, PANEL_H = 40, 21           # 面板外框（参考像素）
PANEL_BORDER = 2                   # 面板精灵四周边框（参考像素）
INNER_W, INNER_H = 36, 17          # 截图里量到的「内区」尺寸
STRIP_CLOCK_SIZE, STRIP_GAP, STRIP_BAND = 25, 6, 32

# 饱和色判定（对蓝外观也管用）
CHROMA_MIN = 40
GREEN_MIN = 90
GREEN_DOM = 25


def load(path):
    im = Image.open(path).convert('RGB')
    return np.array(im).astype(np.int16)


def green_mask(a):
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (g > GREEN_MIN) & (g > r + GREEN_DOM) & (g > b + GREEN_DOM)


def chroma_mask(a):
    """饱和色：蓝外观的凹槽 (49,86,156) 和绿外观的 LED (61,147,46) 都过，
    状态条底色 (198,205,221) / 银灰零件 / 白色数码管都过不了。"""
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return (mx - mn) >= CHROMA_MIN


def runs(mask, gap=3):
    """把「有内容的列」并成连续段（与 click_matrix 的并段口径一致，gap=3）。"""
    idx = np.where(mask.any(axis=0))[0]
    if len(idx) == 0:
        return []
    out = []
    s = p = int(idx[0])
    for v in idx[1:]:
        v = int(v)
        if v > p + gap:
            out.append((s, p))
            s = v
        p = v
    out.append((s, p))
    return out


def row_runs(mask):
    idx = np.where(mask.any(axis=1))[0]
    if len(idx) == 0:
        return []
    out = []
    s = p = int(idx[0])
    for v in idx[1:]:
        v = int(v)
        if v > p + 3:
            out.append((s, p))
            s = v
        p = v
    out.append((s, p))
    return out


def app_panel_geometry(lay):
    """照抄 GameController.drawStatusStrip 的算法，算两个面板的预期位置。

    抄的是 app 仓 entry/src/main/ets/common/GameController.ets 第 840~925 行。
    """
    u = lay['unit']
    canvas_w = lay['canvas_w']
    board_x = lay['board_x']
    tile = lay['tile']
    col_count = 9
    board_right = board_x + col_count * tile
    margin = 0                       # stripMargin(9) 对 9 列返回 0（Theme.ets）
    group_ref = STRIP_CLOCK_SIZE + STRIP_GAP + PANEL_W          # 71
    max_su = 2 * int(canvas_w / (2 * group_ref) / 2)
    su = max(2, min(u, max_su))
    group_w = group_ref * su
    anchor_margin = min(margin, max(0, int((canvas_w - 2 * group_w) / 2)))
    clock_x = max(0, min(max(board_x + margin, anchor_margin),
                         canvas_w - group_w - anchor_margin))
    strip_top = lay['strip_top']
    content_top = (strip_top + round((STRIP_BAND - STRIP_CLOCK_SIZE) / 2) * u) if su == u \
        else (strip_top + round((STRIP_BAND * u - STRIP_CLOCK_SIZE * su) / 2))
    time_x = clock_x + (STRIP_CLOCK_SIZE + STRIP_GAP) * su
    time_y = content_top + round((STRIP_CLOCK_SIZE - PANEL_H) * su / 2)
    icon_x = min(board_right - margin - STRIP_CLOCK_SIZE * su,
                 canvas_w - anchor_margin - STRIP_CLOCK_SIZE * su)
    icon_x = max(icon_x, clock_x + group_w + (STRIP_GAP + PANEL_W) * su)
    icon_x = min(icon_x, canvas_w - STRIP_CLOCK_SIZE * su)
    mine_x = icon_x - (STRIP_GAP + PANEL_W) * su
    mine_y = time_y
    inner = []
    for x in (time_x, mine_x):
        inner.append((x + PANEL_BORDER * su, mine_y if x == mine_x else time_y,
                      INNER_W * su, INNER_H * su))
    return {'su': su, 'max_su': max_su, 'content_top': content_top,
            'clock_x': clock_x, 'time_x': time_x, 'time_y': time_y,
            'mine_x': mine_x, 'icon_x': icon_x, 'inner': inner}


def detect_canvas_y(a, lay):
    """量画布顶在屏幕上的纵向偏移（棋盘第一行砖色上沿 - 棋盘原点 y）。

    与 click_matrix.probe_canvas_y() 同一口径，但这里直接用饱和色行段
    （砖块/绿砖都是饱和色，状态条底色不是）。
    """
    sat = chroma_mask(a)
    cnt = sat.sum(axis=1)
    need = max(20, int(lay['canvas_w'] * 0.5))
    y = 0
    while y < len(cnt):
        if cnt[y] >= need:
            y0 = y
            while y < len(cnt) and cnt[y] >= need:
                y += 1
            return y0 - lay['board_y']
        y += 1
    return None


def proposed_boxes(a, y0, canvas_bottom, su):
    """拟议的修法（主题无关）：用「面板本体=饱和色」找面板，再按 su 归一化内框尺寸。

    这是给 click_matrix._strip_panel_rect 用的替换算法，这里只用来自检。
    """
    band = chroma_mask(a)[y0:canvas_bottom, :]
    out = []
    min_panel_w = INNER_W * su - 6
    for x0, x1 in runs(band):
        if x1 - x0 < min_panel_w:
            continue
        sub = band[:, x0:x1 + 1]
        yy = np.where(sub.any(axis=1))[0]
        if len(yy) == 0:
            continue
        top = int(yy.min())
        j = top - 1
        while j >= 0 and band[j, x0:x1 + 1].sum() > (x1 - x0) * 0.6:
            top = j
            j -= 1
        w, h = INNER_W * su, INNER_H * su
        cx = (x0 + x1) / 2.0
        cy = top + (int(yy.max()) - top) / 2.0 + y0
        out.append((int(round(cx - w / 2)), int(round(cy - h / 2)), w, h))
    return out


def self_check(a, boxes):
    """用 tools/sevenseg_read.py 反解面板里的数字（只读导入，不改那个文件）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import sevenseg_read as ss
    except Exception as exc:                # pragma: no cover
        print('    (无法导入 sevenseg_read: %r)' % (exc,))
        return
    for i, box in enumerate(boxes):
        digits = ss.read_panel(a, box)
        if digits is None:
            print('    面板 %d box=%s 读不出来' % (i, box))
            continue
        txt = ''.join(str(t) for t in ss.decode(digits) if t is not None)
        print('    面板 %d box=%s 掩码=%s 读出=%r' % (i, box, digits, txt))


def report(path, lay, thumb=None):
    a = load(path)
    h, w = a.shape[:2]
    cy = lay['canvas_y']
    auto = detect_canvas_y(a, lay)
    y0 = cy + lay['strip_top']
    print('=' * 78)
    print('%s' % lay['label'])
    print('  截图 %s  %dx%d   画布 %dx%d   canvas_y=%d  strip_top=%d  -> 状态条带 y0=%d'
          % (os.path.basename(path), w, h, lay['canvas_w'], lay['canvas_h'], cy,
             lay['strip_top'], y0))
    print('  格边=%d unit=%d 棋盘原点=(%d,%d)  外观=%s'
          % (lay['tile'], lay['unit'], lay['board_x'], lay['board_y'], lay.get('appearance', '?')))
    if auto is not None:
        print('  实测画布顶偏移 canvas_y = %d（棋盘砖色上沿 - 棋盘原点 y）'
              % auto)
        if auto != cy:
            print('  ==> 与内置值 %d 不一致，下面另用实测值重算一遍' % cy)
            lay = dict(lay)
            lay['canvas_y'] = auto
            y0 = auto + lay['strip_top']
            print('      改用 canvas_y=%d -> 状态条带 y0=%d' % (auto, y0))
    print()

    # ---- 1. 绿口径（复现 click_matrix 的报错）-------------------------
    g = green_mask(a)
    gb = g[y0:, :]
    gcols = runs(gb)
    print('[1] 绿口径（click_matrix._strip_panel_rect 的口径）')
    print('    全图绿像素 = %d' % int(g.sum()))
    ys, xs = np.nonzero(g)
    if len(ys):
        print('    全图绿色 bbox x=%d..%d y=%d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
    print('    状态条带内绿像素 = %d   绿列段 = %s'
          % (int(gb.sum()), [(a_, b_, b_ - a_ + 1) for a_, b_ in gcols]))
    if not gcols:
        print('    ==> len(cols)==0  ==>  抛「状态条上找不到绿色面板」（click_matrix.py 第 924 行）')
    print()

    # ---- 2. 饱和色口径 --------------------------------------------------
    # 注意：带只取到**画布底**为止。真机截图 y=1644..1828 是系统导航栏（白底），
    # click_matrix 现在的 band 是 img[y0:]（一直到屏幕底），改用饱和色口径时
    # 必须先把系统栏裁掉，否则系统栏里的彩色像素会被当成面板。
    canvas_bottom = min(h, cy + lay['canvas_h'])
    c = chroma_mask(a)
    cb = c[y0:canvas_bottom, :]
    ccols = runs(cb)
    print('[2] 饱和色口径（chroma = max-min >= %d，带取到画布底 %d）' % (CHROMA_MIN, canvas_bottom))
    print('    状态条带内饱和像素 = %d   饱和列段 = %s'
          % (int(cb.sum()), [(a_, b_, b_ - a_ + 1) for a_, b_ in ccols]))
    found = []
    for (x0, x1) in ccols:
        wdt = x1 - x0 + 1
        if wdt < 30:
            continue
        sub = cb[:, x0:x1 + 1]
        yy = np.where(sub.any(axis=1))[0]
        found.append((x0, int(yy.min()) + y0, wdt, int(yy.max()) - int(yy.min()) + 1))
    print('    宽度>=30 的候选面板 (x0,y0,w,h) = %s' % (found,))
    print()

    # ---- 3. 与应用算法预期几何对比 --------------------------------------
    geo = app_panel_geometry(lay)
    su = geo['su']
    print('[3] 应用算法算出的预期几何（抄 GameController.drawStatusStrip）')
    print('    su=%d (max_su=%d, u=%d)  min_panel_w=36*su-6=%d' % (su, geo['max_su'], lay['unit'],
                                                                 INNER_W * su - 6))
    print('    content_top=%d  clock_x=%d  time_x=%d time_y=%d  mine_x=%d  icon_x=%d'
          % (geo['content_top'], geo['clock_x'], geo['time_x'], geo['time_y'],
             geo['mine_x'], geo['icon_x']))
    print('    面板内区(绿/蓝底那块)预期(画布坐标): %s'
          % [tuple(int(v) for v in t) for t in geo['inner']])
    print('    面板内区预期(屏幕坐标, 加 canvas_y=%d): %s'
          % (cy, [(int(t[0]), int(t[1]) + cy, int(t[2]), int(t[3])) for t in geo['inner']]))
    for i, (px, py, pw, ph) in enumerate(geo['inner']):
        py += cy
        hit = None
        for (fx, fy, fw, fh) in found:
            if abs(fx - px) <= 12 and abs(fy - py) <= 24:
                hit = (fx, fy, fw, fh)
                break
        if hit is None:
            print('    面板 %d: 预期 (x=%d,y=%d,%dx%d) —— **饱和色口径没找到对应块**' % (i, px, py, pw, ph))
        else:
            print('    面板 %d: 预期 (x=%d,y=%d,%dx%d)  实测 (%d,%d,%dx%d)  偏差 dx=%d dy=%d dw=%d dh=%d'
                  % (i, px, py, pw, ph, hit[0], hit[1], hit[2], hit[3],
                     hit[0] - px, hit[1] - py, hit[2] - pw, hit[3] - ph))
    print()

    # ---- 4. 面板那一块的取色 -------------------------------------------
    print('[4] 面板区域的实际颜色（证明面板在、只是不是绿的）')
    for i, (px, py, pw, ph) in enumerate(geo['inner']):
        reg = a[py:py + ph, px:px + pw].reshape(-1, 3)
        cols, cnt = np.unique(reg, axis=0, return_counts=True)
        order = np.argsort(-cnt)[:5]
        gpx = int(((reg[:, 1] > GREEN_MIN) & (reg[:, 1] > reg[:, 0] + GREEN_DOM) &
                   (reg[:, 1] > reg[:, 2] + GREEN_DOM)).sum())
        chroma = reg.max(axis=1) - reg.min(axis=1)
        print('    面板 %d 区域 %dx%d: 主色 %s   其中绿判定像素=%d   chroma>=40 的像素=%d (%.1f%%)'
              % (i, pw, ph,
                 [(tuple(int(v) for v in cols[j]), int(cnt[j])) for j in order],
                 gpx, int((chroma >= CHROMA_MIN).sum()),
                 100.0 * float((chroma >= CHROMA_MIN).mean())))
    print()

    # ---- 5. 白色数码管在哪 ---------------------------------------------
    # 数码管是 LED 白 (250,250,252)；状态条底色是 (198,205,221)，
    # 所以阈值必须卡在两者之间（min>185 会把底色整片算进来）。
    wmask = a.min(axis=2) >= 235
    wb = wmask[y0:canvas_bottom, :]
    wr = row_runs(wb)
    wc = runs(wb)
    print('[5] 状态条带里的白色像素（自绘七段数码管，主题无关；带取到画布底）')
    print('    白色行段 = %s' % [(a_ + y0, b_ + y0) for a_, b_ in wr][:8])
    print('    白色列段 = %s' % [(a_, b_, b_ - a_ + 1) for a_, b_ in wc][:8])
    print('    白色像素数 = %d' % int(wb.sum()))
    print()

    # ---- 6. 拟议修法自检 ------------------------------------------------
    print('[6] 拟议修法自检（饱和色找面板 + 按 su 归一化内框）')
    boxes = proposed_boxes(a, y0, canvas_bottom, geo['su'])
    print('    找到的面板内框 = %s' % (boxes,))
    self_check(a, boxes)
    print()

    if thumb:
        out = thumb
        if not out.lower().endswith('.png'):
            out += '.png'
        os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)
        top = max(0, y0 - 60)
        bottom = min(h, y0 + 320)
        crop = a[top:bottom, :]
        img = Image.fromarray(crop.astype(np.uint8))
        try:
            from PIL import ImageDraw
            dr = ImageDraw.Draw(img)
            for (bx, by, bw, bh) in boxes:
                dr.rectangle([bx, by - top, bx + bw, by + bh - top], outline=(255, 0, 0), width=4)
            dr.rectangle([0, y0 - top, img.width, canvas_bottom - top], outline=(0, 160, 0), width=3)
        except Exception as exc:            # pragma: no cover
            print('    (标注失败: %r)' % (exc,))
        img.thumbnail((1400, 1400))
        img.save(out)
        print('缩略图已存: %s  (状态条带 %d..%d, 缩略 %dx%d；红框=面板内区 绿框=状态条带)'
              % (out, y0, bottom, img.width, img.height))
    return gcols, ccols, found


def main():
    ap = argparse.ArgumentParser(description='状态条计数器面板探针')
    ap.add_argument('path', help='截图路径')
    ap.add_argument('--layout', choices=sorted(KNOWN_LAYOUTS), default=None,
                    help='内置布局（phone=真机 / emu=模拟器）')
    ap.add_argument('--strip-top', type=int, default=None)
    ap.add_argument('--canvas-y', type=int, default=None)
    ap.add_argument('--tile', type=int, default=None)
    ap.add_argument('--canvas-w', type=int, default=None)
    ap.add_argument('--canvas-h', type=int, default=None)
    ap.add_argument('--unit', type=int, default=None)
    ap.add_argument('--board-x', type=int, default=None)
    ap.add_argument('--board-y', type=int, default=None)
    ap.add_argument('--appearance', default=None, help='蓝 / 绿（只打印用）')
    ap.add_argument('--thumb', default=None, help='输出一张状态条带缩略图到该路径')
    args = ap.parse_args()

    if not os.path.exists(args.path):
        print('找不到截图: %s' % args.path)
        sys.exit(2)

    key = args.layout
    if key is None:
        base = os.path.basename(args.path)
        key = 'phone' if '1201pd' in base else ('emu' if '1201a' in base else 'emu')
    lay = dict(KNOWN_LAYOUTS[key])
    for field in ('strip_top', 'canvas_y', 'tile', 'canvas_w', 'canvas_h', 'unit',
                  'board_x', 'board_y'):
        val = getattr(args, field)
        if val is not None:
            lay[field] = val
    if args.appearance:
        lay['appearance'] = args.appearance

    report(args.path, lay, args.thumb)


if __name__ == '__main__':
    main()
