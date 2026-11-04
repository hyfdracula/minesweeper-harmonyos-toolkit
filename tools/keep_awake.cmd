@echo off
REM 双击就能跑：让那台华为平板一直亮屏（不用 token、不用 AI）。
REM 关掉这个黑窗口就停。
setlocal
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

echo 正在让平板保持亮屏...（关掉本窗口即停止）
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0keep_awake.ps1" %*

if errorlevel 1 (
  echo.
  echo [keep_awake] 退出了，错误码 %errorlevel%
  pause
)
endlocal
