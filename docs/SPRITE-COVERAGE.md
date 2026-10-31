# SPRITE-COVERAGE.md —— 精灵引用完整性与越界审计（第二轮：帮助窗口改版后复审）

> 盘点日期：2026-10-31（第二轮）
> 审计脚本：`docs\verify\check_sprites_v2.py`（越界复核）、`docs\verify\smiley_recheck.py`（笑脸独立复核）、
> `docs\verify\strip_evidence.py`、`docs\verify\where_do_frames_live.py`、`docs\verify\montage_assets.py`
> 裁图目录：`docs\verify\sprites\`（另有第一轮的 `docs\analysis\strip_*.png`）
> 只读 `C:\Users\19161\saolei`，只写本文件与 `docs\verify\` 下我自己的脚本/裁图。
> 无 emoji。

---

## 0. 结论速览

| 项 | 数 |
|---|---|
| 命名精灵引用条目 | **19**（活 18 + 本轮新增 `drawWhole(helpBoard)` 1 条；另有 3 条已死的重复常量不算活引用） |
| 展开后的单个源矩形 | **1523** 个 |
| **越界（×2 后超出图集）** | **0** |
| 重复常量组 | **1**（`RECT_PANEL_MINE` == `WinDialog.win.icon`，值相同、无害） |
| 素材清单（win7-assets 34 个文件） | **已进产品 16 个**（4 图 + 12 音频），**未用 18 个** |
| 三个疑点 | **笑脸：不存在**（独立复核，第三次确认）；**绿色棋盘 / 花园模式：原版资源确有，做不做见 §6**；**音频：12/15 已接，缺的 3 个只在花园模式用** |

---

## 1. 精灵越界复核

### 1.1 图集实测尺寸（直接读 runtime `rawfile/` 里 PNG 的 IHDR）

| 图集 | 字节 | 实测尺寸 | 逻辑尺寸（÷2） |
|---|---|---|---|
| `blueSheet.png` | 2 276 292 | **2034 × 1206** | 1017 × 603 |
| `minesweeperSheet.png` | 10 642 | **94 × 54** | 47 × 27 |
| `otherSheet.png` | 853 213 | **2048 × 2016** | 1024 × 1008 |
| `helpBoard.png`（**本轮新增**） | 69 646 | **256 × 192** | **1:1，不折半** |

### 1.2 引用总表（`源矩形(×2后)` = 存储像素坐标 `(x,y,w,h)`）

| 引用名 | 所在文件:行 | 源矩形(最远帧) | 图集 | 越界 | 用途 |
|---|---|---|---|---|---|
| `normalTileRect(frame)` 720 帧 | `Theme.ets:28` | `(684, 1008, 36, 36)` | blueSheet | 否 | 未揭开的凸起方砖（渐变，25 帧/行） |
| `pressedTileRect(frame)` 720 帧 | `Theme.ets:35` | `(1684, 1008, 36, 36)` | blueSheet | 否 | 已翻开的凹陷地板砖（normal +1000） |
| `RECT_FLAG` | `Theme.ets:41` | `(800, 1120, 36, 36)` | blueSheet | 否 | 红旗 |
| `RECT_QUESTION` | `Theme.ets:43` | `(840, 1120, 36, 36)` | blueSheet | 否 | 问号 |
| `RECT_HILITE` | `Theme.ets:45` | `(880, 1120, 36, 36)` | blueSheet | 否 | 悬停高亮（加法混合） |
| `RECT_MISFLAG` | `Theme.ets:47` | `(920, 1120, 36, 36)` | blueSheet | 否 | 错旗红叉 |
| `RECT_SHADOW_U` | `Theme.ets:49` | `(960, 1120, 36, 6)` | blueSheet | 否 | 上边黑边 18×3 |
| `RECT_SHADOW_L` | `Theme.ets:51` | `(2024, 0, 6, 36)` | blueSheet | 否 | 左边黑边 3×18（右边距仅 10px） |
| `INLINE_SHADOW_L_LOW`（内联字面量） | `GameController.ets:510` | `(2024, 6, 6, 30)` | blueSheet | 否 | 角落处从黑边下方开始的左黑边 |
| `RECT_COUNTER` | `Theme.ets:53` | `(0, 1160, 80, 42)` | blueSheet | 否 | 计数器凹槽面板 |
| `digitRect(1..8)` | `Theme.ets:56` | `(2000, 210, 24, 30)` | blueSheet | 否 | 彩色数字 1..8 |
| `RECT_MINE` | `Theme.ets:63` | `(54, 0, 36, 36)` | minesweeperSheet | 否 | 格下地雷 |
| `RECT_PANEL_MINE` | `Theme.ets:65` | `(0, 0, 50, 50)` | minesweeperSheet | 否 | 状态条「雷图标」银钮 |
| `WinDialog.win.icon`（字面量） | `WinDialog.ets:323` | `(0, 0, 50, 50)` | minesweeperSheet | 否 | 胜/负对话框的雷图标 |
| `RECT_CLOCK` | `Theme.ets:70` | `(1810, 850, 50, 50)` | otherSheet | 否 | 状态条时钟图标 |
| `Anim.explodeRect(f)` 23 帧 | `Anim.ets:55` | `(1574, 826, 114, 114)` | otherSheet | 否 | 踩雷爆炸动画 |
| `Anim.disarmRect(f)` 38 帧 | `Anim.ets:115` | `(208, 1520, 100, 300)` | otherSheet | 否 | 胜利拆雷光束 |
| `Anim.SCAN_BAR` | `Anim.ets:85` | `(0, 1824, 550, 124)` | otherSheet | 否 | 胜利扫描条 |
| **`SpriteAtlas.drawWhole(helpBoard)`** | `SpriteAtlas.ets:147` / `WinDialog.ets:463` | **`(0, 0, 256, 192)`（1:1，不折半）** | **helpBoard 256×192** | **否** | 帮助窗口整图 |

### 1.3 越界清单

**空。0 条越界。** 19 条引用展开出的 1523 个源矩形全部落在图集内。

最靠近边界的四条（均在界内，列出以示已核）：

| 引用名 | 源矩形 | 图集宽 | 右边距 |
|---|---|---|---|
| `RECT_SHADOW_L` | `(2024, 0, 6, 36)` | 2034 | 10 px |
| `INLINE_SHADOW_L_LOW` | `(2024, 6, 6, 30)` | 2034 | 10 px |
| `digitRect(8)` | `(2000, 210, 24, 30)` | 2034 | 10 px |
| `RECT_COUNTER` | `(0, 1160, 80, 42)` | 高 1206 | 下 4 px |

### 1.4 `drawWhole` 的 vp / 设备像素换算复核（lead 点名要查的那条）

**代码现状**（`SpriteAtlas.ets:147-150`）：

```ts
ctx.drawImage(sheet,
  0, 0, srcW * pxScale, srcH * pxScale,          // 源矩形（vp）
  devX * pxScale, devY * pxScale,                // 目标左上（vp）
  srcW * scale * pxScale, srcH * scale * pxScale); // 目标尺寸（vp）
```

**结论：换算正确，且在任何密度下都恰好等于原图，不会越界、不会画错位置。** 验证（`check_sprites_v2.py` 的 proof 段，`pxScale = 1/density`）：

| density | pxScale | 源矩形(vp) | 换回位图像素 | 目标(设备像素) |
|---|---|---|---|---|
| 1.0 | 1.0000 | (256.000, 192.000) | **(256, 192)** 恰为原图 | (256, 192) |
| 2.0 | 0.5000 | (128.000, 96.000) | **(256, 192)** | (256, 192) |
| 3.125 | 0.3200 | (81.920, 61.440) | **(256, 192)** | (256, 192) |
| 3.5 | 0.2857 | (73.143, 54.857) | **(256, 192)** | (256, 192) |

理由：源矩形用 vp、位图按 density 折算回像素，**恒等于原图宽高**，所以既不会裁到图外（不像 `draw()` 那样 ×2 会裁到 512×384 直接出界），也不会少画。

**关于「PixelMap 源矩形单位是 vp」这条前提**：本机离线无法直接查官方 API 文档，只能给**内部一致性证据** ——
`SpriteAtlas.draw()`（第 100-104 行）对同一张 PixelMap 取源矩形时乘的是 `pxScale`（不是直接用像素坐标），而这条老路径是**已验证能正确显示棋盘**的；
`drawWhole()` 用的是**同一个约定**。两处自洽，且老路径有实机证据。

**残余风险（如实说明）**：若某台设备上 API 的源矩形实际按像素解释，`draw()` 会整片画错 —— 但那种情况下棋盘早就不能看了，所以这个前提可以认为成立。

**另一处已核对、不成问题的点**：`WinDialog.ets:460` 取 `k = max(1, floor(sDev))` 作为放大倍数，图像占的**设备像素宽 = 256·k ≤ 256·sDev**，
所以在任何缩放下图像都**小于**它在对话框里预留的 256×192 参考槽位，不会被裁、不会溢出客户区。

### 1.5 图集选对没有（越界查不出来的那类问题）

第一轮已把三组动画在两张候选表上并排裁出比对（`docs\verify\sprites\cmp_*.png`），结论保持：

| 对比图 | 蓝色板 | otherSheet | 结论 |
|---|---|---|---|
| `cmp_tripf0.png`（逻辑 728,0,57,57） | 普通渐变方砖 | **爆开的雷球** | 爆炸动画在 otherSheet OK |
| `cmp_disarmf0_blue.png`（逻辑 0,0,50,150） | 渐变方砖 | 灰色方块（光束自带的方砖副本） | 拆雷光束在 otherSheet OK |
| `cmp_scanbar.png`（逻辑 0,912,275,62） | 越界 | **白→透明横向渐变条** | 扫描条在 otherSheet OK |

---

## 2. 素材清单：已用 / 未用 / 用了但素材没有

`win7-assets/` 共 **34** 个文件。

### 2.1 已经进了产品（16 个）

| 素材 | 字节 | 进了哪 | 状态 |
|---|---|---|---|
| `images/blueSheet.png` | 2 276 292 | `rawfile/blueSheet.png`（字节一致） | 在用 |
| `images/minesweeperSheet.png` | 10 642 | `rawfile/minesweeperSheet.png` | 在用 |
| `images/otherSheet.png` | 853 213 | `rawfile/otherSheet.png` | 在用 |
| `images/helpBoard.png` | 69 646 | `rawfile/helpBoard.png`（本轮新增，字节一致） | 在用（帮助窗口整图） |
| `audio/` 12 个 | 见 §3 | `rawfile/*.wav` | 在用（`flowerLose×3` 除外） |

### 2.2 还没用（18 个）

| 素材 | 字节 | 是什么 | 该不该做 |
|---|---|---|---|
| `images/greenSheet.png` | 2 474 027 | 绿色棋盘（与 blueSheet 同尺寸 2034×1206） | **建议做**（§6 第 2 条） |
| `images/flowerGardenSheet.png` | 11 436 | 花园版游戏表（94×54，内容是「银钮装雏菊」+「裸雏菊」） | 可选（§6 第 5 条） |
| `images/thumbBlue.png` | 22 033 | 外观对话框缩略图：蓝格 | 随外观对话框一起做 |
| `images/thumbGreen.png` | 24 292 | 外观对话框缩略图：绿格 | 同上 |
| `images/thumbMines.png` | 13 493 | 外观对话框缩略图：地雷 | 同上 |
| `images/thumbFlowers.png` | 13 296 | 外观对话框缩略图：雏菊 | 同上 |
| `icons/MineSweeper-32/48/64/128.png` | 1 623 / 7 196 / 9 504 / 21 462 | **微软原版应用图标** | **建议做**（§6 第 3 条） |
| `icons/Minesweeper.ico` | 4 286 | 同上，多尺寸 ico | 同上 |
| `images/Frame.bmp` | 631 854 | 窗口底板（**上下颠倒、角落藏着状态条素材**，九宫格不能直接用） | 不建议直接用 |
| `images/png/Frame.png` | 41 375 | Frame.bmp 的 png 版，同样问题 | 不建议直接用 |
| `images/Minesweeper.bmp` | 202 230 | **XP/3.1 时代**的旧精灵表（数字 2..8、红叉、发黄的旧方砖） | 不建议（不是 Win7 素材） |
| `images/png/Minesweeper.png` | 78 651 | 同上的 png 版 | 不建议 |
| `audio/flowerLoseShort/Medium/Long.wav` | 622 670 / 1 065 038 / 1 400 910 | 花园模式的三段失败音 | 只在花园模式用 |

### 2.3 用了但素材里没有对应物

| 我们的实现 | 素材里的对应物 | 说明 |
|---|---|---|
| 状态条两个计数器（`RECT_COUNTER` 凹槽 + 文字） | **没有** | 原版的 LED 是**七段数码管**（`recheck_helpboard_strip_5x.png` 里能清楚看到 `18` 与 `-40` 的段状笔画和独立的**负号段**）。**素材里没有可复用的段形位图** —— 那是微软插图里画出来的，不是精灵。所以这一项要**自己画段**，不是「把素材搬进来」。见 §6 第 1 条。 |
| 应用图标（`AppScope/resources/base/media/foreground.png` 210 016 B + `background.png` 6 705 B） | `icons/MineSweeper-*.png` / `.ico` 共 44 071 B | 微软原版图标是「一颗尖刺地雷」，我们用的是自绘 layered image |
| 帮助窗口的中文说明文字（`WinDialog.helpSpec()` 6 行） | 无（微软帮助窗口是英文原图） | 我们的取舍：原图 + 中文说明 |
| 胜利框「最快时间」 | 原图写的是「**最佳时间**」 | 一字之差，见 §6 备注 |

> **更正第一轮的一处结论**：第一轮 §5.1 曾把 otherSheet 底部（`y 1948..2015`）写成「真七段数码管」。**这是错的。**
> 放大后（`unused_otherSheet_led_digits.png`）那段其实是：一条**横向渐变条** + 一列**彩色数字 1..8 的第二份副本**（blueSheet 的 `digitRect` 已经有了这份）。
> 七段数码管在素材里**根本不存在**。

---

## 3. 音频：事件 → 文件 映射表

权威映射来自 `linux-minesweeper-main/src/ui/Sounds.h`（头部注明「mapped to the roles the game's own MINESWEEPER.xml gives them」）+
`Minesweeper-master/Minesweeper/utf8/Minesweeper.cpp` 里 `IDR_WAVE1..6` 的调用点（其 `res\wav\` 目录正好只有 6 个 wav，可与文件名一一对上）。

| 原版事件（MINESWEEPER.xml 角色） | 音频文件 | 我们产品里的触发点 | 状态 |
|---|---|---|---|
| NewBoard 新开局 | `gameStart.wav` | `GameController.ets:210` | 已接 |
| 首点开格 | `firstPaint.wav` | `GameController.ets:795` | 已接 |
| 0 格洪泛 | `zeroDevelop.wav` | `GameController.ets:798` | 已接 |
| SingleReveal 单格翻开 | `tileSingle.wav` | `GameController.ets:802` | 已接 |
| MultiReveal 多格洪泛 / 和弦 | `tileMultiple.wav` | `GameController.ets:800`、`:838` | 已接 |
| InvalidMove 点了不能做的事 | `invalidMove.wav` | `GameController.ets:805` | 已接 |
| 插旗 / 清旗 | `dbButtonClickFlag.wav` | `GameController.ets:855` | 已接 |
| 爆炸开始 | `mineBombStart.wav` | `GameController.ets:791` | 已接 |
| 爆炸中（循环） | `mineBombRun.wav` | `GameController.ets:978` | 已接 |
| 爆炸结束 | `mineBombEnd.wav` | `GameController.ets:981` | 已接 |
| BoardCleared 通关 | `gameWin.wav` | `GameController.ets:879` | 已接 |
| WrongGuess 踩雷 | `gameLose.wav` | `GameController.ets:879`（**判负结束时**） | **已接，但时机疑似不对**（见 §6 备注） |
| WrongGuess（花园模式） | `flowerLoseShort/Medium/Long.wav` | 无 | **未接**（只在花园模式需要） |

**结论：12/15 已接且全部有触发点；未接的 3 个正是花园模式专用，与「要不要做花园模式」是同一个决定。**

---

## 4. 三个疑点的独立结论

### 4.1 笑脸到底存不存在 —— **不存在**（本轮第三次独立复核，翻的是图集本体）

本轮没沿用旧结论，把**每张图集本体**重新扫了一遍，并做了目视核对：

**（a）黄色圆盘计数**（Win7 的笑脸是黄色圆盘，所以这是最直接的判据）：

| 文件 | 尺寸 | 黄色像素 | 是什么 |
|---|---|---|---|
| `blueSheet.png` | 2034×1206 | **0** | 无 |
| `minesweeperSheet.png` | 94×54 | **0** | 无 |
| `otherSheet.png` | 2048×2016 | 3 965 | 爆炸火球 / 花朵的暖色 |
| `helpBoard.png` | 256×192 | **0** | 无 |
| `greenSheet.png` | 2034×1206 | 10 | 几乎为零 |
| `thumbFlowers.png` | 92×92 | 760 | **雏菊的花心**（不是脸） |
| `flowerGardenSheet.png` | 94×54 | 125 | 同上 |
| `icons/MineSweeper-*.png` / `.ico` | 32..128 | **0** | 无 |

**（b）目视核对**（`docs\verify\sprites\recheck_montage_assets.png`）：`flowerGardenSheet` = 银钮装雏菊 + 裸雏菊；`thumbMines` = 尖刺地雷；`thumbFlowers` = 白雏菊；`thumbBlue/thumbGreen` = 蓝格/绿格；应用图标 = 尖刺地雷。**没有一张脸。**

**（c）状态条两个圆钮逐个放大**：
- `minesweeperSheet.png` 全图 8 倍 → **只有两个精灵**：银钮装雷 + 裸雷。
- `otherSheet.png` 逻辑 (905,425,25,25) 10 倍 → 银钮上的**钟面**（有刻度环、指针）。
- 微软自己的 `helpBoard.png` 状态条 5 倍（`recheck_helpboard_strip_5x.png`）→ 左端**钟**，右端**雷**。

**（d）原版资源索引**：`linux-minesweeper-main/src/ui/Theme.h` 是从游戏自己资源里抽出来的精灵表，
状态条相关条目只有两条 —— 第 113 行 `kClock{905,425,25,25}`、第 109 行 `kPanelMine{0,0,25,25}`，**没有第三条 25×25 面板图**。

**（e）反证（不改变结论）**：`ReversingMinesweeper` 确实有 5 态笑脸
（`drawing.h:4-8` SMILE_NORMAL/WOW/LOST/WINNER/CLICKED，`resource.h:82` `ID_BITMAP_SMILES 430`，24×24，
`windowing.c:128` 点击时 `DisplaySmile(SMILE_CLICKED)` 即重开），
但它用的是**自己的一份独立位图** `ID_BITMAP_SMILES 430`，属于 XP/3.1 时代的脸谱系，**不是 Win7 那三张精灵表里的东西**。

> **结论：Win7 的三张精灵表里没有笑脸，状态条左端就是时钟。**
> 「点时钟重开」是我们自加的功能，不是复刻 —— 详见专文 `docs\STATUS-STRIP-VERDICT.md`（结论 A）。

### 4.2 greenSheet / flowerGardenSheet：原版有没有？要不要做？

**原版有没有：素材层面「有」，且是同一套原版资源的一部分。** 证据链：

1. `linux-minesweeper-main/README.md:7` —— 精灵表是「**extracted by Lmy0217/Minesweeper**」，即从真 Win7 的资源里抽出来的。
2. `Theme.h:33-34` —— `enum class BoardStyle { Blue, Green }; enum class GameStyle { Mines, Flowers };`
3. `Theme.h:146-150` —— `disarmFrame(BoardStyle s, …)` 的**绿色变体基址是 x0=364**（蓝色是 0），
   也就是说**原版资源里另有一整套绿色版的胜利光束**（otherSheet 逻辑 x 364..727，实测 px 728..1455）。
4. `Theme.h:126-131` —— `tripFrame(GameStyle g, …)` 的**花朵变体**是 `905 + 38*(f%3), 38*(f/3), 36, 36`。
5. `Sounds.h:14-17` —— `flowerLose*.wav` 对应 XML 角色「the Flower Garden loss」。
6. 4 张缩略图（thumbBlue/Green/Mines/Flowers，共 73 114 字节）就是**外观选择对话框**要用的图。
7. `linux-minesweeper-main/README.md:18` 的截图说明写着「the green theme, **one of the selectable appearances**」。

> **诚实标注**：这些证据说明**原版 Win7 的资源里确实有绿色棋盘与花园玩法**，且 linux 复刻按 Win7 的
> 「外观/颜色」对话框把它们做成了可选外观。**官方 Win7 零售版 UI 是否把该入口对所有用户暴露**，
> 离线无法 100% 证实（那需要跑真机），本文按「资源层确有」记述。

**要不要做（工作量）**：

| 方案 | 缺什么 | 工作量 | 用户可感知的还原度 |
|---|---|---|---|
| **只做绿色棋盘** | `greenSheet.png` 入库 + Theme 加一个板型枚举 + 拆雷光束基址切 364 + 一个切换入口 | **小，20-30 行 + 1 个 2.4MB 文件** | **中高**：一屏就能看出配色不同 |
| **外观/颜色对话框** | 4 张缩略图 + 一个 Aero 对话框（列表 + 预览 + 确定/取消） | **中，120-200 行** | 中 |
| **花园模式** | `flowerGardenSheet.png` + 3 个 flowerLose 音频（3.09MB）+ 花园版爆炸动画（otherSheet 逻辑 905 起 36×36）+ 游戏型态切换 | **中-大，150-250 行 + 4 个文件** | 低：它是另一种玩法，不是「缺陷」 |

**建议：做绿色棋盘 + 外观对话框；花园模式先不做**（改动面大、收益是「另一种玩法」而非「还原缺陷」，
而且会牵动 3 MB 音频与爆炸动画两套逻辑）。

### 4.3 音频：见 §3。12/15 已接，缺的 3 个是花园模式专用。

---

## 5. 参考图（7 张 jpg）→ 我们实现 的对照表

| 参考图 | 原版内容 | 我们的对应物 | 状态 |
|---|---|---|---|
| `gaming.jpg` (615×408) | 棋盘 + 底部 `[时钟][LED 25] … [LED 96][雷]` | `GameController.drawStatusStrip()` + 棋盘 | OK 版式一致（§4.1 已三次确认） |
| `exploding.jpg` | 连锁爆炸进行中 | `Anim.explodeRect` 23 帧 + `GameController` 级联 | OK |
| `initializing.jpg` | 发牌波纹动画 | `DealIn.ets` | OK |
| `win.jpg` (396×340) | 游戏胜利：恭喜！您赢了！/ 时间 / **最佳时间 + 日期** / 已玩游戏 / 已胜游戏 / 百分比 / 再玩一局(P) / 退出(Q) | `WinDialog.winSpec()`（含 `isNewBest` 时多一行「您所用的时间是这个难度级别的最短时间!」） | OK 逐元素对齐，仅「最佳时间」写成「**最快时间**」 |
| `loss.jpg` (483×288) | 游戏失败：不好意思，您输了！/ 时间 / 已玩游戏 / 已胜游戏 / 百分比 / 退出(X) / 重新开始(R) / 再玩一局(P) | `WinDialog.loseSpec()`（中间按钮改成「换个难度(D)」，有注释说明） | OK 元素齐，**按钮文案是一处有意改动** |
| `information.jpg` | 扫雷统计信息：最佳时间 group box + 已玩游戏/已胜游戏/获胜率/最多连胜/最多连败/当前连局 + 关闭(C) / 重置(R) + 可点选的难度列表 | `StatsWindow.ets`（同样 6 行统计 + 列表框 + 关闭/重置） | OK |
| `about.jpg` | 关于扫雷（classic 边框 + 雷图标 + 版本/致谢） | `WinDialog.aboutSpec()`（`chrome: 'classic'`） | OK 有对应物 |

**七张参考图都有对应物，没有「参考图里的元素我们完全没有」的缺口。**

---

## 6. 「还差什么」优先级清单（Top 5）

按「用户可感知的还原度」×「工作量」排序。

### 第 1 条 —— 状态条计数器改成七段数码管　【还原度影响：高｜工作量：中，80-150 行】

- **缺什么**：原版两个计数器是**深蓝底 + 七段数码管**（`recheck_helpboard_strip_5x.png`：`18` 与 `-40`，负号是独立的一段）；
  我们现在用 sans-serif 粗体字画在 `RECT_COUNTER` 凹槽上（`GameController.ets:744-745`）。
  **素材里没有可复用的段形位图**（otherSheet 底部那段是彩色数字的副本 + 一条渐变条，见 §2.3 的更正），所以要**自己画段**。
- **参考证据**：`win7-assets/images/helpBoard.png` 状态条 5 倍图；`Theme.h:104` `kCounterPanel{0,580,40,21}`（凹槽面板是有的，缺的是数字）。
- **注意**：负号必须支持 —— 原版雷数允许为负（`-40`），这是七段而不是字体的判据。
- **影响**：状态条是玩家全程都在看的元素，字体与段形差异一眼可见。

### 第 2 条 —— 绿色棋盘主题　【还原度影响：中高｜工作量：小，20-30 行 + 1 个 2.4MB 文件】

- **缺什么**：`greenSheet.png`（2 474 027 字节）没进 `rawfile/`；`Theme.ets` 没有板型概念；
  `Anim.disarmRect` 的绿色变体基址（逻辑 364）没接。
- **参考证据**：`win7-assets/images/greenSheet.png`（与 blueSheet 同尺寸 2034×1206）；
  `Theme.h:148` `x0 = s == BoardStyle::Green ? 364 : 0`；`Theme.h:33` `enum class BoardStyle { Blue, Green }`；
  `linux-minesweeper-main/README.md:18` 的绿色主题截图。
- **影响**：一个入口就能切换，配色差异明显。

### 第 3 条 —— Win7 应用图标　【还原度影响：中｜工作量：小，5-10 行 + 5 个文件】

- **缺什么**：微软原版图标（`icons/MineSweeper-32/48/64/128.png` + `Minesweeper.ico`，共 44 071 字节）没用；
  产品现在是自绘 `AppScope/resources/base/media/foreground.png`（210 016 字节）+ `background.png`。
- **参考证据**：`docs\verify\sprites\recheck_montage_assets.png` 底部：原版图标是**一颗尖刺地雷**（小图版本同）。
- **影响**：桌面/应用列表上一眼可见。

### 第 4 条 —— 「外观 / 颜色」选择对话框　【还原度影响：中｜工作量：中，120-200 行】

- **缺什么**：4 张缩略图（thumbBlue 22 033 / thumbGreen 24 292 / thumbMines 13 493 / thumbFlowers 13 296，合计 73 114 字节）没用；
  没有外观选择对话框。
- **参考证据**：`Theme.h:33-34` 的两个枚举；`linux-minesweeper-main/src/ui/AppearanceDialog.cpp`（按 Win7 的 F7 对话框复刻，标题填充色 `0x2E8BE0` 是采样自真 Win7）；
  缩略图本体见 `recheck_montage_assets.png`。
- **依赖**：第 2 条（绿色棋盘）先做，这个对话框才有东西可选。
- **影响**：中等；不做的后果是「绿色棋盘没有入口」。

### 第 5 条 —— 花园模式（flower garden）　【还原度影响：低｜工作量：中-大，150-250 行 + 4 个文件】

- **缺什么**：`flowerGardenSheet.png`（11 436）、3 个 `flowerLose*.wav`（3 088 618 字节合计）、
  花园版爆炸动画（otherSheet 逻辑 905 起，36×36 逻辑格）、游戏型态切换。
- **参考证据**：`Theme.h:129` `905 + 38*(f%3), 38*(f/3), 36, 36`；`Sounds.h:14-17`；
  `recheck_montage_assets.png` 里 `flowerGardenSheet` = 银钮装雏菊 + 裸雏菊。
- **影响**：低 —— 它是另一种玩法而不是还原缺陷；且要带 3 MB 音频。
- **建议**：先不做。

### 备注（不计入 Top 5，但应修）

| # | 问题 | 证据 | 工作量 |
|---|---|---|---|
| a | **`gameLose.wav` 的时机疑似不对**：我们在**判负结束**时播（`GameController.ets:879`），而原版 XML 的角色是「WrongGuess」，按 linux 复刻的映射（`Sounds.h:10-12`）应当是**踩雷那一刻**（原版用 30 个缓冲让连锁爆炸互相叠音）。连锁本身我们已用 mineBombStart/Run/End 覆盖，所以更像是**时机**而非缺音效。**标「疑似」**，建议真机听一遍再定。 | `Sounds.h:10-12`；`GameController.ets:879` | 1-3 行 |
| b | 胜利框的「**最快时间**」应为「**最佳时间**」（`win.jpg` 原文） | `WinDialog.ets:250` | 1 行 |
| c | `Theme.ets` 里 7 个**死常量**仍在：`tripRect`(74) / `disarmRect`(82) / `RECT_SCAN_BAR`(89) / `TRIP_FRAMES`(73) / `TRIP_OFFSET`(78) / `DISARM_FRAMES`(81) / `DISARM_OFFSET`(86)，全部与 `Anim.ets` 的活版本同值且零引用 —— 两边会漂移 | `Theme.ets:73-89` | 删 7 行 |
| d | `SpriteAtlas.frameSheet`（`SpriteAtlas.ets:27`）声明了但**从不赋值也从不使用** | `SpriteAtlas.ets:27` | 删 2 行 |
| e | `WinDialog.win.icon`（`WinDialog.ets:323`）是字面量 `[0,0,25,25]`，与 `Theme.RECT_PANEL_MINE` 完全重复 | `WinDialog.ets:323` | 1 行 |

---

## 7. 复核方法（任何人都能重跑）

```powershell
python "D:\software\harmony\projects\minesweeper\docs\verify\check_sprites_v2.py"        # 越界 + helpBoard 单位证明
python "D:\software\harmony\projects\minesweeper\docs\verify\smiley_recheck.py"         # 黄色圆盘计数 + 全资产总览
python "D:\software\harmony\projects\minesweeper\docs\verify\montage_assets.py"         # 疑似藏脸的资产拼版
python "D:\software\harmony\projects\minesweeper\docs\verify\strip_evidence.py"         # 状态条相关裁图
python "D:\software\harmony\projects\minesweeper\docs\verify\where_do_frames_live.py"   # 图集选对没有
```

只读 `C:\Users\19161\saolei` 与 `C:\Users\19161\Desktop\minesweeper-refs`，只写 `docs\verify\sprites\`。
中间数据落在 `docs\verify\sprites\_audit_v2.json`（含每条引用的源矩形、越界像素数、重复组）。
