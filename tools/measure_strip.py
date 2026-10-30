"""
measure_strip.py —— 从 Win7 复刻截图里量出状态条各元素的真实位置。

Lmy0217 的 gaming.jpg 是 1:1 渲染的 Win7 界面（30×16 盘，18px 格子），
用它反推原版状态条相对棋盘的位置。

先做诊断采样，再按颜色聚类定位：
  - 计数器凹槽面板：蓝色
  - 圆形按钮（时钟 / 雷）：灰色圆环
"""

import sys
from PIL import Image

SRC = r"C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg\gaming.jpg"


def main():
    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    px = img.load()
    print(f"截图 {w} x {h}")

    # 采样几个点，看画面结构
    print("--- 采样 ---")
    for (x, y) in [(2, 2), (5, 20), (300, 15), (300, 40), (300, 100), (300, 200),
                   (300, 330), (300, 350), (300, 370), (300, 390), (300, 405),
                   (100, 380), (400, 380), (20, 380), (610, 380)]:
        print(f"  ({x},{y}) = {px[x, y]}")

    def is_panel(p):
        r, g, b = p
        return 25 <= r <= 80 and 60 <= g <= 120 and 120 <= b <= 200 and b - r > 70

    def is_gray(p):
        r, g, b = p
        return abs(r - g) < 18 and abs(g - b) < 22 and 110 <= r <= 215

    # 蓝色面板聚类（按列分组）
    cols = {}
    for y in range(h):
        for x in range(w):
            if is_panel(px[x, y]):
                cols.setdefault(x, []).append(y)
    xs = sorted(cols)
    groups = []
    cur = []
    for x in xs:
        if cur and x - cur[-1] > 3:
            groups.append(cur); cur = []
        cur.append(x)
    if cur:
        groups.append(cur)
    print("--- 蓝色面板分组 ---")
    for g in groups:
        ys = [y for x in g for y in cols[x]]
        print(f"  x={g[0]}..{g[-1]} (宽 {g[-1]-g[0]+1})  y={min(ys)}..{max(ys)} (高 {max(ys)-min(ys)+1})")

    # 灰色圆环（图标）：限制在面板所在的垂直带内
    if groups:
        band_top = min(min(y for x in g for y in cols[x]) for g in groups) - 30
        band_bot = max(max(y for x in g for y in cols[x]) for g in groups) + 8
        print(f"--- 灰色图标扫描带 y={band_top}..{band_bot} ---")
        gray_cols = {}
        for y in range(max(0, band_top), min(h, band_bot)):
            for x in range(w):
                if is_gray(px[x, y]):
                    gray_cols.setdefault(x, []).append(y)
        gxs = sorted(gray_cols)
        ggroups = []
        cur = []
        for x in gxs:
            if cur and x - cur[-1] > 4:
                ggroups.append(cur); cur = []
            cur.append(x)
        if cur:
            ggroups.append(cur)
        for g in ggroups:
            if len(g) < 8:
                continue
            ys = [y for x in g for y in gray_cols[x]]
            print(f"  x={g[0]}..{g[-1]} (宽 {g[-1]-g[0]+1})  y={min(ys)}..{max(ys)} (高 {max(ys)-min(ys)+1})")


if __name__ == "__main__":
    main()
