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
| 代码已就位，待真机验证 | 7 | §3 |
| 已知缺陷 / 待办 | 5 | §4 |

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
| 原版音效播放 | `SoundPlayer.ets` | 代码已就位，待真机验证 | 11 个 wav 已进 rawfile，播放走 `AVPlayer.fdSrc` |
| 自定义难度对话框 | 对话框绘制模块 | 代码已就位，待接线、待真机验证 | **接线未做**（见 §4.5） |
| 动画模块 | 爆炸 / 插旗 / 胜利扫描条 | 代码已就位，待接线、待真机验证 | **接线未做**（见 §4.5） |
| 双击和弦 | `GameController` | 代码已就位，待真机验证 | `uitest uiInput doubleClick` 未验证过，沿用上版检查表的待测标记 |

---

## 4. 已知缺陷与待办

1. **结束对话框与菜单栏的按钮命中 / 尺寸**：2026-10-31 修过两次单位换算（画布坐标是 vp，font 里的 px 是设备像素），**最新一轮尚未真机复验**。
2. **Codex 对抗性复审（commit c32e2e6）裁定 BLOCKER**，7 条已全部修（平移夹紧、捏合累计倍率、音效重播、分难度最快纪录、捏合后拖动原点重设、关对话框重画、对话框关闭按钮可点），**修完尚未复验**。
3. **设备调试通道（hdc）最近掉线**，需要手机点亮解锁才能继续验证。记录本条时的实测：`hdc list targets` 能看到 `6HR0226409003317`、`hdc shell` 也能回包，通道暂时恢复；但设备息屏 / 锁屏后会掉，验证期间手机保持点亮解锁。
4. **捏合缩放无法用 uitest 注入**，必须用户手动在真机上双指捏一下，并看 hilog 里的 `[Touch] 捏合 档位n=…`。
5. **未做**：自定义难度接线、动画接线、菜单栏「最佳成绩 / 关于」在真机上的复验、胜利扫描条。

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
