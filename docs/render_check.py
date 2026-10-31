# -*- coding: utf-8 -*-
"""
render_check.py —— 自检：用 WinDialog.ets 里**实际写死的常量**渲染三个对话框，
和参考图并排输出，肉眼核对版式（几何 / 按钮 / 文字行 / 标题栏）。

常量直接从 .ets 源文件里正则抠出来，避免脚本与源码写歪。
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont

ETS = r"C:\Users\19161\saolei\entry\src\main\ets\common\WinDialog.ets"
REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))

src = open(ETS, encoding="utf-8").read()


def const(name):
    m = re.search(r'^const\s+' + name + r'\s*:\s*number\s*=\s*([-\d.]+)\s*;', src, re.M)
    if not m:
        raise KeyError(name)
    return float(m.group(1))


def color(name):
    m = re.search(r'^const\s+' + name + r'\s*:\s*string\s*=\s*\'(#\w{6})\'\s*;', src, re.M)
    if not m:
        raise KeyError(name)
    return m.group(1)


FONT_CAND = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
             r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\segoeui.ttf"]


def load_font(size):
    for f in FONT_CAND:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, int(size))
            except Exception:
                pass
    return ImageFont.load_default()


def draw_dialog(w, h, title, lines, buttons, chrome, icon_pos=None):
    im = Image.new("RGB", (w, h), (255, 0, 255))
    d = ImageDraw.Draw(im)
    classic = chrome == 'classic'
    FX, FY, TH = const('FRAME_X'), const('FRAME_Y'), const('TITLE_H')
    c_glass = color('C_C_FRAME_GLASS') if classic else color('C_FRAME_GLASS')
    c_line = color('C_C_FRAME_LINE') if classic else color('C_FRAME_LINE')
    c_out = color('C_C_OUTER_LINE') if classic else color('C_OUTER_LINE')
    c_sep = color('C_C_TITLE_SEP') if classic else color('C_TITLE_SEP')
    if classic:
        stops = [(0, color('C_C_TITLE_TOP')), (0.035, color('C_C_TITLE_TOP')),
                 (0.07, color('C_C_TITLE_MID')), (0.45, color('C_C_TITLE_MID2')),
                 (0.55, color('C_C_TITLE_LOW')), (0.93, color('C_C_TITLE_BOTTOM')),
                 (0.965, color('C_C_TITLE_EDGE'))]
    else:
        stops = [(0, color('C_TITLE_TOP')), (0.04, color('C_TITLE_TOP')),
                 (0.07, color('C_TITLE_MID')), (0.55, color('C_TITLE_MID')),
                 (0.93, color('C_TITLE_BOTTOM')), (0.965, color('C_TITLE_EDGE'))]

    d.rectangle([0, 0, w - 1, h - 1], fill=c_glass)
    # 标题栏渐变（逐行插值）
    THi = int(TH)
    for y in range(THi):
        t = y / float(THi)
        c0, c1 = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                c0, c1 = stops[i], stops[i + 1]
                break
        span = max(1e-6, c1[0] - c0[0])
        k = min(1.0, max(0.0, (t - c0[0]) / span))
        a = tuple(int(c0[1][i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(c1[1][i:i + 2], 16) for i in (1, 3, 5))
        d.line([(0, y), (w - 1, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    # 客户区
    cx, cy = FX, TH
    cw, ch = w - FX * 2, h - TH - FY - 1
    d.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], fill=color('C_CLIENT'))
    d.rectangle([cx - 1, cy, cx - 1, cy + ch - 1], fill=c_line)
    d.rectangle([cx + cw, cy, cx + cw, cy + ch - 1], fill=c_line)
    d.rectangle([cx - 1, cy + ch, cx + cw, cy + ch], fill=c_line)
    d.rectangle([0, TH - 1, w - 1, TH - 1], fill=c_sep)
    d.rectangle([0, 0, w - 1, 0], fill=c_out)
    d.rectangle([0, h - 1, w - 1, h - 1], fill=c_out)
    d.rectangle([0, 0, 0, h - 1], fill=c_out)
    d.rectangle([w - 1, 0, w - 1, h - 1], fill=c_out)
    # 标题
    tf = load_font(const('TITLE_FONT'))
    d.text((const('TITLE_TEXT_X'), const('TITLE_TEXT_Y') + const('TEXT_INK_DY')),
           title, font=tf, fill=color('C_TEXT'))
    # 关闭按钮
    cw2 = const('CLOSE_W_CLASSIC') if classic else const('CLOSE_W_AERO')
    cr2 = const('CLOSE_RIGHT_CLASSIC') if classic else const('CLOSE_RIGHT_AERO')
    bx, by = w - cr2 - cw2, const('CLOSE_TOP')
    bh = const('CLOSE_H')
    d.rectangle([bx, by, bx + cw2 - 1, by + bh - 1],
                fill=color('C_C_CLOSE_MID') if classic else color('C_CLOSE_MID'))
    ccx, ccy = bx + cw2 / 2.0, by + bh / 2.0
    hw, hh = const('CLOSE_X_HALF_W'), const('CLOSE_X_HALF_H')
    d.line([(ccx - hw, ccy - hh), (ccx + hw, ccy + hh)], fill=(255, 255, 255), width=2)
    d.line([(ccx + hw, ccy - hh), (ccx - hw, ccy + hh)], fill=(255, 255, 255), width=2)
    # 正文
    for (txt, x, y, size, align) in lines:
        f = load_font(size)
        if align == 'center':
            d.text((x, y + const('TEXT_INK_DY')), txt, font=f, fill=color('C_TEXT'), anchor='ma')
        else:
            d.text((x, y + const('TEXT_INK_DY')), txt, font=f, fill=color('C_TEXT'), anchor='la')
    # 按钮
    for (bx2, by2, bw2, bh2, label) in buttons:
        d.rectangle([bx2, by2, bx2 + bw2 - 1, by2 + bh2 - 1],
                    fill=color('C_BTN_BOTTOM'), outline=color('C_BTN_BORDER'))
        f = load_font(const('BTN_FONT'))
        d.text((bx2 + bw2 / 2.0, by2 + bh2 / 2.0), label, font=f, fill=color('C_TEXT'), anchor='mm')
    if icon_pos:
        d.rectangle([icon_pos[0], icon_pos[1], icon_pos[0] + 24, icon_pos[1] + 24],
                    outline=(200, 0, 0))
    return im


# ---- 失败框（常量与 WinDialog.ets loseSpec 一致）----
lose = draw_dialog(
    483, 288, '游戏失败',
    [('不好意思，您输了！下次走运!', 236, 51, 14, 'center'),
     ('时间: 1秒', 22, 93, 12, 'left'),
     ('已玩游戏: 2', 23, 140, 12, 'left'),
     ('已胜游戏: 0', 23, 164, 12, 'left'),
     ('百分比: 0%', 203, 164, 12, 'left')],
    [(17, 236, 144, 26, '退出(X)'), (170, 236, 144, 26, '换个难度(D)'),
     (323, 236, 144, 26, '再玩一局(P)')], 'aero')

win = draw_dialog(
    396, 340, '游戏胜利',
    [('恭喜！您赢了！', 194, 44, 14, 'center'),
     ('您所用的时间是这个难度级别的最短时间!', 197, 77, 12, 'center'),
     ('时间: 17秒', 22, 127, 12, 'left'),
     ('最快时间: 17秒', 22, 161, 12, 'left'),
     ('日期: Sat Nov 28 23:34:41 2015', 210, 161, 12, 'left'),
     ('已玩游戏: 3', 23, 185, 12, 'left'),
     ('已胜游戏: 1', 23, 210, 12, 'left'),
     ('百分比: 33%', 209, 210, 12, 'left')],
    [(23, 252, 136, 27, '再玩一局(P)'), (23, 286, 136, 27, '退出(Q)')], 'aero')

about = draw_dialog(
    314, 197, '关于 扫雷',
    [('HarmonyOS 移植版', 86, 64, 12, 'left'),
     ('原版：Windows 7 扫雷', 86, 92, 12, 'left'),
     ('适配：华为 Pura X Max 折叠屏', 86, 120, 12, 'left')],
    [(206, 153, 88, 25, '确定')], 'classic', icon_pos=[38, 78, 25, 25])

# ---- 并排输出 ----
ref_loss = Image.open(os.path.join(REF, "loss.jpg")).convert("RGB")
ref_win = Image.open(os.path.join(REF, "win.jpg")).convert("RGB")
ref_about = Image.open(os.path.join(REF, "about.jpg")).convert("RGB").crop((152, 101, 466, 298))

rows = []
for ref, mine in ((ref_loss, lose), (ref_win, win), (ref_about, about)):
    H = max(ref.height, mine.height)
    row = Image.new("RGB", (ref.width + mine.width + 12, H), (255, 255, 255))
    row.paste(ref, (0, 0))
    row.paste(mine, (ref.width + 12, 0))
    rows.append(row)

W = max(r.width for r in rows)
H = sum(r.height for r in rows) + 12 * (len(rows) - 1)
sheet = Image.new("RGB", (W, H), (255, 255, 255))
yy = 0
for r in rows:
    sheet.paste(r, (0, yy))
    yy += r.height + 12
path = os.path.join(OUT, "render_check.png")
sheet.save(path)
print("saved", path, sheet.size)
