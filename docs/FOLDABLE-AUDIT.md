# 折叠屏 / 横屏 / 矮画布 风险清单（只读审计）

日期：2026-11-01
审计对象：`C:\Users\19161\saolei\entry\src\main\ets\`（应用仓，**本次未做任何修改**）
规格仓：`D:\software\harmony\projects\minesweeper`
本文件：`docs/FOLDABLE-AUDIT.md`（本次唯一新建文件）

---

## 0. 审计前提

### 0.1 读过的代码

| 文件 | 与本题相关的位置 |
|---|---|
| `common/GameController.ets` | `attach` 225-233；`layout` 247-323；`applyGeometry` 334-366；`clampPan` 380-401；`zoomTo` 403-427；`draw` 457-481；`drawStatusStrip` 840-926；`hitTest` 931-946；`computeDialogScale` 1439-1447；`dialogLayout` 1449-1463；`statsLayout` 1524-1533；`customLayout` 1636-1647；`drawCustom` 1650-1664；`customActionAt` 1672-1705；`dialogButtonAt` 1726-1740；`drawMenu` 1814-1827；`isOnMenuBar` 1830-1852；`dispose` 1956-1964；`resume` 1988-1999 |
| `components/MinefieldCanvas.ets` | `aboutToAppear` 75-105；`aboutToDisappear` 107-110；`tryAttach` 112-117；`onReady` 130-145；`onAreaChange` 146-151；触摸换算 178/200-208/221-223/250/262-265；`handleTap` 298-354 |
| `pages/Index.ets` | 整页（103-117 布局；**没有** expandSafeArea、**没有** onPageShow/onPageHide） |
| `entryability/EntryAbility.ets` | 26-48 窗口舞台重建；50-70 前后台与计时 |
| `common/Theme.ets` | TILE=18(11)、MAX_SCALE_INDEX=8(13)、STRIP_BAND=32(140)、MIN_CELL_PX=48(149)、STRIP_CLOCK_SIZE=25(152)、STRIP_PANEL_W=40(154)、STRIP_PANEL_H=21(155)、STRIP_GAP=6(157)、stripMargin 231 |
| `common/WinMenu.ets` | BAR_H_REF=18(113)、APP_FONT_VP=14(110)、REF_FONT_PX=12(107)、MENU_BAR_H 186（= 21 vp） |
| `common/WinDialog.ets` | 框尺寸：失败 483x288(287-288)、胜利 396x340(342-343)、死代码 bestSpec 400x320(380-381)、关于 314x197(404-405)、帮助 584x280(447-448)；hitButton 的缩略图/按钮/关闭叉命中区 |
| `common/Appearance.ets` | DLG_W=420(47)、DLG_H=340(48)、缩略图 64/76 见方(57-58) |
| `common/CustomField.ets` | DLG_W=280(37)、DLG_H=200(39)、CLOSE_W=18(43)、CLOSE_H=14(44)、BTN_W=70(63)、BTN_H=25(64) |
| `common/NumKeypad.ets` | KEY_W=34(25)、KEY_H=30(26)、GAP=4(27) |
| `common/StatsWindow.ets` | CLOSE_W=45 / CLOSE_H=17（标题栏红叉） |
| `common/GameSession.ets` | 全局单例控制器（折叠不丢局的依据） |

### 0.2 设备参数

| 设备 | 画布（设备像素） | 密度 | pxScale | menuBarPx |
|---|---|---|---|---|
| Mate 90 Pro（模拟器） | 1280 x 2598 | 3.5 | 0.2857 | round(21x3.5)=74 |
| Mate X7（模拟器，折叠竖屏） | 2210 x 2416 级 | 3.5 级 | 0.2857 级 | 74 级 |
| **Pura X Max 内屏（真机，横屏）** | **2584 x 1644** | **2.75** | **0.3636** | **round(21x2.75)=58** |
| Pura X Max 外屏（真机，竖屏） | 1323 x （1936 减去上下系统栏，按 ~1800 估） | 2.75 | 0.3636 | 58 |

### 0.3 代码模型的校验（先证明我的读法对）

用上面这套参数把 lead 给的真机日志逐项复算：

```
布局：画布=2584x1644px 密度换算=0.3636 适配档n=4 当前档n=4 unit=8 格边=144px
      棋盘原点=(644,75) HUD=0 状态条上沿=1371px
```

9x9 盘面代入代码：

1. `layout` 263-272 的适配档循环：u=8 时 bw=9x18x8=1152<=2584（成立）、bh=9x18x8+32x8=1552、menuPx+bh=58+1552=1610<=1644（成立）-> n=4；u=10 时 58+1940=1998>1644（不成立）-> 停，适配档 n=4（与日志一致）
2. `TILE*2*fit=18x2x4=144>=MIN_CELL_PX(48)` -> 不抬档（与日志 n=4 一致）
3. `applyGeometry` 343：boardX=round((2584-1296)/2)=**644**（一致）
4. `applyGeometry` 358-360：groupFits=true -> boardY=58+round((1586-1296-256)/2)=58+17=**75**（一致）
5. `applyGeometry` 364：stripTop=75+1296=**1371**（一致）
6. `hudActive=false` -> **HUD=0**（一致）

六项全部复现，说明下面的推导用的就是真机上的那条代码路径。

---

## 1. 结论速览

| 级别 | 条数 | 一句话 |
|---|---|---|
| 高 | 4 | HUD 模式整条路径、折叠重建路径、密度只取一次、折叠保留缩放档 |
| 中 | 4 | 对话框缩放下限没有 48px 兜底、红叉恒小于 48px、横屏统计窗四周留白、对话框命中区用旧布局 |
| 低 | 5 | 死代码 bestSpec、外屏统计窗非整数档、横屏棋盘留白、未接 onPageShow/onPageHide、下拉菜单命中宽 168vp |

---

## 2. 高风险

### H1. 状态条钉底（HUD 模式）这条分支在两个模拟器上从未执行过

- 代码位置：`GameController.ets:352`（`groupFits` 判定）、`353`（`hudTop`）、`355`（`boardAreaH`）、`358-360`（顶对齐）、`364`（`stripTop`）、`365`（`hudActive`）、`380-401`（`clampPan` 的纵向单向）、`857-860`（HUD 模式铺不透明底色）、`937-939`（`hitTest` 排除状态条区域）
- 触发条件：`menuPx + boardH + stripH > canvasH`，即「画布矮 + 棋盘高」。Pura X Max 内屏画布只有 1644 px 高：24 行自定义局在 n=2（格边 72 px）时 `58+1728+128=1914 > 1644` -> HUD=1；16 行以内的标准局 `58+1152+128=1338 <= 1644` -> 仍是 HUD=0
- 后果：
  - 棋盘底部若干行被状态条带盖住（画了不透明底色 `COLOR_OUTSIDE`，`857-860`），必须纵向拖动才看得见；
  - 纵向平移变成单向（`panY ∈ [-overV, 0]`，`398-400`）；按代数核对：`boardAreaH=hudTop-menuPx`、`overV=boardH-boardAreaH`，`panY=-overV` 时棋盘下沿正好等于 `hudTop`（最后一行完整露出），`panY=0` 时棋盘上沿正好在菜单栏下沿 58 px 处（第一行完整可见）—— 逻辑自洽，但**没有真机画面验证**；
  - 状态条区域内的点击一律返回 -1（`937-939`），避免「点计数器翻开看不见的格子」；
  - 状态条内容有自己的缩放档 su（`873-874`）：2584 宽下 `maxSu=2*floor(2584/142/2)=18`，而 u 最大 16 -> su 恒等于 u，`su<u` 的居中分支不会走
- 模拟器为什么没暴露：Mate 90 Pro 画布高 2598、Mate X7 约 2416，标准局最多 16 行（n=2 时连状态条 1338 px），`groupFits` 永远是 true；两个模拟器上从来没有出现过 `hudActive=1`
- 需要真机做的验证：开一个 24 行（或更高）的自定义局，确认（a）状态条在画布底边且两个计数器可见；（b）上下拖到底时第一行和最后一行都完整可见；（c）状态条上点击不会翻开格子

### H2. 折叠开合会重建窗口舞台，整条「重建后恢复」路径没在真机验过

- 代码位置：`EntryAbility.ets:26-36`（`onWindowStageCreate` -> `loadContent`）、`45-48`（`onWindowStageDestroy` 不做任何事）、`MinefieldCanvas.ets:75-105`（`aboutToAppear` 的异步链）、`107-109`（`aboutToDisappear` -> `controller.dispose()`）、`130-145`（`onReady` -> `tryAttach`）、`146-151`（`onAreaChange` -> `tryAttach`）、`GameController.ets:225-233`（`attach`）、`1956-1964`（`dispose`）、`1988-1999`（`resume`）
- 触发条件：折叠/展开导致窗口舞台销毁重建（而不是只改尺寸）
- 后果：
  - 局面本身不丢：`GameSession.controller` 是模块级单例（`GameSession.ets`），`dispose()` 只停表和清 `context`，不清引擎（`1956-1964` 的注释明确写了「不要清 pendingGameOver」）；
  - 计时会中断一次：`dispose()` 停表 -> `resume()` 再起表（`1988-1994`），中间那几百毫秒（存档+图集重新异步加载）不计入秒数，行为上可接受但未验证；
  - 图集与存档会重新异步加载（`MinefieldCanvas.ets:86-89`）。`SpriteAtlas.applyStyle` 只换引用、**不重画**（该函数注释「只换引用，不重画」），所以存在一个时序窗口：`attach` 先画了一帧还没有精灵的棋盘，图集随后到位但没人触发重画。正常时序下靠 `resume()` 里那次 `layout()+draw()` 补上（`1995-1998`，前提是 `context` 非空），但这条时序在真机上没验过；
  - `resume()` 只在 `engine.rowCount > 0` 时被调（`MinefieldCanvas.ets:94-101`），逻辑与 `dispose` 不清引擎是自洽的；
  - `onWindowStageDestroy` 里没有任何清理，`GameSession.controller` 是跨舞台存活的单例，因此窗口舞台重建不会重置局面——这正是折叠不丢局的关键，但**只在真机上才会走这条路**
- 模拟器为什么没暴露：模拟器不折叠，窗口舞台不会销毁重建；旋转是否重建组件未在模拟器上验证过

### H3. 密度只在 `aboutToAppear` 取一次，折叠换屏后不刷新

- 代码位置：`MinefieldCanvas.ets:76`（`this.density = display.getDefaultDisplaySync().densityPixels`，整个生命周期只此一次）、`146-151`（`onAreaChange` 里 `tryAttach` 用的就是这个旧值）、`112-117`（`tryAttach` -> `controller.attach(..., this.density)`）、`178/200-208/221-223/250/262-265`（触摸坐标一律 `x * this.density`）、`GameController.ets:225-229`（`attach` 用传入的 density 算 `canvasW/canvasH` 并设 `pxScale = 1/density`）
- 触发条件：折叠到**密度与内屏不同**的外屏；或者应用被移到另一块密度不同的屏
- 后果：画布设备像素尺寸整错（`canvasW = round(widthVp * 旧密度)`），棋盘适配档、格边、状态条位置、对话框缩放档与原点全部错位；触摸换算同样用旧密度，点到哪一格也会偏
- 本机情况：Pura X Max 内外屏密度都是 2.75，**不会触发**；但代码没有任何刷新逻辑，换一块密度不同的屏就立刻炸
- 另有一处相关：`display.getDefaultDisplaySync()` 返回的是**默认屏**（内屏），不是应用当前所在的屏，折叠到外屏时它并不会变成外屏
- 模拟器为什么没暴露：模拟器只有一个屏，密度恒定；`onAreaChange` 在旋转时也会触发，但旋转不改密度

### H4. 折叠后保留用户手动缩放档（`userZoomed`）

- 代码位置：`GameController.ets:300-305`（`if (!this.userZoomed) { this.scaleIndex = fit; this.panX = 0; this.panY = 0; }`）
- 触发条件：用户在内屏放大过（`zoomTo` 会置 `userZoomed=true`，`412-413`）之后折叠
- 后果：换屏后档位不重算。举例：内屏放大到 n=8（格边 288 px）后折到外屏（1323 px 宽），一屏只剩 4 列多一点，用户必须自己捏合缩回去；反向（外屏放大后折回内屏）则棋盘只占屏幕中间一小块
- 平移量也不重置（只在 `!userZoomed` 时归零），虽然 `clampPan` 会把越界的值夹回来（`307-308`），但视角会跳
- 模拟器为什么没暴露：模拟器不换屏，旋转虽换画布尺寸，但两屏尺寸相近，体感不明显

---

## 3. 中风险

### M1. 对话框缩放的下限是 0.5，没有「最小可点边 48 设备像素」的兜底

- 代码位置：`GameController.ets:1439-1447`（`computeDialogScale`：`Math.max(0.5, Math.min(2, density, maxByWidth, maxByHeight))`）
- 本机数字（内屏 2584x1644，密度 2.75）：五个框与统计窗的缩放档**全部被 2 封顶**（密度 2.75 > 2），算出来是

  | 框 | 参考尺寸 | 缩放档 | 实际尺寸 | 主按钮高（设备像素） |
  |---|---|---|---|---|
  | 胜利框 | 396x340 | 2 | 792x680 | 27x2 = 54 |
  | 失败框 | 483x288 | 2 | 966x576 | 26x2 = 52 |
  | 帮助框 | 584x280 | 2 | 1168x560 | 25x2 = 50 |
  | 关于框 | 314x197 | 2 | 628x394 | 25x2 = 50 |
  | 外观框 | 420x340 | 2 | 840x680 | 26x2 = 52 |
  | 统计窗 | 702x254 | 2 | 1404x508 | 27x2 = 54 |
  | 自定义框 | 280x200 | 2 | 560x400 | 25x2 = 50 |
  | 数字键盘 | 110x132 | 2 | 220x264 | 30x2 = 60 |

  都 >= 48 设备像素，主按钮在真机上够点
- 风险点：下限 0.5 一旦被碰到，按钮高度只剩 12~13 设备像素（**项目硬规则是宁可溢出也不能缩到点不准**）。会碰到的条件是「画布窄/矮」：比如分屏窄条 540 px 宽时，统计窗 `maxByWidth=(540-32)/702=0.72`，按钮高只剩 19 px；`maxByHeight=(1644-32)/702` 那类也同理。本机纯折叠不触发
- 建议真机验证：开分屏/悬浮窗后再开统计窗和自定义框，确认按钮仍可点

### M2. 标题栏红叉永远小于 48 设备像素

- 代码位置：`StatsWindow.ets` 的 `CLOSE_W=45 / CLOSE_H=17`（标题栏红叉）、`CustomField.ets:43-44` 的 `CLOSE_W=18 / CLOSE_H=14`、`WinDialog.ets` 的 `closeRect`
- 数字：统计窗红叉 45x17 参考像素 -> s=2 时 90x34 设备像素（高度 34 < 48）；自定义框红叉 18x14 -> 36x28（两边都 < 48）
- 后果：违反最小可点边规则，红叉在小屏上难点；不是折叠特有，模拟器上同样存在
- 模拟器为什么没暴露：模拟器上也是同样尺寸，不是新问题，只是与折叠审计一起列出来

### M3. 横屏下统计窗四周留白很大，点窗口外就关窗

- 代码位置：`GameController.ets:1524-1533`（`statsLayout` 居中）、`1600-1607`（点在窗外返回 `'close'`）、`MinefieldCanvas.ets:300-313`（`statsOpen` 时只吃窗口自己的点击）
- 数字：内屏 2584 宽 -> 统计窗 1404 宽，左右各留 590 px 的棋盘
- 后果：用户想点棋盘，结果先把统计窗关了；原版的最佳成绩是**独立窗口**，点棋盘不会关它，这是行为偏差
- 模拟器为什么没暴露：模拟器上统计窗比例接近全屏宽（Mate 90 Pro 1280 宽时 s=1.78，窗宽 1250），左右几乎没棋盘，不容易误触

### M4. 对话框的命中区用的是上一次布局算出来的值

- 代码位置：`GameController.ets:1726-1740`（`dialogButtonAt` 直接用 `this.dialogScale / dialogOx / dialogOy`，**没有先调 `dialogLayout()`**）；对比 `customActionAt:1677`（先调 `customLayout()`）与 `statsButtonAt:1579`（先调 `statsLayout()`）—— 两个都取了新值，只有结束对话框这一条没取
- 触发条件：画布尺寸变了、但在下一次 `draw()` 之前点对话框
- 实际会不会发生：`attach()` -> `layout()` -> `draw()` -> `drawDialog` -> `dialogLayout()`（`1471`）会把三个值刷新，所以正常折叠不会错位。残留风险在 `draw()` 提前返回的分支（`459-461` context 为空、`465-468` CALIBRATE 标定模式）——这两条都不在发布路径上
- 模拟器为什么没暴露：模拟器上对话框开着时画布不变，从来没有「改了尺寸还没重画」的中间态

---

## 4. 低风险

### L1. `WinDialog.bestSpec`（400x320 的旧统计框）是死代码

- 代码位置：`WinDialog.ets:366-388`，全仓无调用点（`openInfoDialog` 的 `'best'` 分支走 `openStatsWindow`，`GameController.ets:1488-1491`）
- 后果：无（画不出来）。留在这里是因为它同样走 `computeDialogScale`，容易让人误以为统计有两个实现

### L2. 外屏竖屏时统计窗的缩放档是非整数

- 数字：外屏 1323 宽 -> `maxByWidth=(1323-32)/702=1.84`，统计窗缩放档 1.84（非整数），文字与边框落在半像素上会发虚
- 模拟器为什么没暴露：Mate 90 Pro 1280 宽时是 1.78，同样非整数，这个观感在模拟器上已经存在

### L3. 横屏下棋盘左右留白很大，状态条两端贴着棋盘边而不是屏幕边

- 代码位置：`GameController.ets:888-890`（时钟锚点 `max(boardX+margin, anchorMargin)`）、`904-909`（雷数图标同逻辑）
- 数字：内屏 9x9 局 n=4 时棋盘 1296 宽、画布 2584 宽 -> 两侧各 644 px 空白，时钟在 x=644、雷数在 x≈1368
- 后果：纯观感问题；计数器不会跑到屏外（这一点在 `883-890` 的注释里已经处理过）

### L4. 页面没有接 `onPageShow/onPageHide`

- 代码位置：`pages/Index.ets` 整页（`aboutToAppear` 29-75 只挂了回调，没有生命周期钩子）；暂停计时只在 `EntryAbility.ets:50-70` 的 `onForeground/onBackground`
- 后果：折叠若没有触发 `onBackground`，重建期间计时会一直走（`resume()` 又起一次表），秒数可能多算折叠那一瞬
- 模拟器为什么没暴露：模拟器不折叠

### L5. 下拉菜单的命中区宽 168 vp

- 代码位置：`GameController.ets:1851`（`pxVp <= x + 168`）
- 数字：168 vp -> 462 设备像素，外屏 1323 宽放得下；但菜单栏总高 `MENU_BAR_H=21 vp`（`WinMenu.ets:186`）-> 58 设备像素，横屏时只占画布高的 3.5%

---

## 5. 逐条回答 lead 的五个问题

### 问题 1：横屏内屏下，对话框的缩放档和原点算得对不对？按钮会不会落到画布外或被状态条盖住？

- 缩放档：**对**。`computeDialogScale`（1439-1447）在内屏得到 `min(2, 2.75, 宽度余量, 高度余量) = 2`（被硬上限 2 封顶，五个框与统计窗无一例外，见 M1 的表）
- 原点：**对**。`dialogLayout`（1449-1463）水平居中、垂直居中（框高都远小于 1644，不触发「比画布还高就顶对齐」的分支）；统计窗 `statsLayout`（1524-1533）、自定义框 `customLayout`（1636-1647）同理。举例胜利框：792x680 -> 原点 (896, 482)，下沿 1162，离画布底 482，离状态条还远
- 会不会落画布外：**不会**。最大的帮助框 1168x560、统计窗 1404x508，都小于 2584x1644
- 会不会被状态条盖住：**不会**。绘制顺序是 `drawStatusStrip` -> `drawMenu` -> `drawCustom` -> `drawDialog` -> `drawStats`（`GameController.ets:473-477`），对话框永远画在状态条之上；命中顺序也是统计窗 -> 自定义框 -> 结束框 -> 菜单 -> 棋盘（`MinefieldCanvas.ets:298-343`），对话框的按钮优先
- 例外：HUD 模式下状态条钉在画布底边（1516~1644），对话框下沿最多到 1162，仍不重叠

### 问题 2：画布只有 1644 高时，「状态条钉底 + 棋盘溢出 + 平移范围」自洽吗？clampPan 会不会让棋盘拖不到顶或拖不出底？

- **自洽**（按代数核对）：`boardAreaH = hudTop - menuPx`（355）、`overV = boardH - boardAreaH`（398）、`panY ∈ [-overV, 0]`（400）。
  - 24x30 局 n=2：`boardH=1728`、`hudTop=1644-128=1516`、`boardAreaH=1458`、`overV=270` -> 棋盘上沿 `58+panY ∈ [-212, 58]`，下沿 `上沿+1728 ∈ [1516, 1786]`。`panY=-270` 时下沿正好 1516（贴着状态条上沿，最后一行完整露出），`panY=0` 时上沿正好 58（菜单栏下沿，第一行完整露出）—— 两个极端都可达，中间连续
  - 横向同理：`limX=(frameW-canvasW)/2`（385），`panX ∈ [-limX, limX]`，左右边缘都能拖到
- **不会**出现「拖不到顶」或「拖不出底」：纵向是单向的（只能往上推），但起点 0 就是「顶对齐菜单栏」，终点 -overV 就是「下沿贴状态条」，全程覆盖
- 真正要注意的是：**棋盘底部若干行在 HUD 模式下常态不可见**（被状态条的不透明底色盖住，`857-860`），必须先往上拖才看得到；这是设计如此，不是 bug
- 未验证项见 H1

### 问题 3：折叠开合时对局状态会不会丢？有没有只在真机才触发的重建路径？

- **局面不丢**：`GameSession.controller` 是模块级单例（`GameSession.ets`），`dispose()`（1956-1964）只停表、不清引擎、不清 `dialog`/`customSpec`/`statsOpen`；重建后 `aboutToAppear`（75-105）走 `engine.rowCount > 0` 分支调 `resume()`（1988-1999），继续原局
- 计时：`dispose` 停表、`resume` 起表，中断的那几百毫秒（存档+图集重新加载）不计入
- 对话框/统计窗/自定义框：都存在控制器上，重建后由 `draw()` 重画，位置用新的画布尺寸重算（`dialogLayout`/`statsLayout`/`customLayout`）
- **只在真机触发的路径**：H2（窗口舞台销毁重建）、H3（换屏密度）、H4（保留缩放档）

### 问题 4：三个对话框的按钮在最小缩放档下会不会小于 48 设备像素？

- 「三个对话框」若是胜利框、失败框、统计窗：**在 Pura X Max 上不会**，缩放档 2，按钮高 52/54/54 设备像素（见 M1 的表）
- 但**代码层面没有兜底**：`computeDialogScale` 的下限 0.5（M1）会让按钮掉到 12~13 设备像素；触发条件是「画布窄到装不下」（分屏窄条 540 px 宽时统计窗 s=0.72，按钮高 19 px）
- 另有三个**始终**小于 48 的命中区：统计窗红叉 34 高、自定义框红叉 36x28、外观框的缩略图命中区是缩略图四周各留 4 参考像素（`WinDialog.ets` 的 hitButton），实际 64+8=72 参考像素 -> 144 设备像素（够大）
- 数字键盘的键 34x30 参考像素 -> 68x60 设备像素，够大

### 问题 5：哪些路径只在横屏/矮画布才走、模拟器从来没走过？

按「只有真机内屏横屏（画布 1644 高）才会进」的顺序排：

1. `hudActive=1` 的整条路径（`GameController.ets:352-365`、`857-860`、`937-939`）——标准局不会，需要 17 行以上的局（H1）
2. `clampPan` 里纵向 `overV>0` 的分支（`398-400`）——它只在 HUD 模式出现（H1）
3. 折叠导致的窗口舞台销毁重建 -> `loadContent` -> 新页面 -> `dispose`/`resume`（H2）
4. `onAreaChange` 触发的 `tryAttach`（`MinefieldCanvas.ets:146-151`）——模拟器旋转也可能触发，但换屏密度变化只有真机有（H3）
5. `userZoomed=true` 时折叠不改缩放档（`GameController.ets:300-305`）（H4）
6. `computeDialogScale` 的 `maxByHeight` 成为瓶颈——内屏 1644 高时五个框都还有余量（最小余量是失败框 `(1644-32)/288=5.6`），这一条在内屏**不会**成为瓶颈；真正会的是分屏窄条（M1）
7. `computeDialogScale` 落到非整数档——内屏被上限 2 封顶，不会；外屏的统计窗 1.84 会（与模拟器同病，L2）

---

## 6. 真机复测清单（按优先级）

1. 内屏横屏开 24 行自定义局 -> 确认 HUD=1：状态条贴底、两个计数器可见、上下拖到底时第一行与最后一行都完整可见、点状态条不会翻格子
2. 折叠开合各一次（内屏 -> 外屏 -> 内屏）-> 确认：局面/旗子/秒数/难度都没丢、对话框还开着且按钮还能点、秒数没有跳变
3. 外屏竖屏各开一个框（胜利框、统计窗、自定义框）-> 确认按钮都点得到、红叉点得到
4. 外屏横过来（如果允许）-> 确认布局与内屏一致
5. 分屏/悬浮窗（若系统支持）-> 打开统计窗与自定义框，确认按钮没有被缩到点不准（这是 M1 的兜底缺失暴露的地方）
6. 打开 hilog 看 `[GameController] 布局 ...` 这行：换屏后 `适配档n` 与 `当前档n` 是否符合预期，`HUD=` 是否符合棋盘大小

---

## 7. 处置结果（2026-11-02 晚）

这一节记的是**上面这些条目的实际处置**，全部在 **Mate X7 折叠屏模拟器**上
（`Emulator.exe -instance 'Mate X7' -foldedState open|half-open|close`）验证，
真机 Pura X Max 当时不在线。

| 条目 | 处置 | 证据 |
|---|---|---|
| **H3** 密度只在 `aboutToAppear` 取一次 | **已修**：改读**窗口所在屏**的密度（`window.getLastWindow()` → `displayId` → `display.getDisplayByIdSync(id).densityPixels`）；画布 `onAreaChange`（尺寸变化）也触发一次重取，密度变了就重算布局 | 折叠后布局日志从 2210×2208/n=5 变成 1080×2236/n=3 ✓ |
| **H2** 折叠开合会重建窗口舞台 | **部分修好**：Ability 里的 `onWindowStageChange` 方法**根本不会被调用**（UIAbility 没有这个回调 ✗ —— Codex 复审 P1 ✓）；换成 `window.on('windowSizeChange')` ✓，折叠时确实触发（日志「窗口尺寸变化」）✓ | `docs\verify\X7_folded_play.jpeg` ✓ |
| **H4** 折叠后保留用户手动缩放档 | **逻辑保留**（`layout()` 里 `if (!this.userZoomed)` 那条没动 ✓）：没手动缩放过时换屏按新的适配档重算 ✓；手动缩放过时保留原档 ✓。**手感要用户自己捏合验证**（模拟器没有多点触控 ✗） | 代码路径 + 布局日志 ✓ |
| **H1** HUD 模式在两个模拟器上没执行过 | **仍待真机**：24×30 在 Pura X Max 内屏（画布 2584×1644）会溢出 322 px 进 HUD ✓（算式见 `LAYOUT-MATRIX.md` §4.3.2.1 ✓）；Mate X7 / Mate 90 Pro 都装得下 ✗ → 模拟器出不了 HUD | `LAYOUT-MATRIX.md` §4.3.2.1 ✓ |
| **新发现（Codex 复审 P1）** | 「画布 `context.width` ÷ 组件 vp 宽」算密度是**错的** —— ArkUI 的 Canvas 2D 上下文整个坐标系都是 vp，这个比值恒等于 1（曾把画布画成 707×707 ✗） | 已改为读窗口所在屏的密度 ✓ |

### 7.1 折叠实测记录（Mate X7 模拟器）

| 时刻 | 屏幕 | 布局日志 |
|---|---|---|
| 展开 | 2210×2416 | 画布 2210×2208，适配档 n=5，unit=10，格边 180 px，棋盘原点 (295,167)，HUD=0 |
| 折叠（**不重启应用**） | 1080×2444 | 画布 **1080×2236**，适配档 **n=3**，unit=6，格边 **108 px**，棋盘原点 **(54,569)**，HUD=0 |

- **活的重排**：两次切换应用都没重启，日志直接变了 ✓
- **局面完整保留**：同样的「1」「2」、同样的雷、同样翻开的格子 ✓；计时继续走 ✓
- 折叠后状态条读数 **计时 3 / 雷数 10** ✓（用 `tools/sevenseg_read.py` 反解出来 ✓）
- 证据图：`docs\verify\X7_unfolded_play.jpeg`、`X7_folded_play.jpeg`、
  `X7_state_before.png`、`X7_state_after.png`、`X7_strip_after.png`

### 7.2 模拟器折叠的一个坑

`Emulator.exe -instance 'Mate X7' -foldedState close` 有时**只改了屏幕尺寸、
没把正在运行的窗口叫醒**（应用仍按旧尺寸画）。这时需要**重启一次应用**
才能让它在新屏上布局 ✓。判据看截图分辨率：
`snapshot_display` 的输出里 width/height 变了才算数 ✓。
