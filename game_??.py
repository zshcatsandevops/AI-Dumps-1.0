import pygame
import random
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# Initialize pygame
pygame.init()

# ---------------------------
# Core data structures (unchanged from original)
# ---------------------------

Grid = List[List[str]]

@dataclass
class EnemySpawn:
    x: int
    y: int
    kind: str = "goomba"
    patrol: Optional[Tuple[int, int]] = None

@dataclass
class LevelSpec:
    id: str
    name: str
    theme: str
    width: int = 128
    height: int = 16
    ground_y: int = 13
    chunks: List[Tuple[str, Tuple]] = field(default_factory=list)
    coins: List[Tuple[int, int]] = field(default_factory=list)
    items: List[Tuple[int, int, str]] = field(default_factory=list)
    enemies: List[EnemySpawn] = field(default_factory=list)
    player_start: Tuple[int, int] = (2, 10)
    goal_x: int = 120
    time_limit: int = 400
    par_time: int = 180
    music: str = "overworld"
    flips: bool = False
    flip_rules: Dict[str, str] = field(default_factory=dict)
    rng_seed: Optional[int] = None
    waterline: Optional[int] = None

# ---------------------------
# Chunk builder DSL (unchanged from original)
# ---------------------------

def make_grid(w: int, h: int, fill: str = " ") -> Grid:
    return [[fill for _ in range(w)] for _ in range(h)]

def render_grid(grid: Grid) -> List[str]:
    return ["".join(row) for row in grid]

def _stamp(grid: Grid, x: int, y: int, ch: str):
    h = len(grid)
    w = len(grid[0])
    if 0 <= x < w and 0 <= y < h:
        grid[y][x] = ch

def _hline(grid: Grid, x0: int, x1: int, y: int, ch: str):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        _stamp(grid, x, y, ch)

def _vline(grid: Grid, x: int, y0: int, y1: int, ch: str):
    for y in range(min(y0, y1), max(y0, y1) + 1):
        _stamp(grid, x, y, ch)

def chunk_flat(width: int) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        y = spec.ground_y
        for x in range(x0, x0 + width):
            for yy in range(y, spec.height):
                _stamp(grid, x, yy, 'X')
    return op, width

def chunk_pit(width: int, hazard: Optional[str] = None) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        if hazard:
            for x in range(x0, x0 + width):
                for yy in range(spec.ground_y + 1, spec.height):
                    _stamp(grid, x, yy, hazard)
    return op, width

def chunk_bridge(width: int) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        pit_op, _ = chunk_pit(width, '~')
        pit_op(grid, x0, spec)
        _hline(grid, x0, x0 + width - 1, spec.ground_y, '=')
    return op, width

def chunk_pipe(height_blocks: int = 4, body_width: int = 2) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    w = body_width + 2
    def op(grid: Grid, x0: int, spec: LevelSpec):
        flat_op, _ = chunk_flat(w)
        flat_op(grid, x0, spec)
        top_y = max(0, spec.ground_y - height_blocks)
        lx = x0 + 1
        rx = lx + body_width - 1
        for x in range(lx, rx + 1):
            _vline(grid, x, top_y, spec.ground_y - 1, '|')
        _hline(grid, lx - 1, rx + 1, top_y, '|')
    return op, w

def chunk_stairs_up(steps: int = 4, step_w: int = 2) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    w = steps * step_w
    def op(grid: Grid, x0: int, spec: LevelSpec):
        gy = spec.ground_y
        flat_op, _ = chunk_flat(w)
        flat_op(grid, x0, spec)
        for s in range(steps):
            height = s + 1
            x_start = x0 + s * step_w
            for x in range(x_start, x_start + step_w):
                for y in range(gy - height + 1, gy + 1):
                    _stamp(grid, x, y, 'X')
    return op, w

def chunk_stairs_down(steps: int = 4, step_w: int = 2) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    w = steps * step_w
    def op(grid: Grid, x0: int, spec: LevelSpec):
        gy = spec.ground_y
        flat_op, _ = chunk_flat(w)
        flat_op(grid, x0, spec)
        for s in range(steps):
            height = steps - s
            x_start = x0 + s * step_w
            for x in range(x_start, x_start + step_w):
                for y in range(gy - height + 1, gy + 1):
                    _stamp(grid, x, y, 'X')
    return op, w

def chunk_platforms(width: int, spans: Sequence[Tuple[int, int]]) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        flat_op, _ = chunk_flat(width)
        flat_op(grid, x0, spec)
        lanes = len(spans)
        gap = max(3, (width - 4) // max(1, lanes))
        x = x0 + 2
        for (y, plen) in spans:
            for xx in range(x, min(x + plen, x0 + width - 1)):
                _stamp(grid, xx, y, 'X')
            _stamp(grid, x + plen // 2, y + 1, 'M')
            x += gap
    return op, width

def chunk_cave_ceiling(width: int, undulate: bool = True) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        flat_op, _ = chunk_flat(width)
        flat_op(grid, x0, spec)
        for x in range(x0, x0 + width):
            top = 2 + ((x - x0) % 3 if undulate else 0)
            _hline(grid, x, x, top, 'X')
    return op, width

def chunk_airship(width: int) -> Tuple[Callable[[Grid, int, LevelSpec], None], int]:
    def op(grid: Grid, x0: int, spec: LevelSpec):
        deck_y = max(2, spec.ground_y - 3)
        for x in range(x0, x0 + width):
            _stamp(grid, x, deck_y, '=')
            if (x - x0) % 11 == 0:
                _stamp(grid, x, deck_y - 1, '^')
        for x in range(x0, x0 + width, 5):
            _vline(grid, x, deck_y + 1, min(spec.height - 1, deck_y + 3), 'X')
    return op, width

# ---------------------------
# Level building (unchanged from original)
# ---------------------------

def build_level_grid(spec: LevelSpec) -> Grid:
    grid = make_grid(spec.width, spec.height, ' ')
    x = 0
    for (kind, args) in spec.chunks:
        if kind == "flat":
            op, w = chunk_flat(*args)
        elif kind == "pit":
            op, w = chunk_pit(*args)
        elif kind == "bridge":
            op, w = chunk_bridge(*args)
        elif kind == "pipe":
            op, w = chunk_pipe(*args)
        elif kind == "stairs_up":
            op, w = chunk_stairs_up(*args)
        elif kind == "stairs_down":
            op, w = chunk_stairs_down(*args)
        elif kind == "platforms":
            op, w = chunk_platforms(*args)
        elif kind == "cave":
            op, w = chunk_cave_ceiling(*args)
        elif kind == "airship":
            op, w = chunk_airship(*args)
        else:
            raise ValueError(f"Unknown chunk kind: {kind}")
        op(grid, x, spec)
        x += w

    if x < spec.width:
        flat_op, _ = chunk_flat(spec.width - x)
        flat_op(grid, x, spec)

    if spec.waterline is not None:
        for y in range(spec.waterline, spec.height):
            for xx in range(spec.width):
                if grid[y][xx] == ' ':
                    grid[y][xx] = '~'

    for (cx, cy) in spec.coins:
        _stamp(grid, cx, cy, 'C')
    for (ix, iy, kind) in spec.items:
        _stamp(grid, ix, iy, '?' if kind != "1up" else 'B')
    for e in spec.enemies:
        _stamp(grid, e.x, e.y, 'E')

    _stamp(grid, spec.player_start[0], spec.player_start[1], 'P')
    _stamp(grid, spec.goal_x, spec.ground_y - 5, 'G')

    return grid

# ---------------------------
# World 3 Levels (unchanged from original)
# ---------------------------

def L(id, name, theme, chunks, **kw) -> LevelSpec:
    base = dict(
        id=id, name=name, theme=theme,
        width=sum({
            "flat": lambda w: w,
            "pit": lambda w, *_: w,
            "bridge": lambda w: w,
            "pipe": lambda w, *_: w,
            "stairs_up": lambda w, *_: w,
            "stairs_down": lambda w, *_: w,
            "platforms": lambda w, *_: w,
            "cave": lambda w, *_: w,
            "airship": lambda w: w
        }[k](*a) if k != "pipe" else (a[0] + 2) for (k, a) in chunks) + 32,
        height=16, ground_y=13, goal_x=0, chunks=chunks, player_start=(2, 10),
        enemies=[], coins=[], items=[]
    )
    spec = LevelSpec(**{**base, **kw})
    spec.goal_x = spec.width - 8
    return spec

WORLD3_LEVELS: List[LevelSpec] = [
    L("3-1", "Green Rise", "grass", chunks=[
        ("flat", (16,)), ("pipe", (3,)), ("flat", (12,)), ("pit", (5, ' ')),
        ("bridge", (10,)), ("flat", (18,)), ("stairs_up", (3, 3)), ("flat", (14,)), ("pipe", (4,)),
        ("flat", (24,))
    ], coins=[(10,10),(22,9),(40,9),(58,8),(76,9)], items=[(14,10,"mushroom"),(52,9,"fire")],
      enemies=[EnemySpawn(26,12,"goomba",(-3,3)), EnemySpawn(48,12,"koopa",(-4,4))],
      music="overworld", par_time=90, time_limit=300, rng_seed=301),

    L("3-2", "Pipe Valley", "grass", chunks=[
        ("flat", (12,)), ("pipe", (5,)), ("flat", (8,)), ("pipe", (6,)), ("flat", (10,)),
        ("pit", (6, ' ')), ("flat", (18,)), ("pipe", (4,)), ("flat", (28,))
    ], coins=[(18,9),(26,9),(44,8),(72,9)], items=[(32,10,"mushroom")],
      enemies=[EnemySpawn(14,12,"piranha"), EnemySpawn(28,12,"piranha"), EnemySpawn(60,12,"goomba",(-3,3))],
      music="overworld", par_time=95, time_limit=300, rng_seed=302),

    L("3-3", "Phantom Steps", "grass", chunks=[
        ("flat", (14,)), ("pit", (5,' ')), ("flat", (14,)), ("stairs_up", (4,2)),
        ("flat", (10,)), ("pit", (8,' ')), ("flat", (24,)), ("stairs_down", (4,2)), ("flat", (22,))
    ], coins=[(22,8),(38,7),(64,6)], items=[(46,9,"mushroom")],
      enemies=[EnemySpawn(36,12,"goomba",(-4,4)), EnemySpawn(68,12,"koopa",(-3,3))],
      flips=True, flip_rules={"#":" ", " ":"#"}, par_time=110, time_limit=350, rng_seed=303),

    L("3-4", "Echo Tunnel", "cave", chunks=[
        ("cave", (22, True)), ("pit", (6,' ')), ("cave", (18, True)),
        ("platforms", (20, [(8,6),(7,5)])), ("cave", (26, True)), ("flat", (12,))
    ], coins=[(10,7),(34,6),(44,7),(72,7)], items=[(28,8,"mushroom")],
      enemies=[EnemySpawn(20,12,"spiny"), EnemySpawn(46,12,"goomba",(-2,2)), EnemySpawn(62,12,"koopa",(-3,3))],
      music="underground", par_time=120, time_limit=350, rng_seed=304),

    L("3-5", "River Crossing", "grass", chunks=[
        ("flat", (10,)), ("bridge", (14,)), ("pit", (6,' ')), ("bridge", (16,)), ("flat", (10,)),
        ("pipe", (3,)), ("flat", (30,)), ("bridge", (18,)), ("flat", (18,))
    ], coins=[(14,12),(26,12),(42,12),(78,12)], items=[(36,11,"fire")],
      enemies=[EnemySpawn(24,12,"goomba",(-3,3)), EnemySpawn(54,12,"koopa",(-4,4))],
      music="overworld", par_time=105, time_limit=320, rng_seed=305, waterline=14),

    L("3-6", "Sky Gym", "grass", chunks=[
        ("flat", (12,)), ("platforms", (22, [(7,5),(6,4),(6,6)])), ("pit", (6,' ')),
        ("platforms", (24, [(6,5),(8,5)])), ("flat", (20,)), ("stairs_up", (3,3)), ("flat", (18,))
    ], coins=[(20,8),(34,7),(40,8),(58,7)], items=[(28,9,"mushroom")],
      enemies=[EnemySpawn(38,12,"goomba",(-3,3)), EnemySpawn(64,12,"spiny")],
      music="athletic", par_time=115, time_limit=340, rng_seed=306),

    L("3-7", "Leafway", "forest", chunks=[
        ("flat", (10,)), ("platforms", (20, [(6,7),(7,6)])), ("pit", (8,' ')),
        ("platforms", (24, [(8,6),(7,6)])), ("flat", (12,)), ("pipe", (4,)), ("flat", (26,))
    ], coins=[(16,7),(36,6),(68,9)], items=[(26,9,"1up")],
      enemies=[EnemySpawn(22,12,"koopa",(-3,3)), EnemySpawn(50,12,"goomba",(-2,2))],
      music="forest", par_time=120, time_limit=340, rng_seed=307),

    L("3-8", "Grotto Run", "cave", chunks=[
        ("cave", (18, True)), ("platforms", (20, [(7,5),(6,5)])), ("pit", (6,' ')),
        ("cave", (22, True)), ("stairs_down", (4,2)), ("cave", (24, True))
    ], coins=[(12,7),(28,6),(48,7),(70,6)], items=[(36,8,"mushroom")],
      enemies=[EnemySpawn(24,12,"spiny"), EnemySpawn(60,12,"koopa",(-2,2))],
      music="underground", par_time=120, time_limit=360, rng_seed=308),

    L("3-9", "Moonlit Sprint", "grass", chunks=[
        ("flat", (16,)), ("pit", (5,' ')), ("flat", (20,)), ("pit", (8,' ')),
        ("flat", (18,)), ("pipe", (3,)), ("flat", (26,)), ("pit", (6,' ')), ("flat", (24,))
    ], coins=[(20,9),(46,9),(68,9),(96,9)], items=[(34,10,"fire")],
      enemies=[EnemySpawn(26,12,"goomba",(-3,3)), EnemySpawn(54,12,"goomba",(-3,3)), EnemySpawn(88,12,"koopa",(-4,4))],
      music="night", par_time=85, time_limit=260, rng_seed=309),

    L("3-10", "Dune Path", "desert", chunks=[
        ("flat", (18,)), ("pit", (6,' ')), ("flat", (16,)), ("stairs_up", (4,2)),
        ("pit", (8,' ')), ("flat", (20,)), ("pipe", (5,)), ("flat", (26,))
    ], coins=[(22,9),(40,8),(66,8),(92,9)], items=[(46,10,"mushroom")],
      enemies=[EnemySpawn(34,12,"spiny"), EnemySpawn(72,12,"goomba",(-3,3))],
      music="desert", par_time=110, time_limit=320, rng_seed=310),

    L("3-11", "Frostbite Falls", "ice", chunks=[
        ("flat", (12,)), ("bridge", (16,)), ("flat", (10,)), ("stairs_down", (4,2)),
        ("bridge", (18,)), ("flat", (22,)), ("pipe", (4,)), ("flat", (22,))
    ], coins=[(18,12),(40,12),(66,12)], items=[(30,11,"mushroom")],
      enemies=[EnemySpawn(26,12,"goomba",(-3,3)), EnemySpawn(58,12,"koopa",(-4,4))],
      music="ice", par_time=115, time_limit=340, rng_seed=311, waterline=14),

    L("3-12", "Haunted Halls", "ghost", chunks=[
        ("flat", (14,)), ("pit", (6,' ')), ("platforms", (24, [(6,6),(6,5)])),
        ("flat", (10,)), ("stairs_up", (3,3)), ("flat", (16,)), ("pit", (6,' ')), ("flat", (20,))
    ], coins=[(18,8),(42,7),(64,8)], items=[(34,9,"fire")],
      enemies=[EnemySpawn(30,8,"boo"), EnemySpawn(54,8,"boo")],
      flips=True, flip_rules={"#":" ", " ":"#"}, music="ghost", par_time=130, time_limit=360, rng_seed=312),

    L("3-13", "Sky Armada", "airship", chunks=[
        ("airship", (22,)), ("pit", (6,' ')), ("airship", (24,)),
        ("pit", (6,' ')), ("airship", (26,)), ("flat", (12,))
    ], coins=[(16,9),(44,9),(72,9)], items=[(32,9,"mushroom")],
      enemies=[EnemySpawn(24,9,"goomba",(-3,3)), EnemySpawn(52,9,"spiny"), EnemySpawn(78,9,"koopa",(-3,3))],
      music="airship", par_time=120, time_limit=360, rng_seed=313),

    L("3-14", "Magikoopa Keep", "fortress", chunks=[
        ("flat", (16,)), ("cave", (18, False)), ("stairs_up", (4,2)),
        ("pit", (6,' ')), ("platforms", (20, [(7,5),(7,6)])), ("flat", (30,))
    ], coins=[(20,8),(42,7),(66,8)], items=[(34,9,"mushroom")],
      enemies=[EnemySpawn(26,12,"dry_bones"), EnemySpawn(54,12,"thwomp")],
      music="fortress", par_time=125, time_limit=360, rng_seed=314),

    L("3-15", "Kamek's Workshop", "fortress", chunks=[
        ("flat", (24,)), ("cave", (18, False)), ("flat", (24,)), ("pit", (6,' ')), ("flat", (40,))
    ], coins=[(16,8),(44,7)], items=[(28,9,"fire")],
      enemies=[EnemySpawn(72,8,"magikoopa")],
      music="boss", par_time=999, time_limit=400, rng_seed=315)
]

# ---------------------------
# Pygame 2D Visualization
# ---------------------------

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480
TILE_SIZE = 32

# Colors
COLORS = {
    ' ': (0, 0, 0),           # Background (black)
    'X': (150, 75, 0),       # Ground (brown)
    'B': (200, 0, 0),        # Brick (red)
    '?': (255, 215, 0),      # Question block (gold)
    'C': (255, 255, 0),      # Coin (yellow)
    'M': (100, 100, 100),    # Moving platform (gray)
    '|': (0, 128, 0),        # Pipe (green)
    '=': (139, 69, 19),      # Bridge (dark brown)
    '~': (0, 0, 255),        # Water (blue)
    '^': (255, 0, 0),        # Spike (red)
    'G': (0, 255, 0),        # Goal (green)
    'P': (255, 0, 0),        # Player (red)
    'E': (255, 165, 0),      # Enemy (orange)
    'K': (128, 0, 128),      # Kamek boss (purple)
}

def draw_level(screen, grid, camera_x):
    screen.fill(COLORS[' '])
    
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            screen_x = x * TILE_SIZE - camera_x
            screen_y = y * TILE_SIZE
            
            # Only draw tiles that are visible on screen
            if -TILE_SIZE <= screen_x < SCREEN_WIDTH:
                if tile in COLORS:
                    pygame.draw.rect(screen, COLORS[tile], 
                                    (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
                    
                    # Add some visual details for certain tiles
                    if tile == 'X':  # Ground texture
                        pygame.draw.rect(screen, (100, 50, 0), 
                                        (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 1)
                    elif tile == 'B':  # Brick pattern
                        pygame.draw.line(screen, (150, 0, 0), 
                                        (screen_x, screen_y), 
                                        (screen_x + TILE_SIZE, screen_y + TILE_SIZE), 2)
                        pygame.draw.line(screen, (150, 0, 0), 
                                        (screen_x + TILE_SIZE, screen_y), 
                                        (screen_x, screen_y + TILE_SIZE), 2)
                    elif tile == '?':  # Question mark
                        font = pygame.font.SysFont(None, 24)
                        text = font.render("?", True, (0, 0, 0))
                        screen.blit(text, (screen_x + 10, screen_y + 5))
                    elif tile == 'C':  # Coin circle
                        pygame.draw.circle(screen, (255, 255, 0), 
                                        (screen_x + TILE_SIZE//2, screen_y + TILE_SIZE//2), 
                                        TILE_SIZE//3)
                    elif tile == '~':  # Water waves
                        for i in range(0, TILE_SIZE, 8):
                            pygame.draw.arc(screen, (0, 0, 200), 
                                        [screen_x, screen_y + i//2, TILE_SIZE, 10], 
                                        0, 3.14, 1)
    
    # Draw level info
    font = pygame.font.SysFont(None, 24)
    info_text = f"Level: {current_level+1}/15 - {WORLD3_LEVELS[current_level].name}"
    text = font.render(info_text, True, (255, 255, 255))
    screen.blit(text, (10, 10))
    
    pygame.display.flip()

def main():
    global current_level
    current_level = 0
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("World 3 Level Viewer")
    clock = pygame.time.Clock()
    
    # Build the first level
    grid = build_level_grid(WORLD3_LEVELS[current_level])
    level_width = len(grid[0]) * TILE_SIZE
    
    camera_x = 0
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    camera_x = min(camera_x + 100, level_width - SCREEN_WIDTH)
                elif event.key == pygame.K_LEFT:
                    camera_x = max(camera_x - 100, 0)
                elif event.key == pygame.K_n:
                    # Next level
                    current_level = (current_level + 1) % len(WORLD3_LEVELS)
                    grid = build_level_grid(WORLD3_LEVELS[current_level])
                    level_width = len(grid[0]) * TILE_SIZE
                    camera_x = 0
                elif event.key == pygame.K_p:
                    # Previous level
                    current_level = (current_level - 1) % len(WORLD3_LEVELS)
                    grid = build_level_grid(WORLD3_LEVELS[current_level])
                    level_width = len(grid[0]) * TILE_SIZE
                    camera_x = 0
        
        draw_level(screen, grid, camera_x)
        clock.tick(30)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
