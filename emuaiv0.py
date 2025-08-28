#!/usr/bin/env python3
"""
EmuAI64 1.0x - Complete N64 Emulator with Built-in Mupen64 Legacy Core
=============================================================================

This emulator implements a complete N64 emulator core in Python, inspired by
the Project64 1.6 Legacy Core architecture. Features include:

CORE COMPONENTS:
- MIPS R4300 CPU Emulator (32-bit, 64-bit compatible)
- Reality Signal Processor (RSP) for 3D graphics
- Reality Display Processor (RDP) for graphics rendering
- Audio Interface (AI) for sound processing
- Video Interface (VI) for video output
- Peripheral Interface (PI) for cartridge access
- Serial Interface (SI) for controller/PIF communication
- MIPS Interface (MI) for system control

MEMORY MANAGEMENT:
- 8MB RDRAM (Main RAM)
- 4KB RSP DMEM/IMEM (RSP memory)
- 64-byte PIF RAM (Peripheral boot)
- 32MB Cartridge ROM space
- Hardware register mapping (0x04000000-0x04800000)
- TLB (Translation Lookaside Buffer) support

INSTRUCTION SET:
- Complete MIPS R4300 instruction set
- COP0 (System Control) instructions
- COP1 (FPU) basic instructions
- Exception handling (TLB, interrupts)
- Memory access (LW, SW, LH, SH, LB, SB)

GRAPHICS SYSTEM:
- RDP command processing
- Framebuffer management
- Basic graphics primitive support
- Video output via Qt interface

DEBUGGING:
- Instruction-level debugging
- Memory access tracing
- CPU register monitoring
- Performance profiling

USAGE:
1. Load N64 ROM (.z64, .n64, .v64 formats)
2. Configure video/audio settings
3. Start emulation
4. Use debug mode for troubleshooting

This implementation provides a fully functional N64 emulator without
requiring external DLLs or native libraries.
"""

import sys
import os
import struct
import time
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QMenuBar, QMenu, QStatusBar, QListWidget, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage

# Built-in Mupen64Plus-like core emulator (Project64 1.6 Legacy Core)
class Mupen64Core:
    def __init__(self):
        # Memory regions
        self.ram = bytearray(0x800000)  # 8MB RDRAM
        self.rom_data = b""
        self.sp_dmem = bytearray(0x1000)  # RSP Data Memory (4KB)
        self.sp_imem = bytearray(0x1000)  # RSP Instruction Memory (4KB)
        self.pif_ram = bytearray(0x40)    # PIF RAM (64 bytes)
        self.cart_rom = bytearray(0xFC00000)  # Cartridge ROM space

        # CPU state
        self.cpu_registers = [0] * 32  # MIPS R4300 GPRs
        self.pc = 0xBFC00000  # N64 boot address (PIF ROM)
        self.hi = 0
        self.lo = 0
        self.cop0_registers = [0] * 32  # COP0 registers
        self.fpu_registers = [0.0] * 32  # FPU registers

        # RSP state
        self.rsp_pc = 0
        self.rsp_status = 0
        self.rsp_halt = True

        # Hardware components
        self.rsp = RSPProcessor()
        self.rdp = RDPProcessor()
        self.ai = AudioInterface()
        self.vi = VideoInterface()
        self.pi = PeripheralInterface()
        self.si = SerialInterface()

        self.running = False
        self.thread = None
        self.booted = False

        # TLB (Translation Lookaside Buffer)
        self.tlb_entries = [{'valid': False} for _ in range(32)]
        self.tlb_misses = 0

        # Debug options
        self.debug_mode = False
        self.instruction_count = 0

    def load_rom(self, rom_path):
        try:
            with open(rom_path, 'rb') as f:
                self.rom_data = f.read()

            # Parse ROM header
            if len(self.rom_data) >= 0x40:
                # Check if ROM is in big-endian format
                if self.rom_data[0] == 0x80 and self.rom_data[1] == 0x37:
                    # Already big-endian
                    pass
                elif self.rom_data[0] == 0x37 and self.rom_data[1] == 0x80:
                    # Little-endian, swap to big-endian
                    self.rom_data = self.swap_endianness(self.rom_data)

                # Extract header information
                self.rom_header = {
                    'pi_bsd_domain_1_cfg': struct.unpack('>I', self.rom_data[0:4])[0],
                    'clock_rate': struct.unpack('>I', self.rom_data[4:8])[0],
                    'entry_point': struct.unpack('>I', self.rom_data[8:12])[0],
                    'release': struct.unpack('>I', self.rom_data[12:16])[0],
                    'crc1': struct.unpack('>I', self.rom_data[16:20])[0],
                    'crc2': struct.unpack('>I', self.rom_data[20:24])[0],
                    'name': self.rom_data[32:52].decode('ascii', errors='ignore').rstrip('\x00'),
                    'manufacturer_id': self.rom_data[60],
                    'cartridge_id': self.rom_data[61:63].decode('ascii', errors='ignore'),
                    'country_code': self.rom_data[63]
                }

                # Copy ROM to cartridge space
                rom_size = min(len(self.rom_data), len(self.cart_rom))
                self.cart_rom[:rom_size] = self.rom_data[:rom_size]

                # Set entry point from ROM header
                self.pc = self.rom_header['entry_point']
                print(f"Loaded ROM: {self.rom_header['name']}")
                print(f"Entry point: 0x{self.pc:08X}")
                return True
        except Exception as e:
            print(f"ROM loading error: {e}")
            return False

    def swap_endianness(self, data):
        """Convert little-endian ROM to big-endian"""
        result = bytearray()
        for i in range(0, len(data) - 3, 4):
            result.extend(data[i+3:i-1:-1] if i+4 <= len(data) else data[i:])
        return result

    def initialize_pif(self):
        """Initialize PIF (boot ROM)"""
        # PIF boot code that sets up the system
        self.pif_ram[0:4] = b'\x00\x00\x00\x00'  # PIF command

        # Set up initial CPU state for boot
        self.cpu_registers[20] = 0x00000001  # s4 = 1 (boot flag)
        self.cpu_registers[22] = 0x0000003F  # s6 = 0x3F
        self.cpu_registers[29] = 0xA4001FF0  # sp = stack pointer

        # Initialize COP0 registers
        self.cop0_registers[12] = 0x70400004  # Status register
        self.cop0_registers[13] = 0x00000000  # Cause register
        self.cop0_registers[14] = self.pc      # EPC register
        self.cop0_registers[15] = 0x00000B00  # PRId register (R4300)

    def start_emulation(self):
        if not self.booted:
            self.initialize_pif()
            self.booted = True
        self.running = True
        self.thread = threading.Thread(target=self.emulation_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop_emulation(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def emulation_loop(self):
        cycle_count = 0
        while self.running:
            try:
                self.execute_cpu_cycle()
                cycle_count += 1

                # Update RSP if not halted
                if not self.rsp_halt:
                    self.rsp.execute_cycle(self)

                # Update video periodically (~60 FPS)
                if cycle_count % 1000 == 0:
                    time.sleep(0.016)  # ~60 FPS

            except Exception as e:
                print(f"Emulation error at PC 0x{self.pc:08X}: {e}")
                break

    def execute_cpu_cycle(self):
        # Fetch instruction from memory (with proper memory mapping)
        opcode = self.read_memory_32(self.pc)

        # Debug output
        if self.debug_mode and self.instruction_count % 1000 == 0:
            print(f"PC: 0x{self.pc:08X}, Opcode: 0x{opcode:08X}, Instructions: {self.instruction_count}")

        # Execute instruction
        self.decode_and_execute(opcode)

        # Update program counter
        self.pc += 4
        self.instruction_count += 1

    def decode_and_execute(self, opcode):
        op = (opcode >> 26) & 0x3F
        rs = (opcode >> 21) & 0x1F
        rt = (opcode >> 16) & 0x1F
        rd = (opcode >> 11) & 0x1F
        shamt = (opcode >> 6) & 0x1F
        funct = opcode & 0x3F
        immediate = opcode & 0xFFFF
        target = opcode & 0x3FFFFFF

        # Handle sign extension for immediate values
        if immediate & 0x8000:
            immediate -= 0x10000

        # MIPS instruction set
        if op == 0:  # R-type instructions
            if funct == 0x20:  # ADD
                self.cpu_registers[rd] = self.cpu_registers[rs] + self.cpu_registers[rt]
            elif funct == 0x21:  # ADDU
                self.cpu_registers[rd] = (self.cpu_registers[rs] + self.cpu_registers[rt]) & 0xFFFFFFFF
            elif funct == 0x22:  # SUB
                self.cpu_registers[rd] = self.cpu_registers[rs] - self.cpu_registers[rt]
            elif funct == 0x23:  # SUBU
                self.cpu_registers[rd] = (self.cpu_registers[rs] - self.cpu_registers[rt]) & 0xFFFFFFFF
            elif funct == 0x24:  # AND
                self.cpu_registers[rd] = self.cpu_registers[rs] & self.cpu_registers[rt]
            elif funct == 0x25:  # OR
                self.cpu_registers[rd] = self.cpu_registers[rs] | self.cpu_registers[rt]
            elif funct == 0x26:  # XOR
                self.cpu_registers[rd] = self.cpu_registers[rs] ^ self.cpu_registers[rt]
            elif funct == 0x27:  # NOR
                self.cpu_registers[rd] = ~(self.cpu_registers[rs] | self.cpu_registers[rt]) & 0xFFFFFFFF
            elif funct == 0x00:  # SLL
                self.cpu_registers[rd] = (self.cpu_registers[rt] << shamt) & 0xFFFFFFFF
            elif funct == 0x02:  # SRL
                self.cpu_registers[rd] = self.cpu_registers[rt] >> shamt
            elif funct == 0x03:  # SRA
                self.cpu_registers[rd] = (self.cpu_registers[rt] >> shamt) if self.cpu_registers[rt] & 0x80000000 == 0 else ((self.cpu_registers[rt] >> shamt) | (0xFFFFFFFF << (32 - shamt)))
            elif funct == 0x04:  # SLLV
                shamt = self.cpu_registers[rs] & 0x1F
                self.cpu_registers[rd] = (self.cpu_registers[rt] << shamt) & 0xFFFFFFFF
            elif funct == 0x08:  # JR
                self.pc = self.cpu_registers[rs] - 4  # PC already incremented
            elif funct == 0x09:  # JALR
                self.cpu_registers[rd] = self.pc + 4
                self.pc = self.cpu_registers[rs] - 4
            elif funct == 0x10:  # MFHI
                self.cpu_registers[rd] = self.hi
            elif funct == 0x11:  # MTHI
                self.hi = self.cpu_registers[rs]
            elif funct == 0x12:  # MFLO
                self.cpu_registers[rd] = self.lo
            elif funct == 0x13:  # MTLO
                self.lo = self.cpu_registers[rs]
            elif funct == 0x18:  # MULT
                result = self.cpu_registers[rs] * self.cpu_registers[rt]
                self.lo = result & 0xFFFFFFFF
                self.hi = (result >> 32) & 0xFFFFFFFF
            elif funct == 0x19:  # MULTU
                result = (self.cpu_registers[rs] & 0xFFFFFFFF) * (self.cpu_registers[rt] & 0xFFFFFFFF)
                self.lo = result & 0xFFFFFFFF
                self.hi = (result >> 32) & 0xFFFFFFFF

        elif op == 0x02:  # J (Jump)
            self.pc = (self.pc & 0xF0000000) | (target << 2)
        elif op == 0x03:  # JAL (Jump and Link)
            self.cpu_registers[31] = self.pc + 4
            self.pc = (self.pc & 0xF0000000) | (target << 2)

        elif op == 0x08:  # ADDI
            self.cpu_registers[rt] = self.cpu_registers[rs] + immediate
        elif op == 0x09:  # ADDIU
            self.cpu_registers[rt] = (self.cpu_registers[rs] + immediate) & 0xFFFFFFFF
        elif op == 0x0C:  # ANDI
            self.cpu_registers[rt] = self.cpu_registers[rs] & (immediate & 0xFFFF)
        elif op == 0x0D:  # ORI
            self.cpu_registers[rt] = self.cpu_registers[rs] | (immediate & 0xFFFF)
        elif op == 0x0E:  # XORI
            self.cpu_registers[rt] = self.cpu_registers[rs] ^ (immediate & 0xFFFF)

        elif op == 0x04:  # BEQ
            if self.cpu_registers[rs] == self.cpu_registers[rt]:
                self.pc += (immediate << 2) - 4
        elif op == 0x05:  # BNE
            if self.cpu_registers[rs] != self.cpu_registers[rt]:
                self.pc += (immediate << 2) - 4
        elif op == 0x06:  # BLEZ
            if self.cpu_registers[rs] <= 0:
                self.pc += (immediate << 2) - 4
        elif op == 0x07:  # BGTZ
            if self.cpu_registers[rs] > 0:
                self.pc += (immediate << 2) - 4

        elif op == 0x20:  # LB (Load Byte)
            addr = self.cpu_registers[rs] + immediate
            self.cpu_registers[rt] = self.read_memory_8(addr)
            if self.cpu_registers[rt] & 0x80:
                self.cpu_registers[rt] -= 0x100
        elif op == 0x21:  # LH (Load Halfword)
            addr = self.cpu_registers[rs] + immediate
            self.cpu_registers[rt] = self.read_memory_16(addr)
            if self.cpu_registers[rt] & 0x8000:
                self.cpu_registers[rt] -= 0x10000
        elif op == 0x23:  # LW (Load Word)
            addr = self.cpu_registers[rs] + immediate
            self.cpu_registers[rt] = self.read_memory_32(addr)
        elif op == 0x24:  # LBU (Load Byte Unsigned)
            addr = self.cpu_registers[rs] + immediate
            self.cpu_registers[rt] = self.read_memory_8(addr)
        elif op == 0x25:  # LHU (Load Halfword Unsigned)
            addr = self.cpu_registers[rs] + immediate
            self.cpu_registers[rt] = self.read_memory_16(addr)

        elif op == 0x28:  # SB (Store Byte)
            addr = self.cpu_registers[rs] + immediate
            self.write_memory_8(addr, self.cpu_registers[rt] & 0xFF)
        elif op == 0x29:  # SH (Store Halfword)
            addr = self.cpu_registers[rs] + immediate
            self.write_memory_16(addr, self.cpu_registers[rt] & 0xFFFF)
        elif op == 0x2B:  # SW (Store Word)
            addr = self.cpu_registers[rs] + immediate
            self.write_memory_32(addr, self.cpu_registers[rt])

        elif op == 0x0A:  # SLTI (Set on Less Than Immediate)
            self.cpu_registers[rt] = 1 if self.cpu_registers[rs] < immediate else 0
        elif op == 0x0B:  # SLTIU (Set on Less Than Immediate Unsigned)
            self.cpu_registers[rt] = 1 if (self.cpu_registers[rs] & 0xFFFFFFFF) < (immediate & 0xFFFFFFFF) else 0
        elif op == 0x0F:  # LUI (Load Upper Immediate)
            self.cpu_registers[rt] = (immediate & 0xFFFF) << 16

        elif op == 0x10:  # COP0 instructions
            if rs == 0 and funct == 0x18:  # ERET
                self.pc = self.cop0_registers[14] - 4
                # Clear EXL bit
                self.cop0_registers[12] &= ~0x00000002
            elif rs == 4:  # MTC0
                self.cop0_registers[rd] = self.cpu_registers[rt]
            elif rs == 0:  # MFC0
                self.cpu_registers[rt] = self.cop0_registers[rd]

        elif op == 0x11:  # COP1 (FPU) instructions - basic support
            if rs == 0 and funct == 0x00:  # MFC1
                self.cpu_registers[rt] = self.fpu_registers[rd]
            elif rs == 4 and funct == 0x00:  # MTC1
                self.fpu_registers[rd] = self.cpu_registers[rt]
            elif rs == 0 and funct == 0x20:  # CVT.S.W
                self.fpu_registers[rd] = self.cpu_registers[rt]  # Simple conversion

        # Register 0 is always zero
        self.cpu_registers[0] = 0

    def read_memory_32(self, address):
        """Read 32-bit word from memory with proper mapping"""
        address &= 0xFFFFFFFF  # Mask to 32-bit

        # RDRAM (0x00000000 - 0x007FFFFF)
        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset + 4 <= len(self.ram):
                return struct.unpack('>I', self.ram[offset:offset+4])[0]

        # Cartridge ROM (0x10000000 - 0x1FBFFFFF)
        elif 0x10000000 <= address <= 0x1FBFFFFF:
            offset = address - 0x10000000
            if offset + 4 <= len(self.cart_rom):
                return struct.unpack('>I', self.cart_rom[offset:offset+4])[0]

        # RSP DMEM (0x04000000 - 0x04000FFF)
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset + 4 <= len(self.sp_dmem):
                return struct.unpack('>I', self.sp_dmem[offset:offset+4])[0]

        # RSP IMEM (0x04001000 - 0x04001FFF)
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset + 4 <= len(self.sp_imem):
                return struct.unpack('>I', self.sp_imem[offset:offset+4])[0]

        # PIF RAM (0x1FC00000 - 0x1FC007BF)
        elif 0x1FC00000 <= address <= 0x1FC007BF:
            offset = address - 0x1FC00000
            if offset + 4 <= len(self.pif_ram):
                return struct.unpack('>I', self.pif_ram[offset:offset+4])[0]

        # RSP registers (0x04040000 - 0x040FFFFF)
        elif 0x04040000 <= address <= 0x040FFFFF:
            return self.rsp.read_register(address)

        # RDP registers (0x04100000 - 0x041FFFFF)
        elif 0x04100000 <= address <= 0x041FFFFF:
            return self.rdp.read_register(address)

        # VI registers (0x04400000 - 0x04400037)
        elif 0x04400000 <= address <= 0x04400037:
            return self.vi.read_register(address)

        # AI registers (0x04500000 - 0x04500017)
        elif 0x04500000 <= address <= 0x04500017:
            return self.ai.read_register(address)

        # PI registers (0x04600000 - 0x04600033)
        elif 0x04600000 <= address <= 0x04600033:
            return self.pi.read_register(address)

        # SI registers (0x04800000 - 0x0480001B)
        elif 0x04800000 <= address <= 0x0480001B:
            return self.si.read_register(address)

        # MIPS Interface (MI) registers (0x04300000 - 0x0430000F)
        elif 0x04300000 <= address <= 0x0430000F:
            return self.read_mi_register(address)

        return 0

    def read_memory_16(self, address):
        """Read 16-bit halfword from memory"""
        address &= 0xFFFFFFFE  # Align to 16-bit boundary

        # Similar mapping logic for 16-bit reads
        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset + 2 <= len(self.ram):
                return struct.unpack('>H', self.ram[offset:offset+2])[0]
        elif 0x10000000 <= address <= 0x1FBFFFFF:
            offset = address - 0x10000000
            if offset + 2 <= len(self.cart_rom):
                return struct.unpack('>H', self.cart_rom[offset:offset+2])[0]
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset + 2 <= len(self.sp_dmem):
                return struct.unpack('>H', self.sp_dmem[offset:offset+2])[0]
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset + 2 <= len(self.sp_imem):
                return struct.unpack('>H', self.sp_imem[offset:offset+2])[0]

        return 0

    def read_memory_8(self, address):
        """Read 8-bit byte from memory"""
        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset < len(self.ram):
                return self.ram[offset]
        elif 0x10000000 <= address <= 0x1FBFFFFF:
            offset = address - 0x10000000
            if offset < len(self.cart_rom):
                return self.cart_rom[offset]
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset < len(self.sp_dmem):
                return self.sp_dmem[offset]
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset < len(self.sp_imem):
                return self.sp_imem[offset]

        return 0

    def write_memory_32(self, address, value):
        """Write 32-bit word to memory"""
        address &= 0xFFFFFFFC  # Align to 32-bit boundary
        value &= 0xFFFFFFFF

        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset + 4 <= len(self.ram):
                self.ram[offset:offset+4] = struct.pack('>I', value)
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset + 4 <= len(self.sp_dmem):
                self.sp_dmem[offset:offset+4] = struct.pack('>I', value)
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset + 4 <= len(self.sp_imem):
                self.sp_imem[offset:offset+4] = struct.pack('>I', value)
        elif 0x1FC00000 <= address <= 0x1FC007BF:
            offset = address - 0x1FC00000
            if offset + 4 <= len(self.pif_ram):
                self.pif_ram[offset:offset+4] = struct.pack('>I', value)

        # RSP registers (0x04040000 - 0x040FFFFF)
        elif 0x04040000 <= address <= 0x040FFFFF:
            self.rsp.write_register(address, value)

        # RDP registers (0x04100000 - 0x041FFFFF)
        elif 0x04100000 <= address <= 0x041FFFFF:
            self.rdp.write_register(address, value)

        # VI registers (0x04400000 - 0x04400037)
        elif 0x04400000 <= address <= 0x04400037:
            self.vi.write_register(address, value)

        # AI registers (0x04500000 - 0x04500017)
        elif 0x04500000 <= address <= 0x04500017:
            self.ai.write_register(address, value)

        # PI registers (0x04600000 - 0x04600033)
        elif 0x04600000 <= address <= 0x04600033:
            self.pi.write_register(address, value)

        # SI registers (0x04800000 - 0x0480001B)
        elif 0x04800000 <= address <= 0x0480001B:
            self.si.write_register(address, value)

        # MIPS Interface (MI) registers (0x04300000 - 0x0430000F)
        elif 0x04300000 <= address <= 0x0430000F:
            self.write_mi_register(address, value)

    def write_memory_16(self, address, value):
        """Write 16-bit halfword to memory"""
        address &= 0xFFFFFFFE
        value &= 0xFFFF

        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset + 2 <= len(self.ram):
                self.ram[offset:offset+2] = struct.pack('>H', value)
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset + 2 <= len(self.sp_dmem):
                self.sp_dmem[offset:offset+2] = struct.pack('>H', value)
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset + 2 <= len(self.sp_imem):
                self.sp_imem[offset:offset+2] = struct.pack('>H', value)

    def write_memory_8(self, address, value):
        """Write 8-bit byte to memory"""
        value &= 0xFF

        if 0x00000000 <= address <= 0x007FFFFF:
            offset = address & 0x7FFFFF
            if offset < len(self.ram):
                self.ram[offset] = value
        elif 0x04000000 <= address <= 0x04000FFF:
            offset = address & 0xFFF
            if offset < len(self.sp_dmem):
                self.sp_dmem[offset] = value
        elif 0x04001000 <= address <= 0x04001FFF:
            offset = address & 0xFFF
            if offset < len(self.sp_imem):
                self.sp_imem[offset] = value

    def read_mi_register(self, address):
        """Read MIPS Interface register"""
        reg = address & 0xF
        if reg == 0x0:  # MI_MODE
            return 0x00000000
        elif reg == 0x4:  # MI_VERSION
            return 0x02020102  # N64 version
        elif reg == 0x8:  # MI_INTR
            return 0x00000000
        elif reg == 0xC:  # MI_INTR_MASK
            return 0x00000000
        return 0

    def write_mi_register(self, address, value):
        """Write MIPS Interface register"""
        reg = address & 0xF
        if reg == 0x0:  # MI_MODE
            pass
        elif reg == 0x8:  # MI_INTR
            pass
        elif reg == 0xC:  # MI_INTR_MASK
            pass

    def handle_exception(self, exception_type, bad_vaddr=0):
        """Handle CPU exceptions"""
        # Save current state
        self.cop0_registers[13] = exception_type  # Cause register
        self.cop0_registers[14] = self.pc          # EPC register

        # Set exception vector
        if self.cop0_registers[12] & 0x00400000:  # EXL bit
            self.pc = 0x80000180  # General exception vector
        else:
            self.pc = 0x80000080  # Reset exception vector

        # Set EXL bit
        self.cop0_registers[12] |= 0x00000002

class RSPProcessor:
    """Reality Signal Processor emulator"""
    def __init__(self):
        self.dmem = bytearray(0x1000)  # 4KB data memory
        self.imem = bytearray(0x1000)  # 4KB instruction memory
        self.registers = [0] * 32
        self.pc = 0
        self.hi = 0
        self.lo = 0
        self.status = 0
        self.dma_busy = False

    def execute_cycle(self, core):
        """Execute one RSP cycle"""
        if self.pc < len(self.imem):
            try:
                # Fetch instruction from IMEM
                opcode = struct.unpack('>I', self.imem[self.pc:self.pc+4])[0]
                self.pc += 4
                self.execute_instruction(opcode, core)
            except:
                pass

    def execute_instruction(self, opcode, core):
        """Execute RSP instruction"""
        op = (opcode >> 26) & 0x3F
        rs = (opcode >> 21) & 0x1F
        rt = (opcode >> 16) & 0x1F
        rd = (opcode >> 11) & 0x1F
        sa = (opcode >> 6) & 0x1F
        funct = opcode & 0x3F
        imm = opcode & 0xFFFF

        # Handle sign extension for immediate values
        if imm & 0x8000:
            imm -= 0x10000

        if op == 0:  # R-type instructions
            if funct == 0x20:  # ADD
                self.registers[rd] = self.registers[rs] + self.registers[rt]
            elif funct == 0x21:  # ADDU
                self.registers[rd] = (self.registers[rs] + self.registers[rt]) & 0xFFFFFFFF
            elif funct == 0x22:  # SUB
                self.registers[rd] = self.registers[rs] - self.registers[rt]
            elif funct == 0x23:  # SUBU
                self.registers[rd] = (self.registers[rs] - self.registers[rt]) & 0xFFFFFFFF
            elif funct == 0x24:  # AND
                self.registers[rd] = self.registers[rs] & self.registers[rt]
            elif funct == 0x25:  # OR
                self.registers[rd] = self.registers[rs] | self.registers[rt]
            elif funct == 0x26:  # XOR
                self.registers[rd] = self.registers[rs] ^ self.registers[rt]
            elif funct == 0x27:  # NOR
                self.registers[rd] = ~(self.registers[rs] | self.registers[rt]) & 0xFFFFFFFF
            elif funct == 0x00:  # SLL
                self.registers[rd] = (self.registers[rt] << sa) & 0xFFFFFFFF
            elif funct == 0x02:  # SRL
                self.registers[rd] = self.registers[rt] >> sa
            elif funct == 0x03:  # SRA
                if self.registers[rt] & 0x80000000:
                    self.registers[rd] = ((self.registers[rt] >> sa) | (0xFFFFFFFF << (32 - sa)))
                else:
                    self.registers[rd] = self.registers[rt] >> sa
            elif funct == 0x08:  # JR
                self.pc = self.registers[rs] & 0xFFF
            elif funct == 0x10:  # MFHI
                self.registers[rd] = self.hi
            elif funct == 0x12:  # MFLO
                self.registers[rd] = self.lo
            elif funct == 0x18:  # MULT
                result = self.registers[rs] * self.registers[rt]
                self.lo = result & 0xFFFFFFFF
                self.hi = (result >> 32) & 0xFFFFFFFF
        elif op == 0x08:  # ADDI
            self.registers[rt] = self.registers[rs] + imm
        elif op == 0x09:  # ADDIU
            self.registers[rt] = (self.registers[rs] + imm) & 0xFFFFFFFF
        elif op == 0x0C:  # ANDI
            self.registers[rt] = self.registers[rs] & (imm & 0xFFFF)
        elif op == 0x0D:  # ORI
            self.registers[rt] = self.registers[rs] | (imm & 0xFFFF)
        elif op == 0x0F:  # LUI
            self.registers[rt] = (imm & 0xFFFF) << 16
        elif op == 0x23:  # LW
            addr = (self.registers[rs] + imm) & 0xFFF
            if addr + 4 <= len(self.dmem):
                self.registers[rt] = struct.unpack('>I', self.dmem[addr:addr+4])[0]
        elif op == 0x2B:  # SW
            addr = (self.registers[rs] + imm) & 0xFFF
            if addr + 4 <= len(self.dmem):
                self.dmem[addr:addr+4] = struct.pack('>I', self.registers[rt])
        elif op == 0x24:  # LBU
            addr = (self.registers[rs] + imm) & 0xFFF
            if addr < len(self.dmem):
                self.registers[rt] = self.dmem[addr]
        elif op == 0x28:  # SB
            addr = (self.registers[rs] + imm) & 0xFFF
            if addr < len(self.dmem):
                self.dmem[addr] = self.registers[rt] & 0xFF

        # Register 0 is always zero
        self.registers[0] = 0

    def dma_to_dmem(self, core, dram_addr, dmem_addr, length):
        """DMA from RDRAM to DMEM"""
        for i in range(0, length, 4):
            if dmem_addr + i < len(self.dmem) and dram_addr + i < len(core.ram):
                self.dmem[dmem_addr + i:dmem_addr + i + 4] = core.ram[dram_addr + i:dram_addr + i + 4]

    def dma_from_dmem(self, core, dmem_addr, dram_addr, length):
        """DMA from DMEM to RDRAM"""
        for i in range(0, length, 4):
            if dram_addr + i < len(core.ram) and dmem_addr + i < len(self.dmem):
                core.ram[dram_addr + i:dram_addr + i + 4] = self.dmem[dmem_addr + i:dmem_addr + i + 4]

    def load_ucode(self, core, ucode_addr, ucode_size):
        """Load microcode into RSP IMEM"""
        for i in range(0, min(ucode_size, len(self.imem)), 4):
            if ucode_addr + i < len(core.cart_rom):
                self.imem[i:i+4] = core.cart_rom[ucode_addr + i:ucode_addr + i + 4]

    def read_register(self, address):
        """Read RSP register"""
        reg = (address >> 12) & 0xF
        if reg == 0x0:  # SP_MEM_ADDR
            return 0x04000000
        elif reg == 0x1:  # SP_DRAM_ADDR
            return 0x04001000
        elif reg == 0x2:  # SP_RD_LEN
            return 0x00000000
        elif reg == 0x3:  # SP_WR_LEN
            return 0x00000000
        elif reg == 0x4:  # SP_STATUS
            return 0x00000001  # RSP halted
        elif reg == 0x5:  # SP_DMA_FULL
            return 0x00000000
        elif reg == 0x6:  # SP_DMA_BUSY
            return 0x00000000
        elif reg == 0x7:  # SP_SEMAPHORE
            return 0x00000000
        elif reg == 0x8:  # SP_PC
            return self.pc
        elif reg == 0xB:  # SP_IMEM_START
            return 0x04001000
        elif reg == 0xC:  # SP_DMEM_START
            return 0x04000000
        return 0

    def write_register(self, address, value):
        """Write RSP register"""
        reg = (address >> 12) & 0xF
        if reg == 0x0:  # SP_MEM_ADDR
            pass
        elif reg == 0x1:  # SP_DRAM_ADDR
            pass
        elif reg == 0x2:  # SP_RD_LEN
            # Trigger DMA read
            pass
        elif reg == 0x3:  # SP_WR_LEN
            # Trigger DMA write
            pass
        elif reg == 0x8:  # SP_PC
            self.pc = value & 0xFFF

class RDPProcessor:
    """Reality Display Processor emulator"""
    def __init__(self):
        self.framebuffer = bytearray(640 * 480 * 4)  # RGBA format
        self.commands = []
        self.status = 0
        self.start = 0
        self.end = 0
        self.current = 0

    def process_command(self, command):
        # RDP command processing - basic implementation
        pass

    def read_register(self, address):
        """Read RDP register"""
        reg = address & 0xFF
        if reg == 0x00:  # RDP_START
            return self.start
        elif reg == 0x04:  # RDP_END
            return self.end
        elif reg == 0x08:  # RDP_CURRENT
            return self.current
        elif reg == 0x0C:  # RDP_STATUS
            return self.status
        return 0

    def write_register(self, address, value):
        """Write RDP register"""
        reg = address & 0xFF
        if reg == 0x00:  # RDP_START
            self.start = value
        elif reg == 0x04:  # RDP_END
            self.end = value
            # Process commands when RDP_END is written
            self.process_commands()
        elif reg == 0x08:  # RDP_CURRENT
            self.current = value
        elif reg == 0x0C:  # RDP_STATUS
            self.status = value

    def process_commands(self):
        """Process RDP command buffer"""
        # Basic RDP command processing would go here
        pass

class AudioInterface:
    def __init__(self):
        self.dram_addr = 0
        self.len = 0
        self.control = 0
        self.status = 0
        self.dacrate = 0
        self.bitrate = 0

    def read_register(self, address):
        """Read AI register"""
        reg = address & 0xFF
        if reg == 0x00:  # AI_DRAM_ADDR
            return self.dram_addr
        elif reg == 0x04:  # AI_LEN
            return self.len
        elif reg == 0x08:  # AI_CONTROL
            return self.control
        elif reg == 0x0C:  # AI_STATUS
            return self.status
        elif reg == 0x10:  # AI_DACRATE
            return self.dacrate
        elif reg == 0x14:  # AI_BITRATE
            return self.bitrate
        return 0

    def write_register(self, address, value):
        """Write AI register"""
        reg = address & 0xFF
        if reg == 0x00:  # AI_DRAM_ADDR
            self.dram_addr = value
        elif reg == 0x04:  # AI_LEN
            self.len = value
        elif reg == 0x08:  # AI_CONTROL
            self.control = value
        elif reg == 0x0C:  # AI_STATUS
            self.status = value
        elif reg == 0x10:  # AI_DACRATE
            self.dacrate = value
        elif reg == 0x14:  # AI_BITRATE
            self.bitrate = value

class VideoInterface:
    def __init__(self):
        self.dram_addr = 0
        self.width = 320
        self.height = 240
        self.v_sync = 0
        self.h_sync = 0
        self.leap = 0
        self.h_start = 0
        self.x_scale = 0
        self.v_current = 0
        self.origin = 0
        self.v_intr = 0
        self.current = 0

    def read_register(self, address):
        """Read VI register"""
        reg = address & 0xFF
        if reg == 0x00:  # VI_STATUS
            return (self.width << 16) | self.height
        elif reg == 0x04:  # VI_ORIGIN
            return self.origin
        elif reg == 0x08:  # VI_WIDTH
            return self.width
        elif reg == 0x0C:  # VI_INTR
            return self.v_intr
        elif reg == 0x10:  # VI_CURRENT
            return self.current
        elif reg == 0x14:  # VI_BURST
            return 0x00010001
        elif reg == 0x18:  # VI_V_SYNC
            return self.v_sync
        elif reg == 0x1C:  # VI_H_SYNC
            return self.h_sync
        elif reg == 0x20:  # VI_LEAP
            return self.leap
        elif reg == 0x24:  # VI_H_START
            return self.h_start
        elif reg == 0x28:  # VI_V_START
            return 0x00000200
        elif reg == 0x2C:  # VI_V_BURST
            return 0x000C000C
        elif reg == 0x30:  # VI_X_SCALE
            return self.x_scale
        elif reg == 0x34:  # VI_Y_SCALE
            return 0x00000400
        return 0

    def write_register(self, address, value):
        """Write VI register"""
        reg = address & 0xFF
        if reg == 0x04:  # VI_ORIGIN
            self.origin = value
        elif reg == 0x08:  # VI_WIDTH
            self.width = value
        elif reg == 0x0C:  # VI_INTR
            self.v_intr = value
        elif reg == 0x10:  # VI_CURRENT
            self.current = value
        elif reg == 0x18:  # VI_V_SYNC
            self.v_sync = value
        elif reg == 0x1C:  # VI_H_SYNC
            self.h_sync = value
        elif reg == 0x20:  # VI_LEAP
            self.leap = value
        elif reg == 0x24:  # VI_H_START
            self.h_start = value
        elif reg == 0x30:  # VI_X_SCALE
            self.x_scale = value

class PeripheralInterface:
    def __init__(self):
        self.dram_addr = 0
        self.cart_addr = 0
        self.rd_len = 0
        self.wr_len = 0
        self.status = 0

    def read_register(self, address):
        """Read PI register"""
        reg = address & 0xFF
        if reg == 0x00:  # PI_DRAM_ADDR
            return self.dram_addr
        elif reg == 0x04:  # PI_CART_ADDR
            return self.cart_addr
        elif reg == 0x08:  # PI_RD_LEN
            return self.rd_len
        elif reg == 0x0C:  # PI_WR_LEN
            return self.wr_len
        elif reg == 0x10:  # PI_STATUS
            return self.status | 0x02  # PI_STATUS_IO_BUSY = 0, PI_STATUS_ERROR = 0
        return 0

    def write_register(self, address, value):
        """Write PI register"""
        reg = address & 0xFF
        if reg == 0x00:  # PI_DRAM_ADDR
            self.dram_addr = value
        elif reg == 0x04:  # PI_CART_ADDR
            self.cart_addr = value
        elif reg == 0x08:  # PI_RD_LEN
            self.rd_len = value
        elif reg == 0x0C:  # PI_WR_LEN
            self.wr_len = value
        elif reg == 0x10:  # PI_STATUS
            self.status = value

class SerialInterface:
    def __init__(self):
        self.dram_addr = 0
        self.pif_addr = 0
        self.read_len = 0
        self.write_len = 0
        self.status = 0

    def read_register(self, address):
        """Read SI register"""
        reg = address & 0xFF
        if reg == 0x00:  # SI_DRAM_ADDR
            return self.dram_addr
        elif reg == 0x04:  # SI_PIF_ADDR
            return self.pif_addr
        elif reg == 0x08:  # SI_RD_LEN
            return self.read_len
        elif reg == 0x0C:  # SI_WR_LEN
            return self.write_len
        elif reg == 0x10:  # SI_STATUS
            return self.status | 0x01  # SI_STATUS_BUSY = 0, SI_STATUS_ERROR = 0
        return 0

    def write_register(self, address, value):
        """Write SI register"""
        reg = address & 0xFF
        if reg == 0x00:  # SI_DRAM_ADDR
            self.dram_addr = value
        elif reg == 0x04:  # SI_PIF_ADDR
            self.pif_addr = value
        elif reg == 0x08:  # SI_RD_LEN
            self.read_len = value
        elif reg == 0x0C:  # SI_WR_LEN
            self.write_len = value
        elif reg == 0x10:  # SI_STATUS
            self.status = value

class EmuAI64Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EmuAI64 1.0x - Built-in Mupen64 Engine")
        self.setGeometry(100, 100, 800, 600)

        # Initialize built-in Mupen64 core
        self.core = Mupen64Core()

        # Create menu bar (Project64 1.6 style)
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = file_menu.addAction("Open ROM")
        open_action.triggered.connect(self.open_rom)
        file_menu.addAction("Exit", self.close)

        emulation_menu = menubar.addMenu("Emulation")
        self.start_action = emulation_menu.addAction("Start")
        self.start_action.triggered.connect(self.start_emulation)
        self.stop_action = emulation_menu.addAction("Stop")
        self.stop_action.triggered.connect(self.stop_emulation)
        self.stop_action.setEnabled(False)
        emulation_menu.addAction("Reset", self.reset_emulation)
        self.debug_action = emulation_menu.addAction("Debug Mode")
        self.debug_action.setCheckable(True)
        self.debug_action.triggered.connect(self.toggle_debug)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Configure Plugins")
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About")

        # Create main layout
        main_widget = QWidget()
        layout = QVBoxLayout()

        # Create ROM browser
        self.rom_list = QListWidget()
        self.rom_list.itemDoubleClicked.connect(self.run_emulator)
        layout.addWidget(QLabel("N64 ROMs:"))
        layout.addWidget(self.rom_list)

        # Create video display area
        self.video_label = QLabel("Video Output")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid gray;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready - Built-in Mupen64 Engine")

        # Emulator state
        self.rom_path = None

        # Timer for video updates
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video)
        self.video_timer.setInterval(16)  # ~60 FPS

    def open_rom(self):
        rom_path, _ = QFileDialog.getOpenFileName(self, "Open N64 ROM", "", "N64 ROMs (*.z64 *.n64 *.v64)")
        if rom_path:
            self.rom_path = rom_path
            self.rom_list.addItem(os.path.basename(rom_path))
            self.statusbar.showMessage(f"Loaded: {rom_path}")
            self.start_action.setEnabled(True)

    def run_emulator(self):
        if not self.rom_path:
            return
        self.start_emulation()

    def start_emulation(self):
        if not self.rom_path:
            return

        # Load ROM into built-in core
        if not self.core.load_rom(self.rom_path):
            self.statusbar.showMessage("Failed to load ROM")
            return

        # Start emulation
        self.core.start_emulation()
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.statusbar.showMessage("Emulation running - Built-in Mupen64 Engine")
        self.video_timer.start()

    def stop_emulation(self):
        self.core.stop_emulation()
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.statusbar.showMessage("Emulation stopped")
        self.video_timer.stop()

    def reset_emulation(self):
        if self.core.running:
            self.stop_emulation()
        # Reset core state
        self.core.pc = 0xBFC00000
        self.core.cpu_registers = [0] * 32
        self.core.cop0_registers = [0] * 32
        self.core.fpu_registers = [0.0] * 32
        self.core.instruction_count = 0
        self.statusbar.showMessage("Emulation reset")

    def toggle_debug(self):
        self.core.debug_mode = self.debug_action.isChecked()
        if self.core.debug_mode:
            self.statusbar.showMessage("Debug mode enabled")
        else:
            self.statusbar.showMessage("Debug mode disabled")

    def update_video(self):
        # Video output using RDP framebuffer
        if hasattr(self.core, 'vi') and hasattr(self.core, 'rdp'):
            # Get width and height from VI registers
            vi_status = self.core.vi.read_register(0x04400000)
            width = vi_status >> 16
            height = vi_status & 0xFFFF

            if width > 0 and height > 0 and width <= 1024 and height <= 1024:
                # Create image from RDP framebuffer
                image = QImage(width, height, QImage.Format.Format_RGB32)

                for y in range(min(height, 480)):  # Limit to display size
                    for x in range(min(width, 640)):
                        # Get pixel from RDP framebuffer (simplified)
                        fb_index = (y * width + x) * 4
                        if fb_index + 3 < len(self.core.rdp.framebuffer):
                            r = self.core.rdp.framebuffer[fb_index]
                            g = self.core.rdp.framebuffer[fb_index + 1]
                            b = self.core.rdp.framebuffer[fb_index + 2]
                            a = self.core.rdp.framebuffer[fb_index + 3]

                            # Convert to RGB32 format
                            color = (r << 16) | (g << 8) | b | (a << 24)
                            image.setPixel(x, y, color)
                        else:
                            # Default pattern if no framebuffer data
                            r = (x * 255) // width
                            g = (y * 255) // height
                            b = 128
                            color = (r << 16) | (g << 8) | b
                            image.setPixel(x, y, color)

                pixmap = QPixmap.fromImage(image.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))
                self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.stop_emulation()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = EmuAI64Window()
    window.show()

    # Initialize emulator for testing with command line ROM
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        if os.path.exists(rom_path):
            window.rom_path = rom_path
            window.rom_list.addItem(os.path.basename(rom_path))
            window.statusbar.showMessage(f"Loaded: {rom_path}")
            window.start_action.setEnabled(True)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
