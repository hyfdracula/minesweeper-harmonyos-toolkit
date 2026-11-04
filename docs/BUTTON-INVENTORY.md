# 可交互元素清单（扫雷 · HarmonyOS 移植）

全量静态分析产出，用于后续「逐个点击验证」派活。

- 分析对象：`C:\Users\19161\saolei\entry\src\main\ets`（ArkTS / HarmonyOS 7 = API 26）
- 分析方式：**纯静态读源码**，没有连设备、没有跑任何代码
- 首版产出：2026-10-31 上午；**本次更新：2026-10-31 晚**（对应应用仓 commit `a2b635f`）
- **可交互元素合计 61 个**（统计口径见文末「口径说明」；比首版的 49 个多 12 个，差的来源见 §8）

> **引用约定**：代码位置一律写成**函数名 / 常量名**（如 `GameController.buildMenu()`、
> `WinDialogPainter.loseSpec()`、`Theme.MIN_CELL_PX`），**不写行号** ——
> 应用仓一直在被并行修改，行号会漂移，函数名不会。核对时请按函数名找。

> **两条来自用户本人的权威结论**（2026-10-31，lead 直接向用户确认，
> 用户本人用过 Win7 扫雷；这比任何二手复刻都权威）：
>
> 1. **Win7 判负后确实会弹一个对话框** —— 我们保留「结束对话框」是对的，
>    **不是**与原版的差异。但对话框里的**按钮文案**目前**无据可依**（见 §2 的说明）。
> 2. **Win7 没有笑脸按钮** —— 与我们的实现一致（我们也没做），
>    与「四张图集里查不到笑脸素材」的三方核查结论相互印证。
>
> **用户手上已经没有 Win7 了**（没法再截图）。所以「原版对话框到底长什么样」
> 只能靠**素材与复刻互证**，不要再写「用户会提供截图」。

坐标与单位约定：菜单栏 / 对话框的几何坐标是**参考像素**（原版 1 倍像素），绘制时乘 `sVp` 换算成 vp；
`ctx.font` 里的 `px` 是**设备像素**，字号乘 `sDev`。两者差一个密度（见 `docs/SPEC.md` §5.7）。

---

## 1. 菜单栏（顶层 2 项 + 两个下拉共 12 项）

菜单栏本体画在画布顶部（`WinMenu.ets`），不是系统浮层。点菜单栏时棋盘不吃触摸
（`GameController.inputLocked`）。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 1 | 菜单栏 | 游戏(G) | 单击 | `WinMenuPainter.topHit` → `GameController.menuActionAt` | 展开「游戏」下拉；再点一次收起 | `WinMenuPainter.topHit`；条目 `GameController.buildMenu()` |
| 2 | 菜单栏 | 帮助(H) | 单击 | 同上 | 展开「帮助」下拉；再点一次收起 | `WinMenuPainter.topHit`；条目 `GameController.buildMenu()` |
| 3 | 游戏下拉 | 新建 (F2) | 单击 | `WinMenuPainter.entryHit` → `menuActionAt` | 同难度重开一局：计时归零、棋盘清空、播开局音 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.restart()` |
| 4 | 游戏下拉 | 初级 | 单击 | 同上 | 切到初级 9×9 / 10 雷；菜单里给「初级」打勾 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.setDifficulty()` |
| 5 | 游戏下拉 | 中级 | 单击 | 同上 | 切到中级 16×16 / 40 雷 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` |
| 6 | 游戏下拉 | 高级 | 单击 | 同上 | 切到高级 16 行 × 30 列 / 99 雷 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` |
| 7 | 游戏下拉 | 自定义 | 单击 | 同上 | 打开「自定义」难度对话框（按**当前盘面**的行列数预填） | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.openCustomDialog()` |
| 8 | 游戏下拉 | 标记(?) | 单击 | 同上 | 开关「允许插问号」；关掉后长按只有 旗 → 无标记 两态；菜单打勾跟着变 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.toggleQuestionMarks()` |
| 9 | 游戏下拉 | 声音 | 单击 | 同上 | 开关音效播放；菜单打勾跟着变 | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `SoundPlayer.setEnabled()` |
| 10 | 游戏下拉 | 最佳成绩 | 单击 | 同上 | 打开「扫雷统计信息」窗口（**不是** `WinDialogPainter.bestSpec()`，见口径说明） | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.openInfoDialog()` → `GameController.openStatsWindow()` |
| 11 | 游戏下拉 | **颜色(C)** (F7) | 单击 | 同上 | 打开「颜色」外观对话框（选游戏样式 + 棋盘样式，**点确定才生效**） | 定义 `WinMenu.appearanceEntry()`（挂进 `GameController.buildMenu()`；文案常量 `Appearance.MENU_APPEARANCE_LABEL`）；处理 `Index.ets` 的 `onMenuAction` → `GameController.openInfoDialog()` 的 `'appearance'` 分支 → `Appearance.begin()` |
| 12 | 游戏下拉 | 退出 (X) | 单击 | 同上 | 终止应用（`ability.terminateSelf()`） | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `Index.ets` 的 `exitApp()` |
| 13 | 帮助下拉 | 帮助(H) (F1) | 单击 | 同上 | 打开帮助对话框（Win7 原版插图 + 6 行说明 + 确定） | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.openInfoDialog()` |
| 14 | 帮助下拉 | 关于扫雷 (A) | 单击 | 同上 | 打开「关于 扫雷」对话框（经典蓝灰标题栏 + 雷图标 + 确定） | 定义 `GameController.buildMenu()`；处理 `Index.ets` 的 `onMenuAction` → `GameController.openInfoDialog()` |

分隔线不是可交互元素（`WinMenuPainter.entryHit` 直接跳过）：游戏下拉 4 条
（`sep1`..`sep4`，定义在 `GameController.buildMenu()`），帮助下拉 1 条（`sep1`，同处）。

---

## 2. 结束对话框

结束对话框由 `GameController.buildDialog()` 生成：判负用 `WinDialogPainter.loseSpec()`，
判胜用 `WinDialogPainter.winSpec()`。按钮命中共用 `WinDialogPainter.hitButton()`，
入口是 `GameController.dialogButtonAt()`，动作回调在 `Index.ets` 的 `onDialogAction`。

> **按钮文案仍未确证**（重要）。
>
> - **结构与存在性已由用户确认**：Win7 判负后**确实会弹一个对话框**
>   （2026-10-31 lead 直接向用户确认，用户本人用过 Win7 扫雷）。
>   所以我们保留这个对话框**是对的**，**不要**把它列成「与原版的差异」。
> - **文案无据可依**：现有文案「退出(X) / 换个难度(D) / 再玩一局(P)」
>   （胜利框是「再玩一局(P) / 退出(Q)」）是照着 Lmy 那个克隆的 `loss.jpg` 做的，
>   而 **Lmy 的对话框是它自己设计的**（它自己的菜单也一样，不等于原版）。
>   原版这三个按钮到底叫什么、怎么排，**目前没有证据**。
> - 有一处已知是**有意改动**：「换个难度(D)」那个位置，原版是「重新开始这个游戏(R)」。
>   手机端改成了换难度，`WinDialog.ets` 的注释里写明这是有意为之。

### 2.1 失败对话框（游戏失败）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 15 | 失败对话框 | 退出(X) | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 关框并终止应用 | 定义 `WinDialogPainter.loseSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 16 | 失败对话框 | 换个难度(D) | 单击 | 同上 | 关框回到主界面（**不会**真的展开菜单栏；原版那个位置是「重新开始这个游戏(R)」，手机端有意改的） | 定义 `WinDialogPainter.loseSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 17 | 失败对话框 | 再玩一局(P) | 单击 | 同上 | 同难度重开一局 | 定义 `WinDialogPainter.loseSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 18 | 失败对话框 | 标题栏右上角红叉 X | 单击 | `WinDialogPainter.hitButton`（关框分支，返回 `'close'`） | 关框回到主界面，不退出 | 判定 `WinDialogPainter.hitButton()`；矩形 `WinDialogPainter.closeRect()`；处理 `Index.ets` 的 `onDialogAction` |
| 18b | 失败对话框（关框之后） | **棋盘任意一格** | 单击 | `GameController.tap()`（`gameState` 为 `Won`/`Lost` 时走 `restart()`） | **同盘面重开一局**（增强功能；原版 Win7 局终后棋盘锁死，见 `WIN7-FEATURE-GAP.md` §2.6） | `GameController.tap()` / `restart()` |

### 2.2 胜利对话框（游戏胜利）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 19 | 胜利对话框 | 再玩一局(P) | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 同难度重开一局 | 定义 `WinDialogPainter.winSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 20 | 胜利对话框 | 退出(Q) | 单击 | 同上 | 关框并终止应用 | 定义 `WinDialogPainter.winSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 21 | 胜利对话框 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关框回到主界面 | 判定 `WinDialogPainter.hitButton()`；处理 `Index.ets` 的 `onDialogAction` |
| 21b | 胜利对话框（关框之后） | **棋盘任意一格** | 单击 | 同 18b | **同盘面重开一局**（增强功能，同 18b） | `GameController.tap()` / `restart()` |

胜利对话框不是踩雷后立刻弹：要先播完扫描条 + 拆雷光束动画（约 3 秒），动画结束才建框并弹
（`GameController.startWinSweep()`，弹框在 `GameController.tickFrames()`）。

---

## 3. 菜单触发的对话框

### 3.1 关于扫雷 与 帮助（4 个）

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 22 | 关于扫雷 | 确定 | 单击 | `WinDialogPainter.hitButton` → `dialogButtonAt` | 关闭对话框 | 定义 `WinDialogPainter.aboutSpec()`（蓝框默认按钮）；处理 `Index.ets` 的 `onDialogAction` |
| 23 | 关于扫雷 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关闭对话框 | 判定 `WinDialogPainter.hitButton()`；矩形 `WinDialogPainter.closeRect()`（classic 尺寸） |
| 24 | 帮助 | 确定 | 单击 | 同上 | 关闭对话框 | 定义 `WinDialogPainter.helpSpec()`；处理 `Index.ets` 的 `onDialogAction` |
| 25 | 帮助 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关闭对话框 | 判定 `WinDialogPainter.hitButton()` |

### 3.2 颜色(C) 外观对话框（7 个）

原版 Win7 扫雷「游戏」菜单里的 **"Change Appearance"（F7）**。实现记录见 `docs\APPEARANCE-DIALOG.md`。
对话框 420×340 参考像素，两个分组框 + 四枚缩略图 + 置灰复选框 + 确定/取消。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 26 | 颜色对话框 | 游戏样式：扫雷 | 单击 | `WinDialogPainter.hitButton`（缩略图分支） → `dialogButtonAt` | 只改**待定值**（`Appearance.pendingGame`），**点确定才生效** | 缩略图 `Appearance.spec()` 的 `thumbs`（`id: 'thumb:style:mines'`）；选中 `Appearance.select()` |
| 27 | 颜色对话框 | 游戏样式：花园 | 单击 | 同上 | 同上（待定的游戏样式切成花园） | 缩略图 `Appearance.spec()` 的 `thumbs`（`id: 'thumb:style:flowers'`）；选中 `Appearance.select()` |
| 28 | 颜色对话框 | 棋盘：银蓝 | 单击 | 同上 | 只改**待定值**，点确定才生效 | 缩略图 `Appearance.spec()` 的 `thumbs`（`id: 'thumb:board:blue'`）；选中 `Appearance.select()` |
| 29 | 颜色对话框 | 棋盘：绿色 | 单击 | 同上 | 同上（待定的棋盘样式切成绿色） | 缩略图 `Appearance.spec()` 的 `thumbs`（`id: 'thumb:board:green'`）；选中 `Appearance.select()` |
| 30 | 颜色对话框 | 确定(O) | 单击 | 同上（返回 `'appearance:ok'`） | **把待定值真正应用**（换图集、换游戏样式），并写进 preferences | 按钮 `Appearance.spec()` 的 `buttons`；分发 `GameController.dialogButtonAt()`；落盘 `GameStats.saveStyle()` |
| 31 | 颜色对话框 | 取消(C) | 单击 | 同上（返回 `'appearance:cancel'`） | 关闭对话框，**不生效** | 按钮 `Appearance.spec()` 的 `buttons`；分发 `GameController.dialogButtonAt()` |
| 32 | 颜色对话框 | 标题栏右上角红叉 X | 单击 | 同上（关框分支，返回 `'close'`） | 关闭对话框，不生效 | 判定 `WinDialogPainter.hitButton()`；矩形 `WinDialogPainter.closeRect()` |

**不算可交互元素的一枚**：「随机选择游戏样式和棋盘」复选框。
它在 `Appearance.spec()` 的 `checkBox` 里画出来了，但 `disabled: true`（**按原版置灰**），
而 `WinDialogPainter.hitButton()` **没有给复选框做命中测试**（只测缩略图、按钮、标题栏 X），
所以它**画着但点不动**，与原版行为一致（Linux 复刻同样未实现）。因此**不计入 61 个**。

---

## 4. 扫雷统计信息窗口（菜单 游戏 → 最佳成绩）

窗口本体是 `StatsWindow.ets`（版式抄 `Minesweeper-master/jpg/information.jpg`，702×254 参考像素）。
不是 `WinDialog` 那一套，所以命中走独立函数 `GameController.statsButtonAt()`，
入口在 `MinefieldCanvas.handleTouch()`。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 33 | 统计信息 | 关闭(C) | 单击 | `StatsWindowPainter.hitClose` → `statsButtonAt` | 关闭统计窗口（默认按钮，蓝框） | 矩形 `StatsWindowPainter.closeButtonRect()`；判定 `StatsWindowPainter.hitClose()`；分发 `GameController.statsButtonAt()`；处理 `MinefieldCanvas.handleTouch()` → `GameController.closeStats()` |
| 34 | 统计信息 | 重置(R) | 单击 | `StatsWindowPainter.hitReset` → `statsButtonAt` | 清空所有成绩与统计（局数、胜局、最快纪录、连胜连败）后重画 | 矩形 `StatsWindowPainter.resetRect()`；判定 `StatsWindowPainter.hitReset()`；分发 `GameController.statsButtonAt()`；处理 `MinefieldCanvas.handleTouch()` → `GameStats.reset()` |
| 35 | 统计信息 | 标题栏右上角红叉 X | 单击 | `StatsWindowPainter.hitTitleClose` → `statsButtonAt` | 关闭统计窗口 | 矩形 `StatsWindowPainter.titleCloseRect()`；判定 `StatsWindowPainter.hitTitleClose()`；分发 `GameController.statsButtonAt()` |
| 36 | 统计信息 | 左栏难度列表：初级 | 单击 | `StatsWindowPainter.hitListItem` → `statsButtonAt` | 选中该难度，中栏「最佳时间」跟着切 | 矩形 `StatsWindowPainter.listItemRect()`；判定 `StatsWindowPainter.hitListItem()`；分发 `GameController.statsButtonAt()` |
| 37 | 统计信息 | 左栏难度列表：中级 | 单击 | 同上 | 同上 | 同上 |
| 38 | 统计信息 | 左栏难度列表：高级 | 单击 | 同上 | 同上 | 同上 |
| 39 | 统计信息 | 窗口外任意处 | 单击 | `statsButtonAt` 的「outside」分支 | 关闭统计窗口（避免误入后找不到出口） | 分发 `GameController.statsButtonAt()` 的 outside 分支 |

> **这一版的变化**：首版清单里，统计窗口右上角那个红叉与左栏难度列表都列在
> 「§7 画出来了但点不动」里，**没有**计入 49 个 —— 当时确实点不动。
> 修好之后（commit `8925f0e`）四个控件**实测全部可用**
> （日志 `[Stats] 选中难度 1` / `[Stats] 点击关闭`），所以现在**计入**（35~38 号）。

---

## 5. 自定义难度对话框

对话框规格与自绘在 `CustomField.ets`，命中在 `CustomField.hit()`，
入口 `GameController.customActionAt()`。对话框左边是三个输入框，右边另画一个数字键盘
（`GameController.customLayout()`）。

### 5.1 对话框本身

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 40 | 自定义 | 高度: 输入框 | 单击 | `CustomField.hit` → `customActionAt` | 聚焦「高度」框（外圈套蓝）；下一次数字键**替换**框里旧值 | 判定 `CustomField.hit()` 的编辑框分支；聚焦 `CustomField.focusField()`；框位常量 `CustomField.ets` 的 `EDIT_TOP` |
| 41 | 自定义 | 宽度: 输入框 | 单击 | 同上 | 聚焦「宽度」框 | 判定 `CustomField.hit()` 的编辑框分支；框位常量 `CustomField.ets` 的 `EDIT_TOP` |
| 42 | 自定义 | 雷数: 输入框 | 单击 | 同上 | 聚焦「雷数」框 | 判定 `CustomField.hit()` 的编辑框分支；框位常量 `CustomField.ets` 的 `EDIT_TOP` |
| 43 | 自定义 | 确定(O) | 单击 | 同上（返回 `'ok'`） | 夹取到合法范围（高 9–24、宽 9–30、雷 10–maxMines）后开新局；这局标记为自定义局，不进统计。**超限时提示行当场说清生效值**（「当前 N 将按 M 布雷」） | 判定 `CustomField.hit()` 的 `'ok'` 分支；处理 `GameController.customActionAt()`；夹取 `CustomField.clampSpec()` |
| 44 | 自定义 | 取消(C) | 单击 | 同上（返回 `'cancel'`） | 关闭对话框，不开新局 | 判定 `CustomField.hit()` 的 `'cancel'` 分支；处理 `GameController.customActionAt()` |
| 45 | 自定义 | 标题栏右上角红叉 X | 单击 | 同上（返回 `'cancel'`） | 关闭对话框，不开新局 | 判定 `CustomField.hit()`；绘制 `CustomField.draw()` |

### 5.2 数字键盘（11 个键）

键盘定义在 `NumKeypad.ets`，命中 `NumKeypad.hit()`，
分发 `GameController.customActionAt()`。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 46 | 数字键盘 | 1 | 单击 | `NumKeypad.hit` → `customActionAt` | 把 1 接到当前聚焦的输入框 | 键表 `NumKeypad.ets` 的 `KEYS`；判定 `NumKeypad.hit()`；输入 `CustomField.inputChar()` |
| 47 | 数字键盘 | 2 | 单击 | 同上 | 同上 | 同上 |
| 48 | 数字键盘 | 3 | 单击 | 同上 | 同上 | 同上 |
| 49 | 数字键盘 | 4 | 单击 | 同上 | 同上 | 同上 |
| 50 | 数字键盘 | 5 | 单击 | 同上 | 同上 | 同上 |
| 51 | 数字键盘 | 6 | 单击 | 同上 | 同上 | 同上 |
| 52 | 数字键盘 | 7 | 单击 | 同上 | 同上 | 同上 |
| 53 | 数字键盘 | 8 | 单击 | 同上 | 同上 | 同上 |
| 54 | 数字键盘 | 9 | 单击 | 同上 | 同上 | 同上 |
| 55 | 数字键盘 | 0 | 单击 | 同上 | 同上 | 同上 |
| 56 | 数字键盘 | 退格 | 单击 | 同上（键值 `'del'`） | 删掉当前聚焦框里最后一位数字 | 键表 `NumKeypad.ets` 的 `KEYS`；分发 `GameController.customActionAt()` → `CustomField.backspace()` |

**键盘实际是 11 个键（0-9 共 10 个 + 退格 1 个），排布为：**

```
1 2 3
4 5 6
7 8 9
⌫ 0
```

「确定」「取消」**不在键盘上**，是 §5.1 里的对话框按钮。键盘上没有单独的「确定」键。

输入规则（`CustomField.inputChar()`）：只收 0-9 的单个字符；
焦点刚切换过时这一位数字**替换**旧值，否则追加；追加后超过该框上限（高 24 / 宽 30 / 雷 maxMines）就**拒绝这次输入**；
改了高度或宽度后，雷数超上限会被立刻收回上限。

---

## 6. 棋盘格子本身

格子没有独立的按钮，全部靠手势 + 坐标反查。命中入口统一是 `GameController.hitTest()`，
手势判定在 `MinefieldCanvas.handleTouch()`。

| 序号 | 所在界面 | 元素文案 | 触发方式 | 命中判定在哪个函数 | 预期行为 | 源码位置 |
|---|---|---|---|---|---|---|
| 57 | 棋盘 | 未翻开的格子 | 单击 | `GameController.hitTest` → `GameController.tap` → `MinesweeperEngine.reveal` | 开格；首点延迟布雷并保证 3×3 安全区；周围 0 雷时洪泛展开；踩雷则爆炸判负 | 手势 `MinefieldCanvas.handleTouch()`；`tap` `GameController.tap()`；引擎 `MinesweeperEngine.reveal()` |
| 58 | 棋盘 | 未翻开的格子 | 长按（≥400ms） | `GameController.longPress` → `MinesweeperEngine.toggleMark` | 标记三态循环：无标记 → 红旗 → 问号 → 无标记；插旗时剩余雷数 −1，可为负。「标记(?)」关掉后只有 旗 ↔ 无标记 两态 | 定时器 `MinefieldCanvas.handleTouch()`；`longPress` `GameController.longPress()`；引擎 `MinesweeperEngine.toggleMark()` |
| 59 | 棋盘 | 已翻开的数字格 | 双击（两次间隔 <300ms，点同一格） | `GameController.chord` → `MinesweeperEngine.chord` | 和弦：周围旗数 == 数字则翻开其余未插旗的邻格；旗数不符不动手；旗插错则周围雷同时引爆判负 | 判定 `MinefieldCanvas.handleTouch()`（`DOUBLE_TAP_MS`）；`chord` `GameController.chord()`；引擎 `MinesweeperEngine.chord()` |
| 60 | 棋盘 | 整块棋盘 | 双指捏合 | `GameController.zoomTo` | 按两指间距变化缩放，吸附到整数档（n ∈ 1..8，每格 36…288 设备像素）；以两指中点为锚点，中点位移同时驱动平移 | 手势 `MinefieldCanvas.updatePinch()`；`zoomTo` `GameController.zoomTo()` |
| 61 | 棋盘 | 整块棋盘 | 单指拖动（位移 ≥10vp） | `GameController.panBy` | 平移棋盘；平移被夹紧，棋盘不能被拖出画布，整盘放得下时平移量强制归零 | 手势 `MinefieldCanvas.handleTouch()`；`panBy` `GameController.panBy()`；夹紧 `GameController.clampPan()` |

拖动判定与点击互斥：一旦位移超过阈值就取消长按与单击。
双指变单指时会把拖动原点重设到剩下那根手指。

---

## 7. 哪些元素目前没有任何测试覆盖

覆盖情况对照 `tools/verify.ps1`（一键整机验证脚本）、`docs/DEV-CHECKLIST.md`
与 `docs/CLICK-MATRIX-X7.md` / `docs/CLICK-MATRIX-90P.md`（逐元素点击矩阵）。
`verify.ps1` 目前只做了 7 步：装包启动、点「游戏」开下拉、选高级、回初级、扫盘踩雷看对话框、单指拖动、长按插旗。

### 7.1 完全没有任何覆盖的元素

首版清单按「49 个里有 43 个没覆盖」来算，**现在不适用了** ——
之后又跑过多轮逐元素点击（`CLICK-MATRIX-X7.md` 补测 21 项 + 收尾补测第 35~48 项；
`CLICK-MATRIX-90P.md` 的 33 元素矩阵），当前**仍未覆盖**的是：

| 分组 | 元素 | 为什么没覆盖 |
|---|---|---|
| 颜色对话框 | 27（花园）、29（绿色）以外的「花园模式」实跑 | 缩略图**选中动作**已点过；**花园模式实跑一局**、**判负开花序列**没验 |
| 棋盘 | 59 双击和弦 | `uitest uiInput doubleClick` 本身也还没验证过 |
| 棋盘 | 60 双指捏合 | **uitest 注入不了双指**，必须人工在真机上捏一下并看 hilog 的 `[Touch] 捏合 档位n=…` |
| 结束对话框 | 失败框 15/16/17/18、胜利框 19/20/21 | 失败框在 14:02 补测里点过；**胜利路径**（扫描条 + 拆雷动画 + 胜利框）整条没验过 |
| 菜单 | 12（退出）、14（关于扫雷）以外的新增项 | 「颜色(C)」的打开动作已点过 |

> 具体到每个编号的覆盖状态，见 `docs/DEV-CHECKLIST.md` 与两份 `CLICK-MATRIX-*.md`。
> 本节不再逐编号罗列，避免与那三份文档重复后再各自过期。

### 7.2 已有覆盖的元素

- 菜单栏顶层「游戏(G)」「帮助(H)」都能展开下拉
- 游戏下拉的「初级」「中级」「高级」「自定义」「标记(?)」「声音」「最佳成绩」「颜色(C)」
- 帮助下拉的「帮助(H)」「关于扫雷」
- 结束框「再玩一局(P)」→ 全新棋盘
- 自定义框的 11 个数字键、超限拒绝、退格、确定、标题栏 X
- 统计窗的 4 个控件（左栏难度列表、标题栏红叉、关闭(C)、重置(R)）
- 颜色对话框：打开、选绿色、点确定生效、点取消不生效
- 棋盘单击开格、长按插旗、单指拖动

### 7.3 画出来了但点不动的元素（不是 bug 报告，是待接线清单）

| 元素 | 画在哪 | 为什么点不动 |
|---|---|---|
| 底部状态条左端时钟图标 | `GameController.drawStatusStrip()`（矩形 `Theme.RECT_CLOCK`） | `GameController.hitTest()` 只测棋盘。**这是原版行为，不是 bug** —— Win7 状态条上的时钟与雷图标是纯装饰（依据见 `docs\STATUS-STRIP-VERDICT.md` 结论 A），与「Win7 没有笑脸按钮」这条用户确认相互印证 |
| 底部状态条右端雷图标 | `GameController.drawStatusStrip()`（矩形 `Theme.RECT_PANEL_MINE`） | 同上 |
| 颜色对话框的「随机选择游戏样式和棋盘」复选框 | `Appearance.spec()` 的 `checkBox`（`disabled: true`） | `WinDialogPainter.hitButton()` **没有给复选框做命中测试**。**按原版就是置灰的**，Linux 复刻同样未实现 |
| 菜单栏的 5 条分隔线 | `GameController.buildMenu()` 的 `sep1`..`sep4` 与帮助下拉的 `sep1` | 本来就不是交互元素（`WinMenuPainter.entryHit` 跳过），列在这里只是防止后续派活时误列 |

### 7.4 定义了但没有入口的死代码

| 东西 | 位置 | 说明 |
|---|---|---|
| `GameController.resetView()` | `GameController.ets` | 回到「整盘刚好放下」的视角，**全工程没有任何调用点**。没有「回到全览」按钮，想加的话是现成的 |
| `WinDialogPainter.bestSpec()` | `WinDialog.ets` | 「最佳成绩」的对话框版本，**从未被调用**。「最佳成绩」菜单项实际打开的是 `StatsWindow`（`GameController.openStatsWindow()`）。两者版式不一样：`bestSpec` 是 400×320 的简单列表，`StatsWindow` 是 702×254 的完整统计窗 |

---

## 8. 口径说明（为什么是 61 个）

计数口径：**「用户能产生一次明确操作意图的元素」**，即要么有独立命中矩形，要么有独立的触摸手势。

- **菜单栏顶层 2 个**：游戏、帮助。
- **游戏下拉 10 个**：新建、初级、中级、高级、自定义、标记(?)、声音、最佳成绩、**颜色(C)**、退出。
  下拉里共 14 个条目，另外 4 条是分隔线，`WinMenuPainter.entryHit` 直接跳过，不可点，不计。
- **帮助下拉 2 个**：帮助(H)、关于扫雷。下拉里共 3 个条目，第 3 个是分隔线，不计。
- **结束对话框 7 个**：失败框 3 按钮 + 标题栏 X；胜利框 2 按钮 + 标题栏 X。
- **信息类对话框 4 个**：关于框 2 个、帮助框 2 个（各一个「确定」+ 标题栏 X）。
- **颜色对话框 7 个**：4 枚缩略图（扫雷/花园/银蓝/绿色）+ 确定 + 取消 + 标题栏 X。
  置灰的「随机选择」复选框**不计**（没有命中测试，按原版置灰）。
- **统计信息窗口 7 个**：关闭(C)、重置(R)、标题栏 X、点窗口外、左栏难度列表 3 项。
- **自定义对话框 6 个**：3 个输入框 + 确定 + 取消 + 标题栏 X。
- **数字键盘 11 个**：0-9 共 10 个 + 退格 1 个。**不是 12 个** —— 「确定」「取消」是对话框按钮，不在键盘上。
- **棋盘手势 5 个**：单击、长按、双击和弦、双指捏合、单指拖动。

合计：2 + 10 + 2 + 7 + 4 + 7 + 7 + 6 + 11 + 5 = **61**。

### 比首版的 49 个多出来的 12 个

| 增量 | 个数 | 原因 |
|---|---|---|
| 游戏下拉多「颜色(C)」 | +1 | commit `a2b635f` 新增（位置：最佳成绩之后、退出之前，F7） |
| 颜色对话框 | +7 | 同上：4 缩略图 + 确定 + 取消 + 标题栏 X |
| 统计信息窗口的红叉与难度列表 | +4 | 首版这两处**点不动**，没计入；修好（`8925f0e`）并实测可用后计入 |

### 与任务描述的两处出入（以源码为准）

1. 任务说「数字键盘 12 个键（0-9、退格、确定）」——源码里键盘只有 **11 个键**
   （`NumKeypad.ets` 的 `KEYS` 数组：`1`..`9` + `del` + `0`），「确定」是 §5.1 的对话框按钮。
2. 任务说「帮助下拉 3 项」——源码里帮助下拉**有 3 个条目**（帮助、分隔线、关于扫雷），
   其中可点的只有 **2 个**。

### 三个对话框规格的差异

`WinDialogPainter.loseSpec()`、`winSpec()`、`bestSpec()`、`aboutSpec()`、`helpSpec()`
是 5 套独立的规格，每套自带按钮表，命中时由 `WinDialogPainter.hitButton()` 遍历 `spec.buttons`
统一处理 —— 所以**加按钮只需要改规格数组，不用改命中逻辑**。

`WinDialog` 与 `StatsWindow` / `CustomField` / `Appearance` 是四套独立的绘制与命中体系：

- `WinDialog` 系：`WinDialogPainter.hitButton()` + `WinDialogPainter.closeRect()`，**有关框命中**，
  并额外支持 `spec.thumbs`（外观对话框的缩略图）。
- `StatsWindow` 系：`StatsWindowPainter.hitReset()` + `hitClose()` + `hitTitleClose()` + `hitListItem()`。
- `CustomField` 系：`CustomField.hit()`，关框并入 `'cancel'`。
- `Appearance` 系：不是独立的一套 —— 它**复用** `WinDialog` 的规格与命中
  （`Appearance.begin()` / `Appearance.spec()` 产出 `DlgSpec`，`Appearance.select()` 处理缩略图，
  `Appearance.owns()` 用来识别这批 id）。

> **笑脸按钮：Win7 没有**（2026-10-31 用户确认）。我们也没做 —— **与原版一致，不是缺口**。
