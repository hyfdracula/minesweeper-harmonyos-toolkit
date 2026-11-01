# 点击矩阵 · 自动跑测版（CLICK-MATRIX-AUTO）

把 `docs/CLICK-MATRIX-90P.md`、`docs/CLICK-MATRIX-X7.md` 里手点的「每一个按钮都点一遍」
变成**一条命令、随时可重跑**的机器检查。

- 跑测器：`tools/click_matrix.py`
- 用例表：`tools/click_cases/<域>.json`
  - `menu.json`（本文档作者，菜单栏 14 项）
  - `board.json`（本文档作者，触摸路由对位）
  - `dialogs.json`、`custom.json`（另两位 agent 各自维护，格式与前两个一致）
- 证据图：`docs/verify/CM_<tag>_<名字>.jpeg`

---

## 1. 怎么跑

```powershell
cd D:\software\harmony\projects\minesweeper

# 只跑菜单 + 棋盘两个域（本机 5557 = Mate 90 Pro 模拟器）
python tools\click_matrix.py --device 127.0.0.1:5557 --cases menu,board --tag 1101

# 跑全部四个域
python tools\click_matrix.py --device 127.0.0.1:5557

# 只跑用例 id 含某段字符串的
python tools\click_matrix.py --device 127.0.0.1:5557 --only menu.game

# 打印每一步断言的细节
python tools\click_matrix.py --device 127.0.0.1:5557 --cases board --verbose
```

参数：

| 参数 | 含义 |
|---|---|
| `--device` | hdc 设备地址（默认 `127.0.0.1:5557`） |
| `--cases` | 要跑的域，逗号分隔；省略 = `tools/click_cases/` 下全部 |
| `--only` | 只跑用例 id 含这个子串的 |
| `--tag` | 证据图名前缀：`CM_<tag>_<名字>.jpeg`；省略则 `CM_<名字>.jpeg` |
| `--verbose` | 打印每条断言的比对细节 |

退出码：全过 = 0，有失败 = 1。

**跑测器不会 `hdc install -r`**：安装会清应用数据，外观设置会丢。
需要装新包请在开跑之前装好，跑测过程中只做 force-stop / start / 点击 / 截图。

---

## 2. 本轮结果（2026-11-01，设备 127.0.0.1:5557 / Mate 90 Pro 模拟器）

命令：`python tools\click_matrix.py --device 127.0.0.1:5557 --cases menu,board --tag 1101`

**总计 27 条：通过 27，失败 0**（用时 468 秒）。

> 2026-11-01 补修：dialog/custom/keypad 空间的 region 的 w/h 之前没乘缩放 s
> （只查了左上角四分之一），已修；修完重跑仍是 27/27。

### 2.1 菜单域 `menu.json`（15 条）

| 用例 id | 断言的是什么 | 结果 | 证据图 |
|---|---|---|---|
| `menu.game.open` | 点「游戏(G)」→ 下拉面板出现（区域变亮 + 像素变化） | 通过 | `CM_1101_game_menu_open.jpeg` |
| `menu.game.toggle` | 再点一次 → 面板收起（区域变暗） | 通过 | `CM_1101_game_menu_toggle.jpeg` |
| `menu.help.open` | 点「帮助(H)」→ 帮助下拉面板出现 | 通过 | `CM_1101_help_menu_open.jpeg` |
| `menu.game.new` | 游戏→新建(F2)：先点开一格再新建，棋盘区域必须变（= 真的重开了） | 通过 | `CM_1101_game_new.jpeg` |
| `menu.game.beginner` | 游戏→初级：hilog `菜单动作 beginner` + 布局日志（格边/棋盘原点）变了 | 通过 | `CM_1101_game_beginner.jpeg` |
| `menu.game.intermediate` | 游戏→中级：hilog `菜单动作 intermediate` + 布局变了 | 通过 | `CM_1101_game_intermediate.jpeg` |
| `menu.game.expert` | 游戏→高级：hilog `菜单动作 expert` + 布局变了 | 通过 | `CM_1101_game_expert.jpeg` |
| `menu.game.custom` | 游戏→自定义：hilog `菜单动作 custom` + 自定义框的值区变了 | 通过 | `CM_1101_game_custom.jpeg` |
| `menu.game.marks` | 游戏→标记(?)：hilog `菜单动作 marks` **且下拉面板消失** | 通过 | `CM_1101_game_marks.jpeg` |
| `menu.game.sound` | 游戏→声音：hilog `菜单动作 sound` **且下拉面板消失** | 通过 | `CM_1101_game_sound.jpeg` |
| `menu.game.best` | 游戏→最佳成绩：hilog `菜单动作 best` + 统计窗口区域变了 | 通过 | `CM_1101_game_best.jpeg` |
| `menu.game.appearance` | 游戏→颜色(C) F7：hilog `菜单动作 appearance` + 外观框区域变了 | 通过 | `CM_1101_game_appearance.jpeg` |
| `menu.help.help` | 帮助→帮助(H) F1：hilog `菜单动作 help` + 帮助框区域变了 | 通过 | `CM_1101_help_help.jpeg` |
| `menu.help.about` | 帮助→关于扫雷 A：hilog `菜单动作 about` + 关于框区域变了 | 通过 | `CM_1101_help_about.jpeg` |
| `menu.game.exit` | 游戏→退出(X)：hilog `菜单动作 exit` + **进程没了**（`app_alive: false`） | 通过 | `CM_1101_game_exit.jpeg` |

菜单栏 14 个元素（`docs/BUTTON-INVENTORY.md` §1 的 1~14 号）全部覆盖：
两个顶层标题（游戏(G)、帮助(H)）用 `menu.game.open` / `menu.help.open` / `menu.game.toggle`，
游戏下拉 10 项、帮助下拉 2 项各一条用例。分隔条（game sep1~sep4、help sep1）不是可交互元素，不在清单内。

### 2.2 棋盘域 `board.json`（12 条）

| 用例 id | 断言的是什么 | 结果 | 证据图 |
|---|---|---|---|
| `board.first_click` | 第一点 (4,4) → 这一格被翻开 | 通过 | `CM_1101_board_first_click.jpeg` |
| `board.cell.00` | 点 (0,0) → 翻开的是 (0,0)（左上角） | 通过 | `CM_1101_board_cell_00.jpeg` |
| `board.cell.04` | 点 (0,4) → 翻开的是 (0,4) | 通过 | `CM_1101_board_cell_04.jpeg` |
| `board.cell.08` | 点 (0,8) → 翻开的是 (0,8) | 通过 | `CM_1101_board_cell_08.jpeg` |
| `board.cell.40` | 点 (4,0) → 翻开的是 (4,0) | 通过 | `CM_1101_board_cell_40.jpeg` |
| `board.cell.44` | 点 (4,4) → 翻开的是 (4,4) | 通过 | `CM_1101_board_cell_44.jpeg` |
| `board.cell.48` | 点 (4,8) → 翻开的是 (4,8) | 通过 | `CM_1101_board_cell_48.jpeg` |
| `board.cell.80` | 点 (8,0) → 翻开的是 (8,0) | 通过 | `CM_1101_board_cell_80.jpeg` |
| `board.cell.84` | 点 (8,4) → 翻开的是 (8,4) | 通过 | `CM_1101_board_cell_84.jpeg` |
| `board.cell.88` | 点 (8,8) → 翻开的是 (8,8)（右下角） | 通过 | `CM_1101_board_cell_88.jpeg` |
| `board.outside.no_open` | 点棋盘上方的空白 → 整块棋盘一个像素都没变 | 通过 | `CM_1101_board_outside_no_open.jpeg` |
| `board.statusbar.no_open` | 点状态条（雷数/计时条）→ 整块棋盘一个像素都没变 | 通过 | `CM_1101_board_statusbar_no_open.jpeg` |

每条格子用例都**重新开局**再点：第一点一定翻开被点的那格（首点安全 + 洪水填充从这里起），
所以断言是确定的，不受雷分布影响；`board.outside.no_open` / `board.statusbar.no_open`
用整块棋盘区域做 `unchanged`，守住「点错地方不会误翻格子」。

### 2.3 其它两个域（别人的用例表，跑测器兼容性抽查）

| 用例 | 结果 |
|---|---|
| `custom.menu.open`（custom-agent，三条连续 `changed`） | 通过 |
| `custom.key.emptycell`（三条连续 `unchanged`） | 通过 |
| `custom.limit.height`（`changed` → 越界按键 → `unchanged`） | 通过 |

---

## 3. 跑出来的结论与判断

### 3.1 「菜单残留」那个历史 bug：当前代码里已经修好了

`docs/CLICK-MATRIX-90P.md` 记的异常 1：选完「标记(?)」「声音」之后**整块下拉菜单留在画布上不消失**。
现在 `GameController.menuActionAt()`（第 1710 行）在返回菜单动作 id 之前统一 `this.menuOpenId = ''`，
所以菜单会正常收起。

跑测器把这条**钉成了回归测试**：`menu.game.marks` / `menu.game.sound` 除了看 hilog
`菜单动作 marks` / `菜单动作 sound`，还断言下拉面板那块区域「变暗了」
（面板打开时那片区域平均亮度 240 = 白面板，关闭后是画布底色 205）。
将来谁再把这个 `menuOpenId = ''` 删了，这两条用例会立刻红。

### 3.2 顺带查出来的三个坑（都写在跑测器的注释里）

1. **菜单栏下拉条目的位置算不出来**（字体推进量），只能实测。本轮在 5557 上从截图量了
   每个条目的文字墨迹 bbox 中心，换算成**画布 vp** 存进跑测器（`MENU_ENTRIES`）。
   换设备不用重测：vp 是设备无关的，跑测器按 `x = round(vp / pxScale)` 换算成屏幕像素。
2. **画布顶在屏幕上的纵向偏移要自己量**（每台设备、每个 build 都可能不同）。
   跑测器在开局时用 `tools/probe_canvas.py` 同一套办法量一次（未开局棋盘第一行砖色上沿 − 棋盘原点 y），
   本轮 5557 上量到 **139 px**（参考值 138 是 lead 给的，实测 139）。
3. **棋盘原点在画布坐标里，图是屏幕截图**，差一个画布顶偏移。
   `cell_opened` 判定（数格子中心 50% 区域里还剩多少砖块蓝）第一次写漏了这个偏移，
   结果第 0 行三条用例全红；补上偏移后全绿。

### 3.3 本轮没有失败用例

27 条全过，所以没有「失败 + 判断」这一节可写。
中途出现过 11 条红（7 条菜单 + 4 条棋盘），根因是上面这三个坑加上两个跑测器自身的 bug
（断言之间共用检查点、动作后没让画面失效），修完再跑就全绿了。

---

## 4. 这个跑测器能验什么、不能验什么

**能验**：

- 点了之后**有没有发生事情**（画面变了 / 变了指定的区域 / 日志出了该出的行 / 进程没了）；
- 触摸**路由对不对位**（点的哪一格，翻开的就是哪一格）；
- 菜单动作**有没有把下拉面板收起来**（回归防护）；
- 切难度**有没有真的换布局**（布局日志的格边、棋盘原点变了）；
- 退出类动作**有没有真的终止应用**（`pidof` 查进程）。

**不能验**：

- **像素级 Win7 复刻保真度**。那是 `tools/pixel_diff.py` 的活（截图与原版素材逐像素比对）。
  本跑测器只看「有没有变化、变了多少像素」，不判断「变得对不对」。
- 像素断言是「区域平均亮度 / 差异像素占比」这种粗判，不是语义判断。
  例如「显示 0」「切回是替换不是追加」这类只能看图的语义，两个 agent 在用例的 `desc` 里注明了，
  跑测器不替它们设计断言。
- 不验**动画过程**（发牌、爆炸、胜利扫描条），只验动画结束后的状态。

---

## 5. 用例表格式

放在 `tools/click_cases/<域>.json`，一个文件一个域。

```json
{
  "domain": "menu",
  "cases": [
    {
      "id": "menu.game.new",
      "desc": "游戏→新建(F2)：重开一局，棋盘清空、计时归零",
      "steps": [
        {"act": "reset"},
        {"act": "menu", "top": "game", "entry": "新建"},
        {"act": "expect", "type": "changed", "region": {"space": "board", "cell": [3, 3], "w": 3, "h": 3}},
        {"act": "shot", "name": "menu_new"}
      ]
    }
  ]
}
```

### 5.1 动作（`act`）

| act | 参数 | 作用 |
|---|---|---|
| `reset` | `difficulty`（可选：beginner/intermediate/expert） | 强制停止 + 重启应用；`difficulty` 会在启动后再切一次难度。**不要在跑测中 `hdc install -r`** |
| `menu` | `top`（game/help）、`entry`（条目文案，可选） | 先点菜单栏空白处收掉已展开的下拉，再点顶层标题，再点条目。不给 `entry` 就只展开 |
| `tap` | `space`、`x`、`y`，或 `cell`（board 空间），或 `dialog`（dialog 空间） | 点一下 |
| `key` | `key`（0-9 / back / ok / cancel） | 数字键盘上的键；`ok`/`cancel` 映射到自定义框里的确定/取消按钮（键盘本身只有 11 个键，没有这两个） |
| `wait` | `ms` | 等一会儿 |
| `shot` | `name` | 存证据图 `docs/verify/CM_<tag>_<name>.jpeg` |
| `expect` | `type` + 各类型的参数 | 见下 |
| `lose_game` | — | 造出「失败框」局面（内部调 `tools/click_mkstate.py --state lose`） |
| `win_game` | — | 造出「胜利框」局面（`--state win`，胜利动画要等 3 秒） |

### 5.2 坐标系（`space`）

坐标单位各不相同，**别混**：

| space | 单位 | 备注 |
|---|---|---|
| `screen` | 屏幕像素 | 绝对坐标 |
| `canvas` | **画布设备像素** | 与屏幕只差一个纵向偏移（画布顶） |
| `menu` | **画布 vp** | 菜单栏专用 |
| `board` | 格子（`cell`: [行, 列]） | 点格中心；行 0 在上、列 0 在左 |
| `dialog` | 对话框**参考像素** | 还要给 `dialog`：`lose`/`win`/`help`/`about`/`stats`/`appearance` |
| `custom` | 自定义框**参考像素** | 原点是框的左上角 |
| `keypad` | 数字键盘**参考像素** | 原点是键盘自己的左上角（键左上 = (col*38, row*34)，键心 = 左上 +(17,15)） |

换算公式全部照抄 `GameController.ets`（跑测器里也有注释）：

```
画布 vp → 屏幕：x = round(vp / pxScale)，y = 画布顶偏移 + round(vp / pxScale)
对话框：s  = max(0.5, min(2, 密度, (画布宽-32)/参考宽, (画布高-32)/参考高))
        ox = round((画布宽 - 参考宽*s)/2)
        oy = 参考高*s > 画布高 ? 0 : round((画布高 - 参考高*s)/2)
自定义：s  = computeDialogScale(280+12+键盘宽, max(200, 键盘高))
        键盘原点 = customOx + (280+12)*s
```

### 5.3 断言（`expect` 的 `type`）

| type | 参数 | 判定 |
|---|---|---|
| `changed` | `region`（必给） | 区域相对基准**变了** |
| `unchanged` | `region`（必给） | 区域相对基准**没变** |
| `layout_changed` | — | 布局日志（格边/棋盘原点/适配档）与上一次不同 |
| `layout_regex` | `re` | 布局日志匹配正则 |
| `hilog_regex` | `re` | hilog 里出现匹配的新行（只看跑测期间新出现的） |
| `cell_opened` | `cell` | 被点的那一格被翻开了（触摸路由对位） |
| `region_light` / `region_dark` | `region`，可选 `min` / `max` | 区域平均亮度偏亮 / 偏暗（默认亮 ≥170、暗 ≤110） |
| `app_alive` | `alive`（true/false） | 应用进程在不在（`pidof`） |

**region 格式**：`{"space": "...", "x": .., "y": .., "w": .., "h": ..}`，
`space` 用的是跟 `tap` 同一套解析器（所以也能写 `{"space":"dialog","dialog":"lose",...}`）；
`space` 为 `board` 时用 `cell` + `w`/`h`（`w`/`h` 的单位是**格**）。

**region 的 x/y 与 w/h 单位一致**（w/h 会跟着该空间的缩放一起换算，别自己再乘一遍）：

| space | x/y 的单位 | w/h 的单位 | 换算成设备像素 |
|---|---|---|---|
| `screen` | 屏幕像素 | **屏幕像素** | 原样 |
| `canvas` | 画布设备像素 | **画布设备像素** | 原样 |
| `menu` | 画布 vp | **画布 vp** | ÷ pxScale |
| `board` | 格子（`cell`） | **格数** | × 格边（tile） |
| `dialog` | 对话框参考像素 | **对话框参考像素** | × 对话框缩放 s |
| `custom` | 自定义框参考像素 | **自定义框参考像素** | × 自定义框缩放 s |
| `keypad` | 数字键盘参考像素 | **数字键盘参考像素** | × 自定义框缩放 s |

> 坑（2026-11-01，dialog-fidelity-agent 报出、lead 确认）：早先 `region_to_screen()`
> 只把 x/y 按 s 换算，**w/h 原样返回**，于是 5557 上 s=2 时 dialog 空间的 region
> 只有意图的**四分之一**（左上角那块）。现在 w/h 会跟着乘 s ✓。
> 用例表里 dialog/custom/keypad 空间的 w/h 一律按**参考像素**写就对了。

**必须给 region**：`changed` / `unchanged` 不允许整屏——
状态条的时钟每秒跳，整屏永远在变，整屏断言必然假失败。

### 5.4 基准（checkpoint）怎么算

**基准 = 上一个「动作」之前的画面**。动作指 `reset` / `menu` / `tap` / `key` /
`lose_game` / `win_game`。断言本身**不**推进基准。

这样两条常用写法都成立：

- `reset → menu(自定义) → tap(键盘空格) → expect unchanged ×3`
  基准是「点空格之前」（对话框已开、值还是 9/9/10）→ 三个值区都没变 ✓；
  若拿「用例开头」或「上一条断言的检查点」当基准，就会跟「棋盘画面」比，误判成「变了」。
- `… → key(2) → expect changed → key(5)（越界被拒）→ expect unchanged`
  第二条的基准是「按 5 之前」，值区还是 2 → 没变 ✓。

另外两条给其它 agent 的提醒：

1. `key:"ok"` / `key:"cancel"` 映射到**自定义框里的确定/取消按钮**
   （`NumKeypad` 只有 11 个键：1-9、⌫、0，键盘上没有确定/取消）。
2. 同一个动作后面可以连着放多条断言（`changed` ×3、`unchanged` ×3 都行），
   它们都跟同一个基准比，不会出现「第二条拿自己跟自己比」。

---

## 6. 加一条新用例

1. 挑域：菜单栏 → `menu.json`；触摸路由 → `board.json`；
   对话框 → `dialogs.json`（dialog-fidelity-agent 管）；自定义框 → `custom.json`（custom-agent 管）。
2. 照抄 §5.1~§5.3 的格式，把用例追加到该文件的 `cases` 数组里（**只改自己域的文件**）。
3. 坐标怎么来：
   - 菜单栏条目：跑测器的 `MENU_ENTRIES` 里查（画布 vp）；
   - 对话框：`space=dialog` + `dialog` 名 + 参考像素（参考尺寸见 `WinDialog.ets` /
     `StatsWindow.ets` / `Appearance.ets` 的 width/height）；
   - 棋盘格子：`space=board` + `cell`；
   - 其它：先用截图量屏幕坐标，再换算成 `canvas` 的设备像素。
4. 跑一遍自己的域：`python tools\click_matrix.py --device 127.0.0.1:5557 --cases <域> --only <用例id子串> --verbose`
5. 通不过先看 `--verbose` 打的差异像素数与亮度，再决定是坐标错了还是断言写错了。
6. **每条用例都要有断言**（不许「点了就算过」）。

---

## 7. 已知限制

- 一轮 27 条约 7.5 分钟（每条用例要重启应用 + 截图比对）。
- 一次只占一台设备；并行跑会互相抢设备（`aa force-stop` 会把对方的应用也杀掉）。
- 菜单栏条目坐标是 5557 实测值（已换算成 vp），换分辨率/字体的设备可能要重量
  （量法：打开下拉 → 从截图取条目文字墨迹 bbox 中心 → `vp = 屏幕/密度`、`vp_y = (屏幕y-画布顶)/密度`）。
- `cell_opened` 靠「格子中心 50% 区域里还剩多少砖块蓝」判断，
  砖块蓝的判据与 `tools/probe_canvas.py` 一致（`b > 110 且 b-r > 45`）。
  打开后显示蓝色数字的格子，靠「数字占比 < 50%」跟盖着的砖块区分。
- `hilog_regex` 只在**跑测期间新出现**的日志行里找匹配，跑测器自己维护已读过的行集合。
- 跑测器不判断「变得到底对不对」，只判断「变了 / 没变」。
- **hdc 命令失败 = 错误，不是「没变化」**：点击、截图、`file recv`、`aa start/force-stop`
  失败或超时都会抛 `HdcError`，用例直接判失败。`pidof` 在设备上查无此进程时
  **退出码仍是 0、输出为空**（这才是「进程没了」），非零退出则当成设备/hdc 出问题抛错 ——
  否则一次 pidof 超时会让 `app_alive: false` 假通过。
