<#
  跑引擎单元测试（engine/test/engine.test.ts）。

  为什么不直接 `node --test`：
    - 引擎是 TypeScript，用的是 **enum**，node --experimental-strip-types 不支持 enum；
    - 规格仓里没有 node_modules（也不该装 —— 全局约定禁止随手 pip/npm install）；
    - 所以这里借 **DevEco Studio 自带的 TypeScript 编译器**转译到临时目录再跑。
      DevEco 装了就自带 tsc，不用联网、不装任何东西。

  用法：
    powershell -NoProfile -ExecutionPolicy Bypass -File tools\run_engine_tests.ps1
  #>
param(
  [string]$EngineRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) 'engine'),
  [string]$TscPath = 'D:\software\DevEco Studio\plugins\codelinter\node_modules\typescript\bin\tsc'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $TscPath)) {
  Write-Output "找不到 tsc：$TscPath"
  Write-Output "请改 -TscPath 指向本机任意 TypeScript 编译器的 bin\tsc。"
  exit 1
}

$tmp = Join-Path $env:TEMP ('ms_engine_test_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path (Join-Path $tmp 'src'), (Join-Path $tmp 'test') | Out-Null

Copy-Item (Join-Path $EngineRoot 'src\MinesweeperEngine.ts') (Join-Path $tmp 'src\MinesweeperEngine.ts')
$testSrc = Join-Path $tmp 'test\engine.test.ts'
Copy-Item (Join-Path $EngineRoot 'test\engine.test.ts') $testSrc

# 测试文件里 import 用的是 '../src/MinesweeperEngine.ts'（TS 允许，node 不认），
# 转译后改成 .js。--allowImportingTsExtensions 在这个 tsc 版本上不存在，靠改 import 绕开。
(Get-Content $testSrc -Raw) -replace "'\.\./src/MinesweeperEngine\.ts'", "'../src/MinesweeperEngine.js'" |
  Set-Content $testSrc -NoNewline

# --esModuleInterop 是必需的：测试里 `import assert from 'node:assert/strict'` 用的是默认导入，
# 没有这个开关 assert 会是 undefined，报 "Cannot read properties of undefined (reading 'equal')"。
& node $TscPath --target es2020 --module commonjs --moduleResolution node --skipLibCheck `
  --esModuleInterop --outDir (Join-Path $tmp 'out') `
  (Join-Path $tmp 'src\MinesweeperEngine.ts') $testSrc 2>&1 |
  Where-Object { $_ -notmatch 'TS2307|TS2580' } | ForEach-Object { Write-Output $_ }

$outDir = Join-Path $tmp 'out'
if (-not (Test-Path (Join-Path $outDir 'test\engine.test.js'))) {
  Write-Output '转译失败，没有产出测试文件。'
  exit 1
}

Push-Location $outDir
try {
  $log = & node --test test/engine.test.js 2>&1 | Out-String
  # node 的 TAP 输出里每个用例是 "ok N - 标题"，失败是 "not ok N - 标题"
  $ok = ([regex]::Matches($log, '(?m)^\s*ok\s+\d')).Count
  $notOk = ([regex]::Matches($log, '(?m)^\s*not ok\s+\d')).Count
  # 末尾还有一行汇总 "41 passed, 0 failed"，它是权威口径（用例行可能被 node 折叠）
  $summary = [regex]::Match($log, '(?m)^(\d+) passed, (\d+) failed')
  if ($summary.Success) {
    Write-Output ("node 汇总: {0} passed, {1} failed" -f $summary.Groups[1].Value, $summary.Groups[2].Value)
    $ok = [int]$summary.Groups[1].Value
    $notOk = [int]$summary.Groups[2].Value
  }
  Write-Output ("通过用例 {0}，失败用例 {1}" -f $ok, $notOk)
  if ($notOk -gt 0) {
    Write-Output '--- 失败详情 ---'
    $log -split "`r?`n" | Where-Object { $_ -match '^not ok|AssertionError|expected|actual' } |
      Select-Object -First 40 | ForEach-Object { Write-Output $_ }
    exit 1
  }
  Write-Output '引擎测试全部通过。'
} finally {
  Pop-Location
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
