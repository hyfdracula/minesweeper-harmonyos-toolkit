# 自定义难度对话框 —— Win7 一致性定性（键盘裁决 + 四项核对）

- 日期：2026-10-31
- 范围：只读 `C:\Users\19161\saolei` 与 `C:\Users\19161\Desktop\minesweeper-refs`；**未改任何代码**。
- 离线证据清单（全部在本机，未联网）：`Minesweeper-master`（Lmy0217 Win32 仿 Win7）、
  `linux-minesweeper-main`（Qt6 复刻）、`ReversingMinesweeper-master`（**原版 XP 二进制的逆向重建**）、
  `win7-assets`（原版素材）、`Minesweeper-master/jpg`（原版界面截图）。
- 术语：**「原版」** 下面特指 `ReversingMinesweeper` 逆向重建出来的 Windows XP 原版 Minesweeper；
  **「两份参考」** 指 Lmy0217 与 linux-minesweeper。

---

## 1. 裁决：原版 Win7 的自定义对话框**没有数字键盘**；我们的画布键盘是**有意增强**

### 1.1 裁决

**原版的自定义对话框里没有任何按键控件。** 输入靠**系统键盘**（桌面版是物理键盘）。
因此「键盘是内嵌在框内右侧还是外挂」这个问题**在保真层面没有对照物**：
我们画的那块 3 列键盘是**我们自己加的触屏增强**，不是复刻对象；
外挂布局（框本体右侧留 12 参考像素、键盘整块画在框外）**不构成对原版的偏离**，
因为原版压根没有这块东西。

**同时要纠正一条线索**：「真实 Win7 中文版的自定义对话框带一整块数字键盘」这一说法，
**在本机全部离线证据里零支持**（见 §1.3 的穷举清单）。在拿到真机截图之前，
不应把它当作规格。

### 1.2 四条独立证据

**证据 A（最强）：原版 XP 二进制逆向重建 —— `ReversingMinesweeper-master`**

- `Minesweeper/resource.h:67-76`：
  ```
  // Custom Field Dialog
  #define ID_DIALOG_CUSTOM_FIELD            80
  #define ID_DIALOG_CUSTOM_FIELD_OK         1
  #define ID_DIALOG_CUSTOM_FIELD_CANCEL     2
  #define ID_DIALOG_CUSTOM_FIELD_HEIGHT     141
  #define ID_DIALOG_CUSTOM_FIELD_WIDTH      142
  #define ID_DIALOG_CUSTOM_FIELD_MINES      143
  #define ID_DIALOG_CUSTOM_FIELD_HEIGHT_LABEL 112
  #define ID_DIALOG_CUSTOM_FIELD_WIDTH_LABEL  113
  #define ID_DIALOG_CUSTOM_FIELD_MINES_LABEL  111
  ```
  → 自定义对话框的控件集合 = **3 个编辑框 + 3 个标签 + 确定 + 取消**。没有按键、没有上下箭头。
- `Minesweeper/windowing.c:51-57` 的帮助数据表只列了上面那 6 个可帮助项（HEIGHT/WIDTH/MINES + 三个标签），
  **再次确认对话框里没有别的控件**。
- `Minesweeper/windowing.c:194-238` `CustomFieldDialogProc`：只有 `SetDlgItemInt`（填初值）与
  `GetDlgIntOfRange`（取值并夹范围），**没有任何自绘、没有按键处理**。
- `Minesweeper/windowing.c:905-918` `GetDlgIntOfRange` 的语义是**夹取**：
  小于下界返回下界，大于上界返回上界。

**证据 B：Lmy0217 的 Win32 对话框模板（找到了，lead 之前找的是 utf8 副本，那份确实没有 DIALOGEX）**

- 真正的模板在 **`Minesweeper-master/Minesweeper/Minesweeper.rc:94-118`**（UTF-16LE 编码），
  不是 `utf8/Minesweeper.rc`（那份只有头文件，grep `DIALOGEX` 零命中）。
  ```
  IDD_OPTION DIALOGEX 0, 0, 297, 317
  ...
      LTEXT       "高度(9-24)(&H):",IDC_STATIC_HEIGHT,153,47,51,10
      LTEXT       "宽度(9-30)(&W):",IDC_STATIC_WIDTH,153,70,55,8
      LTEXT       "雷数(10-668)(&M):",IDC_STATIC_COUNT,153,94,58,8
      EDITTEXT    IDC_EDIT_HEIGHT,224,42,46,18,ES_AUTOHSCROLL
      EDITTEXT    IDC_EDIT_WIDTH,224,66,46,18,ES_AUTOHSCROLL
      EDITTEXT    IDC_EDIT_COUNT,224,90,46,18,ES_AUTOHSCROLL
  ```
  → 三个**普通编辑框**，连 spin 都没有，更没有键盘。
- `Minesweeper/utf8/Minesweeper.cpp:228` 的越界检查是**全局 668**：
  `if (tRow < 9 || tRow > 24 || tCol < 9 || tCol > 30 || tCount < 10 || tCount > 668)`
  且越界时**把夹取值写回编辑框**（234/240/246 行的 `SetDlgItemInt`）。

**证据 C：linux-minesweeper（Qt6）**

- `src/ui/OptionsDialog.cpp:83-88`：
  ```cpp
  m_rows = new QSpinBox;  m_rows->setRange(9, 24);
  m_cols = new QSpinBox;  m_cols->setRange(9, 30);
  m_mines = new QSpinBox; m_mines->setRange(10, 668);
  ```
  → **上下箭头式 spinbox，没有键盘**；雷数也是**全局 668**。

**证据 D：原版 XP 的雷数上限是「按盘面」而不是全局**

- `windowing.c:220-223`：
  ```c
  GameConfig.Height = GetDlgIntOfRange(hDlg, ID_DIALOG_CUSTOM_FIELD_HEIGHT, 9, 24);
  GameConfig.Width  = GetDlgIntOfRange(hDlg, ID_DIALOG_CUSTOM_FIELD_WIDTH, 9, 30);
  int maxMines = min((GameConfig.Height - 1) * (GameConfig.Width - 1), 999);
  GameConfig.Mines = GetDlgIntOfRange(hDlg, ID_DIALOG_CUSTOM_FIELD_MINES, 10, maxMines);
  ```
  → **原版在对话框里就按盘面尺寸夹雷数**（XP 的上限是 999，不是 668；
  668 是 Win7 的上限，而 24×30 时 `(24-1)*(30-1)+1 = 668`，两者在最大盘上重合）。
  我们的公式 `(h-1)*(w-1)+1` 与它同形，多出的 `+1` 是给「首点 3×3 安全区」留的余量
  （引擎 `reset()` 的注释就是这么写的）。

### 1.3 「原版有没有键盘」的穷举清单（证明确实找过）

`C:\Users\19161\Desktop\minesweeper-refs` 下**全部**图片逐张列尺寸（40 余张，按文件名+尺寸双重过滤）：

| 目录 | 图片 | 尺寸 | 是自定义对话框吗 |
|---|---|---|---|
| `Minesweeper-master/jpg` | win.jpg / loss.jpg / about.jpg / information.jpg / gaming.jpg / exploding.jpg / initializing.jpg | 396x340 / 483x288 / 615x408 / 702x254 / 615x408 / 615x408 / 615x408 | 否（只有结束框、关于、统计信息、棋盘） |
| `linux-minesweeper-main/screenshots` | blue.png / green.png / bosnia.png | 271x314 / 271x314 / 649x584 | 否（棋盘） |
| `win7-assets/images` | Minesweeper.bmp/png、Frame.bmp/png、helpBoard.png、thumb*.png、*Sheet.png | 144x468 / 600x351 / 256x192 / 92x92 / 109x109 / 94x54 / 2034x1206 / 2048x2016 | 否（精灵图、窗口九宫格、帮助图、缩略图） |
| `win7-assets/icons` | MineSweeper-{32,48,64,128}.png | — | 否（图标） |
| `Minesweeper-master/Minesweeper/res/bmp` | Minesweeper.bmp / Frame.bmp | 144x468 / 600x351 | 否 |
| `_wiki` | （空目录） | — | — |

**没有任何一张自定义对话框的截图。** 文件名过滤（`custom|option|setting|dialog|field|dlg|自定义`）
在整个 refs 树上只命中源码文件（`OptionsDialog.cpp` 等），没有命中任何图片。
→ **「Win7 中文版带一整块数字键盘」在本机离线证据里不成立**；要推翻这个裁决需要真机截图。

### 1.4 我们这套键盘该怎么定性（写进 SPEC 的措辞建议）

> **有意增强（偏离原版）**：原版的自定义对话框只有三个编辑框（高度/宽度/雷数），
> 没有任何按键控件（证据：`ReversingMinesweeper/resource.h:67-76`、`Minesweeper.rc:94-118`、
> `OptionsDialog.cpp:83-88`），输入依赖系统键盘。
> 本移植在对话框右侧外挂一块画布自绘的 3 列数字键盘（11 键：1-9 / 退格 / 0），
> 理由是：**鸿蒙的 Canvas 无法弹出系统软键盘**，而弹 IME 会破坏「像素级复刻的模态对话框」这一前提；
> 自绘键盘同时让「输入」与「绘制」共用同一套坐标，命中测试不会跑偏。
> 该键盘**不是原版元素**，复刻时不得据此推断原版版式。

外挂 vs 内嵌的取舍：**外挂**（框 280 + 间隙 12 + 键盘 110 = 402 参考像素）——
原版那个小框根本放不下键盘，外挂是唯一能把两者都放大的办法；
若改成内嵌，框宽要涨到 402，桌面版那个「小方框」的比例就完全不像原版了。

---

## 2. 窄屏（1280 宽）会不会裁切：**不会**

### 2.1 外接框宽度的算法

- 框本体 `DLG_W = 280`（`CustomField.ets:37`），键盘 `NumKeypad.width() = 3*34 + 2*4 = 110`（`NumKeypad.ets:36-39`），
  间隙 12（`GameController.ets:1286` 的 `dlgW + 12*s + keyW`）。
- **总宽 = (280 + 12 + 110) = 402 参考像素**；总高 = `max(DLG_H=200, keypad.height()=4*30+3*4=132) = 200`。
- `GameController.customLayout():1279-1290` → `computeDialogScale(402, 200)`；
  `computeDialogScale():1102-1107` = `max(1, min(2, 密度, (canvasW-32)/402, (canvasH-32)/200))`。
- 落位 `customOx = round((canvasW - 402*scale)/2)`，键盘画在 `oxVp + (280+12)*sVp`，
  右边缘正好 = `oxVp + 402*sVp` → **绘制与命中用的是同一个外接框，自洽**。

### 2.2 各画布宽度的数值（密度 2.75）

| 画布 | scale | 总宽(设备px) | 单侧留白 | 装得下吗 | 裁切 |
|---|---|---|---|---|---|
| 内屏 X7 2210×1616 | 2.000 | 804.0 | 703.0 | 是 | 无 |
| 外屏 1323×1000 | 2.000 | 804.0 | 259.5 | 是 | 无 |
| **lead 说的窄屏 1280** | **2.000** | **804.0** | **238.0** | **是** | **无** |
| 直屏手机 1080×2340 | 2.000 | 804.0 | 138.0 | 是 | 无 |
| 横屏/分屏 900×400 | 1.840 | 739.7 | 80.2 | 是 | 无 |
| 分屏宽 900（高 1616） | 2.000 | 804.0 | 48.0 | 是 | 无 |
| 分屏窄条 540×1200 | 1.264 | 508.0 | 16.0 | 是 | 无 |
| 450 宽 | 1.040 | 418.0 | 16.0 | 是 | 无 |
| 434 宽 | 1.000 | 402.0 | 16.0 | 是 | 无 |
| 400 宽 | 1.000 | 402.0 | -1.0 | 否 | 超出 2 px |
| 350 宽 | 1.000 | 402.0 | -26.0 | 否 | 超出 52 px（键盘右列被切） |

### 2.3 结论

1. **1280 宽屏上不会裁切**：scale = 2（宽度上限 `(1280-32)/402 = 3.10` 不构成约束，
   真正的约束是封顶 2 和密度 2.75），总宽 **804 设备像素**，单侧留白 **238 像素**。
   lead 提的「键位 x=1320/1395/1470」那组坐标是按更早的 scale 记的，现在整体缩到
   `oxVp + (280+12)*sVp` 起步，按 scale=2 算第三列右边缘 = `oxVp + 402*2 = oxVp+804`，
   而 `oxVp = (1280-804)/2 = 238` → 右边缘 1042 ≤ 1280 √ **在屏内**。
2. **唯一会裁切的条件**：画布宽 **< 434 设备像素**（= 158 vp @2.75）。那时
   `computeDialogScale` 里的 `Math.max(1, …)` 下限会把 scale 钉在 1，总宽 402 > 画布宽 → 键盘右列出屏。
   400 宽切 2px、350 宽切 52px。**任何真机（含分屏窄条 540）都到不了这个宽度**，
   所以现网不会出问题；但这是靠 `Math.max(1,…)` 之外的巧合兜住的。
   **建议**：把 `computeDialogScale` 里的 `Math.max(1, (canvasW-32)/refWidth)` 改成允许 <1
   （下限放到 0.5 之类），这样任何宽度都是「等比缩小以适应」，从根上消除裁切。
3. **高度封顶不会反过来把宽度顶出去**：`computeDialogScale` 是取 min，高度封顶只会让 scale 变小、
   总宽同比变小 √（900×400 那行：scale 被高度压到 1.84 → 总宽 739.7 ≤ 900 √）。

---

## 3. 输入规则实际行为表（逐条对着 `CustomField.ets` 核）

| # | 行为 | **实际** | 出处 | 与原版对照 |
|---|---|---|---|---|
| 1 | 接受哪些字符 | 只接受**单个** 0-9；其余一律 `return false` | `CustomField.ets:224-230` | 原版是系统编辑框，能打负号/字母，但夹取时会被 `GetDlgIntOfRange` 归位 |
| 2 | 焦点范围 | 焦点不在 0..2 直接 `return false` | 231-234 | — |
| 3 | 替换 vs 追加 | `replace = replaceNext || 焦点变了` → **刚获得焦点时第一位数字覆盖旧值**，之后逐位追加 | 236-237 | 对应 Win7 编辑框「获得焦点即全选」 |
| 4 | 超上限 | **拒绝这一位**（值不变、返回 false），**不是截断** | 239-241 | 原版是「输入时不限、确定时夹取」→ 我们更严 |
| 5 | 高度上限 | 24 | `maxOfField` 516-518 | 原版 9-24 √ |
| 6 | 宽度上限 | 30 | 519-521 | 原版 9-30 √ |
| 7 | 雷数上限 | **668（全局，不按盘面）** | 522-533 | Lmy 的标签「雷数(10-668)」与源码 `tCount > 668` √；linux `setRange(10,668)` √ |
| 8 | 下限 | **输入阶段不夹下限**（高度可以输成 1），下限统一在确定时由 `clampSpec` 处理 | 220-221 注释 + `clampSpec:190-194` | 原版确定时才夹 √ 语义一致 |
| 9 | 改行列后的连带 | 改了高度或宽度，若当前雷数超新上限，**立刻被收回**（数字可见地变小） | 244-249 | 原版无此连带（对话框里三框独立） |
| 10 | 退格 | `Math.floor(cur/10)`；单位数退成 **0**（不是空），再退仍是 0 | 256-265 | 原版编辑框退格会真的清空 |
| 11 | 退格后继续输入 | 退格后 `replaceNext=false` → 下一位数字是**追加**（19→退格→1→输 5→15） | 263-264 | — |
| 12 | 负数 | **不可达**（无负号键、字符白名单、退格恒非负） | 228-230 / 262 | — |
| 13 | 空值 | **不可达**（字段最小为 0） | 262 | 原版可以清空后确定 → 夹到下界 |
| 14 | 换字段 | **只能点输入框**（`hit` 返回 height/width/mines → `focusField`），键盘上没有 Tab/下一个键 | 272-286；`NumKeypad.ets:17-22` | 原版用 Tab 键切焦点 |
| 15 | 换字段后的输入 | 下一位数字**替换**该框旧值（`replaceNext=true`） | 285 + 236 | 对应 Win7 获得焦点即全选 √ |
| 16 | 确定时的夹取 | 高度→[9,24]、宽度→[9,30]、**雷数→[10, maxMines(高,宽)]**、焦点→[0,2] | `clampSpec:189-196` | 原版 XP 用 `GetDlgIntOfRange` 做同样的夹取（`utils`→`windowing.c:905`）√ |

---

## 4. 雷数上限：三处公式是否一致

| 位置 | 公式 | 语义 |
|---|---|---|
| `CustomField.maxMines(h,w)`（202-207） | `min(668, (h-1)*(w-1)+1)`，行列先夹到 [9,24]/[9,30] | 面板层「本盘面最多 N」 |
| `CustomField.maxOfField(s,2)`（522-533） | `MAX_MINES = 668` | 面板层**输入**上限（全局） |
| `MinesweeperEngine.maxMinesFor(r,c)`（184-188） | `min((r-1)*(c-1)+1, r*c-1)` | 引擎层兜底 |

**一致性核对：**
- `maxMines` 与 `maxMinesFor` **数值恒等**：`(r-1)*(c-1)+1 ≤ r*c-1` 恒成立
  （展开：rc-r-c+2 ≤ rc-1 ⟺ r+c ≥ 3，恒真），所以引擎那层 `min` 永远取第一项 →
  **两个公式结果完全相同**，不存在「面板说 65、引擎说 64」的错位 √。
- 24×30 时 `(24-1)*(30-1)+1 = 23*29+1 = **668**` → 与全局上限 668 在最大盘上重合 √
  （这正是 SPEC §2 里「最大 668」的来源）。
- 9×9 时 `(9-1)*(9-1)+1 = 65`；16×16 → 226；16×30 → 436。
- **提示行文案与代码一致**：`CustomField.ets:393-394` 写「雷数 10-668（本盘面最多 N）」，
  N 取 `maxMines(s.height, s.width)` → 与实际夹取用的是同一个函数 √ **文案不骗人** √。

**两处需要修（都不是公式错，是行为/文档）：**

1. **静默替换**：9×9 填 500 → 面板放行（≤668）→ 确定时 `clampSpec` 夹成 **65**，
   界面上没有任何一句话说明「实际生效 65 颗」。
   原版两处都会把结果**写回输入框**（Lmy `Minesweeper.cpp:234/240/246` 的 `SetDlgItemInt`；
   原版 XP 至少用 `GetDlgIntOfRange` 夹了值）。
   **建议**：确定时若发生夹取，把生效值回填到框里并给一句提示（或直接在确定按钮上方显示
   「本盘面最多 65 雷，已按 65 开局」）。
2. **注释过期**：`CustomField.ets:217` 的注释仍写「雷数上限 maxMines(高度, 宽度)」，
   与 533 行改成的全局 668 **矛盾** → 注释该改成「输入上限 668；确定时按盘面夹取」。

---

## 5. 确定后的参数来源与统计链路（核对结果）

| 问题 | 结论 | 出处 |
|---|---|---|
| 确定后真的用上自定义参数吗？ | **是**。`'ok'` → `clampSpec(spec)` → `customGame = true` → `startNewGame(s.height, s.width, s.mines)` | `GameController.ets:1356-1361` |
| 自定义局 → 「再玩一局 / 新建(F2)」的参数来源 | **当前盘面**，不是难度预设：`restart()` 取 `engine.rowCount/colCount/mineCount` 再 `startNewGame` | `GameController.ets:166-177` |
| `restart()` 会把 `customGame` 清掉吗？ | **不会**（只有 `rows<=0` 的兜底分支清 false，172 行）→ 重开后的自定义局**仍然不进统计** √ | 166-177 |
| 换难度会清掉吗？ | 会，`setDifficulty()` 里 `customGame = false` √ | 150 |
| 自定义局进不进统计？ | **不进**。`GameStats.record()` 的唯一调用点被 `if (!this.customGame)` 包住 | 1081-1084 |
| 会污染最佳成绩吗？ | 不会。`isNewBest` 同样被 `!this.customGame` 抑制 | 1088 |
| `GameStats.level` 有没有污染难度归属？ | **没有**。全工程 grep：`GameStats.level` **只有一处赋值**（`GameController.ets:1078`）**和一处声明**，`GameStats.ets` 里出现的 `GameStats.levels()` 是另一个符号 —— **没有任何读取点** → 纯死字段，写什么都不可见 | 1078 / `GameStats.ets` |
| 遗留（老 P6，未解） | 自定义局的结束框仍显示**预设难度**的最快时间：`buildDialog` 里 `cfg = configOf(this.difficulty)`，`cfg.name` 是预设名（例如「初级」）→ 20×20 的自定义局赢了，框里显示的是初级的纪录 | 1078 附近 |
| 遗留（老 P4，未解） | `openCustomDialog()` 用 `configOf(this.difficulty)` 预填，**不按当前盘面预填** → 正在玩 20×20×50 时打开自定义框，里面是 9/9/10 | `GameController.ets:1295-1296` |

---

## 6. 给 lead 的一句话

**键盘问题：原版没有键盘（证据 A/B/C），我们的是有意增强，判为「有意偏离」而非「实现错误」，
外挂布局不需要改；1280 宽屏上总宽只有 804 设备像素、不会裁切（真正会裁的门槛是画布宽 < 434 设备像素，
即 158 vp）；雷数上限三处公式数值恒等、提示行文案与代码一致，只剩「确定时静默夹取不回显」和一处过期注释两处要改。**
