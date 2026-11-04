# Codex 对抗性复审记录（2026-11-03 这一轮）

复审由 `~/.dsh/skills/codex-delegate/codex-delegate.ps1 -Review` 跑的，
模型是 Codex CLI（gpt-6-sol）。**每次复审的裁定值和它的来源都记在这里**，
不写成「通过」了事。

> 裁定解析按 `codex-delegate/SKILL.md` 的口径：
> 模型给了 `VERDICT:` 行 → 直接采信；
> 没给行、但有 P0/P1/P2、Critical/High 等标记 → **由标记推断**，报告时说明是推断；
> 两者都没有 → `UNKNOWN`，**不得当作通过**。

| 轮次 | 范围 | 裁定 | 来源 | 发现 | 处置 |
|---|---|---|---|---|---|
| 第 4 轮 | `50e1bae` 之前 | **BLOCKER** | 由 P0/P1/critical 标记**推断**（无 VERDICT 行） | ① 求解器把旗算进 unknown 又减旗数 → 真雷被标成安全（`solve([1,'F','X','X'],1,4,2)` 返回了可能爆的那格）② preflight 用 `hdc shell ls` 判装没装，而它对**不存在的路径也退出 0** | ① `all_unknown` 只留 X，旗不重复扣 ② 改用 `bm dump -n` + 看 `aa start` 的**输出文本** |
| 第 5 轮 | `50e1bae..HEAD` | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | ① preflight 可能把**上一轮**残留的布局日志当成本次的，应用没画出来也报「正常」② `tablet_check.py` 只读当前那个盘面，另外三个难度根本没跑到 ③ 截图取不到也照样打印「通过」 | ① 起应用**前**记设备时间戳，只认之后的布局行 ② `tablet_check` 依次切四个盘面逐个核对，期望表补齐中级 ③ 检查 `file recv` 的返回码和文件非空 |
| 第 6 轮 | `e05bfdd..HEAD` | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行） | `free` 坐标系在**矮画布**上会落到统计窗**里面**：画布 1280×484、密度 3.5 时统计窗占 x=16..1264、y=16..468，而「棋盘上方空隙」算出来是 (26,80) | 空间改名 `outside_stats`，**按窗的实际边界**挑点（窗居中 → 只可能在左/右/上/下）；离线验过五组画布含该反例 |
| 第 7 轮 | 应用仓 `edb935f..ca5548c`（结算动画可跳过） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | ① 跳过动画时**正在响的爆炸声还在放**（`stopBombTail()` 只撤了定时器）② **长按菜单栏**也会跳过动画，与普通点击菜单栏被排除在外不一致 | ① 跳过时 `SoundPlayer.stop(BOMB_START/BOMB_RUN/BOMB_END)` 三段都停 ② `longPress()` 里先把菜单栏排掉，再判跳过 |
| 第 8 轮 | 规格仓 `1c553f3..HEAD`（跑测器归因修复） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | 文档里引用的 `docs/verify/CM_2355tabfull.log` **不存在**，而跑测器只往 stdout 打 —— 仓里没有任何能核对的产物（原文：*the updated handover relies on a nonexistent log as evidence*） | ① 跑测器每轮自动写 `docs/verify/CM_<tag>.log`（`_Tee` 类，stdout 同时写屏幕和文件）② 那一轮的成绩单**手工归档**成 `docs/verify/CM_2355tabfull.log` |
| 第 9 轮 | 规格仓 `bc22e84..HEAD`（跑测器唤醒/错误检查 + 新增回归用例 + 文档） | **PASS** | **由「无任何严重级别标记」推断**（无 VERDICT 行；模型原话：*I found no actionable defect in the diff*） | 无 | — |
| 第 9 轮 | 应用仓 `d6bac3d..HEAD`（局终点棋盘重开） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | 「重开那一击把画布的双击状态也记下了 → 300ms 内再点同一格被判成**和弦** → 新局里那格还没翻开，和弦什么也不做 → 玩家想开的第一下被静默吃掉」 | 局终时（`controller.gameOver`）**清掉**双击状态再走 `tap()`；`GameController` 加公开只读属性 `gameOver`。应用仓提交 `80a0f98` |

## 第 7 轮：这一轮复审**第一次查的是应用代码**

前六轮的全部发现都在**跑测工具**里，应用仓一行没动。
第 7 轮复审的是应用仓新加的「结算动画可跳过」（提交 `ca5548c`），
两条发现都**在应用代码里**，也都已修（提交 `26ed1ba`）：

| 发现 | 位置 | 为什么是真问题 | 怎么修的 |
|---|---|---|---|
| 跳过时爆炸声还在放 | `GameController.ets` 的 `skipGameOverAnimation()` | `stopBombTail()` 只撤了延时播放的定时器，**已经在放的那一声**还在放完 —— 于是「框已经弹出来了，爆炸声还在耳朵里响」 | 跳过时把爆炸三段（开始/中/结束）都 `SoundPlayer.stop()`。依据：原版是先停循环再放结束音 |
| 长按菜单栏也会跳动画 | `GameController.ets` 的 `longPress()` | 普通点击菜单栏被排除在「跳过」之外（菜单是另一个控件，见 `BoardWidget.cpp:783` 的 `mousePressEvent` 只管棋盘区域），长按菜单栏却会走到 `longPress()` 里跳过 —— 两条路不一致 | `longPress()` 里先 `isOnMenuBar()` 判掉菜单栏，再判跳过 |

修完又复验了一遍（真平板 + 模拟器）：两条都过了。


## 这一轮复审里「模型没输出 VERDICT 行」的情况

第 4、5、6 轮**都没有** `VERDICT:` 行，裁定是从答案里的严重级别标记推断的。
按规矩，**推断来源必须写出来**，不能写成「Codex 说通过了」。

## 前六轮复审查出来的问题，**没有一条在应用代码里**

前六轮的全部发现都在**跑测工具**里（`tools/click_matrix.py`、
`tools/tablet_check.py`、用例 JSON），应用仓 `C:\Users\19161\saolei` 那六轮
**一行代码都没改**（HEAD 仍是 `edb935f`）。

这本身就是个结论：**应用侧是干净的，偶发失败来自测试工具。**

第七轮（见上表）是**第一次查应用代码**：新加的「结算动画可跳过」被指出两个 P2，
都在应用里，也都改了。
