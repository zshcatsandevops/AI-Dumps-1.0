import pygame
import sys
import random

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRAVITY = 0.5
JUMP_HEIGHT = -12
PLAYER_SPEED = 5
TILE_SIZE = 32

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BROWN = (139, 69, 19)
SKY_BLUE = (135, 206, 235)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
LIGHT_BLUE = (173, 216, 230)

# Camera class for scrolling
class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        # Calculate boundaries
        x = min(0, x)  # Left boundary
        y = min(0, y)  # Top boundary
        x = max(-(self.width - SCREEN_WIDTH), x)  # Right boundary
        y = max(-(self.height - SCREEN_HEIGHT), y)  # Bottom boundary

        self.camera = pygame.Rect(x, y, self.width, self.height)

# Player class
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((28, 28))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = 100
        self.rect.y = 400
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.power_up = 'small'
        self.coins = 0
        self.lives = 3
        self.invulnerable = False  # New: invulnerability after hit
        self.invulnerable_timer = 0
        self.facing_right = True  # New: track player direction

    def update(self, platforms, enemies, items):
        # Handle invulnerability
        if self.invulnerable:
            self.invulnerable_timer -= 1
            if self.invulnerable_timer <= 0:
                self.invulnerable = False
            # Make player blink when invulnerable
            if self.invulnerable_timer % 10 < 5:
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)

        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > 15:  # Terminal velocity
            self.vel_y = 15

        # Store old position for collision resolution
        old_x = self.rect.x
        old_y = self.rect.y

        # Vertical movement first
        self.rect.y += self.vel_y
        self.on_ground = False

        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                # Check if it's a spike
                is_spike = platform.image.get_at((0, 0)) == GRAY
                
                if is_spike:
                    if not self.invulnerable:
                        self.get_hit()
                else:
                    if self.vel_y > 0:  # Falling down
                        self.rect.bottom = platform.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                    elif self.vel_y < 0:  # Jumping up
                        self.rect.top = platform.rect.bottom
                        self.vel_y = 0

        # Horizontal movement
        self.rect.x += self.vel_x
        
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                is_spike = platform.image.get_at((0, 0)) == GRAY
                
                if is_spike:
                    if not self.invulnerable:
                        self.get_hit()
                else:
                    if self.vel_x > 0:  # Moving right
                        self.rect.right = platform.rect.left
                    elif self.vel_x < 0:  # Moving left
                        self.rect.left = platform.rect.right

        # Enemy collision - REVISED LOGIC
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                # Check if we're stomping the enemy (coming from above)
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.top + 10:
                    enemy.kill()
                    self.vel_y = JUMP_HEIGHT / 2  # Bounce
                else:
                    # Side or bottom collision
                    if not self.invulnerable:
                        self.get_hit()

        # Item collection
        for item in items:
            if self.rect.colliderect(item.rect):
                if item.type == 'coin':
                    self.coins += 1
                elif item.type == 'mushroom':
                    self.power_up = 'mushroom'
                    # Visual feedback for power-up
                    self.image.fill(ORANGE)  # Change color for mushroom power-up
                item.kill()

        # Screen boundary death fix - Only die if falling below screen
        if self.rect.y > SCREEN_HEIGHT + 100:  # Added buffer
            self.lives -= 1
            self.reset_position()

        # Horizontal screen wrapping for some levels (optional feature)
        # if self.rect.right < 0:
        #     self.rect.left = SCREEN_WIDTH
        # elif self.rect.left > SCREEN_WIDTH:
        #     self.rect.right = 0

    def get_hit(self):
        """Handle player getting hit"""
        self.lives -= 1
        self.invulnerable = True
        self.invulnerable_timer = 120  # 2 seconds at 60 FPS
        self.reset_position()

    def reset_position(self):
        """Reset player to starting position"""
        self.rect.x = 100
        self.rect.y = 400
        self.vel_y = 0
        self.vel_x = 0

    def jump(self):
        if self.on_ground:
            self.vel_y = JUMP_HEIGHT

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=GREEN):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type='goomba'):
        super().__init__()
        self.type = enemy_type
        self.image = pygame.Surface((28, 28))
        if enemy_type == 'goomba':
            self.image.fill(BROWN)
            self.vel_x = -1
        elif enemy_type == 'koopa':
            self.image.fill(GREEN)
            self.vel_x = -2
        elif enemy_type == 'flying':
            self.image.fill(ORANGE)
            self.vel_x = -1
            self.vel_y = 0
            self.fly_height = y
        else:
            self.image.fill(PURPLE)
            self.vel_x = -1
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.move_counter = 0

    def update(self):
        # Update horizontal position
        self.rect.x += self.vel_x
        
        # Handle flying enemies
        if self.type == 'flying':
            self.move_counter += 1
            # Simplified flying pattern
            self.rect.y = self.fly_height + int(20 * math.sin(self.move_counter * 0.1))
        
        # Keep enemies within level bounds (prevent them from wandering off)
        # This uses the level width (3x screen width as defined in enemy class)
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH * 3:
            self.vel_x = -self.vel_x
            # Flip the image to face the other direction (visual improvement)
            self.image = pygame.transform.flip(self.image, True, False)

# Import math for sine function in flying enemies
import math

class Item(pygame.sprite.Sprite):
    def __init__(self, x, y, item_type='coin'):
        super().__init__()
        self.type = item_type
        self.image = pygame.Surface((20, 20))
        if item_type == 'coin':
            self.image.fill(YELLOW)
        elif item_type == 'mushroom':
            self.image.fill(RED)
        else:
            self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# Level definitions with proper playable layouts
# Legend: G=ground, B=brick, P=pipe, C=coin, M=mushroom, E=goomba, K=koopa, F=flying enemy, S=spike, W=water, I=ice, .=empty
levels = [
    {
        "name": "Wild Ride in the Sky",
        "theme": "sky",
        "tiles": [
            "                                                            ",
            "                  CCC                    CCC               ",
            "                 BBBBB                  BBBBB              ",
            "       CCC                   F                    CCC      ",
            "      BBBBB             BB        BB            BBBBB      ",
            "                   BB                  BB                  ",
            "             BB              K              BB       E     ",
            "   GGG                                            GGG      ",
            "                                                            ",
            "         GGGG                                  GGGG        ",
            "                    GGGGG        GGGGG                     ",
            "                           GGGG                            ",
            "    M                                                      ",
            "GGGGGGGG                                        GGGGGGGGGG",
            "GGGGGGGG                                        GGGGGGGGGG",
            "GGGGGGGG                                        GGGGGGGGGG",
        ]
    },
    {
        "name": "Slidin' the Slopes",
        "theme": "ice",
        "tiles": [
            "                                                            ",
            "                                                      C     ",
            "                                                    III     ",
            "                                                  III       ",
            "                             E                  III         ",
            "         C               IIIIIII              III           ",
            "       III             III     III          III             ",
            "     III             III         III      III               ",
            "   III      K      III             III  III                 ",
            " III             III                 IIII                   ",
            "II             III                                          ",
            "             III                          E                 ",
            "           III                      IIIIIIIIIIII            ",
            "         III                      IIIIIIIIIIIIIIII          ",
            "       III                      IIIIIIIIIIIIIIIIIIII        ",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        ]
    },
    {
        "name": "Vegetable Volley",
        "theme": "grass",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "    C   C   C        E        C   C   C        K           ",
            "   BB  BB  BB               BB  BB  BB                     ",
            "                  GGGG                      GGGG           ",
            "         E                        E                  E      ",
            "      GGGGG                    GGGGG              GGGGG    ",
            "                   M                                        ",
            "             GGGGGGGGGG                  GGGGGGGG          ",
            "   GGG                     GGG                              ",
            "           E                        E           E           ",
            "         GGG              GGG              GGG             ",
            "                                                            ",
            "      C  C  C          C  C  C          C  C  C            ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Doors o' Plenty",
        "theme": "underground",
        "tiles": [
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "B   P   B   P   B       B   P   B   P   B   C   B   P    B",
            "B       B       B   E   B       B       B       B        B",
            "B   B   B   B   BBBBBBBBB   B   B   B   B   B   B   B    B",
            "B   B       B           B   B       B       B       B    B",
            "B   BBBBBBBBB   BBBBB   B   BBBBBBBBB   BBBBBBBBBBBBB    B",
            "B                   B               B                    B",
            "BBBBBBBBB   BBBBB   B   BBBBB   B   B   BBBBBBBB   BBBBBB",
            "B       B   B   B   B       B   B           B   B        B",
            "B   M   B   B   B   BBBBB   B   BBBBBBBBB   B   BBBBB    B",
            "B       B       B       B   B           B       B        B",
            "B   BBBBBBBBB   B   B   B   BBBBB   B   B   B   B   B    B",
            "B           B   B   B       B       B   B   B   B   B    B",
            "B   E   K   B   B   BBBBBBBBB   BBBBB   B   B   B   B    B",
            "B           B                           B       B        B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Bombarded by Bob-ombs",
        "theme": "castle",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "      E       E       E       E       E       E            ",
            "    PPPP    PPPP    PPPP    PPPP    PPPP    PPPP          ",
            "                                                            ",
            "  C     C     C     C     C     C     C     C     C       ",
            "BBB   BBB   BBB   BBB   BBB   BBB   BBB   BBB   BBB       ",
            "                                                            ",
            "     E       E       E       E       E       E             ",
            "   PPPP    PPPP    PPPP    PPPP    PPPP    PPPP            ",
            "                                                            ",
            "BBB   BBB   BBB   BBB   BBB   BBB   BBB   BBB   BBB       ",
            "                              M                             ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Magical Note Blocks",
        "theme": "music",
        "tiles": [
            "                                                            ",
            "         C C C           C C C           C C C             ",
            "        NNNNNN          NNNNNN          NNNNNN             ",
            "                                                            ",
            "    F           F           F           F           F      ",
            "  NNNN        NNNN        NNNN        NNNN        NNNN    ",
            "                                                            ",
            "         NNN       NNN       NNN       NNN       NNN       ",
            "                                                            ",
            "   E         E         E         E         E         E     ",
            "NNNNNN    NNNNNN    NNNNNN    NNNNNN    NNNNNN    NNNNNN  ",
            "                                                            ",
            "      M                                                     ",
            "NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "The ol' Switcheroo",
        "theme": "puzzle",
        "tiles": [
            "                                                            ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB  ",
            "B C C C C C C C C C C C C C C C C C C C C C C C C C C C B  ",
            "B                                                       B  ",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB  B  ",
            "B                                                    B  B  ",
            "B  E     K     E     K     E     K     E     K      B  B  ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB B  B  ",
            "                                                   B B  B  ",
            "                                                   B B  B  ",
            "  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB B  B  ",
            "  B                                                  B  B  ",
            "  B  M              S S S S S S S S S S              B  B  ",
            "  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB  ",
            "                                                            ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Piped Full of Plants",
        "theme": "pipe",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "       E          E          E          E          E       ",
            "      PPP        PPP        PPP        PPP        PPP      ",
            "      PPP        PPP        PPP        PPP        PPP      ",
            "      PPP        PPP        PPP        PPP        PPP      ",
            "                                    C C C                  ",
            "   C        C         C         GGGGGGGGGGG       C        ",
            "GGGGG    GGGGG     GGGGG                        GGGGG      ",
            "            E          E          E          E             ",
            "           PPP        PPP        PPP        PPP            ",
            "           PPP        PPP        PPP        PPP            ",
            "           PPP   M    PPP        PPP        PPP            ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Swinging Bars of Doom",
        "theme": "castle",
        "tiles": [
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "B                                                         B",
            "B     S S S     S S S     S S S     S S S     S S S      B",
            "B   BBBBBBB   BBBBBBB   BBBBBBB   BBBBBBB   BBBBBBB      B",
            "B                                                         B",
            "B         E         E         E         E         E       B",
            "B   C   BBBBBB   BBBBBB   BBBBBB   BBBBBB   BBBBBB   C   B",
            "B   C                                                 C   B",
            "BBBBBBB      BBBBBB      BBBBBB      BBBBBB      BBBBBB  B",
            "B                                                         B",
            "B     S S S     S S S     S S S     S S S     S S S      B",
            "B   BBBBBBB   BBBBBBB   BBBBBBB   BBBBBBB   BBBBBBB      B",
            "B         M                                               B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   BBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Para Beetle Challenge",
        "theme": "sky",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "         F         F         F         F         F         ",
            "                                                            ",
            "    BB       BB       BB       BB       BB       BB        ",
            "                                                            ",
            "                C C C     C C C     C C C                  ",
            "         F         F         F         F         F         ",
            "                                                            ",
            "  BB       BB       BB       BB       BB       BB       BB ",
            "                                                            ",
            "       F         F         F         F         F           ",
            "                                                            ",
            "GGG                                                     GGG",
            "GGG           M                                         GGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Puzzlin' Pipe Maze",
        "theme": "pipe",
        "tiles": [
            "PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP",
            "P      P     P     P     P     P     P     P     P      P",
            "P  PP  P  PP P  PP P  PP P  PP P  PP P  PP P  PP P  PP  P",
            "P  PC  P  PC P  PC P  PC P  PC P  PC P  PC P  PC P  PC  P",
            "P  PP  PP PP PP PP PP PP PP PP PP PP PP PP PP PP PP PP  P",
            "P                                                        P",
            "PPPPPP  PPPPPP  PPPPPP  PPPPPP  PPPPPP  PPPPPP  PPPPPP  P",
            "P                                                        P",
            "P  E     K     E     K     E     K     E     K     E    P",
            "P  PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP   P",
            "P                                                        P",
            "P  PPPP  PPPP  PPPP  PPPP  PPPP  PPPP  PPPP  PPPP  PPP  P",
            "P     P     P     P     P     P     P     P     P    M  P",
            "PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PPP  PP",
            "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
            "PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP",
        ]
    },
    {
        "name": "A Towering Tour",
        "theme": "tower",
        "tiles": [
            "BBBB                                                  BBBB",
            "B  B            C C C C C C C C C C                   B  B",
            "B  B          BBBBBBBBBBBBBBBBBBBBBBB                 B  B",
            "B  B      E                         E                 B  B",
            "B  BBBBBBBBBB                   BBBBBBBBBB            B  B",
            "B                                         B           B  B",
            "B           BBBBBBBBBBBBBBBBBBBBBBB       B           B  B",
            "B       K                         K       B           B  B",
            "B   BBBBBBBB                   BBBBBBBB   B           B  B",
            "B                                         B           B  B",
            "B         BBBBBBBBBBBBBBBBBBBBBBBBB       B           B  B",
            "B     E                           E       B           B  B",
            "B BBBBBBBB       M           BBBBBBBB     B           B  B",
            "B                                         B           B  B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Slip Slidin' Away",
        "theme": "ice",
        "tiles": [
            "                                                            ",
            "                       C C C                                ",
            "                     IIIIIIIII                              ",
            "           E                        E                       ",
            "        IIIIII                   IIIIII                     ",
            "                    K                      K                ",
            "     IIIII      IIIIIII      IIIII      IIIIIII            ",
            "                                                            ",
            "  III                                            III        ",
            "            E              E              E                 ",
            "         IIIII          IIIII          IIIII               ",
            "                                                            ",
            "      M                                                     ",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        ]
    },
    {
        "name": "Ice Cream Isle",
        "theme": "ice",
        "tiles": [
            "                                                            ",
            "        C     C     C     C     C     C     C              ",
            "      III   III   III   III   III   III   III             ",
            "                                                            ",
            "    F         F         F         F         F              ",
            "  IIIII    IIIII    IIIII    IIIII    IIIII    IIIII      ",
            "                                                            ",
            "         E         E         E         E         E         ",
            "      IIIIII    IIIIII    IIIIII    IIIIII    IIIIII       ",
            "                                                            ",
            "   III      III      III      III      III      III        ",
            "                                                            ",
            "         M                                                  ",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        ]
    },
    {
        "name": "A Sky-High Adventure",
        "theme": "sky",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "      C           C           C           C           C    ",
            "     BBB         BBB         BBB         BBB         BBB   ",
            "                                                            ",
            "           F           F           F           F           ",
            "         BBB         BBB         BBB         BBB           ",
            "                                                            ",
            "    BBB         BBB         BBB         BBB         BBB    ",
            "                                                            ",
            "         E           E           E           E             ",
            "       BBBBB       BBBBB       BBBBB       BBBBB           ",
            "                                                            ",
            "GG                  M                                    GG",
            "GGG                                                     GGG",
            "GGGG                                                   GGGG",
        ]
    },
    {
        "name": "Sea to Sky",
        "theme": "water",
        "tiles": [
            "                                                            ",
            "                  C C C           C C C                     ",
            "                BBBBBBB         BBBBBBB                    ",
            "      F                                   F                ",
            "    BBBB              E     E           BBBB               ",
            "              BBBB                BBBB                     ",
            "                    BBBB    BBBB                           ",
            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            "                                                            ",
            "      GGG         GGG         GGG         GGG              ",
            "                                                            ",
            "            M                                               ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "A Musical Lesson",
        "theme": "music",
        "tiles": [
            "                                                            ",
            "    C   C   C   C   C   C   C   C   C   C   C   C   C     ",
            "   NN  NN  NN  NN  NN  NN  NN  NN  NN  NN  NN  NN  NN    ",
            "                                                            ",
            "        E       E       E       E       E       E          ",
            "      NNNN    NNNN    NNNN    NNNN    NNNN    NNNN        ",
            "                                                            ",
            "   NN      NN      NN      NN      NN      NN      NN     ",
            "                                                            ",
            "       K       K       K       K       K       K           ",
            "     NNNNNN  NNNNNN  NNNNNN  NNNNNN  NNNNNN  NNNNNN       ",
            "                                                            ",
            "           M                                                ",
            "NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "The Big Switch",
        "theme": "puzzle",
        "tiles": [
            "                                                            ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "                                                            ",
            "  C C C C C C C C C C C C C C C C C C C C C C C C C C C    ",
            "  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   ",
            "                                                            ",
            "      E     K     E     K     E     K     E     K          ",
            "    BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB        ",
            "                                                            ",
            "  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB    ",
            "                                                            ",
            "        S S S S S S S S S S S S S S S S S S S S S          ",
            "      M                                                     ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Sea Pipe Statues",
        "theme": "water",
        "tiles": [
            "                                                            ",
            "       PPP       PPP       PPP       PPP       PPP         ",
            "       PCP       PCP       PCP       PCP       PCP         ",
            "       PPP       PPP       PPP       PPP       PPP         ",
            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            "                                                            ",
            "    E       E       E       E       E       E              ",
            "  GGGG    GGGG    GGGG    GGGG    GGGG    GGGG            ",
            "                                                            ",
            "       PPP       PPP       PPP       PPP       PPP         ",
            "       PPP       PPP       PPP       PPP       PPP         ",
            "                                                            ",
            "         M                                                  ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Jumping Piranha Plant",
        "theme": "plant",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "      E     E     E     E     E     E     E     E          ",
            "     PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP        ",
            "     PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP        ",
            "                                                            ",
            "   C     C     C     C     C     C     C     C     C      ",
            "  GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG     ",
            "                                                            ",
            "     E     E     E     E     E     E     E     E           ",
            "    PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP          ",
            "    PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP          ",
            "              M                                             ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Piped Full of Piranhas",
        "theme": "pipe",
        "tiles": [
            "PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP",
            "PEP   PEP   PEP   PEP   PEP   PEP   PEP   PEP   PEP   PEP",
            "PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP",
            "                                                            ",
            "   C     C     C     C     C     C     C     C     C      ",
            "  GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG     ",
            "                                                            ",
            "PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP",
            "PKP   PKP   PKP   PKP   PKP   PKP   PKP   PKP   PKP   PKP",
            "PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP   PPP",
            "                                                            ",
            "  GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG   GGG     ",
            "            M                                               ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Armored Airship",
        "theme": "airship",
        "tiles": [
            "                                                            ",
            "    C     C     C     C     C     C     C     C     C     ",
            "  SSSSS SSSSS SSSSS SSSSS SSSSS SSSSS SSSSS SSSSS SSSSS   ",
            "  BBBBB BBBBB BBBBB BBBBB BBBBB BBBBB BBBBB BBBBB BBBBB   ",
            "                                                            ",
            "     E     E     E     E     E     E     E     E           ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "B                                                         B",
            "B    PPP    PPP    PPP    PPP    PPP    PPP    PPP       B",
            "B    PEP    PEP    PEP    PEP    PEP    PEP    PEP       B",
            "B    PPP    PPP    PPP    PPP    PPP    PPP    PPP       B",
            "B                                                         B",
            "B          M                                              B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "A Flying Battleship",
        "theme": "airship",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "      F       F       F       F       F       F            ",
            "    BBBB    BBBB    BBBB    BBBB    BBBB    BBBB          ",
            "                                                            ",
            "  BBB    BBB    BBB    BBB    BBB    BBB    BBB    BBB    ",
            "                                                            ",
            "     E     E     E     E     E     E     E     E           ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "B  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  B",
            "B                                                         B",
            "B    K     K     K     K     K     K     K     K         B",
            "B          M                                              B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Ice Dungeon",
        "theme": "ice",
        "tiles": [
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "I                                                         I",
            "I  C  C  C        E        E        E        C  C  C     I",
            "I  IIIIIII   IIIIIIIIIIIIIIIIIIIIIIIIIIII   IIIIIII      I",
            "I                                                         I",
            "I      K                                     K            I",
            "IIII  IIII  IIIIIIIIIIIIIIIIIIIIIIIIIIIIII  IIII  IIII   I",
            "I                                                         I",
            "I   IIIIIIIIII   IIIIIIIIIIIIIIIIIIII   IIIIIIIIII       I",
            "I                                                         I",
            "I       E     E     E     E     E     E     E            I",
            "I   IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII       I",
            "I             M                                           I",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",
        ]
    },
    {
        "name": "Gusty Glade",
        "theme": "wind",
        "tiles": [
            "                                                            ",
            "         C         C         C         C         C         ",
            "       GGGG      GGGG      GGGG      GGGG      GGGG        ",
            "                                                            ",
            "    F         F         F         F         F              ",
            "  GGGG      GGGG      GGGG      GGGG      GGGG      GGGG   ",
            "                                                            ",
            "        E         E         E         E         E          ",
            "      GGGG      GGGG      GGGG      GGGG      GGGG         ",
            "                                                            ",
            "   GG      GG      GG      GG      GG      GG      GG      ",
            "                                                            ",
            "         M                                                  ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Castle Dash",
        "theme": "castle",
        "tiles": [
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "B                                                         B",
            "B  S S S S S S S S S S S S S S S S S S S S S S S S S S    B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B                                                         B",
            "B    E   E   E   E   E   E   E   E   E   E   E   E        B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B                                                         B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B    K   K   K   K   K   K   K   K   K   K   K   K        B",
            "B                                                         B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B           M                                             B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Rich with Raccoons",
        "theme": "forest",
        "tiles": [
            "                                                            ",
            "    C C C C C C C C C C C C C C C C C C C C C C C C        ",
            "   GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG      ",
            "                                                            ",
            "      E       E       E       E       E       E            ",
            "    GGGG    GGGG    GGGG    GGGG    GGGG    GGGG          ",
            "                                                            ",
            "  GGG    GGG    GGG    GGG    GGG    GGG    GGG    GGG    ",
            "                                                            ",
            "     K       K       K       K       K       K             ",
            "   GGGGG   GGGGG   GGGGG   GGGGG   GGGGG   GGGGG          ",
            "                                                            ",
            "         M M M M M                                          ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "It's a Shoe-In",
        "theme": "shoe",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "    S S S S S S S S S S S S S S S S S S S S S S S S       ",
            "  GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG     ",
            "                                                            ",
            "      E       E       E       E       E       E            ",
            "    GGGG    GGGG    GGGG    GGGG    GGGG    GGGG          ",
            "  S S S S S S S S S S S S S S S S S S S S S S S S S       ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG     ",
            "                                                            ",
            "    K       K       K       K       K       K              ",
            "  GGGGG   GGGGG   GGGGG   GGGGG   GGGGG   GGGGG           ",
            "        M M M                                               ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Airship's Revenge",
        "theme": "airship",
        "tiles": [
            "                                                            ",
            "  F   F   F   F   F   F   F   F   F   F   F   F   F       ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "B                                                         B",
            "B  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C  C     B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B                                                         B",
            "B    E   E   E   E   E   E   E   E   E   E   E   E        B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B                                                         B",
            "B    K   K   K   K   K   K   K   K   K   K   K   K        B",
            "B  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB   B",
            "B           M                                             B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Classic World 1-1",
        "theme": "classic",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "           C                                                ",
            "                                                            ",
            "         BBBCB              C C                             ",
            "                          BBBBBBB            BB            ",
            "                 PPP                        BB             ",
            "                PPPP                      BB               ",
            "    C          PPPPP                    BB                 ",
            "              PPPPPP                  BB                   ",
            "      E   E  PPPPPPP  E     K   E   BB     E     E     E   ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Classic World 1-2",
        "theme": "underground",
        "tiles": [
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "B                                                         B",
            "B                   C C C                                 B",
            "B                 BBBBBBBBB                  PPP         B",
            "B                                            PPP         B",
            "B         BBBB              BBBB             PPP         B",
            "B                                            PPP         B",
            "B   E         E         E         E          PPP         B",
            "B BBBBB   BBBBBBB   BBBBBBB   BBBBBBB                    B",
            "B                                        BBBBBBBBB        B",
            "B     K         K         K         K                     B",
            "B                                                         B",
            "B       M                                                 B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Classic World 1-3",
        "theme": "classic",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "         C C                     C C                       ",
            "       BBBBBBB                 BBBBBBB                     ",
            "                                                            ",
            "    F         F         F         F         F              ",
            "  BBBB      BBBB      BBBB      BBBB      BBBB            ",
            "                                                            ",
            "        BBBB      BBBB      BBBB      BBBB      BBBB       ",
            "                                                            ",
            "            E         E         E         E                ",
            "          BBBB      BBBB      BBBB      BBBB               ",
            "                                                            ",
            "GGG                 M                                  GGG ",
            "GGGG                                                  GGGG ",
            "GGGGG                                                GGGGG ",
        ]
    },
    {
        "name": "Classic World 1-4",
        "theme": "castle",
        "tiles": [
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "B                                                         B",
            "B                                                         B",
            "B     BBBBBBBBBBBB          BBBBBBBBBBBB                  B",
            "B                                                         B",
            "B                    E E E                   S S S S      B",
            "B              BBBBBBBBBBBBBBBBBB      BBBBBBBBBBBBBBB    B",
            "B                                                         B",
            "B   BBBBBB                        BBBBBB                  B",
            "B                                                         B",
            "B           BBBBBBBBBBBBBBBBBBBBBBBB                      B",
            "B       K                               K       K         B",
            "B       M                                                 B",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
        ]
    },
    {
        "name": "Classic World 2-1",
        "theme": "classic",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "      C C C           C C C           C C C                ",
            "    BBBBBBBBB       BBBBBBBBB       BBBBBBBBB              ",
            "                                                            ",
            "         E             E             E             E        ",
            "       GGGG          GGGG          GGGG          GGGG      ",
            "                                                            ",
            "   GGG      GGG  GGG      GGG  GGG      GGG  GGG           ",
            "                                                            ",
            "        K         K         K         K         K          ",
            "      GGGGG     GGGGG     GGGGG     GGGGG     GGGGG        ",
            "            M                                               ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Classic World 2-2",
        "theme": "water",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "       C     C     C     C     C     C     C               ",
            "     BBBB  BBBB  BBBB  BBBB  BBBB  BBBB  BBBB             ",
            "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
            "                                                            ",
            "    E       E       E       E       E       E              ",
            "  GGGG    GGGG    GGGG    GGGG    GGGG    GGGG            ",
            "                                                            ",
            "       K       K       K       K       K       K           ",
            "     GGGGG   GGGGG   GGGGG   GGGGG   GGGGG   GGGGG        ",
            "                                                            ",
            "           M                                                ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Classic World 3-1",
        "theme": "classic",
        "tiles": [
            "                                                            ",
            "                                                            ",
            "         F         F         F         F         F         ",
            "       BBBB      BBBB      BBBB      BBBB      BBBB        ",
            "                                                            ",
            "    C       C       C       C       C       C              ",
            "  GGGG    GGGG    GGGG    GGGG    GGGG    GGGG            ",
            "                                                            ",
            "       E       E       E       E       E       E           ",
            "     GGGGG   GGGGG   GGGGG   GGGGG   GGGGG   GGGGG        ",
            "                                                            ",
            "  GG      GG      GG      GG      GG      GG      GG      ",
            "            M                                               ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Classic World 4-1",
        "theme": "classic",
        "tiles": [
            "                                                            ",
            "    C   C   C   C   C   C   C   C   C   C   C   C         ",
            "  BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB       ",
            "                                                            ",
            "      F       F       F       F       F       F            ",
            "    GGGG    GGGG    GGGG    GGGG    GGGG    GGGG          ",
            "                                                            ",
            "  E     E     E     E     E     E     E     E     E       ",
            "GGGG  GGGG  GGGG  GGGG  GGGG  GGGG  GGGG  GGGG  GGGG     ",
            "                                                            ",
            "    K     K     K     K     K     K     K     K           ",
            "  GGGGG GGGGG GGGGG GGGGG GGGGG GGGGG GGGGG GGGGG         ",
            "          M                                                 ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    },
    {
        "name": "Mad Dash",
        "theme": "speed",
        "tiles": [
            "                                                            ",
            "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
            "                                                            ",
            "  E E E E E E E E E E E E E E E E E E E E E E E E E E E    ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "                                                            ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "                                                            ",
            "  K K K K K K K K K K K K K K K K K K K K K K K K K K K    ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "                                                            ",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB ",
            "      M M M M M                                             ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
    }
]

# Parse tile character to create game objects
def parse_tile(char, x, y, platforms, enemies, items):
    if char == 'G':  # Ground/Grass
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, GREEN))
    elif char == 'B':  # Brick
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, BROWN))
    elif char == 'I':  # Ice
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, LIGHT_BLUE))
    elif char == 'P':  # Pipe
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, GREEN))
    elif char == 'N':  # Note block
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, YELLOW))
    elif char == 'W':  # Water (decorative)
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, BLUE))
    elif char == 'S':  # Spike (hazard)
        platforms.add(Platform(x, y, TILE_SIZE, TILE_SIZE, GRAY))
    elif char == 'E':  # Goomba enemy
        enemies.add(Enemy(x, y, 'goomba'))
    elif char == 'K':  # Koopa enemy
        enemies.add(Enemy(x, y, 'koopa'))
    elif char == 'F':  # Flying enemy
        enemies.add(Enemy(x, y, 'flying'))
    elif char == 'C':  # Coin
        items.add(Item(x, y + 5, 'coin'))
    elif char == 'M':  # Mushroom
        items.add(Item(x, y + 5, 'mushroom'))

# World-e Overworld
def draw_overworld(screen, selected_level):
    screen.fill(SKY_BLUE)
    # Draw e-shaped island
    pygame.draw.rect(screen, GREEN, (200, 200, 400, 200))
    pygame.draw.rect(screen, GREEN, (200, 200, 100, 100))
    pygame.draw.rect(screen, GREEN, (500, 200, 100, 100))
    pygame.draw.rect(screen, GREEN, (200, 300, 100, 100))
    font = pygame.font.SysFont(None, 24)
    title = font.render("World-e: Select a Level (↑/↓ to select, Enter to play)", True, WHITE)
    screen.blit(title, (100, 50))
    # Display level list with scrolling
    visible_start = max(0, selected_level - 7)
    visible_end = min(len(levels), visible_start + 15)
    for i in range(visible_start, visible_end):
        color = RED if i == selected_level else WHITE
        text = font.render(f"{i+1}: {levels[i]['name']}", True, color)
        screen.blit(text, (100, 100 + (i - visible_start) * 30))

# Play a level
def play_level(screen, level_data):
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    items = pygame.sprite.Group()
    player = Player()
    all_sprites.add(player)

    # Parse level tiles
    tiles = level_data.get("tiles", [])
    map_width = len(tiles[0]) * TILE_SIZE if tiles and tiles[0] else SCREEN_WIDTH * 2
    map_height = len(tiles) * TILE_SIZE if tiles else SCREEN_HEIGHT
    
    for row_idx, row in enumerate(tiles):
        for col_idx, tile in enumerate(row):
            x = col_idx * TILE_SIZE
            y = row_idx * TILE_SIZE
            parse_tile(tile, x, y, platforms, enemies, items)

    all_sprites.add(platforms, enemies, items)
    camera = Camera(map_width, map_height)
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        keys = pygame.key.get_pressed()
        player.vel_x = 0
        if keys[pygame.K_LEFT]:
            player.vel_x = -PLAYER_SPEED
            player.facing_right = False
        if keys[pygame.K_RIGHT]:
            player.vel_x = PLAYER_SPEED
            player.facing_right = True
        if keys[pygame.K_SPACE]:
            player.jump()

        # Update game objects
        player.update(platforms, enemies, items)
        enemies.update()
        camera.update(player)

        # Draw everything
        theme = level_data.get("theme", "")
        if theme == "sky":
            screen.fill(SKY_BLUE)
        elif theme == "underground" or theme == "castle":
            screen.fill(BLACK)
        elif theme == "water":
            screen.fill(BLUE)
        elif theme == "ice":
            screen.fill(LIGHT_BLUE)
        else:
            screen.fill(SKY_BLUE)

        for sprite in all_sprites:
            screen.blit(sprite.image, camera.apply(sprite))

        # Draw HUD
        font = pygame.font.SysFont(None, 24)
        level_text = font.render(f"{level_data['name']}", True, WHITE)
        stats_text = font.render(f"Coins: {player.coins}  Lives: {player.lives}", True, WHITE)
        screen.blit(level_text, (10, 10))
        screen.blit(stats_text, (10, 35))

        # Game over screen
        if player.lives <= 0:
            game_over = font.render("GAME OVER! Press ESC", True, RED)
            screen.blit(game_over, (SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2))

        # Win condition (optional - you could add flagpole or similar)
        # For now, we'll just let players explore

        pygame.display.flip()
        clock.tick(60)

    return True

# Main function
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ultra Mario 2D Bros 2: PC Port")
    clock = pygame.time.Clock()
    state = "overworld"
    selected_level = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if state == "overworld":
                    if event.key == pygame.K_RETURN:
                        state = "level"
                    elif event.key == pygame.K_UP:
                        selected_level = (selected_level - 1) % len(levels)
                    elif event.key == pygame.K_DOWN:
                        selected_level = (selected_level + 1) % len(levels)

        if state == "overworld":
            draw_overworld(screen, selected_level)
        elif state == "level":
            if not play_level(screen, levels[selected_level]):
                running = False
            state = "overworld"

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
