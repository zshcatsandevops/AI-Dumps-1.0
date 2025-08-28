import os
import pygame
import sys
import random
import math

# Init
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60

# Physics constants (Mario-like)
GRAVITY = 0.7
MAX_FALL = 12
ACCEL = 0.5
FRICTION = 0.15
MAX_SPEED = 5
JUMP_FORCE = -12

# Colors
WHITE = (255, 255, 255)
SKY_BLUE = (135, 206, 235)
BROWN = (139, 69, 19)
GREEN = (0, 200, 0)
RED = (200, 0, 0)

# --- CLASSES ---

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Simple Mario
        pygame.draw.rect(self.image, RED, (8, 8, 16, 12))  # Shirt
        pygame.draw.rect(self.image, (0,0,255), (6, 16, 20, 16))  # Overalls
        pygame.draw.rect(self.image, (255,220,177), (8, 0, 16, 12))  # Face
        pygame.draw.rect(self.image, RED, (4, 0, 24, 8))  # Hat
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x, self.vel_y = 0, 0
        self.on_ground = False

    def update(self, keys, platforms):
        # Horizontal accel
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x -= ACCEL
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x += ACCEL
        else:
            # friction
            if abs(self.vel_x) < FRICTION:
                self.vel_x = 0
            else:
                self.vel_x -= FRICTION * math.copysign(1, self.vel_x)

        # Clamp X speed
        self.vel_x = max(-MAX_SPEED, min(MAX_SPEED, self.vel_x))

        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL:
            self.vel_y = MAX_FALL

        # Apply movement
        self.rect.x += self.vel_x
        self.collide(self.vel_x, 0, platforms)

        self.rect.y += self.vel_y
        self.on_ground = False
        self.collide(0, self.vel_y, platforms)

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_FORCE

    def collide(self, vel_x, vel_y, platforms):
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if vel_x > 0:
                    self.rect.right = p.rect.left
                if vel_x < 0:
                    self.rect.left = p.rect.right
                if vel_y > 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                if vel_y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(BROWN)
        pygame.draw.rect(self.image, GREEN, (0, 0, w, 6))  # grass top
        self.rect = self.image.get_rect(topleft=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.image.fill((160,80,40))
        self.rect = self.image.get_rect(topleft=(x,y))
        self.vel_x = random.choice([-2,2])

    def update(self, platforms):
        self.rect.x += self.vel_x
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_x > 0: self.rect.right = p.rect.left
                else: self.rect.left = p.rect.right
                self.vel_x *= -1
        if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
            self.vel_x *= -1

# --- MAIN LOOP ---

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Groups
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    # Player
    player = Player(100, SCREEN_HEIGHT-200)
    all_sprites.add(player)

    # Level (sample)
    ground = Platform(0, SCREEN_HEIGHT-40, SCREEN_WIDTH, 40)
    platforms.add(ground); all_sprites.add(ground)
    block1 = Platform(200, 400, 100, 20)
    platforms.add(block1); all_sprites.add(block1)
    block2 = Platform(400, 300, 100, 20)
    platforms.add(block2); all_sprites.add(block2)

    # Enemy
    goomba = Enemy(300, SCREEN_HEIGHT-72)
    enemies.add(goomba); all_sprites.add(goomba)

    running = True
    while running:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    player.jump()

        keys = pygame.key.get_pressed()
        player.update(keys, platforms)
        enemies.update(platforms)

        # Stomp detection
        for enemy in enemies:
            if player.rect.colliderect(enemy.rect):
                if player.vel_y > 0 and player.rect.bottom-10 < enemy.rect.top:
                    enemy.kill()
                    player.vel_y = JUMP_FORCE/2
                else:
                    print("Game Over!")
                    running = False

        # Draw
        screen.fill(SKY_BLUE)
        all_sprites.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
