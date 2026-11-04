<#
.SYNOPSIS
    让 HarmonyOS 设备（默认那台华为平板）**一直亮屏**，不用手动解锁、不用再点。

.DESCRIPTION
    背景（2026-11-04 实测）：
      * `power-shell timeout -o 7200000` 把「息屏倒计时」设成 2 小时，
        但它是**一次性**的：倒计时走完，屏幕照样黑。
      * 屏幕黑掉之后 `aa start` 会静默失败：
        `Error Code:10106102 The device screen is locked during the application launch`
        —— 这正是跑测器整轮用例集体失败、却查不出原因的那个坑。
      * `power-shell wakeup` 只是把屏幕**点亮**，**解锁**还得人来划；
        但只要不熄屏，keyguard 就不会出现，锁屏这条坎就绕过去了。

    所以这个脚本做的事就是一个**看门狗循环**：
      每隔几分钟把息屏倒计时**重新拉满**，屏幕就一直亮着。

    **它不需要任何 token、不需要联网、不需要 AI**：
    只调本机 hdc.exe 的两条 shell 命令，纯 PowerShell。

    要停就按 Ctrl+C。

.PARAMETER Device
    设备地址。默认那台华为平板 3KQYD25331202962。

.PARAMETER KeepMs
    每次把息屏倒计时设成多少毫秒。默认 7200000（= 2 小时）。

.PARAMETER RefreshSec
    隔多少秒重新拉一次倒计时。
    必须**明显小于** KeepMs（否则倒计时会先走完）。
    默认 300（5 分钟）。

.PARAMETER LogPath
    日志文件路径。留空则只写控制台。
    传一个路径就同时落盘（后台跑、关掉窗口也留得住痕迹）。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\keep_awake.ps1

.EXAMPLE
    # 后台跑，并把日志写到文件
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\keep_awake.ps1 `
        -LogPath D:\software\harmony\projects\minesweeper\docs\verify\keep_awake.log
#>
[CmdletBinding()]
param(
    [string]$Device = '3KQYD25331202962',
    [int]$KeepMs = 7200000,
    [int]$RefreshSec = 300,
    [string]$LogPath = ''
)

$ErrorActionPreference = 'Continue'

# hdc.exe 的位置：DevEco Studio 自带的那份
$HdcCandidates = @(
    'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe',
    "$env:DEVECO_SDK_HOME\toolchains\hdc.exe",
    "$env:LOCALAPPDATA\Huawei\Sdk\openharmony\toolchains\hdc.exe"
)
$Hdc = $null
foreach ($c in $HdcCandidates) {
    if ($c -and (Test-Path -LiteralPath $c)) { $Hdc = $c; break }
}
if (-not $Hdc) {
    # 退一步：在 PATH 里找
    $cmd = Get-Command hdc.exe -ErrorAction SilentlyContinue
    if ($cmd) { $Hdc = $cmd.Source }
}
if (-not $Hdc) {
    Write-Output '[keep_awake] 找不到 hdc.exe，请用 -Hdc 显式指定路径'
    exit 2
}

$logFh = $null
if ($LogPath) {
    try {
        $dir = Split-Path -Parent $LogPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        $logFh = New-Object System.IO.StreamWriter($LogPath, $true, [Text.Encoding]::UTF8)
        $logFh.AutoFlush = $true
    } catch {
        Write-Output ('[keep_awake] 日志开不了（继续跑，只写控制台）: ' + $_.Exception.Message)
        $logFh = $null
    }
}

function Write-Both([string]$msg) {
    Write-Output $msg
    if ($logFh) { try { $logFh.WriteLine($msg) } catch { } }
}

$msg1 = '[keep_awake] 开始看门狗：设备 {0}；每 {1} 秒把息屏倒计时拉回 {2} ms' -f $Device, $RefreshSec, $KeepMs
Write-Both $msg1
Write-Both '[keep_awake] 停止：Ctrl+C'

# 试一把：把**持久化**的息屏超时也改了。
# 成了就一劳永逸；不成也无所谓 —— 下面那个循环本来就能一直兜着。
# 注意（2026-11-05 实测）：这台设备上 `param get` **读不回来**
# （errNum 1002，系统参数不暴露），所以 SET 回显的 "success" 无法回读验证；
# 真正能验证的是下面的 `power-shell timeout -o` 覆盖值（hidumper 读得到）。
try {
    $out = & $Hdc -t $Device shell "param set persist.ace.timeout.screen.off $KeepMs" 2>&1
    $txt = ($out | Out-String).Trim()
    Write-Both ('[keep_awake] 试过改持久化息屏超时（该机读不回来，改了也验证不了，靠循环兜着）: ' + $txt)
} catch {
    Write-Both '[keep_awake] 持久化参数那一步出错（可忽略）'
}

# 自检：把覆盖值读回来，证明「真的生效了」。
# 坑（2026-11-05）：`power-shell timeout -o` 的单位是**毫秒**，
# 写成 7200 会被当成 7.2 秒 —— 看着像设了 2 小时，其实几秒就黑屏。
function Test-Override {
    try {
        $d = & $Hdc -t $Device shell "hidumper -s PowerManagerService -a -s" 2>&1 | Out-String
        if ($d -match 'OverrideTimeout=(\d+)ms') {
            return [int]$Matches[1]
        }
    } catch { }
    return -1
}
$ov = Test-Override
if ($ov -ge 0) {
    Write-Both ('[keep_awake] 自检：当前息屏覆盖值 = {0} ms' -f $ov)
}

$lastErr = ''
while ($true) {
    try {
        # 点亮（已经是亮的也无妨）
        & $Hdc -t $Device shell "power-shell wakeup" 2>&1 | Out-Null
        # 把息屏倒计时拉满
        & $Hdc -t $Device shell "power-shell timeout -o $KeepMs" 2>&1 | Out-Null
        $msg2 = '[keep_awake] {0} 已刷新（息屏倒计时 = {1} ms）' -f (Get-Date -Format 'HH:mm:ss'), $KeepMs
        Write-Both $msg2
    } catch {
        $e = $_.Exception.Message
        if ($e -ne $lastErr) {
            Write-Both ('[keep_awake] {0} 这一轮出错（会重试）: {1}' -f (Get-Date -Format 'HH:mm:ss'), $e)
            $lastErr = $e
        }
    }
    Start-Sleep -Seconds $RefreshSec
}
