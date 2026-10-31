# -*- coding: utf-8 -*-
"""render_stats.py —— 用 StatsWindow.ets 里实际写死的常量渲染统计窗口，和 information.jpg 并排对比。"""
import os
import re
from PIL import Image, ImageDraw, ImageFont

ETS = r"C:\Users\19161\saolei\entry\src\main\ets\common\StatsWindow.ets"
REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))

src = open(ETS, encoding="utf-8").read()


def num(name):
    m = re.search(r'^const\s+' + name + r'\s*:\s*number\s*=\s*([-\d.]+)\s*;', src, re.M)
    return float(m.group(1))


def col(name):
    m = re.search(r'^const\s+' + name + r'\s*:\s*string\s*=\s*\'(#\w{6})\'\s*;', src, re.M)
    return m.group(1)


def arr(name):
    m = re.search(r'^const\s+' + name + r'\s*:\s*number\[\]\s*=\s*\[([^\]]*)\]', src, re.M)
    return [float(v) for v in m.group(1).split(',')]


def font(size):
    for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
              r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, int(size))
            except Exception:
                pass
    return ImageFont.load_default()


W = int(num('WIDTH') if 'WIDTH' in src else 702)
H = int(num('HEIGHT') if 'HEIGHT' in src else 254)
im = Image.new("RGB", (W, H), (255, 0, 255))
d = ImageDraw.Draw(im)
FX, FY, TH = num('FRAME_X'), num('FRAME_Y'), num('TITLE_H')

# 玻璃边框
d.rectangle([0, 0, W - 1, H - 1], fill=col('C_FRAME_GLASS'))
# 标题栏渐变
stops = [(0, col('C_TITLE_TOP')), (0.07, col('C_TITLE_DARK')), (0.31, col('C_TITLE_MID')),
         (0.55, col('C_TITLE_LOW')), (0.90, col('C_TITLE_LOW')), (0.965, col('C_TITLE_EDGE'))]
for y in range(int(TH)):
    t = y / float(TH)
    c0, c1 = stops[0], stops[-1]
    for i in range(len(stops) - 1):
        if stops[i][0] <= t <= stops[i + 1][0]:
            c0, c1 = stops[i], stops[i + 1]
            break
    span = max(1e-6, c1[0] - c0[0])
    k = min(1.0, max(0.0, (t - c0[0]) / span))
    a = tuple(int(c0[1][i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c1[1][i:i + 2], 16) for i in (1, 3, 5))
    d.line([(0, y), (W - 1, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
# 客户区
cx, cy = int(FX), int(TH)
cw, ch = W - FX * 2, H - TH - FY - 1
d.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], fill=col('C_CLIENT'))
d.rectangle([cx - 1, cy, cx - 1, cy + ch - 1], fill=col('C_FRAME_LINE'))
d.rectangle([cx + cw, cy, cx + cw, cy + ch - 1], fill=col('C_FRAME_LINE'))
d.rectangle([cx - 1, cy + ch, cx + cw, cy + ch], fill=col('C_FRAME_LINE'))
d.rectangle([0, TH - 1, W - 1, TH - 1], fill=col('C_TITLE_SEP'))
d.rectangle([0, 0, W - 1, 0], fill=col('C_OUTER_LINE'))
d.rectangle([0, H - 1, W - 1, H - 1], fill=col('C_OUTER_LINE'))
d.rectangle([0, 0, 0, H - 1], fill=col('C_OUTER_LINE'))
d.rectangle([W - 1, 0, W - 1, H - 1], fill=col('C_OUTER_LINE'))
# 标题
d.text((num('TITLE_TEXT_X'), num('TITLE_TEXT_Y') + num('TEXT_INK_DY')), '扫雷统计信息',
       font=font(num('TITLE_FONT')), fill=col('C_TEXT'))
# 关闭按钮
cbx = W - int(num('CLOSE_RIGHT')) - int(num('CLOSE_W'))
d.rectangle([cbx, int(num('CLOSE_TOP')), cbx + int(num('CLOSE_W')) - 1,
             int(num('CLOSE_TOP')) + int(num('CLOSE_H')) - 1], fill=col('C_CLOSE_RED'))
ccx = cbx + num('CLOSE_W') / 2.0
ccy = num('CLOSE_TOP') + num('CLOSE_H') / 2.0
hw, hh = num('CLOSE_X_HALF_W'), num('CLOSE_X_HALF_H')
d.line([(ccx - hw, ccy - hh), (ccx + hw, ccy + hh)], fill=(255, 255, 255), width=2)
d.line([(ccx + hw, ccy - hh), (ccx - hw, ccy + hh)], fill=(255, 255, 255), width=2)
# 左：列表框
LX, LY, LW, LH = int(num('LIST_X')), int(num('LIST_Y')), int(num('LIST_W')), int(num('LIST_H'))
d.rectangle([LX, LY, LX + LW - 1, LY + LH - 1], fill=(255, 255, 255),
            outline=col('C_LIST_BORDER'))
sy = int(num('LIST_SEL_Y'))
d.rectangle([LX + 1, sy, LX + LW - 2, sy + int(num('LIST_SEL_H')) - 1], fill=col('C_SEL_BOTTOM'))
f12 = font(num('BTN_FONT'))
for i, lv in enumerate(['初级', '中级', '高级']):
    d.text((num('LIST_ITEM_X'), num('LIST_ITEM_Y0') + num('LIST_ITEM_DY') * i + num('TEXT_INK_DY')),
           lv, font=f12, fill=(255, 255, 255) if i == 0 else (0, 0, 0))
# 中：group box
GX, GY, GW, GH = int(num('GB_X')), int(num('GB_Y')), int(num('GB_W')), int(num('GB_H'))
gapx = int(num('GB_TITLE_GAP_X'))
gapw = int(num('GB_TITLE_GAP_W'))
d.rectangle([GX, GY, GX + GW - 1, GY], fill=col('C_CLIENT'))
d.line([(GX, GY), (GX + GW - 1, GY)], fill=col('C_GB_BORDER'))
d.line([(GX, GY), (GX, GY + GH - 1)], fill=col('C_GB_BORDER'))
d.line([(GX + GW - 1, GY), (GX + GW - 1, GY + GH - 1)], fill=col('C_GB_BORDER'))
d.line([(GX, GY + GH - 1), (GX + GW - 1, GY + GH - 1)], fill=col('C_GB_BORDER'))
d.rectangle([gapx, GY - 1, gapx + gapw - 1, GY + 1], fill=col('C_CLIENT'))
d.text((num('GB_TITLE_X'), num('GB_TITLE_Y') + num('TEXT_INK_DY')), '最佳时间',
       font=f12, fill=(0, 0, 0))
d.text((num('GB_TIME_X'), num('GB_ROW_Y') + num('TEXT_INK_DY')), '17', font=f12, fill=(0, 0, 0))
d.text((num('GB_DATE_X'), num('GB_ROW_Y') + num('TEXT_INK_DY')), 'Sat Nov 28 23:34:41 2015',
       font=font(9), fill=(0, 0, 0))
# 右栏
rows = ['已玩游戏: 3', '已胜游戏: 1', '获胜率: 33%', '最多连胜: 1', '最多连败: 2', '当前连局: 1']
for i, t in enumerate(rows):
    d.text((num('RC_X'), arr('RC_Y')[i] + num('TEXT_INK_DY')), t, font=f12, fill=(0, 0, 0))
# 底部按钮
cbx2 = int(num('BTN_CLOSE_X'))
cby2 = int(num('BTN_CLOSE_Y'))
cbw2 = int(num('BTN_CLOSE_W'))
cbh2 = int(num('BTN_CLOSE_H'))
d.rectangle([cbx2, cby2, cbx2 + cbw2 - 1, cby2 + cbh2 - 1], fill=col('C_DEF_BTN_RING'))
d.rectangle([cbx2 + 1, cby2 + 1, cbx2 + cbw2 - 2, cby2 + cbh2 - 2], fill=col('C_CLIENT'))
d.rectangle([cbx2, cby2, cbx2 + cbw2 - 1, cby2 + cbh2 - 1], outline=col('C_DEF_BTN_BORDER'))
rbx = int(num('BTN_RESET_X'))
rby = int(num('BTN_RESET_Y'))
rbw = int(num('BTN_RESET_W'))
rbh = int(num('BTN_RESET_H'))
d.rectangle([rbx, rby, rbx + rbw - 1, rby + rbh - 1], fill=col('C_BTN_FILL_BOTTOM'),
            outline=col('C_BTN_BORDER'))
d.text((cbx2 + cbw2 / 2.0, cby2 + cbh2 / 2.0), '关闭(C)', font=f12, fill=(0, 0, 0), anchor='mm')
d.text((rbx + rbw / 2.0, rby + rbh / 2.0), '重置(R)', font=f12, fill=(0, 0, 0), anchor='mm')

ref = Image.open(os.path.join(REF, "information.jpg")).convert("RGB")
row = Image.new("RGB", (ref.width + W + 12, max(ref.height, H)), (255, 255, 255))
row.paste(ref, (0, 0))
row.paste(im, (ref.width + 12, 0))
path = os.path.join(OUT, "render_stats.png")
row.save(path)
print("saved", path, row.size)
