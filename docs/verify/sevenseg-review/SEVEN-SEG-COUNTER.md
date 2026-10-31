# SEVEN-SEG-COUNTER.md —— 状态条计数器的七段数码管几何与接线说明

> 日期：2026-10-31
> 实现文件：`C:\Users\19161\saolei\entry\src\main\ets\common\SevenSeg.ets`（本轮新建，**未**被工程引用）
> 预览图：`docs\verify\sprites\sevenseg_preview.png`（第一行=微软原图，第二行=本实现）、`sevenseg_variants.png`（4 个候选几何对比）
> 量图脚本：`docs\verify\measure_seg2.py`、`measure_seg3.py`、`sevenseg_preview.py`、`sevenseg_variants.py`
> 无 emoji。

---

## 0. 结论

**几何定死了，可以接。** 每一项都有出处，标了置信度：

| 结论 | 置信度 | 出处 |
|---|---|---|
| 面板 40×21、3 个槽、槽距 13、第 0 槽在面板内 x=1 | **高** | XP 版扫雷的二进制逆向重建（`drawing.c`）+ 「40 = 1 + 3×13」严丝合缝 |
| 数字**右对齐、不补零** | **高** | `helpBoard.png` 逐像素实测：计时「18」左边那一槽一个亮点都没有 |
| 负号是**独立的一段**（中段 g） | **高** | `helpBoard.png` 的「-40」+ XP 的 `NUM_MINUS 11` |
| 段的存在性与拓扑（a..g） | **高** | `helpBoard.png` 的「8」「4」「0」逐像素连通域分解 |
| 段的**粗细比例** | **中（反推）** | 三处独立来源互相吻合（见 §3.3），但绝对值取自 XP 字格 |
| 数字格绝对尺寸 13×21 | **中** | 由「面板宽 40 = 1 + 3×13」反推，与 XP 同宽面板一致 |
| 亮段颜色 `#FAFAFC` | **高** | `helpBoard.png` 段芯像素实测 |

---

## 1. 几何表

### 1.1 面板与槽位（单位：**参考像素**，即本项目 Theme 里的逻辑单位）

| 项 | 值 | 说明 |
|---|---|---|
| 凹槽面板 | **40 × 21** | `Theme.RECT_COUNTER = [0,580,40,21]`，与 `Theme.STRIP_PANEL_W/H`（40/21）一致 |
| 槽位数 | **3** | 百位 / 十位 / 个位 |
| 槽距 | **13** | 第 i 槽的 x = 1 + 13·i，即 **1 / 14 / 27** |
| 数字格 | **13 宽 × 21 高** | 格子填满面板高度；宽 13 = 槽距 |
| 第 0 槽在面板内的 x | **1** | 1 + 13×3 = 40，正好填满面板宽 |
| 对齐 | **右对齐，不补零** | 2 位数占右两槽，左槽空着 |
| 负号 | **只亮中段 g** | 占「紧挨数字左边那一槽」 |

### 1.2 段的坐标（**数字格局部坐标**，原点在数字格左上角；格宽 13、格高 21）

| 段 | 名称 | x | y | 宽 | 高 | 备注 |
|---|---|---|---|---|---|---|
| a | 上横 | 3 | 0 | 7 | 3 | |
| b | 右上竖 | 10 | 3 | 3 | 6 | |
| c | 右下竖 | 10 | 12 | 3 | 6 | |
| d | 下横 | 3 | 18 | 7 | 3 | |
| e | 左下竖 | 0 | 12 | 3 | 6 | |
| f | 左上竖 | 0 | 3 | 3 | 6 | |
| g | 中横 | 3 | 9 | 7 | 3 | **负号也用这一段** |

校验：
- 竖向：3（上横厚）+ 6 + 3（中横厚）+ 6 + 3（下横厚）= **21** = 格高 OK 
- 横向：3（左竖厚）+ 7（横段长）+ 3（右竖厚）= **13** = 格宽 OK 
- 横段长度 = 13 − 2×3 = 7，正好卡在两根竖段之间；
  角上是**斜角相接**（横段末行与竖段首列错开一格，形成 1 px 对角缺口），
  和 `helpBoard.png` 里「8」的角部处理一致。

### 1.3 数字 → 段组合

| 数字 | 亮段 | 掩码 |
|---|---|---|
| 0 | a b c d e f | 0x3F |
| 1 | b c | 0x06 |
| 2 | a b g e d | 0x5B |
| 3 | a b g c d | 0x4F |
| 4 | f g b c | 0x66 |
| 5 | a f g c d | 0x6D |
| 6 | a f g e c d | 0x7D |
| 7 | a b c | 0x07 |
| 8 | a b c d e f g | 0x7F |
| 9 | a b c d f g | 0x6F |
| 负号 | g | 0x40 |

（位序：a=1, b=2, c=4, d=8, e=16, f=32, g=64）

### 1.4 颜色

| 元素 | 值 | 出处 |
|---|---|---|
| 亮段 | **#FAFAFC**（RGB 250,250,252） | `helpBoard.png` 段芯像素实测：(247,249,251) / (250,250,252) / (250,251,253) / (254,254,255)；1 px 细笔画因抗锯齿偏暗 (218,225,237)，那是下界不是真值 |
| 灭的段 | **不画** | 原版凹槽里看不到暗段 |
| 凹槽底色 | 不用管 | 由 `RECT_COUNTER` 精灵负责 |

---

## 2. 与原版插图的逐项对照

`helpBoard.png` 状态条（`docs\verify\ORIG_STRIP_5x.png`，我自己的放大图在 `docs\verify\sprites\recheck_helpboard_strip_5x.png`）：

- 左面板 `x 53..79`（27 px 宽的凹槽）、`y 179..187`（9 px 高）；
  亮像素只在 **x 61..72**，即**偏右**，左边 8 px 全空 → **右对齐、不补零**（若补零，左槽该有个「0」）。
- 右面板 `x 175..201`，亮像素 `x 181..193` → 「-40」占满三槽。
- 连通域分解（`measure_seg3.py`）：
  - 「1」= `x 61..65, y 180..186`（5×7，13 个亮点）
  - 「8」= 七根独立的段：左上竖 `x 68, y 181..182`、右上竖 `x 72, y 181..182`、
    中横 `x 69..71, y 183`、左下竖 `x 68, y 184..185`、右下竖 `x 72, y 184..185`、
    下横 `x 69..70, y 186`、上横 `x 69..71, y 180`
  - 负号横杠 = `x 182..187, y 184`（右面板，中行位置 → 就是 g 段）
- 段的比例（插图尺度，格 5 宽 × 7 高）：横段厚 1/7 格高、竖段厚 1/5 格宽。

---

## 3. 几何来源与不确定性（逐条交代）

### 3.1 高置信部分

**（a）槽位布局 —— XP 版扫雷的二进制逆向重建**

`C:\Users\19161\Desktop\minesweeper-refs\ReversingMinesweeper-master\Minesweeper\drawing.c`：

```c
#define POINT_BIG_NUM_X 17
#define POINT_MID_NUM_X 30
#define POINT_LOW_NUM_X 43
#define NUMBER_WIDTH 13
#define NUMBER_HEIGHT 23
#define NUMBER_Y 16
#define NUM_MINUS 11
```

即：**3 个槽、槽距 13、负号是同一张位图里的第 11 个字形**；
XP 的计数面板是 `left=16, right=56`（**也是 40 宽**），数字从 17 开始（= 面板内 +1）。
本项目的凹槽面板 `RECT_COUNTER` 正好也是 **40 宽**，
于是槽位落在面板内 x = 1 / 14 / 27，**1 + 13×3 = 40，一像素不差** —— 这条对不上的概率极低。

**（b）右对齐、不补零** —— `helpBoard.png` 实测（§2）。

**（c）负号是独立段** —— `helpBoard.png` 的「-40」+ XP 的 `NUM_MINUS 11`。

**（d）段拓扑** —— `helpBoard.png` 的「8」正好分解成七根独立的段，
「4」= f g b c，「0」= a b c d e f，与标准七段一致。

**（e）颜色** —— §1.4。

### 3.2 中置信 / 反推部分（明确标出来）

**（f）段的粗细绝对值** —— **反推**。

`helpBoard.png` 的计数器只有 9 px 高，插图又是手绘的（凹槽 27×9 对应真实 40×21，
横向比 0.675、纵向比 0.43，**不是等比缩放**），所以它只能给**比例**，给不了绝对值。
绝对值取自 XP 的字格（13 宽 × 23 高，段粗 3），按 Win7 面板 21 高缩成 3/3/6。

**（g）数字格 13×21** —— **反推**。由「面板宽 40 = 1 + 3×13」与 XP 同宽面板推出。
高度取 21（填满面板），依据是 XP 的字格 23 高正好填满它 23 高的面板。

**（h）「1」的画法** —— **与原版插图有一处已知差异**。
插图里的「1」是**带小旗和底横的普通数字 1**（连通域 5×7、13 个亮点），不是七段的 b+c。
七段字体画不出小旗和底横，所以那是插图手绘的产物。
本实现按**标准七段**画 1 = b+c（真机的 LED 字体就是 b+c）。
若真机上看着不对，只需改 `DIGIT_MASKS` 里 1 那一项。

**（i）1 位负数的负号位置** —— 插图只有「-40」一例。
本实现取「负号紧挨数字左边那一槽」（-4 → `[空][-][4]`）；
XP 的代码是把负号固定放最左槽（-4 → `[-][0][4]`）。
**两种都说得通**，选前者是因为 Win7 是右对齐不补零，负号跟着数字走更自洽。
要改成 XP 那种，只要改 `slotsFor()` 里负号那一处。

**（j）灭段不画** —— 原版凹槽里看不到暗段，按原样。

### 3.3 三处来源的比例对照（互相吻合）

| 来源 | 横段厚 / 格高 | 竖段厚 / 格宽 | 说明 |
|---|---|---|---|
| `helpBoard.png` 插图（格 5×7） | 1/7 = **14.3 %** | 1/5 = **20 %** | 反推比例 |
| XP 字格（13×23，段粗 3） | 3/23 = **13.0 %** | 3/13 = **23.1 %** | 逆向重建 |
| **本实现**（13×21，tv=3/th=3） | 3/21 = **14.3 %** | 3/13 = **23.1 %** | 取二者一致的值 |

三处吻合，说明「横段比竖段细、竖段占宽约 1/4、横段占高约 1/7」这个比例是稳的；
只有绝对值（3 px）是反推的。

### 3.4 找不到的东西（如实交代）

- **Win7 原版七段字体的位图数据，本机找不到**：
  `win7-assets` 的四张图集里**没有**任何段形位图
  （`otherSheet` 底部那条是**渐变条 + 彩色数字 1..8 的副本**，见 `docs\SPRITE-COVERAGE.md` §2.3 的更正）；
  微软的 `helpBoard.png` 里那些段是**插图里画的**，不是可复用的精灵。
- **本机没有 winmine.exe**（`C:\Windows\System32`、`SysWOW64` 都没有），拿不到 XP 那张 `ID_BITMAP_NUMBERS 420` 的原始像素。
  所以段的**绝对粗细**只能反推（见 §3.2 f）。

---

## 4. 接线说明

### 4.1 调用签名

```ts
static draw(ctx: CanvasRenderingContext2D, value: number, xVp: number, yVp: number,
  sVp: number, sDev: number): void
```

| 参数 | 含义 |
|---|---|
| `ctx` | Canvas 上下文 |
| `value` | 要显示的整数，**可负**；小数截断。负号会自动画成独立的中段 |
| `xVp` | **凹槽面板左上角**在 **vp**（Canvas 单位）里的位置 |
| `yVp` | 同上，纵坐标 |
| `sVp` | **一个参考像素等于多少 vp**（= 参考像素→vp 的总缩放） |
| `sDev` | **一个参考像素等于多少设备像素**（本例只用来把段的边对齐到整数设备像素） |

面板内偏移与对齐规则（都已写死在 `SevenSeg` 里，调用方不用管）：

- 数字**右对齐**进 3 个槽（槽位在面板内 x = 1 / 14 / 27）；
- 数字格 13×21，**填满面板高度**（面板 40×21，数字从面板 x=1 开始）；
- 负号占数字左边那一槽；
- 灭的段不画。

### 4.2 要替换的现有代码

文件：`C:\Users\19161\saolei\entry\src\main\ets\common\GameController.ets`
函数：**`drawStatusStrip(ctx)`**（当前在第 724-756 行）

要删掉的两行（画数字的那两行）：

```ts
    ctx.fillText(`${this.seconds}`, this.v(timeX + STRIP_PANEL_W * u / 2), this.v(timeY + STRIP_PANEL_H * u / 2));   // 第 754 行
    ctx.fillText(`${e.minesRemaining()}`, this.v(mineX + STRIP_PANEL_W * u / 2), this.v(mineY + STRIP_PANEL_H * u / 2)); // 第 755 行
```

以及它们上面**只为这两行服务**的字体设置（第 748-753 行）：

```ts
    ctx.font = `bold ${12 * u}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
```

> 注意：`drawStatusStrip` 里如果还有别的 `fillText`，就只删字体设置里用得上的那几行；
> `ctx.textAlign/textBaseline` 改成 `left/alphabetic` 会不会影响别处，要自己确认。

**不要动**的第 743-746 行（凹槽面板与图标照旧由精灵画）：

```ts
    this.atlas.drawLogical(ctx, this.atlas.otherSheet, RECT_CLOCK, clockX, clockY, u);
    this.atlas.drawLogical(ctx, this.atlas.boardSheet, RECT_COUNTER, timeX, timeY, u);
    this.atlas.drawLogical(ctx, this.atlas.boardSheet, RECT_COUNTER, mineX, mineY, u);
    this.atlas.drawLogical(ctx, this.atlas.gameSheet, RECT_PANEL_MINE, iconX, iconY, u);
```

### 4.3 可直接粘贴的调用示例

在 `GameController.ets` 顶部的 import 区加一行（同目录）：

```ts
import { SevenSeg } from './SevenSeg';
```

在 `drawStatusStrip()` 里，把上面那两行 `fillText` 换成：

```ts
    // 状态条的两个计数器：原版是七段数码管（深蓝凹槽 + 亮段），不是字体。
    // 凹槽面板已经由 RECT_COUNTER 画好，这里只画亮着的段。
    // sVp = 一个参考像素等于多少 vp（u 个设备像素 * pxScale）；sDev = 一个参考像素多少设备像素。
    const segVp: number = u * this.pxScale;
    SevenSeg.draw(ctx, this.seconds, this.v(timeX), this.v(timeY), segVp, u);
    SevenSeg.draw(ctx, e.minesRemaining(), this.v(mineX), this.v(mineY), segVp, u);
```

为什么这样换算是对的：

- `this.v(px)` = `Math.round(px) * this.pxScale`（GameController 第 232-233 行），设备像素 → vp；
- 面板是用 `drawLogical(..., timeX, timeY, u)` 画的，设备尺寸 = 40·u × 21·u，
  所以**一个参考像素 = u 个设备像素 = u·pxScale 个 vp** ⇒ `sVp = u * this.pxScale`、`sDev = u`；
- `SevenSeg` 内部用 `pxScale = sVp / sDev` 反推回设备像素并取整，
  保证段的边落在**整数设备像素**上（不虚）。

### 4.4 需要留意

- 数字右对齐 ⇒ 2 位数（18）右边两槽有字、左边一槽空着，和原版一致；
  3 位数（999）会占满，负数 -40 占三槽（`[-][4][0]`）。
- 计时超过 999 时丢掉最高位（3 位只剩低 3 位）；负数放不下负号时丢掉最高位数字（-100 → `[-][0][0]`）。
- `SevenSeg` 内部会设 `ctx.fillStyle`，**不影响**别处（画完颜色被覆盖也没关系）。
- `SevenSeg` 目前**没有被工程任何地方 import**，所以 `build.ps1` 不会编译它。
  我已用一份**工程副本**加引用重编验证过它能过编译（见 §5），工程本体一行没改。

---

## 5. 已完成的验证

| 项 | 结果 |
|---|---|
| `build.ps1`（工程本体） | BUILD SUCCESSFUL —— 但**没编译到** SevenSeg（没人引用），所以这条不算数 |
| **工程副本加引用后重编** | BUILD SUCCESSFUL，`modules.abc` 里能查到 `SevenSeg` / `slotsFor` / `COLOR_LIT` ⇒ **文件本身编译通过** |
| 副本清理 | 已删除；工程 `pages/Index.ets` 等文件 mtime 未变，**工程本体没被改动** |
| 几何预览 | `docs\verify\sprites\sevenseg_preview.png`：第一行是微软原图裁剪，第二行是本实现画同样的「18」和「-40」 |
| 候选几何对比 | `docs\verify\sprites\sevenseg_variants.png`：4 个候选（13×21 / 13×18 / 13×16、细/粗段） |

---

## 6. 复核方法

```powershell
python "D:\software\harmony\projects\minesweeper\docs\verify\measure_seg3.py"        # 凹槽/亮段逐像素、连通域、颜色
python "D:\software\harmony\projects\minesweeper\docs\verify\measure_seg2.py"        # 状态条两个面板的 ASCII 像素图
python "D:\software\harmony\projects\minesweeper\docs\verify\sevenseg_preview.py"    # 本实现 vs 原图 预览
python "D:\software\harmony\projects\minesweeper\docs\verify\sevenseg_variants.py"   # 候选几何对比
```

只读 `C:\Users\19161\saolei` 与 `C:\Users\19161\Desktop\minesweeper-refs`，只写 `docs\verify\`。
