import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Screen dimensions (NES resolution scaled up x2)
SCREEN_WIDTH = 512
SCREEN_HEIGHT = 448
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Super Mario Bros. 1 Clone")

# Colors (SMB1 NES palette accurate)
SKY_BLUE = (92, 148, 252)
BROWN = (172, 124, 0)
RED = (228, 92, 16)
GREEN = (0, 168, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (248, 216, 24)
SKIN = (248, 188, 168)
ORANGE = (248, 136, 24)  # For fire Mario
DARK_GREEN = (0, 104, 0)
LIGHT_BROWN = (212, 152, 0)
DARK_BROWN = (140, 100, 0)

# Game constants (tuned for SMB1 feel)
GRAVITY = 0.75  # SMB1 gravity
SCROLL_THRESH = 150
TILE_SIZE = 32
MARIO_WALK_SPEED = 4  # Fixed slow movement
MARIO_ACCEL = 0.3
JUMP_FORCE = -12  # SMB1 jump
MAX_VEL_Y = 12
INVINCIBLE_TIME = 120  # Frames after power down
LEVEL_TIME = 400  # SMB1 timer

# Create SMB1 sprites with more pixel-accurate drawings
def create_mario_sprite(power_state='small'):
    if power_state == 'small':
        surface = pygame.Surface((16, 16), pygame.SRCALPHA)
        # Improved small Mario facing right
        # Cap
        pygame.draw.rect(surface, RED, (2, 1, 3, 1))
        pygame.draw.rect(surface, RED, (1, 2, 5, 1))
        pygame.draw.rect(surface, RED, (1, 3, 4, 1))
        # Face
        pygame.draw.rect(surface, SKIN, (1, 4, 3, 1))
        pygame.draw.rect(surface, SKIN, (2, 5, 3, 1))
        pygame.draw.rect(surface, SKIN, (3, 6, 3, 1))
        # Eyes and mustache
        pygame.draw.rect(surface, BLACK, (4, 4, 1, 1))
        pygame.draw.rect(surface, BLACK, (2, 6, 2, 1))
        # Shirt
        pygame.draw.rect(surface, RED, (2, 7, 4, 1))
        pygame.draw.rect(surface, RED, (1, 8, 6, 1))
        pygame.draw.rect(surface, RED, (1, 9, 3, 1))
        pygame.draw.rect(surface, RED, (5, 9, 1, 1))
        # Arms
        pygame.draw.rect(surface, SKIN, (4, 8, 2, 1))
        pygame.draw.rect(surface, SKIN, (6, 9, 1, 1))
        # Pants
        pygame.draw.rect(surface, RED, (2, 10, 3, 3))
        # Shoes
        pygame.draw.rect(surface, BLACK, (1, 13, 4, 1))
        pygame.draw.rect(surface, BLACK, (4, 12, 2, 1))
    else:
        surface = pygame.Surface((16, 32), pygame.SRCALPHA)
        if power_state == 'fire':
            cap_color = WHITE
            overall_color = ORANGE
            shirt_color = ORANGE
        else:
            cap_color = RED
            overall_color = RED
            shirt_color = RED
        # Improved super/fire Mario facing right
        # Cap
        pygame.draw.rect(surface, cap_color, (2, 2, 4, 1))
        pygame.draw.rect(surface, cap_color, (1, 3, 6, 1))
        pygame.draw.rect(surface, cap_color, (1, 4, 5, 1))
        # Face
        pygame.draw.rect(surface, SKIN, (1, 5, 4, 1))
        pygame.draw.rect(surface, SKIN, (1, 6, 5, 1))
        pygame.draw.rect(surface, SKIN, (3, 7, 3, 1))
        pygame.draw.rect(surface, SKIN, (3, 8, 3, 1))
        # Eyes and mustache
        pygame.draw.rect(surface, BLACK, (5, 5, 1, 1))
        pygame.draw.rect(surface, BLACK, (2, 7, 2, 1))
        pygame.draw.rect(surface, BLACK, (2, 8, 2, 1))
        # Shirt
        pygame.draw.rect(surface, shirt_color, (2, 9, 4, 2))
        pygame.draw.rect(surface, shirt_color, (1, 11, 6, 3))
        # Buttons
        pygame.draw.rect(surface, YELLOW, (3, 11, 1, 1))
        pygame.draw.rect(surface, YELLOW, (4, 13, 1, 1))
        # Arms
        pygame.draw.rect(surface, SKIN, (6, 9, 1, 2))
        pygame.draw.rect(surface, SKIN, (0, 10, 1, 2))
        # Overalls
        pygame.draw.rect(surface, overall_color, (2, 14, 4, 5))
        pygame.draw.rect(surface, overall_color, (1, 19, 6, 4))
        # Shoes
        pygame.draw.rect(surface, BLACK, (1, 23, 4, 1))
        pygame.draw.rect(surface, BLACK, (5, 22, 2, 1))
        pygame.draw.rect(surface, BLACK, (3, 24, 3, 1))
    return pygame.transform.scale(surface, (surface.get_width() * 2, surface.get_height() * 2))

def create_goomba_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Improved Goomba
    pygame.draw.ellipse(surface, BROWN, (0, 4, 16, 10))
    pygame.draw.rect(surface, DARK_BROWN, (0, 8, 16, 2))
    # Feet
    pygame.draw.rect(surface, BLACK, (2, 14, 4, 2))
    pygame.draw.rect(surface, BLACK, (10, 14, 4, 2))
    # Eyes
    pygame.draw.rect(surface, WHITE, (4, 6, 2, 2))
    pygame.draw.rect(surface, WHITE, (10, 6, 2, 2))
    pygame.draw.rect(surface, BLACK, (5, 7, 1, 1))
    pygame.draw.rect(surface, BLACK, (11, 7, 1, 1))
    # Eyebrows
    pygame.draw.rect(surface, BLACK, (3, 5, 4, 1))
    pygame.draw.rect(surface, BLACK, (9, 5, 4, 1))
    return pygame.transform.scale(surface, (32, 32))

def create_block_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Improved brick block
    pygame.draw.rect(surface, BROWN, (0, 0, 16, 16))
    pygame.draw.line(surface, LIGHT_BROWN, (0, 0), (15, 0))
    pygame.draw.line(surface, LIGHT_BROWN, (0, 0), (0, 15))
    pygame.draw.line(surface, DARK_BROWN, (15, 0), (15, 15))
    pygame.draw.line(surface, DARK_BROWN, (0, 15), (15, 15))
    pygame.draw.rect(surface, DARK_BROWN, (4, 4, 2, 2))
    pygame.draw.rect(surface, LIGHT_BROWN, (8, 8, 2, 2))
    return pygame.transform.scale(surface, (32, 32))

def create_question_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    # SMB1 ? block
    pygame.draw.rect(surface, ORANGE, (0, 0, 16, 16))
    pygame.draw.line(surface, YELLOW, (0, 0), (15, 0))
    pygame.draw.line(surface, YELLOW, (0, 0), (0, 15))
    pygame.draw.line(surface, DARK_BROWN, (15, 0), (15, 15))
    pygame.draw.line(surface, DARK_BROWN, (0, 15), (15, 15))
    # ? sign
    pygame.draw.rect(surface, WHITE, (5, 2, 6, 2))
    pygame.draw.rect(surface, WHITE, (3, 4, 2, 2))
    pygame.draw.rect(surface, WHITE, (9, 4, 2, 2))
    pygame.draw.rect(surface, WHITE, (7, 6, 4, 2))
    pygame.draw.rect(surface, WHITE, (3, 8, 2, 2))
    pygame.draw.rect(surface, WHITE, (5, 10, 2, 2))
    pygame.draw.rect(surface, WHITE, (9, 10, 2, 2))
    return pygame.transform.scale(surface, (32, 32))

def create_used_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Used block
    pygame.draw.rect(surface, DARK_BROWN, (0, 0, 16, 16))
    pygame.draw.line(surface, BROWN, (0, 0), (15, 0))
    pygame.draw.line(surface, BROWN, (0, 0), (0, 15))
    pygame.draw.line(surface, BLACK, (15, 0), (15, 15))
    pygame.draw.line(surface, BLACK, (0, 15), (15, 15))
    return pygame.transform.scale(surface, (32, 32))

def create_coin_sprite():
    surface = pygame.Surface((8, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(surface, YELLOW, (0, 0, 8, 14))
    pygame.draw.ellipse(surface, WHITE, (1, 1, 6, 12))
    pygame.draw.rect(surface, YELLOW, (2, 5, 4, 4))
    return pygame.transform.scale(surface, (16, 28))

def create_mushroom_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Mushroom powerup
    pygame.draw.rect(surface, RED, (4, 0, 8, 8))
    pygame.draw.rect(surface, WHITE, (2, 8, 12, 8))
    # Spots
    pygame.draw.circle(surface, WHITE, (6, 4), 2)
    pygame.draw.circle(surface, WHITE, (10, 4), 2)
    # Eyes
    pygame.draw.rect(surface, BLACK, (6, 10, 2, 2))
    pygame.draw.rect(surface, BLACK, (10, 10, 2, 2))
    return pygame.transform.scale(surface, (32, 32))

def create_pipe_sprite():
    surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(surface, GREEN, (0, 0, 32, 32))
    pygame.draw.rect(surface, DARK_GREEN, (0, 0, 32, 4))
    pygame.draw.rect(surface, DARK_GREEN, (0, 0, 4, 32))
    pygame.draw.rect(surface, LIGHT_BROWN, (4, 4, 24, 24))
    return pygame.transform.scale(surface, (64, 64))

def create_ground_sprite():
    surface = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.rect(surface, BROWN, (0, 0, 16, 16))
    pygame.draw.line(surface, LIGHT_BROWN, (0, 0), (15, 0))
    pygame.draw.line(surface, LIGHT_BROWN, (0, 0), (0, 15))
    pygame.draw.rect(surface, DARK_BROWN, (4, 4, 2, 2))
    return pygame.transform.scale(surface, (32, 32))

def create_flag_sprite():
    surface = pygame.Surface((16, 32), pygame.SRCALPHA)
    # Pole
    pygame.draw.rect(surface, WHITE, (8, 0, 2, 32))
    # Flag rect
    pygame.draw.rect(surface, GREEN, (0, 0, 8, 8))
    # Flag triangle approximation using lines
    pygame.draw.lines(surface, GREEN, True, [(0, 0), (8, 0), (4, 4)], 1)
    return pygame.transform.scale(surface, (32, 64))

# Player class
class Player:
    def __init__(self, x, y):
        self.power_state = 'small'
        self.image = create_mario_sprite(self.power_state)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        self.vel_y = 0
        self.vel_x = 0
        self.jumped = False
        self.in_air = True
        self.flip = False
        self.score = 0
        self.lives = 3
        self.coins = 0
        self.level_complete = False
        self.spawn_x = x
        self.spawn_y = y
        self.death_timer = 0
        self.invincible_timer = 0
        self.jump_counter = 0

    def update(self, platforms, enemies, coins, pipes, flag, blocks, powerups):
        if self.death_timer > 0:
            self.death_timer -= 1
            if self.death_timer <= 0:
                self.rect.x = self.spawn_x
                self.rect.y = self.spawn_y
                self.vel_y = 0
                self.vel_x = 0
                self.in_air = True
                self.power_state = 'small'
                self.update_sprite()
            return "playing"

        dx = 0
        dy = 0

        # Controls
        key = pygame.key.get_pressed()
        if key[pygame.K_LEFT]:
            self.vel_x = max(self.vel_x - MARIO_ACCEL, -MARIO_WALK_SPEED)
            self.flip = True
        elif key[pygame.K_RIGHT]:
            self.vel_x = min(self.vel_x + MARIO_ACCEL, MARIO_WALK_SPEED)
            self.flip = False
        else:
            self.vel_x *= 0.9  # Improved deceleration
        if key[pygame.K_SPACE] and not self.jumped and not self.in_air:
            self.vel_y = JUMP_FORCE
            self.jumped = True
            self.in_air = True
            self.jump_counter = 1
        if key[pygame.K_SPACE] and self.in_air and self.jump_counter < 5:  # Variable jump height
            self.vel_y -= 1.0  # Add upward force while holding
            self.jump_counter += 1
        if not key[pygame.K_SPACE]:
            self.jumped = False

        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_VEL_Y:
            self.vel_y = MAX_VEL_Y
        dy += self.vel_y
        dx += self.vel_x

        # Invincible timer
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        # Collisions with platforms and blocks
        self.in_air = True
        collidables = platforms + blocks + pipes
        for tile in collidables:
            # X collision
            if tile.rect.colliderect(self.rect.x + dx, self.rect.y, self.width, self.height):
                dx = 0
            # Y collision
            if tile.rect.colliderect(self.rect.x, self.rect.y + dy, self.width, self.height):
                if self.vel_y < 0:  # Hitting head
                    dy = tile.rect.bottom - self.rect.top
                    self.vel_y = 0
                    if hasattr(tile, 'hit'):
                        tile.hit(self, powerups)
                elif self.vel_y >= 0:  # Landing
                    dy = tile.rect.top - self.rect.bottom
                    self.vel_y = 0
                    self.in_air = False
                    self.jump_counter = 0

        # Enemy collisions
        for enemy in enemies[:]:
            if enemy.rect.colliderect(self.rect.x + dx, self.rect.y + dy, self.width, self.height):
                if self.invincible_timer > 0:
                    continue
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    enemies.remove(enemy)
                    self.vel_y = -8
                    self.score += 100
                else:
                    if self.power_state != 'small':
                        self.power_state = 'small'
                        self.invincible_timer = INVINCIBLE_TIME
                        self.update_sprite()
                        self.rect.y += 32  # Adjust position when shrinking
                    else:
                        self.lives -= 1
                        enemies.remove(enemy)
                        self.death_timer = 60
                        if self.lives <= 0:
                            return "game_over"
                        return "playing"

        # Coin collisions
        for coin in coins[:]:
            if coin.rect.colliderect(self.rect):
                coins.remove(coin)
                self.score += 200
                self.coins += 1
                if self.coins >= 100:
                    self.lives += 1
                    self.coins = 0

        # Powerup collisions
        for powerup in powerups[:]:
            if powerup.rect.colliderect(self.rect):
                if self.power_state == 'small':
                    self.power_state = 'super'
                    self.update_sprite()
                    self.rect.y -= 32  # Grow upwards
                powerups.remove(powerup)
                self.score += 1000

        # Flag collision
        if flag.rect.colliderect(self.rect):
            self.level_complete = True
            return "level_complete"

        # Update position
        self.rect.x += dx
        self.rect.y += dy

        # Bounds
        if self.rect.left < 0:
            self.rect.left = 0
            self.vel_x = 0
        if self.rect.bottom > SCREEN_HEIGHT:
            self.lives -= 1
            self.death_timer = 60
            if self.lives <= 0:
                return "game_over"

        return "playing"

    def update_sprite(self):
        self.image = create_mario_sprite(self.power_state)
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        self.rect.size = (self.width, self.height)

    def draw(self, screen, scroll):
        if self.invincible_timer > 0 and self.invincible_timer % 4 < 2:
            return  # Flash by not drawing
        screen.blit(pygame.transform.flip(self.image, self.flip, False), (self.rect.x - scroll, self.rect.y))

# Platform class
class Platform:
    def __init__(self, x, y, width, height, is_ground=False):
        self.image = pygame.Surface((width, height))
        tile = create_ground_sprite() if is_ground else create_block_sprite()
        for i in range(0, width, TILE_SIZE):
            for j in range(0, height, TILE_SIZE):
                self.image.blit(tile, (i, j))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Block class
class Block:
    def __init__(self, x, y, type='question', content='coin'):
        self.type = type
        self.state = 'normal'
        self.content = content
        self.image = create_question_sprite() if type == 'question' else create_block_sprite()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def hit(self, player, powerups):
        if self.state == 'used':
            return
        if self.type == 'brick':
            if player.power_state != 'small':
                # Destroy
                return
            # Bounce
            return
        elif self.type == 'question':
            self.state = 'used'
            self.image = create_used_sprite()
            if self.content == 'coin':
                player.score += 200
                player.coins += 1
            elif self.content == 'mushroom':
                powerups.append(Powerup('mushroom', self.rect.x, self.rect.y - TILE_SIZE))

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Enemy class (Goomba)
class Enemy:
    def __init__(self, x, y):
        self.image = create_goomba_sprite()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = -1  # Initial direction
        self.vel_y = 0
        self.in_air = True

    def update(self, scroll, collidables):
        dx = self.vel_x
        dy = self.vel_y

        self.vel_y += GRAVITY
        if self.vel_y > MAX_VEL_Y:
            self.vel_y = MAX_VEL_Y
        dy += self.vel_y

        self.in_air = True
        for tile in collidables:
            if tile.rect.colliderect(self.rect.x + dx, self.rect.y, self.image.get_width(), self.image.get_height()):
                dx = 0
                self.vel_x *= -1  # Reverse direction on wall
            if tile.rect.colliderect(self.rect.x, self.rect.y + dy, self.image.get_width(), self.image.get_height()):
                if self.vel_y < 0:
                    dy = tile.rect.bottom - self.rect.top
                    self.vel_y = 0
                elif self.vel_y >= 0:
                    dy = tile.rect.top - self.rect.bottom
                    self.vel_y = 0
                    self.in_air = False

        self.rect.x += dx
        self.rect.y += dy

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Coin class
class Coin:
    def __init__(self, x, y):
        self.image = create_coin_sprite()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.animation_counter = 0

    def update(self):
        self.animation_counter += 0.2
        if self.animation_counter >= 4:
            self.animation_counter = 0

    def draw(self, screen, scroll):
        frame = int(self.animation_counter) % 4
        img = pygame.transform.rotate(self.image, frame * 90)
        screen.blit(img, (self.rect.x - scroll, self.rect.y))

# Powerup class
class Powerup:
    def __init__(self, type, x, y):
        self.type = type
        self.image = create_mushroom_sprite()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = 2
        self.vel_y = 0
        self.in_air = True

    def update(self, collidables):
        dx = self.vel_x
        dy = self.vel_y

        self.vel_y += GRAVITY
        dy += self.vel_y

        for tile in collidables:
            if tile.rect.colliderect(self.rect.x + dx, self.rect.y, self.image.get_width(), self.image.get_height()):
                self.vel_x *= -1
            if tile.rect.colliderect(self.rect.x, self.rect.y + dy, self.image.get_width(), self.image.get_height()):
                if self.vel_y < 0:
                    dy = tile.rect.bottom - self.rect.top
                    self.vel_y = 0
                elif self.vel_y >= 0:
                    dy = tile.rect.top - self.rect.bottom
                    self.vel_y = 0
                    self.in_air = False

        self.rect.x += dx
        self.rect.y += dy

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Pipe class
class Pipe:
    def __init__(self, x, y, height):
        self.image = pygame.Surface((64, height))
        pipe_top = create_pipe_sprite()
        pipe_body = pygame.Surface((64, 32))
        pipe_body.fill(GREEN)
        self.image.blit(pipe_top, (0, 0))
        for i in range(64, height, 32):
            self.image.blit(pipe_body, (0, i))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Flag class
class Flag:
    def __init__(self, x, y):
        self.image = create_flag_sprite()
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def draw(self, screen, scroll):
        screen.blit(self.image, (self.rect.x - scroll, self.rect.y))

# Create level
def create_level():
    platforms = []
    blocks = []
    enemies = []
    coins = []
    pipes = []
    powerups = []

    # Ground
    for i in range(100):
        platforms.append(Platform(i * TILE_SIZE, SCREEN_HEIGHT - 64, TILE_SIZE, 64, True))

    # Floating platforms
    platforms.append(Platform(10 * TILE_SIZE, 320, 4 * TILE_SIZE, 32))
    platforms.append(Platform(16 * TILE_SIZE, 256, 4 * TILE_SIZE, 32))
    platforms.append(Platform(22 * TILE_SIZE, 192, 4 * TILE_SIZE, 32))

    # Question blocks
    blocks.append(Block(12 * TILE_SIZE, 256, 'question', 'mushroom'))
    blocks.append(Block(18 * TILE_SIZE, 192, 'question', 'coin'))

    # Pipes
    pipes.append(Pipe(18 * TILE_SIZE, SCREEN_HEIGHT - 128, 64))
    pipes.append(Pipe(28 * TILE_SIZE, SCREEN_HEIGHT - 160, 96))

    # Enemies
    enemies.append(Enemy(12 * TILE_SIZE, SCREEN_HEIGHT - 96))
    enemies.append(Enemy(20 * TILE_SIZE, SCREEN_HEIGHT - 96))
    enemies.append(Enemy(30 * TILE_SIZE, SCREEN_HEIGHT - 96))

    # Coins
    for i in range(8):
        coins.append(Coin(8 * TILE_SIZE + i * 64, 256))
        coins.append(Coin(24 * TILE_SIZE + i * 64, 192))

    flag = Flag(50 * TILE_SIZE, SCREEN_HEIGHT - 128)

    return platforms, blocks, enemies, coins, pipes, flag, powerups

# Draw text
def draw_text(text, font, color, x, y):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

# Clouds
def draw_clouds(scroll):
    for i in range(6):
        pygame.draw.ellipse(screen, WHITE, (i * 300 - scroll // 2, 80, 80, 40))
        pygame.draw.ellipse(screen, WHITE, (i * 300 + 40 - scroll // 2, 60, 60, 50))
        pygame.draw.ellipse(screen, WHITE, (i * 300 + 20 - scroll // 2, 100, 60, 30))

# Main game loop
def main():
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24)

    player = Player(100, SCREEN_HEIGHT - 128)
    platforms, blocks, enemies, coins, pipes, flag, powerups = create_level()

    scroll = 0
    game_state = "playing"
    level = 1
    max_levels = 32
    time_left = LEVEL_TIME
    frame_counter = 0

    running = True
    while running:
        clock.tick(60)
        frame_counter += 1
        if frame_counter % 60 == 0 and game_state == "playing":
            time_left -= 1
            if time_left <= 0:
                player.lives -= 1
                player.death_timer = 60
                if player.lives <= 0:
                    game_state = "game_over"

        screen.fill(SKY_BLUE)
        draw_clouds(scroll)

        for platform in platforms:
            platform.draw(screen, scroll)
        for block in blocks:
            block.draw(screen, scroll)
        for pipe in pipes:
            pipe.draw(screen, scroll)
        for coin in coins:
            coin.update()
            coin.draw(screen, scroll)
        for enemy in enemies:
            enemy.update(scroll, platforms + blocks + pipes)
            enemy.draw(screen, scroll)
        for powerup in powerups:
            powerup.update(platforms + blocks + pipes)
            powerup.draw(screen, scroll)
        flag.draw(screen, scroll)
        player.draw(screen, scroll)

        # HUD
        pygame.draw.rect(screen, BLACK, (0, 0, SCREEN_WIDTH, 40))
        draw_text(f"MARIO {player.score:06d}", font, WHITE, 20, 10)
        draw_text(f"x{player.coins:02d}", font, WHITE, 180, 10)
        draw_text(f"WORLD 1-{level}", font, WHITE, 280, 10)
        draw_text(f"TIME {time_left:03d}", font, WHITE, 380, 10)
        draw_text(f"x{player.lives:02d}", font, WHITE, 460, 10)

        if game_state == "playing":
            game_state = player.update(platforms, enemies, coins, pipes, flag, blocks, powerups)

            if player.rect.right > SCREEN_WIDTH - SCROLL_THRESH and scroll < (len(platforms) * TILE_SIZE) - SCREEN_WIDTH:
                scroll += player.vel_x
            if player.rect.left < SCROLL_THRESH and scroll > 0:
                scroll += player.vel_x

        elif game_state == "level_complete":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            draw_text("COURSE CLEAR!", font, WHITE, 180, 150)
            draw_text("Press SPACE to continue", font, WHITE, 140, 200)

            key = pygame.key.get_pressed()
            if key[pygame.K_SPACE]:
                level += 1
                if level > max_levels:
                    game_state = "game_complete"
                else:
                    platforms, blocks, enemies, coins, pipes, flag, powerups = create_level()
                    player.rect.x = 100
                    player.rect.y = SCREEN_HEIGHT - 128
                    player.vel_x = 0
                    player.vel_y = 0
                    scroll = 0
                    time_left = LEVEL_TIME
                    game_state = "playing"

        elif game_state == "game_over":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            draw_text("GAME OVER", font, WHITE, 200, 150)
            draw_text("Press SPACE to restart", font, WHITE, 160, 200)

            key = pygame.key.get_pressed()
            if key[pygame.K_SPACE]:
                player = Player(100, SCREEN_HEIGHT - 128)
                platforms, blocks, enemies, coins, pipes, flag, powerups = create_level()
                scroll = 0
                level = 1
                time_left = LEVEL_TIME
                game_state = "playing"

        elif game_state == "game_complete":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            draw_text("THANKS FOR PLAYING!", font, WHITE, 160, 150)
            draw_text("Press SPACE to restart", font, WHITE, 160, 200)

            key = pygame.key.get_pressed()
            if key[pygame.K_SPACE]:
                player = Player(100, SCREEN_HEIGHT - 128)
                platforms, blocks, enemies, coins, pipes, flag, powerups = create_level()
                scroll = 0
                level = 1
                time_left = LEVEL_TIME
                game_state = "playing"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()

        pygame.display.update()

if __name__ == "__main__":
    main()
