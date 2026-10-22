from __future__ import annotations
import os, re, shutil, subprocess, tempfile, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

APP = "ScriptDeck"
BG, PANEL, EDITOR_BG = "#101015", "#18181f", "#111116"
FG, MUTED, RED, GREEN = "#f1f1f4", "#9a9aa5", "#e84141", "#60d394"
CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "ScriptDeck"
LIBRARY = CONFIG_DIR / "Scripts"
TARGETS = {
    "Server Script · сервер": ("server", ".server.lua"),
    "LocalScript · клиент": ("client", ".client.lua"),
    "ModuleScript · общий модуль": ("shared", ".lua"),
    "LocalScript · StarterGui": ("gui", ".client.lua"),
}

def safe_name(value):
    return (re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_-")[:70] or "MyScript")

class ScriptDeck:
    def __init__(self, root):
        self.root = root
        root.title("ScriptDeck")
        root.geometry("1180x760")
        root.minsize(900, 600)
        root.configure(bg=BG)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        LIBRARY.mkdir(parents=True, exist_ok=True)
        self.tabs = {}
        self.counter = 0
        self.target_var = tk.StringVar(value=list(TARGETS)[0])
        self.status = tk.StringVar(value="Ready")
        self._style()
        self._build()
        self.new_tab()
        self.refresh_library()
        self.log("ScriptDeck ready. Local execution runs in a separate Luau/Lua CLI, not in the Roblox game client.")
        root.bind("<Control-n>", lambda _e: self.new_tab())
        root.bind("<Control-o>", lambda _e: self.open_file())
        root.bind("<Control-s>", lambda _e: self.save_file())
        root.bind("<F5>", lambda _e: self.run_local())
        root.protocol("WM_DELETE_WINDOW", root.destroy)

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TButton", background="#202027", foreground=FG, padding=(9, 7), borderwidth=0, font=("Segoe UI", 9))
        s.map("TButton", background=[("active", "#35353f")])
        s.configure("Execute.TButton", background=RED, foreground="white", padding=(12, 8), font=("Segoe UI", 9, "bold"))
        s.map("Execute.TButton", background=[("active", "#ff5a5a")])
        s.configure("TCombobox", fieldbackground=EDITOR_BG, background="#202027", foreground=FG, arrowcolor=FG, padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", EDITOR_BG)], foreground=[("readonly", FG)])
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 8), borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", EDITOR_BG)], foreground=[("selected", FG)])
        s.configure("Treeview", background=EDITOR_BG, fieldbackground=EDITOR_BG, foreground=FG, rowheight=27, borderwidth=0)
        s.map("Treeview", background=[("selected", "#4a2227")], foreground=[("selected", "white")])

    def _build(self):
        header = tk.Frame(self.root, bg=BG, padx=16, pady=11)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=BG); brand.pack(side="left")
        tk.Label(brand, text="S", bg=RED, fg="white", font=("Segoe UI", 20, "bold"), width=2, pady=3).pack(side="left", padx=(0, 10))
        titles = tk.Frame(brand, bg=BG); titles.pack(side="left")
        tk.Label(titles, text="ScriptDeck", bg=BG, fg=FG, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(titles, text="Lua / Luau workspace", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(header, text="SCRIPT WORKSPACE", bg=BG, fg=RED, font=("Segoe UI", 9, "bold")).pack(side="right")

        toolbar = tk.Frame(self.root, bg=PANEL, padx=9, pady=8); toolbar.pack(fill="x", padx=12, pady=(0, 10))
        for label, cmd in [("＋ New", self.new_tab), ("Open", self.open_file), ("Save", self.save_file),
                           ("Save to Library", self.save_to_library), ("Export to Game", self.export_for_game)]:
            ttk.Button(toolbar, text=label, command=cmd).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Execute · local", style="Execute.TButton", command=self.run_local).pack(side="right", padx=3)

        content = tk.Frame(self.root, bg=BG); content.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        content.grid_rowconfigure(0, weight=1); content.grid_columnconfigure(1, weight=1)
        sidebar = tk.Frame(content, bg=PANEL, width=235, padx=10, pady=12)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10)); sidebar.grid_propagate(False)
        self._section(sidebar, "SCRIPT LIBRARY")
        tk.Label(sidebar, text="Saved scripts", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(11, 6))
        self.library_list = tk.Listbox(sidebar, bg=EDITOR_BG, fg=FG, selectbackground="#4a2227", selectforeground="white",
                                       activestyle="none", borderwidth=0, highlightthickness=0, font=("Consolas", 10))
        self.library_list.pack(fill="both", expand=True)
        self.library_list.bind("<Double-1>", lambda _e: self.open_selected_library())
        tk.Frame(sidebar, bg="#35353f", height=1).pack(fill="x", pady=12)
        self._section(sidebar, "EXPORT TARGET")
        ttk.Combobox(sidebar, textvariable=self.target_var, values=list(TARGETS), state="readonly").pack(fill="x", pady=(9, 6))
        ttk.Button(sidebar, text="Refresh library", command=self.refresh_library).pack(fill="x", pady=3)
        ttk.Button(sidebar, text="Open script folder", command=self.open_library_folder).pack(fill="x", pady=3)
        tk.Label(sidebar, text="F5  Execute locally\nCtrl+N  New tab\nCtrl+O  Open file\nCtrl+S  Save file",
                 bg=PANEL, fg=MUTED, font=("Consolas", 9), justify="left").pack(anchor="w", pady=(14, 0))

        main = tk.Frame(content, bg=PANEL); main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1); main.grid_columnconfigure(0, weight=1)
        self.notebook = ttk.Notebook(main); self.notebook.grid(row=0, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._sync_status())

        console = tk.Frame(self.root, bg=PANEL, padx=10, pady=8); console.pack(fill="x", padx=12, pady=(0, 6))
        top = tk.Frame(console, bg=PANEL); top.pack(fill="x")
        tk.Label(top, text="OUTPUT", bg=PANEL, fg=FG, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(top, text="Clear", command=self.clear_output).pack(side="right")
        self.console = tk.Text(console, height=5, bg="#0a0a0e", fg="#c7cad4", insertbackground="white",
                               font=("Consolas", 9), borderwidth=0, padx=8, pady=6, state="disabled", wrap="word")
        self.console.pack(fill="x", pady=(6, 0))
        tk.Label(self.root, textvariable=self.status, bg=BG, fg=GREEN, anchor="w",
                 font=("Segoe UI", 9), padx=12, pady=5).pack(fill="x")

    @staticmethod
    def _section(parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=FG, font=("Segoe UI", 10, "bold")).pack(anchor="w")

    def _active(self):
        return self.tabs.get(self.notebook.select())

    def _sync_status(self):
        tab = self._active()
        if tab:
            self.status.set("Editing: " + (tab["path"].name if tab["path"] else "Untitled"))

    def new_tab(self, text="", path=None):
        self.counter += 1
        frame = tk.Frame(self.notebook, bg=EDITOR_BG)
        frame.grid_rowconfigure(0, weight=1); frame.grid_columnconfigure(0, weight=1)
        editor = tk.Text(frame, bg=EDITOR_BG, fg="#e8e8ee", insertbackground="white", selectbackground="#54272c",
                         font=("Consolas", 11), padx=14, pady=12, undo=True, wrap="none", borderwidth=0, tabs=(36,))
        editor.grid(row=0, column=0, sticky="nsew")
        ys = ttk.Scrollbar(frame, orient="vertical", command=editor.yview); ys.grid(row=0, column=1, sticky="ns")
        xs = ttk.Scrollbar(frame, orient="horizontal", command=editor.xview); xs.grid(row=1, column=0, sticky="ew")
        editor.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        editor.insert("1.0", text)
        self.tabs[str(frame)] = {"frame": frame, "editor": editor, "path": Path(path) if path else None}
        self.notebook.add(frame, text=(Path(path).name if path else f"Untitled {self.counter}"))
        self.notebook.select(frame); editor.focus_set()
        editor.bind("<KeyRelease>", lambda _e, w=editor: self._highlight(w))
        self._highlight(editor); self._sync_status()

    def _highlight(self, editor):
        code = editor.get("1.0", "end-1c")
        for tag in ("keyword", "string", "comment", "builtin", "number"):
            editor.tag_remove(tag, "1.0", "end")
        rules = [
            ("comment", r"--[^\n]*", "#777b89"),
            ("string", r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", "#a8dba8"),
            ("keyword", r"\b(?:and|break|continue|do|else|elseif|end|export|false|for|function|if|in|local|nil|not|or|repeat|return|then|true|type|typeof|until|while)\b", "#ff777d"),
            ("builtin", r"\b(?:game|workspace|script|Enum|Instance|Vector3|CFrame|Color3|UDim2|task|math|string|table|pairs|ipairs|warn|print|require)\b", "#85c8ff"),
            ("number", r"\b\d+(?:\.\d+)?\b", "#edc58a"),
        ]
        for tag, pattern, color in rules:
            editor.tag_configure(tag, foreground=color)
            for m in re.finditer(pattern, code):
                editor.tag_add(tag, f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars")
        editor.tag_raise("sel")

    def open_file(self):
        paths = filedialog.askopenfilenames(parent=self.root, title="Open script",
            filetypes=[("Lua / Luau", "*.lua *.luau"), ("Text files", "*.txt"), ("All files", "*.*")])
        for filename in paths:
            try:
                text = Path(filename).read_text(encoding="utf-8-sig")
                self.new_tab(text, filename); self.log("Opened: " + filename)
            except (OSError, UnicodeError) as exc:
                messagebox.showerror(APP, f"Could not open file:\n{exc}", parent=self.root)

    def save_file(self):
        tab = self._active()
        if not tab: return
        path = tab["path"]
        if path is None:
            filename = filedialog.asksaveasfilename(parent=self.root, title="Save script", defaultextension=".luau",
                initialfile="NewScript.luau", filetypes=[("Luau", "*.luau"), ("Lua", "*.lua"), ("All files", "*.*")])
            if not filename: return
            path = Path(filename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(tab["editor"].get("1.0", "end-1c"), encoding="utf-8")
            tab["path"] = path; self.notebook.tab(tab["frame"], text=path.name)
            self.status.set("Saved: " + str(path)); self.log("Saved: " + str(path)); self.refresh_library()
        except OSError as exc:
            messagebox.showerror(APP, str(exc), parent=self.root)

    def save_to_library(self):
        tab = self._active()
        if not tab: return
        initial = safe_name(tab["path"].stem if tab["path"] else "MyScript") + ".luau"
        name = simpledialog.askstring(APP, "File name for the library:", initialvalue=initial, parent=self.root)
        if not name: return
        dest = LIBRARY / (safe_name(Path(name).stem) + ".luau")
        try:
            dest.write_text(tab["editor"].get("1.0", "end-1c"), encoding="utf-8")
            self.log("Saved to library: " + str(dest)); self.refresh_library()
        except OSError as exc:
            messagebox.showerror(APP, str(exc), parent=self.root)

    def refresh_library(self):
        self.library_list.delete(0, "end")
        for path in sorted(LIBRARY.glob("*")):
            if path.is_file() and path.suffix.lower() in (".lua", ".luau", ".txt"):
                self.library_list.insert("end", path.name)

    def open_selected_library(self):
        selected = self.library_list.curselection()
        if not selected: return
        path = LIBRARY / self.library_list.get(selected[0])
        try:
            self.new_tab(path.read_text(encoding="utf-8-sig"), path)
            self.log("Opened from library: " + path.name)
        except (OSError, UnicodeError) as exc:
            messagebox.showerror(APP, str(exc), parent=self.root)

    def open_library_folder(self):
        try:
            if os.name == "nt": os.startfile(str(LIBRARY))
            elif os.sys.platform == "darwin": subprocess.Popen(["open", str(LIBRARY)])
            else: subprocess.Popen(["xdg-open", str(LIBRARY)])
        except OSError as exc:
            messagebox.showerror(APP, str(exc), parent=self.root)

    def run_local(self):
        tab = self._active()
        if not tab: return
        runner = shutil.which("luau") or shutil.which("luau.exe") or shutil.which("lua") or shutil.which("lua.exe")
        if not runner:
            message = ("Local Luau/Lua runtime was not found.\n\n"
                       "Install the Luau CLI and add luau.exe to PATH to run general Lua/Luau code locally.\n"
                       "Roblox APIs such as game, workspace and Players only exist inside Roblox. "
                       "This button does not execute code in the Roblox client.")
            self.log(message); messagebox.showinfo(APP, message, parent=self.root); return
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".luau", delete=False, encoding="utf-8", newline="\n") as f:
                f.write(tab["editor"].get("1.0", "end-1c")); temp_path = Path(f.name)
            try:
                result = subprocess.run([runner, str(temp_path)], capture_output=True, text=True,
                                        encoding="utf-8", errors="replace", timeout=10, cwd=str(LIBRARY))
            finally:
                temp_path.unlink(missing_ok=True)
            if result.stdout.strip(): self.log(result.stdout.rstrip())
            if result.stderr.strip(): self.log(result.stderr.rstrip(), error=True)
            self.log(f"Local runtime exit code: {result.returncode}")
            self.status.set(f"Local run finished · exit {result.returncode}")
        except subprocess.TimeoutExpired:
            self.log("Execution stopped after 10 seconds (timeout).", error=True); self.status.set("Local run timed out")
        except OSError as exc:
            self.log(f"Could not start local runtime: {exc}", error=True)

    def export_for_game(self):
        tab = self._active()
        if not tab: return
        folder, suffix = TARGETS[self.target_var.get()]
        project = filedialog.askdirectory(parent=self.root, title="Choose your Roblox project folder")
        if not project: return
        initial = safe_name(tab["path"].stem if tab["path"] else "MyScript")
        name = simpledialog.askstring(APP, "Script file name:", initialvalue=initial, parent=self.root)
        if not name: return
        dest_dir = Path(project) / "src" / folder
        dest = dest_dir / (safe_name(name) + suffix)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest.exists() and not messagebox.askyesno(APP, f"Replace existing file?\n{dest}", parent=self.root): return
            dest.write_text(tab["editor"].get("1.0", "end-1c").rstrip() + "\n", encoding="utf-8")
            self.log("Exported to Roblox project: " + str(dest))
            self.status.set("Exported: " + dest.name)
            messagebox.showinfo(APP, f"Script exported:\n{dest}\n\nFor your own experience, sync the project in Roblox Studio through Rojo and use Play/Test.", parent=self.root)
        except OSError as exc:
            messagebox.showerror(APP, str(exc), parent=self.root)

    def log(self, message, error=False):
        self.console.configure(state="normal")
        if error:
            self.console.insert("end", "[error] " + message + "\n", "err")
            self.console.tag_configure("err", foreground="#ff777d")
        else:
            self.console.insert("end", message.rstrip() + "\n")
        self.console.see("end"); self.console.configure(state="disabled")

    def clear_output(self):
        self.console.configure(state="normal"); self.console.delete("1.0", "end"); self.console.configure(state="disabled")


def main():
    root = tk.Tk()
    ScriptDeck(root)
    root.mainloop()

if __name__ == "__main__":
    main()
