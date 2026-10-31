#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pixel_diff.py —— 设备截图 vs 原版参考图的**逐像素**比对工具。

用途：把「像素级」从口头承诺变成可测量的数字。
本工程的绘制是「整数倍 + 最近邻（imageSmoothingEnabled=false）」，
所以比对时也必须用最近邻重采样，否则会把抗锯齿当成差异。

依赖：Python 标准库 + Pillow（不 pip install）。

常用法
------
--rect 的语义是「**--ref-rect 选中的那块参考图**在截图里的位置与尺寸（设备像素）」；
不给 --ref-rect 时，它就是参考图整幅。

1) 已知位置与倍数（最快）：

       python tools/pixel_diff.py --ref refs/loss.jpg --shot shot.jpeg \
              --rect 157,1147,966,576 --scale 2 --out docs/verify/DIFF_loss_2x.png

2) 只比对话框的某一块（比如客户区，不含 Aero 标题栏）：
   --ref-rect 选参考图里的那块，--rect 给它在**截图**里的位置（= 整幅原点 + 该块偏移×k）：

       python tools/pixel_diff.py --ref refs/loss.jpg --shot shot.jpeg \
              --ref-rect 8,29,467,250 --rect 173,1205,934,500 --scale 2

   参考图是整窗截图（about.jpg）而屏上只有其中一块对话框时，同理：

       python tools/pixel_diff.py --ref refs/about.jpg --shot shot.jpeg \
              --ref-rect 152,101,314,197 --rect 326,1238,628,394 --scale 2

3) 不给 --rect，让工具自己找（暴力试 k=1..8 + 滑窗 SAD）：

       python tools/pixel_diff.py --ref refs/loss.jpg --shot shot.jpeg --auto-scale

输出
----
* 差异像素数 / 占比、逐通道 R/G/B 平均绝对差、最大单像素通道差
* 差异最大的 N 个区域（连通块，按累计差异排序，带截图坐标）
* 一张三联差异图：参考图 | 截图裁剪 | 差异热力图
* 一行总结：一致率 xx.xx% | 尺度 k=2（整数）| 最大单像素通道差 nn
"""

import argparse
import json
import os
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageStat

# 差异热力图的配色（不用 matplotlib，自己拼）
_HEAT = [
    (0, 0, 0),
    (60, 0, 120),
    (200, 40, 40),
    (255, 160, 0),
    (255, 255, 120),
]


def heat_color(v, vmax):
    """v: 0..255 的差异强度 -> RGB"""
    if vmax <= 0:
        return _HEAT[0]
    t = v / float(vmax)
    if t >= 1.0:
        return _HEAT[-1]
    seg = t * (len(_HEAT) - 1)
    i = int(seg)
    f = seg - i
    a = _HEAT[i]
    b = _HEAT[min(i + 1, len(_HEAT) - 1)]
    return (int(a[0] + (b[0] - a[0]) * f),
            int(a[1] + (b[1] - a[1]) * f),
            int(a[2] + (b[2] - a[2]) * f))


def parse_rect(s):
    """'x,y,w,h' -> (x, y, w, h)"""
    if not s:
        return None
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError('矩形要写成 x,y,w,h')
    try:
        x, y, w, h = [int(float(p)) for p in parts]
    except ValueError:
        raise argparse.ArgumentTypeError('矩形要写成四个整数：x,y,w,h')
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError('矩形的宽高必须为正')
    return (x, y, w, h)


def load_rgb(path):
    im = Image.open(path)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    return im


def crop(img, rect):
    x, y, w, h = rect
    return img.crop((x, y, x + w, y + h))


def crop_clamped(img, rect, what):
    """
    裁剪，但**先把矩形夹到图内**。

    PIL 的 crop 超出边界时会补黑，那会让「一致率」凭空掉一大截却看不出原因，
    所以这里夹住并明确告警。
    """
    x, y, w, h = rect
    W, H = img.size
    cx = max(0, min(x, W))
    cy = max(0, min(y, H))
    cw = max(1, min(w, W - cx))
    ch = max(1, min(h, H - cy))
    if (cx, cy, cw, ch) != (x, y, w, h):
        print('!! 告警：%s 的矩形 %s 超出图像 %dx%d，已夹到 (%d,%d,%d,%d)'
              % (what, (x, y, w, h), W, H, cx, cy, cw, ch))
    return img.crop((cx, cy, cx + cw, cy + ch))


def resize_nearest(img, k):
    """整数倍最近邻放大（我们的实现就是这个，绝不能用双线性）"""
    if k == 1:
        return img.copy()
    w, h = img.size
    return img.resize((w * k, h * k), Image.NEAREST)


def sad(a, b):
    """两张同尺寸图的平均绝对差（C 速度，用 ImageChops）"""
    d = ImageChops.difference(a, b)
    st = ImageStat.Stat(d)
    return sum(st.mean) / 3.0


def ncc(a, b):
    """归一化互相关（-1..1），同尺寸"""
    d = ImageChops.difference(a, b)
    st = ImageStat.Stat(d)
    va = ImageStat.Stat(a)
    vb = ImageStat.Stat(b)
    num = 0.0
    den = 0.0
    for i in range(3):
        ma = va.mean[i]
        mb = vb.mean[i]
        sa = va.stddev[i]
        sb = vb.stddev[i]
        num += ma * mb
        den += sa * sb
    # 用 1 - mean|diff| 归一化（SAD 与 NCC 在本工具里只用来排序）
    mad = sum(st.mean) / 3.0
    return 1.0 - mad / 255.0


def downscale(img, factor):
    """
    缩小，仅用于 --auto-scale 的**粗定位**（先缩小再滑窗，快 64 倍）。

    用**最近邻**：整数倍放大后的硬边在最近邻缩小后仍然是硬边，
    与最终比对的约定一致；粗搜选错尺度的风险由原分辨率精修来兜。
    """
    if factor <= 1:
        return img
    w, h = img.size
    nw = max(1, w // factor)
    nh = max(1, h // factor)
    return img.resize((nw, nh), Image.NEAREST)


def auto_scale(ref, shot, kmin=1, kmax=8, verbose=False):
    """
    自动找「这块参考图在截图里的位置 + 整数放大倍数」。

    做法（暴力但够用）：
      1) 先把截图和参考图按候选 k **用最近邻**缩小 DOWNFACTOR 倍
         （最近邻保持整数倍硬边，与最终比对的约定一致）；
      2) 在缩小后的截图上逐像素滑窗，比平均绝对差（SAD），取最小的几个候选；
      3) 对候选 k 在**原分辨率**上精修 +-REFINE 像素，按原分辨率的 SAD 选出最优 k。

    返回 (k, (x, y, w, h))：参考图这块在截图里的矩形（已按 k 放大）。
    """
    DOWNFACTOR = 8
    REFINE = 6
    TOPK = 3
    W, H = shot.size
    small_shot = downscale(shot, DOWNFACTOR)
    sw, sh = small_shot.size
    cands = []
    for k in range(kmin, kmax + 1):
        tpl_full = resize_nearest(ref, k)
        tw, th = tpl_full.size
        if tw > W or th > H:
            # 原分辨率就放不下，这个 k 不可能
            continue
        tpl = downscale(tpl_full, DOWNFACTOR)
        if tpl.size[0] > sw or tpl.size[1] > sh:
            continue
        tw2, th2 = tpl.size
        kbest = None
        for y in range(0, sh - th2 + 1):
            for x in range(0, sw - tw2 + 1):
                s = sad(tpl, small_shot.crop((x, y, x + tw2, y + th2)))
                if kbest is None or s < kbest[0]:
                    kbest = (s, x, y)
        if kbest is None:
            continue
        if verbose:
            print('  k=%d 粗搜 SAD=%.2f 位置=(%d,%d)' % (k, kbest[0], kbest[1], kbest[2]))
        cands.append((kbest[0], k, kbest[1], kbest[2]))
    if not cands:
        raise RuntimeError('自动定位失败：参考图放大后比截图还大（k=%d..%d 都不行）'
                           % (kmin, kmax))
    cands.sort()
    # 只对最好的几个候选 k 做原分辨率精修，避免粗搜选错尺度
    finals = []
    for _, k, sx, sy in cands[:TOPK]:
        tpl = resize_nearest(ref, k)
        tw, th = tpl.size
        ox = sx * DOWNFACTOR
        oy = sy * DOWNFACTOR
        best2 = None
        for y in range(max(0, oy - REFINE), min(H - th, oy + REFINE) + 1):
            for x in range(max(0, ox - REFINE), min(W - tw, ox + REFINE) + 1):
                s = sad(tpl, shot.crop((x, y, x + tw, y + th)))
                if best2 is None or s < best2[0]:
                    best2 = (s, x, y)
        if best2 is None:
            continue
        if verbose:
            print('  k=%d 精修 SAD=%.2f 位置=(%d,%d)' % (k, best2[0], best2[1], best2[2]))
        finals.append((best2[0], k, best2[1], best2[2]))
    if not finals:
        raise RuntimeError('自动定位失败：候选尺度在原分辨率下都放不下')
    finals.sort()
    _, k, fx, fy = finals[0]
    tw, th = resize_nearest(ref, k).size
    return k, (fx, fy, tw, th)


def estimate_scale_from_rect(ref, shot_rect):
    """
    已知「参考图整幅在截图里的矩形」时，直接从宽度反推放大倍数，
    并判断是不是**整数倍**。

    返回 (k, is_integer, exact_w, exact_h)
    """
    rw, rh = ref.size
    sw, sh = shot_rect[2], shot_rect[3]
    kx = sw / float(rw)
    ky = sh / float(rh)
    k = int(round((kx + ky) / 2.0))
    if k < 1:
        k = 1
    is_int = abs(kx - k) < 0.02 and abs(ky - k) < 0.02
    return k, is_int, kx, ky


def label(img, text, color=(255, 255, 255)):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 * len(text) + 6, 14], fill=(0, 0, 0))
    d.text((3, 2), text, fill=color)
    return img


def top_regions(mask, offset, topn=5, min_area=4, mag=None):
    """
    mask: 二值图（L 模式，255 = 有差异）
    offset: (x0, y0) 掩码左上角在**截图**里的坐标
    mag: 与 mask 同尺寸的差异强度数据（0..255），用来按**累计差异**排序
    返回按累计差异排序的区域列表 [(x0,y0,x1,y1,面积,累计差异), ...]
    """
    w, h = mask.size
    data = mask.tobytes()
    if mag is None:
        mag = data
    seen = bytearray(w * h)
    regions = []
    for i in range(w * h):
        if data[i] == 0 or seen[i]:
            continue
        # 4 邻接洪泛。**行跨度是 w（图像宽度），不是 h** ——
        # 上下邻居是 p-w / p+w，用错会在非正方形的比对区里连错块甚至越界。
        stack = [i]
        seen[i] = 1
        minx = maxx = i % w
        miny = maxy = i // w
        area = 0
        weight = 0
        while stack:
            p = stack.pop()
            area += 1
            weight += mag[p]
            x = p % w
            y = p // w
            if x < minx:
                minx = x
            if x > maxx:
                maxx = x
            if y < miny:
                miny = y
            if y > maxy:
                maxy = y
            if x > 0 and data[p - 1] and not seen[p - 1]:
                seen[p - 1] = 1
                stack.append(p - 1)
            if x < w - 1 and data[p + 1] and not seen[p + 1]:
                seen[p + 1] = 1
                stack.append(p + 1)
            if y > 0 and data[p - w] and not seen[p - w]:
                seen[p - w] = 1
                stack.append(p - w)
            if y < h - 1 and data[p + w] and not seen[p + w]:
                seen[p + w] = 1
                stack.append(p + w)
        if area >= min_area:
            regions.append((offset[0] + minx, offset[1] + miny,
                            offset[0] + maxx, offset[1] + maxy, area, weight))
    # 按**累计差异**排序（面积大但色差小的块不该排在面积小但色差大的块前面）
    regions.sort(key=lambda r: -r[5])
    return regions[:topn]


def build_diff_image(ref_scaled, shot_crop, maxdiff, path, k):
    """三联图：参考图 | 截图裁剪 | 差异热力图"""
    ph = ref_scaled.size[1]
    pw = ref_scaled.size[0]
    sw, sh = shot_crop.size
    pad = 8
    W = pw + sw + pw + pad * 4
    H = max(ph, sh) + 26
    canvas = Image.new('RGB', (W, H), (24, 24, 28))
    canvas.paste(ref_scaled, (pad, 22))
    canvas.paste(shot_crop, (pad * 2 + pw, 22))
    canvas.paste(maxdiff, (pad * 3 + pw * 2, 22))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 6), 'REF x%d' % k, fill=(230, 230, 230))
    d.text((pad * 2 + pw, 6), 'SHOT', fill=(230, 230, 230))
    d.text((pad * 3 + pw * 2, 6), 'DIFF (bright = big)', fill=(230, 230, 230))
    canvas.save(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='设备截图 vs 原版参考图的逐像素比对（整数倍 + 最近邻）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''例:
  # 已知位置与倍数（--rect 给的是「参考图整幅」在截图里的矩形）
  python pixel_diff.py --ref loss.jpg --shot shot.jpeg --rect 157,1147,966,576 --scale 2

  # 只比客户区（参考图里的 8,29,467,250 -> 截图里的 173,1205,934,500）
  python pixel_diff.py --ref loss.jpg --shot shot.jpeg --rect 173,1205,934,500 \\
         --ref-rect 8,29,467,250 --scale 2

  # 参考图是一张整窗截图，对话框只在其中一块时（about.jpg）
  python pixel_diff.py --ref about.jpg --shot shot.jpeg --rect 326,1238,628,394 \\
         --ref-rect 152,101,314,197 --scale 2

  # 让工具自己找位置和倍数
  python pixel_diff.py --ref loss.jpg --shot shot.jpeg --auto-scale
''')
    ap.add_argument('--ref', required=True, help='参考图（png/jpg）')
    ap.add_argument('--shot', required=True, help='设备截图（png/jpg）')
    ap.add_argument('--rect', type=parse_rect, default=None,
                    help='--ref-rect 选中的那块参考图，在截图里的位置与尺寸 x,y,w,h（设备像素）')
    ap.add_argument('--ref-rect', type=parse_rect, default=None,
                    help='参考图里参与比对的区域 x,y,w,h（缺省=整幅）')
    ap.add_argument('--scale', type=int, default=None, help='放大倍数（整数）')
    ap.add_argument('--auto-scale', action='store_true',
                    help='自动估计位置与整数倍数（暴力试 k=1..8 + 滑窗）')
    ap.add_argument('--threshold', type=int, default=8,
                    help='判定「像素不同」的通道差阈值（0..254，默认 8）')
    ap.add_argument('--top', type=int, default=5, help='列出差异最大的 N 个区域（默认 5）')
    ap.add_argument('--name', default=None, help='输出文件名前缀（默认取参考图名）')
    ap.add_argument('--out', default=None, help='差异图输出路径')
    ap.add_argument('--json', default=None, help='把结果写成 json')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args(argv)

    if args.threshold < 0 or args.threshold > 254:
        ap.error('--threshold 必须在 0..254 之间（>=255 会让任何两张图都变成 100% 一致，'
                 '失去判别力；<0 会把完全相同的像素也算成差异）')

    t0 = time.time()
    ref_all = load_rgb(args.ref)
    shot = load_rgb(args.shot)

    # ---- 1. 取参考图里参与比对的区域 ----
    if args.ref_rect is not None:
        ref = crop_clamped(ref_all, args.ref_rect, '参考图区域')
        ref_off = (args.ref_rect[0], args.ref_rect[1])
    else:
        ref = ref_all
        ref_off = (0, 0)

    # ---- 2. 定位与尺度 ----
    #
    # --rect 的语义：**--ref-rect 选中的那块参考图**在截图里的位置与尺寸（设备像素）。
    #   例：loss.jpg 整幅 483x288 在截图里是 157,1147,966,576（= 483x288 放大 2 倍）；
    #        若只想比客户区（参考图里的 8,29,467,250），--rect 就要给
    #        173,1205,934,500（= 8*2+157, 29*2+1147, 467*2, 250*2）。
    scale_src = ''
    rw, rh = ref.size
    if args.rect is not None:
        region = args.rect
        if args.scale is not None:
            k = args.scale
            scale_src = '命令行指定'
            is_int = (region[2] == rw * k and region[3] == rh * k)
        else:
            k, is_int, kx, ky = estimate_scale_from_rect(ref, region)
            scale_src = '按区域尺寸反推'
            # 是不是整数倍：区域的宽高必须正好是参考区域宽高的整数倍（且两个方向一致）
            is_int = (region[2] % rw == 0 and region[3] % rh == 0 and
                      region[2] // rw == region[3] // rh)
            if is_int:
                k = region[2] // rw
    else:
        # 没给 --rect：自己找「参考图里选中的那块」在截图里的位置（暴力试 k=1..8 + 滑窗）
        k, region = auto_scale(ref, shot, verbose=args.verbose)
        scale_src = '自动估计'
        is_int = True
    ref_scaled = resize_nearest(ref, k)

    # 截图里参与比对的区域（--rect 给的就是它）
    shot_rect = region
    shot_crop = crop_clamped(shot, shot_rect, '截图区域')
    size_mismatch = ref_scaled.size != shot_crop.size
    if size_mismatch:
        w = min(ref_scaled.size[0], shot_crop.size[0])
        h = min(ref_scaled.size[1], shot_crop.size[1])
        print('!! 告警：参考图放大后是 %dx%d，截图区域是 %dx%d，尺寸对不上，'
              '**下面的一致率只覆盖重叠的 %dx%d 部分，不能当整体结论**'
              % (ref_scaled.size[0], ref_scaled.size[1],
                 shot_crop.size[0], shot_crop.size[1], w, h))
        ref_scaled = ref_scaled.crop((0, 0, w, h))
        shot_crop = shot_crop.crop((0, 0, w, h))

    # ---- 3. 逐像素差 ----
    diff = ImageChops.difference(ref_scaled, shot_crop)
    st = ImageStat.Stat(diff)
    means = st.mean
    mad = sum(means) / 3.0
    extrema = diff.getextrema()
    max_ch = max(e[1] for e in extrema)

    r, g, b = diff.split()
    maxpix = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mask = maxpix.point(lambda v: 255 if v > args.threshold else 0)
    hist = mask.histogram()
    n_diff = hist[255]
    total = mask.size[0] * mask.size[1]
    ratio = n_diff / float(total) if total else 0.0
    same = 100.0 * (1.0 - ratio)

    # ---- 4. 差异热力图 ----
    vmax = maxpix.getextrema()[1]
    heat = Image.new('RGB', maxpix.size)
    hp = heat.load()
    md = maxpix.tobytes()
    for i in range(len(md)):
        hp[i % maxpix.size[0], i // maxpix.size[0]] = heat_color(md[i], vmax)

    # ---- 5. 差异最大的区域 ----
    regions = top_regions(mask, (shot_rect[0], shot_rect[1]), args.top,
                          mag=maxpix.tobytes())

    # ---- 6. 输出图 ----
    name = args.name or os.path.splitext(os.path.basename(args.ref))[0]
    if args.out:
        out = args.out
    else:
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'docs', 'verify')
        if not os.path.isdir(d):
            d = os.path.abspath(os.path.dirname(args.ref))
        out = os.path.join(d, 'DIFF_%s_%dx.png' % (name, k))
    if not os.path.isdir(os.path.dirname(os.path.abspath(out))):
        os.makedirs(os.path.dirname(os.path.abspath(out)))
    build_diff_image(ref_scaled, shot_crop, heat, out, k)

    # ---- 7. 打印 ----
    print('参考图      : %s  %dx%d  参与比对区域 %s' %
          (args.ref, ref_all.size[0], ref_all.size[1],
           ('%d,%d,%d,%d' % args.ref_rect) if args.ref_rect else '整幅'))
    print('设备截图    : %s  %dx%d' % (args.shot, shot.size[0], shot.size[1]))
    print('定位        : %s  参与比对区域在截图里的矩形 = %s' % (scale_src, shot_rect))
    print('尺度        : k=%d  %s（%s）' %
          (k, '整数倍' if is_int else '非整数倍', scale_src))
    print('参与比对    : %d x %d = %d 像素' %
          (shot_crop.size[0], shot_crop.size[1], total))
    print('差异像素    : %d  (%.3f%%)   一致率 %.2f%%' % (n_diff, ratio * 100, same))
    print('通道平均绝对差: R=%.2f G=%.2f B=%.2f  (平均 %.2f)' %
          (means[0], means[1], means[2], mad))
    print('最大单像素通道差: %d' % max_ch)
    print('差异最大的 %d 个区域（截图坐标, 左上x,左上y,右下x,右下y,面积,累计差异）:' % len(regions))
    for i, r in enumerate(regions, 1):
        print('  %d) x=%d..%d y=%d..%d  面积 %d px (%.2f%% 画布)  累计差异 %d'
              % (i, r[0], r[2], r[1], r[3], r[4], 100.0 * r[4] / total, r[5]))
    print('差异图      : %s' % out)
    print('一致率 %.2f%% | 尺度 k=%d（%s）| 最大单像素通道差 %d | 用时 %.1fs%s'
          % (same, k, '整数' if is_int else '非整数', max_ch, time.time() - t0,
             ' | [尺寸不符，仅重叠部分]' if size_mismatch else ''))

    if args.json:
        data = {
            'ref': args.ref, 'shot': args.shot, 'scale': k,
            'scale_is_integer': bool(is_int), 'scale_source': scale_src,
            'rect_in_shot': list(shot_rect),
            'ref_rect': list(args.ref_rect) if args.ref_rect else None,
            'total_px': total, 'diff_px': n_diff, 'diff_ratio': ratio,
            'same_ratio': same / 100.0,
            'channel_mean_absdiff': {'R': means[0], 'G': means[1], 'B': means[2]},
            'max_channel_diff': max_ch, 'threshold': args.threshold,
            'size_mismatch': bool(size_mismatch),
            'top_regions': [list(r) for r in regions],
            'diff_image': out,
        }
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('json        : %s' % args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
