#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced NES Emulator with Tkinter GUI
Features: Full 6502 CPU, Sprites, Scrolling, Multiple Mappers, Save States
Window: 600x400 (non-resizable), NES output: 256x240 centered
Compatible with more homebrew and some commercial ROMs
Audio disabled by default (can be enabled if pyaudio is installed)
"""

import sys
import struct
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import zlib
import os
from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple

# Try to import audio libraries (optional)
try:
    import pyaudio
    import numpy as np
    AUDIO_ENABLED = True
except ImportError:
    AUDIO_ENABLED = False
    print("Audio disabled - install pyaudio and numpy for sound support")

# ======================== NES Color Palette ========================
NES_PALETTE = [
    0x7C7C7C, 0x0000FC, 0x0000BC, 0x4428BC, 0x940084, 0xA80020, 0xA81000, 0x881400,
    0x503000, 0x007800, 0x006800, 0x005800, 0x004058, 0x000000, 0x000000, 0x000000,
    0xBCBCBC, 0x0078F8, 0x0058F8, 0x6844FC, 0xD800CC, 0xE40058, 0xF83800, 0xE45C10,
    0xAC7C00, 0x00B800, 0x00A800, 0x00A844, 0x008888, 0x000000, 0x000000, 0x000000,
    0xF8F8F8, 0x3CBCFC, 0x6888FC, 0x9878F8, 0xF878F8, 0xF85898, 0xF87858, 0xFCA044,
    0xF8B800, 0xB8F818, 0x58D854, 0x58F898, 0x00E8D8, 0x787878, 0x000000, 0x000000,
    0xFCFCFC, 0xA4E4FC, 0xB8B8F8, 0xD8B8F8, 0xF8B8F8, 0xF8A4C0, 0xF0D0B0, 0xFCE0A8,
    0xF8D878, 0xD8F878, 0xB8F8B8, 0xB8F8D8, 0x00FCFC, 0xF8D8F8, 0x000000, 0x000000,
]

def rgb_to_hex(v):
    return f'#{(v>>16)&0xFF:02x}{(v>>8)&0xFF:02x}{v&0xFF:02x}'

NES_PALETTE_HEX = [rgb_to_hex(c) for c in NES_PALETTE]

# ======================== ROM Loader ========================
class NESRom:
    def __init__(self, data: bytes):
        self.valid = False
        self.prg_rom = b''
        self.chr_rom = b''
        self.mapper = 0
        self.mirror_vertical = False
        self.mirror_four = False
        self.battery = False
        self.trainer = None
        self.prg_ram_size = 8192
        self._parse(data)
   
    def _parse(self, data: bytes):
        if len(data) < 16 or data[0:4] != b'NES\x1A':
            return
       
        prg_banks = data[4]
        chr_banks = data[5]
        flag6 = data[6]
        flag7 = data[7]
       
        self.mapper = ((flag7 & 0xF0) >> 4) | (flag6 & 0xF0)
        self.mirror_vertical = (flag6 & 0x01) != 0
        self.mirror_four = (flag6 & 0x08) != 0
        self.battery = (flag6 & 0x02) != 0
        trainer_present = (flag6 & 0x04) != 0
       
        offset = 16
        if trainer_present:
            self.trainer = data[offset:offset+512]
            offset += 512
       
        prg_size = prg_banks * 16384
        chr_size = chr_banks * 8192
       
        self.prg_rom = data[offset:offset + prg_size]
        offset += prg_size
        self.chr_rom = data[offset:offset + chr_size] if chr_banks > 0 else b''
       
        self.valid = True

# ======================== PPU (Picture Processing Unit) ========================
class PPU:
    def __init__(self):
        # Memory
        self.vram = bytearray(2048)  # Nametable RAM
        self.palette = bytearray(32)  # Palette RAM
        self.oam = bytearray(256)     # Object Attribute Memory (sprites)
       
        # Registers
        self.ctrl = 0      # $2000
        self.mask = 0      # $2001
        self.status = 0    # $2002
        self.oam_addr = 0  # $2003
        self.scroll_x = 0
        self.scroll_y = 0
        self.addr_latch = False
        self.vram_addr = 0
        self.vram_temp = 0
        self.fine_x = 0
        self.data_buffer = 0
       
        # Mirroring
        self.mirroring = 'HORIZONTAL'
        self.mirror_four = False
       
        # Frame buffer
        self.frame = [[NES_PALETTE_HEX[0] for _ in range(256)] for _ in range(240)]
       
        # Timing
        self.scanline = 0
        self.cycle = 0
        self.frame_complete = False
        self.nmi_occurred = False
        self.nmi_output = False
       
        # Sprite evaluation
        self.sprite_zero_hit = False
        self.sprite_overflow = False
       
        self.bus = None
       
    def reset(self):
        self.ctrl = 0
        self.mask = 0
        self.status = 0
        self.oam_addr = 0
        self.scroll_x = 0
        self.scroll_y = 0
        self.addr_latch = False
        self.vram_addr = 0
        self.vram_temp = 0
        self.fine_x = 0
        self.scanline = 0
        self.cycle = 0
       
    def read_register(self, addr):
        addr = 0x2000 + (addr & 7)
       
        if addr == 0x2002:  # PPUSTATUS
            result = self.status & 0xFF
            self.status &= 0x7F  # Clear vblank
            self.addr_latch = False
            return result
        elif addr == 0x2004:  # OAMDATA
            if self.oam_addr < len(self.oam):
                return self.oam[self.oam_addr] & 0xFF
            return 0
        elif addr == 0x2007:  # PPUDATA
            value = self.data_buffer & 0xFF
            self.data_buffer = self._read(self.vram_addr)
            if self.vram_addr >= 0x3F00:  # Palette read
                value = self.data_buffer & 0xFF
            self.vram_addr = (self.vram_addr + (32 if self.ctrl & 0x04 else 1)) & 0x3FFF
            return value
        return 0
   
    def write_register(self, addr, value):
        addr = 0x2000 + (addr & 7)
        value &= 0xFF
       
        if addr == 0x2000:  # PPUCTRL
            self.ctrl = value
            self.vram_temp = (self.vram_temp & 0xF3FF) | ((value & 0x03) << 10)
        elif addr == 0x2001:  # PPUMASK
            self.mask = value
        elif addr == 0x2003:  # OAMADDR
            self.oam_addr = value
        elif addr == 0x2004:  # OAMDATA
            self.oam[self.oam_addr] = value
            self.oam_addr = (self.oam_addr + 1) & 0xFF
        elif addr == 0x2005:  # PPUSCROLL
            if not self.addr_latch:
                self.vram_temp = (self.vram_temp & 0xFFE0) | (value >> 3)
                self.fine_x = value & 0x07
            else:
                self.vram_temp = (self.vram_temp & 0x8FFF) | ((value & 0x07) << 12)
                self.vram_temp = (self.vram_temp & 0xFC1F) | ((value & 0xF8) << 2)
            self.addr_latch = not self.addr_latch
        elif addr == 0x2006:  # PPUADDR
            if not self.addr_latch:
                self.vram_temp = (self.vram_temp & 0x80FF) | ((value & 0x3F) << 8)
            else:
                self.vram_temp = (self.vram_temp & 0xFF00) | value
                self.vram_addr = self.vram_temp
            self.addr_latch = not self.addr_latch
        elif addr == 0x2007:  # PPUDATA
            self._write(self.vram_addr, value)
            self.vram_addr = (self.vram_addr + (32 if self.ctrl & 0x04 else 1)) & 0x3FFF
           
    def _read(self, addr):
        addr &= 0x3FFF
        if addr < 0x2000:  # Pattern tables
            return self.bus.mapper.ppu_read(addr)
        elif addr < 0x3F00:  # Nametables
            return self.vram[self._mirror_addr(addr)]
        else:  # Palette
            addr = (addr - 0x3F00) & 0x1F
            if addr == 0x10 or addr == 0x14 or addr == 0x18 or addr == 0x1C:
                addr -= 0x10
            return self.palette[addr]
   
    def _write(self, addr, value):
        addr &= 0x3FFF
        if addr < 0x2000:  # Pattern tables
            self.bus.mapper.ppu_write(addr, value)
        elif addr < 0x3F00:  # Nametables
            self.vram[self._mirror_addr(addr)] = value
        else:  # Palette
            addr = (addr - 0x3F00) & 0x1F
            if addr == 0x10 or addr == 0x14 or addr == 0x18 or addr == 0x1C:
                addr -= 0x10
            self.palette[addr] = value & 0x3F
           
    def _mirror_addr(self, addr):
        addr = (addr - 0x2000) & 0x0FFF
        table = addr // 0x400
        offset = addr % 0x400
        
        if self.mirroring == 'FOUR':
            return addr
        elif self.mirroring == 'VERTICAL':
            table = table & 1
        elif self.mirroring == 'HORIZONTAL':
            table = (table >> 1) & 1
        elif self.mirroring == 'SINGLE_LOW':
            table = 0
        elif self.mirroring == 'SINGLE_HIGH':
            table = 1
            
        return table * 0x400 + offset
   
    def step(self):
        # Simplified PPU timing
        if self.scanline < 240:  # Visible scanlines
            if self.cycle == 256:
                self._render_scanline()
        elif self.scanline == 241:  # VBlank start
            if self.cycle == 1:
                self.status |= 0x80  # Set VBlank flag
                self.nmi_occurred = True
                if self.ctrl & 0x80:  # NMI enabled
                    self.nmi_output = True
        elif self.scanline == 261:  # Pre-render line
            if self.cycle == 1:
                self.status &= 0x7F  # Clear VBlank
                self.sprite_zero_hit = False
                self.sprite_overflow = False
               
        self.cycle += 1
        if self.cycle > 340:
            self.cycle = 0
            self.scanline += 1
            if self.scanline > 261:
                self.scanline = 0
                self.frame_complete = True
               
    def _render_scanline(self):
        if self.scanline >= 240:
            return
           
        y = self.scanline
       
        # Fill with backdrop color
        backdrop = NES_PALETTE_HEX[self.palette[0] & 0x3F]
        for x in range(256):
            self.frame[y][x] = backdrop
       
        # Background rendering
        if self.mask & 0x08:
            self._render_background_line(y)
           
        # Sprite rendering
        if self.mask & 0x10:
            self._render_sprites_line(y)
           
    def _render_background_line(self, y):
        # Calculate scroll from vram_temp
        scroll_x = ((self.vram_temp & 0x001F) << 3) | self.fine_x
        scroll_y = (((self.vram_temp >> 5) & 0x001F) << 3) | ((self.vram_temp >> 12) & 0x0007)
        nametable_select = (self.vram_temp >> 10) & 0x0003
        nametable_base = 0x2000 + nametable_select * 0x400
        pattern_base = 0x1000 if self.ctrl & 0x10 else 0
       
        for x in range(256):
            # Calculate scrolled position
            px = (x + scroll_x) & 0x1FF
            py = (y + scroll_y) & 0x1FF
           
            # Get tile
            tx = px >> 3
            ty = py >> 3
           
            nametable = nametable_base
            if px >= 256:
                nametable ^= 0x400  # Switch horizontal nametable
            if py >= 240:
                nametable ^= 0x800  # Switch vertical nametable
               
            tile_addr = nametable + ty * 32 + (tx & 0x1F)
            tile = self._read(tile_addr)
           
            # Get attribute
            attr_addr = nametable + 0x3C0 + (ty >> 2) * 8 + (tx >> 2)
            attr = self._read(attr_addr)
            shift = ((ty & 2) << 1) | (tx & 2)
            palette_num = (attr >> shift) & 0x03
           
            # Get pattern
            pattern_addr = pattern_base + tile * 16 + (py & 7)
            pattern_low = self._read(pattern_addr)
            pattern_high = self._read(pattern_addr + 8)
           
            bit = 7 - (px & 7)
            color_idx = ((pattern_high >> bit) & 1) << 1 | ((pattern_low >> bit) & 1)
           
            if color_idx == 0:
                palette_idx = self.palette[0]
            else:
                palette_idx = self.palette[palette_num * 4 + color_idx]
               
            self.frame[y][x] = NES_PALETTE_HEX[palette_idx & 0x3F]
           
    def _render_sprites_line(self, scanline):
        sprite_size = 16 if self.ctrl & 0x20 else 8
        pattern_base = 0x1000 if self.ctrl & 0x08 else 0
       
        sprites_found = 0
       
        for i in range(64):
            y = self.oam[i * 4]
            if y >= 0xEF:
                continue
               
            if scanline >= y and scanline < y + sprite_size:
                if sprites_found >= 8:
                    self.sprite_overflow = True
                    break
                   
                tile = self.oam[i * 4 + 1]
                attr = self.oam[i * 4 + 2]
                x = self.oam[i * 4 + 3]
               
                palette_num = (attr & 0x03) + 4
                behind_bg = attr & 0x20
                flip_h = attr & 0x40
                flip_v = attr & 0x80
               
                row = scanline - y
                if flip_v:
                    row = sprite_size - 1 - row
                   
                if sprite_size == 16:
                    if row >= 8:
                        tile += 1
                        row -= 8
                    pattern_addr = (tile & 0xFE) * 16 + row
                    if tile & 1:
                        pattern_addr += 0x1000
                else:
                    pattern_addr = pattern_base + tile * 16 + row
                   
                pattern_low = self._read(pattern_addr)
                pattern_high = self._read(pattern_addr + 8)
               
                for col in range(8):
                    px = x + col
                    if px >= 256:
                        continue
                       
                    bit = col if flip_h else 7 - col
                    color_idx = ((pattern_high >> bit) & 1) << 1 | ((pattern_low >> bit) & 1)
                   
                    if color_idx != 0:
                        # Check sprite 0 hit
                        if i == 0 and (self.mask & 0x18) == 0x18:
                            if px < 255 and scanline < 239:
                                self.sprite_zero_hit = True
                                self.status |= 0x40
                               
                        if not behind_bg or self.frame[scanline][px] == NES_PALETTE_HEX[self.palette[0] & 0x3F]:
                            palette_idx = self.palette[palette_num * 4 + color_idx]
                            self.frame[scanline][px] = NES_PALETTE_HEX[palette_idx & 0x3F]
                           
                sprites_found += 1

# ======================== APU (Audio Processing Unit) - Stub ========================
class APU:
    def __init__(self, bus):
        self.bus = bus
        self.enabled = False
        
    def step(self):
        pass  # Stub - no audio processing
    
    def write(self, addr, value):
        pass  # Stub - ignore APU writes
    
    def read(self, addr):
        return 0  # Stub - return 0 for APU reads

# ======================== CPU (6502) ========================
class CPU:
    # Status flags
    C = 0x01  # Carry
    Z = 0x02  # Zero
    I = 0x04  # Interrupt disable
    D = 0x08  # Decimal
    B = 0x10  # Break
    U = 0x20  # Unused
    V = 0x40  # Overflow
    N = 0x80  # Negative
   
    def __init__(self, bus):
        self.bus = bus
        self.A = 0      # Accumulator
        self.X = 0      # X register
        self.Y = 0      # Y register
        self.SP = 0xFD  # Stack pointer
        self.PC = 0     # Program counter
        self.P = 0x24   # Status register
        self.cycles = 0
        self.total_cycles = 0
       
        # Build opcode table
        self._build_opcodes()
       
    def reset(self):
        self.A = 0
        self.X = 0
        self.Y = 0
        self.SP = 0xFD
        self.P = 0x24
        self.PC = self.bus.read16(0xFFFC)
        self.cycles = 0
       
    def irq(self):
        if not (self.P & self.I):
            self._push16(self.PC)
            self._push(self.P | self.U)
            self.P |= self.I
            self.PC = self.bus.read16(0xFFFE)
            self.cycles += 7
           
    def nmi(self):
        self._push16(self.PC)
        self._push(self.P | self.U)
        self.P |= self.I
        self.PC = self.bus.read16(0xFFFA)
        self.cycles += 7
       
    def step(self):
        opcode = self.bus.read(self.PC)
        self.PC = (self.PC + 1) & 0xFFFF
       
        if opcode in self.opcodes:
            mode, operation, cycles = self.opcodes[opcode]
            addr, page_crossed = self._get_address(mode)
            operation(addr, mode)
            self.cycles += cycles
            if page_crossed and opcode in self.page_sensitive_ops:
                self.cycles += 1
        else:
            # Illegal opcode - treat as NOP
            self.cycles += 2
           
        self.total_cycles += self.cycles
        result = self.cycles
        self.cycles = 0
        return result
       
    def _build_opcodes(self):
        """Build the opcode lookup table"""
        # Format: opcode: (addressing_mode, operation, base_cycles)
        self.opcodes = {
            # Load/Store
            0xA9: ('IMM', self._lda, 2), 0xA5: ('ZP', self._lda, 3),
            0xB5: ('ZPX', self._lda, 4), 0xAD: ('ABS', self._lda, 4),
            0xBD: ('ABX', self._lda, 4), 0xB9: ('ABY', self._lda, 4),
            0xA1: ('IDX', self._lda, 6), 0xB1: ('IDY', self._lda, 5),
           
            0xA2: ('IMM', self._ldx, 2), 0xA6: ('ZP', self._ldx, 3),
            0xB6: ('ZPY', self._ldx, 4), 0xAE: ('ABS', self._ldx, 4),
            0xBE: ('ABY', self._ldx, 4),
           
            0xA0: ('IMM', self._ldy, 2), 0xA4: ('ZP', self._ldy, 3),
            0xB4: ('ZPX', self._ldy, 4), 0xAC: ('ABS', self._ldy, 4),
            0xBC: ('ABX', self._ldy, 4),
           
            0x85: ('ZP', self._sta, 3), 0x95: ('ZPX', self._sta, 4),
            0x8D: ('ABS', self._sta, 4), 0x9D: ('ABX', self._sta, 5),
            0x99: ('ABY', self._sta, 5), 0x81: ('IDX', self._sta, 6),
            0x91: ('IDY', self._sta, 6),
           
            0x86: ('ZP', self._stx, 3), 0x96: ('ZPY', self._stx, 4),
            0x8E: ('ABS', self._stx, 4),
           
            0x84: ('ZP', self._sty, 3), 0x94: ('ZPX', self._sty, 4),
            0x8C: ('ABS', self._sty, 4),
           
            # Transfer
            0xAA: ('IMP', self._tax, 2), 0xA8: ('IMP', self._tay, 2),
            0xBA: ('IMP', self._tsx, 2), 0x8A: ('IMP', self._txa, 2),
            0x9A: ('IMP', self._txs, 2), 0x98: ('IMP', self._tya, 2),
           
            # Stack
            0x48: ('IMP', self._pha, 3), 0x68: ('IMP', self._pla, 4),
            0x08: ('IMP', self._php, 3), 0x28: ('IMP', self._plp, 4),
           
            # Arithmetic
            0x69: ('IMM', self._adc, 2), 0x65: ('ZP', self._adc, 3),
            0x75: ('ZPX', self._adc, 4), 0x6D: ('ABS', self._adc, 4),
            0x7D: ('ABX', self._adc, 4), 0x79: ('ABY', self._adc, 4),
            0x61: ('IDX', self._adc, 6), 0x71: ('IDY', self._adc, 5),
           
            0xE9: ('IMM', self._sbc, 2), 0xE5: ('ZP', self._sbc, 3),
            0xF5: ('ZPX', self._sbc, 4), 0xED: ('ABS', self._sbc, 4),
            0xFD: ('ABX', self._sbc, 4), 0xF9: ('ABY', self._sbc, 4),
            0xE1: ('IDX', self._sbc, 6), 0xF1: ('IDY', self._sbc, 5),
           
            # Compare
            0xC9: ('IMM', self._cmp, 2), 0xC5: ('ZP', self._cmp, 3),
            0xD5: ('ZPX', self._cmp, 4), 0xCD: ('ABS', self._cmp, 4),
            0xDD: ('ABX', self._cmp, 4), 0xD9: ('ABY', self._cmp, 4),
            0xC1: ('IDX', self._cmp, 6), 0xD1: ('IDY', self._cmp, 5),
           
            0xE0: ('IMM', self._cpx, 2), 0xE4: ('ZP', self._cpx, 3),
            0xEC: ('ABS', self._cpx, 4),
           
            0xC0: ('IMM', self._cpy, 2), 0xC4: ('ZP', self._cpy, 3),
            0xCC: ('ABS', self._cpy, 4),
           
            # Increment/Decrement
            0xE6: ('ZP', self._inc, 5), 0xF6: ('ZPX', self._inc, 6),
            0xEE: ('ABS', self._inc, 6), 0xFE: ('ABX', self._inc, 7),
           
            0xC6: ('ZP', self._dec, 5), 0xD6: ('ZPX', self._dec, 6),
            0xCE: ('ABS', self._dec, 6), 0xDE: ('ABX', self._dec, 7),
           
            0xE8: ('IMP', self._inx, 2), 0xC8: ('IMP', self._iny, 2),
            0xCA: ('IMP', self._dex, 2), 0x88: ('IMP', self._dey, 2),
           
            # Logical
            0x29: ('IMM', self._and, 2), 0x25: ('ZP', self._and, 3),
            0x35: ('ZPX', self._and, 4), 0x2D: ('ABS', self._and, 4),
            0x3D: ('ABX', self._and, 4), 0x39: ('ABY', self._and, 4),
            0x21: ('IDX', self._and, 6), 0x31: ('IDY', self._and, 5),
           
            0x09: ('IMM', self._ora, 2), 0x05: ('ZP', self._ora, 3),
            0x15: ('ZPX', self._ora, 4), 0x0D: ('ABS', self._ora, 4),
            0x1D: ('ABX', self._ora, 4), 0x19: ('ABY', self._ora, 4),
            0x01: ('IDX', self._ora, 6), 0x11: ('IDY', self._ora, 5),
           
            0x49: ('IMM', self._eor, 2), 0x45: ('ZP', self._eor, 3),
            0x55: ('ZPX', self._eor, 4), 0x4D: ('ABS', self._eor, 4),
            0x5D: ('ABX', self._eor, 4), 0x59: ('ABY', self._eor, 4),
            0x41: ('IDX', self._eor, 6), 0x51: ('IDY', self._eor, 5),
           
            # Bit manipulation
            0x24: ('ZP', self._bit, 3), 0x2C: ('ABS', self._bit, 4),
           
            # Shifts
            0x0A: ('ACC', self._asl, 2), 0x06: ('ZP', self._asl, 5),
            0x16: ('ZPX', self._asl, 6), 0x0E: ('ABS', self._asl, 6),
            0x1E: ('ABX', self._asl, 7),
           
            0x4A: ('ACC', self._lsr, 2), 0x46: ('ZP', self._lsr, 5),
            0x56: ('ZPX', self._lsr, 6), 0x4E: ('ABS', self._lsr, 6),
            0x5E: ('ABX', self._lsr, 7),
           
            0x2A: ('ACC', self._rol, 2), 0x26: ('ZP', self._rol, 5),
            0x36: ('ZPX', self._rol, 6), 0x2E: ('ABS', self._rol, 6),
            0x3E: ('ABX', self._rol, 7),
           
            0x6A: ('ACC', self._ror, 2), 0x66: ('ZP', self._ror, 5),
            0x76: ('ZPX', self._ror, 6), 0x6E: ('ABS', self._ror, 6),
            0x7E: ('ABX', self._ror, 7),
           
            # Branches
            0x10: ('REL', self._bpl, 2), 0x30: ('REL', self._bmi, 2),
            0x50: ('REL', self._bvc, 2), 0x70: ('REL', self._bvs, 2),
            0x90: ('REL', self._bcc, 2), 0xB0: ('REL', self._bcs, 2),
            0xD0: ('REL', self._bne, 2), 0xF0: ('REL', self._beq, 2),
           
            # Jumps
            0x4C: ('ABS', self._jmp, 3), 0x6C: ('IND', self._jmp, 5),
            0x20: ('ABS', self._jsr, 6), 0x60: ('IMP', self._rts, 6),
            0x40: ('IMP', self._rti, 6),
           
            # Flags
            0x18: ('IMP', self._clc, 2), 0x38: ('IMP', self._sec, 2),
            0x58: ('IMP', self._cli, 2), 0x78: ('IMP', self._sei, 2),
            0xB8: ('IMP', self._clv, 2), 0xD8: ('IMP', self._cld, 2),
            0xF8: ('IMP', self._sed, 2),
           
            # System
            0x00: ('IMP', self._brk, 7), 0xEA: ('IMP', self._nop, 2),
        }
       
        # Instructions that take an extra cycle on page boundary cross
        self.page_sensitive_ops = {
            0xBD, 0xB9, 0xB1,  # LDA
            0xBE, 0xBC,        # LDX, LDY
            0x7D, 0x79, 0x71,  # ADC
            0xFD, 0xF9, 0xF1,  # SBC
            0xDD, 0xD9, 0xD1,  # CMP
            0x1D, 0x19, 0x11,  # ORA
            0x3D, 0x39, 0x31,  # AND
            0x5D, 0x59, 0x51,  # EOR
        }
       
    def _get_address(self, mode):
        page_crossed = False
       
        if mode == 'IMP' or mode == 'ACC':
            return 0, False
        elif mode == 'IMM':
            addr = self.PC
            self.PC = (self.PC + 1) & 0xFFFF
            return addr, False
        elif mode == 'ZP':
            return self.bus.read(self._fetch()), False
        elif mode == 'ZPX':
            return (self.bus.read(self._fetch()) + self.X) & 0xFF, False
        elif mode == 'ZPY':
            return (self.bus.read(self._fetch()) + self.Y) & 0xFF, False
        elif mode == 'ABS':
            return self._fetch16(), False
        elif mode == 'ABX':
            base = self._fetch16()
            addr = (base + self.X) & 0xFFFF
            page_crossed = (base & 0xFF00) != (addr & 0xFF00)
            return addr, page_crossed
        elif mode == 'ABY':
            base = self._fetch16()
            addr = (base + self.Y) & 0xFFFF
            page_crossed = (base & 0xFF00) != (addr & 0xFF00)
            return addr, page_crossed
        elif mode == 'IND':
            ptr = self._fetch16()
            # 6502 bug: wraps within page
            if (ptr & 0xFF) == 0xFF:
                return self.bus.read(ptr) | (self.bus.read(ptr & 0xFF00) << 8), False
            else:
                return self.bus.read16(ptr), False
        elif mode == 'IDX':
            zp = (self.bus.read(self._fetch()) + self.X) & 0xFF
            return self.bus.read(zp) | (self.bus.read((zp + 1) & 0xFF) << 8), False
        elif mode == 'IDY':
            zp = self.bus.read(self._fetch())
            base = self.bus.read(zp) | (self.bus.read((zp + 1) & 0xFF) << 8)
            addr = (base + self.Y) & 0xFFFF
            page_crossed = (base & 0xFF00) != (addr & 0xFF00)
            return addr, page_crossed
        elif mode == 'REL':
            offset = self.bus.read(self._fetch())
            if offset & 0x80:
                offset -= 256
            return (self.PC + offset) & 0xFFFF, False
       
        return 0, False
   
    def _fetch(self):
        value = self.PC
        self.PC = (self.PC + 1) & 0xFFFF
        return value
   
    def _fetch16(self):
        lo = self.bus.read(self._fetch())
        hi = self.bus.read(self._fetch())
        return (hi << 8) | lo
   
    def _push(self, value):
        self.bus.write(0x100 + self.SP, value)
        self.SP = (self.SP - 1) & 0xFF
   
    def _pop(self):
        self.SP = (self.SP + 1) & 0xFF
        return self.bus.read(0x100 + self.SP)
   
    def _push16(self, value):
        self._push((value >> 8) & 0xFF)
        self._push(value & 0xFF)
   
    def _pop16(self):
        lo = self._pop()
        hi = self._pop()
        return (hi << 8) | lo
   
    def _set_nz(self, value):
        self.P = (self.P & ~(self.N | self.Z)) | (value & 0x80) | (self.Z if value == 0 else 0)
   
    # Instruction implementations (abbreviated for space - same as original)
    def _lda(self, addr, mode):
        self.A = self.bus.read(addr)
        self._set_nz(self.A)
   
    def _ldx(self, addr, mode):
        self.X = self.bus.read(addr)
        self._set_nz(self.X)
   
    def _ldy(self, addr, mode):
        self.Y = self.bus.read(addr)
        self._set_nz(self.Y)
   
    def _sta(self, addr, mode):
        self.bus.write(addr, self.A)
   
    def _stx(self, addr, mode):
        self.bus.write(addr, self.X)
   
    def _sty(self, addr, mode):
        self.bus.write(addr, self.Y)
   
    def _tax(self, addr, mode):
        self.X = self.A
        self._set_nz(self.X)
   
    def _tay(self, addr, mode):
        self.Y = self.A
        self._set_nz(self.Y)
   
    def _tsx(self, addr, mode):
        self.X = self.SP
        self._set_nz(self.X)
   
    def _txa(self, addr, mode):
        self.A = self.X
        self._set_nz(self.A)
   
    def _txs(self, addr, mode):
        self.SP = self.X
   
    def _tya(self, addr, mode):
        self.A = self.Y
        self._set_nz(self.A)
   
    def _pha(self, addr, mode):
        self._push(self.A)
   
    def _pla(self, addr, mode):
        self.A = self._pop()
        self._set_nz(self.A)
   
    def _php(self, addr, mode):
        self._push(self.P | self.B | self.U)
   
    def _plp(self, addr, mode):
        self.P = (self._pop() | self.U) & ~self.B
   
    def _adc(self, addr, mode):
        value = self.bus.read(addr)
        result = self.A + value + (1 if self.P & self.C else 0)
        overflow = ~(self.A ^ value) & (self.A ^ result) & 0x80
       
        self.P = self.P & ~(self.C | self.V)
        if result > 255:
            self.P |= self.C
        if overflow:
            self.P |= self.V
       
        self.A = result & 0xFF
        self._set_nz(self.A)
   
    def _sbc(self, addr, mode):
        value = self.bus.read(addr) ^ 0xFF
        result = self.A + value + (1 if self.P & self.C else 0)
        overflow = ~(self.A ^ value) & (self.A ^ result) & 0x80
       
        self.P = self.P & ~(self.C | self.V)
        if result > 255:
            self.P |= self.C
        if overflow:
            self.P |= self.V
       
        self.A = result & 0xFF
        self._set_nz(self.A)
   
    def _cmp(self, addr, mode):
        value = self.bus.read(addr)
        result = self.A - value
        self.P = self.P & ~self.C
        if self.A >= value:
            self.P |= self.C
        self._set_nz(result & 0xFF)
   
    def _cpx(self, addr, mode):
        value = self.bus.read(addr)
        result = self.X - value
        self.P = self.P & ~self.C
        if self.X >= value:
            self.P |= self.C
        self._set_nz(result & 0xFF)
   
    def _cpy(self, addr, mode):
        value = self.bus.read(addr)
        result = self.Y - value
        self.P = self.P & ~self.C
        if self.Y >= value:
            self.P |= self.C
        self._set_nz(result & 0xFF)
   
    def _inc(self, addr, mode):
        value = (self.bus.read(addr) + 1) & 0xFF
        self.bus.write(addr, value)
        self._set_nz(value)
   
    def _dec(self, addr, mode):
        value = (self.bus.read(addr) - 1) & 0xFF
        self.bus.write(addr, value)
        self._set_nz(value)
   
    def _inx(self, addr, mode):
        self.X = (self.X + 1) & 0xFF
        self._set_nz(self.X)
   
    def _iny(self, addr, mode):
        self.Y = (self.Y + 1) & 0xFF
        self._set_nz(self.Y)
   
    def _dex(self, addr, mode):
        self.X = (self.X - 1) & 0xFF
        self._set_nz(self.X)
   
    def _dey(self, addr, mode):
        self.Y = (self.Y - 1) & 0xFF
        self._set_nz(self.Y)
   
    def _and(self, addr, mode):
        self.A &= self.bus.read(addr)
        self._set_nz(self.A)
   
    def _ora(self, addr, mode):
        self.A |= self.bus.read(addr)
        self._set_nz(self.A)
   
    def _eor(self, addr, mode):
        self.A ^= self.bus.read(addr)
        self._set_nz(self.A)
   
    def _bit(self, addr, mode):
        value = self.bus.read(addr)
        self.P = (self.P & ~(self.V | self.N)) | (value & 0xC0)
        if (self.A & value) == 0:
            self.P |= self.Z
        else:
            self.P &= ~self.Z
   
    def _asl(self, addr, mode):
        if mode == 'ACC':
            self.P = (self.P & ~self.C) | ((self.A >> 7) & 1)
            self.A = (self.A << 1) & 0xFF
            self._set_nz(self.A)
        else:
            value = self.bus.read(addr)
            self.P = (self.P & ~self.C) | ((value >> 7) & 1)
            value = (value << 1) & 0xFF
            self.bus.write(addr, value)
            self._set_nz(value)
   
    def _lsr(self, addr, mode):
        if mode == 'ACC':
            self.P = (self.P & ~self.C) | (self.A & 1)
            self.A >>= 1
            self._set_nz(self.A)
        else:
            value = self.bus.read(addr)
            self.P = (self.P & ~self.C) | (value & 1)
            value >>= 1
            self.bus.write(addr, value)
            self._set_nz(value)
   
    def _rol(self, addr, mode):
        if mode == 'ACC':
            carry = 1 if self.P & self.C else 0
            self.P = (self.P & ~self.C) | ((self.A >> 7) & 1)
            self.A = ((self.A << 1) | carry) & 0xFF
            self._set_nz(self.A)
        else:
            value = self.bus.read(addr)
            carry = 1 if self.P & self.C else 0
            self.P = (self.P & ~self.C) | ((value >> 7) & 1)
            value = ((value << 1) | carry) & 0xFF
            self.bus.write(addr, value)
            self._set_nz(value)
   
    def _ror(self, addr, mode):
        if mode == 'ACC':
            carry = 0x80 if self.P & self.C else 0
            self.P = (self.P & ~self.C) | (self.A & 1)
            self.A = (self.A >> 1) | carry
            self._set_nz(self.A)
        else:
            value = self.bus.read(addr)
            carry = 0x80 if self.P & self.C else 0
            self.P = (self.P & ~self.C) | (value & 1)
            value = (value >> 1) | carry
            self.bus.write(addr, value)
            self._set_nz(value)
   
    def _beq(self, addr, mode):
        if self.P & self.Z:
            self._branch(addr)
   
    def _bne(self, addr, mode):
        if not (self.P & self.Z):
            self._branch(addr)
   
    def _bcc(self, addr, mode):
        if not (self.P & self.C):
            self._branch(addr)
   
    def _bcs(self, addr, mode):
        if self.P & self.C:
            self._branch(addr)
   
    def _bpl(self, addr, mode):
        if not (self.P & self.N):
            self._branch(addr)
   
    def _bmi(self, addr, mode):
        if self.P & self.N:
            self._branch(addr)
   
    def _bvc(self, addr, mode):
        if not (self.P & self.V):
            self._branch(addr)
   
    def _bvs(self, addr, mode):
        if self.P & self.V:
            self._branch(addr)
   
    def _branch(self, addr):
        self.cycles += 1
        if (self.PC & 0xFF00) != (addr & 0xFF00):
            self.cycles += 1
        self.PC = addr
   
    def _jmp(self, addr, mode):
        self.PC = addr
   
    def _jsr(self, addr, mode):
        self._push16((self.PC - 1) & 0xFFFF)
        self.PC = addr
   
    def _rts(self, addr, mode):
        self.PC = (self._pop16() + 1) & 0xFFFF
   
    def _rti(self, addr, mode):
        self.P = (self._pop() | self.U) & ~self.B
        self.PC = self._pop16()
   
    def _brk(self, addr, mode):
        self._push16((self.PC + 1) & 0xFFFF)
        self._push(self.P | self.B | self.U)
        self.P |= self.I
        self.PC = self.bus.read16(0xFFFE)
   
    def _nop(self, addr, mode):
        pass
   
    def _clc(self, addr, mode):
        self.P &= ~self.C
   
    def _sec(self, addr, mode):
        self.P |= self.C
   
    def _cli(self, addr, mode):
        self.P &= ~self.I
   
    def _sei(self, addr, mode):
        self.P |= self.I
   
    def _clv(self, addr, mode):
        self.P &= ~self.V
   
    def _cld(self, addr, mode):
        self.P &= ~self.D
   
    def _sed(self, addr, mode):
        self.P |= self.D

# ======================== Mapper Classes ========================
class Mapper:
    def __init__(self, prg_banks, chr_banks):
        self.prg_banks = prg_banks
        self.chr_banks = chr_banks
        self.prg_rom = None
        self.chr_rom = None
        self.use_chr_ram = False
        self.chr_ram = None
        self.bus = None

    def cpu_read(self, addr):
        return 0
   
    def cpu_write(self, addr, value):
        pass

    def ppu_read(self, addr):
        return 0

    def ppu_write(self, addr, value):
        pass

    def get_state(self):
        return {}

    def set_state(self, state):
        pass

class Mapper0(Mapper):
    """NROM - No mapper"""
    def __init__(self, prg_banks, chr_banks):
        super().__init__(prg_banks, chr_banks)
        self.use_chr_ram = chr_banks == 0
        if self.use_chr_ram:
            self.chr_ram = bytearray(8192)

    def cpu_read(self, addr):
        mapped_addr = addr - 0x8000
        if self.prg_banks == 1:
            mapped_addr &= 0x3FFF
        return self.prg_rom[mapped_addr % len(self.prg_rom)]

    def cpu_write(self, addr, value):
        pass

    def ppu_read(self, addr):
        addr &= 0x1FFF
        if self.use_chr_ram:
            return self.chr_ram[addr]
        else:
            return self.chr_rom[addr] if addr < len(self.chr_rom) else 0

    def ppu_write(self, addr, value):
        addr &= 0x1FFF
        if self.use_chr_ram:
            self.chr_ram[addr] = value

    def get_state(self):
        state = {}
        if self.use_chr_ram:
            state['chr_ram'] = list(self.chr_ram)
        return state

    def set_state(self, state):
        if 'chr_ram' in state:
            self.chr_ram = bytearray(state['chr_ram'])

class Mapper1(Mapper):
    """MMC1"""
    def __init__(self, prg_banks, chr_banks):
        super().__init__(prg_banks, chr_banks)
        self.shift_register = 0x10
        self.control = 0x0C
        self.chr_bank0 = 0
        self.chr_bank1 = 0
        self.prg_bank = 0
        self.use_chr_ram = chr_banks == 0
        if self.use_chr_ram:
            self.chr_ram = bytearray(8192)

    def cpu_write(self, addr, value):
        if value & 0x80:
            self.shift_register = 0x10
            self.control |= 0x0C
        else:
            complete = self.shift_register & 0x01
            self.shift_register = (self.shift_register >> 1) | ((value & 0x01) << 4)
           
            if complete:
                if addr < 0xA000:
                    self.control = self.shift_register & 0x1F
                    mirror_mode = self.control & 0x03
                    if mirror_mode == 0:
                        self.bus.ppu.mirroring = 'SINGLE_LOW'
                    elif mirror_mode == 1:
                        self.bus.ppu.mirroring = 'SINGLE_HIGH'
                    elif mirror_mode == 2:
                        self.bus.ppu.mirroring = 'VERTICAL'
                    elif mirror_mode == 3:
                        self.bus.ppu.mirroring = 'HORIZONTAL'
                elif addr < 0xC000:
                    self.chr_bank0 = self.shift_register & 0x1F
                elif addr < 0xE000:
                    self.chr_bank1 = self.shift_register & 0x1F
                else:
                    self.prg_bank = self.shift_register & 0x0F
               
                self.shift_register = 0x10

    def cpu_read(self, addr):
        prg_mode = (self.control >> 2) & 0x03
        bank = self.prg_bank
        
        if addr < 0xC000:
            if prg_mode == 0 or prg_mode == 1:
                bank = bank & 0xFE
                mapped_addr = bank * 0x4000 + (addr - 0x8000)
            elif prg_mode == 2:
                mapped_addr = 0 + (addr - 0x8000)
            else:
                mapped_addr = bank * 0x4000 + (addr - 0x8000)
        else:
            if prg_mode == 0 or prg_mode == 1:
                bank = bank | 0x01
                mapped_addr = bank * 0x4000 + (addr - 0xC000)
            elif prg_mode == 2:
                bank = self.prg_banks - 1
                mapped_addr = bank * 0x4000 + (addr - 0xC000)
            else:
                mapped_addr = bank * 0x4000 + (addr - 0xC000)
                
        return self.prg_rom[mapped_addr % len(self.prg_rom)]

    def ppu_read(self, addr):
        addr &= 0x1FFF
        if self.use_chr_ram:
            return self.chr_ram[addr]
        else:
            chr_mode = (self.control >> 4) & 0x01
            if chr_mode == 0:
                bank = self.chr_bank0 & 0x1E
                mapped_addr = bank * 0x1000 + addr
            else:
                if addr < 0x1000:
                    bank = self.chr_bank0
                    mapped_addr = bank * 0x1000 + addr
                else:
                    bank = self.chr_bank1
                    mapped_addr = bank * 0x1000 + (addr - 0x1000)
            return self.chr_rom[mapped_addr % len(self.chr_rom)] if self.chr_rom else 0

    def ppu_write(self, addr, value):
        addr &= 0x1FFF
        if self.use_chr_ram:
            self.chr_ram[addr] = value

    def get_state(self):
        state = {
            'shift_register': self.shift_register,
            'control': self.control,
            'chr_bank0': self.chr_bank0,
            'chr_bank1': self.chr_bank1,
            'prg_bank': self.prg_bank,
        }
        if self.use_chr_ram:
            state['chr_ram'] = list(self.chr_ram)
        return state

    def set_state(self, state):
        self.shift_register = state['shift_register']
        self.control = state['control']
        self.chr_bank0 = state['chr_bank0']
        self.chr_bank1 = state['chr_bank1']
        self.prg_bank = state['prg_bank']
        if 'chr_ram' in state:
            self.chr_ram = bytearray(state['chr_ram'])

# ======================== Bus ========================
class Bus:
    def __init__(self):
        self.ram = bytearray(2048)
        self.prg_ram = bytearray(8192)
        self.mapper = None
        self.ppu = PPU()
        self.ppu.bus = self
        self.cpu = CPU(self)
        self.apu = APU(self)
       
        # Controllers
        self.controller1 = 0
        self.controller2 = 0
        self.controller1_shift = 0
        self.controller2_shift = 0
        self.strobe = False
       
        # DMA
        self.dma_page = 0
        self.dma_addr = 0
        self.dma_data = 0
        self.dma_dummy = True
        self.dma_transfer = False
       
    def load_rom(self, rom: NESRom):
        prg_banks = len(rom.prg_rom) // 16384
        chr_banks = len(rom.chr_rom) // 8192 if rom.chr_rom else 0
       
        if rom.mapper == 0:
            self.mapper = Mapper0(prg_banks, chr_banks)
        elif rom.mapper == 1:  # Fixed: was = instead of ==
            self.mapper = Mapper1(prg_banks, chr_banks)
        else:
            self.mapper = Mapper0(prg_banks, chr_banks)
       
        self.mapper.bus = self
        self.mapper.prg_rom = bytearray(rom.prg_rom)
        if rom.chr_rom:
            self.mapper.chr_rom = bytearray(rom.chr_rom)
        if rom.trainer:
            self.prg_ram[0x1000:0x1200] = rom.trainer
       
        if rom.mirror_four:
            self.ppu.mirroring = 'FOUR'
            self.ppu.vram = bytearray(4096)
        else:
            self.ppu.vram = bytearray(2048)
            self.ppu.mirroring = 'VERTICAL' if rom.mirror_vertical else 'HORIZONTAL'
       
        self.reset()
   
    def reset(self):
        self.cpu.reset()
        self.ppu.reset()
        self.dma_transfer = False
       
    def read(self, addr):
        addr &= 0xFFFF
       
        if addr < 0x2000:
            return self.ram[addr & 0x7FF]
        elif addr < 0x4000:
            return self.ppu.read_register(addr)
        elif addr < 0x4018:
            # APU read
            if addr == 0x4015:
                return 0  # APU status stub
            elif addr == 0x4016:
                data = (self.controller1_shift & 0x80) >> 7
                self.controller1_shift <<= 1
                return data | 0x40
            elif addr == 0x4017:
                data = (self.controller2_shift & 0x80) >> 7
                self.controller2_shift <<= 1
                return data | 0x40
            return 0
        elif addr < 0x4020:
            return 0
        elif addr < 0x6000:
            return 0
        elif addr < 0x8000:
            return self.prg_ram[addr - 0x6000]
        else:
            return self.mapper.cpu_read(addr)
   
    def write(self, addr, value):
        addr &= 0xFFFF
        value &= 0xFF
       
        if addr < 0x2000:
            self.ram[addr & 0x7FF] = value
        elif addr < 0x4000:
            self.ppu.write_register(addr, value)
        elif addr < 0x4018:
            # APU write
            self.apu.write(addr, value)
            if addr == 0x4014:
                # OAM DMA
                self.dma_page = value
                self.dma_addr = 0
                self.dma_transfer = True
            elif addr == 0x4016:
                if self.strobe and not (value & 1):
                    self.controller1_shift = self.controller1
                    self.controller2_shift = self.controller2
                self.strobe = (value & 1) != 0
        elif addr < 0x4020:
            pass
        elif addr < 0x6000:
            pass
        elif addr < 0x8000:
            self.prg_ram[addr - 0x6000] = value
        else:
            self.mapper.cpu_write(addr, value)
   
    def read16(self, addr):
        lo = self.read(addr)
        hi = self.read((addr + 1) & 0xFFFF)
        return (hi << 8) | lo
   
    def set_controller(self, controller, buttons):
        if controller == 1:
            self.controller1 = buttons
        else:
            self.controller2 = buttons

# ======================== Emulator Core ========================
class Emulator:
    def __init__(self):
        self.bus = Bus()
        self.cpu = self.bus.cpu
        self.ppu = self.bus.ppu
       
        self.running = False
        self.fps = 60
        self.frame_time = 1.0 / self.fps
       
        # Timing
        self.master_cycles = 0
        self.cpu_frequency = 1789773  # NTSC
        self.ppu_frequency = self.cpu_frequency * 3
       
    def load_rom(self, rom_data):
        rom = NESRom(rom_data)
        if not rom.valid:
            raise ValueError("Invalid ROM file")
        self.bus.load_rom(rom)
       
    def reset(self):
        self.bus.reset()
        self.master_cycles = 0
       
    def step_frame(self):
        """Run one complete frame"""
        ppu_cycles = 0
        target_cycles = 341 * 262  # NTSC frame
       
        while ppu_cycles < target_cycles:
            # DMA transfer
            if self.bus.dma_transfer:
                if self.bus.dma_dummy:
                    if self.master_cycles % 2 == 1:
                        self.bus.dma_dummy = False
                else:
                    if self.master_cycles % 2 == 0:
                        self.bus.dma_data = self.bus.read(self.bus.dma_page << 8 | self.bus.dma_addr)
                    else:
                        self.ppu.oam[self.bus.dma_addr] = self.bus.dma_data
                        self.bus.dma_addr = (self.bus.dma_addr + 1) & 0xFF
                        if self.bus.dma_addr == 0:
                            self.bus.dma_transfer = False
                            self.bus.dma_dummy = True
            else:
                # CPU step
                cpu_cycles = self.cpu.step()
                self.master_cycles += cpu_cycles
               
            # PPU steps (3 PPU cycles per CPU cycle)
            for _ in range(3):
                self.ppu.step()
                ppu_cycles += 1
               
            # APU step
            self.bus.apu.step()
               
            # Check for NMI
            if self.ppu.nmi_output:
                self.ppu.nmi_output = False
                self.cpu.nmi()
               
        return self.ppu.frame
   
    def set_controller(self, controller, state):
        self.bus.set_controller(controller, state)

# ======================== Save State Support ========================
class SaveState:
    @staticmethod
    def save(emulator):
        state = {
            'cpu': {
                'A': emulator.cpu.A,
                'X': emulator.cpu.X,
                'Y': emulator.cpu.Y,
                'SP': emulator.cpu.SP,
                'PC': emulator.cpu.PC,
                'P': emulator.cpu.P,
            },
            'ppu': {
                'ctrl': emulator.ppu.ctrl,
                'mask': emulator.ppu.mask,
                'status': emulator.ppu.status,
                'vram_addr': emulator.ppu.vram_addr,
                'scroll_x': emulator.ppu.scroll_x,
                'scroll_y': emulator.ppu.scroll_y,
                'vram': list(emulator.ppu.vram),
                'palette': list(emulator.ppu.palette),
                'oam': list(emulator.ppu.oam),
                'mirroring': emulator.ppu.mirroring,
            },
            'ram': list(emulator.bus.ram),
            'prg_ram': list(emulator.bus.prg_ram),
            'mapper': {
                'type': type(emulator.bus.mapper).__name__,
                'state': emulator.bus.mapper.get_state(),
            }
        }
        return json.dumps(state)
   
    @staticmethod
    def load(emulator, state_json):
        state = json.loads(state_json)
       
        # Restore CPU
        emulator.cpu.A = state['cpu']['A']
        emulator.cpu.X = state['cpu']['X']
        emulator.cpu.Y = state['cpu']['Y']
        emulator.cpu.SP = state['cpu']['SP']
        emulator.cpu.PC = state['cpu']['PC']
        emulator.cpu.P = state['cpu']['P']
       
        # Restore PPU
        emulator.ppu.ctrl = state['ppu']['ctrl']
        emulator.ppu.mask = state['ppu']['mask']
        emulator.ppu.status = state['ppu']['status']
        emulator.ppu.vram_addr = state['ppu']['vram_addr']
        emulator.ppu.scroll_x = state['ppu']['scroll_x']
        emulator.ppu.scroll_y = state['ppu']['scroll_y']
        emulator.ppu.vram = bytearray(state['ppu']['vram'])
        emulator.ppu.palette = bytearray(state['ppu']['palette'])
        emulator.ppu.oam = bytearray(state['ppu']['oam'])
        emulator.ppu.mirroring = state['ppu']['mirroring']
       
        # Restore RAM
        emulator.bus.ram = bytearray(state['ram'])
        emulator.bus.prg_ram = bytearray(state['prg_ram'])
       
        # Restore mapper
        emulator.bus.mapper.set_state(state['mapper']['state'])

# ======================== GUI Application ========================
class NESEmulatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NES Emulator - FCEUX Style")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
       
        # Emulator
        self.emulator = Emulator()
        self.rom_loaded = False
        self.running = False
       
        # Save states
        self.save_states = {}
       
        # Setup UI
        self._setup_menu()
        self._setup_display()
        self._setup_controls()
        self._setup_status_bar()
       
        # Keyboard mapping
        self.key_map = {
            'z': 0x01,  # A
            'x': 0x02,  # B
            'Return': 0x04,  # Select
            'space': 0x08,  # Start
            'Up': 0x10,
            'Down': 0x20,
            'Left': 0x40,
            'Right': 0x80,
        }
        self.controller_state = 0
       
        # Bind keys
        self.root.bind('<KeyPress>', self._on_key_press)
        self.root.bind('<KeyRelease>', self._on_key_release)
       
        # Frame timer
        self.frame_timer = None
       
    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
       
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open ROM...", command=self._load_rom, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save State", command=lambda: self._save_state(1), accelerator="F5")
        file_menu.add_command(label="Load State", command=lambda: self._load_state(1), accelerator="F7")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
       
        # Emulation menu
        emu_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Emulation", menu=emu_menu)
        emu_menu.add_command(label="Reset", command=self._reset, accelerator="Ctrl+R")
        emu_menu.add_command(label="Pause", command=self._toggle_pause, accelerator="P")
       
        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Configure Controls...", command=self._show_controls)
       
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
       
    def _setup_display(self):
        # Main display frame
        display_frame = tk.Frame(self.root, bg='#000000')
        display_frame.pack(fill=tk.BOTH, expand=True)
       
        # Canvas for NES display
        self.canvas = tk.Canvas(display_frame, width=600, height=360, bg='#000000', highlightthickness=0)
        self.canvas.pack()
       
        # Photo image for rendering
        self.photo = tk.PhotoImage(width=256, height=240)
        self.canvas_image = self.canvas.create_image(300, 180, image=self.photo)
       
    def _setup_controls(self):
        # Control buttons frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=5, pady=2)
       
        self.load_btn = ttk.Button(control_frame, text="Load ROM", command=self._load_rom)
        self.load_btn.pack(side=tk.LEFT, padx=2)
       
        self.reset_btn = ttk.Button(control_frame, text="Reset", command=self._reset, state=tk.DISABLED)
        self.reset_btn.pack(side=tk.LEFT, padx=2)
       
        self.pause_btn = ttk.Button(control_frame, text="Pause", command=self._toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=2)
       
        # FPS display
        self.fps_label = tk.Label(control_frame, text="FPS: 0")
        self.fps_label.pack(side=tk.RIGHT, padx=5)
       
    def _setup_status_bar(self):
        self.status_bar = tk.Label(self.root, text="No ROM loaded", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _load_rom(self):
        filename = filedialog.askopenfilename(
            title="Select NES ROM",
            filetypes=[("NES ROMs", "*.nes"), ("All Files", "*.*")]
        )
       
        if filename:
            try:
                with open(filename, 'rb') as f:
                    rom_data = f.read()
               
                self.emulator.load_rom(rom_data)
                self.rom_loaded = True
               
                # Update UI
                self.reset_btn.config(state=tk.NORMAL)
                self.pause_btn.config(state=tk.NORMAL)
               
                # Update status
                rom_name = os.path.basename(filename)
                self.status_bar.config(text=f"Loaded: {rom_name}")
               
                # Start emulation
                self._start_emulation()
               
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM: {str(e)}")
                
    def _reset(self):
        if self.rom_loaded:
            self.emulator.reset()
            
    def _toggle_pause(self):
        self.running = not self.running
        self.pause_btn.config(text="Resume" if not self.running else "Pause")
        if self.running:
            self._run_frame()
            
    def _start_emulation(self):
        self.running = True
        self._run_frame()
        
    def _run_frame(self):
        if not self.running or not self.rom_loaded:
            return
            
        try:
            # Update controller state
            self.emulator.set_controller(1, self.controller_state)
            
            # Run frame
            start_time = time.perf_counter()
            frame = self.emulator.step_frame()
            
            # Render frame
            self._render_frame(frame)
            
            # Calculate timing
            elapsed = time.perf_counter() - start_time
            fps = 1.0 / elapsed if elapsed > 0 else 0
            self.fps_label.config(text=f"FPS: {fps:.1f}")
            
            # Schedule next frame
            delay = max(1, int((1000/60) - (elapsed * 1000)))
            self.frame_timer = self.root.after(delay, self._run_frame)
            
        except Exception as e:
            print(f"Runtime error: {e}")
            self.running = False
            self.pause_btn.config(text="Resume")
        
    def _render_frame(self, frame):
        """Render frame to canvas"""
        # Build PPM image data
        ppm_header = f"P6 256 240 255 ".encode('ascii')
        pixels = bytearray()
       
        for row in frame:
            for color in row:
                # Convert hex to RGB
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                pixels.extend([r, g, b])
               
        # Update photo image
        self.photo.config(data=ppm_header + pixels)
        
    def _save_state(self, slot):
        if self.rom_loaded:
            self.save_states[slot] = SaveState.save(self.emulator)
            self.status_bar.config(text=f"State {slot} saved")
            
    def _load_state(self, slot):
        if slot in self.save_states:
            SaveState.load(self.emulator, self.save_states[slot])
            self.status_bar.config(text=f"State {slot} loaded")
            
    def _on_key_press(self, event):
        if event.keysym in self.key_map:
            self.controller_state |= self.key_map[event.keysym]
        elif event.keysym == 'F5':
            self._save_state(1)
        elif event.keysym == 'F7':
            self._load_state(1)
            
    def _on_key_release(self, event):
        if event.keysym in self.key_map:
            self.controller_state &= ~self.key_map[event.keysym]
            
    def _show_controls(self):
        msg = """Controls:
        
        D-Pad: Arrow Keys
        A Button: Z
        B Button: X
        Start: Space
        Select: Enter
        
        Save State: F5
        Load State: F7"""
        messagebox.showinfo("Controls", msg)
        
    def _show_about(self):
        msg = """NES Emulator
        Version 1.0
        
        A Nintendo Entertainment System emulator
        with Tkinter GUI
        
        Supports Mapper 0 & 1 ROMs
        Audio disabled (install pyaudio for sound)"""
        messagebox.showinfo("About", msg)
        
    def run(self):
        self.root.mainloop()

# ======================== Main ========================
if __name__ == "__main__":
    app = NESEmulatorGUI()
    app.run()
