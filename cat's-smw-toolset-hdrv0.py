import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import struct
import binascii
from PIL import Image, ImageTk, ImageDraw
import numpy as np

class SMWRomHacker:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Super Mario World ROM Hacking Toolset 1.0")
        self.root.geometry("1200x800")
        self.rom_data = None
        self.rom_path = None
        self.tile_cache = {}
        
        # Create main interface
        self.create_menu()
        self.create_main_interface()
        
    def create_menu(self):
        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open ROM", command=self.open_rom)
        file_menu.add_command(label="Save ROM", command=self.save_rom, state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Level Editor", command=self.open_level_editor)
        edit_menu.add_command(label="Graphics Editor", command=self.open_graphics_editor)
        edit_menu.add_command(label="Map Editor", command=self.open_map_editor)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Decompile", command=self.decompile_rom)
        tools_menu.add_command(label="Hex Editor", command=self.open_hex_editor)
        tools_menu.add_command(label="Palette Editor", command=self.open_palette_editor)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_main_interface(self):
        # Create main paned window
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel for ROM info and navigation
        left_frame = ttk.Frame(main_pane, width=200)
        main_pane.add(left_frame, weight=1)
        
        # ROM info section
        rom_info_frame = ttk.LabelFrame(left_frame, text="ROM Information", padding=5)
        rom_info_frame.pack(fill=tk.X, pady=5)
        
        self.rom_info_text = tk.Text(rom_info_frame, height=8, width=25)
        self.rom_info_text.pack(fill=tk.X)
        self.rom_info_text.insert("1.0", "No ROM loaded")
        self.rom_info_text.config(state=tk.DISABLED)
        
        # Navigation tree
        nav_frame = ttk.LabelFrame(left_frame, text="Navigation", padding=5)
        nav_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.nav_tree = ttk.Treeview(nav_frame)
        self.nav_tree.pack(fill=tk.BOTH, expand=True)
        self.nav_tree.heading("#0", text="ROM Structure")
        
        # Right panel for content
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)
        
        # Notebook for different editors
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Welcome tab
        welcome_frame = ttk.Frame(self.notebook)
        self.notebook.add(welcome_frame, text="Welcome")
        
        welcome_text = """
        Universal Super Mario World ROM Hacking Toolset 1.0
        
        Features:
        - ROM decompilation and analysis
        - Level editor with visual interface
        - Graphics editor with palette support
        - Map editor for overworld design
        - Hex editor for advanced modifications
        
        To get started, open a Super Mario World ROM file.
        """
        
        welcome_label = tk.Label(welcome_frame, text=welcome_text, justify=tk.LEFT)
        welcome_label.pack(padx=10, pady=10)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_rom(self):
        file_path = filedialog.askopenfilename(
            title="Open Super Mario World ROM",
            filetypes=[
                ("SNES ROM files", "*.smc *.sfc"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.rom_data = bytearray(f.read())
                
                self.rom_path = file_path
                self.update_rom_info()
                self.enable_editing()
                self.status_bar.config(text=f"Loaded: {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM: {str(e)}")
    
    def update_rom_info(self):
        self.rom_info_text.config(state=tk.NORMAL)
        self.rom_info_text.delete("1.0", tk.END)
        
        if self.rom_data:
            # Extract basic ROM info (simplified)
            rom_size = len(self.rom_data)
            header = self.rom_data[0:50]
            
            info_text = f"ROM Size: {rom_size} bytes\n"
            info_text += f"Header: {binascii.hexlify(header).decode('utf-8')[:20]}...\n"
            info_text += f"Checksum: {self.calculate_checksum()}\n"
            
            # Try to detect if it's a Super Mario World ROM
            if self.detect_smw():
                info_text += "Detected: Super Mario World ROM\n"
                info_text += self.extract_smw_info()
            else:
                info_text += "Warning: May not be a Super Mario World ROM\n"
            
            self.rom_info_text.insert("1.0", info_text)
        
        self.rom_info_text.config(state=tk.DISABLED)
    
    def calculate_checksum(self):
        # Simplified checksum calculation
        if not self.rom_data:
            return "N/A"
        
        checksum = sum(self.rom_data) & 0xFFFF
        return f"0x{checksum:04X}"
    
    def detect_smw(self):
        # Simple detection based on known ROM characteristics
        if not self.rom_data or len(self.rom_data) < 0x8000:
            return False
        
        # Check for known SMW header data
        try:
            # Look for "SUPER MARIOWORLD" in header
            title = self.rom_data[0x7FC0:0x7FD5].decode('ascii', errors='ignore')
            return "MARIO" in title
        except:
            return False
    
    def extract_smw_info(self):
        if not self.rom_data or len(self.rom_data) < 0x8000:
            return ""
        
        try:
            # Extract title from header
            title = self.rom_data[0x7FC0:0x7FD5].decode('ascii').strip()
            maker = self.rom_data[0x7FD5:0x7FDB].decode('ascii').strip()
            rom_type = self.rom_data[0x7FD6]
            
            info = f"Title: {title}\n"
            info += f"Maker: {maker}\n"
            info += f"ROM Type: 0x{rom_type:02X}\n"
            
            return info
        except:
            return "Could not extract detailed info\n"
    
    def enable_editing(self):
        # Enable menu items that require a loaded ROM
        self.root.nametowidget("!menu").entryconfig("File", state="normal")
        self.root.nametowidget("!menu").entryconfig("Edit", state="normal")
        self.root.nametowidget("!menu").entryconfig("Tools", state="normal")
        
        # Enable Save option
        file_menu = self.root.nametowidget("!menu").entrycget(0, "menu")
        self.root.nametowidget(file_menu).entryconfig(1, state="normal")
    
    def save_rom(self):
        if not self.rom_data:
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save ROM As",
            defaultextension=".smc",
            filetypes=[("SNES ROM files", "*.smc *.sfc")]
        )
        
        if file_path:
            try:
                with open(file_path, "wb") as f:
                    f.write(self.rom_data)
                
                self.status_bar.config(text=f"Saved: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", "ROM saved successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save ROM: {str(e)}")
    
    def open_level_editor(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create level editor tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Level Editor":
                self.notebook.select(i)
                return
        
        level_frame = ttk.Frame(self.notebook)
        self.notebook.add(level_frame, text="Level Editor")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Level editor content
        level_label = tk.Label(level_frame, text="Level Editor - Under Development")
        level_label.pack(padx=10, pady=10)
        
        # Simulated level grid
        canvas_frame = ttk.Frame(level_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg="white", width=600, height=400)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw a simple grid
        for x in range(0, 600, 16):
            canvas.create_line(x, 0, x, 400, fill="lightgray")
        for y in range(0, 400, 16):
            canvas.create_line(0, y, 600, y, fill="lightgray")
    
    def open_graphics_editor(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create graphics editor tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Graphics Editor":
                self.notebook.select(i)
                return
        
        graphics_frame = ttk.Frame(self.notebook)
        self.notebook.add(graphics_frame, text="Graphics Editor")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Graphics editor content
        graphics_label = tk.Label(graphics_frame, text="Graphics Editor - Under Development")
        graphics_label.pack(padx=10, pady=10)
        
        # Simulated graphics viewer
        canvas_frame = ttk.Frame(graphics_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a simple 8x8 tile pattern
        img = Image.new("RGB", (128, 128), "white")
        draw = ImageDraw.Draw(img)
        
        # Draw some patterns to simulate tiles
        for y in range(0, 128, 16):
            for x in range(0, 128, 16):
                draw.rectangle([x, y, x+15, y+15], outline="black")
                draw.rectangle([x+2, y+2, x+6, y+6], fill="red")
                draw.rectangle([x+9, y+9, x+13, y+13], fill="blue")
        
        self.graphics_img = ImageTk.PhotoImage(img)
        graphics_canvas = tk.Canvas(canvas_frame, width=128, height=128)
        graphics_canvas.pack()
        graphics_canvas.create_image(0, 0, anchor=tk.NW, image=self.graphics_img)
    
    def open_map_editor(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create map editor tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Map Editor":
                self.notebook.select(i)
                return
        
        map_frame = ttk.Frame(self.notebook)
        self.notebook.add(map_frame, text="Map Editor")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Map editor content
        map_label = tk.Label(map_frame, text="Map Editor - Under Development")
        map_label.pack(padx=10, pady=10)
        
        # Simulated overworld map
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg="lightblue", width=600, height=400)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw some simple map elements
        canvas.create_oval(50, 50, 100, 100, fill="green", outline="darkgreen")
        canvas.create_oval(150, 80, 200, 130, fill="green", outline="darkgreen")
        canvas.create_oval(300, 120, 350, 170, fill="green", outline="darkgreen")
        canvas.create_oval(450, 70, 500, 120, fill="green", outline="darkgreen")
        
        # Draw paths
        canvas.create_line(75, 75, 175, 105, fill="brown", width=3)
        canvas.create_line(175, 105, 325, 145, fill="brown", width=3)
        canvas.create_line(325, 145, 475, 95, fill="brown", width=3)
    
    def decompile_rom(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create decompiler tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Decompiler":
                self.notebook.select(i)
                return
        
        decompile_frame = ttk.Frame(self.notebook)
        self.notebook.add(decompile_frame, text="Decompiler")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Decompiler content
        decompile_label = tk.Label(decompile_frame, text="ROM Decompilation Results")
        decompile_label.pack(padx=10, pady=5)
        
        # Text area for decompilation output
        text_frame = ttk.Frame(decompile_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # Simulate decompilation output
        decompilation_text = self.simulate_decompilation()
        text_area.insert(tk.END, decompilation_text)
        text_area.config(state=tk.DISABLED)
    
    def simulate_decompilation(self):
        # This is a simplified simulation of decompilation output
        output = "ROM Decompilation Analysis\n"
        output += "=" * 40 + "\n\n"
        
        output += "Header Analysis:\n"
        output += f"  ROM Size: {len(self.rom_data)} bytes\n"
        output += "  ROM Type: LoROM\n"
        output += "  Calculated Checksum: " + self.calculate_checksum() + "\n\n"
        
        output += "Code Segments Identified:\n"
        output += "  Bank $80: Main game code (12,288 bytes)\n"
        output += "  Bank $81: Game engine routines (8,192 bytes)\n"
        output += "  Bank $82: Level loading routines (4,096 bytes)\n\n"
        
        output += "Data Segments Identified:\n"
        output += "  Bank $00: Level data (16,384 bytes)\n"
        output += "  Bank $01: Graphics data (24,576 bytes)\n"
        output += "  Bank $02: Map data (8,192 bytes)\n"
        output += "  Bank $03: Sound data (4,096 bytes)\n\n"
        
        output += "Functions Identified:\n"
        output += "  $808000: Main game loop\n"
        output += "  $808200: Player physics handler\n"
        output += "  $808500: Enemy behavior routines\n"
        output += "  $808800: Object collision detection\n"
        output += "  $808A00: Level loading routine\n\n"
        
        output += "Note: This is a simulated decompilation for demonstration purposes.\n"
        output += "A real decompiler would provide more detailed analysis of the ROM structure."
        
        return output
    
    def open_hex_editor(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create hex editor tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Hex Editor":
                self.notebook.select(i)
                return
        
        hex_frame = ttk.Frame(self.notebook)
        self.notebook.add(hex_frame, text="Hex Editor")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Hex editor content
        hex_label = tk.Label(hex_frame, text="Hex Editor - First 1024 bytes of ROM")
        hex_label.pack(padx=10, pady=5)
        
        # Text area for hex dump
        text_frame = ttk.Frame(hex_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.NONE, font=("Courier", 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        
        # Generate hex dump
        hex_dump = self.generate_hex_dump(1024)
        text_area.insert(tk.END, hex_dump)
        text_area.config(state=tk.DISABLED)
    
    def generate_hex_dump(self, length):
        if not self.rom_data:
            return "No ROM data available"
        
        # Generate a formatted hex dump
        output = "Offset   00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F   ASCII\n"
        output += "------   -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --   -----\n"
        
        for i in range(0, min(length, len(self.rom_data)), 16):
            # Offset
            output += f"{i:06X}   "
            
            # Hex bytes
            hex_bytes = []
            ascii_chars = []
            for j in range(16):
                if i + j < len(self.rom_data):
                    byte = self.rom_data[i + j]
                    hex_bytes.append(f"{byte:02X}")
                    
                    # ASCII representation (printable characters only)
                    if 32 <= byte <= 126:
                        ascii_chars.append(chr(byte))
                    else:
                        ascii_chars.append(".")
                else:
                    hex_bytes.append("  ")
                    ascii_chars.append(" ")
            
            output += " ".join(hex_bytes) + "   "
            output += "".join(ascii_chars) + "\n"
        
        return output
    
    def open_palette_editor(self):
        if not self.rom_data:
            messagebox.showwarning("No ROM", "Please open a ROM first")
            return
        
        # Create palette editor tab if it doesn't exist
        for i in range(self.notebook.index("end")):
            if self.notebook.tab(i, "text") == "Palette Editor":
                self.notebook.select(i)
                return
        
        palette_frame = ttk.Frame(self.notebook)
        self.notebook.add(palette_frame, text="Palette Editor")
        self.notebook.select(self.notebook.index("end") - 1)
        
        # Palette editor content
        palette_label = tk.Label(palette_frame, text="Palette Editor - Under Development")
        palette_label.pack(padx=10, pady=10)
        
        # Simulated palette display
        canvas_frame = ttk.Frame(palette_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(canvas_frame, bg="white", width=400, height=300)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw some color swatches
        colors = ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", 
                 "#FFFF00", "#FF00FF", "#00FFFF", "#800000", "#008000",
                 "#000080", "#808000", "#800080", "#008080", "#808080", "#C0C0C0"]
        
        for i, color in enumerate(colors):
            x = (i % 8) * 50 + 10
            y = (i // 8) * 50 + 10
            canvas.create_rectangle(x, y, x+40, y+40, fill=color, outline="black")
    
    def show_about(self):
        about_text = """
        Universal Super Mario World ROM Hacking Toolset 1.0
        
        A comprehensive tool for hacking Super Mario World ROMs
        
        Features:
        - ROM loading and saving
        - Level editing capabilities
        - Graphics editing with palette support
        - Map editor for overworld design
        - ROM decompilation and analysis
        - Hex editor for advanced modifications
        
        This is a demonstration tool created with Python and Tkinter.
        """
        
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = SMWRomHacker(root)
    root.mainloop()
