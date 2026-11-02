# -*- coding: utf-8 -*-
"""
solve_test.py —— win_probe 求解器的正式回归测试。

跑法：  python tools/solve_test.py
被 run_engine_tests.ps1 串进去。

为什么要有这个（2026-11-03）：
解算器的子集规则写反了一条（把「B\\A 全是雷」写成「A 全是雷」）。
后果是互斥的两格被同时标成雷，全局约束的缺口一减就归零，
把一个**真是雷**的格子标成安全 —— 跑测器一脚踩上去判负，
「造胜局」在 Mate X7 上白白重试二十多分钟。

这个测试盯三件事：
  1. 具体用例（下面那些盘面）的结论必须一字不差；
  2. **随机对局**：随机布雷、随机揭开若干格，
     反复调用求解器，**它返回的格子绝不能是真雷**；
  3. 求解器不能崩，也不能返回盘面之外的格子。
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_probe as wp  # noqa: E402

FAILS = []
PASSED = [0]


def check(cond, msg):
    if cond:
        PASSED[0] += 1
    else:
        FAILS.append(msg)
    return cond


def mk(rows):
    return [list(r) for r in rows]


# ---------------------------------------------------------------------------
# 用例 1：真实事故盘面（2026-11-03，Mate X7 踩雷的那一局）
#
# 盘面来自实拍截图 ANIM_play_09.jpeg（9x9 / 10 雷）。
# 'X' = 未揭开，None = 揭开的空格，数字 = 揭开的数字。
# 真雷位置（判负后动画翻出来的）：(0,0) (0,8) (2,3) (6,2) (6,5) (7,1) (7,8) (8,0) …
#
# 旧版解算器在这里：
#   * 把 (7,0) 和 (7,1) **同时**标成雷（它们互斥，见 (6,0)=1 的约束）
#   * 于是全局缺口归零，把 (8,0) 标成「安全」
#   * 跑测器点了 (8,0) -> 踩雷 -> 判负
# 修复后：(7,0)/(7,1) 不再同时被标雷，(8,0) 也不在「确定是雷」里，
#         选出的格子是 (8,2)（由 (7,3)=2 与 (6,2)、(8,4) 两颗已知雷推出安全）。
# ---------------------------------------------------------------------------
ACCIDENT = mk([
    ['X', 1, None, None, None, None, None, 1, 'X'],
    [1, 1, 1, 1, 1, None, None, 1, 1],
    [None, None, 1, 'X', 1, None, None, None, None],
    [None, None, 1, 1, 1, None, None, None, None],
    [None, 1, 1, 1, None, None, None, None, None],
    [None, 2, 'X', 2, 1, 1, 1, None, None],
    [1, 3, 'X', 2, 1, 'X', 1, 1, 1],
    ['X', 'X', 2, 2, 2, 2, 1, 1, 'X'],
    ['X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'X'],
])


def test_accident():
    res, mc = wp.solve(ACCIDENT, 9, 9, 10)
    check(not ((7, 0) in mc and (7, 1) in mc),
          '事故盘面：(7,0) 与 (7,1) 被同时标成雷（它们互斥，源自 (6,0)=1 的约束）')
    check((8, 0) not in mc,
          '事故盘面：(8,0) 被标成确定是雷（实际它可能是安全格，标错就会乱点）')
    # 选出的格子必须是**推得出的安全格**，不能是「大概安全」
    if res is not None:
        check(res in [(8, 2), (8, 3)],
              '事故盘面：选出的格子 %s 不是确定安全的 (8,2)/(8,3)' % (res,))
    else:
        check(True, '')


# ---------------------------------------------------------------------------
# 用例 2：子集规则本身
# ---------------------------------------------------------------------------
def test_subset_rule():
    # 「(6,1)=3 -> {(5,2),(6,2),(7,0),(7,1)} 里 3 雷」与
    # 「(6,0)=1 -> {(7,0),(7,1)} 里 1 雷」并置时，
    # 正确结论是 (5,2)、(6,2) 是雷（差集全是雷），而不是 (7,0)、(7,1) 是雷。
    b = mk([
        [None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None],
        [None, None, 'X', None, None, None, None, None, None],
        [1, 3, 'X', None, None, None, None, None, None],
        ['X', 'X', None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None, None],
    ])
    res, mc = wp.solve(b, 9, 9, 3)
    check((5, 2) in mc and (6, 2) in mc,
          '子集规则：(5,2)、(6,2) 应被判成确定是雷，实际确定是雷 = %s' % sorted(mc))
    check(not ((7, 0) in mc and (7, 1) in mc),
          '子集规则：(7,0)、(7,1) 被同时判成雷')


# ---------------------------------------------------------------------------
# 用例 3：几个基础盘面
# ---------------------------------------------------------------------------
def test_basics():
    res, mc = wp.solve(mk([['X', 1, 'X']]), 1, 3, 1)
    check(res is None or res in [(0, 0), (0, 2)],
          '用例3：1x3 的选择应在两端之间，实际 %s' % (res,))

    # 2x2 斜对角两个 1 + 2 颗雷：全局约束说「2 颗雷都在这 2 个未揭开格子里」，
    # 而局部约束说「(0,0) 的邻格里正好 1 颗雷」—— 两条**互相矛盾**，
    # 所以这个盘面没有可行解，返回 None 是对的。
    res, mc = wp.solve(mk([[1, 'X'], ['X', 1]]), 2, 2, 2)
    check(res is None, '用例4：2x2 的矛盾盘面应该返回 None（没有可行解），实际 %s' % (res,))

    # 3x3 中心一个 1 + 1 颗雷：8 个邻格里正好 1 颗，
    # 每一格都可能是那颗雷 —— 推不出确定安全的格子，返回 None（改插旗）是对的。
    res, mc = wp.solve(mk([
        ['X', 'X', 'X'],
        ['X', 1, 'X'],
        ['X', 'X', 'X'],
    ]), 3, 3, 1)
    check(res is None, '用例5：3x3 中心一个 1 推不出安全格，应返回 None，实际 %s' % (res,))

    # 矛盾盘面不能崩
    try:
        wp.solve(mk([[1, 1, 'X'], ['X', 'X', 'X'], ['X', 'X', 'X']]), 3, 3, 3)
        check(True, '')
    except Exception as exc:
        check(False, '用例6：矛盾盘面求解器崩了：%s' % exc)


# ---------------------------------------------------------------------------
# 用例 4：随机对局 —— 求解器返回的格子**绝不能是真雷**
#
# 这是最要紧的一条：上面所有具体用例都只是「结论对不对」，
# 随机对局盯的是「会不会踩雷」—— 这才是跑测器真正依赖的性质。
# ---------------------------------------------------------------------------
def _make_board(rows, cols, mines, rng):
    """随机布雷 + 随机揭开若干格，返回 (盘面, 真雷集合)。"""
    while True:
        cells = [(r, c) for r in range(rows) for c in range(cols)]
        rng.shuffle(cells)
        mine_set = set(cells[:mines])
        if (0, 0) not in mine_set:
            break
    board = [['X'] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if (r, c) in mine_set:
                continue
            # 随机决定这一格揭开了没有（首点那一片会被揭开，模拟得宽松一点）
            if rng.random() < 0.45:
                n = sum(1 for rr, cc in wp.neighbours(r, c, rows, cols)
                        if (rr, cc) in mine_set)
                board[r][c] = n if n else None
    return board, mine_set


def test_random_never_steps_on_a_mine():
    rng = random.Random(20261103)
    bad = 0
    runs = 0
    # 求解器内部会打印，把 stdout 暂时压掉，免得刷屏
    import io
    import contextlib
    for _ in range(150):
        rows, cols, mines = 9, 9, 10
        board, mine_set = _make_board(rows, cols, mines, rng)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                res, mc = wp.solve(board, rows, cols, mines)
        except Exception as exc:
            check(False, '随机对局：求解器崩了：%s' % exc)
            return
        runs += 1
        if res is None:
            continue          # 推不出安全格 -> 调用方改插旗，不碰雷
        if res in mine_set:
            bad += 1
    check(bad == 0,
          '随机对局：求解器有 %d/%d 次返回了真雷格子' % (bad, runs))


def test_flagging_path():
    """
    插旗路径：插完旗再求解，**不能**把真雷标成安全。

    坑（2026-11-03，Codex 对抗性复审 P1）：
    `solve()` 的 all_unknown 原来把 'F'（已插旗）也算进去，
    而全局约束的 need = 雷数 - 旗数又把旗子减掉了 ——
    **旗子被算了两遍**，全局约束的缺口算错，会把真雷标成安全。

    Codex 给的复现：1x4 盘面 [1,'F','X','X]、2 颗雷，
    求解器返回 (0,2) 当安全格点，而 (0,2) 完全可能是第二颗雷。
    """
    res, mc = wp.solve(mk([[1, 'F', 'X', 'X']]), 1, 4, 2)
    check(res is None or res != (0, 2),
          '插旗路径：solve([1,F,X,X],1,4,2) 把 (0,2) 当安全格点了，而它可能是第二颗雷')
    # 已插旗的格**不能**出现在「确定是雷」里 ——
    # 调用方拿这个集合去长按插旗，重复插一次等于把旗取消。
    check((0, 1) not in mc,
          '插旗路径：已插旗的 (0,1) 不该出现在「确定是雷」里（会被重复插旗）')

    # 两面旗 + 2 颗雷 -> 剩下的 (0,3) **确实**是安全格（这里期望求解器点它）
    res2, mc2 = wp.solve(mk([[1, 'F', 'F', 'X']]), 1, 4, 2)
    check(res2 == (0, 3),
          '插旗路径：solve([1,F,F,X],1,4,2) 应推出 (0,3) 安全，实际 %s' % (res2,))

    # 更一般地：任何「插了旗」的盘面，求解器返回的格子都不能是旗子数
    # 之外算出来的假安全格 —— 用随机对局覆盖（见下面的随机用例）。
    return True


def test_random_with_flags_never_steps_on_a_mine():
    """随机对局 + 随机插旗：求解器返回的格子绝不能是真雷。"""
    rng = random.Random(20261104)
    bad = 0
    runs = 0
    import io
    import contextlib
    for _ in range(120):
        rows, cols, mines = 9, 9, 10
        board, mine_set = _make_board(rows, cols, mines, rng)
        # 随机把几个**确实是雷**的未揭开格插上旗（模拟解算器的插旗推进）
        candidates = [x for x in mine_set if board[x[0]][x[1]] == 'X']
        rng.shuffle(candidates)
        for x in candidates[:rng.randint(0, 3)]:
            board[x[0]][x[1]] = 'F'
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                res, mc = wp.solve(board, rows, cols, mines)
        except Exception as exc:
            check(False, '随机插旗对局：求解器崩了：%s' % exc)
            return
        runs += 1
        if res is None:
            continue
        if res in mine_set:
            bad += 1
        # 「确定是雷」的集合里不能有**已经插了旗**的格 ——
        # 调用方会拿它去长按插旗，重复插一次等于把旗取消。
        flagged_cells = set((x[0], x[1]) for x in mine_set
                            if board[x[0]][x[1]] == 'F')
        if flagged_cells & set(mc):
            bad += 1
    check(bad == 0,
          '随机插旗对局：求解器有 %d/%d 次返回了真雷格子或重复插旗' % (bad, runs))


def main():
    t0 = time.time()
    test_accident()
    test_subset_rule()
    test_basics()
    test_flagging_path()
    test_random_never_steps_on_a_mine()
    test_random_with_flags_never_steps_on_a_mine()
    dt = time.time() - t0
    print('solve_test: 通过 %d，失败 %d（用时 %.1f 秒）' % (PASSED[0], len(FAILS), dt))
    for m in FAILS:
        print('  FAIL: %s' % m)
    return 1 if FAILS else 0


if __name__ == '__main__':
    raise SystemExit(main())
