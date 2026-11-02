/**
 * sevenseg_test.ts —— 状态条七段数码管渲染器的单元测试
 *
 * 测的是**应用仓里那份真的** SevenSeg.ets（runner 会把它复制进临时目录再编译），
 * 不是另写一份实现 —— 否则测的就是测试自己。
 *
 * 覆盖的���陷（Codex 对抗性复审 2026-11-02 点出的）：
 * 「The existing tests do not cover this renderer.」
 * 在这之前，七段渲染器的几何只有一个离线的 Python 预览脚本（sevenseg_preview.py）
 * 手工抄了一份常量 —— 常量改了、预览没改，没人发现。
 *
 * 测法：用 mock 上下文把每个数字真的画一遍（记录 fillRect），
 * 再把记录的矩形还原成字符图，和**冻结的黄金图**逐字符比对。
 * 这样任何几何改动（格宽、笔画粗细、槽位起点、「1」的画法）都会立刻炸出来。
 */

import assert from 'node:assert/strict';
import { SevenSeg } from './SevenSeg';

/** mock 上下文：只记 fillRect，够渲染器用 */
class MockCtx {
  fillStyle: string = '';
  rects: number[][] = [];
  fillRect(x: number, y: number, w: number, h: number): void {
    this.rects.push([x, y, w, h]);
  }
}

/** 把一次 draw 画出来的矩形还原成字符图（参考像素网格） */
function renderAscii(value: number, width: number, height: number): string[] {
  const ctx = new MockCtx();
  // sVp = sDev = 1 → 画出来的矩形就是**参考像素**坐标，pxScale = 1
  SevenSeg.draw(ctx as never, value, 0, 0, 1, 1);
  const grid: string[][] = [];
  for (let y = 0; y < height; y++) {
    grid.push(new Array<string>(width).fill('.'));
  }
  for (const r of ctx.rects) {
    const [x, y, w, h] = r;
    for (let yy = y; yy < y + h; yy++) {
      for (let xx = x; xx < x + w; xx++) {
        if (yy >= 0 && yy < height && xx >= 0 && xx < width) {
          grid[yy][xx] = '#';
        }
      }
    }
  }
  return grid.map((row) => row.join(''));
}

/** 单个数字的字符图（只取它自己那一格） */
function digitArt(value: number): string[] {
  const slotIndex = SevenSeg.SLOT_COUNT - 1;  // 单个数字放在最右槽
  const cellX = SevenSeg.SLOT_X0 + slotIndex * SevenSeg.SLOT_PITCH;
  const cellY = SevenSeg.CELL_Y;
  const ctx = new MockCtx();
  SevenSeg.draw(ctx as never, value, 0, 0, 1, 1);
  const grid: string[][] = [];
  for (let y = 0; y < SevenSeg.CELL_H; y++) {
    grid.push(new Array<string>(SevenSeg.CELL_W).fill('.'));
  }
  for (const r of ctx.rects) {
    const [x, y, w, h] = r;
    for (let yy = y; yy < y + h; yy++) {
      for (let xx = x; xx < x + w; xx++) {
        const gy = yy - cellY;
        const gx = xx - cellX;
        if (gy >= 0 && gy < SevenSeg.CELL_H && gx >= 0 && gx < SevenSeg.CELL_W) {
          grid[gy][gx] = '#';
        }
      }
    }
  }
  return grid.map((row) => row.join(''));
}

const tests: { name: string; fn: () => void }[] = [];
function test(name: string, fn: () => void): void {
  tests.push({ name, fn });
}

/* ---------------------------------------------------------------- 几何常量 */

test('几何常量是第六版定案值', () => {
  assert.equal(SevenSeg.SLOT_COUNT, 3, '槽位数');
  assert.equal(SevenSeg.SLOT_PITCH, 12, '槽距');
  assert.equal(SevenSeg.SLOT_X0, 3, '槽位起点');
  assert.equal(SevenSeg.CELL_W, 9, '数字格宽');
  assert.equal(SevenSeg.CELL_H, 11, '数字格高');
  assert.equal(SevenSeg.CELL_Y, 5, '数字格在面板内的 y 偏移');
  assert.equal(SevenSeg.TV, 1, '竖段粗细');
  assert.equal(SevenSeg.TH, 1, '横段粗细');
  assert.equal(SevenSeg.HL, 4, '半高竖段长度');
  assert.equal(SevenSeg.PANEL_W, 40, '面板宽');
  assert.equal(SevenSeg.PANEL_H, 21, '面板高');
});

test('三根横段 + 两根半高竖段正好铺满格高', () => {
  // 竖向：TH + HL + TH + HL + TH = CELL_H，少一格多一格都会露缝或压边
  assert.equal(3 * SevenSeg.TH + 2 * SevenSeg.HL, SevenSeg.CELL_H, '格高不自洽');
});

test('三格完整落在面板内区里（不压面板斜角高光）', () => {
  // 面板彩色内区是 x 3..36（33 单位宽）。三格占 SLOT_X0 .. SLOT_X0+2*PITCH+CELL_W
  const right = SevenSeg.SLOT_X0 + (SevenSeg.SLOT_COUNT - 1) * SevenSeg.SLOT_PITCH + SevenSeg.CELL_W;
  assert.ok(right <= 37, `最右格右沿 ${right} 压到面板边缘了`);
  assert.ok(SevenSeg.SLOT_X0 >= 3, '最左格左沿压到面板左边缘');
  // 纵向：数字格顶 + 格高 <= 面板高
  assert.ok(SevenSeg.CELL_Y + SevenSeg.CELL_H <= SevenSeg.PANEL_H, '数字格超出面板下沿');
});

/* ---------------------------------------------------------------- 字形 */

test('「1」是两根分开的小竖杠（中间有缝），不是一根整笔', () => {
  const art = digitArt(1);
  // 竖笔在格子的右沿（TV=1 宽）：x = CELL_W-1
  const barX = SevenSeg.CELL_W - SevenSeg.TV;
  // 上半根 b：行 TH .. TH+HL-1
  const top = art[SevenSeg.TH];
  const bot = art[SevenSeg.TH + SevenSeg.HL + SevenSeg.TH];
  assert.equal(top[barX], '#', '「1」上半根竖杠没画出来');
  assert.equal(bot[barX], '#', '「1」下半根竖杠没画出来');
  // 中间那一行必须是空的（缝）
  const gapRow = art[SevenSeg.TH + SevenSeg.HL];
  assert.equal(gapRow[barX], '.', '「1」中间没有缝，两根竖杠连成一根了');
  // 左边不能有别的笔画（不许有旗/衬线）
  assert.ok(!top.slice(0, barX).includes('#'), '「1」左边多了笔画');
  // 上下不能有横段
  assert.ok(!art[0].includes('#'), '「1」顶上多了横段');
  assert.ok(!art[SevenSeg.CELL_H - 1].includes('#'), '「1」底下多了横段');
});

test('十个数字的字形是冻结的黄金图', () => {
  // 黄金图：**人眼确认过**（2026-11-02）的一份真实渲染输出，冻结在这里。
  // 格宽 9、笔画 1、半高竖段 4 → 横段 7 宽、竖段 1 宽，中段 g 在第 5 行。
  // 「1」= 右边两根小竖杠，第 5 行是空的（中间有缝）—— 用户 2026-11-02 定的规矩。
  const GOLDEN: { [k: string]: string[] } = {
    '0': [
      '.#######.',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.........',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
    ],
    '1': [
      '.........',
      '........#',
      '........#',
      '........#',
      '........#',
      '.........',
      '........#',
      '........#',
      '........#',
      '........#',
      '.........',
    ],
    '2': [
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.#######.',
      '#........',
      '#........',
      '#........',
      '#........',
      '.#######.',
    ],
    '3': [
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.#######.',
    ],
    '4': [
      '.........',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.........',
    ],
    '5': [
      '.#######.',
      '#........',
      '#........',
      '#........',
      '#........',
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.#######.',
    ],
    '6': [
      '.#######.',
      '#........',
      '#........',
      '#........',
      '#........',
      '.#######.',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
    ],
    '7': [
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.........',
      '........#',
      '........#',
      '........#',
      '........#',
      '.........',
    ],
    '8': [
      '.#######.',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
    ],
    '9': [
      '.#######.',
      '#.......#',
      '#.......#',
      '#.......#',
      '#.......#',
      '.#######.',
      '........#',
      '........#',
      '........#',
      '........#',
      '.#######.',
    ],
  };
  for (const d of ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) {
    const got = digitArt(Number(d));
    const want = GOLDEN[d];
    assert.equal(got.length, want.length, `数字 ${d} 的行数不对`);
    for (let i = 0; i < want.length; i++) {
      assert.equal(got[i], want[i], `数字 ${d} 第 ${i} 行不一样\n  实际 ${got[i]}\n  期望 ${want[i]}`);
    }
  }
});

test('「1」画出来的笔画数就是 2 根（不许有额外装饰段）', () => {
  const ctx = new MockCtx();
  SevenSeg.draw(ctx as never, 1, 0, 0, 1, 1);
  assert.equal(ctx.rects.length, 2, `「1」画了 ${ctx.rects.length} 笔，应为 2 笔`);
});

/* ---------------------------------------------------------------- 槽位规则 */

test('数字右对齐、不补零', () => {
  assert.deepEqual(SevenSeg.slotsFor(0), [0, 0, 0x3F], '0');
  assert.deepEqual(SevenSeg.slotsFor(7), [0, 0, 0x07], '7');
  assert.deepEqual(SevenSeg.slotsFor(18), [0, 0x06, 0x7F], '18（右对齐，左槽空）');
  assert.deepEqual(SevenSeg.slotsFor(123), [0x06, 0x5B, 0x4F], '123');
});

test('负号占紧挨数字左边那一槽', () => {
  assert.deepEqual(SevenSeg.slotsFor(-40), [0x40, 0x66, 0x3F], '-40');
  assert.deepEqual(SevenSeg.slotsFor(-1), [0, 0x40, 0x06], '-1');
});

test('三位装不下时钳到端点，而不是丢高位显示错数', () => {
  assert.deepEqual(SevenSeg.slotsFor(1000), SevenSeg.slotsFor(999), '上界钳到 999');
  assert.deepEqual(SevenSeg.slotsFor(-100), SevenSeg.slotsFor(-99), '下界钳到 -99');
  assert.deepEqual(SevenSeg.slotsFor(12345), SevenSeg.slotsFor(999), '超界也要钳');
});

test('NaN / Infinity 不画东西，也不死循环', () => {
  assert.deepEqual(SevenSeg.slotsFor(Number.NaN), [0, 0, 0], 'NaN');
  assert.deepEqual(SevenSeg.slotsFor(Number.POSITIVE_INFINITY), [0, 0, 0], 'Infinity');
  assert.deepEqual(SevenSeg.slotsFor(Number.NEGATIVE_INFINITY), [0, 0, 0], '-Infinity');
});

/* ---------------------------------------------------------------- 缩放 */

test('放大后每个段的边都落在整数设备像素上（不发虚）', () => {
  // 真机密度 2.75、档位 su=8 → 参考像素 1 个 = 8 个设备像素 = 2.909 vp
  const ctx = new MockCtx();
  SevenSeg.draw(ctx as never, 10, 0, 0, 8 * 2.75 / 8, 8);
  for (const r of ctx.rects) {
    // 矩形的边在 vp 空间里应当是设备像素的整数倍（pxScale = 1/8）
    for (const v of [r[0], r[1], r[0] + r[2], r[1] + r[3]]) {
      const dev = v * 8;
      assert.ok(Math.abs(dev - Math.round(dev)) < 1e-6, `边 ${v} 落在分数设备像素上`);
    }
  }
});

/* ---------------------------------------------------------------- 跑 */

let failed = 0;
for (const t of tests) {
  try {
    t.fn();
    console.log(`  ok  ${t.name}`);
  } catch (e) {
    failed++;
    console.log(`  FAIL ${t.name}`);
    console.log(`       ${(e as Error).message}`);
  }
}
console.log(`sevenseg: ${tests.length} 条，通过 ${tests.length - failed}，失败 ${failed}`);
if (failed > 0) {
  process.exit(1);
}
