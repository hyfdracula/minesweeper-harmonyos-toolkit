# Codex 对抗性复审记录（2026-11-03 这一轮）

复审由 `~/.dsh/skills/codex-delegate/codex-delegate.ps1 -Review` 跑的，
模型是 Codex CLI（gpt-6-sol）。**每次复审的裁定值和它的来源都记在这里**，
不写成「通过」了事。

> 裁定解析按 `codex-delegate/SKILL.md` 的口径：
> 模型给了 `VERDICT:` 行 → 直接采信；
> 没给行、但有 P0/P1/P2、Critical/High 等标记 → **由标记推断**，报告时说明是推断；
> 两者都没有 → `UNKNOWN`，**不得当作通过**。

| 轮次 | 范围 | 裁定 | 来源 | 发现 | 处置 |
|---|---|---|---|---|---|
| 第 4 轮 | `50e1bae` 之前 | **BLOCKER** | 由 P0/P1/critical 标记**推断**（无 VERDICT 行） | ① 求解器把旗算进 unknown 又减旗数 → 真雷被标成安全（`solve([1,'F','X','X'],1,4,2)` 返回了可能爆的那格）② preflight 用 `hdc shell ls` 判装没装，而它对**不存在的路径也退出 0** | ① `all_unknown` 只留 X，旗不重复扣 ② 改用 `bm dump -n` + 看 `aa start` 的**输出文本** |
| 第 5 轮 | `50e1bae..HEAD` | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | ① preflight 可能把**上一轮**残留的布局日志当成本次的，应用没画出来也报「正常」② `tablet_check.py` 只读当前那个盘面，另外三个难度根本没跑到 ③ 截图取不到也照样打印「通过」 | ① 起应用**前**记设备时间戳，只认之后的布局行 ② `tablet_check` 依次切四个盘面逐个核对，期望表补齐中级 ③ 检查 `file recv` 的返回码和文件非空 |
| 第 6 轮 | `e05bfdd..HEAD` | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行） | `free` 坐标系在**矮画布**上会落到统计窗**里面**：画布 1280×484、密度 3.5 时统计窗占 x=16..1264、y=16..468，而「棋盘上方空隙」算出来是 (26,80) | 空间改名 `outside_stats`，**按窗的实际边界**挑点（窗居中 → 只可能在左/右/上/下）；离线验过五组画布含该反例 |
| 第 7 轮 | 应用仓 `edb935f..ca5548c`（结算动画可跳过） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | ① 跳过动画时**正在响的爆炸声还在放**（`stopBombTail()` 只撤了定时器）② **长按菜单栏**也会跳过动画，与普通点击菜单栏被排除在外不一致 | ① 跳过时 `SoundPlayer.stop(BOMB_START/BOMB_RUN/BOMB_END)` 三段都停 ② `longPress()` 里先把菜单栏排掉，再判跳过 |
| 第 8 轮 | 规格仓 `1c553f3..HEAD`（跑测器归因修复） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | 文档里引用的 `docs/verify/CM_2355tabfull.log` **不存在**，而跑测器只往 stdout 打 —— 仓里没有任何能核对的产物（原文：*the updated handover relies on a nonexistent log as evidence*） | ① 跑测器每轮自动写 `docs/verify/CM_<tag>.log`（`_Tee` 类，stdout 同时写屏幕和文件）② 那一轮的成绩单**手工归档**成 `docs/verify/CM_2355tabfull.log` |
| 第 9 轮 | 规格仓 `bc22e84..HEAD`（跑测器唤醒/错误检查 + 新增回归用例 + 文档） | **PASS** | **由「无任何严重级别标记」推断**（无 VERDICT 行；模型原话：*I found no actionable defect in the diff*） | 无 | — |
| 第 9 轮 | 应用仓 `d6bac3d..HEAD`（局终点棋盘重开） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | 「重开那一击把画布的双击状态也记下了 → 300ms 内再点同一格被判成**和弦** → 新局里那格还没翻开，和弦什么也不做 → 玩家想开的第一下被静默吃掉」 | 局终时（`controller.gameOver`）**清掉**双击状态再走 `tap()`；`GameController` 加公开只读属性 `gameOver`。应用仓提交 `80a0f98` |
| 第 10 轮 | 规格仓 `7913b67..HEAD`（唤醒节流 + 周期性唤醒 + 目标机决策文档） | **PASS** | **由「无任何严重级别标记」推断**（无 VERDICT 行；模型原话：*I found no actionable regression in the changed wake-up, logging, or state-data paths. The remaining changes are documentation updates.*） | 无 | — |
| 第 11 轮 | 应用仓 `c121cc8..HEAD`（音效：归属改正 + 音画对齐 + 逐雷爆点） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；本次无 P0/P1/critical） | ① **逐雷音效在级联被打断时没取消** —— 那些 `setTimeout` 的句柄没留，`stopBombTail()` 撤不掉，跳过动画或换局后爆炸还在结算框上炸；而且池子里的 `GAME_LOSE` 也不在 `SoundPlayer.stop(BOMB_*)` 的射程内 ② **预热建了 19 个 AVPlayer**（15 个普通 + 4 个池子），超过平台建议的 16 个上限，资源紧张的设备上后面的音效建不出来 ③ **预热与播放并发时重复建播放器** —— `ensurePlayer()` 只看已建好的 `players`、不看在建的 `warming`，两条路各建一个，后者顶掉前者，多出来的那个 `dispose()` 也 release 不掉（泄漏）④ **池子无条件轮转会挑到还在播的播放器** —— `seek(0)` 把那声爆炸切断，而这正是池子要避免的事（级联里 5 颗以上雷会挤在一起起爆） | 四条全修：① 逐雷的定时器句柄存进 `bombBoomTimers`，`stopBombTail()` 里全撤；新增 `SoundPlayer.stopPooled()`，跳过动画时把池子里的声音也停掉 ② 预热改成**按优先级 + 有预算**（`WARM_BUDGET=12`），实例总数不超 `HARD_MAX=14`；不常用又互斥的（`gameStart` 无调用点、三条花园音效）不预热，改懒建 ③ `ensurePlayer()` 缓存**在建的 promise**，谁要都 await 同一个 ④ 池子改成**挑空闲的**播放器，全忙时挑开始最早的 |
| 第 12 轮 | 应用仓（第 11 轮那四条修完之后） | **CONCERNS** | 由 P2/P1 标记**推断**（无 VERDICT 行；模型明说「已通过对实际方法运行内存中的异步 AVPlayer 桩验证关键路径」——它**真的复现**了） | **1 条 P1 + 5 条 P2，全部关于新加的音效池的并发**：① **【P1】扩容前不预留名额** —— 多个 `playPooledAsync()` 都通过容量检查后在 `await createPlayer()` 挂起，在途实例没算进 `pool.length`/`playerCount()`；**实测预热 12 个实例在并发 6 次播放后涨到 19 个、池子涨到 9**（上限 14 和 4）② **播放要等整个池扩容** —— 预热只建 2 个池成员，第一次爆炸即使有空闲的也必须先串行建另外两个 → 冷创建延迟又放回爆点之后，**破坏首次爆炸的音画同步**；建失败则已有的两个**完全不播** ③ **选中的成员没先标记占用** —— `playOn()` 里 await 期间成员还不是 `playing`，后续调用继续选**同一个**；**实测 3 个并发调用全选了 0 号** ④ **`stopPooled()` 作废不了在途请求** —— 正在 `await createPlayer()` 的请求回来后照样播 → 结算框出现后爆炸声重新响起 ⑤ **`HARD_MAX` 对普通播放器没真正执行** —— 只打印警告仍无条件创建；可达路径：预热 10 普通 + 2 池 → 判负把池扩到 4 → 再玩三种花园难度触发三条失败音 = 17 个，正常游戏中都不释放 ⑥ **换局时没停已播的逐雷音效** —— `startNewGame()` 只撤定时器，不停池成员；逐雷声 2 秒而每颗雷动画只有 1 秒，级联结束后立刻「再玩一局」会让最后几颗雷的声音盖住新局发牌 | 六条全修：① **建之前同步占位**（`poolPending` + 全局 `creatingCount`），容量检查与占位之间没有 await ② 改成**先用现成的空闲成员**，没得用才建（播放不再等扩容）③ 选中成员**立刻** `busy[i]=true`（同步），播完 `finally` 里放开 ④ 加**取消代次**（generation）：`stopPooled()` 代次 +1，在途请求回来一看代次变了就作废并 release ⑤ `HARD_MAX` 到顶时先**回收一个闲置的普通播放器**（`reclaimIdle()`，池子成员和正在响的不回收），回收不到才退让 ⑥ `startNewGame()` 里补 `SoundPlayer.stopPooled(Sound.GAME_LOSE)` |
| 第 13 轮 | 应用仓（第 12 轮那六条修完之后） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；模型明说「Asynchronous stub checks confirmed …」——**又用桩复现了**） | ① **池子该扩容时却抢占** —— 两个预热成员都被占用时，代码直接挑「开始最早」的那个用掉，**永远走不到扩容那条路** → 池子停在 2 个，后面的爆炸只能把前面的声音**切断**而不是叠起来 ② **已存在成员的取消没贯穿** —— `stopPooled()` 把代次 +1 并 stop 了播放器，但那条路的 `playOn()` **再也不查代次** → 它回来照样 `play()`，结算框上面又炸一声 ③ **池子的预热没预留容量** —— 预热直接 `createPlayer()`，在途实例既不在 `poolPending` 也不在 `creatingCount` 里 → **实测池子 6 个（上限 4）、实例 16 个（上限 14）**；重进 warmup 还会重复建 | 三条全修：① 改成**先试扩容、扩不了才抢占**（扩容走新的 `growPool()`，建之前同步占位）② `playOn()` 加**可选的取消判据**，在真正 `play()` **之前**查一次 ③ 池子的预热也走**同步占位**，并用 warming 的键**去重** |
| 第 14 轮 | 应用仓（第 13 轮那三条修完之后） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；模型明说「Both defects were reproduced with asynchronous stubs」——**又复现了**） | ① **抢占会撞上正在做状态切换的成员** —— 几个雷在同一个 stop/prepare/play 的延迟窗口内起爆，所有成员都 busy，而 fallback **无视 `busy`** 又对「开始最早」的那个调了一次 `playOn()` → 两个状态机叠在同一个 AVPlayer 上；**实测 6 个请求 + 4 个成员时有两个成员出现并发操作，播放失败** ② **取消没在 seek 之前查** —— 慢速扩容跨过一次「跳过/换局」时，`growPool()` 因代次变了返回 -1，而调用方**掉进 fallback** 挑了一个成员；若那个成员正在放新一轮的级联，这一条路会 `seek(0)` **把新声音倒回开头**（且不查取消） | 两条全修：① 选择逻辑改成**四级**：空闲的 → 扩容 → **只抢「已经在播、且没有状态切换在进行」的**（`!busy && state === 'playing'`）→ 全都在切换状态就**等**（每 15 ms 重新挑，最多等 600 ms）② `growPool()` 返回 -1 之后**先查取消代次**，作废就**直接返回**；`playOn()` 也改成**动手之前就查取消**（`'playing'` 那条快速路径原来直接 `seek(0)`，会倒回**下一轮**的声音） |
| 第 15 轮 | 应用仓（第 14 轮那两条修完之后） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；模型明说「两条路径均已通过对实际方法运行内存桩复现」——**又复现了**） | ① **逐雷音效没跟随动画暂停** —— 爆炸级联期间切到后台时，`pauseForBackground()` 停了帧定时器（`Anim.tripElapsed` 随之暂停），但新增的逐雷 `setTimeout` **仍在触发** → 还没显示爆炸的雷**提前发声**，回到前台继续动画时反而没有对应声音；**实测动画停在 100 ms 时，安排在 600 ms 起爆的雷仍然播了** ② **取消在途请求时会过早复用成员** —— 跳过动画或换局时若某成员仍在等 `stop()`/`prepare()`，原实现**立即清 `busy`** 且不等这次 `stop()` 完成 → 下一轮级联可能重新选中同一成员，与旧请求**并发准备**同一个播放器（取消代次只阻止旧请求最后 `play()`，挡不住状态操作干扰新播放）；**实测可复现「新旧请求并发准备同一成员」** | 两条全修：① 逐雷爆点改成**由动画时钟触发** —— 去掉每颗雷的 `setTimeout`，改为每帧按 `Anim.tripElapsed` 判断「哪些雷到点了」（`fireBoomSounds()`）；动画停 → 声音停，动画继续 → 声音接着走。这正是原版的做法（声音由动画时钟触发）② `stopPooled()` **不再清 `busy`** —— 占用改由**持有它的那个请求**在退出时（`finally`）释放，这样旧请求的状态操作没结束之前，成员不会被下一轮挑中；抢占条件也收紧成 `!busy && state === 'playing'` |
| 第 16 轮 | 应用仓（第 15 轮那两条修完之后） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行；模型明说「两项均已用内存内异步桩复现，但尚未进行真机音频验证」） | ① **回收普通播放器前没看在途占用** —— `state !== 'playing'` **不代表闲置**：普通播放请求可能已经拿到它、正等着 `stop()`/`prepare()`；这时回收它 → 原请求的 `prepare()`/`play()` 失败，**音效丢失**（异步桩可复现；如池扩到四成员后，花园失败音的懒创建可能回收同时触发的翻格音播放器）② **回收失败时仍然继续创建** —— 到顶且无可回收时只打警告，随后仍 `creatingCount++` 并 `createPlayer()` → 普通音效路径**没有真正执行硬上限**；**实测能一路建到 17 个**，超过平台建议的 16 个 | 两条全修：① 普通播放器也加 `playerBusy` 标记（拿到播放器到放完为止），`reclaimIdle()` 跳过有在途请求的 ② 回收不到名额时**真的不建**（抛错 → 这一声不播），宁可少一声也不能撑爆实例数 |
| 第 17 轮 | 应用仓 `e0cdc14`（对比 HEAD，工作区已提交） | **（无内容可审）** | — | 模型回的是「工作区是干净的，请求的 git diff 是空的，没有可审的代码改动」。**这一轮等于没审**（因为改动已经提交了，而脚本审的是「工作区 vs HEAD」的差异）。**教训**：审之前别急着提交，或者用 `-ReviewTarget <上一个提交>` 来审已提交的那一段 | — |
| 第 18 轮 | 应用仓 `cd1c69b..e0cdc14`（**补审**第 16 轮那两处修法） | **PASS** | **由「无任何严重级别标记」推断**（无 VERDICT 行；模型原话：*No actionable regressions introduced by this diff were identified. Validation was limited to source inspection and diff checks; HarmonyOS runtime tests were not run.*） | 无 | — |

| 第 19 轮 | 应用仓（发牌动画可以被按下打断） | **CONCERNS** | 由 P2 标记**推断**（无 VERDICT 行） | ① **打断发牌时取消不掉在途的音效请求** —— SoundPlayer.stop() 只清除「还没到点的定时器」并停当前播放器，而**已经进了 prepare() 的 playAsync() 没有取消检查**，仍会走到 player.play()。startNewGame() 传给 playAt() 的时间通常已经到点，所以请求会**立刻**进入这条异步链、根本不在可撤销的定时器里 → 用户打断发牌动画之后配乐才响起来。模型用「延迟完成的 prepare」模拟复现了 | 已修：普通音效也加**取消代次**（playGen）——stop(name) 把代次 +1，playAsync() 取调用时刻的代次并作为取消判据传进 playOn()，playOn() 在真正 play() 之前查一次（与池子那套同源） |
| 第 20 轮 | 应用仓（第 19 轮那一条修完之后） | **PASS** | **由「无任何严重级别标记」推断**（无 VERDICT 行；模型原话：*No actionable regressions were identified in the diff. The frame timer redraws the completed board after interruption, and focused mock-AVPlayer checks passed for cancellation during creation and preparation, replay after cancellation, and stopping active playback. Full HarmonyOS build and device behavior were not verified.*） | 无 | — |
## 第 7 轮：这一轮复审**第一次查的是应用代码**

前六轮的全部发现都在**跑测工具**里，应用仓一行没动。
第 7 轮复审的是应用仓新加的「结算动画可跳过」（提交 `ca5548c`），
两条发现都**在应用代码里**，也都已修（提交 `26ed1ba`）：

| 发现 | 位置 | 为什么是真问题 | 怎么修的 |
|---|---|---|---|
| 跳过时爆炸声还在放 | `GameController.ets` 的 `skipGameOverAnimation()` | `stopBombTail()` 只撤了延时播放的定时器，**已经在放的那一声**还在放完 —— 于是「框已经弹出来了，爆炸声还在耳朵里响」 | 跳过时把爆炸三段（开始/中/结束）都 `SoundPlayer.stop()`。依据：原版是先停循环再放结束音 |
| 长按菜单栏也会跳动画 | `GameController.ets` 的 `longPress()` | 普通点击菜单栏被排除在「跳过」之外（菜单是另一个控件，见 `BoardWidget.cpp:783` 的 `mousePressEvent` 只管棋盘区域），长按菜单栏却会走到 `longPress()` 里跳过 —— 两条路不一致 | `longPress()` 里先 `isOnMenuBar()` 判掉菜单栏，再判跳过 |

修完又复验了一遍（真平板 + 模拟器）：两条都过了。


## 这一轮复审里「模型没输出 VERDICT 行」的情况

第 4、5、6 轮**都没有** `VERDICT:` 行，裁定是从答案里的严重级别标记推断的。
按规矩，**推断来源必须写出来**，不能写成「Codex 说通过了」。

## 前六轮复审查出来的问题，**没有一条在应用代码里**

前六轮的全部发现都在**跑测工具**里（`tools/click_matrix.py`、
`tools/tablet_check.py`、用例 JSON），应用仓 `C:\Users\19161\saolei` 那六轮
**一行代码都没改**（HEAD 仍是 `edb935f`）。

这本身就是个结论：**应用侧是干净的，偶发失败来自测试工具。**

第七轮（见上表）是**第一次查应用代码**：新加的「结算动画可跳过」被指出两个 P2，
都在应用里，也都改了。
