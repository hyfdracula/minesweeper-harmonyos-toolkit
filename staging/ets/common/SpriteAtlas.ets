/**
 * SpriteAtlas.ets —— 精灵图集加载与绘制
 *
 * 素材放在 entry/src/main/resources/rawfile/ 下，用 resourceManager 读出来，
 * 解成 ImageBitmap 后按逻辑坐标切片绘制。
 *
 * 绘制坐标约定：**全部用设备像素（px）**，不用 vp。
 * 原因：素材一格是 36 存储像素，要像素锐利就必须让格子的设备像素数是 36 的整数倍；
 * 用 vp 画会引入小数，缩放插值就把边缘弄糊了。
 * 所以外层用 ctx.scale(1/density) 把画布坐标系变成 px 空间。
 */

import { image } from '@kit.ImageKit';
import { common } from '@kit.AbilityKit';
import { SPRITE_SCALE } from './Theme';

/** 图集里的三张图 + 底板 */
export class SpriteAtlas {
  /** blueSheet / greenSheet：砖块渐变、旗、问号、高亮、红叉、阴影、数字、计数器面板 */
  boardSheet: image.ImageBitmap | null = null;
  /** minesweeperSheet / flowerGardenSheet：地雷、面板雷图标 */
  gameSheet: image.ImageBitmap | null = null;
  /** otherSheet：时钟、踩雷动画、拆雷动画、胜利扫描条 */
  otherSheet: image.ImageBitmap | null = null;
  /** Frame.png：棋盘区底板（九宫格） */
  frameSheet: image.ImageBitmap | null = null;

  async load(ctx: common.UIAbilityContext): Promise<void> {
    this.boardSheet = await SpriteAtlas.loadBitmap(ctx, 'blueSheet.png');
    this.gameSheet = await SpriteAtlas.loadBitmap(ctx, 'minesweeperSheet.png');
    this.otherSheet = await SpriteAtlas.loadBitmap(ctx, 'otherSheet.png');
    this.frameSheet = await SpriteAtlas.loadBitmap(ctx, 'Frame.png');
  }

  private static async loadBitmap(ctx: common.UIAbilityContext, name: string): Promise<image.ImageBitmap | null> {
    try {
      const buffer = await ctx.resourceManager.getRawFileContent(name);
      const source = image.createImageSource(buffer);
      if (source === null) {
        return null;
      }
      const pixelMap = await source.createPixelMap();
      const bitmap = await image.createImageBitmap(pixelMap);
      source.release();
      return bitmap;
    } catch (err) {
      console.error(`[SpriteAtlas] 加载 ${name} 失败: ${err}`);
      return null;
    }
  }

  /**
   * 从图集裁一块画出来。
   * @param srcRect 逻辑坐标 [x, y, w, h]，取像素时自动乘 SPRITE_SCALE
   * @param dx,dy,dw,dh 目标矩形（设备像素）
   */
  draw(ctx: CanvasRenderingContext2D, sheet: image.ImageBitmap | null,
    srcRect: number[], dx: number, dy: number, dw: number, dh: number): void {
    if (sheet === null) {
      return;
    }
    const sx = srcRect[0] * SPRITE_SCALE;
    const sy = srcRect[1] * SPRITE_SCALE;
    const sw = srcRect[2] * SPRITE_SCALE;
    const sh = srcRect[3] * SPRITE_SCALE;
    ctx.drawImage(sheet, sx, sy, sw, sh, dx, dy, dw, dh);
  }

  /** 数字：原版字形槽 12×15，在 18×18 的格子里居中 */
  drawDigit(ctx: CanvasRenderingContext2D, n: number, dx: number, dy: number, cell: number): void {
    if (this.boardSheet === null) {
      return;
    }
    const w = 12 * SPRITE_SCALE;
    const h = 15 * SPRITE_SCALE;
    const x = dx + Math.round((cell - w) / 2);
    const y = dy + Math.round((cell - h) / 2);
    this.draw(ctx, this.boardSheet, [1000, 15 * (n - 1), 12, 15], x, y, w, h);
  }
}
