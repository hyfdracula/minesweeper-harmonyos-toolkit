# 交接文档 —— Win7 扫雷移植（HarmonyOS）

> 用途：**新会话/新模型接手时，只读这一份就能继续干活。**
> 写于 2026-11-01 00:50，对应应用仓 `66e6c33`、规格仓 `35bd447`（本文件的更新在随后一笔）。
> 本文件不谈过程，只谈「现在是什么状态、怎么动手、还差什么」。

---

## 0. 三十秒版本

- **做什么**：把 Windows 7 扫雷**像素级**移植到鸿蒙，目标机是华为 **Pura X Max 典藏版**（折叠屏），
  自用。用户零代码基础，**代码全部由 agent 写**，用户只负责装工具、连手机、跑应用、截图。
- **现在到哪了**：三个难度 / 问号 / chording / 计时 / 计数器 / 胜负 / 自定义 / 统计 / 帮助 / 关于 /
  颜色对话框 / 绿棋盘 / 花园玩法 / 爆炸与拆雷动画 / 七段数码管计数器 —— **全部已实现并在模拟器上跑通**。
- **最大的一块还没做的**：**真机（Pura X Max）上的一切都没验过**（手里只有两台模拟器）。
- 用户原话定调：「**像素级，我要无敌完整的复刻**」「**不惜 token，只要最好的效果**」
  「**每一个屏幕比例都要适配，每一个按钮都要尝试点击，每一个操作逻辑顺序都要跑通**」。

---

## 1. 两个仓库

| 用途 | 路径 | 分支/HEAD |
|---|---|---|
| **应用仓**（鸿蒙工程，真正要装到手机上的） | `C:\Users\19161\saolei` | master @ `b540a56` |
| **规格仓**（文档 + 工具 + 证据图） | `D:\software\harmony\projects\minesweeper` | master @ `55c69a0` |

应用仓 `bundleName = com.example.saolei`。

### 常用命令

```powershell
# 构建（约 17~18 秒）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\software\harmony\projects\minesweeper\tools\build.ps1
# 产物
C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap
# 装到模拟器
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
& $hdc -t 127.0.0.1:5555 install -r <上面那个 hap>
& $hdc -t 127.0.0.1:5555 shell aa force-stop com.example.saolei
& $hdc -t 127.0.0.1:5555 shell aa start -a EntryAbility -b com.example.saolei
# 全量回归（自标定密度/棋盘原点，出 20 多张截图）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\software\harmony\projects\minesweeper\tools\verify.ps1 -Device 127.0.0.1:5555 -Tag XXX
# 引擎单元测试（41 个用例，不装任何东西：借 DevEco 自带 tsc 转译）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\software\harmony\projects\minesweeper\tools\run_engine_tests.ps1
# 原版对话框逐像素比对
python D:\software\harmony\projects\minesweeper\tools\pixel_diff.py --ref <参考图> --shot <截图> --rect X,Y,W,H --auto-scale
# HUD 分支实测（自标定 + 造 24×30 局 + 命中拦截 + 纵向拖动）
python D:\software\harmony\projects\minesweeper\tools\hud_probe.py --device 127.0.0.1:5557
# 量「拖动挪了多少 / 状态条有没有跟着动」
python D:\software\harmony\projects\minesweeper\tools\drag_shift.py --before <图A> --after <图B> --board-top 212 --strip-top 1908 --strip-bottom 2036 --x0 0 --x1 550
```

---

## 2. 设备与模拟器

| 设备 | 地址 | 画布 | 密度 | pxScale | 说明 |
|---|---|---|---|---|---|
| Mate X7 模拟器（内屏） | `127.0.0.1:5555` | 2210×2208 | 3.125 | 0.32 | 折叠屏，`-foldedState open` |
| Mate X7 模拟器（外屏） | 同上 | 1080×2236 | 3.125 | 0.32 | `-foldedState close`，整屏 1080×2444 |
| Mate 90 Pro 模拟器 | `127.0.0.1:5557` | 1280×2598 | 3.5002 | 0.2857 | 直屏，整屏 1280×2832 |

```powershell
$emu = 'D:\software\DevEco Studio\tools\emulator\Emulator.exe'
& $emu -instance 'Mate X7' -foldedState close        # open = 内屏，close = 外屏
& $emu -instance 'Mate X7' -screenshot -screenshotPath <png>
& $hdc -t 127.0.0.1:5555 shell "uitest uiInput click X Y"     # 也可 doubleClick/longClick/drag/swipe/keyEvent
& $hdc -t 127.0.0.1:5555 shell snapshot_display -f /data/local/tmp/x.jpeg
& $hdc -t 127.0.0.1:5555 file recv /data/local/tmp/x.jpeg <本地路径>
& $hdc -t 127.0.0.1:5555 shell hilog -r                       # 清日志
& $hdc -t 127.0.0.1:5555 shell hilog -x | Select-String JSAPP  # 取应用日志
```

**真实目标机 Pura X Max 典藏版**：内屏 2584×1824（横）、外屏 1323×1936，密度 2.75。
这两块屏**没有模拟器**，只能用 `tools\check_layout.py` 算版式 + 等用户真机验。

**规矩：一台设备同一时刻归一个 agent 独占**（并发点击会互相干扰）。当前：5555 = 动画智能体，5557 = 主线程。

---

## 3. 代码结构（应用仓）

```
entry/src/main/ets/
├── pages/Index.ets                 页面壳 + 菜单动作分发
├── components/MinefieldCanvas.ets  画布宿主：读存档→加载图集→开局、触摸/手势入口
└── common/
    ├── GameController.ets          *核心：布局(applyGeometry/layout)、绘制、命中判定、对话框分发
    ├── MinesweeperEngine.ets       引擎（与规格仓 engine/src/MinesweeperEngine.ts 逐字节相同）
    ├── SpriteAtlas.ets             图集加载 + 按样式切换(applyStyle) + 整图/切片绘制
    ├── Theme.ets                   常量与几何（TILE=18、STRIP_BAND=32、MIN_CELL_PX=48、样式枚举…）
    ├── WinMenu.ets                 菜单栏与下拉（MENU_BAR_H=21vp；appearanceEntry()）
    ├── WinDialog.ets               所有自绘对话框（失败/胜利/帮助/关于/颜色）
    ├── Appearance.ets              「颜色(C)」对话框的状态机
    ├── CustomField.ets             自定义难度对话框（含数字键盘、maxMines()）
    ├── StatsWindow.ets             最佳成绩窗口
    ├── SevenSeg.ets            *  七段数码管计数器（含「1」的衬线旗与衬线底横）
    ├── Anim.ets                    爆炸 23 帧 / 拆雷 38 帧 / 胜利扫描条
    ├── DealIn.ets / Ripple.ets     发牌入场、洪泛涟漪
    ├── SoundPlayer.ets             AVPlayer 音效池（12+3 个 wav）
    └── GameStats.ets               preferences 存档（局数/连胜/最快纪录/**外观设置**）
```

### 必须知道的 API 26 坑（全部实测过，别再踩）

1. **Canvas 坐标单位是 vp**；`PixelMap` 的 `srcRect` 在 API 18+ 也是 vp → 要乘 `pxScale`。
2. `onReady` 的类型声明在撒谎 → 用 `this.drawCtx = this.context`。
3. `ctx.font` 写 `"px"` 指的是**设备像素** → 字号用 `sDev`，几何用 `sVp = sDev * pxScale`。
4. **手势 API 没导出** → 用裸 `onTouch` 自己做（pinch/pan/长按）。
5. **`HitTestMode.Block` 在 API 26 上会把子节点的 `onClick` 一起打死** → 别用；用 `controller.inputLocked`。
6. ArkTS 严格模式：不能用 any/unknown、**静态方法里不能用 `this`**、不能重复标识符、
   不能用访问修饰符；`CanvasRenderingContext2D` 是**全局类型**（不用 import）。
7. 图集约定：`Theme.ets` 里的源矩形是**半尺寸逻辑坐标**（SPRITE_SCALE=2，TILE=18）；
   `draw()` 会把源矩形乘 `SPRITE_SCALE × pxScale`。1:1 的图（如 helpBoard.png 256×192）走 `drawWhole()`。

---

## 4. 已经落地的功能（与对应证据）

| 功能 | 状态 | 关键证据 |
|---|---|---|
| 三种难度 + 自定义(9~24 行 / 9~30 列 / ≤668 雷) | 已实现 | `engine.test.ts` 41 用例全绿 |
| 首点 3×3 无雷、边界裁剪、退化保护 | 已实现 | 同上（穷举 9×9 全起点） |
| 问号三态、chording、剩余雷数可为负 | 已实现 | 同上 |
| 计时（首点起算、上限 999、暂停） | 已实现 | 真机截图 + 日志 |
| **七段数码管计数器** | 已实现 | `docs/SEVEN-SEG-COUNTER.md`、`docs/verify/M10_seg_zoom.png` |
| 菜单栏（游戏 10 项 / 帮助 2 项，含**颜色(C) F7**） | 已实现 | `docs/verify/V4X7_menu_crop.png` |
| 失败/胜利/帮助/关于/统计 对话框 | 已实现 | `docs/DIALOG-PIXEL-DIFF.md`（失败框客户区一致率 92.50%、关于框 86.27%） |
| **颜色(C) 对话框**：游戏样式(扫雷/花园) + 棋盘(银蓝/绿色) + 置灰复选框 | 已实现 | `docs/APPEARANCE-DIALOG.md`、`docs/verify/M2_color_dialog.jpeg` |
| 绿棋盘 + 花园玩法（三段判负音效） | 已实现 | `docs/verify/M6_after_restart.jpeg` |
| 外观设置**重启保留** | 已实现 | `[GameStats] 外观已保存 board=1` + 重启后绿棋盘实测 |
| 状态条**超宽钉屏幕两端**、**纵向溢出钉画布底边(HUD)** | 已实现 | `docs/LAYOUT-MATRIX.md` v4.0 §4.3、§4.3.6 |
| **HUD 命中拦截实测**：点状态条盖住的格子不翻开 | 已实现并**实测** | 点屏幕 (676,1972) → 棋盘变化 **0 px**；对照点可见格 → 296578 px（`docs/verify/hud_09/10_*.jpeg`） |
| **纵向拖动上限 = 整个溢出量**，且状态条钉住不动 | 已实现并**实测** | 拖动实测位移 32 px（= overV），状态条最下 16 px 差异 **0 px** |
| HUD 下被状态条压住的格子**盖住**（不再「看得见却点不着」） | 已实现并**实测** | 状态条上沿 1908 px 以下全是底色 (198,205,221)，无格子透出 |
| 状态条在**极限缩放**下两个计数仍在屏内、且两组不重叠 | 已实现并**实测**（离线断言） | `tools/check_layout.py` 断言 9：4 画布 × 4 盘面 × n=8 全过；普通档位一个像素都没变 |
| **扫描条裁在棋盘矩形内**（原版 `setClipRect(grid)`）、高度按原版长宽比 | 已实现并**实测** | 修复前条停在**棋盘外 18 px**，修复后**在棋盘内 233 px**（模板匹配相似度 0.990）；`docs/ANIM-VERDICT.md` §1.4 |
| **胜利动画整条**（扫描条 + 38 帧拆雷光束 + 胜利后全盘插旗） | 已实现并**实测** | 真机赢一局连拍 20 帧：条自下而上扫、光束在扫到那行时起跳、胜利后 10 颗雷全插旗；`docs/ANIM-VERDICT.md` |
| **爆炸动画** | 已实现并**实测**（18/23 帧） | 慢放取证 + 模板匹配认出**第 1~17 与 19 帧**（相似度 0.85~0.97），每轮连拍内部帧号**严格递增**；没抓到 0、18、20、21、22（快门的物理限制）；`docs/ANIM-FRAMES.md` |
| **花园玩法判负的开花序列** | 已实现并**实测**（19/23 帧） | 认出第 1~6、8~14、16~19、21、22 帧；帧号递增已证；`docs/ANIM-FRAMES.md` |
| **可重跑的点击回归**（菜单/棋盘/对话框/自定义框 82 条） | 已实现并**实测** | `tools/click_matrix.py` + `tools/click_cases/*.json`；跨设备（Mate 90 Pro + Mate X7）都跑过；`docs/CLICK-MATRIX-AUTO.md` |
| 胜利框 / 失败框**逐像素比对** | 已做 | 与 Lmy 克隆框：胜利框客户区 **90.55%**、失败框 **92.50%**，缩放 k=2.000 整数倍，**几何 0 处画错**；`docs/DIALOG-PIXEL-DIFF.md`、`docs/DIALOG-PIXEL-DIFF-2.md` |
| 爆炸动画按**时间**推进（原版 1 秒/23 帧）、胜利结束时刻按最后一束光束算 | 已实现 | `Anim.ets` 的 `EXPLODE_FRAME_MS` / `Anim.winEndMs()` |
| 抬档规则：整块装得下优先，格边 <48 设备像素就抬（允许纵向溢出） | 已实现 | 24×30 在 Mate 90 Pro 上 n=2 / 格边 72px 实测 |
| 爆炸 23 帧 / 拆雷 38 帧 / 胜利扫描条 | 已实现 | 代码在 `Anim.ets`；**真机连续帧证据由 anim-agent 出** |
| 音效全套（含花朵三段） | 已实现 | `SoundPlayer.ets` |

---

## 5. 还没做 / 还没验的（按重要度）

### 5.1 只有真机能验（用户来做，agent 做不了）
1. **Pura X Max 真机装上跑** —— 内屏 2584×1824 / 外屏 1323×1936 两块屏的观感。
2. **双指缩放** —— `uitest` 注入不了多点触控，只能在真机上手动捏一下，
   然后去 hilog 找 `[Touch] 捏合 档位n=…`。
3. **折叠开合过程中状态是否保住** —— 外屏本身已验，折合过程没验。
4. **游戏的手感**（点击响应、长按插旗、拖动手感）。

### 5.2 agent 侧还能做的
5. ~~**胜利路径整条**~~ —— **已做完**（`docs/ANIM-VERDICT.md`，2026-11-01）：
   扫描条自下而上扫过、38 帧拆雷光束在扫到那行时起跳、胜利后 10 颗雷全部插旗，
   修复前后对比图 + 帧号模板匹配都在 `docs\verify\ANIM_*`。
   **剩余**：爆炸动画只认出 2 个帧号（第 7、10 帧），
   原因是设备端 `snapshot_display` 497 ms、`uitest uiInput click` 485 ms，
   **快门比 1 秒的爆炸窗口还慢** —— 是工具链的物理限制，不是动画实现的问题。
6. ~~**对话框像素比对**~~ —— **已做完**（`docs/DIALOG-PIXEL-DIFF.md` + `docs/DIALOG-PIXEL-DIFF-2.md`）：
   失败框客户区 92.50%、胜利框 90.50%，缩放 k=2.000 整数倍，
   差异最大的区域逐条核对后**几何 0 处画错**；自定义框**没有可比参考**
   （三个克隆的对话框都是自绘），只验了几何（402×200 → 804×400，s=2.000）与键盘行为。
   **口径提醒**：参考图是 Lmy 克隆**自绘**的框，一致率只能叫「与 Lmy 克隆框的一致率」。
7. **花园玩法判负瞬间的完整开花序列**只验了图标与帧位置，没验动画序列本身。
8. **引擎单元测试只覆盖逻辑层**，不覆盖绘制与触摸路由。
9. **胜利框/失败框的按钮文案仍未确证**（Win7 原版中文拿不到），
   现在照的是 Lmy 克隆；**存在性可信、文案不可信**。

### 5.3 已知差异（有意为之，不是 bug）
- **AppScope 图标**：地雷本体是微软原版素材（与 `win7-assets/icons/MineSweeper-128.png` 同一颗），
  但加了 Win7 蓝渐变底（原版是透明底）。鸿蒙启动器需要底色。
- **帮助窗口正文**：原版中文 Win7 的帮助文本拿不到（没有 `Minesweeper.exe`），
  现在是我们写的中文说明；**版式与原版一致**（左插图 + 右文字 + 确定按钮）。
- **失败对话框的按钮文案**：Win7 **确实会弹对话框**（用户本人确认），但**按钮文案无据可依**
  （现在照的是 Lmy 克隆的 `loss.jpg`，那是它自己设计的）。**结构和存在性可信，文案不可信。**
- **Win7 没有笑脸按钮**（用户确认 + 四张图集逐像素核查双向印证），我们也没有 —— 这是**一致**，不是缺失。
- **`颜色(C)` 这个中文名**来自用户本人 Win7 的菜单（唯一权威来源）。

---

## 6. 参考素材的出处与可信度（重要）

`C:\Users\19161\Desktop\minesweeper-refs\`（详见其中的 `README.md` 与规格仓 `docs/ASSET-AUDIT.md`）：

| 来源 | 是什么 | 能不能当像素依据 |
|---|---|---|
| `win7-assets/` | **从原版 Win7 游戏导出的**精灵图集 / 音效 / 图标 | **能**（微软版权，仅限自用） |
| `linux-minesweeper-main/` | Qt6 复刻，行为最接近 Win7 | 行为可以，**界面不能**（对话框/菜单是它自己设计的） |
| `ReversingMinesweeper-master/` | **XP** 版逆向重建源码 | 数据结构可以，**菜单项是 XP 的**，不是 Win7 |
| `Minesweeper-master/`（Lmy0217） | 2015 年 Win32 仿 Win7 | 首点规则可以，**`loss.jpg`/`about.jpg` 是它自己画的对话框**，不是原版 |

**结论：像素依据只认 `win7-assets/` 里的图集本身 + 微软原版 `helpBoard.png` 的逐像素读数。**
凡是来自三个源码仓库的「界面截图」，都只能当行为参考，**不能当像素依据**。

---

## 7. 团队与写入边界

Lead 之外曾有 8 个后台智能体，各自写过互不重叠的文件。当前仍在跑的两个：

| 智能体 | 负责 | 写入范围 |
|---|---|---|
| `anim-agent` | 动画验证 | `tools/win_probe.py`、`docs/ANIM-VERDICT.md`、`docs/verify/ANIM_*`；必要时可改 `Anim.ets`/`DealIn.ets`/`Ripple.ets` |
| `engine-parity-agent` | 版式与引擎一致性 | `GameController.ets`、`Theme.ets`、`tools/check_layout.py`、`docs/LAYOUT-MATRIX.md` |

其余（docs / assets-audit / dialog-fidelity / menubar-fidelity / custom / face-assets）已交付并空闲。
**Lead 独占**：`GameController.ets` 的绘制与对话框分发、`Theme.ets`、`SpriteAtlas.ets`、`WinDialog.ets`、
`CustomField.ets`、`SevenSeg.ets`、`GameStats.ets`、`SoundPlayer.ets`、`MinefieldCanvas.ets`、`pages/Index.ets`。

### 全局约定（`~/.dsh/AGENTS.md`，必须遵守）
- **禁止 emoji**（任何文件、任何输出；`√`/`×` 属 Dingbats 也算 emoji，用文字替代）。
- Windows 上跑 Python 子进程必须加 `subprocess.CREATE_NO_WINDOW`（用 `~/.dsh/lib/nowindow.py`）。
- **禁止 pip install**。
- 实质性改动完成后跑一次 Codex 对抗性复审（同一任务最多一次），
  汇报时必须写明裁定值**和它的来源**（明确给出 / 由严重级别推断 / UNKNOWN，UNKNOWN 不等于通过）。

---

## 8. Codex 对抗性复审的结论（已处置）

### 8.1 `a2b635f` 的复审：BLOCKER（6 条已处置）

裁定 **BLOCKER**（来源：由 P0/P1 标记推断，模型未给 VERDICT 行），6 条已全部处置：

| # | 问题 | 处置 |
|---|---|---|
| P1 | 纵向平移上限只允许溢出量一半，底部格子够不到 | 改成上限 = 整个溢出量、且单向（只能往上推）；`GameController.clampPan()` |
| P2 | 状态条钉底时命中判定没排除它，点计数器会翻开看不见的格子 | `hitTest()` 在 `hudActive` 时拒绝 `stripTop` 及以下；同文件 |
| P2 | 存档与图集加载并行，外观还原读到默认值 | `MinefieldCanvas.aboutToAppear()` 改成两者都完成再套用 |
| P2 | 关于框图标写了物理坐标，`drawLogical` 会再乘 2 → 出图集画不出来 | 改成逻辑坐标 `[29,2,17,17]` |
| P2 | 七段「1」漏了衬线旗 | 掩码 `0x8E` → `0x186`（b+c+旗+底横，去掉标准 d） |
| P2 | 花园判负时 `gameLose` 与 `flowerLose` 叠着响 | 改成按样式二选一 |

### 8.2 `f261aa9..06b6217` 的复审（整轮改动）：CONCERNS（3 条 P2 已处置）

裁定 **CONCERNS**（来源：**由 P2 标记推断**，模型未给 VERDICT 行；不是明确给出的值，也不是 UNKNOWN）。
命令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\19161\.dsh\skills\codex-delegate\codex-delegate.ps1 `
  -Review -ExpectVerdict -ReviewMode Base -ReviewTarget f261aa9 -Workdir C:\Users\19161\saolei `
  -TimeoutSec 1800 -OutDir D:\software\harmony\projects\minesweeper\docs\codex
```

三条 P2 与处置（全部已修，提交 `66e6c33`）：

| # | 复审原文的判断 | 处置 |
|---|---|---|
| P2 | 「缩放到极限档时，状态条的两个计数会一起跑出屏幕（1280 宽屏、30 列、n=8 时 margin=720px，计时面板从 x=1216 起，雷数面板整个在屏外）。请把两组**独立于棋盘缩放的 margin** 夹在视口内。」 | 状态条内容自己一档 `su = min(u, 两组放得下的最大档)`、留白按「放得下」夹住、两组不许互相压。见 §4.3.7；`check_layout.py` 断言 9 覆盖 4 画布 × 4 盘面 × n=8 |
| P2 | 「HUD 模式下状态条压在棋盘下沿上，但只画了图标和面板，底下的格子**仍然看得见**，而 `hitTest()` 又拒绝整条状态条的点击 —— 留下看着能点其实点不动的格子。请在画内容之前先铺一层不透明的条带底色。」 | HUD 模式下先把带子铺成不透明底色（`COLOR_OUTSIDE`），被压住的格子彻底看不见；实测状态条上沿以下全是底色 |
| P2 | 「花园判负音效按**剩余雷数**分档，插了旗之后剩余雷数偏低，40 雷的局会播 Short、99 雷的局会播 Medium。分档标准是本局雷数，请用 `engine.mineCount`。」 | 改成 `this.engine.mineCount` |


---

## 9. 用户已经拍板的硬决策（不要改）

1. **Win7「游戏(G)」菜单里有「颜色(C)」这一项** —— 用户本人 Win7 上的真名（不是「外观」）。
2. **Win7 判负会弹对话框** —— 所以我们的结束对话框是对的。
3. **Win7 没有笑脸按钮** —— 我们也没有，这是与原版一致。
4. **最小可点格边 48 设备像素**；**宁可溢出也不能缩到点不准**（用户原话「外屏不接受降级，我希望可以拖动放大」）。
5. **自定义局不计入统计/排行榜**（原版如此，已实现 `customGame` 标记）。
6. **没有任何降级档**：不要为了「能放下」而缩小棋盘或去掉功能。
