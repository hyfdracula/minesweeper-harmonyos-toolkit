# -*- coding: utf-8 -*-
"""dlg_measure3.py —— 只量标题栏右上角红按钮：逐行红色连续段 + 白叉包围盒。"""
import os
from PIL import Image

REF = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg"
OUT = os.path.dirname(os.path.abspath(__file__))
L = []


def p(s=""):
    print(s)
    L.append(s)


def runs_of(pred, x0, x1, y):
    im = cur
    out = []
    cur_run = None
    for x in range(x0, x1 + 1):
        if pred(im.getpixel((x, y))):
            if cur_run is None:
                cur_run = [x, x]
            else:
                cur_run[1] = x
        else:
            if cur_run is not None:
                out.append(tuple(cur_run)); cur_run = None
    if cur_run is not None:
        out.append(tuple(cur_run))
    return out


for nm, xr in (("loss.jpg", (400, 483)), ("win.jpg", (320, 396)),
               ("about.jpg", (380, 466))):
    cur = Image.open(os.path.join(REF, nm)).convert("RGB")
    p("=== %s 红按钮（x %d..%d）===" % (nm, xr[0], xr[1] - 1))
    allx = []
    ally = []
    for y in range(0, 24):
        rr = [r for r in runs_of(lambda c: c[0] > 120 and c[0] - c[1] > 45 and c[0] - c[2] > 35,
                                 xr[0], xr[1] - 1, y) if r[1] - r[0] >= 4]
        p("   y=%3d 红段 %s" % (y, rr))
        for (a, b) in rr:
            allx += [a, b]
            ally.append(y)
    if allx:
        p("   -> 红按钮 x=%d..%d (w=%d)  y=%d..%d (h=%d)" %
          (min(allx), max(allx), max(allx) - min(allx) + 1,
           min(ally), max(ally), max(ally) - min(ally) + 1))
        bx0 = by0 = bx1 = by1 = None
        for y in range(min(ally), max(ally) + 1):
            for x in range(min(allx), max(allx) + 1):
                c = cur.getpixel((x, y))
                if c[0] > 195 and c[1] > 195 and c[2] > 195:
                    if bx0 is None:
                        bx0, by0, bx1, by1 = x, y, x, y
                    else:
                        bx0 = min(bx0, x); by0 = min(by0, y)
                        bx1 = max(bx1, x); by1 = max(by1, y)
        p("   -> 白叉 x=%d..%d y=%d..%d" % (bx0, bx1, by0, by1))
    p("")

with open(os.path.join(OUT, "dialog_layout_close.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("wrote dialog_layout_close.md")
