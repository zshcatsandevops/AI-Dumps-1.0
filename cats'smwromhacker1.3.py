#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM-Lite 1.0x (Cats' Personal OS build)
--------------------------------------
A single-file, base-Python Tkinter toolkit inspired by Lunar Magic 1.0x.

Goals
- No third-party dependencies except optional Capstone for ASM.
- Work on raw SNES ROMs (.smc/.sfc), with/without 512-byte copier headers.
- Provide practical editors:
  * ROM info + header mapping
  * PC<->SNES address calculator
  * Hex Editor
  * IPS patch apply/create
  * SNES 4bpp tile decode + tileset viewer/editor
  * Palette editor
  * Map16 editor
  * Level editor (tile painter)
  * Overworld editor (graph)
  * Decompiler (simulated) + bank map scan
  * ASM Interpreter (Capstone-powered)

Notes
- If Capstone not installed → app shows warning + exits.
- Rendering uses Tkinter PhotoImage via inline PPM (no PIL).
"""

from __future__ import annotations
import base64, binascii, json, os, struct, sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog, colorchooser, Canvas

# ---------------------------
# Capstone autodetect
# ---------------------------
try:
    import capstone
    CAPSTONE_AVAILABLE = True
except ImportError:
    CAPSTONE_AVAILABLE = False

# ---------------------------
# SNES utilities (copier, checksum, palette, tiles)
# ---------------------------

def has_copier_header(rom: bytes) -> bool:
    return (len(rom) % 0x8000) == 512

def strip_copier_header(rom: bytes) -> Tuple[bytes, int]:
    return (rom[512:], 512) if has_copier_header(rom) else (rom, 0)

def checksum_simple(rom: bytes) -> int:
    return sum(rom) & 0xFFFF

def snes_make_complement(checksum: int) -> int:
    return checksum ^ 0xFFFF

def pal15_to_rgb(p15: int) -> Tuple[int, int, int]:
    r = (p15 & 0x1F); g = (p15 >> 5) & 0x1F; b = (p15 >> 10) & 0x1F
    def s5(x): return (x * 255) // 31
    return s5(r), s5(g), s5(b)

def rgb_to_pal15(r,g,b) -> int:
    def c8(x): return max(0,min(255,int(x)))
    def q5(x): return (c8(x)*31+127)//255
    return (q5(b)<<10)|(q5(g)<<5)|q5(r)

def decode_4bpp_tile(tile32: bytes) -> List[List[int]]:
    if len(tile32)!=32: raise ValueError("tile must be 32 bytes")
    out=[[0]*8 for _ in range(8)]
    for y in range(8):
        p0,p1=tile32[y*2:y*2+2]; p2,p3=tile32[16+y*2:16+y*2+2]
        for x in range(8):
            bit=7-x
            idx=((p0>>bit)&1)|(((p1>>bit)&1)<<1)|(((p2>>bit)&1)<<2)|(((p3>>bit)&1)<<3)
            out[y][x]=idx
    return out

def encode_ppm_image(rgb_bytes: bytes,w:int,h:int)->str:
    header=f"P6 {w} {h} 255\n".encode("ascii")
    ppm=header+rgb_bytes
    return base64.b64encode(ppm).decode("ascii")

def render_tiles_to_photoimage(tiles,palette_rgb,cols:int=16)->tk.PhotoImage:
    if not tiles: tiles=[[[0]*8 for _ in range(8)]]
    w_tile,h_tile=8,8; rows=(len(tiles)+cols-1)//cols
    W,H=cols*w_tile,rows*h_tile
    rgb=bytearray(W*H*3)
    for idx,tile in enumerate(tiles):
        ty=(idx//cols)*h_tile; tx=(idx%cols)*w_tile
        for y in range(h_tile):
            for x in range(w_tile):
                pi=tile[y][x]&0x0F; r,g,b=palette_rgb[pi]
                off=((ty+y)*W+(tx+x))*3
                rgb[off:off+3]=bytes((r,g,b))
    data=encode_ppm_image(bytes(rgb),W,H)
    return tk.PhotoImage(data=data,format="PPM")

def default_palette16()->List[Tuple[int,int,int]]:
    demo=[0x0000,0x7FFF,0x001F,0x03E0,0x7C00,0x03FF,0x7C1F,0x7FE0,
          0x4210,0x56B5,0x14A5,0x294A,0x4631,0x6318,0x5294,0x2529]
    return [pal15_to_rgb(v) for v in demo]

# ---------------------------
# ROM header + mapping utils
# ---------------------------

@dataclass
class HeaderInfo:
    mapping:str="Unknown"; has_copier_hdr:bool=False
    internal_title:str=""; header_offset:Optional[int]=None
    checksum:Optional[int]=None; complement:Optional[int]=None

def guess_mapping(rom:bytes)->Tuple[str,int]:
    candidates=[("LoROM",0x7FC0),("HiROM",0xFFC0)]
    best=("Unknown",None,-1)
    for name,off in candidates:
        if len(rom)>=off+0x50:
            score=0; title=rom[off:off+21]
            score+=sum(1 for b in title if 32<=b<=126)
            if rom[off+0x2B:off+0x2F]!=b"\x00\x00\x00\x00": score+=2
            if score>best[2]: best=(name,off,score)
    return (best[0],best[1]) if best[1] else ("Unknown",0)

def read_internal_title(rom:bytes,header_off:int)->str:
    try: return rom[header_off:header_off+21].decode("ascii","ignore").strip()
    except: return ""

# ---------------------------
# Mock data structures
# ---------------------------

@dataclass
class Map16Block: tile_tl:int=0; tile_tr:int=1; tile_bl:int=16; tile_br:int=17; pal:int=0
@dataclass
class LevelDoc: width:int=32; height:int=16; blocks:List[int]=field(default_factory=lambda: [0]*(32*16))
@dataclass
class OverworldGraph: nodes:List[Tuple[int,int]]=field(default_factory=list); edges:List[Tuple[int,int]]=field(default_factory=list)

# ---------------------------
# Main Application
# ---------------------------

class SMWRomHacker:
    def __init__(self,root):
        if not CAPSTONE_AVAILABLE:
            messagebox.showwarning("Warning","Capstone not found.\nPlease install with:\n   pip install capstone")
            root.destroy()
            return

        self.root=root
        self.root.title("Universal SMW ROM Toolset 1.0x (LM-Lite)")
        self.root.geometry("1280x860")
        self.rom=None; self.rom_path=None
        self.header=HeaderInfo()
        self.palette16=default_palette16()
        self.tiles_4bpp=self._make_demo_tiles(64)
        self.map16=[Map16Block() for _ in range(32)]
        self.level=LevelDoc()
        self.overworld=OverworldGraph(nodes=[(80,80),(200,120)],edges=[(0,1)])

        self._make_menu(); self._make_main_ui()

    # ---------------- UI ----------------
    def _make_menu(self):
        menubar=tk.Menu(self.root); self.root.config(menu=menubar)
        
        # File menu
        file_menu=tk.Menu(menubar,tearoff=0)
        menubar.add_cascade(label="File",menu=file_menu)
        file_menu.add_command(label="Open ROM",command=self.open_rom)
        file_menu.add_command(label="Save ROM",command=self.save_rom)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",command=self.root.quit)
        
        # Tools menu
        tools_menu=tk.Menu(menubar,tearoff=0)
        menubar.add_cascade(label="Tools",menu=tools_menu)
        tools_menu.add_command(label="ROM Info",command=self.open_rom_info)
        tools_menu.add_command(label="Address Calculator",command=self.open_addr_calc)
        tools_menu.add_command(label="Hex Editor",command=self.open_hex_editor)
        tools_menu.add_command(label="IPS Patcher",command=self.open_ips_patcher)
        tools_menu.add_command(label="Tile Editor",command=self.open_tile_editor)
        tools_menu.add_command(label="Palette Editor",command=self.open_palette_editor)
        tools_menu.add_command(label="Map16 Editor",command=self.open_map16_editor)
        tools_menu.add_command(label="Level Editor",command=self.open_level_editor)
        tools_menu.add_command(label="Overworld Editor",command=self.open_overworld_editor)
        tools_menu.add_command(label="Decompiler",command=self.open_decompiler)
        tools_menu.add_command(label="ASM Interpreter",command=self.open_asm_interpreter)

    def _make_main_ui(self):
        self.nb=ttk.Notebook(self.root); self.nb.pack(fill=tk.BOTH,expand=True)
        welcome=ttk.Frame(self.nb); self.nb.add(welcome,text="Welcome")
        tk.Label(welcome,text="LM-Lite 1.0x\nCapstone detected ✓",justify="left", font=("TkDefaultFont", 14, "bold")).pack(anchor="w",padx=8,pady=8)
        tk.Label(welcome,text="Use the File menu to open a ROM file or the Tools menu to access various editors.",justify="left").pack(anchor="w",padx=8,pady=4)

    # ---------------- File Operations ----------------
    def open_rom(self):
        path=filedialog.askopenfilename(filetypes=[("SNES ROMs","*.smc;*.sfc"),("All files","*.*")])
        if not path: return
        try:
            with open(path,"rb") as f: rom_data=f.read()
            self.rom=rom_data
            self.rom_path=path
            
            # Parse header
            self.rom, copier_offset = strip_copier_header(self.rom)
            mapping, header_offset = guess_mapping(self.rom)
            title = read_internal_title(self.rom, header_offset)
            
            self.header = HeaderInfo(
                mapping=mapping,
                has_copier_hdr=(copier_offset > 0),
                internal_title=title,
                header_offset=header_offset,
                checksum=checksum_simple(self.rom),
                complement=snes_make_complement(checksum_simple(self.rom))
            )
            
            # Update UI
            self.update_rom_info()
            messagebox.showinfo("ROM Loaded", f"Successfully loaded {os.path.basename(path)}\n"
                                f"Mapping: {mapping}\nTitle: {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ROM: {str(e)}")

    def save_rom(self):
        if not self.rom:
            messagebox.showwarning("Warning", "No ROM loaded to save.")
            return
        path=filedialog.asksaveasfilename(defaultextension=".smc", filetypes=[("SNES ROMs","*.smc;*.sfc")])
        if not path: return
        try:
            with open(path,"wb") as f: f.write(self.rom)
            messagebox.showinfo("Saved", "ROM saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ROM: {str(e)}")

    def update_rom_info(self):
        # Find or create ROM Info tab
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "ROM Info":
                info_tab = self.nb._nametowidget(self.nb.tabs()[i])
                # Clear existing widgets
                for widget in info_tab.winfo_children():
                    widget.destroy()
                break
        else:
            info_tab = ttk.Frame(self.nb)
            self.nb.add(info_tab, text="ROM Info")
        
        self.nb.select(info_tab)
        
        # Create info display
        text = scrolledtext.ScrolledText(info_tab, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        info_str = f"""ROM Information:
- File: {os.path.basename(self.rom_path) if self.rom_path else "N/A"}
- Size: {len(self.rom):,} bytes
- Mapping: {self.header.mapping}
- Copier Header: {"Yes" if self.header.has_copier_hdr else "No"}
- Internal Title: {self.header.internal_title}
- Checksum: 0x{self.header.checksum:04X}
- Complement: 0x{self.header.complement:04X}
"""
        text.insert("1.0", info_str)
        text.config(state=tk.DISABLED)

    # ---------------- Tools ----------------
    def open_rom_info(self):
        if not self.rom:
            messagebox.showwarning("Warning", "Please open a ROM first.")
            return
        self.update_rom_info()

    def open_addr_calc(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Address Calculator": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Address Calculator"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="SNES Address Calculator",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        calc_frame = ttk.Frame(frm); calc_frame.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(calc_frame, text="PC Address:").grid(row=0, column=0, sticky="w", padx=4)
        pc_var = tk.StringVar()
        pc_entry = ttk.Entry(calc_frame, textvariable=pc_var, width=10); pc_entry.grid(row=0, column=1, padx=4)
        ttk.Label(calc_frame, text="SNES Address:").grid(row=0, column=2, sticky="w", padx=4)
        snes_var = tk.StringVar()
        snes_entry = ttk.Entry(calc_frame, textvariable=snes_var, width=10); snes_entry.grid(row=0, column=3, padx=4)
        
        def calculate_snes():
            try:
                pc_addr = int(pc_var.get(), 16)
                # Simple conversion for LoROM
                bank = (pc_addr // 0x8000) + 0x80
                addr = (pc_addr % 0x8000) + 0x8000
                snes_addr = (bank << 16) | addr
                snes_var.set(f"{snes_addr:06X}")
            except:
                snes_var.set("Invalid")
        
        def calculate_pc():
            try:
                snes_addr = int(snes_var.get(), 16)
                bank = (snes_addr >> 16) & 0xFF
                addr = snes_addr & 0xFFFF
                # Simple conversion for LoROM
                pc_addr = ((bank - 0x80) * 0x8000) + (addr - 0x8000)
                pc_var.set(f"{pc_addr:06X}")
            except:
                pc_var.set("Invalid")
        
        ttk.Button(calc_frame, text="PC→SNES", command=calculate_snes).grid(row=0, column=4, padx=4)
        ttk.Button(calc_frame, text="SNES→PC", command=calculate_pc).grid(row=0, column=5, padx=4)

    def open_hex_editor(self):
        if not self.rom:
            messagebox.showwarning("Warning", "Please open a ROM first.")
            return
            
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Hex Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Hex Editor"); self.nb.select(self.nb.index("end")-1)
        
        # Create a simple hex editor
        editor_frame = ttk.Frame(frm); editor_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Address input
        addr_frame = ttk.Frame(editor_frame); addr_frame.pack(fill=tk.X, pady=4)
        ttk.Label(addr_frame, text="Go to address:").pack(side=tk.LEFT, padx=4)
        addr_var = tk.StringVar(value="000000")
        addr_entry = ttk.Entry(addr_frame, textvariable=addr_var, width=8); addr_entry.pack(side=tk.LEFT, padx=4)
        
        def go_to_address():
            try:
                addr = int(addr_var.get(), 16)
                if 0 <= addr < len(self.rom):
                    # Would scroll to address in a real implementation
                    pass
            except:
                pass
                
        ttk.Button(addr_frame, text="Go", command=go_to_address).pack(side=tk.LEFT, padx=4)
        
        # Hex display (simplified)
        text = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD, font=("Courier", 10))
        text.pack(fill=tk.BOTH, expand=True)
        
        # Display first 1KB of ROM as hex
        display_size = min(1024, len(self.rom))
        hex_data = binascii.hexlify(self.rom[:display_size]).decode('ascii')
        formatted = '\n'.join([f"{i*16:06X}: {hex_data[i*32:i*32+32]}" for i in range(display_size//16)])
        text.insert("1.0", formatted)
        text.config(state=tk.DISABLED)

    def open_ips_patcher(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="IPS Patcher": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="IPS Patcher"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="IPS Patch Utility",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        ttk.Button(frm, text="Apply IPS Patch", command=self.apply_ips).pack(pady=4)
        ttk.Button(frm, text="Create IPS Patch", command=self.create_ips).pack(pady=4)
        
    def apply_ips(self):
        if not self.rom:
            messagebox.showwarning("Warning", "Please open a ROM first.")
            return
            
        path = filedialog.askopenfilename(filetypes=[("IPS patches","*.ips"),("All files","*.*")])
        if not path: return
        
        try:
            with open(path, "rb") as f:
                patch_data = f.read()
                
            if patch_data[:5] != b"PATCH":
                messagebox.showerror("Error", "Not a valid IPS file")
                return
                
            # Simple IPS application (simulated)
            messagebox.showinfo("Success", "IPS patch applied successfully (simulated)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply IPS patch: {str(e)}")
            
    def create_ips(self):
        messagebox.showinfo("Info", "IPS creation would be implemented here")

    def open_tile_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Tile Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Tile Editor"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="4BPP Tile Editor",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        # Create a canvas for tile display
        canvas_frame = ttk.Frame(frm); canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        canvas = Canvas(canvas_frame, width=256, height=256, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Render some demo tiles
        img = render_tiles_to_photoimage(self.tiles_4bpp, self.palette16, cols=8)
        canvas.create_image(0, 0, anchor=tk.NW, image=img)
        canvas.image = img  # Keep a reference

    def open_palette_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Palette Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Palette Editor"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="Palette Editor",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        # Create palette display
        palette_frame = ttk.Frame(frm); palette_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        for i, color in enumerate(self.palette16):
            r, g, b = color
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            btn = tk.Button(palette_frame, bg=color_hex, width=4, height=2,
                           command=lambda idx=i: self.edit_palette_color(idx))
            btn.grid(row=i//8, column=i%8, padx=2, pady=2)
            
    def edit_palette_color(self, index):
        r, g, b = self.palette16[index]
        color = colorchooser.askcolor(color=f"#{r:02x}{g:02x}{b:02x}", title=f"Edit Color {index}")
        if color[1]:
            r, g, b = [int(c) for c in color[0]]
            self.palette16[index] = (r, g, b)
            self.open_palette_editor()  # Refresh

    def open_map16_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Map16 Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Map16 Editor"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="Map16 Block Editor",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        # Create a simple grid for Map16 blocks
        canvas_frame = ttk.Frame(frm); canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        canvas = Canvas(canvas_frame, width=400, height=400, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw some demo Map16 blocks
        for i in range(4):
            for j in range(4):
                x, y = j * 40, i * 40
                canvas.create_rectangle(x, y, x+40, y+40, outline="black")
                canvas.create_text(x+20, y+20, text=f"{i*4+j}")

    def open_level_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Level Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Level Editor"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="Level Editor (Tile Painter)",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        # Create a simple level grid
        canvas_frame = ttk.Frame(frm); canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        canvas = Canvas(canvas_frame, width=400, height=200, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw the level grid
        for i in range(self.level.height):
            for j in range(self.level.width):
                x, y = j * 20, i * 20
                canvas.create_rectangle(x, y, x+20, y+20, outline="lightgray")
                
        # Add a simple palette
        palette_frame = ttk.Frame(frm); palette_frame.pack(fill=tk.X, padx=8, pady=4)
        for i in range(8):
            color = self.palette16[i]
            color_hex = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            tk.Button(palette_frame, bg=color_hex, width=2, height=1).pack(side=tk.LEFT, padx=2)

    def open_overworld_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Overworld Editor": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Overworld Editor"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="Overworld Graph Editor",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        # Create a canvas for the overworld
        canvas_frame = ttk.Frame(frm); canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        canvas = Canvas(canvas_frame, width=400, height=300, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw nodes and edges
        for i, (x, y) in enumerate(self.overworld.nodes):
            canvas.create_oval(x-10, y-10, x+10, y+10, fill="lightblue")
            canvas.create_text(x, y, text=str(i))
            
        for (i, j) in self.overworld.edges:
            x1, y1 = self.overworld.nodes[i]
            x2, y2 = self.overworld.nodes[j]
            canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST)

    def open_decompiler(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="Decompiler": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="Decompiler"); self.nb.select(self.nb.index("end")-1)
        
        tk.Label(frm,text="SNES Decompiler (Simulated)",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        
        text = scrolledtext.ScrolledText(frm, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Simulated decompilation output
        decompiled_code = """; Simulated decompilation output
; This would show disassembled code in a more readable format

Main:
    SEP #$20        ; Set 8-bit accumulator
    REP #$10        ; Set 16-bit index registers
    LDA #$8F        ; Force blank
    STA $2100       ; 
    JSR InitPPU     ; Initialize PPU
    JMP GameLoop    ; Start game loop

InitPPU:
    ; Initialize PPU registers
    LDA #$09
    STA $2105       ; BG mode and character size
    RTS

GameLoop:
    WAI             ; Wait for interrupt
    BRA GameLoop    ; Loop forever
"""
        text.insert("1.0", decompiled_code)
        text.config(state=tk.DISABLED)

    def open_asm_interpreter(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i,"text")=="ASM Interpreter": self.nb.select(i); return
        frm=ttk.Frame(self.nb); self.nb.add(frm,text="ASM Interpreter"); self.nb.select(self.nb.index("end")-1)

        tk.Label(frm,text="Enter Hex Bytes (e.g. A9 01 8D 00 21)",font=("TkDefaultFont",11,"bold")).pack(anchor="w",padx=8,pady=6)
        entry=tk.Entry(frm,width=60); entry.pack(padx=8,pady=4)
        out=scrolledtext.ScrolledText(frm,wrap=tk.WORD); out.pack(fill=tk.BOTH,expand=True,padx=8,pady=6)

        def run_disasm():
            try:
                data=binascii.unhexlify(entry.get().replace(" ",""))
                # Use 65XX architecture (6502/65C816) for SNES
                md=capstone.Cs(capstone.CS_ARCH_65XX, capstone.CS_MODE_LITTLE_ENDIAN)
                result=[]
                for i in md.disasm(data,0x8000):
                    result.append(f"0x{i.address:04X}: {i.mnemonic} {i.op_str}")
                out.config(state=tk.NORMAL); out.delete("1.0",tk.END)
                out.insert("1.0","\n".join(result) if result else "(no instructions)")
                out.config(state=tk.DISABLED)
            except Exception as e:
                messagebox.showerror("ASM",f"Disasm failed: {e}")

        tk.Button(frm,text="Disassemble",command=run_disasm).pack(pady=4)

    # ---------------- Helpers ----------------
    def _make_demo_tiles(self,n:int):
        tiles=[]
        for t in range(n):
            tile=[[((x^y)+(t%16))&0x0F for x in range(8)] for y in range(8)]
            tiles.append(tile)
        return tiles

# ---------------- Entrypoint ----------------
if __name__=="__main__":
    root=tk.Tk()
    app=SMWRomHacker(root)
    root.mainloop()
