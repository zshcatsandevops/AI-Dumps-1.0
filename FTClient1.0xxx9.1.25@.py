import os
import sys
import json
import shutil
import zipfile
import tarfile
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import urllib.request
import re
import subprocess
import hashlib
import platform
import threading
import uuid

# --- Constants ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

# Directory Setup
if platform.system() == "Windows":
    APPDATA = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
    BASE_DIR = os.path.join(APPDATA, '.ftlauncher')
else:
    BASE_DIR = os.path.join(os.path.expanduser('~'), '.ftlauncher')

MINECRAFT_DIR = os.path.join(BASE_DIR, 'minecraft')
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, 'versions')
JAVA_DIR = os.path.join(BASE_DIR, 'java')
LIBRARIES_DIR = os.path.join(MINECRAFT_DIR, 'libraries')
ASSETS_DIR = os.path.join(MINECRAFT_DIR, 'assets')

for dir_path in [MINECRAFT_DIR, VERSIONS_DIR, JAVA_DIR, LIBRARIES_DIR, ASSETS_DIR,
                 os.path.join(ASSETS_DIR, 'indexes'), os.path.join(ASSETS_DIR, 'objects')]:
    os.makedirs(dir_path, exist_ok=True)

# Windows XP Theme
THEME = {
    "bg": "#ece9d8",
    "sidebar": "#d4d0c8",
    "accent": "#0a246a",
    "text": "#000000",
    "text_secondary": "#5a5a5a",
    "input_bg": "#ffffff",
    "button": "#d4d0c8",
    "button_hover": "#c0bcaa"
}

class ScrollableFrame(tk.Frame):
    """A scrollable frame widget"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        # Configure scroll region
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

class FTLauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FTLauncher")
        self.geometry("800x500")
        self.minsize(600, 400)  # Set minimum window size
        self.configure(bg=THEME['bg'])

        # Data Initialization
        self.versions = {}
        self.version_categories = {
            "Latest Release": [], "Latest Snapshot": [], "Release": [],
            "Snapshot": [], "Old Beta": [], "Old Alpha": []
        }
        self.ai_mode = tk.BooleanVar(value=False)

        # Style Configuration
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TCombobox", fieldbackground=THEME['input_bg'], background=THEME['input_bg'],
                             foreground=THEME['text'], arrowcolor=THEME['text'], selectbackground=THEME['accent'],
                             selectforeground=THEME['text'], bordercolor=THEME['sidebar'], darkcolor=THEME['sidebar'],
                             lightcolor=THEME['sidebar'], arrowsize=15)

        self.init_ui()
        threading.Thread(target=self.load_version_manifest, daemon=True).start()

    def init_ui(self):
        # Main container with proper weight distribution
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_container = tk.Frame(self, bg=THEME['bg'])
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid weights for proper resizing
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = tk.Frame(main_container, bg=THEME['sidebar'], width=250)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar.grid_propagate(False)  # Keep fixed width

        # Content Area
        content_area = tk.Frame(main_container, bg=THEME['bg'])
        content_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Configure sidebar weights
        sidebar.grid_rowconfigure(5, weight=1)  # Allow buttons to stay at top

        # Logo and Title
        logo_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        logo_frame.grid(row=0, column=0, sticky="ew", pady=(10, 20))
        tk.Label(logo_frame, text="📶 FTLauncher", font=("Arial", 22, "bold"), bg=THEME['sidebar'], fg=THEME['accent']).pack(anchor="center")
        tk.Label(logo_frame, text="Minecraft Launcher", font=("Arial", 16, "bold"), bg=THEME['sidebar'], fg=THEME['text']).pack(anchor="center", pady=(0, 10))

        # Version Selection
        version_frame = tk.LabelFrame(sidebar, text="GAME VERSION", bg=THEME['sidebar'], fg=THEME['text_secondary'],
                                      font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        version_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        tk.Label(version_frame, text="Category", font=("Arial", 8, "bold"), bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.category_combo = ttk.Combobox(version_frame, values=list(self.version_categories.keys()), state="readonly", font=("Arial", 10))
        self.category_combo.pack(fill="x", padx=5, pady=(0, 5))
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)
        tk.Label(version_frame, text="Version", font=("Arial", 8, "bold"), bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.version_combo = ttk.Combobox(version_frame, state="readonly", font=("Arial", 10))
        self.version_combo.pack(fill="x", padx=5, pady=(0, 5))

        # Settings
        settings_frame = tk.LabelFrame(sidebar, text="SETTINGS", bg=THEME['sidebar'], fg=THEME['text_secondary'],
                                       font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        settings_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Username Field Only (Offline Mode)
        auth_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        auth_frame.pack(fill="x", padx=5, pady=(5, 5))
        tk.Label(auth_frame, text="USERNAME", font=("Arial", 8, "bold"), bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w")
        self.username_input = tk.Entry(auth_frame, font=("Arial", 10), bg=THEME['input_bg'], fg=THEME['text'],
                                       insertbackground=THEME['text'], bd=1, highlightthickness=1)
        self.username_input.pack(fill="x", pady=(3, 0))
        self.username_input.insert(0, "Player")

        # RAM
        ram_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ram_frame.pack(fill="x", padx=5, pady=(5, 5))
        ram_label_frame = tk.Frame(ram_frame, bg=THEME['sidebar'])
        ram_label_frame.pack(fill="x")
        tk.Label(ram_label_frame, text="RAM ALLOCATION", font=("Arial", 8, "bold"), bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")
        self.ram_value_label = tk.Label(ram_label_frame, text="4 GB", font=("Arial", 8), bg=THEME['sidebar'], fg=THEME['text'])
        self.ram_value_label.pack(side="right")
        self.ram_scale = tk.Scale(ram_frame, from_=1, to=16, orient="horizontal", bg=THEME['sidebar'], fg=THEME['text'],
                                  activebackground=THEME['accent'], highlightthickness=0, bd=1, troughcolor=THEME['input_bg'],
                                  sliderrelief='raised', command=lambda v: self.ram_value_label.config(text=f"{int(float(v))} GB"))
        self.ram_scale.set(4)
        self.ram_scale.pack(fill="x", pady=(3,0))

        # AI Mode
        ai_mode_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ai_mode_frame.pack(fill="x", padx=5, pady=(5, 5))
        tk.Label(ai_mode_frame, text="AI MODE", font=("Arial", 8, "bold"), bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")
        tk.Checkbutton(ai_mode_frame, variable=self.ai_mode, bg=THEME['sidebar'], fg=THEME['text'], selectcolor=THEME['sidebar'],
                       activebackground=THEME['sidebar'], activeforeground=THEME['text'], bd=1, highlightthickness=0, relief='sunken').pack(side="right")

        # Buttons
        button_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(10, 0))
        def on_enter(e): e.widget.configure(bg=THEME['button_hover'])
        def on_leave(e): e.widget.configure(bg=THEME['accent'] if e.widget['text'] == "PLAY" else THEME['button'])
        skin_button = tk.Button(button_frame, text="CHANGE SKIN", font=("Arial", 10, "bold"), bg=THEME['button'], fg=THEME['text'],
                                bd=1, padx=10, pady=8, relief='raised', command=self.select_skin)
        skin_button.pack(fill="x", pady=(0, 5))
        skin_button.bind("<Enter>", on_enter)
        skin_button.bind("<Leave>", on_leave)
        self.launch_button = tk.Button(button_frame, text="PLAY", font=("Arial", 12, "bold"), bg=THEME['accent'], fg=THEME['text'],
                                       bd=1, padx=10, pady=10, relief='raised', command=self.prepare_and_launch)
        self.launch_button.pack(fill="x")
        self.launch_button.bind("<Enter>", on_enter)
        self.launch_button.bind("<Leave>", on_leave)

        # Add empty space at bottom to push content up
        tk.Frame(sidebar, bg=THEME['sidebar'], height=10).grid(row=4, column=0)

        # Content Area Configuration
        content_area.grid_columnconfigure(0, weight=1)
        content_area.grid_rowconfigure(1, weight=1)  # Allow changelog to expand
        
        tk.Label(content_area, text="RECENT CHANGES", font=("Arial", 14, "bold"), bg=THEME['bg'], fg=THEME['text']).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Create scrollable frame for changelog
        scroll_frame = ScrollableFrame(content_area, bg=THEME['bg'])
        scroll_frame.grid(row=1, column=0, sticky="nsew")
        
        changelog_items = [
            "📶 Updated to FTLauncher with WiFi logo",
            "🏠 Offline mode only",
            "🎨 Windows XP style theme",
            "⚙️ Enhanced performance options",
            "🖥️ Improved window sizing and responsiveness",
            "📱 Better layout management for different screen sizes",
            "🔧 Fixed various UI scaling issues"
        ]
        
        for i, item in enumerate(changelog_items):
            item_bg = THEME['sidebar'] if i % 2 == 0 else THEME['input_bg']
            item_frame = tk.Frame(scroll_frame.scrollable_frame, bg=item_bg, padx=10, pady=8)
            item_frame.pack(fill="x", pady=(0, 5))
            tk.Label(item_frame, text=item, font=("Arial", 10), bg=item_bg, fg=THEME['text'], 
                     justify="left", anchor="w", wraplength=400).pack(fill='x')

    def update_version_list(self, event=None):
        category = self.category_combo.get()
        versions = self.version_categories.get(category, [])
        self.version_combo['values'] = versions
        if versions:
            self.version_combo.current(0)
        else:
            self.version_combo.set('')

    def load_version_manifest(self):
        print("Loading version manifest...")
        try:
            req = urllib.request.Request(VERSION_MANIFEST_URL, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req) as url:
                manifest = json.loads(url.read().decode())
                self.versions = {v["id"]: v["url"] for v in manifest["versions"]}
                for category in self.version_categories:
                    self.version_categories[category] = []
                latest_release_id = manifest["latest"]["release"]
                latest_snapshot_id = manifest["latest"]["snapshot"]
                for v in manifest["versions"]:
                    if v["id"] == latest_release_id:
                        self.version_categories["Latest Release"].append(v["id"])
                    elif v["id"] == latest_snapshot_id:
                        self.version_categories["Latest Snapshot"].append(v["id"])
                    elif v["type"] == "release":
                        self.version_categories["Release"].append(v["id"])
                    elif v["type"] == "snapshot":
                        self.version_categories["Snapshot"].append(v["id"])
                    elif v["type"] == "old_beta":
                        self.version_categories["Old Beta"].append(v["id"])
                    elif v["type"] == "old_alpha":
                        self.version_categories["Old Alpha"].append(v["id"])
                for category in self.version_categories:
                    if category not in ["Latest Release", "Latest Snapshot"]:
                        self.version_categories[category].sort(reverse=True)
                self.update_version_list()
                print("Version manifest loaded successfully.")
        except Exception as e:
            print(f"Error loading version manifest: {e}")
            self.after(0, lambda: messagebox.showerror("Error", "Failed to load version manifest."))

    def is_java_installed(self, required_version="21"):
        local_java_path = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(local_java_path):
            try:
                result = subprocess.run([local_java_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', result.stderr)
                if match and int(match.group(1)) >= int(required_version):
                    print(f"Found local Java version: {match.group(1)}")
                    return local_java_path
            except Exception:
                pass
        try:
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', result.stderr)
            if match and int(match.group(1)) >= int(required_version):
                print(f"Found system Java version: {match.group(1)}")
                return "java"
            return None
        except Exception:
            print("Java not found.")
            return None

    def install_java_if_needed(self):
        java_path = self.is_java_installed()
        if java_path:
            print("Java 21+ already installed.")
            return java_path
        print("Installing OpenJDK 21 locally...")
        system, arch = platform.system(), platform.architecture()[0]
        java_url = {
            ("Windows", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_windows_hotspot_21.0.5_11.zip", ".zip"),
            ("Linux", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_linux_hotspot_21.0.5_11.tar.gz", ".tar.gz"),
            ("Darwin", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_mac_hotspot_21.0.5_11.tar.gz", ".tar.gz")
        }.get((system, arch))
        if not java_url:
            messagebox.showerror("Error", f"Unsupported OS ({system}) or architecture ({arch}). Install OpenJDK 21 manually.")
            return None
        url, ext = java_url
        archive_path = os.path.join(JAVA_DIR, f"openjdk{ext}")
        extracted_folder = os.path.join(JAVA_DIR, "jdk-21.0.5+11")
        if os.path.exists(extracted_folder):
            print("Local OpenJDK 21 already exists.")
            return os.path.join(extracted_folder, "bin", "java.exe" if system == "Windows" else "java")
        try:
            print(f"Downloading Java from: {url}")
            urllib.request.urlretrieve(url, archive_path)
            print("Extracting...")
            if ext == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(JAVA_DIR)
            else:
                with tarfile.open(archive_path, "r:gz") as tar_ref:
                    tar_ref.extractall(JAVA_DIR)
            os.remove(archive_path)
            print("Java 21 installed locally.")
            return os.path.join(extracted_folder, "bin", "java.exe" if system == "Windows" else "java")
        except Exception as e:
            print(f"Failed to install Java: {e}")
            messagebox.showerror("Error", f"Failed to install Java 21: {e}")
            return None

    def select_skin(self):
        file_path = filedialog.askopenfilename(title="Select Skin File", filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")])
        if file_path:
            skin_dest_dir = os.path.join(MINECRAFT_DIR, "skins")
            os.makedirs(skin_dest_dir, exist_ok=True)
            dest_path = os.path.join(skin_dest_dir, "custom_skin.png")
            try:
                shutil.copy2(file_path, dest_path)
                print(f"Skin applied: {dest_path}")
                messagebox.showinfo("Skin Applied", "Skin applied successfully!")
            except Exception as e:
                print(f"Failed to apply skin: {e}")
                messagebox.showerror("Error", f"Failed to apply skin: {e}")

    @staticmethod
    def verify_file(file_path, expected_sha1):
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha1()
                while chunk := f.read(4096):
                    file_hash.update(chunk)
            return file_hash.hexdigest() == expected_sha1
        except Exception as e:
            print(f"Error verifying file {file_path}: {e}")
            return False

    def download_file(self, url, dest_path, description="file"):
        print(f"Downloading {description}: {os.path.basename(dest_path)} from {url}")
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            print(f"Finished downloading {os.path.basename(dest_path)}")
        except Exception as e:
            print(f"Failed to download {description}: {e}")
            raise

    def download_version_files(self, version_id, version_url):
        print(f"⬇️ Downloading files for {version_id}...")
        version_dir = os.path.join(VERSIONS_DIR, version_id)
        os.makedirs(version_dir, exist_ok=True)
        version_json_path = os.path.join(version_dir, f"{version_id}.json")
        if not os.path.exists(version_json_path):
            self.download_file(version_url, version_json_path, f"version JSON ({version_id})")
        with open(version_json_path, "r") as f:
            version_data = json.load(f)

        jar_info = version_data.get("downloads", {}).get("client")
        if jar_info:
            jar_path = os.path.join(version_dir, f"{version_id}.jar")
            if not os.path.exists(jar_path) or not self.verify_file(jar_path, jar_info["sha1"]):
                self.download_file(jar_info["url"], jar_path, f"client JAR ({version_id})")
                if not self.verify_file(jar_path, jar_info["sha1"]):
                    os.remove(jar_path)
                    print("Checksum mismatch for JAR.")
                    return False

        natives_dir = os.path.join(version_dir, "natives")
        os.makedirs(natives_dir, exist_ok=True)
        current_os = "osx" if platform.system() == "Darwin" else platform.system().lower()
        for lib in version_data.get("libraries", []):
            if self.is_library_allowed(lib, current_os):
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    artifact = lib["downloads"]["artifact"]
                    lib_path = os.path.join(LIBRARIES_DIR, artifact["path"])
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    if not os.path.exists(lib_path) or not self.verify_file(lib_path, artifact["sha1"]):
                        self.download_file(artifact["url"], lib_path, f"library ({os.path.basename(lib_path)})")
                        if not self.verify_file(lib_path, artifact["sha1"]):
                            os.remove(lib_path)
                            print(f"Checksum mismatch for library: {lib.get('name')}")
                if "natives" in lib and current_os in lib["natives"]:
                    classifier = lib["natives"][current_os].replace("${arch}", platform.architecture()[0].replace('bit', ''))
                    if "downloads" in lib and classifier in lib["downloads"]["classifiers"]:
                        native = lib["downloads"]["classifiers"][classifier]
                        native_path = os.path.join(natives_dir, f"{lib['name'].split(':')[-1]}-{classifier}.jar")
                        if not os.path.exists(native_path) or not self.verify_file(native_path, native["sha1"]):
                            self.download_file(native["url"], native_path, f"native ({os.path.basename(native_path)})")
                            if self.verify_file(native_path, native["sha1"]):
                                with zipfile.ZipFile(native_path, "r") as zip_ref:
                                    zip_ref.extractall(natives_dir)
                            else:
                                os.remove(native_path)
                                print(f"Checksum mismatch for native: {lib.get('name')}")

        asset_index_info = version_data.get("assetIndex")
        if asset_index_info:
            idx_id = asset_index_info["id"]
            idx_path = os.path.join(ASSETS_DIR, "indexes", f"{idx_id}.json")
            if not os.path.exists(idx_path):
                self.download_file(asset_index_info["url"], idx_path, f"asset index ({idx_id})")
            with open(idx_path, "r") as f:
                idx_data = json.load(f)
            for asset_name, info in idx_data.get("objects", {}).items():
                if hash_val := info.get("hash"):
                    subdir = hash_val[:2]
                    asset_path = os.path.join(ASSETS_DIR, "objects", subdir, hash_val)
                    if not os.path.exists(asset_path):
                        self.download_file(f"http://resources.download.minecraft.net/{subdir}/{hash_val}", asset_path, f"asset ({hash_val[:8]})")
        print("✅ Files downloaded!")
        return True

    def modify_options_txt(self, target_fps=60, ai_mode=False):
        options_path = os.path.join(MINECRAFT_DIR, "options.txt")
        options = {}
        if os.path.exists(options_path):
            with open(options_path, "r") as f:
                for line in f:
                    parts = line.strip().split(":", 1)
                    if len(parts) == 2:
                        options[parts[0]] = parts[1]
        options['maxFps'] = str(target_fps)
        options['enableVsync'] = 'false'
        if ai_mode:
            options.update({
                'renderDistance': '8', 'particles': 'minimal', 'graphics': 'fast',
                'smoothLighting': 'false', 'clouds': 'false', 'fancyGrass': 'false', 'useVbo': 'true'
            })
        with open(options_path, "w") as f:
            for key, value in options.items():
                f.write(f"{key}:{value}\n")
        print(f"⚙️ Updated options.txt with {'AI mode' if ai_mode else 'standard'} settings.")

    def is_library_allowed(self, lib, current_os):
        if "rules" not in lib:
            return True
        allow = False
        for rule in lib["rules"]:
            action = rule.get("action")
            os_info = rule.get("os")
            if "features" in rule:
                continue
            os_match = os_info is None or (isinstance(os_info, dict) and os_info.get("name") == current_os)
            if os_match:
                if action == "allow":
                    allow = True
                elif action == "disallow":
                    return False
        return allow

    def evaluate_rules(self, rules, current_os):
        if not rules:
            return True
        allow = False
        for rule in rules:
            action = rule.get("action")
            os_info = rule.get("os")
            if "features" in rule:
                continue
            os_match = os_info is None or (isinstance(os_info, dict) and os_info.get("name") == current_os)
            if os_match:
                if action == "allow":
                    allow = True
                elif action == "disallow":
                    return False
        return allow

    def build_launch_command(self, version, username, ram, java_path, ai_mode=False):
        version_dir = os.path.join(VERSIONS_DIR, version)
        json_path = os.path.join(version_dir, f"{version}.json")
        if not os.path.exists(json_path):
            print("Version JSON missing.")
            return []
        with open(json_path, "r") as f:
            version_data = json.load(f)

        current_os = "osx" if platform.system() == "Darwin" else platform.system().lower()
        main_class = version_data.get("mainClass", "")
        if not main_class:
            print("Main class not found.")
            return []

        # Generate offline UUID and access token
        offline_uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, username)).replace("-", "")
        offline_token = "offline_token_" + str(uuid.uuid4())

        natives_dir = os.path.join(version_dir, "natives")
        classpath = [os.path.join(version_dir, f"{version}.jar")]
        for lib in version_data.get("libraries", []):
            if self.is_library_allowed(lib, current_os) and "downloads" in lib and "artifact" in lib["downloads"]:
                lib_path = os.path.join(LIBRARIES_DIR, lib["downloads"]["artifact"]["path"])
                if os.path.exists(lib_path):
                    classpath.append(lib_path)

        command = [java_path, f"-Xmx{ram}G", f"-Djava.library.path={natives_dir}"]
        jvm_args = []
        if "arguments" in version_data and "jvm" in version_data["arguments"]:
            for arg in version_data["arguments"]["jvm"]:
                if isinstance(arg, str):
                    jvm_args.append(arg)
                elif isinstance(arg, dict) and self.evaluate_rules(arg.get("rules", []), current_os):
                    jvm_args.extend(arg["value"] if isinstance(arg["value"], list) else [arg["value"]])
        else:
            jvm_args = ["-XX:+UseG1GC", "-XX:-UseAdaptiveSizePolicy"]

        if platform.system() == "Darwin":
            if "-XstartOnFirstThread" not in jvm_args:
                jvm_args.append("-XstartOnFirstThread")
            if "-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true" not in jvm_args:
                jvm_args.append("-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true")

        if ai_mode:
            command.extend(["-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:+UnlockExperimentalVMOptions",
                            "-XX:G1NewSizePercent=20", "-XX:G1ReservePercent=20", "-XX:G1HeapRegionSize=32M"])

        command.extend(jvm_args)
        command.extend(["-cp", os.pathsep.join(classpath), main_class])
        game_args = []
        if "arguments" in version_data and "game" in version_data["arguments"]:
            for arg in version_data["arguments"]["game"]:
                if isinstance(arg, str):
                    game_args.append(arg)
                elif isinstance(arg, dict) and self.evaluate_rules(arg.get("rules", []), current_os):
                    game_args.extend(arg["value"] if isinstance(arg["value"], list) else [arg["value"]])
        elif "minecraftArguments" in version_data:
            game_args = version_data["minecraftArguments"].split()

        # Offline mode replacements
        replacements = {
            "${auth_player_name}": username, 
            "${version_name}": version, 
            "${game_directory}": MINECRAFT_DIR,
            "${assets_root}": ASSETS_DIR, 
            "${assets_index_name}": version_data.get("assetIndex", {}).get("id", version),
            "${auth_uuid}": offline_uuid, 
            "${auth_access_token}": offline_token, 
            "${user_type}": "legacy",
            "${version_type}": version_data.get("type", "release"), 
            "${user_properties}": "{}",
            "${quickPlayRealms}": "", 
            "${quickPlaySingleplayer}": "", 
            "${quickPlayMultiplayer}": ""
        }
        
        final_game_args = [arg.replace(key, str(value)) for arg in game_args for key, value in replacements.items() if key in arg]
        command.extend(final_game_args)
        return command

    def prepare_and_launch(self):
        selected_version = self.version_combo.get()
        if not selected_version:
            messagebox.showerror("Error", "Please select a version.")
            return
        username = self.username_input.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return

        self.launch_button.config(text="LAUNCHING...", state="disabled")
        
        def launch_thread():
            java_path = self.install_java_if_needed()
            if not java_path or not self.download_version_files(selected_version, self.versions.get(selected_version)):
                self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))
                return
            self.modify_options_txt(target_fps=60, ai_mode=self.ai_mode.get())
            ram = int(self.ram_scale.get())
            cmd = self.build_launch_command(selected_version, username, ram, java_path, ai_mode=self.ai_mode.get())
            if cmd:
                try:
                    subprocess.Popen(cmd, cwd=MINECRAFT_DIR)
                    print("Minecraft launched in offline mode.")
                except Exception as e:
                    print(f"Launch failed: {e}")
                    self.after(0, lambda: messagebox.showerror("Error", f"Launch failed: {e}"))
            self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))

        threading.Thread(target=launch_thread, daemon=True).start()

if __name__ == "__main__":
    app = FTLauncherApp()
    app.mainloop()
