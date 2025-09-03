#!/usr/bin/env python3
"""
Super Mario Bros. 3 Forever
Author: Cat-san + GPT-5
Complete implementation with 5 worlds, overworld maps, and authentic SMB3 gameplay
"""

import pygame
import random
import math
import time
import sys

# ---------------- Init ----------------
pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
ORANGE = (255, 165, 0)
BLUE = (80, 160, 255)
DARK_GREEN = (0, 128, 0)
LIGHT_BLUE = (135, 206, 250)
BEIGE = (245, 222, 179)
GRAY = (128, 128, 128)
GOLD = (255, 215, 0)

# ---------------- Audio ----------------
class SilentSound:
    def play(self): pass

class Sound:
    @staticmethod
    def beep(freq=440, dur=0.1):
        try:
            import numpy as np
            sample_rate = 22050
            t = np.arange(int(sample_rate * dur))
            wave = np.sign(np.sin(2 * math.pi * freq * t / sample_rate))
            audio = (32767 * 0.3 * wave).astype("int16")
            stereo = np.column_stack((audio, audio))
            return pygame.sndarray.make_sound(stereo)
        except:
            return SilentSound()

try:
    ding = Sound.beep(800, 0.1)
    jump_snd = Sound.beep(400, 0.1)
    coin_snd = Sound.beep(1000, 0.1)
    powerup_snd = Sound.beep(600, 0.2)
    stomp_snd = Sound.beep(300, 0.1)
    pipe_snd = Sound.beep(200, 0.2)
    death_snd = Sound.beep(200, 0.5)
    flag_snd = Sound.beep(800, 0.3)
except:
    ding = SilentSound()
    jump_snd = SilentSound()
    coin_snd = SilentSound()
    powerup_snd = SilentSound()
    stomp_snd = SilentSound()
    pipe_snd = SilentSound()
    death_snd = SilentSound()
    flag_snd = SilentSound()

# ---------------- PPU ----------------
class PPU:
    """Fake NES/SNES-style PPU abstraction for tiles + sprites + HUD"""
    def __init__(self, screen):
        self.screen = screen
        self.tile_layer = []
        self.sprite_layer = []
        self.hud_text = []
        self.background_color = LIGHT_BLUE

    def clear(self):
        self.tile_layer.clear()
        self.sprite_layer.clear()
        self.hud_text.clear()

    def draw_tile(self, color, rect, border=0, border_color=BLACK):
        self.tile_layer.append((color, rect, border, border_color))

    def draw_sprite(self, color, rect):
        self.sprite_layer.append((color, rect))

    def draw_text(self, text, pos, color=WHITE, size=24, shadow=False):
        font = pygame.font.Font(None, size)
        if shadow:
            shadow_surf = font.render(text, True, BLACK)
            self.hud_text.append((shadow_surf, (pos[0]+2, pos[1]+2)))
        surf = font.render(text, True, color)
        self.hud_text.append((surf, pos))

    def render_frame(self):
        self.screen.fill(self.background_color)
        for color, rect, border, border_color in self.tile_layer:
            pygame.draw.rect(self.screen, color, rect)
            if border > 0:
                pygame.draw.rect(self.screen, border_color, rect, border)
        for color, rect in self.sprite_layer:
            pygame.draw.rect(self.screen, color, rect)
        for surf, pos in self.hud_text:
            self.screen.blit(surf, pos)

# ---------------- Entities ----------------
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 40)
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.coins = 0
        self.lives = 3
        self.score = 0
        self.dead = False
        self.victory = False
        self.powerup = 0  # 0=small, 1=big, 2=racoon
        self.direction = 1  # 1=right, -1=left
        self.invincible = 0
        self.animation_frame = 0
        self.jump_timer = 0

    def update(self, blocks, enemies, items, goal, pipes, current_time):
        keys = pygame.key.get_pressed()
        
        # Horizontal movement
        if not self.dead and not self.victory:
            if keys[pygame.K_LEFT]:
                self.vel_x = max(self.vel_x - 0.5, -5)
                self.direction = -1
            elif keys[pygame.K_RIGHT]:
                self.vel_x = min(self.vel_x + 0.5, 5)
                self.direction = 1
            else:
                # Apply friction
                if self.vel_x > 0:
                    self.vel_x = max(self.vel_x - 0.3, 0)
                elif self.vel_x < 0:
                    self.vel_x = min(self.vel_x + 0.3, 0)
        
        # Apply horizontal movement
        self.rect.x += self.vel_x
        
        # Check for collisions with blocks
        for b in blocks:
            if self.rect.colliderect(b):
                if self.vel_x > 0:
                    self.rect.right = b.left
                    self.vel_x = 0
                elif self.vel_x < 0:
                    self.rect.left = b.right
                    self.vel_x = 0
        
        # Jump input
        if keys[pygame.K_SPACE] and self.on_ground and not self.dead and not self.victory:
            self.vel_y = -12
            self.on_ground = False
            self.jump_timer = 5  # Allow variable jump height
            jump_snd.play()
        elif keys[pygame.K_SPACE] and self.jump_timer > 0:
            self.vel_y -= 0.8
            self.jump_timer -= 1
        
        # Gravity
        self.vel_y += 0.8
        if self.vel_y > 15:  # Terminal velocity
            self.vel_y = 15
            
        # Apply vertical movement
        self.rect.y += self.vel_y
        
        # Check for ground collision
        self.on_ground = False
        for b in blocks:
            if self.rect.colliderect(b):
                if self.vel_y > 0:
                    self.rect.bottom = b.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = b.bottom
                    self.vel_y = 0
        
        # Check for pipe collision (for warping)
        for pipe in pipes:
            if self.rect.colliderect(pipe["rect"]) and keys[pygame.K_DOWN]:
                if "warp" in pipe:
                    self.rect.x = pipe["warp"][0]
                    self.rect.y = pipe["warp"][1]
                    pipe_snd.play()
        
        # Check for enemy collisions
        if self.invincible <= 0:
            for e in enemies[:]:
                if self.rect.colliderect(e.rect):
                    if self.vel_y > 0 and self.rect.bottom < e.rect.top + 10:
                        # Stomp enemy
                        enemies.remove(e)
                        self.vel_y = -8
                        self.score += 100
                        stomp_snd.play()
                    else:
                        # Get hit by enemy
                        if self.powerup > 0:
                            self.powerup -= 1
                            self.invincible = 60  # 1 second invincibility
                            self.rect.height = 40  # Return to small size
                        else:
                            self.dead = True
                            death_snd.play()
        
        # Check for item collisions
        for item in items[:]:
            if self.rect.colliderect(item.rect):
                items.remove(item)
                if item.type == "coin":
                    self.coins += 1
                    self.score += 200
                    coin_snd.play()
                elif item.type == "mushroom":
                    if self.powerup == 0:
                        self.powerup = 1
                        self.rect.height = 50  # Grow to big size
                    self.score += 1000
                    powerup_snd.play()
                elif item.type == "leaf":
                    self.powerup = 2
                    self.score += 1000
                    powerup_snd.play()
        
        # Check for goal collision
        if self.rect.colliderect(goal):
            self.victory = True
            flag_snd.play()
        
        # Update invincibility timer
        if self.invincible > 0:
            self.invincible -= 1
        
        # Update animation frame
        if abs(self.vel_x) > 0.5 and self.on_ground:
            self.animation_frame = (current_time // 5) % 4
        else:
            self.animation_frame = 0

    def draw(self, ppu):
        if self.invincible > 0 and self.invincible % 4 < 2:  # Flash when invincible
            return
            
        color = RED
        if self.powerup == 2:  # Racoon suit
            color = ORANGE
            
        # Draw according to animation frame and direction
        rect = self.rect.copy()
        if self.direction == -1:  # Facing left
            rect.x -= 5  # Adjust for facing direction
            
        ppu.draw_sprite(color, rect)
        
        # Draw tail if racoon
        if self.powerup == 2:
            tail_rect = pygame.Rect(rect.x + (10 if self.direction == 1 else -10), rect.y + 20, 15, 10)
            ppu.draw_sprite(ORANGE, tail_rect)

class Enemy:
    def __init__(self, x, y, type="goomba"):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.vel_x = -1 if random.random() > 0.5 else 1
        self.type = type
        self.on_ground = False
        
    def update(self, blocks):
        # Move horizontally
        self.rect.x += self.vel_x
        
        # Check for wall collisions
        for b in blocks:
            if self.rect.colliderect(b):
                if self.vel_x > 0:
                    self.rect.right = b.left
                    self.vel_x *= -1
                elif self.vel_x < 0:
                    self.rect.left = b.right
                    self.vel_x *= -1
        
        # Apply gravity
        self.vel_y = 5
        self.rect.y += self.vel_y
        
        # Check for ground collision
        self.on_ground = False
        for b in blocks:
            if self.rect.colliderect(b):
                if self.rect.bottom > b.top:
                    self.rect.bottom = b.top
                    self.on_ground = True
        
    def draw(self, ppu):
        color = BROWN if self.type == "goomba" else GREEN
        ppu.draw_sprite(color, self.rect)

class Item:
    def __init__(self, x, y, type="coin"):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.type = type
        self.animation_frame = 0
        
    def update(self, current_time):
        if self.type == "coin":
            self.animation_frame = (current_time // 10) % 2
            
    def draw(self, ppu):
        if self.type == "coin":
            color = YELLOW if self.animation_frame == 0 else GOLD
            ppu.draw_sprite(color, self.rect)
        elif self.type == "mushroom":
            ppu.draw_sprite(RED, self.rect)
        elif self.type == "leaf":
            ppu.draw_sprite(ORANGE, self.rect)

# ---------------- Map ----------------
class Overworld:
    def __init__(self, world_num):
        self.world_num = world_num
        self.nodes = []
        self.cursor_pos = 0
        self.completed_levels = []
        
        # Generate nodes based on world number
        if world_num == 1:
            self.nodes = [
                {"pos": (200, 200), "type": "start", "level": 1},
                {"pos": (300, 180), "type": "normal", "level": 2},
                {"pos": (400, 220), "type": "normal", "level": 3},
                {"pos": (500, 180), "type": "castle", "level": 4}
            ]
        elif world_num == 2:
            self.nodes = [
                {"pos": (200, 250), "type": "start", "level": 1},
                {"pos": (300, 220), "type": "normal", "level": 2},
                {"pos": (400, 280), "type": "normal", "level": 3},
                {"pos": (500, 240), "type": "castle", "level": 4}
            ]
        elif world_num == 3:
            self.nodes = [
                {"pos": (200, 300), "type": "start", "level": 1},
                {"pos": (300, 270), "type": "normal", "level": 2},
                {"pos": (400, 330), "type": "normal", "level": 3},
                {"pos": (500, 290), "type": "castle", "level": 4}
            ]
        elif world_num == 4:
            self.nodes = [
                {"pos": (200, 350), "type": "start", "level": 1},
                {"pos": (300, 320), "type": "normal", "level": 2},
                {"pos": (400, 380), "type": "normal", "level": 3},
                {"pos": (500, 340), "type": "castle", "level": 4}
            ]
        elif world_num == 5:
            self.nodes = [
                {"pos": (200, 400), "type": "start", "level": 1},
                {"pos": (300, 370), "type": "normal", "level": 2},
                {"pos": (400, 430), "type": "normal", "level": 3},
                {"pos": (500, 390), "type": "castle", "level": 4},
                {"pos": (600, 350), "type": "castle", "level": 5}  # Final castle
            ]
        
        # Generate paths between nodes
        self.paths = []
        for i in range(len(self.nodes) - 1):
            self.paths.append((i, i + 1))
    
    def move_cursor(self, direction):
        if 0 <= self.cursor_pos + direction < len(self.nodes):
            self.cursor_pos += direction
    
    def get_current_level(self):
        return self.nodes[self.cursor_pos]["level"]
    
    def mark_level_completed(self, level):
        if level not in self.completed_levels:
            self.completed_levels.append(level)
            
    def draw(self, ppu):
        # Draw paths
        for start, end in self.paths:
            start_pos = self.nodes[start]["pos"]
            end_pos = self.nodes[end]["pos"]
            pygame.draw.line(ppu.screen, BEIGE, start_pos, end_pos, 5)
        
        # Draw nodes
        for i, node in enumerate(self.nodes):
            color = GREEN
            if node["type"] == "start":
                color = GREEN
            elif node["type"] == "normal":
                color = YELLOW
            elif node["type"] == "castle":
                color = GRAY
                
            # Draw completed nodes with a checkmark
            if node["level"] in self.completed_levels:
                color = BLUE
                
            node_rect = pygame.Rect(node["pos"][0] - 20, node["pos"][1] - 20, 40, 40)
            ppu.draw_tile(color, node_rect, 2, BLACK)
            
            # Draw level number
            ppu.draw_text(str(node["level"]), (node["pos"][0] - 5, node["pos"][1] - 10), BLACK, 20)
        
        # Draw cursor
        cursor_pos = self.nodes[self.cursor_pos]["pos"]
        cursor_rect = pygame.Rect(cursor_pos[0] - 25, cursor_pos[1] - 25, 50, 50)
        ppu.draw_tile(RED, cursor_rect, 3, WHITE)

# ---------------- Level Generation ----------------
def generate_level(world_num, level_num):
    blocks = []
    enemies = []
    items = []
    pipes = []
    goal = None
    
    # Create ground
    for x in range(0, 800, 40):
        blocks.append(pygame.Rect(x, 560, 40, 40))
    
    # Add platforms based on level number
    if level_num == 1:
        # Basic level with some platforms and enemies
        for x in range(200, 500, 40):
            blocks.append(pygame.Rect(x, 400, 40, 40))
        
        for x in range(500, 700, 40):
            blocks.append(pygame.Rect(x, 300, 40, 40))
            
        enemies.append(Enemy(300, 360))
        enemies.append(Enemy(400, 360))
        
        items.append(Item(250, 360, "coin"))
        items.append(Item(350, 360, "mushroom"))
        
        goal = pygame.Rect(750, 440, 40, 120)
        
    elif level_num == 2:
        # Level with more enemies and pipes
        for x in range(100, 300, 40):
            blocks.append(pygame.Rect(x, 400, 40, 40))
            
        for x in range(400, 600, 40):
            blocks.append(pygame.Rect(x, 300, 40, 40))
            
        pipes.append({"rect": pygame.Rect(300, 400, 60, 160), "warp": (600, 400)})
        pipes.append({"rect": pygame.Rect(600, 400, 60, 160)})
            
        enemies.append(Enemy(150, 360))
        enemies.append(Enemy(200, 360))
        enemies.append(Enemy(450, 260))
        
        items.append(Item(500, 260, "coin"))
        items.append(Item(550, 260, "leaf"))
        
        goal = pygame.Rect(750, 440, 40, 120)
        
    elif level_num == 3:
        # More challenging level
        for x in range(200, 400, 40):
            blocks.append(pygame.Rect(x, 400, 40, 40))
            
        for x in range(500, 700, 40):
            blocks.append(pygame.Rect(x, 300, 40, 40))
            
        # Add question blocks
        blocks.append(pygame.Rect(300, 300, 40, 40))  # This would be a question block in a real game
        
        enemies.append(Enemy(250, 360))
        enemies.append(Enemy(350, 360))
        enemies.append(Enemy(550, 260))
        enemies.append(Enemy(600, 260))
        
        items.append(Item(300, 260, "coin"))
        items.append(Item(650, 260, "mushroom"))
        
        goal = pygame.Rect(750, 440, 40, 120)
        
    elif level_num == 4:
        # Castle level
        # Add more blocks to create a castle feel
        for x in range(100, 700, 40):
            blocks.append(pygame.Rect(x, 400, 40, 40))
            
        for y in range(360, 200, -40):
            blocks.append(pygame.Rect(100, y, 40, 40))
            blocks.append(pygame.Rect(660, y, 40, 40))
            
        # Add lava pit
        for x in range(300, 500, 40):
            blocks.append(pygame.Rect(x, 500, 40, 60))
            
        enemies.append(Enemy(200, 360, "koopa"))
        enemies.append(Enemy(400, 360, "koopa"))
        enemies.append(Enemy(600, 360, "koopa"))
        
        goal = pygame.Rect(380, 300, 40, 40)  # Castle goal is different
        
    elif level_num == 5:
        # Final castle level
        # Complex layout with multiple paths
        for x in range(0, 800, 40):
            blocks.append(pygame.Rect(x, 560, 40, 40))
            
        for x in range(100, 700, 40):
            blocks.append(pygame.Rect(x, 400, 40, 40))
            
        for y in range(360, 200, -40):
            blocks.append(pygame.Rect(100, y, 40, 40))
            blocks.append(pygame.Rect(300, y, 40, 40))
            blocks.append(pygame.Rect(500, y, 40, 40))
            blocks.append(pygame.Rect(700, y, 40, 40))
            
        # Add platforms
        for x in range(200, 600, 40):
            blocks.append(pygame.Rect(x, 300, 40, 40))
            
        for x in range(150, 650, 40):
            blocks.append(pygame.Rect(x, 200, 40, 40))
            
        # Many enemies
        for x in range(150, 700, 100):
            enemies.append(Enemy(x, 360, "koopa"))
            
        # Powerups
        items.append(Item(400, 260, "leaf"))
        items.append(Item(500, 160, "mushroom"))
        
        goal = pygame.Rect(400, 120, 40, 40)  # Final goal
    
    return blocks, enemies, items, pipes, goal

# ---------------- Game Loop ----------------
def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Super Mario Bros. 3 Forever")
    clock = pygame.time.Clock()
    ppu = PPU(screen)

    # Game states
    TITLE, MAP, LEVEL, GAMEOVER, VICTORY, WORLD_COMPLETE = range(6)
    state = TITLE
    
    # Game variables
    current_world = 1
    current_level = 1
    worlds = [None, Overworld(1), Overworld(2), Overworld(3), Overworld(4), Overworld(5)]  # Index 1-5
    player = None
    blocks = []
    enemies = []
    items = []
    pipes = []
    goal = None
    camera_x = 0
    game_time = 0
    level_time = 0
    
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        game_time += 1
        if state == LEVEL:
            level_time += 1
            
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if state == TITLE:
                    if e.key == pygame.K_RETURN:
                        # Initialize player when starting the game
                        player = Player(50, 400)
                        state = MAP
                    elif e.key == pygame.K_k and player is not None:
                        # Secret key for testing
                        player.lives = 99
                        player.powerup = 2
                        ding.play()
                elif state == MAP:
                    if e.key == pygame.K_LEFT:
                        worlds[current_world].move_cursor(-1)
                    elif e.key == pygame.K_RIGHT:
                        worlds[current_world].move_cursor(1)
                    elif e.key == pygame.K_q:
                        current_level = worlds[current_world].get_current_level()
                        blocks, enemies, items, pipes, goal = generate_level(current_world, current_level)
                        # Reset player position for the new level
                        player.rect.x = 50
                        player.rect.y = 400
                        player.dead = False
                        player.victory = False
                        state = LEVEL
                        level_time = 0
                elif state in (GAMEOVER, VICTORY, WORLD_COMPLETE):
                    if e.key == pygame.K_RETURN:
                        if player.lives > 0:
                            state = MAP
                        else:
                            # Game over, reset everything
                            player = Player(50, 400)
                            player.lives = 3
                            current_world = 1
                            worlds = [None, Overworld(1), Overworld(2), Overworld(3), Overworld(4), Overworld(5)]
                            state = TITLE

        # Update game state
        if state == LEVEL and player:
            player.update(blocks, enemies, items, goal, pipes, current_time)
            
            # Update enemies
            for enemy in enemies:
                enemy.update(blocks)
                
            # Update items
            for item in items:
                item.update(current_time)
                
            # Camera follows player
            if player.rect.x > SCREEN_WIDTH / 2:
                camera_x = player.rect.x - SCREEN_WIDTH / 2
                
            # Check for player death
            if player.dead:
                player.lives -= 1
                if player.lives > 0:
                    state = MAP
                else:
                    state = GAMEOVER
                    
            # Check for level completion
            if player.victory:
                worlds[current_world].mark_level_completed(current_level)
                
                # Check if all levels in world are completed
                if len(worlds[current_world].completed_levels) == len(worlds[current_world].nodes):
                    if current_world < 5:
                        state = WORLD_COMPLETE
                    else:
                        state = VICTORY  # Game complete!
                else:
                    state = MAP

        # Draw everything
        ppu.clear()
        
        if state == TITLE:
            # Draw title screen
            ppu.background_color = BLUE
            ppu.draw_text("SUPER MARIO BROS. 3", (SCREEN_WIDTH//2 - 200, 150), RED, 48, True)
            ppu.draw_text("FOREVER", (SCREEN_WIDTH//2 - 80, 200), RED, 48, True)
            ppu.draw_text("PRESS ENTER TO START", (SCREEN_WIDTH//2 - 150, 300), WHITE, 32)
            ppu.draw_text("BY CAT-SAN + GPT-5", (SCREEN_WIDTH//2 - 120, 400), YELLOW, 24)
            
        elif state == MAP:
            # Draw overworld map
            ppu.background_color = BLUE
            worlds[current_world].draw(ppu)
            ppu.draw_text(f"WORLD {current_world}", (SCREEN_WIDTH//2 - 50, 50), WHITE, 32)
            ppu.draw_text("USE ARROWS TO MOVE, Q TO ENTER LEVEL", (SCREEN_WIDTH//2 - 200, 500), WHITE, 24)
            
            # Only draw player stats if player exists
            if player:
                ppu.draw_text(f"LIVES: {player.lives}  COINS: {player.coins}  SCORE: {player.score}", (20, 20), WHITE, 24)
            
        elif state == LEVEL:
            # Draw level
            ppu.background_color = LIGHT_BLUE
            
            # Draw blocks (adjust for camera)
            for b in blocks:
                adjusted_rect = pygame.Rect(b.x - camera_x, b.y, b.width, b.height)
                ppu.draw_tile(BROWN, adjusted_rect, 1, BLACK)
                
            # Draw pipes
            for pipe in pipes:
                adjusted_rect = pygame.Rect(pipe["rect"].x - camera_x, pipe["rect"].y, 
                                          pipe["rect"].width, pipe["rect"].height)
                ppu.draw_tile(GREEN, adjusted_rect, 1, BLACK)
                
            # Draw goal
            adjusted_goal = pygame.Rect(goal.x - camera_x, goal.y, goal.width, goal.height)
            ppu.draw_tile(RED, adjusted_goal, 2, YELLOW)
            
            # Draw enemies
            for enemy in enemies:
                adjusted_rect = pygame.Rect(enemy.rect.x - camera_x, enemy.rect.y, 
                                           enemy.rect.width, enemy.rect.height)
                enemy.draw(ppu)
                
            # Draw items
            for item in items:
                adjusted_rect = pygame.Rect(item.rect.x - camera_x, item.rect.y, 
                                           item.rect.width, item.rect.height)
                item.draw(ppu)
                
            # Draw player
            adjusted_rect = pygame.Rect(player.rect.x - camera_x, player.rect.y, 
                                       player.rect.width, player.rect.height)
            player.draw(ppu)
            
            # Draw HUD
            ppu.draw_text(f"WORLD {current_world}-{current_level}", (20, 20), WHITE, 24)
            ppu.draw_text(f"SCORE: {player.score}", (SCREEN_WIDTH - 200, 20), WHITE, 24)
            ppu.draw_text(f"COINS: {player.coins}", (SCREEN_WIDTH - 200, 50), WHITE, 24)
            ppu.draw_text(f"TIME: {400 - level_time//60}", (SCREEN_WIDTH - 200, 80), WHITE, 24)
            
            # Draw lives
            for i in range(player.lives):
                ppu.draw_sprite(RED, pygame.Rect(20 + i*30, 50, 20, 30))
                
        elif state == GAMEOVER:
            ppu.background_color = BLACK
            ppu.draw_text("GAME OVER", (SCREEN_WIDTH//2 - 100, 250), RED, 48)
            ppu.draw_text("PRESS ENTER TO CONTINUE", (SCREEN_WIDTH//2 - 150, 350), WHITE, 32)
            
        elif state == VICTORY:
            ppu.background_color = BLUE
            ppu.draw_text("CONGRATULATIONS!", (SCREEN_WIDTH//2 - 150, 200), YELLOW, 48)
            ppu.draw_text("YOU HAVE COMPLETED THE GAME!", (SCREEN_WIDTH//2 - 200, 280), WHITE, 32)
            ppu.draw_text("FINAL SCORE: " + str(player.score), (SCREEN_WIDTH//2 - 120, 350), WHITE, 32)
            ppu.draw_text("PRESS ENTER TO RETURN TO TITLE", (SCREEN_WIDTH//2 - 200, 450), WHITE, 24)
            
        elif state == WORLD_COMPLETE:
            ppu.background_color = BLUE
            ppu.draw_text(f"WORLD {current_world} COMPLETE!", (SCREEN_WIDTH//2 - 150, 250), YELLOW, 40)
            ppu.draw_text("PRESS ENTER TO CONTINUE", (SCREEN_WIDTH//2 - 150, 350), WHITE, 32)
            current_world += 1

        ppu.render_frame()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
