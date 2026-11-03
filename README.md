# Win7 扫雷 -> 鸿蒙（HarmonyOS）：客观验证工具集

本仓是给「Windows 7 扫雷的 HarmonyOS 复刻」做**客观验证**的工具、规格与证据，
**不含应用本体**。应用本体是另一个 HarmonyOS 工程仓（DevEco Studio 工程）。

| 用途 | 位置 |
|---|---|
| 应用本体（要装到手机上的） | 另一个仓，HarmonyOS 工程，bundleName `com.example.saolei` |
| 本仓：验证工具 + 规格 + 证据图 | 本仓 |
| 参考资料（素材 + 三份参考实现） | `C:\Users\19161\Desktop\minesweeper-refs\`（本机，不在本仓内） |

其中 `linux-minesweeper-main/` 是一份 **C++17 / Qt6 Widgets + Multimedia 的 Win7 扫雷复刻**
（上游 <https://github.com/actuallyaridan/linux-minesweeper>），在本项目里**当行为依据**：
原版行为的许多细节是照它核对的，例如「结算动画期间点一下就跳过」出自它的
`src/ui/BoardWidget.cpp:783-793`（`finishExplosionNow(); // a click skips the cascade, like Win7`）。
本仓公开后读者拿不到这个目录，若要引用它，需要单独说明来源与许可。

规格与证据基线：[`docs/SPEC.md`](docs/SPEC.md)。

---

## 1. 本仓有什么

```
minesweeper/
|-- docs/                      规格、逐项核对记录、证据图（2389 个文件）
|   |-- SPEC.md                规格：规则、素材坐标、渲染、交互、折叠屏适配
|   |-- WIN7-FEATURE-GAP.md    与原版的功能差异清单（逐条带出处）
|   |-- LAYOUT-MATRIX.md       版式矩阵：各画布下的缩放档/格边/原点/溢出推演
|   |-- HANDOVER.md            交接文档：现在是什么状态、还差什么
|   |-- DIALOG-PIXEL-DIFF*.md  对话框逐像素比对（第一/二/三批）
|   |-- ANIM-PARITY.md         动画逐帧比对
|   |-- SEVEN-SEG-COUNTER.md   七段数码管的几何与实测
|   |-- FOLDABLE-AUDIT.md      折叠屏/横屏/矮画布的风险清单（只读审计）
|   `-- verify/                跑测器产出的证据图与日志
|-- engine/
|   |-- src/MinesweeperEngine.ts  规则层唯一事实源（纯逻辑，无 UI / 无平台依赖）
|   `-- test/engine.test.ts        规则层离线测试
|-- tools/                     跑测与验证工具（本仓的核心，见第 2 节）
`-- staging/                   中间产物
```

跑测器每轮生成的用例截图按 `.gitignore` 不进仓（可再生，需要时重跑即可）；
`docs/verify/` 里已入库的是精选证据图与日志。

---

## 2. 五个工具

### 2.1 `tools/click_matrix.py` —— 四域点击回归

把「每一个按钮都点一遍」变成可重跑的机器检查。用例表在 `tools/click_cases/<域>.json`，
共 **86 条**：`menu.json` 15 条、`board.json` 15 条、`dialogs.json` 27 条、`custom.json` 29 条。
退出码：全过 0，有失败 1。

覆盖的域：菜单栏与下拉菜单、棋盘触摸路由（点哪格翻哪格、长按插旗）、五个对话框的按钮、
自定义难度框与数字键盘。断言类型：`changed` / `unchanged`（必给 region）、
`layout_changed` / `layout_regex`（读应用打的布局日志）、`hilog_regex`、
`cell_opened`（触摸路由对位）、`region_dark` / `region_light`、`app_alive`。

### 2.2 `tools/check_layout.py` —— 版式离线推演

把 `GameController` 的版式几何公式**原样翻译成 Python**，对若干块画布 x 若干盘面逐个算：
适配档 n、格边、棋盘/状态条/菜单栏矩形、上下左右留白、是否溢出、溢出后能不能拖到头、
状态条是否还在可视区、是不是整数像素。共 **803 条断言**，覆盖手机、平板、折叠屏的多种
分辨率与密度。不需要设备，纯离线。

### 2.3 `tools/sevenseg_read.py` —— 七段反解器

状态条上的计时与剩余雷数不是字体，是**程序画的七段数码管**，没有 OCR 可用，
所以这个工具按与 `SevenSeg.ets` 完全一致的几何，从截图里**反解**出数字
（先只在状态条那一条横带里找绿色面板，再逐段采样中心点是否发白，槽位从右往左读、右对齐不补零）。

### 2.4 `tools/win_probe.py` / `tools/anim_skip_test.py` —— 造局面与动画 A/B

- `win_probe.py`：在真机上把扫雷「赢」一次，或抓爆炸动画的连续帧。
  做法不依赖产品代码改动：截图 -> 按格子之间的深色缝定位棋盘网格 ->
  从 `blueSheet.png` 取数字字形做模板匹配认出 1..8 -> 跑标准扫雷推理（约束传播 + 穷举可行解）
  -> 挑一个必定安全的格子点它，直到胜利。
- `anim_skip_test.py`：验证「结算动画期间点一下，立刻跳过动画直接弹结算框」。
  **A/B 对照**：A 组踩雷后等框自己弹出记耗时 ΔA，B 组踩雷后 0.4 秒补一刀记 ΔB，
  ΔB 明显小于 ΔA 就说明点击跳过生效（9x9 的爆炸级联本来要约 2.5 秒）。

### 2.5 其它（顺带一提）

`tools/build.ps1` 构建应用、`tools/verify.ps1` 一条命令跑全量回归、
`tools/pixel_diff.py` 与参考图做逐像素比对、`tools/tablet_check.py` 平板专用的画布实测核对、
`tools/hud_probe.py` 钉底（HUD）分支的实测、`tools/run_engine_tests.ps1` 一键跑引擎 + 七段 + 求解器测试。

---

## 3. 怎么跑

前置：本机装了 DevEco Studio（`hdc` 在它自带的 SDK 里），
Python 运行时已有 `PIL` 与 `numpy`（**不要** `pip install`）。

```powershell
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'

# 看有哪些设备
& $hdc list targets

# 1) 四域点击回归（86 条）。--cases 可只跑某几个域，--only 按用例 id 过滤
cd D:\software\harmony\projects\minesweeper
python tools\click_matrix.py --device 127.0.0.1:5557 --tag 1201
python tools\click_matrix.py --device 127.0.0.1:5557 --cases menu,board --only menu.game

# 2) 版式离线推演（803 条断言，不需要设备）
python tools\check_layout.py
python tools\check_layout.py --md        # 额外输出 markdown 表格

# 3) 七段反解器：把截图里状态条上的数字读出来
python tools\sevenseg_read.py <截图路径> [状态条矩形 x,y,w,h]

# 4) 在真机上造一个胜局 / 抓爆炸动画连续帧
python tools\win_probe.py --device 127.0.0.1:5555 --phase win
python tools\win_probe.py --device 127.0.0.1:5555 --phase explode --rows 16 --cols 30 --mines 99

# 5) 结算动画「点一下跳过」的 A/B 对照
python tools\anim_skip_test.py --device 127.0.0.1:5555

# 6) 离线单元测试（引擎 59 + 七段 11 + 求解器 14，不碰设备）
powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_engine_tests.ps1

# 7) 与参考图做逐像素比对
python tools\pixel_diff.py --ref <参考图> --shot <截图> --rect X,Y,W,H --auto-scale
```

跑测器**不会**执行 `hdc install -r`：安装会清应用数据，需要装包请自己先装。

---

## 4. 这套工具怎么用

### 4.1 坐标系

用例里的坐标必须落在某个**坐标系**里，写 `space` 指定：

| space | 含义 | 写法 |
|---|---|---|
| `board` | 棋盘格子 | 给 `cell: [行, 列]`，取格子中心 |
| `menu` | 菜单栏的画布 vp | 菜单面板左缘 vp 4、上缘 vp 21、宽 168 vp |
| `canvas_frac` | 画布比例坐标 0..1 | 与画布实际尺寸无关 |
| `outside_stats` | 统计窗**外面**的一个点 | 按统计窗的实际边界自动挑（先左、再右、再上、再下） |
| `dialog` | 对话框的参考像素 | 还要给 `dialog` 名字（win/lose/about/help/appearance/stats） |
| `custom` | 自定义难度框的参考像素 | |
| `keypad` | 数字键盘的参考像素 | |
| `canvas` / `screen` | 画布设备像素 / 屏幕像素 | 尽量别用，见下面的铁律 |

### 4.2 一条铁律

**断言里绝不写死画布像素坐标。**

这不是洁癖，是被罚过的：平板四域回归时 5 条用例挂掉，根因全是「把坐标写死成画布设备像素」，
而画布像素尺寸各设备不同（Mate X7 是 2210x2208，平板是 2800x1690 且顶部还有系统状态栏）。
三次栽在同一个地方：菜单面板区域、点统计窗外面、推演期望值时把「画布 = 全屏」当成前提。

坐标要么走 `board`（按格子）、`menu`（按 vp）、`canvas_frac`（按比例）、`outside_stats`（按窗边界），
**不要再写画布像素**。详见 `docs/HANDOVER.md` 第 12.4 与 12.6 节。

### 4.3 检查点语义

`changed` / `unchanged` 是跟**上一个 expect 的检查点**比，不是跟用例开头比；
每个 expect 执行完把当前截图存成新检查点，`reset` 重置检查点。

---

## 5. 验证结论摘要

只列有据可查的（出处都在本仓文档里）：

| 项 | 结果 | 出处 |
|---|---|---|
| 四域点击回归（86 条） | 三台模拟器各 **86/86**：Mate X7 2210x2208、MatePad 12.2 2800x1690、Mate 90 Pro 1280x2598 | `docs/HANDOVER.md` 12.6；`docs/DEV-CHECKLIST.md` |
| 四域点击回归（真平板 MatePad Pro，竖屏） | **82/86**：4 条失败经定位是**跑测器**在竖屏下的时序/几何问题（用例坐标写死了画布像素、截图与重绘之间的时序），应用本身在竖屏下渲染正确 | 根因分析：`docs/HANDOVER.md` 12.4、12.5（本次成绩由维护者提供） |
| 离线单元测试 | 引擎 **59** + 七段渲染器 **11** + 跑测器求解器 **14** = 84 条全绿 | `docs/HANDOVER.md` 第 0 节、12 节；`tools/run_engine_tests.ps1` |
| 版式离线推演 | **803 条断言**全过 | `docs/HANDOVER.md` 第 0 节；`tools/check_layout.py` |
| 真机版式核对 | Pura X Max 内屏（画布 2584x1644 @2.75）的适配档 4、格边 144 px、棋盘原点 (644, 75)、状态条上沿 1371 px，与离线推演逐项吻合 | `docs/HANDOVER.md` 12.7 |
| 真平板版式核对 | MatePad Pro 横屏画布 2800x1690，三个盘面与推演逐项吻合；竖屏（模拟器实例）画布 1840x2650，四个盘面吻合 | `docs/LAYOUT-MATRIX.md` 9.6.1、9.6.2 |

**没验过的**：Pura X Max 真机上的四域整套回归没跑完（跑测时设备被断开）；
声音效果、捏合手感、折叠折合过程、外屏观感这四项只能人做。
详见 `docs/REAL-DEVICE-CHECKLIST.md` 与 `docs/HANDOVER.md` 第 0 节。

---

## 6. 逻辑层与 UI 层的分界

`engine/src/MinesweeperEngine.ts` 是规则层的唯一事实源，只管规则：

- 延迟布雷 + 首点 3x3 无雷（越界裁剪）
- BFS 洪泛展开（尊重旗子，问号格清空）
- 右键三态标记、剩余雷数可为负
- 和弦（旗数吻合才动手，旗插错同时引爆判负）
- 胜负判定与失败展示、胜利自动插旗
- 方块显示状态码沿用原版字节语义

渲染、动画、手势、折叠屏布局全在 UI 层（应用仓的 `entry/src/main/ets/`）。

逻辑层用 `.ts` 维护是为了能离线跑测试，ArkTS 只认 `.ets`，改完同步一次：

```powershell
powershell -File tools\sync-engine.ps1 -ProjectRoot <应用仓目录>
```

---

## 7. 素材

原版 Windows 7 扫雷的图集与音效提取件**在应用仓**的
`entry/src/main/resources/rawfile/` 下（应用仓 README 里有完整的来源与版权声明）。
本仓只放精灵坐标的推导与核对记录，不重复放素材。

精灵坐标以 `linux-minesweeper/src/ui/Theme.h` 为参考事实源，
逐项核对记录见 `docs/SPRITE-COVERAGE.md` 与 `docs/ASSET-AUDIT.md`。

---

## 8. 许可

本仓**目前没有 LICENSE 文件**，这不是遗漏，是有意留白。

原因：整个项目要公开的两个仓里，有一份装着**微软 Win7 扫雷的版权素材**（在应用仓的
`entry/src/main/resources/rawfile/` 下）。这些文件不是本项目的代码，不能被一份代码许可证
顺带覆盖，所以**加 LICENSE 的前提是先把素材排除在许可证之外**。补之前要先定两件事：

1. **代码（本仓的 `tools/`、`engine/`、文档）用什么许可** —— 由仓库维护者选定；
2. **素材（应用仓的 `entry/src/main/resources/rawfile/`）怎么声明** —— 单独一段说明
   （来源、权利人、非商业分发、移除请求），不并入代码许可证。

这两件事定下来之前，两个仓都不加 LICENSE 文件，本 README 也不替维护者预选任何一种许可。
