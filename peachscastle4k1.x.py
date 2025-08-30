# castle_full.py — SM64-inspired Peach's Castle (600x400 base, HD window)

from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from math import sin, cos, pi
import random, time as pytime

app = Ursina()

# -------------------------
# Window setup
# -------------------------
window.title = "Peach's Castle — Full Build (600x400 Base)"
window.size = (1980,1080)
window.color = color.rgb(155, 205, 255)
window.fps_counter.enabled = False
window.fullscreen = False
window.borderless = False
window.sizeable = False   # disable maximize/resize

# -------------------------
# Helpers
# -------------------------
def safe_cone_model():
    try:
        load_model('cone')
        return 'cone'
    except:
        print('[info] cone model missing; using cylinder.')
        return 'cylinder'
CONE_MODEL = safe_cone_model()

def set_cast_shadows(e,on=True):
    for attr in ('shadows','cast_shadows'):
        if hasattr(e,attr): setattr(e,attr,on)
    return e

# -------------------------
# Scene + Lighting
# -------------------------
Sky()
AmbientLight(color=color.rgba(255,255,255,150))
d = DirectionalLight(shadows=True)
d.look_at(Vec3(1,-2,-1))

# Palette
WALLS     = color.rgb(200,140,120)   # terracotta bricks
ROOF_RED  = color.rgb(220,60,40)     # roofs
DOOR_WOOD = color.rgb(90,55,25)      # wooden door
STAR_Y    = color.rgb(255,240,90)    # star above door

# -------------------------
# Brick Wall Generator
# -------------------------
def brick_wall(parent,w,h,d,brick_w=6,brick_h=3):
    rows=int(h/brick_h)
    cols=int(w/brick_w)
    for row in range(rows):
        offset=(brick_w/2) if row%2 else 0
        for col in range(cols):
            x=-w/2+col*brick_w+brick_w/2+offset
            y=row*brick_h+brick_h/2
            tint=random.uniform(-0.08,0.08)
            c=color.rgb(
                max(0,min(255,int(200+40*tint))),
                max(0,min(255,int(140+25*tint))),
                max(0,min(255,int(120+20*tint)))
            )
            Entity(parent=parent,model='cube',
                   scale=(brick_w,brick_h,d),
                   position=(x,y,0),color=c)

# -------------------------
# Castle Builder
# -------------------------
def build_castle():
    root = Entity()

    # --- Main Keep (600x400 base) ---
    brick_wall(root,w=600,h=80,d=400)

    # Roof slab across the keep
    Entity(parent=root,model='cube',color=ROOF_RED,
           scale=(610,4,410),position=(0,82,0))

    # --- Entrance ---
    Entity(parent=root,model='cube',color=WALLS,
           scale=(200,60,60),position=(0,30,-220))
    Entity(parent=root,model='cube',color=DOOR_WOOD,
           scale=(80,40,10),position=(0,20,-250))
    Text(text='★',world=True,position=(0,70,-240),
         scale=10,color=STAR_Y,always_on_top=True)

    # --- Central Tower ---
    tower = Entity(parent=root,model='cylinder',color=WALLS,
                   scale=(120,200,120),position=(0,180,0))
    Entity(parent=root,model=CONE_MODEL,color=ROOF_RED,
           scale=(180,100,180),position=(0,330,0))

    # --- Four Corner Towers ---
    corner_positions = [
        Vec3(-300,40,-200), Vec3(300,40,-200),
        Vec3(-300,40, 200), Vec3(300,40, 200)
    ]
    for p in corner_positions:
        t = Entity(parent=root,model='cylinder',color=WALLS,
                   scale=(100,160,100),position=p)
        Entity(parent=root,model=CONE_MODEL,color=ROOF_RED,
               scale=(140,80,140),position=p+Vec3(0,120,0))

    # Add shadows
    for e in root.children:
        set_cast_shadows(e,True)

    return root

castle = build_castle()

# -------------------------
# Camera Setup
# -------------------------
camera.position = (0,200,-800)
camera.look_at(castle.position+Vec3(0,40,0))

guided_orbit = False
def orbit_camera(target,radius=900,height=200,speed=6):
    t = pytime.time()*(speed/20)
    camera.position = Vec3(sin(t)*radius,height,cos(t)*radius-300)
    camera.look_at(target.position+Vec3(0,40,0))

def input(key):
    global guided_orbit
    if key=='g': guided_orbit=not guided_orbit

def update():
    if guided_orbit:
        orbit_camera(castle)

app.run()
