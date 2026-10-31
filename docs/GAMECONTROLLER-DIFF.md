# GameController.ets 改动建议（等 lead 合并）

> 这份是**建议**，不是已提交的改动。`GameController.ets` 不在我的写入范围内，
> 所以扫描条「裁在棋盘内」这一条我把几何全部放进了 `Anim.ets`，
> 这里只需要改**画的那一处**。

## 1) 扫描条裁到棋盘矩形内（原版行为）

**位置**：`entry/src/main/ets/common/GameController.ets` 的 `drawScanBar()`（约 625 行）

### 现在（要替换掉的）

```ts
  private drawScanBar(ctx: CanvasRenderingContext2D): void {
    const u = this.unit;
    // 1) 拆雷光束
    for (let i = 0; i < Anim.beams.length; i++) {
      const f = Anim.beamFrame(i);
      if (f < 0) {
        continue;
      }
      const cell = Anim.beams[i].cell;
      const r = Math.floor(cell / this.engine.colCount);
      const c = cell - r * this.engine.colCount;
      const x = this.boardX + c * this.tile + Anim.DISARM_OFFSET[0] * u;
      const y = this.boardY + r * this.tile + Anim.DISARM_OFFSET[1] * u;
      this.atlas.drawLogical(ctx, this.atlas.otherSheet, disarmRectFor(f, this.atlas.boardStyle), x, y, u);
    }
    // 2) 扫描条
    const barY = this.scanBarY();
    if (barY < 0) {
      return;
    }
    const boardW = this.engine.colCount * this.tile;
    const barH = Math.round(62 * u);
    this.atlas.draw(ctx, this.atlas.otherSheet, Anim.SCAN_BAR,
      this.boardX, barY, boardW, barH);
  }
```

### 建议改成

```ts
    // 2) 扫描条（Anim.scanBarRect 已经把矩形裁在棋盘内，并按原版保持长宽比）
    const boardW = this.engine.colCount * this.tile;
    const boardBottom = this.boardY + this.engine.rowCount * this.tile;
    const bar = Anim.scanBarRect(this.boardY, boardBottom, boardW);
    if (bar === null) {
      return;
    }
    this.atlas.draw(ctx, this.atlas.otherSheet,
      [bar[0], bar[1], bar[2], bar[3]],   // 源矩形（已裁到可见的那一段）
      this.boardX, bar[4], bar[5], bar[6]);  // 目标：dy / dw / dh
```

改完之后 `private scanBarY()`（约 1005 行）就没有调用方了，可以删掉，
留着也不影响编译（只是未使用方法）。

### 为什么这么改

原版 `linux-minesweeper` 的扫描条是 `p.setClipRect(m_grid)` **裁在棋盘矩形内**的，
所以扫到顶端时整条消失。我们现在是整条直接画，`p=1` 时条的上沿停在
`boardTop - barH`，也就是**条整个跑到棋盘外面去了**，留在棋盘顶上不走。

2026-11-01 在 5555/5557 上实测到的就是这个现象（`docs/verify/ANIM_win_00/01.jpeg`）：
`ANIM_win_01.jpeg` 里那条蓝白高光条停在棋盘**上沿之外**。

顺带修掉两个问题：
- **高度**：原来 `barH = 62 * u`（9×9、unit=6 时是 372px），跟 275:62 的源比例对不上，
  条被拉扁了。原版是 `barH = grid.width() * src.height() / src.width()`
  （9×9、unit=6 时 boardW=972 → barH≈219px）。
- **结束时机**：`Anim.winEndMs()`（已在 `Anim.ets` 里改好）按最后一束光束算，
  不用原来写死的 5000ms。

## 2) 可选：光束起始时刻改成原版的线性公式

**位置**：`GameController.ets` 里算 `startTimes` 的地方（`startWinSweep()` 附近，约 979 行）

现在的算法和原版在数学上等价（实测差 0.00ms），**不改也能跑**。
但原版是「条扫到第 r 行时那一行开始拆雷」，公式是
`startMs = SWEEP_MS * (rows - r) / (rows + 1)`，
我们是把底部 3 行都钳到 0。若想和原版逐帧一致，可按上面的公式替换。
