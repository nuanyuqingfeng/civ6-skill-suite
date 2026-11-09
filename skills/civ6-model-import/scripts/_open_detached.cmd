@echo off
rem ---------------------------------------------------------------------------
rem STAGE 2 - detached executor for "open a Civ6 model in Blender".
rem
rem This file is launched by explorer.exe (the Session-1 desktop shell), NOT by
rem a cmd.exe belonging to an agent command session. It starts Blender and then
rem exits, so Blender has NO live parent inside any agent session tree and is
rem never reaped when that session/command ends.
rem
rem Target resolution: %TEMP%\civ6_open_model_target.txt (written by stage 1);
rem if absent, CIV6_DEFAULT_MODEL is used. Double-click = default, drag&drop = target.
rem ---------------------------------------------------------------------------
setlocal
if not defined CIV6_BLENDER_HOME    set "CIV6_BLENDER_HOME=E:\SoftWares\blender45\blender-4.5.9-windows-x64"
if not defined CIV6_BLENDER_USERRES set "CIV6_BLENDER_USERRES=E:\SoftWares\blender45\userres"
if not defined CIV6_OPEN_MODEL_PY   set "CIV6_OPEN_MODEL_PY=E:\SoftWares\blender45\open_model.py"
if not defined CIV6_DEFAULT_MODEL   set "CIV6_DEFAULT_MODEL=E:\SoftWares\civ6_nexus_work\dj_stage_s2b\LEAD_DJ_DANJIN_QYQXP.cn6"

set "BLENDER_USER_RESOURCES=%CIV6_BLENDER_USERRES%"
set "MODEL=%CIV6_DEFAULT_MODEL%"
set "TARGET_FILE=%TEMP%\civ6_open_model_target.txt"
if exist "%TARGET_FILE%" (
  for /f "usebackq delims=" %%A in ("%TARGET_FILE%") do if not "%%A"=="" set "MODEL=%%A"
)

>>"%TEMP%\civ6_open_model_launch.log" echo LAUNCH %DATE% %TIME% MODEL=%MODEL% EXECUTOR=%~f0
cd /d "%CIV6_BLENDER_HOME%"
start "" "%CIV6_BLENDER_HOME%\blender.exe" --python "%CIV6_OPEN_MODEL_PY%" -- "%MODEL%"
endlocal
exit /b 0
