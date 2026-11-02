<#
  跑状态条七段数码管渲染器的单元测试（tools/sevenseg_test.ts）。

  测的是**应用仓里那份真的** SevenSeg.ets：
  runner 把它复制到临时目录，补一个 Canvas 类型桩，用 DevEco 自带的 tsc 转译，再交给 node 跑。

  为什么不用 node --test：
    - SevenSeg.ets 是 ArkTS/TS，import 的是相对路径的 .ets（node 不认）；
    - 规格仓里没有 node_modules，也不该装（全局约定禁止随手 npm install）；
    - 所以借 DevEco Studio 自带的 TypeScript 编译器转译到临时目录再跑。

  用法：
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_sevenseg_test.ps1
#>
param(
  [string]$AppRoot = 'C:\Users\19161\saolei',
  [string]$TscPath = 'D:\software\DevEco Studio\plugins\codelinter\node_modules\typescript\bin\tsc'
)

$ErrorActionPreference = 'Stop'

$sevenSeg = Join-Path $AppRoot 'entry\src\main\ets\common\SevenSeg.ets'
if (-not (Test-Path $sevenSeg)) {
  Write-Output "找不到渲染器：$sevenSeg"
  Write-Output '用 -AppRoot 指向应用仓目录。'
  exit 1
}
if (-not (Test-Path $TscPath)) {
  Write-Output "找不到 tsc：$TscPath"
  Write-Output '请改 -TscPath 指向本机任意 TypeScript 编译器的 bin\tsc。'
  exit 1
}

$tmp = Join-Path $env:TEMP ('ms_sevenseg_test_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try {
  Copy-Item $sevenSeg (Join-Path $tmp 'SevenSeg.ts')
  Copy-Item (Join-Path $PSScriptRoot 'sevenseg_dom_stub.d.ts') (Join-Path $tmp 'sevenseg_dom_stub.d.ts')
  Copy-Item (Join-Path $PSScriptRoot 'sevenseg_test.ts') (Join-Path $tmp 'sevenseg_test.ts')

  Push-Location $tmp
  try {
    & node $TscPath --target es2020 --module commonjs --moduleResolution node --skipLibCheck `
      --esModuleInterop --outDir $tmp $tmp\SevenSeg.ts $tmp\sevenseg_test.ts $tmp\sevenseg_dom_stub.d.ts 2>&1 |
      Where-Object { $_ -notmatch 'TS2307|TS2580' } | ForEach-Object { Write-Output $_ }

    if (-not (Test-Path (Join-Path $tmp 'sevenseg_test.js'))) {
      Write-Output '转译失败，没有产出测试文件。'
      exit 1
    }
    & node (Join-Path $tmp 'sevenseg_test.js')
    $rc = $LASTEXITCODE
  } finally {
    Pop-Location
  }
  exit $rc
} finally {
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
