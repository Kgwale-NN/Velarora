@echo off
cd /d "%~dp0.."
REM ─────────────────────────────────────────────────────────────────────────
REM  Velarora — build script
REM  Run from repo root:  scripts\build.bat
REM ─────────────────────────────────────────────────────────────────────────

echo.
echo [1/4] Checking Python environment...

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found.
    echo Create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\Activate.ps1
    echo   pip install -e ".[dev,build]"
    pause
    exit /b 1
)

REM Use the environment Python directly; activation scripts may contain old paths.
echo    Using .venv\Scripts\python.exe

echo.
echo [2/4] Checking build tools...

".venv\Scripts\python.exe" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found in venv. Installing...
    ".venv\Scripts\python.exe" -m pip install "pyinstaller>=6.0"
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import nicegui" >nul 2>&1
if errorlevel 1 (
    echo ERROR: nicegui not found in venv. Run:
    echo   pip install -e ".[dev,build]"
    pause
    exit /b 1
)

echo    PyInstaller: OK
echo    nicegui: OK

echo.
echo [3/4] Running build.py...
".venv\Scripts\python.exe" scripts\build.py
if errorlevel 1 (
    echo.
    echo Build FAILED. See errors above.
    pause
    exit /b 1
)

echo.
echo [4/4] Done!
echo.
echo   Distribute the folder:  dist\
echo   Users run:               dist\Velarora.exe
echo.
pause
