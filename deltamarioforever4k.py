import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
WIDTH = 800
HEIGHT = 600
FPS = 60
GRAVITY = 0.5
JUMP_HEIGHT = -12
PLAYER_SPEED = 5
ENEMY_SPEED = 2

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
SKIN = (255, 222, 173)
YELLOW = (255, 255, 0)
TRANSPARENT = (0, 0, 0, 0)  # For alpha

# Screen setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mario Forever 6.0 - Simple Edition (5 Worlds)")
clock = pygame.time.Clock()

# Function to create pixel art surface
def create_pixel_art(pixels, color_map, scale=2):
    height = len(pixels)
    width = len(pixels[0]) if height > 0 else 0
    surf = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    for y in range(height):
        for x in range(width):
            color_key = pixels[y][x]
            color = color_map.get(color_key, TRANSPARENT)
            pygame.draw.rect(surf, color, (x * scale, y * scale, scale, scale))
    return surf

# Player class with baked-in sprite
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Simple Mario-like pixel art (16x32)
        pixels = [
            [0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
            [0,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0],
            [0,0,0,0,2,2,2,3,3,2,3,0,0,0,0,0],
            [0,0,0,2,3,2,3,3,3,2,3,3,3,0,0,0],
            [0,0,0,2,3,2,3,3,3,3,2,3,3,3,0,0],
            [0,0,0,2,2,3,3,3,3,3,2,2,2,0,0,0],
            [0,0,0,0,0,3,3,3,3,3,0,0,0,0,0,0],
            [0,0,0,0,1,1,4,4,4,1,1,0,0,0,0,0],
            [0,0,0,1,1,1,4,4,4,1,1,1,0,0,0,0],
            [0,0,1,1,1,1,4,4,4,1,1,1,1,0,0,0],
            [0,0,5,5,1,4,4,4,4,4,1,5,5,0,0,0],
            [0,5,5,5,4,4,4,4,4,4,4,5,5,5,0,0],
            [0,5,5,4,4,4,4,4,4,4,4,4,5,5,0,0],
            [0,5,5,5,0,4,4,4,4,0,5,5,5,0,0,0],
            [0,0,5,0,0,6,6,6,6,0,0,5,0,0,0,0],
            [0,0,0,0,6,6,6,6,6,6,0,0,0,0,0,0],
            [0,0,0,0,6,6,6,6,6,6,0,0,0,0,0,0],
            [0,0,0,1,1,1,0,0,1,1,1,0,0,0,0,0],
            [0,0,1,1,1,1,0,0,1,1,1,1,0,0,0,0],
            [0,1,1,1,1,1,0,0,1,1,1,1,1,0,0,0],
            [0,3,3,1,1,0,0,0,0,1,1,3,3,0,0,0],
            [0,3,3,3,0,0,0,0,0,0,3,3,3,0,0,0],
            [0,3,3,0,0,0,0,0,0,0,0,3,3,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
        ]
        color_map = {
            0: TRANSPARENT,
            1: RED,    # Hat, shirt
            2: BROWN,  # Hair
            3: SKIN,   # Face, hands
            4: BLUE,   # Overalls
            5: YELLOW, # Buttons, shoes
            6: BLACK,  # Eyes, mustache
        }
        self.image = create_pixel_art(pixels, color_map, scale=2)  # 32x64
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = HEIGHT - self.rect.height - 20  # Adjust for ground
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = True
        self.alive = True

    def update(self, platforms, enemies):
        # Apply gravity
        if not self.on_ground:
            self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        # Check vertical collisions
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect) and self.vel_y >= 0 and self.rect.bottom <= platform.rect.top + 10:
                self.rect.bottom = platform.rect.top
                self.vel_y = 0
                self.on_ground = True
        # Horizontal movement
        self.rect.x += self.vel_x
        # Check horizontal collisions
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_x > 0:
                    self.rect.right = platform.rect.left
                elif self.vel_x < 0:
                    self.rect.left = platform.rect.right
        # Check enemy collisions
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.bottom:  # Stomp
                    enemy.kill()
                else:
                    self.alive = False
        # Boundaries
        if self.rect.top > HEIGHT:
            self.alive = False
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH

# Platform class with baked-in tile pattern
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        # Simple brick-like pattern (16x16 tile)
        tile_pixels = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]
        color_map = {
            0: BROWN,
            1: RED,
        }
        tile = create_pixel_art(tile_pixels, color_map, scale=1)
        self.image = pygame.Surface((w, h))
        for tx in range(0, w, 16):
            for ty in range(0, h, 16):
                self.image.blit(tile, (tx, ty))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Enemy class with baked-in sprite (Goomba-like)
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, direction=1):
        super().__init__()
        # Simple Goomba pixel art (16x16)
        pixels = [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0],
            [0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
            [0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0],
            [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0],
            [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
            [0,1,1,2,2,1,1,1,1,1,2,2,1,1,0,0],
            [0,1,2,3,3,2,1,1,1,2,3,3,2,1,0,0],
            [1,1,2,3,3,3,2,2,2,3,3,3,2,1,1,0],
            [1,1,2,3,3,3,3,3,3,3,3,3,2,1,1,0],
            [1,1,1,2,3,3,3,3,3,3,3,2,1,1,1,0],
            [0,1,1,1,2,2,2,2,2,2,2,1,1,1,0,0],
            [0,0,1,1,1,0,0,0,0,0,1,1,1,0,0,0],
            [0,0,0,4,4,0,0,0,0,0,4,4,0,0,0,0],
            [0,0,4,4,4,4,0,0,0,4,4,4,4,0,0,0],
            [0,4,4,4,4,4,4,0,4,4,4,4,4,4,0,0],
        ]
        color_map = {
            0: TRANSPARENT,
            1: BROWN,  # Body
            2: BLACK,  # Eyes
            3: WHITE,  # Eye shine
            4: YELLOW, # Feet
        }
        self.image = create_pixel_art(pixels, color_map, scale=2)  # 32x32
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y - self.rect.height + 20  # Adjust to ground
        self.direction = direction

    def update(self, platforms):
        self.rect.x += self.direction * ENEMY_SPEED
        # Check for platform edges
        future_rect = self.rect.copy()
        future_rect.x += self.direction * ENEMY_SPEED
        on_platform = False
        for platform in platforms:
            if future_rect.colliderect(platform.rect):
                if self.direction > 0:
                    self.rect.right = platform.rect.left
                else:
                    self.rect.left = platform.rect.right
                self.direction *= -1
                on_platform = True
        if not on_platform:
            self.direction *= -1  # Turn around if no platform ahead

# Goal class with baked-in flagpole-like
class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        # Simple flagpole (8x40)
        pixels = [
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [0,1,1,0,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
            [2,2,2,2,0,0,0,0],
        ]
        color_map = {
            0: TRANSPARENT,
            1: GREEN,  # Pole
            2: RED,    # Flag
        }
        self.image = create_pixel_art(pixels, color_map, scale=1)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y - self.rect.height + 40  # Adjust

# Define 5 worlds (levels) with platforms, enemies, goal
# Adjusted y positions for new sprite sizes
worlds = [
    # World 1: Simple ground level
    {
        'platforms': [
            Platform(0, HEIGHT - 20, WIDTH, 20),  # Ground
            Platform(200, HEIGHT - 100, 100, 20),
            Platform(400, HEIGHT - 200, 100, 20),
        ],
        'enemies': [
            Enemy(300, HEIGHT - 20),
        ],
        'goal': Goal(WIDTH - 50, HEIGHT),
    },
    # World 2: More platforms
    {
        'platforms': [
            Platform(0, HEIGHT - 20, WIDTH, 20),
            Platform(100, HEIGHT - 150, 150, 20),
            Platform(300, HEIGHT - 250, 100, 20),
            Platform(500, HEIGHT - 100, 200, 20),
        ],
        'enemies': [
            Enemy(150, HEIGHT - 150),
            Enemy(350, HEIGHT - 250),
        ],
        'goal': Goal(WIDTH - 50, HEIGHT),
    },
    # World 3: Higher jumps needed
    {
        'platforms': [
            Platform(0, HEIGHT - 20, WIDTH, 20),
            Platform(50, HEIGHT - 300, 100, 20),
            Platform(200, HEIGHT - 200, 150, 20),
            Platform(400, HEIGHT - 350, 100, 20),
            Platform(550, HEIGHT - 150, 200, 20),
        ],
        'enemies': [
            Enemy(250, HEIGHT - 200),
            Enemy(450, HEIGHT - 350),
        ],
        'goal': Goal(WIDTH - 50, HEIGHT - 150 + 20),
    },
    # World 4: More enemies
    {
        'platforms': [
            Platform(0, HEIGHT - 20, WIDTH, 20),
            Platform(100, HEIGHT - 100, 100, 20),
            Platform(250, HEIGHT - 200, 150, 20),
            Platform(450, HEIGHT - 300, 100, 20),
            Platform(600, HEIGHT - 150, 150, 20),
        ],
        'enemies': [
            Enemy(150, HEIGHT - 100),
            Enemy(300, HEIGHT - 200),
            Enemy(500, HEIGHT - 300),
            Enemy(650, HEIGHT - 150),
        ],
        'goal': Goal(WIDTH - 50, HEIGHT),
    },
    # World 5: Challenging layout
    {
        'platforms': [
            Platform(0, HEIGHT - 20, WIDTH, 20),
            Platform(50, HEIGHT - 250, 50, 20),
            Platform(150, HEIGHT - 350, 100, 20),
            Platform(300, HEIGHT - 150, 50, 20),
            Platform(400, HEIGHT - 300, 150, 20),
            Platform(600, HEIGHT - 200, 100, 20),
        ],
        'enemies': [
            Enemy(100, HEIGHT - 250),
            Enemy(200, HEIGHT - 350),
            Enemy(350, HEIGHT - 150),
            Enemy(450, HEIGHT - 300),
            Enemy(650, HEIGHT - 200),
        ],
        'goal': Goal(WIDTH - 50, HEIGHT - 200 + 20),
    },
]

# Main game loop
def main():
    current_world = 0
    player = Player()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)

    running = True
    while running:
        # Load current world
        platforms = pygame.sprite.Group()
        enemies = pygame.sprite.Group()
        goal = worlds[current_world]['goal']
        for p in worlds[current_world]['platforms']:
            platforms.add(p)
            all_sprites.add(p)
        for e in worlds[current_world]['enemies']:
            enemies.add(e)
            all_sprites.add(e)
        all_sprites.add(goal)

        level_running = True
        while level_running and running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and player.on_ground:
                        player.vel_y = JUMP_HEIGHT
                        player.on_ground = False

            # Player movement
            keys = pygame.key.get_pressed()
            player.vel_x = 0
            if keys[pygame.K_LEFT]:
                player.vel_x = -PLAYER_SPEED
            if keys[pygame.K_RIGHT]:
                player.vel_x = PLAYER_SPEED

            # Update
            player.update(platforms, enemies)
            for enemy in enemies:
                enemy.update(platforms)

            # Check for death
            if not player.alive:
                level_running = False  # Restart level
                player.rect.x = 50
                player.rect.y = HEIGHT - player.rect.height - 20
                player.alive = True
                player.vel_y = 0

            # Check for goal
            if player.rect.colliderect(goal.rect):
                current_world += 1
                if current_world >= len(worlds):
                    print("You won!")
                    running = False
                else:
                    player.rect.x = 50
                    player.rect.y = HEIGHT - player.rect.height - 20
                    level_running = False

            # Draw
            screen.fill(BLUE)  # Sky background
            all_sprites.draw(screen)
            pygame.display.flip()
            clock.tick(FPS)

        # Remove level sprites
        for sprite in list(all_sprites):
            if sprite != player:
                all_sprites.remove(sprite)
                sprite.kill()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
