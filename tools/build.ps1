<#
  build.ps1 —— 命令行构建鸿蒙工程

  DevEco Studio 自带 hvigor / SDK，不需要单独装 Command Line Tools。
  但命令行构建必须显式告诉 hvigor SDK 在哪：环境变量 DEVECO_SDK_HOME。

  用法：
    powershell -File tools\build.ps1                # 构建 debug HAP
    powershell -File tools\build.ps1 -Release
#>
param(
  [switch]$Release,
  [string]$Project = 'C:\Users\19161\saolei'
)

$ErrorActionPreference = 'Continue'

$deveco = 'D:\software\DevEco Studio'
$sdk = Join-Path $deveco 'sdk'
$hvigorw = Join-Path $deveco 'tools\hvigor\bin\hvigorw.bat'

if (-not (Test-Path $hvigorw)) {
  throw "找不到 hvigorw：$hvigorw"
}

$env:DEVECO_SDK_HOME = $sdk
$env:OHOS_SDK_HOME = $sdk

$mode = if ($Release) { 'release' } else { 'debug' }
$log = Join-Path $PSScriptRoot '..\build.log'

Set-Location $Project
Write-Output "构建 $mode ..."
& $hvigorw --mode module -p product=default -p module=entry@default -p buildMode=$mode assembleHap --no-daemon *>&1 |
  Tee-Object -FilePath $log | Out-Null

$code = $LASTEXITCODE
Write-Output "==== 错误 ===="
Select-String -Path $log -Pattern "ERROR:|Error Message:" -ErrorAction SilentlyContinue |
  Select-Object -First 30 | ForEach-Object { Write-Output ("  " + $_.Line.Trim()) }
Write-Output "==== 结果 ===="
Select-String -Path $log -Pattern "COMPILE RESULT|BUILD (FAILED|SUCCESSFUL)" -ErrorAction SilentlyContinue |
  Select-Object -Last 3 | ForEach-Object { Write-Output ("  " + $_.Line.Trim()) }

if ($code -eq 0) {
  $hap = Get-ChildItem (Join-Path $Project 'entry\build\default\outputs\default') -Filter '*.hap' -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($hap) {
    Write-Output ("HAP: " + $hap.FullName + "  (" + ('{0:N0}' -f $hap.Length / 1KB) + " KB)")
  }
}
exit $code
