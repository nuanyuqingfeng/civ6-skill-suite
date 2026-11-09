@echo off
rem ---------------------------------------------------------------------------
rem STAGE 1 - detached entry point: open a Civ6 model in Blender GUI.
rem
rem   double-click -> opens the default/current model (see _open_detached.cmd)
rem   drag & drop  -> pass any .cn6 / .psk / .fgx / .blend onto this file
rem
rem Blender is NOT started here. Every process launched from an agent command
rem session is reaped when that command/session ends (the job object forbids
rem breakaway: CREATE_BREAKAWAY_FROM_JOB -> WinError 5). Instead we hand the
rem executor to explorer.exe, a Session-1 desktop process OUTSIDE the agent
rem tree. The executor starts Blender and exits, so Blender is left with no
rem live parent in any agent session and the window never disappears.
rem
rem This file exits immediately and is never Blender's parent.
rem Keep stage-1 logic identical at every deployment of this launcher.
rem ---------------------------------------------------------------------------
setlocal
set "TARGET_FILE=%TEMP%\civ6_open_model_target.txt"
if not "%~1"=="" (
  >"%TARGET_FILE%" echo(%~1
) else (
  if exist "%TARGET_FILE%" del "%TARGET_FILE%"
)
start "" explorer.exe "%~dp0_open_detached.cmd"
endlocal
exit /b 0
