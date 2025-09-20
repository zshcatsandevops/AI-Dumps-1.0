import pygame
import sys
import random
import math
import hashlib
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
GRAVITY = 0.8
JUMP_STRENGTH = -15
PLAYER_SPEED = 5
ENEMY_SPEED = 2
TILE_SIZE = 32
LEVEL_HEIGHT = 24
LEVEL_WIDTH = 320

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (135, 206, 235)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
DARK_GREEN = (0, 100, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
PINK = (255, 192, 203)
GRAY = (128, 128, 128)
SAND = (238, 203, 173)
ICE_BLUE = (176, 224, 230)
GOLD = (255, 215, 0)

# Game States
class GameState(Enum):
    OVERWORLD = 1
    LEVEL = 2
    GAME_OVER = 3
    VICTORY = 4

class PowerUpType(Enum):
    NONE = 0
    MUSHROOM = 1
    FIRE_FLOWER = 2
    LEAF = 3
    STAR = 4

class WorldTheme(Enum):
    GRASS = 1
    DESERT = 2
    WATER = 3
    GIANT = 4
    SKY = 5
    ICE = 6
    PIPE = 7
    DARKNESS = 8

class TerrainType(Enum):
    EMPTY = 0
    GROUND = 1
    BRICK = 2
    QUESTION = 3
    PIPE = 4
    CLOUD = 5
    MOVING = 6
    ICE = 7
    SPIKE = 8
    COIN = 9
    POWERUP = 10
    ENEMY = 11

# Map Node for Overworld
class MapNode:
    def __init__(self, x, y, level_type, world_num, level_num):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x - 20, y - 20, 40, 40)
        self.level_type = level_type
        self.world_num = world_num
        self.level_num = level_num
        self.completed = False
        self.unlocked = False
        self.connections = []
        
    def draw(self, screen, selected=False):
        # Draw based on type
        if self.level_type == 'level':
            color = GREEN if self.completed else BLUE if self.unlocked else GRAY
            pygame.draw.circle(screen, color, (self.x, self.y), 18)
            pygame.draw.circle(screen, BLACK, (self.x, self.y), 18, 2)
            
            font = pygame.font.Font(None, 20)
            text = font.render(str(self.level_num), True, WHITE)
            text_rect = text.get_rect(center=(self.x, self.y))
            screen.blit(text, text_rect)
            
        elif self.level_type == 'fortress':
            rect = pygame.Rect(self.x - 20, self.y - 20, 40, 40)
            color = BROWN if self.completed else GRAY if self.unlocked else (50, 50, 50)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            
        elif self.level_type == 'castle':
            rect = pygame.Rect(self.x - 25, self.y - 25, 50, 50)
            color = PURPLE if self.completed else DARK_GREEN if self.unlocked else BLACK
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, GOLD, rect, 3)
            
        elif self.level_type == 'bonus':
            pygame.draw.polygon(screen, YELLOW, [
                (self.x, self.y - 15),
                (self.x + 5, self.y - 5),
                (self.x + 15, self.y - 3),
                (self.x + 7, self.y + 5),
                (self.x + 10, self.y + 15),
                (self.x, self.y + 10),
                (self.x - 10, self.y + 15),
                (self.x - 7, self.y + 5),
                (self.x - 15, self.y - 3),
                (self.x - 5, self.y - 5)
            ])
            
        # Selection indicator
        if selected:
            pygame.draw.circle(screen, WHITE, (self.x, self.y), 25, 3)

# World Map
class WorldMap:
    def __init__(self, world_num):
        self.world_num = world_num
        self.nodes = []
        self.current_node_index = 0
        self.generate_map()
        
    def generate_map(self):
        # Generate nodes based on world
        num_levels = 7 if self.world_num < 8 else 10
        
        for i in range(num_levels + 2):  # +2 for fortress and castle
            x = 100 + i * 100
            y = 300 + (i % 2) * 50  # Zigzag pattern
            
            if i == num_levels // 2:
                level_type = 'fortress'
                level_num = 0
            elif i == num_levels + 1:
                level_type = 'castle'
                level_num = 0
            elif i % 4 == 3 and i < num_levels:
                level_type = 'bonus'
                level_num = 0
            else:
                level_type = 'level'
                level_num = i + 1 if i < num_levels // 2 else i
                
            node = MapNode(x, y, level_type, self.world_num, level_num)
            self.nodes.append(node)
            
        # Connect nodes
        for i in range(len(self.nodes) - 1):
            self.nodes[i].connections.append(self.nodes[i + 1])
            if i > 0:
                self.nodes[i].connections.append(self.nodes[i - 1])
                
        # Unlock first node
        if self.nodes:
            self.nodes[0].unlocked = True
            
    def draw(self, screen):
        # Draw paths
        for i in range(len(self.nodes) - 1):
            start = self.nodes[i]
            end = self.nodes[i + 1]
            
            # Draw dotted line
            steps = 10
            for j in range(steps):
                t = j / steps
                x = int(start.x + t * (end.x - start.x))
                y = int(start.y + t * (end.y - start.y))
                pygame.draw.circle(screen, WHITE, (x, y), 2)
                
        # Draw nodes
        for i, node in enumerate(self.nodes):
            node.draw(screen, i == self.current_node_index)
            
    def move(self, direction):
        current = self.nodes[self.current_node_index]
        
        # Find connected node in direction
        best_node = None
        best_index = -1
        
        for i, node in enumerate(self.nodes):
            if node in current.connections and node.unlocked:
                if direction == 'right' and node.x > current.x:
                    if best_node is None or node.x < best_node.x:
                        best_node = node
                        best_index = i
                elif direction == 'left' and node.x < current.x:
                    if best_node is None or node.x > best_node.x:
                        best_node = node
                        best_index = i
                        
        if best_index >= 0:
            self.current_node_index = best_index
            return True
        return False
        
    def get_current_node(self):
        return self.nodes[self.current_node_index]
        
    def complete_current_level(self):
        node = self.get_current_node()
        node.completed = True
        
        # Unlock next nodes
        for conn in node.connections:
            conn.unlocked = True

# Overworld Controller
class Overworld:
    def __init__(self):
        self.current_world = 1
        self.world_maps = {}
        for i in range(1, 9):
            self.world_maps[i] = WorldMap(i)
        self.current_map = self.world_maps[1]
        
    def draw(self, screen):
        # Background
        colors = {
            1: (100, 150, 200),
            2: (255, 220, 150),
            3: (50, 100, 150),
            4: (150, 200, 100),
            5: (200, 150, 255),
            6: (200, 230, 255),
            7: (50, 100, 50),
            8: (50, 0, 100)
        }
        screen.fill(colors.get(self.current_world, BLUE))
        
        # Draw map
        self.current_map.draw(screen)
        
        # Draw title
        font = pygame.font.Font(None, 48)
        world_names = {
            1: "GRASS LAND",
            2: "DESERT LAND", 
            3: "WATER LAND",
            4: "GIANT LAND",
            5: "SKY LAND",
            6: "ICE LAND",
            7: "PIPE LAND",
            8: "DARK LAND"
        }
        
        title = font.render(f"WORLD {self.current_world} - {world_names[self.current_world]}", 
                          True, WHITE)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
        
        # Instructions
        inst_font = pygame.font.Font(None, 24)
        inst = inst_font.render("Arrow Keys: Move | Enter: Start Level | ESC: Quit", True, WHITE)
        screen.blit(inst, (SCREEN_WIDTH//2 - inst.get_width()//2, SCREEN_HEIGHT - 30))
        
    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.current_map.move('right')
            elif event.key == pygame.K_LEFT:
                self.current_map.move('left')
            elif event.key == pygame.K_RETURN:
                node = self.current_map.get_current_node()
                if node.unlocked and node.level_type in ['level', 'fortress', 'castle']:
                    return ('start_level', node)
        return None
        
    def complete_level(self):
        self.current_map.complete_current_level()
        
        # Check world completion
        all_complete = all(n.completed for n in self.current_map.nodes 
                          if n.level_type in ['level', 'fortress', 'castle'])
        
        if all_complete and self.current_world < 8:
            self.current_world += 1
            self.current_map = self.world_maps[self.current_world]

# Simple noise generator
class SimplexNoise:
    def __init__(self, seed=0):
        random.seed(seed)
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm *= 2
        
    def noise2d(self, x, y):
        xi = int(x)
        yi = int(y)
        xf = x - xi
        yf = y - yi
        
        aa = self.perm[(self.perm[xi % 256] + yi) % 256] / 128.0 - 1.0
        ba = self.perm[(self.perm[(xi+1) % 256] + yi) % 256] / 128.0 - 1.0
        ab = self.perm[(self.perm[xi % 256] + yi + 1) % 256] / 128.0 - 1.0
        bb = self.perm[(self.perm[(xi+1) % 256] + yi + 1) % 256] / 128.0 - 1.0
        
        x1 = aa + xf * (ba - aa)
        x2 = ab + xf * (bb - ab)
        return x1 + yf * (x2 - x1)

# AI Level Generator
class AILevelGenerator:
    def __init__(self, world_num, level_num):
        self.world_num = world_num
        self.level_num = level_num
        
        seed_str = f"{world_num}_{level_num}_{random.randint(0, 99999)}"
        self.seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        random.seed(self.seed)
        
        self.noise = SimplexNoise(self.seed)
        self.grid = [[TerrainType.EMPTY for _ in range(LEVEL_HEIGHT)] 
                     for _ in range(LEVEL_WIDTH)]
        
    def generate(self):
        # Generate base terrain
        ground_level = 18
        
        for x in range(LEVEL_WIDTH):
            noise_val = self.noise.noise2d(x * 0.1, 0)
            height = ground_level + int(noise_val * 3)
            height = max(12, min(20, height))
            
            for y in range(height, LEVEL_HEIGHT):
                self.grid[x][y] = TerrainType.GROUND
                
        # Add platforms
        for _ in range(20 + self.world_num * 5):
            x = random.randint(5, LEVEL_WIDTH - 10)
            y = random.randint(5, 15)
            width = random.randint(3, 8)
            
            for i in range(width):
                if x + i < LEVEL_WIDTH:
                    self.grid[x + i][y] = TerrainType.BRICK
                    
        # Add coins
        for _ in range(30):
            x = random.randint(5, LEVEL_WIDTH - 5)
            y = random.randint(5, 15)
            if self.grid[x][y] == TerrainType.EMPTY:
                self.grid[x][y] = TerrainType.COIN
                
        # Add enemies
        for _ in range(10 + self.world_num * 2):
            x = random.randint(10, LEVEL_WIDTH - 10)
            for y in range(LEVEL_HEIGHT - 1):
                if self.grid[x][y] == TerrainType.EMPTY and self.grid[x][y+1] != TerrainType.EMPTY:
                    self.grid[x][y] = TerrainType.ENEMY
                    break
                    
        # Add power-ups
        for _ in range(3):
            x = random.randint(20, LEVEL_WIDTH - 20)
            y = random.randint(8, 12)
            self.grid[x][y] = TerrainType.QUESTION
            
        return self.grid

# Dynamic Level
class DynamicLevel:
    def __init__(self, world_num, level_num):
        self.generator = AILevelGenerator(world_num, level_num)
        self.grid = self.generator.generate()
        
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.power_ups = []
        
        self.start_pos = (100, 400)
        self.goal_rect = pygame.Rect(LEVEL_WIDTH * TILE_SIZE - 100, 100, 50, 500)
        
        self._build_from_grid()
        
    def _build_from_grid(self):
        for x in range(LEVEL_WIDTH):
            for y in range(LEVEL_HEIGHT):
                tile = self.grid[x][y]
                world_x = x * TILE_SIZE
                world_y = y * TILE_SIZE
                
                if tile == TerrainType.GROUND:
                    self.platforms.append(Platform(world_x, world_y, TILE_SIZE, TILE_SIZE, 'ground'))
                elif tile == TerrainType.BRICK:
                    self.platforms.append(Platform(world_x, world_y, TILE_SIZE, TILE_SIZE, 'brick'))
                elif tile == TerrainType.QUESTION:
                    self.platforms.append(Platform(world_x, world_y, TILE_SIZE, TILE_SIZE, 'question'))
                    self.power_ups.append(PowerUp(world_x + TILE_SIZE//2, world_y - TILE_SIZE))
                elif tile == TerrainType.COIN:
                    self.coins.append(Coin(world_x + TILE_SIZE//2, world_y + TILE_SIZE//2))
                elif tile == TerrainType.ENEMY:
                    self.enemies.append(Enemy(world_x, world_y))
                    
    def update(self):
        for platform in self.platforms:
            if hasattr(platform, 'update'):
                platform.update()
                
    def draw(self, screen, camera_x):
        # Background
        screen.fill(BLUE)
        
        # Draw platforms
        for platform in self.platforms:
            if -100 <= platform.rect.x - camera_x <= SCREEN_WIDTH + 100:
                platform.draw(screen, camera_x)
                
        # Draw goal
        goal_draw = self.goal_rect.copy()
        goal_draw.x -= camera_x
        pygame.draw.rect(screen, BLACK, goal_draw)
        pygame.draw.polygon(screen, RED, [
            (goal_draw.right, goal_draw.top + 20),
            (goal_draw.right + 30, goal_draw.top + 30),
            (goal_draw.right, goal_draw.top + 40)
        ])

# Platform
class Platform:
    def __init__(self, x, y, width, height, platform_type='ground'):
        self.rect = pygame.Rect(x, y, width, height)
        self.type = platform_type
        
    def draw(self, screen, camera_x):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        
        colors = {
            'ground': GREEN,
            'brick': BROWN,
            'question': YELLOW,
            'pipe': DARK_GREEN
        }
        
        pygame.draw.rect(screen, colors.get(self.type, GRAY), draw_rect)
        
        if self.type == 'question':
            font = pygame.font.Font(None, 24)
            text = font.render('?', True, WHITE)
            text_rect = text.get_rect(center=draw_rect.center)
            screen.blit(text, text_rect)

# Player
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 40)
        self.vel_y = 0
        self.on_ground = False
        self.lives = 3
        self.coins = 0
        self.score = 0
        self.power_up = PowerUpType.NONE
        
    def update(self, platforms, enemies, coins, power_ups):
        keys = pygame.key.get_pressed()
        dx = 0
        
        if keys[pygame.K_LEFT]:
            dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            dx = PLAYER_SPEED
            
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            
        self.vel_y += GRAVITY
        if self.vel_y > 20:
            self.vel_y = 20
            
        # Horizontal movement
        self.rect.x += dx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if dx > 0:
                    self.rect.right = platform.rect.left
                elif dx < 0:
                    self.rect.left = platform.rect.right
                    
        # Vertical movement
        self.rect.y += self.vel_y
        self.on_ground = False
        
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0
                    
        # Enemy collision
        for enemy in enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    enemies.remove(enemy)
                    self.vel_y = JUMP_STRENGTH / 2
                    self.score += 100
                else:
                    self.lives -= 1
                    self.rect.x = 100
                    self.rect.y = 400
                    
        # Coin collection
        for coin in coins[:]:
            if self.rect.colliderect(coin.rect):
                coins.remove(coin)
                self.coins += 1
                self.score += 10
                
        # Power-up collection
        for power_up in power_ups[:]:
            if self.rect.colliderect(power_up.rect):
                self.power_up = PowerUpType.MUSHROOM
                power_ups.remove(power_up)
                self.score += 1000
                
    def draw(self, screen, camera_x):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        
        color = RED
        if self.power_up == PowerUpType.MUSHROOM:
            color = ORANGE
        elif self.power_up == PowerUpType.FIRE_FLOWER:
            color = ORANGE
            
        pygame.draw.rect(screen, color, draw_rect)

# Enemy
class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 25, 25)
        self.vel_x = random.choice([-ENEMY_SPEED, ENEMY_SPEED])
        self.vel_y = 0
        
    def update(self, platforms):
        self.rect.x += self.vel_x
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10
            
        self.rect.y += self.vel_y
        
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    
        if random.randint(0, 100) < 2:
            self.vel_x = -self.vel_x
            
    def draw(self, screen, camera_x):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        
        if -50 <= draw_rect.x <= SCREEN_WIDTH + 50:
            pygame.draw.rect(screen, BROWN, draw_rect)

# Coin
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 7, y - 7, 15, 15)
        self.animation = 0
        
    def update(self):
        self.animation += 0.1
        
    def draw(self, screen, camera_x):
        draw_x = self.rect.centerx - camera_x
        draw_y = self.rect.centery
        
        if -20 <= draw_x <= SCREEN_WIDTH + 20:
            pygame.draw.circle(screen, YELLOW, (draw_x, draw_y), 7)

# PowerUp
class PowerUp:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        
    def draw(self, screen, camera_x):
        draw_rect = self.rect.copy()
        draw_rect.x -= camera_x
        
        if -30 <= draw_rect.x <= SCREEN_WIDTH + 30:
            pygame.draw.rect(screen, RED, draw_rect)

# Main Game Class
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Mario Bros 3 - GBA Style")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
        self.state = GameState.OVERWORLD
        self.overworld = Overworld()
        self.player = Player(100, 400)
        self.camera_x = 0
        
        self.current_level = None
        self.current_node = None
        
    def start_level(self, node):
        self.current_node = node
        self.current_level = DynamicLevel(node.world_num, node.level_num)
        self.player.rect.x = self.current_level.start_pos[0]
        self.player.rect.y = self.current_level.start_pos[1]
        self.camera_x = 0
        self.state = GameState.LEVEL
        
    def update_camera(self):
        target_x = self.player.rect.x - SCREEN_WIDTH // 2
        self.camera_x += (target_x - self.camera_x) * 0.1
        max_x = LEVEL_WIDTH * TILE_SIZE - SCREEN_WIDTH
        self.camera_x = max(0, min(self.camera_x, max_x))
        
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == GameState.LEVEL:
                            self.state = GameState.OVERWORLD
                        else:
                            running = False
                            
                if self.state == GameState.OVERWORLD:
                    action = self.overworld.handle_input(event)
                    if action and action[0] == 'start_level':
                        self.start_level(action[1])
                        
            # Update
            if self.state == GameState.LEVEL:
                self.current_level.update()
                self.player.update(self.current_level.platforms,
                                  self.current_level.enemies,
                                  self.current_level.coins,
                                  self.current_level.power_ups)
                
                for enemy in self.current_level.enemies:
                    enemy.update(self.current_level.platforms)
                    
                for coin in self.current_level.coins:
                    coin.update()
                    
                self.update_camera()
                
                # Check goal
                if self.player.rect.colliderect(self.current_level.goal_rect):
                    self.player.score += 5000
                    self.overworld.complete_level()
                    self.state = GameState.OVERWORLD
                    
                # Check death
                if self.player.rect.top > SCREEN_HEIGHT:
                    self.player.lives -= 1
                    if self.player.lives > 0:
                        self.player.rect.x = self.current_level.start_pos[0]
                        self.player.rect.y = self.current_level.start_pos[1]
                    else:
                        self.state = GameState.GAME_OVER
                        
            # Draw
            if self.state == GameState.OVERWORLD:
                self.overworld.draw(self.screen)
                
            elif self.state == GameState.LEVEL:
                self.current_level.draw(self.screen, self.camera_x)
                
                for enemy in self.current_level.enemies:
                    enemy.draw(self.screen, self.camera_x)
                    
                for coin in self.current_level.coins:
                    coin.draw(self.screen, self.camera_x)
                    
                for power_up in self.current_level.power_ups:
                    power_up.draw(self.screen, self.camera_x)
                    
                self.player.draw(self.screen, self.camera_x)
                
                # HUD
                lives_text = self.font.render(f"Lives: {self.player.lives}", True, WHITE)
                self.screen.blit(lives_text, (10, 10))
                
                coins_text = self.font.render(f"Coins: {self.player.coins}", True, YELLOW)
                self.screen.blit(coins_text, (10, 50))
                
                score_text = self.font.render(f"Score: {self.player.score}", True, WHITE)
                self.screen.blit(score_text, (10, 90))
                
            elif self.state == GameState.GAME_OVER:
                self.screen.fill(BLACK)
                game_over_text = self.font.render("GAME OVER", True, RED)
                text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
                self.screen.blit(game_over_text, text_rect)
                
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
