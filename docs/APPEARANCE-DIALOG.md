# Win7「外观(Change Appearance)」对话框 —— 实现记录

日期：2026-10-31
作者：menubar-fidelity-agent
范围：`entry\src\main\ets\common\` 下的 `Appearance.ets`（新）、`WinDialog.ets`、`WinMenu.ets`、`Theme.ets`、`SpriteAtlas.ets`，以及 `entry\src\main\resources\rawfile\` 的 6 张图 + 3 段音频。

---

## 0. 结论速览（lead 要的三个答复）

| 待定点 | 结论 | 把握 |
|---|---|---|
| 中文菜单项叫什么 | **「外观(C)」**（占位名，**未确证**） | 见 §1.1 |
| 菜单插在哪 | **「最佳成绩」之后、「退出」之前**（倒数第二项，F7） | 见 §1.2 |
| 对话框有没有确定/取消 | **有「确定(O)」和「取消(C)」**；**点确定才生效**，不是即时生效 | 见 §1.3 |

三个阶段都已实现并在真机（Mate X7，127.0.0.1:5555）上跑通：

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段 1 | 菜单项 + 画布自绘的外观对话框（两个分组框 / 四枚缩略图 / 选中框 / 确定 / 取消 / 置灰复选框） | 完成，真机通过 |
| 阶段 2 | 绿色棋盘（greenSheet.png + 棋盘样式概念 + 绿色胜利拆雷动画基址） | 完成，真机通过 |
| 阶段 3 | 花园玩法（flowerGardenSheet.png + 花朵踩雷动画 + 面板花朵图标） | 完成，真机通过 |

---

## 1. 三个待定点的证据链

### 1.1 中文菜单名 —— **未确证，用占位名「外观(C)」**

**查过什么**：把 `minesweeper-refs` 全仓扫了一遍 CJK 字符（Python + 正则，覆盖 `.c/.h/.cpp/.txt/.md/.xml/.rc/.py/.json/.ui/.ts/.html`，UTF-8 / UTF-16LE / GBK 三种编码逐个试），共 21 个文件含中文，**没有一条是这个菜单项的中文串**：

- `Minesweeper-master\Minesweeper\Minesweeper.rc`（Lmy0217 那个 Win32 复刻自带的中文资源）：
  ```
  POPUP "游戏(&G)"
      MENUITEM "新游戏(&N)\tF2",   ID_NEWGAME
      MENUITEM "统计信息(&S)\tF4",  ID_STATISTICS
      MENUITEM "选项(&O)\tF5",     ID_OPTION
      MENUITEM "退出(&X)",         IDM_EXIT
  ```
  它压根没有「外观」这一项（它的「选项」是难度/标记/声音/统计合一的另一个框）。
- 其余中文全是注释与 README。

**已确证的是英文原名**：原版 Win7 只有英文串 **"Change Appearance"**，快捷键 F7。证据两处，互相独立：

1. `linux-minesweeper-main\src\ui\HelpDialog.cpp:56-68` —— 复刻里**逐字镜像的 Win7 帮助原文**：
   ```
   To customize the game's appearance
   You can change the board color, and whether it conceals mines or flowers.
   1. Click to open Games.
   2. Double-click Minesweeper. ...
   3. Click the Game menu, and then click Change Appearance.
   4. Make your choices, and then click OK.
   ```
2. `linux-minesweeper-main\src\ui\AppearanceDialog.h:6-7`：
   > The Game > Change Appearance dialog, laid out like Windows 7's: a "Select Game Style" group and a "Select Board" group, each holding ...

**所以**：中文名**无法从 refs 确证**，按 lead 的指示用占位名。

取 **「外观(C)」** 而不是「颜色(C)」的理由：

- 它是已确证英文 "Change Appearance" 的直译；
- 这个对话框同时管**两组**：「游戏样式」（扫雷 / 花园）与「棋盘」（银蓝 / 绿色）。叫「颜色」只覆盖了其中一组，语义不全。
- 备选「颜色(C)」出自本项目旧文档 `WIN7-FEATURE-GAP.md` §3.2（那是照 XP 逆向工程里 `ID_MENUITEM_COLOR` 起的名，XP 那个 COLOR 是「彩色 / 单色」的开关，不是 Win7 的外观框）。

**改名成本 = 一行**：`Appearance.ets` 顶部的 `MENU_APPEARANCE_LABEL` 常量。

### 1.2 菜单位置 —— 「最佳成绩」之后、「退出」之前

| 证据 | 内容 | 倾向 |
|---|---|---|
| `linux-minesweeper-main\src\ui\MainWindow.cpp:134-145` | `New Game` / `Statistics` / `Options` / **`Change Appearance` (F7)** / `Exit` | 在最后一项之前 |
| `linux-minesweeper-main\src\ui\HelpDialog.cpp:52,65-66` | Win7 帮助先把 Game 菜单的 **Options** 讲一遍，再讲 **Change Appearance** | 在 Options 类项之后 |
| `ReversingMinesweeper-master\Minesweeper\resource.h:33-37` | `SOUND 526 / MARKS 527 / BEST_TIMES 528 / COLOR 529` —— COLOR 是最后一个自定义 ID | 紧跟 BEST_TIMES |

三处都指向同一处：**在「最佳成绩」之后、「退出」之前**。已按此实现（见 §3）。

> 注意：`ReversingMinesweeper` 是 **XP 扫雷的逆向重建源码**，它的 `resource.h` 是重建者自己的 ID 表，不是 Win7 exe 的资源表；`ID_MENUITEM_COLOR 529` 在那个项目里是「彩色 / 单色」开关（配 `CONFIG_COLOR`）。所以这条只能当**位置**参考，不能当**功能**参考。功能证据要看 Linux 复刻 + Win7 帮助原文。

### 1.3 对话框有没有确定/取消 —— **有，且是「点确定才生效」**

- Win7 帮助原文（`HelpDialog.cpp:67`）：**"Make your choices, and then click OK."** → 原版**有确定按钮**，且**不是即时生效**。
- 取消按钮：帮助原文没提（帮助只讲成功路径），但 Win7 对话框成对出现，且 Linux 复刻用的是 `QDialogButtonBox::Ok | QDialogButtonBox::Cancel`（`AppearanceDialog.cpp:177-181`）。
  → 本实现按 **确定 + 取消** 做，「取消」这一项标注为**推断**。
- 生效时机：本实现是**点缩略图只改「待定值」，点确定才真正换图集**，点取消则待定值作废（行为与帮助原文一致）。
- 另有一个原版有、Linux 复刻置灰的复选框 **「随机选择游戏样式和棋盘」**，本实现同样画出来并置灰（原版未实现）。

---

## 2. 对话框最终版式

参照 `AppearanceDialog.cpp` 的结构 + Win7 的观感自绘。单位是**参考像素**（与 `WinDialog.ets` 一致：几何乘 sVp，字号乘 sDev）。

对话框：**420 × 340 参考像素**，Aero 玻璃标题栏（与游戏内「失败 / 胜利」框同一套 chrome），标题 **「外观」**，右上角红 X。

```
 0                                        420
 0 ┌────────────────────────────────────────────┐  标题栏 29（粉渐变 + 红 X）
29 │  ┌── 游戏样式 ─────────────────────────┐   │
   │  │  [雷图]        [花图]              │   │  第 1 组 (12,40,396,104)
   │  │   扫雷          花园                │   │  缩略图 64×64，x=40 / x=226，y=52
   │  └────────────────────────────────────┘   │  说明文字墨迹顶 124
   │  ┌── 棋盘 ─────────────────────────────┐   │
   │  │  [蓝砖图]      [绿砖图]            │   │  第 2 组 (12,164,396,112)
   │  │   银蓝          绿色                │   │  缩略图 76×76，x=40 / x=226，y=176
   │  └────────────────────────────────────┘   │  说明文字墨迹顶 260
   │  □ 随机选择游戏样式和棋盘（置灰）         │  复选框 (18,284,13)
   │                    [确定(O)] [取消(C)]    │  按钮 (210,302,90,26) / (310,302,90,26)
340└────────────────────────────────────────────┘
```

配色取自 Linux 复刻的 Win7 取色（`AppearanceDialog.cpp:16-20`）：
选中框线 `#3c7fb1`、框内底 `#dcecfb`、选中说明文字的蓝底 `#2e8be0`（白字）。

**缩放**：直接复用现成的 `GameController.computeDialogScale()`（对话框走 `this.dialog` 这条现成通路，缩放是 `drawDialog()` 里现算的，没有另起炉灶）。
Mate X7 内屏实测：画布 2210×2208，缩放倍数 = 2，对话框 840×680 设备像素，居中，原点 (685, 764)（画布坐标）。

---

## 3. 菜单最终形态

```
游戏(G) ▾
   新建              F2
  ─────
   √初级
   中级
   高级
   自定义
   √标记(?)
  ─────
   √声音
  ─────
   最佳成绩
   外观(C)           F7     ← 新增
  ─────
   退出              X
```

---

## 4. 绿色 / 花园的资源基址（实测，不是抄坐标）

素材：`win7-assets\images\greenSheet.png`（2034×1206）、`flowerGardenSheet.png`（94×54）、`otherSheet.png`（2048×2016）。

### 4.1 棋盘图集（blueSheet / greenSheet）

用 PIL 逐区域对比两张图集，**布局完全同构**，坐标可以共用：

| 元素 | 逻辑矩形 | 蓝 | 绿 | 结论 |
|---|---|---|---|---|
| 砖块渐变第 f 帧 | `(18*(f%25), 18*(f/25), 18, 18)` | 蓝 | 绿 | 同坐标，只换图集 |
| 同帧按下态 | 上面 + (500, 0) | 蓝 | 绿 | 同坐标 |
| 旗 / 问号 / 高亮 / 错旗红叉 | `(400,560)` `(420,560)` `(440,560)` `(460,560)` 各 18×18 | 有 | 有 | 同坐标 |
| 上/左阴影条 | `(480,560,18,3)` `(1012,0,3,18)` | 有 | 有 | 同坐标 |
| 数字 1–8 | `(1000, 15*(n-1), 12, 15)` | 有 | 有 | 同坐标 |
| 计数器面板 | `(0, 580, 40, 21)` | 蓝 | 绿 | 同坐标 |

> lead 提醒「绿色版坐标可能不一样，必须逐个量」——**这条对砖块/旗/数字/面板不成立**，实测两张图集逐区域同构；
> 真正会变的是**胜利拆雷动画的基址**（下表）。

### 4.2 真正需要按主题切换的基址（`otherSheet.png`）

| 元素 | 蓝 | 绿 | 依据 |
|---|---|---|---|
| 胜利拆雷动画 38 帧（每帧 50×150） | 逻辑 x = **0** | 逻辑 x = **364** | `Theme.h:146-151` `x0 = Green ? 364 : 0`（7 帧 × (50+2) = 364） |
| 踩雷动画 23 帧（每帧 57×57） | 逻辑 x = **728** | 同左（与主题无关） | `Theme.h:130` |
| 踩雷动画 · **花** 23 帧（每帧 36×36） | —— | 逻辑 x = **905**，偏移 (−9,−9) | `Theme.h:129,135`；本机实测 otherSheet 存储像素 x=1810..2038 处确实是**雏菊开花**序列 |
| 胜利扫描条 | `(0, 912, 275, 62)` | 同左 | `Theme.h:157` |

### 4.3 游戏图集（minesweeperSheet / flowerGardenSheet）

| 元素 | 矩形 | 蓝雷版 | 花版 |
|---|---|---|---|
| 格下地雷 / 花 | `(27, 0, 18, 18)` | 银雷 | 白雏菊 |
| 面板雷图标（剩余雷数旁） | `(0, 0, 25, 25)` | 银雷 | 白雏菊 |

两张图集同为 94×54，坐标共用 √（真机已验证：切到花园后，剩余雷数旁的图标变成白雏菊）。

---

## 5. 代码改动

### 5.1 我直接改的（已落地、已构建）

| 文件 | 改了什么 |
|---|---|
| `common\Appearance.ets` | **新增**。对话框的规格（两个分组框、四枚缩略图、置灰复选框、确定/取消）、待定选择状态、`select()` / `owns()`；`MENU_APPEARANCE_LABEL` 常量 |
| `common\WinDialog.ets` | `DlgSpec` 增加可选的 `groups` / `thumbs` / `checkBox`；`WinDialogPainter.draw()` 画分组框、缩略图（选中蓝框 + 蓝底说明文字）、复选框；`WinDialogPainter.hitButton()` 增加缩略图命中（命中区 = 选中框，与画法严格一致） |
| `common\WinMenu.ets` | 头部注释更新（菜单列表）；新增 `appearanceEntry()`，返回「外观(C) / F7」这条菜单项 |
| `common\Theme.ets` | 新增 `BoardStyle`（Blue/Green）、`GameStyle`（Mines/Flowers）两个枚举；`DISARM_BASE_BLUE/GREEN`；`disarmRectFor(frame, style)`；`flowerTripRect(frame)`；`FLOWER_TRIP_OFFSET` |
| `common\SpriteAtlas.ets` | 加载 `greenSheet.png` / `flowerGardenSheet.png` / 四张 thumb；`applyStyle(board, game)` 切换当前图集；`boardStyle` / `gameStyle` 字段；`drawWholeToRect()`（1:1 图画进任意矩形，缩略图用） |
| `resources\rawfile\` | 新增 `greenSheet.png`、`flowerGardenSheet.png`、`thumbMines.png`、`thumbFlowers.png`、`thumbBlue.png`、`thumbGreen.png`、`flowerLoseShort/Medium/Long.wav` |

> **为什么 `boardSheet` / `gameSheet` 保留成字段而不是改成方法**：`GameController` 里有十几处 `this.atlas.boardSheet`，
> 改成方法就要动十几处（而 GameController 现在别人在改）。保留字段 + 一个 `applyStyle()` 切换点，改动面最小。

### 5.2 需要 lead 合并的 diff（`GameController.ets` + `Index.ets`）

**这些文件我没动**（按 lead 的要求）。下面是在**项目副本**上实际打上、**实际构建通过、实际在 5555 真机跑通**的完整 diff。

#### `entry\src\main\ets\common\GameController.ets`

```diff
@@ -16,7 +16,8 @@ import { SpriteAtlas } from './SpriteAtlas';
 import { WinDialogPainter, DlgSpec } from './WinDialog';
 import { GameStats } from './GameStats';
 import { SoundPlayer, Sound } from './SoundPlayer';
-import { WinMenuPainter, MenuSpec, MENU_BAR_H } from './WinMenu';
+import { WinMenuPainter, MenuSpec, MENU_BAR_H, appearanceEntry } from './WinMenu';
+import { Appearance } from './Appearance';
 import { CustomField, CustomSpec, DLG_W, DLG_H } from './CustomField';
 import { NumKeypad } from './NumKeypad';
 import { Anim } from './Anim';
@@ -28,8 +29,7 @@ import {
   gradientFrame, normalTileRect, pressedTileRect, RECT_FLAG, RECT_QUESTION, RECT_HILITE, RECT_MISFLAG,
   RECT_SHADOW_U, RECT_SHADOW_L, RECT_COUNTER, digitRect, RECT_MINE, RECT_PANEL_MINE, RECT_CLOCK,
   COLOR_OUTSIDE, COLOR_FLOOR, COLOR_SUNKEN,
-  STRIP_BAND, STRIP_CLOCK_SIZE, STRIP_PANEL_W, STRIP_PANEL_H, STRIP_GAP, stripMargin
-} from './Theme';
+  STRIP_BAND, STRIP_CLOCK_SIZE, STRIP_PANEL_W, STRIP_PANEL_H, STRIP_GAP, stripMargin, disarmRectFor, GameStyle, flowerTripRect, FLOWER_TRIP_OFFSET } from './Theme';

@@ -520,9 +520,11 @@ export class GameController {
             if (Anim.tripActive && idx === Anim.tripCell) {
               // 原版帧是 57x57 的整块（含溢出格子的部分），按原版偏移 (-18,-18) 画，
               // 不能居中缩放，否则爆炸会缩水。
-              const rect = Anim.explodeRect(Anim.tripFrame);
+              const isFlower = this.atlas.gameStyle === GameStyle.Flowers;
+              const rect = isFlower ? flowerTripRect(Anim.tripFrame) : Anim.explodeRect(Anim.tripFrame);
+              const off = isFlower ? FLOWER_TRIP_OFFSET : Anim.EXPLODE_OFFSET;
               this.atlas.draw(ctx, this.atlas.otherSheet, rect,
-                x + Anim.EXPLODE_OFFSET[0] * u, y + Anim.EXPLODE_OFFSET[1] * u,
+                x + off[0] * u, y + off[1] * u,
                 rect[2] * u, rect[3] * u);
             }
           } else if (cell.mine) {
@@ -590,7 +592,7 @@ export class GameController {
       const c = cell - r * this.engine.colCount;
       const x = this.boardX + c * this.tile + Anim.DISARM_OFFSET[0] * u;
       const y = this.boardY + r * this.tile + Anim.DISARM_OFFSET[1] * u;
-      this.atlas.drawLogical(ctx, this.atlas.otherSheet, Anim.disarmRect(f), x, y, u);
+      this.atlas.drawLogical(ctx, this.atlas.otherSheet, disarmRectFor(f, this.atlas.boardStyle), x, y, u);
     }
@@ -1175,6 +1177,8 @@ export class GameController {
       // 原版的「最佳成绩」是独立的**扫雷统计信息窗口**（information.jpg 的版式）
       this.openStatsWindow();
       return;
+    } else if (kind === 'appearance') {
+      this.dialog = Appearance.begin(this.atlas.boardStyle, this.atlas.gameStyle);
     } else if (kind === 'help') {
       this.dialog = WinDialogPainter.helpSpec();
     } else {
@@ -1413,7 +1417,21 @@ export class GameController {
       return null;
     }
     this.dialogLayout();
-    return WinDialogPainter.hitButton(d, this.dialogScale, this.dialogOx, this.dialogOy, px, py);
+    const hit = WinDialogPainter.hitButton(d, this.dialogScale, this.dialogOx, this.dialogOy, px, py);
+    // 「外观」对话框：缩略图切换 / 确定 / 取消 —— 自己处理，不往上抛
+    if (hit !== null && Appearance.owns(hit)) {
+      if (hit === 'appearance:ok') {
+        this.atlas.applyStyle(Appearance.pendingBoard, Appearance.pendingGame);
+        this.dialog = null;
+      } else if (hit === 'appearance:cancel') {
+        this.dialog = null;
+      } else if (Appearance.select(hit)) {
+        this.dialog = Appearance.spec();
+      }
+      this.draw();
+      return null;
+    }
+    return hit;
   }

@@ -1445,6 +1463,7 @@ export class GameController {
             { id: 'sound', label: '声音', checked: SoundPlayer.isEnabled },
             { id: 'sep3', label: '', separator: true },
             { id: 'best', label: '最佳成绩' },
+            appearanceEntry(),
             { id: 'sep4', label: '', separator: true },
             { id: 'exit', label: '退出', accelerator: 'X' }
           ]
```

#### `entry\src\main\ets\pages\Index.ets`

```diff
@@ -64,7 +64,7 @@ struct Index {
         this.controller.refreshMenu();
       } else if (action === 'marks') {
         this.controller.toggleQuestionMarks();
-      } else if (action === 'best' || action === 'about' || action === 'help') {
+      } else if (action === 'best' || action === 'about' || action === 'help' || action === 'appearance') {
         this.controller.openInfoDialog(action);
       } else if (action === 'custom') {
         this.controller.openCustomDialog();
```

合计：GameController 7 处 + Index.ets 1 处。

**为什么 Index.ets 也要动**：菜单动作统一走 `Index.onMenuAction`，而它只把 `best/about/help` 转给 `controller.openInfoDialog()`；`appearance` 得跟着进同一条路，**加一个 `|| action === 'appearance'` 即可**（如果 lead 更想零改动 Index.ets，也可以改成在 `GameController.menuActionAt()` 里直接把外观框打开，但那样菜单动作就不走统一回调了，不推荐）。

---

## 6. 构建结果

| 工程 | 命令 | 结果 |
|---|---|---|
| 真工程（只有我改的文件，**未合 diff**） | `powershell -NoProfile -ExecutionPolicy Bypass -File D:\software\harmony\projects\minesweeper\tools\build.ps1` | `BUILD SUCCESSFUL in 15 s`（HAP 12 265 KB） |
| 项目副本 + 上面那份 diff | 同上，加 `-Project <副本目录>` | `BUILD SUCCESSFUL in 18 s`（HAP 12 268 KB） |

编译告警 8 条，**全部是工程原有的**（`SoundPlayer.ets` / `MinefieldCanvas.ets` / `Index.ets`），我改的 5 个文件**零告警**。

**一个必须说的坑**：新文件如果没人 import，hvigor **根本不编译它**（我一开始就在 `Appearance.ets` 里塞了个类型错误，构建照样 SUCCESSFUL）。
所以做了两步：
1. 用故意写错的探针验证过「没被编译」（构建仍成功）；
2. 改成 `WinMenu.ets` → `import { MENU_APPEARANCE_LABEL } from './Appearance';`（`appearanceEntry()` 用它），
   让 `Appearance.ets` 进编译图。再用探针验证：故意写错后构建 **BUILD FAILED**（`Type 'string' is not assignable to type 'number'`），确认已被编译，随后还原。
   → **现在真工程不合并 diff 也能把 `Appearance.ets` 编译一遍**，类型错误会在构建期暴露。

---

## 7. 真机验证（Mate X7，127.0.0.1:5555）

设备：Mate X7 内屏，画布 2210×2208，密度 3.125，`[GameController] 布局` 日志为准。
截图存 `docs\verify\X7_8*.jpeg` … `X7_9*.jpeg`。

| 步骤 | 操作（屏幕坐标） | 期望 | 结果 |
|---|---|---|---|
| 1 | 菜单「游戏(G)」→ 「外观(C) F7」 | 弹对话框 | 通过（日志 `[Menu] 菜单动作 appearance`） |
| 2 | 看对话框 | 两个分组框 + 四枚缩略图 + 选中蓝框 + 置灰复选框 + 确定/取消 | 通过（`X7_91_final_dialog.jpeg`） |
| 3 | 点「绿色」缩略图 `(1213, 1313)` | 选中框移到绿色，蓝底白字 | 通过（`X7_92_final_green_selected.jpeg`） |
| 4 | 点「确定(O)」`(1195, 1515)` | 对话框关闭，棋盘变绿 | 通过（`X7_93_final_green_board.jpeg`，绿色像素 43 589 → 2 304 302） |
| 5 | 重新打开 → 点「花园」→ 点「取消(C)」`(1395, 1515)` | 棋盘保持绿色不变（取消不生效） | 通过（绿色像素前后都是 2 304 302） |
| 6 | 点「花园」→ 确定 → 开一局 | 剩余雷数旁的图标变成白雏菊 | 通过（`X7_90_flower_game.jpeg`） |

**坐标换算（实测，别再用预览图目测）**：
- 屏幕 y = 画布 y + **121**（本次 build 实测；lead 之前给的是 126，状态栏高度会变，以日志/实测为准）。
- 画布 → 屏幕 x 不偏移。
- 命中测试用的是**画布坐标**（`dialogButtonAt` 收到的就是画布坐标）。
- 对话框画布原点 (685, 764)，缩放 2。

---

## 8. 已知限制 / 还没做的

1. **样式不持久化**：切了绿色/花园，**重启 App 就回默认值**（蓝色/扫雷）。
   原版是持久化的（Linux 复刻存在 QSettings）。要持久化得写 `GameStats` / preferences（不在我的可写范围），或加一个 `AppearanceStorage`。
2. **花园的失败音效没接**：`flowerLoseShort/Medium/Long.wav` 三段已经拷进 rawfile，但触发点在 `SoundPlayer.ets`（不在我的范围）。目前花园版判负仍播 `gameLose.wav`。
   Linux 复刻的规则（`Sounds.h`）：雷数 ≤ 10 播 Short，≤ 40 播 Medium，更多播 Long。
3. **花园的「开花」动画已接**，但**没有验证过判负瞬间的完整开花序列**（只验证了图标与帧的位置正确）。
4. **对话框的视觉是「按 Win7 观感设计」**，不是照着 Win7 原图抠的 —— refs 里**没有 Win7 外观对话框的原图**（Lmy0217 的 jpg 里只有 about/gaming/loss/win，没有展开的对话框）。配色取自 Linux 复刻的 Win7 取色常量。
5. **菜单名「外观(C)」与对话框标题「外观」**的最终中文写法，**需要 lead 定**（refs 无中文证据，见 §1.1）。
6. 复选框「随机选择游戏样式和棋盘」按原版置灰不可点（Linux 复刻同样未实现）。

---

## 9. 附：改动文件清单（供 review）

```
entry/src/main/ets/common/Appearance.ets          （新增，217 行）
entry/src/main/ets/common/WinDialog.ets           （+分组框/缩略图/复选框的绘制与命中）
entry/src/main/ets/common/WinMenu.ets             （+appearanceEntry()，头部注释更新）
entry/src/main/ets/common/Theme.ets               （+BoardStyle/GameStyle/两个基址函数）
entry/src/main/ets/common/SpriteAtlas.ets         （+加载 6 张新图、applyStyle()、drawWholeToRect()）
entry/src/main/resources/rawfile/greenSheet.png
entry/src/main/resources/rawfile/flowerGardenSheet.png
entry/src/main/resources/rawfile/thumbMines.png
entry/src/main/resources/rawfile/thumbFlowers.png
entry/src/main/resources/rawfile/thumbBlue.png
entry/src/main/resources/rawfile/thumbGreen.png
entry/src/main/resources/rawfile/flowerLoseShort.wav
entry/src/main/resources/rawfile/flowerLoseMedium.wav
entry/src/main/resources/rawfile/flowerLoseLong.wav
```

未改（按 lead 要求）：`GameController.ets`、`Index.ets`、`MinefieldCanvas.ets`、`CustomField.ets`、`StatsWindow.ets`、`Anim.ets`。
