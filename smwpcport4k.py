import pygame, sys, random

# -------------------------------
# Super Mario World (Hallucinated .smc -> pygame)
# -------------------------------

pygame.init()
WIDTH, HEIGHT = 512, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World — Pygame 60FPS")
clock = pygame.time.Clock()
FPS = 60

# Colors
SKY = (135, 206, 235)
GROUND = (139, 69, 19)
GREEN = (0, 200, 0)
MARIO_RED = (220, 0, 0)
COIN = (255, 215, 0)
GOOMBA = (150, 75, 0)

# Physics
GRAVITY = 0.6
JUMP = -12
MOVE_SPEED = 4
TILESIZE = 32

# A simple "World 1-1" layout
level = [
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "        o     g      o          ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "                                ",
    "================================",
]

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(MARIO_RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.on_ground = False
        self.score = 0

    def update(self, tiles, coins, enemies):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]: dx -= MOVE_SPEED
        if keys[pygame.K_RIGHT]: dx += MOVE_SPEED
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = JUMP
            self.on_ground = False

        # gravity
        self.vel_y += GRAVITY
        if self.vel_y > 10: self.vel_y = 10
        dy += self.vel_y

        # collisions
        self.on_ground = False
        for tile in tiles:
            if self.rect.move(dx,0).colliderect(tile): dx = 0
            if self.rect.move(0,dy).colliderect(tile):
                if self.vel_y > 0:
                    dy = tile.top - self.rect.bottom
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    dy = tile.bottom - self.rect.top
                    self.vel_y = 0

        self.rect.x += dx
        self.rect.y += dy

        # coin collection
        for coin in coins[:]:
            if self.rect.colliderect(coin):
                coins.remove(coin)
                self.score += 100

        # enemy stomp
        for enemy in enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0:
                    enemies.remove(enemy)
                    self.vel_y = JUMP//2
                    self.score += 200
                else:
                    print("Game Over!")
                    pygame.quit(); sys.exit()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(GOOMBA)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = 2
    def update(self, tiles):
        self.rect.x += self.speed
        for tile in tiles:
            if self.rect.colliderect(tile):
                self.speed *= -1
                break

# build world
tiles, coins, enemies = [], [], []
for y,row in enumerate(level):
    for x,char in enumerate(row):
        if char=="=": tiles.append(pygame.Rect(x*TILESIZE,y*TILESIZE,TILESIZE,TILESIZE))
        if char=="o": coins.append(pygame.Rect(x*TILESIZE+8,y*TILESIZE+8,16,16))
        if char=="g": enemies.append(Enemy(x*TILESIZE,y*TILESIZE-TILESIZE))

player = Player(64, HEIGHT-3*TILESIZE)

while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT: pygame.quit(); sys.exit()

    player.update(tiles, coins, enemies)
    for en in enemies: en.update(tiles)

    screen.fill(SKY)
    for t in tiles: pygame.draw.rect(screen,GROUND,t); pygame.draw.rect(screen,GREEN,(t.x,t.y,TILESIZE,6))
    for c in coins: pygame.draw.circle(screen,COIN,c.center,8)
    for en in enemies: screen.blit(en.image,en.rect)
    screen.blit(player.image,player.rect)

    font=pygame.font.SysFont("Arial",20,bold=True)
    screen.blit(font.render(f"Score: {player.score}",True,(0,0,0)),(10,10))

    pygame.display.flip()
    clock.tick(FPS)
