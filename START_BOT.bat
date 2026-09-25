@echo off
chcp 65001 >nul
echo ====================================
echo  Telegram Auto Sender BOT
echo ====================================
echo.

python telegram_bot.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить бота!
    echo.
    echo Убедитесь что:
    echo 1. Python установлен
    echo 2. Установлены библиотеки: pip install python-telegram-bot telethon pysocks
    echo.
)

pause
