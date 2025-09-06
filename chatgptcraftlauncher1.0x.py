import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog
import json
import os
import subprocess
import uuid
import requests
from pathlib import Path
import minecraft_launcher_lib
from threading import Thread
import webbrowser
from PIL import Image, ImageTk  # for skin preview
import io

# Configuration
MINECRAFT_DIR = os.path.join(str(Path.home()), ".meowclient")
VERSIONS_DIR = os.path.join(MINECRAFT_DIR, "versions")
LAUNCHER_PROFILES_FILE = os.path.join(MINECRAFT_DIR, "launcher_profiles.json")
ASSETS_DIR = os.path.join(MINECRAFT_DIR, "assets")
LIBRARIES_DIR = os.path.join(MINECRAFT_DIR, "libraries")


class MeowClientLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Meow Client 1.0a")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Ensure directories exist
        os.makedirs(VERSIONS_DIR, exist_ok=True)
        os.makedirs(ASSETS_DIR, exist_ok=True)
        os.makedirs(LIBRARIES_DIR, exist_ok=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create frames for tabs
        self.play_frame = ttk.Frame(self.notebook)
        self.news_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        self.mods_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.play_frame, text="Play")
        self.notebook.add(self.news_frame, text="News")
        self.notebook.add(self.settings_frame, text="Settings")
        self.notebook.add(self.mods_frame, text="Mods")

        # Setup each tab
        self.setup_play_tab()
        self.setup_news_tab()
        self.setup_settings_tab()
        self.setup_mods_tab()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

        self.status_var.set("Ready")

        # Load available versions
        self.load_versions()

    def setup_play_tab(self):
        # Left side - Player info
        left_frame = ttk.LabelFrame(self.play_frame, text="Player", padding="10")
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        ttk.Label(left_frame, text="Username:").pack(anchor="w")
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(left_frame, textvariable=self.username_var, width=20)
        username_entry.pack(fill="x", pady=5)

        # Skin preview
        self.skin_label = ttk.Label(left_frame, text="Skin preview\n(64x64)", background="lightgray")
        self.skin_label.pack(pady=10, ipadx=32, ipady=32)

        # Load skin button
        load_skin_btn = ttk.Button(left_frame, text="Load Skin", command=self.load_skin_preview)
        load_skin_btn.pack(pady=(0, 10))

        # Right side - Version selection
        right_frame = ttk.LabelFrame(self.play_frame, text="Version", padding="10")
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ttk.Label(right_frame, text="Minecraft Version:").pack(anchor="w")
        self.version_var = tk.StringVar()
        self.version_combo = ttk.Combobox(right_frame, textvariable=self.version_var, state="readonly")
        self.version_combo.pack(fill="x", pady=5)

        # Version description
        self.version_desc = scrolledtext.ScrolledText(right_frame, height=10, width=40)
        self.version_desc.pack(fill="both", expand=True, pady=5)
        self.version_desc.config(state="disabled")

        # Bottom - Launch options
        bottom_frame = ttk.Frame(self.play_frame)
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        ttk.Label(bottom_frame, text="RAM (GB):").pack(side="left")
        self.ram_var = tk.IntVar(value=2)
        ram_spin = ttk.Spinbox(bottom_frame, from_=1, to=16, textvariable=self.ram_var, width=5)
        ram_spin.pack(side="left", padx=5)

        self.offline_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom_frame, text="Offline Mode", variable=self.offline_var).pack(side="left", padx=10)

        self.demo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom_frame, text="Demo Mode", variable=self.demo_var).pack(side="left", padx=10)

        launch_btn = ttk.Button(bottom_frame, text="Launch", command=self.launch_game)
        launch_btn.pack(side="right")

    def setup_news_tab(self):
        news_text = scrolledtext.ScrolledText(self.news_frame, wrap=tk.WORD)
        news_text.pack(fill="both", expand=True, padx=10, pady=10)
        news_text.insert("1.0", "Loading Minecraft news...")
        news_text.config(state="disabled")

        # Load news in background
        Thread(target=self.load_news, args=(news_text,), daemon=True).start()

    def setup_settings_tab(self):
        settings_frame = ttk.Frame(self.settings_frame)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(settings_frame, text="Java Path:").grid(row=0, column=0, sticky="w", pady=5)
        self.java_path_var = tk.StringVar(value="java")
        ttk.Entry(settings_frame, textvariable=self.java_path_var).grid(row=0, column=1, sticky="we", pady=5, padx=5)

        ttk.Label(settings_frame, text="Game Directory:").grid(row=1, column=0, sticky="w", pady=5)
        self.game_dir_var = tk.StringVar(value=MINECRAFT_DIR)
        ttk.Entry(settings_frame, textvariable=self.game_dir_var).grid(row=1, column=1, sticky="we", pady=5, padx=5)

        ttk.Label(settings_frame, text="Window Size:").grid(row=2, column=0, sticky="w", pady=5)
        size_frame = ttk.Frame(settings_frame)
        size_frame.grid(row=2, column=1, sticky="w", pady=5, padx=5)

        self.width_var = tk.StringVar(value="854")
        self.height_var = tk.StringVar(value="480")
        ttk.Entry(size_frame, textvariable=self.width_var, width=5).pack(side="left")
        ttk.Label(size_frame, text="x").pack(side="left", padx=2)
        ttk.Entry(size_frame, textvariable=self.height_var, width=5).pack(side="left")

        ttk.Checkbutton(settings_frame, text="Fullscreen", variable=tk.BooleanVar()).grid(row=3, column=1, sticky="w", pady=5)

        settings_frame.columnconfigure(1, weight=1)

    def setup_mods_tab(self):
        mods_frame = ttk.Frame(self.mods_frame)
        mods_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(mods_frame, text="Mod Loader:").grid(row=0, column=0, sticky="w", pady=5)
        # Use all supported mod loaders from minecraft_launcher_lib
        try:
            loader_ids = minecraft_launcher_lib.mod_loader.list_mod_loader()
            # Map loader ids to human friendly names (capitalize first letter)
            loader_names = [loader_id.title() for loader_id in loader_ids]
        except Exception:
            loader_ids = []
            loader_names = []
        # Prepend None option
        loader_names.insert(0, "None")
        loader_ids.insert(0, "none")
        self.mod_loader_ids = loader_ids
        self.mod_loader_combo = ttk.Combobox(mods_frame, values=loader_names, state="readonly")
        self.mod_loader_combo.set("None")
        self.mod_loader_combo.grid(row=0, column=1, sticky="we", pady=5, padx=5)

        # Mods list
        self.mod_listbox = tk.Listbox(mods_frame)
        self.mod_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=5)

        btn_frame = ttk.Frame(mods_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, sticky="we", pady=5)

        ttk.Button(btn_frame, text="Add Mod", command=self.add_mod).pack(side="left")
        ttk.Button(btn_frame, text="Remove Mod", command=self.remove_mod).pack(side="left")
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_mods_list).pack(side="right")

        # Button to install selected mod loader
        ttk.Button(btn_frame, text="Install Loader", command=self.install_selected_loader).pack(side="right", padx=(5, 0))

        mods_frame.columnconfigure(1, weight=1)
        mods_frame.rowconfigure(1, weight=1)

    def load_versions(self):
        try:
            # Get all available versions
            versions = minecraft_launcher_lib.utils.get_version_list()
            version_names = [v["id"] for v in versions]
            self.version_combo["values"] = version_names

            # Select latest release if available
            latest_release = next((v for v in versions if v["type"] == "release"), None)
            if latest_release:
                self.version_var.set(latest_release["id"])

            # Bind version selection event
            self.version_combo.bind("<<ComboboxSelected>>", self.on_version_select)
            self.on_version_select()  # Initial update

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load versions: {str(e)}")

    def load_skin_preview(self):
        """
        Download and display the player's skin preview using the MCHeads API.
        If the username is invalid or the request fails, fallback to a placeholder
        text. This method fetches a full body preview (100px) and scales it down
        to 64×64 for display.
        """
        username = self.username_var.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username before loading the skin.")
            return
        # Build the URL for the skin preview (full body). The API returns a PNG
        # representation of the player's skin.
        url = f"https://mc-heads.net/player/{username}/100.png"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            # Convert the bytes into a PIL Image
            image = Image.open(io.BytesIO(resp.content))
            # Resize down to 64x64 while preserving aspect ratio
            image = image.resize((64, 64), Image.NEAREST)
            photo = ImageTk.PhotoImage(image)
            # Update label
            self.skin_label.config(image=photo, text='')
            # Keep a reference to prevent garbage collection
            self.skin_label.image = photo
        except Exception:
            # If download fails, clear skin preview and show default text
            self.skin_label.config(image='', text="Failed to load skin\n(64x64)")

    def install_selected_loader(self):
        """
        Install the mod loader selected in the Mods tab for the currently
        selected Minecraft version. This method uses minecraft_launcher_lib's
        mod_loader API. If the loader is already installed, a message will
        indicate success. Progress updates are reflected in the status bar.
        """
        loader_name = self.mod_loader_combo.get()
        # 'None' means do not install any loader
        if loader_name.lower() in ("none", ""):
            messagebox.showinfo("Mod Loader", "No mod loader selected.")
            return
        # Map back to loader id (lowercase)
        loader_id = loader_name.lower()
        version = self.version_var.get()
        if not version:
            messagebox.showerror("Error", "Please select a Minecraft version first.")
            return
        # Get the mod loader instance
        try:
            loader = minecraft_launcher_lib.mod_loader.get_mod_loader(loader_id)
        except ValueError:
            messagebox.showerror("Error", f"Unknown mod loader: {loader_name}")
            return
        # Install loader asynchronously
        def _install():
            try:
                # Set up callbacks for progress
                def set_status(status: str):
                    self.status_var.set(status)
                def set_progress(progress: int):
                    if progress > 0:
                        self.status_var.set(f"Installing {loader_name}: {progress}%")
                def set_max(new_max: int):
                    pass
                # Install the loader; this will also install the vanilla version if necessary
                loader.install(version, self.game_dir_var.get(), callback={
                    "setStatus": set_status,
                    "setProgress": set_progress,
                    "setMax": set_max
                })
                self.status_var.set(f"{loader_name} installed for version {version}.")
                messagebox.showinfo("Success", f"{loader_name} has been installed for version {version}.")
            except minecraft_launcher_lib.exceptions.UnsupportedVersion:
                self.status_var.set(f"{loader_name} does not support version {version}.")
                messagebox.showerror("Error", f"{loader_name} does not support version {version}.")
            except Exception as e:
                self.status_var.set(f"Failed to install {loader_name}.")
                messagebox.showerror("Error", f"Failed to install {loader_name}: {str(e)}")
        Thread(target=_install, daemon=True).start()

    def refresh_mods_list(self):
        """
        Refresh the list of mods displayed in the listbox. It scans the mods
        directory inside the selected game directory and lists all .jar files.
        """
        self.mod_listbox.delete(0, tk.END)
        mods_dir = os.path.join(self.game_dir_var.get(), 'mods')
        if not os.path.isdir(mods_dir):
            return
        for filename in os.listdir(mods_dir):
            if filename.lower().endswith('.jar'):
                self.mod_listbox.insert(tk.END, filename)

    def add_mod(self):
        """
        Add a mod file (.jar) to the mods directory. This opens a file dialog to
        choose a local .jar file and copies it into the mods folder. After
        copying, the list is refreshed. If the user cancels the dialog, no
        action is taken.
        """
        file_path = filedialog.askopenfilename(title="Select Mod", filetypes=[("Jar Files", "*.jar")])
        if not file_path:
            return
        mods_dir = os.path.join(self.game_dir_var.get(), 'mods')
        os.makedirs(mods_dir, exist_ok=True)
        try:
            dest_path = os.path.join(mods_dir, os.path.basename(file_path))
            # Copy the file (overwriting if exists)
            with open(file_path, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            self.refresh_mods_list()
            messagebox.showinfo("Mod Added", f"{os.path.basename(file_path)} has been added.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add mod: {str(e)}")

    def remove_mod(self):
        """
        Remove the selected mod from the mods directory. Prompts the user for
        confirmation before deletion. After removal, the list is refreshed.
        """
        selection = self.mod_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "No mod selected to remove.")
            return
        filename = self.mod_listbox.get(selection[0])
        mods_dir = os.path.join(self.game_dir_var.get(), 'mods')
        file_path = os.path.join(mods_dir, filename)
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", "Mod file not found.")
            return
        if messagebox.askyesno("Remove Mod", f"Are you sure you want to remove {filename}?"):
            try:
                os.remove(file_path)
                self.refresh_mods_list()
                messagebox.showinfo("Removed", f"{filename} has been removed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove mod: {str(e)}")

    def on_version_select(self, event=None):
        version_id = self.version_var.get()
        if not version_id:
            return

        try:
            version_info = minecraft_launcher_lib.utils.get_version_list()
            selected_version = next((v for v in version_info if v["id"] == version_id), None)

            self.version_desc.config(state="normal")
            self.version_desc.delete("1.0", tk.END)

            if selected_version:
                desc_text = f"Version: {selected_version['id']}\n"
                desc_text += f"Type: {selected_version['type']}\n"
                desc_text += f"Release Time: {selected_version['releaseTime']}\n"

                if "url" in selected_version:
                    desc_text += f"URL: {selected_version['url']}\n"

                self.version_desc.insert("1.0", desc_text)

            self.version_desc.config(state="disabled")

        except Exception as e:
            self.version_desc.config(state="normal")
            self.version_desc.delete("1.0", tk.END)
            self.version_desc.insert("1.0", f"Error loading version info: {str(e)}")
            self.version_desc.config(state="disabled")

    def load_news(self, news_text):
        try:
            # Try to get Minecraft news
            news = minecraft_launcher_lib.utils.get_news()

            news_text.config(state="normal")
            news_text.delete("1.0", tk.END)

            for item in news:
                news_text.insert(tk.END, f"{item['title']}\n")
                news_text.insert(tk.END, f"{item['date']}\n")
                news_text.insert(tk.END, f"{item['text']}\n\n")
                news_text.insert(tk.END, "-" * 50 + "\n\n")

            news_text.config(state="disabled")

        except Exception as e:
            news_text.config(state="normal")
            news_text.delete("1.0", tk.END)
            news_text.insert(tk.END, f"Failed to load news: {str(e)}")
            news_text.config(state="disabled")

    def launch_game(self):
        username = self.username_var.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username!")
            return

        version = self.version_var.get()
        if not version:
            messagebox.showerror("Error", "Please select a version!")
            return

        # Prepare launch options
        options = {
            "username": username,
            "uuid": str(uuid.uuid4()),
            "token": "0",
            "jvmArguments": [
                f"-Xmx{self.ram_var.get()}G",
                f"-Xms{max(1, self.ram_var.get() // 2)}G"
            ],
            "launcherVersion": "MeowClient-1.0a"
        }

        # Add window size options if not fullscreen
        if not self.demo_var.get():
            options["customResolution"] = True
            options["resolutionWidth"] = self.width_var.get()
            options["resolutionHeight"] = self.height_var.get()

        # Set game directory
        options["gameDirectory"] = self.game_dir_var.get()

        self.status_var.set("Launching Minecraft...")

        try:
            # Determine if a mod loader is selected; if so, use the modded version
            loader_name = self.mod_loader_combo.get() if hasattr(self, 'mod_loader_combo') else "None"
            target_version = version
            loader = None
            loader_version = None
            if loader_name and loader_name.lower() not in ("none", ""):
                loader_id = loader_name.lower()
                try:
                    loader = minecraft_launcher_lib.mod_loader.get_mod_loader(loader_id)
                    # Use the latest loader version for the selected vanilla version
                    loader_version = loader.get_latest_loader_version(version)
                    target_version = loader.get_installed_version(version, loader_version)
                except Exception:
                    # Fallback to vanilla if retrieval fails
                    loader = None
                    target_version = version
            # Ensure the required version (vanilla or modded) is installed
            try:
                # Try to build command directly. If the version is missing, this will raise VersionNotFound.
                command = minecraft_launcher_lib.command.get_minecraft_command(
                    target_version,
                    self.game_dir_var.get(),
                    options
                )
            except minecraft_launcher_lib.exceptions.VersionNotFound:
                # If the modded version is missing but a mod loader is selected, install it
                if loader is not None:
                    # Ensure vanilla version is installed first
                    minecraft_launcher_lib.install.install_minecraft_version(
                        version,
                        self.game_dir_var.get(),
                        callback=None
                    )
                    # Install the mod loader synchronously to ensure the modded version exists
                    loader.install(version, self.game_dir_var.get(), loader_version=loader_version)
                    # Recompute target version after installation
                    target_version = loader.get_installed_version(version, loader_version)
                else:
                    # For vanilla version missing, install vanilla
                    minecraft_launcher_lib.install.install_minecraft_version(
                        version,
                        self.game_dir_var.get(),
                        callback=None
                    )
                # Build command again after installation
                command = minecraft_launcher_lib.command.get_minecraft_command(
                    target_version,
                    self.game_dir_var.get(),
                    options
                )
            # Launch the game
            subprocess.Popen(command, cwd=self.game_dir_var.get())
            self.status_var.set("Game launched successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch: {str(e)}")
            self.status_var.set("Launch failed")

    def download_version(self, version):
        try:
            # Create callback for progress
            def set_status(status: str):
                self.status_var.set(status)

            def set_progress(progress: int):
                if progress == 0:
                    return
                self.status_var.set(f"Downloading... {progress}%")

            def set_max(new_max: int):
                pass

            # Download the version
            minecraft_launcher_lib.install.install_minecraft_version(
                version,
                self.game_dir_var.get(),
                callback={
                    "setStatus": set_status,
                    "setProgress": set_progress,
                    "setMax": set_max
                }
            )

            self.status_var.set(f"Version {version} installed successfully!")
            messagebox.showinfo("Success", f"Version {version} has been installed. You can now launch the game.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to download version: {str(e)}")
            self.status_var.set("Download failed")


if __name__ == "__main__":
    root = tk.Tk()
    app = MeowClientLauncher(root)
    root.mainloop()
