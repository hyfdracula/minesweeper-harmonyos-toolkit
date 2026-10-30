/**
 * Theme.ets —— 渲染常量与精灵表坐标
 *
 * 坐标全部是「逻辑坐标」（原版 tile = 18 单位），素材按 2 倍存（36 像素），
 * 取像素时乘 SPRITE_SCALE。唯一事实源：linux-minesweeper/src/ui/Theme.h。
 *
 * 坐标表已于 2026-10-30 逐项裁图核对通过（见 docs/SPEC.md §5.1）。
 */

/** 原版逻辑格子边长 */
export const TILE: number = 18;

/** 素材相对逻辑坐标的倍数 */
export const SPRITE_SCALE: number = 2;

/** 素材里一格占的设备像素 */
export const TILE_SRC_PX: number = TILE * SPRITE_SCALE;

/** 最大棋盘（渐变帧按 30 列 × 24 行排布） */
export const GRAD_COLS: number = 30;
export const GRAD_ROWS: number = 24;

/** 砖块渐变每行帧数 */
export const GRAD_PER_ROW: number = 25;

// ---- blueSheet / greenSheet ------------------------------------------------

/** 砖块渐变第 frame 帧（普通态） */
export function normalTileRect(frame: number): number[] {
  const x = TILE * (frame % GRAD_PER_ROW);
  const y = TILE * Math.floor(frame / GRAD_PER_ROW);
  return [x, y, TILE, TILE];
}

/** 砖块渐变第 frame 帧（按下态） */
export function pressedTileRect(frame: number): number[] {
  const r = normalTileRect(frame);
  return [r[0] + 500, r[1], TILE, TILE];
}

/** 旗 */
export const RECT_FLAG: number[] = [400, 560, 18, 18];
/** 问号 */
export const RECT_QUESTION: number[] = [420, 560, 18, 18];
/** 悬停高亮（相加混合） */
export const RECT_HILITE: number[] = [440, 560, 18, 18];
/** 错旗红叉 */
export const RECT_MISFLAG: number[] = [460, 560, 18, 18];
/** 上方阴影条 */
export const RECT_SHADOW_U: number[] = [480, 560, 18, 3];
/** 左侧阴影条 */
export const RECT_SHADOW_L: number[] = [1012, 0, 3, 18];
/** 计数器凹槽面板 */
export const RECT_COUNTER: number[] = [0, 580, 40, 21];

/** 数字 1..8（字形槽 12×15，不是原 XML 的 10×13） */
export function digitRect(n: number): number[] {
  return [1000, 15 * (n - 1), 12, 15];
}

// ---- minesweeperSheet / flowerGardenSheet ---------------------------------

/** 格下地雷 */
export const RECT_MINE: number[] = [27, 0, 18, 18];
/** 面板雷图标（银色圆钮装地雷） */
export const RECT_PANEL_MINE: number[] = [0, 0, 25, 25];

// ---- otherSheet ------------------------------------------------------------

/** 时钟图标（银色圆钮装时钟） */
export const RECT_CLOCK: number[] = [905, 425, 25, 25];

/** 踩雷动画帧（雷），23 帧 / 1 秒 */
export const TRIP_FRAMES: number = 23;
export function tripRect(frame: number): number[] {
  return [728 + 59 * (frame % 3), 59 * Math.floor(frame / 3), 57, 57];
}
/** 踩雷动画绘制偏移 */
export const TRIP_OFFSET: number[] = [-18, -18];

/** 拆雷动画帧（胜利），38 帧 / 2 秒 */
export const DISARM_FRAMES: number = 38;
export function disarmRect(frame: number): number[] {
  return [52 * (frame % 7), 152 * Math.floor(frame / 7), 50, 150];
}
/** 拆雷动画绘制偏移 */
export const DISARM_OFFSET: number[] = [-18, -69];

/** 胜利扫描条 */
export const RECT_SCAN_BAR: number[] = [0, 912, 275, 62];

// ---- 棋盘底板 Frame.bmp ----------------------------------------------------

/** 底板原图尺寸（像素） */
export const FRAME_W: number = 600;
export const FRAME_H: number = 351;
/** 九宫格拉伸边距 */
export const FRAME_GAP_L: number = 30;
export const FRAME_GAP_T: number = 30;
export const FRAME_GAP_R: number = 29;
export const FRAME_GAP_B: number = 32;

/**
 * 砖块渐变帧映射：原版不是所有格子同一个蓝色，而是 720 帧（30×24）从左上到右下
 * 由亮到暗的渐变，每格取自己那一帧。小棋盘取「居中窗口」而不是拉伸整个渐变，
 * 否则初级局会显得过亮或过暗。
 */
export function gradientFrame(row: number, col: number, rows: number, cols: number): number {
  const r = Math.min(GRAD_ROWS - 1, row + Math.max(0, Math.floor((GRAD_ROWS - rows) / 2)));
  const c = Math.min(GRAD_COLS - 1, col + Math.max(0, Math.floor((GRAD_COLS - cols) / 2)));
  return r * GRAD_COLS + c;
}
