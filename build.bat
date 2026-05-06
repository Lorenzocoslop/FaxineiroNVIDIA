@echo off
setlocal enabledelayedexpansion

set "MYPATH=%~dp0"

:: Detecta caminho UNC (começa com \\) e reloca pro %TEMP%
if "!MYPATH:~0,2!"=="\\" (
    set "DEST=%TEMP%\FaxineiroNVIDIA_build"
    mkdir "!DEST!" 2>nul
    copy /Y "%~f0" "!DEST!\build.bat" >nul
    copy /Y "!MYPATH!faxineiro.py" "!DEST!\faxineiro.py" >nul
    echo Relocando de caminho UNC para !DEST!...
    cmd /c "!DEST!\build.bat"
    exit /b
)

echo === Build Faxineiro NVIDIA ===
cd /d "%~dp0"

py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale em python.org e marque "Add Python to PATH".
    pause
    exit /b 1
)

py -m pip install pyinstaller pystray pillow --quiet

taskkill /f /im FaxineiroNVIDIA.exe >nul 2>&1
del /f "dist\FaxineiroNVIDIA.exe" >nul 2>&1

py -m PyInstaller --onefile --noconsole --name FaxineiroNVIDIA faxineiro.py
py -m PyInstaller --onefile --noconsole --name Uninstall uninstall.py

echo.
if exist dist\FaxineiroNVIDIA.exe (
    echo [OK] dist\FaxineiroNVIDIA.exe gerado.
    echo [OK] dist\Uninstall.exe gerado.
    start "" "%~dp0dist\FaxineiroNVIDIA.exe"
) else (
    echo [ERRO] Build falhou. Veja mensagens acima.
)
pause
