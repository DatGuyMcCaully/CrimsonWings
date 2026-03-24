@echo off
:: ─────────────────────────────────────────────────────────────────
::  Build CrimsonWings.exe
::  Run this once on any Windows machine that has Python 3.8+ installed.
::  The .exe will appear in the "dist" subfolder next to this script.
:: ─────────────────────────────────────────────────────────────────

echo Installing / verifying PyInstaller...
pip install pyinstaller --quiet

echo.
echo Building exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "CrimsonWings" ^
  --icon "icon.ico" ^
  --add-data "icon.ico;." ^
  cd_glide_patcher.py

echo.
if exist dist\CrimsonWings.exe (
  echo SUCCESS: dist\CrimsonWings.exe is ready.
) else (
  echo FAILED: something went wrong. Check the output above.
)
echo.
pause
