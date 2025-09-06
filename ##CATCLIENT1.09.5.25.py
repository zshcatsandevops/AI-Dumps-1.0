import tkinter as tk
from tkinter import ttk, messagebox
import minecraft_launcher_lib as mll
import subprocess
import os
import json
import uuid
import threading
import requests
import re

class CatClient21:
    def __init__(self, root):
        self.root = root
        self.root.title("CatClient 2.1 - Lunar Replica")
        self.root.geometry("800x500")
        self.root.resizable(False, False)
        self.root.configure(bg='#0a0a23')
        
        # Apply a custom theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#0a0a23')
        self.style.configure('TLabel', background='#0a0a23', foreground='white')
        self.style.configure('TButton', background='#4d4dff', foreground='white', borderwidth=0)
        self.style.map('TButton', background=[('active', '#6666ff')])
        self.style.configure('TCombobox', fieldbackground='#1a1a3a', background='#1a1a3a', foreground='white')
        self.style.configure('TEntry', fieldbackground='#1a1a3a', foreground='white')
        self.style.configure('TProgressbar', troughcolor='#1a1a3a', background='#4d4dff')
        
        # Minecraft directory
        self.minecraft_dir = mll.utils.get_minecraft_directory()
        
        # Setup variables
        self.versions = []
        self.selected_version = tk.StringVar()
        self.selected_install_version = tk.StringVar()
        self.username = tk.StringVar(value="Player")
        self.setup_done = False
        
        self.setup_ui()
        self.load_available_mc_versions()
        self.check_setup()
    
    # ----------------- Config helpers -----------------
    def get_config_path(self):
        return os.path.join(self.minecraft_dir, "catclient_config.json")

    def load_config(self):
        try:
            path = self.get_config_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except:
            pass
        return {}

    def save_config(self, data):
        try:
            path = self.get_config_path()
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.status_label.config(text=f"Failed to save config: {str(e)}")

    # ----------------- UI -----------------
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        logo_label = ttk.Label(main_frame, text="CatClient 2.1", 
                               font=("Arial", 24, "bold"))
        logo_label.pack(pady=20)
        
        username_frame = ttk.Frame(main_frame)
        username_frame.pack(fill=tk.X, pady=10)
        ttk.Label(username_frame, text="Username:").pack(side=tk.LEFT)
        username_entry = ttk.Entry(username_frame, textvariable=self.username)
        username_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        version_install_frame = ttk.Frame(main_frame)
        version_install_frame.pack(fill=tk.X, pady=10)
        ttk.Label(version_install_frame, text="Install Version:").pack(side=tk.LEFT)
        self.install_version_combo = ttk.Combobox(version_install_frame, textvariable=self.selected_install_version)
        self.install_version_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=10)
        ttk.Label(version_frame, text="Launch Version:").pack(side=tk.LEFT)
        self.version_combo = ttk.Combobox(version_frame, textvariable=self.selected_version)
        self.version_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=30)
        self.setup_btn = ttk.Button(button_frame, text="Setup", 
                                   command=self.setup_minecraft, width=20)
        self.setup_btn.pack(side=tk.LEFT, padx=10)
        self.launch_btn = ttk.Button(button_frame, text="Launch", 
                                    command=self.launch_minecraft, state=tk.DISABLED, width=20)
        self.launch_btn.pack(side=tk.LEFT, padx=10)
        self.refresh_btn = ttk.Button(button_frame, text="Refresh", 
                                     command=self.refresh_versions, width=20)
        self.refresh_btn.pack(side=tk.LEFT, padx=10)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack()
    
    # ----------------- Versions -----------------
    def refresh_versions(self):
        self.load_available_mc_versions()
        self.load_versions()
        self.status_label.config(text="Versions refreshed")
    
    def load_available_mc_versions(self):
        try:
            version_list = mll.utils.get_version_list()
            releases = []
            for v in version_list:
                if v['type'] in ['release', 'snapshot']:
                    try:
                        if mll.fabric.is_minecraft_version_supported(v['id']):
                            releases.append(v['id'])
                    except:
                        continue
            self.install_version_combo['values'] = releases
            if releases:
                latest_release = next((v for v in releases if re.match(r'^\d+\.\d+(\.\d+)?$', v)), releases[0])
                self.selected_install_version.set(latest_release)
        except Exception as e:
            self.status_label.config(text=f"Error loading available versions: {str(e)}")
    
    def check_setup(self):
        if os.path.exists(self.minecraft_dir):
            self.load_versions()
            config = self.load_config()
            saved_version = config.get("launch_version")
            if saved_version and saved_version in [v['id'] for v in self.versions]:
                self.selected_version.set(saved_version)
                self.status_label.config(text=f"Loaded saved launch version: {saved_version}")
        else:
            self.status_label.config(text="Minecraft directory not found. Click Setup.")
    
    def load_versions(self):
        try:
            all_versions = mll.utils.get_installed_versions(self.minecraft_dir)
            self.versions = [v for v in all_versions if 'fabric' in v['id'].lower()]
            version_list = [v['id'] for v in self.versions]
            self.version_combo["values"] = version_list
            if version_list:
                if not self.selected_version.get():
                    self.selected_version.set(version_list[0])
                self.launch_btn.config(state=tk.NORMAL)
                self.setup_done = True
                self.status_label.config(text="Ready to play!")
            else:
                self.launch_btn.config(state=tk.DISABLED)
                self.status_label.config(text="No Fabric versions installed. Click Setup.")
        except Exception as e:
            self.status_label.config(text=f"Error loading versions: {str(e)}")
    
    # ----------------- Setup -----------------
    def setup_minecraft(self):
        threading.Thread(target=self._setup_minecraft_thread, daemon=True).start()
    
    def _setup_minecraft_thread(self):
        try:
            self.setup_btn.config(state=tk.DISABLED)
            self.progress.start()
            self.status_label.config(text="Setting up CatClient...")
            
            if not os.path.exists(self.minecraft_dir):
                os.makedirs(self.minecraft_dir)
            
            mc_version = self.selected_install_version.get()
            if not mc_version:
                raise Exception("No version selected for installation")
            
            if not mll.fabric.is_minecraft_version_supported(mc_version):
                raise Exception(f"Fabric not supported for {mc_version}")
            
            self.status_label.config(text=f"Installing Minecraft {mc_version}...")
            callback = {"setStatus": lambda text: self.status_label.config(text=text),
                        "setProgress": lambda p: None, "setMax": lambda m: None}
            mll.install.install_minecraft_version(mc_version, self.minecraft_dir, callback=callback)
            
            self.status_label.config(text=f"Installing Fabric for {mc_version}...")
            mll.fabric.install_fabric(mc_version, self.minecraft_dir, callback=callback)
            
            mods_dir = os.path.join(self.minecraft_dir, 'mods')
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir)
            
            essential_mods = ['sodium','lithium','phosphor','iris','modmenu']
            for slug in essential_mods:
                self.download_mod_from_modrinth(slug, mc_version)
            
            self.load_versions()
            if self.versions:
                installed = self.versions[0]['id']
                self.selected_version.set(installed)
                self.save_config({"launch_version": installed})
                self.status_label.config(text=f"Setup complete! Default set to {installed}")
        except Exception as e:
            messagebox.showerror("Error", f"Setup failed: {str(e)}")
            self.status_label.config(text=f"Setup failed: {str(e)}")
        finally:
            self.progress.stop()
            self.setup_btn.config(state=tk.NORMAL)
    
    def download_mod_from_modrinth(self, slug, mc_version, loader='fabric'):
        try:
            api_url = f"https://api.modrinth.com/v2/project/{slug}/version?game_versions=[\"{mc_version}\"]&loaders=[\"{loader}\"]"
            resp = requests.get(api_url)
            resp.raise_for_status()
            versions = resp.json()
            if versions:
                version_data = versions[0]
                file_url = version_data['files'][0]['url']
                filename = version_data['files'][0]['filename']
                mod_path = os.path.join(self.minecraft_dir, 'mods', filename)
                self.status_label.config(text=f"Downloading {slug}...")
                mod_data = requests.get(file_url).content
                with open(mod_path, 'wb') as f:
                    f.write(mod_data)
        except Exception as e:
            self.status_label.config(text=f"Failed to download {slug}: {str(e)}, skipping...")
    
    # ----------------- Launch -----------------
    def launch_minecraft(self):
        if not self.setup_done:
            messagebox.showerror("Error", "Please setup CatClient first")
            return
        threading.Thread(target=self._launch_minecraft_thread, daemon=True).start()
    
    def _launch_minecraft_thread(self):
        try:
            self.launch_btn.config(state=tk.DISABLED)
            self.progress.start()
            
            version = self.selected_version.get()
            username = self.username.get()
            player_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, username))
            
            self.status_label.config(text=f"Launching CatClient ({version})...")
            self.root.title(f"CatClient 2.1 - Running {version}")
            
            options = {"username": username, "uuid": player_uuid, "token": ""}
            command = mll.command.get_minecraft_command(version, self.minecraft_dir, options)
            
            self.status_label.config(text=f"Starting game ({version})...")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            try:
                stdout, stderr = process.communicate(timeout=5)
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else stdout.decode('utf-8')
                    raise Exception(f"Game failed to start: {error_msg}")
            except subprocess.TimeoutExpired:
                pass
            
            self.status_label.config(text=f"Game started! ({version})")
            self.save_config({"launch_version": version})
        except Exception as e:
            messagebox.showerror("Error", f"Launch failed: {str(e)}")
            self.status_label.config(text=f"Launch failed: {str(e)}")
        finally:
            self.progress.stop()
            self.launch_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = CatClient21(root)
    root.mainloop()
