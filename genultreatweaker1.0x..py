import tkinter as tk
from tkinter import filedialog, messagebox
import os
import struct

try:
    from capstone import *
    CAPSTONE_AVAILABLE = True
except ImportError:
    CAPSTONE_AVAILABLE = False

class SM64AssetDumper:
    # Define ROM sections for assets (non-ASM data)
    SECTIONS = {
        "textures": (0x100000, 0x200000, "bin"),     # Texture data
        "models": (0x200000, 0x300000, "bin"),       # 3D model data
        "audio": (0x300000, 0x400000, "bin"),        # Audio data
        "levels": (0x400000, 0x500000, "bin"),       # Level data
        "text": (0x500000, 0x600000, "bin"),         # Text data
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Universal Mario 64 ROMHACK ASSET DUMPER 1.0")
        self.root.geometry("600x400")
        self.rom_path = None
        
        # GUI Elements
        self.label = tk.Label(root, text="Select a Super Mario 64 .z64 ROM file to dump assets")
        self.label.pack(pady=10)
        
        self.select_button = tk.Button(root, text="Select ROM", command=self.select_rom)
        self.select_button.pack(pady=5)
        
        self.rom_label = tk.Label(root, text="No ROM selected")
        self.rom_label.pack(pady=5)
        
        self.dump_asm_button = tk.Button(root, text="Dump ASM", command=self.dump_asm, state="disabled")
        self.dump_asm_button.pack(pady=5)
        
        self.dump_assets_button = tk.Button(root, text="Dump Assets", command=self.dump_assets, state="disabled")
        self.dump_assets_button.pack(pady=5)
        
        self.status = tk.Label(root, text="Status: Idle")
        self.status.pack(pady=10)
        
        self.output_text = tk.Text(root, height=10, width=60)
        self.output_text.pack(pady=10)
        
        # Warn about hypothetical offsets and ASM behavior
        self.output_text.insert(tk.END, "Note: ASM dump processes the entire ROM. Asset offsets are hypothetical; consult SM64 documentation for accuracy.\n")
        if not CAPSTONE_AVAILABLE:
            self.output_text.insert(tk.END, "Error: Capstone library not found. Please install it using 'pip install capstone' to dump ASM.\n")
            self.dump_asm_button.config(state="disabled")

    def select_rom(self):
        self.rom_path = filedialog.askopenfilename(filetypes=[("Z64 ROM files", "*.z64")])
        if self.rom_path:
            # Validate ROM file
            try:
                with open(self.rom_path, "rb") as rom_file:
                    rom_data = rom_file.read()
                if len(rom_data) < 8 * 1024 * 1024:  # Less than 8MB
                    messagebox.showerror("Error", "Invalid ROM: File is too small for a standard SM64 ROM (expected ~8MB).")
                    self.rom_path = None
                    return
                # Check N64 header (first 4 bytes should be 0x80371240 for .z64)
                header = struct.unpack(">I", rom_data[:4])[0]
                if header != 0x80371240:
                    messagebox.showwarning("Warning", "ROM header does not match expected SM64 format. Proceed with caution.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to validate ROM: {str(e)}")
                self.rom_path = None
                return
                
            self.rom_label.config(text=f"Selected: {os.path.basename(self.rom_path)}")
            self.dump_assets_button.config(state="normal")
            if CAPSTONE_AVAILABLE:
                self.dump_asm_button.config(state="normal")
            self.status.config(text="Status: ROM loaded, ready to dump")
        else:
            self.rom_label.config(text="No ROM selected")
            self.dump_asm_button.config(state="disabled")
            self.dump_assets_button.config(state="disabled")
            self.status.config(text="Status: Idle")

    def dump_asm(self):
        if not self.rom_path:
            messagebox.showerror("Error", "No ROM file selected!")
            return
        
        if not CAPSTONE_AVAILABLE:
            messagebox.showerror("Error", "Capstone library not installed. Install it using 'pip install capstone'.")
            return
        
        self.status.config(text="Status: Dumping ASM...")
        self.output_text.delete(1.0, tk.END)
        
        try:
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                self.status.config(text="Status: Output directory not selected")
                return
            if not os.access(output_dir, os.W_OK):
                self.status.config(text="Status: No write permission for output directory")
                messagebox.showerror("Error", "No write permission for selected directory.")
                return
                
            with open(self.rom_path, "rb") as rom_file:
                rom_data = rom_file.read()
                
            # Dump entire ROM as ASM
            self.output_text.insert(tk.END, "Dumping entire ROM as ASM...\n")
            try:
                md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_BIG_ENDIAN)
                output_file = os.path.join(output_dir, "rom.asm")
                with open(output_file, "w") as asm_file:
                    # Process ROM in chunks to handle large files
                    chunk_size = 0x100000  # 1MB chunks
                    for offset in range(0, len(rom_data), chunk_size):
                        chunk = rom_data[offset:offset + chunk_size]
                        instructions_found = False
                        for i in md.disasm(chunk, offset):
                            asm_file.write(f"0x{i.address:08X}:\t{i.mnemonic}\t{i.op_str}\n")
                            instructions_found = True
                        if not instructions_found:
                            self.output_text.insert(tk.END, f"Warning: No valid instructions in chunk at offset 0x{offset:08X}. May contain data.\n")
                self.output_text.insert(tk.END, "Saved rom.asm\n")
            except Exception as e:
                self.output_text.insert(tk.END, f"Error dumping ASM: {str(e)}\n")
                raise
                
            self.status.config(text="Status: ASM dump complete")
            messagebox.showinfo("Success", "Entire ROM dumped as ASM successfully")
                
        except Exception as e:
            self.status.config(text="Status: Error during ASM dump")
            self.output_text.insert(tk.END, f"Error: {str(e)}\n")
            messagebox.showerror("Error", f"Failed to dump ASM: {str(e)}")

    def dump_assets(self):
        if not self.rom_path:
            messagebox.showerror("Error", "No ROM file selected!")
            return
        
        self.status.config(text="Status: Dumping assets...")
        self.output_text.delete(1.0, tk.END)
        
        try:
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                self.status.config(text="Status: Output directory not selected")
                return
            if not os.access(output_dir, os.W_OK):
                self.status.config(text="Status: No write permission for output directory")
                messagebox.showerror("Error", "No write permission for selected directory.")
                return
                
            with open(self.rom_path, "rb") as rom_file:
                rom_data = rom_file.read()
                
            # Dump all asset sections
            for name, (start, end, typ) in self.SECTIONS.items():
                if typ != "bin":
                    continue
                if end > len(rom_data):
                    self.output_text.insert(tk.END, f"Warning: Section {name} exceeds ROM size, skipping.\n")
                    continue
                self.output_text.insert(tk.END, f"Dumping {name}...\n")
                data = rom_data[start:end]
                try:
                    output_file = os.path.join(output_dir, f"{name}.bin")
                    with open(output_file, "wb") as asset_file:
                        asset_file.write(data)
                    self.output_text.insert(tk.END, f"Saved {name}.bin\n")
                except Exception as e:
                    self.output_text.insert(tk.END, f"Error dumping {name}: {str(e)}\n")
                
            self.status.config(text="Status: Asset dump complete")
            messagebox.showinfo("Success", "Asset sections dumped successfully")
                
        except Exception as e:
            self.status.config(text="Status: Error during asset dump")
            self.output_text.insert(tk.END, f"Error: {str(e)}\n")
            messagebox.showerror("Error", f"Failed to dump assets: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SM64AssetDumper(root)
    root.mainloop()
