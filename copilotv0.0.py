#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flames Co. SNES Pipeline Simulator — Tkinter Edition
program.py  (LoROM, unheadered by default)
Educational use only.

What this does:
--------------
- Builds a minimal, *valid* SNES LoROM (.sfc default).
- Inserts tiny 65816 boot code at $00:8000 that turns the screen on and loops.
- Writes a correct internal header at $00:FFC0 with proper field order.
- Computes and applies checksum & complement.
- Optionally includes a 512-byte copier header (produces .smc).
- Appends the contents of a chosen folder into ROM starting at 0x008100.

"""

import os, struct, sys, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

VERSION = "0.7-Tk"

REGIONS = {
    "NTSC-J": 0x00,
    "NTSC-U": 0x01,
    "PAL":    0x02,
}

BOOT_CODE = bytes([
    0x78, 0xD8,
    0xA2, 0xFF,
    0x9A,
    0xA9, 0x0F,
    0x8D, 0x00, 0x21,
    0x80, 0xFE
])

HDR_OFS       = 0x7FC0
RESET_VEC_OFS = 0x7FFC
BANK0_CODE_OFS= 0x0000
APPEND_START  = 0x008100

def ensure_size(buf: bytearray, size: int, fill: int = 0xFF):
    if len(buf) < size:
        buf += bytes([fill]) * (size - len(buf))

def next_pow2(n: int) -> int:
    if n <= 0x8000:
        return 0x8000
    p = 1
    while p < n:
        p <<= 1
    return p

def rom_size_exponent(size_bytes: int) -> int:
    if size_bytes & (size_bytes - 1):
        raise ValueError("ROM size must be power-of-two")
    return (size_bytes.bit_length() - 1) - 10

def write_header(rom: bytearray, title: str, region: str):
    ensure_size(rom, HDR_OFS + 32)
    title_bytes = title.encode("ascii", "ignore")[:21].ljust(21, b" ")
    rom[HDR_OFS:HDR_OFS+21] = title_bytes
    rom[HDR_OFS+0x15] = 0x20
    rom[HDR_OFS+0x16] = 0x00
    rom[HDR_OFS+0x17] = rom_size_exponent(len(rom))
    rom[HDR_OFS+0x18] = 0x00
    rom[HDR_OFS+0x19] = REGIONS.get(region, 0x01)
    rom[HDR_OFS+0x1A] = 0x33
    rom[HDR_OFS+0x1B] = 0x00
    struct.pack_into("<H", rom, HDR_OFS+0x1C, 0xFFFF)
    struct.pack_into("<H", rom, HDR_OFS+0x1E, 0x0000)

def write_reset_vector(rom: bytearray):
    ensure_size(rom, RESET_VEC_OFS + 2)
    rom[RESET_VEC_OFS] = 0x00
    rom[RESET_VEC_OFS+1] = 0x80

def place_boot(rom: bytearray):
    ensure_size(rom, BANK0_CODE_OFS + len(BOOT_CODE))
    rom[BANK0_CODE_OFS:BANK0_CODE_OFS+len(BOOT_CODE)] = BOOT_CODE

def append_folder(rom: bytearray, folder: Optional[str]):
    if not folder:
        return APPEND_START
    offset = APPEND_START
    for root, _, files in os.walk(folder):
        for name in files:
            try:
                data = open(os.path.join(root, name), "rb").read()
                ensure_size(rom, offset + len(data))
                rom[offset:offset+len(data)] = data
                offset += len(data)
            except Exception as e:
                print("Skipping", name, e, file=sys.stderr)
    return offset

def apply_checksum(rom: bytearray):
    total = sum(rom) & 0xFFFF
    checksum = total
    complement = checksum ^ 0xFFFF
    struct.pack_into("<H", rom, HDR_OFS+0x1C, complement)
    struct.pack_into("<H", rom, HDR_OFS+0x1E, checksum)

def build_rom(folder, region, title, include_header, out_path):
    rom = bytearray()
    place_boot(rom)
    write_reset_vector(rom)
    end = append_folder(rom, folder)
    min_needed = max(end, RESET_VEC_OFS+2, HDR_OFS+32, 0x8000)
    ensure_size(rom, next_pow2(min_needed))
    write_header(rom, title, region)
    apply_checksum(rom)
    payload = (b"\x00"*512 + rom) if include_header else bytes(rom)
    with open(out_path, "wb") as f:
        f.write(payload)

def run_gui():
    root = tk.Tk()
    root.title(f"Flames Co. SNES Pipeline Simulator {VERSION}")
    root.geometry("460x260")
    root.resizable(False, False)
    try: root.eval('tk::PlaceWindow . center')
    except: pass

    frm = ttk.Frame(root, padding=12); frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="SNES LoROM Builder", font=("Arial",14,"bold")).pack(pady=(0,8))

    title_var = tk.StringVar(value="FlamesCoSim")
    ttk.Label(frm, text="ROM Title:").pack()
    ttk.Entry(frm, textvariable=title_var).pack()

    region_var = tk.StringVar(value="NTSC-U")
    ttk.Label(frm, text="Region:").pack(pady=(6,0))
    ttk.Combobox(frm, textvariable=region_var, values=list(REGIONS.keys()), state="readonly").pack()

    copier_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm, text="Include copier header (.smc)", variable=copier_var).pack(pady=6)

    folder_var = tk.StringVar(value="")
    ttk.Label(frm, text="Source folder (optional):").pack()
    ttk.Entry(frm, textvariable=folder_var, width=40).pack()
    ttk.Button(frm, text="Browse…", command=lambda: folder_var.set(filedialog.askdirectory() or folder_var.get())).pack(pady=4)

    def on_build():
        folder = folder_var.get().strip() or None
        region = region_var.get() or "NTSC-U"
        title = title_var.get().strip() or "FlamesCoSim"
        include_hdr = copier_var.get()
        ext = ".smc" if include_hdr else ".sfc"
        out_file = filedialog.asksaveasfilename(defaultextension=ext, initialfile=f"{title}_{region}{ext}")
        if not out_file: return
        try:
            build_rom(folder, region, title, include_hdr, out_file)
            messagebox.showinfo("Done", f"ROM built!\n\nTitle: {title}\nRegion: {region}\nFile: {out_file}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    ttk.Button(frm, text="Build ROM", command=on_build).pack(pady=10)
    ttk.Button(frm, text="Exit", command=root.destroy).pack()

    root.mainloop()

if __name__ == "__main__":
    run_gui()
