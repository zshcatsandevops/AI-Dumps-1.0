import pygame
import asyncio
import platform

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World - NES Style")

# Colors (NES palette approximation)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 0, 0)
BROWN = (139, 69, 19)
GREEN = (0, 100, 0)
BLUE = (0, 0, 200)

# Game settings
FPS = 60
GRAVITY = 0.8
JUMP_FORCE = -15
MOVE_SPEED = 5

# Mario class
class Mario:
    def __init__(self):
        self.width, self.height = 16, 16  # NES-style sprite size
        self.x, self.y = 50, HEIGHT - 40
        self.vx, self.vy = 0, 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False

    def update(self, keys, platforms):
        # Horizontal movement
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
        if keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED

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
            self.y = HEIGHT - 40
            self.vy = 0
            self.on_ground = True
        self.rect.topleft = (self.x, self.y)

    def draw(self, surface):
        # Draw Mario as a red rectangle (NES-style placeholder)
        pygame.draw.rect(surface, RED, self.rect)

# Platform class
class Platform:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def draw(self, surface):
        # Draw platform as brown rectangle (NES-style ground)
        pygame.draw.rect(surface, BROWN, self.rect)

# Goomba class
class Goomba:
    def __init__(self, x, y):
        self.width, self.height = 16, 16
        self.x, self.y = x, y
        self.vx = -2  # Move left
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self, platforms):
        self.x += self.vx
        self.rect.topleft = (self.x, self.y)

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

    def draw(self, surface):
        # Draw Goomba as a brown rectangle (NES-style placeholder)
        pygame.draw.rect(surface, BROWN, self.rect)

# Game setup
mario = Mario()
platforms = [
    Platform(0, HEIGHT - 20, WIDTH, 20),  # Ground
    Platform(200, HEIGHT - 100, 100, 20),  # Floating platform
]
goombas = [Goomba(300, HEIGHT - 36)]

async def main():
    def setup():
        pass  # Initialization done above

    def update_loop():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        keys = pygame.key.get_pressed()
        mario.update(keys, platforms)
        for goomba in goombas:
            goomba.update(platforms)

        # Collision with Goombas
        for goomba in goombas:
            if mario.rect.colliderect(goomba.rect):
                if mario.vy > 0 and mario.rect.bottom <= goomba.rect.bottom:
                    goombas.remove(goomba)  # Mario jumps on Goomba
                else:
                    mario.y = HEIGHT - 40  # Reset Mario (simulated death)
                    mario.vy = 0
                    mario.on_ground = True

        # Draw everything
        SCREEN.fill(BLACK)  # Clear screen
        for platform in platforms:
            platform.draw(SCREEN)
        for goomba in goombas:
            goomba.draw(SCREEN)
        mario.draw(SCREEN)
        pygame.display.flip()

    while True:
        update_loop()
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
