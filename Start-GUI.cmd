@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -X utf8 -m game_localizer.gui --workspace work/gui
) else (
  python -X utf8 -m game_localizer.gui --workspace work/gui
)
if errorlevel 1 (
  echo GUI could not start. Install Python 3.10 or newer, then try again.
  pause
)
