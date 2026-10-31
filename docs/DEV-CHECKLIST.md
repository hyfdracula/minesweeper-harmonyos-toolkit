# 开发检查表 · HarmonyOS Win7 扫雷移植

- 规格与引擎仓库：`D:\software\harmony\projects\minesweeper`
- 应用工程：`C:\Users\19161\saolei`（命令行构建已验证通过，`tools\build.ps1`，约 8 秒）
- 验证设备：Pura X Max，内屏 2584×1828，序列号 `6HR0226409003317`

最后更新：2026-10-31

---

## 1. 状态总览

| 状态 | 条数 | 明细 |
|---|---|---|
| 已真机验证通过 | 9 | §2 |
| 代码已就位，待真机验证 | 13 | §3 |
| 已知缺陷 / 待办 | 6 | §4 |

本表只记录**已经验证过**的东西。凡是没在真机上跑出结果的，一律进 §3 或 §4，不进 §2。

---

## 2. 已真机验证通过

以下各项在 Pura X Max 真机上跑通并留过证据（2026-10-30 ~ 2026-10-31）：

- [x] **三难度渲染与切换**：9×9 / 16×16 / 16×30，棋盘尺寸与雷数随难度变（30 列高级盘自动缩到 72px/格）
- [x] **单击开格**
- [x] **洪泛展开**（连锁开空地）
- [x] **胜利 / 失败判定**
- [x] **菜单栏打开与难度切换**（画布自绘的 Win7 菜单栏，替换了最初的「≡」浮层）
- [x] **结束对话框绘制**（Win7 风格：Aero 玻璃标题栏 + 画布自绘按钮）
- [x] **长按插旗**
- [x] **计时器**（第一次左键松开起走，终局停住）
- [x] **切后台暂停**（`EntryAbility.onBackground` → `pauseForBackground()`）

---

## 3. 代码已就位，待真机验证

这些功能**代码已经写好，但尚未在真机上验证**，不能算完成。验证方式见各项备注。

| 功能 | 落点 | 状态 | 备注 |
|---|---|---|---|
| 双指捏合缩放 | `MinefieldCanvas.ets` / `GameController.ets` | 代码已就位，待真机验证 | 无法用 uitest 注入，必须手捏（见 §4.4） |
| 单指拖动平移 | 同上 | 代码已就位，待真机验证 | 越界夹紧逻辑已改，**修完未复验** |
| 折叠屏换屏重排 | `onAreaChange` → `attach()` → `layout()` | 代码已就位，待真机验证 | 需实际折屏一次，看状态是否保住 |
| 原版音效播放 | `SoundPlayer.ets` | 代码已就位，待真机验证 | 12 个 wav 已进 rawfile，播放走 `AVPlayer.fdSrc`；事件映射见 `docs/SOUND-MAP.md` |
| 自定义难度对话框 + 数字键盘 | `CustomField.ets` / `NumKeypad.ets` | 代码已就位，待真机验证 | 接线已做（菜单「自定义」→ 画布对话框 + 数字键盘输入） |
| 踩雷爆炸动画 | `Anim.ets` | 代码已就位，待真机验证 | 帧表按原版 `Theme.h` 修正：23 帧、57×57、偏移 (−18,−18)、23 帧/秒 |
| 胜利扫描条 + 拆雷光束 | `Anim.ets` | 代码已就位，待真机验证 | 38 帧/2 秒的光束 + 3 秒扫描条，扫完才弹胜利框 |
| 结束对话框版式重测 | `WinDialog.ets` | 代码已就位，待真机验证 | 三个框按 `loss.jpg`/`win.jpg`/`about.jpg` 逐像素重排（47 个常量带出处） |
| 菜单栏版式重测 | `WinMenu.ets` | 代码已就位，待真机验证 | 18px 高的渐变菜单栏、12px 字号、实测基线；(G)/(H) 快捷键 |
| 帮助对话框 | `WinDialog.helpSpec()` | 代码已就位，待真机验证 | 菜单「帮助(H)」项 |
| 状态条顺序校正 | `GameController.drawStatusStrip` | 代码已就位，待真机验证 | `[时钟][计时]…[雷数][雷图标]`（曾两次误判，见 SPEC §5.5） |
| 悬停高亮改加法混合 | `GameController.drawBoard` | 代码已就位，待真机验证 | 原版是 additive，普通合成会把整格涂成深青 |
| 自定义局不进统计 | `GameController.buildDialog` | 代码已就位，待真机验证 | 原版自定义局既不记最好成绩也不计入局数 |
| 双击和弦 | `GameController` | 代码已就位，待真机验证 | `uitest uiInput doubleClick` 未验证过 |

---

## 4. 已知缺陷与待办

1. **结束对话框与菜单栏的按钮命中 / 尺寸**：2026-10-31 修过两次单位换算（画布坐标是 vp，font 里的 px 是设备像素），随后又按参考图重排过版式，**最新一轮尚未真机复验**。
2. **Codex 对抗性复审**：最近一次（commit 7be4da8 之后）裁定 **CONCERNS**（来源：**由 P2 标记推断**，报告无显式 VERDICT 行），唯一问题是「关于」框图标坐标换算两次，**已修**。再往前一次（c32e2e6）裁定 BLOCKER，7 条已全部修。两轮修完都**尚未真机复验**。
3. **设备调试通道（hdc）最近掉线**，需要手机点亮解锁才能继续验证。记录本条时的实测：`hdc list targets` 能看到 `6HR0226409003317`、`hdc shell` 也能回包，通道暂时恢复；但设备息屏 / 锁屏后会掉，验证期间手机保持点亮解锁。
4. **捏合缩放无法用 uitest 注入**，必须用户手动在真机上双指捏一下，并看 hilog 里的 `[Touch] 捏合 档位n=…`。
5. **未做**（详见 `docs/WIN7-FEATURE-GAP.md`）：新局发牌动画、洪泛涟漪淡出、判负时其它雷逐个烧红、独立帮助窗口（现在是对话框）、扫雷统计信息窗口（现在是简版对话框）、绿色主题。
6. **首点机制与真 Win7 有意不同**：本项目是「首点必开一片空地（角落≥4/中心≥9）」，真 Win7 是「首点安全但可能开出一个数字」。这是产品决定，不是 bug（SPEC §8 待确认项）。

---

## 5. 装机清单（需要你在电脑上做 3 件事）

### 第 1 步：打开 DevEco Studio 并登录

1. 启动 `D:\software\DevEco Studio\bin\devecostudio.exe`
2. 用**华为账号**登录（这一步必须联网，签名要靠账号生成证书）
3. 打开工程 `C:\Users\19161\saolei`

### 第 2 步：自动签名

1. 菜单 **File → Project Structure → Signing Configs**
2. 勾选 **Automatically generate signature**
3. 等它生成 `.p12` / `.cer` / `.p7b`（一般在 `C:\Users\19161\.ohos\config\`）
4. 回到 **Project Structure → Modules → entry**，确认 **Signing Configs** 选的是 `default`

命令行构建不需要签名（产出 `entry-default-unsigned.hap`），但装到真机必须签名。

### 第 3 步：手机连电脑

1. 手机：**设置 → 关于手机 → 连续点击「版本号」7 次** → 输入锁屏密码，进入开发者选项
2. 开发者选项里打开 **USB 调试**
3. 用数据线连电脑，手机上弹「允许 USB 调试」→ 勾「一直允许」→ 确定
4. HarmonyOS NEXT / 鸿蒙 7 上还可能需要 **设置 → 关于手机 → 开发者选项 → 监视应用安装**（部分版本）

连上以后，在 DevEco 的 **Run** 按钮或命令行都能装：

```powershell
$env:DEVECO_SDK_HOME='D:\software\DevEco Studio\sdk'
& 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe' list targets
& 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe' install -r 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
```

（`-signed.hap` 是签名后产物的名字，以实际目录里的文件为准。）

---

## 6. 真机调试命令速查

```powershell
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$d   = '6HR0226409003317'   # Pura X Max 的序列号

# 装 + 起 + 截图
& $hdc -t $d install -r 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
& $hdc -t $d shell aa force-stop com.example.saolei
& $hdc -t $d shell aa start -a EntryAbility -b com.example.saolei
& $hdc -t $d shell snapshot_display -f /data/local/tmp/s.jpeg
New-Item -ItemType Directory -Force -Path 'D:\software\harmony\projects\minesweeper\docs\verify' | Out-Null
& $hdc -t $d file recv /data/local/tmp/s.jpeg 'D:\software\harmony\projects\minesweeper\docs\verify\s.jpeg'

# 模拟触摸（屏幕坐标 = 画布坐标 + 状态栏 107px；触摸事件里是相对画布的坐标）
& $hdc -t $d shell "uitest uiInput click 1295 900"          # 单击
& $hdc -t $d shell "uitest uiInput longClick 1241 546"      # 长按（插旗）
& $hdc -t $d shell "uitest uiInput doubleClick 1295 900"    # 双击（和弦）

# 看日志（崩溃时看这里）
& $hdc -t $d shell hilog -r
& $hdc -t $d shell hilog -x | Select-String 'JSAPP|ArkCompiler'
```

**一键整机验证脚本**（菜单栏 / 难度切换 / 结束对话框 / 平移 / 插旗）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\software\harmony\projects\minesweeper\tools\verify.ps1'
```

脚本的证据图统一落在 `docs\verify\`，**不要往 `docs\` 根目录丢截图**。捏合缩放脚本注入不了，得手捏。

---

## 7. 布局速查（真机实测）

| 项 | 值 |
|---|---|
| 内屏画布 | 2584 × 1644 设备像素 |
| 密度 | **2.75**（px per vp），1 vp = 2.75 px |
| 缩放档位 | 9×9 → n=3（108px/格）；16×30 → n=2（72px/格） |
| 状态栏占位 | 屏幕顶部 107 px |

截图发我，我按原版逐项对照。
