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

// ---------------------------------------------------------------- 标记

test('右键三态：无标记 → 旗 → 问号 → 无标记', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  assert.equal(e.toggleMark(4, 4), true);
  assert.equal(e.cellAt(4, 4).mark, Mark.Flag);
  assert.equal(e.minesRemaining(), 9, '插一面旗，剩余雷数减一');
  assert.equal(e.toggleMark(4, 4), true);
  assert.equal(e.cellAt(4, 4).mark, Mark.Question);
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
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10, seededRandom(3));
  e.reveal(4, 4);
  assert.equal(e.toggleMark(4, 4), false, '已翻开的格子不应能插旗');

  e.toggleMark(0, 0);
  const outcome = e.reveal(0, 0);
  assert.equal(outcome.changed, false, '插旗的格子不应能被翻开');
  assert.equal(e.cellAt(0, 0).mark, Mark.Flag);
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

test('1×1 极端棋盘不会死循环', () => {
  const e = new MinesweeperEngine();
  e.reset(1, 1, 1, seededRandom(1));
  const outcome = e.reveal(0, 0);
  assert.ok(outcome.lost || outcome.opened.length >= 0);
  assert.equal(e.cells.length, 1);
});

test('越界操作被安全忽略', () => {
  const e = new MinesweeperEngine();
  e.reset(9, 9, 10);
  assert.equal(e.reveal(-1, 0).changed, false);
  assert.equal(e.reveal(0, 99).changed, false);
  assert.equal(e.toggleMark(-1, -1), false);
  assert.equal(e.chord(99, 99), false);
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

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exitCode = 1;
}
