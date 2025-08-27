import pygame
import asyncio
import platform

# Initialize Pygame
pygame.init()

# Screen settings - NES resolution
WIDTH, HEIGHT = 256, 240
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World - NES Style")

# Colors (NES palette)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (216, 40, 0)
BROWN = (168, 96, 72)
GREEN = (0, 168, 0)
BLUE = (0, 72, 168)
YELLOW = (248, 192, 0)
SKY_BLUE = (104, 168, 248)
NES_DARK_BLUE = (0, 0, 136)

# Game settings
FPS = 60
GRAVITY = 0.5
JUMP_FORCE = -9
MOVE_SPEED = 2

# Mario class
class Mario:
    def __init__(self):
        self.width, self.height = 16, 16
        self.x, self.y = 50, HEIGHT - 60
        self.vx, self.vy = 0, 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False
        self.facing_right = True
        self.frame = 0
        self.animation_timer = 0

    def update(self, keys, platforms):
        # Horizontal movement
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_right = False
            self.animate()
        if keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_right = True
            self.animate()

        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False

        # Apply gravity
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (self.x, self.y)

        # Platform collision
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0 and self.rect.bottom <= platform.rect.bottom:
                    self.rect.bottom = platform.rect.top
                    self.y = self.rect.y
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0 and self.rect.top >= platform.rect.top:
                    self.rect.top = platform.rect.bottom
                    self.y = self.rect.y
                    self.vy = 0

        # Keep Mario on screen
        self.x = max(0, min(self.x, WIDTH - self.width))
        if self.y > HEIGHT:
            self.y = HEIGHT - 60
            self.vy = 0
            self.on_ground = True
        self.rect.topleft = (self.x, self.y)
        
    def animate(self):
        self.animation_timer += 1
        if self.animation_timer > 10:
            self.frame = (self.frame + 1) % 2
            self.animation_timer = 0

    def draw(self, surface):
        # Draw Mario with NES-style graphics
        color = RED if self.facing_right else (200, 0, 0)
        
        # Body
        pygame.draw.rect(surface, color, self.rect)
        
        # Overalls
        pygame.draw.rect(surface, BLUE, 
                         (self.x + 2, self.y + 8, self.width - 4, self.height - 8))
        
        # Cap
        pygame.draw.rect(surface, color, 
                         (self.x, self.y, self.width, 4))
        
        # Animation - moving legs
        if self.vx != 0 and self.on_ground:
            leg_offset = 2 if self.frame == 0 else -2
            pygame.draw.rect(surface, BLUE, 
                            (self.x + 4, self.y + self.height - 4, 4, leg_offset))
            pygame.draw.rect(surface, BLUE, 
                            (self.x + self.width - 8, self.y + self.height - 4, 4, -leg_offset))

# Platform class
class Platform:
    def __init__(self, x, y, width, height, color=BROWN):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color

    def draw(self, surface):
        # Draw platform with NES-style brick pattern
        pygame.draw.rect(surface, self.color, self.rect)
        
        # Add brick pattern
        for i in range(0, self.rect.width, 4):
            for j in range(0, self.rect.height, 4):
                if (i // 4 + j // 4) % 2 == 0:
                    pygame.draw.rect(surface, (min(self.color[0] + 20, 255), 
                                             min(self.color[1] + 20, 255), 
                                             min(self.color[2] + 20, 255)), 
                                    (self.rect.x + i, self.rect.y + j, 2, 2))

# Goomba class
class Goomba:
    def __init__(self, x, y):
        self.width, self.height = 16, 16
        self.x, self.y = x, y
        self.vx = -1  # Move left
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.frame = 0
        self.animation_timer = 0

    def update(self, platforms):
        self.x += self.vx
        self.rect.topleft = (self.x, self.y)
        
        # Animate
        self.animate()

        # Platform collision
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right
                self.x = self.rect.x
                self.vx = -self.vx

        # Keep Goomba on screen
        if self.x < 0 or self.x > WIDTH - self.width:
            self.vx = -self.vx
            self.x = max(0, min(self.x, WIDTH - self.width))
        self.rect.topleft = (self.x, self.y)
        
    def animate(self):
        self.animation_timer += 1
        if self.animation_timer > 20:
            self.frame = (self.frame + 1) % 2
            self.animation_timer = 0

    def draw(self, surface):
        # Draw Goomba with NES-style graphics
        color = BROWN
        
        # Body
        pygame.draw.ellipse(surface, color, self.rect)
        
        # Feet - animated
        foot_offset = 2 if self.frame == 0 else 0
        pygame.draw.rect(surface, BROWN, (self.x + 2, self.y + self.height - 2, 4, foot_offset))
        pygame.draw.rect(surface, BROWN, (self.x + self.width - 6, self.y + self.height - 2, 4, -foot_offset))
        
        # Eyes
        pygame.draw.rect(surface, WHITE, (self.x + 4, self.y + 4, 2, 2))
        pygame.draw.rect(surface, WHITE, (self.x + self.width - 6, self.y + 4, 2, 2))

# Cloud class for decoration
class Cloud:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.speed = 0.5

    def update(self):
        self.x -= self.speed
        if self.x < -40:
            self.x = WIDTH + 10

    def draw(self, surface):
        # Draw NES-style cloud
        pygame.draw.ellipse(surface, WHITE, (self.x, self.y, 20, 10))
        pygame.draw.ellipse(surface, WHITE, (self.x + 10, self.y - 5, 25, 12))
        pygame.draw.ellipse(surface, WHITE, (self.x + 25, self.y, 15, 8))

# Bush class for decoration
class Bush:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def draw(self, surface):
        # Draw NES-style bush
        pygame.draw.ellipse(surface, GREEN, (self.x, self.y, 20, 12))
        pygame.draw.ellipse(surface, GREEN, (self.x + 10, self.y - 5, 25, 15))
        pygame.draw.ellipse(surface, GREEN, (self.x + 25, self.y, 15, 10))

# Game setup
mario = Mario()
platforms = [
    Platform(0, HEIGHT - 20, WIDTH, 20, GREEN),  # Ground
    Platform(50, HEIGHT - 60, 40, 10),           # Platform
    Platform(120, HEIGHT - 80, 60, 10),          # Platform
    Platform(200, HEIGHT - 100, 40, 10),         # Platform
    Platform(60, HEIGHT - 120, 30, 10),          # Platform
    Platform(150, HEIGHT - 140, 70, 10),         # Platform
]
goombas = [
    Goomba(100, HEIGHT - 36),
    Goomba(180, HEIGHT - 116),
    Goomba(220, HEIGHT - 36),
]
clouds = [
    Cloud(50, 30),
    Cloud(150, 50),
    Cloud(250, 40),
]
bushes = [
    Bush(70, HEIGHT - 30),
    Bush(180, HEIGHT - 30),
]

# Draw NES-style background
def draw_background():
    # Sky
    SCREEN.fill(SKY_BLUE)
    
    # Hills in background
    for i in range(0, WIDTH, 50):
        pygame.draw.arc(SCREEN, NES_DARK_BLUE, (i, HEIGHT - 100, 100, 50), 3.14, 6.28, 3)
    
    # Draw clouds
    for cloud in clouds:
        cloud.draw(SCREEN)
    
    # Draw bushes
    for bush in bushes:
        bush.draw(SCREEN)

async def main():
    clock = pygame.time.Clock()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        keys = pygame.key.get_pressed()
        mario.update(keys, platforms)
        for goomba in goombas:
            goomba.update(platforms)
        for cloud in clouds:
            cloud.update()

        # Collision with Goombas
        for goomba in goombas[:]:
            if mario.rect.colliderect(goomba.rect):
                if mario.vy > 0 and mario.rect.bottom <= goomba.rect.top + 8:
                    goombas.remove(goomba)  # Mario jumps on Goomba
                    mario.vy = -4  # Small bounce after killing Goomba
                else:
                    # Reset Mario on death
                    mario.x, mario.y = 50, HEIGHT - 60
                    mario.vx, mario.vy = 0, 0
                    mario.on_ground = True

        # Draw everything
        draw_background()
        for platform in platforms:
            platform.draw(SCREEN)
        for goomba in goombas:
            goomba.draw(SCREEN)
        mario.draw(SCREEN)
        
        # Draw NES-style UI
        pygame.draw.rect(SCREEN, BLACK, (0, 0, WIDTH, 16))
        font = pygame.font.SysFont('Arial', 8)
        score_text = font.render("SCORE 000000", True, WHITE)
        coin_text = font.render("COINx00", True, WHITE)
        world_text = font.render("WORLD 1-1", True, WHITE)
        time_text = font.render("TIME 300", True, WHITE)
        
        SCREEN.blit(score_text, (10, 4))
        SCREEN.blit(coin_text, (100, 4))
        SCREEN.blit(world_text, (150, 4))
        SCREEN.blit(time_text, (220, 4))
        
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
