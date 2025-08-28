import pygame, sys

# ----------------------------
# Super Mario Bros. 1-1 (NES) — Pygame Rebuild
# ----------------------------

pygame.init()
WIDTH, HEIGHT = 512, 240
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario Bros 1-1 (Pygame)")
clock = pygame.time.Clock()
FPS = 60
TILE = 16

# NES palette
BLACK = (0,0,0)
RED   = (228, 0, 88)
BLUE  = (60, 188, 252)
BROWN = (160, 82, 45)
GREEN = (0, 168, 0)
YELLOW= (252, 224, 56)
SKIN  = (248, 216, 168)

# Mario sprite (16x16 pixel map)
MARIO_PIXELS = [
"................",
"....RRRRR.......",
"...RYYYYYR......",
"..RRYYYYYRR.....",
"..RSYYYSYRS.....",
"..RRRYYYRRR.....",
"....BBBB........",
"...BBBBBB.......",
"..BBYYBBYYB.....",
"..BBYYBBYYB.....",
"...B....B.......",
"...B....B.......",
"..RR......RR....",
"..RR......RR....",
"..BB......BB....",
"..BB......BB....",
]

def make_sprite(pixels, cmap):
    surf = pygame.Surface((16,16), pygame.SRCALPHA)
    for y,row in enumerate(pixels):
        for x,ch in enumerate(row):
            if ch != ".":
                pygame.draw.rect(surf,cmap.get(ch,BLACK),(x,y,1,1))
    return pygame.transform.scale(surf,(TILE,TILE))

color_map = {"R":RED,"Y":YELLOW,"S":SKIN,"B":BLUE}
mario_sprite = make_sprite(MARIO_PIXELS,color_map)

# Simple Goomba sprite
GOOMBA_PIXELS = [
"................",
"....BBBBBB......",
"...BBBBBBBB.....",
"..BBYYYYYYBB....",
"..BBYYYYYYBB....",
"..BBBBBBBBBB....",
"...BB....BB.....",
"...BB....BB.....",
"..BB......BB....",
"................",
"................",
"................",
"................",
"................",
"................",
"................",
]
goomba_sprite = make_sprite(GOOMBA_PIXELS,{"B":BROWN,"Y":YELLOW})

# Level 1-1 map (partial, extendable)
level = [
"...............................................................................................................F",
"................................................................................................................",
"................................................................................................................",
"................................................................................................................",
"................................................................................................................",
"................................................................................................................",
"................................................................................................................",
"...................................................??...........................................................",
"................................................................................................................",
"...........B?B..................................................................................................",
"................................................................................................................",
"GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
]

# Tile dictionary
TILE_MAP = {
    "G": BROWN,   # ground
    "B": BROWN,   # brick
    "?": YELLOW,  # question
    "F": GREEN,   # flagpole
}

# Player
player = pygame.Rect(32, 120, TILE, TILE)
vel_y = 0
GRAVITY = 0.6
JUMP = -10
on_ground = True
speed = 2

# Goombas
goombas = [pygame.Rect(200, 192, TILE, TILE)]
goomba_dir = {id(g): -1 for g in goombas}

# Camera offset
camera_x = 0

running=True
while running:
    for e in pygame.event.get():
        if e.type==pygame.QUIT:
            running=False

    keys=pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player.x-=speed
    if keys[pygame.K_RIGHT]:
        player.x+=speed
    if keys[pygame.K_SPACE] and on_ground:
        vel_y=JUMP

    # Apply gravity
    vel_y+=GRAVITY
    player.y+=vel_y

    # Collisions
    on_ground=False
    for row in range(len(level)):
        for col in range(len(level[row])):
            tile=level[row][col]
            if tile!=".":
                rect=pygame.Rect(col*TILE,row*TILE,TILE,TILE)
                if player.colliderect(rect) and vel_y>0:
                    player.bottom=rect.top
                    vel_y=0
                    on_ground=True

    # Goomba movement
    for g in goombas:
        g.x += goomba_dir[id(g)]
        # bounce off blocks
        for row in range(len(level)):
            for col in range(len(level[row])):
                tile=level[row][col]
                if tile!=".":
                    rect=pygame.Rect(col*TILE,row*TILE,TILE,TILE)
                    if g.colliderect(rect):
                        goomba_dir[id(g)]*=-1
                        g.x+=goomba_dir[id(g)]*2

        # Mario stomp
        if player.colliderect(g):
            if vel_y>0: # stomped
                goombas.remove(g)
            else:
                print("Game Over")
                running=False

    # Camera follows Mario
    camera_x = max(0, player.x - WIDTH//2)

    # Draw
    screen.fill(BLUE)
    for row in range(len(level)):
        for col in range(len(level[row])):
            tile=level[row][col]
            if tile!=".":
                rect=pygame.Rect(col*TILE-camera_x,row*TILE,TILE,TILE)
                pygame.draw.rect(screen,TILE_MAP.get(tile,BROWN),rect)
                pygame.draw.rect(screen,BLACK,rect,1)

    # Draw goombas
    for g in goombas:
        screen.blit(goomba_sprite,(g.x-camera_x,g.y))

    # Draw Mario
    screen.blit(mario_sprite,(player.x-camera_x,player.y))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
