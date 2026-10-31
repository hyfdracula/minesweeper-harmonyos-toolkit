# verify.ps1 —— 一条命令跑完整机验证
#
# 用法（手机点亮解锁、USB 调试已授权的前提下）：
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1 -SkipInstall   # 只跑交互验证
#
# 覆盖：启动/发牌动画、菜单栏与难度切换、洪泛涟漪、踩雷爆炸、结束对话框、
#       胜利扫描条（需赢一局，本脚本用「点满全盘直到踩雷」走失败路径）、
#       帮助/关于/最佳成绩三个窗口、长按插旗、单指平移。
#
# 坐标是按当前版本常量算出来的（菜单栏 21vp、条目 24vp、分隔线 7vp），
# 若以后改了 WinMenu.ets 的常量，这里要同步。
#
# 证据图与日志都落到 docs\verify\。

param(
  [switch]$SkipInstall,
  [string]$Device = '6HR0226409003317'
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$vdir = Join-Path $root 'docs\verify'
New-Item -ItemType Directory -Force -Path $vdir | Out-Null

$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$hap = 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
$pkg = 'com.example.saolei'

# 画布在屏幕上的纵向偏移（状态栏高度，实测 107px）
$CANVAS_Y = 107

function Shot([string]$name) {
  $out = Join-Path $vdir ("$name.jpeg")
  Remove-Item $out -ErrorAction SilentlyContinue
  & $hdc -t $Device shell "snapshot_display -f /data/local/tmp/$name.jpeg" | Out-Null
  & $hdc -t $Device file recv "/data/local/tmp/$name.jpeg" $out | Out-Null
  Write-Output ("  截图: $name.jpeg")
}
function Tap([int]$x, [int]$y, [int]$ms = 500) {
  & $hdc -t $Device shell "uitest uiInput click $x $y" | Out-Null
  Start-Sleep -Milliseconds $ms
}
function Drag([int]$x1, [int]$y1, [int]$x2, [int]$y2) {
  & $hdc -t $Device shell "uitest uiInput drag $x1 $y1 $x2 $y2" | Out-Null
  Start-Sleep -Milliseconds 800
}
function LongClick([int]$x, [int]$y) {
  & $hdc -t $Device shell "uitest uiInput longClick $x $y" | Out-Null
  Start-Sleep -Milliseconds 800
}
function Logs([string]$pattern, [int]$n = 15) {
  (& $hdc -t $Device shell hilog -x 2>&1 | Select-String -Pattern $pattern | Select-Object -Last $n) |
    ForEach-Object { Write-Output ("  | " + $_.Line) }
}

# ---- 菜单坐标（由 WinMenu.ets 的常量算出，单位：设备像素，含状态栏偏移）----
# 菜单栏高 21vp；条目 24vp、分隔线 7vp；下拉从 21vp 起、内边距 4vp
function MenuY([double]$itemCenterVp) { return [int]($CANVAS_Y + $itemCenterVp * 2.75) }
$Y_GAME = MenuY 10.5          # 顶栏「游戏(G)」
$Y_HELP = MenuY 10.5          # 顶栏「帮助(H)」
$X_GAME = 95
$X_HELP = 250
# 游戏下拉各项的中心（vp → 屏）
$Y_NEW = MenuY 37
$Y_BEGINNER = MenuY 68
$Y_INTERMEDIATE = MenuY 92
$Y_EXPERT = MenuY 116
$Y_CUSTOM = MenuY 140
$Y_MARKS = MenuY 164
$Y_SOUND = MenuY 195
$Y_BEST = MenuY 226
$Y_EXIT = MenuY 257
$X_DROP_GAME = 150            # 游戏下拉的点击横向位置
$X_DROP_HELP = 300            # 帮助下拉的点击横向位置（顶栏第二项在右侧）

Write-Output '== 0. 连接检查 =='
$targets = (& $hdc list targets 2>&1 | Out-String)
if ($targets -notmatch $Device) {
  Write-Output '  hdc 没看到设备。手机要点亮并解锁，然后重跑本脚本。'
  Write-Output ("  当前 targets: " + $targets.Trim())
  exit 2
}
Write-Output '  设备在线'

if (-not $SkipInstall) {
  Write-Output '== 1. 安装并启动（顺带抓发牌动画的三帧）=='
  & $hdc -t $Device install -r $hap | Select-Object -Last 1 | ForEach-Object { Write-Output ("  " + $_.Line) }
  & $hdc -t $Device shell aa force-stop $pkg | Out-Null
  & $hdc -t $Device shell hilog -r | Out-Null
  & $hdc -t $Device shell "aa start -a EntryAbility -b $pkg" | Out-Null
  Start-Sleep -Milliseconds 1500
  Shot 'a1_deal_in_early'
  Start-Sleep -Milliseconds 500
  Shot 'a2_deal_in_late'
  Start-Sleep -Seconds 3
  Shot 'a3_ready'
  Logs 'GameController\] 布局|MinefieldCanvas'
} else {
  Write-Output '== 1. 跳过安装（-SkipInstall），只重启应用 =='
  & $hdc -t $Device shell aa force-stop $pkg | Out-Null
  & $hdc -t $Device shell hilog -r | Out-Null
  & $hdc -t $Device shell "aa start -a EntryAbility -b $pkg" | Out-Null
  Start-Sleep -Seconds 4
  Shot 'a3_ready'
}

Write-Output '== 2. 菜单栏：开「游戏」，换高级 =='
Tap $X_GAME $Y_GAME 800
Shot 'b1_menu_open'
Tap $X_DROP_GAME $Y_EXPERT 1500
Shot 'b2_expert'
Logs 'GameController\] 布局'

Write-Output '== 3. 回初级（顺便验证菜单能反复切换）=='
Tap $X_GAME $Y_GAME 700
Tap $X_DROP_GAME $Y_BEGINNER 1400
Shot 'c1_beginner'

Write-Output '== 4. 点一格格开棋盘（顺带看洪泛涟漪）=='
# 初级盘 9×9，居中的一块区域，逐格点开
for ($k = 0; $k -lt 6; $k++) {
  Tap (900 + 90 * ($k % 3)) (700 + 90 * [math]::Floor($k / 3)) 400
  if ($k -eq 1) { Shot 'd1_ripple' }
}
Shot 'd2_board'

Write-Output '== 5. 点满全盘直到终局，抓爆炸/胜利动画与结束对话框 =='
# 初级盘格子在 100~160px 之间，用 80px 步长铺满覆盖，保证能点到大多数格子
for ($j = 0; $j -lt 18; $j++) {
  for ($i = 0; $i -lt 18; $i++) {
    Tap (420 + 80 * $i) (300 + 80 * $j) 90
  }
}
Shot 'e1_ending'
Start-Sleep -Milliseconds 600
Shot 'e2_ending_mid'
Start-Sleep -Seconds 3
Shot 'e3_dialog'
Logs '\[Dialog\]|\[Menu\]'

Write-Output '== 6. 帮助菜单：帮助(H) 与 关于扫雷 =='
Tap $X_HELP $Y_HELP 800
Shot 'f1_help_menu'
Tap $X_DROP_HELP (MenuY 37) 900
Shot 'f2_help_dialog'
Write-Output '  （对话框关闭按钮坐标见 f2_help_dialog.jpeg，脚本这里按居中偏下点一次试）'
Tap 1290 1400 700
Shot 'f3_after_help_close'

Write-Output '== 7. 最佳成绩：扫雷统计信息窗口 =='
Tap $X_GAME $Y_GAME 700
Tap $X_DROP_GAME $Y_BEST 1200
Shot 'g1_stats_window'
Logs '\[Stats\]'
Tap 1290 1400 700
Shot 'g2_after_stats_close'

Write-Output '== 8. 长按插旗 =='
LongClick 900 700
Shot 'h1_flag'

Write-Output '== 9. 单指拖动（平移）=='
Drag 1500 900 900 900
Shot 'i1_pan'

Write-Output '== 10. 日志汇总 =='
Logs 'JSAPP' 25

Write-Output ''
Write-Output ("证据图目录: " + $vdir)
Write-Output '注意：双指捏合无法用 uitest 注入，需要手动双指捏一下，'
Write-Output '      然后在 hilog 里找 [Touch] 捏合 档位n=… 这一行。'
