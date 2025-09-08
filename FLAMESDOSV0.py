#!/usr/bin/env python3
# FT-DOS 0.1 — A retro, DOS-like shell in Tkinter (FILES=OFF)
# (C) [Flames Co 199X-20?? ]
#
# FIXED: Enhanced prompt handling with proper token parsing
#
# Design goals:
#  - Single-file Tkinter app, no external assets
#  - DOS-style shell with prompt, history, basic commands
#  - Read-only in-memory VFS (FILES=OFF)
#  - No disk writes, no file creation/deletion
#  - Simple color theming via "COLOR XY" like DOS
#
# Commands implemented:
#   HELP, VER, ABOUT, LICENSE
#   DIR [path], CD [path], TYPE <file>
#   CLS, ECHO <text>, DATE, TIME, PROMPT [template], HISTORY
#   COLOR [XY] | COLOR /?
#   SYSINFO, MEM, EXIT
#   (Disabled stubs due to FILES=OFF): COPY, DEL, REN, MOVE, MKDIR, RMDIR
#
# Notes:
#   - Paths are case-insensitive and use "\" or "/" separators.
#   - Paths with spaces are not supported (keep names 8.3-style).
#   - PROMPT tokens: $P (path), $G (>), $D (date), $T (time), $N (drive "A"), $$ ($)
#   - This is a playful simulation, not a full shell.

import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime
import platform
import sys
import re

APP_NAME = "FT-DOS"
APP_VER = "0.1"
COPYRIGHT = "[Flames Co 199X-20?? ]"
FILES_ENABLED = False  # hard-locked OFF per request

DEFAULT_PROMPT = "$P$G"  # e.g., "A:\>"

# DOS color palette mapping (0..F) to Tk hex colors
DOS_COLOR_MAP = {
    "0": "#000000", "1": "#0000AA", "2": "#00AA00", "3": "#00AAAA",
    "4": "#AA0000", "5": "#AA00AA", "6": "#AA5500", "7": "#AAAAAA",
    "8": "#555555", "9": "#5555FF", "A": "#55FF55", "B": "#55FFFF",
    "C": "#FF5555", "D": "#FF55FF", "E": "#FFFF55", "F": "#FFFFFF",
}

# Read-only Virtual File System (VFS) — no writes allowed.
# Directory -> dict; File -> str (text)
VFS = {
    "": {  # root
        "DOCS": {
            "README.TXT": (
                "FT-DOS 0.1 (FILES=OFF)\r\n"
                f"(C) {COPYRIGHT}\r\n\r\n"
                "Welcome to FT-DOS 0.1 — a minimal, retro DOS-like shell.\r\n"
                "This system is read-only: file creation/modification commands are disabled.\r\n"
                "\r\n"
                "Try: HELP, DIR, TYPE README.TXT, VER, COLOR /?\r\n"
            ),
            "CHANGELOG.TXT": (
                "FT-DOS 0.1 CHANGELOG\r\n"
                " - Initial release based on first OS concept\r\n"
                " - Tkinter UI, command history, prompt tokens\r\n"
                " - Color theming via COLOR XY\r\n"
                " - Read-only VFS (FILES=OFF)\r\n"
                " - Fixed prompt token parsing\r\n"
            ),
        },
        "BIN": {
            "HELPTIPS.TXT": (
                "TIPS\r\n"
                " - Use UP/DOWN to navigate command history\r\n"
                " - PROMPT $P$G sets classic A:\\> prompt\r\n"
                " - COLOR 0A gives black background with bright green text\r\n"
                " - Use $$ in prompt to display a literal $\r\n"
            )
        },
        "SYSTEM": {
            "LICENSE.TXT": f"{APP_NAME} {APP_VER} License\r\n(C) {COPYRIGHT}\r\nAll rights reserved.\r\nFor demo purposes only.\r\n",
        },
        "WELCOME.TXT": "Meow! FT-DOS boot complete.\r\nType HELP to see commands.\r\n",
    }
}

def now_date():
    return datetime.now().strftime("%Y-%m-%d")

def now_time():
    return datetime.now().strftime("%H:%M:%S")

class FTDOSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VER} — {COPYRIGHT}")
        self.geometry("980x620")
        self.minsize(740, 420)
        self.configure(bg="#000000")

        # Theme (default black bg, bright green fg)
        self.bg_color = DOS_COLOR_MAP["0"]
        self.fg_color = DOS_COLOR_MAP["A"]  # A = bright green
        self._apply_theme()

        # Fonts
        self.font = tkfont.Font(family=self._pick_mono_font(), size=12)

        # Widgets
        self._build_ui()

        # Shell state
        self.cwd = []  # current working directory as list of components from root
        self.prompt_template = DEFAULT_PROMPT
        self.history = []
        self.history_index = None  # None when not navigating history

        # Banner + initial prompt
        self._print_banner()
        self._show_prompt()

    def _pick_mono_font(self):
        candidates = ["Consolas", "Menlo", "DejaVu Sans Mono", "Courier New", "Liberation Mono", "Courier"]
        families = set(tkfont.families())
        for name in candidates:
            if name in families:
                return name
        return "Courier"

    def _apply_theme(self):
        self.configure(bg=self.bg_color)

    def _build_ui(self):
        # Scrollable Text console
        self.text = tk.Text(
            self,
            wrap="none", undo=False, autoseparators=False, maxundo=0,
            bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color,
            borderwidth=0, highlightthickness=0, padx=8, pady=8
        )
        self.text.configure(font=self.font)
        self.text.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(self, orient="vertical", command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)

        # Tags for styling
        self.text.tag_configure("banner", foreground=DOS_COLOR_MAP["B"])
        self.text.tag_configure("info", foreground=DOS_COLOR_MAP["7"])
        self.text.tag_configure("error", foreground=DOS_COLOR_MAP["C"])
        self.text.tag_configure("prompt", foreground=self.fg_color)
        self.text.tag_configure("output", foreground=self.fg_color)

        # Input control
        self.input_start = self.text.index("end-1c")

        # Bindings
        self.text.bind("<Return>", self._on_enter)
        self.text.bind("<BackSpace>", self._on_backspace)
        self.text.bind("<Key>", self._on_key)
        self.text.bind("<Button-1>", self._on_click)
        self.text.bind("<Up>", self._on_history_up)
        self.text.bind("<Down>", self._on_history_down)
        self.text.focus_set()

        # Prevent right-click paste from modifying previous content
        self.text.bind("<<Paste>>", lambda e: self._paste_guard(e))

        # Menu (optional minimal)
        self._build_menu()

        # Close handling
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = tk.Menu(self)
        sysmenu = tk.Menu(menubar, tearoff=False)
        sysmenu.add_command(label="About", command=lambda: self._cmd_about([]))
        sysmenu.add_separator()
        sysmenu.add_command(label="Exit", command=self._on_close, accelerator="ALT+F4")
        menubar.add_cascade(label="System", menu=sysmenu)
        self.config(menu=menubar)

    # ---------- Console helpers ----------

    def _write(self, s="", tag="output", end="\n"):
        if s is None:
            s = ""
        self.text.insert("end", (s + end), tag)
        self.text.see("end")

    def _print_banner(self):
        border = "─" * 56
        self._write(f"{APP_NAME} {APP_VER}  (FILES=OFF)", tag="banner")
        self._write(f"(C) {COPYRIGHT}", tag="banner")
        self._write(border, tag="banner")
        self._write("Booting kernel ... OK", tag="info")
        self._write(f"Host: {platform.system()} {platform.release()} | Python {platform.python_version()}", tag="info")
        self._write(f"Date: {now_date()}  Time: {now_time()}", tag="info")
        self._write("")  # blank line
        self._safe_cat_path("WELCOME.TXT")  # show welcome if present

    def _show_prompt(self):
        prompt = self._render_prompt()
        self.text.insert("end", prompt, ("prompt",))
        self.text.see("end")
        self.input_start = self.text.index("end-1c")

    def _render_prompt(self):
        """
        Enhanced prompt rendering with proper token parsing.
        Tokens: $P (path), $G (>), $D (date), $T (time), $N (drive letter), $$ (literal $)
        """
        path = self._fmt_path()
        prompt = self.prompt_template
        
        # Define token replacements
        tokens = {
            '$P': path,
            '$G': '>',
            '$D': now_date(),
            '$T': now_time(),
            '$N': 'A',
            '$$': '$'
        }
        
        # Process tokens using regex to handle them properly
        # This ensures $$ is processed correctly and tokens don't interfere with each other
        def replace_token(match):
            token = match.group(0)
            return tokens.get(token, token)
        
        # Match any of our tokens
        pattern = r'\$[$PGDTN]'
        result = re.sub(pattern, replace_token, prompt)
        
        # Ensure prompt ends with a space for better UX
        if not result.endswith(" "):
            result += " "
        
        return result

    def _fmt_path(self, parts=None):
        if parts is None:
            parts = self.cwd
        return "A:\\" + ("\\".join(parts) if parts else "")

    def _on_close(self):
        self.destroy()

    # ---------- Input editing guards ----------

    def _enforce_edit_boundary(self):
        # Prevent editing before input_start
        try:
            if self.text.compare("insert", "<", self.input_start):
                self.text.mark_set("insert", "end-1c")
                self.text.see("end")
        except tk.TclError:
            pass

    def _on_click(self, event):
        self.text.after_idle(self._enforce_edit_boundary)

    def _on_key(self, event):
        # Disallow edits before the prompt
        # Allow Ctrl+C/V etc. for copy/paste but keep guard
        if event.keysym in ("Left", "BackSpace", "Delete", "Home"):
            if self.text.compare("insert", "<=", self.input_start):
                return "break"
        return None

    def _on_backspace(self, event):
        # Prevent deleting prompt
        if self.text.compare("insert", "<=", self.input_start):
            return "break"
        return None

    def _paste_guard(self, event):
        # Block paste before prompt
        try:
            if self.text.compare("insert", "<", self.input_start):
                self.text.mark_set("insert", "end-1c")
        except tk.TclError:
            pass
        return None

    def _on_enter(self, event):
        # Capture the command line
        line = self.text.get(self.input_start, "end-1c").strip()
        # Echo newline to end the input line
        self.text.insert("end", "\n")
        self.text.see("end")

        if line:
            self.history.append(line)
        self.history_index = None

        self._dispatch_command(line)
        self._show_prompt()
        return "break"

    def _on_history_up(self, event):
        if not self.history:
            return "break"
        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        self._replace_current_input(self.history[self.history_index])
        return "break"

    def _on_history_down(self, event):
        if not self.history:
            return "break"
        if self.history_index is None:
            return "break"
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._replace_current_input(self.history[self.history_index])
        else:
            # At the end of history, clear input
            self.history_index = None
            self._replace_current_input("")
        return "break"

    def _replace_current_input(self, s):
        self.text.delete(self.input_start, "end-1c")
        self.text.insert("end", s)
        self.text.see("end")

    # ---------- Command dispatch ----------

    def _dispatch_command(self, line: str):
        if not line:
            return
        # Parse command word and rest (no quotes-with-spaces support to keep it simple)
        parts = line.strip().split()
        cmd = parts[0].upper()
        args = parts[1:]

        # Built-ins
        table = {
            "HELP": self._cmd_help,
            "VER": self._cmd_ver,
            "ABOUT": self._cmd_about,
            "LICENSE": self._cmd_license,
            "CLS": self._cmd_cls,
            "ECHO": self._cmd_echo,
            "DATE": self._cmd_date,
            "TIME": self._cmd_time,
            "PROMPT": self._cmd_prompt,
            "COLOR": self._cmd_color,
            "DIR": self._cmd_dir,
            "CD": self._cmd_cd,
            "TYPE": self._cmd_type,
            "HISTORY": self._cmd_history,
            "SYSINFO": self._cmd_sysinfo,
            "MEM": self._cmd_mem,
            "EXIT": self._cmd_exit,
            # Disabled due to FILES=OFF
            "COPY": self._cmd_disabled,
            "DEL": self._cmd_disabled,
            "ERASE": self._cmd_disabled,
            "REN": self._cmd_disabled,
            "RENAME": self._cmd_disabled,
            "MOVE": self._cmd_disabled,
            "MKDIR": self._cmd_disabled,
            "MD": self._cmd_disabled,
            "RMDIR": self._cmd_disabled,
            "RD": self._cmd_disabled,
            "EDIT": self._cmd_disabled,
        }

        func = table.get(cmd)
        if func:
            func(args)
        else:
            self._write(f"'{cmd}' is not recognized as an internal or external command.", tag="error")

    # ---------- Commands ----------

    def _cmd_help(self, args):
        self._write("FT-DOS 0.1 Help")
        self._write("----------------")
        self._write("HELP                 Show this help")
        self._write("VER                  Show version")
        self._write("ABOUT                Product information")
        self._write("LICENSE              Display license")
        self._write("CLS                  Clear screen")
        self._write("ECHO <text>          Print text")
        self._write("DATE                 Show today's date")
        self._write("TIME                 Show current time")
        self._write("PROMPT [template]    Set prompt tokens: $P $G $D $T $N $$")
        self._write("COLOR [XY | /?]      Set colors (X=bg, Y=fg), e.g., COLOR 0A")
        self._write("DIR [path]           List directory")
        self._write("CD [path]            Change directory")
        self._write("TYPE <file>          Display text file")
        self._write("HISTORY              Show command history")
        self._write("SYSINFO              Show system information")
        self._write("MEM                  Show memory summary")
        self._write("EXIT                 Quit FT-DOS")
        self._write("")
        self._write("FILES=OFF disables: COPY, DEL, REN, MOVE, MKDIR, RMDIR, EDIT", tag="info")

    def _cmd_ver(self, args):
        self._write(f"{APP_NAME} version {APP_VER}")
        self._write(f"(C) {COPYRIGHT}")
        self._write(f"FTLayer File Ops: {'ON' if FILES_ENABLED else 'OFF'}")

    def _cmd_about(self, args):
        self._write(f"{APP_NAME} {APP_VER} — Based on the first OS concept")
        self._write(f"(C) {COPYRIGHT}")
        self._write("No Wrappers, Just Files — simulated, read-only edition.")
        self._write("Tkinter-based shell with prompt, history, and DOS flavor.")

    def _cmd_license(self, args):
        self._safe_cat_path(r"SYSTEM\LICENSE.TXT")

    def _cmd_cls(self, args):
        self.text.delete("1.0", "end")
        # Re-apply tags since Text is cleared
        self.text.tag_configure("banner", foreground=DOS_COLOR_MAP["B"])
        self.text.tag_configure("info", foreground=DOS_COLOR_MAP["7"])
        self.text.tag_configure("error", foreground=DOS_COLOR_MAP["C"])
        self.text.tag_configure("prompt", foreground=self.fg_color)
        self.text.tag_configure("output", foreground=self.fg_color)

    def _cmd_echo(self, args):
        if not args:
            self._write("")
            return
        # Support "ECHO OFF/ON" as a no-op display (no internal echo state kept)
        if len(args) == 1 and args[0].upper() in ("ON", "OFF"):
            self._write(f"ECHO is {args[0].upper()}")
        else:
            self._write(" ".join(args))

    def _cmd_date(self, args):
        self._write(f"The current date is: {now_date()}")

    def _cmd_time(self, args):
        self._write(f"The current time is: {now_time()}")

    def _cmd_prompt(self, args):
        if not args:
            self._write(f"PROMPT={self.prompt_template}")
            return
        
        # Handle special cases like "PROMPT $P$G" or just "PROMPT"
        new_prompt = " ".join(args)
        
        # Validate prompt tokens (optional - warn about unknown tokens)
        valid_tokens = ['$P', '$G', '$D', '$T', '$N', '$$']
        # Find all tokens in the new prompt
        found_tokens = re.findall(r'\$[$PGDTN]', new_prompt)
        
        # Check for invalid tokens ($ followed by invalid character)
        invalid = re.findall(r'\$[^$PGDTN\s]', new_prompt)
        if invalid:
            self._write(f"Warning: Unknown token(s): {', '.join(invalid)}", tag="info")
        
        self.prompt_template = new_prompt
        self._write(f"PROMPT set to: {self.prompt_template}")

    def _cmd_color(self, args):
        if not args:
            # Reset to default colors
            self._apply_color_pair("0A")
            self._write("Color reset to default (0A).")
            return
        code = args[0].upper()
        if code in ("/?", "-?", "--HELP"):
            self._write("Set console colors: COLOR XY")
            self._write("X = background, Y = foreground (hex 0..F)")
            self._write("Examples: COLOR 0A  (black bg, bright green fg)")
            self._write("          COLOR 1F  (blue bg, bright white fg)")
            self._write("")
            self._write("Colors: 0=Black 1=Blue 2=Green 3=Cyan")
            self._write("        4=Red 5=Magenta 6=Brown 7=Gray")
            self._write("        8=DarkGray 9=LightBlue A=LightGreen B=LightCyan")
            self._write("        C=LightRed D=LightMagenta E=Yellow F=White")
            return
        if len(code) != 2 or code[0] not in DOS_COLOR_MAP or code[1] not in DOS_COLOR_MAP:
            self._write("Invalid color code. Use COLOR XY where X,Y are hex 0..F.", tag="error")
            return
        self._apply_color_pair(code)
        self._write(f"Color set to {code}.")

    def _apply_color_pair(self, code2):
        bg = DOS_COLOR_MAP[code2[0]]
        fg = DOS_COLOR_MAP[code2[1]]
        self.bg_color, self.fg_color = bg, fg

        # Apply to window and text
        self.configure(bg=bg)
        self.text.configure(bg=bg, fg=fg, insertbackground=fg)
        # Refresh tag colors for prompt/output to match fg
        self.text.tag_configure("prompt", foreground=fg)
        self.text.tag_configure("output", foreground=fg)

    def _cmd_dir(self, args):
        target = args[0] if args else "."
        node, is_dir, path_elems, err = self._resolve_path(target)
        if err:
            self._write(err, tag="error")
            return
        if not is_dir:
            self._write("Not a directory.", tag="error")
            return
        # List directory contents
        names = sorted(node.keys())
        self._write(f" Directory of {self._fmt_path(path_elems)}")
        self._write("")
        dirs = []
        files = []
        for name in names:
            if isinstance(node[name], dict):
                dirs.append(name)
            else:
                files.append(name)
        for d in dirs:
            self._write(f" {d:<12} <DIR>")
        for f in files:
            size = len(node[f]) if isinstance(node[f], str) else 0
            self._write(f" {f:<12} {size:>7} bytes")
        self._write("")
        self._write(f" {len(files)} File(s)")
        self._write(f" {len(dirs)} Dir(s)")

    def _cmd_cd(self, args):
        if not args:
            self._write(self._fmt_path())
            return
        target = args[0]
        
        # Handle special case: "CD\" or "CD/" to go to root
        if target in ("\\", "/"):
            self.cwd = []
            self._write(self._fmt_path())
            return
            
        node, is_dir, path_elems, err = self._resolve_path(target)
        if err:
            self._write(err, tag="error")
            return
        if not is_dir:
            self._write("The system cannot find the path specified.", tag="error")
            return
        self.cwd = path_elems
        self._write(self._fmt_path())

    def _cmd_type(self, args):
        if not args:
            self._write("The syntax of the command is incorrect.", tag="error")
            self._write("Usage: TYPE <FILENAME>")
            return
        target = args[0]
        node, is_dir, path_elems, err = self._resolve_path(target)
        if err:
            self._write(err, tag="error")
            return
        if is_dir:
            self._write("Access denied: target is a directory.", tag="error")
            return
        # Text files only (simulated)
        contents = node
        if isinstance(contents, str):
            for line in contents.splitlines():
                self._write(line)
        else:
            self._write("Cannot display binary file.", tag="error")

    def _cmd_history(self, args):
        if not self.history:
            self._write("(no commands)")
            return
        # Show last 100 commands with proper numbering
        start_idx = max(1, len(self.history) - 99)
        for idx, cmd in enumerate(self.history[-100:], start=start_idx):
            self._write(f"{idx:>4}: {cmd}")

    def _cmd_sysinfo(self, args):
        self._write(f"{APP_NAME} {APP_VER} System Info")
        self._write(f"OS: {platform.system()} {platform.release()}  ({platform.version()})")
        self._write(f"Python: {platform.python_version()}  ({platform.python_implementation()})")
        self._write(f"Machine: {platform.machine()}  Node: {platform.node()}")
        self._write(f"FILES: {'ON' if FILES_ENABLED else 'OFF'} (read-only VFS)")

    def _cmd_mem(self, args):
        # Simulated memory stats (not true system RAM)
        self._write("655,360 bytes total conventional memory")
        self._write("655,360 bytes available to FT-DOS (simulated)")
        self._write("No EMS/XMS drivers loaded (simulated)")

    def _cmd_exit(self, args):
        self._write("Exiting FT-DOS ...")
        self.after(100, self._on_close)

    def _cmd_disabled(self, args):
        self._write("Operation disabled (FILES=OFF).", tag="error")

    # ---------- Path + VFS helpers ----------

    def _resolve_path(self, raw: str):
        """
        Resolve a VFS path to a node.
        Returns: (node, is_dir, path_elems, err_message_or_None)
        """
        # Determine start point
        s = raw.strip()
        absolute = s.startswith("\\") or s.startswith("/")
        parts = [p for p in s.replace("/", "\\").split("\\") if p and p != "."]
        if absolute:
            elems = []
        else:
            elems = list(self.cwd)

        node = VFS[""]
        # Walk
        for p in parts:
            if p == "..":
                if elems:
                    elems.pop()
                    node = self._get_node_by_elems(elems)
                else:
                    node = VFS[""]
                continue
            match = self._case_insensitive_find(node, p)
            if match is None:
                return None, False, elems, "The system cannot find the path specified."
            sub = node[match]
            if isinstance(sub, dict):
                # Directory
                elems.append(match)
                node = sub
            else:
                # File
                # Only acceptable if it's the last segment
                if p != parts[-1]:
                    return None, False, elems, "The system cannot find the path specified."
                return sub, False, elems, None
        return node, True, elems, None

    def _get_node_by_elems(self, elems):
        node = VFS[""]
        for e in elems:
            node = node[e]
        return node

    def _case_insensitive_find(self, node_dict, name):
        up = name.upper()
        for k in node_dict.keys():
            if k.upper() == up:
                return k
        return None

    def _safe_cat_path(self, path_str):
        node, is_dir, _, err = self._resolve_path(path_str)
        if err:
            return
        if is_dir:
            return
        if isinstance(node, str):
            for line in node.splitlines():
                self._write(line)

# ---------- main ----------

if __name__ == "__main__":
    app = FTDOSApp()
    app.mainloop()
