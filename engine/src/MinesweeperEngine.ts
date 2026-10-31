/**
 * MinesweeperEngine.ts —— Win7 扫雷逻辑层
 *
 * 纯逻辑，不依赖任何 UI / 平台 API。同一个文件有两个用途：
 *   1) Node 离线测试：node --experimental-transform-types engine/test/engine.test.ts
 *   2) 鸿蒙工程：tools/sync-engine.ps1 复制为 entry/src/main/ets/common/MinesweeperEngine.ets
 *
 * ArkTS 约束（刻意遵守，避免移植期踩坑）：
 *   - 不使用 any / unknown / 索引签名 / 访问修饰符（public/private 都不写）
 *   - 所有成员显式标注类型，对象字面量用 interface 显式定型
 *   - 只用 number / string / boolean / 数组 / 类 / 枚举
 *
 * 行为依据（证据见 docs/SPEC.md）：
 *   - 首点 3×3 无雷（延迟布雷）      Lmy0217 core.h initMineCount()
 *   - 洪泛用 BFS，尊重旗子，问号格打开时清空   linux-minesweeper Board.cpp floodReveal()
 *   - 右键三态 无标记→旗→问号→无标记  同上 toggleMark()
 *   - 和弦：旗数==数字才动作，旗插错则同时引爆并判负  同上 chord()
 *   - 失败展示 / 胜利自动插旗 / 雷数可为负   同上 lose() checkWin()
 *   - 方块状态码沿用原版字节编码   ReversingMinesweeper game.h
 */

/** 标记状态：右键三态 */
export enum Mark {
  None = 0,
  Flag = 1,
  Question = 2
}

/** 局面状态 */
export enum GameState {
  Ready = 0,
  Playing = 1,
  Won = 2,
  Lost = 3
}

/**
 * 方块显示状态码，取值沿用原版（ReversingMinesweeper/game.h）的低 5 位编码。
 * 原版把「是雷 / 已打开」放在 bit7 / bit6，显示状态放 bit4..0；
 * 这里拆成独立字段，显示时用 displayState() 还原同一套语义。
 *
 * 与 game.h 的唯一差异：旗与问号的码值对调。
 *   game.h  ：FLAG = 0x0E、QUESTION_MARK = 0x0D
 *   本文件  ：Flag = 0x0D、Question = 0x0E（与 docs/SPEC.md §4 的表一致）
 * 其余 11 个码值与 game.h 逐一相同。
 * 这个差异只动内部常量，不动行为：渲染层用的是 cell.mark / cell.revealed /
 * cell.exploded / cell.misflagged，displayState() 的码值只有离线测试在用。
 */
export enum BlockState {
  OpenedEmpty = 0x00,
  OpenedOne = 0x01,
  OpenedTwo = 0x02,
  OpenedThree = 0x03,
  OpenedFour = 0x04,
  OpenedFive = 0x05,
  OpenedSix = 0x06,
  OpenedSeven = 0x07,
  OpenedEight = 0x08,
  OpenedQuestion = 0x09,
  Mine = 0x0A,
  Misflag = 0x0B,
  Exploded = 0x0C,
  Flag = 0x0D,
  Question = 0x0E,
  Covered = 0x0F,
  Border = 0x10
}

/** 随机源：可注入，便于测试复现 */
export type RandomSource = () => number;

/** 难度预设 */
export interface DifficultyPreset {
  name: string;
  rows: number;
  cols: number;
  mines: number;
}

export const DIFFICULTY_BEGINNER: DifficultyPreset = { name: 'Beginner', rows: 9, cols: 9, mines: 10 };
export const DIFFICULTY_INTERMEDIATE: DifficultyPreset = { name: 'Intermediate', rows: 16, cols: 16, mines: 40 };
export const DIFFICULTY_ADVANCED: DifficultyPreset = { name: 'Advanced', rows: 16, cols: 30, mines: 99 };

/** 自定义局的面板约束（Win7 对话框的实际取值范围，来源 Lmy0217 Minesweeper.cpp:228） */
export const CUSTOM_MIN_ROWS = 9;
export const CUSTOM_MAX_ROWS = 24;
export const CUSTOM_MIN_COLS = 9;
export const CUSTOM_MAX_COLS = 30;
export const CUSTOM_MIN_MINES = 10;
export const CUSTOM_MAX_MINES = 668;

/** 原版内部数组 BlockArray[27][32]，去掉一圈边框后可玩区域为 25×30 */
export const ENGINE_MAX_ROWS = 24;
export const ENGINE_MAX_COLS = 30;

/** 单个格子 */
export class Cell {
  mine: boolean = false;
  revealed: boolean = false;
  /** 被踩中的那颗雷（失败时红底显示） */
  exploded: boolean = false;
  /** 插错旗的非雷格（失败时叠红叉） */
  misflagged: boolean = false;
  mark: Mark = Mark.None;
  /** 周围雷数，0..8 */
  adjacent: number = 0;

  displayState(): BlockState {
    if (this.exploded) {
      return BlockState.Exploded;
    }
    if (this.misflagged) {
      return BlockState.Misflag;
    }
    if (this.revealed) {
      if (this.mine) {
        return BlockState.Mine;
      }
      if (this.adjacent > 0) {
        return BlockState.OpenedOne + (this.adjacent - 1);
      }
      return BlockState.OpenedEmpty;
    }
    if (this.mark === Mark.Flag) {
      return BlockState.Flag;
    }
    if (this.mark === Mark.Question) {
      return BlockState.Question;
    }
    return BlockState.Covered;
  }
}

/** 一次 reveal 的结果 */
export class RevealOutcome {
  /** 局面是否发生了变化 */
  changed: boolean = false;
  /** 是否踩雷判负 */
  lost: boolean = false;
  /** 本次翻开的格子索引，按 BFS 展开顺序（洪泛动画按这个顺序播放） */
  opened: number[] = [];
}

function mathRandom(): number {
  return Math.random();
}

function clampInt(value: number, min: number, max: number): number {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

/**
 * 扫雷引擎。
 * 说明：字段一律不加访问修饰符，ArkTS 与 TypeScript 都合法。
 */
export class MinesweeperEngine {
  rowCount: number = 0;
  colCount: number = 0;
  /** 总局雷数 */
  mineCount: number = 0;
  /** 已插旗数 */
  flagCount: number = 0;
  /** 已翻开格数 */
  revealedCount: number = 0;
  gameState: GameState = GameState.Ready;
  /** 雷是否已经布下（Win7 是延迟布雷：第一次点击才布） */
  minesPlaced: boolean = false;
  /** 问号标记是否启用（选项里可关，关闭后右键两态） */
  questionMarksAllowed: boolean = true;
  cells: Cell[] = [];
  rng: RandomSource = mathRandom;

  /**
   * 该尺寸下允许的最大雷数。
   * 依据：自定义局上限 668（24 行 × 30 列），反推公式 (rows-1)*(cols-1)+1。
   * 这个公式同时保证剩余空格 >= rows+cols-1，够放首点 3×3 安全区。
   */
  static maxMinesFor(rows: number, cols: number): number {
    const bySize = (rows - 1) * (cols - 1) + 1;
    const byCells = rows * cols - 1;
    return bySize < byCells ? bySize : byCells;
  }

  /**
   * 开新局。rows/cols 允许 1..24 / 1..30（引擎层），
   * 面板层的 9..24 / 9..30 约束由 UI 用 CUSTOM_* 常量校验。
   */
  reset(rows: number, cols: number, mines: number, rng?: RandomSource): void {
    const r = clampInt(rows, 1, ENGINE_MAX_ROWS);
    const c = clampInt(cols, 1, ENGINE_MAX_COLS);
    const maxMines = MinesweeperEngine.maxMinesFor(r, c);
    const m = clampInt(mines, 1, maxMines);

    if (rng === undefined || rng === null) {
      this.rng = mathRandom;
    } else {
      this.rng = rng;
    }

    this.rowCount = r;
    this.colCount = c;
    this.mineCount = m;
    this.flagCount = 0;
    this.revealedCount = 0;
    this.gameState = GameState.Ready;
    this.minesPlaced = false;

    const fresh: Cell[] = [];
    for (let i = 0; i < r * c; i++) {
      fresh.push(new Cell());
    }
    this.cells = fresh;
  }

  /**
   * 同雷场重来一局（保留已布下的雷，只盖回面）。
   * 原版的「新游戏」是重新布雷；这个接口对应「再来一局同布局」。
   */
  restart(): void {
    if (!this.minesPlaced) {
      return;
    }
    for (let i = 0; i < this.cells.length; i++) {
      const cell = this.cells[i];
      cell.revealed = false;
      cell.exploded = false;
      cell.misflagged = false;
      cell.mark = Mark.None;
    }
    this.flagCount = 0;
    this.revealedCount = 0;
    this.gameState = GameState.Ready;
  }

  /** 剩余雷数 = 总局雷数 - 已插旗数，可为负（原版就允许显示负数） */
  minesRemaining(): number {
    return this.mineCount - this.flagCount;
  }

  isOver(): boolean {
    return this.gameState === GameState.Won || this.gameState === GameState.Lost;
  }

  inBounds(row: number, col: number): boolean {
    return row >= 0 && row < this.rowCount && col >= 0 && col < this.colCount;
  }

  cellAt(row: number, col: number): Cell {
    return this.cells[row * this.colCount + col];
  }

  /** 左键开格 */
  reveal(row: number, col: number): RevealOutcome {
    const outcome = new RevealOutcome();
    if (this.isOver() || !this.inBounds(row, col)) {
      return outcome;
    }
    const cell = this.cellAt(row, col);
    if (cell.revealed || cell.mark === Mark.Flag) {
      return outcome;
    }

    if (this.gameState === GameState.Ready) {
      if (!this.minesPlaced) {
        this.placeMines(row, col);
        this.minesPlaced = true;
      }
      this.gameState = GameState.Playing;
    }

    if (cell.mine) {
      cell.exploded = true;
      this.lose();
      outcome.changed = true;
      outcome.lost = true;
      return outcome;
    }

    this.floodReveal(row, col, outcome.opened);
    this.checkWin();
    outcome.changed = true;
    return outcome;
  }

  /** 右键循环标记：无标记 → 旗 → 问号 → 无标记 */
  toggleMark(row: number, col: number): boolean {
    if (this.isOver() || !this.inBounds(row, col)) {
      return false;
    }
    const cell = this.cellAt(row, col);
    if (cell.revealed) {
      return false;
    }
    if (cell.mark === Mark.None) {
      cell.mark = Mark.Flag;
      this.flagCount++;
    } else if (cell.mark === Mark.Flag) {
      this.flagCount--;
      cell.mark = this.questionMarksAllowed ? Mark.Question : Mark.None;
    } else {
      cell.mark = Mark.None;
    }
    return true;
  }

  /**
   * 和弦：在已翻开的数字格上，若周围旗数 == 该数字，打开其余未插旗的邻格。
   * 旗插错时周围所有未正确标记的雷同时引爆，直接判负。
   * 返回 false 表示没有发生任何事（不是数字，或旗数不匹配）。
   */
  chord(row: number, col: number): boolean {
    if (this.gameState !== GameState.Playing || !this.inBounds(row, col)) {
      return false;
    }
    const cell = this.cellAt(row, col);
    if (!cell.revealed || cell.adjacent === 0) {
      return false;
    }

    let flags = 0;
    this.forEachNeighbor(row, col, (r: number, c: number): void => {
      if (this.cellAt(r, c).mark === Mark.Flag) {
        flags++;
      }
    });
    if (flags !== cell.adjacent) {
      return false;
    }

    let exploded = false;
    this.forEachNeighbor(row, col, (r: number, c: number): void => {
      const neighbor = this.cellAt(r, c);
      if (!neighbor.revealed && neighbor.mark !== Mark.Flag && neighbor.mine) {
        neighbor.exploded = true;
        exploded = true;
      }
    });
    if (exploded) {
      this.lose();
      return true;
    }

    const opened: number[] = [];
    this.forEachNeighbor(row, col, (r: number, c: number): void => {
      const neighbor = this.cellAt(r, c);
      if (!neighbor.revealed && neighbor.mark !== Mark.Flag) {
        this.floodReveal(r, c, opened);
      }
    });
    this.checkWin();
    return true;
  }

  /**
   * 仅供测试用：直接指定雷的位置，跳过随机布雷。
   * 传入的是格子索引（row * colCount + col）。
   */
  debugPlaceMines(indices: number[]): void {
    for (let i = 0; i < this.cells.length; i++) {
      this.cells[i].mine = false;
    }
    for (let i = 0; i < indices.length; i++) {
      const idx = indices[i];
      if (idx >= 0 && idx < this.cells.length) {
        this.cells[idx].mine = true;
      }
    }
    this.minesPlaced = true;
    this.recomputeAdjacent();
  }

  /** 重新统计每格周围的雷数 */
  recomputeAdjacent(): void {
    for (let r = 0; r < this.rowCount; r++) {
      for (let c = 0; c < this.colCount; c++) {
        let count = 0;
        this.forEachNeighbor(r, c, (nr: number, nc: number): void => {
          if (this.cellAt(nr, nc).mine) {
            count++;
          }
        });
        this.cellAt(r, c).adjacent = count;
      }
    }
  }

  /**
   * 延迟布雷：Win7 规则，首点及其 3×3 邻域（越界裁剪）内不放雷。
   * Lmy0217 的 core.h 用「首点 ± {0,1,col,col±1}」排除 9 个位置，
   * 但漏了边界判断（角落点击时会误伤对角远处的格子），
   * 这里改成按行列裁剪的 3×3 邻域。
   */
  placeMines(safeRow: number, safeCol: number): void {
    let allowed: number[] = [];
    for (let r = 0; r < this.rowCount; r++) {
      for (let c = 0; c < this.colCount; c++) {
        const dr = r - safeRow;
        const dc = c - safeCol;
        if (Math.abs(dr) <= 1 && Math.abs(dc) <= 1) {
          continue;
        }
        allowed.push(r * this.colCount + c);
      }
    }

    // 极端小棋盘放不下时逐级放宽：3×3 安全区 → 只排除首点。
    // 放宽到哪一级都不能把首点放回候选池——「首点必不是雷」是 SPEC §3.1 的硬约束，
    // 宁可少布几颗雷（计数器同步下调，见本方法末尾），也不能让首点踩雷。
    if (allowed.length < this.mineCount) {
      allowed = [];
      for (let r = 0; r < this.rowCount; r++) {
        for (let c = 0; c < this.colCount; c++) {
          if (r !== safeRow || c !== safeCol) {
            allowed.push(r * this.colCount + c);
          }
        }
      }
    }

    // 无放回地取 mineCount 个格子：对 allowed 做部分 Fisher-Yates 洗牌，取前 mineCount 个。
    // 不用拒绝采样——随机源退化时（比如恒返回 0）拒绝采样会死循环并静默少布雷，
    // 洗牌则保证「随机源多差都恰好布出 mineCount 颗雷」。
    const pool: number[] = allowed.slice();
    const take = Math.min(this.mineCount, pool.length);
    for (let i = 0; i < take; i++) {
      let j = i + Math.floor(this.rng() * (pool.length - i));
      if (j < i) {
        j = i;
      }
      if (j >= pool.length) {
        j = pool.length - 1;
      }
      const swap = pool[i];
      pool[i] = pool[j];
      pool[j] = swap;
    }
    for (let i = 0; i < take; i++) {
      this.cells[pool[i]].mine = true;
    }

    // 候选池装不下时实际布下的雷会少于请求值：计数器必须跟着局面走，
    // 否则剩余雷数与胜负判定都会和棋盘对不上（也判不了胜）。
    this.mineCount = take;

    this.recomputeAdjacent();
  }

  /** 洪泛展开：BFS，尊重旗子，打开问号格时清掉问号 */
  floodReveal(row: number, col: number, out: number[]): void {
    const queue: number[] = [];
    queue.push(row * this.colCount + col);
    let head = 0;
    while (head < queue.length) {
      const idx = queue[head];
      head++;
      const r = Math.floor(idx / this.colCount);
      const c = idx - r * this.colCount;
      const cell = this.cells[idx];
      if (cell.revealed || cell.mark === Mark.Flag) {
        continue;
      }
      cell.revealed = true;
      cell.mark = Mark.None;
      this.revealedCount++;
      out.push(idx);
      if (cell.adjacent !== 0) {
        continue;
      }
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (dr === 0 && dc === 0) {
            continue;
          }
          const nr = r + dr;
          const nc = c + dc;
          if (!this.inBounds(nr, nc)) {
            continue;
          }
          const nIdx = nr * this.colCount + nc;
          if (!this.cells[nIdx].revealed) {
            queue.push(nIdx);
          }
        }
      }
    }
  }

  /** 判负：亮出所有未插旗的雷，错旗打叉 */
  lose(): void {
    this.gameState = GameState.Lost;
    for (let i = 0; i < this.cells.length; i++) {
      const cell = this.cells[i];
      if (cell.mine && cell.mark !== Mark.Flag) {
        cell.revealed = true;
      }
      if (!cell.mine && cell.mark === Mark.Flag) {
        cell.misflagged = true;
      }
    }
  }

  /** 判胜：剩余的雷由程序自动插旗，雷数归零 */
  checkWin(): void {
    if (this.revealedCount !== this.rowCount * this.colCount - this.mineCount) {
      return;
    }
    this.gameState = GameState.Won;
    for (let i = 0; i < this.cells.length; i++) {
      const cell = this.cells[i];
      if (cell.mine) {
        cell.mark = Mark.Flag;
      }
    }
    this.flagCount = this.mineCount;
  }

  /** 遍历 8 邻域（不含自己） */
  forEachNeighbor(row: number, col: number, fn: (r: number, c: number) => void): void {
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) {
          continue;
        }
        const nr = row + dr;
        const nc = col + dc;
        if (this.inBounds(nr, nc)) {
          fn(nr, nc);
        }
      }
    }
  }
}
