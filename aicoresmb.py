import asyncio
import pygame
import platform
import sys

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Super Mario Forever - World 1")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (139, 69, 19)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BEIGE = (245, 245, 220)
DARK_GREEN = (0, 100, 0)
LIGHT_BLUE = (135, 206, 250)
PURPLE = (128, 0, 128)  # Added for mystical theme

# Level themes
THEMES = {
    "grass": {"ground": GREEN, "bg": LIGHT_BLUE, "details": DARK_GREEN},
    "snow": {"ground": WHITE, "bg": (200, 200, 255), "details": (150, 150, 200)},
    "desert": {"ground": YELLOW, "bg": (255, 200, 100), "details": (200, 150, 50)},
    "swamp": {"ground": DARK_GREEN, "bg": (50, 50, 100), "details": (0, 150, 0)},
    "castle": {"ground": GRAY, "bg": BLACK, "details": (100, 100, 100)},
    "cave": {"ground": GRAY, "bg": BLACK, "details": RED},  # For Vanilla Dome
    "bridge": {"ground": BLUE, "bg": LIGHT_BLUE, "details": WHITE},  # For Twin Bridges
    "forest": {"ground": DARK_GREEN, "bg": GREEN, "details": BROWN},  # For Forest of Illusion
    "rocky": {"ground": BROWN, "bg": YELLOW, "details": GRAY},  # For Chocolate Island
    "subterranean": {"ground": GRAY, "bg": BLACK, "details": RED},  # For Valley of Bowser
    "mystical": {"ground": PURPLE, "bg": LIGHT_BLUE, "details": YELLOW},  # For Star World
    "special": {"ground": YELLOW, "bg": (255, 200, 100), "details": RED}  # For Special Zone
}

# Game constants
GRAVITY = 0.8
FPS = 60
TIME_LIMIT = 400

# Game variables
score = 0
coins = 0
lives = 3
start_time = 0

# Font for HUD
font = pygame.font.SysFont(None, 24)

# Player class
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.jump_power = -15
        self.speed = 5
        self.facing_right = True
        self.image = self._create_image()

    def _create_image(self):
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Head
        pygame.draw.rect(surface, BEIGE, (12, 4, 8, 8))  # Face
        pygame.draw.rect(surface, RED, (10, 2, 12, 4))   # Hat
        # Body
        pygame.draw.rect(surface, BLUE, (10, 12, 12, 12)) # Overalls
        pygame.draw.rect(surface, RED, (10, 12, 12, 6))  # Shirt
        # Arms
        pygame.draw.rect(surface, BEIGE, (8, 12, 4, 8))  # Left arm
        pygame.draw.rect(surface, BEIGE, (20, 12, 4, 8)) # Right arm
        # Legs
        pygame.draw.rect(surface, BLUE, (12, 24, 4, 8))  # Left leg
        pygame.draw.rect(surface, BLUE, (16, 24, 4, 8))  # Right leg
        return surface

    def update(self, platforms):
        # Horizontal movement and collision
        self.rect.x += self.vx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                    self.vx = 0
                elif self.vx < 0:
                    self.rect.left = platform.rect.right
                    self.vx = 0

        # Vertical movement and collision
        self.vy += GRAVITY
        self.rect.y += self.vy
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:
                    self.rect.bottom = platform.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = platform.rect.bottom
                    self.vy = 0

        # Check for falling off the screen (death)
        if self.rect.top > SCREEN_HEIGHT:
            self.die()

        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False

    def jump(self):
        if self.on_ground:
            self.vy = self.jump_power

    def draw(self):
        img = self.image if self.facing_right else pygame.transform.flip(self.image, True, False)
        screen.blit(img, self.rect)

    def die(self):
        global lives
        lives -= 1
        if lives <= 0:
            pygame.quit()
            sys.exit()
        else:
            setup()
            self.vx = 0
            self.vy = 0

# Platform class
class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, theme):
        # SNES-style platform with theme-specific textures
        surface = pygame.Surface((self.rect.width, self.rect.height))
        surface.fill(theme["ground"])
        # Add details (e.g., grass tufts, snow patches)
        for i in range(0, self.rect.width, 16):
            pygame.draw.rect(surface, theme["details"], (i, 0, 8, 4))
        screen.blit(surface, self.rect)

# Enemy class
class Enemy:
    def __init__(self, x, y, min_x, max_x):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.vx = 2
        self.vy = 0
        self.min_x = min_x
        self.max_x = max_x
        self.on_ground = False
        self.image = self._create_image()

    def _create_image(self):
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, BROWN, (8, 8, 16, 16))  # Body
        pygame.draw.rect(surface, BLACK, (12, 8, 4, 4))      # Eye
        pygame.draw.rect(surface, BLACK, (16, 8, 4, 4))      # Eye
        pygame.draw.rect(surface, BLACK, (12, 20, 8, 4))     # Mouth
        return surface

    def update(self, platforms):
        # Vertical movement and collision
        self.vy += GRAVITY
        self.rect.y += self.vy
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:
                    self.rect.bottom = platform.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = platform.rect.bottom
                    self.vy = 0

        # Horizontal movement
        self.rect.x += self.vx
        if self.rect.x <= self.min_x or self.rect.x >= self.max_x:
            self.vx = -self.vx

    def draw(self):
        img = self.image if self.vx > 0 else pygame.transform.flip(self.image, True, False)
        screen.blit(img, self.rect)

# Coin class
class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 16, 16)
        self.image = self._create_image()

    def _create_image(self):
        surface = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(surface, YELLOW, (8, 8), 8)
        return surface

    def draw(self):
        screen.blit(self.image, self.rect)

# Level data incorporating worlds from Super Mario World
current_level = 0
levels = [
    # World 1: Yoshi's Island - Theme: grass
    {"theme": "grass", "platforms": [(100, 500, 200, 20), (400, 400, 200, 20), (700, 300, 100, 20)],
     "enemies": [(150, 480, 100, 268)], "coins": [(120, 450), (420, 350), (720, 250)]},
    # World 2: Donut Plains - Theme: grass (plains-like)
    {"theme": "grass", "platforms": [(150, 500, 200, 20), (450, 360, 150, 20)],
     "enemies": [(200, 480, 150, 318)], "coins": [(170, 450), (470, 310)]},
    # World 3: Vanilla Dome - Theme: cave
    {"theme": "cave", "platforms": [(200, 500, 200, 20), (500, 450, 200, 20)],
     "enemies": [(250, 480, 200, 368)], "coins": [(220, 450), (520, 400)]},
    # World 4: Twin Bridges - Theme: bridge
    {"theme": "bridge", "platforms": [(100, 500, 200, 20), (400, 400, 200, 20)],
     "enemies": [(150, 480, 100, 268)], "coins": [(120, 450), (420, 350)]},
    # World 5: Forest of Illusion - Theme: forest
    {"theme": "forest", "platforms": [(150, 500, 200, 20), (450, 360, 150, 20), (700, 400, 100, 20)],
     "enemies": [(200, 480, 150, 318)], "coins": [(170, 450), (470, 310), (720, 350)]},
    # World 6: Chocolate Island - Theme: rocky
    {"theme": "rocky", "platforms": [(100, 500, 200, 20), (300, 450, 150, 20), (550, 400, 200, 20)],
     "enemies": [(150, 480, 100, 250)], "coins": [(120, 450), (320, 400), (570, 350)]},
    # World 7: Valley of Bowser - Theme: subterranean
    {"theme": "subterranean", "platforms": [(200, 500, 200, 20), (450, 400, 150, 20), (700, 350, 100, 20)],
     "enemies": [(250, 480, 200, 350)], "coins": [(220, 450), (470, 350), (720, 300)]},
    # World 8: Star World - Theme: mystical
    {"theme": "mystical", "platforms": [(100, 500, 200, 20), (400, 350, 200, 20)],
     "enemies": [(150, 480, 100, 268)], "coins": [(120, 450), (420, 300)]},
    # World 9: Special Zone - Theme: special
    {"theme": "special", "platforms": [(150, 500, 200, 20), (450, 300, 150, 20), (700, 400, 100, 20)],
     "enemies": [(200, 480, 150, 318)], "coins": [(170, 450), (470, 250), (720, 350)]}
]

# Game objects
player = Player(0, 0)  # Initial position will be set in setup
platforms = []
enemies = []
coins_list = []  # Renamed to avoid conflict with coins variable
clock = pygame.time.Clock()

def setup():
    global platforms, enemies, coins_list, start_time
    level = levels[current_level]
    platforms = [Platform(x, y, w, h) for x, y, w, h in level["platforms"]]
    enemies = [Enemy(x, y, min_x, max_x) for x, y, min_x, max_x in level["enemies"]]
    coins_list = [Coin(x, y) for x, y in level.get("coins", [])]
    start_time = pygame.time.get_ticks()
    # Set player starting position on the first platform
    if platforms:
        player.rect.x = platforms[0].rect.x + 10
        player.rect.y = platforms[0].rect.y - player.rect.height
    player.vx = 0
    player.vy = 0
    player.on_ground = True  # Assume starting on ground

def update_loop():
    global score, coins, lives
    keys = pygame.key.get_pressed()
    player.vx = 0
    if keys[pygame.K_LEFT]:
        player.vx = -player.speed
    if keys[pygame.K_RIGHT]:
        player.vx = player.speed

    player.update(platforms)
    for enemy in enemies:
        enemy.update(platforms)

    # Coin collections
    for coin in coins_list[:]:
        if player.rect.colliderect(coin.rect):
            coins_list.remove(coin)
            coins += 1
            score += 50

    # Enemy collisions with player
    for enemy in enemies[:]:
        if player.rect.colliderect(enemy.rect):
            if player.vy > 0 and player.rect.bottom <= enemy.rect.top + 20:
                enemies.remove(enemy)
                score += 100
            else:
                player.die()

    # Time management
    current_time = pygame.time.get_ticks()
    elapsed = (current_time - start_time) // 1000
    time_display = max(0, TIME_LIMIT - elapsed)
    if time_display <= 0:
        player.die()

    # Level progression
    if player.rect.right > SCREEN_WIDTH:
        global current_level
        current_level += 1
        if current_level >= len(levels):
            current_level = 0  # Loop back or win condition
        setup()

    theme = THEMES[levels[current_level]["theme"]]
    screen.fill(theme["bg"])
    for platform in platforms:
        platform.draw(theme)
    for coin in coins_list:
        coin.draw()
    for enemy in enemies:
        enemy.draw()
    player.draw()

    # Draw HUD
    hud_y = 10
    # MARIO
    text = font.render("MARIO", True, WHITE)
    screen.blit(text, (20, hud_y))
    # Score
    score_str = f"{score:06d}"
    text = font.render(score_str, True, WHITE)
    screen.blit(text, (100, hud_y))
    # Coin icon and count
    pygame.draw.circle(screen, YELLOW, (200, hud_y + 12), 6)
    text = font.render(f"x {coins:02d}", True, WHITE)
    screen.blit(text, (215, hud_y))
    # World
    world_str = f"WORLD 1-{current_level + 1}"
    text = font.render(world_str, True, WHITE)
    screen.blit(text, (SCREEN_WIDTH // 2 - 60, hud_y))
    # Time
    time_str = f"TIME {time_display:03d}"
    text = font.render(time_str, True, WHITE)
    screen.blit(text, (SCREEN_WIDTH - 150, hud_y))
    # Lives
    lives_str = f"LIVES x {lives}"
    text = font.render(lives_str, True, WHITE)
    screen.blit(text, (20, SCREEN_HEIGHT - 30))

    pygame.display.flip()

async def main():
    setup()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
        update_loop()
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
