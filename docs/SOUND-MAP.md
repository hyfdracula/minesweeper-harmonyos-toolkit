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
| invalidMove.wav | 0.279 s | 是 | 无效点击（点已翻开的数字格且旗数不符） |
| tileMultiple.wav | 0.325 s | 是 | 一次翻开多格 |
| mineBombStart.wav | 1.294 s | 是 | 爆炸开始 |
| mineBombEnd.wav | 1.951 s | 是 | 爆炸结束 |
| gameLose.wav | 1.997 s | 是 | 判负（每个雷都播，原版保留 30 个缓冲可叠加） |
| gameWin.wav | 2.183 s | 是 | 通关 |
| firstPaint.wav | 2.368 s | 是 | 首点开格（firstPaint 动画） |
| gameStart.wav | 2.554 s | 是 | 新局发牌 |
| mineBombRun.wav | 3.949 s | 是 | 爆炸中（原版是**循环**播） |
| flowerLoseShort/Medium/Long.wav | 3.5 / 6.0 / 7.9 s | 否 | 「花园版」判负，本项目无关 |

## 事件 → 文件（最终口径）

| 事件 | 播放 | 说明 |
|---|---|---|
| 新建一局 / 换难度 | `gameStart` | 原版角色 NewBoard，「一副新牌发下来」 |
| **第一次**开格 | `firstPaint` | 参考实现在首点开格时播它，而不是 tileSingle |
| 开 0 格（洪泛展开） | `zeroDevelop` | 原版 0 格展开有自己的音效 |
| 普通单格翻开 | `tileSingle` | SingleReveal |
| 一次翻开多格（非 0 格起点） | `tileMultiple` | MultiReveal |
| 无效点击 | `invalidMove` | InvalidMove |
| 插旗 / 拔旗 | `dbButtonClickFlag` | 「planting or clearing a flag」 |
| 踩雷 | `mineBombStart` → 575ms → `mineBombRun` → 3949ms → `mineBombEnd` | 原版时序：爆炸开始音 → 爆炸动画（25 帧 × 23ms = 575ms）→ 爆炸中音循环播（同时其它雷逐颗烧红）→ 爆炸结束音 |
| 判负（其余雷） | `gameLose` | 原版 WrongGuess，每个雷都播、可叠加 |
| 通关 | `gameWin` | BoardCleared |

## 本项目的取舍

- **「其它雷逐个烧红」的动画没做**（原版有，见 `Minesweeper.cpp` 的 `getMineDevelopNo`）：素材里缺「红热雷」的逐帧序列，只有整张表的火球动画。
- **`gameLose` 目前只在判负时播一次**，原版是每个雷都播并叠加；本项目没有逐雷爆炸动画，所以一次即可。
- **花园版音效（flowerLose*）未复制**：那是「花园模式」变体的，与本项目的标准扫雷无关。
