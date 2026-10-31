# -*- coding: utf-8 -*-
"""
dlg_measure.py —— 用 PIL 实测三张参考图里对话框的版式。

参考图（版式依据，1 倍像素）：
    loss.jpg   483x288  失败框整框
    win.jpg    396x340  胜利框整框
    about.jpg  615x408  整窗截图，「关于扫雷」对话框只是其中一块

量法（对抗 JPEG 压缩噪点）：
  * 不用单点阈值判断边缘，改为「按行/按列的亮度跳变」：
      - 竖线：整列中位亮度明显偏离邻列 => 竖线
      - 横线：一行里连续 >= minrun 个像素偏离底色 => 横线
  * 文字行：客户区内「暗像素计数 >= 2」的连续行带 => 文字带；
      带内再按列切出字符块，得到每个字符的 x 范围与字形上下边界（字高）。
  * 颜色：区域内取三通道中位色（对 JPEG 色度噪声稳健）。

用法:
    python dlg_measure.py            # 打印全部实测结果 + 生成网格标注图
    python dlg_measure.py loss.jpg   # 只测一张
结果同时写到同目录 dialog_layout.md（留档），网格标注图写到 dialog_grid_*.png。
"""
import os
import sys
from PIL import Image, ImageDraw

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUTDIR = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.join(OUTDIR, "dialog_layout.md")

_REPORT = []


def p(s=""):
    print(s)
    _REPORT.append(s)


def g_px(im):
    return im.convert("L").load()


def median(vals):
    vals = sorted(vals)
    return vals[len(vals) // 2]


def med_rgb(im, x0, y0, x1, y1):
    r = []; g = []; b = []
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = im.getpixel((x, y))
            r.append(c[0]); g.append(c[1]); b.append(c[2])
    return (median(r), median(g), median(b))


def hexs(c):
    return '#%02x%02x%02x' % c


def col_median(im, x, y0, y1):
    px = g_px(im)
    return median([px[x, y] for y in range(y0, y1 + 1)])


def row_median(im, y, x0, x1):
    px = g_px(im)
    return median([px[x, y] for x in range(x0, x1 + 1)])


def long_runs_row(im, y, x0, x1, bg, tol, minrun):
    px = g_px(im)
    segs = []
    run = None
    for x in range(x0, x1 + 1):
        if abs(px[x, y] - bg) > tol:
            if run is None:
                run = [x, x]
            else:
                run[1] = x
        else:
            if run is not None and run[1] - run[0] + 1 >= minrun:
                segs.append(tuple(run))
            run = None
    if run is not None and run[1] - run[0] + 1 >= minrun:
        segs.append(tuple(run))
    return segs


def text_bands(im, x0, x1, y0, y1, thresh=170, minpix=2):
    px = g_px(im)
    counts = []
    for y in range(y0, y1 + 1):
        counts.append(sum(1 for x in range(x0, x1 + 1) if px[x, y] < thresh))
    res = []
    y = y0
    while y <= y1:
        if counts[y - y0] >= minpix:
            s = y
            while y <= y1 and counts[y - y0] >= minpix:
                y += 1
            res.append((s, y - 1))
        else:
            y += 1
    return res


def glyph_runs(im, y0, y1, x0, x1, thresh=170):
    px = g_px(im)
    runs = []
    x = x0
    while x <= x1:
        if any(px[x, y] < thresh for y in range(y0, y1 + 1)):
            xa = x
            tops, bots = [], []
            while x <= x1:
                d = [y for y in range(y0, y1 + 1) if px[x, y] < thresh]
                if d:
                    tops.append(min(d)); bots.append(max(d)); x += 1
                else:
                    break
            runs.append((xa, x - 1, min(tops), max(bots)))
        else:
            x += 1
    return runs


def merge_runs(runs, gap=3):
    if not runs:
        return []
    out = [[runs[0][0], runs[0][1]]]
    for r in runs[1:]:
        if r[0] - out[-1][1] <= gap + 1:
            out[-1][1] = r[1]
        else:
            out.append([r[0], r[1]])
    return [tuple(o) for o in out]


def find_red(im, x0, x1, y0, y1):
    best = None
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = im.getpixel((x, y))
            if c[0] > 130 and c[0] - c[1] > 50 and c[0] - c[2] > 50:
                if best is None:
                    best = [x, y, x, y]
                else:
                    best[0] = min(best[0], x); best[1] = min(best[1], y)
                    best[2] = max(best[2], x); best[3] = max(best[3], y)
    return best


def white_bbox(im, x0, x1, y0, y1, thr=190):
    px = g_px(im)
    bx0 = by0 = bx1 = by1 = None
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c = im.getpixel((x, y))
            if c[0] > thr and c[1] > thr and c[2] > thr:
                if bx0 is None:
                    bx0, by0, bx1, by1 = x, y, x, y
                else:
                    bx0 = min(bx0, x); by0 = min(by0, y)
                    bx1 = max(bx1, x); by1 = max(by1, y)
    return (bx0, by0, bx1, by1)


def buttons_from_bands(im, x0, x1, y0, y1, min_h=20):
    """按钮在文字带里表现为高度 >= min_h 的连续带；返回 [(x0,x1,y0,y1)]"""
    out = []
    for (b0, b1) in text_bands(im, x0, x1, y0, y1):
        if b1 - b0 + 1 < min_h:
            continue
        runs = glyph_runs(im, b0, b1, x0, x1)
        if not runs:
            continue
        # 按钮边框是闭合矩形，整行都有暗像素 => 单个很长的 run
        merged = merge_runs(runs, gap=3)
        for (a, b) in merged:
            if b - a >= 40:
                out.append((a, b, b0, b1))
    return out


def grid_png(name, scale=3, step=10, out=None):
    """生成带坐标网格的放大图，方便人工核对。"""
    im = Image.open(os.path.join(REF, name)).convert("RGB")
    w, h = im.size
    g = im.resize((w * scale, h * scale), Image.NEAREST)
    d = ImageDraw.Draw(g)
    for x in range(0, w, step):
        d.line([(x * scale, 0), (x * scale, h * scale)], fill=(255, 0, 0), width=1)
        d.text((x * scale + 2, 2), str(x), fill=(255, 0, 0))
    for y in range(0, h, step):
        d.line([(0, y * scale), (w * scale, y * scale)], fill=(0, 160, 255), width=1)
        d.text((2, y * scale + 2), str(y), fill=(0, 100, 220))
    path = out or os.path.join(OUTDIR, "dialog_grid_%s.png" % name.replace(".jpg", ""))
    g.save(path)
    return path


# ==========================================================================
def analyze_glass(name, cx0, cx1, cy0, cy1, sep_y):
    im = Image.open(os.path.join(REF, name)).convert("RGB")
    w, h = im.size
    p("#" * 74)
    p("# %s  (%dx%d)   客户区 x=%d..%d  y=%d..%d" % (name, w, h, cx0, cx1, cy0, cy1))
    p("#" * 74)

    p("## 外框（左右列中位亮度 / 代表色）")
    for x in list(range(0, 10)) + list(range(w - 10, w)):
        p("   x=%3d med=%3d rgb=%s" % (x, col_median(im, x, cy0, cy1),
                                       hexs(med_rgb(im, x, cy0 + 20, x, cy0 + 24))))
    p("   客户区底色 = %s" % hexs(med_rgb(im, cx0 + 100, cy0 + 2, cx0 + 200, cy0 + 6)))

    p("## 标题栏渐变（每行在无文字处的 RGB 中位）")
    tx0, tx1 = cx0 + 20, cx1 - 130
    for y in range(1, sep_y):
        p("   y=%3d rgb=%s med=%3d" % (y, hexs(med_rgb(im, tx0, y, tx1, y)), row_median(im, y, tx0, tx1)))
    p("   分隔线 y=%d rgb=%s" % (sep_y, hexs(med_rgb(im, cx0 + 5, sep_y, cx1 - 5, sep_y))))

    p("## 标题文字（仅搜标题栏左侧 80px 内，近黑阈值 120）")
    for (b0, b1) in text_bands(im, cx0 + 1, cx0 + 80, 1, sep_y - 1, thresh=120):
        runs = glyph_runs(im, b0, b1, cx0 + 1, cx0 + 80, thresh=120)
        if runs:
            p("   标题文字带 y=%d..%d (字高 %d) x=%d..%d" % (b0, b1, b1 - b0 + 1, runs[0][0], runs[-1][1]))
            p("      字符块 %s" % (runs,))

    p("## 关闭按钮（红）")
    # 逐列统计「足够红」的像素，取连续列段；比包围盒更抗 JPEG 噪点
    def red_px(x, y):
        c = im.getpixel((x, y))
        return c[0] > 140 and c[0] - c[1] > 55 and c[0] - c[2] > 45
    colhits = []
    for x in range(cx1 - 90, cx1):
        colhits.append((x, sum(1 for y in range(1, sep_y) if red_px(x, y))))
    seg = []
    cur = None
    for (x, n) in colhits:
        if n >= 6:
            if cur is None:
                cur = [x, x]
            else:
                cur[1] = x
        else:
            if cur is not None:
                seg.append(tuple(cur)); cur = None
    if cur is not None:
        seg.append(tuple(cur))
    p("   红色列段: %s" % seg)
    if seg:
        rx0, rx1 = seg[-1]
        rows = [y for y in range(1, sep_y) if red_px(rx0 + 1, y) or red_px(rx1 - 1, y)]
        ry0, ry1 = min(rows), max(rows)
        p("   按钮矩形 x=%d..%d (w=%d) y=%d..%d (h=%d)" % (rx0, rx1, rx1 - rx0 + 1, ry0, ry1, ry1 - ry0 + 1))
        p("   红色 = %s" % hexs(med_rgb(im, rx0 + 2, ry0 + 2, rx1 - 2, ry1 - 2)))
        wb = white_bbox(im, rx0 + 3, rx1 - 3, ry0 + 2, ry1 - 2, thr=205)
        p("   白色叉号 x=%d..%d y=%d..%d" % wb)

    p("## 客户区文字带")
    for (b0, b1) in text_bands(im, cx0 + 1, cx1 - 1, cy0, cy1):
        runs = glyph_runs(im, b0, b1, cx0 + 1, cx1 - 1)
        if not runs:
            continue
        p("   行 y=%d..%d (字高 %d) 段: %s" % (b0, b1, b1 - b0 + 1, merge_runs(runs, 3)))

    p("## 按钮")
    for (a, b, y0, y1) in buttons_from_bands(im, cx0 + 1, cx1 - 1, cy0, cy1):
        p("   按钮 x=%d..%d (w=%d)  y=%d..%d (h=%d)" % (a, b, b - a + 1, y0, y1, y1 - y0 + 1))
        p("      顶边 rgb=%s  底边 rgb=%s  左边 rgb=%s  右边 rgb=%s" % (
            hexs(med_rgb(im, a + 4, y0, b - 4, y0)),
            hexs(med_rgb(im, a + 4, y1, b - 4, y1)),
            hexs(med_rgb(im, a, y0 + 3, a, y1 - 3)),
            hexs(med_rgb(im, b, y0 + 3, b, y1 - 3))))
        p("      填充上 rgb=%s  填充下 rgb=%s" % (
            hexs(med_rgb(im, a + 6, y0 + 2, b - 6, y0 + 3)),
            hexs(med_rgb(im, a + 6, y1 - 3, b - 6, y1 - 2))))
        for (t0, t1) in text_bands(im, a + 3, b - 3, y0 + 2, y1 - 2, thresh=140):
            rr = glyph_runs(im, t0, t1, a + 3, b - 3, thresh=140)
            if rr:
                p("      按钮文字 y=%d..%d (字高 %d) x=%d..%d 文字中心=%d 按钮中心=%d" %
                  (t0, t1, t1 - t0 + 1, rr[0][0], rr[-1][1],
                   (rr[0][0] + rr[-1][1]) // 2, (a + b) // 2))
    return im


def analyze_about():
    im = Image.open(os.path.join(REF, "about.jpg")).convert("RGB")
    w, h = im.size
    p("#" * 74)
    p("# about.jpg (%dx%d) —— 整窗截图，「关于扫雷」对话框只是其中一块" % (w, h))
    p("#" * 74)

    # 对话框客户区：接近无彩且很亮的像素
    def light(c):
        return min(c) > 195 and (max(c) - min(c)) < 14

    rows = []
    for y in range(80, 320):
        n = sum(1 for x in range(140, 500) if light(im.getpixel((x, y))))
        rows.append((y, n))
    p("## 客户区行剖面（亮且无彩的像素数；>=250 视为客户区）")
    for (y, n) in rows:
        if n > 0:
            p("   y=%3d n=%3d" % (y, n))

    cols = []
    for x in range(140, 500):
        n = sum(1 for y in range(120, 300) if light(im.getpixel((x, y))))
        cols.append((x, n))
    p("## 客户区列剖面")
    for (x, n) in cols:
        if n > 0:
            p("   x=%3d n=%3d" % (x, n))

    # ---- 对话框内部（局部坐标）----
    DX0, DY0, DX1, DY1 = 156, 96, 464, 292      # 对话框外框范围（整窗坐标）
    p("## 对话框内部（整窗坐标 x=%d..%d y=%d..%d）" % (DX0, DX1, DY0, DY1))

    p("### 顶部：逐行 RGB（x=200..400）")
    for y in range(DY0 - 4, DY0 + 36):
        p("   y=%3d rgb=%s" % (y, hexs(med_rgb(im, 200, y, 400, y))))

    p("### 左侧：逐列 RGB（y=140..280）")
    for x in range(DX0 - 6, DX0 + 12):
        p("   x=%3d rgb=%s" % (x, hexs(med_rgb(im, x, 140, x, 280))))

    p("### 标题文字")
    for (b0, b1) in text_bands(im, DX0, DX0 + 130, DY0, DY0 + 34, thresh=120):
        runs = glyph_runs(im, b0, b1, DX0, DX0 + 130, thresh=120)
        if runs:
            p("   标题 y=%d..%d (字高 %d) x=%d..%d  字符块=%s" %
              (b0, b1, b1 - b0 + 1, runs[0][0], runs[-1][1], runs))

    p("### 红色关闭按钮")
    red = find_red(im, DX0 + 200, DX1, DY0, DY0 + 34)
    p("   红像素包围盒 x=%d..%d y=%d..%d (w=%d h=%d)" %
      (red[0], red[2], red[1], red[3], red[2] - red[0] + 1, red[3] - red[1] + 1))
    p("   红色 = %s" % hexs(med_rgb(im, red[0] + 2, red[1] + 2, red[2] - 2, red[3] - 2)))
    wb = white_bbox(im, red[0] + 2, red[2] - 2, red[1] + 2, red[3] - 2, thr=210)
    p("   白色叉号 x=%d..%d y=%d..%d" % wb)

    p("### 客户区文字带（x %d..%d, y %d..%d）" % (DX0 + 4, DX1 - 4, DY0 + 36, DY1 - 4))
    for (b0, b1) in text_bands(im, DX0 + 4, DX1 - 4, DY0 + 36, DY1 - 4):
        runs = glyph_runs(im, b0, b1, DX0 + 4, DX1 - 4)
        if not runs:
            continue
        p("   行 y=%d..%d (字高 %d) 段: %s" % (b0, b1, b1 - b0 + 1, merge_runs(runs, 4)))

    p("### 客户区里非灰色的像素（雷图标 / 彩色边框）")
    for y in range(DY0 + 36, DY1 - 4):
        xs = []
        for x in range(DX0 + 4, DX1 - 4):
            c = im.getpixel((x, y))
            if max(c) - min(c) > 25 or min(c) < 170:
                xs.append(x)
        if xs:
            p("   y=%3d 彩色/暗像素 x=%d..%d (n=%d)" % (y, xs[0], xs[-1], len(xs)))

    p("### 「确定」按钮")
    for (a, b, y0, y1) in buttons_from_bands(im, DX0 + 4, DX1 - 4, DY0 + 36, DY1 - 4, min_h=18):
        p("   按钮 x=%d..%d (w=%d) y=%d..%d (h=%d)" % (a, b, b - a + 1, y0, y1, y1 - y0 + 1))
        p("      顶边 rgb=%s 底边 rgb=%s 左边 rgb=%s 右边 rgb=%s" % (
            hexs(med_rgb(im, a + 4, y0, b - 4, y0)),
            hexs(med_rgb(im, a + 4, y1, b - 4, y1)),
            hexs(med_rgb(im, a, y0 + 3, a, y1 - 3)),
            hexs(med_rgb(im, b, y0 + 3, b, y1 - 3))))
        for (t0, t1) in text_bands(im, a + 3, b - 3, y0 + 2, y1 - 2, thresh=140):
            rr = glyph_runs(im, t0, t1, a + 3, b - 3, thresh=140)
            if rr:
                p("      按钮文字 y=%d..%d (字高 %d) x=%d..%d 中心=%d 按钮中心=%d" %
                  (t0, t1, t1 - t0 + 1, rr[0][0], rr[-1][1],
                   (rr[0][0] + rr[-1][1]) // 2, (a + b) // 2))
    return im


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    p("版式实测 —— 参考图目录 %s" % REF)
    p("")
    if only in (None, "loss.jpg"):
        analyze_glass("loss.jpg", 8, 474, 30, 279, 29)
        p("")
    if only in (None, "win.jpg"):
        analyze_glass("win.jpg", 8, 387, 30, 331, 29)
        p("")
    if only in (None, "about.jpg"):
        analyze_about()
        p("")
    for nm in ("loss.jpg", "win.jpg", "about.jpg"):
        try:
            p("grid png: " + grid_png(nm))
        except Exception as e:
            p("grid fail %s: %s" % (nm, e))
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(_REPORT))
    print("\nwrote " + OUT_MD)


if __name__ == "__main__":
    main()
