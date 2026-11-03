# 对话框逐像素比对 · 第三批（统计窗口补四项 + 胜利/失败框复测）

日期：2026-11-01
设备：`127.0.0.1:5557`（Mate 90 Pro 模拟器，屏幕 1280x2832，画布 1280x2598，密度 3.5，画布顶比屏幕顶低 **136 px**，本轮 7 张证据图实测一致）
本轮**没有碰设备**：全部用已有证据图 + 桌面上的参考图做离线比对。
写入范围：`C:\Users\19161\saolei\entry\src\main\ets\common\GameStats.ets`、`StatsWindow.ets`、本文件。

---

## 0. 结论表

| 项 | 结论 | 证据 |
|---|---|---|
| 统计窗口四项 | 已按 Win7 原版「最佳成绩」表的四行补齐：最快用时 / 最快百分比 / 最慢百分比 / 最慢用时 | `GameStats.ets`（新增 `LevelRecord`）、`StatsWindow.ets`（中栏四行） |
| 百分比的分母 | **该难度已玩的局数**（不是全局局数） | Lmy 克隆 `io.h:268-271` |
| 百分比的小数位 | 保留一位小数（2/3 局 = 66.7%，不抹成 67） | `StatsWindow.ets` `percentText()` |
| 向后兼容 | 老存档只有 `played/won/best_<难度>/bestDate_<难度>`，照读不误；新键缺失按「没有纪录」处理，不崩不丢 | `GameStats.ets` `load()` |
| 胜利框（当前 build） | 客户区一致率 **90.55%**、整框一致率 **79.29%** | `DLG2_win_dialog_v2.jpeg` vs `win.jpg` |
| 失败框（**旧** build） | 客户区一致率 **92.50%**、整框一致率 **81.36%**（旧 build 数字，当前 build 会更高，见 §3.2） | `P90_lose_dialog.jpeg` vs `loss.jpg` |
| 统计窗口 | 整框一致率 **79.20%**（对照 `information.jpg`，缩放 1.7778 非整数） | `CM_1101d_stats_list_beginner.jpeg` |
| 六框几何偏差 | **0 处**（外框位置/尺寸、按钮矩形、文字墨迹顶全部对齐，见 §3.3） | §3.3 |
| 构建 | `BUILD SUCCESSFUL`，产物 `entry-default-signed.hap`（12.6 MB） | §4 |

> **参考图出处（必须一起读）**：`win.jpg` / `loss.jpg` / `about.jpg` / `information.jpg` 全部来自
> `C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg\`，那是 **Lmy 自己做的 Win7 克隆的对话框截图**，
> **不是 Win7 原版截图**。所以本文所有百分比只能叫**「与 Lmy 克隆框的一致率」**，
> 不能写成「与 Win7 原版一致」。本文不引用任何「Win7 原版像素」当依据。

---

## 1. 原版那四项：是什么、怎么算、怎么排版

### 1.1 出处清单（都是本机可查的代码/资源）

| # | 出处 | 行号 | 提供了什么 |
|---|---|---|---|
| 1 | `Minesweeper-master/Minesweeper/utf8/io.h` | 246-305 | `readProfileStatistic()`：**按难度分节**读统计的函数 |
| 2 | 同上 | **268-271** | **百分比的算法**：`valueCount[2] = (int)((float)winCount / gameCount * 100)`；`gameCount==0` 时为 0 |
| 3 | 同上 | 248-252 | 分节里的键：`GAMECOUNT` / `WINCOUNT` / `MOSTWIN` / `MOSTLOSE` / `NOWCOUNT` |
| 4 | 同上 | 274-278 | `BESTTIME1..5`：**按难度分节**各存 5 个最快时间，单位是**十分之一秒**（读出来 ×10） |
| 5 | 同上 | 287-290 | `DATE1..5`：与最快时间配套的日期 |
| 6 | `Minesweeper-master/Minesweeper/utf8/Minesweeper.cpp` | 500 | 统计数组的注释：`gameCount, winCount, winRate, mostWin, mostLost, nowCount` |
| 7 | 同上 | 526-533 | 统计对话框填数：右栏 6 行（`IDC_STATIC1..6`）分别写 局数/胜局/胜率/连胜/连败/当前连败 |
| 8 | 同上 | 536-547 | 中栏「最佳时间」表：按难度分节填 `IDC_TIME1..5` + 日期 |
| 9 | `Minesweeper-master/Minesweeper/utf8/Minesweeper.rc` | **45-66** | `IDD_STATISTIC DIALOGEX 0,0,457,133` 的完整版式：左 `LISTBOX` (8,8,105,49)、中 `GROUPBOX "最佳时间"` (123,8,158,70)、右 6 个标签 (x=290) + 6 个数值 (x=328, y=8/22/36/50/64/78)、底部 `关闭(C)` (328,107,104,18) 与 `重置(&R)` |
| 10 | `linux-minesweeper-main/src/game/Statistics.cpp` | 25-51 | Win7 观感复刻的**按难度**统计：`load/recordGame/reset`，键 `stats/<难度>/played / won / bestTime / curStreak / bestWinStreak / worstLossStreak` |
| 11 | `linux-minesweeper-main/src/ui/StatisticsDialog.cpp` | 34-44, 64-77 | 统计窗口的 6 个标题（Games played/won/Win percentage/Best time/Longest winning streak/Longest losing streak）与**胜率 = `won*100/played`（整除）** |
| 12 | `ReversingMinesweeper-master/Minesweeper/windowing.c` | 304-361 | **Windows XP 原版**的 Winners 对话框：只有「每档最快用时 + 玩家名」（`GameConfig.Times[0..2]`、`ShowWinnerNameAndTime`） |

### 1.2 四项的定义（对照表）

| 项 | 含义 | 分子 / 分母 | 我们代码里的对应 | 依据 |
|---|---|---|---|---|
| **最快用时** | 该难度**获胜局**里最短的一次用时（秒） | 直接取最小值 | `GameStats.bestSeconds`（按难度存） | io.h:274-278（BESTTIME 按难度分节）；Statistics.cpp:34-37 |
| **最快百分比** | 该难度**历史胜率**的最大值 | 分子=该难度获胜局数 / 分母=**该难度已玩局数** | `LevelRecord.bestPercent` | io.h:268-271（胜率算式 + 同分节取 gameCount/winCount） |
| **最慢百分比** | 该难度**历史胜率**的最小值 | 同上 | `LevelRecord.worstPercent` | 同上；胜率随胜负上下波动，取历史极值 |
| **最慢用时** | 该难度**获胜局**里最长的一次用时（秒） | 直接取最大值 | `LevelRecord.slowest` | 与「最快用时」同一口径（只统计获胜局）；失败的局没有可比性 |
| （附带）已玩游戏 / 已胜游戏 / 获胜率 | 全局口径，原封不动保留 | 全局 won / 全局 played | `GameStats.played/won` | Minesweeper.cpp:528-530；SPEC §5.8 |

**百分号的分母到底是哪个**：io.h 的 `readProfileStatistic(section[level], …)` 是**按难度分节**读的，
分节里的 `GAMECOUNT`/`WINCOUNT` 属于**这一档难度**，所以 `winCount/gameCount` 的分母是
**该难度已玩的局数**，不是全局局数。我们的实现照这个口径做（`GameStats.levelRecord(level).played`）。

**小数位**：两个克隆都取整数（io.h:271 是 `(int)(...)`；StatisticsDialog.cpp:70 是整除）。
本轮按 lead 要求**保留一位小数**（2/3 局是 66.7%，整数会抹成 67）；
整除的那一位差异在 §5 列为已知取舍。

### 1.3 版式（我们怎么摆）

- 窗口骨架、标题栏、左栏列表、右栏 6 行、底部两个按钮：**全部沿用 `information.jpg` 实测值**（`StatsWindow.ets` 顶部常量），一个像素没动。
- 改动只在**中栏 group box**：
  - 原版 `information.jpg` 里中栏是「最佳时间」+ 一行（左边秒数、右边日期）；
  - 现在中栏改成 **Win7 原版「最佳成绩」表的四行**（最快用时 / 最快百分比 / 最慢百分比 / 最慢用时），
    取**左栏当前选中那一档难度**（与原版列表联动一致）。
  - 版式：标签左对齐 x=202，**数值右对齐**（右缘 x=420），行距 22，字体 12（与右栏同一字号），
    墨迹顶 66 / 88 / 110 / 132。
  - group box 的标题由「最佳时间」改成「**最快纪录**」（4 个字，与原来同宽，缺口宽度不变）。
  - 原版那一行的**达成日期**因此不再显示在本窗口 —— 日期仍在**胜利框**里（`bestDate_<难度>` 没动）。

---

## 2. 改了什么（只动了两个文件）

### 2.1 `GameStats.ets`

| 改动 | 说明 |
|---|---|
| 新增 `export interface LevelRecord` | `played / won / slowest / bestPercent / worstPercent` 五个字段 |
| 新增 `private static levelRecords: Map<string, LevelRecord>` | 按难度存 |
| `load()` | 读新键 `lvPlayed_/lvWon_/lvSlowest_/lvBestPct_/lvWorstPct_<难度>`；**旧键 `played/won/best_<难度>/bestDate_<难度>` 照旧读**，一个都没删 |
| `record()` | 局末多调一次 `updateLevelRecord(level, won, seconds)` |
| `updateLevelRecord()` | 局数 +1；获胜局更新最慢用时；算本档胜率 `round(won*1000/played)/10`，再更新最快/最慢百分比 |
| `levelRecord(level)` | 取某一档的四项；没有记录时返回一份全空的（`-1` 表示无纪录） |
| `reset()` | 一并清掉 `levelRecords` |
| `save()` | 写新键；旧键照旧写（`best_<难度>` 仍等于最快用时，与胜利框共用同一份数据） |

**向后兼容的具体行为**：老存档里没有 `lv*` 键 → 读出来是默认值（局数 0、其余 -1）→
统计窗口显示「---」而不是崩；老存档的 `best_<难度>` 继续被胜利框和统计窗口的「最快用时」使用 →
**老数据一条不丢**。新键只增不改，旧版本读新存档也不会崩（多出来的键它不认而已）。

### 2.2 `StatsWindow.ets`

| 改动 | 说明 |
|---|---|
| `import { GameStats, LevelRecord } from './GameStats'` | 取当前选中难度的四项（不用改 `GameController.ets`，写范围之外） |
| 新增常量 `GB4_LABEL_X / GB4_VALUE_RIGHT / GB4_Y0 / GB4_DY` | 四行的标签左缘、数值右缘、首行墨迹顶、行距 |
| `percentText(v)` | 一位小数的百分比文本 |
| `draw()` 中栏 | 「最佳时间」+ 一行 → 「最快纪录」+ 四行（最快用时 / 最快百分比 / 最慢百分比 / 最慢用时），标签左对齐、数值右对齐 |
| 右栏 6 行 | **未动**（已玩游戏 / 已胜游戏 / 获胜率 / 最多连胜 / 最多连败 / 当前连局） |

---

## 3. 逐像素差（离线，用已有证据图）

### 3.1 口径与工具

- 工具：仓库里现成的 `tools/pixel_diff.py`（**只读使用，本轮没改它**）；统计窗口因为缩放不是整数倍，单独用最近邻自比（口径在表里注明）。
- 判定阈值：通道差 > 8 记为不同像素（工具默认）。
- 缩放：胜利框/失败框在真机上是 **k = 2（整数倍）**，参考像素与设备像素一一对应，没有插值；
  统计窗口缩放是 **1.7778**（宽度受限），所以只给整框口径。

### 3.2 数字

| 对话框 | 渲染图（证据） | 参考图 | 缩放 | 客户区一致率 | 整框一致率 | 备注 |
|---|---|---|---|---|---|---|
| 胜利框 | `docs/verify/DLG2_win_dialog_v2.jpeg`（build 323a324） | `win.jpg` 396x340 | k=2 整数 | **90.55%**（差异 44384 / 469680） | **79.29%**（差异 111523 / 538560） | 与第二轮 `DIALOG-PIXEL-DIFF-2.md` 完全复现 |
| 失败框 | `docs/verify/P90_lose_dialog.jpeg`（**旧 build 66e6c33**） | `loss.jpg` 483x288 | k=2 整数 | **92.50%**（差异 35048 / 467000） | **81.36%**（差异 103699 / 556416） | **这是旧 build 的数**，见下 |
| 关于框 | `docs/verify/CM_1101c_help_about.jpeg`（当前 build） | `about.jpg` 615x408（整窗） | k=2 整数 | **87.54%**（差异 23310 / 187144） | **69.41%**（差异 75679 / 247432） | 比第一轮（旧 build）的 86.27% / 68.28% 高（客户区 +1.08 pt），因为 2026-10-31 修过「客户区整体下移 1 参考像素」 |
| 统计窗口 | `docs/verify/CM_1101d_stats_list_beginner.jpeg`（当前 build） | `information.jpg` 702x254 | **1.7778 最近邻** | 无（非整数倍不做分块口径） | **79.20%**（差异 117096 / 562848） | 与 `DIALOG-PIXEL-DIFF-2.md` 同口径复算一致 |
| 帮助框 | `docs/verify/CM_1101c_help_help.jpeg`（当前 build） | 无（Lmy 克隆里没有帮助框参考图） | — | — | — | 只做几何核对 |
| 外观框 | `docs/verify/CM_1101_appearance_thumb_mines.jpeg`（当前 build） | 无 | — | — | — | 只做几何核对 |

**失败框为什么只能给旧 build 的数**：`docs/verify/` 里**没有当前 build 的失败框截图**——
`CM_1101c_lose_*.jpeg`、`CM_1101d_lose_*.jpeg` 全都是 dialogs 用例**点完按钮之后**拍的（框已经关掉），
`CM_1101d_lose_*.jpeg` 逐张找框的结果是「无框」。
唯一带失败框的图是 `P90_lose_dialog.jpeg`，它是 **build 66e6c33** 的（早于 2026-10-31 的两处修复），
证据：它的按钮左边线在设备上是 **1617..1622（约 6 px）**，而当前 build 的同一条边
（`DLG2_win_dialog_v2.jpeg` 胜利框同名按钮）是 **1599..1602（约 4 px）**，
即当前 build 是「内侧平涂 1 参考像素」，旧图是旧的「跨在边外 1 vp」。
按第一轮 `DIALOG-PIXEL-DIFF.md` 的实测，**失败框按钮行占客户区差异的 42%（14767 px）**，
所以当前 build 的失败框客户区一致率**应当明显高于 92.50%**（粗估 ≈95.7%，整框 ≈84.0%）。
**这个数必须等 lead 排到设备、重新出一张带失败框的图再复测**（§4 待复测项 1）。

### 3.3 几何核对（目标 0 处画错）

判据：外框位置/尺寸按源码公式算出来的期望值 vs 截图实测；按钮矩形 vs `buttons[]` 的坐标；
每行文字的墨迹顶 vs `lines[].y`。

| 对话框 | 外框实测（设备像素） | 外框期望 | 偏差 | 按钮矩形偏差 | 文字墨迹顶偏差 |
|---|---|---|---|---|---|
| 失败框 | (157,1147,966,575) | (157,1147,966,576) | (0,0,0,-1) | 上边线 0 | 0..1 px |
| 胜利框 | (244,1095,792,679) | (244,1095,792,680) | (0,0,0,-1) | 上边线 0 / 下边线落在期望的描边带首行 | 0..1 px |
| 帮助框 | (56,1155,1168,560) | (56,1155,1168,560) | **0,0,0,0** | 上边线 0 | 0..1 px（6 行全对） |
| 关于框 | (326,1238,629,394) | (326,1238,628,394) | (0,0,1,0) | 描边色见下 | 0..1 px（3 行全对） |
| 统计窗口 | (16,1209,1248,451) | (16,1209,1248,451) | **0,0,0,0** | 上边线 -1（非整数缩放的取整） | — |
| 外观框 | (220,1095,841,680) | (220,1095,840,680) | (0,0,1,0) | 上边线 0 | — |

- 偏差里 ±1 px 的都是 **JPEG 压缩噪声**（行方向的长暗线在压缩后差一行），不是画错。
- 文字墨迹顶全部落在 0..1 设备像素内（= 0..0.5 参考像素），即**基线与行距是对的**；
  剩下的差异是字形光栅化（Windows GDI 点阵 vs ArkUI 无衬线），第一轮已用同方法判定过。
- 边框粗细：外沿 1 参考像素（设备 2 px）、玻璃 6 px、客户区内侧暗线 1 px、标题栏分隔线 1 px，
  实测与 `WinDialog.ets` / `StatsWindow.ets` 里的常量一致（例：胜利框外沿 `#1e252d`/`#33363d`，
  客户区内侧暗线 `#515153`，底部描边带 `#515153`）。
- 配色：客户区 `#f0f0f0`、外沿 `#222025`（classic 框 `#15192c`）、玻璃 `#c9c1d6`（classic `#a09dc4`）、
  标题栏渐变 `#fbf3fe → #e1d0e8 → #8d87b4`、按钮描边 `#707070`、关闭按钮红 `#dfaeaa/#b04a40/#d88671`，
  实测值与常量逐项吻合。

### 3.4 accelerator 下划线

| 对照 | 参考图 `loss.jpg` | 我们 |
|---|---|---|
| 「再玩一局(P)」里 P 下面有没有下划线 | **没有**（按钮内文字墨迹 y=243..254，下方 y=255..261 无短横线） | **没有**（代码里就没画） |

结论：**我们与 Lmy 克隆框一致**；Win7 原版是给快捷字母加下划线的，我们两边都没做 ——
这是「跟原版还差一处」的已知项（§5），不是相对参考图的画错。

---

## 4. 构建与待复测项

**构建**（`tools\build.ps1`，debug）：

```
BUILD SUCCESSFUL in 22 s 456 ms   （CompileArkTS 8.2 s，无 ERROR）
HAP: C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap   (12 618 846 字节)
```

**按 lead 要求没有装设备**（5557 lead 在跑跑测、5555 归 menubar-fidelity-agent）。
待装包：`entry-default-signed.hap`（12.6 MB）。

**待复测项**（lead 排好设备后跑）：

1. **失败框的当前 build 数字**：需要一张**带失败框**的真机图（dialogs 用例点按钮之后的截图里没有框），
   用来把 §3.2 里旧 build 的 92.50% / 81.36% 换成当前 build 的实测值（粗估 ≈95.7% / ≈84.0%）。
2. **统计窗口四项**：
   - 打开「游戏 → 最佳成绩」，左栏分别点初级/中级/高级，确认四行跟着换档；
   - 玩几局（赢 1 局输 1 局）后确认：最快百分比 = 50.0%、最慢百分比 = 50.0%、最快用时/最慢用时合理；
   - 快速赢一局再输一局，确认「最快百分比」停在 100.0%、「最慢百分比」掉到 50.0%；
   - 换档后确认另一档是独立的四项（分母是**那一档**的局数）。
3. **老存档兼容**：用老版本装过的包升级上来（preferences 里只有 `played/won/best_*`），
   打开统计窗口应显示「---」而不是崩溃，胜利框的最快用时和日期仍应显示。
4. **重置(R)**：点一次后四项与全局计数全部归零，关闭重开应用仍是零。
5. **像素复测**：统计窗口改了中栏内容（标题「最佳时间」→「最快纪录」、一行→四行），
   重新出一张统计窗口截图，按 §3.3 的方法再核一遍几何。

---

## 5. 已知取舍与偏差（留给 lead 拍板）

1. **百分比一位小数**：两个克隆都是整数（io.h:271、StatisticsDialog.cpp:70），
   按 lead 的「保留原版的小数位」改成了**一位小数**。若要跟克隆完全一致，把
   `StatsWindow.ets` 的 `percentText()` 改成 `Math.round(v) + '%'` 即可。
2. **中栏标题与内容变了**：「最佳时间」→「最快纪录」，一行 → 四行，
   原来的「最快用时 + 达成日期」一行不再显示（**日期仍在胜利框里**）。
   这是相对 `information.jpg` 的可见像素偏差，属于「按 lead 要求补 Win7 四项」的必然结果。
3. **最慢用时只统计获胜局**：失败的局没有可比性（可以挂机挂到天荒地老），
   所以只取获胜局里的最长用时。若 lead 要求改成「所有局的最长用时」，改 `updateLevelRecord()` 一处即可。
4. **accelerator 下划线没做**：参考图（Lmy 克隆）也没做，所以相对参考图不是偏差；
   相对 Win7 原版（会给快捷字母加下划线）我们还差这一处，暂未实现。
5. **全局口径与分档口径并存**：右栏 6 行仍是全局（已玩游戏 / 已胜游戏 / 获胜率 / 连胜连败），
   中栏四项是分档口径。两套口径并存是原版列表联动的必然结果，不是 bug。

---

## 6. 本轮用到的证据文件

| 文件 | 用途 |
|---|---|
| `docs/verify/DLG2_win_dialog_v2.jpeg` | 胜利框渲染图（当前 build） |
| `docs/verify/P90_lose_dialog.jpeg` | 失败框渲染图（旧 build 66e6c33） |
| `docs/verify/CM_1101c_help_about.jpeg` | 关于框渲染图（当前 build） |
| `docs/verify/CM_1101c_help_help.jpeg` | 帮助框渲染图（当前 build） |
| `docs/verify/CM_1101d_stats_list_beginner.jpeg` | 统计窗口渲染图（当前 build） |
| `docs/verify/CM_1101_appearance_thumb_mines.jpeg` | 外观框渲染图（当前 build） |
| `C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg\{win,loss,about,information}.jpg` | **Lmy 克隆框**参考图（非 Win7 原版） |
