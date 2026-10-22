# Luau Desk — редактор Lua/Luau для Roblox Studio

**Luau Desk** — настольное приложение для Windows: вставляй Luau-код, редактируй его с подсветкой синтаксиса, открывай и сохраняй файлы `.lua` / `.luau`, копируй код и открывай Roblox Studio.

> Важно: это редактор, а не инжектор. Приложение не внедряет скрипты в работающий клиент Roblox и не обходит защиту чужих игр. Для тестирования вставляй код в `Script` или `LocalScript` своего проекта в Roblox Studio.

## Запуск из исходников

1. Установи Python 3.10 или новее: https://www.python.org/downloads/windows/
2. При установке включи **Add Python to PATH**.
3. Запусти `run.bat` или выполни в папке проекта:

   ```powershell
   python app.py
   ```

Дополнительные библиотеки для запуска не нужны: приложение использует Tkinter из стандартной поставки Python.

## Сборка EXE локально

Запусти `build_exe.bat`. Скрипт установит PyInstaller и создаст `dist\LuauDesk.exe`.

## Сборка через GitHub Actions

Workflow `.github/workflows/build-windows.yml` собирает Windows EXE. В GitHub открой **Actions**, выбери запуск **Build Luau Desk for Windows** и скачай артефакт `LuauDesk-Windows`.

## Возможности

- редактор с базовой подсветкой синтаксиса и номерами строк;
- создание, открытие и сохранение `.lua` и `.luau`;
- копирование кода в буфер обмена;
- попытка открыть установленный Roblox Studio;
- горячие клавиши `Ctrl+N`, `Ctrl+O`, `Ctrl+S`.

## Использование

1. Напиши или вставь код в Luau Desk.
2. Нажми **Код + Studio** или **Копировать код**.
3. В Roblox Studio добавь `Script` или `LocalScript` в подходящий объект своего проекта.
4. Вставь код и проверь его в режиме Play.
