# output.py
# Minecraft 1.0-ish in one file (Ursina) — "files = off", ~60 FPS target.
# No external textures or assets required.
# pip install ursina
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math, random
random.seed(1337)

# -------------------------
# Tunables & World Settings
# -------------------------
SEED = 12345                      # world seed (change for a new world)
CHUNK_SIZE = 16                   # blocks per chunk edge
VIEW_DISTANCE = 2                 # chunks in each direction (2 => 5x5 chunks)
SEA_LEVEL = 12
BASE_HEIGHT = 16                  # average ground height
HEIGHT_AMPLITUDE = 18             # terrain variance
TARGET_FPS = 60
REACH = 5                         # block reach distance (ray length)
MAX_WORLD_Y = 96                  # vertical safety cap (for placements)

# -------------------------
# Block Types (no textures)
# -------------------------
AIR, GRASS, DIRT, STONE, SAND, WOOD, LEAVES, WATER = range(8)
BLOCK_NAME = {
    GRASS: 'Grass', DIRT: 'Dirt', STONE: 'Stone',
    WOOD: 'Wood', LEAVES: 'Leaves', SAND: 'Sand', WATER: 'Water'
}
PALETTE = [GRASS, DIRT, STONE, WOOD, LEAVES, SAND]  # placeable via hotbar

def block_color(bt:int):
    # Simple, clean colors that read well with no texture files.
    if bt == GRASS:  return color.rgb(106, 170, 80)
    if bt == DIRT:   return color.rgb(134, 96, 67)
    if bt == STONE:  return color.rgb(125, 125, 125)
    if bt == SAND:   return color.rgb(218, 210, 158)
    if bt == WOOD:   return color.rgb(102, 81, 60)
    if bt == LEAVES: return Color(0.30, 0.55, 0.25, 0.95)
    if bt == WATER:  return Color(0.20, 0.35, 0.95, 0.65)
    return color.white

# ---------------
# App & Rendering
# ---------------
app = Ursina(title='Cats’ Personal OS 1.0 — UrsinaCraft (single file)')
window.vsync = True
window.fps_counter.enabled = True
window.exit_button.enabled = False
if hasattr(application, 'target_fps'):
    application.target_fps = TARGET_FPS

# Minimal “sky” (no textures)
sky = Entity(model='sphere', scale=600, double_sided=True, color=color.rgb(135, 206, 235))
ambient = AmbientLight(color=color.rgba(180, 180, 200, 255))
sun = DirectionalLight(shadows=False)
sun.look_at(Vec3(1, -1, 0.3))

# ------------------------
# Smooth Value Noise (2D)
# ------------------------
def _fract(x): return x - math.floor(x)
def _hash(ix:int, iz:int, seed:int=SEED):
    # Deterministic hash -> [0,1)
    return _fract(math.sin(ix * 12.9898 + iz * 78.233 + seed*0.1) * 43758.5453)
def _fade(t): return t*t*t*(t*(t*6 - 15) + 10)
def value_noise(x:float, z:float, seed:int=SEED):
    x0, z0 = math.floor(x), math.floor(z)
    xf, zf = x - x0, z - z0
    u, v = _fade(xf), _fade(zf)
    v00 = _hash(x0,   z0,   seed)
    v10 = _hash(x0+1, z0,   seed)
    v01 = _hash(x0,   z0+1, seed)
    v11 = _hash(x0+1, z0+1, seed)
    ix0 = lerp(v00, v10, u)
    ix1 = lerp(v01, v11, u)
    return lerp(ix0, ix1, v)
def fbm(x:float, z:float, octaves=5, lacunarity=2.0, gain=0.5):
    amp, freq = 1.0, 1.0
    total, norm = 0.0, 0.0
    for _ in range(octaves):
        n = value_noise(x*freq, z*freq) * 2.0 - 1.0  # [-1,1]
        total += n * amp
        norm  += amp
        amp   *= gain
        freq  *= lacunarity
    return total / max(1e-6, norm)  # [-1,1]

height_cache = {}
def height_at(x:int, z:int) -> int:
    key = (x, z)
    h = height_cache.get(key)
    if h is None:
        n = fbm(x/48.0, z/48.0, octaves=5, lacunarity=2.1, gain=0.52)
        h = int(BASE_HEIGHT + HEIGHT_AMPLITUDE * n)
        if h < 1: h = 1
        height_cache[key] = h
    return h

def default_block_at(x:int, y:int, z:int) -> int:
    """Return the procedural block type if the player hasn't modified this pos."""
    h = height_at(x, z)
    if y > max(h, SEA_LEVEL): return AIR
    if y <= h:
        d = h - y
        if d == 0:
            return GRASS if h >= SEA_LEVEL else SAND
        elif d <= 3:
            return DIRT if h >= SEA_LEVEL else SAND
        else:
            return STONE
    # y between (h, SEA_LEVEL]
    return WATER

# ------------------------
# Voxels & World Chunks
# ------------------------
class Voxel(Entity):
    __slots__ = ('btype',)
    def __init__(self, pos:Vec3, btype:int):
        super().__init__(
            parent=scene, position=pos,
            model='cube', origin_y=0.5, scale=1,
            color=block_color(btype), collider='box'
        )
        self.btype = btype

class World:
    def __init__(self):
        self.chunks = {}             # (cx,cz) -> set of positions (x,y,z) in this chunk
        self.entities = {}           # (x,y,z) -> Voxel
        self.mods = {}               # (x,y,z) -> block type (player changes), 0 = air
        self._spawn_initial_area()

    def _spawn_initial_area(self):
        # Preload around origin to avoid falling
        for cx in range(-1, 2):
            for cz in range(-1, 2):
                self.generate_chunk(cx, cz)

    def chunk_key(self, x:int, z:int):
        return (math.floor(x/CHUNK_SIZE), math.floor(z/CHUNK_SIZE))

    def ensure_active_chunks(self, player_x:float, player_z:float):
        pcx, pcz = self.chunk_key(player_x, player_z)
        needed = set()
        for dz in range(-VIEW_DISTANCE, VIEW_DISTANCE+1):
            for dx in range(-VIEW_DISTANCE, VIEW_DISTANCE+1):
                needed.add((pcx+dx, pcz+dz))
        # Generate missing
        for ck in needed:
            if ck not in self.chunks:
                self.generate_chunk(*ck)
        # Unload far chunks
        to_unload = [ck for ck in self.chunks.keys() if ck not in needed]
        for ck in to_unload:
            self.unload_chunk(*ck)

    def generate_chunk(self, cx:int, cz:int):
        if (cx, cz) in self.chunks:
            return
        created = set()
        xs = range(cx*CHUNK_SIZE, (cx+1)*CHUNK_SIZE)
        zs = range(cz*CHUNK_SIZE, (cz+1)*CHUNK_SIZE)

        for x in xs:
            for z in zs:
                h = height_at(x, z)

                # Top block
                top_bt = default_block_at(x, h, z)
                self._spawn_block((x, h, z), top_bt, created)

                # Vertical faces where neighbors are lower (cheap "shell" meshing)
                for dx, dz in ((1,0),(-1,0),(0,1),(0,-1)):
                    hn = height_at(x+dx, z+dz)
                    if hn < h:
                        for y in range(hn+1, h+1):
                            bt = default_block_at(x, y, z)
                            self._spawn_block((x, y, z), bt, created)

                # Shallow water surface
                if h < SEA_LEVEL:
                    self._spawn_block((x, SEA_LEVEL, z), WATER, created)

        self.chunks[(cx, cz)] = created

    def unload_chunk(self, cx:int, cz:int):
        pos_set = self.chunks.pop((cx, cz), None)
        if not pos_set: return
        for pos in pos_set:
            ent = self.entities.pop(pos, None)
            if ent: destroy(ent)

    def _spawn_block(self, pos_tuple, btype, created_set):
        if btype == AIR: return
        if pos_tuple in self.entities: return
        if pos_tuple in self.mods and self.mods[pos_tuple] == AIR:  # player removed here
            return
        ent = Voxel(Vec3(*pos_tuple), btype)
        self.entities[pos_tuple] = ent
        created_set.add(pos_tuple)

    def get_block(self, pos_tuple):
        if pos_tuple in self.mods:
            return self.mods[pos_tuple]
        # default
        x,y,z = pos_tuple
        return default_block_at(x,y,z)

    def break_block(self, pos_tuple):
        ent = self.entities.pop(pos_tuple, None)
        if ent:
            destroy(ent)
        # remember removal
        self.mods[pos_tuple] = AIR
        # Optionally reveal block behind (simple reveal below if it exists and is solid)
        x,y,z = pos_tuple
        below = (x, y-1, z)
        if y-1 >= -1 and self.get_block(below) != AIR and below not in self.entities:
            # only reveal if face is exposed (there is air above it now)
            self.entities[below] = Voxel(Vec3(*below), self.get_block(below))

    def place_block(self, pos_tuple, btype):
        if btype == AIR: return
        if pos_tuple in self.entities: return
        x,y,z = pos_tuple
        if y < 0 or y > MAX_WORLD_Y: return
        self.mods[pos_tuple] = btype
        self.entities[pos_tuple] = Voxel(Vec3(*pos_tuple), btype)

world = World()

# ------------------------
# Player, UI & Input
# ------------------------
spawn_x, spawn_z = 0, 0
spawn_y = height_at(spawn_x, spawn_z) + 2
player = FirstPersonController(
    position=Vec3(spawn_x+0.5, spawn_y, spawn_z+0.5),
    speed=6, origin_y=-0.5, model='cube'
)
mouse.locked = True

# Simple crosshair & HUD
crosshair = Entity(model='quad', color=color.black, scale=0.003, parent=camera.ui, position=(0,0))
hotbar = Text('', origin=(-.5,-.5), position=(-.87,-.47), scale=0.9)
debug_txt = Text('', origin=(-.5,.5), position=(-.88,.48), enabled=False, scale=0.8)
selected_idx = 0

def update_hotbar():
    items = []
    for i, bt in enumerate(PALETTE, start=1):
        name = BLOCK_NAME.get(bt, f'#{bt}')
        if i-1 == selected_idx:
            items.append(f'[{i}:{name}]')
        else:
            items.append(f'{i}:{name}')
    hotbar.text = '  '.join(items)

update_hotbar()

# ---------------
# Day/Night Cycle
# ---------------
DAY_SECONDS = 120.0
time_accum = random.uniform(0, DAY_SECONDS)

def _update_day_night(dt):
    global time_accum
    time_accum = (time_accum + dt) % DAY_SECONDS
    t = time_accum / DAY_SECONDS            # [0,1)
    # light intensity and sky tint over time
    light = 0.35 + 0.65 * max(0.0, math.sin(t * math.tau))
    ambient.color = color.rgba(int(120+90*light), int(120+90*light), int(130+90*light), 255)
    sky.color = Color(0.35+0.45*light, 0.55+0.35*light, 0.85*light+0.15, 1.0)
    sun.look_at(Vec3(1, -1 + 2.0*math.sin(t*math.tau), 0.3))

# ----------
# Game Loop
# ----------
def update():
    # Cap reach indicator / show hovered
    if mouse.world_point:
        pass

    # Load/unload chunks around player
    world.ensure_active_chunks(player.x, player.z)

    # Basic debug overlay
    if debug_txt.enabled:
        px, py, pz = player.position
        pcx, pcz = world.chunk_key(px, pz)
        debug_txt.text = (
            f'FPS: {int(1/max(1e-6,time.dt))}  '
            f'Pos: ({px:.1f},{py:.1f},{pz:.1f})  '
            f'Chunk: ({pcx},{pcz})  '
            f'Entities: {len(world.entities)}  '
            f'Chunks: {len(world.chunks)}'
        )

    _update_day_night(time.dt)

def input(key):
    global selected_idx
    if key == 'escape':
        mouse.locked = not mouse.locked

    # Hotbar selection
    if key in ('scroll up', 'scroll down'):
        step = 1 if key == 'scroll up' else -1
        selected_idx = (selected_idx + step) % len(PALETTE)
        update_hotbar()
    elif key in ('1','2','3','4','5','6'):
        n = int(key) - 1
        if n < len(PALETTE):
            selected_idx = n
            update_hotbar()

    if key == 'f3':
        debug_txt.enabled = not debug_txt.enabled

    # Mining / placing
    if key == 'left mouse down':
        hit = mouse.hovered_entity
        if isinstance(hit, Voxel):
            if distance(camera.world_position, hit.world_position) <= REACH:
                pos = tuple(map(int, hit.position))
                world.break_block(pos)

    if key == 'right mouse down':
        hit = mouse.hovered_entity
        if isinstance(hit, Voxel):
            if distance(camera.world_position, hit.world_position) <= REACH+0.5:
                # place onto face normal
                p = hit.position + mouse.normal
                pos = (int(round(p.x)), int(round(p.y)), int(round(p.z)))
                if pos not in world.entities:
                    world.place_block(pos, PALETTE[selected_idx])

# Start!
update_hotbar()
app.run()
