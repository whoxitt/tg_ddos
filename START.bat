@echo off
chcp 65001 >nul
echo ====================================
echo  Telegram Auto Sender (Простая версия)
echo ====================================
echo.

python telegram_sender_simple.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось запустить программу!
    echo.
    echo Убедитесь что:
    echo 1. Python установлен
    echo 2. Установлена библиотека telethon: pip install telethon
    echo.
)

pause
