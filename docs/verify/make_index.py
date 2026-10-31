# -*- coding: utf-8 -*-
"""Generate docs/verify/sprites/INDEX.md from the audit data + the directory listing."""
import os, json

D = r'D:\software\harmony\projects\minesweeper\docs\verify\sprites'
audit = json.load(open(os.path.join(D, '_audit.json'), encoding='utf-8'))
counts = json.load(open(os.path.join(D, '_counts.json'), encoding='utf-8'))

GROUPS = [
    ('RECT_FLAG.png', '红旗（blueSheet 800,1120,36,36）'),
    ('RECT_QUESTION.png', '问号（blueSheet 840,1120,36,36）'),
    ('RECT_HILITE.png', '悬停高亮，相加混合用（blueSheet 880,1120,36,36）'),
    ('RECT_MISFLAG.png', '错旗红叉（blueSheet 920,1120,36,36）'),
    ('RECT_SHADOW_U.png', '上边黑边 18x3（blueSheet 960,1120,36,6）'),
    ('RECT_SHADOW_L.png', '左边黑边 3x18（blueSheet 2024,0,6,36）'),
    ('INLINE_SHADOW_L_LOW.png', 'GameController.ets:436 内联字面量 [1012,3,3,15]'),
    ('RECT_COUNTER.png', '计数器凹槽面板（blueSheet 0,1160,80,42）'),
    ('RECT_MINE.png', '格下地雷（minesweeperSheet 54,0,36,36）'),
    ('RECT_PANEL_MINE.png', '状态条雷图标：银钮装雷（minesweeperSheet 0,0,50,50）'),
    ('WinDialog_win_icon.png', 'WinDialog.ets:303 字面量 [0,0,25,25]，同上'),
    ('RECT_CLOCK.png', '状态条时钟图标：银钮装钟（otherSheet 1810,850,50,50）'),
    ('Anim_SCAN_BAR.png', '胜利扫描条（otherSheet 0,1824,550,124）'),
    ('Theme_RECT_SCAN_BAR_DEAD.png', 'Theme.ets:89 的死常量，与上面同像素'),
    ('digits_contact.png', '彩色数字 1..8 拼版'),
    ('normal_tiles_contact.png', '720 帧凸起砖拼版（25 帧/行）'),
    ('pressed_tiles_contact.png', '720 帧凹陷砖拼版（25 帧/行）'),
    ('explode_frames_contact.png', '踩雷爆炸 23 帧拼版'),
    ('disarm_frames_contact.png', '胜利拆雷光束 38 帧拼版'),
    ('cmp_tripf0.png', '并排对比：逻辑 728,0,57,57 在 blueSheet / otherSheet'),
    ('cmp_tripf1.png', '并排对比：逻辑 787,0,57,57'),
    ('cmp_tripf3.png', '并排对比：逻辑 728,59,57,57'),
    ('cmp_disarmf0_blue.png', '并排对比：逻辑 0,0,50,150（蓝色光束）'),
    ('cmp_disarmf0_green.png', '并排对比：逻辑 364,0,50,150（绿色光束）'),
    ('cmp_disarmf1.png', '并排对比：逻辑 52,0,50,150'),
    ('cmp_scanbar.png', '并排对比：逻辑 0,912,275,62'),
    ('cmp_clock.png', '并排对比：逻辑 905,425,25,25'),
    ('cmp_minesweeperSheet_full4x.png', 'minesweeperSheet 全图 4 倍：只有面板雷与裸雷两个精灵'),
    ('unused_otherSheet_green_beam.png', '未引用：otherSheet 绿色版拆雷光束 x728..1455'),
    ('unused_otherSheet_green_beam_mid.png', '未引用：同上，中段'),
    ('unused_otherSheet_flower_trip.png', '未引用：otherSheet 花园版爆炸动画 x1810..2047'),
    ('unused_otherSheet_led_digits.png', '未引用：otherSheet 底部渐变条 + 第二份彩色数字'),
    ('unused_otherSheet_scanbar_row.png', '未引用：扫描条那一行 x560 之后全空'),
    ('unused_blueSheet_right_strip.png', '未引用：blueSheet 右侧渐变条（窗口边框残片）'),
    ('unused_blueSheet_counter_row.png', '未引用：blueSheet 计数器那一行 x80 之后全空'),
    ('unused_blueSheet_sprite_row.png', '未引用：blueSheet 精灵行 x956 之后全空'),
    ('unused_blueSheet_sprite_band.png', '未引用：blueSheet 渐变块下方横带'),
]

files = sorted(f for f in os.listdir(D) if f.lower().endswith('.png'))

lines = []
lines.append('# sprites/ 裁图索引')
lines.append('')
lines.append('> 由 `docs\\verify\\check_sprites.py` 与 `docs\\verify\\make_unused_crops.py` 生成。')
lines.append('> 全部为**存储像素**（逻辑坐标 ×2）裁出的原始素材，未做任何重绘。')
lines.append('> 用途：一眼看出每条精灵引用切对了没有。')
lines.append('> 无 emoji。')
lines.append('')
lines.append('## 统计')
lines.append('')
lines.append('| 项 | 数 |')
lines.append('|---|---|')
lines.append('| 命名精灵引用条目 | %d（活 %d / 死 %d） |' %
             (counts['entries'], counts['entries'] - counts['dead'], counts['dead']))
lines.append('| 展开后的源矩形 | %d（活 %d + 死 %d） |' %
             (counts['live'] + counts['dead'], counts['live'], counts['dead']))
lines.append('| 越界 | %d |' % len(audit['oob']))
lines.append('| 重复常量组 | %d |' % len(set((d[0], d[1], d[2]) for d in audit['dup'])))
lines.append('| 本目录 PNG 张数 | %d |' % len(files))
lines.append('')
lines.append('## 逐张说明')
lines.append('')
lines.append('| 文件 | 内容 |')
lines.append('|---|---|')
desc = dict(GROUPS)
for f in files:
    d = desc.get(f)
    if d is None:
        if f.startswith('normalTileRect_f'):
            d = '凸起方砖代表帧（0,1,24,25,100,349,699,718,719）'
        elif f.startswith('pressedTileRect_f'):
            d = '凹陷方砖代表帧（0,1,24,25,100,349,699,718,719）'
        elif f.startswith('digitRect_'):
            d = '彩色数字 %s' % f.replace('digitRect_', '').replace('.png', '')
        elif f.startswith('Anim.explodeRect_f'):
            d = '踩雷爆炸第 %s 帧' % f.split('_f')[1].replace('.png', '')
        elif f.startswith('Anim.disarmRect_f'):
            d = '胜利拆雷光束第 %s 帧' % f.split('_f')[1].replace('.png', '')
        elif f.startswith('Theme.tripRect_f'):
            d = '死常量 Theme.tripRect 第 %s 帧（与 Anim.explodeRect 同像素）' % f.split('_f')[1].replace('.png', '')
        elif f.startswith('Theme.disarmRect_f'):
            d = '死常量 Theme.disarmRect 第 %s 帧（与 Anim.disarmRect 同像素）' % f.split('_f')[1].replace('.png', '')
        else:
            d = '（自动生成）'
    lines.append('| `%s` | %s |' % (f, d))
lines.append('')

open(os.path.join(D, 'INDEX.md'), 'w', encoding='utf-8').write('\n'.join(lines))
print('INDEX.md written: %d lines, %d png entries' % (len(lines), len(files)))
