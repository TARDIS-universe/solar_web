@echo off
setlocal

:: Path to the entry point.
set "ENTRY=main.py"

:: Executable metadata.
set "NAME=Solar"
set "ICON=%~dp0icon.png"

:: Choose console mode:
::   - Leave CONSOLE undefined (default) for a GUI build without a console window.
::   - Set CONSOLE=1 before running this batch file if you want the console visible.
if /i "%CONSOLE%"=="1" (
    set "CONSOLE_FLAG=--console"
) else (
    set "CONSOLE_FLAG=--windowed"
)

:: Assemble the PyInstaller flags.
set "FLAGS=--noconfirm --clean --onefile --name %NAME% %CONSOLE_FLAG%"
if exist "%ICON%" (
    set "FLAGS=%FLAGS% --icon "%ICON%""
) else (
    echo Warning: icon file not found at %ICON%, proceeding without an icon.
)

pyinstaller %FLAGS% "%ENTRY%"

if %ERRORLEVEL% equ 0 (
    echo Build succeeded. Executable is in dist\%NAME%.exe
) else (
    echo Build failed with exit code %ERRORLEVEL%.
)

endlocal
