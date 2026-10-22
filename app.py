from __future__ import annotations

import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Luau Desk"
APP_VERSION = "1.0.0"

COLORS = {
    "bg": "#10131a",
    "panel": "#171b25",
    "panel2": "#1d2330",
    "editor": "#0e1117",
    "border": "#2b3445",
    "text": "#e6edf7",
    "muted": "#8b97ab",
    "accent": "#7c6cff",
    "accent_hover": "#9184ff",
    "green": "#47c99b",
    "red": "#ff7385",
    "yellow": "#e7c879",
}

KEYWORDS = {
    "and", "break", "continue", "do", "else", "elseif", "end", "export",
    "false", "for", "function", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "type", "typeof", "until", "while",
}
BUILTINS = {
    "game", "workspace", "script", "plugin", "Enum", "Instance", "Vector2",
    "Vector3", "CFrame", "Color3", "UDim", "UDim2", "BrickColor", "RaycastParams",
    "TweenInfo", "math", "string", "table", "task", "coroutine", "debug", "os",
    "warn", "print", "error", "assert", "select", "tonumber", "tostring", "pairs",
    "ipairs", "next", "type", "require", "wait", "spawn", "delay", "tick", "time",
}
TOKEN_RE = re.compile(
    r"(?P<comment>--\[\[[\s\S]*?\]\]|--[^\n]*)"
    r"|(?P<string>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
    r"|(?P<keyword>\b(?:" + "|".join(sorted(KEYWORDS, key=len, reverse=True)) + r")\b)"
    r"|(?P<builtin>\b(?:" + "|".join(sorted(BUILTINS, key=len, reverse=True)) + r")\b)"
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<call>\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())"
)

TEMPLATE = '''-- Пример Luau для Roblox Studio
-- Добавь этот код в Script или LocalScript своей игры.

print("Hello from Luau!")
'''


class LuauDesk(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.current_path: Path | None = None
        self.is_dirty = False
        self._highlight_after: str | None = None
        self._building_editor = False

        self.title(APP_NAME)
        self.geometry("1120x740")
        self.minsize(820, 560)
        self.configure(bg=COLORS["bg"])
        self._setup_style()
        self._build_ui()
        self._bind_shortcuts()
        self._set_editor_text(TEMPLATE)
        self._set_status("Готово • Создай или открой .lua / .luau файл")
        self.after(120, self._highlight_syntax)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Vertical.TScrollbar", background=COLORS["panel2"],
                        troughcolor=COLORS["editor"], bordercolor=COLORS["editor"],
                        arrowcolor=COLORS["muted"])

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=COLORS["panel"], height=68,
                          highlightbackground=COLORS["border"], highlightthickness=1)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        logo = tk.Frame(header, bg=COLORS["accent"], width=40, height=40)
        logo.pack(side="left", padx=(18, 11), pady=13)
        logo.pack_propagate(False)
        tk.Label(logo, text="LU", bg=COLORS["accent"], fg="white",
                 font=("Segoe UI", 12, "bold")).pack(expand=True)

        brand = tk.Frame(header, bg=COLORS["panel"])
        brand.pack(side="left", pady=10)
        tk.Label(brand, text=APP_NAME, bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(brand, text="Редактор Luau для Roblox Studio", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")

        tk.Label(header, text=f"v{APP_VERSION}", bg=COLORS["panel2"], fg=COLORS["muted"],
                 font=("Segoe UI", 9), padx=10, pady=5).pack(side="right", padx=18)

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=COLORS["panel"], width=205,
                           highlightbackground=COLORS["border"], highlightthickness=1)
        sidebar.pack(side="left", fill="y", padx=(14, 0), pady=14)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="ФАЙЛ", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(18, 8))
        self._side_button(sidebar, "＋   Новый скрипт", self.new_file)
        self._side_button(sidebar, "↗   Открыть файл", self.open_file)
        self._side_button(sidebar, "↓   Сохранить", self.save_file)
        self._side_button(sidebar, "⇩   Сохранить как…", self.save_file_as)

        divider = tk.Frame(sidebar, bg=COLORS["border"], height=1)
        divider.pack(fill="x", padx=14, pady=12)
        tk.Label(sidebar, text="ROBLOX STUDIO", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(0, 8))
        self._side_button(sidebar, "▣   Копировать код", self.copy_code, accent=True)
        self._side_button(sidebar, "↗   Открыть Studio", self.open_studio)
        self._side_button(sidebar, "⇧   Код + Studio", self.copy_and_open_studio)

        info = tk.Frame(sidebar, bg=COLORS["panel2"], highlightbackground=COLORS["border"],
                        highlightthickness=1)
        info.pack(side="bottom", fill="x", padx=10, pady=10)
        tk.Label(info, text="Важно", bg=COLORS["panel2"], fg=COLORS["yellow"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(9, 3))
        tk.Label(info, text="Это редактор, а не инжектор.\nКод запускается в Studio\nв твоём собственном проекте.",
                 justify="left", bg=COLORS["panel2"], fg=COLORS["muted"],
                 font=("Segoe UI", 9), wraplength=165).pack(anchor="w", padx=10, pady=(0, 10))

        workspace = tk.Frame(body, bg=COLORS["bg"])
        workspace.pack(side="left", fill="both", expand=True, padx=14, pady=14)

        editor_top = tk.Frame(workspace, bg=COLORS["panel"], height=48,
                              highlightbackground=COLORS["border"], highlightthickness=1)
        editor_top.pack(fill="x")
        editor_top.pack_propagate(False)
        tk.Label(editor_top, text="  ◈   РЕДАКТОР", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 12))
        self.file_label = tk.Label(editor_top, text="untitled.luau", bg=COLORS["panel"],
                                   fg=COLORS["text"], font=("Consolas", 10))
        self.file_label.pack(side="left")
        tk.Label(editor_top, text="Luau", bg=COLORS["panel2"], fg=COLORS["green"],
                 font=("Segoe UI", 9, "bold"), padx=9, pady=4).pack(side="right", padx=12)

        editor_frame = tk.Frame(workspace, bg=COLORS["editor"],
                                highlightbackground=COLORS["border"], highlightthickness=1)
        editor_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.gutter = tk.Text(editor_frame, width=4, padx=10, pady=13, takefocus=0,
                              borderwidth=0, state="disabled", wrap="none",
                              bg=COLORS["editor"], fg="#536078",
                              font=("Consolas", 11), selectbackground=COLORS["editor"])
        self.gutter.pack(side="left", fill="y")

        self.editor = tk.Text(editor_frame, undo=True, wrap="none", borderwidth=0,
                              padx=10, pady=13, bg=COLORS["editor"], fg=COLORS["text"],
                              insertbackground="white", selectbackground="#363b63",
                              selectforeground="white", font=("Consolas", 11),
                              spacing1=2, spacing3=2, tabs=("4c",))
        self.editor.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(editor_frame, orient="vertical", command=self._scroll_editor,
                                  style="Vertical.TScrollbar")
        self._scrollbar = scrollbar
        scrollbar.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=self._on_editor_scroll)

        self.editor.tag_configure("keyword", foreground="#c4a7ff")
        self.editor.tag_configure("builtin", foreground="#7dcfff")
        self.editor.tag_configure("string", foreground="#c3e88d")
        self.editor.tag_configure("comment", foreground="#718096")
        self.editor.tag_configure("number", foreground="#f6ad75")
        self.editor.tag_configure("call", foreground="#82aaff")

        footer = tk.Frame(self, bg=COLORS["panel"], height=28,
                          highlightbackground=COLORS["border"], highlightthickness=1)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        self.status_label = tk.Label(footer, text="Готово", bg=COLORS["panel"],
                                     fg=COLORS["muted"], font=("Segoe UI", 9), anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=13)
        self.position_label = tk.Label(footer, text="Стр. 1  •  Столбец 1",
                                       bg=COLORS["panel"], fg=COLORS["muted"],
                                       font=("Segoe UI", 9))
        self.position_label.pack(side="right", padx=13)

        self.editor.bind("<<Modified>>", self._on_modified)
        self.editor.bind("<KeyRelease>", self._on_key_release)
        self.editor.bind("<ButtonRelease-1>", self._update_cursor_position)
        self.editor.bind("<MouseWheel>", self._on_mousewheel)
        self.editor.bind("<Configure>", lambda _e: self._update_line_numbers())

    def _side_button(self, parent: tk.Widget, label: str, command, accent: bool = False) -> None:
        base = COLORS["accent"] if accent else COLORS["panel"]
        hover = COLORS["accent_hover"] if accent else COLORS["panel2"]
        button = tk.Button(parent, text=label, command=command, anchor="w", relief="flat",
                           borderwidth=0, padx=13, pady=10, cursor="hand2",
                           bg=base, fg="white" if accent else COLORS["text"],
                           activebackground=hover, activeforeground="white",
                           font=("Segoe UI", 10))
        button.pack(fill="x", padx=8, pady=2)
        button.bind("<Enter>", lambda _e: button.configure(bg=hover))
        button.bind("<Leave>", lambda _e: button.configure(bg=base))

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _e: self.new_file())
        self.bind("<Control-o>", lambda _e: self.open_file())
        self.bind("<Control-s>", lambda _e: self.save_file())
        self.bind("<Control-Shift-S>", lambda _e: self.save_file_as())
        self.bind("<Control-Shift-s>", lambda _e: self.save_file_as())
        self.bind("<Control-Shift-c>", lambda _e: self.copy_code())

    def _set_editor_text(self, text: str) -> None:
        self._building_editor = True
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._building_editor = False
        self.is_dirty = False
        self._update_line_numbers()
        self._update_title()
        self._schedule_highlight()

    def _on_modified(self, _event=None) -> None:
        if self._building_editor:
            return
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.is_dirty = True
            self._update_title()
            self._update_line_numbers()
            self._schedule_highlight()
            self._update_cursor_position()

    def _on_key_release(self, _event=None) -> None:
        self._update_cursor_position()

    def _schedule_highlight(self) -> None:
        if self._highlight_after is not None:
            try:
                self.after_cancel(self._highlight_after)
            except tk.TclError:
                pass
        self._highlight_after = self.after(140, self._highlight_syntax)

    def _highlight_syntax(self) -> None:
        self._highlight_after = None
        source = self.editor.get("1.0", "end-1c")
        for tag in ("keyword", "builtin", "string", "comment", "number", "call"):
            self.editor.tag_remove(tag, "1.0", "end")
        for match in TOKEN_RE.finditer(source):
            tag = match.lastgroup
            if not tag:
                continue
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.editor.tag_add(tag, start, end)
        self.editor.tag_raise("string")
        self.editor.tag_raise("comment")
        self.editor.edit_modified(False)

    def _update_line_numbers(self) -> None:
        if not hasattr(self, "editor"):
            return
        last_line = int(self.editor.index("end-1c").split(".")[0])
        numbers = "\n".join(str(n) for n in range(1, max(last_line, 1) + 1))
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", numbers)
        self.gutter.configure(state="disabled")
        try:
            self.gutter.yview_moveto(self.editor.yview()[0])
        except tk.TclError:
            pass

    def _on_editor_scroll(self, first: str, last: str) -> None:
        self._scrollbar.set(first, last)
        try:
            self.gutter.yview_moveto(float(first))
        except (tk.TclError, ValueError):
            pass
        self._update_line_numbers()

    def _scroll_editor(self, *args) -> None:
        self.editor.yview(*args)
        self.gutter.yview_moveto(self.editor.yview()[0])

    def _on_mousewheel(self, event) -> None:
        try:
            delta = int(-1 * (event.delta / 120))
            self.editor.yview_scroll(delta, "units")
            self.gutter.yview_scroll(delta, "units")
        except (tk.TclError, ZeroDivisionError):
            pass

    def _update_cursor_position(self, _event=None) -> None:
        try:
            row, col = self.editor.index("insert").split(".")
            self.position_label.configure(text=f"Стр. {row}  •  Столбец {int(col) + 1}")
        except (tk.TclError, ValueError):
            pass

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _update_title(self) -> None:
        name = self.current_path.name if self.current_path else "untitled.luau"
        marker = " •" if self.is_dirty else ""
        self.file_label.configure(text=name + marker)
        self.title(f"{APP_NAME} — {name}{marker}")

    def _confirm_discard(self) -> bool:
        if not self.is_dirty:
            return True
        answer = messagebox.askyesnocancel("Несохранённые изменения",
            "Сохранить изменения перед продолжением?", parent=self)
        if answer is None:
            return False
        if answer:
            return self.save_file()
        return True

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self.current_path = None
        self._set_editor_text(TEMPLATE)
        self._set_status("Создан новый скрипт")
        self._update_title()

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        selected = filedialog.askopenfilename(parent=self, title="Открыть скрипт Luau",
            filetypes=[("Luau / Lua", "*.luau *.lua"), ("Все файлы", "*.*")])
        if not selected:
            return
        path = Path(selected)
        try:
            contents = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Не удалось открыть файл", str(exc), parent=self)
            return
        self.current_path = path
        self._set_editor_text(contents)
        self._set_status(f"Открыт файл: {path.name}")
        self._update_title()

    def save_file(self) -> bool:
        if self.current_path is None:
            return self.save_file_as()
        try:
            self.current_path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8", newline="\n")
        except OSError as exc:
            messagebox.showerror("Не удалось сохранить файл", str(exc), parent=self)
            return False
        self.is_dirty = False
        self.editor.edit_modified(False)
        self._update_title()
        self._set_status(f"Сохранено: {self.current_path}")
        return True

    def save_file_as(self) -> bool:
        selected = filedialog.asksaveasfilename(parent=self, title="Сохранить скрипт",
            defaultextension=".luau", initialfile=(self.current_path.name if self.current_path else "script.luau"),
            filetypes=[("Luau", "*.luau"), ("Lua", "*.lua"), ("Все файлы", "*.*")])
        if not selected:
            return False
        self.current_path = Path(selected)
        return self.save_file()

    def copy_code(self) -> None:
        code = self.editor.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update()
        self._set_status("Код скопирован. Вставь его в Script / LocalScript в Roblox Studio.")

    def _find_studio(self) -> Path | None:
        local = os.environ.get("LOCALAPPDATA")
        if local:
            versions = Path(local) / "Roblox" / "Versions"
            if versions.is_dir():
                candidates = list(versions.glob("*/RobloxStudioBeta.exe"))
                if candidates:
                    return max(candidates, key=lambda p: p.stat().st_mtime)
        program_files = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
        for root in filter(None, program_files):
            candidate = Path(root) / "Roblox" / "Versions"
            if candidate.is_dir():
                found = list(candidate.glob("*/RobloxStudioBeta.exe"))
                if found:
                    return max(found, key=lambda p: p.stat().st_mtime)
        return None

    def open_studio(self) -> bool:
        studio = self._find_studio()
        try:
            if studio:
                subprocess.Popen([str(studio)], close_fds=True)
                self._set_status("Запущен Roblox Studio")
                return True
            if sys.platform == "win32":
                os.startfile("roblox-studio:")  # type: ignore[attr-defined]
                self._set_status("Отправлен запрос на открытие Roblox Studio")
                return True
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showwarning("Не удалось запустить Studio",
                f"{exc}\n\nОткрой Roblox Studio вручную.", parent=self)
            return False
        messagebox.showinfo("Roblox Studio не найден",
            "Установи Roblox Studio с сайта create.roblox.com и открой его вручную.", parent=self)
        webbrowser.open("https://create.roblox.com/")
        return False

    def copy_and_open_studio(self) -> None:
        self.copy_code()
        opened = self.open_studio()
        messagebox.showinfo("Код готов к тестированию",
            "Код скопирован в буфер обмена. В Roblox Studio:\n\n"
            "1. Открой свой проект.\n"
            "2. В Explorer создай Script или LocalScript в подходящем месте.\n"
            "3. Вставь код и нажми Play для проверки.\n\n"
            "Приложение не внедряет код в запущенный клиент Roblox.", parent=self)
        if opened:
            self._set_status("Код скопирован • Вставь его в Script / LocalScript в Studio")

    def _on_close(self) -> None:
        if self._confirm_discard():
            self.destroy()


def main() -> None:
    app = LuauDesk()
    app.protocol("WM_DELETE_WINDOW", app._on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
