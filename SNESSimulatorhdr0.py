#!/usr/bin/env python3
# Flames Co. SNES Pipeline Simulator 0.7-infdev
# by CatSama + GPT-5
#
# Builds a SNES .smc ROM that boots (minimal code)
# and appends all files from a chosen folder into the ROM.
# Educational only!

import os, struct, tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk

VERSION = "0.7-infdev"
REGIONS = {
    "NTSC-J": 0x00,
    "NTSC-U": 0x01,
    "PAL":    0x02
}

# --- Minimal boot program (65816 machine code at $8000) ---
BOOT_CODE = bytes([
    0x78,             # SEI
    0xD8,             # CLD
    0xA2, 0xFF, 0x1F, # LDX #$1FFF
    0x9A,             # TXS
    0xA9, 0x0F,       # LDA #$0F (screen on, bright)
    0x8D, 0x00, 0x21, # STA $2100 (INIDISP)
    0x80, 0xFE        # BRA Forever
])

def make_header(title: str, region: str) -> bytes:
    """Create a 32-byte SNES LoROM header."""
    title_bytes = title.encode("ascii", "ignore")[:21].ljust(21, b" ")
    map_mode = 0x20      # LoROM
    rom_size = 0x0A      # ~1Mbit
    sram_size = 0x00     # no SRAM
    region_code = REGIONS.get(region, 0x01)  # default NTSC-U
    license_code = 0x33
    version = 0x00
    checksum_complement = 0xFFFF
    checksum = 0x0000

    header = (
        title_bytes +
        bytes([map_mode, rom_size, sram_size, region_code, license_code, version]) +
        struct.pack("<H", checksum_complement) +
        struct.pack("<H", checksum)
    )
    return header

def build_rom(folder, region, out_path):
    # base ROM size (512KB min, padded)
    rom_size = 512 * 1024
    rom = bytearray([0xFF] * rom_size)

    # Insert boot code at $8000
    rom[0x8000:0x8000+len(BOOT_CODE)] = BOOT_CODE

    # Insert header at 0x7FC0
    header = make_header("FlamesCoSim", region)
    rom[0x7FC0:0x7FC0+len(header)] = header

    # Set reset vector ($FFFC-$FFFD) → $8000
    rom[0x7FFC] = 0x00
    rom[0x7FFD] = 0x80

    # Append folder file contents starting after boot code
    offset = 0x8100
    for root, _, files in os.walk(folder):
        for f in files:
            try:
                with open(os.path.join(root, f), "rb") as infile:
                    data = infile.read()
                rom[offset:offset+len(data)] = data
                offset += len(data)
            except Exception as e:
                print("Skipping", f, ":", e)

    # Save
    with open(out_path, "wb") as f:
        f.write(rom)

def run_pipeline():
    folder = filedialog.askdirectory(title="Pick Source Folder")
    if not folder:
        return

    region = region_var.get()
    if not region:
        region = "NTSC-U"

    out_path = os.path.join(folder, f"FlamesCoSim_{region}.smc")
    build_rom(folder, region, out_path)

    messagebox.showinfo("Pipeline Complete",
        f"ROM built!\nRegion: {region}\nOutput: {out_path}")

def main():
    global region_var

    root = tk.Tk()
    root.title(f"Flames Co. SNES Pipeline Simulator {VERSION}")
    root.geometry("400x200")
    root.resizable(False, False)  # Disable maximize
    root.eval('tk::PlaceWindow . center')

    ttk.Label(root, text="SNES Pipeline Builder", font=("Arial", 14, "bold")).pack(pady=10)

    ttk.Label(root, text="Select Region:").pack(pady=5)
    region_var = tk.StringVar(value="NTSC-U")
    ttk.Combobox(root, textvariable=region_var, values=list(REGIONS.keys()), state="readonly").pack()

    ttk.Button(root, text="Build ROM", command=run_pipeline).pack(pady=20)
    ttk.Button(root, text="Exit", command=root.destroy).pack()

    root.mainloop()

if __name__ == "__main__":
    main()
