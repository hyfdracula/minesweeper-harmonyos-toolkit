# 音效专项审计（Sound Audit）

日期：2026-11-01
审计范围：**纯文件与代码，设备无关**。没有跑模拟器、没有连任何设备。
app 仓 `C:\Users\19161\saolei` **全程只读**，本审计没有改过 app 仓任何文件；
要改的地方全部写在第 8 节，交给 lead 处置。
测量脚本：纯标准库（`wave`/`hashlib`/`array`），不起子进程、不 pip install。

---

## 0. 摘要

| 项目 | 结论 |
|---|---|
| 素材一致性 | **15 个音效与原版素材字节级完全一致**（sha256 全等），0 处不一致 |
| 格式 | 全部 44100 Hz / 16 bit / 立体声（4 个是双单声道，11 个是真立体声） |
| 触发点 | 共 **15 个调用点**：**14 处** `SoundPlayer.play`（覆盖 15 个音效名）+ 1 处开关；**漏接 2 处、误响 2 处、重复叠播 1 处**（见第 3 节） |
| 花园判负分档 | **当前按总雷数分档，符合要求**；但本地唯一可查的参照实现按"待爆雷数"分档，阈值相同（见第 4 节） |
| 播放通道 | 每个音效名一个独立 `AVPlayer`，**不同音效可叠加、同一音效会互相截断**；有 3 处资源/并发隐患（见第 5 节） |

---

## 1. 素材清单与原版对齐

### 1.1 原版侧素材在哪（三份副本，内容相同）

| 目录 | 文件数 | 角色 |
|---|---|---|
| `minesweeper-refs\win7-assets\audio\` | 15 | **微软原版 Win7 素材**（本项目的真正来源） |
| `minesweeper-refs\linux-minesweeper-main\assets\audio\` | 15 | Linux 复刻带的同款副本 |
| `minesweeper-refs\Minesweeper-master\Minesweeper\res\wav\` | 6 | 另一份 Win32 复刻只带了 6 个（dbButtonClickFlag / firstPaint / mineBombEnd / mineBombRun / mineBombStart / zeroDevelop） |
| `saolei\entry\src\main\resources\rawfile\` | 15 | **本项目使用的** |

### 1.2 逐文件测量（本项目 rawfile 的文件）

格式列：全部为 **44100 Hz / 16 bit / 2 ch**。
包络列：头 20 ms / 中段（文件中点 ±50 ms）/ 尾部 100 ms 的 RMS，单位 dBFS（0 = 满刻度）。
「起音」= 第一个超过 -60 dBFS 的样本时刻（毫秒）。

| 文件 | 时长 s | 峰值 dBFS | 起音 ms | 头 20ms | 中段 | 尾 100ms | 全长 RMS | 声道 | 字节 | sha256 |
|---|---|---|---|---|---|---|---|---|---|---|
| dbButtonClickFlag.wav | 0.184 | -0.91 | 0.0 | -7.00 | -13.27 | -20.94 | -12.77 | 立体声 | 32530 | 99266938e33ef918ad8f84f8c1327281164cda1f48ead64d9260d2c949e13798 |
| firstPaint.wav | 2.368 | -0.06 | 0.2 | -4.01 | -20.59 | -36.59 | -10.29 | 立体声 | 417858 | a27214debd6bc3c0caee0fd13c7dfd0605ea91ce6d713759e9cd700bcde05677 |
| flowerLoseLong.wav | 7.941 | -1.09 | 0.0 | -36.66 | -16.72 | -74.38 | -15.93 | 双单 | 1400910 | 6b0e4e4829ae22d81beec1c230e6e3d2d977044aeb96d8f5bda68a2a378e64de |
| flowerLoseMedium.wav | 6.037 | -1.94 | 0.0 | -36.62 | -17.71 | -74.13 | -17.02 | 双单 | 1065038 | 45e8e7f92617521c7a7950a4faa7f3bcf1ad2e75b1d81907da4d603a3361a7b0 |
| flowerLoseShort.wav | 3.529 | -1.10 | 0.0 | -37.35 | -16.46 | -77.72 | -16.21 | 立体声 | 622670 | 1eccb7119e9b72f0c000e7c36fa133e7d7f8d65ed900a2e0d88174f5230d2e35 |
| gameLose.wav | 1.997 | -2.91 | 0.0 | -44.60 | -25.00 | -35.89 | -21.79 | 立体声 | 352334 | df601a1628d658afbd6293b131f117334992b8a409f6d5b31ff773b57bdedd85 |
| gameStart.wav | 2.554 | -0.51 | 43.5 | -80.87 | -30.41 | -48.78 | -14.38 | 立体声 | 450638 | 62cac498a0fe10e5789e583e332a5db04a1d42d11633ced308babcdb6fa783c1 |
| gameWin.wav | 2.183 | -0.01 | 39.8 | -75.39 | -16.07 | -53.98 | -14.63 | 双单 | 385102 | fc18811084887ac6bc3789852c89be99dc67f5169815648eab232209913edbd6 |
| invalidMove.wav | 0.279 | -10.52 | 18.8 | -25.97 | -39.89 | -61.53 | -26.91 | 立体声 | 49230 | 0927a5da6cb1ed4eccd2565906c9f194bb06128bc87be69ebc3a2a0ca1a1b121 |
| mineBombEnd.wav | 1.951 | -2.82 | 0.0 | -11.29 | -19.74 | -32.34 | -15.87 | 立体声 | 344282 | 9605e9b602ea58941107a250a136364dfc1dd157fddf2e66c5f6e8c455b5f92f |
| mineBombRun.wav | 3.949 | -1.25 | 0.0 | -9.09 | -10.85 | -11.53 | -11.03 | 双单 | 696638 | 559fbd0712228b687d4783d5b148a714d9fe43c6cf94db50791aa1af10413cd6 |
| mineBombStart.wav | 1.294 | -1.65 | 0.0 | -7.97 | -13.95 | -22.42 | -13.53 | 立体声 | 228354 | 02b4ca1f07502faaa92a04940eea8b383b78e40a0628c77fccc186719bad8ce0 |
| tileMultiple.wav | 0.325 | -0.04 | 2.6 | -8.82 | -8.72 | -16.52 | -8.58 | 立体声 | 57422 | cb63fe2f150f3ba8ca4ade28afa791f8aaa990276851b9def6dc54bcdf72397b |
| tileSingle.wav | 0.186 | -0.05 | 2.6 | -5.68 | -4.98 | -8.38 | -6.03 | 立体声 | 32846 | 344ecf8c8f7be81853b763c02f8520c287845a92d90f44851cbd61a42a340660 |
| zeroDevelop.wav | 0.233 | 0.00 | 0.0 | -3.74 | -4.78 | -7.16 | -4.84 | 双单 | 41254 | dd56209395df4487dbfa26638c039da9a07d1874a240fd1525d85c41ae4e2596 |

### 1.3 与原版逐一对齐的结果

**15 个文件全部一致**：本项目 rawfile 里的每个 wav，与 `win7-assets\audio\`（原版）、
与 `linux-minesweeper-main\assets\audio\`（Linux 复刻副本）、
以及 Lmy 复刻 `res\wav\` 里存在的那 6 个，**sha256 完全相同**，字节数也相同。
也就是说：**素材层面零偏差，不需要换任何文件**。

抽样核对三份副本的 sha256 前 8 位：

| 文件 | app | win7（原版） | linux | lmy |
|---|---|---|---|---|
| dbButtonClickFlag.wav | 99266938 | 99266938 | 99266938 | 99266938 |
| firstPaint.wav | a27214de | a27214de | a27214de | a27214de |
| flowerLoseLong.wav | 6b0e4e48 | 6b0e4e48 | 6b0e4e48 | — |
| flowerLoseMedium.wav | 45e8e7f9 | 45e8e7f9 | 45e8e7f9 | — |
| flowerLoseShort.wav | 1eccb711 | 1eccb711 | 1eccb711 | — |
| gameLose.wav | df601a16 | df601a16 | df601a16 | — |
| gameStart.wav | 62cac498 | 62cac498 | 62cac498 | — |
| gameWin.wav | fc188110 | fc188110 | fc188110 | — |
| invalidMove.wav | 0927a5da | 0927a5da | 0927a5da | — |
| mineBombEnd.wav | 9605e9b6 | 9605e9b6 | 9605e9b6 | 9605e9b6 |
| mineBombRun.wav | 559fbd07 | 559fbd07 | 559fbd07 | 559fbd07 |
| mineBombStart.wav | 02b4ca1f | 02b4ca1f | 02b4ca1f | 02b4ca1f |
| tileMultiple.wav | cb63fe2f | cb63fe2f | cb63fe2f | — |
| tileSingle.wav | 344ecf8c | 344ecf8c | 344ecf8c | — |
| zeroDevelop.wav | dd562093 | dd562093 | dd562093 | dd562093 |

**没有覆盖到的原版音效**：15 个之外没有别的 wav（`win7-assets` 与 `linux-minesweeper` 的
audio 目录都只有这 15 个）。原版另外两个角色（SingleReveal/MultiReveal 等）对应的就是
tileSingle/tileMultiple，已在表内。

---

## 2. 原版触发点基线（审计的参照系）

三个参照实现的触发点，用来判断我们接得对不对：

| 事件 | 原版（Win7 角色 / Lmy 克隆源码行） | Linux 复刻 | 本项目 |
|---|---|---|---|
| 新局发牌 | NewBoard → `gameStart` | `newGame()` → gameStart | `GameController.ets:219` gameStart（应用启动时 silent） |
| 首次点击（初始化动画） | FirstPaint → `firstPaint`（Lmy `Minesweeper.cpp:1497`） | 未实现 | `GameController.ets:932` firstPaint |
| 0 格洪泛展开 | `zeroDevelop`（Lmy `:1783`，在 `zeroDevelop()` 动画里） | 未实现 | `GameController.ets:935` zeroDevelop（判定条件见 3.2） |
| 单格翻开 | SingleReveal → `tileSingle` | `cellsOpened` size==1 → singleReveal | `GameController.ets:939` tileSingle |
| 多格翻开 | MultiReveal → `tileMultiple` | size>1 → multiReveal | `GameController.ets:937` / `:975` tileMultiple |
| 无效点击 / 和弦失败 | InvalidMove → `invalidMove`（Lmy 用 dbButtonClickFlag 近似，`:1361`） | `chord()` 失败 → `emit invalidMove()`（`BoardWidget.cpp:840`） | **没接**（见 3.2-A） |
| 插旗 / 问号 | `dbButtonClickFlag`（"planting or clearing a flag"） | `markToggled` → flag() | `GameController.ets:992` dbButtonClickFlag |
| 踩雷 | `mineBombStart` →（25 帧 × 23 ms = 575 ms 动画）→ `mineBombRun`（**SND_LOOP 循环**）→ `mineBombEnd`（Lmy `:1817/:1829/:1840`） | `mineTripped()` → 逐雷 gameLose | `:928` + `:1114` + `:1117`（时序见 3.1） |
| 判负（雷主题） | WrongGuess → `gameLose`，**每个雷都播、原版留 30 个缓冲可叠加** | 4 个 gameLose 轮转池 | `:1030` gameLose（**只播一次**，已知取舍） |
| 判负（花园主题） | `flowerLoseShort/Medium/Long`，按雷数分档 | `beginLoss(doomed)`：≤10 Short / ≤40 Medium / 否则 Long | `:1026-1028`（见第 4 节） |
| 通关 | BoardCleared → `gameWin` | `win()` | `:1017` gameWin |

原版"每个雷都播 gameLose"这条：本项目只播一次，是 `docs/SOUND-MAP.md` 里已经写明的取舍
（因为本项目没做"其它雷逐颗烧红"的级联动画），不是漏接。

---

## 3. 触发点逐条审计

### 3.1 全部调用点（14 处 `play` + 1 处开关）

| # | 调用点 | 音效 | 触发条件 | 与原版对照 |
|---|---|---|---|---|
| 1 | `GameController.ets:219` | gameStart | `startNewGame()` 且 `silent == false`；**应用首次启动走 `silent=true`**（`MinefieldCanvas.ets:97`） | 一致（原版启动静音、换难度才响） |
| 2 | `GameController.ets:932` | firstPaint | `tap()` 里 `wasReady`（本局第一次点击） | 一致（对应原版 FirstPaint） |
| 3 | `GameController.ets:935` | zeroDevelop | `tap()` 里被点格子的 `adjacent === 0` | **近似**：见 3.2-D |
| 4 | `GameController.ets:937` | tileMultiple | `tap()` 里 `outcome.opened.length > 1` | 一致 |
| 5 | `GameController.ets:939` | tileSingle | `tap()` 里其它情况（只开 1 格） | 一致 |
| 6 | `GameController.ets:942` | invalidMove | `tap()` 里 `!changed && !revealed && mark !== Flag` | **条件写错**：见 3.2-A |
| 7 | `GameController.ets:975` | tileMultiple | `chord()` 里 `e.revealedCount` 增加 | 一致（和弦成功） |
| 8 | `GameController.ets:992` | dbButtonClickFlag | `longPress()` 每次长按（旗/问号/取消三态循环） | 次数对，**但无条件响**：见 3.2-C |
| 9 | `GameController.ets:1017` | gameWin | `notifyGameOver()` 判胜 | 一致 |
| 10 | `GameController.ets:1026-1028` | flowerLose×3 | 花园主题判负，按总雷数分档 | 分档口径见第 4 节 |
| 11 | `GameController.ets:1030` | gameLose | 雷主题判负，**只播一次** | 已知取舍（原版逐雷叠加） |
| 12 | `GameController.ets:928` | mineBombStart | `tap()` 里踩雷 | 一致 |
| 13 | `GameController.ets:1114` | mineBombRun | 踩雷后 **+575 ms** | 一致（575 ms = 原版 25 帧 × 23 ms） |
| 14 | `GameController.ets:1117` | mineBombEnd | 再 **+3949 ms**（= mineBombRun.wav 的全长） | **近似**：原版是循环播到级联结束，见 3.2-E |
| 15 | `Index.ets:63` | — | 菜单「游戏 → 声音」开关，只改运行时状态、不落盘 | 原版存注册表；小差异 |

爆炸三段的时序（与原版对照）：

```
t = 0        mineBombStart 起爆（1.294 s）
t = 0~560    我们的爆炸动画 8 帧 × 70 ms = 560 ms（原版 25 帧 × 23 ms = 575 ms）
t = 575      mineBombRun 起播（3.949 s）
t = 4524     mineBombEnd 起播（1.951 s）
```

原版是 `mineBombRun` 带 `SND_LOOP` **一直循环到所有雷炸完**（级联时长随雷数变化），
我们是固定 3.949 s（正好一个 wav 的长度）后切到 mineBombEnd。
没有级联动画时这是合理近似，但**高级局（99 雷）比原版短**。

### 3.2 查出来的问题（4 类）

**A. 漏接：invalidMove 的正常触发场景根本没接（最严重的一条）**

- 原版：和弦失败（周围旗数 ≠ 数字）要响一声提示音
  （Linux 复刻 `BoardWidget.cpp:840`：`if (!m_board->chord(...)) emit invalidMove();`；
  Lmy 克隆 `Minesweeper.cpp:1357-1361` 和弦失败播 `IDR_WAVE3`）。
- 我们：`GameController.ets:960-980` 的 `chord()` 里，`e.chord()` 返回 false（旗数不符）时
  **不播任何音**；`tap()` 点已翻开的数字格也不播任何音。
- 后果：`invalidMove.wav`（峰值 -10.52 dBFS，全表最轻的一个）在正常玩法里**永远不会响**。

**B. 误响：invalidMove 只在"终局之后"才响**

`GameController.ets:941-943` 的条件：

```ts
} else if (!e.cellAt(r, c).revealed && e.cellAt(r, c).mark !== Mark.Flag) {
  SoundPlayer.play(Sound.INVALID_MOVE);
}
```

`reveal()` 返回 `changed == false` 只有三个原因（`MinesweeperEngine.ets:261-267`）：
**终局**、**格子已翻开**、**格子已插旗**。条件排除了后两个，
于是这个分支**只在"游戏已结束且格子没翻开没插旗"时成立**。
而结束对话框还开着时 `tap()` 会在开头直接 return（`:910-913`），
所以它实际会响的场景是：**在结束对话框点「换个难度(D)」（`Index.ets:38-42`，关掉对话框、
弹出游戏菜单，棋局仍处于 Lost 状态），再点棋盘上的未翻开格** → 每点一下响一声"无效移动"。
原版此时是静默的（棋盘已锁死）。
改法：把条件改成"和弦失败/无效点击"语义，并把终局情况排除掉。

**C. 误响：长按一个已翻开的格子也会响插旗音**

`GameController.ets:991-992`：

```ts
e.toggleMark(r, c);          // 返回值被丢掉
SoundPlayer.play(Sound.FLAG);
```

`toggleMark()` 在格子已翻开、已终局、越界时都返回 `false`（`MinesweeperEngine.ets:292-298`），
但音效无条件播。原版这时候是安静的。改法：`if (e.toggleMark(r, c)) { SoundPlayer.play(Sound.FLAG); }`。

**D. 近似偏差（不算 bug，但和原版有差）**

- zeroDevelop 的判定只看**被点那一格**的相邻雷数（`:933`）。若从数字格点开、经由 0 格连带
  洪泛展开，我们响 tileMultiple，原版响 zeroDevelop（Lmy 的 `zeroDevelop()` 是整段洪泛动画）。
- 第一次点击正好点开 0 格时，我们只响 firstPaint（`:930` 的 `else if` 链把 zeroDevelop 吃掉了），
  原版是两段都响。
- 花园玩法判负时，爆炸三段（`:928`/`:1114`/`:1117`）**和** flowerLose 一段**同时响**，
  一共 4 条音叠在一起；原版花园玩法只有 flower 一条
  （Linux 复刻 `Sounds.h:71`：花园模式下 `mineTripped()` 直接 return）。
  这一条算"重复叠播"，也是三处问题里用户最容易听出来的。

---

## 4. 花园玩法判负的三段音效：分档核对（重点）

### 4.1 现状

`GameController.ets:1018-1028`：

```ts
} else if (this.atlas.gameStyle === GameStyle.Flowers) {
  const mines: number = this.engine.mineCount;
  const name: string = mines <= 10 ? Sound.FLOWER_LOSE_SHORT
    : (mines <= 40 ? Sound.FLOWER_LOSE_MEDIUM : Sound.FLOWER_LOSE_LONG);
  SoundPlayer.play(name);
}
```

- `engine.mineCount` 是**本局总雷数**（`MinesweeperEngine.ets:166/208/449`；剩余雷数是另一个
  方法 `minesRemaining()` = 总雷数 − 已插旗数，`:242-244`）。
- 分档阈值：≤10 → Short、≤40 → Medium、>40 → Long。
- **结论：当前实现按总雷数分档，符合本次要求。**
- 花园玩法本身是可达路径：菜单「游戏 → 外观(F7)」→ 选花朵 → 确定
  （`Appearance.ets:196-200`，存 `GameStats.gameStyle=1`，
  `MinefieldCanvas.ets:92` 读回，`SpriteAtlas.ets:125` 换图集）。

### 4.2 需要 lead 拍板的一个口径分歧（附数字）

本地**唯一**能查到的花园分档参照实现是 Linux 复刻 `src/ui/Sounds.h:57-63`：

```cpp
void beginLoss(int doomedMines)          // doomedMines = 判负后**还要炸的雷数**
{
    if (m_loseStyle == LoseStyle::Flowers) {
        play(doomedMines <= 10   ? m_flowerShort
             : doomedMines <= 40 ? m_flowerMedium
                                 : m_flowerLong);
    }
```

它的 `doomedMines` 在 `MainWindow.cpp:249-256` 是这么数的：
`cell.mine && cell.mark != Mark::Flag && !cell.exploded` —— 即**没插旗、还没炸的雷**，
也就是"剩余雷数"，而不是总雷数。

两边阈值完全相同（10 / 40），差别只在喂进去的数：

| 局面 | 总雷数口径（我们） | 待爆雷数口径（Linux 复刻） | 差出来的档 |
|---|---|---|---|
| 初级 10 雷，插了 8 面旗 | 10 → Short | 2 → Short | 同 |
| 中级 40 雷，插了 30 面旗 | 40 → Medium | 10 → Short | **差一档** |
| 高级 99 雷，插了 90 面旗 | 99 → Long | 9 → Short | **差两档** |

支持"总雷数"口径的两条理由：
1. 阈值 10 / 40 恰好就是初级 / 中级的**总雷数**，三段音效与三个标准难度一一对应，
   自带"难度越大、枯萎时间越长"的语义；
2. 本次任务的要求就是按总雷数。

支持"待爆雷数"口径的一条理由：Linux 复刻的注释说这三段是"sized to the cascade"
（按级联规模配的音），而级联炸的是没插旗的雷。

**取证边界（必须如实说）**：本地素材里**没有**原版的 `MINESWEEPER.xml`
（`minesweeper-refs` 下 0 个 xml 文件），也没有带花朵玩法的原版 exe
（Lmy 复刻的 `releases\Minesweeper.exe` 是复刻件；花簇主题是 Win7 才有的，
XP 的原版 exe 里没有）。所以**无法从原版侧再取证**，这条只能由 lead 拍板。
若要改，代码位置就是 `GameController.ets:1025` 一行。

---

## 5. 播放通道：会不会互相打断

### 5.1 机制

`SoundPlayer.ets`：

- `players: Map<string, media.AVPlayer>`（`:44`）—— **每个音效名一个独立播放器实例**，最多 15 个。
- `playAsync()` 的重播路径是 `stop() → prepare() → seek(0) → play()`（`:136-151`）。

### 5.2 结论

| 情况 | 行为 | 是否符合原版 |
|---|---|---|
| **不同**音效同时响 | 各自独立播放器，**互不打断、可叠加** | 符合。爆炸三段就是靠这个叠起来的：mineBombStart（1.294 s）在 +575 ms 时还没结束，mineBombRun 直接叠上去 |
| **同一个**音效重复触发 | 同一个播放器被 stop 后从头重播，**前一次被截断，不叠加** | 符合。Linux 复刻也是 `e.stop(); e.play();`（`Sounds.h:97`），原版 `PlaySound(..., SND_ASYNC)` 同样是重触发覆盖 |
| 判负时逐雷叠加 | 我们只播一次 gameLose | **不符合**（原版留 30 个缓冲逐雷叠加）。已知取舍，见 `docs/SOUND-MAP.md` |

### 5.3 三处隐患（建议交给 lead 修）

1. **同名音效并发会互相打断**：`playAsync` 是 fire-and-forget
   （`:69` `SoundPlayer.playAsync(...).catch(...)`）。两个同名音效几乎同时触发时，
   两条异步链会在**同一个 AVPlayer** 上交错地 stop/prepare/seek/play，
   可能抛状态机错误（被 catch 吞掉，表现为声音缺失）或把播放截断在半路。
2. **`ensurePlayer` 首次并发会漏一个播放器**：`:95-97` 只在 `prepare()` 之后才写 Map，
   两个同名音效"首次同时触发"会各自 `createAVPlayer()`，第二个覆盖 Map 条目，
   **第一个播放器永远不会被 release**（泄漏）。
3. **`SoundPlayer.dispose()` 从未被调用**：全仓只有定义（`SoundPlayer.ets:155`）没有调用点；
   `GameController.dispose()`（`:1766`）只停计时器。15 个 AVPlayer 及其 fd
   在应用整个生命周期不释放。另外 `SoundPlayer.playSequence()`（`:75`）是**死代码**（无人调用，
   爆炸用的是 `playBombTail()` 的两个 setTimeout）。

### 5.4 音量

代码里**没有任何音量设置**，AVPlayer 用默认音量 1.0，播出来的就是文件本身的电平：
最响的 zeroDevelop 峰值 **0.00 dBFS（满刻度）**，tileSingle/tileMultiple 约 -0.05 dBFS，
最轻的 invalidMove 峰值 -10.52 dBFS。
参照实现 Linux 复刻统一用 `e.setVolume(0.9)`（`Sounds.h:92`）。
若真机听感偏吵，建议给所有播放统一加 0.9 的音量系数（改动点：`SoundPlayer.ets:151` 前的 `play()`）。

---

## 6. 真机试听对照清单（给用户照着听）

操作前置：菜单「游戏 → 声音」打开；音量与系统媒体音量一致。
下表的"时长/电平"都是本报告第 1.2 节的实测值，听感描述由包络推出。

| 编号 | 你要做的操作 | 该响的音效 | 时长 | 峰值电平 | 听感该是什么样 |
|---|---|---|---|---|---|
| T1 | 换难度 / 点笑脸开新局 | gameStart | 2.554 s | -0.51 dBFS | **前 43 ms 是安静的**，然后像洗牌一样"沙沙"翻牌，2 秒多慢慢落下去 |
| T2 | 新局后点**第一下**格子 | firstPaint | 2.368 s | -0.06 dBFS | 一记很脆的"铛"，起音几乎无延迟（0.2 ms），后面拖着长长的余韵，最后 100 ms 已经很轻（-37 dB） |
| T3 | 点开一个**相邻有雷**的数字格 | tileSingle | 0.186 s | -0.05 dBFS | 一声短促、清脆的"嗒"，几乎全在前三分之一，尾巴快速掉到 -8 dB |
| T4 | 一次翻开**多个**格子 | tileMultiple | 0.325 s | -0.04 dBFS | 比 T3 长一点、音量一样，中段更饱满（-8.7 dB），像一小串砖块一起翻 |
| T5 | 点开一个**周围 0 雷**的格子（洪泛展开） | zeroDevelop | 0.233 s | **0.00 dBFS（满刻度）** | 三个开格音里**最响**的一个，清脆的"哗啦"，衰减平缓（尾 -7 dB） |
| T6 | 长按一格：插旗 → 问号 → 取消，每按一次 | dbButtonClickFlag | 0.184 s | -0.91 dBFS | 短促的"哒"，比开格音闷一点，尾巴掉得快（尾 -21 dB） |
| T7 | 双击一个**旗数不够**的已翻开数字格 | **应该响 invalidMove**（现在**不响**，见 3.2-A） | 0.279 s | -10.52 dBFS（最轻） | 原版是一声很轻、发闷的"嘟"，前 19 ms 几乎无声 |
| T8 | 踩雷 | mineBombStart →（约 0.6 s 后）mineBombRun →（再 3.9 s 后）mineBombEnd | 1.294 / 3.949 / 1.951 s | -1.65 / -1.25 / -2.82 dBFS | 先"轰"一声炸开（起爆），中段是一段**几乎不衰减的低频轰鸣**（头 -9、中 -11、尾 -11.5 dB），最后"噗"一声收尾（尾 -32 dB） |
| T9 | 雷主题判负 | gameLose | 1.997 s | -2.91 dBFS | 低沉的一声，起音很轻（头 -44.6 dB），中段才起来（-25 dB），慢慢沉下去 |
| T10 | 花园主题判负（外观里选花朵） | flowerLoseShort/Medium/Long | 3.529 / 6.037 / 7.941 s | -1.10 / -1.94 / -1.09 dBFS | **前 20 ms 几乎没有声音**（-37 dB），中段才慢慢响起来（-16 dB），是"慢慢枯萎"的长音，尾巴几乎归零（-75 ~ -78 dB）。**注意：现在它会和爆炸三段同时响**（见 3.2-D） |
| T11 | 通关（扫完所有雷） | gameWin | 2.183 s | -0.01 dBFS | 前 40 ms 安静，随后一声明亮的上扬和弦，峰值几乎满刻度，尾部渐渐散掉（尾 -54 dB） |

**听感判定口径**：只要"起音时机 + 持续长短 + 亮/闷"三样对上，就算过。
最难判的是 T5（zeroDevelop）和 T3（tileSingle）——两者峰值几乎一样（0.00 vs -0.05 dBFS），
区别在长度和衰减（0.233 s 且衰减慢 vs 0.186 s 且衰减快）。

---

## 7. 复现方法（都是只读、可重跑）

```powershell
# 1) 素材测量（纯标准库）：采样率/位深/声道/时长/峰值/RMS 包络/sha256
#    脚本：本次临时脚本 sound_measure.py（不入仓）
#    根目录配置 sound_roots.json：
#      app   = C:\Users\19161\saolei\entry\src\main\resources\rawfile
#      win7  = C:\Users\19161\Desktop\minesweeper-refs\win7-assets\audio
#      linux = C:\Users\19161\Desktop\minesweeper-refs\linux-minesweeper-main\assets\audio
#      lmy   = C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\Minesweeper\res\wav
python sound_measure.py sound_roots.json sound_data.json

# 2) 触发点：全量搜
grep -n "SoundPlayer\.\|Sound\.[A-Z_]\+" C:\Users\19161\saolei\entry\src\main\ets

# 3) 原版触发点基线
#    Lmy 克隆（Win7 UI 复刻）的 6 处 PlaySound：
#    C:\Users\19161\Desktop\minesweeper-refs\Minesweeper-master\Minesweeper\utf8\Minesweeper.cpp
#      :1361 dbButtonClickFlag(和弦失败) :1497 firstPaint :1783 zeroDevelop
#      :1817 mineBombStart :1829 mineBombRun(SND_LOOP) :1840 mineBombEnd
#    Linux 复刻的映射与分档：
#    C:\Users\19161\Desktop\minesweeper-refs\linux-minesweeper-main\src\ui\Sounds.h
```

---

## 8. 交给 lead 的待改清单（本次审计**未改** app 仓）

按"用户最容易听出来"排序：

| 优先级 | 问题 | 位置 | 建议改法 | 影响 |
|---|---|---|---|---|
| P1 | 和弦失败 / 无效点击**没有音效**（invalidMove 永远不会响） | `GameController.ets:960-980`（chord）、`:941-943`（tap） | chord 失败时播 `Sound.INVALID_MOVE`；tap 点已翻开数字格时也播 | 补上一整条原版音效 |
| P1 | 花园玩法判负时**爆炸三段与 flower 音叠着响** | `GameController.ets:928`/`:929` | 花园主题下跳过 `BOMB_START` + `playBombTail()`，只留 flower 一条 | 消除 4 条音叠在一起的噪音 |
| P2 | 终局后点棋盘会误响 invalidMove | `GameController.ets:941-943` | 条件补上 `!e.isOver()`，并改成"和弦失败"语义 | 消除误响 |
| P2 | 长按已翻开/终局后的格子仍响插旗音 | `GameController.ets:991-992` | `if (e.toggleMark(r, c)) { SoundPlayer.play(Sound.FLAG); }` | 消除误响 |
| P3 | 同名音效并发时互相截断；首次并发漏播放器；`dispose()` 从不调用 | `SoundPlayer.ets:93-152` | ensurePlayer 缓存 Promise；playAsync 对同一播放器加串行/互斥；页面销毁时调 `SoundPlayer.dispose()` | 稳定性 + 资源释放 |
| P3 | 音量未设，默认 1.0（zeroDevelop 满刻度） | `SoundPlayer.ets:151` | 统一 `player.volume = 0.9`（对齐 Linux 复刻） | 听感不刺耳 |
| P3 | 声音开关不落盘 | `Index.ets:63` | 存进 `GameStats`（和 `gameStyle` 一样） | 重启后仍保持原版的设置 |
| 待定 | 花园分档口径：总雷数（当前）还是待爆雷数（Linux 复刻） | `GameController.ets:1025` | 需要原版证据或 lead 拍板；本地无法再取证（见 4.2） | 高级局可能差一档音效 |
| 备注 | 判负时逐雷叠加 gameLose | `GameController.ets:1030` | 若要做级联动画再补；当前是有意取舍 | 已知差异 |

---

## 9. 审计边界（如实说明）

- 本轮**没有跑过模拟器、没有连任何设备、没有真机试听**；所有数字来自 wav 文件的离线测量
  与源码阅读。试听结论需要用户在真机上按第 6 节核对。
- app 仓只读：本次审计**没有修改** `C:\Users\19161\saolei` 下任何文件。
- 花园分档的原版口径**未能取证**（本地无 `MINESWEEPER.xml`、无带花朵玩法的原版 exe），
  见 4.2。
- 「原版素材」的取样范围是 `minesweeper-refs` 下的 3 份 audio 副本（共 15 个 wav，
  内容互为字节相同），不是从原版 exe 里现场提取的资源段。

---

## 10. 2026-11-04 用户报障后的修正（已落地并有回归）

用户 2026-11-04 报了两条：

> 1. 音画不同步
> 2. 在点击第一个方块打开的时候，还是会播放一次开始音频，原版是只有方块波浪形展开的时候才播放一次

两条都查清了根因并已改。**这一节把改动和依据集中记在这里**，
前面的章节保持「审计当时的样子」不动，便于对照。

### 10.1 首点音效归属 —— 原来确实挂错了

第 2 节「原版触发点基线」表里写着：

| 事件 | 原版 | 本项目（当时） |
|---|---|---|
| 新局发牌 | NewBoard → `gameStart` | `GameController.ets:219` gameStart |
| 首次点击 | FirstPaint → `firstPaint` | `GameController.ets:932` firstPaint |

**这个「首次点击 → firstPaint」是错的**。两份复刻都不把任何音效挂在首点上：

- **Qt 复刻** `src/ui/MainWindow.cpp:41-48`，注释原文
  *"The original's SingleReveal / MultiReveal pair."*：
  ```cpp
  connect(m_board, &Board::cellsOpened, this, [this](const QVector<QPoint> &order) {
      if (order.size() > 1) m_sounds.multiReveal();
      else if (order.size() == 1) m_sounds.singleReveal();
  });
  ```
  —— 判据是**翻开几格**，没有「首点」这一说。
- **Lmy 复刻** `utf8/Minesweeper.cpp:1774-1797`：`zeroDevelop()` 是独立函数，
  判据是**被点那格的相邻雷数**，同样不看是不是首点。
- **Lmy 复刻** `utf8/Minesweeper.cpp:1495-1508`：`firstPaint`（`IDR_WAVE1`，
  见 `Minesweeper.rc:344`）是在**发牌的逐格绘制循环之前**播的
  —— 它是**发牌动画的配乐**，不是首点的音。

本项目原来的 `else if` 链：

```ts
if (wasReady)            SoundPlayer.play(Sound.FIRST_PAINT);   // 首点：只响这一声
else if (adjacent === 0) SoundPlayer.play(Sound.ZERO_DEVELOP);
else if (opened > 1)     SoundPlayer.play(Sound.TILE_MULTIPLE);
else                     SoundPlayer.play(Sound.TILE_SINGLE);
```

`wasReady` 排在最前，于是**首点永远只响 firstPaint**，
`zeroDevelop` / `tileSingle` / `tileMultiple` 在首点时一声不响。
用户听到的「又播了一次开始音」就是它。

**已改**：
- 首点删掉 `wasReady` 分支，改按 `adjacent==0 → ZERO_DEVELOP` /
  `opened.length>1 → TILE_MULTIPLE` / 否则 `TILE_SINGLE` 走（与其它开格同一套规则）；
- 发牌动画改播 `Sound.FIRST_PAINT`；
- `Sound.GAME_START` 目前**全仓无调用点**（两份复刻对「发牌那一刻响哪一条」互相矛盾，
  详见 `SOUND-MAP.md` 的「两份复刻与分歧」；在真 Win7 上试听定案前不擅自补播）。

### 10.2 `invalidMove` 那条分支是**死代码**（第 3.2-A 已记，这次确认并删掉）

`tap()` 里原来有：

```ts
} else if (e.gameState === GameState.Playing &&
  !e.cellAt(r, c).revealed && e.cellAt(r, c).mark !== Mark.Flag) {
  SoundPlayer.play(Sound.INVALID_MOVE);
}
```

`e.reveal(r, c)` 返回 `changed=false` 只有两种可能
（`MinesweeperEngine.ets:259-289`）：

1. 棋局已终局（`:261`，`isOver()` 见 `:246-248`）；
2. 该格**已翻开**或**已插旗**（`:265-267`）。

而上面那个分支要求的是「**没**翻开、**没**插旗」——
**两条正好互斥，所以它永远进不去**。

而且原版本来就不该在这里响：
**Qt 复刻** `src/ui/BoardWidget.cpp:833-849`（`mouseReleaseEvent`）里
`emit invalidMove()` 只出现在 `Press::Chord` 分支（**和弦失败**），
普通点击那条分支只调 `m_board->reveal()`，不响任何音。
我们的 `chord()` 里已经是对的。

**已改**：删掉这条死分支，并留下注释说明原版的口径。

### 10.3 音画不同步 —— 两套时钟的问题

**根因**：画面动画走 `Date.now()` 的**绝对时间轴**
（`DealIn.ts` 的 `dealStart`、涟漪的 `rippleStart`、`Anim` 的 `tripElapsed`），
声音却是从「调用 `play()` 的那一刻」开始**异步**准备播放器的：

```
getRawFd → createAVPlayer → 等 initialized → prepare → seek(0) → play()
```

第一次播某个音效要几百毫秒，全花在**该响的那一刻之后** ——
于是声音总是比画面晚一截。

**已改**（`SoundPlayer.ets`）：

1. **`warmup()`**：启动后把 15 个音效的播放器全部提前建好并 `prepare`，
   真正要播时只剩 `seek(0) → play`，延迟降到几十毫秒。
   预热挂在 `MinefieldCanvas.ets` 的 `setTimeout(..., 0)` 上（让首帧先画完）。
2. **`playAt(name, atMs)`**：把「该响的绝对时刻」交给声音层 ——
   按剩余时间补偿，**声音与画面落在同一个绝对时刻**。
   发牌配乐、翻开声、爆炸三段、胜利音都改用它。
3. **重播路径分两档**：播放器正在 `playing` 时直接 `seek(0)`
   （API 契约：`play()` 只在 `prepared`/`paused`/`completed` 可调，
   在 `playing` 下调用会抛 5400102）；其余状态才走 `stop → prepare → seek → play`。

### 10.4 爆炸三段的切换点：抄错了 575ms

第 3.1 节记的原版时序是「爆炸动画 25 帧 × 23ms = 575ms → 切到爆炸中音」。
那 575ms 是**参考实现**的动画时长，**不是本工程的**。

本工程的爆炸是 `Anim.EXPLODE_FRAMES = 23` 帧 × `1000/23 = 43.478` ms
= **1000ms**（`Anim.ets:60-62`，依据是原版的 `MineTrip.xml`）。
照抄 575 会让「爆炸中音」比画面上的爆炸**早 425ms** 响起来 —— 又一处不同步。

**已改**：`playBombTail()` 用 `Anim.explodeDurationMs()`
（本工程自己的动画时长），而且三段都锚到**级联的绝对起始时刻**，
不再各用各的 `setTimeout`（那是「从调用时刻起算」，一抖动就各自漂移）。

### 10.5 `gameLose` 改成**逐雷各炸一声**（第 8 节「备注」那行的取舍，已推翻）

第 8 节把它记成「有意取舍」，理由是「本项目没做其它雷逐颗烧红的级联动画」。
**那个理由现在不成立了** —— 级联动画早就有了
（`Anim.startTrip(booms)` + `Anim.boomFrame(index)` + `boom.startMs`）。

原版的判负音是**每颗雷各炸一声、叠着响**
（**Qt 复刻** `src/ui/Sounds.h:10-12`：
*"the original keeps 30 buffers so cascading mines overlap"*），
而且**由动画时钟触发**（**Qt 复刻** `src/ui/BoardWidget.cpp:305-306`：
环走到这颗雷时才 `emit mineTripped()`）——
**那才是原版的音画同步机制**。

**已改**：
- `playBombTail()` 按每颗雷的 `boom.startMs`（与 `Anim.boomFrame()` 用的是同一个数）
  **逐颗**触发 `gameLose` —— 声音与那一格的爆炸帧**同一时刻**；
- 新增 `SoundPlayer.playPooled()`：4 个播放器轮转，
  单一播放器会让后一声打断前一声，级联听起来是「哒哒哒」而不是原版的「轰隆隆一片」。

### 10.6 自动化回归（新增 `tools/click_cases/sound.json`，8 条）

音效是**听觉**的，像素断言抓不到。但应用每播一声都会打一行日志：

```
[Sound] 播放 <名字> at=<时刻>            —— 立即播放
[Sound] 对齐播放 <名字> at=<时刻>         —— 对齐到画面的绝对时刻
```

于是「这一刻到底播了哪一声」可以用日志断言 —— 硬且可复现。

跑测器新增了一个断言类型 `hilog_checks`（在**同一个日志窗口**里做多条检查）。
为什么不能写成「两个 `hilog_regex` / `hilog_absent` 连着写」：
`log_new_lines()` 每读一次就把读到的行标成「已见过」，
所以连续两个 expect 看不到同一批日志 —— 第二个会**空跑通过**（假的绿灯）。
这是实测踩到的：首轮跑测「首点只播一声」那条用例**假通过**，
因为它数到了两条重复日志（`playAt` 调度时一行 + `play()` 实际播放时一行）。

### 10.7 顺带修的：`SoundPlayer.playSequence()` 是死代码

全仓无调用点（爆炸三段是各自 `setTimeout` 的）。已删。

