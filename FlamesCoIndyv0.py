#!/usr/bin/env python3
"""
Flames Co. Indy 1.0a - Professional Workstation Operating System
Copyright (c) 1994 Flames Computing Corporation
"""

import tkinter as tk
from tkinter import ttk, Menu, Text, Scrollbar, Canvas, Toplevel, Frame, Label, Button, Entry, Listbox, messagebox
import os
import time
from datetime import datetime
import random
import threading

class IndyDesktop:
    """Main Desktop Environment for Flames Co. Indy"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Flames Co. Indy 1.0a - Professional Workstation")
        self.root.geometry("1024x768")
        
        # Classic Indy color scheme
        self.colors = {
            'desktop': '#5D6B7A',
            'desktop_pattern': '#4A5968',
            'primary': '#007575',  # Teal
            'primary_dark': '#005858',
            'window_bg': '#B8B8B8',
            'window_content': '#D0D0D0',
            'highlight': '#00FFFF',
            'text': '#000000',
            'text_light': '#FFFFFF'
        }
        
        self.root.configure(bg=self.colors['desktop'])
        
        # Window management
        self.windows = []
        self.window_z_index = 100
        self.dragged_window = None
        self.drag_offset = {'x': 0, 'y': 0}
        
        # System state
        self.username = "flames"
        self.hostname = "indy"
        self.system_processes = []
        self.wizard_complete = False
        
        # Virtual filesystem
        self.init_filesystem()
        
        # Create desktop
        self.create_desktop_pattern()
        self.create_toolchest()
        self.create_desktop_icons()
        self.create_clock()
        
        # Start with setup wizard
        self.root.after(500, self.show_wizard)
        
        # Update clock
        self.update_clock()

    def init_filesystem(self):
        """Initialize virtual filesystem"""
        self.fs = {
            '/': {
                'type': 'dir',
                'contents': {
                    'usr': {
                        'type': 'dir',
                        'contents': {
                            'demos': {
                                'type': 'dir',
                                'contents': {
                                    'butterfly.demo': {'type': 'file', 'size': 2048},
                                    'flames.demo': {'type': 'file', 'size': 4096},
                                    'wave3d.demo': {'type': 'file', 'size': 3072}
                                }
                            },
                            'people': {
                                'type': 'dir',
                                'contents': {
                                    'flames': {
                                        'type': 'dir',
                                        'contents': {
                                            'Desktop': {'type': 'dir', 'contents': {}},
                                            'Documents': {'type': 'dir', 'contents': {}},
                                            'Projects': {'type': 'dir', 'contents': {}}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    'etc': {
                        'type': 'dir',
                        'contents': {
                            'motd': {'type': 'file', 'content': 'Welcome to Flames Co. Indy 1.0a'},
                            'sys_id': {'type': 'file', 'content': 'FC-INDY-1994'}
                        }
                    }
                }
            }
        }

    def create_desktop_pattern(self):
        """Create the classic crosshatch desktop pattern"""
        self.desktop_canvas = Canvas(self.root, bg=self.colors['desktop'], highlightthickness=0)
        self.desktop_canvas.place(x=0, y=24, width=1024, height=744)
        
        # Crosshatch pattern
        for i in range(0, 1024, 8):
            self.desktop_canvas.create_line(i, 0, i, 768, fill=self.colors['desktop_pattern'], width=1)
        for i in range(0, 768, 8):
            self.desktop_canvas.create_line(0, i, 1024, i, fill=self.colors['desktop_pattern'], width=1)
        
        # Desktop branding
        self.desktop_canvas.create_text(512, 300, text="Flames Co. Indy",
                                       font=('Helvetica', 48, 'bold'),
                                       fill='#333333')
        self.desktop_canvas.create_text(512, 340, text="1.0a Professional",
                                       font=('Helvetica', 24),
                                       fill='#333333')
        self.desktop_canvas.create_text(512, 370, text="🔥 Igniting Innovation",
                                       font=('Helvetica', 14),
                                       fill='#444444')

    def create_toolchest(self):
        """Create the Toolchest menu button"""
        self.toolchest_frame = Frame(self.root, bg=self.colors['primary'], height=24)
        self.toolchest_frame.place(x=0, y=0, width=1024, height=24)
        
        self.toolchest_btn = Button(
            self.toolchest_frame,
            text="Toolchest",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 10, 'bold'),
            bd=2,
            relief=tk.RAISED,
            activebackground=self.colors['primary_dark'],
            command=self.show_toolchest_menu
        )
        self.toolchest_btn.pack(side=tk.LEFT, padx=2, pady=1)
        
        # Quick launch buttons
        Button(
            self.toolchest_frame,
            text="Console",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 9),
            bd=1,
            command=self.open_console
        ).pack(side=tk.LEFT, padx=2)
        
        Button(
            self.toolchest_frame,
            text="Files",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 9),
            bd=1,
            command=self.open_file_manager
        ).pack(side=tk.LEFT, padx=2)

    def show_toolchest_menu(self):
        """Display the Toolchest dropdown menu"""
        menu = Menu(self.root, tearoff=0)
        
        # Desktop submenu
        desktop_menu = Menu(menu, tearoff=0)
        desktop_menu.add_command(label="Customize", command=lambda: self.show_message("Desktop Customization"))
        desktop_menu.add_command(label="Screen Saver", command=lambda: self.show_message("Screen Saver Settings"))
        menu.add_cascade(label="Desktop", menu=desktop_menu)
        
        # System submenu
        system_menu = Menu(menu, tearoff=0)
        system_menu.add_command(label="System Info", command=self.open_system_info)
        system_menu.add_command(label="Process Manager", command=self.open_process_manager)
        system_menu.add_command(label="Hardware Inventory", command=self.show_hinv)
        menu.add_cascade(label="System", menu=system_menu)
        
        menu.add_separator()
        
        # Applications
        menu.add_command(label="Console", command=self.open_console)
        menu.add_command(label="File Manager", command=self.open_file_manager)
        menu.add_command(label="Text Editor", command=self.open_text_editor)
        
        menu.add_separator()
        
        # Demos
        demos_menu = Menu(menu, tearoff=0)
        demos_menu.add_command(label="🔥 Flames Demo", command=lambda: self.run_demo("flames"))
        demos_menu.add_command(label="🦋 Butterfly", command=lambda: self.run_demo("butterfly"))
        demos_menu.add_command(label="🌊 Wave3D", command=lambda: self.run_demo("wave3d"))
        menu.add_cascade(label="Demos", menu=demos_menu)
        
        menu.add_separator()
        menu.add_command(label="About Indy", command=self.show_about)
        menu.add_command(label="Setup Wizard", command=self.show_wizard)
        menu.add_command(label="Logout", command=self.logout)
        
        # Position menu below button
        x = self.toolchest_btn.winfo_rootx()
        y = self.toolchest_btn.winfo_rooty() + self.toolchest_btn.winfo_height()
        menu.post(x, y)

    def create_desktop_icons(self):
        """Create desktop icon shortcuts"""
        icons = [
            ("Console", "📟", 50, 60, self.open_console),
            ("File Manager", "📁", 50, 160, self.open_file_manager),
            ("System", "⚙️", 50, 260, self.open_system_info),
            ("Demos", "🔥", 50, 360, lambda: self.run_demo("flames"))
        ]
        
        for name, icon, x, y, command in icons:
            frame = Frame(self.desktop_canvas, bg=self.colors['desktop'], width=80, height=90)
            frame.place(x=x, y=y)
            
            icon_btn = Button(
                frame,
                text=icon,
                font=('Arial', 32),
                bg=self.colors['primary'],
                fg=self.colors['text_light'],
                width=3,
                height=1,
                bd=2,
                relief=tk.RAISED,
                command=command
            )
            icon_btn.pack()
            
            Label(
                frame,
                text=name,
                bg=self.colors['desktop'],
                fg=self.colors['text_light'],
                font=('Helvetica', 9)
            ).pack()

    def create_clock(self):
        """Create system clock display"""
        self.clock_label = Label(
            self.toolchest_frame,
            text="",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Courier', 10, 'bold')
        )
        self.clock_label.pack(side=tk.RIGHT, padx=10)

    def update_clock(self):
        """Update clock display"""
        now = datetime.now()
        time_str = now.strftime("%a %b %d %H:%M:%S")
        self.clock_label.config(text=time_str)
        self.root.after(1000, self.update_clock)

    def show_wizard(self):
        """Show the Out Box Setup Wizard"""
        self.wizard = Toplevel(self.root)
        self.wizard.title("Flames Co. Indy - Out Box Setup")
        self.wizard.geometry("600x500")
        self.wizard.configure(bg=self.colors['window_bg'])
        self.wizard.transient(self.root)
        
        # Make modal
        self.wizard.grab_set()
        
        # Header
        header = Frame(self.wizard, bg=self.colors['primary'], height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Logo
        logo_frame = Frame(header, bg=self.colors['highlight'], width=60, height=60)
        logo_frame.place(x=20, y=10)
        Label(logo_frame, text="🔥", font=('Arial', 28), bg=self.colors['highlight']).place(x=8, y=8)
        
        Label(
            header,
            text="Welcome to Flames Co. Indy",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 18, 'bold')
        ).place(x=100, y=15)
        
        Label(
            header,
            text="Professional Workstation Setup",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 12)
        ).place(x=100, y=45)
        
        # Content area
        self.wizard_content = Frame(self.wizard, bg=self.colors['window_content'])
        self.wizard_content.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Footer
        footer = Frame(self.wizard, bg=self.colors['window_bg'], height=60)
        footer.pack(fill=tk.X)
        footer.pack_propagate(False)
        
        self.wizard_skip_btn = Button(
            footer,
            text="Skip",
            bg=self.colors['window_bg'],
            font=('Helvetica', 10),
            width=10,
            command=self.skip_wizard
        )
        self.wizard_skip_btn.place(x=20, y=15)
        
        self.wizard_back_btn = Button(
            footer,
            text="◀ Back",
            bg=self.colors['window_bg'],
            font=('Helvetica', 10),
            width=10,
            state=tk.DISABLED,
            command=self.wizard_previous
        )
        self.wizard_back_btn.place(x=400, y=15)
        
        self.wizard_next_btn = Button(
            footer,
            text="Next ▶",
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 10, 'bold'),
            width=10,
            command=self.wizard_next
        )
        self.wizard_next_btn.place(x=490, y=15)
        
        self.wizard_step = 1
        self.show_wizard_step1()

    def show_wizard_step1(self):
        """Wizard Step 1: Welcome"""
        for widget in self.wizard_content.winfo_children():
            widget.destroy()
        
        # Boot sequence display
        boot_frame = Frame(self.wizard_content, bg='black', height=100)
        boot_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        boot_frame.pack_propagate(False)
        
        boot_text = Text(
            boot_frame,
            bg='black',
            fg='#00FF00',
            font=('Courier', 8),
            height=6,
            bd=0
        )
        boot_text.pack(fill=tk.BOTH, expand=True)
        
        # Simulate boot sequence
        boot_messages = [
            "Starting Flames OS kernel...",
            "Flames Indy Release 1.0a Build 1994.11.22",
            "Copyright 1994 Flames Computing Corporation",
            "CPU: FIRE R5000 Processor @ 150MHz",
            "Memory Test: 128MB OK",
            "Graphics: FlameXZ 24-bit Accelerator",
            "Starting Indigo Magic Desktop..."
        ]
        
        for i, msg in enumerate(boot_messages):
            boot_text.insert(tk.END, msg + '\n')
            boot_text.see(tk.END)
            boot_text.update()
            time.sleep(0.1)
        
        # Welcome content
        Label(
            self.wizard_content,
            text="Out Box Personal Environment Setup",
            bg=self.colors['window_content'],
            font=('Helvetica', 16, 'bold'),
            fg=self.colors['primary']
        ).pack(pady=20)
        
        info_frame = Frame(self.wizard_content, bg=self.colors['text_light'], relief=tk.SUNKEN, bd=2)
        info_frame.pack(padx=40, pady=10, fill=tk.X)
        
        info_text = """System Configuration:
• Flames Indy R5000 @ 150MHz
• 128MB RAM  
• FlameXZ Graphics
• Indigo Magic Desktop 1.0a
• Professional 3D Acceleration"""
        
        Label(
            info_frame,
            text=info_text,
            bg=self.colors['text_light'],
            font=('Courier', 10),
            justify=tk.LEFT
        ).pack(padx=20, pady=20)
        
        Label(
            self.wizard_content,
            text="Click Next to begin personalizing your workstation.",
            bg=self.colors['window_content'],
            font=('Helvetica', 11)
        ).pack(pady=20)

    def show_wizard_step2(self):
        """Wizard Step 2: User Information"""
        for widget in self.wizard_content.winfo_children():
            widget.destroy()
        
        Label(
            self.wizard_content,
            text="Personal Information",
            bg=self.colors['window_content'],
            font=('Helvetica', 16, 'bold'),
            fg=self.colors['primary']
        ).pack(pady=20)
        
        form_frame = Frame(self.wizard_content, bg=self.colors['window_content'])
        form_frame.pack(padx=40, fill=tk.BOTH, expand=True)
        
        # Full Name
        Label(form_frame, text="Full Name:", bg=self.colors['window_content'],
              font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=10)
        self.name_entry = Entry(form_frame, font=('Helvetica', 10), width=30)
        self.name_entry.insert(0, "Flames User")
        self.name_entry.grid(row=0, column=1, pady=10)
        
        # Organization
        Label(form_frame, text="Organization:", bg=self.colors['window_content'],
              font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=10)
        self.org_entry = Entry(form_frame, font=('Helvetica', 10), width=30)
        self.org_entry.insert(0, "Flames Computing Corp.")
        self.org_entry.grid(row=1, column=1, pady=10)
        
        # Login Name
        Label(form_frame, text="Login Name:", bg=self.colors['window_content'],
              font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=10)
        login_entry = Entry(form_frame, font=('Courier', 10), width=30)
        login_entry.insert(0, "flames")
        login_entry.config(state='readonly')
        login_entry.grid(row=2, column=1, pady=10)
        
        # Note
        note_frame = Frame(self.wizard_content, bg='#FFFFCC', relief=tk.RIDGE, bd=2)
        note_frame.pack(padx=40, pady=20, fill=tk.X)
        Label(
            note_frame,
            text="Note: Your login name will be used to access this workstation.",
            bg='#FFFFCC',
            font=('Helvetica', 9)
        ).pack(padx=10, pady=10)
        
        self.wizard_back_btn.config(state=tk.NORMAL)

    def show_wizard_step3(self):
        """Wizard Step 3: System Configuration"""
        for widget in self.wizard_content.winfo_children():
            widget.destroy()
        
        Label(
            self.wizard_content,
            text="System Configuration",
            bg=self.colors['window_content'],
            font=('Helvetica', 16, 'bold'),
            fg=self.colors['primary']
        ).pack(pady=20)
        
        config_frame = Frame(self.wizard_content, bg=self.colors['window_content'])
        config_frame.pack(padx=40, fill=tk.BOTH, expand=True)
        
        # Graphics Mode
        Label(config_frame, text="Graphics Mode:", bg=self.colors['window_content'],
              font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        self.graphics_var = tk.StringVar(value="24-bit TrueColor")
        graphics_options = ["24-bit TrueColor (Recommended)", "8-bit PseudoColor", "16-bit HighColor"]
        for opt in graphics_options:
            tk.Radiobutton(
                config_frame,
                text=opt,
                variable=self.graphics_var,
                value=opt.split()[0],
                bg=self.colors['window_content']
            ).pack(anchor=tk.W, padx=20)
        
        # Desktop Features
        Label(config_frame, text="\nDesktop Features:", bg=self.colors['window_content'],
              font=('Helvetica', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        self.features = {
            'showcase': tk.BooleanVar(value=True),
            'inventor': tk.BooleanVar(value=True),
            'media': tk.BooleanVar(value=True),
            'dev': tk.BooleanVar(value=False)
        }
        
        features_text = {
            'showcase': "Showcase (3D Presentations)",
            'inventor': "Inventor (3D Modeling)",
            'media': "Media Tools",
            'dev': "Development Environment"
        }
        
        for key, text in features_text.items():
            tk.Checkbutton(
                config_frame,
                text=text,
                variable=self.features[key],
                bg=self.colors['window_content']
            ).pack(anchor=tk.W, padx=20)

    def show_wizard_step4(self):
        """Wizard Step 4: Complete"""
        for widget in self.wizard_content.winfo_children():
            widget.destroy()
        
        Label(
            self.wizard_content,
            text="Setup Complete!",
            bg=self.colors['window_content'],
            font=('Helvetica', 18, 'bold'),
            fg=self.colors['primary']
        ).pack(pady=30)
        
        # Success icon
        success_frame = Frame(self.wizard_content, bg=self.colors['highlight'], width=100, height=100)
        success_frame.pack(pady=20)
        success_frame.pack_propagate(False)
        Label(
            success_frame,
            text="✓",
            font=('Arial', 48),
            bg=self.colors['highlight'],
            fg=self.colors['text_light']
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        Label(
            self.wizard_content,
            text="Your Flames Co. Indy workstation is ready!",
            bg=self.colors['window_content'],
            font=('Helvetica', 14, 'bold')
        ).pack(pady=10)
        
        # Summary
        summary_frame = Frame(self.wizard_content, bg=self.colors['text_light'], relief=tk.SUNKEN, bd=2)
        summary_frame.pack(padx=40, pady=20, fill=tk.X)
        
        summary_text = """Quick Start Guide:
• Click Toolchest for system menu
• Double-click icons to launch apps
• Console provides UNIX shell
• Check /usr/demos for demos
• 🔥 Igniting Innovation™"""
        
        Label(
            summary_frame,
            text=summary_text,
            bg=self.colors['text_light'],
            font=('Courier', 10),
            justify=tk.LEFT
        ).pack(padx=20, pady=20)
        
        self.wizard_next_btn.config(text="Finish")

    def wizard_next(self):
        """Navigate to next wizard step"""
        if self.wizard_step == 1:
            self.wizard_step = 2
            self.show_wizard_step2()
        elif self.wizard_step == 2:
            self.wizard_step = 3
            self.show_wizard_step3()
        elif self.wizard_step == 3:
            self.wizard_step = 4
            self.show_wizard_step4()
        elif self.wizard_step == 4:
            self.complete_wizard()

    def wizard_previous(self):
        """Navigate to previous wizard step"""
        if self.wizard_step == 2:
            self.wizard_step = 1
            self.wizard_back_btn.config(state=tk.DISABLED)
            self.show_wizard_step1()
        elif self.wizard_step == 3:
            self.wizard_step = 2
            self.show_wizard_step2()
        elif self.wizard_step == 4:
            self.wizard_step = 3
            self.wizard_next_btn.config(text="Next ▶")
            self.show_wizard_step3()

    def skip_wizard(self):
        """Skip the setup wizard"""
        if messagebox.askyesno("Skip Setup", "Skip the Out Box setup? You can run it again from the Toolchest menu."):
            self.wizard.destroy()
            self.wizard_complete = True
            self.show_welcome()

    def complete_wizard(self):
        """Complete the wizard setup"""
        self.wizard.destroy()
        self.wizard_complete = True
        self.show_welcome()

    def show_welcome(self):
        """Show welcome message window"""
        win = self.create_window("Welcome to Flames Indy", 400, 250, 300, 200)
        
        content = Frame(win, bg=self.colors['window_content'])
        content.pack(fill=tk.BOTH, expand=True)
        
        Label(
            content,
            text="Welcome to Flames Computing",
            font=('Helvetica', 14, 'bold'),
            bg=self.colors['window_content'],
            fg=self.colors['primary']
        ).pack(pady=20)
        
        # Logo
        logo_frame = Frame(content, bg=self.colors['primary'], width=80, height=80)
        logo_frame.pack(pady=10)
        logo_frame.pack_propagate(False)
        Label(
            logo_frame,
            text="🔥",
            font=('Arial', 36),
            bg=self.colors['primary'],
            fg=self.colors['text_light']
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        Label(
            content,
            text="Flames Indy 1.0a",
            font=('Helvetica', 12),
            bg=self.colors['window_content']
        ).pack()
        
        Label(
            content,
            text="Igniting Innovation™",
            font=('Helvetica', 10, 'italic'),
            bg=self.colors['window_content'],
            fg=self.colors['primary']
        ).pack(pady=10)

    def create_window(self, title, width, height, x, y):
        """Create a new window"""
        window = Toplevel(self.root)
        window.title(title)
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.configure(bg=self.colors['window_bg'])
        
        # Title bar
        titlebar = Frame(window, bg=self.colors['primary'], height=24)
        titlebar.pack(fill=tk.X)
        titlebar.pack_propagate(False)
        
        Label(
            titlebar,
            text=title,
            bg=self.colors['primary'],
            fg=self.colors['text_light'],
            font=('Helvetica', 10, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        # Window controls
        Button(
            titlebar,
            text="X",
            bg=self.colors['window_bg'],
            font=('Helvetica', 8, 'bold'),
            width=2,
            command=window.destroy
        ).pack(side=tk.RIGHT, padx=2, pady=2)
        
        self.windows.append(window)
        return window

    def open_console(self):
        """Open console terminal"""
        win = self.create_window(f"{self.username}@{self.hostname} - Console", 650, 400, 200, 100)
        
        # Console text widget
        console = Text(
            win,
            bg='black',
            fg='#00FF00',
            font=('Courier', 11),
            insertbackground='#00FF00'
        )
        console.pack(fill=tk.BOTH, expand=True)
        
        # Initial text
        console.insert(tk.END, f"Flames Indy Release 1.0a Build 1994.11.22\n")
        console.insert(tk.END, f"Copyright 1994 Flames Computing Corporation\n")
        console.insert(tk.END, f"All Rights Reserved.\n\n")
        console.insert(tk.END, f"Last login: {datetime.now()}\n")
        console.insert(tk.END, f"{self.username}@{self.hostname} $ ")
        
        # Bind commands
        def handle_command(event):
            # Get current line
            current_pos = console.index(tk.INSERT)
            line_start = console.index(f"{current_pos} linestart")
            line_content = console.get(line_start, "end-1c")
            
            if '$ ' in line_content:
                cmd = line_content.split('$ ', 1)[1].strip()
                console.insert(tk.END, '\n')
                
                # Process command
                output = self.process_command(cmd)
                if output:
                    console.insert(tk.END, output + '\n')
                
                console.insert(tk.END, f"{self.username}@{self.hostname} $ ")
                console.see(tk.END)
            
            return "break"
        
        console.bind('<Return>', handle_command)
        console.focus_set()

    def process_command(self, cmd):
        """Process console commands"""
        parts = cmd.split()
        if not parts:
            return ""
        
        command = parts[0]
        
        commands = {
            'ls': "Desktop  Documents  Projects  demos  bin  lib",
            'pwd': f"/usr/people/{self.username}",
            'date': datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y"),
            'uname': "Flames Indy 1.0a FIRE-R5000",
            'hinv': """CPU: FIRE R5000 Processor @ 150MHz
Memory: 128 Mbytes
Graphics: FlameXZ 24-bit Accelerator
Audio: Integrated FlameSound System
Disk: 2.0 GB SCSI""",
            'clear': '\033[2J\033[H',
            'whoami': self.username,
            'hostname': self.hostname,
            'help': """Available commands:
ls       - list directory
pwd      - print working directory
date     - show date/time
uname    - system info
hinv     - hardware inventory
clear    - clear screen
help     - show this help"""
        }
        
        if command in commands:
            return commands[command]
        elif command == 'exit':
            return "[Console will close]"
        else:
            return f"flames-sh: {command}: command not found"

    def open_file_manager(self):
        """Open file manager"""
        win = self.create_window("File Manager - /usr/people/flames", 600, 400, 250, 150)
        
        # Toolbar
        toolbar = Frame(win, bg=self.colors['window_bg'], height=30)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        Button(toolbar, text="Up", width=8, command=lambda: None).pack(side=tk.LEFT, padx=2, pady=2)
        Button(toolbar, text="Home", width=8, command=lambda: None).pack(side=tk.LEFT, padx=2, pady=2)
        Button(toolbar, text="New", width=8, command=lambda: None).pack(side=tk.LEFT, padx=2, pady=2)
        
        # File list frame
        list_frame = Frame(win, bg=self.colors['window_content'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create file grid
        files = [
            ("Desktop", "📁"),
            ("Documents", "📁"),
            ("Projects", "📁"),
            ("demos", "📁"),
            ("showcase.app", "🎨"),
            ("inventor.app", "🔧"),
            ("README.txt", "📄"),
            ("flames.demo", "🔥")
        ]
        
        row = 0
        col = 0
        for filename, icon in files:
            file_frame = Frame(list_frame, bg=self.colors['window_content'], width=100, height=100)
            file_frame.grid(row=row, column=col, padx=10, pady=10)
            
            Button(
                file_frame,
                text=icon,
                font=('Arial', 28),
                bg=self.colors['window_content'],
                bd=0,
                activebackground=self.colors['primary']
            ).pack()
            
            Label(
                file_frame,
                text=filename,
                bg=self.colors['window_content'],
                font=('Helvetica', 9)
            ).pack()
            
            col += 1
            if col > 4:
                col = 0
                row += 1

    def open_text_editor(self):
        """Open text editor"""
        win = self.create_window("Text Editor - untitled.txt", 600, 400, 300, 200)
        
        # Menu bar simulation
        menubar = Frame(win, bg=self.colors['window_bg'], height=24)
        menubar.pack(fill=tk.X)
        
        Button(menubar, text="File", width=6).pack(side=tk.LEFT)
        Button(menubar, text="Edit", width=6).pack(side=tk.LEFT)
        Button(menubar, text="View", width=6).pack(side=tk.LEFT)
        
        # Text area
        text_area = Text(win, font=('Courier', 11), bg='white')
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = Scrollbar(text_area)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_area.yview)
        
        text_area.insert('1.0', "# Welcome to Flames Text Editor\n\n")
        text_area.insert('end', "Start typing your document here...")

    def open_system_info(self):
        """Open system information window"""
        win = self.create_window("System Information", 500, 450, 260, 150)
        
        info_text = Text(win, bg=self.colors['window_content'], font=('Courier', 10))
        info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        system_info = f"""=== Flames Co. Indy System Information ===

System: Flames Indy Professional Workstation
Version: 1.0a Build 1994.11.22
Kernel: FIRE-OS 5.3.1994
Architecture: FIRE64

Hardware Configuration:
-----------------------
CPU: FIRE R5000 @ 150 MHz
  Cache: L1 32KB, L2 512KB
Memory: 128 MB SDRAM
  Speed: 100 MHz
  
Graphics: FlameXZ 24-bit Accelerator
  VRAM: 8 MB
  Max Resolution: 1280x1024 @ 76Hz
  3D Pipeline: Yes
  Z-Buffer: 24-bit
  
Storage: 2.0 GB Ultra SCSI
  Interface: SCSI-2 Fast/Wide
  
Audio: FlameSound Integrated
  16-bit Stereo
  44.1 KHz Sampling
  
Network: 10BASE-T Ethernet
  MAC: 08:00:69:FF:FF:FF

Software Features:
------------------
Desktop: Indigo Magic 1.0a
OpenGL: 1.0 Compatible
Inventor: 2.0 Ready
Media Tools: Installed

© 1994 Flames Computing Corporation
🔥 Igniting Innovation™"""
        
        info_text.insert('1.0', system_info)
        info_text.config(state='disabled')

    def open_process_manager(self):
        """Open process manager"""
        win = self.create_window("Process Manager", 500, 350, 280, 180)
        
        # Process list
        columns = ('PID', 'Process', 'CPU%', 'Memory')
        tree = ttk.Treeview(win, columns=columns, show='headings', height=12)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # Sample processes
        processes = [
            (1, 'init', '0.0', '1M'),
            (42, 'kernel', '0.1', '3M'),
            (128, 'window_mgr', '2.5', '12M'),
            (256, 'toolchest', '0.5', '8M'),
            (512, 'console', '1.0', '4M'),
            (1024, 'clock', '0.1', '2M'),
            (2048, 'flames_daemon', '0.8', '6M')
        ]
        
        for proc in processes:
            tree.insert('', tk.END, values=proc)
        
        # Buttons
        btn_frame = Frame(win, bg=self.colors['window_bg'])
        btn_frame.pack(fill=tk.X, pady=5)
        
        Button(btn_frame, text="Kill Process", width=12).pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Refresh", width=12).pack(side=tk.LEFT, padx=5)

    def show_hinv(self):
        """Show hardware inventory"""
        self.show_message("Hardware Inventory", """Flames Indy Hardware Inventory:

1 150 MHZ IP22 Processor (FIRE R5000)
CPU: FIRE R5000 Processor Chip Revision: 2.1
FPU: FIRE R5010 Floating Point Revision: 1.0
Main memory: 128 Mbytes
Secondary cache: 512 Kbytes
Instruction cache: 32 Kbytes Data cache: 32 Kbytes
Graphics board: FlameXZ 24-bit
SCSI Disk: unit 1 on SCSI controller 0
Audio: FlameSound Integrated System""")

    def run_demo(self, demo_name):
        """Run a graphics demo"""
        demos = {
            'flames': "🔥 Flames Demo - Real-time particle system",
            'butterfly': "🦋 Butterfly - 3D animated butterfly",
            'wave3d': "🌊 Wave3D - Ocean wave simulation"
        }
        
        win = self.create_window(f"Demo: {demo_name}", 400, 300, 312, 234)
        
        canvas = Canvas(win, bg='black')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Animated demo simulation
        if demo_name == 'flames':
            # Flame particles
            particles = []
            for _ in range(20):
                x = random.randint(150, 250)
                y = 250
                particle = canvas.create_oval(x, y, x+10, y+10,
                                             fill='orange', outline='red')
                particles.append({'id': particle, 'x': x, 'y': y,
                                'vx': random.uniform(-2, 2),
                                'vy': random.uniform(-5, -2)})
            
            def animate():
                for p in particles:
                    p['x'] += p['vx']
                    p['y'] += p['vy']
                    p['vy'] += 0.2  # gravity
                    
                    if p['y'] > 250:
                        p['y'] = 250
                        p['x'] = random.randint(150, 250)
                        p['vx'] = random.uniform(-2, 2)
                        p['vy'] = random.uniform(-5, -2)
                    
                    canvas.coords(p['id'], p['x'], p['y'], p['x']+10, p['y']+10)
                
                win.after(50, animate)
            
            animate()
        
        Label(
            canvas,
            text=demos.get(demo_name, "Demo"),
            bg='black',
            fg='white',
            font=('Helvetica', 12)
        ).place(relx=0.5, rely=0.1, anchor=tk.CENTER)

    def show_about(self):
        """Show about dialog"""
        win = self.create_window("About Flames Indy", 400, 350, 312, 200)
        
        content = Frame(win, bg=self.colors['window_content'])
        content.pack(fill=tk.BOTH, expand=True)
        
        # Logo
        logo_frame = Frame(content, bg=self.colors['primary'], width=100, height=100)
        logo_frame.pack(pady=20)
        logo_frame.pack_propagate(False)
        
        Label(
            logo_frame,
            text="🔥",
            font=('Arial', 48),
            bg=self.colors['primary'],
            fg=self.colors['text_light']
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        Label(
            content,
            text="Flames Co. Indy®",
            font=('Helvetica', 18, 'bold'),
            bg=self.colors['window_content'],
            fg=self.colors['primary']
        ).pack()
        
        Label(
            content,
            text="Version 1.0a",
            font=('Helvetica', 12),
            bg=self.colors['window_content']
        ).pack(pady=5)
        
        Label(
            content,
            text="Professional Workstation OS",
            font=('Helvetica', 10),
            bg=self.colors['window_content']
        ).pack()
        
        Frame(content, bg='gray', height=2).pack(fill=tk.X, pady=20, padx=40)
        
        Label(
            content,
            text="Copyright © 1994 Flames Computing Corporation",
            font=('Helvetica', 9),
            bg=self.colors['window_content']
        ).pack()
        
        Label(
            content,
            text="All Rights Reserved.",
            font=('Helvetica', 9),
            bg=self.colors['window_content']
        ).pack()
        
        Label(
            content,
            text="🔥 Igniting Innovation™",
            font=('Helvetica', 11, 'italic'),
            bg=self.colors['window_content'],
            fg=self.colors['primary']
        ).pack(pady=20)

    def show_message(self, title, message=""):
        """Show a simple message dialog"""
        messagebox.showinfo(title, message if message else f"{title} feature")

    def logout(self):
        """Logout confirmation"""
        if messagebox.askyesno("Logout", "End your Flames Indy session?"):
            self.root.quit()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = IndyDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
