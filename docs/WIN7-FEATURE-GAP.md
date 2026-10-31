# WIN7-FEATURE-GAP.md —— 「真 Win7 扫雷有、本项目还没有或做错了」逐条清单

> 只读分析，未改动工程代码。
> 盘点日期：2026-10-31
> 本项目现状以 `C:\Users\19161\saolei\entry\src\main\ets\` 下的 `.ets` 为准（只读）。
> **行号说明**：盘点期间 `saolei` 工程正在被并行修改（`GameController.ets` 从 37 879 B 变成 40 001 B）。
> 本文的行号取自 2026-10-31 约 08:40~08:55 读取到的那一版，**函数名/常量名比行号更可靠**，核对时请以函数名为准。
> 无 emoji。

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
| 游戏 → **外观/颜色(F7)** | **缺** | 见 §3.2（绿色主题），素材已就位 | 小 |
| 游戏 → 标记(?) | 有 | **等价**：关闭后 `toggleMark` 只走「无→旗→无」两态（`MinesweeperEngine.ets:285-303`） | — |
| 游戏 → 声音 | 有 | 等价 | — |
| 游戏 → **最佳成绩** | 有（`openInfoDialog('best')`） | 缺「最多连胜/最多连败/当前连赢」和「重置」按钮，见 §3.7 | 中 |
| 游戏 → 退出 | 有 | — | — |
| 帮助 → **查看帮助(F1)** | **缺** | 见 §3.1 | 中 |
| 帮助 → 关于扫雷(A) | 有（`WinDialog.ets` 的 `aboutSpec`） | 等价 | — |
| （顶层）**统计** | 无独立项 | 与上面「统计(F4)」同一条 | — |

---

## 2. 结论速览：缺口清单（按工作量从小到大）

| # | 行为 | 工作量 | 是否必须补 |
|---|---|---|---|
| 1 | 悬停高亮用了普通合成而不是**相加混合** | 小 | 必须（是 bug） |
| 2 | 状态条两个 LED **左右颠倒** + `face.png` 实为时钟不是笑脸 | 小 | 必须（是 bug） |
| 3 | **自定义局的成绩被记到了当前难度名下** | 小 | 必须（是 bug） |
| 4 | 「颜色(F7)」绿色主题 | 小 | 可有可无（但性价比最高） |
| 5 | **新开局的发牌动画**（1100 ms 逐格波浪淡入） | 中 | 可有可无 |
| 6 | **判负时其它雷逐个烧红的级联** | 中 | 可有可无 |
| 7 | 洪泛开格的**涟漪淡出**动画 | 中 | 可有可无 |
| 8 | 统计窗口缺「连胜/连败」与「重置」 | 中 | 可有可无 |
| 9 | **独立帮助窗口(F1)** | 中 | 可有可无 |
| 10 | 「选项(F5)」独立设置窗口 | 大 | 可有可无（菜单栏已覆盖大部分功能） |
| 11 | 计时器/雷数用真**七段数码管** | 中 | 可有可无 |

---

## 3. 逐条详情

### 3.1 独立帮助窗口(F1) —— 缺

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

### 3.2 「颜色(F7)」—— 缺，但素材已就位，复用成本极小

**原版确切表现**
- **[REV] `resource.h:36`**：`#define ID_MENUITEM_COLOR 529`。
- **[QT] `MainWindow.cpp:142`**：`game->addAction(tr("&Change Appearance"), QKeySequence(Qt::Key_F7), this, &MainWindow::showAppearance);`
- **[QT] `AppearanceDialog.cpp:151-164`**：「外观」对话框有两组单选图示：
  - **Select Game Style**：`thumbMines.png`（Minesweeper）/ `thumbFlowers.png`（Flower Garden）
  - **Select Board**：`thumbBlue.png`（Silver and Blue）/ `thumbGreen.png`（Green）
- **[QT] `MainWindow.cpp:187-189`**：配色是一个持久化设置（`boardStyle` = blue|green），随时可切。

**本项目现状**
- 菜单里没有「颜色」项（`buildMenu()` 约 940~965 行）。
- `Theme.ets` 没有任何 `BoardStyle` 概念；`disarmRect`（`Theme.ets` 91~94 行）硬编码蓝色基址。
- `SpriteAtlas.ets` 只加载 `blueSheet.png`。
- `rawfile/` 里**没有** `greenSheet.png`。

**素材侧结论（本次盘点实测，见 `ASSET-AUDIT.md` §2.1）**
- `blueSheet.png` 与 `greenSheet.png` **同为 2034×1206，逐区域同构**。
- 差异**只在**：砖块渐变区（px `0..900, 0..1044`，99.3 % 像素不同）、已翻开凹陷格区（px `1000..1900`，浅色偏色）、计数器面板（px `0..120, 1155..1206`）。
- **数字 1..8、旗、问号、高亮、红叉、阴影条全部逐字节相同**（差异 0 %）。
- **唯一必须改的坐标**：胜利拆雷动画的基址 —— 蓝色在逻辑 `x=0`，绿色在逻辑 `x=364`（`otherSheet.png` 存储像素 `x 728..1455`）。
- 现成的预览图：`thumbBlue.png` / `thumbGreen.png`（各 109×109，1:1 原图，6×6 方砖马赛克）。

**工作量估计：小（< 30 行）**
1. `rawfile/` 拷 `greenSheet.png`（+2.4 MB）与 `thumbBlue.png`/`thumbGreen.png`
2. `Theme.ets` 加 `BoardStyle`，`disarmRect(frame, style)` 加 baseX（蓝 0 / 绿 364）
3. `SpriteAtlas.ets` 按主题选图集
4. 菜单加 `{ id: 'color', label: '颜色' }`，弹一个两图选择对话框
合计约 15~25 行代码 + 2 个文件拷贝。

**附注**：花园区（Flower Garden）**不建议做** —— 需要额外的 `flowerGardenSheet.png`、花朵踩雷动画（`otherSheet` 逻辑 `905+38*(f%3)`）、3 条 `flowerLose*.wav`，与「扫雷」定位不符。

---

### 3.3 判负后「其它雷逐个烧红」—— 缺

**原版确切表现**
- **[Lmy] `utf8/Minesweeper.cpp:1800-1841` `mineBomb()`**：
  1. 先把**所有雷**一次性画出来（1805~1813 行）；
  2. 踩中的那颗播 `IDR_WAVE4`（爆炸开始音 = `mineBombStart.wav`），然后 **25 帧 × `Sleep(23)` = 575 ms**（1819~1825 行）；
  3. `getMineDevelopNo(no, mapInfo, 25, row, col, count)` 算出**其它雷逐个爆炸的顺序数组**（1827 行），同时播 `IDR_WAVE5` 且 `SND_LOOP`（循环爆炸中音 = `mineBombRun.wav`）；
  4. 按该顺序逐个把雷画成爆炸态，每步 `speed(150, ...)` 延时（1833~1838 行）；
  5. 最后播 `IDR_WAVE6`（爆炸结束音 = `mineBombEnd.wav`）。
- **[JPG] `exploding.jpg`** 正是这个级联进行中的画面：雷已经全部露出，右半边散布着深色的爆炸精灵，且**越靠近爆炸源越密、越远越稀**。

**本项目现状**
- `MinesweeperEngine.ets:488-500` `lose()`：**一次性**把所有未插旗的雷 `revealed = true`，**没有逐个烧红的时序**。
- `GameController.ets` 约 619~621 行：踩雷后 `Anim.startTrip(cell)` 播**那一格**的 23 帧爆炸动画（约 619 行）。
- 音效三段时序**已做对**：`BOMB_START` → 575 ms → `BOMB_RUN` → 3949 ms → `BOMB_END`（`GameController.ets` 约 700~710 行 `playBombTail()`）。

**工作量估计：中（30~120 行）**
- 需要一个「按到爆炸源的距离/环带排序的逐格爆炸队列」+ 一个 25 帧/雷的爆炸态绘制（素材够：踩雷帧是 23 帧 57×57 逻辑，`otherSheet` 逻辑 `728 + 59*(f%3), 59*(f//3)`）。
- 估计 60~100 行。

---

### 3.4 胜利后的扫描条 + 逐雷拆解 —— **已实现（不算缺口）**

**原版确切表现**
- **[QT] `BoardWidget.cpp:226-254` `playWin()`**：`kScanTicks = 3000/30`（**扫描条自下而上扫过棋盘 3 秒**），每颗雷的拆解光束在扫描条**扫到它那一行**时发射：`start = kScanTicks * (rows - r) / (rows + 1)`，光束本身 `kDisarmTicks = 2000/30`（**2 秒**）。
- **[QT] `Theme.h:146-157`**：`disarmFrame`（38 帧，`50×150` 逻辑，7 帧/行）、`kDisarmOffset{-18,-69}`、`kScanBar{0,912,275,62}`。

**本项目现状：已实现，且逐帧参数与原版一致**
- `Anim.ets`：已把爆炸帧改成**原版 23 帧**（`EXPLODE_FRAMES=23`，步距 59），并新增胜利动画：`DISARM_FRAMES=38`、`DISARM_FRAME_MS=2000/38`、`SWEEP_MS=3000`、`SCAN_BAR=[0,912,275,62]`、`startWin()`、`beamFrame()`。
- `GameController.ets`：`startWinSweep()`（约 645~664 行）按行算每颗雷的起始时刻并调 `Anim.startWin(cells, times)`；约 670~676 行用 `Anim.winElapsed / Anim.SWEEP_MS` 算扫描条进度。
- **判定：不是缺口。**（若主线程要复核，注意 `Anim.disarmRect` 的基址仍写死蓝色 `52*(f%7)`，接绿色主题时要改成 `364 + 52*(f%7)`。）

---

### 3.5 首点 / 新开局的发牌动画 —— 缺

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

### 3.6 洪泛开格的涟漪淡出 —— 缺

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

### 3.7 统计/最佳成绩窗口 —— 部分缺

**原版确切表现**
- **[JPG] `information.jpg`（702×254）** 就是这个窗口的截图，标题「扫雷统计信息」，布局：
  - 左：级别列表（初级/中级/高级，当前项高亮蓝）
  - 中：「最佳时间」列（时间值 + 日期，如 `17` + `Sat Nov 28 23:94:41 2015`）
  - 右：`已玩游戏: 3`、`已胜游戏: 1`、`获胜率: 33%`、**`最多连胜: 1`**、**`最多连败: 2`**、**`当前连赢: 1`**
  - 底：`关闭(C)`、`重置(R)`
- **[Lmy] `Resource.h`**：`IDD_STATISTIC 142`；**[REV] `resource.h`**：`ID_DIALOG_WINNERS 700` + `ID_DIALOG_WINNERS_BTN_RESET_SCORES 707`（**有重置按钮**）。

**本项目现状**
- `GameStats.ets` 只存：`played`、`won`、`best_<难度>`、`bestDate_<难度>`（`GameStats.ets:19-28`）。
- **没有**：连胜/连败/当前连赢的统计，**也没有「重置记录」按钮**。
- `GameController.openInfoDialog('best')`（约 800 行附近）画的行是 `难度 + 最佳时间 + 日期` 三列 + `played/won/percent`。

**工作量估计：中（30~120 行）**
- `GameStats` 加 `maxWinStreak / maxLoseStreak / currentWinStreak` 三个字段与更新逻辑（约 25 行），`WinDialog.bestSpec` 加三行显示（约 15 行），加「重置」按钮与清除存档（约 20 行）。

---

### 3.8 「选项(F5)」独立设置窗口 —— 缺

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

### 3.9 「重新开局」 vs 「重开同一盘」 —— 疑似有差异

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

### 3.10 键盘快捷键 —— 疑似未接线

**原版确切表现**
- **[QT] `MainWindow.cpp:135-150`**：F2 新建、F4 统计、F5 选项、F7 外观、F1 帮助，全部是菜单项上的 `QKeySequence`。
- **[REV] `resource.h:20-21`**：`#define ID_ACCELERATORS 501`（加速键表）。

**本项目现状**
- 菜单项上标了快捷键文字（`buildMenu()` 里 `accelerator: 'F2'` / `'X'` / `'A'`），但**那是画在菜单右边的提示文字**。
- `Index.ets` 只接了 `this.controller.onMenuAction = (action: string) => {...}`（`Index.ets:51`）这一条回调；`grep` 全 `entry/src/main/ets` **没有找到任何 key/keyDown/keyEvent 处理**。
- → **F2 / X / A 的提示在界面上写着，但很可能按了没反应。**

**判定**：**疑似**未接线（未找到键盘事件处理代码）。
**工作量估计：小（< 30 行）** —— 页面接 `onKeyEvent`，把 F2 映射到 `new`、A 映射到 `about`。

---

### 3.11 悬停高亮的混合模式 —— **是 bug**

**原版确切表现**
- **[QT] `Theme.h:86-87`**：「The hilite is additive: the original engine **adds** it onto the hovered tile, which is what makes hover glow.」
- **[QT] `BoardWidget.cpp:622`**：「The hover glow is **additive**, like the original engine」。
- 素材侧实测：`blueSheet.png` 的 `RECT_HILITE`（逻辑 `[440,560,18,18]` → 存储像素 `880..915, 1120..1155`）是一块 **100 % 不透明**的深青灰方块（平均 RGB ≈ 32,64,63）。

**本项目现状**
- `Theme.ets:44-45` 的注释已经写明「悬停高亮（**相加混合**）」。
- 但 `GameController.drawBoard()`（约 445~447 行）用的是普通 `this.atlas.drawLogical(ctx, this.atlas.boardSheet, RECT_HILITE, x, y, u);` —— **普通 alpha 合成**，没有设置加法混合。
- 后果：因为那块方块 100 % 不透明，普通合成会把整格砖块**整个涂成深青灰**；原版是**加法**，表现为砖块上浮起一层微亮的高光。

**判定**：**这是 bug**，注释与实现不一致。
**工作量估计：小（< 30 行）** —— Canvas 2D 里把 `globalCompositeOperation` 设为 `'lighter'`（或 `'screen'`）再画这一块即可；顺带确认 `RECT_HILITE` 的 alpha 语义。

---

### 3.12 状态条左右顺序 —— **是 bug（且 `face.png` 被误标为笑脸）**

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
- `Theme.ets:71-79` 把 `rawfile/face.png` 注释成「**笑脸按钮**（从真 Win7 素材 helpBoard.png 的帮助插图里抠出来的 14×14 原图）」，并写「真 Win7 的状态条顺序见 SPEC §5.5：**左侧 [笑脸][雷数面板] …… [计时面板][雷图标]**」。
- **但那个抠出来的图是时钟，不是笑脸**（见 `docs/audit_helpboard_lefticon.png`）。
- 净效果：项目画出的是 `[时钟][雷数LED] ····· [计时LED][地雷图标]` —— **两个 LED 的左右位置与真 Win7 相反**。

**判定**：**这是 bug**。两种改法任选：
- (a) 改成 `[时钟][计时LED] ····· [雷数LED][地雷图标]`：把 `face.png` 挪到右边靠计时器，或直接用 `otherSheet` 的 `RECT_CLOCK`（项目已有），并把两个 LED 面板对调。**约 10~20 行。**
- (b) 保持项目现状但改注释和命名（承认这是 Lmy 复刻的版式）。**约 5 行。**
- 建议同时把 `face.png` 改名成 `clock.png`、把 `RECT_FACE` 改成 `RECT_CLOCK_HELP`，避免继续误导。

**工作量估计：小（< 30 行）**

**附：笑脸表情不是缺口。** 真 Win7 的这套素材里**没有笑脸精灵** —— `minesweeperSheet.png` 只有 2 个精灵（面板雷钮 `[0,0,25,25]` 与裸雷 `[27,0,18,18]`），`otherSheet.png` 与 `Minesweeper.bmp` 里也没有。**[HELP] 的状态条里同样没有笑脸**（只有时钟和地雷两个圆钮）。
→ 「笑脸随状态变化（惊讶/死亡/戴墨镜）」在**这套素材里无据可依**，**不应作为缺口补**。

---

### 3.13 自定义局是否记成绩 —— 项目**记错了**

**原版确切表现**
- **[QT] `MainWindow.cpp:236-238`**：
  ```cpp
  // Custom games are not recorded, matching Windows 7.
  if (m_difficulty.id != QLatin1String("custom"))
      m_lastRecord = Stats::recordGame(m_difficulty.id, won, m_seconds);
  ```
- **[QT] `MainWindow.cpp:262`**：自定义局的结束对话框里，`played/won/percent` 也用**空统计**（`preset ? Stats::load(...) : Stats::Data()`）。

**本项目现状**
- `GameStats.ets:100-102` `levels()` 只返回 `['初级','中级','高级']` → 最好成绩不记自定义局，**这一半是对的**。
- **但**：`GameController.buildDialog()`（约 752~756 行）无条件调
  ```ts
  const cfg = GameController.configOf(this.difficulty);
  GameStats.level = cfg.name;
  GameStats.record(won, this.seconds, cfg.name)
  ```
  而自定义局走 `startNewGame(s.height, s.width, s.mines)`（约 885 行）**不会改 `this.difficulty`** —— `this.difficulty` 仍是上一次选的那个难度。
  → **自定义局的成绩被记到了「初级/中级/高级」的名下**，并且会污染该难度的最佳纪录。
- 另外 `GameStats.record()` 里的 `played += 1` / `won += 1` 是**无条件累加**的（`GameStats.ets:56-63`），所以自定义局的**总局数/胜局数/胜率也被算进去了**，与 Win7「自定义局完全不进统计」不一致。

**判定**：**这是 bug**（不是缺功能）。
**工作量估计：小（< 30 行）** —— 给 `startNewGame` / `buildDialog` 加一个 `isCustom` 标志；自定义时跳过 `GameStats.record()`，并且结束对话框里的 `played/won/percent` 用空统计。

---

### 3.14 计时器 999 上限 / 雷数负数 —— 已实现，不算缺口

- 计时器封顶 999：`GameController.startTimer()`（约 1009~1019 行）`if (this.seconds < 999) { this.seconds++; }` ✔
- 雷数可为负：`MinesweeperEngine.minesRemaining()`（约 234~237 行）`return this.mineCount - this.flagCount;` ✔，且 `GameStats`/对话框都允许负数。
- **[HELP]** 的 `-40` 也印证了原版允许负数。

---

### 3.15 和弦（点数字开邻格）的细节 —— 基本等价，一处疑似差异

**原版确切表现**
- **[QT] `Board.cpp:159-199` `chord()`**：旗数 != 数字 → **`return false`，什么都不发生**；旗数 == 数字但邻格有雷 → **邻格所有雷同时引爆**并直接判负。
- **[REV] `resource.h`** 与 **[Lmy]** 都实现了同样的和弦逻辑。

**本项目现状**
- `MinesweeperEngine.chord()`（约 310~351 行）：旗数不匹配 → `return false`（**静默**，无音效）✔；匹配但有雷 → 邻格雷同时 `exploded = true` 并 `lose()` ✔。
- `GameController.chord()`（约 560~580 行）：只在 `revealedCount > before` 时播 `TILE_MULTIPLE`。
- **疑似差异**：和弦**引爆**（旗插错）时，`lose()` 直接把雷 `revealed = true`，`revealedCount` 并不通过 `floodReveal` 增加 → **和弦引爆这一路没有爆炸音效**（`Sound.BOMB_START` 只在 `tap()` 里播）。真 Win7 在这种情况下会炸。
  → 标记为**疑似**，工作量 小（< 30 行）。

---

### 3.16 问号格被翻开 / 插旗又取消 —— 基本等价

- **[QT] `Board.cpp:121`**：开格时 `c.mark = Mark::None;`（问号被清掉）✔
- **[QT] `Board.cpp:146-153` `toggleMark()`**：旗 →（允许问号时）问号 → 无 ✔
- 本项目 `MinesweeperEngine.floodReveal()`（约 460~486 行）与 `toggleMark()`（约 285~303 行）行为一致。
- **音效差异（疑似）**：真 Win7 里「点开一个带问号的格子」与「给问号格插旗/取消」的音效是否与普通格不同，**在本机三份复刻里都没有证据**，无法确认。标记为**不确定**，不作为缺口。

---

### 3.17 其它视觉细节 —— 三条

1. **七段数码管显示雷数/计时**
   真 Win7 的两个 LED 是**七段数码管**（**[HELP]** 里能看到 "18" / "-40" 的段状笔画，负号也是一段）。
   本项目用 `ctx.font = bold ${12*u}px sans-serif` 直接画文字（`GameController.drawStatusStrip()` 约 491~496 行）。
   素材里**有现成的七段笔段**：`otherSheet.png` 存储像素 `x 1..252, y 1953..2014` 与 `x 255..450, y 1953..2014`（两组各 3 个字位），见 `ASSET-AUDIT.md` §3。
   **工作量估计：中（30~120 行）**（需要把笔段按 0-9 拼出来，含负号）。

2. **鼠标移出按下格会取消待开的格**
   **[QT] `BoardWidget.cpp:823`**：「Sliding off the pressed tile cancels the pending reveal (Win7 lets you ...)」。
   本项目是触屏为主，**基本不适用**，工作量 小，**可不做**。

3. **点一下可以跳过爆炸级联**
   **[QT] `BoardWidget.cpp:790`**：「`finishExplosionNow();  // a click skips the cascade, like Win7`」。
   本项目的爆炸动画播完才弹对话框（`GameController` 约 727~735 行），**不能中途跳过**。
   工作量估计：小（< 30 行），**可有可无**。

---

## 4. 本节：需要主线程裁决 / 复核的点

1. **`face.png` 是时钟不是笑脸**（§3.12）。建议改代码并把文件/常量改名。
2. **首点音效归属疑似对调**（§3.5）：原版 `firstPaint.wav` 配的是**发牌动画**，项目把它挂在首点开格上，发牌只用 `gameStart.wav`。
3. **和弦引爆没有爆炸音效**（§3.15），标记疑似。
4. **「再玩一局」是否要同盘重来**（§3.9），标记疑似。
5. **键盘快捷键疑似未接线**（§3.10），标记疑似。
6. **[HELP] 与 **[JPG]** 的证据一致**（都是「计时+时钟在左、雷数+雷在右」），所以 §3.12 的判定可以放心改。
