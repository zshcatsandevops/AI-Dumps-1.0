import tkinter as tk
from tkinter import ttk, Menu, Text, Scrollbar, Canvas, Toplevel, Frame, Label, Button, Entry, Listbox, messagebox, filedialog
import os
import json
import time
from datetime import datetime
import random
import threading
from pathlib import Path
import base64
import mimetypes

class VirtualFileSystem:
    """Virtual file system for the OS"""
    def __init__(self):
        self.root = {
            'type': 'directory',
            'name': '/',
            'children': {
                'home': {
                    'type': 'directory',
                    'name': 'home',
                    'children': {
                        'user': {
                            'type': 'directory',
                            'name': 'user',
                            'children': {
                                'Documents': {'type': 'directory', 'name': 'Documents', 'children': {}},
                                'Downloads': {'type': 'directory', 'name': 'Downloads', 'children': {}},
                                'Games': {
                                    'type': 'directory',
                                    'name': 'Games',
                                    'children': {
                                        'ROMs': {'type': 'directory', 'name': 'ROMs', 'children': {}}
                                    }
                                },
                                'Pictures': {'type': 'directory', 'name': 'Pictures', 'children': {}},
                                'Music': {'type': 'directory', 'name': 'Music', 'children': {}}
                            }
                        }
                    }
                },
                'usr': {
                    'type': 'directory',
                    'name': 'usr',
                    'children': {
                        'bin': {'type': 'directory', 'name': 'bin', 'children': {}},
                        'share': {'type': 'directory', 'name': 'share', 'children': {}}
                    }
                },
                'etc': {'type': 'directory', 'name': 'etc', 'children': {}},
                'tmp': {'type': 'directory', 'name': 'tmp', 'children': {}}
            }
        }
        
        # Add some default files
        self.create_file('/home/user/Documents', 'readme.txt', 
                        'Welcome to GNU/Koopa OS!\n\nThis is a fully functional desktop environment.')
        self.create_file('/home/user/Documents', 'notes.md', 
                        '# My Notes\n\n- Try the Switch 2 gaming mode\n- Upload some ROM files\n- Explore the file system')

    def navigate(self, path):
        """Navigate to a path and return the node"""
        if path == '/':
            return self.root
        
        parts = path.strip('/').split('/')
        current = self.root
        
        for part in parts:
            if current.get('children') and part in current['children']:
                current = current['children'][part]
            else:
                return None
        return current

    def create_file(self, path, name, content='', file_type='text'):
        """Create a new file"""
        dir_node = self.navigate(path)
        if dir_node and dir_node['type'] == 'directory':
            dir_node['children'][name] = {
                'type': 'file',
                'name': name,
                'content': content,
                'file_type': file_type,
                'size': len(content) if isinstance(content, (str, bytes)) else 0,
                'created': datetime.now().isoformat()
            }
            return True
        return False

    def create_directory(self, path, name):
        """Create a new directory"""
        dir_node = self.navigate(path)
        if dir_node and dir_node['type'] == 'directory':
            dir_node['children'][name] = {
                'type': 'directory',
                'name': name,
                'children': {}
            }
            return True
        return False

    def delete_item(self, path, name):
        """Delete a file or directory"""
        dir_node = self.navigate(path)
        if dir_node and dir_node.get('children') and name in dir_node['children']:
            del dir_node['children'][name]
            return True
        return False

    def read_file(self, path, name):
        """Read file content"""
        dir_node = self.navigate(path)
        if dir_node and dir_node.get('children') and name in dir_node['children']:
            file_node = dir_node['children'][name]
            if file_node['type'] == 'file':
                return file_node.get('content', '')
        return None

    def list_directory(self, path):
        """List directory contents"""
        dir_node = self.navigate(path)
        if dir_node and dir_node['type'] == 'directory':
            return list(dir_node.get('children', {}).values())
        return []

    def rename_item(self, path, old_name, new_name):
        """Rename a file or directory"""
        dir_node = self.navigate(path)
        if dir_node and dir_node.get('children') and old_name in dir_node['children']:
            dir_node['children'][new_name] = dir_node['children'][old_name]
            dir_node['children'][new_name]['name'] = new_name
            del dir_node['children'][old_name]
            return True
        return False

class Window:
    """Base window class for all applications"""
    def __init__(self, parent, title, width=600, height=400):
        self.parent = parent
        self.window = Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg='#d0d0d0')
        
        # Track window for management
        if hasattr(parent, 'windows'):
            parent.windows.append(self.window)
        
        # Create title bar
        self.create_title_bar(title)
        
        # Content frame
        self.content_frame = Frame(self.window, bg='white')
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))
        
    def create_title_bar(self, title):
        """Create window title bar"""
        title_bar = Frame(self.window, bg='#006633', height=25)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        
        Label(title_bar, text=title, bg='#006633', fg='white',
              font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        Button(title_bar, text="X", bg='#c0c0c0', fg='black',
               font=('Arial', 8, 'bold'), command=self.window.destroy,
               width=3).pack(side=tk.RIGHT, padx=2, pady=2)

class Terminal(Window):
    """Terminal application"""
    def __init__(self, parent, fs):
        super().__init__(parent, "🐢 Koopa Shell", 600, 400)
        self.fs = fs
        self.current_dir = '/home/user'
        self.history = []
        self.history_index = 0
        
        # Terminal display
        self.terminal = Text(self.content_frame, bg='black', fg='#00ff00',
                           font=('Courier', 10), insertbackground='#00ff00')
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        # Initial prompt
        self.terminal.insert('1.0', f"GNU/Koopa 1.0.x [Beta]\n")
        self.terminal.insert('end', f"Copyright (c) 2025 The Koopa Project\n\n")
        self.terminal.insert('end', f"Last login: {datetime.now()}\n")
        self.show_prompt()
        
        # Bind events
        self.terminal.bind('<Return>', self.execute_command)
        self.terminal.bind('<Up>', self.history_up)
        self.terminal.bind('<Down>', self.history_down)
        self.terminal.focus_set()

    def show_prompt(self):
        """Show command prompt"""
        prompt = f"{self.current_dir}$ "
        self.terminal.insert('end', prompt)
        self.terminal.mark_set('prompt_end', 'end-1c')
        self.terminal.see('end')

    def execute_command(self, event):
        """Execute terminal command"""
        # Get command from current line
        current_line = self.terminal.get('prompt_end', 'end-1c').strip()
        if not current_line:
            self.terminal.insert('end', '\n')
            self.show_prompt()
            return 'break'
        
        self.history.append(current_line)
        self.history_index = len(self.history)
        
        self.terminal.insert('end', '\n')
        
        # Parse and execute command
        parts = current_line.split()
        if not parts:
            self.show_prompt()
            return 'break'
            
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Command processing
        if cmd == 'ls':
            items = self.fs.list_directory(self.current_dir)
            for item in items:
                icon = '📁' if item['type'] == 'directory' else '📄'
                self.terminal.insert('end', f"{icon} {item['name']}\n")
                
        elif cmd == 'pwd':
            self.terminal.insert('end', f"{self.current_dir}\n")
            
        elif cmd == 'cd':
            if args:
                new_path = args[0]
                if new_path == '..':
                    parts = self.current_dir.split('/')
                    if len(parts) > 2:
                        self.current_dir = '/'.join(parts[:-1])
                    elif len(parts) == 2 and parts[0] == '':
                        self.current_dir = '/'
                elif new_path.startswith('/'):
                    if self.fs.navigate(new_path):
                        self.current_dir = new_path
                    else:
                        self.terminal.insert('end', f"cd: {new_path}: No such directory\n")
                else:
                    test_path = f"{self.current_dir}/{new_path}".replace('//', '/')
                    if self.fs.navigate(test_path):
                        self.current_dir = test_path
                    else:
                        self.terminal.insert('end', f"cd: {new_path}: No such directory\n")
                        
        elif cmd == 'mkdir':
            if args:
                if self.fs.create_directory(self.current_dir, args[0]):
                    self.terminal.insert('end', f"Directory '{args[0]}' created\n")
                else:
                    self.terminal.insert('end', f"mkdir: cannot create directory '{args[0]}'\n")
                    
        elif cmd == 'touch':
            if args:
                if self.fs.create_file(self.current_dir, args[0], ''):
                    self.terminal.insert('end', f"File '{args[0]}' created\n")
                    
        elif cmd == 'rm':
            if args:
                if self.fs.delete_item(self.current_dir, args[0]):
                    self.terminal.insert('end', f"Removed '{args[0]}'\n")
                else:
                    self.terminal.insert('end', f"rm: cannot remove '{args[0]}': No such file\n")
                    
        elif cmd == 'cat':
            if args:
                content = self.fs.read_file(self.current_dir, args[0])
                if content is not None:
                    if isinstance(content, bytes):
                        self.terminal.insert('end', "[Binary file]\n")
                    else:
                        self.terminal.insert('end', f"{content}\n")
                else:
                    self.terminal.insert('end', f"cat: {args[0]}: No such file\n")
                    
        elif cmd == 'echo':
            self.terminal.insert('end', ' '.join(args) + '\n')
            
        elif cmd == 'clear':
            self.terminal.delete('1.0', 'end')
            
        elif cmd == 'help':
            help_text = """Available commands:
ls       - List directory contents
pwd      - Print working directory
cd       - Change directory
mkdir    - Create directory
touch    - Create empty file
rm       - Remove file or directory
cat      - Display file contents
echo     - Display text
clear    - Clear terminal
uname    - System information
date     - Show date and time
switch2  - Launch Switch 2 Gaming Mode
help     - Show this help
exit     - Close terminal
"""
            self.terminal.insert('end', help_text)
            
        elif cmd == 'uname':
            self.terminal.insert('end', "GNU/Koopa 1.0.x koopa-kernel-5.19.0 x86_64\n")
            
        elif cmd == 'date':
            self.terminal.insert('end', f"{datetime.now()}\n")
            
        elif cmd == 'switch2':
            self.terminal.insert('end', "Launching Switch 2 Gaming Mode...\n")
            Switch2Mode(self.parent, self.fs)
            
        elif cmd == 'exit':
            self.window.destroy()
            return 'break'
            
        else:
            self.terminal.insert('end', f"ksh: {cmd}: command not found\n")
        
        self.show_prompt()
        return 'break'

    def history_up(self, event):
        """Navigate command history up"""
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.terminal.delete('prompt_end', 'end-1c')
            self.terminal.insert('prompt_end', self.history[self.history_index])
        return 'break'

    def history_down(self, event):
        """Navigate command history down"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.terminal.delete('prompt_end', 'end-1c')
            self.terminal.insert('prompt_end', self.history[self.history_index])
        return 'break'

class FileManager(Window):
    """File Manager application"""
    def __init__(self, parent, fs, initial_path='/home/user'):
        super().__init__(parent, "📁 File Manager", 600, 400)
        self.fs = fs
        self.current_path = initial_path
        self.selected_item = None
        
        # Toolbar
        toolbar = Frame(self.content_frame, bg='#e0e0e0', height=30)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        
        Button(toolbar, text="⬆️ Up", command=self.navigate_up).pack(side=tk.LEFT, padx=2, pady=2)
        Button(toolbar, text="📁 New Folder", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        Button(toolbar, text="📄 New File", command=self.create_file).pack(side=tk.LEFT, padx=2)
        Button(toolbar, text="📤 Upload", command=self.upload_file).pack(side=tk.LEFT, padx=2)
        Button(toolbar, text="🗑️ Delete", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        
        # Path display
        self.path_var = tk.StringVar(value=self.current_path)
        path_entry = Entry(toolbar, textvariable=self.path_var, state='readonly',
                          font=('Courier', 10))
        path_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5, pady=2)
        
        # File list
        list_frame = Frame(self.content_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set,
                                   font=('Courier', 10), bg='white')
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Bindings
        self.file_listbox.bind('<Double-Button-1>', self.open_item)
        self.file_listbox.bind('<<ListboxSelect>>', self.on_select)
        self.file_listbox.bind('<Button-3>', self.show_context_menu)
        
        self.refresh_list()

    def refresh_list(self):
        """Refresh file list"""
        self.file_listbox.delete(0, tk.END)
        items = self.fs.list_directory(self.current_path)
        
        if not items:
            self.file_listbox.insert(tk.END, "[Empty folder]")
            return
        
        # Sort directories first, then files
        dirs = [item for item in items if item['type'] == 'directory']
        files = [item for item in items if item['type'] == 'file']
        
        for item in sorted(dirs, key=lambda x: x['name']):
            self.file_listbox.insert(tk.END, f"📁 {item['name']}")
            
        for item in sorted(files, key=lambda x: x['name']):
            icon = self.get_file_icon(item)
            size = self.format_size(item.get('size', 0))
            self.file_listbox.insert(tk.END, f"{icon} {item['name']} ({size})")

    def get_file_icon(self, file):
        """Get icon for file type"""
        name = file['name'].lower()
        if name.endswith(('.nes', '.smc', '.sfc', '.gb', '.gbc', '.gba', '.n64', '.z64')):
            return '🎮'
        elif name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return '🖼️'
        elif name.endswith(('.mp3', '.wav', '.ogg', '.flac')):
            return '🎵'
        elif name.endswith(('.mp4', '.avi', '.mkv', '.webm')):
            return '🎬'
        elif name.endswith(('.py', '.js', '.html', '.css', '.c', '.cpp', '.java')):
            return '💻'
        elif name.endswith(('.txt', '.md', '.log', '.ini', '.cfg')):
            return '📝'
        else:
            return '📄'

    def format_size(self, size):
        """Format file size"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def navigate_up(self):
        """Navigate to parent directory"""
        if self.current_path != '/':
            parts = self.current_path.split('/')
            if len(parts) > 2:
                self.current_path = '/'.join(parts[:-1])
            else:
                self.current_path = '/'
            self.path_var.set(self.current_path)
            self.refresh_list()

    def open_item(self, event=None):
        """Open selected item"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
            
        item_text = self.file_listbox.get(selection[0])
        if item_text == "[Empty folder]":
            return
            
        # Extract name from display text
        if item_text.startswith('📁'):
            name = item_text[2:].strip()
            self.current_path = f"{self.current_path}/{name}".replace('//', '/')
            self.path_var.set(self.current_path)
            self.refresh_list()
        else:
            # Extract filename (remove icon and size)
            parts = item_text.split(' ')
            if len(parts) >= 2:
                name = ' '.join(parts[1:]).rsplit(' (', 1)[0]
                self.open_file(name)

    def open_file(self, name):
        """Open a file with appropriate application"""
        content = self.fs.read_file(self.current_path, name)
        if content is None:
            return
            
        # Determine file type and open appropriate app
        if name.lower().endswith(('.nes', '.smc', '.sfc', '.gb', '.gbc', '.gba', '.n64', '.z64')):
            Emulator(self.parent, name, content)
        elif name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            ImageViewer(self.parent, name, content)
        else:
            TextEditor(self.parent, self.fs, self.current_path, name, content)

    def on_select(self, event):
        """Handle item selection"""
        selection = self.file_listbox.curselection()
        if selection:
            self.selected_item = self.file_listbox.get(selection[0])

    def create_folder(self):
        """Create new folder"""
        dialog = tk.Toplevel(self.window)
        dialog.title("New Folder")
        dialog.geometry("300x100")
        
        Label(dialog, text="Folder name:").pack(pady=5)
        name_entry = Entry(dialog, width=30)
        name_entry.pack(pady=5)
        
        def create():
            name = name_entry.get().strip()
            if name:
                if self.fs.create_directory(self.current_path, name):
                    self.refresh_list()
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Could not create folder")
        
        Button(dialog, text="Create", command=create).pack(pady=10)
        name_entry.focus_set()

    def create_file(self):
        """Create new file"""
        dialog = tk.Toplevel(self.window)
        dialog.title("New File")
        dialog.geometry("300x100")
        
        Label(dialog, text="File name:").pack(pady=5)
        name_entry = Entry(dialog, width=30)
        name_entry.pack(pady=5)
        
        def create():
            name = name_entry.get().strip()
            if name:
                if self.fs.create_file(self.current_path, name, ''):
                    self.refresh_list()
                    dialog.destroy()
        
        Button(dialog, text="Create", command=create).pack(pady=10)
        name_entry.focus_set()

    def upload_file(self):
        """Upload files from host system"""
        files = filedialog.askopenfilenames()
        for filepath in files:
            try:
                name = os.path.basename(filepath)
                # Determine file type
                mime_type, _ = mimetypes.guess_type(filepath)
                
                # Read file content
                if mime_type and mime_type.startswith('text'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                
                # Determine virtual file type
                if name.lower().endswith(('.nes', '.smc', '.gb', '.gba', '.n64')):
                    file_type = 'rom'
                elif mime_type and mime_type.startswith('image'):
                    file_type = 'image'
                elif mime_type and mime_type.startswith('text'):
                    file_type = 'text'
                else:
                    file_type = 'binary'
                
                self.fs.create_file(self.current_path, name, content, file_type)
            except Exception as e:
                messagebox.showerror("Upload Error", f"Failed to upload {name}: {str(e)}")
        
        self.refresh_list()

    def delete_selected(self):
        """Delete selected item"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
            
        item_text = self.file_listbox.get(selection[0])
        if item_text == "[Empty folder]":
            return
            
        # Extract name
        if item_text.startswith('📁'):
            name = item_text[2:].strip()
        else:
            parts = item_text.split(' ')
            if len(parts) >= 2:
                name = ' '.join(parts[1:]).rsplit(' (', 1)[0]
            else:
                return
        
        if messagebox.askyesno("Delete", f"Delete '{name}'?"):
            if self.fs.delete_item(self.current_path, name):
                self.refresh_list()

    def show_context_menu(self, event):
        """Show context menu"""
        menu = Menu(self.window, tearoff=0)
        menu.add_command(label="Open", command=self.open_item)
        menu.add_command(label="Delete", command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label="Refresh", command=self.refresh_list)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

class TextEditor(Window):
    """Text Editor application"""
    def __init__(self, parent, fs, path, filename, content=''):
        super().__init__(parent, f"📝 Text Editor - {filename}", 600, 400)
        self.fs = fs
        self.path = path
        self.filename = filename
        self.modified = False
        
        # Menu bar
        menubar = Menu(self.window)
        self.window.config(menu=menubar)
        
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.destroy)
        
        # Text area
        self.text_area = Text(self.content_frame, wrap=tk.WORD,
                             font=('Courier', 11))
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = Scrollbar(self.text_area)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_area.yview)
        
        # Insert content
        if isinstance(content, bytes):
            self.text_area.insert('1.0', "[Binary file - cannot edit]")
            self.text_area.config(state='disabled')
        else:
            self.text_area.insert('1.0', content)
            self.text_area.bind('<Key>', self.on_modify)

    def on_modify(self, event=None):
        """Mark as modified"""
        if not self.modified:
            self.modified = True
            self.window.title(f"📝 Text Editor - {self.filename} *")

    def save_file(self):
        """Save file"""
        if self.text_area['state'] == 'disabled':
            return
            
        content = self.text_area.get('1.0', 'end-1c')
        dir_node = self.fs.navigate(self.path)
        if dir_node and dir_node.get('children') and self.filename in dir_node['children']:
            dir_node['children'][self.filename]['content'] = content
            dir_node['children'][self.filename]['size'] = len(content)
            self.modified = False
            self.window.title(f"📝 Text Editor - {self.filename}")
            messagebox.showinfo("Save", "File saved successfully!")

    def save_as(self):
        """Save as new file"""
        if self.text_area['state'] == 'disabled':
            return
            
        dialog = tk.Toplevel(self.window)
        dialog.title("Save As")
        dialog.geometry("300x100")
        
        Label(dialog, text="File name:").pack(pady=5)
        name_entry = Entry(dialog, width=30)
        name_entry.insert(0, self.filename)
        name_entry.pack(pady=5)
        
        def save():
            name = name_entry.get().strip()
            if name:
                content = self.text_area.get('1.0', 'end-1c')
                if self.fs.create_file(self.path, name, content):
                    self.filename = name
                    self.modified = False
                    self.window.title(f"📝 Text Editor - {self.filename}")
                    dialog.destroy()
                    messagebox.showinfo("Save", f"Saved as '{name}'")
        
        Button(dialog, text="Save", command=save).pack(pady=10)

class ImageViewer(Window):
    """Image Viewer application"""
    def __init__(self, parent, filename, content):
        super().__init__(parent, f"🖼️ Image Viewer - {filename}", 600, 400)
        
        Label(self.content_frame, text=f"Image: {filename}",
              font=('Arial', 14)).pack(pady=20)
        Label(self.content_frame, text="[Image display not implemented in tkinter version]",
              fg='gray').pack(pady=50)
        
        # In a real implementation, you would decode and display the image

class Emulator(Window):
    """ROM Emulator application"""
    def __init__(self, parent, rom_name, rom_content):
        super().__init__(parent, f"🎮 RetroArch - {rom_name}", 600, 400)
        self.rom_name = rom_name
        self.rom_content = rom_content
        self.running = False
        
        # Emulator screen
        self.screen = Frame(self.content_frame, bg='black', height=320)
        self.screen.pack(fill=tk.BOTH, expand=True)
        self.screen.pack_propagate(False)
        
        # Display
        self.display = Label(self.screen, bg='black', fg='#00ff00',
                           font=('Courier', 16))
        self.display.pack(expand=True)
        
        # Initial state
        self.display.config(text=f"🎮\n\nROM Loaded: {rom_name}\n\nSystem: {self.get_system()}\n\nPress PLAY to start")
        
        # Controls
        controls = Frame(self.content_frame, bg='#202020', height=50)
        controls.pack(fill=tk.X)
        
        Button(controls, text="▶️ Play", command=self.start_emulation).pack(side=tk.LEFT, padx=5, pady=10)
        Button(controls, text="⏸️ Pause", command=self.pause_emulation).pack(side=tk.LEFT, padx=5)
        Button(controls, text="🔄 Reset", command=self.reset_emulation).pack(side=tk.LEFT, padx=5)
        Button(controls, text="⏹️ Stop", command=self.stop_emulation).pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status = Label(controls, text="Ready", bg='#202020', fg='white')
        self.status.pack(side=tk.RIGHT, padx=10)

    def get_system(self):
        """Determine emulated system from ROM extension"""
        ext = self.rom_name.lower().split('.')[-1]
        systems = {
            'nes': 'Nintendo Entertainment System',
            'smc': 'Super Nintendo',
            'sfc': 'Super Famicom', 
            'gb': 'Game Boy',
            'gbc': 'Game Boy Color',
            'gba': 'Game Boy Advance',
            'n64': 'Nintendo 64',
            'z64': 'Nintendo 64'
        }
        return systems.get(ext, 'Unknown System')

    def start_emulation(self):
        """Start emulation simulation"""
        self.running = True
        self.status.config(text="Running")
        self.display.config(text=f"🎮 EMULATING\n\n{self.rom_name}\n\n[Simulation Mode]\n\nFPS: 60")
        
    def pause_emulation(self):
        """Pause emulation"""
        self.running = False
        self.status.config(text="Paused")
        self.display.config(text=f"🎮 PAUSED\n\n{self.rom_name}")

    def reset_emulation(self):
        """Reset emulation"""
        self.status.config(text="Reset")
        self.display.config(text=f"🔄 RESET\n\n{self.rom_name}\n\nPress PLAY to restart")
        self.running = False

    def stop_emulation(self):
        """Stop emulation"""
        self.running = False
        self.status.config(text="Stopped")
        self.display.config(text=f"⏹️ STOPPED\n\n{self.rom_name}\n\nPress PLAY to start")

class Switch2Mode(Window):
    """Switch 2 Gaming Mode"""
    def __init__(self, parent, fs):
        super().__init__(parent, "🎮 Switch 2 Gaming Mode", 600, 400)
        self.fs = fs
        self.content_frame.config(bg='black')
        
        # Title
        Label(self.content_frame, text="🎮 Switch 2 Gaming Mode",
              bg='black', fg='#00d4aa', font=('Arial', 20, 'bold')).pack(pady=20)
        
        # Game grid
        games_frame = Frame(self.content_frame, bg='black')
        games_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        games = [
            ("🍄 Mario Odyssey 2", self.launch_mario),
            ("⚔️ Zelda BOTW 2", self.launch_zelda),
            ("🏎️ Koopa Kart", self.launch_kart),
            ("🚀 Metroid Prime 4", self.launch_metroid),
            ("🕹️ RetroArch", self.open_retroarch),
            ("📁 ROM Library", self.open_rom_library)
        ]
        
        for i, (name, command) in enumerate(games):
            btn = Button(games_frame, text=name, bg='#00d4aa', fg='white',
                        font=('Arial', 12), command=command, width=20, height=3)
            btn.grid(row=i // 2, column=i % 2, padx=10, pady=10)

    def launch_mario(self):
        self.launch_game("Super Mario Odyssey 2")
        
    def launch_zelda(self):
        self.launch_game("Zelda: Breath of the Wild 2")
        
    def launch_kart(self):
        self.launch_game("Koopa Kart Racing")
        
    def launch_metroid(self):
        self.launch_game("Metroid Prime 4")

    def launch_game(self, game_name):
        """Launch a game simulation"""
        game_window = Window(self.parent, game_name, 600, 400)
        game_window.content_frame.config(bg='black')
        
        Label(game_window.content_frame, text="🎮", font=('Arial', 60),
              bg='black', fg='#00d4aa').pack(pady=50)
        Label(game_window.content_frame, text=f"Loading {game_name}...",
              font=('Arial', 16), bg='black', fg='white').pack()
        Label(game_window.content_frame, text="Press any key to start",
              font=('Arial', 12), bg='black', fg='gray').pack(pady=20)

    def open_retroarch(self):
        """Open RetroArch with ROM list"""
        retroarch_window = Window(self.parent, "🕹️ RetroArch", 600, 400)
        
        Label(retroarch_window.content_frame, text="ROM Library",
              font=('Arial', 14, 'bold')).pack(pady=10)
        
        # List ROMs
        rom_listbox = Listbox(retroarch_window.content_frame, font=('Courier', 10))
        rom_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Get ROMs from file system
        rom_path = '/home/user/Games/ROMs'
        roms = self.fs.list_directory(rom_path)
        
        if not roms:
            rom_listbox.insert(tk.END, "No ROMs found. Upload ROMs to /home/user/Games/ROMs")
        else:
            for rom in roms:
                if rom['type'] == 'file':
                    rom_listbox.insert(tk.END, f"🎮 {rom['name']}")
        
        def load_rom():
            selection = rom_listbox.curselection()
            if selection:
                rom_text = rom_listbox.get(selection[0])
                if rom_text.startswith('🎮'):
                    rom_name = rom_text[2:].strip()
                    content = self.fs.read_file(rom_path, rom_name)
                    if content:
                        Emulator(self.parent, rom_name, content)
        
        Button(retroarch_window.content_frame, text="Load ROM",
               command=load_rom).pack(pady=10)

    def open_rom_library(self):
        """Open file manager to ROM directory"""
        FileManager(self.parent, self.fs, '/home/user/Games/ROMs')

class ProcessManager(Window):
    """Process Manager application"""
    def __init__(self, parent):
        super().__init__(parent, "⚙️ Process Manager", 600, 400)
        
        # Create treeview
        columns = ('PID', 'Name', 'CPU%', 'Memory', 'Status')
        self.tree = ttk.Treeview(self.content_frame, columns=columns, show='headings')
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Add sample processes
        processes = [
            ('1', 'init', '0.0', '1.2 MB', 'Running'),
            ('42', 'kernel', '0.1', '2.5 MB', 'Running'),
            ('137', 'koopa-desktop', '2.5', '45.2 MB', 'Running'),
            ('256', 'koopa-shell', '0.5', '12.3 MB', 'Running'),
            ('512', 'file-manager', '0.2', '18.7 MB', 'Running'),
            ('1337', 'python3', '3.2', '87.4 MB', 'Running'),
        ]
        
        for proc in processes:
            self.tree.insert('', 'end', values=proc)
        
        # Buttons
        btn_frame = Frame(self.content_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        Button(btn_frame, text="Kill Process", 
               command=lambda: messagebox.showinfo("Info", "Cannot kill process (simulation)")).pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=5)

    def refresh(self):
        """Refresh process list (simulation)"""
        for item in self.tree.get_children():
            values = list(self.tree.item(item, 'values'))
            values[2] = f"{random.uniform(0, 5):.1f}"  # Random CPU%
            self.tree.item(item, values=values)

class SystemInfo(Window):
    """System Information window"""
    def __init__(self, parent):
        super().__init__(parent, "⚙️ System Information", 600, 400)
        
        info_text = Text(self.content_frame, font=('Courier', 10))
        info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        info = """=== GNU/Koopa System Information ===

System: GNU/Koopa 1.0.x [Beta]
Kernel: koopa-kernel-5.19.0
Architecture: x86_64
Hostname: shellstation
Uptime: 42 days, 13:37:00

Memory: 8192 MB Total
  Used: 2456 MB
  Free: 5736 MB
  
CPU: Koopa Shell Processor
  Cores: 4
  Speed: 3.2 GHz
  
Graphics: Switch 2 GPU Compatible
  Driver: koopa-gpu 2.0
  Memory: 4096 MB
  
Storage:
  /dev/kda1: 256 GB (42 GB used)
  
Network:
  eth0: 192.168.1.42
  wlan0: Not configured
  
Desktop Environment: KDE (Koopa Desktop Environment)
Window Manager: kwm (Koopa Window Manager)
Shell: ksh (Koopa Shell) 2.0
Gaming Mode: Switch 2 Interface Available

Shell Technology: Powered by 🐢"""
        
        info_text.insert('1.0', info)
        info_text.config(state='disabled')

class GNUKoopaOS:
    """Main OS Desktop"""
    def __init__(self, root):
        self.root = root
        self.root.title("GNU/Koopa OS 1.0.x [Beta]")
        self.root.geometry("1024x768")
        self.root.configure(bg='#4a4a4a')
        
        # Virtual file system
        self.fs = VirtualFileSystem()
        
        # Window list
        self.windows = []
        
        # Create desktop
        self.create_desktop()
        self.create_panel()
        
        # Start clock
        self.update_clock()

    def create_panel(self):
        """Create top panel"""
        panel = Frame(self.root, bg='#b0b0b0', height=40)
        panel.pack(fill=tk.X)
        panel.pack_propagate(False)
        
        # Shell menu
        self.shell_btn = Button(panel, text="🐢 Shell", bg='#c0c0c0',
                               font=('Arial', 10, 'bold'), command=self.show_app_menu)
        self.shell_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Quick launch
        Button(panel, text="🎮 Gaming", bg='#00d4aa', fg='white',
               font=('Arial', 10, 'bold'),
               command=lambda: Switch2Mode(self.root, self.fs)).pack(side=tk.LEFT, padx=5)
        Button(panel, text="📁 Files", bg='#c0c0c0',
               command=lambda: FileManager(self.root, self.fs)).pack(side=tk.LEFT, padx=5)
        Button(panel, text="🐢 Terminal", bg='#c0c0c0',
               command=lambda: Terminal(self.root, self.fs)).pack(side=tk.LEFT, padx=5)
        
        # Clock
        self.clock_label = Label(panel, text="", bg='#b0b0b0', font=('Courier', 10, 'bold'))
        self.clock_label.pack(side=tk.RIGHT, padx=10)

    def create_desktop(self):
        """Create desktop with icons"""
        desktop = Frame(self.root, bg='#4a4a4a')
        desktop.pack(fill=tk.BOTH, expand=True)
        
        # Desktop background pattern
        canvas = Canvas(desktop, bg='#4a4a4a', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create crosshatch pattern
        for i in range(0, 1024, 4):
            canvas.create_line(i, 0, i, 768, fill='#5a5a5a', width=1)
        for i in range(0, 768, 4):
            canvas.create_line(0, i, 1024, i, fill='#5a5a5a', width=1)
        
        # Desktop text
        canvas.create_text(512, 300, text="GNU/Koopa", fill='#333333',
                          font=('Courier', 48, 'bold'))
        canvas.create_text(512, 340, text="1.0.x [Beta]", fill='#333333',
                          font=('Courier', 24))
        canvas.create_text(512, 370, text="🐢 Powered by Shell Technology",
                          fill='#333333', font=('Arial', 12))
        
        # Desktop icons
        self.create_desktop_icons(canvas)

    def create_desktop_icons(self, canvas):
        """Create desktop icon buttons"""
        icons = [
            ("Switch 2\nMode", "🎮", 50, 50, lambda: Switch2Mode(self.root, self.fs)),
            ("Terminal", "🐢", 50, 160, lambda: Terminal(self.root, self.fs)),
            ("File\nManager", "📁", 50, 270, lambda: FileManager(self.root, self.fs)),
            ("Text\nEditor", "📝", 50, 380, lambda: TextEditor(self.root, self.fs, '/home/user', 'untitled.txt', '')),
            ("System\nInfo", "⚙️", 160, 50, lambda: SystemInfo(self.root)),
            ("RetroArch", "🕹️", 160, 160, self.open_retroarch),
            ("Process\nManager", "📊", 160, 270, lambda: ProcessManager(self.root))
        ]
        
        for name, icon, x, y, command in icons:
            # Create icon frame
            icon_frame = Frame(canvas, bg='#4a4a4a', width=80, height=90)
            icon_frame.place(x=x, y=y)
            
            # Icon button
            btn = Button(icon_frame, text=f"{icon}\n{name}", bg='#4a4a4a',
                        fg='white', font=('Arial', 10), bd=0,
                        activebackground='#00d4aa', command=command,
                        width=8, height=4)
            btn.pack()

    def open_retroarch(self):
        """Open RetroArch"""
        Switch2Mode(self.root, self.fs).open_retroarch()

    def show_app_menu(self):
        """Show application menu"""
        menu = Menu(self.root, tearoff=0)
        
        # Gaming submenu
        gaming_menu = Menu(menu, tearoff=0)
        gaming_menu.add_command(label="🎮 Switch 2 Mode",
                               command=lambda: Switch2Mode(self.root, self.fs))
        gaming_menu.add_command(label="🕹️ RetroArch",
                               command=self.open_retroarch)
        menu.add_cascade(label="Gaming", menu=gaming_menu)
        
        # System submenu
        system_menu = Menu(menu, tearoff=0)
        system_menu.add_command(label="🐢 Terminal",
                               command=lambda: Terminal(self.root, self.fs))
        system_menu.add_command(label="📁 File Manager",
                               command=lambda: FileManager(self.root, self.fs))
        system_menu.add_command(label="📝 Text Editor",
                               command=lambda: TextEditor(self.root, self.fs, '/home/user', 'untitled.txt', ''))
        system_menu.add_command(label="📊 Process Manager",
                               command=lambda: ProcessManager(self.root))
        system_menu.add_command(label="⚙️ System Info",
                               command=lambda: SystemInfo(self.root))
        menu.add_cascade(label="System", menu=system_menu)
        
        menu.add_separator()
        menu.add_command(label="About", command=self.show_about)
        menu.add_command(label="Logout", command=self.logout)
        
        try:
            x = self.shell_btn.winfo_rootx()
            y = self.shell_btn.winfo_rooty() + self.shell_btn.winfo_height()
            menu.post(x, y)
        except:
            pass

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About GNU/Koopa",
                          "GNU/Koopa OS 1.0.x [Beta]\n\n"
                          "Powered by Shell Technology 🐢\n\n"
                          "Copyright (c) 2025 The Koopa Project\n\n"
                          "A fully functional desktop environment\n"
                          "with gaming capabilities")

    def logout(self):
        """Logout confirmation"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.quit()

    def update_clock(self):
        """Update clock display"""
        self.clock_label.config(text=datetime.now().strftime("%a %b %d %H:%M:%S"))
        self.root.after(1000, self.update_clock)

if __name__ == "__main__":
    root = tk.Tk()
    app = GNUKoopaOS(root)
    root.mainloop()
