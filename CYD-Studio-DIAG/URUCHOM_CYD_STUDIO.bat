    @echo off
    setlocal EnableExtensions
    title CYD Studio DIAG 2.34 - LCD TEXT FIX
    cd /d "%~dp0"
    if not exist "launch_studio.py" (
      echo BLAD: Rozpakuj caly ZIP; brakuje launch_studio.py.
      pause
      exit /b 1
    )
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0START.ps1"
    if errorlevel 1 (
      echo.
      echo WYSTAPIL BLAD URUCHAMIANIA - skopiuj komunikaty z tego okna.
    ) else (
      echo.
      echo CYD Studio zostalo zamkniete.
    )
    pause