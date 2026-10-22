# LuauDesk — Roblox Luau Editor for Windows

Desktop app for editing Lua/Luau scripts and syncing them into **your own Roblox Studio experience** through Rojo.

> LuauDesk does not inject code into a running Roblox client. Use Roblox Studio's Play/Test workflow to run your own game scripts.

## Run on Windows

1. Install Python 3.10+ from https://www.python.org/downloads/windows/ (enable **Add Python to PATH**).
2. Download or clone this repository.
3. Double-click `run.bat`.

The app uses Python's standard library and Tkinter. It does not need extra packages to run from source.

## Build an EXE

Double-click `build_exe.bat`. It installs PyInstaller and builds `dist\LuauDesk.exe`. Internet access is needed for the first build to install PyInstaller. The EXE should be built on Windows for Windows.

## Connect to Roblox Studio

1. Install the Rojo CLI and Roblox Studio plugin: https://rojo.space/docs/v7/getting-started/installation/
2. With Rokit, the CLI installation commands are `rokit add rojo-rbx/rojo` and `rokit install`.
3. Install the Studio plugin with `rojo plugin install`.
4. Open LuauDesk, choose this repository/project folder and click **Запустить Rojo / sync** (or run `rojo serve` here).
5. In Roblox Studio, open the Rojo plugin and press **Connect**.
6. Paste your code, choose the target service and click **Экспорт в проект**. Press **Play** in Studio; check **View → Output** for messages/errors.

Rojo maps these folders to Roblox instances:

- `src/server/*.server.lua` → `ServerScriptService` Scripts
- `src/client/*.client.lua` → `StarterPlayerScripts` LocalScripts
- `src/gui/*.client.lua` → `StarterGui` LocalScripts
- `src/shared/*.lua` → `ReplicatedStorage` ModuleScripts
- `src/workspace/*.server.lua` → `Workspace` Scripts

For an existing Rojo project, select its folder. LuauDesk leaves an existing `default.project.json` untouched; verify that it maps the relevant `src/` folders.

## Features

- Dark-themed Luau editor and basic syntax coloring.
- Open and save `.lua` / `.luau` files.
- Export to Script, LocalScript, or ModuleScript locations.
- Create a Rojo project file when starting a new project.
- Basic paired-bracket check (not a full Luau parser).
- Start/stop `rojo serve` from the app when Rojo is in PATH.

## Files

- `app.py` — desktop editor
- `run.bat` — launch from source
- `build_exe.bat` — build a Windows EXE
- `default.project.json` and `src/` — sample Rojo project
