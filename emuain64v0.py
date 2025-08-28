import sys
import os
import ctypes
from ctypes import c_char_p, c_int, c_void_p
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget, QMenuBar, QMenu, QStatusBar, QListWidget
from PyQt6.QtCore import Qt

# Load Mupen64Plus core library
if sys.platform.startswith('win'):
    mupen = ctypes.WinDLL('libmupen64plus.dll')
else:
    mupen = ctypes.CDLL('libmupen64plus.so')

# Define Mupen64Plus API functions
mupen.CoreStartup.argtypes = [c_int, c_char_p, c_char_p, c_void_p, c_void_p, c_void_p, c_void_p]
mupen.CoreStartup.restype = c_int
mupen.CoreDoCommand.argtypes = [c_int, c_int, c_void_p]
mupen.CoreDoCommand.restype = c_int
mupen.CoreShutdown.restype = c_int

M64P_CORE_API_VERSION = 0x020000
M64CMD_ROM_OPEN = 0
M64CMD_EXECUTE = 2

class EmuAI64Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EmuAI64 1.0x")
        self.setGeometry(100, 100, 800, 600)

        # Create menu bar (Project64 1.6 style)
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = file_menu.addAction("Open ROM")
        open_action.triggered.connect(self.open_rom)
        file_menu.addAction("Exit", self.close)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Configure Plugins")
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About")

        # Create ROM browser
        self.rom_list = QListWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.rom_list)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

        # Emulator state
        self.rom_path = None

    def open_rom(self):
        rom_path, _ = QFileDialog.getOpenFileName(self, "Open N64 ROM", "", "N64 ROMs (*.z64 *.n64)")
        if rom_path:
            self.rom_path = rom_path
            self.rom_list.addItem(os.path.basename(rom_path))
            self.statusbar.showMessage(f"Loaded: {rom_path}")
            self.run_emulator()

    def run_emulator(self):
        if not self.rom_path:
            return

        # Initialize Mupen64Plus core
        core_dir = os.path.abspath(".").encode('utf-8')
        app_name = "EmuAI64".encode('utf-8')
        if mupen.CoreStartup(M64P_CORE_API_VERSION, core_dir, app_name, None, None, None, None) != 0:
            self.statusbar.showMessage("Core startup failed")
            return

        # Disable file outputs (saves, logs)
        mupen.CoreDoCommand(1, 0, None)  # Set config to disable saves
        config = ctypes.c_void_p()
        mupen.CoreDoCommand(3, 0, ctypes.byref(config))  # Get config handle
        mupen.ConfigSetParameter(config, "SaveSRAM".encode('utf-8'), 0, ctypes.c_int(0))
        mupen.ConfigSetParameter(config, "SaveState".encode('utf-8'), 0, ctypes.c_int(0))

        # Load ROM
        rom_path_b = self.rom_path.encode('utf-8')
        if mupen.CoreDoCommand(M64CMD_ROM_OPEN, len(rom_path_b), rom_path_b) != 0:
            self.statusbar.showMessage("Failed to load ROM")
            return

        # Start emulation
        mupen.CoreDoCommand(M64CMD_EXECUTE, 0, None)
        self.statusbar.showMessage("Emulation running")

def main():
    app = QApplication(sys.argv)
    window = EmuAI64Window()
    window.show()

    # Initialize emulator for testing
    if len(sys.argv) > 1:
        window.rom_path = sys.argv[1]
        window.run_emulator()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
