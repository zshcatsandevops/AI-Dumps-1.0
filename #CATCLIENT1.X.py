import os
import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import urllib.request
import subprocess
import platform
import threading
import uuid
import requests
import shutil
from typing import Dict, List, Optional, Any

# --- Constants ---
USER_AGENT = "CatClient/1.5 (LunarCat)"
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
ELYBY_AUTH_URL = "https://authserver.ely.by/auth/authenticate"

# Directories
if platform.system() == "Windows":
    APPDATA = os.environ.get('APPDATA', os.path.expanduser('~\\AppData\\Roaming'))
    BASE_DIR = os.path.join(APPDATA, '.catclient')
else:
    BASE_DIR = os.path.join(os.path.expanduser('~'), '.catclient')

MINECRAFT_DIR = os.path.join(BASE_DIR, 'minecraft')
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, 'versions')
LIBRARIES_DIR = os.path.join(MINECRAFT_DIR, 'libraries')
ASSETS_DIR = os.path.join(MINECRAFT_DIR, 'assets')

# --- Helpers ---
def ensure_directories():
    """Create all necessary directories if they don't exist"""
    for d in [MINECRAFT_DIR, VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR,
              os.path.join(ASSETS_DIR, 'indexes'), os.path.join(ASSETS_DIR, 'objects')]:
        os.makedirs(d, exist_ok=True)

def download_file(url: str, dest: str, progress_callback=None) -> bool:
    """Download a file with optional progress callback"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest): 
        if progress_callback:
            progress_callback(100)  # Already downloaded
        return True
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req) as resp:
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    f.write(chunk)
                    
                    if progress_callback and total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        progress_callback(progress)
            
            if progress_callback:
                progress_callback(100)
                
        print(f"Downloaded {dest}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def authenticate_elyby(username: str, password: str) -> Optional[Dict]:
    """Authenticate with Ely.by service"""
    try:
        payload = {
            "agent": {"name": "Minecraft", "version": 1},
            "username": username, 
            "password": password
        }
        resp = requests.post(ELYBY_AUTH_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            profile = data.get("selectedProfile", {})
            return {
                "username": profile.get("name", username),
                "uuid": profile.get("id"),
                "token": data.get("accessToken"),
                "type": "elyby"
            }
        else:
            print(f"Ely.by auth failed: {resp.text}")
    except Exception as e:
        print(f"Ely.by auth error: {e}")
    return None

def create_offline_session(username: str) -> Dict:
    """Create an offline session with the given username"""
    return {
        "username": username,
        "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, username)),
        "token": "cat_offline_token",
        "type": "offline"
    }

# --- Version Manager ---
class VersionManager:
    def __init__(self):
        self.versions = {}
        self.version_categories = {
            "Latest Release": [], "Latest Snapshot": [],
            "Release": [], "Snapshot": [], "Old Beta": [], "Old Alpha": []
        }
    
    def load_version_manifest(self) -> bool:
        """Load the version manifest from Mojang"""
        try:
            req = urllib.request.Request(VERSION_MANIFEST_URL, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(req) as url:
                manifest = json.loads(url.read().decode())
            
            self.versions = {v["id"]: v["url"] for v in manifest["versions"]}
            
            # Clear categories
            for c in self.version_categories:
                self.version_categories[c] = []
            
            # Categorize versions
            latest_release = manifest["latest"]["release"]
            latest_snapshot = manifest["latest"]["snapshot"]
            
            for v in manifest["versions"]:
                if v["id"] == latest_release:
                    self.version_categories["Latest Release"].append(v["id"])
                elif v["id"] == latest_snapshot:
                    self.version_categories["Latest Snapshot"].append(v["id"])
                elif v["type"] == "release":
                    self.version_categories["Release"].append(v["id"])
                elif v["type"] == "snapshot":
                    self.version_categories["Snapshot"].append(v["id"])
                elif v["type"] == "old_beta":
                    self.version_categories["Old Beta"].append(v["id"])
                elif v["type"] == "old_alpha":
                    self.version_categories["Old Alpha"].append(v["id"])
            
            # Sort version lists
            for c in ["Release", "Snapshot", "Old Beta", "Old Alpha"]:
                self.version_categories[c].sort(reverse=True)
                
            return True
        except Exception as e:
            print(f"Failed to load versions: {e}")
            return False
    
    def ensure_version(self, version_id: str, progress_callback=None) -> Optional[str]:
        """Ensure all files for a version are downloaded"""
        vdir = os.path.join(VERSIONS_DIR, version_id)
        vjson = os.path.join(vdir, f"{version_id}.json")
        os.makedirs(vdir, exist_ok=True)

        # Download version JSON
        if not os.path.exists(vjson):
            url = self.versions.get(version_id)
            if not url or not download_file(url, vjson, progress_callback):
                return None

        # Load version data
        try:
            with open(vjson) as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load version JSON: {e}")
            return None

        # Download client JAR
        jar_info = data.get("downloads", {}).get("client")
        jar_path = os.path.join(vdir, f"{version_id}.jar")
        if jar_info and not os.path.exists(jar_path):
            if not download_file(jar_info["url"], jar_path, progress_callback):
                return None

        # Download libraries
        libraries = data.get("libraries", [])
        for i, lib in enumerate(libraries):
            art = lib.get("downloads", {}).get("artifact")
            if art:
                lib_path = os.path.join(LIBRARIES_DIR, art["path"])
                if not os.path.exists(lib_path):
                    if progress_callback:
                        progress_callback(0, f"Downloading libraries ({i+1}/{len(libraries)})")
                    if not download_file(art["url"], lib_path):
                        print(f"Failed to download library: {art['url']}")

        # Download assets
        asset_index = data.get("assetIndex", {})
        if asset_index:
            idx_path = os.path.join(ASSETS_DIR, "indexes", f"{asset_index['id']}.json")
            if not os.path.exists(idx_path):
                if not download_file(asset_index["url"], idx_path, progress_callback):
                    return None
            
            try:
                with open(idx_path) as f:
                    idx = json.load(f)
            except Exception as e:
                print(f"Failed to load asset index: {e}")
                return None
            
            objects = idx.get("objects", {})
            total_objects = len(objects)
            for j, (name, obj) in enumerate(objects.items()):
                h = obj["hash"]
                sub = h[:2]
                apath = os.path.join(ASSETS_DIR, "objects", sub, h)
                if not os.path.exists(apath):
                    if progress_callback and j % 100 == 0:  # Update progress every 100 assets
                        progress_callback(int((j / total_objects) * 100), f"Downloading assets ({j}/{total_objects})")
                    url = f"https://resources.download.minecraft.net/{sub}/{h}"
                    if not download_file(url, apath):
                        print(f"Failed to download asset: {url}")

        return vjson

    def build_launch_command(self, version_id: str, session: Dict) -> List[str]:
        """Build the launch command for a version"""
        vdir = os.path.join(VERSIONS_DIR, version_id)
        vjson = os.path.join(vdir, f"{version_id}.json")
        
        if not os.path.exists(vjson):
            return []
            
        try:
            with open(vjson) as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load version JSON: {e}")
            return []
            
        main_class = data.get("mainClass")
        if not main_class:
            return []
            
        jar_path = os.path.join(vdir, f"{version_id}.jar")
        classpath = [jar_path]
        
        # Add libraries to classpath
        for lib in data.get("libraries", []):
            art = lib.get("downloads", {}).get("artifact")
            if art:
                lib_path = os.path.join(LIBRARIES_DIR, art["path"])
                if os.path.exists(lib_path):
                    classpath.append(lib_path)
        
        # Build Java command
        cmd = ["java", "-Xmx2G", "-cp", os.pathsep.join(classpath), main_class]
        
        # Process Minecraft arguments
        args = data.get("minecraftArguments", "").split()
        repl = {
            "${auth_player_name}": session["username"],
            "${auth_uuid}": session["uuid"],
            "${auth_access_token}": session["token"],
            "${version_name}": version_id,
            "${game_directory}": MINECRAFT_DIR,
            "${assets_root}": ASSETS_DIR,
            "${assets_index_name}": data.get("assetIndex", {}).get("id", ""),
            "${user_type}": session.get("type", "catclient"),
            "${user_properties}": "{}"
        }
        
        final_args = []
        for a in args:
            for k, v in repl.items():
                if k in a:
                    a = a.replace(k, v)
            final_args.append(a)
            
        return cmd + final_args

# --- CatClient Lunar Edition ---
class CatClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CatClient 1.5.x 🐾 (Lunar Cat)")
        self.geometry("900x550")
        self.configure(bg="#1b1b1b")
        
        self.version_manager = VersionManager()
        self.session = create_offline_session("CatPlayer")
        self.online_mode = tk.BooleanVar(value=False)
        self.downloading = False
        
        ensure_directories()
        self.init_ui()
        threading.Thread(target=self.load_version_manifest, daemon=True).start()

    def init_ui(self):
        # Main layout frames
        main_frame = tk.Frame(self, bg="#1b1b1b")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left sidebar
        sidebar = tk.Frame(main_frame, bg="#242424", width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Right content area
        content = tk.Frame(main_frame, bg="#1b1b1b")
        content.pack(side="right", fill="both", expand=True)
        
        # Sidebar content
        tk.Label(sidebar, text="🐾 CatClient 1.5.x", font=("Consolas", 18, "bold"),
                 bg="#242424", fg="#55ff55").pack(pady=15)
        
        # Status indicator
        self.status_var = tk.StringVar(value="Ready")
        status_frame = tk.Frame(sidebar, bg="#242424")
        status_frame.pack(fill="x", padx=15, pady=5)
        tk.Label(status_frame, text="Status:", bg="#242424", fg="white").pack(side="left")
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                    bg="#242424", fg="#aaaaaa")
        self.status_label.pack(side="right")
        
        # Login section
        login_frame = tk.LabelFrame(sidebar, text="Authentication", bg="#242424", fg="white")
        login_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(login_frame, text="Username/Email", bg="#242424", fg="white").pack(anchor="w", padx=5)
        self.username_input = tk.Entry(login_frame, bg="#404040", fg="white", relief="flat")
        self.username_input.pack(fill="x", padx=5, pady=3)
        self.username_input.insert(0, "CatPlayer")
        
        tk.Label(login_frame, text="Password", bg="#242424", fg="white").pack(anchor="w", padx=5, pady=(10, 0))
        self.password_input = tk.Entry(login_frame, bg="#404040", fg="white", show="*", relief="flat")
        self.password_input.pack(fill="x", padx=5, pady=3)
        
        tk.Checkbutton(login_frame, text="Login with Ely.by", variable=self.online_mode,
                       bg="#242424", fg="white", activebackground="#242424",
                       selectcolor="#242424", command=self.toggle_auth_fields).pack(anchor="w", padx=5, pady=5)
        
        # Version selection
        version_frame = tk.LabelFrame(sidebar, text="Game Version", bg="#242424", fg="white")
        version_frame.pack(fill="x", padx=15, pady=10)
        
        self.category_combo = ttk.Combobox(version_frame, values=list(self.version_manager.version_categories.keys()), 
                                          state="readonly")
        self.category_combo.pack(fill="x", padx=5, pady=3)
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)
        
        self.version_combo = ttk.Combobox(version_frame, state="readonly")
        self.version_combo.pack(fill="x", padx=5, pady=3)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(version_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", padx=5, pady=5)
        self.progress_label = tk.Label(version_frame, text="", bg="#242424", fg="white")
        self.progress_label.pack(fill="x", padx=5)
        
        # Buttons
        button_frame = tk.Frame(sidebar, bg="#242424")
        button_frame.pack(fill="x", padx=15, pady=10)
        
        self.play_btn = tk.Button(button_frame, text="🐾 PLAY 🐾", font=("Consolas", 14, "bold"),
                                 bg="#3aa13a", fg="white", relief="flat", command=self.prepare_and_launch)
        self.play_btn.pack(fill="x", pady=5)
        
        self.offline_btn = tk.Button(button_frame, text="Play Offline", font=("Consolas", 10),
                                    bg="#505050", fg="white", relief="flat", command=self.play_offline)
        self.offline_btn.pack(fill="x", pady=5)
        
        # Content area - News
        tk.Label(content, text="CatClient News", font=("Consolas", 16, "bold"),
                 bg="#1b1b1b", fg="white").pack(anchor="w", padx=15, pady=15)
        
        self.news_box = tk.Text(content, bg="#101010", fg="white", wrap="word",
                                relief="flat", font=("Consolas", 10))
        self.news_box.pack(fill="both", expand=True, padx=15, pady=10)
        self.news_box.insert("end", "✨ CatClient Lunar Edition\n\n- Ely.by online mode\n- Mojang offline mode\n- Auto-downloads JSON, JAR, libs, assets\n- Modern dark UI (Lunar vibes)\n")
        
        # Initialize UI state
        self.toggle_auth_fields()

    def toggle_auth_fields(self):
        """Enable/disable auth fields based on online mode selection"""
        state = "normal" if self.online_mode.get() else "disabled"
        self.password_input.config(state=state)

    def set_status(self, message: str, is_error: bool = False):
        """Update status message"""
        self.status_var.set(message)
        self.status_label.config(fg="#ff5555" if is_error else "#aaaaaa")
        self.update_idletasks()

    def update_progress(self, value: int, message: str = ""):
        """Update progress bar and label"""
        self.progress_var.set(value)
        self.progress_label.config(text=message)
        self.update_idletasks()

    def load_version_manifest(self):
        """Load version manifest in background thread"""
        self.set_status("Loading versions...")
        if self.version_manager.load_version_manifest():
            self.update_version_list()
            self.set_status("Versions loaded")
        else:
            self.set_status("Failed to load versions", True)
            messagebox.showerror("Error", "Failed to load version manifest. Check your internet connection.")

    def update_version_list(self, event=None):
        """Update version list based on selected category"""
        cat = self.category_combo.get()
        vs = self.version_manager.version_categories.get(cat, [])
        self.version_combo['values'] = vs
        if vs: 
            self.version_combo.current(0)

    def prepare_and_launch(self):
        """Prepare and launch the game"""
        version = self.version_combo.get()
        if not version:
            messagebox.showerror("Error", "Please select a version")
            return
            
        # Try online authentication if selected
        if self.online_mode.get():
            username = self.username_input.get().strip()
            password = self.password_input.get().strip()
            
            if not username or not password:
                messagebox.showerror("Error", "Please enter username and password for online mode")
                return
                
            self.set_status("Authenticating...")
            session = authenticate_elyby(username, password)
            
            if session:
                self.session = session
                self.launch_game(version, "Online")
            else:
                # Fall back to offline mode if auth fails
                if messagebox.askyesno("Auth Failed", "Online authentication failed. Would you like to play offline instead?"):
                    self.play_offline(version)
        else:
            # Use offline mode
            self.play_offline(version)

    def play_offline(self, version=None):
        """Play in offline mode"""
        if not version:
            version = self.version_combo.get()
            if not version:
                messagebox.showerror("Error", "Please select a version")
                return
                
        username = self.username_input.get().strip() or "CatPlayer"
        self.session = create_offline_session(username)
        self.launch_game(version, "Offline")

    def launch_game(self, version: str, mode: str):
        """Launch the game with the specified version and mode"""
        self.set_status(f"Preparing {version} ({mode})...")
        self.play_btn.config(state="disabled")
        self.offline_btn.config(state="disabled")
        
        # Download required files in a separate thread
        def download_thread():
            self.downloading = True
            vjson = self.version_manager.ensure_version(
                version, 
                lambda p, msg=None: self.update_progress(p, msg or f"Downloading: {p}%")
            )
            
            self.downloading = False
            self.after(0, self.finish_launch, version, vjson, mode)
            
        threading.Thread(target=download_thread, daemon=True).start()

    def finish_launch(self, version: str, vjson: Optional[str], mode: str):
        """Finish the launch process after downloads complete"""
        self.play_btn.config(state="normal")
        self.offline_btn.config(state="normal")
        self.update_progress(0, "")
        
        if not vjson:
            self.set_status(f"Failed to prepare {version}", True)
            messagebox.showerror("Error", f"Failed to download required files for {version}")
            return
            
        # Build and execute launch command
        cmd = self.version_manager.build_launch_command(version, self.session)
        if not cmd:
            self.set_status("Failed to build launch command", True)
            messagebox.showerror("Error", "Failed to build launch command")
            return
            
        try:
            self.set_status(f"Launching {version} ({mode}) as {self.session['username']}...")
            subprocess.Popen(cmd, cwd=MINECRAFT_DIR)
            self.set_status("Game launched")
            messagebox.showinfo("Launch", f"Meowcraft {version} started as {self.session['username']}!")
        except Exception as e:
            self.set_status("Launch failed", True)
            messagebox.showerror("Error", f"Launch failed: {e}")

    def on_closing(self):
        """Handle application closing"""
        if self.downloading and messagebox.askokcancel("Quit", "Downloads are in progress. Are you sure you want to quit?"):
            self.destroy()
        elif not self.downloading:
            self.destroy()

if __name__ == "__main__":
    ensure_directories()
    app = CatClientApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
