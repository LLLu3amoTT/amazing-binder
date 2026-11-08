@echo off
chcp 65001 > nul
title Amazing RP Binder Launcher

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Запуск от имени администратора...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo [1/2] Проверка зависимостей...
py -c "import keyboard, PIL"
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Установите библиотеки: pip install -r requirements.txt
    echo.
    pause
    exit /b
)

echo [2/2] Запуск биндера...
py binder.py

echo.
echo =======================================================
echo Скрипт завершил работу. Если была ошибка — она выше.
echo =======================================================
pause