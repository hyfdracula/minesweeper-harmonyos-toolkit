/**
 * 引擎离线测试：node --experimental-transform-types engine/test/engine.test.ts
 *
 * 覆盖 Win7 扫雷的全部关键规则，重点是三处最容易移植错的地方：
 *   1) 首点 3×3 无雷（且边界裁剪正确）
 *   2) 和弦的两条分支（旗数不符不动手 / 旗插错直接判负）
 *   3) 胜负后的展示状态（亮雷 / 错旗打叉 / 胜利自动插旗）
 */
import assert from 'node:assert/strict';
import {
  MinesweeperEngine,
  Mark,
  GameState,
  BlockState,
  DIFFICULTY_BEGINNER,
  DIFFICULTY_INTERMEDIATE,
  DIFFICULTY_ADVANCED,
  CUSTOM_MAX_MINES,
  CUSTOM_MAX_ROWS,
  CUSTOM_MAX_COLS,
} from '../src/MinesweeperEngine.ts';

/** 可复现的伪随机源（mulberry32） */
function seededRandom(seed: number): () => number {
  let a = seed >>> 0;
  return (): number => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

let passed = 0;
let failed = 0;

function test(name: string, fn: () => void): void {
  try {
    fn();
    passed++;
    console.log(`  ok   ${name}`);
  } catch (err) {
    failed++;
    console.log(`  FAIL ${name}`);
    console.log(`       ${err instanceof Error ? err.message : String(err)}`);
  }
}

function countMines(engine: MinesweeperEngine): number {
  let n = 0;
  for (let i = 0; i < engine.cells.length; i++) {
    if (engine.cells[i].mine) {
      n++;
    }
  }
  return n;
}

/**
 * 洪泛深度（独立于引擎实现的参考算法）。
 * 洪泛只能从 0 格继续往外扩，所以「层次」= 在「0 格 → 它的 8 邻域」这张图上
 * 从首点出发的 BFS 深度。引擎的展开顺序应当与这个深度单调一致（SPEC §3.2）。
 */
function floodDepths(engine: MinesweeperEngine, row: number, col: number): number[] {
  const depths: number[] = [];
  const visited: boolean[] = [];
  for (let i = 0; i < engine.cells.length; i++) {
    depths.push(-1);
    visited.push(false);
  }
  const start = row * engine.colCount + col;
  const queue: number[] = [start];
  visited[start] = true;
  depths[start] = 0;
  let head = 0;
  while (head < queue.length) {
    const idx = queue[head];
    head++;
    const r = Math.floor(idx / engine.colCount);
    const c = idx - r * engine.colCount;
    if (engine.cellAt(r, c).adjacent !== 0) {
      continue; // 只有 0 格能继续扩展
    }
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) {
          continue;
        }
        const nr = r + dr;
        const nc = c + dc;
        if (!engine.inBounds(nr, nc)) {
          continue;
        }
        const nIdx = nr * engine.colCount + nc;
        if (visited[nIdx]) {
          continue;
        }
        visited[nIdx] = true;
        depths[nIdx] = depths[idx] + 1;
        queue.push(nIdx);
      }
    }
  }
  return depths;
}

console.log('minesweeper engine tests\n');

// ---------------------------------------------------------------- 基础尺寸

test('难度预设与 Win7 一致', () => {
  assert.equal(DIFFICULTY_BEGINNER.rows, 9);
  assert.equal(DIFFICULTY_BEGINNER.cols, 9);
  assert.equal(DIFFICULTY_BEGINNER.mines, 10);
  assert.equal(DIFFICULTY_INTERMEDIATE.rows, 16);
  assert.equal(DIFFICULTY_INTERMEDIATE.cols, 16);
  assert.equal(DIFFICULTY_INTERMEDIATE.mines, 40);
  assert.equal(DIFFICULTY_ADVANCED.rows, 16);
  assert.equal(DIFFICULTY_ADVANCED.cols, 30);
  assert.equal(DIFFICULTY_ADVANCED.mines, 99);
});

test('自定义面板上限：24 行 30 列 668 雷', () => {
  assert.equal(CUSTOM_MAX_ROWS, 24);
  assert.equal(CUSTOM_MAX_COLS, 30);
  assert.equal(CUSTOM_MAX_MINES, 668);
  assert.equal(MinesweeperEngine.maxMinesFor(24, 30), 668);
});

test('reset 建立正确尺寸并处于 Ready', () => {
  const e = new MinesweeperEngine();
  e.reset(16, 30, 99);
  assert.equal(e.rowCount, 16);
  assert.equal(e.colCount, 30);
  assert.equal(e.cells.length, 480);
  assert.equal(e.mineCount, 99);
  assert.equal(e.gameState, GameState.Ready);
  assert.equal(e.minesPlaced, false);
  assert.equal(e.revealedCount, 0);
  assert.equal(e.flagCount, 0);
  assert.equal(e.minesRemaining(), 99);
});

test('雷数被夹到该尺寸允许的上限', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 9999);
  assert.equal(e.mineCount, MinesweeperEngine.maxMinesFor(9, 9));
  assert.ok(countMines(e) === 0, 'reset 后不应立即布雷');
});

// ---------------------------------------------------------------- 首点 3×3

test('首点 3×3 无雷：9×9 全部 81 个起点 × 3 组种子', () => {
  const e = new MinesweeperEngine();
  for (let seed = 1; seed <= 3; seed++) {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        e.reset(9, 9, 10, seededRandom(seed * 10000 + r * 10 + c));
        e.reveal(r, c);
        assert.equal(e.cellAt(r, c).mine, false, `首点 (${r},${c}) 本身是雷`);
        for (let dr = -1; dr <= 1; dr++) {
          for (let dc = -1; dc <= 1; dc++) {
            const nr = r + dr;
            const nc = c + dc;
            if (nr < 0 || nr >= 9 || nc < 0 || nc >= 9) {
              continue;
            }
            assert.equal(
              e.cellAt(nr, nc).mine,
              false,
              `首点 (${r},${c}) 的邻格 (${nr},${nc}) 上有雷`,
            );
          }
        }
        assert.equal(countMines(e), 10, '雷总数应为 10');
        assert.equal(e.gameState, GameState.Playing);
      }
    }
  }
});

test('首点必定开出空地（角落至少 4 格，中心至少 9 格）', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(7));
  e.reveal(0, 0);
  assert.ok(e.revealedCount >= 4, `角落首点只开了 ${e.revealedCount} 格`);

  const e2 = new MinesweeperEngine();
  e2.reset(9, 9, 10, seededRandom(7));
  e2.reveal(4, 4);
  assert.ok(e2.revealedCount >= 9, `中心首点只开了 ${e2.revealedCount} 格`);
});

test('首点安全区在边缘按行列裁剪，不会误伤远处的格子', () => {
  // 9×9，首点 (0,8)：3×3 裁剪后只有 6 格安全。
  // Lmy0217 的 core.h 缺边界判断，会把 (0,0) 也误排除。
  const e = new MinesweeperEngine();
  let sawMineAt00 = false;
  for (let seed = 1; seed <= 40 && !sawMineAt00; seed++) {
    e.reset(9, 9, 40, seededRandom(seed));
    e.reveal(0, 8);
    if (e.cellAt(0, 0).mine) {
      sawMineAt00 = true;
    }
  }
  assert.ok(sawMineAt00, '远处格子 (0,0) 40 次都没能布到雷，说明安全区算错了');
});

test('首点安全区：三个难度 × 全部起点 × 3 组种子都无雷', () => {
  // SPEC §3.1：首点及其周围 8 格（越界裁剪）内不放雷
  const presets: number[][] = [
    [9, 9, 10],
    [16, 16, 40],
    [16, 30, 99],
  ];
  for (const preset of presets) {
    const rows = preset[0];
    const cols = preset[1];
    const mines = preset[2];
    const e = new MinesweeperEngine();
    for (let seed = 1; seed <= 3; seed++) {
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          e.reset(rows, cols, mines, seededRandom(seed * 100003 + r * 101 + c));
          const outcome = e.reveal(r, c);
          assert.equal(outcome.lost, false, `${rows}x${cols} 首点 (${r},${c}) 踩雷`);
          const r0 = Math.max(0, r - 1);
          const r1 = Math.min(rows - 1, r + 1);
          const c0 = Math.max(0, c - 1);
          const c1 = Math.min(cols - 1, c + 1);
          for (let nr = r0; nr <= r1; nr++) {
            for (let nc = c0; nc <= c1; nc++) {
              assert.equal(
                e.cellAt(nr, nc).mine,
                false,
                `${rows}x${cols} 首点 (${r},${c}) 的邻格 (${nr},${nc}) 上有雷`,
              );
            }
          }
          assert.equal(countMines(e), mines, `${rows}x${cols} 首点 (${r},${c}) 的雷数不对`);
        }
      }
    }
  }
});

test('首点必开空地：安全区整片都被翻开（9×9 全起点穷举）', () => {
  // SPEC §3.1：安全区整片无雷 ⇒ 首点周围雷数为 0 ⇒ 洪泛至少打开整个安全区。
  // 角落安全区 4 格 ⇒ 角落首点至少开 4 格；内部安全区 9 格 ⇒ 至少开 9 格。
  const e = new MinesweeperEngine();
  for (let seed = 1; seed <= 5; seed++) {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        e.reset(9, 9, 10, seededRandom(seed * 7919 + r * 31 + c));
        e.reveal(r, c);
        const zoneRows = Math.min(8, r + 1) - Math.max(0, r - 1) + 1;
        const zoneCols = Math.min(8, c + 1) - Math.max(0, c - 1) + 1;
        const zone = zoneRows * zoneCols;
        assert.ok(
          e.revealedCount >= zone,
          `首点 (${r},${c}) 只开 ${e.revealedCount} 格，安全区有 ${zone} 格`,
        );
        const isCorner = (r === 0 || r === 8) && (c === 0 || c === 8);
        if (isCorner) {
          assert.ok(e.revealedCount >= 4, `角落首点 (${r},${c}) 只开 ${e.revealedCount} 格`);
        }
        if (r >= 1 && r <= 7 && c >= 1 && c <= 7) {
          assert.ok(e.revealedCount >= 9, `中心首点 (${r},${c}) 只开 ${e.revealedCount} 格`);
        }
      }
    }
  }
});

test('退化到「只排除首点」时首点仍不是雷，计数器与棋盘一致', () => {
  // SPEC §3.1 的硬约束：首点必不是雷。雷数被顶到放不下时，
  // 只能少布雷（计数器跟着下调），绝不能把雷布回首点。
  const e = new MinesweeperEngine();
  e.reset(3, 3, 5);
  e.mineCount = 9; // 人为把雷数顶到整盘大小（面板不会这么干，引擎层要自洽）
  e.placeMines(1, 1);
  assert.equal(e.cellAt(1, 1).mine, false, '首点被布上了雷');
  assert.equal(countMines(e), 8, '3×3 盘扣掉首点最多只能放 8 颗雷');
  assert.equal(e.mineCount, 8, '计数器必须与棋盘上的实际雷数一致');
});

test('雷数被顶到放不下时，首点也不会踩雷', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 5);
  e.mineCount = 9;
  e.minesPlaced = false;
  const outcome = e.reveal(1, 1);
  assert.equal(outcome.lost, false, '首点踩雷');
  assert.equal(e.cellAt(1, 1).mine, false);
  assert.equal(countMines(e), e.mineCount, '计数器与实际雷数不一致');
});

// ---------------------------------------------------------------- 标记

test('右键三态：无标记 → 旗 → 问号 → 无标记', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  assert.equal(e.toggleMark(4, 4), true);
  assert.equal(e.cellAt(4, 4).mark, Mark.Flag);
  assert.equal(e.flagCount, 1, '插旗时 flagCount 加一');
  assert.equal(e.minesRemaining(), 9, '插一面旗，剩余雷数减一');
  assert.equal(e.toggleMark(4, 4), true);
  assert.equal(e.cellAt(4, 4).mark, Mark.Question);
  assert.equal(e.flagCount, 0, '旗变问号时 flagCount 减一');
  assert.equal(e.minesRemaining(), 10, '旗取消成问号，旗数归零，剩余雷数回到 10');
  assert.equal(e.toggleMark(4, 4), true);
  assert.equal(e.cellAt(4, 4).mark, Mark.None);
  assert.equal(e.minesRemaining(), 10);
});

test('关闭问号后右键只有两态', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  e.questionMarksAllowed = false;
  e.toggleMark(4, 4);
  assert.equal(e.cellAt(4, 4).mark, Mark.Flag);
  e.toggleMark(4, 4);
  assert.equal(e.cellAt(4, 4).mark, Mark.None);
});

test('剩余雷数可以为负', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 16, 10);
  for (let i = 0; i < 12; i++) {
    assert.equal(e.toggleMark(0, i), true);
  }
  assert.equal(e.flagCount, 12);
  assert.equal(e.minesRemaining(), -2, '插了比雷数还多的旗，剩余数应为负');
});

test('已翻开的格子不能插旗，插旗的格子不能翻开', () => {
  // 分成两个盘做，避免第一个盘的洪泛把第二个盘要用到的格子也开掉
  const a = new MinesweeperEngine();
  a.reset(9, 9, 10, seededRandom(3));
  a.reveal(4, 4);
  assert.equal(a.cellAt(4, 4).revealed, true);
  assert.equal(a.toggleMark(4, 4), false, '已翻开的格子不应能插旗');

  const b = new MinesweeperEngine();
  b.reset(9, 9, 10, seededRandom(3));
  b.toggleMark(0, 0);
  assert.equal(b.cellAt(0, 0).mark, Mark.Flag);
  const outcome = b.reveal(0, 0);
  assert.equal(outcome.changed, false, '插旗的格子不应能被翻开');
  assert.equal(b.cellAt(0, 0).mark, Mark.Flag);
});

// ---------------------------------------------------------------- 洪泛

test('洪泛不自动翻开插了旗的格子', () => {
  const e = new MinesweeperEngine();
  e.reset(5, 5, 1);
  e.debugPlaceMines([0]); // 雷在 (0,0)
  e.toggleMark(0, 0);
  e.reveal(2, 2);
  assert.equal(e.cellAt(0, 0).mark, Mark.Flag);
  assert.equal(e.cellAt(0, 0).revealed, false);
});

test('洪泛按 BFS 顺序展开，第一个就是被点的格子', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(11));
  const outcome = e.reveal(4, 4);
  assert.ok(outcome.opened.length > 1, '应该展开了一片');
  assert.equal(outcome.opened[0], 4 * 9 + 4, '展开顺序第一个应是点击点');
});

test('问号格被翻开时清成空白', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  e.debugPlaceMines([]);
  e.toggleMark(4, 4);
  e.toggleMark(4, 4);
  assert.equal(e.cellAt(4, 4).mark, Mark.Question);
  e.reveal(4, 4);
  assert.equal(e.cellAt(4, 4).mark, Mark.None);
  assert.equal(e.cellAt(4, 4).revealed, true);
});

test('洪泛按 BFS 顺序展开（0 格图上的层次单调不降）', () => {
  // SPEC §3.2：展开顺序按 BFS，UI 照此播放扩散动画。
  const e = new MinesweeperEngine();
  e.reset(16, 16, 40, seededRandom(11));
  const outcome = e.reveal(8, 8);
  assert.ok(outcome.opened.length > 20, '这片空地应该足够大');
  const depths = floodDepths(e, 8, 8);
  let last = -1;
  for (const idx of outcome.opened) {
    const d = depths[idx];
    assert.ok(d >= 0, `格子 ${idx} 不在洪泛可达集合里`);
    assert.ok(d >= last, `展开顺序不是 BFS：层次 ${last} 之后出现了 ${d}`);
    last = d;
  }
  let reachable = 0;
  for (let i = 0; i < depths.length; i++) {
    if (depths[i] >= 0) {
      reachable++;
    }
  }
  assert.equal(outcome.opened.length, reachable, '展开的格子数与参考 BFS 不一致');
});

test('洪泛不穿过插旗格（旗子阻断扩展）', () => {
  // 原版 ShowBlockValue 遇到旗子直接 return，扩展不会从旗子后面穿过去。
  const plain = new MinesweeperEngine();
  plain.reset(5, 5, 1);
  plain.debugPlaceMines([24]); // 雷在 (4,4)
  plain.reveal(0, 0);

  const flagged = new MinesweeperEngine();
  flagged.reset(5, 5, 1);
  flagged.debugPlaceMines([24]);
  flagged.toggleMark(2, 2);
  flagged.reveal(0, 0);

  assert.equal(flagged.cellAt(2, 2).revealed, false, '插旗的格子被洪泛翻开了');
  assert.equal(flagged.cellAt(2, 2).mark, Mark.Flag);
  assert.equal(
    flagged.revealedCount,
    plain.revealedCount - 1,
    '有旗时展开的格子应当恰好少一个（旗子挡住了那一格）',
  );
});

// ---------------------------------------------------------------- 和弦

test('和弦：旗数与数字不符时不动手', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0);
  assert.equal(e.cellAt(0, 0).adjacent, 1);
  assert.equal(e.chord(0, 0), false, '没插旗时和弦不应生效');
  assert.equal(e.gameState, GameState.Playing);
});

test('和弦：旗数吻合时翻开其余邻格', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0);
  e.toggleMark(1, 1); // 把真正的雷插上旗
  assert.equal(e.chord(0, 0), true);
  assert.equal(e.cellAt(1, 0).revealed, true, '其余邻格应被翻开');
  assert.equal(e.cellAt(1, 1).revealed, false, '旗子不能被和弦翻开');
  assert.equal(e.gameState, GameState.Playing);
});

test('和弦：旗插错时周围未标雷同时引爆并判负', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0);
  e.toggleMark(0, 1); // 插错旗
  assert.equal(e.chord(0, 0), true);
  assert.equal(e.gameState, GameState.Lost);
  assert.equal(e.cellAt(1, 1).exploded, true);
});

test('和弦不能用在空白格上', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]);
  e.reveal(0, 0);
  assert.equal(e.chord(0, 0), false, '数字为 0 的格子不能和弦');
});

test('和弦不能用在没翻开的格子上', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0); // (0,0) 邻着雷 → 数字 1
  e.toggleMark(1, 1); // 正确的旗
  // (1,0) 还没翻开（它也是数字 1），对它和弦无效
  assert.equal(e.chord(1, 0), false, '没翻开的格子不能和弦');
  assert.equal(e.gameState, GameState.Playing);
  assert.equal(e.cellAt(1, 0).revealed, false);
  assert.equal(e.cellAt(0, 1).revealed, false);
});

test('和弦：旗数比数字多时不动手', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0); // (0,0) 邻着雷 → 数字 1
  e.toggleMark(1, 1); // 正确的旗
  e.toggleMark(1, 0); // 邻格多插一面 → 旗数 2 > 数字 1
  assert.equal(e.chord(0, 0), false, '旗数比数字多时不应动手');
  assert.equal(e.cellAt(0, 1).revealed, false);
  assert.equal(e.gameState, GameState.Playing);
});

test('和弦：旗插错时未标雷同时引爆（红底），别的雷亮黑雷，错旗打叉', () => {
  const e = new MinesweeperEngine();
  e.reset(4, 4, 2);
  e.debugPlaceMines([5, 15]); // (1,1) 与 (3,3)
  e.reveal(0, 0); // (0,0) 邻着 (1,1) 的雷 → 数字 1
  e.toggleMark(0, 1); // 插错的旗（非雷格）
  assert.equal(e.chord(0, 0), true);
  assert.equal(e.gameState, GameState.Lost);
  assert.equal(e.cellAt(1, 1).exploded, true, '未标雷应同时引爆');
  assert.equal(e.cellAt(1, 1).displayState(), BlockState.Exploded);
  assert.equal(e.cellAt(3, 3).revealed, true, '别的雷应被亮出来');
  assert.equal(e.cellAt(3, 3).exploded, false);
  assert.equal(e.cellAt(3, 3).displayState(), BlockState.Mine);
  assert.equal(e.cellAt(0, 1).misflagged, true, '错旗应打叉');
  assert.equal(e.cellAt(0, 1).displayState(), BlockState.Misflag);
});

test('和弦：问号格被翻开时清空标记', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]); // 雷在中心
  e.reveal(0, 0); // (0,0) 邻着雷 → 数字 1
  e.toggleMark(1, 1); // 正确的旗
  e.toggleMark(0, 1); // 无标记 → 旗
  e.toggleMark(0, 1); // 旗 → 问号
  assert.equal(e.cellAt(0, 1).mark, Mark.Question);
  assert.equal(e.chord(0, 0), true);
  assert.equal(e.cellAt(0, 1).revealed, true);
  assert.equal(e.cellAt(0, 1).mark, Mark.None, '问号格被翻开时标记应清空');
});

// ---------------------------------------------------------------- 胜负

test('踩雷判负：亮出所有未插旗的雷，错旗打叉', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 2);
  e.debugPlaceMines([4, 8]);
  e.toggleMark(0, 0); // 插错的旗（非雷格）
  e.toggleMark(1, 1); // (1,1) 是雷，插对的旗
  const outcome = e.reveal(0, 1);
  // (0,1) 紧邻 (1,1) 的雷，所以 (0,1) 不是雷，安全
  assert.equal(outcome.lost, false);

  const e2 = new MinesweeperEngine();
  e2.reset(3, 3, 2);
  e2.debugPlaceMines([4, 8]);
  e2.toggleMark(0, 0); // 错旗
  const lost = e2.reveal(1, 1); // 踩到 (1,1) 的雷
  assert.equal(lost.lost, true);
  assert.equal(e2.gameState, GameState.Lost);
  assert.equal(e2.cellAt(1, 1).exploded, true);
  assert.equal(e2.cellAt(2, 2).revealed, true, '另一颗雷应被亮出来');
  assert.equal(e2.cellAt(2, 2).displayState(), BlockState.Mine);
  assert.equal(e2.cellAt(0, 0).misflagged, true, '错旗应打叉');
  assert.equal(e2.cellAt(0, 0).displayState(), BlockState.Misflag);
});

test('胜利：剩余的雷由程序自动插旗，雷数归零', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]);
  e.reveal(0, 0);
  // 翻开全部非雷格
  const order: number[][] = [
    [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2], [0, 0],
  ];
  for (let i = 0; i < order.length; i++) {
    e.reveal(order[i][0], order[i][1]);
  }
  assert.equal(e.gameState, GameState.Won);
  assert.equal(e.cellAt(1, 1).mark, Mark.Flag, '胜利后雷应自动插旗');
  assert.equal(e.minesRemaining(), 0);
  assert.equal(e.flagCount, e.mineCount);
});

test('判负：插对的雷保持旗不翻开，旗数与剩余雷数不变', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 2);
  e.debugPlaceMines([4, 8]); // (1,1) 与 (2,2)
  e.toggleMark(1, 1); // 插对的旗
  e.toggleMark(0, 0); // 插错的旗
  assert.equal(e.flagCount, 2);
  const remainingBefore = e.minesRemaining();
  const outcome = e.reveal(2, 2); // 踩到 (2,2) 的雷
  assert.equal(outcome.lost, true);
  assert.equal(e.cellAt(1, 1).revealed, false, '插对的雷不该被翻开');
  assert.equal(e.cellAt(1, 1).mark, Mark.Flag);
  assert.equal(e.cellAt(1, 1).displayState(), BlockState.Flag, '插对的雷仍显示为旗');
  assert.equal(e.flagCount, 2, '判负后旗数不应变化');
  assert.equal(e.minesRemaining(), remainingBefore, '判负后剩余雷数不应变化');
});

test('终局后所有操作都无效', () => {
  const e = new MinesweeperEngine();
  e.reset(3, 3, 1);
  e.debugPlaceMines([4]);
  e.reveal(0, 0);
  const order: number[][] = [[0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]];
  for (let i = 0; i < order.length; i++) {
    e.reveal(order[i][0], order[i][1]);
  }
  assert.equal(e.gameState, GameState.Won);
  assert.equal(e.reveal(0, 0).changed, false);
  assert.equal(e.toggleMark(0, 1), false);
  assert.equal(e.chord(0, 0), false);
  assert.equal(e.gameState, GameState.Won);
  assert.equal(e.minesRemaining(), 0);
});

test('同雷场重来：盖回面但雷不变', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(5));
  e.reveal(4, 4);
  e.restart();
  assert.equal(e.gameState, GameState.Ready);
  assert.equal(e.revealedCount, 0);
  assert.equal(e.flagCount, 0);
  assert.equal(e.minesPlaced, true, '重来不应重新布雷');
  assert.equal(countMines(e), 10);
});

// ---------------------------------------------------------------- 边界

test('退化随机源（恒返回同一个值）也必须布够雷数', () => {
  // 拒绝采样在这种随机源下会死循环并少布雷，导致棋盘永远赢不了
  for (const constant of [0, 0.5, 0.999999]) {
    const e = new MinesweeperEngine();
    e.reset(9, 9, 10, (): number => constant);
    e.reveal(4, 4);
    assert.equal(countMines(e), 10, `随机源恒为 ${constant} 时只布了 ${countMines(e)} 颗雷`);
  }
});

test('安全区放不下时逐级放宽，但雷数仍布够', () => {
  // 3×3 盘、首点在中心：3×3 安全区覆盖整盘，放不下 5 颗雷，
  // 引擎应退化为「只排除首点」，并且照样布够 5 颗
  const e = new MinesweeperEngine();
  e.reset(3, 3, 5);
  assert.equal(e.mineCount, 5);
  e.reveal(1, 1);
  assert.equal(countMines(e), 5, '应该布够 5 颗雷');
  assert.equal(e.cellAt(1, 1).mine, false, '首点本身不能是雷');
});

test('1×1 极端棋盘不会死循环', () => {
  const e = new MinesweeperEngine();
  e.reset(1, 1, 1, seededRandom(1));
  const outcome = e.reveal(0, 0);
  assert.ok(outcome.lost || outcome.opened.length >= 0);
  assert.equal(e.cells.length, 1);
});

test('1×1 / 1×2 极端棋盘：首点不踩雷、结果自洽', () => {
  const one = new MinesweeperEngine();
  one.reset(1, 1, 1, seededRandom(1));
  assert.equal(one.mineCount, 0, '1×1 棋盘放不下雷');
  const outOne = one.reveal(0, 0);
  assert.equal(outOne.lost, false, '1×1 首点不能踩雷');
  assert.equal(one.gameState, GameState.Won, '1×1 无雷盘翻开即胜');
  assert.equal(one.minesRemaining(), 0);

  const two = new MinesweeperEngine();
  two.reset(1, 2, 1, seededRandom(2));
  const outTwo = two.reveal(0, 0);
  assert.equal(outTwo.lost, false, '1×2 首点不能踩雷');
  assert.equal(two.gameState, GameState.Won);
  assert.equal(two.minesRemaining(), 0);
  assert.equal(countMines(two), two.mineCount);
});

test('越界操作被安全忽略', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  assert.equal(e.reveal(-1, 0).changed, false);
  assert.equal(e.reveal(0, 99).changed, false);
  assert.equal(e.toggleMark(-1, -1), false);
  assert.equal(e.chord(99, 99), false);
});

test('越界操作既不改局面也不开局', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  const snapshot = (): string =>
    e.cells
      .map((c) => `${c.revealed ? 1 : 0}${c.mark}${c.exploded ? 1 : 0}${c.mine ? 1 : 0}`)
      .join('');
  const before = snapshot();
  e.reveal(-1, 0);
  e.reveal(0, -1);
  e.reveal(9, 0);
  e.reveal(0, 9);
  e.toggleMark(-1, 5);
  e.toggleMark(0, 99);
  e.chord(-1, -1);
  e.chord(99, 99);
  assert.equal(snapshot(), before, '越界操作改变了棋盘');
  assert.equal(e.gameState, GameState.Ready, '越界操作不该开局');
  assert.equal(e.minesPlaced, false, '越界操作不该触发布雷');
});

test('方块状态码与 SPEC §4 的表一致', () => {
  // SPEC §4：0x00 空格 / 0x01-0x08 数字 / 0x09 打开的问号 / 0x0A 黑雷
  // 0x0B 红叉错旗 / 0x0C 红底雷 / 0x0D 旗 / 0x0E 问号 / 0x0F 未打开 / 0x10 边框
  // 注意：旗与问号的码值与原版 game.h（FLAG=0x0E、QUESTION_MARK=0x0D）是对调的，
  // 这里以 SPEC §4 为准，其余码值与 game.h 逐一相同。
  assert.equal(BlockState.OpenedEmpty, 0x00);
  assert.equal(BlockState.OpenedOne, 0x01);
  assert.equal(BlockState.OpenedEight, 0x08);
  assert.equal(BlockState.OpenedQuestion, 0x09);
  assert.equal(BlockState.Mine, 0x0A);
  assert.equal(BlockState.Misflag, 0x0B);
  assert.equal(BlockState.Exploded, 0x0C);
  assert.equal(BlockState.Flag, 0x0D);
  assert.equal(BlockState.Question, 0x0E);
  assert.equal(BlockState.Covered, 0x0F);
  assert.equal(BlockState.Border, 0x10);
});

test('全部格子翻开即胜利（无雷盘）', () => {
  const e = new MinesweeperEngine();
  e.reset(2, 2, 1);
  e.debugPlaceMines([]);
  e.mineCount = 0;
  e.reveal(0, 0);
  e.reveal(0, 1);
  e.reveal(1, 0);
  e.reveal(1, 1);
  assert.equal(e.gameState, GameState.Won);
});

// ================================================================ 引擎一致性补测
// 2026-11-01：逐条核对 SPEC §3.1–§3.7 写下的真 Win7 行为，规则清单见
// docs/ENGINE-PARITY.md。下面的用例覆盖原 41 条没盯住的分支。

/** 造一个确定局面：指定尺寸与雷的位置（格子索引），跳过随机布雷 */
function scenario(rows: number, cols: number, mineIdx: number[]): MinesweeperEngine {
  const e = new MinesweeperEngine();
  e.reset(rows, cols, Math.max(1, mineIdx.length), seededRandom(7));
  e.debugPlaceMines(mineIdx);
  return e;
}

// ---------------------------------------------------------------- 规则 1 首点安全

test('首点：右键先插旗的格子不能当首点，也不布雷不开局', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(11));
  e.toggleMark(4, 4);
  const out = e.reveal(4, 4);
  assert.equal(out.changed, false);
  assert.equal(e.gameState, GameState.Ready);
  assert.equal(e.minesPlaced, false);
  assert.equal(countMines(e), 0);
  assert.equal(e.cellAt(4, 4).mark, Mark.Flag);
  // 换一格作为真正的首点：正常布雷并开局
  const out2 = e.reveal(0, 0);
  assert.equal(out2.changed, true);
  assert.equal(e.gameState, GameState.Playing);
  assert.equal(e.minesPlaced, true);
  assert.equal(countMines(e), e.mineCount);
  assert.equal(e.cellAt(0, 0).mine, false);
});

test('首点 3×3 安全区在四条边中：安全区是 3×2 六格', () => {
  const seeds = [1, 2, 3];
  for (const seed of seeds) {
    const e = new MinesweeperEngine();
    e.reset(9, 9, 10, seededRandom(seed));
    e.placeMines(0, 4);
    for (let r = 0; r <= 1; r++) {
      for (let c = 3; c <= 5; c++) {
        assert.equal(e.cellAt(r, c).mine, false, `种子 ${seed} 安全区 (${r},${c}) 有雷`);
      }
    }
    // 安全区外允许有雷
    let outside = 0;
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (r >= 0 && r <= 1 && c >= 3 && c <= 5) {
          continue;
        }
        if (e.cellAt(r, c).mine) {
          outside++;
        }
      }
    }
    assert.equal(outside, e.mineCount);
  }
});

test('首点 3×3 安全区在四个角：安全区是 2×2 四格', () => {
  const corners = [[0, 0], [0, 8], [8, 0], [8, 8]];
  for (const corner of corners) {
    const e = new MinesweeperEngine();
    e.reset(9, 9, 10, seededRandom(21));
    e.placeMines(corner[0], corner[1]);
    for (let r = corner[0] - 1; r <= corner[0] + 1; r++) {
      for (let c = corner[1] - 1; c <= corner[1] + 1; c++) {
        if (r < 0 || r > 8 || c < 0 || c > 8) {
          continue;
        }
        assert.equal(e.cellAt(r, c).mine, false, `角 (${corner}) 安全区 (${r},${c}) 有雷`);
      }
    }
  }
});

// ---------------------------------------------------------------- 规则 2 和弦

test('和弦：旗数比数字少时不动手，周围格子保持原状', () => {
  // 3×3，雷在 (0,1) 与 (1,0)，中心 (1,1) 的数字是 2
  const e = scenario(3, 3, [1, 3]);
  e.reveal(1, 1);
  assert.equal(e.cellAt(1, 1).adjacent, 2);
  e.toggleMark(0, 1); // 只插一面旗，旗数 1 < 数字 2
  const before = e.revealedCount;
  assert.equal(e.chord(1, 1), false);
  assert.equal(e.revealedCount, before);
  assert.equal(e.cellAt(0, 0).revealed, false);
  assert.equal(e.gameState, GameState.Playing);
});

test('和弦：旗数比数字多时也不动手', () => {
  const e = scenario(3, 3, [1, 3]);
  e.reveal(1, 1);
  e.toggleMark(0, 1);
  e.toggleMark(1, 0);
  e.toggleMark(2, 2); // 多插一面旗（2,2 是安全格），旗数 3 > 数字 2
  const before = e.revealedCount;
  assert.equal(e.chord(1, 1), false);
  assert.equal(e.revealedCount, before);
});

test('和弦：旗数吻合时翻开周围未开格，并在翻开最后一批非雷格时立刻判胜', () => {
  const e = scenario(3, 3, [1, 3]);
  e.reveal(1, 1);
  e.toggleMark(0, 1);
  e.toggleMark(1, 0);
  assert.equal(e.chord(1, 1), true);
  // 周围 6 格全开，中心早就开着 → 7 个非雷格全开
  assert.equal(e.revealedCount, 7);
  assert.equal(e.gameState, GameState.Won);
  assert.equal(e.minesRemaining(), 0);
});

test('和弦：旗数吻合但有未标雷时判负，那颗雷是红底，别的雷亮黑雷', () => {
  // 雷在 (0,1) 与 (1,0)；旗插在 (1,0)（雷）与 (2,2)（安全格）上，旗数 2 = 数字 2
  const e = scenario(3, 3, [1, 3]);
  e.reveal(1, 1);
  e.toggleMark(1, 0);
  e.toggleMark(2, 2);
  assert.equal(e.chord(1, 1), true);
  assert.equal(e.gameState, GameState.Lost);
  assert.equal(e.cellAt(0, 1).exploded, true);
  assert.equal(e.cellAt(0, 1).revealed, true);
  assert.equal(e.cellAt(1, 0).mark, Mark.Flag); // 插对的雷保持旗
  assert.equal(e.cellAt(2, 2).misflagged, true); // 插错的旗打叉
});

test('和弦：旗数吻合时未插旗的邻格被翻开，已插旗的格不被翻开', () => {
  // 雷在 (0,1) 与 (1,0)；中心 (1,1) 数字 2；两面旗都插在雷上
  const e = scenario(3, 3, [1, 3]);
  e.reveal(1, 1);
  e.toggleMark(0, 1);
  e.toggleMark(1, 0);
  assert.equal(e.chord(1, 1), true);
  assert.equal(e.cellAt(0, 1).revealed, false); // 插旗的格不翻开
  assert.equal(e.cellAt(1, 0).revealed, false);
  assert.equal(e.cellAt(0, 0).revealed, true);
  assert.equal(e.cellAt(2, 2).revealed, true);
});

test('和弦：旗数吻合时，0 邻格会继续连锁展开（和弦也走洪泛）', () => {
  // 3×3 只有一颗雷在 (0,0)，中心 (1,1) 数字 1；旗插在 (0,0) 上
  const e = scenario(3, 3, [0]);
  e.reveal(1, 1);
  e.toggleMark(0, 0);
  assert.equal(e.chord(1, 1), true);
  // 除那颗雷以外全被翻开（其中 0 格继续洪泛）
  assert.equal(e.revealedCount, 8);
  assert.equal(e.gameState, GameState.Won);
});

// ---------------------------------------------------------------- 规则 3 问号三态

test('问号：旗 → 问号这一步剩余雷数不变（只有旗计入雷数）', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(31));
  assert.equal(e.minesRemaining(), 10);
  e.toggleMark(4, 4);
  assert.equal(e.minesRemaining(), 9);
  e.toggleMark(4, 4); // 旗 → 问号
  assert.equal(e.cellAt(4, 4).mark, Mark.Question);
  assert.equal(e.minesRemaining(), 10); // 问号不是旗，雷数回到原值
  e.toggleMark(4, 4); // 问号 → 无标记
  assert.equal(e.cellAt(4, 4).mark, Mark.None);
  assert.equal(e.minesRemaining(), 10);
});

test('问号：已翻开的格子上右键被拒，旗数与标记都不变', () => {
  const e = scenario(3, 3, []);
  e.reveal(1, 1);
  const flags = e.flagCount;
  assert.equal(e.toggleMark(1, 1), false);
  assert.equal(e.flagCount, flags);
  assert.equal(e.cellAt(1, 1).mark, Mark.None);
});

test('问号：插旗的格子不能被左键翻开，旗数不变', () => {
  const e = scenario(3, 3, []);
  e.toggleMark(1, 1);
  const out = e.reveal(1, 1);
  assert.equal(out.changed, false);
  assert.equal(e.cellAt(1, 1).revealed, false);
  assert.equal(e.cellAt(1, 1).mark, Mark.Flag);
  assert.equal(e.flagCount, 1);
});

// ---------------------------------------------------------------- 规则 4 计时契约（引擎侧）

test('计时契约：第一次 reveal 把 Ready 变成 Playing，之后状态不再变', () => {
  const e = scenario(9, 9, []);
  assert.equal(e.gameState, GameState.Ready);
  e.reveal(4, 4);
  assert.equal(e.gameState, GameState.Playing);
  e.reveal(0, 0);
  assert.equal(e.gameState, GameState.Playing);
});

test('计时契约：终局（胜/负）之后状态不再变化', () => {
  const e = scenario(2, 2, [3]); // 雷在 (1,1)
  e.reveal(1, 1);
  assert.equal(e.gameState, GameState.Lost);
  e.reveal(0, 0);
  e.toggleMark(0, 0);
  assert.equal(e.gameState, GameState.Lost);
});

// ---------------------------------------------------------------- 规则 5 胜利判定

test('胜利：差一格没翻开就不算赢', () => {
  // 雷在 (0,0)，非雷格是 (0,1) (1,0) (1,1)
  const e = scenario(2, 2, [0]);
  e.reveal(0, 1);
  e.reveal(1, 0);
  assert.equal(e.revealedCount, 2);
  assert.equal(e.gameState, GameState.Playing); // (1,1) 还没开
  e.reveal(1, 1);
  assert.equal(e.gameState, GameState.Won);
});

test('胜利：插错旗的棋盘判不了胜（非雷格翻不齐），取消错旗后可以赢', () => {
  // 雷在 (1,1)，非雷格是 (0,0) (0,1) (1,0)
  const e = scenario(2, 2, [3]);
  e.toggleMark(0, 0); // 插错旗（这是安全格）
  e.toggleMark(0, 1); // 再插一面，总旗数 2 > 雷数 1
  assert.equal(e.minesRemaining(), -1);
  e.reveal(1, 0);
  assert.equal(e.gameState, GameState.Playing); // 还有两个非雷格被旗压着，翻不齐
  e.toggleMark(0, 0); // 取消错旗
  e.toggleMark(0, 1);
  e.reveal(0, 0);
  e.reveal(0, 1);
  assert.equal(e.gameState, GameState.Won);
});

// ---------------------------------------------------------------- 规则 7 左右键语义

test('双击不重复处理：第二次点已翻开的格子没有任何变化', () => {
  const e = scenario(9, 9, []);
  const first = e.reveal(4, 4);
  assert.equal(first.changed, true);
  const count = e.revealedCount;
  const second = e.reveal(4, 4);
  assert.equal(second.changed, false);
  assert.equal(second.opened.length, 0);
  assert.equal(e.revealedCount, count);
});

test('左右键语义分开：左键只翻不标，右键只标不翻', () => {
  const e = scenario(3, 3, []);
  e.toggleMark(2, 2);
  assert.equal(e.cellAt(2, 2).revealed, false);
  assert.equal(e.cellAt(2, 2).mark, Mark.Flag);
  e.reveal(0, 0);
  assert.equal(e.cellAt(0, 0).revealed, true);
  assert.equal(e.cellAt(0, 0).mark, Mark.None);
  assert.equal(e.cellAt(2, 2).mark, Mark.Flag); // 左键不动别处的旗
});

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exitCode = 1;
}
