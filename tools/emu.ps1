# emu.ps1 —— 用本机 HarmonyOS 模拟器（Mate X7 折叠屏）做验证
#
# 为什么需要它：真机拔掉以后，很多"只有运行时才暴露"的问题（AVPlayer 状态机、
# 触摸路由、对话框命中）必须跑起来才看得到。DevEco 自带模拟器，本机已装好
# Mate X7（foldable、API 26.0.0、x86_64、2210x2416 @ density 500）。
#
# 用法：
#   powershell -File tools\emu.ps1 -Action start      # 启动并等 hdc 目标出现
#   powershell -File tools\emu.ps1 -Action stop       # 关闭
#   powershell -File tools\emu.ps1 -Action status     # 看状态
#   powershell -File tools\emu.ps1 -Action fold -Fold closed   # 折起来（或 open）
#   powershell -File tools\emu.ps1 -Action shot -Name xxx      # 截图到 docs\verify
#
# 注意：
#   1) 必须用 Start-Process 脱离启动。用 Start-Job / 前台跑，工具调用结束时
#      模拟器会被一起清理掉（2026-10-31 踩过）。
#   2) 首次要 -license accept，否则起不来。
#   3) 引导约 60~90 秒（镜像校验 system.img 就要 40 秒），hdc 里会出现
#      127.0.0.1:5555 这个目标。

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('start', 'stop', 'status', 'fold', 'shot', 'install', 'launch')]
  [string]$Action,
  [string]$Fold = 'closed',
  [string]$Name = 'shot',
  [string]$Instance = 'Mate X7'
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$vdir = Join-Path $root 'docs\verify'
New-Item -ItemType Directory -Force -Path $vdir | Out-Null

$emu = 'D:\software\DevEco Studio\tools\emulator\Emulator.exe'
$hdc = 'D:\software\DevEco Studio\sdk\default\openharmony\toolchains\hdc.exe'
$hap = 'C:\Users\19161\saolei\entry\build\default\outputs\default\entry-default-signed.hap'
$pkg = 'com.example.saolei'
$dev = '127.0.0.1:5555'

function Get-Target {
  return (& $hdc list targets 2>&1 | Out-String).Trim()
}

switch ($Action) {
  'start' {
    & $emu -license accept | Out-Null
    Start-Process -FilePath $emu -ArgumentList '-start', "`"$Instance`"" -WindowStyle Minimized | Out-Null
    Write-Output '已发出启动命令，等待目标出现（最多 180 秒）...'
    for ($i = 1; $i -le 30; $i++) {
      Start-Sleep -Seconds 6
      $t = Get-Target
      if ($t -match '127\.0\.0\.1') {
        Write-Output ("  目标已出现: " + $t)
        exit 0
      }
    }
    Write-Output '  超时未出现目标，去看模拟器窗口与 Emulator.log'
    exit 1
  }
  'stop' {
    & $emu -stop $Instance | Out-Null
    Write-Output '已请求关闭'
  }
  'status' {
    $t = Get-Target
    $p = (Get-Process -Name Emulator -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Output ("  hdc targets: [" + $t + "]    Emulator 进程数: " + $p)
  }
  'fold' {
    $state = if ($Fold -eq 'closed') { 'closed' } else { 'opened' }
    & $emu -instance $Instance -foldedState $state | Out-Null
    Write-Output ("  已切换折叠状态: " + $state)
  }
  'shot' {
    $out = Join-Path $vdir ("$Name.jpeg")
    Remove-Item $out -ErrorAction SilentlyContinue
    & $hdc -t $dev shell "snapshot_display -f /data/local/tmp/$Name.jpeg" | Out-Null
    & $hdc -t $dev file recv "/data/local/tmp/$Name.jpeg" $out | Out-Null
    Write-Output ("  截图: " + $out)
  }
  'install' {
    & $hdc -t $dev install -r $hap | Select-Object -Last 1 | ForEach-Object { Write-Output ("  " + $_) }
  }
  'launch' {
    & $hdc -t $dev shell aa force-stop $pkg | Out-Null
    & $hdc -t $dev shell hilog -r | Out-Null
    & $hdc -t $dev shell "aa start -a EntryAbility -b $pkg" | Out-Null
    Write-Output '  已启动（日志已清空）'
  }
}
