# Windows desktop tools: ScriptDeck, MacroDesk, LuauDesk

This repository contains three small Windows desktop applications.

## ScriptDeck — dark Lua / Luau workspace

ScriptDeck provides a dark, executor-inspired editor workspace with tabs, syntax coloring, a saved-script library, an output panel, local CLI execution and export for your own Roblox experience.

**Important limitation:** ScriptDeck is a script editor and local runner, not a Roblox-client injector. Its Execute button runs general Lua/Luau through a separately installed CLI on your computer; Roblox APIs such as `game`, `workspace`, and `Players` are not available in that separate process. Exporting scripts into a project and running them in your own experience uses Roblox Studio and Rojo. The app does not inject code into the Roblox process or bypass client protection.

### Run on Windows
1. Install Python 3.10+ from https://www.python.org/downloads/windows/ and enable **Add Python to PATH**.
2. Download or clone this repository.
3. Double-click `run_scriptdeck.bat`.

### Build ScriptDeck.exe
Double-click `build_scriptdeck.bat`. The EXE is created at `dist\ScriptDeck.exe`. Build it on Windows for a Windows executable. The first build requires internet access to install PyInstaller.

### ScriptDeck features
- Multiple tabs for Lua / Luau source files.
- Syntax coloring, open/save, and script library stored in `%APPDATA%\ScriptDeck\Scripts`.
- Local CLI run via `luau.exe` or `lua.exe` on PATH, with a 10-second process timeout.
- Export as Server Script, LocalScript or ModuleScript into the `src/` folder structure of your own Roblox project.
- F5 to run locally; Ctrl+N / Ctrl+O / Ctrl+S for new/open/save.

## MacroDesk — keyboard macro editor

MacroDesk manages profiles of normal desktop keyboard actions (paste text, press a key or key combination, wait, open a URL). It supports configurable run/stop hotkeys and JSON profile import/export.

Run `run_macrodesk.bat` to install dependencies and start from source. Use `build_macrodesk.bat` to build a Windows EXE. MacroDesk is a general desktop automation tool; use it only where automation is allowed. It does not inject scripts into Roblox or automate mouse clicks.

## LuauDesk — Roblox Studio project editor

LuauDesk edits Lua / Luau and exports scripts into your own Roblox Studio project through Rojo. It does not execute arbitrary code in the live Roblox client.

Run `run.bat` to start from source or `build_exe.bat` to build the EXE. Rojo setup: https://rojo.space/docs/v7/getting-started/installation/

## CI build

GitHub Actions validates all Python files, builds the three Windows executables and uploads them as the `Windows-Apps` artifact. Open the Actions tab, select the latest successful build, and download that artifact ZIP.
