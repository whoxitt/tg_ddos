@echo off
chcp 65001 >nul
echo ====================================
echo  Установка Telegram Auto Sender
echo ====================================
echo.

echo [1/2] Проверка Python...
python --version
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Python не найден!
    echo.
    echo Установите Python с https://www.python.org/downloads/
    echo При установке отметьте "Add Python to PATH"
    pause
    exit /b 1
)

echo.
echo [2/2] Установка зависимостей...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости!
    pause
    exit /b 1
)

echo.
echo ====================================
echo  Установка завершена успешно!
echo ====================================
echo.
echo Запустите программу: python telegram_sender.py
echo.
pause
