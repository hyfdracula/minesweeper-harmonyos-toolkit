# 音效映射表（真 Win7 原版素材）

依据：微软原版 `win7-assets\audio\*.wav`（15 个）、参考实现
`linux-minesweeper-main\src\ui\Sounds.h`（它明确说映射来自原版的 `MINESWEEPER.xml`）、
`ReversingMinesweeper-master\Minesweeper\game.c`（触发时机）、
`Minesweeper-master\Minesweeper\Minesweeper.cpp`（`mineBomb()` 的爆炸时序）。

## 时长实测（Python wave 模块，44.1 kHz / 16bit / 立体声）

| 文件 | 时长 | 已复制进 rawfile | 用途 |
|---|---|---|---|
| dbButtonClickFlag.wav | 0.184 s | 是 | 插旗 / 拔旗 |
| tileSingle.wav | 0.186 s | 是 | 单格翻开 |
| zeroDevelop.wav | 0.233 s | 是 | 0 格展开（洪泛） |
| invalidMove.wav | 0.279 s | 是 | **和弦失败**（旗数与数字不符） |
| tileMultiple.wav | 0.325 s | 是 | 一次翻开多格 |
| mineBombStart.wav | 1.294 s | 是 | 爆炸开始 |
| mineBombEnd.wav | 1.951 s | 是 | 爆炸结束 |
| gameLose.wav | 1.997 s | 是 | 判负（**每颗雷各播一声**，原版保留 30 个缓冲可叠加） |
| gameWin.wav | 2.183 s | 是 | 通关 |
| firstPaint.wav | 2.368 s | 是 | **新局发牌动画的配乐** |
| gameStart.wav | 2.554 s | 是 | 新局发牌（另见下方「两份复刻的分歧」） |
| mineBombRun.wav | 3.949 s | 是 | 爆炸中（原版是**循环**播） |
| flowerLoseShort/Medium/Long.wav | 3.5 / 6.0 / 7.9 s | 否 | 「花园版」判负，本项目无关 |

## 事件 → 文件（最终口径）

> **2026-11-04 修正**：首点开格**不再**单独播 `firstPaint`，
> 发牌动画改播 `firstPaint`。理由见下方「音效归属的两份复刻与分歧」。

| 事件 | 播放 | 说明 |
|---|---|---|
| 新建一局 / 换难度（发牌动画） | `firstPaint` | 原版的**发牌配乐**（`IDR_WAVE1`）。原版发牌动画共 1100 ms |
| **第一次**开格 | `tileSingle` / `tileMultiple` / `zeroDevelop` | **首点没有专属音效**，与其它开格同一套规则（按翻开格数） |
| 开 0 格（洪泛展开） | `zeroDevelop` | 原版 0 格展开有自己的音效 |
| 普通单格翻开 | `tileSingle` | SingleReveal |
| 一次翻开多格（非 0 格起点） | `tileMultiple` | MultiReveal |
| 和弦失败（旗数与数字不符） | `invalidMove` | InvalidMove（**只在这时候响**） |
| 插旗 / 拔旗 | `dbButtonClickFlag` | 「planting or clearing a flag」 |
| 踩雷 | `mineBombStart` → 1000ms → `mineBombRun`（循环）→ 级联结束 → `mineBombEnd` | 本工程爆炸动画是 23 帧 × 43.478ms = **1000ms**（原版 Win32 复刻是 25 帧 × 23ms = 575ms，**切换点按本工程的实际动画时长**） |
| 判负（每颗雷） | `gameLose` | 原版 WrongGuess，**每颗雷都播、可叠加**（用 4 个播放器轮转） |
| 通关 | `gameWin` | BoardCleared（与胜利扫描条同时起播） |

## 音效归属的两份复刻与分歧

两份复刻对「发牌那一刻响哪一条」的答案**互相矛盾**，这里如实记下：

| 复刻 | 说法 | 依据 |
|---|---|---|
| Lmy（Win32，资源 ID 与原版一一对应） | 发牌动画播 **`firstPaint`** | `Minesweeper.rc:344`（`IDR_WAVE1 = firstPaint.wav`）+ `utf8/Minesweeper.cpp:1495-1508`（在发牌的逐格绘制循环**之前** `PlaySound(IDR_WAVE1)`） |
| linux-minesweeper（Qt） | 新局播 **`gameStart`**（角色 NewBoard） | `src/ui/Sounds.h:6` + `src/ui/MainWindow.cpp:211-213`（`playIntro()` 紧挨着 `m_sounds.newGame()`） |

**本项目的取舍**：发牌播 `firstPaint`。

理由：
1. Lmy 是 Win32 版，**资源 ID 直接照搬原版**，把 `IDR_WAVE1` 放在发牌函数里
   是对原版资源绑定最直接的证据；
2. 两份复刻**都没有**把某条音效挂在「首点开格」上 ——
   Qt 版按翻开格数选 `tileSingle`/`tileMultiple`
   （`MainWindow.cpp:41-48`，注释原文 "The original's SingleReveal / MultiReveal pair."），
   Lmy 版 0 格洪泛走独立的 `zeroDevelop()`（`:1774-1797`）。
   而本项目原先让首点只响 `firstPaint`、把整条 `zeroDevelop`/`tileSingle`/`tileMultiple` 吃掉 ——
   这正是用户 2026-11-04 报的「点击第一个方块时还是会播放一次开始音频」。

**仍未定案的一点**：`gameStart.wav` 现在全仓无调用点。
两份复刻都说它是「新局那一刻」的声音，但都说得比 `firstPaint` 弱
（Qt 版没有 `firstPaint` 资源，Lmy 版没有 `gameStart` 资源，两边都没法直接对照）。
要彻底定案，需要在**真 Win7** 上听一次新局瞬间：
「密集颗粒翻牌感」（≈900ms 不间断）⇒ `gameStart`；
「清脆钟声 + 长余韵」⇒ `firstPaint`。
在此之前不擅自补播，避免多出一声。

## 本项目的取舍

- **`gameLose` 用 4 个播放器轮转**（原版留 30 个缓冲）：一颗雷的爆炸声 1.997 秒，
  4 个能叠住约 8 秒的级联。单一播放器会让后一声打断前一声，
  级联听起来是「哒哒哒」而不是原版的「轰隆隆一片」。
- **花园版音效（flowerLose*）已复制进 rawfile**：那是「花园模式」变体的判负音效。

