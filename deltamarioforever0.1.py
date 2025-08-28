import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
JUMP_HEIGHT = -15
PLAYER_SPEED = 5

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
LAVA_RED = (255, 69, 0)
SKY_BLUE = (135, 206, 235)
MARIO_RED = (255, 0, 0)
MARIO_BLUE = (0, 0, 255)
MARIO_SKIN = (255, 220, 177)
GOOMBA_BROWN = (139, 69, 19)
GOOMBA_BLACK = (0, 0, 0)
GOOMBA_WHITE = (255, 255, 255)
BOWSER_GREEN = (0, 128, 0)
BOWSER_YELLOW = (255, 255, 0)
BOWSER_ORANGE = (255, 165, 0)
CLOUD_WHITE = (240, 240, 240)
SUN_YELLOW = (255, 255, 0)
HILL_GREEN = (34, 139, 34)
BRICK_RED = (205, 92, 92)
DIRT_BROWN = (139, 69, 19)
LAVA_ORANGE = (255, 165, 0)
CASTLE_GRAY = (128, 128, 128)
GRAY = (128, 128, 128)

# Function to draw background procedurally
def draw_background(screen, world_type):
    if world_type == 'grass':
        screen.fill(SKY_BLUE)
        # Draw hills
        pygame.draw.polygon(screen, HILL_GREEN, [(0, SCREEN_HEIGHT), (200, 400), (400, SCREEN_HEIGHT)])
        pygame.draw.polygon(screen, HILL_GREEN, [(400, SCREEN_HEIGHT), (600, 400), (800, SCREEN_HEIGHT)])
        # Draw sun
        pygame.draw.circle(screen, SUN_YELLOW, (700, 100), 50)
        # Draw clouds
        draw_cloud(screen, 100, 100)
        draw_cloud(screen, 500, 150)
    elif world_type == 'sky':
        screen.fill(SKY_BLUE)
        # Draw clouds
        draw_cloud(screen, 50, 50)
        draw_cloud(screen, 300, 100)
        draw_cloud(screen, 600, 80)
    elif world_type == 'lava':
        screen.fill(LAVA_RED)
        # Draw lava bubbles
        for _ in range(10):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(SCREEN_HEIGHT - 100, SCREEN_HEIGHT)
            pygame.draw.circle(screen, LAVA_ORANGE, (x, y), random.randint(10, 20))
    elif world_type == 'bowser':
        screen.fill(BLACK)
        # Draw castle bricks pattern
        for x in range(0, SCREEN_WIDTH, 20):
            for y in range(0, SCREEN_HEIGHT, 20):
                pygame.draw.rect(screen, CASTLE_GRAY, (x, y, 20, 20), 1)

def draw_cloud(screen, x, y):
    pygame.draw.ellipse(screen, CLOUD_WHITE, (x, y, 100, 50))
    pygame.draw.ellipse(screen, CLOUD_WHITE, (x + 20, y - 20, 60, 40))
    pygame.draw.ellipse(screen, CLOUD_WHITE, (x + 60, y - 10, 80, 40))

# Function to create tiled platform surface procedurally
def create_tiled_surface(width, height, world_type):
    surface = pygame.Surface((width, height))
    tile_size = 20
    for tx in range(0, width, tile_size):
        for ty in range(0, height, tile_size):
            if world_type == 'grass':
                surface.fill(DIRT_BROWN, (tx, ty, tile_size, tile_size))
                pygame.draw.line(surface, GREEN, (tx, ty), (tx + tile_size, ty), 3)  # Green top
            elif world_type == 'sky':
                surface.fill(WHITE, (tx, ty, tile_size, tile_size))
                pygame.draw.circle(surface, SKY_BLUE, (tx + 10, ty + 10), 5)
            elif world_type == 'lava':
                surface.fill(BLACK, (tx, ty, tile_size, tile_size))
                pygame.draw.rect(surface, LAVA_RED, (tx + 2, ty + 2, 16, 16), 2)
            elif world_type == 'bowser':
                surface.fill(BLACK, (tx, ty, tile_size, tile_size))
                pygame.draw.rect(surface, CASTLE_GRAY, (tx, ty, tile_size, tile_size), 1)
    return surface

# Simple classes for game objects
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Draw simple Mario (inspired by classic style)
        pygame.draw.rect(self.image, MARIO_RED, (8, 8, 16, 12))  # Shirt
        pygame.draw.rect(self.image, MARIO_BLUE, (6, 16, 20, 16))  # Overalls
        pygame.draw.rect(self.image, MARIO_SKIN, (8, 0, 16, 12))  # Head
        pygame.draw.rect(self.image, MARIO_RED, (4, 0, 24, 8))  # Hat
        self.rect = self.image.get_rect()
        self.rect.x = 100
        self.rect.y = SCREEN_HEIGHT - 100
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False

    def update(self, platforms, enemies, bosses):
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Move vertically
        self.rect.y += self.vel_y
        
        # Check platform collisions (vertical)
        self.on_ground = False
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for hit in hits:
            if self.vel_y > 0:  # Falling down
                self.rect.bottom = hit.rect.top
                self.vel_y = 0
                self.on_ground = True
            elif self.vel_y < 0:  # Jumping up
                self.rect.top = hit.rect.bottom
                self.vel_y = 0

        # Move horizontally
        self.rect.x += self.vel_x
        
        # Check platform collisions (horizontal)
        hits = pygame.sprite.spritecollide(self, platforms, False)
        for hit in hits:
            if self.vel_x > 0:  # Moving right
                self.rect.right = hit.rect.left
            elif self.vel_x < 0:  # Moving left
                self.rect.left = hit.rect.right

        # Keep player on screen
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Check enemy collisions
        enemy_hits = pygame.sprite.spritecollide(self, enemies, False)
        for hit in enemy_hits:
            if self.vel_y > 0 and self.rect.bottom < hit.rect.centery + 10:  # Stomping
                hit.kill()
                self.vel_y = JUMP_HEIGHT / 2
            else:
                return True  # Game over

        # Check boss collisions
        boss_hits = pygame.sprite.spritecollide(self, bosses, False)
        for hit in boss_hits:
            if self.vel_y > 0 and self.rect.bottom < hit.rect.centery + 10:
                hit.health -= 1
                self.vel_y = JUMP_HEIGHT / 2
                if hit.health <= 0:
                    hit.kill()
            else:
                return True  # Game over

        # Check if fallen off the screen
        if self.rect.top > SCREEN_HEIGHT:
            return True  # Game over

        return False

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_HEIGHT

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, world_type):
        super().__init__()
        self.image = create_tiled_surface(width, height, world_type)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, world_type):
        super().__init__()
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Draw simple Goomba
        pygame.draw.ellipse(self.image, GOOMBA_BROWN, (4, 8, 24, 16))  # Body
        pygame.draw.rect(self.image, GOOMBA_BLACK, (0, 24, 32, 8))  # Feet
        pygame.draw.circle(self.image, GOOMBA_WHITE, (8, 12), 4)  # Left eye
        pygame.draw.circle(self.image, GOOMBA_WHITE, (20, 12), 4)  # Right eye
        pygame.draw.circle(self.image, GOOMBA_BLACK, (9, 13), 2)  # Left pupil
        pygame.draw.circle(self.image, GOOMBA_BLACK, (21, 13), 2)  # Right pupil
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = random.choice([-2, 2])
        self.world_type = world_type

    def update(self, platforms):
        # Move horizontally
        self.rect.x += self.vel_x
        
        # Check platform collisions and turn around at edges
        hits = pygame.sprite.spritecollide(self, platforms, False)
        if hits:
            self.vel_x *= -1
            
        # Turn around at screen edges
        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.vel_x *= -1

class Boss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((64, 64), pygame.SRCALPHA)
        # Draw simple Bowser
        pygame.draw.ellipse(self.image, BOWSER_GREEN, (8, 16, 48, 32))  # Body
        pygame.draw.circle(self.image, BOWSER_GREEN, (32, 16), 16)  # Head
        pygame.draw.rect(self.image, BOWSER_ORANGE, (16, 8, 32, 8))  # Shell spikes
        pygame.draw.circle(self.image, RED, (24, 16), 3)  # Left eye
        pygame.draw.circle(self.image, RED, (40, 16), 3)  # Right eye
        
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.health = 3
        self.vel_x = -1

    def update(self, platforms):
        # Move horizontally
        self.rect.x += self.vel_x
        
        # Turn around at screen edges
        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.vel_x *= -1

def create_level(world_type):
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    bosses = pygame.sprite.Group()
    
    # Create ground platform
    ground = Platform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40, world_type)
    platforms.add(ground)
    
    # Add additional platforms based on world type
    if world_type == 'grass':
        platforms.add(Platform(200, 450, 100, 20, world_type))
        platforms.add(Platform(400, 350, 150, 20, world_type))
        platforms.add(Platform(600, 400, 100, 20, world_type))
        enemies.add(Enemy(250, 420, world_type))
        enemies.add(Enemy(450, 320, world_type))
        
    elif world_type == 'sky':
        platforms.add(Platform(150, 450, 80, 20, world_type))
        platforms.add(Platform(350, 350, 100, 20, world_type))
        platforms.add(Platform(550, 250, 120, 20, world_type))
        platforms.add(Platform(250, 200, 80, 20, world_type))
        enemies.add(Enemy(380, 320, world_type))
        enemies.add(Enemy(580, 220, world_type))
        
    elif world_type == 'lava':
        platforms.add(Platform(100, 450, 80, 20, world_type))
        platforms.add(Platform(300, 400, 80, 20, world_type))
        platforms.add(Platform(500, 350, 80, 20, world_type))
        platforms.add(Platform(700, 300, 80, 20, world_type))
        enemies.add(Enemy(330, 370, world_type))
        enemies.add(Enemy(530, 320, world_type))
        enemies.add(Enemy(730, 270, world_type))
        
    elif world_type == 'bowser':
        platforms.add(Platform(200, 450, 100, 20, world_type))
        platforms.add(Platform(500, 450, 100, 20, world_type))
        platforms.add(Platform(350, 300, 100, 20, world_type))
        bosses.add(Boss(400, 200))
        enemies.add(Enemy(250, 420, world_type))
        enemies.add(Enemy(550, 420, world_type))
    
    return platforms, enemies, bosses

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Mario Platformer")
    clock = pygame.time.Clock()
    
    # Game states
    world_types = ['grass', 'sky', 'lava', 'bowser']
    current_world = 0
    
    # Create player
    player = Player()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    
    # Create level
    platforms, enemies, bosses = create_level(world_types[current_world])
    all_sprites.add(platforms)
    all_sprites.add(enemies)
    all_sprites.add(bosses)
    
    # Game variables
    running = True
    game_over = False
    font = pygame.font.Font(None, 36)
    
    while running:
        clock.tick(FPS)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over:
                    player.jump()
                elif event.key == pygame.K_r and game_over:
                    # Reset game
                    game_over = False
                    current_world = 0
                    all_sprites.empty()
                    player = Player()
                    all_sprites.add(player)
                    platforms, enemies, bosses = create_level(world_types[current_world])
                    all_sprites.add(platforms)
                    all_sprites.add(enemies)
                    all_sprites.add(bosses)
        
        if not game_over:
            # Handle input
            keys = pygame.key.get_pressed()
            player.vel_x = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.vel_x = -PLAYER_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.vel_x = PLAYER_SPEED
            
            # Update
            game_over = player.update(platforms, enemies, bosses)
            enemies.update(platforms)
            bosses.update(platforms)
            
            # Check if level complete (all enemies and bosses defeated)
            if len(enemies) == 0 and len(bosses) == 0:
                current_world += 1
                if current_world >= len(world_types):
                    # Win condition
                    game_over = True
                else:
                    # Next level
                    all_sprites.empty()
                    player.rect.x = 100
                    player.rect.y = SCREEN_HEIGHT - 100
                    all_sprites.add(player)
                    platforms, enemies, bosses = create_level(world_types[current_world])
                    all_sprites.add(platforms)
                    all_sprites.add(enemies)
                    all_sprites.add(bosses)
        
        # Draw
        draw_background(screen, world_types[min(current_world, len(world_types)-1)])
        all_sprites.draw(screen)
        
        # Draw UI
        level_text = font.render(f"World: {world_types[min(current_world, len(world_types)-1)].title()}", True, WHITE)
        screen.blit(level_text, (10, 10))
        
        if game_over:
            if current_world >= len(world_types):
                game_over_text = font.render("YOU WIN! Press R to restart", True, WHITE)
            else:
                game_over_text = font.render("GAME OVER! Press R to restart", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
            screen.blit(game_over_text, text_rect)
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
