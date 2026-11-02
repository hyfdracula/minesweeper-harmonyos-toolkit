/**
 * 给 Node 侧编译用的最小 Canvas 类型桩。
 *
 * 为什么要桩：状态条的七段数码管渲染器是 ArkTS，签名里带 `CanvasRenderingContext2D`
 * （ArkUI 的类型，Node 的 TS 环境里不存在）。不补桩就没法把**应用仓里那份真的**
 * SevenSeg.ets 拉下来跑单测。
 *
 * 桩只声明渲染器真正用到的东西：fillStyle + fillRect。
 * 故意**不**声明 fillText / stroke 之类 —— 用到了就会编译报错，
 * 免得测试悄悄漏测新加的绘制调用。
 */
declare class CanvasRenderingContext2D {
  fillStyle: string;
  fillRect(x: number, y: number, w: number, h: number): void;
}
