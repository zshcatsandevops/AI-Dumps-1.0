# delta_mario_64dd_boot.py
# ---------------------------------------------------------
# Delta Mario 64DD Boot Menu — Ursina 8.x
#  - 2D text overlays (camera.ui)
#  - 3D spinning 64DD drive
#  - "Press Z to boot" prompt
# ---------------------------------------------------------

from ursina import *

app = Ursina()

window.color = color.black
window.title = "Delta Mario 64DD — Boot Menu"

# Camera setup
camera.position = (0, 3, -12)
camera.look_at((0, 0, 0))

# --- Title Text (UI overlay) ---
title1 = Text("DELTA", scale=3, x=-.6, y=.4,  color=color.azure,  parent=camera.ui)
title2 = Text("MARIO", scale=3, x=-.2, y=.25, color=color.violet, parent=camera.ui)
title3 = Text("64DD",  scale=3, x=.2,  y=.1,  color=color.orange, parent=camera.ui)

# Blinking prompt (UI overlay)
press_text = Text("PRESS Z TO BOOT GAME", scale=2, y=-.35, color=color.white, parent=camera.ui)

# --- 64DD Disk Drive (3D objects) ---
drive_base = Entity(model=Cylinder(64,64), color=color.gray,    scale=(6,1,6),   y=-2)
drive_top  = Entity(model=Cylinder(64,64), color=color.black66, scale=(5.5,.3,5.5), y=-1.6)

# Dongle mock (cube)
dongle = Entity(model='cube', color=color.dark_gray, scale=(1,.3,.3), y=-2, x=5)

# Labels (UI overlay instead of tiny 3D text)
drive_label = Text("64DD", scale=2, color=color.cyan, y=-.55, parent=camera.ui)
z_label     = Text("Z",    scale=2, color=color.white, x=.5, y=-.55, parent=camera.ui)

# --- Boot sequence ---
def boot_game():
    print(">>> Delta Mario 64DD is booting...")
    press_text.enabled = False
    fade = Entity(model="quad", color=color.black, scale=30, z=-5)
    fade.fade_in(duration=1)
    invoke(application.quit, delay=1.5)

def update():
    # Blink "Press Z" text
    press_text.enabled = (int(time.time()*2) % 2 == 0)
    # Spin platter
    drive_top.rotation_y += time.dt * 30
    # Keys
    if held_keys['z']:
        boot_game()
    if held_keys['escape']:
        application.quit()

app.run()
