@echo off
echo === Instalacion de Loki ===
echo.

set "SCRIPT_DIR=%~dp0.."

echo Creando entorno virtual...
if not exist "%SCRIPT_DIR%\.venv\" (
    python -m venv "%SCRIPT_DIR%\.venv"
    if %errorlevel% neq 0 (
        echo ERROR: no se pudo crear el venv. Verifica que Python este en el PATH.
        pause
        exit /b 1
    )
)

echo Instalando dependencias de Python en el venv...
"%SCRIPT_DIR%\.venv\Scripts\pip" install -r "%SCRIPT_DIR%\requirements.txt"
if %errorlevel% neq 0 (
    echo ERROR: fallo pip install.
    pause
    exit /b 1
)

echo.
echo Registrando el arranque de Loki con Windows...
set "PYTHONW=%SCRIPT_DIR%\.venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=%SCRIPT_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHONW%" (
    echo ERROR: no se encontro el Python del venv. La instalacion pudo haber fallado.
    pause
    exit /b 1
)

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "Loki" ^
    /t REG_SZ ^
    /d "\"%PYTHONW%\" -m loki.main" ^
    /f

echo.
echo Listo.
echo - Loki va a arrancar solo la proxima vez que inicies sesion en Windows.
echo - Para arrancarlo ahora sin reiniciar: "%PYTHONW%" -m loki.main
echo - Antes de arrancarlo por primera vez, copia y completa config.local.example.yaml
echo   como config.local.yaml, y .env.example como .env (ver README.md).
echo.
pause
