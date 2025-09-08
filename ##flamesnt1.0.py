#!/usr/bin/env python3
# FlamesNT 1.0 - a GUI-only "toy OS shell" in one Python file.
# Inspired by Windows 1.0's tiled feel, modernized a bit.
# No external libs needed (tkinter/ttk only).
#
# NOTE: This is not a real OS. It's a playful desktop shell for demo and learning.
#       You can extend it with more "apps" in this single file.

import os
import sys
import math
import time
import datetime as dt
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from typing import Optional, List, Tuple, Dict, Any

__PRODUCT__ = "FlamesNT"
__VERSION__ = "1.0"
__TITLE__ = f"{__PRODUCT__} {__VERSION__}"


# ----------------------------- Theming ---------------------------------------

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "desktop_bg": "#0f1115",
        "bg": "#171a21",
        "window_bg": "#171a21",
        "fg": "#e6e6e6",
        "muted": "#b7beca",
        "accent": "#ff5c1a",
        "button_bg": "#232733",
        "button_active": "#2b3142",
        "taskbar_bg": "#0c0e12",
        "input_bg": "#10131a",
        "canvas_bg": "#ffffff",
    },
    "light": {
        "desktop_bg": "#e9edf5",
        "bg": "#f7f9fc",
        "window_bg": "#ffffff",
        "fg": "#10131a",
        "muted": "#4b5565",
        "accent": "#d9480f",
        "button_bg": "#eef1f7",
        "button_active": "#e1e6f0",
        "taskbar_bg": "#dde3ee",
        "input_bg": "#ffffff",
        "canvas_bg": "#ffffff",
    },
}


# ---------------------------- Utilities --------------------------------------

def platform_open(path: str) -> None:
    """Open a file using the platform's default handler."""
    try:
        if not os.path.exists(path):
            messagebox.showerror("Open Error", f"Path does not exist:\n{path}")
            return
            
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Open Error", f"Could not open:\n{path}\n\n{e}")


def human_size(n: int) -> str:
    """Convert bytes to human-readable format."""
    if n < 0:
        return "0 B"
    
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} PB"


# --------------------------- Window Manager ----------------------------------

class WindowManager:
    def __init__(self, app: "FlamesNTApp"):
        self.app = app
        self.windows: List[tk.Toplevel] = []

    # --- registry ---
    def register(self, win: tk.Toplevel) -> None:
        if win not in self.windows:
            self.windows.append(win)
            self.app.update_taskbar()

    def unregister(self, win: tk.Toplevel) -> None:
        if win in self.windows:
            self.windows.remove(win)
            self.app.update_taskbar()

    # --- arrange ---
    def _visible_windows(self) -> List[tk.Toplevel]:
        visible = []
        for w in self.windows:
            try:
                if str(w.state()) == "normal":
                    visible.append(w)
            except tk.TclError:
                pass
        return visible

    def cascade(self) -> None:
        ws = self._visible_windows()
        if not ws:
            return
        
        self.app.update_idletasks()
        step = 28
        x0 = 10
        y0 = 10
        
        try:
            avail_w = self.app.winfo_width()
            avail_h = self.app.winfo_height() - self.app.taskbar.winfo_height()
        except tk.TclError:
            return
            
        base_w = max(480, int(avail_w * 0.62))
        base_h = max(320, int(avail_h * 0.62))
        
        for i, w in enumerate(ws):
            x = x0 + i * step
            y = y0 + i * step
            # Ensure windows don't go off-screen
            x = min(x, avail_w - 100)
            y = min(y, avail_h - 100)
            try:
                w.geometry(f"{base_w}x{base_h}+{x}+{y}")
                w.lift()
            except tk.TclError:
                pass

    def tile(self, orientation: str = "auto") -> None:
        ws = self._visible_windows()
        if not ws:
            return
        
        self.app.update_idletasks()

        try:
            W = self.app.winfo_width()
            H = self.app.winfo_height() - self.app.taskbar.winfo_height()
        except tk.TclError:
            return
            
        n = len(ws)

        if orientation == "vertical":
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)
        elif orientation == "horizontal":
            rows = math.ceil(math.sqrt(n))
            cols = math.ceil(n / rows)
        else:
            # auto: prefer roughly square grid
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)

        cell_w = max(340, W // max(1, cols))
        cell_h = max(240, H // max(1, rows))

        for idx, w in enumerate(ws):
            r = idx // cols
            c = idx % cols
            x = c * cell_w
            y = r * cell_h
            try:
                w.geometry(f"{cell_w}x{cell_h}+{x}+{y}")
                w.lift()
            except tk.TclError:
                pass

    def minimize_all(self) -> None:
        for w in self.windows:
            try:
                w.iconify()
            except tk.TclError:
                pass

    def restore_all(self) -> None:
        for w in self.windows:
            try:
                w.deiconify()
                w.lift()
            except tk.TclError:
                pass


# ------------------------------ Base App Window -------------------------------

class AppWindow(tk.Toplevel):
    def __init__(self, app: "FlamesNTApp", title: str, minsize: Tuple[int, int] = (360, 240)):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(bg=self.app.colors["window_bg"])
        self.minsize(*minsize)
        self._task_button: Optional[tk.Button] = None

        # register with window manager
        self.app.wm.register(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<FocusIn>", lambda e: self.app.highlight_task_button(self))

        # custom menu holder (per-window)
        self.menu = tk.Menu(self, tearoff=False)
        self.config(menu=self.menu)

    def _on_close(self) -> None:
        self.app.wm.unregister(self)
        try:
            self.destroy()
        except tk.TclError:
            pass

    # convenience
    def themed_frame(self, **kwargs) -> ttk.Frame:
        return ttk.Frame(self, **kwargs)

    def themed_label(self, **kwargs) -> ttk.Label:
        return ttk.Label(self, **kwargs)

    def themed_button(self, **kwargs) -> ttk.Button:
        return ttk.Button(self, **kwargs)


# ------------------------------ Built-in Apps ---------------------------------

class Notepad(AppWindow):
    def __init__(self, app: "FlamesNTApp", path: Optional[str] = None):
        super().__init__(app, "Flames Notepad", minsize=(420, 320))

        self.path: Optional[str] = None
        c = self.app.colors

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.text = tk.Text(
            self.container,
            wrap="word",
            undo=True,
            bg=c["input_bg"],
            fg=c["fg"],
            insertbackground=c["fg"],
            relief="flat",
        )
        self.scroll = ttk.Scrollbar(self.container, command=self.text.yview)
        self.text.config(yscrollcommand=self.scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self.status = ttk.Label(self, text="Ready", anchor="w")
        self.status.pack(side="bottom", fill="x")

        # menu
        file_m = tk.Menu(self.menu, tearoff=False)
        edit_m = tk.Menu(self.menu, tearoff=False)
        view_m = tk.Menu(self.menu, tearoff=False)

        file_m.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_m.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_file)
        file_m.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_m.add_command(label="Save As…", command=self.save_as)
        file_m.add_separator()
        file_m.add_command(label="Exit", command=self._on_close)

        edit_m.add_command(label="Cut", accelerator="Ctrl+X",
                           command=lambda: self.text.event_generate("<<Cut>>"))
        edit_m.add_command(label="Copy", accelerator="Ctrl+C",
                           command=lambda: self.text.event_generate("<<Copy>>"))
        edit_m.add_command(label="Paste", accelerator="Ctrl+V",
                           command=lambda: self.text.event_generate("<<Paste>>"))
        edit_m.add_separator()
        edit_m.add_command(label="Select All", accelerator="Ctrl+A",
                           command=lambda: self.text.tag_add(tk.SEL, "1.0", tk.END))

        self._wrap_var = tk.BooleanVar(value=True)
        view_m.add_checkbutton(
            label="Word Wrap", variable=self._wrap_var, command=self._toggle_wrap
        )

        self.menu.add_cascade(label="File", menu=file_m)
        self.menu.add_cascade(label="Edit", menu=edit_m)
        self.menu.add_cascade(label="View", menu=view_m)

        # bindings
        self.bind("<Control-n>", lambda e: self.new_file() or "break")
        self.bind("<Control-o>", lambda e: self.open_file() or "break")
        self.bind("<Control-s>", lambda e: self.save() or "break")
        self.bind("<Control-a>", lambda e: self.text.tag_add(tk.SEL, "1.0", tk.END) or "break")
        self.text.bind("<<Modified>>", self._on_modified)

        # preload if path provided
        if path:
            self.load_path(path)
        else:
            self.text.edit_modified(False)

    # --- file ops ---
    def new_file(self) -> None:
        if self._confirm_discard():
            self.text.delete("1.0", tk.END)
            self.path = None
            self.text.edit_modified(False)
            self.title("Flames Notepad - Untitled")
            self.status.config(text="New file")

    def open_file(self) -> None:
        p = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("Text files", "*.txt *.md *.py *.json *.csv *.log"), ("All files", "*.*")]
        )
        if p:
            self.load_path(p)

    def load_path(self, p: str) -> None:
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
            self.text.delete("1.0", tk.END)
            self.text.insert("1.0", data)
            self.path = p
            self.text.edit_modified(False)
            self.title(f"Flames Notepad - {os.path.basename(p)}")
            self.status.config(text=f"Opened: {p}")
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open file:\n{p}\n\n{e}")

    def save(self) -> bool:
        if not self.path:
            return self.save_as()
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            self.text.edit_modified(False)
            self.status.config(text=f"Saved: {self.path}")
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file:\n{self.path}\n\n{e}")
            return False

    def save_as(self) -> bool:
        p = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")]
        )
        if not p:
            return False
        self.path = p
        return self.save()

    # --- helpers ---
    def _on_modified(self, _evt=None) -> None:
        self._update_title_dirty()
        chars = len(self.text.get("1.0", "end-1c"))
        lines = self.text.get("1.0", tk.END).count("\n")
        self.status.config(text=f"{chars} chars, {lines} lines")

    def _toggle_wrap(self) -> None:
        self.text.config(wrap="word" if self._wrap_var.get() else "none")

    def _update_title_dirty(self) -> None:
        base = os.path.basename(self.path) if self.path else "Untitled"
        dirty = self.text.edit_modified()
        self.title(f"Flames Notepad - {base}{' *' if dirty else ''}")

    def _confirm_discard(self) -> bool:
        if self.text.edit_modified():
            return messagebox.askyesno("Discard changes?", "You have unsaved changes. Discard?")
        return True

    def _on_close(self) -> None:
        if self._confirm_discard():
            super()._on_close()


class Paint(AppWindow):
    def __init__(self, app: "FlamesNTApp"):
        super().__init__(app, "Flames Paint", minsize=(420, 320))
        c = self.app.colors

        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=6, pady=6)

        self.pen_color = tk.StringVar(value="#1e90ff")
        self.pen_size = tk.IntVar(value=3)

        ttk.Label(toolbar, text="Pen size:").pack(side="left", padx=(0, 4))
        size_spin = ttk.Spinbox(toolbar, from_=1, to=20, width=5, textvariable=self.pen_size)
        size_spin.pack(side="left", padx=5)
        
        ttk.Button(toolbar, text="Color…", command=self.pick_color).pack(side="left")
        
        # Color preview
        self.color_preview = tk.Label(toolbar, width=3, bg=self.pen_color.get())
        self.color_preview.pack(side="left", padx=5)

        ttk.Button(toolbar, text="Clear", command=self.clear_canvas).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Export .ps", command=self.export_ps).pack(side="left")

        self.canvas = tk.Canvas(self, bg=c["canvas_bg"], highlightthickness=0, cursor="pencil")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._last: Optional[Tuple[int, int]] = None
        self.canvas.bind("<Button-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._up)

    def pick_color(self) -> None:
        rgb, hexv = colorchooser.askcolor(color=self.pen_color.get(), title="Choose Pen Color")
        if hexv:
            self.pen_color.set(hexv)
            self.color_preview.config(bg=hexv)

    def clear_canvas(self) -> None:
        if self.canvas.find_all():
            if messagebox.askyesno("Clear Canvas", "Clear all drawings?"):
                self.canvas.delete("all")

    def _down(self, e: tk.Event) -> None:
        self._last = (e.x, e.y)

    def _draw(self, e: tk.Event) -> None:
        if self._last is None:
            self._last = (e.x, e.y)
        x0, y0 = self._last
        x1, y1 = e.x, e.y
        self.canvas.create_line(
            x0, y0, x1, y1, 
            fill=self.pen_color.get(), 
            width=self.pen_size.get(), 
            capstyle="round",
            smooth=True
        )
        self._last = (x1, y1)

    def _up(self, e: tk.Event) -> None:
        self._last = None

    def export_ps(self) -> None:
        p = filedialog.asksaveasfilename(
            title="Export PostScript",
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("All files", "*.*")]
        )
        if not p:
            return
        try:
            self.canvas.postscript(file=p, colormode="color")
            messagebox.showinfo("Exported", f"Canvas exported to:\n{p}\n\nTip: convert to PNG using external tools if needed.")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{e}")


class Calculator(AppWindow):
    def __init__(self, app: "FlamesNTApp"):
        super().__init__(app, "Flames Calculator", minsize=(300, 380))
        c = self.app.colors

        self.expr = tk.StringVar(value="")
        self.result_shown = False
        
        entry = tk.Entry(
            self, 
            textvariable=self.expr, 
            bg=c["input_bg"], 
            fg=c["fg"], 
            insertbackground=c["fg"], 
            relief="flat", 
            font=("Segoe UI", 16),
            justify="right"
        )
        entry.pack(side="top", fill="x", padx=10, pady=10)
        entry.focus_set()

        grid = ttk.Frame(self)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        buttons = [
            "7", "8", "9", "÷",
            "4", "5", "6", "×",
            "1", "2", "3", "−",
            "0", ".", "=", "+",
            "C", "(", ")", "⌫",
        ]

        def add_btn(text: str, r: int, c: int) -> None:
            b = ttk.Button(grid, text=text, command=lambda t=text: self.on_button(t))
            b.grid(row=r, column=c, sticky="nsew", padx=4, pady=4, ipady=8)

        rows = 5
        cols = 4
        for r in range(rows):
            grid.rowconfigure(r, weight=1)
        for c in range(cols):
            grid.columnconfigure(c, weight=1)

        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx < len(buttons):
                    add_btn(buttons[idx], r, c)
                    idx += 1

        self.bind("<Return>", lambda e: self.on_button("="))
        self.bind("<Escape>", lambda e: self.on_button("C"))
        self.bind("<BackSpace>", lambda e: self.on_button("⌫"))
        
        # Bind number keys
        for i in range(10):
            self.bind(str(i), lambda e, n=str(i): self.on_button(n))

    def on_button(self, sym: str) -> None:
        # Clear result if starting new expression
        if self.result_shown and sym not in ["=", "C", "⌫"]:
            if sym in "0123456789(":
                self.expr.set("")
            self.result_shown = False
            
        if sym == "C":
            self.expr.set("")
            self.result_shown = False
            return
        if sym == "⌫":
            self.expr.set(self.expr.get()[:-1])
            self.result_shown = False
            return
        if sym == "=":
            self.evaluate()
            return
            
        mapping = {"÷": "/", "×": "*", "−": "-"}
        self.expr.set(self.expr.get() + mapping.get(sym, sym))

    def evaluate(self) -> None:
        s = self.expr.get().strip()
        if not s:
            return
            
        # Replace display symbols with Python operators
        s = s.replace("÷", "/").replace("×", "*").replace("−", "-")
        
        # Very strict validation - only allow safe math operations
        allowed = "0123456789+-*/(). "
        if any(ch not in allowed for ch in s):
            messagebox.showerror("Error", "Invalid characters in expression.")
            return
            
        try:
            # Safe evaluation using compile with restricted mode
            # Only allow arithmetic operations
            code = compile(s, '<string>', 'eval')
            
            # Check for dangerous operations
            if any(name in code.co_names for name in ['__import__', 'eval', 'exec', 'compile', 'open']):
                messagebox.showerror("Error", "Invalid expression.")
                return
                
            # Evaluate with empty namespace (no builtins)
            val = eval(code, {"__builtins__": {}}, {})
            
            # Format result nicely
            if isinstance(val, float) and val.is_integer():
                val = int(val)
                
            self.expr.set(str(val))
            self.result_shown = True
            
        except ZeroDivisionError:
            messagebox.showerror("Error", "Division by zero.")
        except (SyntaxError, ValueError, TypeError):
            messagebox.showerror("Error", "Invalid expression.")
        except Exception as e:
            messagebox.showerror("Error", f"Calculation error: {e}")


class Clock(AppWindow):
    def __init__(self, app: "FlamesNTApp"):
        super().__init__(app, "Flames Clock", minsize=(260, 160))
        
        self.label = ttk.Label(self, anchor="center", font=("Segoe UI", 24))
        self.label.pack(fill="both", expand=True, padx=16, pady=16)
        
        self.tz_label = ttk.Label(self, anchor="center", font=("Segoe UI", 10))
        self.tz_label.pack(pady=(0, 10))
        
        self.tz = time.tzname[0] if time.tzname else "Local"
        self._tick()

    def _tick(self) -> None:
        try:
            now = dt.datetime.now()
            s = now.strftime("%H:%M:%S\n%a, %b %d %Y")
            self.label.config(text=s)
            self.tz_label.config(text=f"Timezone: {self.tz}")
        except Exception:
            pass
        self.after(250, self._tick)


class Explorer(AppWindow):
    COLS = ("name", "size", "type", "modified")

    def __init__(self, app: "FlamesNTApp", start_dir: Optional[str] = None):
        super().__init__(app, "Flames Explorer", minsize=(520, 360))
        self.curdir = start_dir or os.path.expanduser("~")

        # Nav bar
        nav = ttk.Frame(self)
        nav.pack(side="top", fill="x", padx=8, pady=8)

        ttk.Label(nav, text="Path:").pack(side="left", padx=(0, 4))
        self.path_var = tk.StringVar(value=self.curdir)
        self.path_entry = ttk.Entry(nav, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.path_entry.bind("<Return>", lambda e: self.go_path())
        
        ttk.Button(nav, text="Go", command=self.go_path).pack(side="left")
        ttk.Button(nav, text="Up", command=self.go_up).pack(side="left", padx=4)
        ttk.Button(nav, text="Home", command=self.go_home).pack(side="left")
        ttk.Button(nav, text="Open External", command=lambda: platform_open(self.curdir)).pack(side="left", padx=8)

        # Listing
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        self.tree = ttk.Treeview(tree_frame, columns=self.COLS, show="headings")
        
        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        headings = {
            "name": "Name",
            "size": "Size",
            "type": "Type",
            "modified": "Modified",
        }
        for k, v in headings.items():
            self.tree.heading(k, text=v, command=lambda c=k: self.sort_by_column(c))
            
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("type", width=100, anchor="w")
        self.tree.column("modified", width=140, anchor="w")

        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<Return>", self.on_double)
        
        # Context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open", command=self.open_selected)
        self.context_menu.add_command(label="Open in System", command=self.open_in_system)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        self.populate()

    def go_home(self) -> None:
        self.curdir = os.path.expanduser("~")
        self.path_var.set(self.curdir)
        self.populate()

    def go_up(self) -> None:
        parent = os.path.dirname(self.curdir.rstrip(os.sep))
        if parent and os.path.isdir(parent):
            self.curdir = parent
            self.path_var.set(self.curdir)
            self.populate()

    def go_path(self) -> None:
        p = self.path_var.get().strip()
        p = os.path.expanduser(p)  # Expand ~ to home directory
        
        if not p:
            p = self.curdir
            
        if os.path.isdir(p):
            self.curdir = os.path.abspath(p)
            self.path_var.set(self.curdir)
            self.populate()
        else:
            messagebox.showerror("Not Found", f"Directory does not exist:\n{p}")
            self.path_var.set(self.curdir)

    def populate(self) -> None:
        # Clear existing items
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        try:
            items = []
            with os.scandir(self.curdir) as it:
                for entry in it:
                    try:
                        # Skip hidden files on Unix-like systems
                        if entry.name.startswith('.') and sys.platform != "win32":
                            continue
                            
                        is_dir = entry.is_dir(follow_symlinks=False)
                        ftype = "Folder" if is_dir else self._get_file_type(entry.name)
                        
                        try:
                            stat = entry.stat(follow_symlinks=False)
                            size = 0 if is_dir else stat.st_size
                            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                        except (OSError, PermissionError):
                            size = 0
                            mtime = "—"
                            
                        items.append((entry.name, size, ftype, mtime, is_dir, entry.path))
                    except Exception:
                        continue
                        
            # Sort: folders first, then files, alphabetically
            items.sort(key=lambda t: (not t[4], t[0].lower()))
            
            for name, size, ftype, mtime, is_dir, path in items:
                self.tree.insert("", "end", 
                               values=(name, "" if is_dir else human_size(size), ftype, mtime), 
                               tags=(path, "dir" if is_dir else "file"))
                               
        except PermissionError:
            messagebox.showwarning("Permission Denied", f"Cannot access:\n{self.curdir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list directory:\n{self.curdir}\n\n{e}")

        self.title(f"Flames Explorer - {self.curdir}")

    def _get_file_type(self, filename: str) -> str:
        """Get file type based on extension."""
        if "." in filename:
            ext = filename.split(".")[-1].upper()
            return f"{ext} File"
        return "File"

    def sort_by_column(self, col: str) -> None:
        """Sort treeview by column."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        
        # Sort with proper handling of different data types
        if col == "size":
            # Extract numeric size for sorting
            def get_size(item):
                size_str = item[0]
                if not size_str:
                    return 0
                # Parse human-readable size back to bytes
                parts = size_str.split()
                if len(parts) == 2:
                    num, unit = parts
                    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
                    return float(num) * multipliers.get(unit, 1)
                return 0
            items.sort(key=lambda x: get_size(x))
        else:
            items.sort()
            
        # Rearrange items
        for index, (val, k) in enumerate(items):
            self.tree.move(k, '', index)

    def on_double(self, _evt) -> None:
        self.open_selected()

    def open_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
            
        item = sel[0]
        tags = self.tree.item(item, "tags")
        if not tags:
            return
            
        path = tags[0]
        
        if os.path.isdir(path):
            self.curdir = path
            self.path_var.set(path)
            self.populate()
        else:
            # Try to open text files in Notepad, else system default
            text_exts = {".txt", ".md", ".py", ".json", ".csv", ".log", ".ini", ".cfg", ".xml", ".html", ".css", ".js"}
            if os.path.splitext(path)[1].lower() in text_exts:
                Notepad(self.app, path)
            else:
                platform_open(path)

    def open_in_system(self) -> None:
        sel = self.tree.selection()
        if sel:
            item = sel[0]
            tags = self.tree.item(item, "tags")
            if tags:
                platform_open(tags[0])

    def show_context_menu(self, event) -> None:
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)


# ------------------------------ Main Desktop ----------------------------------

class FlamesNTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # basics
        self.title(__TITLE__)
        self.geometry("1200x750+120+60")
        self.minsize(900, 600)

        # ttk theme + colors
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.theme_name = "dark"
        self.colors = THEMES[self.theme_name]

        self.configure(bg=self.colors["desktop_bg"])

        # window manager
        self.wm = WindowManager(self)

        # UI
        self._make_menubar()
        self._make_taskbar()
        self._make_desktop()

        self._apply_style()
        self._tick_clock()

    # --- UI builders ---
    def _make_menubar(self) -> None:
        self.menubar = tk.Menu(self, tearoff=False)

        sys_m = tk.Menu(self.menubar, tearoff=False)
        sys_m.add_command(label="About FlamesNT…", command=self._about)
        sys_m.add_separator()
        sys_m.add_command(label="Toggle Theme (Light/Dark)", command=self.toggle_theme)
        sys_m.add_separator()
        sys_m.add_command(label="Exit", command=self.quit_app)

        prog_m = tk.Menu(self.menubar, tearoff=False)
        prog_m.add_command(label="Notepad", command=lambda: Notepad(self))
        prog_m.add_command(label="Paint", command=lambda: Paint(self))
        prog_m.add_command(label="Calculator", command=lambda: Calculator(self))
        prog_m.add_command(label="Clock", command=lambda: Clock(self))
        prog_m.add_command(label="Explorer", command=lambda: Explorer(self))

        win_m = tk.Menu(self.menubar, tearoff=False)
        win_m.add_command(label="Cascade", command=self.wm.cascade)
        win_m.add_command(label="Tile (Auto)", command=lambda: self.wm.tile("auto"))
        win_m.add_command(label="Tile (Vertical)", command=lambda: self.wm.tile("vertical"))
        win_m.add_command(label="Tile (Horizontal)", command=lambda: self.wm.tile("horizontal"))
        win_m.add_separator()
        win_m.add_command(label="Minimize All", command=self.wm.minimize_all)
        win_m.add_command(label="Restore All", command=self.wm.restore_all)

        self.menubar.add_cascade(label="System", menu=sys_m)
        self.menubar.add_cascade(label="Programs", menu=prog_m)
        self.menubar.add_cascade(label="Windows", menu=win_m)

        self.config(menu=self.menubar)

    def _make_taskbar(self) -> None:
        c = self.colors
        self.taskbar = tk.Frame(self, bg=c["taskbar_bg"], height=36)
        self.taskbar.pack(side="bottom", fill="x")
        self.taskbar.pack_propagate(False)  # Maintain fixed height

        # "Start" programs menu on the left
        self.start_btn = tk.Menubutton(
            self.taskbar, 
            text="⊞ Start", 
            relief="raised",
            bg=c["button_bg"],
            fg=c["fg"],
            activebackground=c["button_active"]
        )
        self.start_menu = tk.Menu(self.start_btn, tearoff=False)
        
        programs = [
            ("📝 Notepad", lambda: Notepad(self)),
            ("🎨 Paint", lambda: Paint(self)),
            ("🔢 Calculator", lambda: Calculator(self)),
            ("⏰ Clock", lambda: Clock(self)),
            ("📁 Explorer", lambda: Explorer(self)),
        ]
        
        for label, cmd in programs:
            self.start_menu.add_command(label=label, command=cmd)
            
        self.start_btn.configure(menu=self.start_menu)
        self.start_btn.pack(side="left", padx=6, pady=3)

        # running window buttons
        self.task_buttons = tk.Frame(self.taskbar, bg=c["taskbar_bg"])
        self.task_buttons.pack(side="left", fill="x", expand=True)

        # Clock on the right
        self.tb_clock = tk.Label(self.taskbar, text="", bg=c["taskbar_bg"], fg=c["fg"])
        self.tb_clock.pack(side="right", padx=8)

    def _make_desktop(self) -> None:
        # Desktop area with gradient effect
        self.desktop = tk.Canvas(self, highlightthickness=0, bg=self.colors["desktop_bg"])
        self.desktop.pack(side="top", fill="both", expand=True)

        # Welcome splash
        self._splash = tk.Label(
            self.desktop,
            text=f"{__TITLE__}\nGUI Desktop Shell\n\n🖱️ Click 'Start' or use 'Programs' menu\nto launch applications",
            fg=self.colors["muted"],
            bg=self.colors["desktop_bg"],
            font=("Segoe UI", 12),
            justify="center",
        )
        self._splash_id = self.desktop.create_window(0, 0, anchor="center", window=self._splash)
        self.bind("<Configure>", self._center_splash)

    # --- helpers ---
    def _center_splash(self, _evt=None) -> None:
        try:
            w = self.desktop.winfo_width()
            h = self.desktop.winfo_height()
            self.desktop.coords(self._splash_id, w // 2, h // 2)
        except (tk.TclError, ValueError):
            pass

    def _apply_style(self) -> None:
        c = self.colors
        self.configure(bg=c["desktop_bg"])
        self.desktop.configure(bg=c["desktop_bg"])
        
        # Update splash
        if hasattr(self, "_splash"):
            self._splash.configure(bg=c["desktop_bg"], fg=c["muted"])
        
        # ttk styles
        self.style.configure(".", background=c["bg"], foreground=c["fg"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        self.style.configure("TButton", padding=6)
        self.style.map("TButton", 
                      background=[("active", c["button_active"]), ("!active", c["button_bg"])])
        
        # Taskbar
        self.taskbar.configure(bg=c["taskbar_bg"])
        self.task_buttons.configure(bg=c["taskbar_bg"])
        self.tb_clock.configure(bg=c["taskbar_bg"], fg=c["fg"])
        self.start_btn.configure(bg=c["button_bg"], fg=c["fg"], activebackground=c["button_active"])
        
        # Update existing task buttons
        for child in self.task_buttons.winfo_children():
            child.configure(bg=c["button_bg"], fg=c["fg"], activebackground=c["button_active"])

    def update_taskbar(self) -> None:
        # Rebuild buttons for running windows
        for child in self.task_buttons.winfo_children():
            child.destroy()

        c = self.colors
        for w in self.wm.windows:
            try:
                text = w.title()
                # Truncate long titles
                if len(text) > 30:
                    text = text[:27] + "..."
                    
                btn = tk.Button(
                    self.task_buttons,
                    text=text,
                    relief="groove",
                    bg=c["button_bg"],
                    fg=c["fg"],
                    activebackground=c["button_active"],
                    command=lambda win=w: self.focus_window(win),
                )
                btn.pack(side="left", padx=2, pady=4)
                w._task_button = btn
            except tk.TclError:
                pass

    def highlight_task_button(self, target: tk.Toplevel) -> None:
        for w in self.wm.windows:
            btn = getattr(w, "_task_button", None)
            if btn:
                try:
                    btn.config(relief="groove")
                except tk.TclError:
                    pass
                    
        target_btn = getattr(target, "_task_button", None)
        if target_btn:
            try:
                target_btn.config(relief="sunken")
            except tk.TclError:
                pass

    def focus_window(self, w: tk.Toplevel) -> None:
        try:
            w.deiconify()
            w.lift()
            w.focus_force()
            self.highlight_task_button(w)
        except tk.TclError:
            pass

    def _tick_clock(self) -> None:
        try:
            now = dt.datetime.now()
            self.tb_clock.config(text=now.strftime("%H:%M:%S"))
        except Exception:
            pass
        self.after(250, self._tick_clock)

    def toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.colors = THEMES[self.theme_name]
        self._apply_style()
        
        # Update windows
        for w in self.wm.windows:
            try:
                w.configure(bg=self.colors["window_bg"])
                # Update text widgets in Notepad
                if isinstance(w, Notepad):
                    w.text.configure(
                        bg=self.colors["input_bg"],
                        fg=self.colors["fg"],
                        insertbackground=self.colors["fg"]
                    )
                # Update canvas in Paint
                elif isinstance(w, Paint):
                    w.canvas.configure(bg=self.colors["canvas_bg"])
                # Update entry in Calculator
                elif isinstance(w, Calculator):
                    for child in w.winfo_children():
                        if isinstance(child, tk.Entry):
                            child.configure(
                                bg=self.colors["input_bg"],
                                fg=self.colors["fg"],
                                insertbackground=self.colors["fg"]
                            )
            except tk.TclError:
                pass

    def quit_app(self) -> None:
        if messagebox.askyesno("Exit FlamesNT", "Exit FlamesNT?"):
            self.quit()

    def _about(self) -> None:
        about_text = (
            f"{__TITLE__}\n\n"
            f"A retro-inspired desktop shell\n"
            f"Built with Python & tkinter\n\n"
            f"Features:\n"
            f"• Multiple applications\n"
            f"• Window management\n"
            f"• Theme switching\n"
            f"• File explorer\n\n"
            f"© 2024 - Educational Demo"
        )
        messagebox.showinfo("About FlamesNT", about_text)


def main():
    try:
        app = FlamesNTApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
