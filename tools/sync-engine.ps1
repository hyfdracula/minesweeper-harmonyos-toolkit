<#
  sync-engine.ps1 —— 把逻辑层源码同步进鸿蒙工程的 .ets 文件

  逻辑层用 .ts 维护（为了能用 Node 直接跑离线测试），
  鸿蒙工程里 ArkTS 只认 .ets，所以每次改动逻辑层后跑一次这个脚本。

  用法：
    powershell -File tools\sync-engine.ps1 -ProjectRoot D:\software\harmony\projects\minesweeper\harmony
#>
param(
  [string]$ProjectRoot = 'D:\software\harmony\projects\minesweeper\harmony',
  [string]$SourceDir  = (Join-Path $PSScriptRoot '..\engine\src'),
  [string]$DestDir    = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($DestDir)) {
  $DestDir = Join-Path $ProjectRoot 'entry\src\main\ets\common'
}

if (-not (Test-Path $SourceDir)) {
  throw "源目录不存在：$SourceDir"
}

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

$copied = 0
Get-ChildItem -Path $SourceDir -Filter '*.ts' | ForEach-Object {
  $dest = Join-Path $DestDir ($_.BaseName + '.ets')
  Copy-Item -Path $_.FullName -Destination $dest -Force
  Write-Output ("  synced  " + $_.Name + "  ->  " + $dest)
  $copied++
}

Write-Output ("同步完成：" + $copied + " 个文件 -> " + $DestDir)
