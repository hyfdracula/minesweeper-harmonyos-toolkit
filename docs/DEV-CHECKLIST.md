# 装机清单（需要你在电脑上做 3 件事）

工程在 `C:\Users\19161\saolei`，命令行构建已验证通过（`tools\build.ps1`，约 8 秒）。

## 第 1 步：打开 DevEco Studio 并登录

1. 启动 `D:\software\DevEco Studio\bin\devecostudio.exe`
2. 用**华为账号**登录（这一步必须联网，签名要靠账号生成证书）
3. 打开工程 `C:\Users\19161\saolei`

## 第 2 步：自动签名

1. 菜单 **File → Project Structure → Signing Configs**
2. 勾选 **Automatically generate signature**
3. 等它生成 `.p12` / `.cer` / `.p7b`（一般在 `C:\Users\19161\.ohos\config\`）
4. 回到 **Project Structure → Modules → entry**，确认 **Signing Configs** 选的是 `default`

命令行构建不需要签名（产出 `entry-default-unsigned.hap`），但装到真机必须签名。

## 第 3 步：手机连电脑

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

## 连上以后我要做的验证（M1 + M2 清单）

**已于 2026-10-30 在 Pura X Max（内屏 2584×1828）真机逐项验证通过**：

- [x] 画面出来：蓝砖渐变、浅灰地板、黑色格线
- [x] 左下角时钟 + 计时、右下角雷数 + 雷图标，位置与原版一致
- [x] 单击开格、数字颜色对（1 蓝 / 2 绿 / 3 红），数字居中
- [x] 长按 400ms 出红旗，再长按出问号，再长按取消
- [x] 左上角「≡」按钮：切初级/中级/高级，棋盘尺寸和雷数跟着变（30 列高级盘自动缩到 72px/格）
- [x] 计时从 0 开始走，终局停住
- [x] 踩雷后全盘亮雷、弹出「踩到雷了」面板（居中）
- [ ] 双击已翻开的数字格 = 和弦（**待测**：`uitest uiInput doubleClick` 未验证）
- [ ] 通关弹出「扫雷成功」+ 用时（**待测**：需要真的把一局打通）

## 真机调试命令速查

```powershell
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$d   = '6HR0226409003317'   # Pura X Max 的序列号

# 装 + 起 + 截图
& $hdc -t $d install -r 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
& $hdc -t $d shell aa force-stop com.example.saolei
& $hdc -t $d shell aa start -a EntryAbility -b com.example.saolei
& $hdc -t $d shell snapshot_display -f /data/local/tmp/s.jpeg
& $hdc -t $d file recv /data/local/tmp/s.jpeg 'D:\software\harmony\projects\minesweeper\docs\s.jpeg'

# 模拟触摸（屏幕坐标 = 画布坐标 + 状态栏 107px；触摸事件里是相对画布的坐标）
& $hdc -t $d shell "uitest uiInput click 1295 900"          # 单击
& $hdc -t $d shell "uitest uiInput longClick 1241 546"      # 长按（插旗）
& $hdc -t $d shell "uitest uiInput doubleClick 1295 900"    # 双击（和弦）

# 看日志（崩溃时看这里）
& $hdc -t $d shell hilog -r
& $hdc -t $d shell hilog -x | Select-String 'JSAPP|ArkCompiler'
```

## 布局速查（真机实测）

| 项 | 值 |
|---|---|
| 内屏画布 | 2584 × 1644 设备像素 |
| 密度 | **2.75**（px per vp），1 vp = 2.75 px |
| 缩放档位 | 9×9 → n=3（108px/格）；16×30 → n=2（72px/格） |
| 状态栏占位 | 屏幕顶部 107 px |

截图发我，我按原版逐项对照。
