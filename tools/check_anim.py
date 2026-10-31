"""
check_anim.py —— 离线校验三段动画的帧矩形与绘制偏移

为什么需要它：动画的帧矩形是「公式 + 偏移」写死在 Anim.ets 里的，
装到真机才知道对不对太慢；而**切错一帧在缩略图上几乎看不出来**。
这个脚本用与 Anim.ets **完全相同**的公式，从原版 otherSheet.png 里把帧切出来，
按真实的绘制偏移合成到一张棋盘上，输出一段胶片图，肉眼一看就知道有没有：
  - 帧切偏（画面里出现相邻帧的边缘、或整块错位）
  - 偏移错（爆炸不居中 / 光束没对准雷）
  - 帧数错（序列断掉或重复）

用法：
  python tools\\check_anim.py             # 输出到 docs\\analysis\\
  python tools\\check_anim.py <输出目录>

公式与 Anim.ets 的对应关系：
  EXPLODE: rect = (728 + 59*(f%3), 59*(f/3), 57, 57)，偏移 (-18,-18)，23 帧 / 1 秒
  DISARM : rect = (0 + 52*(f%7), 152*(f/7), 50, 150)，偏移 (-18,-69)，38 帧 / 2 秒
  SCANBAR: rect = (0, 912, 275, 62)，横向拉伸到棋盘宽
所有矩形都是**逻辑坐标**，取像素时要乘 SPRITE_SCALE = 2。
"""

import os
import sys
from PIL import Image, ImageDraw

BASE = r"C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images"
OUT = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\software\harmony\projects\minesweeper\docs\analysis"

SPRITE_SCALE = 2
TILE = 18

# ---- 与 Anim.ets 完全一致的常量 ----
EXPLODE_FRAMES = 23
EXPLODE_X0 = 728
EXPLODE_PITCH = 59
EXPLODE_SIZE = 57
EXPLODE_OFFSET = (-18, -18)

DISARM_FRAMES = 38
DISARM_W, DISARM_H = 50, 150
DISARM_GUTTER = 2
DISARM_OFFSET = (-18, -69)

SCAN_BAR = (0, 912, 275, 62)


def load_sheet(name):
    return Image.open(os.path.join(BASE, name)).convert("RGBA")


def crop_logical(sheet, rect):
    """逻辑坐标矩形 → 裁出来（乘 SPRITE_SCALE）"""
    x, y, w, h = rect
    s = SPRITE_SCALE
    return sheet.crop((x * s, y * s, (x + w) * s, (y + h) * s))


def explode_rect(f):
    return (EXPLODE_X0 + EXPLODE_PITCH * (f % 3),
            EXPLODE_PITCH * (f // 3),
            EXPLODE_SIZE, EXPLODE_SIZE)


def disarm_rect(f):
    return (52 * (f % 7), 152 * (f // 7), DISARM_W, DISARM_H)


def make_explode_strip(sheet, unit=4):
    """
    把 23 帧按原版偏移合成到「一格」上，排成胶片。
    一格 = TILE * unit 像素；帧 = 57 * unit；偏移 = (-18,-18)*unit
    """
    tile_px = TILE * unit
    frame_px = EXPLODE_SIZE * unit
    ox, oy = EXPLODE_OFFSET[0] * unit, EXPLODE_OFFSET[1] * unit
    cols = 6
    rows = (EXPLODE_FRAMES + cols - 1) // cols
    pad = 12
    cw = frame_px + pad
    ch = frame_px + pad
    out = Image.new("RGBA", (cols * cw, rows * ch), (240, 240, 240, 255))
    d = ImageDraw.Draw(out)
    for f in range(EXPLODE_FRAMES):
        cx = (f % cols) * cw
        cy = (f // cols) * ch
        # 先画一格的底色（模拟棋盘上的这颗雷）
        d.rectangle((cx + pad // 2, cy + pad // 2,
                     cx + pad // 2 + tile_px, cy + pad // 2 + tile_px),
                    fill=(160, 168, 180, 255))
        frame = crop_logical(sheet, explode_rect(f)).resize(
            (frame_px, frame_px), Image.NEAREST)
        # 绘制位置 = 格子左上 + 偏移；这里格子左上记在 (cx+pad/2, cy+pad/2)
        out.alpha_composite(frame, (int(cx + pad // 2 + ox), int(cy + pad // 2 + oy)))
        d.text((cx + 2, cy + 1), str(f), fill=(0, 0, 0, 255))
    return out


def make_disarm_strip(sheet, unit=2):
    """38 帧拆雷光束（每帧 50x150，绘制偏移 (-18,-69)）"""
    tile_px = TILE * unit
    fw, fh = DISARM_W * unit, DISARM_H * unit
    ox, oy = DISARM_OFFSET[0] * unit, DISARM_OFFSET[1] * unit
    cols = 8
    rows = (DISARM_FRAMES + cols - 1) // cols
    pad = 8
    cw, chh = fw + pad, fh + pad
    out = Image.new("RGBA", (cols * cw, rows * chh), (240, 240, 240, 255))
    d = ImageDraw.Draw(out)
    for f in range(DISARM_FRAMES):
        cx = (f % cols) * cw
        cy = (f // cols) * chh
        # 一块棋盘（3 格宽，让上下溢出看得见）
        d.rectangle((cx + pad // 2, cy + pad // 2,
                     cx + pad // 2 + tile_px * 3, cy + pad // 2 + tile_px * 3),
                    fill=(120, 140, 200, 255))
        # 中间那格画雷
        mx = cx + pad // 2 + tile_px
        my = cy + pad // 2 + tile_px
        d.rectangle((mx, my, mx + tile_px, my + tile_px), fill=(90, 110, 170, 255))
        frame = crop_logical(sheet, disarm_rect(f)).resize((fw, fh), Image.NEAREST)
        out.alpha_composite(frame, (int(mx + ox), int(my + oy)))
        d.text((cx + 2, cy + 1), str(f), fill=(0, 0, 0, 255))
    return out


def make_scanbar_check(sheet, board_w=9, unit=2):
    """扫描条：横向拉伸到棋盘宽，看它是不是一条完整、无缝、可拉伸的横条"""
    bar = crop_logical(sheet, SCAN_BAR)
    w = TILE * board_w * unit
    h = int(SCAN_BAR[3] * unit)
    stretched = bar.resize((w, h), Image.BILINEAR)
    out = Image.new("RGBA", (w + 20, h + 40), (240, 240, 240, 255))
    d = ImageDraw.Draw(out)
    # 上面放原始比例，下面放拉伸后的
    out.alpha_composite(bar, (10, 10))
    out.alpha_composite(stretched, (10, h + 25))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    other = load_sheet("otherSheet.png")

    p1 = os.path.join(OUT, "check_explode_23f.png")
    make_explode_strip(other).save(p1)
    print("爆炸 23 帧:", p1)

    p2 = os.path.join(OUT, "check_disarm_38f.png")
    make_disarm_strip(other).save(p2)
    print("拆雷 38 帧:", p2)

    p3 = os.path.join(OUT, "check_scanbar.png")
    make_scanbar_check(other).save(p3)
    print("扫描条:", p3)

    # 顺便报一下每帧的不透明包围盒，便于确认没有切到相邻帧
    print("\n爆炸帧不透明包围盒（应逐帧变化、且都不贴到 57 的边框上）:")
    for f in (0, 5, 11, 17, 22):
        fr = crop_logical(other, explode_rect(f))
        print("  帧%2d  bbox=%s" % (f, fr.split()[3].getbbox()))

    print("\n拆雷帧不透明包围盒（第 0 帧应包含一份方砖副本）:")
    for f in (0, 10, 20, 37):
        fr = crop_logical(other, disarm_rect(f))
        print("  帧%2d  bbox=%s" % (f, fr.split()[3].getbbox()))


if __name__ == "__main__":
    main()
