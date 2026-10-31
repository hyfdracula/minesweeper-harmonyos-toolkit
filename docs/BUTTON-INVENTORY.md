# 可交互元素清单（扫雷 · HarmonyOS 移植）

全量静态分析产出，用于后续「逐个点击验证」派活。

- 分析对象：`C:\Users\19161\saolei\entry\src\main\ets`（ArkTS / HarmonyOS 7 = API 26）
- 分析方式：**纯静态读源码**，没有连设备、没有跑任何代码
- 产出时间：2026-10-31
- **可交互元素合计 49 个**（统计口径见文末「口径说明」）

坐标与单位约定：菜单栏 / 对话框的几何坐标是**参考像素**（原版 1 倍像素），绘制时乘 `sVp` 换算成 vp；
`ctx.font` 里的 `px` 是**设备像素**，字号乘 `sDev`。两者差一个密度（见 `docs/SPEC.md` §5.7）。

---

## 1. 菜单栏（顶层 2 项 + 两个下拉共 11 项）

菜单栏本体画在画布顶部（`WinMenu.ets`），不是系统浮层。点菜单栏时棋盘不吃触摸
（`GameController.inputLocked`，`GameController.ets:109`）。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 1 | 菜单栏 | 游戏(G) | 单击 | `WinMenuPainter.topHit` → `GameController.menuActionAt` | 展开「游戏」下拉；再点一次收起 | `WinMenu.ets:373` / `GameController.ets:1383` / 定义 `GameController.ets:1290` |
| 2 | 菜单栏 | 帮助(H) | 单击 | 同上 | 展开「帮助」下拉；再点一次收起 | `WinMenu.ets:373` / `GameController.ets:1383` / 定义 `GameController.ets:1309` |
| 3 | 游戏下拉 | 新建 (F2) | 单击 | `WinMenuPainter.entryHit` → `menuActionAt` | 同难度重开一局：计时归零、棋盘清空、播开局音 | 定义 `GameController.ets:1293`；处理 `Index.ets:52` → `restart()` `GameController.ets:156` |
| 4 | 游戏下拉 | 初级 | 单击 | 同上 | 切到初级 9×9 / 10 雷；菜单里给「初级」打勾 | 定义 `GameController.ets:1295`；处理 `Index.ets:54` → `setDifficulty` `GameController.ets:148` |
| 5 | 游戏下拉 | 中级 | 单击 | 同上 | 切到中级 16×16 / 40 雷 | 定义 `GameController.ets:1296`；处理 `Index.ets:55` |
| 6 | 游戏下拉 | 高级 | 单击 | 同上 | 切到高级 16 行 × 30 列 / 99 雷 | 定义 `GameController.ets:1297`；处理 `Index.ets:56` |
| 7 | 游戏下拉 | 自定义 | 单击 | 同上 | 打开「自定义」难度对话框（按当前难度的行列数预填） | 定义 `GameController.ets:1298`；处理 `Index.ets:67` → `openCustomDialog` `GameController.ets:1170` |
| 8 | 游戏下拉 | 标记(?) | 单击 | 同上 | 开关「允许插问号」；关掉后长按只有 旗 → 无标记 两态；菜单打勾跟着变 | 定义 `GameController.ets:1299`；处理 `Index.ets:63` → `toggleQuestionMarks` `GameController.ets:1372` |
| 9 | 游戏下拉 | 声音 | 单击 | 同上 | 开关音效播放；菜单打勾跟着变 | 定义 `GameController.ets:1301`；处理 `Index.ets:60` → `SoundPlayer.setEnabled` |
| 10 | 游戏下拉 | 最佳成绩 | 单击 | 同上 | 打开「扫雷统计信息」窗口（**不是** `WinDialog.bestSpec`，见口径说明） | 定义 `GameController.ets:1303`；处理 `Index.ets:65` → `openInfoDialog` `GameController.ets:1058` → `openStatsWindow` `GameController.ets:1080` |
| 11 | 游戏下拉 | 退出 (X) | 单击 | 同上 | 终止应用（`ability.terminateSelf()`） | 定义 `GameController.ets:1305`；处理 `Index.ets:69` → `exitApp()` `Index.ets:92` |
| 12 | 帮助下拉 | 帮助(H) (F1) | 单击 | 同上 | 打开帮助对话框（6 行说明 + 确定） | 定义 `GameController.ets:1312`；处理 `Index.ets:65` → `openInfoDialog` `GameController.ets:1063` |
| 13 | 帮助下拉 | 关于扫雷 (A) | 单击 | 同上 | 打开「关于 扫雷」对话框（经典蓝灰标题栏 + 雷图标 + 确定） | 定义 `GameController.ets:1314`；处理 `Index.ets:65` → `openInfoDialog` `GameController.ets:1066` |

分隔线不是可交互元素（`entryHit` 直接跳过，`WinMenu.ets:397-400`）：游戏下拉 4 条（`sep1`..`sep4`，
`GameController.ets:1294/1300/1302/1304`），帮助下拉 1 条（`sep1`，`GameController.ets:1313`）。

---

## 2. 结束对话框

结束对话框由 `GameController.buildDialog`（`GameController.ets:1002`）生成：判负用 `loseSpec`，
判胜用 `winSpec`。按钮命中共用 `WinDialogPainter.hitButton`（`WinDialog.ets:503`），
入口是 `GameController.dialogButtonAt`（`GameController.ets:1266`），
动作回调在 `Index.ets:35` 的 `onDialogAction`。

### 2.1 失败对话框（游戏失败）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 14 | 失败对话框 | 退出(X) | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 关框并终止应用 | 定义 `WinDialog.ets:204`；处理 `Index.ets:41` |
| 15 | 失败对话框 | 换个难度(D) | 单击 | 同上 | 关框回到主界面（**不会**真的展开菜单栏，原版那个位置是「重新开始这个游戏(R)」，手机端改的） | 定义 `WinDialog.ets:205`；处理 `Index.ets:38` |
| 16 | 失败对话框 | 再玩一局(P) | 单击 | 同上 | 同难度重开一局 | 定义 `WinDialog.ets:206`；处理 `Index.ets:36` |
| 17 | 失败对话框 | 标题栏右上角红叉 X | 单击 | `WinDialogPainter.hitButton`（关框分支，返回 `'close'`） | 关框回到主界面，不退出 | 判定 `WinDialog.ets:513-518`；矩形 `WinDialogPainter.closeRect` `WinDialog.ets:346`；处理 `Index.ets:45` |

### 2.2 胜利对话框（游戏胜利）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 18 | 胜利对话框 | 再玩一局(P) | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 同难度重开一局 | 定义 `WinDialog.ets:248`；处理 `Index.ets:36` |
| 19 | 胜利对话框 | 退出(Q) | 单击 | 同上 | 关框并终止应用 | 定义 `WinDialog.ets:249`；处理 `Index.ets:41` |
| 20 | 胜利对话框 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关框回到主界面 | 判定 `WinDialog.ets:513-518`；处理 `Index.ets:45` |

胜利对话框不是踩雷后立刻弹：要先播完扫描条 + 拆雷光束动画（约 3 秒），动画结束才建框并弹
（`GameController.startWinSweep` `GameController.ets:835`，弹框在 `tickFrames` `GameController.ets:986-992`）。

---

## 3. 信息类对话框（菜单触发的）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 21 | 关于扫雷 | 确定 | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 关闭对话框 | 定义 `WinDialog.ets:311`（蓝框默认按钮）；处理 `Index.ets:45` |
| 22 | 关于扫雷 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关闭对话框 | 判定 `WinDialog.ets:513-518`；矩形 `WinDialog.ets:346-351`（classic 尺寸） |
| 23 | 帮助 | 确定 | 单击 | 同上 | 关闭对话框 | 定义 `WinDialog.ets:337`；处理 `Index.ets:45` |
| 24 | 帮助 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关闭对话框 | 判定 `WinDialog.ets:513-518` |

---

## 4. 扫雷统计信息窗口（菜单 游戏 → 最佳成绩）

窗口本体是 `StatsWindow.ets`（版式抄 `Minesweeper-master/jpg/information.jpg`，702×254 参考像素）。
不是 `WinDialog` 那一套，所以命中走独立函数 `GameController.statsButtonAt`（`GameController.ets:1140`），
入口在 `MinefieldCanvas.handleTap`（`MinefieldCanvas.ets:289-302`）。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 25 | 统计信息 | 关闭(C) | 单击 | `StatsWindowPainter.hitClose` → `statsButtonAt` | 关闭统计窗口（默认按钮，蓝框） | 矩形 `StatsWindow.ets:221-223`；判定 `StatsWindow.ets:453`；分发 `GameController.ets:1148`；处理 `MinefieldCanvas.ets:298` → `closeStats` `GameController.ets:1162` |
| 26 | 统计信息 | 重置(R) | 单击 | `StatsWindowPainter.hitReset` → `statsButtonAt` | 清空所有成绩与统计（局数、胜局、最快纪录、连胜连败）后重画 | 矩形 `StatsWindow.ets:216-218`；判定 `StatsWindow.ets:442`；分发 `GameController.ets:1145`；处理 `MinefieldCanvas.ets:291` → `GameStats.reset()` `GameStats.ets:96` |
| 27 | 统计信息 | 窗口外任意处 | 单击 | `statsButtonAt` 的「outside」分支 | 关闭统计窗口（避免误入后找不到出口） | `GameController.ets:1151-1157` |

**注意：统计窗口右上角那个红色 X 是画了但点不动的** —— `statsButtonAt` 只测了重置、关闭和「窗口外」，
红块矩形（`StatsWindow.ets:290-299`，x = 702-9-45 = 648）落在窗口内部，所以点击返回 `null`、什么也不发生。
这跟 `WinDialog` 那边（`WinDialog.ets:513-518` 专门补了关框命中）不一样。见 §7。

---

## 5. 自定义难度对话框

对话框规格与自绘在 `CustomField.ets`，命中在 `CustomField.hit`（`CustomField.ets:412`），
入口 `GameController.customActionAt`（`GameController.ets:1212`）→ `MinefieldCanvas.ets:305-307`。
对话框左边是三个输入框，右边另画一个数字键盘（`GameController.customLayout` `GameController.ets:1179`）。

### 5.1 对话框本身

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 28 | 自定义 | 高度: 输入框 | 单击 | `CustomField.hit` → `customActionAt` | 聚焦「高度」框（外圈套蓝）；下一次数字键**替换**框里旧值 | 判定 `CustomField.ets:430-444`；聚焦 `CustomField.focusField` `CustomField.ets:272`；框位 `CustomField.ets:54`（EDIT_TOP[0]=46） |
| 29 | 自定义 | 宽度: 输入框 | 单击 | 同上 | 聚焦「宽度」框 | 判定 `CustomField.ets:430-444`；框位 `CustomField.ets:54`（EDIT_TOP[1]=76） |
| 30 | 自定义 | 雷数: 输入框 | 单击 | 同上 | 聚焦「雷数」框 | 判定 `CustomField.ets:430-444`；框位 `CustomField.ets:54`（EDIT_TOP[2]=106） |
| 31 | 自定义 | 确定(O) | 单击 | 同上（返回 `'ok'`） | 夹取到合法范围（高 9–24、宽 9–30、雷 10–maxMines）后开新局；这局标记为自定义局，不进统计 | 判定 `CustomField.ets:423-425`；处理 `GameController.ets:1228-1236`；夹取 `CustomField.clampSpec` `CustomField.ets:189` |
| 32 | 自定义 | 取消(C) | 单击 | 同上（返回 `'cancel'`） | 关闭对话框，不开新局 | 判定 `CustomField.ets:426-428`；处理 `GameController.ets:1237-1241` |
| 33 | 自定义 | 标题栏右上角红叉 X | 单击 | 同上（返回 `'cancel'`） | 关闭对话框，不开新局 | 判定 `CustomField.ets:419-421`；绘制 `CustomField.ets:328-342` |

### 5.2 数字键盘（11 个键）

键盘定义在 `NumKeypad.ets`，命中 `NumKeypad.hit`（`NumKeypad.ets:74`），
分发 `GameController.ets:1250-1258`。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 34 | 数字键盘 | 1 | 单击 | `NumKeypad.hit` → `customActionAt` | 把 1 接到当前聚焦的输入框 | 键表 `NumKeypad.ets:17-22`；判定 `NumKeypad.ets:74`；输入 `CustomField.inputChar` `CustomField.ets:223` |
| 35 | 数字键盘 | 2 | 单击 | 同上 | 同上 | 同上 |
| 36 | 数字键盘 | 3 | 单击 | 同上 | 同上 | 同上 |
| 37 | 数字键盘 | 4 | 单击 | 同上 | 同上 | 同上 |
| 38 | 数字键盘 | 5 | 单击 | 同上 | 同上 | 同上 |
| 39 | 数字键盘 | 6 | 单击 | 同上 | 同上 | 同上 |
| 40 | 数字键盘 | 7 | 单击 | 同上 | 同上 | 同上 |
| 41 | 数字键盘 | 8 | 单击 | 同上 | 同上 | 同上 |
| 42 | 数字键盘 | 9 | 单击 | 同上 | 同上 | 同上 |
| 43 | 数字键盘 | 0 | 单击 | 同上 | 同上 | 同上 |
| 44 | 数字键盘 | ⌫ 退格 | 单击 | 同上（键值 `'del'`） | 删掉当前聚焦框里最后一位数字 | 键表 `NumKeypad.ets:21`；分发 `GameController.ets:1252-1253` → `CustomField.backspace` `CustomField.ets:256` |

**键盘实际是 11 个键（0-9 共 10 个 + 退格 1 个），排布为：**

```
1 2 3
4 5 6
7 8 9
⌫ 0
```

「确定」「取消」**不在键盘上**，是 §5.1 里的对话框按钮。键盘上没有单独的「确定」键。

输入规则（`CustomField.inputChar` `CustomField.ets:223-253`）：只收 0-9 的单个字符；
焦点刚切换过时这一位数字**替换**旧值，否则追加；追加后超过该框上限（高 24 / 宽 30 / 雷 maxMines）就**拒绝这次输入**；
改了高度或宽度后，雷数超上限会被立刻收回上限。

---

## 6. 棋盘格子本身

格子没有独立的按钮，全部靠手势 + 坐标反查。命中入口统一是 `GameController.hitTest`
（`GameController.ets:687`，把设备像素换算成行列索引），手势判定在
`MinefieldCanvas.handleTouch`（`MinefieldCanvas.ets:156`）。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码行号 |
|---|---|---|---|---|---|---|
| 45 | 棋盘 | 未翻开的格子 | 单击 | `GameController.hitTest` → `GameController.tap` → `MinesweeperEngine.reveal` | 开格；首点延迟布雷并保证 3×3 安全区；周围 0 雷时洪泛展开；踩雷则爆炸判负 | 手势 `MinefieldCanvas.ets:236-241`；`tap` `GameController.ets:698`；引擎 `MinesweeperEngine.ets:259` |
| 46 | 棋盘 | 未翻开的格子 | 长按（≥400ms） | `GameController.longPress` → `MinesweeperEngine.toggleMark` | 标记三态循环：无标记 → 红旗 → 问号 → 无标记；插旗时剩余雷数 −1，可为负。「标记(?)」关掉后只有 旗 ↔ 无标记 两态 | 定时器 `MinefieldCanvas.ets:203-207`；`longPress` `GameController.ets:772`；引擎 `MinesweeperEngine.ets:292-310`；三态枚举 `MinesweeperEngine.ets:23` |
| 47 | 棋盘 | 已翻开的数字格 | 双击（两次间隔 <300ms，点同一格） | `GameController.chord` → `MinesweeperEngine.chord` | 和弦：周围旗数 == 数字则翻开其余未插旗的邻格；旗数不符不动手；旗插错则周围雷同时引爆判负 | 判定 `MinefieldCanvas.ets:335-338`（`DOUBLE_TAP_MS` `MinefieldCanvas.ets:35`）；`chord` `GameController.ets:749`；引擎 `MinesweeperEngine.ets:317` |
| 48 | 棋盘 | 整块棋盘 | 双指捏合 | `GameController.zoomTo` | 按两指间距变化缩放，吸附到整数档（n ∈ 1..8，每格 36…288 设备像素）；以两指中点为锚点，中点位移同时驱动平移 | 手势 `MinefieldCanvas.updatePinch` `MinefieldCanvas.ets:248-281`；`zoomTo` `GameController.ets:281-301` |
| 49 | 棋盘 | 整块棋盘 | 单指拖动（位移 ≥10vp） | `GameController.panBy` | 平移棋盘；平移被夹紧，棋盘不能被拖出画布，整盘放得下时平移量强制归零 | 手势 `MinefieldCanvas.ets:209-225`；`panBy` `GameController.ets:304-313`；夹紧 `clampPan` `GameController.ets:271-278` |

拖动判定与点击互斥：一旦位移超过阈值就取消长按与单击（`MinefieldCanvas.ets:215-219`）。
双指变单指时会把拖动原点重设到剩下那根手指（`MinefieldCanvas.ets:181-193`）。

---

## 7. 哪些元素目前没有任何测试覆盖

覆盖情况对照 `tools/verify.ps1`（一键整机验证脚本）与 `docs/DEV-CHECKLIST.md`。
脚本目前只做了 7 步：装包启动、点「游戏」开下拉、选高级、回初级、扫盘踩雷看对话框、单指拖动、长按插旗。

### 7.1 完全没有任何覆盖的元素（43 个）

| 分组 | 序号 | 说明 |
|---|---|---|
| 菜单栏顶层 | 2 | 「帮助(H)」顶层项：脚本只点过「游戏」 |
| 游戏下拉 | 3, 5, 7, 8, 9, 10, 11 | 「新建」「中级」「自定义」「标记(?)」「声音」「最佳成绩」「退出」都没点过（脚本只点过初级 4 和高级 6） |
| 帮助下拉 | 12, 13 | 「帮助(H)」「关于扫雷」都没点过 |
| 失败对话框 | 14, 15, 16, 17 | 三个按钮和标题栏 X 都没点过 —— `verify.ps1` 第 5 步自己写着「坐标需按截图现场点，脚本先只截图」 |
| 胜利对话框 | 18, 19, 20 | 整条胜利路径都没有：脚本从来没有真的打通一局，胜利对话框连出现都没验证过 |
| 关于扫雷 | 21, 22 | 「确定」与标题栏 X 都没点过 |
| 帮助 | 23, 24 | 「确定」与标题栏 X 都没点过 |
| 统计信息 | 25, 26, 27 | 「关闭(C)」「重置(R)」「点窗口外关闭」都没点过 |
| 自定义 | 28, 29, 30, 31, 32, 33 | 三个输入框、「确定(O)」「取消(C)」、标题栏 X 都没点过 |
| 数字键盘 | 34-44（11 个） | 一个键都没点过 |
| 棋盘 | 47 | 双击和弦没点过（`uitest uiInput doubleClick` 本身也还没验证过） |
| 棋盘 | 48 | 双指捏合没测过 —— **uitest 注入不了双指**，必须人工在真机上捏一下并看 hilog 的 `[Touch] 捏合 档位n=…` |

### 7.2 已有覆盖的元素（6 个）

| 序号 | 覆盖方式 |
|---|---|
| 1 | `verify.ps1` 第 2 步：点开「游戏」下拉 |
| 4 | `verify.ps1` 第 4 步：回初级 |
| 6 | `verify.ps1` 第 3 步：选高级 |
| 45 | `verify.ps1` 第 4 步：扫全盘（间接覆盖单击开格，但**没有**单独验证「点开一个确定是雷的格子会爆炸」这个动作） |
| 46 | `verify.ps1` 第 7 步：长按插旗 |
| 49 | `verify.ps1` 第 6 步：单指拖动 |

### 7.3 画出来了但点不动的元素（不是 bug 报告，是待接线清单）

| 元素 | 画在哪 | 为什么点不动 |
|---|---|---|
| 统计信息窗口右上角红色 X | `StatsWindow.ets:290-309` | `statsButtonAt`（`GameController.ets:1140-1159`）只测了重置、关闭、窗口外，没有测这个矩形；红块在窗口内部，点击返回 `null` |
| 统计信息窗口左栏难度列表（初级/中级/高级） | `StatsWindow.ets:311-342` | 没有任何命中测试，选中条永远固定在第 0 项 |
| 底部状态条左端时钟图标 | `GameController.ets:669`（矩形 `Theme.ets:70`） | `hitTest`（`GameController.ets:687`）只测棋盘；`SPEC.md` §8 第 7 条本来就是待定项「底部两个圆按钮是否可点」 |
| 底部状态条右端雷图标 | `GameController.ets:672`（矩形 `Theme.ets:65`） | 同上 |
| 菜单栏的 5 条分隔线 | `GameController.ets:1294/1300/1302/1304/1313` | 本来就不是交互元素（`entryHit` 跳过），列在这里只是防止后续派活时误列 |

### 7.4 定义了但没有入口的死代码

| 东西 | 位置 | 说明 |
|---|---|---|
| `GameController.resetView()` | `GameController.ets:316-322` | 回到「整盘刚好放下」的视角，**全工程没有任何调用点**。没有「回到全览」按钮，想加的话是现成的 |
| `WinDialogPainter.bestSpec()` | `WinDialog.ets:262-284` | 「最佳成绩」的对话框版本，**从未被调用**。「最佳成绩」菜单项实际打开的是 `StatsWindow`（`GameController.ets:1061`）。两者版式不一样：`bestSpec` 是 400×320 的简单列表，`StatsWindow` 是 702×254 的完整统计窗 |

---

## 8. 口径说明（为什么是 49 个）

计数口径：**「用户能产生一次明确操作意图的元素」**，即要么有独立命中矩形，要么有独立的触摸手势。

- **菜单栏顶层 2 个**：游戏、帮助。
- **游戏下拉 9 个**：新建、初级、中级、高级、自定义、标记(?)、声音、最佳成绩、退出。
  下拉里共 13 个条目，另外 4 条是分隔线，`entryHit` 直接跳过（`WinMenu.ets:397-400`），不可点，不计。
- **帮助下拉 2 个**：帮助(H)、关于扫雷。下拉里共 3 个条目，第 3 个是分隔线（`GameController.ets:1313`），不计。
- **结束对话框 7 个**：失败框 3 按钮 + 标题栏 X；胜利框 2 按钮 + 标题栏 X。
- **信息类对话框 4 个**：关于框 2 个、帮助框 2 个（各一个「确定」+ 标题栏 X）。
- **统计信息窗口 3 个**：关闭(C)、重置(R)、点窗口外。
- **自定义对话框 6 个**：3 个输入框 + 确定 + 取消 + 标题栏 X。
- **数字键盘 11 个**：0-9 共 10 个 + 退格 1 个。**不是 12 个** —— 「确定」「取消」是对话框按钮，不在键盘上。
- **棋盘手势 5 个**：单击、长按、双击和弦、双指捏合、单指拖动。

合计：2 + 9 + 2 + 7 + 4 + 3 + 6 + 11 + 5 = **49**。

### 与任务描述的两处出入（以源码为准）

1. 任务说「数字键盘 12 个键（0-9、退格、确定）」——源码里键盘只有 **11 个键**
   （`NumKeypad.ets:17-22` 的 `KEYS` 数组：`1`..`9` + `del` + `0`），「确定」是 §5.1 的对话框按钮。
2. 任务说「帮助下拉 3 项」——源码里帮助下拉**有 3 个条目**（帮助、分隔线、关于扫雷），
   其中可点的只有 **2 个**。

### 三个对话框规格的差异

`loseSpec`（`WinDialog.ets:184`）、`winSpec`（`WinDialog.ets:214`）、`bestSpec`（`WinDialog.ets:262`）、
`aboutSpec`（`WinDialog.ets:297`）、`helpSpec`（`WinDialog.ets:322`）是 5 套独立的规格，
每套自带按钮表，命中时由 `WinDialogPainter.hitButton` 遍历 `spec.buttons` 统一处理
（`WinDialog.ets:503-520`）——所以**加按钮只需要改规格数组，不用改命中逻辑**。

`WinDialog` 与 `StatsWindow` / `CustomField` 是三套独立的绘制与命中体系：
- `WinDialog` 系：`hitButton`（`WinDialog.ets:503`）+ `closeRect`（`WinDialog.ets:346`），**有关框命中**。
- `StatsWindow` 系：`hitReset`（`StatsWindow.ets:442`）+ `hitClose`（`StatsWindow.ets:453`），**没有关框命中**。
- `CustomField` 系：`hit`（`CustomField.ets:412`），关框并入 `'cancel'`。
