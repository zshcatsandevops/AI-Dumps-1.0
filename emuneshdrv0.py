#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TinyNES — single-file educational NES emulator skeleton (program.py)

What you get today (working, single file):
  • Tkinter window with a 256x240 "screen" (scalable)
  • .nes (iNES) ROM loader (Mapper 0 / NROM only)
  • CHR Tile Viewer that renders tiles from the cartridge immediately
  • Controller input wiring & CPU/PPU/APU scaffolding
  • Clean architecture (Cartridge, Bus, CPU, PPU) ready for extension

What is stubbed / partial:
  • 6502 CPU core: instruction table mostly stubbed (enough structure to grow)
  • PPU: functional CHR viewer; no scanline-level rendering yet
  • APU: stub

Run:
  $ python3 program.py
  File → Open ROM… (choose a .nes) → View → CHR Tiles (default) or leave screen blank
  Hotkeys (prewired for future CPU loop):
    Arrows = D-Pad, Z = A, X = B, Right Shift = Select, Enter = Start
"""

import os
import sys
import time
import struct
import tkinter as tk
from tkinter import filedialog, messagebox

NES_WIDTH  = 256
NES_HEIGHT = 240

def rgb(r, g, b) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

# Simple 2-bit grayscale for tile viewer (placeholder for real NES palette)
PALETTE_GRAY = [
    rgb(0, 0, 0),
    rgb(96, 96, 96),
    rgb(192, 192, 192),
    rgb(255, 255, 255),
]

# -----------------------------
# Cartridge & Mapper 0 (NROM)
# -----------------------------
class Cartridge:
    def __init__(self):
        self.path = None
        self.mapper = 0
        self.mirroring = "horizontal"
        self.battery = False
        self.trainer_present = False
        self.four_screen = False

        self.prg_rom = bytearray()
        self.chr = bytearray()
        self.chr_is_ram = False
        self.prg_ram = bytearray(8 * 1024)  # default if header byte is 0
        self.prg_banks = 0
        self.chr_banks = 0
        self.ines2 = False

    @staticmethod
    def from_file(path: str):
        with open(path, "rb") as f:
            data = f.read()
        return Cartridge.from_bytes(data, path)

    @staticmethod
    def from_bytes(data: bytes, path: str = "<memory>"):
        c = Cartridge()
        c.path = path
        if len(data) < 16 or data[0:4] != b"NES\x1a":
            raise ValueError("Not an iNES file (missing NES<1A> header).")

        header = data[:16]
        prg_count = header[4]            # number of 16KB PRG ROM banks
        chr_count = header[5]            # number of 8KB CHR ROM banks (0 → CHR RAM)
        flags6    = header[6]
        flags7    = header[7]
        # iNES 2.0 detection (simple check): if bits 2-3 of byte 7 are 2 (binary 10)
        c.ines2 = ((flags7 & 0x0C) == 0x08)

        c.mapper = ((flags7 & 0xF0) | (flags6 >> 4)) & 0xFF
        c.mirroring       = "vertical" if (flags6 & 0x01) else "horizontal"
        c.battery         = bool(flags6 & 0x02)
        c.trainer_present = bool(flags6 & 0x04)
        c.four_screen     = bool(flags6 & 0x08)
        c.prg_banks       = prg_count
        c.chr_banks       = chr_count

        offset = 16
        if c.trainer_present:
            if len(data) < offset + 512:
                raise ValueError("Header says trainer present but file is too small.")
            offset += 512  # skip trainer

        prg_size = prg_count * 16 * 1024
        chr_size = chr_count * 8 * 1024

        if len(data) < offset + prg_size + chr_size:
            raise ValueError("File too small for declared PRG/CHR sizes.")

        c.prg_rom = bytearray(data[offset:offset+prg_size])
        offset += prg_size

        if chr_size == 0:
            # CHR RAM (8KB default)
            c.chr_is_ram = True
            c.chr = bytearray(8 * 1024)
        else:
            c.chr_is_ram = False
            c.chr = bytearray(data[offset:offset+chr_size])

        return c

    # CPU PRG ROM read mapping (Mapper 0)
    def cpu_read(self, addr: int) -> int:
        if addr < 0x8000 or addr > 0xFFFF:
            return 0x00
        index = addr - 0x8000
        if self.prg_banks == 1:
            # Mirror 16KB bank across 32KB space
            index %= 0x4000
        if index < len(self.prg_rom):
            return self.prg_rom[index]
        return 0x00

    def cpu_write(self, addr: int, value: int):
        # Mapper 0 has no PRG registers; ignore writes to ROM space.
        pass

    # PPU Pattern table (CHR) read/write
    def chr_read(self, addr: int) -> int:
        addr &= 0x1FFF
        if addr < len(self.chr):
            return self.chr[addr]
        return 0

    def chr_write(self, addr: int, value: int):
        if not self.chr_is_ram:
            return
        addr &= 0x1FFF
        if addr < len(self.chr):
            self.chr[addr] = value & 0xFF

# -----------------------------
# Bus (CPU memory map, controllers, PPU regs)
# -----------------------------
class Bus:
    def __init__(self, cartridge: Cartridge | None):
        self.cartridge = cartridge
        self.cpu_ram = bytearray(2 * 1024)  # $0000-$07FF, mirrored through $1FFF
        self.ppu = PPU(self)                # PPU needs bus/cartridge access
        self.apu = APUStub()
        # NES controllers: bits A, B, Select, Start, Up, Down, Left, Right
        self.controller_latch = [0, 0]
        self.controller_shift = [0, 0]
        self.controller_state = [0, 0]
        self.controller_strobe = 0

    def set_controller_bit(self, pad: int, bit_index: int, pressed: bool):
        if not (0 <= pad <= 1):
            return
        mask = 1 << bit_index
        if pressed:
            self.controller_state[pad] |= mask
        else:
            self.controller_state[pad] &= ~mask

    # CPU read/write (simplified)
    def cpu_read(self, addr: int) -> int:
        addr &= 0xFFFF
        if addr <= 0x1FFF:
            return self.cpu_ram[addr & 0x07FF]
        elif 0x2000 <= addr <= 0x3FFF:
            reg = 0x2000 + (addr & 7)
            return self.ppu.cpu_read(reg)
        elif addr == 0x4016:
            # Controller 1
            val = (self.controller_shift[0] & 1)
            self.controller_shift[0] >>= 1
            return 0x40 | val  # upper bits typically open bus; keep bit 6 set like some emus do
        elif addr == 0x4017:
            # Controller 2
            val = (self.controller_shift[1] & 1)
            self.controller_shift[1] >>= 1
            return 0x40 | val
        elif addr >= 0x8000:
            if self.cartridge is None:
                return 0
            return self.cartridge.cpu_read(addr)
        else:
            # APU/IO not implemented; return 0
            return 0

    def cpu_write(self, addr: int, value: int):
        addr &= 0xFFFF
        value &= 0xFF
        if addr <= 0x1FFF:
            self.cpu_ram[addr & 0x07FF] = value
        elif 0x2000 <= addr <= 0x3FFF:
            reg = 0x2000 + (addr & 7)
            self.ppu.cpu_write(reg, value)
        elif addr == 0x4014:
            # OAM DMA (stub)
            pass
        elif addr == 0x4016:
            # Controller strobe
            self.controller_strobe = value & 1
            if self.controller_strobe:
                # Latch current controller states into shift registers
                self.controller_shift[0] = self.controller_state[0]
                self.controller_shift[1] = self.controller_state[1]
        elif addr >= 0x8000 and self.cartridge is not None:
            self.cartridge.cpu_write(addr, value)
        else:
            # APU/IO (stub)
            pass

# -----------------------------
# PPU (stub + CHR tile viewer)
# -----------------------------
class PPU:
    def __init__(self, bus: Bus):
        self.bus = bus
        self.cartridge = bus.cartridge
        self.framebuffer = [[PALETTE_GRAY[0] for _ in range(NES_WIDTH)] for _ in range(NES_HEIGHT)]
        self.display_mode = "CHR"  # "CHR" or "BLANK"
        # Registers (stub)
        self.ppuctrl = 0
        self.ppumask = 0
        self.ppustatus = 0x80  # set vblank bit initially for simplicity
        self.oamaddr = 0
        self.ppuscroll = 0
        self.ppuaddr = 0
        self.ppudata_buffer = 0

    def cpu_read(self, reg: int) -> int:
        # Very stubby PPU registers for now
        if reg == 0x2002:  # PPUSTATUS
            val = self.ppustatus
            # Reading PPUSTATUS clears VBlank (bit 7)
            self.ppustatus &= 0x7F
            return val
        elif reg == 0x2007:  # PPUDATA
            # Return buffered value (stub)
            val = self.ppudata_buffer
            return val
        else:
            return 0

    def cpu_write(self, reg: int, value: int):
        if reg == 0x2000:
            self.ppuctrl = value
        elif reg == 0x2001:
            self.ppumask = value
        elif reg == 0x2003:
            self.oamaddr = value
        elif reg == 0x2005:
            self.ppuscroll = value
        elif reg == 0x2006:
            self.ppuaddr = value
        elif reg == 0x2007:
            # PPUDATA write (stub)
            self.ppudata_buffer = value
        # ignore the rest for this skeleton

    def render_blank(self):
        c = PALETTE_GRAY[0]
        for y in range(NES_HEIGHT):
            row = self.framebuffer[y]
            for x in range(NES_WIDTH):
                row[x] = c

    def render_chr_view(self):
        """Render CHR patterns as a 32x30 tile grid (fills full 256x240).
        Tiles wrap if cartridge has fewer than 960 tiles.
        """
        if self.cartridge is None:
            self.render_blank()
            return
        tiles = self.cartridge.chr
        if not tiles:
            self.render_blank()
            return

        tile_count = len(tiles) // 16  # 16 bytes per 8x8 tile (2 bitplanes)
        if tile_count == 0:
            self.render_blank()
            return

        # Iterate screen in tile space 32x30
        for ty in range(30):
            for tx in range(32):
                tile_index = (ty * 32 + tx) % tile_count
                base = tile_index * 16
                plane0 = tiles[base      : base + 8]
                plane1 = tiles[base + 8  : base + 16]
                # Draw this tile at (tx*8, ty*8)
                dst_y = ty * 8
                for row in range(8):
                    b0 = plane0[row]
                    b1 = plane1[row]
                    py = dst_y + row
                    if py >= NES_HEIGHT:
                        continue
                    out_row = self.framebuffer[py]
                    dst_x = tx * 8
                    # Decode 8 pixels from two bitplanes (MSB left)
                    for col in range(8):
                        bit = 7 - col
                        val = ((b0 >> bit) & 1) | (((b1 >> bit) & 1) << 1)
                        color = PALETTE_GRAY[val]
                        px = dst_x + col
                        if px < NES_WIDTH:
                            out_row[px] = color

    def render_frame(self):
        if self.display_mode == "CHR":
            self.render_chr_view()
        else:
            self.render_blank()

# -----------------------------
# CPU 6502 (scaffold)
# -----------------------------
class CPU6502:
    def __init__(self, bus: Bus):
        self.bus = bus
        # Registers
        self.a = 0
        self.x = 0
        self.y = 0
        self.sp = 0xFD
        self.p = 0x24   # IRQ disabled (I=1), unused bits set
        self.pc = 0xC000

        # Simple instruction map (very incomplete, skeleton)
        self.instructions = {
            0xEA: self.NOP,
            # Add more: A9 (LDA #imm), 8D (STA abs), 4C (JMP abs), etc.
        }

    # Flag helpers
    def set_z(self, v): self.p = (self.p & ~0x02) | (0x02 if v == 0 else 0)
    def set_n(self, v): self.p = (self.p & ~0x80) | (0x80 if (v & 0x80) else 0)

    def reset(self):
        # Read reset vector at $FFFC/$FFFD
        lo = self.bus.cpu_read(0xFFFC)
        hi = self.bus.cpu_read(0xFFFD)
        self.pc = (hi << 8) | lo
        self.sp = 0xFD
        self.p = 0x24

    def step(self, cycles: int = 1):
        """Execute a small number of instructions (stub)."""
        # For now we do nothing meaningful to keep UI responsive
        # Extend: fetch opcode, decode, execute, handle page crossings, cycles, etc.
        for _ in range(cycles):
            opcode = self.bus.cpu_read(self.pc)
            self.pc = (self.pc + 1) & 0xFFFF
            handler = self.instructions.get(opcode, self.NOP)
            handler()

    # --- Instructions (stubs)
    def NOP(self):
        # No operation
        pass

# -----------------------------
# APU Stub
# -----------------------------
class APUStub:
    def __init__(self):
        pass

# -----------------------------
# UI App (Tkinter)
# -----------------------------
class NESEmuApp:
    def __init__(self, scale: int = 3):
        self.root = tk.Tk()
        self.root.title("TinyNES (Skeleton) — program.py")
        self.scale = max(1, int(scale))

        self.cartridge: Cartridge | None = None
        self.bus: Bus | None = None
        self.cpu: CPU6502 | None = None
        self.running = False
        self.frame_interval_ms = int(1000 / 60)

        # Canvas + image
        self.canvas = tk.Canvas(self.root, width=NES_WIDTH*self.scale, height=NES_HEIGHT*self.scale, bd=0, highlightthickness=0)
        self.canvas.pack()
        self.photo = tk.PhotoImage(width=NES_WIDTH, height=NES_HEIGHT)
        self.photo_scaled = self.photo.zoom(self.scale, self.scale)
        self.image_id = self.canvas.create_image(0, 0, image=self.photo_scaled, anchor=tk.NW)

        # Status bar
        self.status_var = tk.StringVar(value="Open a ROM via File → Open ROM…  |  View → CHR Tiles to see graphics")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        self.status.pack(fill="x")

        self.build_menu()
        self.bind_keys()

        # Start with a blank framebuffer so window is not empty
        self.blank_framebuffer()

    # ----- UI boilerplate
    def build_menu(self):
        menubar = tk.Menu(self.root)

        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="Open ROM…", command=self.open_rom)
        m_file.add_separator()
        m_file.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=m_file)

        m_emul = tk.Menu(menubar, tearoff=0)
        m_emul.add_command(label="Run", command=self.run)
        m_emul.add_command(label="Pause", command=self.pause)
        m_emul.add_command(label="Reset", command=self.reset)
        menubar.add_cascade(label="Emulation", menu=m_emul)

        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_radiobutton(label="CHR Tiles (viewer)", command=lambda: self.set_display_mode("CHR"))
        m_view.add_radiobutton(label="Blank Screen",      command=lambda: self.set_display_mode("BLANK"))
        menubar.add_cascade(label="View", menu=m_view)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="About…", command=self.about)
        menubar.add_cascade(label="Help", menu=m_help)

        self.root.config(menu=menubar)

    def bind_keys(self):
        # NES buttons: A, B, Select, Start, Up, Down, Left, Right  → bit 0..7
        self.keymap = {
            "z":    (0, 0),  # A
            "x":    (0, 1),  # B
            "Shift_R": (0, 2),  # Select
            "Return":  (0, 3),  # Start
            "Up":    (0, 4),
            "Down":  (0, 5),
            "Left":  (0, 6),
            "Right": (0, 7),
        }
        self.root.bind("<KeyPress>", self.on_key)
        self.root.bind("<KeyRelease>", self.on_key)

    def about(self):
        messagebox.showinfo(
            "About TinyNES",
            "TinyNES (Skeleton) — educational, single-file NES emulator starter.\n"
            "• Loads .nes (iNES) Mapper 0\n"
            "• Shows CHR tiles immediately\n"
            "• CPU/PPU/APU skeleton to extend\n\n"
            "Save & extend freely. Built for tinkering."
        )

    def set_display_mode(self, mode: str):
        if self.bus is None:
            return
        mode = mode.upper()
        if mode.startswith("CHR"):
            self.bus.ppu.display_mode = "CHR"
        else:
            self.bus.ppu.display_mode = "BLANK"

    def status_info(self, text: str):
        self.status_var.set(text)

    # ----- ROM loading / emulator wiring
    def open_rom(self):
        path = filedialog.askopenfilename(
            title="Open .nes ROM",
            filetypes=[("iNES ROM", "*.nes"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            cart = Cartridge.from_file(path)
        except Exception as e:
            messagebox.showerror("Failed to open ROM", f"{e}")
            return

        if cart.mapper != 0:
            messagebox.showwarning(
                "Unsupported mapper (for now)",
                f"Mapper {cart.mapper} is not supported in this skeleton.\n"
                f"Try an NROM (Mapper 0) ROM or use CHR viewer."
            )

        self.cartridge = cart
        self.bus = Bus(cart)
        self.cpu = CPU6502(self.bus)
        self.cpu.reset()

        info = (
            f"ROM: {os.path.basename(path)} | "
            f"Mapper {cart.mapper} | PRG {cart.prg_banks*16}KB | "
            f"CHR {'RAM 8KB' if cart.chr_is_ram else f'{cart.chr_banks*8}KB'} | "
            f"Mirroring: {cart.mirroring}"
        )
        self.status_info(info)

        # Immediately render CHR tiles so user sees graphics
        self.update_frame()

    def run(self):
        if self.bus is None or self.cpu is None:
            self.status_info("Open a ROM first.")
            return
        self.running = True
        self.loop()

    def pause(self):
        self.running = False
        self.status_info("Paused.")

    def reset(self):
        if self.cpu:
            self.cpu.reset()
        self.update_frame()

    # ----- Controller input
    def on_key(self, event):
        if self.bus is None:
            return
        keysym = event.keysym
        pressed = (event.type == "2")  # KeyPress event type
        if keysym in self.keymap:
            pad, bit = self.keymap[keysym]
            self.bus.set_controller_bit(pad, bit, pressed)

    # ----- Main emulation loop (skeleton)
    def loop(self):
        if not self.running:
            return

        # In a real emulator you'd run ~29,780 CPU cycles per NTSC frame here.
        # We'll keep this skeleton light: step a tiny amount (no-ops) and paint.
        if self.cpu:
            self.cpu.step(100)  # placeholder

        self.update_frame()
        self.root.after(self.frame_interval_ms, self.loop)

    # ----- Rendering helpers
    def blank_framebuffer(self):
        fb = [[PALETTE_GRAY[0] for _ in range(NES_WIDTH)] for _ in range(NES_HEIGHT)]
        self.blit_framebuffer_to_photo(fb)

    def update_frame(self):
        if self.bus is None:
            self.blank_framebuffer()
            return
        # Render one frame from PPU's current display mode
        self.bus.ppu.render_frame()
        self.blit_framebuffer_to_photo(self.bus.ppu.framebuffer)

    def blit_framebuffer_to_photo(self, fb):
        # Push framebuffer (list of list of "#RRGGBB") into Tk PhotoImage.
        # For performance, we upload line-by-line.
        for y in range(NES_HEIGHT):
            # PhotoImage.put expects a tk color list string: "{#000000 #FFFFFF ...}"
            row_str = " ".join(fb[y])
            self.photo.put("{" + row_str + "}", to=(0, y))

        # Scale and display
        self.photo_scaled = self.photo.zoom(self.scale, self.scale)
        self.canvas.itemconfig(self.image_id, image=self.photo_scaled)

    def run_app(self):
        self.root.mainloop()

# -----------------------------
# Entry point
# -----------------------------
def main():
    # Optional: allow scale argument (e.g., python3 program.py 2)
    scale = 3
    if len(sys.argv) >= 2:
        try:
            scale = max(1, int(sys.argv[1]))
        except ValueError:
            pass
    app = NESEmuApp(scale=scale)
    app.run_app()

if __name__ == "__main__":
    main()
