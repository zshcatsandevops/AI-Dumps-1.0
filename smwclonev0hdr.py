#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMW-style Overworld (8 Worlds) + Simple Platformer Levels
Controls:
- Overworld: A/D to move cursor; Q to enter the selected world
- In-Level:  A = left, D = right, W = jump, R = restart level
- General:   ESC returns to the overworld
"""
import sys
import pygame

# ---------- Config ----------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 200, 90)
RED = (200, 50, 50)
BLUE = (40, 120, 220)
GOLD = (230, 200, 40)
GRAY = (160, 160, 160)

# ---------- Sprites ----------
class Platform(pygame.sprite.Sprite):
    def __init__(self, width, height, x, y):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(topleft=(x, y))

class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([18, 64])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect(topleft=(x, y))

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([26, 36])
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.change_x = 0.0
        self.change_y = 0.0
        self.level = None

    def update(self):
        # Apply gravity
        self.calc_grav()

        # Move horizontally
        self.rect.x += self.change_x
        # Collide with platforms (X)
        block_hit_list = pygame.sprite.spritecollide(self, self.level.platforms, False)
        for block in block_hit_list:
            if self.change_x > 0:
                self.rect.right = block.rect.left
            elif self.change_x < 0:
                self.rect.left = block.rect.right

        # Move vertically
        self.rect.y += self.change_y
        # Collide with platforms (Y)
        block_hit_list = pygame.sprite.spritecollide(self, self.level.platforms, False)
        for block in block_hit_list:
            if self.change_y > 0:
                self.rect.bottom = block.rect.top
            elif self.change_y < 0:
                self.rect.top = block.rect.bottom
            self.change_y = 0

        # Floor
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.change_y = 0

    def calc_grav(self):
        if self.change_y == 0:
            self.change_y = 1
        else:
            self.change_y += 0.45  # gravity

    def jump(self):
        # Move down a pixel to check platform collision
        self.rect.y += 2
        platform_hit_list = pygame.sprite.spritecollide(self, self.level.platforms, False)
        self.rect.y -= 2
        if platform_hit_list or self.rect.bottom >= SCREEN_HEIGHT - 1:
            self.change_y = -11.5

    def go_left(self):  self.change_x = -6.0
    def go_right(self): self.change_x = 6.0
    def stop(self):     self.change_x = 0.0

# ---------- Level System ----------
class Level:
    def __init__(self, player):
        self.player = player
        self.platforms = pygame.sprite.Group()
        self.goals = pygame.sprite.Group()
        self.world_shift = 0
        self.level_limit = -2500  # how far the world can scroll left
        self.background_color = WHITE

    def update(self):
        self.platforms.update()
        self.goals.update()

    def draw(self, surface):
        surface.fill(self.background_color)
        self.platforms.draw(surface)
        self.goals.draw(surface)

    def shift_world(self, shift_x):
        """Scrolls platforms and goals by shift_x pixels."""
        self.world_shift += shift_x
        for p in self.platforms:
            p.rect.x += shift_x
        for g in self.goals:
            g.rect.x += shift_x

class LevelTemplate(Level):
    """Helper to create simple platform layouts quickly."""
    def __init__(self, player, layout, goal_x):
        super().__init__(player)
        for w, h, x, y in layout:
            self.platforms.add(Platform(w, h, x, y))
        # Place a long ground across the bottom
        self.platforms.add(Platform(4000, 20, -500, SCREEN_HEIGHT - 20))
        # Goal
        self.goals.add(Goal(goal_x, SCREEN_HEIGHT - 84))

class Level01(LevelTemplate):
    def __init__(self, player):
        layout = [
            (160, 24, 300, 500),
            (160, 24, 700, 460),
            (160, 24, 1050, 420),
            (160, 24, 1400, 380),
            (160, 24, 1750, 420),
        ]
        super().__init__(player, layout, goal_x=2100)
        self.level_limit = -2200

class Level02(LevelTemplate):
    def __init__(self, player):
        layout = [
            (160, 24, 250, 480),
            (200, 24, 620, 420),
            (140, 24, 980, 360),
            (240, 24, 1300, 420),
            (180, 24, 1680, 340),
            (160, 24, 1980, 480),
        ]
        super().__init__(player, layout, goal_x=2400)
        self.level_limit = -2500

class Level03(LevelTemplate):
    def __init__(self, player):
        layout = [
            (140, 24, 220, 430),
            (140, 24, 560, 370),
            (140, 24, 900, 430),
            (140, 24, 1240, 350),
            (200, 24, 1620, 470),
            (160, 24, 1960, 410),
            (200, 24, 2300, 350),
        ]
        super().__init__(player, layout, goal_x=2700)
        self.level_limit = -2800

class Level04(LevelTemplate):
    def __init__(self, player):
        layout = [
            (200, 24, 180, 500),
            (180, 24, 520, 440),
            (160, 24, 860, 380),
            (200, 24, 1200, 440),
            (140, 24, 1560, 520),
            (200, 24, 1880, 420),
            (160, 24, 2220, 360),
            (200, 24, 2580, 460),
        ]
        super().__init__(player, layout, goal_x=3000)
        self.level_limit = -3100

class Level05(LevelTemplate):
    def __init__(self, player):
        layout = [
            (160, 24, 220, 520),
            (160, 24, 540, 420),
            (160, 24, 860, 320),
            (160, 24, 1180, 420),
            (160, 24, 1500, 520),
            (160, 24, 1820, 420),
            (160, 24, 2140, 320),
            (160, 24, 2460, 420),
            (160, 24, 2780, 520),
        ]
        super().__init__(player, layout, goal_x=3200)
        self.level_limit = -3300

class Level06(LevelTemplate):
    def __init__(self, player):
        layout = [
            (200, 24, 200, 420),
            (200, 24, 600, 520),
            (200, 24, 1000, 420),
            (200, 24, 1400, 520),
            (200, 24, 1800, 420),
            (200, 24, 2200, 520),
            (200, 24, 2600, 420),
        ]
        super().__init__(player, layout, goal_x=3000)
        self.level_limit = -3100

class Level07(LevelTemplate):
    def __init__(self, player):
        layout = [
            (200, 24, 150, 360),
            (200, 24, 450, 440),
            (200, 24, 750, 360),
            (200, 24, 1050, 440),
            (200, 24, 1350, 360),
            (200, 24, 1650, 440),
            (200, 24, 1950, 360),
            (200, 24, 2250, 440),
            (200, 24, 2550, 360),
        ]
        super().__init__(player, layout, goal_x=2900)
        self.level_limit = -3000

class Level08(LevelTemplate):
    def __init__(self, player):
        layout = [
            (160, 24, 200, 520),
            (140, 24, 520, 460),
            (120, 24, 800, 400),
            (100, 24, 1040, 340),
            (80,  24, 1240, 280),
            (60,  24, 1380, 220),
            (80,  24, 1500, 280),
            (100, 24, 1680, 340),
            (120, 24, 1920, 400),
            (140, 24, 2200, 460),
            (160, 24, 2520, 520),
        ]
        super().__init__(player, layout, goal_x=2900)
        self.level_limit = -3000

LEVEL_CLASSES = [Level01, Level02, Level03, Level04, Level05, Level06, Level07, Level08]

# ---------- Overworld ----------
class Overworld:
    """A very simple SMW-like overworld with 8 nodes in a path."""
    def __init__(self, unlocked_worlds):
        self.unlocked_worlds = max(1, min(8, unlocked_worlds))
        self.selected = self.unlocked_worlds - 1
        self.font_small = pygame.font.SysFont(None, 24)
        self.font_big = pygame.font.SysFont(None, 36)
        # Precompute node positions along a gentle path
        self.nodes = [
            (120,  420),
            (240,  360),
            (360,  420),
            (480,  300),
            (600,  360),
            (720,  260),
            (840,  320),
            (880,  180),
        ]

    def draw(self, screen):
        screen.fill((72, 184, 248))  # sky blue
        # Draw ground strip
        pygame.draw.rect(screen, (40, 170, 40), (0, SCREEN_HEIGHT-80, SCREEN_WIDTH, 80))
        pygame.draw.rect(screen, (100, 200, 100), (0, SCREEN_HEIGHT-90, SCREEN_WIDTH, 10))

        # Path lines
        for i in range(7):
            start = self.nodes[i]
            end = self.nodes[i+1]
            color = GOLD if i < self.unlocked_worlds - 1 else GRAY
            pygame.draw.line(screen, color, start, end, 4)

        # Nodes
        for i, (x, y) in enumerate(self.nodes):
            unlocked = i < self.unlocked_worlds
            color = GOLD if unlocked else GRAY
            pygame.draw.circle(screen, color, (x, y), 18)
            label = self.font_small.render(str(i+1), True, BLACK if unlocked else WHITE)
            screen.blit(label, (x - label.get_width()//2, y - label.get_height()//2))

        # Cursor (Mario head-ish)
        x, y = self.nodes[self.selected]
        pygame.draw.circle(screen, RED, (x, y - 32), 12)           # head
        pygame.draw.rect(screen, RED, (x-8, y-20, 16, 12), 0)      # body
        pygame.draw.circle(screen, WHITE, (x+4, y-35), 3)          # eye

        # Text
        title = self.font_big.render("SMW-like Overworld — 8 Worlds", True, BLACK)
        instr  = self.font_small.render("A/D: move  •  Q: enter world", True, BLACK)
        unlocked = self.font_small.render(f"Unlocked: {self.unlocked_worlds}/8", True, BLACK)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 20))
        screen.blit(instr, (SCREEN_WIDTH//2 - instr.get_width()//2, 60))
        screen.blit(unlocked, (SCREEN_WIDTH//2 - unlocked.get_width()//2, 86))

    def move_selection(self, direction):
        self.selected += direction
        if self.selected < 0:
            self.selected = 0
        if self.selected >= self.unlocked_worlds:
            self.selected = self.unlocked_worlds - 1

    def select_world(self):
        return self.selected  # 0-based index

# ---------- Game ----------
def run():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SMW Overworld — 8 Worlds (WASD + Q)")
    clock = pygame.time.Clock()

    # State
    game_state = "overworld"
    unlocked_worlds = 1
    overworld = Overworld(unlocked_worlds)

    player = Player()
    active_level = None
    active_sprites = pygame.sprite.Group(player)
    current_world_index = 0  # 0..7

    font_small = pygame.font.SysFont(None, 22)
    font_big = pygame.font.SysFont(None, 32)

    def start_level(world_index):
        nonlocal active_level, game_state, current_world_index
        current_world_index = world_index
        # (Re)build the chosen level
        level = LEVEL_CLASSES[world_index](player)
        player.level = level
        # Position player near left edge
        player.rect.x = 120
        player.rect.bottom = SCREEN_HEIGHT
        player.change_x = 0
        player.change_y = 0
        active_level = level
        game_state = "level"

    def restart_level():
        start_level(current_world_index)

    while True:
        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if game_state == "overworld":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        overworld.move_selection(-1)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        overworld.move_selection(1)
                    elif event.key == pygame.K_q:
                        start_level(overworld.select_world())

            elif game_state == "level":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        player.go_left()
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        player.go_right()
                    elif event.key in (pygame.K_w, pygame.K_UP):
                        player.jump()
                    elif event.key == pygame.K_r:
                        restart_level()
                    elif event.key == pygame.K_ESCAPE:
                        # Return to overworld without progressing
                        game_state = "overworld"
                        # Rebuild overworld to reflect any unlocks
                        overworld = Overworld(unlocked_worlds)

                elif event.type == pygame.KEYUP:
                    if event.key in (pygame.K_a, pygame.K_LEFT, pygame.K_d, pygame.K_RIGHT):
                        player.stop()

        # Update
        if game_state == "level":
            active_level.update()
            player.update()

            # Scroll world left/right to keep player near center
            if player.rect.x >= SCREEN_WIDTH * 0.55:
                diff = player.rect.x - int(SCREEN_WIDTH * 0.55)
                player.rect.x = int(SCREEN_WIDTH * 0.55)
                active_level.shift_world(-diff)

            if player.rect.x <= SCREEN_WIDTH * 0.20 and active_level.world_shift < 0:
                diff = int(SCREEN_WIDTH * 0.20) - player.rect.x
                player.rect.x = int(SCREEN_WIDTH * 0.20)
                active_level.shift_world(diff)

            # Clamp world shift to level_limit
            if active_level.world_shift < active_level.level_limit:
                active_level.shift_world(active_level.level_limit - active_level.world_shift)

            # Goal reached?
            hit_goal = pygame.sprite.spritecollide(player, active_level.goals, False)
            if hit_goal:
                # Unlock next world (if any)
                if unlocked_worlds < 8 and current_world_index + 1 >= unlocked_worlds:
                    unlocked_worlds += 1
                game_state = "overworld"
                overworld = Overworld(unlocked_worlds)

        # Draw
        if game_state == "overworld":
            overworld.draw(screen)
        else:
            active_level.draw(screen)
            active_sprites.draw(screen)

            # HUD
            hud_title = font_big.render(f"World {current_world_index+1}", True, BLACK)
            hud_instr  = font_small.render("W: jump  •  A/D: move  •  R: restart  •  ESC: overworld", True, BLACK)
            screen.blit(hud_title, (16, 14))
            screen.blit(hud_instr, (16, 48))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    run()
