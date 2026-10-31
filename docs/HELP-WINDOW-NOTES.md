# 帮助窗口像素化 —— 把 Win7 原版 helpBoard.png 画进帮助对话框

日期：2026-10-31
改动范围：`entry/src/main/resources/rawfile/helpBoard.png`（新增）、
`entry/src/main/ets/common/Theme.ets`、`entry/src/main/ets/common/SpriteAtlas.ets`、
`entry/src/main/ets/common/WinDialog.ets`。
**没有动** `GameController.ets` / `Index.ets` / `MinefieldCanvas.ets` /
`StatsWindow.ets` / `CustomField.ets`（lead 正在改）。

---

## 1. 原图：它是什么

| 项 | 值 |
|---|---|
| 源文件 | `C:\Users\19161\Desktop\minesweeper-refs\win7-assets\images\helpBoard.png` |
| 尺寸 | **256 × 192 像素** |
| 色彩 | RGB（**无 alpha 通道**），69646 字节 |
| 复制到 | `entry/src/main/resources/rawfile/helpBoard.png`（69646 字节，字节级一致） |

内容（放大后逐块核对）：一局进行中的 Win7 扫雷画面 —— 蓝砖棋盘（已翻开的格子露出
白底和彩色数字 1/2/3），四周是原版窗口的浅蓝玻璃边框，**底部状态条**上左边是
圆形时钟图标 + 深蓝数字面板「18」，右边是深蓝数字面板「40」+ 圆形雷图标。
整张图就是微软自己画的帮助插图，不是本工程渲染出来的。

同目录还有 `thumbBlue.png` 等缩略图，不影响本改动。

## 2. 最容易踩的坑：helpBoard.png 是 1:1 图，不能乘 SPRITE_SCALE

本工程其余三张图集（blueSheet / greenSheet / otherSheet / minesweeperSheet）
都是**按 2 倍存**的，源矩形统一乘 `SPRITE_SCALE = 2`
（`Theme.ets:16`，见 linux-minesweeper 的 `Theme.h`：*the sheets are stored at
twice logical size*）。

**helpBoard.png 不是。** 它就是 256×192 的原图，1 源像素 = 1 像素。
若沿用 `SpriteAtlas.draw()`（内部 `srcRect[i] * SPRITE_SCALE * pxScale`），
源矩形会变成 512×384 —— 直接裁到图外，画出一片空白。

因此新增了 `SpriteAtlas.drawWhole()`：**源坐标不乘 SPRITE_SCALE**，整张图按
「源像素 × 整数放大倍数」画。`Theme.ets` 里也把源尺寸单列成常量并写明原因：

```ts
export const HELP_BOARD_W: number = 256;
export const HELP_BOARD_H: number = 192;
```

## 3. 图集接入

`SpriteAtlas.ets`：

- 新增实例字段 `helpBoard: image.PixelMap | null`，在 `load()` 里
  `await SpriteAtlas.loadPixelMap(ctx, 'helpBoard.png')` 读入。
- 新增**静态**字段 `static helpBoardSheet: image.PixelMap | null`。
  为什么要静态：帮助对话框的图是在 `WinDialog.ets` 里画的（`GameController`
  那边 lead 正在改，不便动），所以用静态字段把 PixelMap 递过去。全局只有一份
  图集，静态不会出现多份。
- 新增 `static drawWhole(ctx, sheet, srcW, srcH, devX, devY, scale, pxScale)`：
  画一张 1:1 整图。

加载失败时 `helpBoardSheet` 保持 `null`，`drawWhole` 直接返回 —— 帮助框退化成
「只有文字」，不会崩。

## 4. 对话框新尺寸与版式

`WinDialogPainter.helpSpec()` 原来只有 6 行中文说明，尺寸 **320×210**；
现在加上原图，尺寸改成 **584×280**（参考像素）。

单位口径与其它对话框一致：**几何是参考像素**，绘制时乘 `sVp`（vp/参考像素），
字号乘 `sDev`（设备像素/参考像素）。

```
0                                                        584
┌──────────────────────────────────────────────────────────┐ 0
│ 扫雷 帮助                                        [ × ]   │  标题栏 0..29
├──────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐                                │
│  │                      │  目标：把地雷全部标出来，别踩到雷。│
│  │   helpBoard.png      │  左键翻开格子；右键插旗，再右键变问号。│
│  │   256 × 192 原图     │  数字表示周围 8 格里的雷数。        │
│  │   x=16..271          │  数字够了就双击它（和弦），其余邻格会自动翻开。│
│  │   y=37..228          │  开局第一下保证不是雷，周围也会空出一片。│
│  │                      │  双指可以缩放棋盘，单指拖动可以平移。│
│  └──────────────────────┘                                │
│                    ┌──────────────┐                      │
│                    │     确定      │                      │  按钮 241..266
│                    └──────────────┘                      │
└──────────────────────────────────────────────────────────┘ 280
```

| 元素 | 参考像素矩形 | 说明 |
|---|---|---|
| 对话框 | 0,0 – 584,280 | 客户区 x=8..575 / y=29..271 |
| 原图 helpBoard.png | x=16..271, y=37..228 | 256×192，**原尺寸 1:1**，放在客户区左上角内缩 8 px |
| 中文说明（6 行） | x=288 起，行距 22 | 墨迹顶 y=67 / 89 / 111 / 133 / 155 / 177，字号 12 |
| 「确定」按钮 | x=242..341, y=241..266 | 100×25，底部居中（与对话框中心对齐，同 bestSpec 的做法） |
| 右上角关闭 X | x=530..574, y=2..18 | 由 `closeRect()` 算出，随 width 自动右移 |

文字块（y=67..189）与原图（y=37..228）**上下居中**（文字块中心 128，原图中心 133）。

排版自检（12 px 字号实测字宽）：最长的一行「数字够了就双击它（和弦），其余邻格会自动翻开。」
= 276 px → 右边界 564，客户区右缘 576，**不越界**；原图右边界 272，文字左边界 288，
中间留 16 px。

## 5. 缩放与「是不是像素级」

对话框缩放倍数由 `GameController.computeDialogScale()` 给：

```
dialogScale = max(1, min(2, density, (canvasW-32)/width, (canvasH-32)/height))
```

帮助框 width=584 / height=280。目标机（Pura X7 内屏 2210 px 宽、密度 3）：
`min(2, 3, 3.73, 8.74) = 2` → **dialogScale = 2（整数）**。

本实现的取法：

| 项 | 取值 | 理由 |
|---|---|---|
| 放大倍数 k | `max(1, floor(dialogScale))` | **整数**：每个源像素正好占 k 个设备像素 |
| 目标左上角 | 先**取整到设备像素**再换算回 vp | 否则图像落在半个像素上，边缘发虚 |
| 源矩形单位 | vp（`srcW * pxScale`） | API 18+ 的 PixelMap 裁剪矩形默认单位是 vp（本工程既有约定） |
| 目标矩形单位 | vp（`devX / pxScale` 等） | Canvas 坐标是 vp |
| 插值 | `ctx.imageSmoothingEnabled = false`（画完恢复原值） | 最近邻放大，边缘不糊 |

**结论：缩放倍数是整数，图像是像素级的。**
dialogScale = 2 时每个源像素占 2 个设备像素，源图 256×192 → 屏幕 512×384 设备像素。

唯一的例外：窗口很窄时 dialogScale 可能是小数（如 1.4）。此时 k 取下界 1，
放大倍数**仍然是整数**（不会糊），代价是图右侧留白最多 `256 × (ds-1)` 设备像素
（图不会溢出它的位置，留白落在图与文字列之间）。没有选择「小数放大 + 最近邻」，
因为那样每个源像素占的设备像素数会忽宽忽窄，不是真正的像素级。

## 6. 命中区怎么跟随

- **「确定」按钮**：`WinDialogPainter.hitButton()` 直接用 `spec.buttons` 里的
  `x/y/w/h` 乘缩放，helpSpec 里改了坐标，命中区自动跟着改 ✓
- **右上角 X**：`WinDialogPainter.closeRect(spec)` = `[spec.width - 9 - 45, 2, 45, 17]`
  = `[530, 2, 45, 17]`，宽度变了它自动右移到新窗口右缘 ✓（draw 与 hitButton 共用
  这一个函数，画出来的位置和能点到的位置严格一致）
- **对话框整体位置**：`GameController.dialogLayout()` 用 `d.width` / `d.height`
  居中，随新尺寸自动重算 ✓
- **图片本身不需要命中区**（不可点）

## 7. 构建

```
powershell -NoProfile -ExecutionPolicy Bypass -File D:\software\harmony\projects\minesweeper\tools\build.ps1
```

结果：**BUILD SUCCESSFUL in 16 s 764 ms**（无 ERROR）。

HAP：`C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap`

按 lead 要求**没有装到模拟器**（5555 / 5557 留给 lead 做点击测试）。

## 8. 取舍与限制

- **原版是一个独立帮助窗口**，本项目仍然是一个对话框（沿用工程既有做法）。
  原图放左边、中文说明放右边，是为了在对话框里保留原版插图，同时不丢中文说明。
- **原图没有再裁剪**：整张 256×192 原样搬过来，包括它自带的浅蓝窗口边框。
  裁掉边框会让它看起来像「贴纸」，而且会破坏与原版的对应关系。
- **原图里的雷数是「40」，计时是「18」**，是微软插图里的固定内容，不是本局的数据；
  不要把它当成状态条读。
- 图片是**静态**的：不随游戏状态变化（原版帮助窗口里的插图也是静态的）。
- 若 `helpBoard.png` 以后被替换成别的尺寸，记得同步
  `Theme.ets` 里的 `HELP_BOARD_W` / `HELP_BOARD_H`（drawWhole 用它们当源矩形尺寸）。
