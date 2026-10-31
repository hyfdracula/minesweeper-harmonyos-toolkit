# 开发检查表 · HarmonyOS Win7 扫雷移植

- 规格与引擎仓库：`D:\software\harmony\projects\minesweeper`
- 应用工程：`C:\Users\19161\saolei`（命令行构建已验证通过，`tools\build.ps1`，约 8 秒）
- 验证设备：
  - **Pura X Max 真机**，内屏 2584×1828，序列号 `6HR0226409003317`
  - **Mate X7 模拟器** `127.0.0.1:5555`（2210×2416 @ density 3.125）
  - **Mate 90 Pro 模拟器** `127.0.0.1:5557`（1280×2832 @ density 3.5）

最后更新：2026-10-31 13:55（收口：把当天 13:05 之后的改动并进来）

> 验证怎么做见 `docs\VERIFY-GUIDE.md`；当天改了什么见 `docs\CHANGELOG-2026-10-31.md`。

---

## 1. 状态总览

| 状态 | 条数 | 明细 |
|---|---|---|
| 已验证通过 | 44 | §2 |
| 代码已就位，待验证 | 11 | §3 |
| 已知缺陷 / 待办 | 11 | §4 |

本表只记录**真的跑出过结果**的东西。凡是没跑出结果的，一律进 §3 或 §4，不进 §2。

**四个 build 的区别（重要）**：

- **旧 build**（13:41 之前）：`CLICK-MATRIX-90P.md` 的 33 元素矩阵、`CLICK-MATRIX-X7.md` 的菜单栏 12 项。
- **13:41 build**：90P 复测 5 项、X7 补测 21 项。
- **14:02 build**（`9a70112` → `c130326`）：X7 收尾补测第 35~48 项**全部通过**。
- **19:00 build**（`a2b635f`）：七段数码管 / 颜色对话框 / 绿棋盘 / 花园 / 状态条超宽修复 /
  对话框像素级修正。

§2 里标「旧 build」的那批结论**坐标全部作废**（版式重做改了棋盘原点与对话框尺寸），
但**功能结论大多仍然成立**。标最新 build 的是当前状态。

**今天 13:05 之后应用仓的 6 个提交**：`8925f0e`（音效/触摸路由/统计窗/重开/雷数上限）、
`9e7befe`（版式重做/对话框缩放/菜单残留/换难度按钮）、`9a70112`（L1/L4 修复 + 帮助窗口像素化）、
`c130326`（帮助插图换算方向写反）、`f261aa9`（自定义对话框还原度 P4/P6 + 雷数夹取回显）、
`a2b635f`（七段数码管 / 颜色对话框与绿棋盘花园 / 对话框像素级修正）。
逐条见 `docs\CHANGELOG-2026-10-31.md`。

---

## 2. 已验证通过

### 2.1 真机（Pura X Max，2026-10-30 ~ 10-31 上午）

- [x] **三难度渲染与切换**：9×9 / 16×16 / 16×30，棋盘尺寸与雷数随难度变
- [x] **单击开格**
- [x] **洪泛展开**（连锁开空地）
- [x] **胜利 / 失败判定**
- [x] **菜单栏打开与难度切换**（画布自绘的 Win7 菜单栏，替换了最初的「≡」浮层）
- [x] **结束对话框绘制**（Win7 风格：Aero 玻璃标题栏 + 画布自绘按钮）
- [x] **长按插旗**
- [x] **计时器**（第一次左键松开起走，终局停住）
- [x] **切后台暂停**（`EntryAbility.onBackground` → `pauseForBackground()`）

### 2.2 模拟器（2026-10-31 下午，逐个元素点击）

Mate 90 Pro（`127.0.0.1:5557`）**实测点击 33 个元素，30 通过 / 3 异常**。
Mate X7（`127.0.0.1:5555`）**菜单栏 12 项全通过**。

- [x] **菜单栏两个顶层项**：「游戏(G)」「帮助(H)」都能展开下拉
- [x] **游戏下拉 9 项**：新建(F2) / 初级 / 中级 / 高级 / 自定义 / 标记(?) / 声音 / 最佳成绩 / 退出(X)
- [x] **帮助下拉 2 项**：帮助(H) F1 / 关于扫雷 A（**是 2 项不是 3 项**，第 3 个是分隔线，不可点）
- [x] **难度切换**（初级/中级/高级）：盘面、行列数、雷数都对
- [x] **「新建」沿用当前难度**：在中级下点新建，出来的是 16×16，不是回初级
- [x] **「标记(?)」开关**：关掉后菜单勾号消失、盘面不变；再开勾号恢复
- [x] **「声音」开关**：同上
- [x] **「最佳成绩」** → 弹出完整的「扫雷统计信息」窗口
- [x] **「退出(X)」** → 应用真的退出（`aa dump -a` 查不到 Mission ID #28）
- [x] **帮助对话框**：打开、内容正确、确定能关
- [x] **关于扫雷对话框**：与帮助对话框**不是同一个**（像素差异 23633/71400）
- [x] **结束框三个按钮**：「再玩一局(P)」「退出(X)」都work；标题栏红叉能关框且应用仍在
- [x] **统计窗口「重置(R)」**：日志 `Stats 点击重置`，已玩游戏 2→0、获胜率 0%、**最多连败 2→0**
- [x] **统计窗口「关闭(C)」**：日志 `Stats 点击关闭`，窗口消失
- [x] **数字键盘**：点 1 → 高度框变「1」；点 2 → 变「12」（输入框上限 2 位）
- [x] **菜单栏像素级复核**：渐变带、墨迹位置、下拉各项文字中心与「参考图实测 → vp」模型偏差 **≤2.5 px**
      （`CLICK-MATRIX-X7.md` 附 A3）

### 2.3 最终 build（`9a70112` → `c130326`，14:02）复测通过

- [x] **统计窗口 4 个控件全部可用**：左栏难度列表 / 标题栏红叉 / 关闭(C) / 重置(R)；
      日志 `[Stats] 选中难度 1`、`[Stats] 点击关闭`
- [x] **自定义框 11 个数字键 + 超限拒绝 + 退格 + 确定 + 取消 + 标题栏 X**：
      逐键记录高度框的值 1→`1`、2→`12`、3→`12`（**拒绝**，>24 上限）、4~9→`12`（均拒绝）、
      退格→`1`、0→`10`；「确定(O)」后棋盘按自定义参数重排（首道网格线 y=288→200）；
      标题栏 X 关闭正常
- [x] **帮助菜单展开**：两项 —— 帮助(H)（文字带 y 215..256）、关于扫雷（y 311..351）
- [x] **结束框「再玩一局(P)」**：对话框关闭，回到全新棋盘（格子全未翻开、计时 0、雷数 10）
- [x] **帮助对话框的 Win7 原版插图正常显示**：`docs\verify\HELP_p90.jpeg`
      （1280×2832，Mate 90 Pro，14:03:21）—— 左侧是原版蓝砖棋盘插图，底部还带着原版状态条
      （时钟 / `18` / `40` / 雷图标），右侧 6 行中文说明，底部「确定」。
      lead 的逐像素比对：与源图 ×2 最近邻的**逐像素差中位数 (0, 0, 0)**；
      位置 (88, 1230) vs 预测 (88, 1232)，差 2 px 在取整范围内（`docs\LEAD-VERIFY-2026-10-31.md` §1）
- [x] **菜单 9 项、帮助菜单 2 项**

### 2.4 13:41 build（版式重做后）复测通过

- [x] **菜单选完即消失**：选「标记(?)」「声音」后菜单白底行数 **858 → 0**，画布只剩棋盘
      （90P R1-1/R1-2，截图 `P90_R61a_menu.jpeg` / `P90_R61_flag_after.jpeg` / `P90_R62_sound_after.jpeg`）
- [x] **「换个难度(D)」真的弹出游戏菜单**：日志 `Dialog 点击按钮 menu`，点完后「游戏」下拉白底 **858 行**
      （90P R1-3，截图 `P90_R74_lose.jpeg` / `P90_R77_after_middle_btn.jpeg`）
- [x] **自定义框尺寸修复**：框本体 **297 px → 632 px**（x172..804），键盘 127 → 215 px，
      整组 935 px 落在 1280 屏内（左右各留 172/173 px），正文 **2.7 vp → 21~23 设备像素**
      （90P R1-5 / R3.3）
- [x] **统计窗口尺寸修复**：X7 内屏上从约 260×190 px 变成约 **1350×410 px**，正文 2.7 vp → 约 7 vp
      （X7 B5）
- [x] **棋盘居中与留白**：三档的上下留白差都在 **13~26 px** 内、水平差在 **3 px** 内
      （90P R3.2）
- [x] **切难度后的浅蓝灰「已翻开」格消失**：同时刻像素数 8848/15972/28440 → **36/0/44**（-99.8%），
      确认那是发牌动画不是 bug（90P R4）
- [x] **「最佳成绩」打开统计窗口**（X7 补测第 13 项）

### 2.5 引擎单元测试（41 个用例全绿，**现在可复现**）

- [x] **引擎单元测试可复现地跑通，41 个用例全绿**
      用法：`powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_engine_tests.ps1`
      （借 DevEco Studio 自带的 tsc 转译到临时目录再跑，**不装任何东西**）
      覆盖：首点 3×3 无雷（**含边界裁剪，首点 (0,8)**）、三个难度 × 全部起点 × 3 组种子、问号三态、
      剩余雷数可为负、首点必开空地等。
      **引擎层与真机同源**：应用仓的引擎文件与规格仓**逐行完全相同**（SHA-256 一致，`13B9BD39…BEA`），
      所以引擎层的结论**直接适用于真机**。

      > 之前那条「跑引擎测试」是**没法执行**的（引擎是 TypeScript 且用了 `enum`，
      > `node --experimental-strip-types` 不支持；规格仓也没有 node_modules，
      > 而全局约定禁止随手 install）—— **现在有脚本了，这条不再是死条目**

### 2.6 19:00 build（commit `a2b635f`）复测通过

- [x] **「颜色(C)」菜单项能打开外观对话框**：位置在「最佳成绩」之后、「退出」之前（倒数第二项，F7）；
      日志 `[Menu] 菜单动作 appearance`；对话框有两个分组框 + 四枚缩略图 + 选中蓝框
      + 置灰的「随机选择游戏样式和棋盘」复选框 + 确定/取消
      （`docs\APPEARANCE-DIALOG.md` §7 步骤 1~2，截图 `X7_91_final_dialog.jpeg`）
- [x] **点「绿色」缩略图 → 选中框移动 + 说明蓝底白字**（同上 步骤 3，`X7_92_final_green_selected.jpeg`）
- [x] **点「确定」→ 棋盘变绿**：绿色像素 **43 589 → 2 304 302**（同上 步骤 4，`X7_93_final_green_board.jpeg`）
- [x] **点「取消」→ 不生效**：棋盘绿色像素前后都是 2 304 302（同上 步骤 5）
- [x] **花园玩法**：剩余雷数旁的图标变成白雏菊（同上 步骤 6，`X7_90_flower_game.jpeg`）
- [x] **状态条超宽可见性修复**：Mate 90 Pro 高级局 → 时钟 + 计时贴左沿、
      雷数「99」+ 雷图标贴右沿，两个计数器**同时可见**
      （截图 `docs\verify\V4P90_strip_left.png` / `V4P90_strip_right.png` / `V4P90_strip_fixed.png`）
- [x] **外观设置重启后保留**：Mate X7 内屏 —— 选绿色 → 确定 → **重启应用** → 棋盘仍是绿色
      （截图 `docs\verify\M6_after_restart.jpeg`；日志 `[GameStats] 外观已保存 board=1 game=0`）
      —— 注：`docs\verify\M3_green.jpeg` 名字带 green，但**那张拍的是蓝色棋盘**（砖块主色采样为偏蓝 `(168,192,216)`），
      不是绿棋盘证据；绿棋盘的证据是 M6。
- [x] **对话框逐像素比对**：失败框与关于框在真机上的缩放都是**整数 2 倍**
      （966 = 483×2、576 = 288×2；628 = 314×2、394 = 197×2），没有半像素、没有插值；
      客户区一致率 **92.50%** / **86.27%**（`docs\DIALOG-PIXEL-DIFF.md`）
- [x] **七段数码管渲染器过了对抗性复审**：Codex 裁定 **BLOCKER**（3 个 P1 + 1 个 P2），
      已按意见修完（`docs\SEVEN-SEG-COUNTER.md` §0.1，复审原文 `docs\verify\sevenseg-review\review.txt`）

### 2.6 最终版式实测数字

| 设备 | 初级 9×9 | 高级 16×30 |
|---|---|---|
| Mate 90 Pro | n=3 / 格边 108 px / 原点 (154, 754) | n=2 / 格边 72 px / 原点 **(-440, 696)**（横向超宽，可平移） |
| Mate X7 | n=5 / 格边 180 px / 原点 (295, 167) | n=2 / 格边 72 px / 原点 (25, 497) |

**逐项证据**：`docs\CLICK-MATRIX-90P.md`、`docs\CLICK-MATRIX-X7.md`、
`docs\APPEARANCE-DIALOG.md`、`docs\SEVEN-SEG-COUNTER.md`、`docs\DIALOG-PIXEL-DIFF.md`，
截图在 `docs\verify\`。

---

## 3. 代码已就位，待验证

这些**代码写好了但没跑出结果**，不能算完成。

| 功能 | 落点 | 状态 | 验证方式 |
|---|---|---|---|
| **音效修复**（之前全哑） | `SoundPlayer.ets` | 代码已就位，待验证 | 真机听四个事件：新建 / 开格 / 插旗 / 踩雷。见 `VERIFY-GUIDE.md` §4.3 |
| **胜利动画与爆炸动画的真实运行** | `Anim.ets` | **未验证**（anim-agent 在做） | 需要人工赢一局并录屏/连拍 |
| **自定义局重开保留盘面** | `GameController.restart()` | 代码已就位，待验证 | 开 20×20×50 自定义局 → 「新建」→ 盘面应仍是 20×20×50 |
| **自定义雷数填 668 后确定** | `CustomField.clampSpec()` | 面板上限与超限拒绝**已复测**，**确定后的夹取未实测** | 填 668 → 确定，看是否被夹到本盘面上限 |
| **「抬一档」修法（L1）在真机/外屏的观感** | `GameController` 的抬档与纵向对齐 | 已修（`9a70112`），**未复测** | 见 `VERIFY-GUIDE.md` §4.6(4) |
| **双指捏合缩放** | `MinefieldCanvas.ets` / `GameController.ets` | 代码已就位，待验证 | **无法用 uitest 注入**，必须手捏，看 hilog 的 `[Touch] 捏合 档位n=…`。见 §4.6(1) |
| 单指拖动平移 | 同上 | 代码已就位，待验证 | 夹紧逻辑本轮改过，**修完未复验** |
| 折叠开合重排 | `onAreaChange` → `attach()` → `layout()` | 代码已就位，待验证 | 实际折屏一次，看状态是否保住。见 §4.6(3) |
| **真机 Pura X Max**（内外屏） | 整套 | **本轮全部改动都只在模拟器上验过** | 见 §4.6(2)(4) |
| longClick 插旗 / doubleClick 和弦 | `MinefieldCanvas.ets` | 收尾补测因**设备被并发操作**无法定性 | 需**独占设备**重跑。`uitest uiInput doubleClick` 本身也没验证过 |
| **花园玩法判负瞬间的完整开花序列** | `Anim.ets` + `flowerGardenSheet.png` | **未验证**（只验了图标与帧的位置） | 选花园 → 开一局 → 踩雷 → 看开花动画与三段判负音效（按剩余雷数 ≤10/≤40/更多分段） |

---

## 4. 已知缺陷与待办

### 4.1 已修但修正后未复测

1. **「抬一档」规则的 HIGH 级缺陷（L1）已修（commit `9a70112`），但修正后的行为未复测**：
   原缺陷是抬档只看「格子太小」、不看「抬完会不会反而装不下」，而纵向用**居中**而不是顶对齐 →
   内容高于视口时**上半截永久藏在菜单栏下**，那部分格子既看不见也点不着。
   现已改成「只有抬完纵向仍装得下、或横向本来就装不下才抬」+「纵向溢出改顶对齐」。
   **另 7 条 MEDIUM/LOW 一条未修**（`docs\LEAD-CHANGE-AUDIT.md` §1）。
2. **对话框高度封顶（Codex 复审那条）已修（commit `9a70112`），短画布场景未实测**：
   `computeDialogScale` 现在宽度与高度都参与封顶，对话框比画布还高时顶对齐。
   900×400 那种短画布没跑过。
3. **七段数码管计数器已换上去（commit `a2b635f`），但只在模拟器上看过观感**：
   几何与出处见 `docs\SEVEN-SEG-COUNTER.md`，渲染器 `common\SevenSeg.ets`。
   **真机上的观感没验过**。
4. **状态条超宽可见性修复已落地（commit `a2b635f`），只在 Mate 90 Pro 上验过**：
   折叠外屏（更窄）上的观感没验。

### 4.2 仍未解决 / 尚未定性

5. **音效是否真的出声**：代码修了（`fdSrc` 异步状态机抢跑），**但没人听过**。
6. **自定义雷数填 668**：面板上限与超限拒绝**已复测**；**静默替换已修**（`f261aa9`：提示行当场写出「当前 N 将按 M 布雷」）；
   但**填 668 → 确定后的实际布雷数还没试过**。
7. **自定义局重开保留盘面**：代码改了，**没试过**。
8. **胜利动画与爆炸动画的真实运行**：**未验证**（anim-agent 在做）。
9. **设备调试通道（hdc）在真机上会掉线**，需要手机点亮解锁才能继续验证。息屏 / 锁屏后掉。
10. **捏合缩放无法用 uitest 注入**，必须人工双指捏一下并看 hilog 的 `[Touch] 捏合 档位n=…`。
11. **`uitest uiInput doubleClick`（和弦）本身没验证过**。
12. **本轮全部改动都只在模拟器上验过，纯真机（Pura X Max）一次都没跑过**。
13. **Codex 对抗性复审**：最近一次（`a2b635f` 这一轮，七段渲染器）裁定 **BLOCKER**（3 个 P1 + 1 个 P2），
    已按意见修完（`docs\SEVEN-SEG-COUNTER.md` §0.1）。
    再往前对应用仓整体的一次裁定 **CONCERNS**（来源：**由 P2 严重级别标记推断**，
    报告里没有显式 VERDICT 行），唯一一条即「对话框缩放只按宽度封顶」，**已修**（`9a70112`）。
    更早两次分别裁定 BLOCKER（`c32e2e6`，由 P1/critical/high 推断）与 CONCERNS，也已修。
14. **`docs\LAYOUT-MATRIX.md` 的数字已过期**：它的数据快照是 13:35，而「格边 < 48px 就抬一档」规则是
    13:39 才加的，所以表里「窄屏 + 高级 16×30 = n=1（格边 36）」那两行**现在应为 n=2（格边 72）**。
    要与当前代码一致的数字，重跑 `tools\check_layout.py`。
15. **对话框的逐像素比对只做了失败框与关于框**：胜利框与自定义框**没比**。
    工具 `tools\pixel_diff.py` 已就位，补比随时可做。

### 4.3 已撤销的旧结论（别再当 bug 追）

| 旧结论 | 撤销理由 |
|---|---|
| 「统计窗口绘制与命中缩放系数不一致」 | 测试方**坐标量偏 2 px**（红叉命中区左边界 x=1699，点的是 1697）。校准后 4 个控件全部可用 |
| 「帮助菜单打不开」 | 同因，用校准坐标后一次点中 |
| 「切换难度后闪出浅蓝灰已翻开格」 | 那是**发牌动画**，新 build 已不复现（同时刻像素数 8848/15972/28440 → 36/0/44，-99.8%） |
| **「计数器用粗体白字不是降级」** | **这条撤回了。** 拿参考实现 `BoardWidget.cpp:552-559` 当依据是错的 —— 参考实现怎么画不能证明原版长什么样。原版确实是七段数码管（微软原图 `helpBoard.png` 的「18」「40」逐像素反推）。现已按七段实现，见 §2.5 与 `docs\SEVEN-SEG-COUNTER.md` |

另外还有三项因**设备被并发操作**而无法定性的（不是应用缺陷，需独占设备重跑）：
longClick 插旗、doubleClick 和弦、「帮助(H)」对话框画面。

### 4.4 未做 / 故意不同

- **未做**（详见 `docs\WIN7-FEATURE-GAP.md` §2.1）：判负时其它雷逐个烧红的级联、
  键盘快捷键、和弦引爆的爆炸音效。**「选项(F5)」独立窗口与七段数码管是「故意不做」，不是待办。**
- **两条已知的「故意不同」**（产品决定，不是 bug）：
  - 首点机制：本项目「首点必开一片空地」，真 Win7 是「首点安全但可能开出一个数字」。
  - 状态条上时钟 / 雷图标**点不动**：**这是对的**，原版就是纯装饰（`docs\STATUS-STRIP-VERDICT.md` 结论 A）。

---

## 5. 装机清单（需要你在电脑上做 3 件事）

### 第 1 步：打开 DevEco Studio 并登录

1. 启动 `D:\software\DevEco Studio\bin\devecostudio.exe`
2. 用**华为账号**登录（这一步必须联网，签名要靠账号生成证书）
3. 打开工程 `C:\Users\19161\saolei`

### 第 2 步：自动签名

1. 菜单 **File → Project Structure → Signing Configs**
2. 勾选 **Automatically generate signature**
3. 等它生成 `.p12` / `.cer` / `.p7b`（一般在 `C:\Users\19161\.ohos\config\`）
4. 回到 **Project Structure → Modules → entry**，确认 **Signing Configs** 选的是 `default`

命令行构建不需要签名（产出 `entry-default-unsigned.hap`），但装到真机必须签名。

### 第 3 步：手机连电脑

1. 手机：**设置 → 关于手机 → 连续点击「版本号」7 次** → 输入锁屏密码，进入开发者选项
2. 开发者选项里打开 **USB 调试**
3. 用数据线连电脑，手机上弹「允许 USB 调试」→ 勾「一直允许」→ 确定
4. HarmonyOS NEXT / 鸿蒙 7 上还可能需要 **设置 → 关于手机 → 开发者选项 → 监视应用安装**（部分版本）

连上以后，在 DevEco 的 **Run** 按钮或命令行都能装：

```powershell
$env:DEVECO_SDK_HOME='D:\software\DevEco Studio\sdk'
& 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe' list targets
& 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe' install -r 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
```

（`-signed.hap` 是签名后产物的名字，以实际目录里的文件为准。）

---

## 6. 验证命令速查

### 6.1 一键脚本（推荐）

```powershell
# 模拟器
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\software\harmony\projects\minesweeper\tools\emu.ps1' -Action start
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\software\harmony\projects\minesweeper\tools\verify.ps1' -Device 127.0.0.1:5555 -Tag X7

# 真机
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\software\harmony\projects\minesweeper\tools\verify.ps1' -Device 6HR0226409003317 -Tag PX
```

脚本**自标定**：坐标一律用 vp，密度从布局日志读，画布顶偏移用 `tools\probe_canvas.py` 从截图量出来。
所以同一套脚本在真机（2.75）和两种模拟器（3.125 / 3.5）上都能跑。

### 6.2 手动命令

```powershell
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$d   = '6HR0226409003317'   # Pura X Max 的序列号

# 装 + 起 + 截图
& $hdc -t $d install -r 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
& $hdc -t $d shell aa force-stop com.example.saolei
& $hdc -t $d shell aa start -a EntryAbility -b com.example.saolei
& $hdc -t $d shell snapshot_display -f /data/local/tmp/s.jpeg
New-Item -ItemType Directory -Force -Path 'D:\software\harmony\projects\minesweeper\docs\verify' | Out-Null
& $hdc -t $d file recv /data/local/tmp/s.jpeg 'D:\software\harmony\projects\minesweeper\docs\verify\s.jpeg'

# 模拟触摸（**屏幕坐标**，不是画布坐标 —— 要自己加画布顶偏移）
& $hdc -t $d shell "uitest uiInput click 1295 900"          # 单击
& $hdc -t $d shell "uitest uiInput longClick 1241 546"      # 长按（插旗）
& $hdc -t $d shell "uitest uiInput doubleClick 1295 900"    # 双击（和弦）

# 看日志（崩溃时看这里）
& $hdc -t $d shell hilog -r
& $hdc -t $d shell hilog -x | Select-String 'JSAPP|ArkCompiler'
```

### 6.3 坐标换算铁律

```
屏幕 X = vp 坐标 × 密度
屏幕 Y = 画布顶偏移 + (vp 坐标 × 密度)
```

画布顶偏移**每台设备都不同**，用脚本量，别抄旧数字：

```powershell
python 'D:\software\harmony\projects\minesweeper\tools\probe_canvas.py' <截图> <棋盘原点x> <棋盘原点y> <格边px>
```

截图统一落 `docs\verify\`，**不要往 `docs\` 根目录丢**。

---

## 7. 布局速查

### 7.1 设备

| 设备 | 画布 | 密度（px per vp） | 画布顶偏移 |
|---|---|---|---|
| Pura X Max 内屏 | 2584 宽 | **2.75** | 用 `probe_canvas.py` 量 |
| Pura X Max 外屏 | 1323 宽 | **2.75** | 用 `probe_canvas.py` 量 |
| Mate X7 模拟器内屏 | 2210 宽 | **3.125** | 实测 **121**（`CLICK-MATRIX-X7.md` 附 A2） |
| Mate 90 Pro 模拟器 | 1280 宽 | **3.5** | 用 `probe_canvas.py` 量 |

### 7.2 缩放档（版式重做后）

来自 `docs\LAYOUT-MATRIX.md` §2 的推演（**注意 §4 第 8 条：已过期**）：

| 画布 | 初级 9×9 | 中级 16×16 | 高级 16×30 |
|---|---|---|---|
| Pura X Max 内屏 | n=4（格边 144） | n=2（72） | n=2（72） |
| Pura X Max 外屏 | n=4（144） | n=2（72） | n=1 → **现应为 n=2（72）** |
| Mate X7 模拟器内屏 | n=5（180） | n=3（108） | n=2（72） |
| Mate 90 Pro 模拟器 | n=3（108） | n=2（72） | n=1 → **现应为 n=2（72）** |

「现应为 n=2」是「格边 < 48px 就抬一档」规则的结果（`MIN_CELL_PX = 48`，``Theme.MIN_CELL_PX``）。

---

## 8. 相关文档

| 文档 | 内容 |
|---|---|
| `docs\SPEC.md` | 规格主文档 |
| `docs\CHANGELOG-2026-10-31.md` | 当天这一轮改了什么的完整记录 |
| `docs\VERIFY-GUIDE.md` | 怎么验证（给人看的） |
| `docs\WIN7-FEATURE-GAP.md` | 与真 Win7 的 17 条差距逐条状态 |
| `docs\BUTTON-INVENTORY.md` | 49 个可交互元素清单 + 哪些还没测 |
| `docs\LAYOUT-MATRIX.md` | 四种屏幕尺寸的版式推演 |
| `docs\CLICK-MATRIX-X7.md` / `docs\CLICK-MATRIX-90P.md` | 两台设备的逐个点击矩阵 |
| `docs\CUSTOM-DIALOG-AUDIT.md` | 自定义难度对话框审计 |
| `docs\SPRITE-COVERAGE.md` | 精灵引用越界审计 |
| `docs\STATUS-STRIP-VERDICT.md` | 状态条左端是时钟不是笑脸的裁决 |
| `docs\ASSET-AUDIT.md` / `docs\SOUND-MAP.md` | 素材与音效盘点 |
