# WIN7-FEATURE-GAP.md —— 「真 Win7 扫雷有、本项目还没有或做错了」逐条清单

> 只读分析，未改动工程代码。
> 盘点日期：2026-10-31
> 本项目现状以 `C:\Users\19161\saolei\entry\src\main\ets\` 下的 `.ets` 为准（只读）。
> **引用约定**：代码位置一律写成**函数名 / 常量名**（如 `GameController.layout()`、
> `Theme.MIN_CELL_PX`），**不写行号** —— 盘点期间 `saolei` 工程一直在被并行修改
> （`GameController.ets` 当天从 37 879 B 涨到 60 000 B 以上），行号会漂移，函数名不会。
> 核对时请按函数名找。
> 无 emoji。
>
> **2026-10-31 收口**：当天 13:05 之后主线程又改了一批代码，本文已按今天的结论重新标注。
> 逐项状态见 **§2.1**（一张表看完 17 条），§3 各小节标题后也带了「今日状态」标注，
> §4 列出了还没裁决的 3 条疑似 + 1 条今天新出现的。
> 当天改了什么、依据是什么，逐条记在 **`docs\CHANGELOG-2026-10-31.md`**。

### 参考源码（只读）

| 代号 | 路径 | 说明 |
|---|---|---|
| **[Lmy]** | `C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\Minesweeper\` | Win7 风格 C++ 复刻（`utf8\` 子目录是 UTF-8 版） |
| **[QT]** | `C:\Users\19161\Desktop\minesweeper-refs\linux-minesweeper-main\src\` | Qt6 复刻，注释里大量写「the original does X」 |
| **[REV]** | `C:\Users\19161\Desktop\minesweeper-refs\ReversingMinesweeper-master\Minesweeper\` | 英文复刻，`resource.h` 有菜单 ID 表 |
| **[JPG]** | `C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\jpg\` | 复刻截图 |
| **[HELP]** | `C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png` | **微软自己**的 Win7 帮助窗口插图，版式的权威证据 |

---

## 1. 菜单结构逐项对照

### 1.1 三份菜单 ID 表

**[REV] `resource.h:27-42`**（英文复刻，最贴近真 Win7 的 ID 表）：

```
ID_MENUITEM_NEWGAME 510   ID_MENUITEM_EXIT 512
ID_MENUITEM_BEGINNER 521   ID_MENUITEM_INTERMEDIATE 522
ID_MENUITEM_EXPERT 523     ID_MENUITEM_CUSTOM 524
ID_MENUITEM_SOUND 526      ID_MENUITEM_MARKS 527
ID_MENUITEM_BEST_TIMES 528 ID_MENUITEM_COLOR 529
ID_MENUITEM_CONTENTS 590   ID_MENUITEM_SEARCH_FOR_HELP 591
ID_MENUITEM_USING_HELP 592 ID_MENUITEM_ABOUT 593
```

**[Lmy] `Resource.h`**（UTF-16LE，需用 `Encoding.Unicode` 读）：`ID_NEWGAME 32776`、`ID_STATISTICS 32778`、`ID_OPTION 32779`、`ID_HELP 32780`、`IDM_ABOUT 104`、`IDM_EXIT 105`、`IDD_OPTION 129`、`IDD_STATISTIC 142`、`IDD_WIN 141`、`IDD_LOSE 140`。
（`ID_HELP` / `ID_STATISTICS` / `ID_OPTION` 三个是**顶层菜单命令 ID**，说明 Lmy 把「统计信息」「设置」「帮助」做成了独立顶层项，不是「游戏」的子项。）

**[QT] `src/ui/MainWindow.cpp:132-151`**（把三者合起来的完整 Win7 菜单）：

```
Game:  &New Game(F2) | &Statistics(F4) &Options(F5) &Change Appearance(F7) | E&xit
Help:  &View Help(F1) | &About Minesweeper
```

### 1.2 本项目现状

`GameController.ets` 的 `buildMenu()`（约 940~965 行）：

```
游戏: 新建(F2) | 初级 中级 高级 自定义 标记(?) | 声音 | 最佳成绩 | 退出(X)
帮助: 关于扫雷(A)
```

### 1.3 对照表

| 真 Win7 菜单项 | 本项目 | 差异 | 工作量 |
|---|---|---|---|
| 游戏 → 新建(F2) | 有 | 快捷键 F2 **是否真的能触发**未验证（见 §4.10） | 小 |
| 游戏 → 初级/中级/高级 | 有，且带勾选 | 等价 | — |
| 游戏 → 自定义 | 有（`CustomField.ets`） | 等价 | — |
| 游戏 → **统计(F4)** | **缺**（只有菜单栏里的「最佳成绩」） | Win7 有独立的统计窗口，见 §3.7 | 中 |
| 游戏 → **选项(F5)** | **缺** | Win7 的选项窗口把难度/标记/声音/颜色/最佳成绩/重置记录收在一起，见 §3.8 | 大 |
| 游戏 → **颜色(C)(F7)** | **有**（commit `a2b635f`） | 见 §3.2（外观对话框：游戏样式 + 棋盘样式）。**中文名取自用户本人 Win7 的真名** | — |
| 游戏 → 标记(?) | 有 | **等价**：关闭后 `toggleMark` 只走「无→旗→无」两态（``MinesweeperEngine.toggleMark()``） | — |
| 游戏 → 声音 | 有 | 等价 | — |
| 游戏 → **最佳成绩** | 有（`openInfoDialog('best')`） | 缺「最多连胜/最多连败/当前连赢」和「重置」按钮，见 §3.7 | 中 |
| 游戏 → 退出 | 有 | — | — |
| 帮助 → **查看帮助(F1)** | **缺** | 见 §3.1 | 中 |
| 帮助 → 关于扫雷(A) | 有（`WinDialog.ets` 的 `aboutSpec`） | 等价 | — |
| （顶层）**统计** | 无独立项 | 与上面「统计(F4)」同一条 | — |

---

## 2. 结论速览：缺口清单（按工作量从小到大）

> **2026-10-31 更新**：下表新增「今日状态」列。逐条状态见 §2.1；详细结论在 §3 各小节标题后的标注里。
> 「已解决」= 本轮代码已改；「仍存在」= 今天没动；「故意差异」= 决定不做。

| # | 行为 | 工作量 | 是否必须补 | 今日状态 |
|---|---|---|---|---|
| 1 | 悬停高亮用了普通合成而不是**相加混合** | 小 | 必须（是 bug） | **已解决** |
| 2 | 状态条两个 LED **左右颠倒** + `face.png` 实为时钟不是笑脸 | 小 | 必须（是 bug） | **已解决** |
| 3 | **自定义局的成绩被记到了当前难度名下** | 小 | 必须（是 bug） | **已解决** |
| 4 | 「颜色(C)」外观对话框 + 绿色主题 | 中 | 可有可无（但性价比最高） | **已解决**（commit `a2b635f`） |
| 5 | **新开局的发牌动画**（1100 ms 逐格波浪淡入） | 中 | 可有可无 | **已解决** |
| 6 | **判负时其它雷逐个烧红的级联** | 中 | 可有可无 | **仍存在** |
| 7 | 洪泛开格的**涟漪淡出**动画 | 中 | 可有可无 | **已解决** |
| 8 | 统计窗口缺「连胜/连败」与「重置」 | 中 | 可有可无 | **已解决** |
| 9 | **独立帮助窗口(F1)** | 中 | 可有可无 | **已解决**（做成对话框，含原版插图） |
| 10 | 「选项(F5)」独立设置窗口 | 大 | 可有可无（菜单栏已覆盖大部分功能） | **故意差异** |
| 11 | 计时器/雷数用真**七段数码管** | 中 | 可有可无 | **已实现**（commit `a2b635f`） |

### 2.1 17 条逐项状态（2026-10-31 收口）

| § | 行为 | 状态 | 依据 / 说明 |
|---|---|---|---|
| 3.1 | 独立帮助窗口(F1) | **已解决**（做成画布对话框，但**含 Win7 原版插图**） | `WinDialog.helpSpec()` 584×280，左边放微软原版 `helpBoard.png`（256×192，整数倍放大 + 最近邻），右边 6 行中文说明，底部「确定」。菜单「帮助(H)」项已接线，**实测通过**（`CLICK-MATRIX-X7.md` 收尾补测第 35 项：帮助下拉正常展开两项 —— 帮助(H)、关于扫雷）。**不是**原版那种模型化可复用的帮助查看器，仍是对话框 —— 形态上算简化，但**视觉素材是原版的**。插图曾有一次没画出来（vp/设备像素换算方向写反），已修（commit `c130326`），实测见 `docs\verify\HELP_p90.jpeg` |
| 3.2 | 「颜色(C)」外观对话框 + 绿色主题 | **已解决** | 原版 Win7 扫雷的「游戏」菜单里有一项 **"Change Appearance"（F7）**，弹出对话框选**游戏样式**（扫雷 / 花园）与**棋盘样式**（银蓝 / 绿色）。本轮落地：菜单项在「最佳成绩」之后、「退出」之前；对话框 420×340 参考像素，两个分组框 + 四枚缩略图 + 置灰的「随机选择」复选框 + 确定/取消，**点「确定」才生效**（原版帮助原文 "Make your choices, and then click OK"）；绿色棋盘用 `greenSheet.png`，花园玩法用 `flowerGardenSheet.png` + 三段 `flowerLose*.wav`（按剩余雷数 ≤10 / ≤40 / 更多分段播）；**外观设置已写入 preferences**（`GameStats.saveStyle()` / `GameStats.load()`，代码层面已核对；**「重启后还在」没有实测记录**）。实现与版式见 `docs\APPEARANCE-DIALOG.md`（commit `a2b635f`） |
| 3.18 | 花园玩法（Flower Garden） | **已实现** | 随「颜色(C)」一起落地：`flowerGardenSheet.png`（花朵代替地雷的踩雷动画）+ 面板上的花朵图标 + 三段判负音效。**未验证**：判负瞬间的完整开花序列（本轮只验了图标与帧的位置）。**「随机选择游戏样式和棋盘」复选框按原版置灰不可点**（Linux 复刻同样未实现） |
| 3.3 | 判负后「其它雷逐个烧红」级联 | **仍存在** | 本轮只做了**踩到那一格**的 23 帧爆炸动画；「其它雷逐个烧红」的时序队列未做 |
| 3.4 | 胜利扫描条 + 逐雷拆解 | **已解决**（本来就不是缺口） | 已实现，参数与原版一致 |
| 3.5 | 首点 / 新开局的发牌动画 | **已解决** | `DealIn.ets`，1100ms 逐格弹起（commit `c2a7a5e`） |
| 3.6 | 洪泛开格的涟漪淡出 | **已解决** | `Ripple.ets`，切比雪夫方环分层、每圈 30ms、单格 150ms（commit `2cadec5`） |
| 3.7 | 统计 / 最佳成绩窗口 | **已解决**（4 个控件实测全部可用） | `StatsWindow.ets` 完整还原 `information.jpg`：左栏难度列表（可点选中）、中栏最佳时间（跟随切换）、右栏六项统计、底部关闭(C)/重置(R)、标题栏红叉（可点）。**实测通过**：左栏难度列表、标题栏红叉、关闭(C)、重置(R) **四个控件全部可用**，日志 `[Stats] 选中难度 1` / `[Stats] 点击关闭`。<br>注：补测一度把这 4 项全记为异常（B1），**2026-10-31 14:02 撤销** —— 是测试方坐标量偏 2 px（红叉命中区左边界 x=1699，点的是 1697），**不是应用缺陷**。见该报告异常 **C2** |
| 3.8 | 「选项(F5)」独立设置窗口 | **故意差异** | 功能上没缺口（难度四项 + 标记(?) + 声音 + 自定义 + 统计 + 重置都摊平在菜单栏里了），只是没有 Win7 那个「一个窗口装完」的形态。**决定不做** |
| 3.9 | 「重新开局」vs「重开同一盘」 | **已解决** | `restart()` 改成保留当前盘面参数（``GameController.restart()``，commit `8925f0e`）。**注意**：保留的是**盘面参数**（行列+雷数），**雷位仍会重新随机**；「同盘雷位重开」这条本身仍与 Win7 有差异，但 §3.9 关心的是「不要换成难度预设」，已达成 |
| 3.10 | 键盘快捷键 | **仍存在** | 手机没有物理键盘，F2/X/A 只是画在菜单右边的提示文字。本轮没接 `onKeyEvent` |
| 3.11 | 悬停高亮的混合模式 | **已解决** | 改成加法混合（commit `d21e2e9`） |
| 3.12 | 状态条左右顺序 + `face.png` 误标 | **已解决** | 状态条回退为 `[时钟][计时]…[雷数][雷图标]`（commit `d21e2e9`）；`RECT_FACE` 与 `rawfile/face.png` 已移除。**裁决依据见 `docs\STATUS-STRIP-VERDICT.md` 结论 A** |
| 3.13 | 自定义局是否记成绩 | **已解决** | 自定义局不进统计（commit `d21e2e9`）；`GameStats.record()` 被 `if (!this.customGame)` 包住，`isNewBest` 同样被抑制。独立核实见 `CUSTOM-DIALOG-AUDIT.md` §0 问题二 |
| 3.14 | 计时器 999 上限 / 雷数负数 | **已实现**（本来就不是缺口） | 保持 |
| 3.15 | 和弦的细节 | **仍存在（疑似）** | 和弦引爆（旗插错）那一路仍没有爆炸音效，`Sound.BOMB_START` 只在 `tap()` 里播。本轮没动 |
| 3.16 | 问号格被翻开 / 插旗又取消 | **已实现**（本来就不是缺口） | 保持；音效差异仍**无证据**，不作缺口 |
| 3.17-1 | 七段数码管显示雷数/计时 | **已实现** | 见下面 §2.2 |
| 3.17-2 | 鼠标移出按下格取消待开的格 | **故意差异** | 触屏为主，基本不适用 |
| 3.17-3 | 点一下跳过爆炸级联 | **仍存在** | 本轮的爆炸动画仍是「播完才弹框」，不能中途跳过。可有可无 |

### 2.2 关于「七段数码管」—— 上午的判断错了两次，现在才对

这一条在一天里被**判了两次**，两个方向都判错过，记下来免得再犯：

**第一次（上午）判「不是差距」**，理由两条：
(a) 参考实现 `linux-minesweeper/src/ui/BoardWidget.cpp:552-559` 就是
`setBold(true)` + `setPen(Qt::white)` + `drawText` 居中，注释写「原版配置里的 PanelLabelTextColor」，
本项目画法与之逐项一致；
(b) 素材里没有七段数码管 —— `otherSheet.png` 存储像素
`x 1..252, y 1953..2014` 与 `x 255..450, y 1953..2014` 实测是**两片纯灰渐变的窗口边框片**
（此前把它当成七段笔段是读图错误，`docs\ASSET-AUDIT.md` 里那两处已更正）。

**第二条 (b) 是对的**（那块区域确实没有笔段素材）；**第一条 (a) 是错的** ——
**参考实现怎么画，只能说明那一份复刻怎么画，不能证明原版长什么样。**

**第二次（19:00 后）判「确实是七段」**：**原版的两个计数器确实是七段数码管**，
权威证据是**微软原图 `win7-assets\images\helpBoard.png`** 的状态条里「18」「40」
**逐像素反推**（`docs\SEVEN-SEG-COUNTER.md` 有完整几何表、逐段坐标与置信度标注）。

→ **结论改成：素材里没有笔段，不是「所以用粗体白字」，而是「所以要自己画」。**
本轮已按 `SEVEN-SEG-COUNTER.md` 的几何**用 Canvas 画出来**（`common\SevenSeg.ets`，
接线在 `GameController.drawStatusStrip()`，commit `a2b635f`）：

| 项 | 值 |
|---|---|
| 面板 / 槽位 | 40×21 参考像素，**3 槽**，槽距 **13** |
| 对齐 | **右对齐、不补零** |
| 负号 | 独立的一段（中段 g），占紧挨数字左边那一槽 |
| 显示区间 | [-99, 999]，超出钳到端点 |
| 亮段颜色 | `#FAFAFC` |
| 「1」的形状 | 带原版的**衬线小旗 + 底横**（第 8 段 `SEG_FLAG`，掩码 `0x0E`） |
| 槽位起点 | 面板内 **x = 0**（不是 XP 的 x = 1）—— 面板精灵右缘有 2 像素斜角高光，数字贴上去会糊成一片 |

> **模拟器上的实拍证据**：docs\verify\V4P90_strip_right.png —— 雷数「99」的
> **七段字形清晰可见**（上横 / 上下竖 / 中横 / 下横逐段分明），与旁边银色尖刺地雷图标同框。

**七段渲染器本身也过了对抗性复审**：Codex 裁定 **BLOCKER**（3 个 P1 + 1 个 P2），
已按意见修完（数字格改成 12×16 避开面板边框、可达到的负数钳到区间端点、
`Infinity` 防护、颜色统计改成逐连通域取核心像素）。复审原文：
`docs\verify\sevenseg-review\review.txt`。

→ **这一条现在是「已实现」，不再是差距。**

### 2.3 四条要特别记住的「不是 bug」

| 现象 | 结论 | 依据 |
|---|---|---|
| 状态条上时钟 / 雷图标**点不动** | **正确行为**，原版就是装饰 | `docs\STATUS-STRIP-VERDICT.md` 结论 A；`BoardWidget.cpp:783-813` 只对棋盘格做命中测试 |
| 状态条在**超宽盘面**上两端跑出屏幕 | **这是我们自己的 bug，已修**（原版没有这个问题，因为原版窗口从不超宽） | 30 列的局在窄屏上棋盘比屏宽 837~880 px，旧实现把时钟与雷数**钉在棋盘两端** → 两端都在屏外 440 px，默认视图里既看不到用了多久、也看不到还剩几颗雷。现改为**两端贴住屏幕边**。实测截图 `docs\verify\V4P90_strip_left.png` / `V4P90_strip_right.png` / `V4P90_strip_fixed.png` |
| 首点**必开一片空地**（角落≥4/中心≥9） | **故意差异**，产品决定 | `docs\SPEC.md` §3.1；真 Win7 是「首点安全但可能开出一个数字」 |
| **没有笑脸按钮** | **与原版一致，不是缺口** | **2026-10-31 用户本人确认「Win7 没有笑脸」**（他本人用过 Win7 扫雷）。与「四张图集里查不到笑脸素材」的三方核查结论相互印证。**我们也没做** |

> **「计数器用粗体白字不是降级」那条已撤回**，理由见 §2.2。现在状态条上是七段数码管。

### 2.4 结束对话框：**存在性已确证**，但**按钮文案仍未确证**

> **2026-10-31，lead 直接向用户确认**（用户本人用过 Win7 扫雷）——
> 这比任何二手复刻都权威。

| 层面 | 状态 | 说明 |
|---|---|---|
| **判负后会不会弹对话框** | **已确证** | **Win7 判负后确实会弹一个对话框。** 所以我们保留现在的「结束对话框」**是对的** —— **不要**把它列成「与原版的差异」 |
| **对话框里那几个按钮叫什么** | **仍未确证** | 我们现在的文案（「退出(X) / 换个难度(D) / 再玩一局(P)」，胜利框是「再玩一局(P) / 退出(Q)」）是照着 **Lmy 那个克隆的 `loss.jpg`** 做的，而 **Lmy 的对话框是它自己设计的**（它自己的菜单也一样，不等于原版）。原版到底叫什么、怎么排，**目前没有证据** |

**已知的、有意为之的一处差异**：失败框中间那个按钮，原版是「重新开始这个游戏(R)」，
与我们右边的「再玩一局(P)」功能重复，手机端改成了「换个难度(D)」
（`WinDialog.ets` 的注释里写明这是有意改动）。

> **用户手上已经没有 Win7 了**（没法再截图）。
> 所以「原版对话框到底长什么样」这件事**只能靠素材与复刻互证**，
> 不要写「等用户提供截图」。

### 2.5 自定义对话框右边那块画布数字键盘 —— **已裁决：有意增强，不是差距**

`docs\CUSTOM-DIALOG-VERDICT.md`（2026-10-31，custom-agent 的裁决）的结论：

> **原版 Win7 的自定义对话框里根本没有数字键盘。** 它的对话框只有三个编辑框
> （高度 / 宽度 / 雷数），没有任何按键控件，输入靠**系统键盘**（桌面版是物理键盘）。
> 所以「键盘该内嵌在框内还是外挂」这个问题**在保真层面没有对照物**。

**四条独立证据**（见该报告 §1.2）：最强的一条是**原版 XP 二进制逆向重建**
（`ReversingMinesweeper`）—— `Minesweeper/resource.h:67-76` 的自定义对话框资源 ID 只有
`OK` / `CANCEL` / `HEIGHT` / `WIDTH` / `MINES` 三个编辑框，**没有按键控件 ID**。

**我们外挂一块画布自绘键盘的理由**（该报告 §1.4 给 SPEC 的措辞）：

> **有意增强（偏离原版）**：本移植在对话框右侧外挂一块画布自绘的 3 列数字键盘
> （11 键：1-9 / 退格 / 0），理由是：**鸿蒙的 Canvas 无法弹出系统软键盘**，
> 而弹 IME 会破坏「像素级复刻的模态对话框」这一前提；
> 自绘键盘同时让「输入」与「绘制」共用同一套坐标，命中测试不会跑偏。
> **该键盘不是原版元素，复刻时不得据此推断原版版式。**

**外挂 vs 内嵌的取舍**：外挂 = 框 280 + 间隙 12 + 键盘 110 = **402 参考像素**。
原版那个小框根本放不下键盘，外挂是唯一能把两者都放大的办法；
改成内嵌框宽要涨到 402，桌面版那个「小方框」的比例就完全不像原版了。

**会不会裁切**：**不会**。1280 宽屏上 scale = 2，总宽 **804 设备像素**，单侧留白 **238 像素**。
唯一会裁的条件是画布宽 **< 434 设备像素**（158 vp @2.75）——
**任何真机（含分屏窄条 540px）都到不了这个宽度**。
为从根上消除裁切，`computeDialogScale` 的下限已从 1 放宽到 **0.5**（commit `f261aa9`）。

> **另一条曾被误传的线索**：「真实 Win7 中文版的自定义对话框带一整块数字键盘」这一说法，
> 在本机全部离线证据里**零支持**（穷举清单见该报告 §1.3）。拿到真机截图之前，
> 不应把它当作规格。

---

## 3. 逐条详情

### 3.1 独立帮助窗口(F1) —— 缺 ｜ **今日状态：已解决（做成画布对话框）**

**原版确切表现**
- **[QT] `MainWindow.cpp:148`**：`help->addAction(tr("&View Help"), QKeySequence(Qt::Key_F1), ...)`，即「帮助 → 查看帮助(F1)」打开一个**模型化、可复用的帮助查看器**（`MainWindow.cpp:346` 注释：「Modeless and reused, like the original help viewer: F1 raises the ...」）。
- **[Lmy] `Resource.h`** 有 `ID_HELP 32780`（顶层命令）。
- **[HELP] `helpBoard.png`（256×192）** 就是这个帮助窗口的插图本体：上半是蓝色棋盘（若干带数字的格子），下半是状态条 `[圆钮][LED "18"] …… [LED "-40"][地雷图标]`。放大后左边那个圆钮**是带指针的时钟**，右边那个圆钮**是地雷**。

**本项目现状**
- 菜单「帮助」下只有「关于扫雷」（`GameController.ets` `buildMenu()` 约 961~965 行）。
- 工程里**没有**任何帮助窗口/帮助页代码。

**工作量估计：中（30~120 行）**
- 素材侧：`helpBoard.png` 可以直接当帮助窗口的插图（1:1，256×192）。
- 代码侧：新增一个 `HelpDialog.ets`（画一张插图 + 滚动/关闭），菜单加一条 `{ id: 'help', label: '查看帮助', accelerator: 'F1' }`，`Index.ets` 的 `onMenuAction` 加一个分支。约 60~100 行。

---

### 3.2 「颜色(C)」外观对话框 + 绿色主题 ｜ **今日状态：已实现**（commit `a2b635f`）

**原版确切表现**
- **[REV] `resource.h:36`**：`#define ID_MENUITEM_COLOR 529`。
- **[QT] `MainWindow.cpp:142`**：`game->addAction(tr("&Change Appearance"), QKeySequence(Qt::Key_F7), this, &MainWindow::showAppearance);`
- **[QT] `AppearanceDialog.cpp:151-164`**：「外观」对话框有两组单选图示：
  - **Select Game Style**：`thumbMines.png`（Minesweeper）/ `thumbFlowers.png`（Flower Garden）
  - **Select Board**：`thumbBlue.png`（Silver and Blue）/ `thumbGreen.png`（Green）
- **[QT] `MainWindow.cpp:187-189`**：配色是一个持久化设置（`boardStyle` = blue|green），随时可切。

**本项目现状（19:00 后）**

- 菜单里**已有**「颜色(C)」项，位置在「最佳成绩」之后、「退出」之前（倒数第二项，F7）。
- 新增 `common\Appearance.ets`（画布自绘的外观对话框）：420×340 参考像素，
  两个分组框 + 四枚缩略图 + 选中蓝框 + 置灰的「随机选择游戏样式和棋盘」复选框 + 确定/取消。
- **点「确定」才生效**（原版帮助原文 "Make your choices, and then click OK"），不是即时生效。
- `Theme.ets` 加了 `BoardStyle`，`SpriteAtlas.ets` 按主题选图集，
  `rawfile/` 里已有 `greenSheet.png` / `thumbBlue.png` / `thumbGreen.png` /
  `thumbMines.png` / `thumbFlowers.png` / `flowerGardenSheet.png`。
- **外观设置已写入 preferences**（原版行为；存 `GameStats.saveStyle()` / `GameStats.load()` 里的
  `boardStyle` / `gameStyle` 两个键，代码层面已核对）。
> **但「重启后还在」这一步没有实测记录** —— `docs\APPEARANCE-DIALOG.md` §7 的六步实测里没有这一步。
- 花园玩法：花朵踩雷动画 + 面板花朵图标 + 三段 `flowerLose*.wav`
  （按**剩余雷数** ≤10 / ≤40 / 更多分段播）。

**中文名「颜色(C)」的来源**：lead 于 2026-10-31 直接问过用户，
用户本人 Win7 的「游戏(G)」菜单里**确实有「颜色(C)」这一项** ——
这是关于「原版到底有没有这一项、叫什么」的**唯一权威来源**。
代码里这个字串是 `Appearance.ets` 的 `MENU_APPEARANCE_LABEL`，要改写法只改这一行。
（`docs\APPEARANCE-DIALOG.md` §1.1 记的还是占位名「外观(C)」与「未确证」，那是定名前的版本。）

**素材侧结论（本次盘点实测，见 `ASSET-AUDIT.md` §2.1）**
- `blueSheet.png` 与 `greenSheet.png` **同为 2034×1206，逐区域同构**。
- 差异**只在**：砖块渐变区（px `0..900, 0..1044`，99.3 % 像素不同）、已翻开凹陷格区（px `1000..1900`，浅色偏色）、计数器面板（px `0..120, 1155..1206`）。
- **数字 1..8、旗、问号、高亮、红叉、阴影条全部逐字节相同**（差异 0 %）。
- **唯一必须改的坐标**：胜利拆雷动画的基址 —— 蓝色在逻辑 `x=0`，绿色在逻辑 `x=364`（`otherSheet.png` 存储像素 `x 728..1455`）。
- 现成的预览图：`thumbBlue.png` / `thumbGreen.png`（各 109×109，1:1 原图，6×6 方砖马赛克）。

**实测通过**（Mate X7 内屏，见 `docs\APPEARANCE-DIALOG.md` §7）：
菜单项能开（`[Menu] 菜单动作 appearance`）→ 点「绿色」缩略图选中框移动 →
点「确定」棋盘变绿（绿色像素 43 589 → 2 304 302）→ 点「取消」棋盘保持不变 →
选「花园」后剩余雷数旁的图标变成白雏菊。

> **附注（这条已过时）**：早先这里写「花园区（Flower Garden）**不建议做**」——
> **本轮做了**，见上。理由当时是「与『扫雷』定位不符」，但原版本来就有这个玩法。

---

### 3.3 判负后「其它雷逐个烧红」—— 缺 ｜ **今日状态：仍存在**

**原版确切表现**
- **[Lmy] `utf8/Minesweeper.cpp:1800-1841` `mineBomb()`**：
  1. 先把**所有雷**一次性画出来（1805~1813 行）；
  2. 踩中的那颗播 `IDR_WAVE4`（爆炸开始音 = `mineBombStart.wav`），然后 **25 帧 × `Sleep(23)` = 575 ms**（1819~1825 行）；
  3. `getMineDevelopNo(no, mapInfo, 25, row, col, count)` 算出**其它雷逐个爆炸的顺序数组**（1827 行），同时播 `IDR_WAVE5` 且 `SND_LOOP`（循环爆炸中音 = `mineBombRun.wav`）；
  4. 按该顺序逐个把雷画成爆炸态，每步 `speed(150, ...)` 延时（1833~1838 行）；
  5. 最后播 `IDR_WAVE6`（爆炸结束音 = `mineBombEnd.wav`）。
- **[JPG] `exploding.jpg`** 正是这个级联进行中的画面：雷已经全部露出，右半边散布着深色的爆炸精灵，且**越靠近爆炸源越密、越远越稀**。

**本项目现状**
- ``MinesweeperEngine.lose()`` `lose()`：**一次性**把所有未插旗的雷 `revealed = true`，**没有逐个烧红的时序**。
- `GameController.ets` 约 619~621 行：踩雷后 `Anim.startTrip(cell)` 播**那一格**的 23 帧爆炸动画（约 619 行）。
- 音效三段时序**已做对**：`BOMB_START` → 575 ms → `BOMB_RUN` → 3949 ms → `BOMB_END`（`GameController.ets` 约 700~710 行 `playBombTail()`）。

**工作量估计：中（30~120 行）**
- 需要一个「按到爆炸源的距离/环带排序的逐格爆炸队列」+ 一个 25 帧/雷的爆炸态绘制（素材够：踩雷帧是 23 帧 57×57 逻辑，`otherSheet` 逻辑 `728 + 59*(f%3), 59*(f//3)`）。
- 估计 60~100 行。

---

### 3.4 胜利后的扫描条 + 逐雷拆解 —— **已实现（不算缺口）** ｜ **今日状态：已解决**

**原版确切表现**
- **[QT] `BoardWidget.cpp:226-254` `playWin()`**：`kScanTicks = 3000/30`（**扫描条自下而上扫过棋盘 3 秒**），每颗雷的拆解光束在扫描条**扫到它那一行**时发射：`start = kScanTicks * (rows - r) / (rows + 1)`，光束本身 `kDisarmTicks = 2000/30`（**2 秒**）。
- **[QT] `Theme.h:146-157`**：`disarmFrame`（38 帧，`50×150` 逻辑，7 帧/行）、`kDisarmOffset{-18,-69}`、`kScanBar{0,912,275,62}`。

**本项目现状：已实现，且逐帧参数与原版一致**
- `Anim.ets`：已把爆炸帧改成**原版 23 帧**（`EXPLODE_FRAMES=23`，步距 59），并新增胜利动画：`DISARM_FRAMES=38`、`DISARM_FRAME_MS=2000/38`、`SWEEP_MS=3000`、`SCAN_BAR=[0,912,275,62]`、`startWin()`、`beamFrame()`。
- `GameController.ets`：`startWinSweep()`（约 645~664 行）按行算每颗雷的起始时刻并调 `Anim.startWin(cells, times)`；约 670~676 行用 `Anim.winElapsed / Anim.SWEEP_MS` 算扫描条进度。
- **判定：不是缺口。**（绿色主题已实现 —— commit `a2b635f` 把胜利拆雷动画的基址
  从写死蓝色改成按 `BoardStyle` 取：蓝 0 / 绿 364。）

---

### 3.5 首点 / 新开局的发牌动画 —— 缺 ｜ **今日状态：已解决**

**原版确切表现**
- **[Lmy] `utf8/Minesweeper.cpp:1495-1508`**：
  ```cpp
  int *ptemp1 = getFirstPaintNo(row, col);   // 初始化动画贴图块序列数组
  if (optionFlag & OF_DRAW && optionFlag & OF_SOUND)
      PlaySound(MAKEINTRESOURCE(IDR_WAVE1), ...);   // = firstPaint.wav
  for (int i = 0; i < brickNumber; i++) {
      LightShadow(hdc, ptemp1[i]/col, ptemp1[i]%col, hdcMem, 4, 0);
      speed((int)(1100.0 / (row * col)), NULL, 0);    // 每格延时
  }
  ```
  → **总时长 1100 ms**（`1100.0 / (rows*cols)` ms × 格数），**逐格绘制**，绘制顺序由 `getFirstPaintNo()` 给出。
- **[QT] `BoardWidget.cpp:24`**：`constexpr int kIntroMs = 700;  // deal-in wave spread; Win7's 1100ms drags` —— Qt 复刻把它缩到 700 ms，并注明 **Win7 是 1100 ms**。
- **[QT] `BoardWidget.cpp:130-148` `playIntro()`**：每一格按「到最近角的对角波」计算出场时刻，**四角发出的波在中间汇合**（`getFirstPaintNo()` 的形状）。
- **[QT] `MainWindow.cpp:211, 222`**：`playIntro()` 是在 **`newGame()` / `restartGame()`** 时播的 —— 即**新开局发牌**，不是首点。
- **[JPG] `initializing.jpg`**（615×408）就是发牌动画进行中的画面：蓝棋盘上能看到**从四角向中间推进的同心波**，波前方的格子是浅色的，波后方是深蓝的。

**本项目现状**
- `Anim.ets` 只有「踩雷爆炸」和「胜利拆雷」两组动画，**没有 intro / 发牌动画**。
- `GameController.startNewGame()`（约 153~172 行）只调 `SoundPlayer.play(Sound.GAME_START)`。
- `Sound.FIRST_PAINT`（`firstPaint.wav`）常量在 `SoundPlayer.ets` 里定义了，但**只在首点开格时播**（`GameController.ets` 约 536 行 `SoundPlayer.play(Sound.FIRST_PAINT)`），**没有动画**。
- **可疑**：真 Win7 的 `firstPaint.wav` 是**发牌动画的配乐**（`IDR_WAVE1` 在发牌时播），而项目把它挂在「首点开格」上。项目用的是 `gameStart.wav` 放在 `startNewGame()`。**这两条音效的位置疑似与原版对调**，标记为**疑似**，建议核对。

**工作量估计：中（30~120 行）**
- 逐格淡入需要 per-cell 的 alpha 淡入（`Theme.ets` 已有 `normalTileRect` / `pressedTileRect`，可用 `ctx.globalAlpha` 实现淡入）。
- 波浪时刻按「到最近角的对角距离」算，与 `[QT] playIntro()` 同款算法，约 60~100 行。

---

### 3.6 洪泛开格的涟漪淡出 —— 缺 ｜ **今日状态：已解决**

**原版确切表现**
- **[QT] `BoardWidget.cpp:26-37`**：
  ```cpp
  constexpr int kRippleStagger = 1;             // 一 tick 推进一格
  constexpr int kRippleFadeTicks = 150 / kTickMs; // 快速 alpha 淡出
  constexpr int kIntroFadeTicks = 300 / kTickMs;
  ```
  注释：开格是「从点击点向外一圈圈融化」，每格到的时候用 `animationAlphaQuickFadeOut` 的形状做一次快速 alpha 淡出；**开格数 < 6 时就直接 pop，不做动画**（`BoardWidget.cpp:271` 「small opens just pop, like the original」）。
- 开格的**顺序**由引擎给出：**[QT] `Board.cpp:109-132` `floodReveal()`** 用**广度优先**，所以 `order` 是从点击点向外一圈圈扩散的。

**本项目现状**
- `MinesweeperEngine.floodReveal()` 用队列广度优先（`MinesweeperEngine.ets` 约 460~486 行），**顺序天然符合**，但结果是一次性画出来的，**没有逐格淡出**。
- `GameController.tap()` 只按 `outcome.opened.length > 1` 决定播 `TILE_MULTIPLE` 还是 `TILE_SINGLE`。

**工作量估计：中（30~120 行）**
- 引擎已给出顺序，只需把 `opened` 顺序传给 Anim，按 ring 距离算每格的淡出起始时刻，约 40~70 行。

---

### 3.7 统计/最佳成绩窗口 —— 部分缺 ｜ **今日状态：已解决**

**原版确切表现**
- **[JPG] `information.jpg`（702×254）** 就是这个窗口的截图，标题「扫雷统计信息」，布局：
  - 左：级别列表（初级/中级/高级，当前项高亮蓝）
  - 中：「最佳时间」列（时间值 + 日期，如 `17` + `Sat Nov 28 23:94:41 2015`）
  - 右：`已玩游戏: 3`、`已胜游戏: 1`、`获胜率: 33%`、**`最多连胜: 1`**、**`最多连败: 2`**、**`当前连赢: 1`**
  - 底：`关闭(C)`、`重置(R)`
- **[Lmy] `Resource.h`**：`IDD_STATISTIC 142`；**[REV] `resource.h`**：`ID_DIALOG_WINNERS 700` + `ID_DIALOG_WINNERS_BTN_RESET_SCORES 707`（**有重置按钮**）。

**本项目现状**
- `GameStats.ets` 只存：`played`、`won`、`best_<难度>`、`bestDate_<难度>`（``GameStats` 的连胜/连败字段`）。
- **没有**：连胜/连败/当前连赢的统计，**也没有「重置记录」按钮**。
- `GameController.openInfoDialog('best')`（约 800 行附近）画的行是 `难度 + 最佳时间 + 日期` 三列 + `played/won/percent`。

**工作量估计：中（30~120 行）**
- `GameStats` 加 `maxWinStreak / maxLoseStreak / currentWinStreak` 三个字段与更新逻辑（约 25 行），`WinDialog.bestSpec` 加三行显示（约 15 行），加「重置」按钮与清除存档（约 20 行）。

---

### 3.8 「选项(F5)」独立设置窗口 —— 缺 ｜ **今日状态：故意差异（决定不做）**

**原版确切表现**
- **[QT] `MainWindow.cpp:140`**：`game->addAction(tr("&Options"), QKeySequence(Qt::Key_F5), this, &MainWindow::showOptions);`
- **[QT] `OptionsDialog.cpp`** + `MainWindow.cpp:181-185`：选项对话框管 `questionMarks` / `sounds` / `animations` 三个开关，以及难度。
- **[Lmy] `Resource.h`**：`IDD_OPTION 129`、`ID_OPTION 32779`，且 `Resource.h` 里有 `IDC_CHECK1..IDC_CHECK6`（6 个复选框）、`IDC_JUNIOR/MEDIATE/SENIOR/USERDEFINED`、`IDC_EDIT_HEIGHT/WIDTH/COUNT` —— 说明 Lmy 的选项窗口同时塞了**难度单选 + 自定义高度/宽/雷数 + 多个复选框 + 最佳成绩列表 + 重置**。

**本项目现状**
- 没有独立的选项窗口；这些开关被摊平到菜单栏里（难度四项、`标记(?)`、`声音`）加上「自定义」对话框（`CustomField.ets`）。
- **功能上没有缺口，只是没有 Win7 那个「一个窗口装完」的形态**。
- 另外 `[QT] MainWindow.cpp:184` 还有一个 `m_animations` 开关（**动画总开关**），本项目没有。

**工作量估计：大（> 120 行）**
- 若要做成一个 Win7 形态的选项窗口（含难度单选、标记/声音/动画三个复选框、自定义字段、最佳成绩列表、重置），约 150~250 行。
- **性价比低**：菜单栏已经覆盖了除「动画开关」「重置记录」以外的全部功能。

---

### 3.9 「重新开局」 vs 「重开同一盘」 —— 疑似有差异 ｜ **今日状态：已解决（保留盘面参数）**

**原版确切表现**
- **[QT] `MainWindow.cpp:204-225`** 把两者分开：
  - `newGame()` → `m_board->reset(...)` → **重新布雷**
  - `restartGame()` → `m_board->restart()` → **同一盘雷位重开**（`Board.cpp:24-39` 只清 `revealed/exploded/misflagged/mark`，**雷位不变**）
- 真 Win7 结束对话框里的「再玩一局」是**同一盘雷位重开**。

**本项目现状**
- `GameController.restart()`（约 142~145 行）调 `startNewGame(cfg.rows, cfg.cols, cfg.mines)` → `engine.reset()` → **重新布雷**。
- 自定义局走 `customActionAt()` 的 `'ok'` 分支，也走 `startNewGame()`。

**判定**：**疑似**与 Win7 不一致。「再玩一局」在真 Win7 是同盘重来（可以拿更好的成绩），项目是重新随机。差异不大，但影响「最佳成绩」的可比性。
**工作量估计：小（< 30 行）** —— 引擎加一个 `restartSameLayout()`，保留布雷结果。

---

### 3.10 键盘快捷键 —— 疑似未接线 ｜ **今日状态：仍存在**

**原版确切表现**
- **[QT] `MainWindow.cpp:135-150`**：F2 新建、F4 统计、F5 选项、F7 外观、F1 帮助，全部是菜单项上的 `QKeySequence`。
- **[REV] `resource.h:20-21`**：`#define ID_ACCELERATORS 501`（加速键表）。

**本项目现状**
- 菜单项上标了快捷键文字（`buildMenu()` 里 `accelerator: 'F2'` / `'X'` / `'A'`），但**那是画在菜单右边的提示文字**。
- `Index.ets` 只接了 `this.controller.onMenuAction = (action: string) => {...}`（``Index.ets` 的 `onMenuAction` 回调`）这一条回调；`grep` 全 `entry/src/main/ets` **没有找到任何 key/keyDown/keyEvent 处理**。
- → **F2 / X / A 的提示在界面上写着，但很可能按了没反应。**

**判定**：**疑似**未接线（未找到键盘事件处理代码）。
**工作量估计：小（< 30 行）** —— 页面接 `onKeyEvent`，把 F2 映射到 `new`、A 映射到 `about`。

---

### 3.11 悬停高亮的混合模式 —— **是 bug** ｜ **今日状态：已解决**

**原版确切表现**
- **[QT] `Theme.h:86-87`**：「The hilite is additive: the original engine **adds** it onto the hovered tile, which is what makes hover glow.」
- **[QT] `BoardWidget.cpp:622`**：「The hover glow is **additive**, like the original engine」。
- 素材侧实测：`blueSheet.png` 的 `RECT_HILITE`（逻辑 `[440,560,18,18]` → 存储像素 `880..915, 1120..1155`）是一块 **100 % 不透明**的深青灰方块（平均 RGB ≈ 32,64,63）。

**本项目现状**
- ``Theme.RECT_HILITE`` 的注释已经写明「悬停高亮（**相加混合**）」。
- 但 `GameController.drawBoard()`（约 445~447 行）用的是普通 `this.atlas.drawLogical(ctx, this.atlas.boardSheet, RECT_HILITE, x, y, u);` —— **普通 alpha 合成**，没有设置加法混合。
- 后果：因为那块方块 100 % 不透明，普通合成会把整格砖块**整个涂成深青灰**；原版是**加法**，表现为砖块上浮起一层微亮的高光。

**判定**：**这是 bug**，注释与实现不一致。
**工作量估计：小（< 30 行）** —— Canvas 2D 里把 `globalCompositeOperation` 设为 `'lighter'`（或 `'screen'`）再画这一块即可；顺带确认 `RECT_HILITE` 的 alpha 语义。

---

### 3.12 状态条左右顺序 —— **是 bug（且 `face.png` 被误标为笑脸）** ｜ **今日状态：已解决**

**原版确切表现（两处独立证据）**
- **[HELP] `helpBoard.png`（微软自己的帮助窗口插图）** 底部状态条放大后是：
  ```
  [ 圆钮A ][ LED "18" ]  ············  [ LED "-40" ][ 圆钮B ]
  ```
  - **圆钮A = 时钟**（放大 14 倍可见钟面与指针，见 `docs/audit_helpboard_lefticon.png`）
  - **圆钮B = 地雷**（银圆钮装雷，见 `docs/audit_helpboard_righticon.png`）
  - 数字语义：左边是 **18**（只能是计时秒数），右边是 **-40**（只能是雷数计数，插旗插多了）→ **左 = 计时 + 时钟，右 = 雷数 + 地雷图标**。
- **[JPG] `exploding.jpg`**（Lmy 复刻整窗截图）底部同样是 `[时钟][LED "1"] ····· [LED "99"][地雷图标]`，与上式一致。
- **[QT] `BoardWidget.cpp:522`**：「The status strip in the **bottom border**, laid out like the original's ...」

**本项目现状**
- `GameController.drawStatusStrip()`（约 464~497 行）：
  - 左端：`face.png`（`RECT_FACE`）+ **雷数**面板
  - 右端：**计时**面板 + `RECT_PANEL_MINE`（地雷图标）
- ``Theme.tripRect()`` 把 `rawfile/face.png` 注释成「**笑脸按钮**（从真 Win7 素材 helpBoard.png 的帮助插图里抠出来的 14×14 原图）」，并写「真 Win7 的状态条顺序见 SPEC §5.5：**左侧 [笑脸][雷数面板] …… [计时面板][雷图标]**」。
- **但那个抠出来的图是时钟，不是笑脸**（见 `docs/audit_helpboard_lefticon.png`）。
- 净效果：项目画出的是 `[时钟][雷数LED] ····· [计时LED][地雷图标]` —— **两个 LED 的左右位置与真 Win7 相反**。

**判定**：**这是 bug**。两种改法任选：
- (a) 改成 `[时钟][计时LED] ····· [雷数LED][地雷图标]`：把 `face.png` 挪到右边靠计时器，或直接用 `otherSheet` 的 `RECT_CLOCK`（项目已有），并把两个 LED 面板对调。**约 10~20 行。**
- (b) 保持项目现状但改注释和命名（承认这是 Lmy 复刻的版式）。**约 5 行。**
- 建议同时把 `face.png` 改名成 `clock.png`、把 `RECT_FACE` 改成 `RECT_CLOCK_HELP`，避免继续误导。

**工作量估计：小（< 30 行）**

**附：笑脸表情不是缺口。** 真 Win7 的这套素材里**没有笑脸精灵** —— `minesweeperSheet.png` 只有 2 个精灵（面板雷钮 `[0,0,25,25]` 与裸雷 `[27,0,18,18]`），`otherSheet.png` 与 `Minesweeper.bmp` 里也没有。**[HELP] 的状态条里同样没有笑脸**（只有时钟和地雷两个圆钮）。
→ 「笑脸随状态变化（惊讶/死亡/戴墨镜）」在**这套素材里无据可依**，**不应作为缺口补**。
  **2026-10-31 用户本人确认「Win7 没有笑脸」** —— 与素材侧的三方核查结论相互印证。

---

### 3.13 自定义局是否记成绩 —— 项目**记错了** ｜ **今日状态：已解决**

**原版确切表现**
- **[QT] `MainWindow.cpp:236-238`**：
  ```cpp
  // Custom games are not recorded, matching Windows 7.
  if (m_difficulty.id != QLatin1String("custom"))
      m_lastRecord = Stats::recordGame(m_difficulty.id, won, m_seconds);
  ```
- **[QT] `MainWindow.cpp:262`**：自定义局的结束对话框里，`played/won/percent` 也用**空统计**（`preset ? Stats::load(...) : Stats::Data()`）。

**本项目现状**
- ``GameStats.saveStyle()`` `levels()` 只返回 `['初级','中级','高级']` → 最好成绩不记自定义局，**这一半是对的**。
- **但**：`GameController.buildDialog()`（约 752~756 行）无条件调
  ```ts
  const cfg = GameController.configOf(this.difficulty);
  GameStats.level = cfg.name;
  GameStats.record(won, this.seconds, cfg.name)
  ```
  而自定义局走 `startNewGame(s.height, s.width, s.mines)`（约 885 行）**不会改 `this.difficulty`** —— `this.difficulty` 仍是上一次选的那个难度。
  → **自定义局的成绩被记到了「初级/中级/高级」的名下**，并且会污染该难度的最佳纪录。
- 另外 `GameStats.record()` 里的 `played += 1` / `won += 1` 是**无条件累加**的（``GameStats.load()``），所以自定义局的**总局数/胜局数/胜率也被算进去了**，与 Win7「自定义局完全不进统计」不一致。

**判定**：**这是 bug**（不是缺功能）。
**工作量估计：小（< 30 行）** —— 给 `startNewGame` / `buildDialog` 加一个 `isCustom` 标志；自定义时跳过 `GameStats.record()`，并且结束对话框里的 `played/won/percent` 用空统计。

---

### 3.14 计时器 999 上限 / 雷数负数 —— 已实现，不算缺口 ｜ **今日状态：已实现**

- 计时器封顶 999：`GameController.startTimer()`（约 1009~1019 行）`if (this.seconds < 999) { this.seconds++; }` —— 与原版一致
- 雷数可为负：`MinesweeperEngine.minesRemaining()`（约 234~237 行）`return this.mineCount - this.flagCount;` —— 与原版一致，且 `GameStats`/对话框都允许负数。
- **[HELP]** 的 `-40` 也印证了原版允许负数。

---

### 3.15 和弦（点数字开邻格）的细节 —— 基本等价，一处疑似差异 ｜ **今日状态：仍存在（疑似）**

**原版确切表现**
- **[QT] `Board.cpp:159-199` `chord()`**：旗数 != 数字 → **`return false`，什么都不发生**；旗数 == 数字但邻格有雷 → **邻格所有雷同时引爆**并直接判负。
- **[REV] `resource.h`** 与 **[Lmy]** 都实现了同样的和弦逻辑。

**本项目现状**
- `MinesweeperEngine.chord()`（约 310~351 行）：旗数不匹配 → `return false`（**静默**，无音效）—— 与原版一致；匹配但有雷 → 邻格雷同时 `exploded = true` 并 `lose()` —— 与原版一致。
- `GameController.chord()`（约 560~580 行）：只在 `revealedCount > before` 时播 `TILE_MULTIPLE`。
- **疑似差异**：和弦**引爆**（旗插错）时，`lose()` 直接把雷 `revealed = true`，`revealedCount` 并不通过 `floodReveal` 增加 → **和弦引爆这一路没有爆炸音效**（`Sound.BOMB_START` 只在 `tap()` 里播）。真 Win7 在这种情况下会炸。
  → 标记为**疑似**，工作量 小（< 30 行）。

---

### 3.16 问号格被翻开 / 插旗又取消 —— 基本等价 ｜ **今日状态：已实现**

- **[QT] `Board.cpp:121`**：开格时 `c.mark = Mark::None;`（问号被清掉）—— 与原版一致
- **[QT] `Board.cpp:146-153` `toggleMark()`**：旗 →（允许问号时）问号 → 无 —— 与原版一致
- 本项目 `MinesweeperEngine.floodReveal()`（约 460~486 行）与 `toggleMark()`（约 285~303 行）行为一致。
- **音效差异（疑似）**：真 Win7 里「点开一个带问号的格子」与「给问号格插旗/取消」的音效是否与普通格不同，**在本机三份复刻里都没有证据**，无法确认。标记为**不确定**，不作为缺口。

---

### 3.17 其它视觉细节 —— 三条 ｜ **今日状态：见 §2.1 的对应行**

1. **七段数码管显示雷数/计时** —— **今日状态：已实现**（commit `a2b635f`）

   **真 Win7 的两个 LED 是七段数码管** —— 这条**原判是对的**，今天上午被误改成了「不是差距」，
   现在改回来：权威证据是**微软原图 `helpBoard.png`** 的状态条里「18」「40」的**逐像素反推**
   （`docs\SEVEN-SEG-COUNTER.md` 有完整几何表、逐段坐标、置信度与出处）。

   **素材里没有现成的七段笔段** —— 这条**仍然成立**：
   `otherSheet.png` 存储像素 `x 1..252, y 1953..2014` 与 `x 255..450, y 1953..2014`
   放大 3 倍实测是**两片纯灰渐变的窗口边框片**（一条竖直接缝），**既没有数字字形也没有笔段**。
   此前把它当成「七段笔段」是读图错误，`docs\ASSET-AUDIT.md` §3 / §5 已同步更正。

   **上午那个「不是降级」的论证是错的**：拿参考实现
   `linux-minesweeper/src/ui/BoardWidget.cpp:552-559`（`setBold(true)` + `setPen(Qt::white)` +
   `drawText` 居中）当依据，只能证明**那一份复刻**怎么画，不能证明**原版**长什么样。

   → **所以本轮的做法是「自己画」**：按 `SEVEN-SEG-COUNTER.md` 的几何用 Canvas 画段
   （`common\SevenSeg.ets`，接线在 `GameController.drawStatusStrip()`）。
   3 槽 / 槽距 13 / 右对齐不补零 / 负号独立一段 / 显示区间 [-99, 999] /
   亮段 `#FAFAFC` / 「1」带衬线小旗 + 底横（`SEG_FLAG`）/ 槽位起点取面板内 x=0。

   **本条从差距清单里去掉（已实现）。**

2. **鼠标移出按下格会取消待开的格**
   **[QT] `BoardWidget.cpp:823`**：「Sliding off the pressed tile cancels the pending reveal (Win7 lets you ...)」。
   本项目是触屏为主，**基本不适用**，工作量 小，**可不做**。

3. **点一下可以跳过爆炸级联**
   **[QT] `BoardWidget.cpp:790`**：「`finishExplosionNow();  // a click skips the cascade, like Win7`」。
   本项目的爆炸动画播完才弹对话框（`GameController` 约 727~735 行），**不能中途跳过**。
   工作量估计：小（< 30 行），**可有可无**。

---

## 4. 本节：需要主线程裁决 / 复核的点

> **2026-10-31 收口后状态**：以下 6 条里，**1、2、6 已裁决并落地**，**3、4、5 仍是「疑似」，未动**。

| # | 原来的疑问 | 现在的状态 |
|---|---|---|
| 1 | `face.png` 是时钟不是笑脸（§3.12）。建议改代码并把文件/常量改名 | **已裁决并落地**：状态条回退为 `[时钟][计时]…[雷数][雷图标]`；`RECT_FACE` 与 `rawfile/face.png` 已移除。裁决依据见 `docs\STATUS-STRIP-VERDICT.md` 结论 A |
| 2 | 首点音效归属疑似对调（§3.5）：原版 `firstPaint.wav` 配的是**发牌动画**，项目把它挂在首点开格上，发牌只用 `gameStart.wav` | **仍疑似，未动**。发牌动画（`DealIn.ets`）本轮已实现，但**首点音效归属没有重新核对**。另：`firstPaint` 是 11 个已落地音效之外的 4 个之一（`SPEC.md` §8-4），尚未接线 |
| 3 | 和弦引爆没有爆炸音效（§3.15），标记疑似 | **仍疑似，未动** |
| 4 | 「再玩一局」是否要同盘重来（§3.9），标记疑似 | **部分解决**：`restart()` 现在保留**盘面参数**（行列 + 雷数），不再换成难度预设（``GameController.restart()``）。但**雷位仍会重新随机**，与 Win7 的「同盘雷位重开」仍有差异 —— 这一半仍留着 |
| 5 | 键盘快捷键疑似未接线（§3.10），标记疑似 | **仍存在**。手机无物理键盘，F2 / X / A 只是画在菜单右边的提示文字 |
| 6 | [HELP] 与 [JPG] 的证据一致（都是「计时+时钟在左、雷数+雷在右」），所以 §3.12 的判定可以放心改 | **已裁决并落地**，见第 1 条 |

### 4.1 今天新出现的、尚未裁决的点

**（a）窄屏 + 30 列局的观感**：`SPEC.md` §8-8 已裁决「装得下但格边 < 48px 就抬一档，宁可超宽也要能点准」，
并且**已复测**：Mate 90 Pro 高级局从 n=1 抬到 n=2（格边 36→72），
棋盘横向出屏 440 px（预期内，可平移）；最终实测 **n=2 / 格边 72 px / 棋盘原点 (-440, 696)**
（`docs\CLICK-MATRIX-90P.md` R3.1 与 §10.5）。

**但规则本身曾有未修的 HIGH 级缺陷** —— `docs\LEAD-CHANGE-AUDIT.md` 的 **L1 [HIGH]**：
抬档只看「格子太小」，不看「抬完会不会反而装不下」；纵向又用**居中**而不是顶对齐 →
内容高于视口时，**上半截永久藏在菜单栏下**，那部分格子既看不见也点不着
（推演：外屏 1323×1000 上高级局 n=1 本来完全装得下 → 抬到 n=2 后 `frameY = -104`，
菜单栏压住 176px 棋盘）。

**L1 已修（commit `9a70112`）**：``GameController.layout()`` 抬档加前提
「抬完纵向仍装得下或横向本来就装不下」+ `:322-326` 纵向溢出改顶对齐。
**但修正后的行为尚未在设备上复测。**
**L2~L8 另 7 条 MEDIUM/LOW 一条未修**，完整清单见该报告 §1。

**（b）统计窗口命中 —— 已撤销，不是冲突**：补测曾把这 4 个控件全记为异常（B1），
与 `docs\LEAD-CHANGE-AUDIT.md` 的 Q4 结论相反，看起来像冲突。
**2026-10-31 14:02 查明并撤销**：是测试方**坐标量偏 2 px**（红叉命中区左边界 x=1699，点的是 1697），
不是应用缺陷。按校准后的坐标点，红叉正常关闭、列表选中正常、`[Stats] 点击关闭` 正常
（`docs\CLICK-MATRIX-X7.md` 异常 **C2**）。
→ **统计窗口的命中已确认可用**，「绘制与命中缩放系数不一致」的怀疑方向作废。

**（c）仍需独占设备重跑的三项**：longClick 插旗、doubleClick 和弦、「帮助(H)」对话框 ——
收尾补测时**设备被并发操作**（lead 也在同一台 5555 上点击），
屏幕被模态对话框覆盖，**无法定性，不是应用缺陷**（`docs\CLICK-MATRIX-X7.md` 异常 C1 / C4）。

**（d）「计数器用粗体白字不是降级」这条裁决已撤回**：理由与新结论见 §2.2。
**（e）外观对话框的中文名**：最终取「**颜色(C)**」，依据是 lead 直接问用户得到的
**用户本人 Win7 上的真名**；`docs\APPEARANCE-DIALOG.md` §1.1 里「外观(C) / 未确证」
是定名前的版本，以本节与 `Appearance.ets` 的 `MENU_APPEARANCE_LABEL` 为准。

> 另注：`docs\LAYOUT-MATRIX.md` v2.0 的数据快照是 13:35，本规则 13:39 才加，
> v2.0 表里「窄屏 + 高级 16×30 = n=1（格边 36）」那几行**已过期**（现应为 n=2 / 格边 72）。
> `LAYOUT-MATRIX.md` 是只读报告，本轮没改；要一致数字请重跑 `tools\check_layout.py`。
