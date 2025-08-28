# output.py — Single-file, asset-free "Mario-like" platformer engine (32 levels, 60 FPS)
# ----------------------------------------------------------------------------------------
# NOTE ON COPYRIGHT / TRADEMARKS
# This file provides an original platformer engine inspired by classic side-scrollers.
# It does NOT reproduce Nintendo's original Super Mario Bros. level data, graphics,
# characters, or music. All tiles, sprites, and levels here are synthetic and drawn as
# simple shapes (rectangles/circles). Level layouts are generated procedurally with a
# deterministic seed so you get 32 unique, completable courses without any external files.
#
# This version has been adjusted to more closely match the mechanics and feel of the NES
# original while maintaining legal distinction from Nintendo's intellectual property.
#
# Quick start:
#   pip install pygame
#   python output.py
#
# Controls:
#   Left/Right .......... Move
#   Shift (hold) ........ Run
#   Z / Space / Up ...... Jump
#   R ................... Restart level
#   Enter ............... Start / continue on title or clear screens
#   Esc ................. Quit
#
# Tips:
# - The engine targets 60 FPS. It uses dt-based physics for consistent movement.
# - All art is generated with code; no images or sounds required.
# - Levels are deterministic per index; feel free to change the generator for different vibes.
#
# Enjoy!
import os
import sys
import math
import random
import pygame

# Hide the default pygame welcome text
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# ----------------------------------------------------------------------------------------
# Config - Adjusted to match NES SMB1 more closely
# ----------------------------------------------------------------------------------------
FPS                 = 60
SCREEN_W, SCREEN_H  = 800, 480
TILE                = 16
GRAVITY             = 1800.0  # Reduced for more floaty jumps like SMB1
WALK_SPEED          = 120.0   # Slower base speed
RUN_SPEED           = 200.0   # Faster run speed
ACCEL_FACTOR        = 0.15    # Slower acceleration for more momentum
JUMP_SPEED          = 520.0   # Higher jump for SMB1 feel
COYOTE_TIME         = 0.12    # Slightly longer coyote time
JUMP_BUFFER         = 0.10    # Jump buffer time
TERMINAL_VY         = 1800.0  # Lower terminal velocity
MAX_LEVELS          = 32
LEVEL_HEIGHT_TILES  = SCREEN_H // TILE  # 30 at 480p with TILE=16

# Colors - Adjusted to match NES palette more closely
COLORS = {
    "sky":          (92, 148, 252),   # NES-like blue sky
    "ground":       (150, 80, 60),    # Brown ground
    "brick":        (180, 80, 60),    # Slightly redder brick
    "pipe":         (0, 160, 0),      # Green pipe
    "question":     (252, 188, 0),    # Yellow question block
    "coin":         (252, 252, 0),    # Bright yellow coin
    "flag":         (252, 0, 0),      # Red flag pole
    "flag_banner":  (252, 0, 0),      # Red flag banner
    "player":       (252, 0, 0),      # Red player (like Mario's clothes)
    "enemy":        (100, 100, 100),  # Gray enemy (like Goomba)
    "platform":     (180, 180, 180),  # Gray platform
    "hud":          (252, 252, 252),  # White HUD text
    "shadow":       (0, 0, 0),        # Black shadow
}

# Tiles:
# ' ' : empty
# 'X' : ground/brick solid
# '|' : pipe (solid)
# '?' : question block (solid; releases coin or boost score on head bump)
# 'o' : coin (collect)
# '=' : platform (solid)
# 'f' : flag (level end)
# 's' : player spawn (not solid at runtime; resolves to empty)
SOLID_TILES = {'X', '|', '?', '=',}

# ----------------------------------------------------------------------------------------
# Utility
# ----------------------------------------------------------------------------------------
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def world_stage(idx):
    # idx 0..31 -> (world 1..8, stage 1..4)
    return idx // 4 + 1, idx % 4 + 1

# ----------------------------------------------------------------------------------------
# Level generation - Adjusted to create more SMB1-like levels
# ----------------------------------------------------------------------------------------
class Level:
    def __init__(self, index):
        self.index = index
        self.rng = random.Random(12345 + index * 777)
        self.height = LEVEL_HEIGHT_TILES
        # Wider later levels; keep in reasonable bounds for performance
        base_w = 160 + (index % 4) * 10 + (index // 4) * 8
        jitter = self.rng.randint(-5, 8)
        self.width = clamp(base_w + jitter, 150, 260)

        # 2D grid of chars [y][x]
        self.grid = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        self.enemies = []   # list of (x_px, y_px)
        self.spawn = (TILE * 2, TILE * 2)
        self.flag_x = (self.width - 6) * TILE
        self._generate()

    def in_bounds(self, tx, ty):
        return 0 <= tx < self.width and 0 <= ty < self.height

    def get(self, tx, ty):
        if not self.in_bounds(tx, ty):
            return 'X' if ty >= self.height else ' '  # below map is "solid floor" illusion? Actually emulate void.
        return self.grid[ty][tx]

    def set(self, tx, ty, v):
        if self.in_bounds(tx, ty):
            self.grid[ty][tx] = v

    def is_solid(self, ch):
        return ch in SOLID_TILES

    def _ground_line(self):
        # Base ground line; varies slowly per x
        base = self.height - 4 - self.rng.randint(0, 1)
        return base

    def _place_ground_strip(self, x0, x1, ground_y):
        for x in range(x0, x1):
            for y in range(ground_y, self.height):
                self.set(x, y, 'X')

    def _make_safe_start(self, ground_y):
        # Safe start region [0..24)
        safe_end = 26
        self._place_ground_strip(0, min(safe_end, self.width), ground_y)
        # Small welcome platform
        for x in range(6, 10):
            self.set(x, ground_y - 3, '=')
        # Spawn
        self.spawn = (TILE * 3, (ground_y - 2) * TILE)
        self.set(3, ground_y - 1, 's')

    def _carve_gap(self, x, length, ground_y):
        length = clamp(length, 1, 5)
        for gx in range(x, min(x + length, self.width)):
            for y in range(ground_y, self.height):
                self.set(gx, y, ' ')  # pit

    def _pipe(self, x, ground_y, height_tiles=3, width_tiles=2):
        # Simple 2-wide pipe columns
        for dx in range(width_tiles):
            for dy in range(height_tiles):
                self.set(x + dx, ground_y - 1 - dy, '|')  # top to bottom
        # Fill below with ground
        for dx in range(width_tiles):
            for y in range(ground_y, self.height):
                self.set(x + dx, y, 'X')

    def _platform(self, x, y, length):
        for i in range(length):
            if self.in_bounds(x + i, y):
                self.set(x + i, y, '=')

    def _question_block(self, x, y):
        self.set(x, y, '?')

    def _coin_cluster(self, x, y, n, arc=False):
        for i in range(n):
            yy = y
            if arc:
                # small sine arc
                yy = y - int(math.sin(i / max(1, n - 1) * math.pi) * 2)
            if self.in_bounds(x + i, yy):
                self.set(x + i, yy, 'o')

    def _maybe_enemy(self, x, ground_y):
        # Place enemy on ground if air above
        if self.get(x, ground_y - 1) == ' ' and self.get(x, ground_y) == 'X':
            self.enemies.append(((x * TILE) + 0.5 * TILE, (ground_y - 2) * TILE))

    def _flag(self, ground_y):
        fx = self.width - 6
        fy = ground_y - 7
        fy = clamp(fy, 6, self.height - 8)
        self.set(fx, fy, 'f')  # the flag tile (we draw pole across multiple tiles)
        # Ensure solid ground to finish
        self._place_ground_strip(self.width - 12, self.width, ground_y)

    def _generate(self):
        # Generate a coherent course by piecing segments and always ensuring a path.
        ground_y = self._ground_line()
        # Safe start area
        self._make_safe_start(ground_y)

        x = 26
        while x < self.width - 14:
            choice = self.rng.random()
            # Probability mix evolves with index for variety
            pit_chance = clamp(0.05 + 0.01 * (self.index // 4), 0.05, 0.16)
            pipe_chance = clamp(0.10 + 0.02 * (self.index % 4), 0.10, 0.22)
            platform_chance = 0.22
            question_chance = 0.16
            coin_chance = 0.30
            enemy_chance = 0.22

            if choice < pit_chance and x > 30:
                # Gap (ensure not too long and not near end)
                gap_len = self.rng.randint(1, 4)
                if x + gap_len < self.width - 24:
                    self._carve_gap(x, gap_len, ground_y)
                    x += gap_len + self.rng.randint(2, 4)
                    continue

            if choice < pit_chance + pipe_chance:
                # Pipe
                h = self.rng.randint(2, 4)
                w = 2
                self._pipe(x, ground_y, height_tiles=h, width_tiles=w)
                # Coins above pipe
                if self.rng.random() < 0.5:
                    self._coin_cluster(x - 1, ground_y - h - 2, 4, arc=True)
                x += w + self.rng.randint(2, 5)
                if self.rng.random() < enemy_chance:
                    self._maybe_enemy(x + 1, ground_y)
                continue

            if choice < pit_chance + pipe_chance + platform_chance:
                # Platform segment
                plat_y = ground_y - self.rng.randint(3, 6)
                length = self.rng.randint(4, 10)
                self._platform(x, plat_y, length)
                if self.rng.random() < coin_chance:
                    self._coin_cluster(x, plat_y - 2, self.rng.randint(3, 7), arc=True)
                if self.rng.random() < question_chance:
                    self._question_block(x + length // 2, plat_y - 2)
                # Ensure ground under platform for safety
                self._place_ground_strip(x - 2, x + length + 2, ground_y)
                if self.rng.random() < enemy_chance:
                    self._maybe_enemy(x + length // 2, ground_y)
                x += length + self.rng.randint(4, 8)
                continue

            # Flat or tiny hills
            step = self.rng.randint(4, 10)
            # Chance to raise/lower ground a bit (keeping stable)
            if self.rng.random() < 0.30:
                delta = self.rng.choice([-1, 0, 1])
                ground_y = clamp(ground_y + delta, self.height - 7, self.height - 4)
            self._place_ground_strip(x, x + step, ground_y)

            # Sprinkle question blocks, coins, enemies
            if self.rng.random() < question_chance:
                qx = x + self.rng.randint(1, step - 1)
                qy = ground_y - self.rng.randint(3, 5)
                self._question_block(qx, qy)
            if self.rng.random() < coin_chance:
                cx = x + self.rng.randint(1, step - 2)
                cy = ground_y - self.rng.randint(3, 6)
                self._coin_cluster(cx, cy, self.rng.randint(3, 7), arc=self.rng.random() < 0.6)
            if self.rng.random() < enemy_chance:
                ex = x + self.rng.randint(1, step - 1)
                self._maybe_enemy(ex, ground_y)

            x += step

        # Final approach + flag
        self._place_ground_strip(self.width - 24, self.width, ground_y)
        self._flag(ground_y)

        # Clear any 's' tile to empty at runtime
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 's':
                    self.grid[y][x] = ' '

    # Tile queries around rectangles for collision
    def solid_rects_near(self, rect):
        # Iterate tile coords overlapping rect
        tx0 = max(0, rect.left // TILE - 1)
        ty0 = max(0, rect.top // TILE - 1)
        tx1 = min(self.width - 1, rect.right // TILE + 1)
        ty1 = min(self.height - 1, rect.bottom // TILE + 1)
        out = []
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                ch = self.grid[ty][tx]
                if ch in SOLID_TILES:
                    out.append((pygame.Rect(tx * TILE, ty * TILE, TILE, TILE), ch, tx, ty))
        return out

    def collect_coins_in_rect(self, rect):
        coins = 0
        tx0 = max(0, rect.left // TILE)
        ty0 = max(0, rect.top // TILE)
        tx1 = min(self.width - 1, rect.right // TILE)
        ty1 = min(self.height - 1, rect.bottom // TILE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                if self.grid[ty][tx] == 'o':
                    self.grid[ty][tx] = ' '
                    coins += 1
        return coins

    def bump_block_at(self, tx, ty):
        # Called when player's head hits a block from below
        if not self.in_bounds(tx, ty):
            return 0, 0  # score, coins
        ch = self.grid[ty][tx]
        score = 0
        coins = 0
        if ch == '?':
            # Convert to brick and release either coin(s) or points
            self.grid[ty][tx] = 'X'
            if (self.index + tx + ty) % 3 == 0:
                # burst of coins
                coins = 3
            else:
                coins = 1
            score = 100 * coins
        elif ch == 'X':
            # Solid brick -> small score for bump
            score = 10
        elif ch == '=':
            score = 10
        return score, coins

# ----------------------------------------------------------------------------------------
# Camera
# ----------------------------------------------------------------------------------------
class Camera:
    def __init__(self):
        self.x = 0.0

    def update(self, target_rect, level):
        # Center toward player but clamp
        target_x = target_rect.centerx - SCREEN_W * 0.4
        # Only scroll forward (classic) unless player goes back near left edge
        self.x += (target_x - self.x) * 0.12
        self.x = clamp(self.x, 0, level.width * TILE - SCREEN_W)

    def apply(self, rect):
        return pygame.Rect(rect.x - int(self.x), rect.y, rect.width, rect.height)

# ----------------------------------------------------------------------------------------
# Entities - Adjusted for SMB1 feel
# ----------------------------------------------------------------------------------------
class Walker:
    WIDTH = 14
    HEIGHT = 14
    SPEED = 50.0

    def __init__(self, x, y, dir_left=True):
        self.rect = pygame.Rect(int(x), int(y), self.WIDTH, self.HEIGHT)
        self.vx = -self.SPEED if dir_left else self.SPEED
        self.vy = 0.0
        self.alive = True

    def update(self, dt, level):
        if not self.alive:
            return
        self.vy = clamp(self.vy + GRAVITY * dt, -TERMINAL_VY, TERMINAL_VY)

        # Horizontal
        self.rect.x += int(self.vx * dt)
        for solid, ch, tx, ty in level.solid_rects_near(self.rect):
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                    self.vx = -abs(self.vx)
                else:
                    self.rect.left = solid.right
                    self.vx = abs(self.vx)

        # Edge turn: if no ground ahead, turn
        ahead_x = self.rect.centerx + (self.rect.width // 2 + 1) * (1 if self.vx > 0 else -1)
        foot_y = self.rect.bottom + 1
        tx = ahead_x // TILE
        ty = foot_y // TILE
        if not level.in_bounds(tx, ty) or level.get(tx, ty) not in SOLID_TILES:
            self.vx *= -1

        # Vertical
        self.rect.y += int(self.vy * dt)
        on_ground = False
        for solid, ch, tx, ty in level.solid_rects_near(self.rect):
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    self.vy = 0.0
                    on_ground = True
                elif self.vy < 0:
                    self.rect.top = solid.bottom
                    self.vy = 0.0

        # Clamp to below map -> die
        if self.rect.top > level.height * TILE + 200:
            self.alive = False

    def draw(self, surf, cam):
        if not self.alive:
            return
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, COLORS["enemy"], r)

class Player:
    WIDTH = 12
    HEIGHT = 16

    def __init__(self, x, y):
        self.rect = pygame.Rect(int(x), int(y), self.WIDTH, self.HEIGHT)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        self.facing = 1
        self.jump_released = True  # For variable jump height

    def want_jump(self):
        self.jump_buffer = JUMP_BUFFER

    def update(self, dt, level, keys):
        # Horizontal input
        run = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        target = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            target -= RUN_SPEED if run else WALK_SPEED
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            target += RUN_SPEED if run else WALK_SPEED
            self.facing = 1
        self.vx += (target - self.vx) * ACCEL_FACTOR

        # Variable jump height (like SMB1)
        jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_z] or keys[pygame.K_UP]
        if not jump_pressed:
            self.jump_released = True
        elif self.jump_released and self.vy < 0:
            # Reduce upward velocity when jump is released
            self.vy *= 0.5
            self.jump_released = False

        # Vertical physics
        self.vy = clamp(self.vy + GRAVITY * dt, -TERMINAL_VY, TERMINAL_VY)

        # Jump consume (buffer + coyote)
        if self.jump_buffer > 0:
            if self.on_ground or self.coyote_timer > 0:
                self.vy = -JUMP_SPEED
                self.on_ground = False
                self.coyote_timer = 0.0
                self.jump_buffer = 0.0
                self.jump_released = False
        self.jump_buffer = max(0.0, self.jump_buffer - dt)

        # Move X
        old_rect = self.rect.copy()
        self.rect.x += int(self.vx * dt)
        for solid, ch, tx, ty in level.solid_rects_near(self.rect):
            if self.rect.colliderect(solid):
                if self.vx > 0:
                    self.rect.right = solid.left
                elif self.vx < 0:
                    self.rect.left = solid.right
                self.vx = 0.0

        # Move Y
        prev_vy = self.vy
        self.rect.y += int(self.vy * dt)
        hit_head = False
        hit_tx_ty = None
        self.on_ground = False
        for solid, ch, tx, ty in level.solid_rects_near(self.rect):
            if self.rect.colliderect(solid):
                if self.vy > 0:
                    self.rect.bottom = solid.top
                    self.vy = 0.0
                    self.on_ground = True
                elif self.vy < 0:
                    # Head bump
                    self.rect.top = solid.bottom
                    self.vy = 0.0
                    hit_head = True
                    hit_tx_ty = (tx, ty)

        # Coyote
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        # Head bump -> resolve block effect
        gained_score = 0
        gained_coins = 0
        if hit_head and hit_tx_ty is not None:
            score, coins = level.bump_block_at(*hit_tx_ty)
            gained_score += score
            gained_coins += coins

        # Coin pickup (any 'o' intersecting player)
        got = level.collect_coins_in_rect(self.rect.inflate(-2, -2))
        gained_coins += got

        return gained_score, gained_coins

    def stomp_check(self, enemy):
        # Return True if player stomps enemy this frame
        if not enemy.alive:
            return False
        # Simple stomp: player's downward movement + above enemy
        overlap = self.rect.colliderect(enemy.rect)
        if not overlap:
            return False
        # Consider stomp if vertical velocity is downward and bottoms are close
        if self.vy >= 0 and self.rect.bottom <= enemy.rect.top + 8:
            return True
        return False

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, COLORS["player"], r)

# ----------------------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------------------
class Game:
    TITLE, PLAY, CLEAR, GAMEOVER = range(4)

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Original Platformer — 32 synthetic levels @60FPS")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.bigfont = pygame.font.SysFont("consolas", 32, bold=True)

        self.state = Game.TITLE
        self.level_index = 0
        self.level = Level(self.level_index)
        self.player = Player(*self.level.spawn)
        self.camera = Camera()
        self.walkers = [Walker(x, y, dir_left=bool((i % 2) == 0)) for i, (x, y) in enumerate(self.level.enemies)]
        self.score = 0
        self.coins = 0
        self.lives = 3
        self.clear_timer = 0.0

    def load_level(self, idx):
        idx = idx % MAX_LEVELS
        self.level_index = idx
        self.level = Level(idx)
        self.player = Player(*self.level.spawn)
        self.camera = Camera()
        self.walkers = [Walker(x, y, dir_left=bool((i % 2) == 0)) for i, (x, y) in enumerate(self.level.enemies)]

    def restart_level(self):
        self.load_level(self.level_index)

    def next_level(self):
        self.load_level((self.level_index + 1) % MAX_LEVELS)

    def handle_death(self):
        self.lives -= 1
        if self.lives < 0:
            self.state = Game.GAMEOVER
        else:
            self.restart_level()

    def update_play(self, dt):
        keys = pygame.key.get_pressed()

        # Input
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                if ev.key == pygame.K_r:
                    self.restart_level()
                if ev.key in (pygame.K_SPACE, pygame.K_z, pygame.K_UP):
                    self.player.want_jump()

        # Player update
        gained_score, gained_coins = self.player.update(dt, self.level, keys)
        self.score += gained_score
        if gained_coins > 0:
            self.coins += gained_coins
            # 1up per 100 coins
            while self.coins >= 100:
                self.coins -= 100
                self.lives += 1
                self.score += 1000

        # Enemies update
        for w in self.walkers:
            w.update(dt, self.level)

        # Player vs enemy
        for w in self.walkers:
            if not w.alive:
                continue
            if self.player.stomp_check(w):
                w.alive = False
                self.player.vy = -JUMP_SPEED * 0.6
                self.score += 200
            elif self.player.rect.colliderect(w.rect):
                # Hurt -> death for now
                self.handle_death()
                return

        # Flag / end detection
        # The flag tile is at (flag_x, some_y); we detect a region to finish
        flag_rect = pygame.Rect(self.level.flag_x, 0, 4 * TILE, self.level.height * TILE)
        if self.player.rect.colliderect(flag_rect):
            self.state = Game.CLEAR
            self.clear_timer = 2.0
            self.score += 500

        # Fell below map
        if self.player.rect.top > self.level.height * TILE + 100:
            self.handle_death()
            return

        # Camera
        self.camera.update(self.player.rect, self.level)

    def draw_tiles(self, surf):
        # Visible tile bounds
        start_tx = max(0, int(self.camera.x) // TILE - 1)
        end_tx = min(self.level.width, (int(self.camera.x) + SCREEN_W) // TILE + 2)
        for ty in range(self.level.height):
            py = ty * TILE
            for tx in range(start_tx, end_tx):
                ch = self.level.get(tx, ty)
                if ch == ' ':
                    continue
                rx = tx * TILE - int(self.camera.x)
                r = pygame.Rect(rx, py, TILE, TILE)
                if ch == 'X':
                    pygame.draw.rect(surf, COLORS["ground"], r)
                elif ch == '|':
                    pygame.draw.rect(surf, COLORS["pipe"], r)
                elif ch == '?':
                    pygame.draw.rect(surf, COLORS["question"], r)
                elif ch == '=':
                    pygame.draw.rect(surf, COLORS["platform"], r)
                elif ch == 'o':
                    pygame.draw.circle(surf, COLORS["coin"], (r.centerx, r.centery), TILE // 3)
                elif ch == 'f':
                    # Draw a tall pole and banner
                    pole_x = rx + TILE // 2
                    pygame.draw.rect(surf, COLORS["flag"], (pole_x, py - 6 * TILE, 3, 7 * TILE))
                    # Banner triangle
                    banner = [
                        (pole_x + 3, py - 6 * TILE + 6),
                        (pole_x + 3 + 10, py - 6 * TILE + 10),
                        (pole_x + 3, py - 6 * TILE + 14),
                    ]
                    pygame.draw.polygon(surf, COLORS["flag_banner"], banner)

    def draw_hud(self, surf):
        w, s = world_stage(self.level_index)
        hud = f"World {w}-{s}   Score {self.score:06d}   Coins {self.coins:02d}   Lives {self.lives}"
        text = self.font.render(hud, True, COLORS["hud"])
        surf.blit(text, (12, 8))

    def draw_title(self, surf):
        surf.fill(COLORS["sky"])
        title = "ORIGINAL PLATFORMER"
        subtitle = "32 synthetic levels • 60 FPS • no external files"
        hint = "Press Enter to Start  •  Arrows/A D to move, Z/Space/Up to jump, Shift to run"
        t1 = self.bigfont.render(title, True, COLORS["hud"])
        t2 = self.font.render(subtitle, True, COLORS["hud"])
        t3 = self.font.render(hint, True, COLORS["hud"])
        surf.blit(t1, (SCREEN_W//2 - t1.get_width()//2, SCREEN_H//2 - 80))
        surf.blit(t2, (SCREEN_W//2 - t2.get_width()//2, SCREEN_H//2 - 34))
        surf.blit(t3, (SCREEN_W//2 - t3.get_width()//2, SCREEN_H//2 + 10))
        pygame.display.flip()

    def draw_clear(self, surf):
        surf.fill(COLORS["sky"])
        w, s = world_stage(self.level_index)
        msg = f"Course Clear! — World {w}-{s}"
        t1 = self.bigfont.render(msg, True, COLORS["hud"])
        t2 = self.font.render("Press Enter for the next course.", True, COLORS["hud"])
        surf.blit(t1, (SCREEN_W//2 - t1.get_width()//2, SCREEN_H//2 - 20))
        surf.blit(t2, (SCREEN_W//2 - t2.get_width()//2, SCREEN_H//2 + 20))
        pygame.display.flip()

    def draw_gameover(self, surf):
        surf.fill(COLORS["sky"])
        t1 = self.bigfont.render("GAME OVER", True, COLORS["hud"])
        t2 = self.font.render("Press Enter to return to Title.", True, COLORS["hud"])
        surf.blit(t1, (SCREEN_W//2 - t1.get_width()//2, SCREEN_H//2 - 20))
        surf.blit(t2, (SCREEN_W//2 - t2.get_width()//2, SCREEN_H//2 + 20))
        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            if self.state == Game.TITLE:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit(); sys.exit(0)
                    elif ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            pygame.quit(); sys.exit(0)
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.state = Game.PLAY
                self.draw_title(self.screen)
                continue

            if self.state == Game.CLEAR:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit(); sys.exit(0)
                    elif ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            pygame.quit(); sys.exit(0)
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.next_level()
                            self.state = Game.PLAY
                self.draw_clear(self.screen)
                continue

            if self.state == Game.GAMEOVER:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit(); sys.exit(0)
                    elif ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            pygame.quit(); sys.exit(0)
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            # Back to title
                            self.__init__()
                            self.state = Game.TITLE
                self.draw_gameover(self.screen)
                continue

            # PLAY
            self.update_play(dt)

            # Draw world
            self.screen.fill(COLORS["sky"])
            self.draw_tiles(self.screen)
            for w in self.walkers:
                w.draw(self.screen, self.camera)
            self.player.draw(self.screen, self.camera)
            self.draw_hud(self.screen)
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
