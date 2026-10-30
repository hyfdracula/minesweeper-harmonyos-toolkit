# verify.ps1 —— 一条命令跑完整机验证（菜单栏 / 难度切换 / 结束对话框 / 缩放平移）
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1
#
# 前置：手机已点亮解锁、USB 调试已授权。
# 脚本只在自己截图之间点击，不会长时间霸屏；每一步都留证据图到 docs\verify\。

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$docs = Join-Path $root 'docs'
$vdir = Join-Path $docs 'verify'
New-Item -ItemType Directory -Force -Path $vdir | Out-Null

$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$dev = '6HR0226409003317'
$hap = 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
$pkg = 'com.example.saolei'

function Shot([string]$name) {
  $out = Join-Path $vdir ("$name.jpeg")
  Remove-Item $out -ErrorAction SilentlyContinue
  & $hdc -t $dev shell "snapshot_display -f /data/local/tmp/$name.jpeg" | Out-Null
  & $hdc -t $dev file recv "/data/local/tmp/$name.jpeg" $out | Out-Null
  Write-Output ("  截图: $out")
}
function Tap([int]$x, [int]$y, [int]$ms = 600) {
  & $hdc -t $dev shell "uitest uiInput click $x $y" | Out-Null
  Start-Sleep -Milliseconds $ms
}
function Drag([int]$x1, [int]$y1, [int]$x2, [int]$y2) {
  & $hdc -t $dev shell "uitest uiInput drag $x1 $y1 $x2 $y2" | Out-Null
  Start-Sleep -Milliseconds 800
}
function Logs([string]$pattern, [int]$n = 12) {
  (& $hdc -t $dev shell hilog -x 2>&1 | Select-String -Pattern $pattern | Select-Object -Last $n) | ForEach-Object {
    Write-Output ("  | " + $_.Line)
  }
}

Write-Output '== 0. 连接检查 =='
$targets = (& $hdc list targets 2>&1 | Out-String)
if ($targets -notmatch $dev) {
  Write-Output "  hdc 没看到设备。手机要点亮并解锁，然后重跑本脚本。"
  Write-Output "  当前 targets: $targets"
  exit 2
}

Write-Output '== 1. 安装并启动 =='
& $hdc -t $dev install -r $hap | Select-Object -Last 1 | ForEach-Object { Write-Output ("  " + $_.Line) }
& $hdc -t $dev shell aa force-stop $pkg | Out-Null
& $hdc -t $dev shell hilog -r | Out-Null
& $hdc -t $dev shell "aa start -a EntryAbility -b $pkg" | Out-Null
Start-Sleep -Seconds 5
Shot 'v1_start'

Write-Output '== 2. 菜单栏：点「游戏」看下拉 =='
Tap 60 140 900
Shot 'v2_menu_open'
Write-Output '== 3. 选「高级」（下拉里的第三项区域） =='
Tap 120 430 1200
Shot 'v3_expert'
Logs 'GameController\] 布局'

Write-Output '== 4. 回初级，踩雷看结束对话框 =='
Tap 60 140 700
Tap 120 340 1200
Shot 'v4_beginner'
# 扫全盘直到踩雷（高级盘 16x30 一格 72px，棋盘原点 428,242）
for ($j = 0; $j -lt 16; $j += 3) {
  for ($i = 0; $i -lt 30; $i += 3) {
    Tap (428 + 36 + 72 * $i) (242 + 36 + 72 * $j) 150
  }
}
Start-Sleep -Seconds 1
Shot 'v5_dialog'
Logs '\[Dialog\]|\[Menu\]'

Write-Output '== 5. 点「再玩一局」 =='
Tap 1290 940 1200
Shot 'v6_again'

Write-Output '== 6. 单指拖动（平移）=='
Drag 1500 900 900 900
Shot 'v7_pan'

Write-Output '== 7. 长按插旗 =='
& $hdc -t $dev shell "uitest uiInput longClick 900 500" | Out-Null
Start-Sleep -Seconds 1
Shot 'v8_flag'

Write-Output ("证据图目录: " + $vdir)
Write-Output '（捏合缩放无法用 uitest 注入，需要手动双指捏一下屏幕）'
