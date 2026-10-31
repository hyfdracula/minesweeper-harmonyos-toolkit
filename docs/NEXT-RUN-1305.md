# 13:05 自动开工任务书

## 用户原话（2026-10-31 11:16，逐字照录）

> 好，继续，激活子智能体继续干活，不惜token，只要最好的效果，每一个屏幕比例都要适配，每一个按钮都要尝试点击，每一个操作逻辑顺序都要跑通，尽善尽美，拉起多个智能体

## 开工时间

**2026-10-31 13:05（Asia/Shanghai）**。由会话内定时提醒触发，不需要用户再喊一次。

## 把原话拆成可验收的五条

| # | 原话 | 验收标准（每条都要有截图或日志为证） |
|---|---|---|
| 1 | 拉起多个智能体 | 至少 3 个子智能体并行，写入范围互不重叠（各自只碰自己的文件） |
| 2 | 每一个屏幕比例都要适配 | 内屏 2210×2416、外屏 1080×2444（模拟器 Mate X7）；真机 2584×1828 与 481×704（Pura X Max 内外屏）。四种画布尺寸下棋盘/菜单/状态条/对话框都不裁切、不重叠、落整数像素 |
| 3 | 每一个按钮都要尝试点击 | 逐个点：菜单栏两个顶层项 + 游戏下拉 9 项 + 帮助下拉 3 项 + 结束框 3 按钮 + 标题栏红叉 + 统计窗口 2 按钮 + 自定义框（确定/取消/数字键盘 12 键）+ 帮助框确定。**每个都要有「点完发生了什么」的记录** |
| 4 | 每一个操作逻辑顺序都要跑通 | 开格→洪泛→插旗→问号→和弦→踩雷→爆炸→结束框→再玩一局；自定义设值→开局；最佳成绩→重置；标记开关；声音开关；退出 |
| 5 | 尽善尽美 | 跑完一遍 Codex 对抗性复审，Critical/High 要么修要么说明为什么不修 |

## 开工第一步（照这个顺序做，别重新摸环境）

1. **确认模拟器还在跑**：
   ```powershell
   powershell -File D:\software\harmony\projects\minesweeper\tools\emu.ps1 -Action status
   ```
   没跑就 `-Action start`（约 90 秒，必须用 Start-Process 脱离启动，不能用 Job，否则会被清理）。

2. **拉子智能体**。写入范围建议这样切（避免互相踩）：
   - A：按钮全量点击清单 → 只写 `docs\BUTTON-MATRIX.md`（只读代码 + 模拟器实测）
   - B：四屏比例适配 → 只改 `GameController.layout()` 相关的一个文件
   - C：操作链路跑通 → 只写 `docs\FLOW-RUNBOOK.md`
   - 我（lead）保留：GameController / MinefieldCanvas / Index / Theme / WinMenu / WinDialog 的最终改动权

3. **自动化验证脚本**：
   ```powershell
   powershell -File D:\software\harmony\projects\minesweeper\tools\verify.ps1 -Device 127.0.0.1:5555
   ```
   （verify.ps1 的菜单坐标是按真机 2.75 密度算的，模拟器是 5.0，**先按 `docs\EMULATOR.md` 里的换算改一下再跑**。）

## 已经踩过的坑（别重复）

- 模拟器必须 `Start-Process` 脱离启动；用 Job 会在工具调用结束时被一起杀掉。
- `-foldedState` 的合法值只有 **`open` / `close`**，`closed`/`opened` 会被拒。
- 截图坐标换算：`snapshot_display` 出的是**物理像素**；预览图会被缩过，按 `原始宽 / 预览宽` 乘回去，否则点击会偏。
- 有对话框时 `inputLocked` 只该禁平移/捏合，**不能挡住点击**（已经修过一次）。
- `AVPlayer` 的 `fdSrc` 是异步状态机，必须等 `stateChange` 到 `initialized` 才能 `prepare()`。
- 编辑器里的 `hdc list targets` 输出要 `| Out-String` 再判断，否则单行输出取 `$_.Line` 会得到空串，把「有设备」误判成「没设备」。
