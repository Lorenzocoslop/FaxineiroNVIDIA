@echo off
echo === Build Faxineiro NVIDIA ===

:: Instala dependências de build se não tiver
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

:: Gera o .exe standalone (sem console = roda invisível em background)
pyinstaller --onefile --noconsole --name FaxineiroNVIDIA faxineiro.py

echo.
if exist dist\FaxineiroNVIDIA.exe (
    echo [OK] Gerado: dist\FaxineiroNVIDIA.exe
    echo Distribua esse arquivo. Usuario so precisa clicar uma vez.
) else (
    echo [ERRO] Build falhou. Verifique os logs acima.
)
pause
