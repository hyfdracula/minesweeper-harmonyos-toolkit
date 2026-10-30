# Win7 扫雷 → 鸿蒙（HarmonyOS）

在华为 Pura X Max 上像素级复刻 Windows 7 扫雷。自用，不上架。

- 规格与证据基线：[`docs/SPEC.md`](docs/SPEC.md)
- 参考资料（素材 + 三份参考实现）：`C:\Users\19161\Desktop\minesweeper-refs\`

## 目录

```
minesweeper/
├── docs/SPEC.md                 规格：规则、素材坐标、渲染、交互、折叠屏适配、待确认项
├── engine/
│   ├── src/MinesweeperEngine.ts 逻辑层（纯逻辑，无 UI / 无平台依赖）
│   └── test/engine.test.ts       离线测试
├── tools/sync-engine.ps1         把 engine/src/*.ts 同步成工程里的 *.ets
└── harmony/                      DevEco 工程（待建）
```

## 跑离线测试

逻辑层不依赖鸿蒙工程，直接用 Node 跑：

```powershell
node --experimental-transform-types --no-warnings engine\test\engine.test.ts
```

Node 22.18+ / 24+ 自带 TypeScript 类型剥离，不需要装依赖。`--experimental-transform-types`
是必需的：引擎用了 `enum`，纯 strip 模式不支持。

当前：24 条用例全绿。

## 逻辑层与 UI 层的分界

`engine/src/MinesweeperEngine.ts` 是唯一事实源，只管规则：

- 延迟布雷 + 首点 3×3 无雷（越界裁剪）
- BFS 洪泛展开（尊重旗子，问号格清空）
- 右键三态标记、剩余雷数可为负
- 和弦（旗数吻合才动手，旗插错同时引爆判负）
- 胜负判定与失败展示、胜利自动插旗
- 方块显示状态码沿用原版字节语义

渲染、动画、手势、折叠屏布局全在 UI 层（尚未开始）。

## 同步到鸿蒙工程

ArkTS 只认 `.ets`，逻辑层用 `.ts` 维护是为了能离线跑测试。改完逻辑层后：

```powershell
powershell -File tools\sync-engine.ps1 -ProjectRoot D:\software\harmony\projects\minesweeper\harmony
```

## 素材

`win7-assets/` 里的图集与音效来自原版 Windows 7 游戏的资源提取，**自用研究，不分发**。
精灵坐标以 `linux-minesweeper/src/ui/Theme.h` 为唯一事实源。
