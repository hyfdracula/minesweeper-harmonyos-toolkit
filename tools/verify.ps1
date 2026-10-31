# verify.ps1 —— 一条命令跑完整机/模拟器验证
#
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1 -Device 127.0.0.1:5555 -Tag X7
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify.ps1 -SkipInstall
#
# 覆盖：启动/发牌、菜单栏与难度切换、洪泛涟漪、踩雷爆炸、结束对话框三个按钮、
#       帮助对话框、最佳成绩窗口（含左栏难度选择/重置/关闭/标题栏红叉）、
#       自定义难度对话框与数字键盘、长按插旗、单指平移。
#
# 坐标一律用 **vp**（与分辨率无关），再按实测密度换算成设备像素；
# 画布在屏幕上的纵向偏移用 tools\probe_canvas.py 从截图里量出来。
# 所以同一套脚本在真机（density 2.75）和两种模拟器（3.125 / 3.5）上都能跑。
#
# 证据图与日志都落到 docs\verify\。

param(
  [switch]$SkipInstall,
  [string]$Device = '127.0.0.1:5555',
  [string]$Tag = ''
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$vdir = Join-Path $root 'docs\verify'
New-Item -ItemType Directory -Force -Path $vdir | Out-Null

$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$hap = 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
$pkg = 'com.example.saolei'
$probe = Join-Path $root 'tools\probe_canvas.py'

if ($Tag -eq '') { $Tag = 'v' }

# ---- 运行期标定出来的量（下面会被自动填）----
$CANVAS_Y = 0        # 画布顶在屏幕上的纵向偏移（px）
$DENS = 1.0          # 密度比例（真机 2.75）
$CANVAS_W = 0
$CANVAS_H = 0
$TILE = 0            # 格边（设备像素）
$BOARD_X = 0
$BOARD_Y = 0

function Shot([string]$name) {
  $out = Join-Path $vdir ("$Tag`_$name.jpeg")
  Remove-Item $out -ErrorAction SilentlyContinue
  & $hdc -t $Device shell "snapshot_display -f /data/local/tmp/$name.jpeg" | Out-Null
  & $hdc -t $Device file recv "/data/local/tmp/$name.jpeg" $out | Out-Null
  Write-Output ("  截图: $Tag`_$name.jpeg")
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
# vp → 屏幕像素
function V([double]$vp) { return [int][math]::Round($vp * $DENS) }
# 画布内的 vp → 屏幕像素
function P([double]$vpX, [double]$vpY) { return @((V $vpX), ($CANVAS_Y + (V $vpY))) }
# 画布内的设备像素 → 屏幕像素
function PD([double]$pxX, [double]$pxY) { return @([int]$pxX, ($CANVAS_Y + [int]$pxY)) }

# ---- 菜单坐标（vp，来源：WinMenu.ets 的常量 + 真机逐项点过一遍校准）----
$MENU_BAR_H = 21
$Y_TOP = 10.5            # 顶栏文字中心
$X_GAME = 36             # 「游戏(G)」
$X_HELP = 91             # 「帮助(H)」
$X_DROP_GAME = 40        # 游戏下拉文字区
$X_DROP_HELP = 110       # 帮助下拉文字区（这个下拉往右缩进）
# 游戏下拉各项中心（vp）：新建/初级/中级/高级/自定义/标记/声音/最佳成绩/退出
$Y_NEW = 41
$Y_BEGINNER = 72
$Y_INTERMEDIATE = 96
$Y_EXPERT = 120
$Y_CUSTOM = 144
$Y_MARKS = 168
$Y_SOUND = 199
$Y_BEST = 230
$Y_EXIT = 261

Write-Output '== 0. 连接检查 =='
$targets = (& $hdc list targets 2>&1 | Out-String)
if ($targets -notmatch [regex]::Escape($Device)) {
  Write-Output ("  hdc 没看到设备 " + $Device)
  Write-Output ("  当前 targets: " + $targets.Trim())
  exit 2
}
Write-Output ("  设备在线: " + $Device)

if (-not $SkipInstall) {
  Write-Output '== 1. 安装并启动 =='
  & $hdc -t $Device install -r $hap | Select-Object -Last 1 | ForEach-Object { Write-Output ("  " + $_.Line) }
}
& $hdc -t $Device shell aa force-stop $pkg | Out-Null
& $hdc -t $Device shell hilog -r | Out-Null
& $hdc -t $Device shell "aa start -a EntryAbility -b $pkg" | Out-Null
Start-Sleep -Milliseconds 1200
Shot 'a1_deal_in_early'
Start-Sleep -Milliseconds 600
Shot 'a2_deal_in_late'
Start-Sleep -Seconds 3
Shot 'a3_ready'

Write-Output '== 2. 自标定（从日志读密度/版面，从截图量画布偏移）=='
$logTxt = (& $hdc -t $Device shell hilog -x 2>&1 | Out-String)
$m = [regex]::Match($logTxt, '画布=(\d+)x(\d+)px 密度换算=([0-9.]+).*格边=(\d+)px 棋盘原点=\((\d+),(\d+)\)')
if (-not $m.Success) {
  Write-Output '  !! 没读到布局日志，无法自标定。手动确认应用是否启动。'
  Logs 'GameController\] 布局' 5
  exit 3
}
$CANVAS_W = [int]$m.Groups[1].Value
$CANVAS_H = [int]$m.Groups[2].Value
$pxScale = [double]$m.Groups[3].Value
$DENS = 1.0 / $pxScale
$TILE = [int]$m.Groups[4].Value
$BOARD_X = [int]$m.Groups[5].Value
$BOARD_Y = [int]$m.Groups[6].Value
$probeImg = Join-Path $vdir ("$Tag`_probe.jpeg")
& $hdc -t $Device shell "snapshot_display -f /data/local/tmp/probe.jpeg" | Out-Null
& $hdc -t $Device file recv "/data/local/tmp/probe.jpeg" $probeImg | Out-Null
$cy = (python $probe $probeImg $BOARD_X $BOARD_Y 2>&1 | Out-String).Trim()
if ($cy -match 'CANVAS_Y=(-?\d+)') {
  $CANVAS_Y = [int]$Matches[1]
} else {
  Write-Output ("  !! 画布偏移探测失败(" + $cy + ")，按 0 处理")
  $CANVAS_Y = 0
}
Write-Output ("  画布 = " + $CANVAS_W + "x" + $CANVAS_H + "px  密度 = " + [math]::Round($DENS, 4) +
  "  格边 = " + $TILE + "px  棋盘原点 = (" + $BOARD_X + "," + $BOARD_Y + ")  画布顶偏移 = " + $CANVAS_Y + "px")

Write-Output '== 3. 菜单栏：开「游戏」，换高级 =='
$p = P $X_GAME $Y_TOP;        Tap $p[0] $p[1] 800
Shot 'b1_menu_open'
$p = P $X_DROP_GAME $Y_EXPERT; Tap $p[0] $p[1] 1500
Shot 'b2_expert'
Logs 'GameController\] 布局'

Write-Output '== 4. 回初级（菜单能反复切换）=='
$p = P $X_GAME $Y_TOP;        Tap $p[0] $p[1] 700
$p = P $X_DROP_GAME $Y_BEGINNER; Tap $p[0] $p[1] 1400
Shot 'c1_beginner'

Write-Output '== 5. 开一格（看洪泛涟漪）=='
$cell = PD ($BOARD_X + [math]::Round($TILE / 2)) ($BOARD_Y + [math]::Round($TILE / 2))
Tap $cell[0] $cell[1] 250
Shot 'd1_ripple'
Start-Sleep -Seconds 2
Shot 'd2_board'

Write-Output '== 6. 点满全盘直到终局（踩雷路径）=='
$step = [int]($TILE * 0.6)
for ($r = 0; $r -lt 12; $r++) {
  for ($c = 0; $c -lt 12; $c++) {
    $x = $BOARD_X + $c * $step
    $y = $BOARD_Y + $r * $step
    $q = PD $x $y
    Tap $q[0] $q[1] 80
  }
}
Shot 'e1_ending'
Start-Sleep -Milliseconds 700
Shot 'e2_ending_mid'
Start-Sleep -Seconds 3
Shot 'e3_dialog'
Logs '\[Dialog\]'

Write-Output '== 7. 结束对话框：点「再玩一局(P)」 =='
# loseSpec 参考像素：483x288，按钮 {x:323,y:236,w:144,h:26}；缩放 s=min(2,canvasW/1400)
$ds = [math]::Min(2.0, [math]::Max(1.0, $CANVAS_W / 1400.0))
$dx = [int](($CANVAS_W - 483 * $ds) / 2)
$dy = [int](($CANVAS_H - 288 * $ds) / 2)
$b3 = PD ($dx + (323 + 72) * $ds) ($dy + (236 + 13) * $ds)
Tap $b3[0] $b3[1] 1000
Shot 'f1_after_again'
Logs '\[Dialog\]'

Write-Output '== 8. 帮助菜单 → 帮助对话框 → 确定 =='
$p = P $X_HELP $Y_TOP;          Tap $p[0] $p[1] 800
Shot 'g1_help_menu'
$p = P $X_DROP_HELP 41;          Tap $p[0] $p[1] 900
Shot 'g2_help_dialog'
# helpSpec 参考像素：320x210，按钮 {x:110,y:170,w:100,h:25}；缩放同上 s
$hx = [int](($CANVAS_W - 320 * $ds) / 2)
$hy = [int](($CANVAS_H - 210 * $ds) / 2)
$ok = PD ($hx + (110 + 50) * $ds) ($hy + (170 + 12) * $ds)
Tap $ok[0] $ok[1] 800
Shot 'g3_help_closed'

Write-Output '== 9. 最佳成绩：统计窗口（左栏选难度 / 重置 / 关闭 / 标题栏红叉）=='
$p = P $X_GAME $Y_TOP;          Tap $p[0] $p[1] 700
$p = P $X_DROP_GAME $Y_BEST;   Tap $p[0] $p[1] 1200
Shot 'h1_stats'
Logs '\[Stats\]'
# 统计窗口：参考 702x254，缩放 ss=min(2,canvasW/1500)；左栏列表项 x=24,y=46+13*i
$ss = [math]::Min(2.0, [math]::Max(1.0, $CANVAS_W / 1500.0))
$sx = [int](($CANVAS_W - 702 * $ss) / 2)
$sy = [int](($CANVAS_H - 254 * $ss) / 2)
$item = PD ($sx + (24 + 20) * $ss) ($sy + (46 + 13 * 2 + 6) * $ss)
Tap $item[0] $item[1] 700
Shot 'h2_stats_select_expert'
Logs '\[Stats\]'
$closeBtn = PD ($sx + (336 + 77) * $ss) ($sy + (205 + 13) * $ss)
Tap $closeBtn[0] $closeBtn[1] 700
Shot 'h3_stats_closed'

Write-Output '== 10. 自定义难度对话框：数字键盘 + 确定 =='
$p = P $X_GAME $Y_TOP;           Tap $p[0] $p[1] 700
$p = P $X_DROP_GAME $Y_CUSTOM;   Tap $p[0] $p[1] 1200
Shot 'i1_custom'
Logs 'CustomField|\[Custom\]'

Write-Output '== 11. 长按插旗 =='
$c2 = PD ($BOARD_X + [math]::Round($TILE / 2)) ($BOARD_Y + [math]::Round($TILE / 2))
LongClick $c2[0] $c2[1]
Shot 'j1_flag'

Write-Output '== 12. 单指拖动（平移）=='
$pan1 = PD ($BOARD_X + [math]::Round($TILE * 2)) ($BOARD_Y + [math]::Round($TILE * 2))
$pan2 = PD ($BOARD_X + [math]::Round($TILE * 0.5)) ($BOARD_Y + [math]::Round($TILE * 0.5))
Drag $pan1[0] $pan1[1] $pan2[0] $pan2[1]
Shot 'k1_pan'

Write-Output '== 13. 日志汇总 =='
Logs 'JSAPP' 25

Write-Output ''
Write-Output ("证据图目录: " + $vdir)
Write-Output '注意：双指捏合无法用 uitest 注入，需要手动双指捏一下，'
Write-Output '      然后在 hilog 里找 [Touch] 捏合 档位n=… 这一行。'
