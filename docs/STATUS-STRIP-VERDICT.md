# STATUS-STRIP-VERDICT.md —— 状态条左端那个圆钮：时钟还是笑脸？点它有原生行为吗？

> 结论先行：**A —— 素材里就是时钟，真 Win7 没有笑脸；点它没有原生行为。**
> 我们现在的画法是对的，「点时钟重开」是我们自己加的功能，不算复刻，建议**不做**。
>
> 盘点日期：2026-10-31
> 只读分析，未改动 `C:\Users\19161\saolei` 下任何文件。
> 裁图目录：`D:\software\harmony\projects\minesweeper\docs\analysis\`
> 无 emoji。

---

## 1. 裁图证据

| 裁图文件 | 来源与坐标 | 看到的内容 |
|---|---|---|
| `strip_otherSheet_clock_10x.png` | `win7-assets\images\otherSheet.png`，像素 (1810,850,50,50)，即逻辑 (905,425,25,25)，放大 10 倍 | **一个银白圆钮，钮面上是钟面**：有刻度环、12/3/6/9 四个刻度、一根指向右上的指针和一根指向下的指针。**不是脸**（没有眼、没有嘴、没有黄色）。 |
| `strip_minesweeperSheet_8x.png` | `win7-assets\images\minesweeperSheet.png` 全图 (94×54) 放大 8 倍 | 整张表里**只有两个精灵**：左边是「银圆钮里装一颗地雷」（面板雷图标），右边是「裸的尖刺地雷」。**没有第三个 25×25 面板图标**，也就没有笑脸位。 |
| `strip_panelMine_10x.png` | 同上表像素 (0,0,50,50) 放大 10 倍 | 银圆钮装雷。与时钟圆钮同一套「银钮 + 内容」的视觉语言。 |
| `strip_bareMine_10x.png` | 同上表像素 (54,0,90,36) 放大 10 倍 | 裸雷（盖在格子底下的那个）。 |
| `strip_helpboard_leftBtn_14x.png` | `win7-assets\images\helpBoard.png` 像素 (24,166,50,192) 放大 14 倍 | **微软自己**的 Win7 帮助窗口插图，左端圆钮：**钟面**，指针清晰可见。 |
| `strip_helpboard_rightBtn_14x.png` | 同上像素 (204,166,230,192) 放大 14 倍 | 右端圆钮：**地雷**（银圆钮里装雷）。 |
| `strip_helpboard_full.png` | `helpBoard.png` 整图放大 3 倍 | 插图底部状态条：`[钟面圆钮][LED "18"] ·········· [LED "-40"][地雷圆钮]`。**两个 LED 的数字语义决定了左右**：左边 18 只能是计时秒数，右边 -40 只能是雷数（插旗插多了才出负号，而雷数确实允许为负）。 |
| `strip_Frame_png_full.png` | `win7-assets\images\png\Frame.png` (600×351) 放大 2 倍 | 窗口底图，**左上角**依次是：钟面圆钮 + 深蓝 LED 面板 + 下面的雷圆钮。同样是钟，不是脸。 |
| `strip_Minesweeper_bmp_yellowregion_5x.png` | `win7-assets\images\Minesweeper.bmp` 像素 (10,30,144,210) 放大 5 倍 | 这张旧版表里唯一的 928 个「黄像素」是**发黄的旧方砖与雷的暖色高光**（右上角那一列是黄色矿脉纹的雷），**整张表没有一张脸**。 |
| `strip_otherSheet_bottomBand.png` | `otherSheet.png` 像素 (0,1948,460,2016) 放大 2 倍 | otherSheet 最底下那条：一条横向渐变条 + 一列 1..8 彩色数字（blueSheet 数字的**另一份副本**，未使用）。 |
| `strip_blueSheet_spriteRow_4x.png` | `blueSheet.png` 像素 (780,1104,1010,1160) 放大 4 倍 | 蓝表里那一行叠图：红旗、问号、高亮、红叉、上黑边。**其中没有任何脸**。 |

---

## 2. 结论与依据

### 2.1 素材层：权威精灵表里根本没有笑脸

`linux-minesweeper-main/src/ui/Theme.h` 的文件头（第 1-22 行）写明这三张表是**从游戏自己的资源里抽出来的**：

> // The Windows 7 Minesweeper artwork proper, extracted from the game's own
> // resources (see assets/more-resources/ and build_sheets.py).
> //   otherSheet  shared: the 23-frame mine-trip (loss) and 38-frame disarm-beam
> //                (win) animations, the win scan bar and **the clock icon**.

该表里与状态条有关的条目**只有两个 25×25 面板图标**：

- `Theme.h:113` —— `constexpr QRect kClock{905, 425, 25, 25};    // next to the time counter`
- `Theme.h:109` —— `constexpr QRect kPanelMine{0, 0, 25, 25};    // next to the mines counter`

**没有任何笑脸条目。** 也没有任何其它 25×25 面板图。

### 2.2 像素层：全量搜索，找不到一张脸

用 Pillow 对全部候选素材做「黄色圆盘」扫描（Win7 的笑脸是黄色圆盘）：

| 文件 | 尺寸 | 黄色像素 | 说明 |
|---|---|---|---|
| `blueSheet.png` | 2034×1206 | **0** | 无 |
| `minesweeperSheet.png` | 94×54 | **0** | 无 |
| `otherSheet.png` | 2048×2016 | 3965 | 全部是爆炸火球与花朵的暖色，不是脸 |
| `Frame.png` | 600×351 | **0** | 无 |
| `Frame.bmp` | 600×351 | **0** | 无 |
| `helpBoard.png` | 256×192 | **0** | 无 |
| `Minesweeper.bmp` | 144×468 | 928 | 发黄的旧方砖/矿脉纹，放大后确认不是脸 |

### 2.3 版式层：微软自己的插图与原版 XML

- 微软自己的 `helpBoard.png`：`[钟][18] ····· [-40][雷]`（见 §1、§2.4）。
- `linux-minesweeper-main/src/ui/BoardWidget.cpp:522-525` 明说布局照的是**原版的 MINESWEEPER.xml CustomLayout**：

  ```
  // The status strip in the bottom border, laid out like the original's
  // MINESWEEPER.xml CustomLayout: X offsets from the window's centre,
  // Y offsets from its bottom. Clock icon and time on the left, mine
  // count and the game style's mine (or flower) icon on the right.
  ```

  → **时钟 + 计时在左，雷数 + 雷图标在右**，与本项目当前版式一致。
- `linux-minesweeper-main/README.md:48`：「the navy time/mine counters with their **clock and mine buttons**」。

### 2.4 两个 LED 的数字语义（独立于图像的第二重证据）

`helpBoard.png` 底部：左边 LED = `18`，右边 LED = `-40`。
- 左边那个数**只能是计时秒数**（雷数不会正好是 18 且带不了这种排版）；
- 右边那个数**只能是雷数**（计时器永远不会是负数，而雷数在旗插多时**会**变负 —— 这正是本项目 `MinesweeperEngine.minesRemaining()` 允许返回负数的依据）。

所以真 Win7 的左端圆钮必然是**配计时的时钟**，右端圆钮必然是**配雷数的地雷**。

### 2.5 交互层：点它没有原生行为

`linux-minesweeper-main/src/ui/BoardWidget.cpp:783-813` `mousePressEvent()` 只对**棋盘格**做命中测试：

```cpp
const QPoint c = cellAt(event->pos());
if (c.x() < 0)
    return;                      // 棋盘外的点击（包括状态条）一律忽略
```

整个 Win7 保真复刻里，状态条上的时钟/雷图标**没有任何点击处理**。它支持的点击行为只有三种：跳过发牌动画、跳过爆炸级联、和弦/翻格。

### 2.6 需要如实说明的反证（不改变结论）

`ReversingMinesweeper-master` **确实有笑脸**：

- `drawing.h:4-8`：`SMILE_NORMAL 0 / SMILE_WOW 1 / SMILE_LOST 2 / SMILE_WINNER 3 / SMILE_CLICKED 4`
- `drawing.c:20-21`：位图 24×24；`resource.h:82`：`ID_BITMAP_SMILES 430`
- `windowing.c:128`：点击时 `DisplaySmile(SMILE_CLICKED)` → 即「点笑脸 = 重开一局」

**但它用的是自己的一份独立位图 `ID_BITMAP_SMILES 430`，不属于 Win7 那三张精灵表。**
那张脸谱系属于 Windows XP / 3.1 时代的经典扫雷，与 Win7 的 Aero 版式不是同一套设计。
因此**不能用它来证明真 Win7 有笑脸**；它证明的是「经典（XP 时代）扫雷有可点的笑脸」。

同理，`Minesweeper-master`（Lmy0217 克隆版）的 `gaming.jpg` / `exploding.jpg` 底部也是
`[时钟][LED] ····· [LED][雷图标]`，同样没有笑脸；它 `.rc` 里没有「颜色」菜单项，只能说明该克隆做得不完整，**不能反推真 Win7 的菜单结构**。

### 2.7 本项目当前状态（已核对源码）

`GameController.ets:653-687` `drawStatusStrip()`：

- 左端 `clockX` 画 `RECT_CLOCK`（otherSheet），`timeX` 画计时面板；
- 右端 `mineX` 画雷数面板，`iconX` 画 `RECT_PANEL_MINE`（雷图标）；
- 代码注释（第 656-663 行）已经写明「左边那个圆钮**是时钟不是笑脸**（盘面上有指针）」。

→ **版式与选图都与真 Win7 一致，本项没有保真度 bug。**

（`Theme.ets` 早期版本里的 `RECT_FACE` / `face.png` —— 即从 `helpBoard.png` 左钮抠出来却命名为「笑脸」的那份 —— 已被移除；当前 `Theme.ets` 里已无 `RECT_FACE`，`rawfile/` 里也已无 `face.png`。）

---

## 3. 建议（一句话）

**状态条上那两个圆钮（时钟、地雷图标）不要做成交互元素** —— 原版它们是纯装饰、点不动；要做「点一下重开一局」属于我们自己加的功能，不是复刻，而且项目已有 F2 与菜单「新建」两条正路。

如果产品上仍然想要「点某个地方重开」，那是一个**独立的易用性决定**，建议明确标注为增强功能，不要写进「与 Win7 一致」的清单里。

---

## 4. 一句话给主线程

**A**：素材里就是时钟（`otherSheet.png` 逻辑 (905,425,25,25) 放大 10 倍可见钟面与指针；Win7 精灵表 `Theme.h:113` 只有 `kClock` 和 `kPanelMine` 两个面板图标，全套素材黄色笑脸扫描为 0；微软自己的 `helpBoard.png` 也是 `[钟][18]…[-40][雷]`），且 Win7 保真复刻 `BoardWidget.cpp:783-813` 对状态条**不做任何命中测试**，所以「点时钟重开」是我们自加的功能，**建议不做**。
