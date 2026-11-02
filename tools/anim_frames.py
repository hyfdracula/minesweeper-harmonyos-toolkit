# -*- coding: utf-8 -*-
"""
anim_frames.py —— 慢放包下的踩雷动画**逐帧取证**工具。

背景：设备端一次截图要 497ms、一次点击要 485ms，而原版爆炸只有 1 秒（23 帧）。
快门比动画窗口还慢，普通包里一次连拍最多压住 1 帧，23 帧根本抓不齐。
所以取证时临时把爆炸**慢放 8 倍**（Anim.EXPLODE_SLOWMO = 8，8 秒），
快门就能连着抓好几帧。本脚本负责：

  1) 在真机上故意踩雷，连拍 N 帧；
  2) 对每一帧做**帧号标注**（模板匹配 otherSheet 里的 23 张动画帧）；
  3) 汇总成一张「帧号 -> 证据文件」的表。

「慢放只是取证手段，发布包仍然是原版的 1 秒 / 23 帧」——
慢放倍率在提交前必须改回 1。

用法：
  python tools\\anim_frames.py --device 127.0.0.1:5555 --kind explode \
      --tag ANIMF_exp --burst 14 --burst-gap 0.05 --first-delay 0.0
  python tools\\anim_frames.py --device 127.0.0.1:5555 --kind flower \
      --tag ANIMF_flo --burst 14 --burst-gap 0.05 --first-delay 0.0
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_probe as wp
from PIL import Image
import numpy as np

SPRITE_SCALE = wp.SPRITE_SCALE

# otherSheet 里的两组踩雷动画帧（逻辑坐标，见 Theme.ets）
# 扫雷：x = 728 + 59*(f%3), y = 59*(f/3), 57x57，绘制偏移 (-18,-18)
# 花园：x = 905 + 38*(f%3), y = 38*(f/3), 36x36，绘制偏移 (-9,-9)
KIND = {
    'explode': {
        'x0': 728, 'pitch': 59, 'w': 57, 'h': 57, 'off': (-18, -18), 'frames': 23,
    },
    'flower': {
        'x0': 905, 'pitch': 38, 'w': 36, 'h': 36, 'off': (-9, -9), 'frames': 23,
    },
}


def trip_templates(kind):
    """取 otherSheet 里该组踩雷帧的源矩形（源像素）。"""
    k = KIND[kind]
    other = Image.open(wp.OTHER).convert('RGBA')
    out = []
    for f in range(k['frames']):
        sx = (k['x0'] + k['pitch'] * (f % 3)) * SPRITE_SCALE
        sy = (k['pitch'] * (f // 3)) * SPRITE_SCALE
        sw = k['w'] * SPRITE_SCALE
        sh = k['h'] * SPRITE_SCALE
        out.append(np.asarray(other.crop((sx, sy, sx + sw, sy + sh)), dtype=np.float32))
    return out


def match_trip_frame(patch, tpls, size, alpha_min=110):
    """
    在 23 张帧里找最像 patch 的那一帧。
    只比精灵里**不透明**的像素（alpha >= alpha_min）——
    爆炸/开花的精灵四周是透明的，比全块会把相似度压垮。
    """
    best = None
    for f, tpl in enumerate(tpls):
        ta = np.asarray(Image.fromarray(tpl.astype(np.uint8)).resize(size, Image.BOX),
                        dtype=np.float32)
        solid = ta[:, :, 3] >= alpha_min
        if int(solid.sum()) < 50:
            continue
        diff = np.abs(ta[:, :, :3][solid] - patch[:, :, :3][solid]).mean(axis=1)
        score = 1.0 - float(diff.mean()) / 255.0
        if best is None or score > best[1]:
            best = (f, score)
    return best


def cell_has_yellow_center(patch):
    """花园格：雏菊中间那团黄。用来认出「已揭开的花雷」。"""
    r = patch[:, :, 0]
    g = patch[:, :, 1]
    b = patch[:, :, 2]
    m = (r > 170) & (g > 120) & (b < 150) & ((r - b) > 55) & ((g - b) > 30)
    return int(m.sum())


def read_board_flower(img, gx, gy, pitch, unit, templates, rows, cols):
    """
    花园主题的读盘：
      未揭开的方砖   -> 'X'
      已揭开的花雷   -> 'M'（雏菊的黄心）
      其它已揭开的格 -> 数字（读不出来是 None）
    """
    board = []
    for r in range(rows):
        row = []
        for c in range(cols):
            cx = gx + c * pitch
            cy = gy + r * pitch
            x = int(round(cx))
            y = int(round(cy))
            patch = np.asarray(img.crop((x, y, x + int(pitch), y + int(pitch))).convert('RGB'),
                               dtype=np.float32)
            sat = patch.max(axis=2) - patch.min(axis=2)
            mx = patch.max(axis=2)
            pale = ((sat < 60) & (mx > 150))
            pale_frac = float(pale.sum()) / (pitch * pitch)
            if pale_frac < 0.25:
                row.append('X')
                continue
            if cell_has_yellow_center(patch) > 20:
                row.append('M')
                continue
            row.append(wp.cell_digit(img, cx, cy, pitch, unit, templates))
        board.append(row)
    return board


def parse_pxscale(layout):
    """从 hilog 的布局行里取「密度换算」（= pxScale）。"""
    import re
    m = re.search(r'密度换算=([0-9.]+)', layout.get('raw', ''))
    return float(m.group(1)) if m else 0.32


def switch_style(device, layout, gx, gy, to_flower):
    """
    切游戏样式（扫雷 <-> 花园）：菜单 -> 游戏(G) -> 颜色(C) -> 缩略图 -> 确定(O)。

    对话框的几何全部由代码算出来（见 Appearance.ets）：
      DLG_W = 420, DLG_H = 340
      s = max(0.5, min(2, 1/pxScale, (canvasW-32)/420, (canvasH-32)/340))   （GameController.computeDialogScale）
      dialogOx = round((canvasW - 420*s)/2),  dialogOy = round((canvasH - 340*s)/2)
    缩略图（参考像素）：扫雷 (40,52,64,64)、花园 (226,52,64,64)；确定按钮 (210,302,90,26)。
    菜单栏两项的位置是实测值（本机 2210x2416、pxScale=0.32）。
    """
    import time
    cdx = gx - layout['board_x']
    cdy = gy - layout['board_y']
    wp.click(device, cdx + 94, cdy + 28)        # 游戏(G)
    time.sleep(0.7)
    wp.click(device, cdx + 139, cdy + 773)      # 颜色(C)
    time.sleep(1.2)
    cw = layout['canvas_w']
    ch = layout['canvas_h']
    px = parse_pxscale(layout)
    s = max(0.5, min(2.0, 1.0 / px, (cw - 32) / 420.0, (ch - 32) / 340.0))
    ox = round((cw - 420 * s) / 2.0)
    oy = round((ch - 340 * s) / 2.0)
    ref = (258, 84) if to_flower else (72, 84)
    wp.click(device, cdx + ox + ref[0] * s, cdy + oy + ref[1] * s)
    time.sleep(0.7)
    wp.click(device, cdx + ox + 255 * s, cdy + oy + 315 * s)   # 确定(O)
    time.sleep(1.5)
    return s


def burst_on_device(device, outdir, tag, count, ci, on_frame):
    """
    **设备端连拍**：一条 shell 命令在设备上连着跑 count 次 snapshot_display，
    文件先落在设备上；本机这边一边等一边把已经拍好的文件取回来。

    为什么这么做：一次 `hdc shell snapshot_display` 要 497ms，
    加上 `file recv` 的 226ms，一帧一轮就是 ~1.5 秒 ——
    慢放 8 倍（每帧 348ms）也只能跨 4.3 帧，23 帧怎么扫都扫不齐。
    把截图留在设备上、取回并行做之后，节奏由设备自己的截图速度决定（~0.5s/帧），
    一轮 16 帧就能覆盖 23 帧。

    on_frame(本地路径, 序号) 每取回一帧就调一次（用来当场做帧号标注）。
    返回本地文件列表。
    """
    import threading
    import time
    remote = '/data/local/tmp'
    local_paths = []

    def runner():
        cmd = ('i=0; while [ $i -lt %d ]; do snapshot_display -f %s/%s_$i.jpeg; '
               'i=$((i+1)); done' % (count, remote, tag))
        try:
            wp.hdc(device, 'shell', cmd)
        except Exception:
            pass

    th = threading.Thread(target=runner)
    th.daemon = True
    th.start()

    for i in range(count):
        rname = '%s_%d.jpeg' % (tag, i)
        rpath = '%s/%s' % (remote, rname)
        lpath = os.path.join(outdir, '%s_c%d_%02d.jpeg' % (tag, ci, i))
        got = False
        for _ in range(120):
            out = wp.hdc(device, 'shell', 'ls -la %s 2>/dev/null' % rpath)
            if rname in out:
                got = True
                break
            time.sleep(0.15)
        if not got:
            break
        wp.hdc(device, 'file', 'recv', rpath, lpath)
        if os.path.exists(lpath):
            local_paths.append(lpath)
            if on_frame:
                on_frame(lpath, i)
    return local_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', default='127.0.0.1:5555')
    ap.add_argument('--kind', default='explode', choices=['explode', 'flower'],
                    help='要取的动画：explode=扫雷爆炸，flower=花园开花。'
                         '**它同时决定应用当前该是哪种游戏样式**')
    ap.add_argument('--out', default=r'D:\software\harmony\projects\minesweeper\docs\verify')
    ap.add_argument('--rows', type=int, default=9)
    ap.add_argument('--cols', type=int, default=9)
    ap.add_argument('--mines', type=int, default=10)
    ap.add_argument('--burst', type=int, default=14)
    ap.add_argument('--burst-gap', type=float, default=0.05)
    ap.add_argument('--first-delay', type=float, default=0.0,
                    help='点击之后到第一张截图之间等多久（慢放下用来微调落点）')
    ap.add_argument('--style', default=None, choices=['mines', 'flower'],
                    help='目标游戏样式。**默认由 --kind 决定**（explode->mines, '
                         'flower->flower）；显式给成与 --kind 矛盾的值会直接报错退出，'
                         '因为那样会拿矿雷画面去匹配花朵帧、帧号全是错的')
    ap.add_argument('--switch', action='store_true',
                    help='跑之前先切一次游戏样式（目标 = --kind 决定的那个）')
    ap.add_argument('--parallel', action='store_true',
                    help='点击丢后台线程、立刻连拍（为了抓第 0 帧）')
    ap.add_argument('--device-burst', action='store_true',
                    help='设备端连拍（截图留在设备上，取回并行做，节奏快一倍多）')
    ap.add_argument('--tag', default=None,
                    help='输出文件名前缀。默认按 --kind 自动取（ANIMF_exp / ANIMF_flo）')
    args = ap.parse_args()

    # --kind 决定样式。显式 --style 与 --kind 矛盾 -> 直接报错，
    # 免得拿矿雷画面去匹配花朵帧、帧号全是错的。
    kind_style = 'flower' if args.kind == 'flower' else 'mines'
    if args.style is not None and args.style != kind_style:
        sys.stderr.write('[anim_frames] --kind %s 对应的游戏样式是 %s，'
                         '不能配 --style %s（会把画面和模板搞错）\n'
                         % (args.kind, kind_style, args.style))
        sys.exit(2)
    args.style = kind_style
    if args.tag is None:
        args.tag = 'ANIMF_flo' if args.kind == 'flower' else 'ANIMF_exp'

    device = args.device
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)
    k = KIND[args.kind]
    templates = wp.load_templates()

    print('[%s] 开机' % args.tag)
    img, layout, rows, cols = wp.restart_app(device, outdir)
    img, layout = wp.dismiss_dialogs(device, outdir, layout, rows, cols)
    if img is None:
        img, layout, rows, cols = wp.restart_app(device, outdir)
        img, layout = wp.dismiss_dialogs(device, outdir, layout, rows, cols)
        if img is None:
            raise RuntimeError('棋盘上有盖不住的对话框')
    # 重拉之后应用会重新布局，布局要跟着换（Codex 复审 2026-11-03 的 P2/P3）
    layout = wp.read_layout(device, required=True)
    gx, gy, pitch = wp.grid_from_layout(img, layout, rows, cols)
    unit = layout['unit']
    print('[%s] 网格=(%.0f,%.0f) 格边=%d unit=%d' % (args.tag, gx, gy, pitch, unit))

    if args.switch:
        want = (args.style == 'flower')
        s = switch_style(device, layout, gx, gy, want)
        print('[%s] 切到%s（对话框缩放 s=%.2f）' % (args.tag, args.style, s))
        img = wp.pull_screenshot(device, os.path.join(outdir, '%s_style.jpeg' % args.tag))
        # 切完样式要重新定位一次棋盘（画布可能没动，但保险）
        gx, gy, pitch = wp.grid_from_layout(img, layout, rows, cols)

    # 开一枪把雷布下（首点安全）
    wp.click(device, gx + cols // 2 * pitch + pitch / 2.0, gy + rows // 2 * pitch + pitch / 2.0)
    import time
    time.sleep(1.8)
    img = wp.pull_screenshot(device, os.path.join(outdir, '%s_first.jpeg' % args.tag))

    if args.style == 'flower':
        board = read_board_flower(img, gx, gy, pitch, unit, templates, rows, cols)
    else:
        board = wp.read_board(img, gx, gy, pitch, unit, templates, rows, cols, None)
    print(wp.fmt_board(board))
    res, mine_certain = wp.solve(board, rows, cols, args.mines)
    if not mine_certain:
        print('[%s] 推不出哪格是雷，退出' % args.tag)
        sys.stderr.write('[anim_frames] 推不出哪格是雷（一帧都没抓到），退出码 3\n')
        sys.exit(3)
    r, c = sorted(mine_certain)[0]
    x = gx + c * pitch + pitch / 2.0
    y = gy + r * pitch + pitch / 2.0
    tpls = trip_templates(args.kind)
    size = (int(k['w'] * unit), int(k['h'] * unit))

    def match_at(im, rr, cc):
        rx = int(round(gx + cc * pitch + k['off'][0] * unit))
        ry = int(round(gy + rr * pitch + k['off'][1] * unit))
        if rx < 0 or ry < 0 or rx + size[0] > im.size[0] or ry + size[1] > im.size[1]:
            return None
        patch = np.asarray(im.crop((rx, ry, rx + size[0], ry + size[1])), dtype=np.float32)
        return match_trip_frame(patch, tpls, size)

    results = []
    hit = None
    candidates = sorted(mine_certain)
    for ci, (rr, cc) in enumerate(candidates[:4]):
        x = gx + cc * pitch + pitch / 2.0
        y = gy + rr * pitch + pitch / 2.0
        print('[%s] 踩雷格 (r=%d,c=%d)' % (args.tag, rr, cc))
        if args.parallel:
            import threading
            th = threading.Thread(target=wp.click, args=(device, x, y))
            th.daemon = True
            th.start()
            time.sleep(args.first_delay)
        else:
            wp.click(device, x, y)
            time.sleep(args.first_delay)
        paths = []
        seen = []

        def on_frame(p, i):
            im = Image.open(p).convert('RGB')
            best = match_at(im, rr, cc)
            fr = None if best is None else best[0]
            sc = 0.0 if best is None else round(best[1], 3)
            seen.append((os.path.basename(p), fr, sc))

        if args.device_burst:
            burst_on_device(device, outdir, args.tag, args.burst, ci, on_frame)
        else:
            for i in range(args.burst):
                p = os.path.join(outdir, '%s_c%d_%02d.jpeg' % (args.tag, ci, i))
                wp.pull_screenshot(device, p)
                on_frame(p, i)
            # 前 4 帧都没有像爆炸的 -> 这一格不是雷，换一颗
            if i >= 3 and not any(f is not None and s >= 0.85 for _, f, s in seen[:4]):
                print('[%s] 这一格没炸（前 4 帧都不匹配），换下一颗' % args.tag)
                break
        results.extend(seen)
        if any(f is not None and s >= 0.85 for _, f, s in seen):
            hit = (rr, cc)
            break
    if hit is None:
        print('[%s] 试了 %d 颗雷都没抓到动画' % (args.tag, min(4, len(candidates))))
    else:
        print('[%s] 抓到了：踩雷格 (r=%d,c=%d)' % (args.tag, hit[0], hit[1]))

    print('%-26s %-8s %s' % ('file', 'frame', 'score'))
    for name, fr, sc in results:
        print('%-26s %-8s %s' % (name, '-' if fr is None else fr, sc))

    # 只认**相似度 >= 0.85** 的帧：动画播完之后画面稳定下来，
    # 那一帧会和某一帧模板「有点像」（爆炸约 0.836、开花约 0.891），那是误认。
    good = [(n, f, s) for n, f, s in results if f is not None and s >= 0.85]
    frame_ids = sorted(set(f for _, f, _ in good))
    summary = os.path.join(outdir, '%s_summary.json' % args.tag)
    with open(summary, 'w', encoding='utf-8') as fh:
        json.dump({'kind': args.kind, 'style': args.style, 'cell': hit,
                   'captured': len(good), 'frame_ids': frame_ids,
                   'frames': results}, fh, indent=1)
    print('[%s] 汇总写入 %s（captured=%d，帧号=%s）'
          % (args.tag, summary, len(good), frame_ids))
    if not good:
        # 一帧都没截到 -> 退出码非 0，自动化/CI 才分得出「截到了」和「没截到」
        sys.stderr.write('[anim_frames] 一帧都没抓到，退出码 3\n')
        sys.exit(3)


if __name__ == '__main__':
    main()
