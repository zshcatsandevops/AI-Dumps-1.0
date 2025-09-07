import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import urllib.request
import json
import subprocess
import re
import platform
import os
import shutil
import hashlib
import zipfile
import tarfile
import sys
import threading

# --- Constants ---
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ELY_BY_AUTH_URL = "https://authserver.ely.by/auth/authenticate"

# Determine base directory for client data
if platform.system() == "Windows":
    APPDATA = os.environ.get('APPDATA', os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming'))
    BASE_DIR = os.path.join(APPDATA, '.cat-client')
else:
    BASE_DIR = os.path.join(os.path.expanduser('~'), '.cat-client')

MINECRAFT_DIR = os.path.join(BASE_DIR, 'minecraft')
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, 'versions')
JAVA_DIR = os.path.join(BASE_DIR, 'java')

os.makedirs(MINECRAFT_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(JAVA_DIR, exist_ok=True)

# --- Theme ---
THEME = {
    "bg": "#1c1c1c",
    "sidebar": "#2a2a2a",
    "accent": "#FFA500",  # Changed to orange for cat theme
    "text": "#f0f0f0",
    "text_secondary": "#aaaaaa",
    "input_bg": "#3a3a3a",
    "button": "#4a4a4a",
    "button_hover": "#5a5a5a"
}

class CatClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cat Client Launcher")
        self.geometry("600x400")
        self.configure(bg=THEME['bg'])
        try:
            # Try to set a simple icon - fixed to handle potential errors
            if platform.system() == "Windows":
                self.iconbitmap(default='')  # Use default empty icon on Windows
        except Exception as e:
            print(f"Note: Could not set icon: {e}")

        # Data initialization
        self.versions = {}
        self.version_categories = {
            "Latest Release": [],
            "Latest Snapshot": [],
            "Release": [],
            "Snapshot": [],
            "Old Beta": [],
            "Old Alpha": []
        }
        self.ai_mode = tk.BooleanVar(value=False)

        # Style configuration
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TCombobox",
                             fieldbackground=THEME['input_bg'],
                             background=THEME['input_bg'],
                             foreground=THEME['text'],
                             arrowcolor=THEME['text'],
                             selectbackground=THEME['accent'],
                             selectforeground=THEME['text'],
                             bordercolor=THEME['sidebar'],
                             darkcolor=THEME['sidebar'],
                             lightcolor=THEME['sidebar'],
                             arrowsize=15)

        self.init_ui()
        threading.Thread(target=self.load_version_manifest, daemon=True).start()

    def init_ui(self):
        main_container = tk.Frame(self, bg=THEME['bg'])
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Sidebar
        sidebar = tk.Frame(main_container, bg=THEME['sidebar'], width=250)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)

        # Logo and title
        logo_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        logo_frame.pack(fill="x", pady=(10, 20))
        
        # Cat paw + wifi + Minecraft logo using text symbols
        logo_text = "🐾 📶 ▣ CAT"
        logo = tk.Label(logo_frame, text=logo_text, font=("Consolas", 22, "bold"),
                        bg=THEME['sidebar'], fg=THEME['accent'])
        logo.pack(anchor="center")
        title = tk.Label(logo_frame, text="Cat Client", font=("Arial", 16, "bold"),
                         bg=THEME['sidebar'], fg=THEME['text'])
        title.pack(anchor="center", pady=(0, 10))

        # Version selection
        version_frame = tk.LabelFrame(sidebar, text="GAME VERSION", bg=THEME['sidebar'],
                                      fg=THEME['text_secondary'], font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        version_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(version_frame, text="Category", font=("Arial", 8, "bold"),
                 bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.category_combo = ttk.Combobox(version_frame, values=list(self.version_categories.keys()),
                                           state="readonly", font=("Arial", 10))
        self.category_combo.pack(fill="x", padx=5, pady=(0, 5))
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)
        tk.Label(version_frame, text="Version", font=("Arial", 8, "bold"),
                 bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w", padx=5, pady=(5,0))
        self.version_combo = ttk.Combobox(version_frame, state="readonly", font=("Arial", 10))
        self.version_combo.pack(fill="x", padx=5, pady=(0, 5))

        # Settings
        settings_frame = tk.LabelFrame(sidebar, text="SETTINGS", bg=THEME['sidebar'],
                                       fg=THEME['text_secondary'], font=("Arial", 9, "bold"), bd=0, labelanchor='nw')
        settings_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Username for offline
        self.username_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        self.username_frame.pack(fill="x", padx=5, pady=(5, 5))
        tk.Label(self.username_frame, text="USERNAME", font=("Arial", 8, "bold"),
                 bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w")
        self.username_input = tk.Entry(self.username_frame, font=("Arial", 10), bg=THEME['input_bg'],
                                       fg=THEME['text'], insertbackground=THEME['text'], bd=0, highlightthickness=0)
        self.username_input.pack(fill="x", pady=(3, 0))
        self.username_input.insert(0, "Enter Username")
        self.username_input.bind("<FocusIn>", self._clear_placeholder)
        self.username_input.bind("<FocusOut>", self._restore_placeholder)

        # RAM
        ram_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ram_frame.pack(fill="x", padx=5, pady=(5, 5))
        ram_label_frame = tk.Frame(ram_frame, bg=THEME['sidebar'])
        ram_label_frame.pack(fill="x")
        tk.Label(ram_label_frame, text="RAM ALLOCATION", font=("Arial", 8, "bold"),
                 bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")
        self.ram_value_label = tk.Label(ram_label_frame, text="4 GB", font=("Arial", 8),
                                        bg=THEME['sidebar'], fg=THEME['text'])
        self.ram_value_label.pack(side="right")
        self.ram_scale = tk.Scale(ram_frame, from_=1, to=16, orient="horizontal",
                                  bg=THEME['sidebar'], fg=THEME['text'], activebackground=THEME['accent'],
                                  highlightthickness=0, bd=0, troughcolor=THEME['input_bg'], sliderrelief='flat',
                                  command=lambda v: self.ram_value_label.config(text=f"{int(float(v))} GB"))
        self.ram_scale.set(4)
        self.ram_scale.pack(fill="x", pady=(3,0))

        # AI Mode
        ai_mode_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ai_mode_frame.pack(fill="x", padx=5, pady=(5, 5))
        tk.Label(ai_mode_frame, text="AI MODE", font=("Arial", 8, "bold"),
                 bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")
        tk.Checkbutton(ai_mode_frame, variable=self.ai_mode, bg=THEME['sidebar'], fg=THEME['text'],
                       selectcolor=THEME['sidebar'], activebackground=THEME['sidebar'],
                       activeforeground=THEME['text'], bd=0, highlightthickness=0, relief='flat').pack(side="right")

        # Buttons
        button_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        button_frame.pack(fill="x", padx=10, pady=(10, 10))
        def on_enter(e): e.widget.configure(bg=THEME['button_hover'])
        def on_leave(e): e.widget.configure(bg=THEME['accent'] if e.widget['text'] == "PLAY" else THEME['button'])
        skin_button = tk.Button(button_frame, text="CHANGE SKIN", font=("Arial", 10, "bold"),
                                bg=THEME['button'], fg=THEME['text'], bd=0, padx=10, pady=8, relief='flat',
                                command=self.select_skin)
        skin_button.pack(fill="x", pady=(0, 5))
        skin_button.bind("<Enter>", on_enter)
        skin_button.bind("<Leave>", on_leave)
        self.launch_button = tk.Button(button_frame, text="PLAY", font=("Arial", 12, "bold"),
                                       bg=THEME['accent'], fg=THEME['text'], bd=0, padx=10, pady=10, relief='flat',
                                       command=self.prepare_and_launch)
        self.launch_button.pack(fill="x")
        self.launch_button.bind("<Enter>", on_enter)
        self.launch_button.bind("<Leave>", on_leave)

        # Content area
        content_area = tk.Frame(main_container, bg=THEME['bg'])
        content_area.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        tk.Label(content_area, text="RECENT CHANGES", font=("Arial", 14, "bold"),
                 bg=THEME['bg'], fg=THEME['text']).pack(anchor="w", pady=(0, 10))
        changelog_items_frame = tk.Frame(content_area, bg=THEME['bg'])
        changelog_items_frame.pack(fill="both", expand=True)
        changelog_items = [
            "🐾 Rebranded to Cat Client with new theme and logo.",
            "⚙️ Added automatic Java 21 installation.",
            "✨ Improved UI styling and layout.",
            "🔓 Offline/cracked client mode enabled.",
            "🌐 Added el.by protocol support for authentication."
        ]
        for i, item in enumerate(changelog_items):
            item_bg = THEME['sidebar'] if i % 2 == 0 else THEME['input_bg']
            item_frame = tk.Frame(changelog_items_frame, bg=item_bg, padx=10, pady=8)
            item_frame.pack(fill="x", pady=(0, 5))
            tk.Label(item_frame, text=item, font=("Arial", 10), bg=item_bg, fg=THEME['text'],
                     justify="left", anchor="w", wraplength=400).pack(fill='x')

    def _clear_placeholder(self, event):
        if self.username_input.get() == "Enter Username":
            self.username_input.delete(0, tk.END)
            self.username_input.config(fg=THEME['text'])

    def _restore_placeholder(self, event):
        if not self.username_input.get():
            self.username_input.insert(0, "Enter Username")
            self.username_input.config(fg=THEME['text_secondary'])

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
            with urllib.request.urlopen(VERSION_MANIFEST_URL) as url:
                manifest = json.loads(url.read().decode())
                self.versions = {}
                for category in self.version_categories:
                    self.version_categories[category] = []
                latest_release_id = manifest["latest"]["release"]
                latest_snapshot_id = manifest["latest"]["snapshot"]
                for v in manifest["versions"]:
                    self.versions[v["id"]] = v["url"]
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
                self.after(0, self.update_version_list)  # Ensure UI update on main thread
                print("Version manifest loaded successfully.")
        except Exception as e:
            print(f"Error loading version manifest: {e}")
            self.after(0, lambda: messagebox.showerror("Error", "Failed to load version manifest. Check your internet connection."))

    def is_java_installed(self, required_version="21"):
        """Check for a suitable Java installation and return its path if found."""
        local_java_path = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java.exe" if platform.system() == "Windows" else "java")
        if os.path.exists(local_java_path):
            try:
                result = subprocess.run([local_java_path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', result.stderr)
                if match and int(match.group(1)) >= int(required_version):
                    print(f"Found local Java version: {match.group(1)}")
                    return local_java_path
            except Exception as e:
                print(f"Error checking local Java: {e}")
        try:
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            match = re.search(r'version "(\d+)\.?(\d+)?\.?(\d+)?', result.stderr)
            if match and int(match.group(1)) >= int(required_version):
                print(f"Found system Java version: {match.group(1)}")
                return "java"
            return None
        except FileNotFoundError:
            print("System Java not found.")
            return None
        except Exception as e:
            print(f"Error checking system Java: {e}")
            return None

    def install_java(self):
        """Install Java 21 locally if no suitable version is found."""
        print("Installing OpenJDK 21 locally...")
        system, arch = platform.system(), platform.architecture()[0]
        java_url = {
            ("Windows", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_windows_hotspot_21.0.5_11.zip", ".zip"),
            ("Linux", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_linux_hotspot_21.0.5_11.tar.gz", ".tar.gz"),
            ("Darwin", "64bit"): ("https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_mac_hotspot_21.0.5_11.tar.gz", ".tar.gz")
        }.get((system, arch))
        if not java_url:
            self.after(0, lambda: messagebox.showerror("Error", f"Unsupported OS ({system}) or architecture ({arch}). Install OpenJDK 21 manually."))
            return False
        url, ext = java_url
        archive_path = os.path.join(JAVA_DIR, f"openjdk{ext}")
        extracted_folder = os.path.join(JAVA_DIR, "jdk-21.0.5+11")
        if os.path.exists(extracted_folder):
            print("Local OpenJDK 21 already exists.")
            return True
        try:
            print(f"Downloading Java from: {url}")
            urllib.request.urlretrieve(url, archive_path)
            print("Extracting Java...")
            if ext == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(JAVA_DIR)
            else:
                with tarfile.open(archive_path, "r:gz") as tar_ref:
                    tar_ref.extractall(JAVA_DIR)
            os.remove(archive_path)
            if platform.system() in ["Linux", "Darwin"]:
                java_bin = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java")
                os.chmod(java_bin, 0o755)  # Ensure executable permissions
            print("Java 21 installed locally.")
            return True
        except Exception as e:
            print(f"Failed to install Java: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to install Java 21: {e}"))
            return False

    def install_java_if_needed(self):
        """Ensure a suitable Java version is available, installing locally if necessary."""
        java_path = self.is_java_installed("21")
        if java_path:
            print(f"Using existing Java at: {java_path}")
            return True
        return self.install_java()

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
                # Fixed: replaced walrus operator for Python < 3.8 compatibility
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    file_hash.update(chunk)
            return file_hash.hexdigest() == expected_sha1
        except Exception as e:
            print(f"Error verifying file {file_path}: {e}")
            return False

    def download_version_files(self, version_id, version_url):
        print(f"⬇️ Downloading files for {version_id}...")
        version_dir = os.path.join(VERSIONS_DIR, version_id)
        os.makedirs(version_dir, exist_ok=True)
        version_json_path = os.path.join(version_dir, f"{version_id}.json")
        if not os.path.exists(version_json_path):
            try:
                with urllib.request.urlopen(version_url) as url:
                    data = json.loads(url.read().decode())
                    with open(version_json_path, "w") as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Failed to download version JSON: {e}")
                return False
        try:
            with open(version_json_path, "r") as f:
                version_data = json.load(f)
        except Exception as e:
            print(f"Failed to load version JSON: {e}")
            return False

        jar_info = version_data.get("downloads", {}).get("client")
        if not jar_info:
            print("Missing client JAR info.")
            return False
        jar_path = os.path.join(version_dir, f"{version_id}.jar")
        if not os.path.exists(jar_path) or not self.verify_file(jar_path, jar_info["sha1"]):
            try:
                urllib.request.urlretrieve(jar_info["url"], jar_path)
                if not self.verify_file(jar_path, jar_info["sha1"]):
                    os.remove(jar_path)
                    print("Checksum mismatch for JAR.")
                    return False
            except Exception as e:
                print(f"Failed to download JAR: {e}")
                return False

        libraries_dir = os.path.join(MINECRAFT_DIR, "libraries")
        natives_dir = os.path.join(version_dir, "natives")
        os.makedirs(libraries_dir, exist_ok=True)
        os.makedirs(natives_dir, exist_ok=True)
        current_os = "osx" if platform.system() == "Darwin" else platform.system().lower()
        for lib in version_data.get("libraries", []):
            if self.is_library_allowed(lib, current_os):
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    artifact = lib["downloads"]["artifact"]
                    lib_path = os.path.join(libraries_dir, artifact["path"])
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    if not os.path.exists(lib_path) or not self.verify_file(lib_path, artifact["sha1"]):
                        try:
                            urllib.request.urlretrieve(artifact["url"], lib_path)
                            if not self.verify_file(lib_path, artifact["sha1"]):
                                os.remove(lib_path)
                                print(f"Checksum mismatch for library: {lib.get('name')}")
                        except Exception as e:
                            print(f"Failed to download library {lib.get('name')}: {e}")
                if "natives" in lib and current_os in lib["natives"]:
                    classifier = lib["natives"][current_os].replace("${arch}", platform.architecture()[0].replace('bit', ''))
                    if "downloads" in lib and classifier in lib["downloads"]["classifiers"]:
                        native = lib["downloads"]["classifiers"][classifier]
                        native_path = os.path.join(natives_dir, f"{lib['name'].split(':')[-1]}-{classifier}.jar")
                        if not os.path.exists(native_path) or not self.verify_file(native_path, native["sha1"]):
                            try:
                                urllib.request.urlretrieve(native["url"], native_path)
                                if self.verify_file(native_path, native["sha1"]):
                                    with zipfile.ZipFile(native_path, "r") as zip_ref:
                                        zip_ref.extractall(natives_dir)
                                else:
                                    os.remove(native_path)
                                    print(f"Checksum mismatch for native: {lib.get('name')}")
                            except Exception as e:
                                print(f"Failed to process native {lib.get('name')}: {e}")
        print("✅ Files downloaded!")
        return True

    def modify_options_txt(self, target_fps=60, ai_mode=False):
        options_path = os.path.join(MINECRAFT_DIR, "options.txt")
        options = {}
        if os.path.exists(options_path):
            try:
                with open(options_path, "r") as f:
                    for line in f:
                        if ":" in line:
                            key, value = line.strip().split(":", 1)
                            options[key] = value
            except Exception as e:
                print(f"Warning: Could not read options.txt: {e}")
        options['maxFps'] = str(target_fps)
        options['enableVsync'] = 'false'
        if ai_mode:
            options.update({
                'renderDistance': '8',
                'particles': 'minimal',
                'graphics': 'fast',
                'smoothLighting': 'false',
                'clouds': 'false',
                'fancyGrass': 'false',
                'useVbo': 'true'
            })
        try:
            with open(options_path, "w") as f:
                for key, value in options.items():
                    f.write(f"{key}:{value}\n")
            print(f"⚙️ Updated options.txt with {'AI mode' if ai_mode else 'standard'} settings.")
        except Exception as e:
            print(f"Warning: Could not write options.txt: {e}")

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

    def generate_offline_uuid(self, username):
        string_to_hash = f"OfflinePlayer:{username}"
        md5_hash = hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()
        return f"{md5_hash[:8]}-{md5_hash[8:12]}-{md5_hash[12:16]}-{md5_hash[16:20]}-{md5_hash[20:]}"

    def authenticate_ely_by(self, username):
        """Authenticate using el.by protocol (cracked mode)"""
        try:
            auth_data = {
                "username": username,
                "password": "",  # Empty password for cracked mode
                "clientToken": "cat-client-token",
                "requestUser": True
            }
            
            req = urllib.request.Request(
                ELY_BY_AUTH_URL,
                data=json.dumps(auth_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                auth_response = json.loads(response.read().decode())
                return auth_response
        except Exception as e:
            print(f"El.by authentication failed: {e}")
            return None

    def build_launch_command(self, version, username, ram, ai_mode=False):
        version_dir = os.path.join(VERSIONS_DIR, version)
        json_path = os.path.join(version_dir, f"{version}.json")
        if not os.path.exists(json_path):
            print("Version JSON missing.")
            return []
        try:
            with open(json_path, "r") as f:
                version_data = json.load(f)
        except Exception as e:
            print(f"Failed to read JSON: {e}")
            return []

        java_path = self.is_java_installed("21")
        if not java_path:
            print("Java 21+ not found.")
            return []
        
        main_class = version_data.get("mainClass", "")
        if not main_class:
            print("Main class not found.")
            return []

        libraries_dir = os.path.join(MINECRAFT_DIR, "libraries")
        natives_dir = os.path.join(version_dir, "natives")
        classpath = [os.path.join(version_dir, f"{version}.jar")]
        current_os = "osx" if platform.system() == "Darwin" else platform.system().lower()
        for lib in version_data.get("libraries", []):
            if self.is_library_allowed(lib, current_os) and "downloads" in lib and "artifact" in lib["downloads"]:
                lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
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
            command.extend([
                "-XX:+UseG1GC", "-XX:MaxGCPauseMillis=50", "-XX:+UnlockExperimentalVMOptions",
                "-XX:G1NewSizePercent=20", "-XX:G1ReservePercent=20", "-XX:G1HeapRegionSize=32M"
            ])

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

        # Fixed: Authenticate with el.by and use UUID from response if available
        auth_data = self.authenticate_ely_by(username)
        if auth_data:
            # Use el.by authentication data
            access_token = auth_data.get("accessToken", "")
            # Get UUID from auth response if available
            if "selectedProfile" in auth_data and "id" in auth_data["selectedProfile"]:
                uuid = auth_data["selectedProfile"]["id"]
            else:
                # Fallback to offline UUID generation
                uuid = self.generate_offline_uuid(username)
            user_properties = json.dumps(auth_data.get("user", {}).get("properties", {}))
        else:
            # Fallback to offline mode with generated UUID
            uuid = self.generate_offline_uuid(username)
            access_token = "0"
            user_properties = "{}"

        replacements = {
            "${auth_player_name}": username,
            "${version_name}": version,
            "${game_directory}": MINECRAFT_DIR,
            "${assets_root}": os.path.join(MINECRAFT_DIR, "assets"),
            "${assets_index_name}": version_data.get("assetIndex", {}).get("id", version),
            "${auth_uuid}": uuid,
            "${auth_access_token}": access_token,
            "${user_type}": "ely.by",  # Use el.by user type
            "${version_type}": version_data.get("type", "release"),
            "${user_properties}": user_properties,
            "${quickPlayRealms}": "",
            "${quickPlaySingleplayer}": "",
            "${quickPlayMultiplayer}": ""
        }
        final_game_args = []
        for arg in game_args:
            for key, value in replacements.items():
                if key in arg:
                    arg = arg.replace(key, str(value))
            final_game_args.append(arg)
        command.extend(final_game_args)
        return command

    def prepare_and_launch(self):
        selected_version = self.version_combo.get()
        if not selected_version:
            messagebox.showerror("Error", "Select a version.")
            return
            
        username = self.username_input.get().strip()
        if not username or username == "Enter Username":
            messagebox.showerror("Error", "Enter a username.")
            return

        self.launch_button.config(text="LAUNCHING...", state="disabled")
        def launch_thread():
            if not self.install_java_if_needed():
                self.after(0, lambda: messagebox.showerror("Error", "Failed to install Java 21."))
                self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))
                return
            if not self.download_version_files(selected_version, self.versions.get(selected_version)):
                self.after(0, lambda: messagebox.showerror("Error", "Failed to download game files."))
                self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))
                return
            self.modify_options_txt(target_fps=60, ai_mode=self.ai_mode.get())
            ram = int(self.ram_scale.get())
            # Fixed: removed UUID generation here since it's now handled in build_launch_command
            cmd = self.build_launch_command(selected_version, username, ram, ai_mode=self.ai_mode.get())
            if not cmd:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to build launch command."))
                self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))
                return
            try:
                subprocess.Popen(cmd, cwd=MINECRAFT_DIR)
                print("Minecraft launched.")
            except Exception as e:
                print(f"Launch failed: {e}")
                self.after(0, lambda: messagebox.showerror("Error", f"Launch failed: {e}"))
            self.after(0, lambda: self.launch_button.config(text="PLAY", state="normal"))

        threading.Thread(target=launch_thread, daemon=True).start()

if __name__ == "__main__":
    app = CatClientApp()
    app.mainloop()
