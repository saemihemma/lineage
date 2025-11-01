@echo off
REM Sync data files from project root to frontend public directory
REM Run this when you update text files in data/ directory

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set DATA_DIR=%PROJECT_ROOT%\data
set FRONTEND_PUBLIC=%PROJECT_ROOT%\frontend\public\data

echo Syncing data files to frontend...

REM Create destination directory if it doesn't exist
if not exist "%FRONTEND_PUBLIC%" mkdir "%FRONTEND_PUBLIC%"

REM Copy JSON data files
if exist "%DATA_DIR%\briefing_text.json" (
  copy /Y "%DATA_DIR%\briefing_text.json" "%FRONTEND_PUBLIC%\briefing_text.json" >nul
  echo Copied briefing_text.json
)

if exist "%DATA_DIR%\loading_text.json" (
  copy /Y "%DATA_DIR%\loading_text.json" "%FRONTEND_PUBLIC%\loading_text.json" >nul
  echo Copied loading_text.json
)

echo Done! Frontend data files synced.
echo.
echo Note: Changes will be visible on next browser refresh (no rebuild needed).

