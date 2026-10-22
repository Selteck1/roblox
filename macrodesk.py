from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.parse import urlparse

APP_NAME = "MacroDesk"
BG = "#0b1020"
PANEL = "#111a2e"
EDITOR = "#080e1b"
FG = "#e6edf7"
MUTED = "#93a4bf"
ACCENT = "#7c9cff"
MAX_ACTIONS = 40
MAX_TEXT = 20000

try:
    import keyboard
except ImportError:
    keyboard = None
try:
    import pyautogui
except ImportError:
    pyautogui = None
try:
    import pyperclip
except ImportError:
    pyperclip = None

CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "MacroDesk"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
DEFAULT_PROFILE = {
    "name": "Мой профиль",
    "hotkey": "F8",
    "stop_hotkey": "F9",
    "actions": [
        {"type": "wait", "value": "0.5"},
        {"type": "text", "value": "Пример текста — измени этот макрос под свою задачу."},
        {"type": "key", "value": "enter"},
    ],
}

def clean_hotkey(value: str) -> str:
    value = value.strip().lower().replace(" ", "")
    if not value:
        raise ValueError("Горячая клавиша не может быть пустой.")
    if len(value) > 40 or not re.fullmatch(r"[a-z0-9_+.-]+", value):
        raise ValueError("Недопустимый формат горячей клавиши.")
    keys = value.split("+")
    if len(keys) > 5 or any(not k for k in keys):
        raise ValueError("Комбинация должна содержать от 1 до 5 клавиш.")
    return "+".join(keys)

def validate_action(action: dict) -> dict:
    kind = str(action.get("type", ""))
    value = str(action.get("value", ""))
    if kind == "text":
        if len(value) > MAX_TEXT:
            raise ValueError(f"Текст действия должен быть не длиннее {MAX_TEXT} символов.")
    elif kind == "key":
        clean_hotkey(value)
        allowed = re.fullmatch(r"[a-z0-9_+.-]+", value.strip().lower().replace(" ", ""))
        if not allowed:
            raise ValueError("Недопустимая комбинация клавиш.")
    elif kind == "wait":
        try:
            seconds = float(value)
        except ValueError as exc:
            raise ValueError("Задержка должна быть числом от 0 до 60 секунд.") from exc
        if not 0 <= seconds <= 60:
            raise ValueError("Задержка должна быть от 0 до 60 секунд.")
        value = str(seconds)
    elif kind == "url":
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Для открытия адреса используй полный URL, начинающийся с https:// или http://.")
    else:
        raise ValueError("Неизвестный тип действия.")
    return {"type": kind, "value": value}

def action_label(action: dict) -> str:
    kind = action["type"]
    value = action["value"]
    labels = {"text": "Ввести текст", "key": "Нажать клавишу", "wait": "Задержка", "url": "Открыть ссылку"}
    value = value.replace("\n", "\\n")
    if len(value) > 90:
        value = value[:87] + "..."
    return f'{labels.get(kind, kind)}  ·  {value}'

class MacroDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("MacroDesk — клавиатурная автоматизация")
        root.geometry("1020x720")
        root.minsize(820, 570)
        root.configure(bg=BG)
        self.profiles = self._load_profiles()
        self.profile_index = 0
        self.running = threading.Event()
        self.stop_requested = threading.Event()
        self.worker = None
        self.event_queue: queue.Queue[str] = queue.Queue()
        self.closing = False
        self.hotkeys_registered = False
        self.hotkey_handles = []
        self.profile_name_var = tk.StringVar()
        self.run_hotkey_var = tk.StringVar()
        self.stop_hotkey_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Готово")
        self._style()
        self._build_ui()
        self._load_profile_into_form()
        self._register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<F6>", lambda _e: self.start_macro())
        self.root.bind("<F7>", lambda _e: self.stop_macro())
        self._poll_queue()
        self._log("Профили сохраняются локально. Горячие клавиши действуют глобально, пока приложение открыто.")
        if pyautogui is None or pyperclip is None:
            self._log("Зависимости для отправки клавиш не найдены. Запусти через run_macrodesk.bat или установи requirements.txt.")

    def _load_profiles(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
            profiles = data.get("profiles", [])
            if not isinstance(profiles, list) or not profiles:
                raise ValueError("profiles list is missing")
            cleaned = []
            for profile in profiles:
                if not isinstance(profile, dict):
                    continue
                actions = [validate_action(a) for a in profile.get("actions", [])[:MAX_ACTIONS]]
                cleaned.append({
                    "name": str(profile.get("name", "Профиль"))[:60] or "Профиль",
                    "hotkey": clean_hotkey(str(profile.get("hotkey", "F8"))),
                    "stop_hotkey": clean_hotkey(str(profile.get("stop_hotkey", "F9"))),
                    "actions": actions
                })
            if cleaned:
                return cleaned
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        return [json.loads(json.dumps(DEFAULT_PROFILE, ensure_ascii=False))]

    def _save_profiles(self, quiet=False):
        self._commit_form()
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            PROFILES_FILE.write_text(json.dumps({"profiles": self.profiles}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set(f"Сохранено профилей: {len(self.profiles)}")
            if not quiet:
                self._log(f"Профили сохранены: {PROFILES_FILE}")
            self._register_hotkeys()
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP_NAME, f"Не удалось сохранить профили:\n{exc}", parent=self.root)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=7, background="#1b2942", foreground=FG, borderwidth=0, font=("Segoe UI", 9))
        style.map("TButton", background=[("active", "#2a3b5c")], foreground=[("disabled", "#65748d")])
        style.configure("Accent.TButton", padding=8, background=ACCENT, foreground="#071125", font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#9bb3ff")])
        style.configure("TEntry", fieldbackground=EDITOR, foreground=FG, insertcolor=FG, padding=6)
        style.configure("TCombobox", fieldbackground=EDITOR, foreground=FG, padding=6)
        style.configure("Treeview", background=EDITOR, fieldbackground=EDITOR, foreground=FG, rowheight=27, borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL, foreground=MUTED, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2a3b62")], foreground=[("selected", "white")])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG, padx=18, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="M", bg=ACCENT, fg="#071125", font=("Segoe UI", 19, "bold"), padx=11, pady=3).pack(side="left", padx=(0, 11))
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left")
        tk.Label(titles, text="MacroDesk", bg=BG, fg=FG, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(titles, text="Профили последовательных действий и горячие клавиши", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(header, text="KEYBOARD MACROS", bg=BG, fg="#72e0b0", font=("Segoe UI", 9, "bold")).pack(side="right")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        sidebar = tk.Frame(body, bg=PANEL, padx=12, pady=12, width=245)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar.grid_propagate(False)
        self._section(sidebar, "ПРОФИЛИ")
        self.profile_list = tk.Listbox(sidebar, bg=EDITOR, fg=FG, selectbackground="#2a3b62", selectforeground="white",
                                       activestyle="none", borderwidth=0, highlightthickness=0, font=("Segoe UI", 10), height=10)
        self.profile_list.pack(fill="x", pady=(10, 6))
        self.profile_list.bind("<<ListboxSelect>>", self._on_profile_select)
        buttons = tk.Frame(sidebar, bg=PANEL)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="＋ Новый", command=self.new_profile).pack(side="left", fill="x", expand=True, padx=(0, 3))
        ttk.Button(buttons, text="− Удалить", command=self.delete_profile).pack(side="left", fill="x", expand=True, padx=(3, 0))
        tk.Frame(sidebar, bg="#263450", height=1).pack(fill="x", pady=14)
        self._section(sidebar, "ГОРЯЧИЕ КЛАВИШИ")
        tk.Label(sidebar, text="Запуск профиля", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 4))
        ttk.Entry(sidebar, textvariable=self.run_hotkey_var).pack(fill="x")
        tk.Label(sidebar, text="Остановить макрос", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 4))
        ttk.Entry(sidebar, textvariable=self.stop_hotkey_var).pack(fill="x")
        ttk.Button(sidebar, text="Применить горячие клавиши", command=self.apply_hotkeys).pack(fill="x", pady=(8, 5))
        tk.Label(sidebar, text="По умолчанию: F8 — запуск, F9 — остановка.\nВременная остановка проверяется между действиями.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8), justify="left", wraplength=215).pack(anchor="w", pady=(5, 0))
        ttk.Button(sidebar, text="Импорт профилей…", command=self.import_profiles).pack(fill="x", pady=(15, 4))
        ttk.Button(sidebar, text="Экспорт профилей…", command=self.export_profiles).pack(fill="x", pady=4)

        main = tk.Frame(body, bg=PANEL, padx=12, pady=12)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)
        section1 = tk.Frame(main, bg=PANEL)
        section1.grid(row=0, column=0, sticky="ew")
        self._section(section1, "НАСТРОЙКИ ПРОФИЛЯ")
        form = tk.Frame(main, bg=PANEL)
        form.grid(row=1, column=0, sticky="ew", pady=(10, 14))
        form.grid_columnconfigure(1, weight=1)
        tk.Label(form, text="Название", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(form, textvariable=self.profile_name_var).grid(row=0, column=1, sticky="ew")
        section2 = tk.Frame(main, bg=PANEL)
        section2.grid(row=2, column=0, sticky="ew")
        self._section(section2, "ПОСЛЕДОВАТЕЛЬНОСТЬ ДЕЙСТВИЙ")
        tree_frame = tk.Frame(main, bg=EDITOR)
        tree_frame.grid(row=3, column=0, sticky="nsew", pady=(9, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.action_tree = ttk.Treeview(tree_frame, columns=("kind", "value"), show="headings", selectmode="browse")
        self.action_tree.heading("kind", text="Действие")
        self.action_tree.heading("value", text="Параметр")
        self.action_tree.column("kind", width=175, stretch=False)
        self.action_tree.column("value", width=500, stretch=True)
        self.action_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_frame, command=self.action_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.action_tree.configure(yscrollcommand=scroll.set)
        self.action_tree.bind("<Double-1>", lambda _e: self.edit_action())
        row1 = tk.Frame(main, bg=PANEL)
        row1.grid(row=4, column=0, sticky="ew")
        for label, cmd in [("＋ Действие", self.add_action), ("Изменить", self.edit_action), ("Удалить", self.remove_action), ("↑", lambda: self.move_action(-1)), ("↓", lambda: self.move_action(1))]:
            ttk.Button(row1, text=label, command=cmd).pack(side="left", padx=(0, 5))
        row2 = tk.Frame(main, bg=PANEL)
        row2.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(row2, text="▶ Запустить", style="Accent.TButton", command=self.start_macro).pack(side="left", padx=(0, 6))
        ttk.Button(row2, text="■ Остановить", command=self.stop_macro).pack(side="left", padx=(0, 6))
        ttk.Button(row2, text="Сохранить профили", command=self._save_profiles).pack(side="right")
        footer = tk.Frame(self.root, bg=BG, padx=14)
        footer.pack(fill="x")
        tk.Label(footer, textvariable=self.status_var, bg=PANEL, fg="#72e0b0", anchor="w", padx=10, pady=7).pack(fill="x")
        self.log_box = tk.Text(footer, height=4, bg=EDITOR, fg=MUTED, font=("Consolas", 9), padx=8, pady=6, state="disabled", borderwidth=0)
        self.log_box.pack(fill="x", pady=(6, 8))
        self._refresh_profiles()

    @staticmethod
    def _section(parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold")).pack(anchor="w")

    def _refresh_profiles(self):
        self.profile_list.delete(0, "end")
        for profile in self.profiles:
            self.profile_list.insert("end", profile["name"])
        if self.profiles:
            self.profile_index = max(0, min(self.profile_index, len(self.profiles) - 1))
            self.profile_list.selection_set(self.profile_index)
            self.profile_list.activate(self.profile_index)

    def _commit_form(self):
        if not self.profiles:
            return
        profile = self.profiles[self.profile_index]
        name = self.profile_name_var.get().strip()[:60]
        profile["name"] = name or "Профиль"
        try:
            profile["hotkey"] = clean_hotkey(self.run_hotkey_var.get())
            profile["stop_hotkey"] = clean_hotkey(self.stop_hotkey_var.get())
            if profile["hotkey"] == profile["stop_hotkey"]:
                raise ValueError("Клавиши запуска и остановки должны отличаться.")
        except ValueError:
            pass
        profile["actions"] = self._current_actions()
        self._refresh_profiles()

    def _load_profile_into_form(self):
        if not self.profiles:
            return
        profile = self.profiles[self.profile_index]
        self.profile_name_var.set(profile["name"])
        self.run_hotkey_var.set(profile["hotkey"])
        self.stop_hotkey_var.set(profile["stop_hotkey"])
        self._refresh_actions()

    def _current_actions(self):
        return [dict(action) for action in self.profiles[self.profile_index]["actions"]]

    def _refresh_actions(self):
        for item in self.action_tree.get_children():
            self.action_tree.delete(item)
        if not self.profiles:
            return
        for index, action in enumerate(self.profiles[self.profile_index]["actions"]):
            kind_names = {"text": "Ввести текст", "key": "Нажать клавишу", "wait": "Задержка", "url": "Открыть ссылку"}
            value = action["value"].replace("\n", "\\n")
            self.action_tree.insert("", "end", iid=str(index), values=(kind_names.get(action["type"], action["type"]), value))

    def _on_profile_select(self, _event=None):
        selected = self.profile_list.curselection()
        if not selected or selected[0] == self.profile_index:
            return
        self._commit_form()
        self.profile_index = selected[0]
        self._load_profile_into_form()

    def new_profile(self):
        self._commit_form()
        name = simpledialog.askstring(APP_NAME, "Название нового профиля:", initialvalue=f"Профиль {len(self.profiles)+1}", parent=self.root)
        if not name:
            return
        self.profiles.append({"name": name.strip()[:60] or "Профиль", "hotkey": f"F{min(8+len(self.profiles), 12)}",
                              "stop_hotkey": "F9", "actions": []})
        self.profile_index = len(self.profiles) - 1
        if self.profiles[-1]["hotkey"] == self.profiles[-1]["stop_hotkey"]:
            self.profiles[-1]["hotkey"] = "F8"
        self._refresh_profiles()
        self._load_profile_into_form()
        self._save_profiles(quiet=True)

    def delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showinfo(APP_NAME, "Нужно оставить хотя бы один профиль.", parent=self.root)
            return
        if not messagebox.askyesno(APP_NAME, f"Удалить профиль «{self.profiles[self.profile_index]['name']}»?", parent=self.root):
            return
        self.profiles.pop(self.profile_index)
        self.profile_index = min(self.profile_index, len(self.profiles)-1)
        self._load_profile_into_form()
        self._save_profiles(quiet=True)

    def _selected_action_index(self):
        selected = self.action_tree.selection()
        return int(selected[0]) if selected else None

    def _action_dialog(self, title, initial=None):
        initial = initial or {"type": "text", "value": ""}
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(True, True)
        dialog.geometry("490x270")
        kind_var = tk.StringVar(value=initial.get("type", "text"))
        tk.Label(dialog, text="Тип действия", bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 5))
        combo = ttk.Combobox(dialog, textvariable=kind_var, values=["text", "key", "wait", "url"], state="readonly")
        combo.pack(fill="x", padx=14)
        hint_var = tk.StringVar(value=self._hint(kind_var.get()))
        tk.Label(dialog, textvariable=hint_var, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=450, justify="left").pack(anchor="w", padx=14, pady=(5, 7))
        text = tk.Text(dialog, height=5, bg=EDITOR, fg=FG, insertbackground="white", font=("Consolas", 10), wrap="word", borderwidth=0)
        text.pack(fill="both", expand=True, padx=14)
        text.insert("1.0", initial.get("value", ""))
        combo.bind("<<ComboboxSelected>>", lambda _e: hint_var.set(self._hint(kind_var.get())))
        result = {"value": None}
        buttons = tk.Frame(dialog, bg=PANEL)
        buttons.pack(fill="x", padx=14, pady=12)
        def accept():
            try:
                result["value"] = validate_action({"type": kind_var.get(), "value": text.get("1.0", "end-1c")})
            except ValueError as exc:
                messagebox.showerror(APP_NAME, str(exc), parent=dialog)
                return
            dialog.destroy()
        ttk.Button(buttons, text="Отмена", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Сохранить", style="Accent.TButton", command=accept).pack(side="right", padx=(0, 7))
        dialog.wait_window()
        return result["value"]

    @staticmethod
    def _hint(kind):
        return {
            "text": "Вставляет текст в активное окно через буфер обмена. Переводы строк поддерживаются.",
            "key": "Одна клавиша или комбинация, например: enter, space, ctrl+v, alt+tab. Действие отправляется в активное окно.",
            "wait": "Пауза перед следующим действием, в секундах: от 0 до 60.",
            "url": "Открывает HTTP(S)-ссылку в браузере по умолчанию."
        }.get(kind, "")

    def add_action(self):
        self._commit_form()
        actions = self.profiles[self.profile_index]["actions"]
        if len(actions) >= MAX_ACTIONS:
            messagebox.showwarning(APP_NAME, f"В одном профиле максимум {MAX_ACTIONS} действий.", parent=self.root)
            return
        result = self._action_dialog("Добавить действие")
        if result:
            actions.append(result)
            self._refresh_actions()
            self._save_profiles(quiet=True)

    def edit_action(self):
        index = self._selected_action_index()
        if index is None:
            return
        self._commit_form()
        old = self.profiles[self.profile_index]["actions"][index]
        result = self._action_dialog("Изменить действие", old)
        if result:
            self.profiles[self.profile_index]["actions"][index] = result
            self._refresh_actions()
            self.action_tree.selection_set(str(index))
            self._save_profiles(quiet=True)

    def remove_action(self):
        index = self._selected_action_index()
        if index is None:
            return
        self.profiles[self.profile_index]["actions"].pop(index)
        self._refresh_actions()
        self._save_profiles(quiet=True)

    def move_action(self, delta):
        index = self._selected_action_index()
        if index is None:
            return
        actions = self.profiles[self.profile_index]["actions"]
        target = index + delta
        if not 0 <= target < len(actions):
            return
        actions[index], actions[target] = actions[target], actions[index]
        self._refresh_actions()
        self.action_tree.selection_set(str(target))
        self.action_tree.see(str(target))
        self._save_profiles(quiet=True)

    def apply_hotkeys(self):
        try:
            run_key = clean_hotkey(self.run_hotkey_var.get())
            stop_key = clean_hotkey(self.stop_hotkey_var.get())
            if run_key == stop_key:
                raise ValueError("Горячие клавиши запуска и остановки должны отличаться.")
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)
            return
        self._commit_form()
        self.profiles[self.profile_index]["hotkey"] = run_key
        self.profiles[self.profile_index]["stop_hotkey"] = stop_key
        self.run_hotkey_var.set(run_key)
        self.stop_hotkey_var.set(stop_key)
        self._save_profiles(quiet=True)
        self.status_var.set(f"Горячие клавиши: {run_key} / {stop_key}")

    def _register_hotkeys(self):
        if keyboard is None:
            self.hotkeys_registered = False
            self.status_var.set("Нет модуля keyboard — установи requirements.txt")
            return
        try:
            for handle in self.hotkey_handles:
                try:
                    keyboard.remove_hotkey(handle)
                except Exception:
                    pass
            self.hotkey_handles.clear()
            for index, profile in enumerate(self.profiles):
                run_key, stop_key = profile["hotkey"], profile["stop_hotkey"]
                self.hotkey_handles.append(keyboard.add_hotkey(
                    run_key, lambda i=index: self.event_queue.put(f"__start__:{i}"),
                    suppress=False, trigger_on_release=False))
                self.hotkey_handles.append(keyboard.add_hotkey(
                    stop_key, lambda: self.event_queue.put("__stop__"),
                    suppress=False, trigger_on_release=False))
            self.hotkeys_registered = True
        except Exception as exc:
            self.hotkeys_registered = False
            self._log(f"Не удалось зарегистрировать горячие клавиши: {exc}")
            self.status_var.set("Не удалось установить глобальные горячие клавиши")

    def start_macro(self, profile=None):
        if self.running.is_set():
            return
        if pyautogui is None or pyperclip is None:
            self.root.after(0, lambda: messagebox.showerror(APP_NAME, "Не найдены pyautogui/pyperclip. Запусти run_macrodesk.bat или установи requirements.txt.", parent=self.root))
            return
        if profile is None:
            self._commit_form()
            profile = self.profiles[self.profile_index]
        else:
            try:
                index = self.profiles.index(profile)
                self.profile_index = index
                self.root.after(0, self._load_profile_into_form)
            except ValueError:
                pass
        profile_copy = json.loads(json.dumps(profile, ensure_ascii=False))
        if not profile_copy["actions"]:
            self.root.after(0, lambda: messagebox.showinfo(APP_NAME, "В этом профиле пока нет действий.", parent=self.root))
            return
        self.stop_requested.clear()
        self.running.set()
        self.status_var.set(f"Выполняется: {profile_copy['name']}")
        self._log(f"Старт профиля «{profile_copy['name']}»")
        self.worker = threading.Thread(target=self._run_actions, args=(profile_copy,), daemon=True)
        self.worker.start()

    def stop_macro(self):
        if self.running.is_set():
            self.stop_requested.set()
            self.status_var.set("Останавливаю после текущего действия…")
            self._log("Запрошена остановка.")

    def _run_actions(self, profile):
        try:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.02
            for index, action in enumerate(profile["actions"], start=1):
                if self.stop_requested.is_set():
                    self._event("Выполнение остановлено пользователем.")
                    break
                kind, value = action["type"], action["value"]
                self._event(f"{index}/{len(profile['actions'])}: {action_label(action)}")
                if kind == "wait":
                    deadline = time.monotonic() + float(value)
                    while time.monotonic() < deadline:
                        if self.stop_requested.wait(min(0.05, max(0, deadline-time.monotonic()))):
                            break
                elif kind == "text":
                    pyperclip.copy(value)
                    pyautogui.hotkey("ctrl", "v")
                elif kind == "key":
                    keys = [x.strip().lower() for x in value.replace(" ", "").split("+")]
                    if len(keys) == 1:
                        pyautogui.press(keys[0])
                    else:
                        pyautogui.hotkey(*keys)
                elif kind == "url":
                    webbrowser.open(value, new=2)
                if self.stop_requested.is_set():
                    self._event("Выполнение остановлено пользователем.")
                    break
            else:
                self._event("Профиль выполнен.")
        except Exception as exc:
            self._event(f"Ошибка макроса: {type(exc).__name__}: {exc}")
        finally:
            self.running.clear()
            self.event_queue.put("__status__:Готово")

    def _event(self, line):
        self.event_queue.put(line)

    def _log(self, line):
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", line.rstrip() + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    def _poll_queue(self):
        if self.closing:
            return
        try:
            while True:
                line = self.event_queue.get_nowait()
                if line == "__stop__":
                    self.stop_macro()
                elif line.startswith("__start__:"):
                    try:
                        index = int(line.split(":", 1)[1])
                        if 0 <= index < len(self.profiles):
                            self.start_macro(self.profiles[index])
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("__status__:"):
                    self.status_var.set(line.split(":", 1)[1])
                else:
                    self._log(line)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def export_profiles(self):
        self._commit_form()
        filename = filedialog.asksaveasfilename(parent=self.root, title="Экспорт профилей", defaultextension=".json",
                                                initialfile="MacroDesk-profiles.json", filetypes=[("JSON", "*.json")])
        if not filename:
            return
        try:
            Path(filename).write_text(json.dumps({"profiles": self.profiles}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set("Профили экспортированы")
        except OSError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)

    def import_profiles(self):
        filename = filedialog.askopenfilename(parent=self.root, title="Импорт профилей", filetypes=[("JSON", "*.json")])
        if not filename:
            return
        try:
            data = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
            imported = data if isinstance(data, list) else data.get("profiles", [])
            if not isinstance(imported, list) or not imported:
                raise ValueError("В файле не найден список profiles.")
            checked = []
            for profile in imported:
                actions = [validate_action(x) for x in profile.get("actions", [])]
                if len(actions) > MAX_ACTIONS:
                    raise ValueError(f"В профиле слишком много действий (максимум {MAX_ACTIONS}).")
                run_key = clean_hotkey(str(profile.get("hotkey", "F8")))
                stop_key = clean_hotkey(str(profile.get("stop_hotkey", "F9")))
                if run_key == stop_key:
                    raise ValueError("Клавиши запуска и остановки должны различаться.")
                checked.append({"name": str(profile.get("name", "Импортированный профиль"))[:60],
                                "hotkey": run_key, "stop_hotkey": stop_key, "actions": actions})
            if not checked:
                raise ValueError("Нет валидных профилей.")
            self.profiles.extend(checked)
            self.profile_index = len(self.profiles) - len(checked)
            self._load_profile_into_form()
            self._save_profiles(quiet=True)
            self._log(f"Импортировано профилей: {len(checked)}")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Не удалось импортировать файл:\n{exc}", parent=self.root)

    def close(self):
        self.closing = True
        self.stop_requested.set()
        for handle in self.hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self.hotkey_handles.clear()
        self._save_profiles(quiet=True)
        self.root.destroy()

def main():
    root = tk.Tk()
    MacroDesk(root)
    root.mainloop()

if __name__ == "__main__":
    main()
