# -*- coding: utf-8 -*-
"""给用例表里的关键用例打上 "critical": true 标记。

为什么不直接用 json.dumps 重写整个文件：
那样会把原文件的紧凑排版全展开，产生几千行**纯格式噪音**的 diff
（实测 custom.json +1644 行），根本没法审。
所以这里做**文本插入**：在用例的 "id" 行后面插一行标记，其余一个字节都不动。

用法：python tools/_mark_critical.py
"""
import io
import os

# 每个域挑一两条**关键**用例：覆盖该域最容易坏的那条路。
CRITICAL = {
    'board.json': ['board.first_click', 'board.restart.after_gameover',
                   'board.outside.no_open'],
    'custom.json': ['custom.key.emptycell', 'custom.limit.height'],
    'dialogs.json': ['dialogs.lose.close', 'dialogs.win.exit',
                     'dialogs.about.close'],
    'menu.json': ['menu.game.new', 'menu.help.about'],
}

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'click_cases')

for fn, ids in CRITICAL.items():
    path = os.path.join(BASE, fn)
    txt = io.open(path, encoding='utf-8').read()
    marked = 0
    for cid in ids:
        pat = '"id": "%s",' % cid
        if pat not in txt:
            print('  !! 找不到 %s（在 %s 里）' % (cid, fn))
            continue
        head, tail = txt.split(pat, 1)
        # 已经标过就别重复标
        if '"critical": true' in tail[:400]:
            continue
        txt = head + pat + '\n      "critical": true,' + tail
        marked += 1
    io.open(path, 'w', encoding='utf-8', newline='').write(txt)
    print('%-14s 标了 %d 条' % (fn, marked))
