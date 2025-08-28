#!/usr/bin/env python3
"""
Flames Co. Indy v0.9.1 [BETA] - SGI IRIX Desktop Environment
Fixed & polished single-file build.

Key fixes & improvements:
- Fixes crash when typing `exit` in the console (no prompt insertion after window destroy).
- Adds simple command history (Up/Down arrows).
- Ensures the console gets keyboard focus on open.
- Adds hover feedback for Toolchest buttons.
- Minor cleanup of imports and widget options.
"""

import tkinter as tk
from tkinter import Menu, Text, Canvas, Toplevel, Frame, Label, Button, Listbox, messagebox
from datetime import datetime


class SgiIndyDesktop:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Flames Co. Indy v0.9.1 [BETA] - IRIX 5.3")
        self.root.geometry("1280x1024")  # Desktop-style fixed geometry
        self.root.minsize(800, 600)

        # Color palette
        self.colors = {
            "desktop": "#4B7399",
            "desktop_pattern": "#5A86A8",
            "toolchest": "#446688",
            "toolchest_hover": "#5577AA",
            "window_bg": "#C4C4C4",
            "window_title": "#446688",
            "window_content": "#E0E0E0",
            "highlight": "#FFC800",
            "text_light": "#FFFFFF",
            "console_bg": "#1E1E1E",
            "console_fg": "#FFFFFF",
        }

        # Session state
        self.username, self.hostname = "guest", "indy"
        self.command_history: list[str] = []
        self.history_index: int = 0

        # Desktop UI
        self.root.configure(bg=self.colors["desktop"])
        self.create_desktop_background()
        self.create_toolchest()
        self.create_desktop_icons()
        self.create_status_bar()

        # Window protocol & clock
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_clock()

    # ---------------- Desktop ----------------
    def create_desktop_background(self) -> None:
        self.desktop_canvas = Canvas(self.root, bg=self.colors["desktop"], highlightthickness=0)
        self.desktop_canvas.place(x=0, y=30, width=1280, height=964)

        # Grid pattern
        for i in range(0, 1280, 16):
            self.desktop_canvas.create_line(i, 0, i, 964, fill=self.colors["desktop_pattern"])
        for i in range(0, 964, 16):
            self.desktop_canvas.create_line(0, i, 1280, i, fill=self.colors["desktop_pattern"])

        # Subtle "sgi" watermark
        self.desktop_canvas.create_text(
            640, 400, text="sgi", font=("Helvetica", 72, "bold italic"), fill="#2A4F6F"
        )

    def _bind_hover(self, widget: tk.Widget, normal_bg: str, hover_bg: str) -> None:
        widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal_bg))

    def create_toolchest(self) -> None:
        self.toolchest_frame = Frame(self.root, bg=self.colors["toolchest"], height=30)
        self.toolchest_frame.place(x=0, y=0, width=1280, height=30)

        logo_btn = Button(
            self.toolchest_frame,
            text="◆",
            bg=self.colors["toolchest"],
            fg=self.colors["highlight"],
            bd=0,
            font=("Arial", 14, "bold"),
            command=self.show_sgi_menu,
            activebackground=self.colors["toolchest_hover"],
        )
        logo_btn.pack(side=tk.LEFT, padx=5)
        self._bind_hover(logo_btn, self.colors["toolchest"], self.colors["toolchest_hover"])

        self.toolchest_btn = Button(
            self.toolchest_frame,
            text="Toolchest",
            bg=self.colors["toolchest"],
            fg=self.colors["text_light"],
            bd=0,
            font=("Helvetica", 11, "bold"),
            command=self.show_toolchest_menu,
            activebackground=self.colors["toolchest_hover"],
        )
        self.toolchest_btn.pack(side=tk.LEFT, padx=10)
        self._bind_hover(self.toolchest_btn, self.colors["toolchest"], self.colors["toolchest_hover"])

    def show_sgi_menu(self) -> None:
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="About This System", command=self.show_about_sgi)
        menu.add_command(label="System Manager", command=self.open_system_manager)
        menu.add_separator()
        menu.add_command(label="Exit Desktop", command=self.logout)
        # Post near top-left, below the toolchest
        menu.post(5, 30)

    def show_toolchest_menu(self) -> None:
        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="Shell", command=self.open_winterm)
        menu.add_command(label="File Manager", command=self.open_file_manager)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.logout)
        menu.post(self.toolchest_btn.winfo_rootx(), self.toolchest_btn.winfo_rooty() + self.toolchest_btn.winfo_height())

    # ---------------- Icons ----------------
    def create_desktop_icons(self) -> None:
        self.create_desktop_icon("Console", "▓", 60, 100, self.open_winterm)
        self.create_desktop_icon("System", "⚙", 60, 200, self.open_system_manager)

    def create_desktop_icon(self, name: str, icon: str, x: int, y: int, command) -> None:
        f = Frame(self.desktop_canvas, bg=self.colors["desktop"])
        f.place(x=x, y=y)
        Button(f, text=icon, font=("Arial", 24), bg=self.colors["desktop"], fg="white", bd=0, command=command).pack()
        Label(f, text=name, bg=self.colors["desktop"], fg="white", font=("Helvetica", 9)).pack()

    # ---------------- Status ----------------
    def create_status_bar(self) -> None:
        self.status_frame = Frame(self.root, bg=self.colors["toolchest"], height=30)
        self.status_frame.place(x=0, y=994, width=1280, height=30)
        self.clock_label = Label(self.status_frame, bg=self.colors["toolchest"], fg="white", font=("Helvetica", 10, "bold"))
        self.clock_label.pack(side=tk.RIGHT, padx=10)

    def update_clock(self) -> None:
        self.clock_label.config(text=datetime.now().strftime("%a %b %d %I:%M %p"))
        self.root.after(1000, self.update_clock)

    # ---------------- Windows ----------------
    def create_window(self, title: str, w: int, h: int, x: int, y: int) -> Toplevel:
        win = Toplevel(self.root)
        win.title(title)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.configure(bg=self.colors["window_bg"])
        win.transient(self.root)
        return win

    # ---------------- Apps ----------------
    def open_winterm(self) -> None:
        """Open a simple pseudo-shell (IRIS Console)."""
        win = self.create_window("IRIS Console", 760, 460, 200, 150)
        text = Text(
            win,
            bg=self.colors["console_bg"],
            fg=self.colors["console_fg"],
            insertbackground="white",
            font=("Courier", 10),
            undo=True,
            wrap="word",
        )
        text.pack(fill=tk.BOTH, expand=True)
        text.focus_set()

        prompt = f"{self.username}@{self.hostname} % "

        def insert_prompt() -> None:
            if not text.winfo_exists():
                return
            text.insert(tk.END, prompt)
            text.see(tk.END)

        insert_prompt()

        def current_command() -> str:
            line = text.get("insert linestart", "insert lineend")
            parts = line.split("%", 1)
            return (parts[-1] if parts else line).strip()

        def run_cmd(event=None):
            cmd = current_command()
            if cmd:
                self.command_history.append(cmd)
            self.history_index = len(self.command_history)

            if cmd == "clear":
                text.delete("1.0", tk.END)
                insert_prompt()
                return "break"
            elif cmd == "ls":
                text.insert(tk.END, "\nDesktop  Documents  bin  demos  lib\n")
            elif cmd == "exit":
                # Prevent post-destroy widget access
                win.destroy()
                return "break"
            elif cmd in ("help", "?"):
                text.insert(
                    tk.END,
                    "\nBuilt-ins: ls, clear, help, exit, echo <text>, date\n",
                )
            elif cmd.startswith("echo "):
                text.insert(tk.END, "\n" + cmd[5:] + "\n")
            elif cmd == "date":
                text.insert(tk.END, "\n" + datetime.now().strftime("%c") + "\n")
            elif cmd == "":
                # Empty line — just show another prompt
                pass
            else:
                text.insert(tk.END, f"\n{cmd}: command not found\n")

            insert_prompt()
            return "break"

        def _replace_with_history() -> None:
            if not self.command_history:
                return
            cmd = "" if self.history_index == len(self.command_history) else self.command_history[self.history_index]
            line = text.get("insert linestart", "insert lineend")
            before = (line.split("%", 1)[0] + "% ") if "%" in line else ""
            text.delete("insert linestart", "insert lineend")
            text.insert("insert linestart", before + cmd)
            text.mark_set("insert", "insert lineend")

        def history_prev(event=None):
            if not self.command_history:
                return "break"
            self.history_index = max(0, self.history_index - 1)
            _replace_with_history()
            return "break"

        def history_next(event=None):
            if not self.command_history:
                return "break"
            self.history_index = min(len(self.command_history), self.history_index + 1)
            _replace_with_history()
            return "break"

        text.bind("<Return>", run_cmd)
        text.bind("<Up>", history_prev)
        text.bind("<Down>", history_next)

    def open_file_manager(self) -> None:
        win = self.create_window("File Manager", 600, 400, 250, 180)
        lb = Listbox(win, font=("Courier", 9))
        lb.pack(fill=tk.BOTH, expand=True)
        for f in ["Desktop", "Documents", "bin", "demos", "lib"]:
            lb.insert(tk.END, f)

    def open_system_manager(self) -> None:
        win = self.create_window("System Manager", 500, 400, 300, 200)
        Label(
            win,
            text="SGI Indy R5000\nIRIX 5.3\nMemory: 64 MB",
            font=("Helvetica", 12),
            bg=self.colors["window_bg"],
        ).pack(pady=20)

    def show_about_sgi(self) -> None:
        messagebox.showinfo("About", "Silicon Graphics Indy\nIRIX 5.3\nFlames Co. v0.9.1 [BETA]")

    # ---------------- Exit ----------------
    def logout(self) -> None:
        if messagebox.askyesno("Exit", "Exit Indigo Magic Desktop?"):
            self.root.destroy()

    def on_close(self) -> None:
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    SgiIndyDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
