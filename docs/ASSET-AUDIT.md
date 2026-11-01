# ASSET-AUDIT.md —— 原版 Win7 扫雷素材逐文件审计

> 第二版（2026-11-01）：本轮做的是**逐文件**审计（sha256 + 像素差 + 波形参数），
> 并回答「爆炸帧序 / 缺什么 / 我们改过什么」三个问题。
> 第一版的**区域级**明细（逐区域表、预览图清单）保留在 §8 附录，一处没丢；
> 其中被本轮证据推翻的 3 处结论已在附录里就地更正。
>
> 审计范围：**只读**，两个仓一个字节都没改。
> 原版侧：`C:\Users\19161\Desktop\minesweeper-refs\`（四个子目录，见 §1）
> 我们侧：`C:\Users\19161\saolei\entry\src\main\resources\`（`rawfile/` + `base/media/`）、`AppScope\resources\base\media\`
> 无 emoji。

---

## 0. 摘要

| 问题 | 结论 | 关键数字 |
|---|---|---|
| 我们的素材有没有被改过？ | **一个都没有** | 25/25 个 rawfile 素材与原版 **sha256 完全相同**；10 张图逐像素复算，**差异像素 0、RMS 0.0000** |
| 原版有、我们缺什么？ | **9 个文件（3 类逻辑资产）** | 5 个应用图标 + `Frame.bmp/png`（窗口底板）+ `Minesweeper.bmp/png`（旧式大图集） |
| 我们多出来什么？ | **5 个文件，全是我们自己的** | `base/media/{background,foreground,startIcon}.png` + AppScope 两个同名图，与原版无关 |
| 爆炸动画帧数/顺序对不对？ | **对** | 素材里那条 strip 恰好 **23 格非空 / 24 格**（第 24 格空），23 帧两两不同；时长 1000 ms / 23 帧与原版动画 XML 一致 |

**一句话**：素材侧没有任何被改动或走样的东西；唯一的缺口是「原版的 5 个应用图标」和「原版的窗口底板 Frame」，两者都不是游戏画面本体。

---

## 1. 审计口径：原版素材到底在哪（重要更正）

任务书里写的原版侧是 `Minesweeper-master`，但**那个仓里没有一张精灵图**。实测：

| 目录 | 媒体文件数 | 内容 |
|---|---|---|
| `minesweeper-refs\Minesweeper-master\`（Lmy 的 Win7 克隆版） | **17** | 只有 **6 个 wav + 2 个 bmp + 2 个 ico + 7 张 jpg 参考截图**；**0 张 png 精灵图** |
| `minesweeper-refs\linux-minesweeper-main\assets\` | **32** | **15 wav + 5 图标 + 12 张图**（5 张精灵表 + helpBoard + 4 张缩略图 + Frame.bmp + Minesweeper.bmp） |
| `minesweeper-refs\win7-assets\` | **34** | 同上，另加 `images/png/Frame.png`、`images/png/Minesweeper.png` 两张无损转码版 |
| `minesweeper-refs\ReversingMinesweeper-master\` | 0 | XP 版扫雷的**源码逆向重建**（几何出处，无素材） |

所以**本轮以 `win7-assets` 为「原版侧」全集**（34 个文件），`linux-assets` 与 `Minesweeper-master/res` 作交叉验证。

**三处原版素材集的 sha256 关系**（实测）：

- `linux-assets` 与 `win7-assets`：**32 个共有文件 sha256 逐个相同**；差的 2 个是 `win7-assets` 多出来的 `png/Frame.png`、`png/Minesweeper.png`。
- `Minesweeper-master/res` 里的 6 个 wav、2 个 bmp、2 个 ico：与 `win7-assets` 中同名文件 **sha256 相同**（`small.ico` 与 `Minesweeper.ico` 也相同，同一文件的两份拷贝）。
- `png/Frame.png` 与 `Frame.bmp`：**逐像素完全相同**（差异像素 0 / 210 600，RMS 0.0000）；`png/Minesweeper.png` 与 `Minesweeper.bmp` 同理（0 / 67 392，RMS 0.0000）。
  ⇒ `images/png/` 只是 BMP→PNG 的无损转码，**不提供任何新信息**。
  ⇒ **更正**：`SpriteAtlas.ets` 里「Frame.png 这张图上下颠倒」那句注释不成立 —— png 与 bmp 之间**不存在翻转**（与上下翻转版相比差 59 018 像素）。SpriteAtlas 真正不加载它的理由见 §8.4.3（零件位置与九宫格不可用），与翻转无关。

### 1.1 两套坐标系（读错就取到空白）

| 坐标系 | 定义 | 例 |
|---|---|---|
| **逻辑坐标（1x）** | 原版 UI XML 的单位，格子边长 18；`Theme.ets` / `Theme.h` 全部用这个 | `RECT_FLAG = [400, 560, 18, 18]` |
| **存储像素（2x）** | PNG 里的实际像素 = 逻辑坐标 × 2（`SPRITE_SCALE = 2`） | 红旗在像素 `x 800..835, y 1120..1155` |

**例外（1:1 图，源坐标不能乘 2）**：`helpBoard.png`（256×192）、四张 `thumb*.png`（92×92 / 109×109）、`Frame.png`（600×351）、`Minesweeper.png`（144×468）、四个应用图标。

---

## 2. 原版侧全部素材总表（`win7-assets`，34 个文件）

### 2.1 图像与图标（19 个）

| 文件 | 格式 | 尺寸 | 模式 | 字节 | sha256 | 像素复用价值 |
|---|---|---|---|---|---|---|
| `images/blueSheet.png` | PNG | 2034×1206 | RGBA | 2 276 292 | `c2ce51fd32fe429ef4cbe2cf143a9eef66fc03d0b031b6baf24abf01f7f7d527` | 高（棋盘主体） |
| `images/greenSheet.png` | PNG | 2034×1206 | RGBA | 2 474 027 | `a480cc06f9d07bb952d2e73ba04e1a0204fc0f9e8790cd7e671c65fec0c9c595` | 高（绿色主题） |
| `images/otherSheet.png` | PNG | 2048×2016 | RGBA | 853 213 | `2152c86332d9cf9f1c4a0801bfa0b66ebff11a47366203164743e70014ba315e` | 高（动画 + 时钟图标） |
| `images/minesweeperSheet.png` | PNG | 94×54 | RGBA | 10 642 | `f084e8eebe85014b60930b4f800ed31771ea2c97c7429b0010fcba39070aaab3` | 高（地雷 2 精灵） |
| `images/flowerGardenSheet.png` | PNG | 94×54 | RGBA | 11 436 | `bf307f624e3e8a9be6ee2413fab4760114131050a93c6a583c87f4492af4065f` | 中（花园变体，现已接入） |
| `images/helpBoard.png` | PNG | 256×192 | RGB | 69 646 | `cfc1bdcbb5b108f5a864dd25a5ddbb23c701ff848ea50031675ba65b69e147ce` | 高（帮助插图 + 七段字形证据） |
| `images/thumbBlue.png` | PNG | 109×109 | RGBA | 22 033 | `b9b81c40114d69a41c83bc2dadefdaf20a098a58aecd02b5810a80698553ef7c` | 中（外观对话框） |
| `images/thumbGreen.png` | PNG | 109×109 | RGBA | 24 292 | `8d6d09bec0afe8989ae043c25285286473dafd2406f84cea20d7804923940d8f` | 中（外观对话框） |
| `images/thumbMines.png` | PNG | 92×92 | RGBA | 13 493 | `2dd91af7f8f8a3d31fd5cacabd95ccbf7634814dedac939077b51cbd2647f8c9` | 中（外观对话框） |
| `images/thumbFlowers.png` | PNG | 92×92 | RGBA | 13 296 | `e68ae8e7414232a30f7872f123badc7a559187637cefaee7af7927b01aa851ce` | 中（外观对话框） |
| `images/Frame.bmp` | BMP | 600×351 | RGB | 631 854 | `299f030c4c2eab1fea118c78c585cc35612ea9c5c626f0852cbe3e9191c701e9` | 低（窗口底板，见 §6 (b)） |
| `images/png/Frame.png` | PNG | 600×351 | RGB | 41 375 | `b0a97aa36bf69d2221970288e6f55ccf7a90d8169edb86df66ce5692605f715e` | 同上（无损转码） |
| `images/Minesweeper.bmp` | BMP | 144×468 | RGB | 202 230 | `65096f8dccb6f35f50e8dcb78b37586974e245ec658f1fffe92052737f09c501` | 低（旧式大图集，拆包源） |
| `images/png/Minesweeper.png` | PNG | 144×468 | RGB | 78 651 | `16528821bfb716bc1afacec16a2df399b4ea272d97de46cd186898bb97fadace` | 同上（无损转码） |
| `icons/MineSweeper-32.png` | PNG | 32×32 | RGBA | 1 623 | `5b9f2e05fe015f1b39b27c66402d3573a6b619c3ca03311e1452f946cb0a4e8a` | 应用图标 |
| `icons/MineSweeper-48.png` | PNG | 48×48 | RGBA | 7 196 | `57d55b13f0f2b330beb083af42a585c87e59d3ffe9bf4b84b497cebe9ea744d9` | 应用图标 |
| `icons/MineSweeper-64.png` | PNG | 64×64 | RGBA | 9 504 | `a9eacc9a5dd1130a6dbc02727187825c22ed9518646ee7cf7335be81936c4257` | 应用图标 |
| `icons/MineSweeper-128.png` | PNG | 128×128 | RGBA | 21 462 | `a371cddf6511173bbafd0e87e8d50739c4eca42550475980780c5d9d8149f77c` | 应用图标（构图最好） |
| `icons/Minesweeper.ico` | ICO | 32×32 | RGBA | 4 286 | `3a84c9867fe1e93f4a8f96ccce535c516cc6ee4af11859044e4d0e9a1c4c1581` | 只含 32 一档 |

### 2.2 音效（15 个 wav，全部 44 100 Hz / 16 bit / 立体声 PCM）

| 文件 | 字节 | 时长 | 帧数 | sha256 |
|---|---|---|---|---|
| `audio/gameStart.wav` | 450 638 | 2.5540 s | 112 640 | `62cac498a0fe10e5789e583e332a5db04a1d42d11633ced308babcdb6fa783c1` |
| `audio/tileSingle.wav` | 32 846 | 0.1860 s | 8 206 | `344ecf8c8f7be81853b763c02f8520c287845a92d90f44851cbd61a42a340660` |
| `audio/tileMultiple.wav` | 57 422 | 0.3250 s | 14 336 | `cb63fe2f150f3ba8ca4ade28afa791f8aaa990276851b9def6dc54bcdf72397b` |
| `audio/zeroDevelop.wav` | 41 254 | 0.2330 s | 10 276 | `dd56209395df4487dbfa26638c039da9a07d1874a240fd1525d85c41ae4e2596` |
| `audio/firstPaint.wav` | 417 858 | 2.3680 s | 104 448 | `a27214debd6bc3c0caee0fd13c7dfd0605ea91ce6d713759e9cd700bcde05677` |
| `audio/invalidMove.wav` | 49 230 | 0.2790 s | 12 304 | `0927a5da6cb1ed4eccd2565906c9f194bb06128bc87be69ebc3a2a0ca1a1b121` |
| `audio/dbButtonClickFlag.wav` | 32 530 | 0.1840 s | 8 114 | `99266938e33ef918ad8f84f8c1327281164cda1f48ead64d9260d2c949e13798` |
| `audio/gameWin.wav` | 385 102 | 2.1830 s | 96 270 | `fc18811084887ac6bc3789852c89be99dc67f5169815648eab232209913edbd6` |
| `audio/gameLose.wav` | 352 334 | 1.9970 s | 88 071 | `df601a1628d658afbd6293b131f117334992b8a409f6d5b31ff773b57bdedd85` |
| `audio/mineBombStart.wav` | 228 354 | 1.2940 s | 57 058 | `02b4ca1f07502faaa92a04940eea8b383b78e40a0628c77fccc186719bad8ce0` |
| `audio/mineBombRun.wav` | 696 638 | 3.9490 s | 174 168 | `559fbd0712228b687d4783d5b148a714d9fe43c6cf94db50791aa1af10413cd6` |
| `audio/mineBombEnd.wav` | 344 282 | 1.9510 s | 86 040 | `9605e9b602ea58941107a250a136364dfc1dd157fddf2e66c5f6e8c455b5f92f` |
| `audio/flowerLoseShort.wav` | 622 670 | 3.5290 s | 155 656 | `1eccb7119e9b72f0c000e7c36fa133e7d7f8d65ed900a2e0d88174f5230d2e35` |
| `audio/flowerLoseMedium.wav` | 1 065 038 | 6.0370 s | 266 232 | `45e8e7f92617521c7a7950a4faa7f3bcf1ad2e75b1d81907da4d603a3361a7b0` |
| `audio/flowerLoseLong.wav` | 1 400 910 | 7.9410 s | 350 228 | `6b0e4e4829ae22d81beec1c230e6e3d2d977044aeb96d8f5bda68a2a378e64de` |

> `Minesweeper-master/res/wav/` 里只有前 6 个雷版音效中的 6 个（`dbButtonClickFlag`、`firstPaint`、`mineBombEnd`、`mineBombRun`、`mineBombStart`、`zeroDevelop`），sha256 与上表相同；`gameStart/gameWin/gameLose/invalidMove/tileSingle/tileMultiple` 与 3 条 `flowerLose*` 只在 `linux-assets` 与 `win7-assets` 里。

---

## 3. 我们侧全部素材总表（30 个文件）

### 3.1 `entry/src/main/resources/rawfile/`（25 个，全部来自原版）

| 文件 | 格式 | 尺寸 / 参数 | 字节 | sha256（前 16） | 与原版 |
|---|---|---|---|---|---|
| `blueSheet.png` | PNG | 2034×1206 RGBA | 2 276 292 | `c2ce51fd32fe429e` | **完全一致** |
| `greenSheet.png` | PNG | 2034×1206 RGBA | 2 474 027 | `a480cc06f9d07bb9` | **完全一致** |
| `otherSheet.png` | PNG | 2048×2016 RGBA | 853 213 | `2152c86332d9cf9f` | **完全一致** |
| `minesweeperSheet.png` | PNG | 94×54 RGBA | 10 642 | `f084e8eebe85014b` | **完全一致** |
| `flowerGardenSheet.png` | PNG | 94×54 RGBA | 11 436 | `bf307f624e3e8a9b` | **完全一致** |
| `helpBoard.png` | PNG | 256×192 RGB | 69 646 | `cfc1bdcbb5b108f5` | **完全一致** |
| `thumbBlue.png` | PNG | 109×109 RGBA | 22 033 | `b9b81c40114d69a4` | **完全一致** |
| `thumbGreen.png` | PNG | 109×109 RGBA | 24 292 | `8d6d09bec0afe898` | **完全一致** |
| `thumbMines.png` | PNG | 92×92 RGBA | 13 493 | `2dd91af7f8f8a3d3` | **完全一致** |
| `thumbFlowers.png` | PNG | 92×92 RGBA | 13 296 | `e68ae8e7414232a3` | **完全一致** |
| `gameStart.wav` | WAV | 44100/16/2, 2.554 s | 450 638 | `62cac498a0fe10e5` | **完全一致** |
| `tileSingle.wav` | WAV | 44100/16/2, 0.186 s | 32 846 | `344ecf8c8f7be818` | **完全一致** |
| `tileMultiple.wav` | WAV | 44100/16/2, 0.325 s | 57 422 | `cb63fe2f150f3ba8` | **完全一致** |
| `zeroDevelop.wav` | WAV | 44100/16/2, 0.233 s | 41 254 | `dd56209395df4487` | **完全一致** |
| `firstPaint.wav` | WAV | 44100/16/2, 2.368 s | 417 858 | `a27214debd6bc3c0` | **完全一致** |
| `invalidMove.wav` | WAV | 44100/16/2, 0.279 s | 49 230 | `0927a5da6cb1ed4e` | **完全一致** |
| `dbButtonClickFlag.wav` | WAV | 44100/16/2, 0.184 s | 32 530 | `99266938e33ef918` | **完全一致** |
| `gameWin.wav` | WAV | 44100/16/2, 2.183 s | 385 102 | `fc18811084887ac6` | **完全一致** |
| `gameLose.wav` | WAV | 44100/16/2, 1.997 s | 352 334 | `df601a1628d658af` | **完全一致** |
| `mineBombStart.wav` | WAV | 44100/16/2, 1.294 s | 228 354 | `02b4ca1f07502faa` | **完全一致** |
| `mineBombRun.wav` | WAV | 44100/16/2, 3.949 s | 696 638 | `559fbd0712228b68` | **完全一致** |
| `mineBombEnd.wav` | WAV | 44100/16/2, 1.951 s | 344 282 | `9605e9b602ea5894` | **完全一致** |
| `flowerLoseShort.wav` | WAV | 44100/16/2, 3.529 s | 622 670 | `1eccb7119e9b72f0` | **完全一致** |
| `flowerLoseMedium.wav` | WAV | 44100/16/2, 6.037 s | 1 065 038 | `45e8e7f92617521c` | **完全一致** |
| `flowerLoseLong.wav` | WAV | 44100/16/2, 7.941 s | 1 400 910 | `6b0e4e4829ae22d8` | **完全一致** |

> 完整 sha256 见 §2.1 / §2.2（两表一一对应，逐字节相同）。

### 3.2 我们自有的应用图标（5 个，**原版没有**）

| 文件 | 尺寸 | 字节 | sha256（前 16） | 说明 |
|---|---|---|---|---|
| `entry/src/main/resources/base/media/startIcon.png` | 152×152 RGBA | 14 062 | `a314ff05afe8a620` | 桌面图标（**我们自己的画**，非原版） |
| `entry/src/main/resources/base/media/background.png` | 1024×1024 RGBA | 91 942 | `497edeafc51af043` | Ability 背景 |
| `entry/src/main/resources/base/media/foreground.png` | 1024×1024 RGBA | 8 805 | `57e549283f255505` | Ability 前景 |
| `AppScope/resources/base/media/background.png` | 1024×1024 RGBA | 6 705 | `24c5b843f4183c57` | AppScope 背景 |
| `AppScope/resources/base/media/foreground.png` | 1024×1024 RGBA | 210 016 | `a9656e80a2973b13` | AppScope 前景 |

> 同名不同内容：`entry` 与 `AppScope` 的 `background/foreground.png` 是**两套不同文件**（sha256 不同），这是 HarmonyOS 的两级资源目录约定，不是重复。

---

## 4. 逐个配对结论

### 4.1 25/25 字节级一致

我们 rawfile 里的 25 个文件，与原版 `win7-assets` 中同名文件**一一对应且 sha256 完全相同**（见 §2 与 §3.1 的哈希对照）。
**没有任何一个原版素材被我们改过、压过或换过。**

### 4.2 像素差复算（10 张图，PIL 逐像素）

把我们的图与原版同名图都读成 RGBA 数组，逐像素求绝对差：

| 文件 | 尺寸是否相同 | 差异像素 | 总像素 | RMS |
|---|---|---|---|---|
| `blueSheet.png` | 相同 | **0** | 2 453 004 | **0.0000** |
| `greenSheet.png` | 相同 | **0** | 2 453 004 | **0.0000** |
| `otherSheet.png` | 相同 | **0** | 4 128 768 | **0.0000** |
| `minesweeperSheet.png` | 相同 | **0** | 5 076 | **0.0000** |
| `flowerGardenSheet.png` | 相同 | **0** | 5 076 | **0.0000** |
| `helpBoard.png` | 相同 | **0** | 49 152 | **0.0000** |
| `thumbBlue.png` | 相同 | **0** | 11 881 | **0.0000** |
| `thumbGreen.png` | 相同 | **0** | 11 881 | **0.0000** |
| `thumbMines.png` | 相同 | **0** | 8 464 | **0.0000** |
| `thumbFlowers.png` | 相同 | **0** | 8 464 | **0.0000** |

15 个 wav 同样逐字节相同（sha256 相同），采样率 44 100 Hz、位深 16 bit、声道 2 全部一致。

### 4.3 我们多出来的（5 个）

全部是我们自己做的 HarmonyOS 应用图标（§3.2），与原版素材无关，不存在「与原版不一致的改动」。

### 4.4 原版有、我们缺的（9 个文件 / 3 类逻辑资产）

| # | 资产 | 文件 | 尺寸 | 字节 | sha256（前 16） | 缺了会怎样 |
|---|---|---|---|---|---|---|
| 1 | **应用图标组** | `icons/MineSweeper-32/48/64/128.png`、`icons/Minesweeper.ico` | 32~128 / ico 32 | 1 623 / 7 196 / 9 504 / 21 462 / 4 286 | `5b9f2e05…` `57d55b13…` `a9eacc9a…` `a371cddf…` `3a84c986…` | 桌面图标不是原版那颗尖刺地雷球 |
| 2 | **原版窗口底板** | `images/Frame.bmp` + `images/png/Frame.png` | 600×351 RGB | 631 854 / 41 375 | `299f030c…` `b0a97aa3…` | 我们用纯色画窗口外圈与棋盘区（原版是 Aero 玻璃渐变边框 + 底部状态条底色带） |
| 3 | **旧式大图集（拆包源）** | `images/Minesweeper.bmp` + `images/png/Minesweeper.png` | 144×468 RGB | 202 230 / 78 651 | `65096f8d…` `16528821…` | 不影响画面（内容已被拆进三张 sheet），只作核对拆包是否有遗漏的权威 |

> 这 9 个文件**在原版素材集里确实存在**（不是「原版也没有」），只是我们没拷进 `rawfile/`。

---

## 5. 重点核对（逐项）

### 5.1 爆炸 23 帧 —— `otherSheet` 逻辑 x=728 起的 strip

**格子网格实测**（按 `Theme.tripRect` 的 3 列 × 8 行、格距 59、格宽 57 逐格量不透明像素）：

```
行0:   1764   1894   2017
行1:   2373   4628   2077
行2:   1946   1968   1991
行3:   2041   2112   2187
行4:   2267   2291   2244
行5:   2177   2058   2087
行6:   2135   2180   2001
行7:   2030   1024  (空)
非空格数: 23 / 24
```

- **恰好 23 格非空，第 24 格（逻辑 846,413）是空的** ⇒ 原版这条 strip 就是 **23 帧**，我们的 `TRIP_FRAMES = 23` 正好取满，不多不少。
- **23 帧两两互不相同**（按可见像素哈希比对，重复数 0）⇒ 是一段真正的 23 帧动画，不是同一张图重复。
- **逐帧亮度**（alpha>0 区域的亮度积分）：
  `78 515 → 175 182 → 224 280 → 188 539 → 939 828(峰值，帧面积也最大 4628) → 168 549 → 125 777 → … → 18 061 → 18 696`
  ⇒ 顺序读作「起手火花 → 火球（最亮的一帧）→ 烟尘逐帧消散 → 末帧只剩 1024 px（32×32 的地雷本体）」，
  **与「原版从同一条 strip 顺序播放」一致**。

**时长**：我们的 `Anim.EXPLODE_FRAME_MS = 1000 / 23`（1 秒 23 帧，按时间推进）。
原版出处（linux 复刻版的注释与常量，转述自原版 Win7 的动画 XML）：
- `linux-minesweeper-main/src/ui/Theme.h:115-119`
  `// The loss ("mine trip" / bad guess) animation, 23 frames over one second per animationMineSweeper_MineTrip.xml`
- `linux-minesweeper-main/src/ui/BoardWidget.cpp:42` `constexpr int kTripTicks = 1000 / kTickMs;`（`kTickMs = 30`）
- 帧推进式 `BoardWidget.cpp:763-765`：`frame = (m_tick - m_boomStart[i]) * kTripFrames / kTripTicks`
  ⇒ 与我们的「按时间推进」在数学上等价。

### 5.2 拆雷 38 帧 —— `otherSheet` 逻辑 x=0（蓝）/ x=364（绿）

| 条带 | 网格 | 非空格 | 重复帧 | 亮度首→末 |
|---|---|---|---|---|
| 蓝色（base 0） | 7 列 × 6 行 = 42 格 | **38**（第 39~42 格空） | 0 | 134 609 → 20 730（峰值 581 246 在第 14 帧） |
| 绿色（base 364） | 7 列 × 6 行 = 42 格 | **38** | 0 | 129 434 → 20 546（峰值 574 296 在第 14 帧） |

- 我们的 `DISARM_FRAMES = 38` 与素材一致（42 格里恰好 38 格有内容）。
- 蓝绿两条带**不是同一块像素**：逐像素差 **145 536 / 663 936 像素不同，RMS 9.63**，
  但两者的帧占用、亮度曲线、峰值帧位置**完全对应**（同一动画的两种配色）⇒
  `Theme.DISARM_BASE_GREEN = 364` 的 baseX 正确。
- 时长：`DISARM_FRAME_MS = 2000 / 38`（2 秒 38 帧），对应原版
  `Theme.h:138-143`（`38 frames over two seconds per animationMinesweeper_MineDisarm.xml`）与
  `BoardWidget.cpp:43` `kDisarmTicks = 2000 / kTickMs`；
  扫描条 `SWEEP_MS = 3000` 对应 `kScanTicks = 3000 / kTickMs`。

### 5.3 花园开花 23 帧 —— `otherSheet` 逻辑 x=905 起（36×36 格距 38）

- 3 列 × 8 行 = 24 格，**恰好 23 格非空**（第 1 格 `905,0` 为空）⇒
  与 `Theme.flowerTripRect` 的 23 帧一致（该函数把帧号钳在 0..22，正确）。
- 23 帧两两不同，重复数 0。
- 亮度序列：`0 → 17 335 → 196 105 → 348 799 → 691 359 → … → 169 310`（第 4 帧最亮），
  与雷版爆炸同为「起手 → 盛放 → 收敛」的结构。

### 5.4 三档难度的**最佳成绩用图** —— 原版素材里**没有**这种东西

- 原版素材全集 34 个文件里**没有任何「成绩/时间」相关的位图**。
- 最佳成绩在原版里是**数字文本**，不是图：
  - Lmy 复刻版把它存在 INI 里（`Minesweeper-master/Minesweeper/io.h:273`
    `static TCHAR* best[] = { TEXT("BESTTIME1") … TEXT("BESTTIME5"), … }`），
    显示时用 `wsprintf(best, TEXT("%d\t"), bestTime[k] / 10)`（`Minesweeper.cpp:543`）—— 纯文本；
  - linux 复刻版的统计对话框用 `QLabel *m_values[6]`（`src/ui/StatisticsDialog.h:20`）—— 也是文本控件。
- **结论：不存在「我们漏拷了最佳成绩用图」这回事。** 三档难度的成绩在原版里就是文本，
  我们按文本渲染即可（若要与计数器一样用七段，自绘即可，不必等素材）。

### 5.5 七个数码管数字 —— 原版素材里**没有可复用的字形**

- 全部精灵图里能数出来的字形只有**雷数数字 1..8**：
  `blueSheet` 逻辑 `x=1000`、每格 `12×15`、逐格不透明像素 **244 / 305 / 287 / 302 / 308 / 343 / 256 / 371**
  （第 9 格 `y=120` 为空），蓝绿两图**逐像素相同**。
  这是** minesweeper 的格内数字**，不是计数器里的七段字形。
- 全素材扫描「七段亮色 ≈ RGB(250,250,252)」的像素数：
  `blueSheet` 31、`greenSheet` 31、`otherSheet` 782、`minesweeperSheet` 11、`flowerGardenSheet` 25、
  `Frame.png` **0**、`Minesweeper.png` **1** —— 都是抗锯齿的零星像素，**不是字形块**。
- 原版唯一的七段字形证据在 **`helpBoard.png` 的插图里**（256×192，1:1），
  那里计数器上的「18」「-40」每个数字只有 **5×7 像素**，是插图不是精灵。
- **结论：原版把计数器的七段字形当作程序绘制（不是位图），所以「自己画段」是唯一正确解** ——
  这正是 `SevenSeg.ets` 现在做的事（掩码 `0x186`，见 `docs\SEVEN-SEG-COUNTER.md`）。

### 5.6 菜单栏位图 —— 原版素材里**没有**

- 原版素材 34 个文件里**没有菜单条位图**；`Frame.png` 是**客户区**（600×351），
  其结构实测为：第 0..28 行是 Aero 玻璃边框（行均 RGB ≈ 208,218,228，每行 100+ 色），
  中间是白色棋盘区（行均 ≈ 247,248,249，每行 20~30 色），第 324..351 行是底部状态条底色带（行均 ≈ 184,199,219）。
  **没有一行是菜单条**（真 Win7 的菜单由系统绘制）。
- 佐证：linux 复刻版的菜单是 `QMenuBar` + `QAction`（`src/ui/MainWindow.cpp:134-140`），
  没有任何菜单贴图。
- **结论：没有「菜单栏位图」可漏。** 我们用 `WinMenu.ets` 画菜单是正确路线。

### 5.7 问号与旗帜 —— 在，已用

| 素材 | 逻辑矩形 | 存储像素 | 不透明像素占比 | 状态 |
|---|---|---|---|---|
| 红旗 `RECT_FLAG` | `[400,560,18,18]` | `x 800..835, y 1120..1155` | **36.0 %**（466 / 1296） | 已用 |
| 白问号 `RECT_QUESTION` | `[420,560,18,18]` | `x 840..875, y 1120..1155` | **25.2 %**（326 / 1296） | 已用（白底上几乎看不见，原版就这样） |
| 悬停高亮 `RECT_HILITE` | `[440,560,18,18]` | `x 880..915, y 1120..1155` | **100.0 %** | 已用（相加混合） |
| 错旗红叉 `RECT_MISFLAG` | `[460,560,18,18]` | `x 920..955, y 1120..1155` | **53.5 %**（694 / 1296） | 已用（alpha 上限 128，半透明） |
| 上阴影条 `RECT_SHADOW_U` | `[480,560,18,3]` | `x 960..995, y 1120..1125` | **100.0 %** | 已用 |
| 左阴影条 `RECT_SHADOW_L` | `[1012,0,3,18]` | `x 2024..2029, y 0..35` | **100.0 %** | 已用 |

### 5.8 小雷与大雷 —— 在，已用

`minesweeperSheet.png`（94×54，RGBA，2 个连通域）与 `flowerGardenSheet.png`（同尺寸同结构、画的是花）：

| 素材 | 逻辑矩形 | 存储像素 | 不透明像素占比 | 用途 |
|---|---|---|---|---|
| 面板大雷 `RECT_PANEL_MINE` | `[0,0,25,25]` | `x 0..49, y 0..49` | **84.4 %**（2111 / 2500） | 状态条「剩余雷数」旁的银钮地雷 |
| 格下小雷 `RECT_MINE` | `[27,0,18,18]` | `x 54..89, y 0..35` | **85.0 %**（1101 / 1296） | 盖在砖块下的裸雷 |

> 对话框里用的那颗黑白尖刺雷也在同一张表里（`minesweeperSheet` 的 `x≈58..92` 一带，`WinDialog.ets` 已引用）。

### 5.9 音效 wav —— 15/15 全部一致，参数齐

- 全部 **44 100 Hz / 16 bit / 立体声**（PCM），逐字节 sha256 与原版相同（§2.2 / §3.1）。
- 我们 15 个都拷进了 `rawfile/`（含 3 条 `flowerLose*`，第一版审计时它们还没拷）。
- **没有「漏拷的音效」**；缺的只是触发时机（见 `docs\WIN7-FEATURE-GAP.md`）。

---

## 6. 三个问题的明确回答

### (a) 我们的爆炸精灵**帧数与顺序**是否与原版一致？—— **一致，「按原版 1 秒/23 帧」可信**

1. **帧数**：素材里那条 strip 的网格是 3 列 × 8 行 = 24 格，**恰好 23 格非空、第 24 格空**
   （逐格不透明像素 1764 / 1894 / 2017 / 2373 / 4628 / 2077 / … / 2030 / 1024 / 空）。
   我们的 `TRIP_FRAMES = 23` 与它**严格相等**，不多取一帧、不少取一帧。
2. **顺序**：我们的 `tripRect(frame) = [728 + 59*(frame%3), 59*floor(frame/3), 57, 57]`
   就是这条 strip 的**行优先（先列后行）**排布，而原版播放的正是这条 strip 本身，
   所以「帧号 → 源矩形」的映射与原版播放顺序**同构**。
3. **各帧确为不同画面**：23 帧按可见像素哈希两两比对，**重复 0 对**。
4. **内容自洽**：亮度从第 0 帧 78 515 升到第 4 帧 939 828（同时也是面积最大的一帧 4628 px），
   再逐帧衰减到第 22 帧 18 696（末帧只剩 1024 px 的地雷本体）—— 读作
   「火花 → 火球 → 烟散 → 露雷」，是一条自洽的爆炸序列。
5. **时长**：1 秒 23 帧的出处是原版的动画 XML
   （`animationMineSweeper_MineTrip.xml`，经 linux 复刻版 `Theme.h:115-119` 与
   `BoardWidget.cpp:42` 的 `kTripTicks = 1000 / kTickMs` 记录）；
   我们的 `EXPLODE_FRAME_MS = 1000/23` 且**按时间推进**（`Anim.ets`），
   与原版的 `(tick - start) * 23 / kTripTicks` 等价。
   ⇒ **可信**。同理拆雷 38 帧 / 2 秒、扫描条 3 秒也都对得上（§5.2）。

### (b) 原版有、我们缺、且**肉眼可见**的素材 —— 按重要性排序

| 排名 | 资产 | 缺了会怎样（用户能不能看出来） | 补它要改哪个文件 | 工作量 |
|---|---|---|---|---|
| **1** | **应用图标组** `icons/MineSweeper-32/48/64/128.png` + `Minesweeper.ico` | **看得见**：桌面图标 / 应用列表里现在是我们自己画的 152×152 `startIcon.png`（`a314ff05…`），不是原版那颗银灰尖刺地雷球 | `AppScope/resources/base/media/`（换图，不改代码）→ 用 `MineSweeper-128.png` 重排一版（缩到画布 70~75 %、去自带投影、导 216×216 或 512×512） | 图片层面，0 行代码 |
| **2** | **`Frame.png`（600×351 原版窗口客户区）** | **半可见**：原版四周是 Aero 玻璃渐变边框（实测行均 RGB 208,218,228）、底部是状态条底色带（行均 184,199,219）；我们用纯色 `#c6cede` / `#ffffff` / `#4c556f` 代替。**手机形态下没有窗口边框，所以主要差在底部那条状态条底色带** | `SpriteAtlas.ets`（`frameSheet` 字段已存在但未加载）+ `Theme.ets`（`FRAME_W/FRAME_H/FRAME_GAP_*` 已备好）+ `MinefieldCanvas.ets` / `GameController.ets` 的棋盘底板绘制 | 中；**注意**九宫格不可直接用（零件被画在左上角、玻璃渐变不对称），按 §8.4.3 的结论要裁切重组 |
| **3** | **`Minesweeper.bmp`（144×468 旧式大图集）** | **看不出来**：内容已被拆进 blueSheet/greenSheet/minesweeperSheet/otherSheet 四张表，画面上不直接出现 | 不必接；作为「拆包是否漏了东西」的权威对照留着即可 | 0 |

**判定为「不需要补」的（重点说明，避免白做工）**：

- **三档难度的最佳成绩用图**：原版素材里**根本没有**（§5.4）—— 成绩在原版是文本。
- **七个数码管数字**：原版素材里**没有可复用的字形**（§5.5），原版是程序绘制，我们自绘（`SevenSeg.ets`）即是正解。
- **菜单栏位图**：原版**没有**（§5.6），菜单由系统绘制。
- **`flowerGardenSheet` + 3 条 `flowerLose*`**：第一版审计时算「未用」，**现已全部拷入 `rawfile/` 并接进 `Appearance.ets` / `Theme.GameStyle`**。

### (c) 有没有我们**自己改过**、与原版不一致的素材？—— **没有**

- 25 个 rawfile 素材与原版 **sha256 逐个相同**，10 张图逐像素复算**差异像素 0、RMS 0.0000**，15 个 wav 逐字节相同。
- **我们多出来的 5 个文件全是我们自己的应用图标**（`base/media/` 与 `AppScope/resources/base/media/`），不属于「改过的原版素材」。
- 因此：**用户能看出来的素材差异，来源只有「缺」（见 (b)），不存在「走样」。**
- 唯一与「不一致」沾边、但**不是素材**的一件事：计数器数字**不是从原版抠的图**，而是我们按原版插图反推后**自绘的七段**。
  这不是素材改动，但属于「自绘替代原版」的取舍 —— 结论与依据见 `docs\SEVEN-SEG-COUNTER.md`
  （几何来源：XP 版逆向重建 + `helpBoard.png` 逐像素读数；原版素材里确实没有七段字形可抠）。

---

## 7. 建议的后续动作（不含本轮）

1. **应用图标**（收益最直接）：按 §6 (b) 第 1 条，用 `icons/MineSweeper-128.png` 重排一版 `startIcon.png`。
2. **状态条底色带**：如果要更贴近原版，取 `Frame.png` 底部 324..351 行那条底色带（行均 RGB 184,199,219），
   画成状态条背景，而不是现在的纯色。
3. **状态条零件位置**：原版 `Frame.png` 把时钟/LED/雷钮**塞在左上角**，与真 Win7 的底部版式不符
   （§8.4.3），**不要**直接把整张 Frame 当底图用。

---

## 8. 附录：区域级明细（第一版内容保留；3 处已被本轮证据更正）

### 8.1 蓝色 / 绿色主题图集：两图**同构**

逐像素量化（第一版实测，结论不变）：

| 区域（存储像素） | RGB 差异（>10 的像素占比） | 平均最大差 | alpha 差异像素 |
|---|---|---|---|
| 砖块渐变区 `x 0..900, y 0..1044` | **99.3 %** | 128.5 | 3 884 |
| 已翻开凹陷格区 `x 1000..1900, y 0..1044` | 87.2 % | 31.4 | 0 |
| 计数器面板 `x 0..120, y 1155..1206` | 43.3 % | 43.0 | 592 |
| 空白沟槽 `x 900..1000` | **0 %** | 0.0 | 0 |
| 数字 1..8 `x 1990..2034, y 0..1044` | **0 %** | 0.0 | 0 |
| 底部覆盖层条 `x 780..1000, y 1110..1170` | **0 %** | 0.0 | 0 |

- 本轮整图复算：两图共 2 453 004 像素中 **1 867 910 像素不同（76.15 %）**，差异 bbox `x 0..1899, y 0..1201`
  —— 即差异**全部集中在砖块与凹陷格两区**，数字/旗/问号/高亮/红叉/阴影**逐字节相同**。
- ⇒ **绿色主题不是「再画一套素材」，而是同一张图集换色板**；唯一要按主题切换的坐标是拆雷动画 baseX（蓝 0 / 绿 364）。

### 8.2 blueSheet / greenSheet 逐区域表

| 逻辑矩形 | 存储像素 | 内容 | 不透明像素占比 | 状态 |
|---|---|---|---|---|
| `normalTile(frame)` 0..719 | `x 0..899, y 0..1043` | **凸起方砖 720 帧渐变**，25 帧/行、29 行，左上浅 → 右下深 | 100 % | 已用 |
| `pressedTile(frame)` = normalTile + (500,0) | `x 1000..1899, y 0..1043` | **已翻开的凹陷格 720 帧渐变** | 100 % | 已用 |
| `RECT_FLAG` | `x 800..835, y 1120..1155` | 红旗（旗面 + 旗杆 + 底座） | 36 % | 已用 |
| `RECT_QUESTION` | `x 840..875, y 1120..1155` | **白色问号**（RGB ≈ 253,253,253，alpha 上限 230） | 25 % | 已用 |
| `RECT_HILITE` | `x 880..915, y 1120..1155` | 悬停高亮深青灰方块，**100 % 不透明** | 100 % | 已用（相加混合） |
| `RECT_MISFLAG` | `x 920..955, y 1120..1155` | 错旗红叉 | 54 % | 已用（alpha 上限 128） |
| `RECT_SHADOW_U` | `x 960..995, y 1120..1125` | 上方阴影条 | 100 % | 已用 |
| `RECT_SHADOW_L` | `x 2024..2029, y 0..35` | 左侧阴影条 | 100 % | 已用 |
| `digitRect(1..8)` | `x 2000..2023, y 0..239` | 彩色数字 1..8（1 蓝 / 2 绿 / 3 红 / 4 深蓝 / 5 暗红 / 6 青 / 7 黑 / 8 灰） | 34~52 % | 已用 |
| `RECT_COUNTER` | `x 0..79, y 1160..1201` | 计数器凹槽面板 | 99~100 % | 已用 |
| （空白） | `x 900..999, y 0..1043` | 完全透明，两图一致 | 0 % | 沟槽 |

### 8.3 otherSheet（2048×2016，逻辑 1024×1008，存储 2x）

| 逻辑矩形 | 存储像素 | 内容 | 状态 |
|---|---|---|---|
| 拆雷动画 **蓝** 38 帧 | `x 0..727, y 0..1043` | 每帧 50×150 逻辑（100×300 px），7 帧/行、6 行；帧内自带一份方砖拷贝 | 已用 |
| 拆雷动画 **绿** 38 帧 | `x 728..1455, y 0..1043` | 同上，绿色板用（baseX = 364 逻辑） | 已用（`disarmRectFor`） |
| 踩雷动画 **雷** 23 帧 | `x 1456..1810, y 0..1043` | 每帧 57×57 逻辑（114×114 px），3 帧/行 | 已用 |
| 踩雷动画 **花** 23 帧 | `x 1810..2037, y 0..?` | 每帧 36×36 逻辑（72×72 px） | 已用（`flowerTripRect`） |
| `RECT_CLOCK` | `x 1810..1859, y 850..899` | 时钟图标（银钮装指针钟） | 已用 |
| `RECT_SCAN_BAR` | `x 0..549, y 1824..1947` | **胜利扫描条**：横向蓝色渐变长条 | 已用 |
| （未引用） | `x 1457..1518, y 945..1290` | **竖向**蓝色渐变条 62×346 px | 未用，**用途存疑** |
| （未引用） | `x 1..252, y 1953..2014` 与 `x 255..450, y 1953..2014` | **两片纯灰渐变的窗口边框片**（中间一条竖直接缝） | 未用，**用途不明，不建议接入** |

> 本轮复算底部带（逻辑 y ≥ 900）的连通域：**只有 3 个** ——
> `y=1840 x=1 h=109 w=552 area=60 168`（扫描条）、
> `y=1953 x=1 h=62 w=252 area=15 623`、`y=1953 x=255 h=62 w=196 area=12 151`（两块灰片）。
> **这两块灰片里既没有数字字形也没有笔段** —— 第一版把这里误记成「七段数码管笔段」是读图错误，此处保留更正。

### 8.4 其余素材（第一版说明，保留）

**8.4.1 minesweeperSheet / flowerGardenSheet（94×54）**：各 2 个精灵，见 §5.8。

**8.4.2 thumb\*.png（外观对话框）**：
`thumbBlue/thumbGreen` 109×109 **完全不透明**（6×6 凸起方砖马赛克，每砖 18×18 px）；
`thumbMines/thumbFlowers` 92×92 **有透明区**（分别 55 % 全透明 / 一颗银雷 / 一朵黄花）。
四张现已全部接入 `Appearance.ets`。

**8.4.3 Frame.bmp / Frame.png（600×351）—— 原版窗口边框，九宫格用不了**：
`png/Frame.png` 与 `Frame.bmp` 逐像素相同（**本轮复算：差异 0 / 210 600，RMS 0.0000**；
与上下翻转版差 **59 018** 像素 ⇒ **更正** `SpriteAtlas.ets` 里「这张图上下颠倒」那句：png 与 bmp 之间不存在翻转）。
内容：四周一圈 Aero 玻璃质感淡蓝灰渐变边框（约 28~30 px 宽）；中间一大块纯白棋盘区；
**左上角**塞着状态条零件（一个圆形时钟按钮约 `x 28..55, y 28..55`、一个蓝色 LED 显示条约 `x 57..95, y 30..50`），
圆形地雷按钮在时钟下方（约 `x 32..52, y 58..78`）。
**不能当九宫格直接用的三条理由**：① 状态条零件被画在**左上角**，而真 Win7 版式在**底部**（见 §8.4.4）；
② 边框是 Aero 玻璃渐变，**不是对称可拉伸的九宫格素材**；③ 图里没有笑脸按钮，也没有完整状态条底板。
**替代方案（本项目现做法是对的）**：不加载 Frame.png，纯色画窗口外圈与棋盘区，
状态条零件分别从 `otherSheet`（时钟）与 `minesweeperSheet`（雷钮）取。

**8.4.4 helpBoard.png（256×192）—— 真 Win7 帮助窗口插图**：
不是文档图，而是**整个 Win7 扫雷窗口的缩略插图**：上部蓝色棋盘（已翻开格上带彩色数字），
下部状态条从左到右是 `[ 圆形按钮A ][ 蓝色 LED "18" ] …… [ 蓝色 LED "-40" ][ 圆形按钮B ]`。
两个圆钮放大 14 倍辨认：**按钮A = 时钟**（钟面 + 指针，**不是笑脸**），**按钮B = 地雷**（与 `RECT_PANEL_MINE` 同款）。
数字语义：左边 LED 只能是计时秒数（`18`），右边 LED 只能是雷数（`-40`），
⇒ 真 Win7 状态条是 **`[时钟][计时 LED] …… [雷数 LED][地雷图标]`**。
**工程曾在这一点上写反**（把时钟叫「笑脸」、两个 LED 左右相反），**2026-10-31 已修**（commit `d21e2e9`），
`RECT_FACE` 与 `rawfile/face.png` 已移除。裁决全文见 `docs\STATUS-STRIP-VERDICT.md`。
**本轮补充**：这张图里的「18」「-40」是**七段 LED**（每个数字 5×7 px），是「原版计数器是七段」的第一手证据；
七段字形的几何推导见 `docs\SEVEN-SEG-COUNTER.md`。

**8.4.5 Minesweeper.bmp / png（144×468）—— 原始大图集**：
Win7 原始资源里那张密排图集：左上角有蓝砖问号、插旗带数字的格子；一列是纯数字 1..8；
左下是红叉 + 数字；右侧大块是「方砖 × ? 叠加 × 旗叠加 × 红叉叠加」的完整矩阵，蓝绿两套并排。
`build_sheets.py`（linux 复刻的打包脚本）把它拆成了 blueSheet / greenSheet / minesweeperSheet / otherSheet。
**这是上游源图，本项目不需要它**；但它是核对拆包是否有遗漏的唯一权威。

### 8.5 音频事件映射（第一版结论，保留）

| 文件 | 波形特征 | 建议事件映射 | 本项目状态 |
|---|---|---|---|
| `gameStart.wav` | 前 3 段持续高（0.90/0.88/0.94）后急落 | 新开局 | 已用（`Sound.GAME_START`） |
| `tileSingle.wav` | 平直高频 0.9 持续 ~0.14 s 后骤停 | 翻开 1 格 | 已用 |
| `tileMultiple.wav` | 中段冲到 1.00 后回落 | 洪泛翻开多格 | 已用 |
| `zeroDevelop.wav` | 全程接近满幅 | 0 格洪泛展开 | 已用 |
| `firstPaint.wav` | 前 3 段满幅后断崖 | 首点开格 | 已用 |
| `invalidMove.wav` | 音量很小的短「嘟」 | 点了已翻开的格子 / 越界 | 已用 |
| `dbButtonClickFlag.wav` | 快速衰减的清脆一响 | 插旗 / 取消旗 | 已用 |
| `gameWin.wav` | 第 2 段冲到 1.00，长尾音 | 通关 | 已用 |
| `gameLose.wav` | 前段 0.72 起单调衰减 | 踩雷（可重叠多次） | 已用 |
| `mineBombStart.wav` | 起伏状，末段仍有 0.32 | 爆炸三段之一 | 已用 |
| `mineBombRun.wav` | **全程高位不衰减**，最长的一条 | 爆炸三段之二 | 已用 |
| `mineBombEnd.wav` | 单调衰减 0.72→0.01 | 爆炸三段之一 | 已用 |
| `flowerLoseShort/Medium/Long.wav` | 起伏花瓣声，长度递增 | 花园版失败（雷数 ≤10 / ≤40 / >40） | **已拷入 rawfile**（第一版时未拷） |

> **声音侧没有漏拷的素材**，缺的是触发时机（见 `docs\WIN7-FEATURE-GAP.md`）。
> 提醒：`mineBombRun.wav` 长 3.949 s，若当「三段连播」用，总时长约 7 s。

### 8.6 预览图清单（第一版生成，保留）

`docs/audit_blueSheet_overview.png`、`audit_greenSheet_overview.png`、`audit_blue_bottomstrip.png`、
`audit_green_bottomstrip.png`、`audit_blue_gutter.png`、`audit_otherSheet_overview.png`、
`audit_otherSheet_TL/TR/BL/BR.png`、`audit_minesweeperSheet_x6.png`、`audit_flowerGardenSheet_x6.png`、
`audit_Frame_full.png`、`audit_Frame_tl.png`、`audit_Frame_br.png`、`audit_Minesweeper_bmp_full.png`、
`audit_helpBoard_full.png`、`audit_thumbBlue_x4.png`、`audit_thumbGreen_x4.png`、
`audit_thumbMines_x4.png`、`audit_thumbFlowers_x4.png`、
`audit_icon_32/48/64/128_x3.png`、`audit_icon_128_native.png`。
另见 `docs\verify\sprites\sevenseg_preview.png`（七段计数器合成到真实面板精灵上的效果）。

### 8.7 「已用 / 未用」总表（按本轮实测更新）

**已用（文件在 `rawfile/`，代码已引用）**：

| 素材 | 代码引用 |
|---|---|
| `blueSheet.png` / `greenSheet.png` | `Theme.normalTileRect / pressedTileRect / digitRect / RECT_*`；`SpriteAtlas.boardSheet`；`BoardStyle` 切换 |
| `minesweeperSheet.png` / `flowerGardenSheet.png` | `RECT_MINE` / `RECT_PANEL_MINE`；`GameStyle` 切换 |
| `otherSheet.png` | `RECT_CLOCK` / `tripRect` / `flowerTripRect` / `disarmRectFor` / `RECT_SCAN_BAR` |
| `helpBoard.png` | `SpriteAtlas.helpBoard` → `WinDialog.ets` 的帮助窗口插图；也是七段字形的证据 |
| 4 张 `thumb*.png` | `Appearance.ets` 的四个单选图示 |
| 15 个 wav | `SoundPlayer` 的 15 个常量 |
| 自绘七段计数器 | `SevenSeg.ets`（**原版无位形可抠，见 §5.5**） |

**未用**：

| 素材 | 结论 |
|---|---|
| `icons/MineSweeper-*.png` / `Minesweeper.ico` | **建议接**（桌面图标，见 §6 (b) 第 1 条） |
| `Frame.bmp` / `png/Frame.png` | 半可见（状态条底色带），九宫格不可用，**要接需裁切重组** |
| `Minesweeper.bmp` / `png/Minesweeper.png` | 不需要（拆包源，已拆完） |
| `otherSheet` 的竖向渐变条 `x 1457..1518, y 945..1290` | **用途存疑**，不建议接入 |
| `otherSheet` 底部两块灰渐变片 | **用途不明**，不建议接入 |

> **已作废的一条（2026-11-01 更正）**：第一版曾写「计数器用粗体白字不是降级，不需要改成七段」，
> 该结论**已被推翻**：微软自己的 `helpBoard.png` 状态条里是七段 LED，
> 工程已改为 `SevenSeg.ets` 自绘七段（掩码 `0x186`），推导与出处见 `docs\SEVEN-SEG-COUNTER.md`。

---

## 9. 复现方法（本轮全部数字的来源）

只读两个仓，未写入任何文件；脚本放在系统临时目录（`%TEMP%\asset_audit\`），可随时重跑：

| 脚本 | 产出 |
|---|---|
| `inv.py` | 全量清单：sha256 + 图像尺寸/模式 + wav 采样率/位深/时长/帧数；并按 sha256 列出跨目录同一文件 |
| `deep.py` | 逐像素差（差异像素数 / RMS）、otherSheet 连通域结构、Theme 各矩形的内容统计（不透明像素占比）、23/38/23 三条动画 strip 的逐帧签名与亮度、blue/green 差异定位、LED 色像素扫描 |
| `strips.py` | 三条动画 strip 的**逐格网格表**（非空格数、重复帧） |
| `frames.py` | Frame/Minesweeper 的 bmp↔png 比对与结构带、角落色彩数、LED 色像素数、蓝绿拆雷条差异 |

关键结论均可由上表脚本复算；本文档所有数字均来自这些脚本的 stdout。
