@echo off
chcp 65001 >nul
echo ====================================
echo  Telegram Auto Message Sender
echo ====================================
echo.

python telegram_sender.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить программу!
    echo.
    echo Убедитесь что:
    echo 1. Python установлен
    echo 2. Выполнили install.bat
    echo.
)

pause
