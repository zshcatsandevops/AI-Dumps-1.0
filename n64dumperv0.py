import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import struct

try:
    from capstone import *
    CAPSTONE_AVAILABLE = True
except ImportError:
    CAPSTONE_AVAILABLE = False

class UniversalN64Dumper:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal N64 ROM Dumper 2.0")
        self.root.geometry("700x500")
        self.rom_path = None
        self.rom_data = None
        self.rom_format = None
        
        # GUI Setup
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title = tk.Label(self.root, text="Universal N64 ROM Dumper", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # ROM Selection Frame
        select_frame = tk.Frame(self.root)
        select_frame.pack(pady=10)
        
        self.select_button = tk.Button(select_frame, text="Select N64 ROM", command=self.select_rom, width=20)
        self.select_button.pack(side=tk.LEFT, padx=5)
        
        # ROM Info
        self.rom_info_label = tk.Label(self.root, text="No ROM selected", fg="gray")
        self.rom_info_label.pack(pady=5)
        
        # ROM Details
        self.details_frame = tk.LabelFrame(self.root, text="ROM Information", padx=10, pady=10)
        self.details_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.details_text = tk.Text(self.details_frame, height=6, width=70, state=tk.DISABLED)
        self.details_text.pack()
        
        # Action Buttons Frame
        action_frame = tk.LabelFrame(self.root, text="Dump Options", padx=10, pady=10)
        action_frame.pack(pady=10, padx=20, fill=tk.X)
        
        button_row1 = tk.Frame(action_frame)
        button_row1.pack(pady=5)
        
        self.dump_full_button = tk.Button(button_row1, text="Dump Full ROM", command=self.dump_full_rom, state="disabled", width=20)
        self.dump_full_button.pack(side=tk.LEFT, padx=5)
        
        self.dump_asm_button = tk.Button(button_row1, text="Dump as ASM", command=self.dump_asm, state="disabled", width=20)
        self.dump_asm_button.pack(side=tk.LEFT, padx=5)
        
        button_row2 = tk.Frame(action_frame)
        button_row2.pack(pady=5)
        
        self.dump_sections_button = tk.Button(button_row2, text="Dump by Sections", command=self.dump_sections, state="disabled", width=20)
        self.dump_sections_button.pack(side=tk.LEFT, padx=5)
        
        self.convert_format_button = tk.Button(button_row2, text="Convert Format", command=self.convert_format, state="disabled", width=20)
        self.convert_format_button.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = tk.Label(self.root, text="Status: Ready", fg="green")
        self.status_label.pack(pady=10)
        
        # Progress Bar
        self.progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress.pack(pady=5)
        
        # Output Log
        log_frame = tk.LabelFrame(self.root, text="Output Log", padx=10, pady=10)
        log_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        self.output_text = tk.Text(log_frame, height=8, width=70)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.log("Universal N64 ROM Dumper initialized")
        self.log("Supports: .z64, .n64, .v64 formats from any region")
        if not CAPSTONE_AVAILABLE:
            self.log("Warning: Capstone not installed. ASM dumping disabled.")
            self.log("Install with: pip install capstone")

    def log(self, message):
        self.output_text.insert(tk.END, f"{message}\n")
        self.output_text.see(tk.END)
        self.root.update()

    def select_rom(self):
        file_path = filedialog.askopenfilename(
            title="Select N64 ROM",
            filetypes=[
                ("N64 ROM files", "*.z64 *.n64 *.v64"),
                ("Z64 format", "*.z64"),
                ("N64 format", "*.n64"),
                ("V64 format", "*.v64"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_rom(file_path)

    def load_rom(self, file_path):
        try:
            self.status_label.config(text="Status: Loading ROM...", fg="orange")
            self.progress['value'] = 0
            
            # Read ROM
            with open(file_path, "rb") as f:
                self.rom_data = f.read()
            
            self.rom_path = file_path
            rom_size = len(self.rom_data)
            
            # Detect format
            self.detect_format()
            
            # Convert to z64 format internally for processing
            if self.rom_format != "z64":
                self.log(f"Converting from {self.rom_format} to z64 format internally...")
                self.rom_data = self.convert_to_z64(self.rom_data, self.rom_format)
            
            # Update UI
            self.rom_info_label.config(text=f"Loaded: {os.path.basename(file_path)} ({rom_size:,} bytes)", fg="black")
            
            # Display ROM info
            self.display_rom_info()
            
            # Enable buttons
            self.dump_full_button.config(state="normal")
            self.dump_sections_button.config(state="normal")
            self.convert_format_button.config(state="normal")
            if CAPSTONE_AVAILABLE:
                self.dump_asm_button.config(state="normal")
            
            self.status_label.config(text="Status: ROM loaded successfully", fg="green")
            self.progress['value'] = 100
            self.log(f"Successfully loaded: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ROM: {str(e)}")
            self.status_label.config(text="Status: Error loading ROM", fg="red")
            self.log(f"Error: {str(e)}")

    def detect_format(self):
        """Detect ROM format based on header bytes"""
        if len(self.rom_data) < 4:
            raise ValueError("ROM too small")
        
        header = struct.unpack(">I", self.rom_data[:4])[0]
        
        if header == 0x80371240:  # Z64 (big-endian)
            self.rom_format = "z64"
        elif header == 0x40123780:  # N64 (little-endian)
            self.rom_format = "n64"
        elif header == 0x37804012:  # V64 (byte-swapped)
            self.rom_format = "v64"
        else:
            # Try to guess based on common patterns
            self.rom_format = "unknown"
            self.log("Warning: Unknown ROM format, assuming z64")
            self.rom_format = "z64"

    def convert_to_z64(self, data, source_format):
        """Convert ROM data to z64 format"""
        if source_format == "n64":
            # Swap endianness (little to big)
            result = bytearray(len(data))
            for i in range(0, len(data), 4):
                if i + 3 < len(data):
                    result[i:i+4] = data[i:i+4][::-1]
            return bytes(result)
        elif source_format == "v64":
            # Byte swap pairs
            result = bytearray(len(data))
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    result[i] = data[i + 1]
                    result[i + 1] = data[i]
            return bytes(result)
        return data

    def display_rom_info(self):
        """Display ROM header information"""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        if len(self.rom_data) >= 0x40:
            # Parse header
            header = struct.unpack(">I", self.rom_data[:4])[0]
            clock_rate = struct.unpack(">I", self.rom_data[0x4:0x8])[0]
            program_counter = struct.unpack(">I", self.rom_data[0x8:0xC])[0]
            release = struct.unpack(">I", self.rom_data[0xC:0x10])[0]
            
            # Game title (0x20-0x33)
            title_bytes = self.rom_data[0x20:0x34]
            title = title_bytes.decode('ascii', errors='ignore').strip()
            
            # Game code (0x3B-0x3E)
            game_code = self.rom_data[0x3B:0x3F].decode('ascii', errors='ignore')
            
            # Region code
            region = self.rom_data[0x3E] if len(self.rom_data) > 0x3E else 0
            region_name = self.get_region_name(region)
            
            info = f"Format: {self.rom_format.upper()}\n"
            info += f"Title: {title}\n"
            info += f"Game Code: {game_code}\n"
            info += f"Region: {region_name} ({chr(region) if 32 <= region <= 126 else hex(region)})\n"
            info += f"Size: {len(self.rom_data):,} bytes ({len(self.rom_data) / (1024*1024):.1f} MB)\n"
            info += f"Header: 0x{header:08X}"
            
            self.details_text.insert(1.0, info)
        else:
            self.details_text.insert(1.0, "ROM too small to read header")
        
        self.details_text.config(state=tk.DISABLED)

    def get_region_name(self, code):
        """Get region name from code"""
        regions = {
            0x44: "Germany",
            0x45: "USA",
            0x46: "France",
            0x49: "Italy",
            0x4A: "Japan",
            0x50: "Europe",
            0x53: "Spain",
            0x55: "Australia",
            0x58: "Europe (X)",
            0x59: "Europe (Y)",
        }
        return regions.get(code, "Unknown")

    def dump_full_rom(self):
        """Dump the entire ROM as-is"""
        if not self.rom_data:
            return
        
        output_file = filedialog.asksaveasfilename(
            title="Save ROM dump as",
            defaultextension=".z64",
            filetypes=[
                ("Z64 ROM", "*.z64"),
                ("Binary file", "*.bin"),
                ("All files", "*.*")
            ]
        )
        
        if output_file:
            try:
                self.status_label.config(text="Status: Dumping ROM...", fg="orange")
                self.progress['value'] = 0
                
                with open(output_file, "wb") as f:
                    f.write(self.rom_data)
                
                self.progress['value'] = 100
                self.status_label.config(text="Status: ROM dumped successfully", fg="green")
                self.log(f"ROM dumped to: {output_file}")
                messagebox.showinfo("Success", f"ROM dumped successfully to:\n{output_file}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to dump ROM: {str(e)}")
                self.status_label.config(text="Status: Error dumping ROM", fg="red")
                self.log(f"Error: {str(e)}")

    def dump_sections(self):
        """Dump ROM in sections"""
        if not self.rom_data:
            return
        
        output_dir = filedialog.askdirectory(title="Select output directory for sections")
        if not output_dir:
            return
        
        try:
            self.status_label.config(text="Status: Dumping sections...", fg="orange")
            
            # Define sections (customizable)
            section_size = 1024 * 1024  # 1MB sections
            num_sections = (len(self.rom_data) + section_size - 1) // section_size
            
            for i in range(num_sections):
                self.progress['value'] = (i / num_sections) * 100
                start = i * section_size
                end = min(start + section_size, len(self.rom_data))
                
                section_data = self.rom_data[start:end]
                output_file = os.path.join(output_dir, f"section_{i:03d}_{start:08X}-{end:08X}.bin")
                
                with open(output_file, "wb") as f:
                    f.write(section_data)
                
                self.log(f"Dumped section {i+1}/{num_sections}: {os.path.basename(output_file)}")
            
            self.progress['value'] = 100
            self.status_label.config(text="Status: Sections dumped successfully", fg="green")
            messagebox.showinfo("Success", f"Dumped {num_sections} sections to:\n{output_dir}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to dump sections: {str(e)}")
            self.status_label.config(text="Status: Error dumping sections", fg="red")
            self.log(f"Error: {str(e)}")

    def dump_asm(self):
        """Dump ROM as MIPS assembly"""
        if not self.rom_data or not CAPSTONE_AVAILABLE:
            return
        
        output_file = filedialog.asksaveasfilename(
            title="Save ASM dump as",
            defaultextension=".asm",
            filetypes=[
                ("Assembly file", "*.asm"),
                ("Text file", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if output_file:
            try:
                self.status_label.config(text="Status: Disassembling ROM...", fg="orange")
                self.log("Starting MIPS disassembly...")
                
                md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_BIG_ENDIAN)
                
                with open(output_file, "w") as asm_file:
                    chunk_size = 0x10000  # 64KB chunks
                    total_chunks = (len(self.rom_data) + chunk_size - 1) // chunk_size
                    
                    for chunk_idx in range(total_chunks):
                        self.progress['value'] = (chunk_idx / total_chunks) * 100
                        offset = chunk_idx * chunk_size
                        chunk = self.rom_data[offset:offset + chunk_size]
                        
                        # Write section header
                        asm_file.write(f"\n; Section at 0x{offset:08X}\n")
                        asm_file.write(f"; {'='*50}\n\n")
                        
                        instruction_count = 0
                        for instr in md.disasm(chunk, offset):
                            asm_file.write(f"0x{instr.address:08X}:\t{instr.mnemonic}\t{instr.op_str}\n")
                            instruction_count += 1
                        
                        if instruction_count == 0:
                            # Write raw data if no instructions found
                            asm_file.write(f"; No valid MIPS instructions found in this chunk\n")
                            asm_file.write(f"; Raw data dump:\n")
                            for i in range(0, min(len(chunk), 256), 16):
                                hex_str = ' '.join(f"{b:02X}" for b in chunk[i:i+16])
                                asm_file.write(f"; 0x{offset+i:08X}: {hex_str}\n")
                        
                        self.log(f"Processed chunk {chunk_idx+1}/{total_chunks} ({instruction_count} instructions)")
                
                self.progress['value'] = 100
                self.status_label.config(text="Status: ASM dump complete", fg="green")
                self.log(f"ASM dumped to: {output_file}")
                messagebox.showinfo("Success", f"ASM dump completed:\n{output_file}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to dump ASM: {str(e)}")
                self.status_label.config(text="Status: Error dumping ASM", fg="red")
                self.log(f"Error: {str(e)}")

    def convert_format(self):
        """Convert ROM to different format"""
        if not self.rom_data:
            return
        
        # Ask for target format
        format_dialog = tk.Toplevel(self.root)
        format_dialog.title("Convert ROM Format")
        format_dialog.geometry("300x200")
        
        tk.Label(format_dialog, text="Select target format:").pack(pady=10)
        
        format_var = tk.StringVar(value="z64")
        formats = [("Z64 (Big-endian)", "z64"), 
                  ("N64 (Little-endian)", "n64"), 
                  ("V64 (Byte-swapped)", "v64")]
        
        for text, value in formats:
            tk.Radiobutton(format_dialog, text=text, variable=format_var, value=value).pack(anchor=tk.W, padx=20)
        
        def do_convert():
            target_format = format_var.get()
            format_dialog.destroy()
            
            output_file = filedialog.asksaveasfilename(
                title=f"Save as {target_format.upper()}",
                defaultextension=f".{target_format}",
                filetypes=[
                    (f"{target_format.upper()} ROM", f"*.{target_format}"),
                    ("All files", "*.*")
                ]
            )
            
            if output_file:
                try:
                    # Convert from z64 to target format
                    if target_format == "z64":
                        output_data = self.rom_data
                    elif target_format == "n64":
                        output_data = self.convert_from_z64_to_n64(self.rom_data)
                    elif target_format == "v64":
                        output_data = self.convert_from_z64_to_v64(self.rom_data)
                    else:
                        output_data = self.rom_data
                    
                    with open(output_file, "wb") as f:
                        f.write(output_data)
                    
                    self.log(f"Converted to {target_format.upper()}: {output_file}")
                    messagebox.showinfo("Success", f"ROM converted to {target_format.upper()} format")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Conversion failed: {str(e)}")
                    self.log(f"Conversion error: {str(e)}")
        
        tk.Button(format_dialog, text="Convert", command=do_convert).pack(pady=20)

    def convert_from_z64_to_n64(self, data):
        """Convert from z64 to n64 format"""
        result = bytearray(len(data))
        for i in range(0, len(data), 4):
            if i + 3 < len(data):
                result[i:i+4] = data[i:i+4][::-1]
        return bytes(result)

    def convert_from_z64_to_v64(self, data):
        """Convert from z64 to v64 format"""
        result = bytearray(len(data))
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                result[i] = data[i + 1]
                result[i + 1] = data[i]
        return bytes(result)

if __name__ == "__main__":
    root = tk.Tk()
    app = UniversalN64Dumper(root)
    root.mainloop()
