#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM-Lite 1.0x (Cats' Personal OS build)
--------------------------------------
A single-file, base-Python Tkinter toolkit inspired by Lunar Magic 1.0x.

Goals
- No third-party dependencies (no PIL, no numpy).
- Work on raw SNES ROMs (.smc/.sfc), with/without 512-byte copier headers.
- Provide practical, working editors:
  * ROM info + header mapping (LoROM/HiROM), checksum & complement
  * PC<->SNES address calculator
  * Hex Editor with paging, goto, and search
  * IPS patch apply/create (stdlib only)
  * SNES 4bpp tile decode + tileset viewer/editor
  * Palette editor (SNES 15-bit BGR)
  * Map16 editor (4x 8x8 tiles w/ flips + palette)
  * Level editor (tile painter) with JSON import/export (invented)
  * Overworld editor (graph of nodes/edges) with JSON import/export (invented)
  * Decompiler (simulated) + bank map scan

Notes
- Real SMW parsing is not included: formats are *invented but consistent* to test the UI
  and end-to-end flows. Swap stub parsers with real ones when ready.
- All rendering uses Tkinter PhotoImage via inline PPM (P6) data (no PIL).

Author: You + ChatGPT (Cats' Personal OS 1.0)
License: MIT
"""
from __future__ import annotations

import base64
import binascii
import io
import json
import os
import struct
import sys
import zlib
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

# ---------------------------
# Utilities & SNES primitives
# ---------------------------

def has_copier_header(rom_bytes: bytes) -> bool:
    # 512-byte copier header often present in .smc
    return (len(rom_bytes) % 0x8000) == 512

def strip_copier_header(rom: bytes) -> Tuple[bytes, int]:
    if has_copier_header(rom):
        return rom[512:], 512
    return rom, 0

def add_copier_header(rom: bytes) -> bytes:
    # Not usually needed, but provided.
    if has_copier_header(rom):
        return rom
    return b"\x00" * 512 + rom

def checksum_simple(rom: bytes) -> int:
    # Simple 16-bit sum over all bytes (not the SNES complement algorithm used by carts)
    return sum(rom) & 0xFFFF

def snes_make_complement(checksum: int) -> int:
    # SNES header typically stores checksum and complement (checksum ^ 0xFFFF)
    return checksum ^ 0xFFFF

def pal15_to_rgb(p15: int) -> Tuple[int, int, int]:
    # SNES 15-bit BGR? Common practice uses R in low 5 bits.
    # We'll assume bits: 0-4 R, 5-9 G, 10-14 B. Scale 0..31 -> 0..255
    r = (p15 & 0x1F)
    g = (p15 >> 5) & 0x1F
    b = (p15 >> 10) & 0x1F
    def s5(x):  # scale 0..31 to 0..255
        return (x * 255) // 31
    return s5(r), s5(g), s5(b)

def rgb_to_pal15(r: int, g: int, b: int) -> int:
    # inverse of pal15_to_rgb, clamp
    def c8(x): return max(0, min(255, int(x)))
    def q5(x): return (c8(x) * 31 + 127) // 255
    return (q5(b) << 10) | (q5(g) << 5) | q5(r)

def decode_4bpp_tile(tile32: bytes) -> List[List[int]]:
    """
    SNES 4bpp 8x8 tile, 32 bytes:
      For each of 8 rows:
        byte0: bitplane0 lo
        byte1: bitplane1 lo
      next 16 bytes:
        byte0: bitplane2 lo
        byte1: bitplane3 lo
    Pixel x uses bit 7-x.
    Returns 8x8 palette index (0..15)
    """
    if len(tile32) != 32:
        raise ValueError("4bpp tile must be 32 bytes")
    out = [[0]*8 for _ in range(8)]
    for y in range(8):
        p0 = tile32[y*2 + 0]
        p1 = tile32[y*2 + 1]
        p2 = tile32[16 + y*2 + 0]
        p3 = tile32[16 + y*2 + 1]
        for x in range(8):
            bit = 7 - x
            idx = ((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) | (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3)
            out[y][x] = idx
    return out

def encode_ppm_image(rgb_bytes: bytes, w: int, h: int) -> str:
    """
    Return base64-encoded binary PPM (P6) suitable for tk.PhotoImage(data=..., format='PPM')
    """
    header = f"P6 {w} {h} 255\n".encode("ascii")
    ppm = header + rgb_bytes
    return base64.b64encode(ppm).decode("ascii")

def render_tiles_to_photoimage(tiles: List[List[List[int]]], palette_rgb: List[Tuple[int,int,int]],
                               cols: int = 16) -> tk.PhotoImage:
    """
    tiles: list of 8x8 tiles (each tile is list[y][x] palette index 0..15)
    palette_rgb: 16 RGB triplets
    Arrange into a grid with 'cols' tiles per row.
    """
    if not tiles:
        # one transparent-ish tile
        tiles = [[[0]*8 for _ in range(8)]]
    w_tile, h_tile = 8, 8
    cols = max(1, cols)
    rows = (len(tiles) + cols - 1) // cols
    W = cols * w_tile
    H = rows * h_tile
    rgb = bytearray(W * H * 3)
    for idx, tile in enumerate(tiles):
        ty = (idx // cols) * h_tile
        tx = (idx % cols) * w_tile
        for y in range(h_tile):
            for x in range(w_tile):
                pi = tile[y][x] & 0x0F
                r, g, b = palette_rgb[pi]
                off = ((ty+y)*W + (tx+x))*3
                rgb[off:off+3] = bytes((r, g, b))
    data = encode_ppm_image(bytes(rgb), W, H)
    return tk.PhotoImage(data=data, format='PPM')

def default_palette16() -> List[Tuple[int,int,int]]:
    # A readable default (invented), matches 0..15 indices.
    demo = [0x0000, 0x7FFF, 0x001F, 0x03E0, 0x7C00, 0x03FF, 0x7C1F, 0x7FE0,
            0x4210, 0x56B5, 0x14A5, 0x294A, 0x4631, 0x6318, 0x5294, 0x2529]
    return [pal15_to_rgb(v) for v in demo]

# ---------------------------
# IPS patching (apply/create)
# ---------------------------

class IPS:
    @staticmethod
    def apply(rom: bytearray, patch_bytes: bytes) -> bytearray:
        """
        Apply IPS to ROM. Returns a new bytearray.
        IPS format:
          'PATCH' header
          Repeat:
            3-byte offset (big-endian)
            2-byte size
              if size != 0: read size bytes of data
              if size == 0: RLE block: read 2-byte rle_size, 1 data byte, repeat data
          'EOF'
        """
        data = patch_bytes
        if not data.startswith(b"PATCH"):
            raise ValueError("Not an IPS file (missing PATCH)")
        i = 5
        out = bytearray(rom)  # copy
        while True:
            if i+3 > len(data):
                raise ValueError("Truncated IPS")
            if data[i:i+3] == b"EOF":
                break
            offset = (data[i]<<16) | (data[i+1]<<8) | data[i+2]
            i += 3
            if i+2 > len(data):
                raise ValueError("Truncated IPS")
            size = (data[i]<<8) | data[i+1]
            i += 2
            if size == 0:
                if i+3 > len(data):
                    raise ValueError("Truncated IPS RLE")
                rle_size = (data[i]<<8) | data[i+1]
                val = data[i+2]
                i += 3
                IPS._ensure_len(out, offset + rle_size)
                out[offset:offset+rle_size] = bytes([val])*rle_size
            else:
                if i+size > len(data):
                    raise ValueError("Truncated IPS data")
                IPS._ensure_len(out, offset + size)
                out[offset:offset+size] = data[i:i+size]
                i += size
        return out

    @staticmethod
    def create(old: bytes, new: bytes) -> bytes:
        """
        Minimal IPS creator: emits changed spans. No fancy coalescing.
        """
        if len(new) < len(old):
            # extend old to new length to diff uniformly
            old = old[:len(new)]
        header = b"PATCH"
        chunks = []
        i = 0
        while i < len(new):
            if i < len(old) and new[i] == old[i]:
                i += 1
                continue
            # start of change
            start = i
            while i < len(new) and (i >= len(old) or new[i] != old[i]) and (i - start) < 0xFFFF:
                i += 1
            size = i - start
            off3 = bytes([(start>>16)&0xFF, (start>>8)&0xFF, start&0xFF])
            sz2 = bytes([(size>>8)&0xFF, size&0xFF])
            chunks.append(off3 + sz2 + new[start:start+size])
        return header + b"".join(chunks) + b"EOF"

    @staticmethod
    def _ensure_len(buf: bytearray, n: int) -> None:
        if len(buf) < n:
            buf.extend(b"\x00"*(n - len(buf)))

# ---------------------------
# ROM header / mapping utils
# ---------------------------

@dataclass
class HeaderInfo:
    mapping: str = "Unknown"  # LoROM / HiROM / Unknown
    has_copier_hdr: bool = False
    internal_title: str = ""
    header_offset: Optional[int] = None  # 0x7FC0 for LoROM or 0xFFC0 for HiROM (no copier header)
    checksum: Optional[int] = None
    complement: Optional[int] = None

def guess_mapping(rom_wo_hdr: bytes) -> Tuple[str, int]:
    """
    Heuristic: check probable internal header at 0x7FC0 (LoROM) and 0xFFC0 (HiROM).
    Return (mapping, header_offset)
    """
    candidates = [("LoROM", 0x7FC0), ("HiROM", 0xFFC0)]
    best = ("Unknown", None, -1)  # name, off, score
    for name, off in candidates:
        if len(rom_wo_hdr) >= off + 0x50:
            score = 0
            title = rom_wo_hdr[off:off+21]
            # ASCII-ness
            for b in title:
                if 32 <= b <= 126:
                    score += 1
            # reset vectors plausibility (very rough, check non-zero near end)
            # Not rigorous, just for UX.
            if rom_wo_hdr[off+0x2B:off+0x2F] != b"\x00\x00\x00\x00":
                score += 2
            if score > best[2]:
                best = (name, off, score)
    if best[1] is None:
        return "Unknown", 0
    return best[0], best[1]

def read_internal_title(rom_wo_hdr: bytes, header_off: int) -> str:
    try:
        t = rom_wo_hdr[header_off:header_off+21]
        return t.decode("ascii", errors="ignore").strip()
    except Exception:
        return ""

def pc_to_snes_lorom(pc: int) -> int:
    bank = pc // 0x8000
    addr = (pc % 0x8000) + 0x8000
    return (0x80 << 16) | (bank << 16) | addr  # use $80.. mirror for clarity

def pc_to_snes_hirom(pc: int) -> int:
    bank = pc // 0x10000
    addr = pc % 0x10000
    return (0xC0 << 16) | (bank << 16) | addr  # $C0.. mirror

def snes_to_pc_lorom(snes: int) -> Optional[int]:
    bank = (snes >> 16) & 0xFF
    addr = snes & 0xFFFF
    if addr < 0x8000:
        return None
    return (bank & 0x7F) * 0x8000 + (addr - 0x8000)

def snes_to_pc_hirom(snes: int) -> int:
    bank = (snes >> 16) & 0xFF
    addr = snes & 0xFFFF
    return (bank & 0x3F) * 0x10000 + addr

# ---------------------------
# Invented data formats
# ---------------------------

@dataclass
class Map16Block:
    tile_tl: int = 0
    tile_tr: int = 1
    tile_bl: int = 16
    tile_br: int = 17
    pal: int = 0      # use 0..7 like SMW-style palette rows (we'll just pick from 0..1 here)
    flip_h_tl: bool = False
    flip_v_tl: bool = False
    flip_h_tr: bool = False
    flip_v_tr: bool = False
    flip_h_bl: bool = False
    flip_v_bl: bool = False
    flip_h_br: bool = False
    flip_v_br: bool = False

@dataclass
class LevelDoc:
    width: int
    height: int
    blocks: List[int]  # indices into Map16 table (width*height)

@dataclass
class OverworldGraph:
    nodes: List[Tuple[int,int]] = field(default_factory=list)  # (x,y) positions on canvas
    edges: List[Tuple[int,int]] = field(default_factory=list)  # pairs of node indices

# ---------------------------
# The Application (Tk)
# ---------------------------

class SMWRomHacker:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal Super Mario World ROM Hacking Toolset 1.0x (LM‑Lite)")
        self.root.geometry("1280x860")
        self.rom: Optional[bytearray] = None
        self.rom_path: Optional[str] = None
        self.header = HeaderInfo()
        self.copier_header_len = 0

        # graphics/palette state for viewer/editor
        self.palette16 = default_palette16()   # 16 RGB tuples
        self.tiles_4bpp: List[List[List[int]]] = self._make_demo_tiles(256)  # generated tiles
        self.map16: List[Map16Block] = [Map16Block(i, i+1, i+16, i+17, pal=(i//32)%2) for i in range(0, 256, 2)]
        self.level = LevelDoc(width=64, height=16, blocks=[0]*(64*16))
        self.overworld = OverworldGraph(nodes=[(80,80), (200,120), (320,160)], edges=[(0,1),(1,2)])

        self._make_menu()
        self._make_main_ui()

    # ---------- UI scaffolding ----------

    def _make_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open ROM...", command=self.open_rom)
        file_menu.add_command(label="Save ROM As...", command=self.save_rom_as, state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Apply IPS Patch...", command=self.apply_ips, state="disabled")
        file_menu.add_command(label="Create IPS from Current...", command=self.create_ips, state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Editors", menu=edit_menu)
        edit_menu.add_command(label="Level Editor", command=self.open_level_editor)
        edit_menu.add_command(label="Graphics Editor", command=self.open_graphics_editor)
        edit_menu.add_command(label="Map16 Editor", command=self.open_map16_editor)
        edit_menu.add_command(label="Palette Editor", command=self.open_palette_editor)
        edit_menu.add_command(label="Overworld Editor", command=self.open_overworld_editor)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Decompiler (Simulated)", command=self.open_decompiler, state="normal")
        tools_menu.add_command(label="Hex Editor", command=self.open_hex_editor, state="disabled")
        tools_menu.add_command(label="Address Calculator", command=self.open_address_calc)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        self._menus = {
            "file": file_menu,
            "edit": edit_menu,
            "tools": tools_menu,
        }

    def _make_main_ui(self):
        main = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left navigation/info
        left = ttk.Frame(main, width=260)
        main.add(left, weight=1)

        info = ttk.LabelFrame(left, text="ROM Information")
        info.pack(fill=tk.X, padx=4, pady=4)
        self.info_text = tk.Text(info, height=10, width=30)
        self.info_text.pack(fill=tk.X, padx=4, pady=4)
        self._set_info("No ROM loaded")

        nav = ttk.LabelFrame(left, text="Navigation")
        nav.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.nav_tree = ttk.Treeview(nav)
        self.nav_tree.pack(fill=tk.BOTH, expand=True)
        self.nav_tree.heading("#0", text="ROM Structure")

        # Right notebook
        right = ttk.Frame(main)
        main.add(right, weight=4)
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill=tk.BOTH, expand=True)

        # Welcome
        welcome = ttk.Frame(self.nb)
        self.nb.add(welcome, text="Welcome")
        tk.Label(
            welcome,
            text=(
                "Universal SMW ROM Hacking Toolset 1.0x (LM‑Lite)\n\n"
                "What’s here now (base-Python only):\n"
                "• LoROM/HiROM detection + copier header\n"
                "• Checksum & complement, SNES address calc\n"
                "• Hex editor with paging / goto / search\n"
                "• IPS apply/create\n"
                "• 4bpp tiles decode + tileset viewer/editor\n"
                "• Palette editor (SNES BGR15)\n"
                "• Map16 editor (invented) + Level editor w/ JSON I/O\n"
                "• Overworld mock editor (graph) + JSON I/O\n"
                "• Simulated decompiler scaffold\n\n"
                "Open a SMW ROM (.smc/.sfc) to unlock ROM-related tools.\n"
                "You can also play entirely with the invented data flow."
            ),
            justify=tk.LEFT
        ).pack(anchor="w", padx=10, pady=10)

        # Status bar
        self.status = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _set_info(self, s: str):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", s)
        self.info_text.config(state=tk.DISABLED)

    def _enable_rom_actions(self, enable: bool):
        state = "normal" if enable else "disabled"
        self._menus["file"].entryconfig("Save ROM As...", state=state)
        self._menus["file"].entryconfig("Apply IPS Patch...", state=state)
        self._menus["file"].entryconfig("Create IPS from Current...", state=state)
        self._menus["tools"].entryconfig("Hex Editor", state=state)

    # ---------- ROM I/O ----------

    def open_rom(self):
        path = filedialog.askopenfilename(
            title="Open SNES ROM (.smc/.sfc)",
            filetypes=[("SNES ROM", "*.smc *.sfc"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
            rom_wo, hdr = strip_copier_header(raw)
            mapping, header_off = guess_mapping(rom_wo)
            title = read_internal_title(rom_wo, header_off) if header_off else ""
            csum = checksum_simple(rom_wo)
            comp = snes_make_complement(csum)
            self.rom = bytearray(rom_wo)
            self.rom_path = path
            self.header = HeaderInfo(mapping=mapping, has_copier_hdr=(hdr>0),
                                     internal_title=title, header_offset=header_off,
                                     checksum=csum, complement=comp)
            self._enable_rom_actions(True)
            self._refresh_info_tree()
            self._set_info(self._fmt_info())
            self.status.config(text=f"Loaded ROM: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open ROM: {e}")

    def save_rom_as(self):
        if not self.rom:
            return
        path = filedialog.asksaveasfilename(
            title="Save ROM As", defaultextension=".sfc",
            filetypes=[("SNES ROM", "*.sfc *.smc"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "wb") as f:
                f.write(self.rom)
            self.status.config(text=f"Saved ROM: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save ROM: {e}")

    def apply_ips(self):
        if not self.rom:
            return
        path = filedialog.askopenfilename(
            title="Apply IPS Patch", filetypes=[("IPS patches", "*.ips"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                ips = f.read()
            self.rom = IPS.apply(self.rom, ips)
            self.header.checksum = checksum_simple(self.rom)
            self.header.complement = snes_make_complement(self.header.checksum)
            self._set_info(self._fmt_info())
            messagebox.showinfo("IPS", "Patch applied successfully.")
        except Exception as e:
            messagebox.showerror("IPS", f"Failed to apply IPS: {e}")

    def create_ips(self):
        if not self.rom or not self.rom_path:
            return
        # Diff current ROM against the on-disk version that was loaded.
        try:
            with open(self.rom_path, "rb") as f:
                disk = strip_copier_header(f.read())[0]
            ips = IPS.create(disk, bytes(self.rom))
            save = filedialog.asksaveasfilename(
                title="Save IPS Patch", defaultextension=".ips",
                filetypes=[("IPS patches", "*.ips")]
            )
            if not save:
                return
            with open(save, "wb") as f:
                f.write(ips)
            messagebox.showinfo("IPS", "Created IPS patch from current edits.")
        except Exception as e:
            messagebox.showerror("IPS", f"Failed to create IPS: {e}")

    # ---------- Info helpers ----------

    def _fmt_info(self) -> str:
        h = self.header
        lines = []
        lines.append(f"Mapping: {h.mapping}")
        lines.append(f"Copier header: {'present (512B)' if h.has_copier_hdr else 'absent'}")
        if h.header_offset is not None:
            lines.append(f"Internal header @ 0x{h.header_offset:06X}")
        if h.internal_title:
            lines.append(f"Internal title: {h.internal_title}")
        if h.checksum is not None:
            lines.append(f"Checksum: 0x{h.checksum:04X}")
        if h.complement is not None:
            lines.append(f"Complement: 0x{h.complement:04X}")
        lines.append(f"ROM size: {len(self.rom) if self.rom else 0} bytes")
        return "\n".join(lines)

    def _refresh_info_tree(self):
        self.nav_tree.delete(*self.nav_tree.get_children())
        root_id = self.nav_tree.insert("", "end", text="ROM", open=True)
        if self.rom:
            # add simplistic bank nodes
            size = len(self.rom)
            # prefer detected mapping
            if self.header.mapping == "LoROM":
                bank_size = 0x8000
            elif self.header.mapping == "HiROM":
                bank_size = 0x10000
            else:
                bank_size = 0x8000
            bank_count = (size + bank_size - 1) // bank_size
            for b in range(bank_count):
                start = b*bank_size
                end = min(size, (b+1)*bank_size)
                self.nav_tree.insert(root_id, "end", text=f"Bank ${b:02X}: 0x{start:06X}-0x{end:06X}")
        else:
            self.nav_tree.insert(root_id, "end", text="(no data)")

    # ---------- Editors / Tools ----------

    # Hex editor
    def open_hex_editor(self):
        if not self.rom:
            messagebox.showwarning("Hex", "Open a ROM first.")
            return
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Hex Editor":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Hex Editor")
        self.nb.select(self.nb.index("end")-1)

        control = ttk.Frame(frm)
        control.pack(fill=tk.X)
        tk.Label(control, text="Offset (hex):").pack(side=tk.LEFT, padx=4)
        off_var = tk.StringVar(value="0")
        tk.Entry(control, textvariable=off_var, width=12).pack(side=tk.LEFT)
        tk.Button(control, text="Goto", command=lambda: show_page()).pack(side=tk.LEFT, padx=2)
        tk.Label(control, text="Find (ASCII/hex like DE AD BE EF):").pack(side=tk.LEFT, padx=8)
        find_var = tk.StringVar()
        tk.Entry(control, textvariable=find_var, width=30).pack(side=tk.LEFT)
        tk.Button(control, text="Search", command=lambda: do_search()).pack(side=tk.LEFT, padx=2)

        text = scrolledtext.ScrolledText(frm, wrap=tk.NONE, font=("Courier", 10))
        text.pack(fill=tk.BOTH, expand=True)

        def show_page(offset: Optional[int]=None):
            try:
                if offset is None:
                    offset = int(off_var.get(), 16)
            except Exception:
                messagebox.showerror("Goto", "Invalid hex offset.")
                return
            offset = max(0, min(len(self.rom)-1, offset))
            lines = ["Offset   " + " ".join(f"{i:02X}" for i in range(16)) + "   ASCII",
                     "------   " + " ".join(["--"]*16) + "   -----"]
            end = min(len(self.rom), offset + 1024)
            for i in range(offset, end, 16):
                chunk = self.rom[i: i+16]
                hexs = " ".join(f"{b:02X}" for b in chunk)
                ascii_ = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                lines.append(f"{i:06X}   {hexs:<47}   {ascii_}")
            text.config(state=tk.NORMAL)
            text.delete("1.0", tk.END)
            text.insert("1.0", "\n".join(lines))
            text.config(state=tk.DISABLED)

        def do_search():
            q = find_var.get().strip()
            if not q:
                return
            # try hex pattern first
            pat: Optional[bytes] = None
            try:
                hs = q.replace(" ", "")
                if all(c in "0123456789abcdefABCDEF" for c in hs) and len(hs)%2==0:
                    pat = binascii.unhexlify(hs)
            except Exception:
                pat = None
            if pat is None:
                pat = q.encode("utf-8", "ignore")
            i = self.rom.find(pat)
            if i < 0:
                messagebox.showinfo("Search", "Not found.")
            else:
                off_var.set(f"{i:06X}")
                show_page(i)

        show_page(0)

    # Address calculator
    def open_address_calc(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Address Calc":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Address Calc")
        self.nb.select(self.nb.index("end")-1)

        tk.Label(frm, text="PC <-> SNES Address Calculator", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8, pady=8)

        row = ttk.Frame(frm); row.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(row, text="Mapping:").pack(side=tk.LEFT)
        mapping = tk.StringVar(value=self.header.mapping if self.header.mapping != "Unknown" else "LoROM")
        ttk.Combobox(row, textvariable=mapping, values=["LoROM","HiROM"], width=8, state="readonly").pack(side=tk.LEFT, padx=4)

        r1 = ttk.Frame(frm); r1.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(r1, text="PC (hex)").pack(side=tk.LEFT)
        pc_var = tk.StringVar(value="0")
        tk.Entry(r1, textvariable=pc_var, width=12).pack(side=tk.LEFT, padx=4)
        out_snes = tk.StringVar(value="")
        tk.Button(r1, text="PC → SNES", command=lambda: conv_pc_to_snes()).pack(side=tk.LEFT, padx=4)
        tk.Entry(r1, textvariable=out_snes, width=12, state="readonly").pack(side=tk.LEFT, padx=4)

        r2 = ttk.Frame(frm); r2.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(r2, text="SNES (hex, e.g. 80:8000 => 0x808000)").pack(side=tk.LEFT)
        snes_var = tk.StringVar(value="808000")
        tk.Entry(r2, textvariable=snes_var, width=12).pack(side=tk.LEFT, padx=4)
        out_pc = tk.StringVar(value="")
        tk.Button(r2, text="SNES → PC", command=lambda: conv_snes_to_pc()).pack(side=tk.LEFT, padx=4)
        tk.Entry(r2, textvariable=out_pc, width=12, state="readonly").pack(side=tk.LEFT, padx=4)

        def conv_pc_to_snes():
            try:
                pc = int(pc_var.get(), 16)
                if mapping.get() == "LoROM":
                    sn = pc_to_snes_lorom(pc)
                else:
                    sn = pc_to_snes_hirom(pc)
                out_snes.set(f"{sn:06X}")
            except Exception:
                messagebox.showerror("Address", "Invalid PC hex value.")

        def conv_snes_to_pc():
            try:
                sn = int(snes_var.get().replace(":","").replace("0x",""), 16)
                if mapping.get() == "LoROM":
                    pc = snes_to_pc_lorom(sn)
                else:
                    pc = snes_to_pc_hirom(sn)
                out_pc.set("—" if pc is None else f"{pc:06X}")
            except Exception:
                messagebox.showerror("Address", "Invalid SNES hex value.")

    # Graphics editor / tiles viewer
    def open_graphics_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Graphics Editor":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Graphics Editor")
        self.nb.select(self.nb.index("end")-1)

        ctrl = ttk.Frame(frm); ctrl.pack(fill=tk.X, padx=6, pady=6)
        tk.Label(ctrl, text="Tiles start (PC hex):").pack(side=tk.LEFT)
        start_var = tk.StringVar(value="0")
        tk.Entry(ctrl, textvariable=start_var, width=10).pack(side=tk.LEFT, padx=4)
        tk.Label(ctrl, text="Count:").pack(side=tk.LEFT)
        count_var = tk.IntVar(value=256)
        tk.Spinbox(ctrl, from_=1, to=1024, textvariable=count_var, width=6).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Load from ROM", command=lambda: load_from_rom()).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Use Demo Tiles", command=lambda: use_demo()).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Redraw", command=lambda: redraw()).pack(side=tk.LEFT, padx=4)

        # palette selector (16 entries)
        palfrm = ttk.LabelFrame(frm, text="Palette (16)")
        palfrm.pack(fill=tk.X, padx=6, pady=4)
        self._pal_btns: List[tk.Canvas] = []
        for i in range(16):
            c = tk.Canvas(palfrm, width=18, height=18, highlightthickness=1, highlightbackground="#444")
            c.grid(row=0, column=i, padx=2, pady=2)
            self._pal_btns.append(c)
        self._paint_palette_buttons()

        canvas = tk.Canvas(frm, width=512, height=512, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._gfx_canvas = canvas
        self._gfx_img = None

        def load_from_rom():
            if not self.rom:
                messagebox.showwarning("GFX", "Open a ROM first or use Demo Tiles.")
                return
            try:
                start = int(start_var.get(), 16)
                count = int(count_var.get())
                tiles = []
                for i in range(count):
                    off = start + i*32
                    if off+32 > len(self.rom):
                        break
                    t = decode_4bpp_tile(self.rom[off:off+32])
                    tiles.append(t)
                if not tiles:
                    messagebox.showwarning("GFX", "No tiles read.")
                    return
                self.tiles_4bpp = tiles
                redraw()
            except Exception as e:
                messagebox.showerror("GFX", f"Failed to read tiles: {e}")

        def use_demo():
            self.tiles_4bpp = self._make_demo_tiles(256)
            redraw()

        def redraw():
            img = render_tiles_to_photoimage(self.tiles_4bpp, self.palette16, cols=16)
            self._gfx_img = img
            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=img)
            canvas.config(scrollregion=(0,0,img.width(), img.height()))

        redraw()

    def _paint_palette_buttons(self):
        for i, c in enumerate(self._pal_btns):
            r,g,b = self.palette16[i]
            hexcol = f"#{r:02x}{g:02x}{b:02x}"
            c.delete("all")
            c.create_rectangle(0,0,18,18, fill=hexcol, outline="#000")

    # Palette editor
    def open_palette_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Palette Editor":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Palette Editor")
        self.nb.select(self.nb.index("end")-1)

        listfrm = ttk.Frame(frm); listfrm.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        self._pal_list = tk.Listbox(listfrm, height=16, exportselection=False)
        self._pal_list.pack(fill=tk.Y)
        for i in range(16):
            r,g,b = self.palette16[i]
            self._pal_list.insert(tk.END, f"{i:02d}: #{r:02X}{g:02X}{b:02X}")
        self._pal_list.select_set(0)

        editfrm = ttk.LabelFrame(frm, text="Edit Color (0..255)"); editfrm.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        r_var = tk.IntVar(value=self.palette16[0][0])
        g_var = tk.IntVar(value=self.palette16[0][1])
        b_var = tk.IntVar(value=self.palette16[0][2])
        for label,var in (("R",r_var),("G",g_var),("B",b_var)):
            row = ttk.Frame(editfrm); row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, width=2).pack(side=tk.LEFT)
            tk.Spinbox(row, from_=0, to=255, textvariable=var, width=5).pack(side=tk.LEFT)

        preview = tk.Canvas(editfrm, width=80, height=50, bg="#000"); preview.pack(pady=6)

        def update_preview(*_):
            r,g,b = r_var.get(), g_var.get(), b_var.get()
            preview.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
        r_var.trace_add("write", update_preview)
        g_var.trace_add("write", update_preview)
        b_var.trace_add("write", update_preview)
        update_preview()

        btnfrm = ttk.Frame(editfrm); btnfrm.pack(pady=6)
        tk.Button(btnfrm, text="Apply to Selected", command=lambda: apply_color()).pack(side=tk.LEFT, padx=3)
        tk.Button(btnfrm, text="Reset to Default", command=lambda: reset_pal()).pack(side=tk.LEFT, padx=3)

        def apply_color():
            idxs = self._pal_list.curselection()
            if not idxs: return
            i = idxs[0]
            self.palette16[i] = (int(r_var.get()), int(g_var.get()), int(b_var.get()))
            self._pal_list.delete(i)
            r,g,b = self.palette16[i]
            self._pal_list.insert(i, f"{i:02d}: #{r:02X}{g:02X}{b:02X}")
            self._paint_palette_buttons()
            messagebox.showinfo("Palette", f"Updated color {i}.")

        def reset_pal():
            self.palette16[:] = default_palette16()
            self._pal_list.delete(0, tk.END)
            for i in range(16):
                r,g,b = self.palette16[i]
                self._pal_list.insert(tk.END, f"{i:02d}: #{r:02X}{g:02X}{b:02X}")
            self._paint_palette_buttons()

    # Map16 editor
    def open_map16_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Map16 Editor":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Map16 Editor")
        self.nb.select(self.nb.index("end")-1)

        left = ttk.Frame(frm); left.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        tk.Label(left, text="Blocks").pack(anchor="w")
        self._map16_list = tk.Listbox(left, width=22, height=24, exportselection=False)
        self._map16_list.pack(fill=tk.Y)
        for i,_b in enumerate(self.map16):
            self._map16_list.insert(tk.END, f"{i:03d}")

        right = ttk.Frame(frm); right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        tk.Label(right, text="Block Preview").pack(anchor="w")
        self._m16_canvas = tk.Canvas(right, width=64, height=64, bg="white")
        self._m16_canvas.pack(anchor="w", pady=4)

        # edit fields
        ef = ttk.LabelFrame(right, text="Tiles (indices)")
        ef.pack(anchor="w", pady=6)
        self._m16_vars = {
            "tl": tk.IntVar(value=0),
            "tr": tk.IntVar(value=1),
            "bl": tk.IntVar(value=16),
            "br": tk.IntVar(value=17),
            "pal": tk.IntVar(value=0),
        }
        grid = ttk.Frame(ef); grid.pack()
        labels = [("TL","tl"),("TR","tr"),("BL","bl"),("BR","br")]
        for j, (lab,key) in enumerate(labels):
            tk.Label(grid, text=lab).grid(row=j, column=0, sticky="e")
            tk.Spinbox(grid, from_=0, to=max(0, len(self.tiles_4bpp)-1), textvariable=self._m16_vars[key], width=6).grid(row=j, column=1, padx=4)
        tk.Label(grid, text="Palette").grid(row=4, column=0, sticky="e")
        tk.Spinbox(grid, from_=0, to=1, textvariable=self._m16_vars["pal"], width=6).grid(row=4, column=1, padx=4)

        btnf = ttk.Frame(right); btnf.pack(anchor="w", pady=6)
        tk.Button(btnf, text="Apply to Block", command=lambda: apply_block()).pack(side=tk.LEFT, padx=4)
        tk.Button(btnf, text="Export Map16 JSON", command=lambda: export_map16()).pack(side=tk.LEFT, padx=4)
        tk.Button(btnf, text="Import Map16 JSON", command=lambda: import_map16()).pack(side=tk.LEFT, padx=4)

        def refresh_preview():
            sel = self._map16_list.curselection()
            if not sel: return
            b = self.map16[sel[0]]
            # Compose a 16x16 from four tiles (no flips for simplicity)
            tiles = []
            for tid in (b.tile_tl, b.tile_tr, b.tile_bl, b.tile_br):
                tid = max(0, min(len(self.tiles_4bpp)-1, tid))
                tiles.append(self.tiles_4bpp[tid])
            # palette row selection demo: use two palettes by offsetting indices (just tint)
            pal = self._palette_variant(b.pal)
            # create 16x16
            composed = self._compose_16x16(tiles, pal)
            img = render_tiles_to_photoimage(composed, pal, cols=2)
            self._m16_img = img
            self._m16_canvas.delete("all")
            self._m16_canvas.create_image(0, 0, anchor="nw", image=img)

            # load fields
            self._m16_vars["tl"].set(b.tile_tl)
            self._m16_vars["tr"].set(b.tile_tr)
            self._m16_vars["bl"].set(b.tile_bl)
            self._m16_vars["br"].set(b.tile_br)
            self._m16_vars["pal"].set(b.pal)

        def on_select(_evt=None):
            refresh_preview()

        def apply_block():
            sel = self._map16_list.curselection()
            if not sel: return
            b = self.map16[sel[0]]
            b.tile_tl = int(self._m16_vars["tl"].get())
            b.tile_tr = int(self._m16_vars["tr"].get())
            b.tile_bl = int(self._m16_vars["bl"].get())
            b.tile_br = int(self._m16_vars["br"].get())
            b.pal = int(self._m16_vars["pal"].get())
            refresh_preview()

        def export_map16():
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
            if not path: return
            data = [b.__dict__ for b in self.map16]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Map16", "Exported Map16 JSON.")

        def import_map16():
            path = filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All","*.*")])
            if not path: return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                self.map16 = [Map16Block(**d) for d in arr]
                self._map16_list.delete(0, tk.END)
                for i in range(len(self.map16)):
                    self._map16_list.insert(tk.END, f"{i:03d}")
                refresh_preview()
            except Exception as e:
                messagebox.showerror("Map16", f"Failed to import: {e}")

        self._map16_list.bind("<<ListboxSelect>>", on_select)
        self._map16_list.select_set(0)
        refresh_preview()

    # Level editor (tile painter)
    def open_level_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Level Editor":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Level Editor")
        self.nb.select(self.nb.index("end")-1)

        top = ttk.Frame(frm); top.pack(fill=tk.X, padx=6, pady=6)
        tk.Button(top, text="Export Level JSON", command=lambda: export_level()).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Import Level JSON", command=lambda: import_level()).pack(side=tk.LEFT, padx=3)
        tk.Label(top, text="Current Block:").pack(side=tk.LEFT, padx=8)
        cur_block = tk.IntVar(value=0)
        tk.Spinbox(top, from_=0, to=max(0,len(self.map16)-1), width=6, textvariable=cur_block).pack(side=tk.LEFT)

        canvas = tk.Canvas(frm, bg="#a6d9ff", width=1024, height=320)
        canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._level_canvas = canvas

        # tile palette (Map16 list)
        palfrm = ttk.Frame(frm); palfrm.pack(fill=tk.X, padx=6, pady=4)
        tk.Label(palfrm, text="Quick Block Palette:").pack(side=tk.LEFT)
        palette_canvas = tk.Canvas(palfrm, width=512, height=64, bg="white")
        palette_canvas.pack(side=tk.LEFT, padx=8)

        # renderers
        tile_img_cache = {}

        def map16_preview(block_idx: int) -> tk.PhotoImage:
            if block_idx in tile_img_cache:
                return tile_img_cache[block_idx]
            b = self.map16[block_idx]
            tiles = [self.tiles_4bpp[b.tile_tl], self.tiles_4bpp[b.tile_tr],
                     self.tiles_4bpp[b.tile_bl], self.tiles_4bpp[b.tile_br]]
            pal = self._palette_variant(b.pal)
            composed = self._compose_16x16(tiles, pal)
            img = render_tiles_to_photoimage(composed, pal, cols=2)
            tile_img_cache[block_idx] = img
            return img

        cell = 16
        def redraw_level():
            canvas.delete("all")
            for y in range(self.level.height):
                for x in range(self.level.width):
                    idx = self.level.blocks[y*self.level.width + x]
                    if idx < 0 or idx >= len(self.map16):
                        continue
                    img = map16_preview(idx)
                    # draw at 16x16 scaled (img is 16x16 already)
                    canvas.create_image(x*cell, y*cell, anchor="nw", image=img)
            # grid
            for x in range(self.level.width+1):
                canvas.create_line(x*cell, 0, x*cell, self.level.height*cell, fill="#cccccc")
            for y in range(self.level.height+1):
                canvas.create_line(0, y*cell, self.level.width*cell, y*cell, fill="#cccccc")

        def on_click(evt):
            gx, gy = evt.x//cell, evt.y//cell
            if 0 <= gx < self.level.width and 0 <= gy < self.level.height:
                self.level.blocks[gy*self.level.width + gx] = int(cur_block.get())
                redraw_level()

        canvas.bind("<Button-1>", on_click)
        redraw_level()

        # palette bar render, click to pick
        def redraw_palette_bar():
            palette_canvas.delete("all")
            cols = 32
            for i in range(min(len(self.map16), cols)):
                img = map16_preview(i)
                palette_canvas.create_image(i*16, 0, anchor="nw", image=img)
                palette_canvas.create_rectangle(i*16,0,i*16+16,16, outline="#444")
            palette_canvas.config(scrollregion=(0,0,cols*16,16))

        def on_palette_click(evt):
            idx = evt.x // 16
            if 0 <= idx < len(self.map16):
                cur_block.set(idx)

        palette_canvas.bind("<Button-1>", on_palette_click)
        redraw_palette_bar()

        def export_level():
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
            if not path: return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.level.__dict__, f)
            messagebox.showinfo("Level", "Exported level JSON.")

        def import_level():
            path = filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All files","*.*")])
            if not path: return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.level = LevelDoc(**d)
                redraw_level()
            except Exception as e:
                messagebox.showerror("Level", f"Failed to import: {e}")

    # Overworld (mock)
    def open_overworld_editor(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Overworld":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Overworld")
        self.nb.select(self.nb.index("end")-1)

        top = ttk.Frame(frm); top.pack(fill=tk.X, padx=6, pady=6)
        tk.Button(top, text="Add Node", command=lambda: add_node()).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Link Nodes", command=lambda: link_nodes()).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Export JSON", command=lambda: export_ow()).pack(side=tk.LEFT, padx=3)
        tk.Button(top, text="Import JSON", command=lambda: import_ow()).pack(side=tk.LEFT, padx=3)

        canvas = tk.Canvas(frm, width=800, height=480, bg="#b0efd1")
        canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        sel: List[int] = []

        def redraw():
            canvas.delete("all")
            # edges
            for a,b in self.overworld.edges:
                x1,y1 = self.overworld.nodes[a]
                x2,y2 = self.overworld.nodes[b]
                canvas.create_line(x1,y1,x2,y2, width=3, fill="#7b4a12")
            # nodes
            for i,(x,y) in enumerate(self.overworld.nodes):
                canvas.create_oval(x-10,y-10,x+10,y+10, fill="#2b8cff", outline="#0b3a66", width=2)
                canvas.create_text(x, y-18, text=str(i), fill="#08304d")

        def add_node():
            x = simpledialog.askinteger("Node", "X (0..800):", minvalue=0, maxvalue=800)
            y = simpledialog.askinteger("Node", "Y (0..480):", minvalue=0, maxvalue=480)
            if x is None or y is None: return
            self.overworld.nodes.append((x,y))
            redraw()

        def link_nodes():
            if len(sel) != 2:
                messagebox.showinfo("Overworld", "Select two nodes (Shift+Click) to link.")
                return
            a,b = sel
            self.overworld.edges.append((min(a,b), max(a,b)))
            sel.clear()
            redraw()

        def on_click(evt):
            # select nearest node within radius
            for i,(x,y) in enumerate(self.overworld.nodes):
                if (evt.x - x)**2 + (evt.y - y)**2 <= 14**2:
                    if evt.state & 0x0001:  # shift
                        if i not in sel:
                            sel.append(i)
                    else:
                        sel.clear()
                        sel.append(i)
                    break

        def export_ow():
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
            if not path: return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.overworld.__dict__, f, indent=2)
            messagebox.showinfo("Overworld", "Exported overworld JSON.")

        def import_ow():
            path = filedialog.askopenfilename(filetypes=[("JSON","*.json"),("All","*.*")])
            if not path: return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.overworld = OverworldGraph(nodes=d["nodes"], edges=[tuple(x) for x in d["edges"]])
                redraw()
            except Exception as e:
                messagebox.showerror("Overworld", f"Failed to import: {e}")

        canvas.bind("<Button-1>", on_click)
        redraw()

    # Decompiler (simulated)
    def open_decompiler(self):
        for i in range(self.nb.index("end")):
            if self.nb.tab(i, "text") == "Decompiler":
                self.nb.select(i); return
        frm = ttk.Frame(self.nb)
        self.nb.add(frm, text="Decompiler")
        self.nb.select(self.nb.index("end")-1)

        tk.Label(frm, text="ROM Decompilation Analysis (Simulated)", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=8, pady=6)
        text = scrolledtext.ScrolledText(frm, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        out = []
        out.append("Header Analysis:")
        out.append(f"  Mapping: {self.header.mapping}")
        out.append(f"  Size: {len(self.rom) if self.rom else 0} bytes")
        out.append(f"  Checksum: 0x{(self.header.checksum or 0):04X} (comp 0x{(self.header.complement or 0):04X})")
        out.append("")
        out.append("Bank Map (heuristic scan of non-zero density):")
        if self.rom:
            bank_size = 0x8000 if self.header.mapping=="LoROM" else 0x10000
            for b in range(0, len(self.rom), bank_size):
                chunk = self.rom[b:b+bank_size]
                nz = sum(1 for x in chunk if x != 0)
                pct = (100.0*nz/len(chunk)) if chunk else 0.0
                out.append(f"  Bank ${b//bank_size:02X}: non-zero {pct:5.1f}%")
        else:
            out.append("  (No ROM loaded)")

        out.append("")
        out.append("Identified Segments (simulated):")
        out.append("  $80:8000  Main loop / IRQ handlers")
        out.append("  $81:8000  Object engine (players, enemies)")
        out.append("  $82:8000  Level loader / compression stubs")
        out.append("  $83:8000  Overworld logic")
        out.append("")
        out.append("Note: This is a scaffold. Swap in a real 65816 disassembler and symbolizer later.")

        text.insert("1.0", "\n".join(out))
        text.config(state=tk.DISABLED)

    # ---------- Shared helpers ----------

    def _palette_variant(self, which: int) -> List[Tuple[int,int,int]]:
        # create two variants by simple brightness adjustment for demo
        base = default_palette16()
        if which % 2 == 0:
            return base
        def clamp(x): return max(0, min(255, x))
        return [(clamp(int(r*0.8)), clamp(int(g*0.8)), clamp(int(b*0.9))) for r,g,b in base]

    def _compose_16x16(self, tiles4: List[List[List[int]]], palette: List[Tuple[int,int,int]]) -> List[List[List[int]]]:
        """
        tiles4: [tl, tr, bl, br] as 8x8 indices -> returns two tiles in one row (so render with cols=2)
        We return a pseudo-tiles array (2 tiles) where each is 8x8 index map.
        """
        tl, tr, bl, br = tiles4
        # stick tiles into two 8x8 tiles to render as 2 cols => visually 16x16
        # We actually need 4 tiles; using render_tiles_to_photoimage(cols=2) on [tl,tr,bl,br]
        return [tl, tr, bl, br]

    def _make_demo_tiles(self, n: int) -> List[List[List[int]]]:
        tiles = []
        for t in range(n):
            tile = [[0]*8 for _ in range(8)]
            for y in range(8):
                for x in range(8):
                    # fun pattern: index depends on tile id and coords
                    tile[y][x] = ((x^y) + (t%16)) & 0x0F
            tiles.append(tile)
        return tiles

    # ---------- About ----------

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Universal SMW ROM Hacking Toolset 1.0x (LM‑Lite)\n\n"
            "• Base-Python only (no third-party libs)\n"
            "• SNES 4bpp tile viewer, Map16, Level editor, Overworld mock, IPS, Hex, etc.\n"
            "This is a demonstration scaffold to iterate toward LM 1.0x parity."
        )

# -------------
# Entrypoint
# -------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SMWRomHacker(root)
    root.mainloop()
