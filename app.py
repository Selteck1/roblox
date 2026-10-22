from __future__ import annotations
import json, os, queue, re, shutil, subprocess, sys, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP = "LuauDesk"
BG, PANEL, EDITOR = "#0b1020", "#111a2e", "#0a1020"
FG, MUTED, ACCENT = "#e6edf7", "#93a4bf", "#7c9cff"
TARGETS = {
    "ServerScriptService · Script": ("server", ".server.lua"),
    "StarterPlayerScripts · LocalScript": ("client", ".client.lua"),
    "StarterGui · LocalScript": ("gui", ".client.lua"),
    "ReplicatedStorage · ModuleScript": ("shared", ".lua"),
    "Workspace · Script": ("workspace", ".server.lua"),
}
PROJECT = {"name": "LuauDeskProject", "tree": {
    "$className": "DataModel", "ReplicatedStorage": {"$path": "src/shared"},
    "ServerScriptService": {"$path": "src/server"},
    "StarterPlayer": {"StarterPlayerScripts": {"$path": "src/client"}},
    "StarterGui": {"$path": "src/gui"}, "Workspace": {"$path": "src/workspace"}}}
SAMPLE = '''-- Script for your own Roblox experience
local Players = game:GetService("Players")

Players.PlayerAdded:Connect(function(player)
    print("Welcome, " .. player.Name .. "!")
end)
'''

class App:
    def __init__(self, root):
        self.root = root
        root.title("LuauDesk — Roblox Luau Editor")
        root.geometry("1120x740"); root.minsize(850, 570); root.configure(bg=BG)
        self.path = None; self.proc = None; self.q = queue.Queue(); self.closing = False
        self.project = tk.StringVar(); self.name = tk.StringVar(value="MyScript")
        self.target = tk.StringVar(value=list(TARGETS)[0]); self.status = tk.StringVar(value="Готово")
        self._style(); self._ui(); self._set_code(SAMPLE); root.protocol("WM_DELETE_WINDOW", self.close); self._poll()

    def _style(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("TButton", padding=7, background="#17223a", foreground=FG, borderwidth=0, font=("Segoe UI", 9))
        s.map("TButton", background=[("active", "#2a3b5c")])
        s.configure("Accent.TButton", background=ACCENT, foreground="#071125")
        s.configure("TEntry", fieldbackground="#080e1b", foreground=FG, insertcolor=FG, padding=6)
        s.configure("TCombobox", fieldbackground="#080e1b", foreground=FG, padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", "#080e1b")], foreground=[("readonly", FG)])

    def _ui(self):
        head = tk.Frame(self.root, bg=BG, padx=18, pady=12); head.pack(fill="x")
        tk.Label(head, text="L", bg=ACCENT, fg="#071125", font=("Segoe UI", 18, "bold"), padx=10, pady=3).pack(side="left", padx=(0, 10))
        labels = tk.Frame(head, bg=BG); labels.pack(side="left")
        tk.Label(labels, text="LuauDesk", bg=BG, fg=FG, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(labels, text="Редактор скриптов для Roblox Studio", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(head, text="STUDIO WORKFLOW", bg=BG, fg="#72e0b0", font=("Segoe UI", 9, "bold")).pack(side="right")
        bar = tk.Frame(self.root, bg=PANEL, padx=8, pady=8); bar.pack(fill="x", padx=14, pady=(0, 10))
        for label, cmd in [("Новый", self.new), ("Открыть", self.open_file), ("Сохранить", self.save_file), ("Проверить скобки", self.check), ("Пример", self.example)]:
            ttk.Button(bar, text=label, command=cmd).pack(side="left", padx=3)
        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        body.grid_rowconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1)
        side = tk.Frame(body, bg=PANEL, width=270, padx=12, pady=12); side.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); side.grid_propagate(False)
        self._label(side, "ПРОЕКТ ROBLOX")
        tk.Label(side, text="Папка проекта Rojo", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 5))
        row = tk.Frame(side, bg=PANEL); row.pack(fill="x")
        ttk.Entry(row, textvariable=self.project).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="…", width=3, command=self.pick_project).pack(side="left", padx=(5, 0))
        ttk.Button(side, text="Открыть папку", command=self.open_folder).pack(fill="x", pady=(7, 14))
        tk.Frame(side, bg="#263450", height=1).pack(fill="x", pady=(0, 12))
        self._label(side, "НАСТРОЙКИ СКРИПТА")
        tk.Label(side, text="Имя файла", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 5))
        ttk.Entry(side, textvariable=self.name).pack(fill="x")
        tk.Label(side, text="Куда поместить", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 5))
        ttk.Combobox(side, textvariable=self.target, values=list(TARGETS), state="readonly").pack(fill="x")
        ttk.Button(side, text="Экспорт в проект", style="Accent.TButton", command=self.export).pack(fill="x", pady=(14, 6))
        ttk.Button(side, text="Запустить Rojo / sync", command=self.start_rojo).pack(fill="x", pady=3)
        ttk.Button(side, text="Остановить Rojo", command=self.stop_rojo).pack(fill="x", pady=3)
        tk.Label(side, text="1. Подключи плагин Rojo в Studio.\n2. Нажми Play в Studio.\n3. Результат смотри в View → Output.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(15, 0))
        pane = tk.Frame(body, bg=PANEL); pane.grid(row=0, column=1, sticky="nsew"); pane.grid_rowconfigure(1, weight=1); pane.grid_columnconfigure(0, weight=1)
        self.file_label = tk.Label(pane, text="● Untitled.luau", bg=PANEL, fg=FG, font=("Consolas", 10), padx=12, pady=10); self.file_label.grid(row=0, column=0, sticky="ew")
        wrap = tk.Frame(pane, bg=EDITOR); wrap.grid(row=1, column=0, sticky="nsew"); wrap.grid_rowconfigure(0, weight=1); wrap.grid_columnconfigure(0, weight=1)
        self.editor = tk.Text(wrap, undo=True, wrap="none", bg=EDITOR, fg="#dce7fb", insertbackground="white", selectbackground="#2a3b62", font=("Consolas", 11), padx=12, pady=12, borderwidth=0, tabs=(36,))
        self.editor.grid(row=0, column=0, sticky="nsew"); ys = ttk.Scrollbar(wrap, command=self.editor.yview); ys.grid(row=0, column=1, sticky="ns"); xs = ttk.Scrollbar(wrap, orient="horizontal", command=self.editor.xview); xs.grid(row=1, column=0, sticky="ew")
        self.editor.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        for tag, color in [("keyword", "#83a7ff"), ("string", "#a9df9c"), ("comment", "#71829e"), ("builtin", "#76d8e7"), ("number", "#e8b88a")]: self.editor.tag_configure(tag, foreground=color)
        self.editor.bind("<KeyRelease>", self._changed); self.editor.bind("<Control-s>", lambda e: (self.save_file(), "break")[1]); self.editor.bind("<Control-o>", lambda e: (self.open_file(), "break")[1])
        bottom = tk.Frame(self.root, bg=BG, padx=14, pady=0); bottom.pack(fill="x")
        tk.Label(bottom, textvariable=self.status, bg=PANEL, fg="#72e0b0", anchor="w", padx=10, pady=7).pack(fill="x")
        self.output = tk.Text(bottom, height=4, bg="#080d18", fg=MUTED, font=("Consolas", 9), padx=8, pady=6, state="disabled", borderwidth=0)
        self.output.pack(fill="x", pady=(6, 8)); self.log("Готово. Экспорт сохраняет скрипт в проект, синхронизируемый с Roblox Studio через Rojo.")

    @staticmethod
    def _label(parent, text): tk.Label(parent, text=text, bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold")).pack(anchor="w")
    def log(self, text):
        self.output.configure(state="normal"); self.output.insert("end", text.rstrip()+"\n"); self.output.see("end"); self.output.configure(state="disabled")
    def _set_code(self, text): self.editor.delete("1.0", "end"); self.editor.insert("1.0", text); self._highlight()
    def _changed(self, _=None): self.root.after(100, self._highlight)
    def _highlight(self):
        code = self.editor.get("1.0", "end-1c")
        for tag in ("keyword", "string", "comment", "builtin", "number"): self.editor.tag_remove(tag, "1.0", "end")
        for tag, pattern in [("comment", r"--[^\n]*"), ("string", r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\""), ("keyword", r"\b(?:and|break|continue|do|else|elseif|end|export|false|for|function|if|in|local|nil|not|or|repeat|return|then|true|type|typeof|until|while)\b"), ("builtin", r"\b(?:game|workspace|script|Enum|Instance|Vector3|CFrame|Color3|UDim2|task|math|string|table|pairs|ipairs|warn|print|require)\b"), ("number", r"\b\d+(?:\.\d+)?\b")]:
            for m in re.finditer(pattern, code): self.editor.tag_add(tag, f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars")
        self.editor.tag_raise("sel")
    def new(self):
        if self.editor.edit_modified() and not messagebox.askyesno(APP, "Отбросить несохранённые изменения?", parent=self.root): return
        self.path = None; self.name.set("MyScript"); self._set_code("-- Новый Luau-скрипт\n\n"); self.editor.edit_modified(False); self.file_label.config(text="● Untitled.luau")
    def example(self): self.name.set("WelcomeMessage"); self.target.set(list(TARGETS)[0]); self.path = None; self._set_code(SAMPLE); self.editor.edit_modified(False); self.file_label.config(text="● WelcomeMessage.server.lua (пример)")
    def open_file(self):
        p = filedialog.askopenfilename(filetypes=[("Lua / Luau", "*.lua *.luau"), ("Все файлы", "*.*")], parent=self.root)
        if not p: return
        try: text = Path(p).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as e: messagebox.showerror(APP, str(e), parent=self.root); return
        self.path = Path(p); self.name.set(self.path.stem.replace(".server", "").replace(".client", "")); self._set_code(text); self.editor.edit_modified(False); self.file_label.config(text="● "+self.path.name); self.status.set("Открыт: "+str(self.path))
    def save_file(self):
        if not self.path:
            p = filedialog.asksaveasfilename(defaultextension=".luau", initialfile=self._safe(self.name.get())+".luau", filetypes=[("Luau", "*.luau"), ("Lua", "*.lua")], parent=self.root)
            if not p: return
            self.path = Path(p)
        try: self.path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as e: messagebox.showerror(APP, str(e), parent=self.root); return
        self.editor.edit_modified(False); self.file_label.config(text="● "+self.path.name); self.status.set("Сохранено: "+str(self.path)); self.log("Сохранено: "+str(self.path))
    @staticmethod
    def _safe(s): return (re.sub(r"[^A-Za-z0-9_-]+", "_", s.strip()).strip("_-")[:80] or "MyScript")
    def pick_project(self):
        p = filedialog.askdirectory(parent=self.root, title="Папка Rojo-проекта")
        if p: self.project.set(p); self.status.set("Проект: "+p)
    def _project_dir(self):
        p = Path(self.project.get().strip().strip('"')).expanduser() if self.project.get().strip() else None
        if p and p.is_dir(): return p
        chosen = filedialog.askdirectory(parent=self.root, title="Выбери папку проекта Roblox")
        if chosen: self.project.set(chosen); return Path(chosen)
        return None
    def export(self):
        code = self.editor.get("1.0", "end-1c")
        if not code.strip(): messagebox.showwarning(APP, "Редактор пустой.", parent=self.root); return
        root = self._project_dir()
        if not root: return
        folder, suffix = TARGETS.get(self.target.get(), TARGETS[list(TARGETS)[0]])
        outdir = root / "src" / folder; out = outdir / (self._safe(self.name.get())+suffix)
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            config = root / "default.project.json"
            if not config.exists(): config.write_text(json.dumps({**PROJECT, "name": self._safe(root.name)}, indent=2)+"\n", encoding="utf-8")
            if out.exists() and not messagebox.askyesno(APP, f"Перезаписать существующий файл?\n{out}", parent=self.root): return
            out.write_text(code.rstrip()+"\n", encoding="utf-8")
        except OSError as e: messagebox.showerror(APP, str(e), parent=self.root); return
        self.file_label.config(text="● "+out.name); self.status.set("Экспортировано: "+str(out)); self.log("Экспорт: "+str(out))
        messagebox.showinfo(APP, f"Сохранено в:\n{out}\n\nЕсли Rojo подключён к Studio, изменения синхронизируются. Нажми Play в Studio для проверки.", parent=self.root)
    @staticmethod
    def _bracket_error(code):
        stack=[]; i=0; line=1; quote=None; comment=False; pairs={')':'(',']':'[','}':'{'}
        while i < len(code):
            c=code[i]
            if c=='\n': line+=1; comment=False; i+=1; continue
            if comment: i+=1; continue
            if quote:
                if c=='\\': i+=2; continue
                if c==quote: quote=None
                i+=1; continue
            if code[i:i+2]=='--': comment=True; i+=2; continue
            if c in "'\"": quote=c; i+=1; continue
            if c in '([{': stack.append((c,line))
            elif c in ')]}':
                if not stack: return line, f"Лишняя закрывающая скобка {c}"
                op, ln=stack.pop()
                if op != pairs[c]: return line, f"Скобка {c} не соответствует {op} (строка {ln})"
            i+=1
        if quote: return line, "Незакрытая строка"
        if stack: return stack[-1][1], f"Не закрыта скобка {stack[-1][0]}"
        return None
    def check(self):
        error = self._bracket_error(self.editor.get("1.0", "end-1c"))
        if error: self.status.set(f"Проверка: {error[1]} · строка {error[0]}"); messagebox.showwarning(APP, f"{error[1]}\nСтрока {error[0]}", parent=self.root)
        else: self.status.set("Скобки сбалансированы"); messagebox.showinfo(APP, "Скобки сбалансированы. Это не полная проверка синтаксиса Luau.", parent=self.root)
    def start_rojo(self):
        if self.proc and self.proc.poll() is None: self.status.set("Rojo уже работает"); return
        root = self._project_dir()
        if not root: return
        config = root / "default.project.json"
        if not config.exists(): config.write_text(json.dumps({**PROJECT, "name": self._safe(root.name)}, indent=2)+"\n", encoding="utf-8")
        exe = shutil.which("rojo")
        if not exe:
            messagebox.showinfo(APP, "Rojo CLI не найден. Установи Rokit: https://github.com/rojo-rbx/rokit\nВ терминале проекта: rokit add rojo-rbx/rojo\nЗатем: rokit install\nУстанови Studio-плагин: rojo plugin install\nИнструкция: https://rojo.space/docs/v7/getting-started/installation/", parent=self.root); self.status.set("Rojo CLI не найден"); return
        try: self.proc = subprocess.Popen([exe, "serve"], cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        except OSError as e: messagebox.showerror(APP, str(e), parent=self.root); return
        threading.Thread(target=self._read, args=(self.proc,), daemon=True).start(); self.status.set("Rojo запущен — подключи плагин в Studio"); self.log("rojo serve: "+str(root))
    def _read(self, proc):
        if proc.stdout:
            for line in proc.stdout: self.q.put(line.rstrip())
        self.q.put(f"[Rojo завершён: {proc.poll()}]")
    def _poll(self):
        if self.closing: return
        try:
            while True:
                line=self.q.get_nowait(); self.log(line)
                if "localhost" in line.lower() or "listening" in line.lower(): self.status.set("Rojo активен — нажми Connect в Studio")
        except queue.Empty: pass
        self.root.after(200, self._poll)
    def stop_rojo(self):
        if self.proc and self.proc.poll() is None: self.proc.terminate(); self.status.set("Останавливаю Rojo")
        else: self.status.set("Rojo не запущен")
    def open_folder(self):
        root = self._project_dir()
        if not root: return
        try:
            if os.name=="nt": os.startfile(str(root))
            elif sys.platform=="darwin": subprocess.Popen(["open", str(root)])
            else: subprocess.Popen(["xdg-open", str(root)])
        except OSError as e: messagebox.showerror(APP, str(e), parent=self.root)
    def close(self):
        self.closing=True
        if self.proc and self.proc.poll() is None: self.proc.terminate()
        self.root.destroy()

def main():
    root=tk.Tk(); App(root); root.mainloop()

if __name__ == "__main__": main()
