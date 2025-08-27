import tkinter as tk
from tkinter import ttk
import webbrowser
import subprocess

# Main class for Flames NX OS simulation
class FlamesNX:
    def __init__(self, root):
        self.root = root
        self.root.title("Flames NX")
        self.root.geometry("800x480")  # Simulate console screen size
        self.root.configure(bg='black')
        
        # Apply Switch 2-inspired theme
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Base theme
        self.style.configure('TFrame', background='black')
        self.style.configure('TLabel', background='black', foreground='white', font=('Arial', 12))
        self.style.configure('TButton', background='#333333', foreground='white', font=('Arial', 14, 'bold'), borderwidth=0)
        self.style.map('TButton', background=[('active', '#555555')])
        
        # Custom colors for multi-colored selectors (inspired by Switch 2)
        self.colors = {
            'terminal': 'green',
            'copilot': 'blue',
            'browser': 'red',
            'youtube': 'teal'
        }
        
        # Home screen frame (grid-like layout)
        self.home_frame = ttk.Frame(self.root, padding=20)
        self.home_frame.pack(fill=tk.BOTH, expand=True)
        
        # Welcome label
        welcome_label = ttk.Label(self.home_frame, text="Welcome to Flames NX", font=('Arial', 18, 'bold'))
        welcome_label.pack(pady=20)
        
        # App grid
        self.create_app_buttons()

    def create_app_buttons(self):
        # App buttons in a grid, rounded style simulated with padding
        apps = [
            ("Terminal", self.open_terminal, self.colors['terminal']),
            ("Copilot", self.open_copilot, self.colors['copilot']),
            ("Mario Browser", self.open_mario_browser, self.colors['browser']),
            ("YouTube", self.open_youtube, self.colors['youtube'])
        ]
        
        row_frame = ttk.Frame(self.home_frame)
        row_frame.pack(pady=10)
        
        for i, (name, command, color) in enumerate(apps):
            btn = ttk.Button(row_frame, text=name, command=command, width=15)
            btn.pack(side=tk.LEFT, padx=10)
            # Apply color accent (simulating multi-colored circles)
            self.style.configure(f'{name}.TButton', background=color, foreground='white')
            self.style.map(f'{name}.TButton', background=[('active', color)])
            btn.configure(style=f'{name}.TButton')
    
    def open_terminal(self):
        # Simulate a BSD-like terminal in a new window
        term_window = tk.Toplevel(self.root)
        term_window.title("Flames NX Terminal")
        term_window.geometry("600x400")
        term_window.configure(bg='black')
        
        output_text = tk.Text(term_window, bg='black', fg='green', font=('Courier', 12))
        output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        input_frame = ttk.Frame(term_window)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        input_entry = ttk.Entry(input_frame, font=('Courier', 12))
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def execute_command(event):
            cmd = input_entry.get()
            input_entry.delete(0, tk.END)
            output_text.insert(tk.END, f"$ {cmd}\n")
            # Simulate simple BSD-like commands
            if cmd == "ls":
                output_text.insert(tk.END, "Desktop Documents Downloads\n")
            elif cmd == "pwd":
                output_text.insert(tk.END, "/home/user\n")
            elif cmd.startswith("echo "):
                output_text.insert(tk.END, f"{cmd[5:]}\n")
            else:
                output_text.insert(tk.END, "Command not found\n")
            output_text.see(tk.END)
        
        input_entry.bind("<Return>", execute_command)
        output_text.insert(tk.END, "Flames NX Terminal (BSD-like simulation)\nType commands like 'ls', 'pwd', 'echo'\n")

    def open_copilot(self):
        # Open Microsoft Copilot in default browser
        webbrowser.open("https://copilot.microsoft.com")

    def open_mario_browser(self):
        # Themed browser opening to a Mario page
        webbrowser.open("https://www.nintendo.com/us/store/characters/mario/")

    def open_youtube(self):
        # Open YouTube
        webbrowser.open("https://www.youtube.com")

# Run the OS simulation
if __name__ == "__main__":
    root = tk.Tk()
    app = FlamesNX(root)
    root.mainloop()
