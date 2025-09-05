#!/usr/bin/env python3
"""
Universal Mario 64 ROM Tool - Advanced Extraction Version
=========================================================

A comprehensive tool for extracting and converting all assets from Super Mario 64 ROMs
into standard, usable formats.

Features:
- Intelligent file detection and extraction
- MIO0 compression support (SM64's primary compression)
- Texture extraction and conversion (RGBA16, RGBA32, IA8, etc.)
- Audio bank and sequence extraction
- Level data parsing
- Model extraction (experimental)
- Automatic file organization

Author: Advanced version
License: MIT
Version: 3.0.0
"""

import argparse
import binascii
import json
import os
import struct
import sys
import threading
import queue
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Callable, BinaryIO
from enum import Enum, auto

# GUI imports (optional)
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

# Try to import PIL for image conversion
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ===========================
# Constants and Configuration
# ===========================

# ROM format magic numbers
MAGIC_Z64 = b"\x80\x37\x12\x40"  # Big-endian
MAGIC_V64 = b"\x37\x80\x40\x12"  # Byte-swapped
MAGIC_N64 = b"\x40\x12\x37\x80"  # Little-endian

# File signatures
MAGIC_MIO0 = b"MIO0"
MAGIC_YAZ0 = b"Yaz0"
MAGIC_AUDIO_BANK = b"B\x00\x00\x00"  # Common audio bank marker
MAGIC_SEQUENCE = b"SEQP"  # Sequence marker

# SM64-specific offsets (US version)
SM64_SEGMENTS = {
    0x00: (0x000000, 0x007000, "Boot/RSP"),
    0x02: (0x108A40, 0x114750, "Segment 02"),
    0x04: (0x000000, 0x000000, "Dynamic"),  # Loaded at runtime
    0x05: (0x000000, 0x000000, "Dynamic"),  # Loaded at runtime
    0x06: (0x000000, 0x000000, "Dynamic"),  # Loaded at runtime
    0x07: (0x000000, 0x000000, "Dynamic"),  # Loaded at runtime
    0x08: (0x800000, 0x801000, "Common Textures 0"),
    0x09: (0x802000, 0x803000, "Common Textures 1"),
    0x0E: (0x000000, 0x000000, "Level Geometry"),
    0x0F: (0x000000, 0x000000, "Level Scripts"),
}

# Texture formats
class TextureFormat(Enum):
    RGBA32 = auto()
    RGBA16 = auto()
    IA16 = auto()
    IA8 = auto()
    IA4 = auto()
    I8 = auto()
    I4 = auto()
    CI8 = auto()
    CI4 = auto()

# File size limits
MIN_ROM_SIZE = 8 * 1024 * 1024   # 8 MB
MAX_ROM_SIZE = 64 * 1024 * 1024  # 64 MB


# ===========================
# Utility Functions
# ===========================

def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def calculate_crc32(data: bytes) -> str:
    """Calculate CRC32 checksum."""
    return f"{binascii.crc32(data) & 0xFFFFFFFF:08X}"


def ensure_directory(path: str) -> None:
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def read_u32_be(data: bytes, offset: int) -> int:
    """Read 32-bit big-endian unsigned integer."""
    return struct.unpack(">I", data[offset:offset+4])[0]


def read_u16_be(data: bytes, offset: int) -> int:
    """Read 16-bit big-endian unsigned integer."""
    return struct.unpack(">H", data[offset:offset+2])[0]


# ===========================
# ROM Format Handling
# ===========================

@dataclass
class RomInfo:
    """ROM file information."""
    path: str
    size: int
    layout: str
    crc32: str
    game_id: str = ""
    version: str = ""
    name: str = ""


class RomFormatError(Exception):
    """ROM format error."""
    pass


def detect_rom_layout(header: bytes) -> str:
    """Detect ROM byte order from header."""
    if header == MAGIC_Z64:
        return "z64"
    elif header == MAGIC_V64:
        return "v64"  
    elif header == MAGIC_N64:
        return "n64"
    else:
        return "unknown"


def normalize_rom(data: bytes, layout: str) -> bytes:
    """Convert ROM to big-endian format."""
    if layout == "z64":
        return data
    elif layout == "v64":
        # Swap every 2 bytes
        output = bytearray(len(data))
        output[0::2] = data[1::2]
        output[1::2] = data[0::2]
        return bytes(output)
    elif layout == "n64":
        # Swap every 4 bytes
        output = bytearray(len(data))
        output[0::4] = data[3::4]
        output[1::4] = data[2::4]
        output[2::4] = data[1::4]
        output[3::4] = data[0::4]
        return bytes(output)
    return data


def read_rom(path: str) -> Tuple[RomInfo, bytes]:
    """Read and normalize ROM file."""
    if not Path(path).exists():
        raise FileNotFoundError(f"ROM file not found: {path}")
    
    file_size = os.path.getsize(path)
    if file_size < MIN_ROM_SIZE:
        raise RomFormatError(f"ROM too small: {human_readable_size(file_size)}")
    if file_size > MAX_ROM_SIZE:
        raise RomFormatError(f"ROM too large: {human_readable_size(file_size)}")
    
    with open(path, "rb") as f:
        data = f.read()
    
    layout = detect_rom_layout(data[:4])
    normalized = normalize_rom(data, layout)
    
    # Extract ROM info from header
    game_id = normalized[0x3B:0x3F].decode('ascii', errors='ignore')
    version = f"{normalized[0x3F]}"
    name = normalized[0x20:0x34].decode('ascii', errors='ignore').strip()
    
    info = RomInfo(
        path=path,
        size=file_size,
        layout=layout,
        crc32=calculate_crc32(normalized),
        game_id=game_id,
        version=version,
        name=name
    )
    
    return info, normalized


# ===========================
# MIO0 Decompression
# ===========================

class MIO0:
    """MIO0 compression handler."""
    
    @staticmethod
    def is_mio0(data: bytes, offset: int = 0) -> bool:
        """Check if data contains MIO0 header."""
        return data[offset:offset+4] == MAGIC_MIO0
    
    @staticmethod
    def decompress(data: bytes, offset: int = 0) -> bytes:
        """
        Decompress MIO0 data.
        
        MIO0 format:
        - 0x00: "MIO0" magic
        - 0x04: Decompressed size
        - 0x08: Compressed data offset
        - 0x0C: Uncompressed data offset
        """
        if not MIO0.is_mio0(data, offset):
            raise ValueError("Not a MIO0 header")
        
        # Read header
        decompressed_size = read_u32_be(data, offset + 4)
        comp_offset = offset + read_u32_be(data, offset + 8)
        uncomp_offset = offset + read_u32_be(data, offset + 12)
        
        # Setup
        output = bytearray(decompressed_size)
        out_pos = 0
        
        # Layout bit stream
        layout_offset = offset + 16
        layout_bit = 0x80000000
        layout_word = read_u32_be(data, layout_offset)
        
        while out_pos < decompressed_size:
            if layout_word & layout_bit:
                # Uncompressed byte
                output[out_pos] = data[uncomp_offset]
                uncomp_offset += 1
                out_pos += 1
            else:
                # Compressed - back reference
                cmd = read_u16_be(data, comp_offset)
                comp_offset += 2
                
                length = (cmd >> 12) + 3
                distance = (cmd & 0x0FFF) + 1
                
                for _ in range(length):
                    output[out_pos] = output[out_pos - distance]
                    out_pos += 1
            
            # Next layout bit
            layout_bit >>= 1
            if layout_bit == 0:
                layout_offset += 4
                layout_word = read_u32_be(data, layout_offset)
                layout_bit = 0x80000000
        
        return bytes(output)


# ===========================
# Texture Handling
# ===========================

class TextureExtractor:
    """Extract and convert N64 textures."""
    
    @staticmethod
    def rgba16_to_rgba32(data: bytes, width: int, height: int) -> bytes:
        """Convert RGBA16 (5551) to RGBA32."""
        output = bytearray(width * height * 4)
        
        for i in range(width * height):
            pixel = read_u16_be(data, i * 2)
            
            r = ((pixel >> 11) & 0x1F) * 8
            g = ((pixel >> 6) & 0x1F) * 8
            b = ((pixel >> 1) & 0x1F) * 8
            a = 255 if (pixel & 1) else 0
            
            output[i*4:i*4+4] = [r, g, b, a]
        
        return bytes(output)
    
    @staticmethod
    def ia8_to_rgba32(data: bytes, width: int, height: int) -> bytes:
        """Convert IA8 (intensity-alpha) to RGBA32."""
        output = bytearray(width * height * 4)
        
        for i in range(width * height):
            intensity = (data[i] >> 4) * 17
            alpha = (data[i] & 0x0F) * 17
            
            output[i*4:i*4+4] = [intensity, intensity, intensity, alpha]
        
        return bytes(output)
    
    @staticmethod
    def i8_to_rgba32(data: bytes, width: int, height: int) -> bytes:
        """Convert I8 (grayscale) to RGBA32."""
        output = bytearray(width * height * 4)
        
        for i in range(width * height):
            intensity = data[i]
            output[i*4:i*4+4] = [intensity, intensity, intensity, 255]
        
        return bytes(output)
    
    @staticmethod
    def save_as_png(rgba_data: bytes, width: int, height: int, output_path: str) -> bool:
        """Save RGBA32 data as PNG if PIL is available."""
        if not PIL_AVAILABLE:
            return False
        
        try:
            img = Image.frombytes('RGBA', (width, height), rgba_data)
            img.save(output_path)
            return True
        except Exception:
            return False


# ===========================
# Asset Scanner and Extractor
# ===========================

@dataclass
class ExtractedAsset:
    """Information about an extracted asset."""
    type: str
    offset: int
    size: int
    output_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssetExtractor:
    """Advanced asset extraction from SM64 ROM."""
    
    def __init__(self, rom_data: bytes, output_dir: str):
        self.rom_data = rom_data
        self.output_dir = output_dir
        self.extracted_assets: List[ExtractedAsset] = []
        
    def extract_all(self, progress_callback: Optional[Callable] = None) -> List[ExtractedAsset]:
        """Extract all detectable assets from ROM."""
        total_steps = 7
        current_step = 0
        
        def update_progress(msg: str):
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, msg)
        
        # Create output directories
        self._create_directories()
        
        # Extract different asset types
        update_progress("Scanning for MIO0 compressed data...")
        self._extract_mio0_blocks()
        
        update_progress("Extracting texture data...")
        self._extract_textures()
        
        update_progress("Extracting audio banks...")
        self._extract_audio_banks()
        
        update_progress("Extracting level data...")
        self._extract_level_data()
        
        update_progress("Extracting models...")
        self._extract_models()
        
        update_progress("Generating metadata...")
        self._generate_metadata()
        
        update_progress("Complete!")
        
        return self.extracted_assets
    
    def _create_directories(self):
        """Create organized output directory structure."""
        dirs = [
            "compressed/mio0",
            "compressed/yaz0",
            "textures/common",
            "textures/levels",
            "audio/banks",
            "audio/sequences",
            "models/objects",
            "models/levels",
            "levels/geometry",
            "levels/scripts",
            "misc"
        ]
        
        for dir_path in dirs:
            ensure_directory(os.path.join(self.output_dir, dir_path))
    
    def _extract_mio0_blocks(self):
        """Find and extract all MIO0 compressed blocks."""
        offset = 0
        mio0_count = 0
        
        while offset < len(self.rom_data) - 16:
            if MIO0.is_mio0(self.rom_data, offset):
                try:
                    # Get compressed size
                    header_data = self.rom_data[offset:offset+16]
                    decompressed_size = read_u32_be(header_data, 4)
                    
                    # Find end of MIO0 block (heuristic)
                    comp_end = offset + 16
                    while comp_end < len(self.rom_data) and comp_end < offset + 0x100000:
                        if MIO0.is_mio0(self.rom_data, comp_end):
                            break
                        comp_end += 4
                    
                    # Extract compressed block
                    compressed = self.rom_data[offset:comp_end]
                    
                    # Decompress
                    decompressed = MIO0.decompress(self.rom_data, offset)
                    
                    # Save both compressed and decompressed
                    comp_path = os.path.join(self.output_dir, f"compressed/mio0/mio0_{mio0_count:03d}_0x{offset:08X}.bin")
                    decomp_path = os.path.join(self.output_dir, f"compressed/mio0/mio0_{mio0_count:03d}_0x{offset:08X}_decomp.bin")
                    
                    with open(comp_path, "wb") as f:
                        f.write(compressed)
                    
                    with open(decomp_path, "wb") as f:
                        f.write(decompressed)
                    
                    # Analyze decompressed content
                    content_type = self._identify_content(decompressed)
                    
                    self.extracted_assets.append(ExtractedAsset(
                        type="MIO0",
                        offset=offset,
                        size=len(compressed),
                        output_path=decomp_path,
                        metadata={
                            "compressed_size": len(compressed),
                            "decompressed_size": len(decompressed),
                            "content_type": content_type
                        }
                    ))
                    
                    mio0_count += 1
                    offset = comp_end
                    
                except Exception as e:
                    # Skip invalid MIO0 blocks
                    offset += 4
            else:
                offset += 4
    
    def _identify_content(self, data: bytes) -> str:
        """Identify the type of content in decompressed data."""
        if len(data) < 16:
            return "unknown"
        
        # Check for common patterns
        if b"\x00\x00\x00\x00" * 4 in data[:64]:
            # Likely texture or model data
            non_zero = sum(1 for b in data[:1024] if b != 0)
            if non_zero > 512:
                return "texture_data"
            else:
                return "model_data"
        
        # Check for level scripts (common opcodes)
        if data[0] in [0x00, 0x02, 0x04, 0x06, 0x08]:
            return "level_script"
        
        return "unknown"
    
    def _extract_textures(self):
        """Extract texture data from known locations."""
        # Common texture banks in SM64
        texture_banks = [
            (0x108A40, 0x114750, "segment_02"),
            (0x114750, 0x134D50, "segment_03"),
            (0x134D50, 0x13B910, "segment_04"),
            (0x13B910, 0x145E90, "segment_05"),
            (0x145E90, 0x152390, "segment_06"),
            (0x152390, 0x160670, "segment_07"),
            (0x160670, 0x166C70, "segment_08"),
            (0x166C70, 0x16D870, "segment_09"),
        ]
        
        for start, end, name in texture_banks:
            if start >= len(self.rom_data) or end > len(self.rom_data):
                continue
            
            data = self.rom_data[start:end]
            output_path = os.path.join(self.output_dir, f"textures/common/{name}.bin")
            
            with open(output_path, "wb") as f:
                f.write(data)
            
            # Try to extract individual textures (experimental)
            self._extract_individual_textures(data, name)
            
            self.extracted_assets.append(ExtractedAsset(
                type="texture_bank",
                offset=start,
                size=end - start,
                output_path=output_path,
                metadata={"bank_name": name}
            ))
    
    def _extract_individual_textures(self, data: bytes, bank_name: str):
        """Attempt to extract individual textures from a bank."""
        # This is highly experimental and game-specific
        # Common texture sizes in SM64
        common_sizes = [
            (32, 32, TextureFormat.RGBA16),
            (64, 32, TextureFormat.RGBA16),
            (32, 64, TextureFormat.RGBA16),
            (64, 64, TextureFormat.RGBA16),
        ]
        
        if not PIL_AVAILABLE:
            return
        
        tex_dir = os.path.join(self.output_dir, f"textures/common/{bank_name}_extracted")
        ensure_directory(tex_dir)
        
        offset = 0
        tex_count = 0
        
        for width, height, fmt in common_sizes:
            if fmt == TextureFormat.RGBA16:
                size = width * height * 2
                
                while offset + size <= len(data):
                    # Try to convert and save
                    try:
                        tex_data = data[offset:offset+size]
                        rgba_data = TextureExtractor.rgba16_to_rgba32(tex_data, width, height)
                        
                        output_path = os.path.join(tex_dir, f"tex_{tex_count:04d}_{width}x{height}.png")
                        if TextureExtractor.save_as_png(rgba_data, width, height, output_path):
                            tex_count += 1
                    except Exception:
                        pass
                    
                    offset += size
    
    def _extract_audio_banks(self):
        """Extract audio banks and sequences."""
        # SM64 audio bank locations (approximate)
        audio_banks = [
            (0x57B720, 0x5C6D80, "audio_bank_1"),
            (0x5C6D80, 0x61F5E0, "audio_bank_2"),
            (0x61F5E0, 0x662A40, "audio_bank_3"),
        ]
        
        for start, end, name in audio_banks:
            if start >= len(self.rom_data) or end > len(self.rom_data):
                continue
            
            data = self.rom_data[start:end]
            output_path = os.path.join(self.output_dir, f"audio/banks/{name}.bin")
            
            with open(output_path, "wb") as f:
                f.write(data)
            
            self.extracted_assets.append(ExtractedAsset(
                type="audio_bank",
                offset=start,
                size=end - start,
                output_path=output_path,
                metadata={"bank_name": name}
            ))
    
    def _extract_level_data(self):
        """Extract level geometry and scripts."""
        # SM64 level data locations
        levels = [
            (0x3D0DC0, 0x3E3A60, "bob_omb_battlefield"),
            (0x3E3A60, 0x3F5E00, "whomp_fortress"),
            (0x3F5E00, 0x405FB0, "jolly_roger_bay"),
            (0x405FB0, 0x419F90, "cool_cool_mountain"),
            (0x419F90, 0x42CF20, "big_boos_haunt"),
            (0x42CF20, 0x437870, "hazy_maze_cave"),
            (0x437870, 0x444CB0, "lethal_lava_land"),
            (0x444CB0, 0x454E00, "shifting_sand_land"),
            (0x454E00, 0x45E320, "dire_dire_docks"),
        ]
        
        for start, end, name in levels:
            if start >= len(self.rom_data) or end > len(self.rom_data):
                continue
            
            data = self.rom_data[start:end]
            
            # Check if compressed
            if MIO0.is_mio0(data):
                try:
                    data = MIO0.decompress(data)
                    name += "_decompressed"
                except Exception:
                    pass
            
            output_path = os.path.join(self.output_dir, f"levels/geometry/{name}.bin")
            
            with open(output_path, "wb") as f:
                f.write(data)
            
            self.extracted_assets.append(ExtractedAsset(
                type="level_data",
                offset=start,
                size=end - start,
                output_path=output_path,
                metadata={"level_name": name}
            ))
    
    def _extract_models(self):
        """Extract 3D model data."""
        # SM64 model data locations (approximate)
        models = [
            (0x114750, 0x12A7E0, "mario_model"),
            (0x12A7E0, 0x132C60, "object_models_1"),
            (0x132C60, 0x134D50, "object_models_2"),
        ]
        
        for start, end, name in models:
            if start >= len(self.rom_data) or end > len(self.rom_data):
                continue
            
            data = self.rom_data[start:end]
            output_path = os.path.join(self.output_dir, f"models/objects/{name}.bin")
            
            with open(output_path, "wb") as f:
                f.write(data)
            
            self.extracted_assets.append(ExtractedAsset(
                type="model_data",
                offset=start,
                size=end - start,
                output_path=output_path,
                metadata={"model_name": name}
            ))
    
    def _generate_metadata(self):
        """Generate metadata file with extraction information."""
        metadata = {
            "rom_crc32": calculate_crc32(self.rom_data),
            "rom_size": len(self.rom_data),
            "extraction_summary": {
                "total_assets": len(self.extracted_assets),
                "asset_types": {}
            },
            "assets": []
        }
        
        # Count asset types
        for asset in self.extracted_assets:
            asset_type = asset.type
            if asset_type not in metadata["extraction_summary"]["asset_types"]:
                metadata["extraction_summary"]["asset_types"][asset_type] = 0
            metadata["extraction_summary"]["asset_types"][asset_type] += 1
            
            # Add asset info
            metadata["assets"].append({
                "type": asset.type,
                "offset": f"0x{asset.offset:08X}",
                "size": asset.size,
                "output": asset.output_path,
                "metadata": asset.metadata
            })
        
        # Save metadata
        metadata_path = os.path.join(self.output_dir, "extraction_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Also save a summary text file
        summary_path = os.path.join(self.output_dir, "extraction_summary.txt")
        with open(summary_path, "w") as f:
            f.write("SM64 ROM Extraction Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"ROM CRC32: {metadata['rom_crc32']}\n")
            f.write(f"ROM Size: {human_readable_size(metadata['rom_size'])}\n")
            f.write(f"Total Assets Extracted: {metadata['extraction_summary']['total_assets']}\n\n")
            f.write("Asset Type Breakdown:\n")
            for asset_type, count in metadata["extraction_summary"]["asset_types"].items():
                f.write(f"  - {asset_type}: {count}\n")


# ===========================
# GUI Implementation
# ===========================

class SM64ExtractorGUI:
    """Enhanced GUI for SM64 asset extraction."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Super Mario 64 Advanced Extractor v3.0")
        self.root.geometry("900x700")
        
        # State
        self.rom_path = None
        self.rom_info = None
        self.rom_data = None
        self.extracted_assets = []
        
        # Build UI
        self._build_ui()
        
        # Start log polling
        self.root.after(100, self._poll_log)
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Super Mario 64 Advanced Asset Extractor", 
                         font=("Arial", 14, "bold"))
        title.pack(pady=(0, 10))
        
        # ROM info frame
        info_frame = ttk.LabelFrame(main_frame, text="ROM Information", padding=10)
        info_frame.pack(fill="x", pady=5)
        
        self.info_label = ttk.Label(info_frame, text="No ROM loaded")
        self.info_label.pack(anchor="w")
        
        # Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.btn_select = ttk.Button(btn_frame, text="Select ROM", 
                                     command=self.select_rom, width=15)
        self.btn_select.pack(side="left", padx=2)
        
        self.btn_extract_all = ttk.Button(btn_frame, text="Extract All Assets", 
                                          command=self.extract_all, 
                                          state="disabled", width=15)
        self.btn_extract_all.pack(side="left", padx=2)
        
        self.btn_extract_selected = ttk.Button(btn_frame, text="Custom Extract", 
                                               command=self.custom_extract, 
                                               state="disabled", width=15)
        self.btn_extract_selected.pack(side="left", padx=2)
        
        self.btn_export_log = ttk.Button(btn_frame, text="Export Log", 
                                         command=self.export_log, width=15)
        self.btn_export_log.pack(side="right", padx=2)
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Status: Ready")
        self.status_label.pack(anchor="w")
        
        self.progress = ttk.Progressbar(progress_frame, mode="determinate", 
                                        maximum=100)
        self.progress.pack(fill="x", pady=2)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Extraction Options", padding=10)
        options_frame.pack(fill="x", pady=5)
        
        self.extract_mio0_var = tk.BooleanVar(value=True)
        self.extract_textures_var = tk.BooleanVar(value=True)
        self.extract_audio_var = tk.BooleanVar(value=True)
        self.extract_levels_var = tk.BooleanVar(value=True)
        self.extract_models_var = tk.BooleanVar(value=True)
        self.convert_textures_var = tk.BooleanVar(value=PIL_AVAILABLE)
        
        ttk.Checkbutton(options_frame, text="Extract MIO0 compressed data", 
                       variable=self.extract_mio0_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(options_frame, text="Extract textures", 
                       variable=self.extract_textures_var).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(options_frame, text="Extract audio", 
                       variable=self.extract_audio_var).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(options_frame, text="Extract levels", 
                       variable=self.extract_levels_var).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(options_frame, text="Extract models", 
                       variable=self.extract_models_var).grid(row=2, column=0, sticky="w")
        
        convert_cb = ttk.Checkbutton(options_frame, text="Convert textures to PNG", 
                                     variable=self.convert_textures_var)
        convert_cb.grid(row=2, column=1, sticky="w")
        if not PIL_AVAILABLE:
            convert_cb.config(state="disabled")
            ttk.Label(options_frame, text="(PIL not installed)", 
                     foreground="gray").grid(row=3, column=1, sticky="w")
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Extraction Log", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(text_frame, height=15, width=80, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Logger
        self.log_queue = queue.Queue()
        self.log("Super Mario 64 Advanced Asset Extractor initialized")
        self.log("=" * 60)
        if not PIL_AVAILABLE:
            self.log("Note: PIL not installed - texture conversion disabled")
    
    def log(self, message: str):
        """Add message to log queue."""
        self.log_queue.put(message)
    
    def _poll_log(self):
        """Poll log queue and update text widget."""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_log)
    
    def select_rom(self):
        """Select and load ROM file."""
        file_path = filedialog.askopenfilename(
            title="Select SM64 ROM",
            filetypes=[
                ("N64 ROMs", "*.z64 *.v64 *.n64"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            self.rom_info, self.rom_data = read_rom(file_path)
            self.rom_path = file_path
            
            # Update UI
            info_text = (
                f"File: {os.path.basename(file_path)}\n"
                f"Size: {human_readable_size(self.rom_info.size)}\n"
                f"Format: {self.rom_info.layout.upper()}\n"
                f"CRC32: {self.rom_info.crc32}\n"
                f"Game: {self.rom_info.name}\n"
                f"ID: {self.rom_info.game_id} v{self.rom_info.version}"
            )
            self.info_label.config(text=info_text)
            
            # Enable extraction buttons
            self.btn_extract_all.config(state="normal")
            self.btn_extract_selected.config(state="normal")
            
            self.log(f"\nROM loaded successfully: {os.path.basename(file_path)}")
            self.log(f"CRC32: {self.rom_info.crc32}")
            self.update_status("ROM loaded - ready to extract")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ROM:\n{str(e)}")
            self.log(f"Error loading ROM: {str(e)}")
    
    def extract_all(self):
        """Extract all assets from ROM."""
        if not self.rom_data:
            messagebox.showerror("Error", "No ROM loaded")
            return
        
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
        
        # Run extraction in thread
        def extract_thread():
            try:
                self.log(f"\nStarting extraction to: {output_dir}")
                self.log("-" * 60)
                
                extractor = AssetExtractor(self.rom_data, output_dir)
                
                def progress_callback(current, total, message):
                    percent = int((current / total) * 100)
                    self.root.after(0, lambda: self.update_progress(percent, message))
                    self.log(f"[{current}/{total}] {message}")
                
                assets = extractor.extract_all(progress_callback)
                
                self.extracted_assets = assets
                
                # Summary
                self.log("-" * 60)
                self.log(f"Extraction complete!")
                self.log(f"Total assets extracted: {len(assets)}")
                
                # Count by type
                type_counts = {}
                for asset in assets:
                    if asset.type not in type_counts:
                        type_counts[asset.type] = 0
                    type_counts[asset.type] += 1
                
                self.log("\nAsset breakdown:")
                for asset_type, count in type_counts.items():
                    self.log(f"  {asset_type}: {count}")
                
                self.log(f"\nFiles saved to: {output_dir}")
                self.update_status("Extraction complete!")
                
                messagebox.showinfo("Success", 
                                   f"Extraction complete!\n\n"
                                   f"Extracted {len(assets)} assets\n"
                                   f"Output: {output_dir}")
                
            except Exception as e:
                self.log(f"Error during extraction: {str(e)}")
                messagebox.showerror("Extraction Error", str(e))
            finally:
                self.root.after(0, lambda: self.enable_controls(True))
        
        self.enable_controls(False)
        thread = threading.Thread(target=extract_thread, daemon=True)
        thread.start()
    
    def custom_extract(self):
        """Show custom extraction dialog."""
        messagebox.showinfo("Custom Extract", 
                           "Custom extraction allows you to:\n"
                           "• Select specific asset types\n"
                           "• Define custom offsets\n"
                           "• Extract from specific segments\n\n"
                           "This feature is coming soon!")
    
    def export_log(self):
        """Export log to file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                content = self.log_text.get("1.0", "end-1c")
                with open(file_path, "w") as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Log saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log:\n{str(e)}")
    
    def update_status(self, message: str):
        """Update status label."""
        self.status_label.config(text=f"Status: {message}")
    
    def update_progress(self, percent: int, message: str = ""):
        """Update progress bar."""
        self.progress["value"] = percent
        if message:
            self.update_status(message)
    
    def enable_controls(self, enabled: bool):
        """Enable/disable controls during extraction."""
        state = "normal" if enabled else "disabled"
        self.btn_select.config(state=state)
        self.btn_extract_all.config(state=state if self.rom_data else "disabled")
        self.btn_extract_selected.config(state=state if self.rom_data else "disabled")


# ===========================
# CLI Implementation
# ===========================

def run_cli(args: argparse.Namespace) -> int:
    """Run the tool in CLI mode."""
    if not args.rom:
        print("Error: --rom is required", file=sys.stderr)
        return 1
    
    try:
        # Load ROM
        print(f"Loading ROM: {args.rom}")
        rom_info, rom_data = read_rom(args.rom)
        
        print(f"  Size: {human_readable_size(rom_info.size)}")
        print(f"  Format: {rom_info.layout.upper()}")
        print(f"  CRC32: {rom_info.crc32}")
        print(f"  Game: {rom_info.name}")
        print(f"  ID: {rom_info.game_id} v{rom_info.version}")
        
        # Create output directory
        ensure_directory(args.output)
        
        # Extract assets
        print(f"\nExtracting assets to: {args.output}")
        print("-" * 50)
        
        extractor = AssetExtractor(rom_data, args.output)
        
        def progress_callback(current, total, message):
            print(f"[{current}/{total}] {message}")
        
        assets = extractor.extract_all(progress_callback)
        
        # Summary
        print("-" * 50)
        print(f"\nExtraction complete!")
        print(f"Total assets extracted: {len(assets)}")
        
        # Count by type
        type_counts = {}
        for asset in assets:
            if asset.type not in type_counts:
                type_counts[asset.type] = 0
            type_counts[asset.type] += 1
        
        print("\nAsset breakdown:")
        for asset_type, count in type_counts.items():
            print(f"  {asset_type}: {count}")
        
        print(f"\nFiles saved to: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1


def build_argument_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Super Mario 64 Advanced Asset Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all assets
  %(prog)s --rom sm64.z64 --output extracted_assets
  
  # Launch GUI
  %(prog)s --gui

This tool extracts and converts all detectable assets from SM64 ROMs,
including MIO0 compressed data, textures, audio, levels, and models.
        """
    )
    
    parser.add_argument("--rom", help="Path to SM64 ROM file")
    parser.add_argument("--output", "-o", default="sm64_extracted",
                       help="Output directory (default: sm64_extracted)")
    parser.add_argument("--gui", action="store_true", help="Launch GUI")
    parser.add_argument("--version", action="version", version="%(prog)s 3.0.0")
    
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    
    # Launch GUI or CLI
    if args.gui or (not args.rom and TK_AVAILABLE):
        if not TK_AVAILABLE:
            print("Error: Tkinter not available. Use CLI mode.", file=sys.stderr)
            return 1
        
        try:
            root = tk.Tk()
            app = SM64ExtractorGUI(root)
            root.mainloop()
            return 0
        except Exception as e:
            print(f"GUI Error: {str(e)}", file=sys.stderr)
            return 1
    else:
        return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
