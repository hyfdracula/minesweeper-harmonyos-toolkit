# SPRITE-COVERAGE.md —— 精灵引用完整性与越界审计

> 盘点日期：2026-10-31
> 审计脚本：`docs\verify\check_sprites.py`（只读工程，只写 docs）
> 裁图目录：`docs\verify\sprites\`（184 张，含索引 `docs\verify\sprites\INDEX.md`）
> 无 emoji。

## 0. 结论速览

| 项 | 数 |
|---|---|
| 命名精灵引用条目 | **21**（其中活引用 18 条，已死的重复常量 3 条） |
| 展开后的单个源矩形 | **1584** 个（活的 1522 + 死的 62） |
| **越界（×2 后超出图集）** | **0** |
| 指向同一块像素的重复常量 | **4 组**（全部是「同一份矩形存在两处定义」，无一是裁错） |
| 疑似漏做的图标 / 素材区 | **4 处**（绿色主题拆雷光束、花园版爆炸动画、真七段数码管、otherSheet 底部渐变条） |

**一句话：越界 0 条；没有裁错的引用；有 4 处明显漏做的素材区（全部是「整块素材没接」，不是「坐标算错」）。**

---

## 1. 审计口径

- **坐标约定**：`Theme.ets` / `Anim.ets` 里存的是**逻辑坐标**（原版 tile = 18 单位），素材按 `SPRITE_SCALE = 2` 存储。
  取源像素时 **逻辑 ×2 = 存储像素**。
- **图集尺寸**（直接读 runtime `rawfile/` 里 PNG 的 IHDR 确认，不靠记忆）：

  | 图集 | 尺寸 | 逻辑尺寸 |
  |---|---|---|
  | `blueSheet.png` | 2034 × 1206 | 1017 × 603 |
  | `minesweeperSheet.png` | 94 × 54 | 47 × 27 |
  | `otherSheet.png` | 2048 × 2016 | 1024 × 1008 |

- **越界判据**：源矩形 ×2 后，只要 `x+w > 图集宽` 或 `y+h > 图集高` 即越界，并统计越界像素数。
- **覆盖面**：把每一条引用（含参数化帧族的每一帧）打进一张覆盖位图，再把没被覆盖的像素按「行游程 → 纵向合并 → 横向合并」分解成矩形块。

---

## 2. 精灵引用总表

`源矩形(×2后)` 一栏是**存储像素**坐标 `(x, y, w, h)`。

### 2.1 blueSheet.png（2034 × 1206）

| 引用名 | 所在文件:行 | 源矩形(×2后) | 是否越界 | 用途 | 裁图文件 |
|---|---|---|---|---|---|
| `normalTileRect(frame)` 720 帧 | `Theme.ets:28` | 帧 f → `(36*(f%25), 36*(f//25), 36, 36)`；最远 f=719 → `(684, 1008, 36, 36)` | 否 | 未揭开的凸起方砖（渐变） | `normalTileRect_f*.png`、`normal_tiles_contact.png` |
| `pressedTileRect(frame)` 720 帧 | `Theme.ets:35` | `normalTileRect` 的 x **+1000**；f=719 → `(1684, 1008, 36, 36)` | 否 | 已翻开的凹陷地板砖 | `pressedTileRect_f*.png`、`pressed_tiles_contact.png` |
| `RECT_FLAG` | `Theme.ets:41` | `(800, 1120, 36, 36)` | 否 | 红旗 | `RECT_FLAG.png` |
| `RECT_QUESTION` | `Theme.ets:43` | `(840, 1120, 36, 36)` | 否 | 问号 | `RECT_QUESTION.png` |
| `RECT_HILITE` | `Theme.ets:45` | `(880, 1120, 36, 36)` | 否 | 悬停高亮（已改为加法混合，见 `GameController.ets:488-490`） | `RECT_HILITE.png` |
| `RECT_MISFLAG` | `Theme.ets:47` | `(920, 1120, 36, 36)` | 否 | 错旗红叉 | `RECT_MISFLAG.png` |
| `RECT_SHADOW_U` | `Theme.ets:49` | `(960, 1120, 36, 6)` | 否 | 上边黑边 18×3 | `RECT_SHADOW_U.png` |
| `RECT_SHADOW_L` | `Theme.ets:51` | `(2024, 0, 6, 36)` | 否 | 左边黑边 3×18（贴最右缘） | `RECT_SHADOW_L.png` |
| `INLINE_SHADOW_L_LOW`（**内联字面量**） | `GameController.ets:436` | `(2024, 6, 6, 30)` | 否 | 角落处从黑边下方开始的左黑边 | `INLINE_SHADOW_L_LOW.png` |
| `RECT_COUNTER` | `Theme.ets:53` | `(0, 1160, 80, 42)` | 否 | 计数器凹槽面板 | `RECT_COUNTER.png` |
| `digitRect(1..8)` | `Theme.ets:56` | n → `(2000, 30*(n-1), 24, 30)`；n=8 → `(2000, 210, 24, 30)` | 否 | 彩色数字 1..8 | `digitRect_1..8.png`、`digits_contact.png` |

### 2.2 minesweeperSheet.png（94 × 54）

| 引用名 | 所在文件:行 | 源矩形(×2后) | 是否越界 | 用途 | 裁图文件 |
|---|---|---|---|---|---|
| `RECT_MINE` | `Theme.ets:63` | `(54, 0, 36, 36)` | 否 | 格下地雷 | `RECT_MINE.png` |
| `RECT_PANEL_MINE` | `Theme.ets:65` | `(0, 0, 50, 50)` | 否 | 状态条「雷图标」银钮 | `RECT_PANEL_MINE.png` |
| `WinDialog.win.icon`（**内联字面量**） | `WinDialog.ets:303` | `(0, 0, 50, 50)` | 否 | 胜利对话框里的雷图标 | `WinDialog_win_icon.png` |

### 2.3 otherSheet.png（2048 × 2016）

| 引用名 | 所在文件:行 | 源矩形(×2后) | 是否越界 | 用途 | 裁图文件 |
|---|---|---|---|---|---|
| `RECT_CLOCK` | `Theme.ets:70` | `(1810, 850, 50, 50)` | 否 | 状态条时钟图标 | `RECT_CLOCK.png`、`strip_otherSheet_clock_10x.png` |
| `Anim.explodeRect(f)` 23 帧 | `Anim.ets:55` | f → `(1456+118*(f%3), 118*(f//3), 114, 114)`；f=22 → `(1574, 826, 114, 114)` | 否 | 踩雷爆炸动画 | `Anim.explodeRect_f00..22.png`、`explode_frames_contact.png` |
| `Anim.disarmRect(f)` 38 帧 | `Anim.ets:115` | f → `(104*(f%7), 304*(f//7), 100, 300)`；f=37 → `(208, 1520, 100, 300)` | 否 | 胜利拆雷光束 | `Anim.disarmRect_f00..37.png`、`disarm_frames_contact.png` |
| `Anim.SCAN_BAR` | `Anim.ets:85` | `(0, 1824, 550, 124)` | 否 | 胜利扫描条 | `Anim_SCAN_BAR.png` |

### 2.4 已死的重复常量（仍然 export，但全工程无引用）

| 引用名 | 所在文件:行 | 源矩形(×2后) | 是否越界 | 状态 |
|---|---|---|---|---|
| `Theme.tripRect(f)` 23 帧 | `Theme.ets:74` | 与 `Anim.explodeRect` **逐帧相同** | 否 | **未引用** |
| `Theme.disarmRect(f)` 38 帧 | `Theme.ets:82` | 与 `Anim.disarmRect` **逐帧相同** | 否 | **未引用** |
| `Theme.RECT_SCAN_BAR` | `Theme.ets:89` | 与 `Anim.SCAN_BAR` **相同** | 否 | **未引用** |
| `Theme.TRIP_FRAMES` = 23 | `Theme.ets:73` | — | — | **未引用**（活的是 `Anim.EXPLODE_FRAMES`） |
| `Theme.TRIP_OFFSET` = [-18,-18] | `Theme.ets:78` | — | — | **未引用**（活的是 `Anim.EXPLODE_OFFSET`） |
| `Theme.DISARM_FRAMES` = 38 | `Theme.ets:81` | — | — | **未引用**（活的是 `Anim.DISARM_FRAMES`） |
| `Theme.DISARM_OFFSET` = [-18,-69] | `Theme.ets:86` | — | — | **未引用**（活的是 `Anim.DISARM_OFFSET`） |
| `SpriteAtlas.frameSheet` | `SpriteAtlas.ets:27` | — | — | 声明了但**从不赋值、从不使用**；`Frame.png` 也没进 `rawfile/` |

---

## 3. 越界清单

**空。0 条越界。**

逐条核算后，21 个命名条目展开出的 1584 个源矩形，全部满足 `x+w ≤ 图集宽` 且 `y+h ≤ 图集高`。

最接近边界的三条（都还在界内，列出以示已核）：

| 引用名 | 源矩形(×2后) | 图集 | 右边距 / 下边距 |
|---|---|---|---|
| `RECT_SHADOW_L` | `(2024, 0, 6, 36)` | 2034 × 1206 | 右 **10 px**，下 1170 px |
| `INLINE_SHADOW_L_LOW` | `(2024, 6, 6, 30)` | 2034 × 1206 | 右 **10 px** |
| `digitRect(8)` | `(2000, 210, 24, 30)` | 2034 × 1206 | 右 **10 px** |

`normalTileRect` / `pressedTileRect` 的帧号上限由 `Theme.gradientFrame()`（`Theme.ets:107-111`）夹到 `r ≤ 23`、`c ≤ 29`，故 frame ≤ 719，`pressedTileRect(719)` 的右边界是 1719，离 2034 还有 315 px。

### 3.1 越界查不出来的那类问题：图集选错（已逐块核对，结果正确）

「坐标算错」查不出来的是「**图集选错**」——数值在界内，但切到的是别的素材。已把三组动画帧在两张候选表上并排裁出来肉眼核对：

| 对比图 | 蓝色板 | otherSheet | 结论 |
|---|---|---|---|
| `cmp_tripf0.png`（逻辑 728,0,57,57） | 一片普通渐变方砖 | **爆开的尖刺雷球** | 爆炸动画在 **otherSheet**，工程画对了 |
| `cmp_disarmf0_blue.png`（逻辑 0,0,50,150） | 蓝色渐变方砖 | 灰色小方块（光束自带的那份方砖副本，位于 50×150 的 (17,69)） | 拆雷光束在 **otherSheet**，工程画对了 |
| `cmp_scanbar.png`（逻辑 0,912,275,62） | 越界 | **白→透明横向渐变条** | 扫描条在 **otherSheet**，工程画对了 |
| `cmp_disarmf0_green.png`（逻辑 364,0,50,150） | 蓝色渐变方砖 | **绿色小方块** | otherSheet 里确实有绿色版光束 —— 但工程没引用（见 §5.1） |

**结论：三组动画全部来自 otherSheet，工程无一处画错图集。**

---

## 4. 重复检查

指向同一块像素的有 **4 组**，全部是「同一份矩形在两处各定义一次」：

| 甲 | 乙 | 图集 | 重合矩形数 | 判定 |
|---|---|---|---|---|
| `Anim.explodeRect` | `Theme.tripRect` | otherSheet | 23 | 复制粘贴遗留，**Theme 侧是死的** |
| `Anim.disarmRect` | `Theme.disarmRect` | otherSheet | 38 | 同上 |
| `Anim.SCAN_BAR` | `Theme.RECT_SCAN_BAR` | otherSheet | 1 | 同上 |
| `RECT_PANEL_MINE` | `WinDialog.win.icon` | minesweeperSheet | 1 | `WinDialog` 里写的是字面量 `[0,0,25,25]`，没复用常量 |

**没有一条是「裁到了错误的像素」。** 前三组是维护性问题（改一处忘另一处），第四组是「该抽常量而没抽」。

---

## 5. 疑似漏做 / 多余（按覆盖图）

### 5.1 漏做（整块素材存在但工程完全没引用）

| # | 素材 | 位置（存储像素） | 是什么 | 影响 | 代价 |
|---|---|---|---|---|---|
| 1 | **绿色主题的拆雷光束** | otherSheet `x 728..1455, y 0..1823`（逻辑 x0 = 364，与 `Theme.h:148` 的 `x0 = s == BoardStyle::Green ? 364 : 0` 对上） | 绿色版的 38 帧胜利光束 | 做绿色主题时，`Anim.disarmRect` 的基址要能切到 364 | 小（一个常量 + 一个分支） |
| 2 | **花园版爆炸动画** | otherSheet `x 1810..2026, y 0..303`（`Theme.h:129`：`905 + 38*(f%3), 38*(f/3), 36, 36`） | 花朵版踩雷动画 | Flower Garden 变体没有素材支撑 | 中（还要 3 条 flowerLose 音效） |
| 3 | **真七段数码管** | otherSheet `y 1948..2015`，其中笔段在 `x 1..450` | 原版计数的七段显示；微软 helpBoard 插图里 LED 就是段状笔画 | 现在两个计数器用 sans-serif 粗体字模拟，与原版形制不同 | 中 |
| 4 | **otherSheet 底部渐变条** | otherSheet `x 0..460, y 1948..2016`（渐变条部分） | 一段窗口/面板渐变 | 用途不明 | 不建议接入 |

另有 **otherSheet 里第二份彩色数字 1..8 的副本**（`y 1948..2015` 右侧，约 `x 195..240`），与 blueSheet 的 `digitRect` 重复且未被引用 —— 属**多余**。

### 5.2 多余 / 无效（工程引用了但素材没有对应物，或素材有但工程用不上）

| 项 | 说明 |
|---|---|
| `Theme.tripRect` / `Theme.disarmRect` / `Theme.RECT_SCAN_BAR` / `Theme.TRIP_FRAMES` / `Theme.TRIP_OFFSET` / `Theme.DISARM_FRAMES` / `Theme.DISARM_OFFSET` | 7 个 export 出去的常量，全工程零引用，值与 `Anim.ets` 里的活版本相同 —— 建议删掉或改成对 `Anim` 的再导出，避免两边漂移 |
| `SpriteAtlas.frameSheet` | 字段声明了，从不赋值也从不使用；`SpriteAtlas.ets:25-26` 的注释说明了原因（`Frame.png` 上下颠倒、角落藏着状态条素材，九宫格不能直接用），但字段本身没有保留价值 |
| `SpriteAtlas.load()` 只加载 3 张表 | `rawfile/` 里也确实只有这 3 张 PNG，其余素材（`greenSheet.png`、`flowerGardenSheet.png`、`Frame.png`、`helpBoard.png`、`thumb*.png`、`icons/`）**全部未入库** |
| blueSheet 未覆盖区 | `x 900..999`（两块渐变之间的缝）、`x 1900..2033`（右侧一条渐变条，见 `unused_blueSheet_right_strip.png`，是窗口边框残片）、`y 1044..1119` 的横带、`x 80..2033, y 1160..1201`（计数器那一行除 0..80 外全空）—— 均为原版布局留白或边框残片，无需接入 |

### 5.3 「画了却点不动」的复核

静态审计提到的 4 处「画了却点不动」，其中状态条那一处已在本轮独立查清并另有专文：
**`docs\STATUS-STRIP-VERDICT.md`（结论 A）—— 素材里是时钟不是笑脸，且原版点它就没反应，所以「不响应」是正确行为，不是 bug。**

---

## 6. 裁图索引

`docs\verify\sprites\` 下 184 张 PNG，命名规则：

| 前缀 / 名字 | 内容 |
|---|---|
| `RECT_*.png` | 单个精灵的原始像素（2 倍放大） |
| `INLINE_SHADOW_L_LOW.png` | `GameController.ets:436` 的内联字面量矩形 |
| `digitRect_1..8.png`、`digits_contact.png` | 数字 1..8 |
| `normalTileRect_f*.png`、`normal_tiles_contact.png` | 720 帧凸起砖的代表帧与拼版 |
| `pressedTileRect_f*.png`、`pressed_tiles_contact.png` | 720 帧凹陷砖的代表帧与拼版 |
| `Anim.explodeRect_f00..22.png`、`explode_frames_contact.png` | 爆炸 23 帧 |
| `Anim.disarmRect_f00..37.png`、`disarm_frames_contact.png` | 拆雷光束 38 帧 |
| `Theme.tripRect_f*.png`、`Theme.disarmRect_f*.png`、`Theme_RECT_SCAN_BAR_DEAD.png` | 三组死掉的重复常量（与上面逐帧相同，可用来直观确认「重复」） |
| `cmp_*.png` | 同一逻辑矩形在两张图集上的并排对比（验图集选对没有） |
| `unused_*.png` | 覆盖图算出来的未引用素材区（疑似漏做） |
| `INDEX.md` | 逐张索引 |

---

## 7. 复核方法（任何人都能重跑）

```powershell
python "D:\software\harmony\projects\minesweeper\docs\verify\check_sprites.py"
```

只读 `C:\Users\19161\saolei` 下的 PNG 与 `.ets`，只写 `docs\verify\sprites\`。
中间结果落在 `docs\verify\sprites\_audit.json`，含每条引用的源矩形、越界像素数、重复组与未覆盖矩形块。
