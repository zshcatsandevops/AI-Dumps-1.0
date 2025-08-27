import pygame
import asyncio
import platform

# Initialize Pygame
pygame.init()

# Screen settings - PC resolution (600x400)
WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World - Tech Demo")

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
PIPE_GREEN = (0, 120, 0)
GRAY = (100, 100, 100)

# Game settings
FPS = 60
GRAVITY = 0.5
JUMP_FORCE = -9
MOVE_SPEED = 3

# Scaling factor for NES to PC resolution
SCALE = 2

# Game states
TITLE_SCREEN = 0
WORLD_MAP = 1
LEVEL = 2
LEVEL_COMPLETE = 3
GAME_OVER = 4

# Current game state
game_state = TITLE_SCREEN
current_world = 1
current_level = 1
unlocked_worlds = [1]
score = 0
coins = 0
lives = 3
time_left = 300

# Mario class
class Mario:
    def __init__(self, x, y):
        self.width, self.height = 16 * SCALE, 16 * SCALE
        self.x, self.y = x, y
        self.vx, self.vy = 0, 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False
        self.facing_right = True
        self.frame = 0
        self.animation_timer = 0
        self.invincible = False
        self.invincible_timer = 0

    def update(self, keys, platforms, pipes):
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

        # Pipe collision
        for pipe in pipes:
            if self.rect.colliderect(pipe.rect):
                if self.vy > 0 and self.rect.bottom <= pipe.rect.bottom:
                    self.rect.bottom = pipe.rect.top
                    self.y = self.rect.y
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0 and self.rect.top >= pipe.rect.top:
                    self.rect.top = pipe.rect.bottom
                    self.y = self.rect.y
                    self.vy = 0

        # Keep Mario on screen
        self.x = max(0, min(self.x, WIDTH - self.width))
        if self.y > HEIGHT:
            self.die()
            
        self.rect.topleft = (self.x, self.y)
        
        # Update invincibility
        if self.invincible:
            self.invincible_timer += 1
            if self.invincible_timer > 120:
                self.invincible = False
                self.invincible_timer = 0
        
    def animate(self):
        self.animation_timer += 1
        if self.animation_timer > 10:
            self.frame = (self.frame + 1) % 2
            self.animation_timer = 0

    def draw(self, surface):
        if self.invincible and self.invincible_timer % 10 < 5:
            return
            
        color = RED if self.facing_right else (200, 0, 0)
        
        # Body
        pygame.draw.rect(surface, color, self.rect)
        
        # Overalls
        pygame.draw.rect(surface, BLUE, 
                         (self.x + 2*SCALE, self.y + 8*SCALE, self.width - 4*SCALE, self.height - 8*SCALE))
        
        # Cap
        pygame.draw.rect(surface, color, 
                         (self.x, self.y, self.width, 4*SCALE))
        
        # Animation - moving legs
        if self.vx != 0 and self.on_ground:
            leg_offset = 2*SCALE if self.frame == 0 else -2*SCALE
            pygame.draw.rect(surface, BLUE, 
                            (self.x + 4*SCALE, self.y + self.height - 4*SCALE, 4*SCALE, leg_offset))
            pygame.draw.rect(surface, BLUE, 
                            (self.x + self.width - 8*SCALE, self.y + self.height - 4*SCALE, 4*SCALE, -leg_offset))
    
    def die(self):
        global lives, game_state
        lives -= 1
        if lives <= 0:
            game_state = GAME_OVER
        else:
            reset_level()

# Platform class
class Platform:
    def __init__(self, x, y, width, height, color=BROWN):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        
        for i in range(0, self.rect.width, 4*SCALE):
            for j in range(0, self.rect.height, 4*SCALE):
                if (i // (4*SCALE) + j // (4*SCALE)) % 2 == 0:
                    pygame.draw.rect(surface, (min(self.color[0] + 20, 255), 
                                             min(self.color[1] + 20, 255), 
                                             min(self.color[2] + 20, 255)), 
                                    (self.rect.x + i, self.rect.y + j, 2*SCALE, 2*SCALE))

# Pipe class
class Pipe:
    def __init__(self, x, y, height):
        self.width = 32 * SCALE
        self.height = height
        self.x, self.y = x, y
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        pygame.draw.rect(surface, PIPE_GREEN, self.rect)
        pygame.draw.rect(surface, PIPE_GREEN, (self.x - 4*SCALE, self.y, self.width + 8*SCALE, 8*SCALE))
        pygame.draw.rect(surface, (0, 150, 0), (self.x, self.y + 8*SCALE, 4*SCALE, self.height - 8*SCALE))
        pygame.draw.rect(surface, (0, 150, 0), (self.x + self.width - 4*SCALE, self.y + 8*SCALE, 4*SCALE, self.height - 8*SCALE))

# Goomba class
class Goomba:
    def __init__(self, x, y):
        self.width, self.height = 16 * SCALE, 16 * SCALE
        self.x, self.y = x, y
        self.vx = -1 * SCALE
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.frame = 0
        self.animation_timer = 0
        self.crushed = False
        self.crush_timer = 0

    def update(self, platforms, pipes):
        if self.crushed:
            self.crush_timer += 1
            if self.crush_timer > 30:
                return True
            return False
            
        self.x += self.vx
        self.rect.topleft = (self.x, self.y)
        
        self.animate()

        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right
                self.x = self.rect.x
                self.vx = -self.vx

        for pipe in pipes:
            if self.rect.colliderect(pipe.rect):
                if self.vx > 0:
                    self.rect.right = pipe.rect.left
                elif self.vx < 0:
                    self.rect.left = pipe.rect.right
                self.x = self.rect.x
                self.vx = -self.vx

        if self.x < 0 or self.x > WIDTH - self.width:
            self.vx = -self.vx
            self.x = max(0, min(self.x, WIDTH - self.width))
        self.rect.topleft = (self.x, self.y)
        return False
        
    def animate(self):
        self.animation_timer += 1
        if self.animation_timer > 20:
            self.frame = (self.frame + 1) % 2
            self.animation_timer = 0

    def draw(self, surface):
        if self.crushed:
            pygame.draw.rect(surface, BROWN, (self.x, self.y + self.height - 4*SCALE, self.width, 4*SCALE))
            return
            
        color = BROWN
        
        pygame.draw.ellipse(surface, color, self.rect)
        
        foot_offset = 2*SCALE if self.frame == 0 else 0
        pygame.draw.rect(surface, BROWN, (self.x + 2*SCALE, self.y + self.height - 2*SCALE, 4*SCALE, foot_offset))
        pygame.draw.rect(surface, BROWN, (self.x + self.width - 6*SCALE, self.y + self.height - 2*SCALE, 4*SCALE, -foot_offset))
        
        pygame.draw.rect(surface, WHITE, (self.x + 4*SCALE, self.y + 4*SCALE, 2*SCALE, 2*SCALE))
        pygame.draw.rect(surface, WHITE, (self.x + self.width - 6*SCALE, self.y + 4*SCALE, 2*SCALE, 2*SCALE))
    
    def crush(self):
        self.crushed = True
        return 100

# Coin class
class Coin:
    def __init__(self, x, y):
        self.width, self.height = 8 * SCALE, 16 * SCALE
        self.x, self.y = x, y
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.frame = 0
        self.animation_timer = 0
        self.collected = False

    def update(self):
        self.animate()
        
    def animate(self):
        self.animation_timer += 1
        if self.animation_timer > 10:
            self.frame = (self.frame + 1) % 4
            self.animation_timer = 0

    def draw(self, surface):
        if self.collected:
            return
            
        coin_offset = [0, -1*SCALE, -2*SCALE, -1*SCALE][self.frame]
        pygame.draw.ellipse(surface, YELLOW, (self.x, self.y + coin_offset, self.width, self.height))
    
    def collect(self):
        global coins, score
        if not self.collected:
            self.collected = True
            coins += 1
            score += 200
            return True
        return False

# Flagpole class
class Flagpole:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.height = 200 * SCALE
        self.flag_y = self.y
        self.flag_raised = False

    def update(self, mario):
        if not self.flag_raised and mario.x > self.x - 20 and mario.x < self.x + 20:
            self.flag_raised = True
            global game_state
            game_state = LEVEL_COMPLETE
            return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, (200, 200, 200), (self.x, self.y, 4*SCALE, self.height))
        if not self.flag_raised:
            pygame.draw.rect(surface, RED, (self.x + 4*SCALE, self.y, 16*SCALE, 10*SCALE))

# Cloud class for decoration
class Cloud:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.speed = 0.5 * SCALE

    def update(self):
        self.x -= self.speed
        if self.x < -40:
            self.x = WIDTH + 10

    def draw(self, surface):
        pygame.draw.ellipse(surface, WHITE, (self.x, self.y, 20*SCALE, 10*SCALE))
        pygame.draw.ellipse(surface, WHITE, (self.x + 10*SCALE, self.y - 5*SCALE, 25*SCALE, 12*SCALE))
        pygame.draw.ellipse(surface, WHITE, (self.x + 25*SCALE, self.y, 15*SCALE, 8*SCALE))

# Bush class for decoration
class Bush:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def draw(self, surface):
        pygame.draw.ellipse(surface, GREEN, (self.x, self.y, 20*SCALE, 12*SCALE))
        pygame.draw.ellipse(surface, GREEN, (self.x + 10*SCALE, self.y - 5*SCALE, 25*SCALE, 15*SCALE))
        pygame.draw.ellipse(surface, GREEN, (self.x + 25*SCALE, self.y, 15*SCALE, 10*SCALE))

# Level data - 5 levels for the tech demo
levels = {
    1: {
        1: {
            "platforms": [
                Platform(0, HEIGHT - 20*SCALE, WIDTH, 20*SCALE, GREEN),
                Platform(100*SCALE, HEIGHT - 60*SCALE, 40*SCALE, 10*SCALE),
                Platform(200*SCALE, HEIGHT - 80*SCALE, 60*SCALE, 10*SCALE),
                Platform(300*SCALE, HEIGHT - 100*SCALE, 40*SCALE, 10*SCALE),
            ],
            "pipes": [
                Pipe(400*SCALE, HEIGHT - 60*SCALE, 60*SCALE),
            ],
            "enemies": [
                Goomba(150*SCALE, HEIGHT - 36*SCALE),
                Goomba(250*SCALE, HEIGHT - 36*SCALE),
            ],
            "coins": [
                Coin(120*SCALE, HEIGHT - 80*SCALE),
                Coin(220*SCALE, HEIGHT - 100*SCALE),
                Coin(320*SCALE, HEIGHT - 120*SCALE),
            ],
            "flagpole": Flagpole(550*SCALE, HEIGHT - 180*SCALE),
            "start_pos": (50, HEIGHT - 60),
        },
        2: {
            "platforms": [
                Platform(0, HEIGHT - 20*SCALE, WIDTH, 20*SCALE, GREEN),
                Platform(80*SCALE, HEIGHT - 60*SCALE, 30*SCALE, 10*SCALE),
                Platform(160*SCALE, HEIGHT - 100*SCALE, 40*SCALE, 10*SCALE),
                Platform(240*SCALE, HEIGHT - 140*SCALE, 50*SCALE, 10*SCALE),
                Platform(340*SCALE, HEIGHT - 100*SCALE, 40*SCALE, 10*SCALE),
                Platform(420*SCALE, HEIGHT - 60*SCALE, 30*SCALE, 10*SCALE),
            ],
            "pipes": [
                Pipe(500*SCALE, HEIGHT - 80*SCALE, 80*SCALE),
            ],
            "enemies": [
                Goomba(100*SCALE, HEIGHT - 36*SCALE),
                Goomba(200*SCALE, HEIGHT - 36*SCALE),
                Goomba(300*SCALE, HEIGHT - 36*SCALE),
                Goomba(400*SCALE, HEIGHT - 36*SCALE),
            ],
            "coins": [
                Coin(90*SCALE, HEIGHT - 80*SCALE),
                Coin(170*SCALE, HEIGHT - 120*SCALE),
                Coin(250*SCALE, HEIGHT - 160*SCALE),
                Coin(350*SCALE, HEIGHT - 120*SCALE),
                Coin(430*SCALE, HEIGHT - 80*SCALE),
            ],
            "flagpole": Flagpole(550*SCALE, HEIGHT - 180*SCALE),
            "start_pos": (50, HEIGHT - 60),
        },
        3: {
            "platforms": [
                Platform(0, HEIGHT - 20*SCALE, WIDTH, 20*SCALE, GREEN),
                Platform(70*SCALE, HEIGHT - 70*SCALE, 40*SCALE, 10*SCALE),
                Platform(150*SCALE, HEIGHT - 110*SCALE, 50*SCALE, 10*SCALE),
                Platform(230*SCALE, HEIGHT - 70*SCALE, 40*SCALE, 10*SCALE),
                Platform(310*SCALE, HEIGHT - 110*SCALE, 50*SCALE, 10*SCALE),
                Platform(390*SCALE, HEIGHT - 70*SCALE, 40*SCALE, 10*SCALE),
            ],
            "pipes": [
                Pipe(480*SCALE, HEIGHT - 70*SCALE, 70*SCALE),
            ],
            "enemies": [
                Goomba(120*SCALE, HEIGHT - 36*SCALE),
                Goomba(220*SCALE, HEIGHT - 36*SCALE),
                Goomba(320*SCALE, HEIGHT - 36*SCALE),
            ],
            "coins": [
                Coin(80*SCALE, HEIGHT - 90*SCALE),
                Coin(160*SCALE, HEIGHT - 130*SCALE),
                Coin(240*SCALE, HEIGHT - 90*SCALE),
                Coin(320*SCALE, HEIGHT - 130*SCALE),
                Coin(400*SCALE, HEIGHT - 90*SCALE),
            ],
            "flagpole": Flagpole(550*SCALE, HEIGHT - 180*SCALE),
            "start_pos": (50, HEIGHT - 60),
        },
        4: {
            "platforms": [
                Platform(0, HEIGHT - 20*SCALE, WIDTH, 20*SCALE, GREEN),
                Platform(60*SCALE, HEIGHT - 80*SCALE, 40*SCALE, 10*SCALE),
                Platform(140*SCALE, HEIGHT - 120*SCALE, 60*SCALE, 10*SCALE),
                Platform(240*SCALE, HEIGHT - 80*SCALE, 40*SCALE, 10*SCALE),
                Platform(320*SCALE, HEIGHT - 120*SCALE, 60*SCALE, 10*SCALE),
                Platform(420*SCALE, HEIGHT - 80*SCALE, 40*SCALE, 10*SCALE),
            ],
            "pipes": [
                Pipe(200*SCALE, HEIGHT - 100*SCALE, 100*SCALE),
                Pipe(400*SCALE, HEIGHT - 100*SCALE, 100*SCALE),
            ],
            "enemies": [
                Goomba(100*SCALE, HEIGHT - 36*SCALE),
                Goomba(180*SCALE, HEIGHT - 36*SCALE),
                Goomba(280*SCALE, HEIGHT - 36*SCALE),
                Goomba(380*SCALE, HEIGHT - 36*SCALE),
            ],
            "coins": [
                Coin(70*SCALE, HEIGHT - 100*SCALE),
                Coin(150*SCALE, HEIGHT - 140*SCALE),
                Coin(250*SCALE, HEIGHT - 100*SCALE),
                Coin(330*SCALE, HEIGHT - 140*SCALE),
                Coin(430*SCALE, HEIGHT - 100*SCALE),
            ],
            "flagpole": Flagpole(550*SCALE, HEIGHT - 180*SCALE),
            "start_pos": (50, HEIGHT - 60),
        },
        5: {
            "platforms": [
                Platform(0, HEIGHT - 20*SCALE, WIDTH, 20*SCALE, GREEN),
                Platform(50*SCALE, HEIGHT - 90*SCALE, 40*SCALE, 10*SCALE),
                Platform(120*SCALE, HEIGHT - 130*SCALE, 50*SCALE, 10*SCALE),
                Platform(200*SCALE, HEIGHT - 90*SCALE, 40*SCALE, 10*SCALE),
                Platform(270*SCALE, HEIGHT - 130*SCALE, 50*SCALE, 10*SCALE),
                Platform(350*SCALE, HEIGHT - 90*SCALE, 40*SCALE, 10*SCALE),
                Platform(430*SCALE, HEIGHT - 130*SCALE, 50*SCALE, 10*SCALE),
            ],
            "pipes": [
                Pipe(500*SCALE, HEIGHT - 90*SCALE, 90*SCALE),
            ],
            "enemies": [
                Goomba(80*SCALE, HEIGHT - 36*SCALE),
                Goomba(160*SCALE, HEIGHT - 36*SCALE),
                Goomba(240*SCALE, HEIGHT - 36*SCALE),
                Goomba(320*SCALE, HEIGHT - 36*SCALE),
                Goomba(400*SCALE, HEIGHT - 36*SCALE),
            ],
            "coins": [
                Coin(60*SCALE, HEIGHT - 110*SCALE),
                Coin(130*SCALE, HEIGHT - 150*SCALE),
                Coin(210*SCALE, HEIGHT - 110*SCALE),
                Coin(280*SCALE, HEIGHT - 150*SCALE),
                Coin(360*SCALE, HEIGHT - 110*SCALE),
                Coin(440*SCALE, HEIGHT - 150*SCALE),
            ],
            "flagpole": Flagpole(550*SCALE, HEIGHT - 180*SCALE),
            "start_pos": (50, HEIGHT - 60),
        }
    }
}

# World map nodes for 5 levels
world_map = {
    1: {
        "pos": (300, 200),
        "levels": {
            1: (100, 180),
            2: (180, 150),
            3: (260, 180),
            4: (340, 150),
            5: (420, 180),
        }
    }
}

# Game objects
mario = None
platforms = []
pipes = []
goombas = []
coins = []
clouds = []
bushes = []
flagpole = None

# Reset level function
def reset_level():
    global mario, platforms, pipes, goombas, coins, clouds, bushes, flagpole, time_left
    
    level_data = levels[current_world][current_level]
    start_x, start_y = level_data["start_pos"]
    mario = Mario(start_x, start_y)
    platforms = level_data["platforms"]
    pipes = level_data["pipes"]
    goombas = level_data["enemies"].copy()
    coins = level_data["coins"].copy()
    flagpole = level_data["flagpole"]
    
    clouds = [
        Cloud(50*SCALE, 30*SCALE),
        Cloud(150*SCALE, 50*SCALE),
        Cloud(250*SCALE, 40*SCALE),
        Cloud(350*SCALE, 60*SCALE),
        Cloud(450*SCALE, 30*SCALE),
    ]
    bushes = [
        Bush(70*SCALE, HEIGHT - 30*SCALE),
        Bush(180*SCALE, HEIGHT - 30*SCALE),
        Bush(380*SCALE, HEIGHT - 30*SCALE),
    ]
    
    time_left = 300

# Draw NES-style background
def draw_background():
    SCREEN.fill(SKY_BLUE)
    
    for i in range(0, WIDTH, 50*SCALE):
        pygame.draw.arc(SCREEN, NES_DARK_BLUE, (i, HEIGHT - 100*SCALE, 100*SCALE, 50*SCALE), 3.14, 6.28, 3*SCALE)
    
    for cloud in clouds:
        cloud.draw(SCREEN)
    
    for bush in bushes:
        bush.draw(SCREEN)

# Draw title screen
def draw_title_screen():
    SCREEN.fill(SKY_BLUE)
    
    font_large = pygame.font.SysFont('Arial', 24*SCALE)
    font_small = pygame.font.SysFont('Arial', 12*SCALE)
    
    title_text = font_large.render("SUPER MARIO WORLD", True, RED)
    subtitle_text = font_small.render("Tech Demo - Press Q to Enter Level", True, WHITE)
    start_text = font_small.render("Press ENTER to Start", True, WHITE)
    
    SCREEN.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//3))
    SCREEN.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, HEIGHT//3 + 40))
    SCREEN.blit(start_text, (WIDTH//2 - start_text.get_width()//2, HEIGHT//2 + 50))
    
    mario_img = pygame.Surface((16*SCALE, 16*SCALE), pygame.SRCALPHA)
    pygame.draw.rect(mario_img, RED, (0, 0, 16*SCALE, 16*SCALE))
    pygame.draw.rect(mario_img, BLUE, (2*SCALE, 8*SCALE, 12*SCALE, 8*SCALE))
    SCREEN.blit(mario_img, (WIDTH//2 - 8*SCALE, HEIGHT//2))

# Draw world map
def draw_world_map():
    SCREEN.fill(SKY_BLUE)
    
    font = pygame.font.SysFont('Arial', 16*SCALE)
    world_text = font.render(f"WORLD {current_world}-{current_level}", True, WHITE)
    SCREEN.blit(world_text, (WIDTH//2 - world_text.get_width()//2, 20))
    
    instruction_text = font.render("Press Q to Enter Level", True, YELLOW)
    SCREEN.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, HEIGHT - 30))
    
    for world_id, world_data in world_map.items():
        x, y = world_data["pos"]
        color = GREEN if world_id in unlocked_worlds else GRAY
        pygame.draw.circle(SCREEN, color, (x, y), 20*SCALE)
        
        world_font = pygame.font.SysFont('Arial', 12*SCALE)
        world_num = world_font.render(str(world_id), True, WHITE)
        SCREEN.blit(world_num, (x - world_num.get_width()//2, y - world_num.get_height()//2))
        
        if world_id in unlocked_worlds:
            for level_id, level_pos in world_data["levels"].items():
                lx, ly = level_pos
                pygame.draw.circle(SCREEN, YELLOW, (lx, ly), 10*SCALE)
                
                level_font = pygame.font.SysFont('Arial', 8*SCALE)
                level_num = level_font.render(str(level_id), True, BLACK)
                SCREEN.blit(level_num, (lx - level_num.get_width()//2, ly - level_num.get_height()//2))
    
    current_x, current_y = world_map[current_world]["levels"][current_level]
    pygame.draw.rect(SCREEN, RED, (current_x - 8*SCALE, current_y - 8*SCALE, 16*SCALE, 16*SCALE))

# Draw level complete screen
def draw_level_complete():
    SCREEN.fill(BLACK)
    
    font_large = pygame.font.SysFont('Arial', 24*SCALE)
    font_small = pygame.font.SysFont('Arial', 16*SCALE)
    
    complete_text = font_large.render("LEVEL COMPLETE!", True, WHITE)
    world_text = font_small.render(f"World {current_world}-{current_level}", True, WHITE)
    next_text = font_small.render("Press ENTER to continue", True, WHITE)
    
    SCREEN.blit(complete_text, (WIDTH//2 - complete_text.get_width()//2, HEIGHT//3))
    SCREEN.blit(world_text, (WIDTH//2 - world_text.get_width()//2, HEIGHT//2))
    SCREEN.blit(next_text, (WIDTH//2 - next_text.get_width()//2, HEIGHT//2 + 50))

# Draw game over screen
def draw_game_over():
    SCREEN.fill(BLACK)
    
    font_large = pygame.font.SysFont('Arial', 24*SCALE)
    font_small = pygame.font.SysFont('Arial', 16*SCALE)
    
    over_text = font_large.render("GAME OVER", True, RED)
    retry_text = font_small.render("Press ENTER to retry", True, WHITE)
    
    SCREEN.blit(over_text, (WIDTH//2 - over_text.get_width()//2, HEIGHT//3))
    SCREEN.blit(retry_text, (WIDTH//2 - retry_text.get_width()//2, HEIGHT//2))

# Draw NES-style UI
def draw_ui():
    pygame.draw.rect(SCREEN, BLACK, (0, 0, WIDTH, 16*SCALE))
    font = pygame.font.SysFont('Arial', 8*SCALE)
    score_text = font.render(f"SCORE {score:06d}", True, WHITE)
    coin_text = font.render(f"COINx{coins:02d}", True, WHITE)
    world_text = font.render(f"WORLD {current_world}-{current_level}", True, WHITE)
    time_text = font.render(f"TIME {time_left:03d}", True, WHITE)
    lives_text = font.render(f"LIVES {lives:02d}", True, WHITE)
    
    SCREEN.blit(score_text, (10*SCALE, 4*SCALE))
    SCREEN.blit(coin_text, (100*SCALE, 4*SCALE))
    SCREEN.blit(world_text, (180*SCALE, 4*SCALE))
    SCREEN.blit(time_text, (300*SCALE, 4*SCALE))
    SCREEN.blit(lives_text, (400*SCALE, 4*SCALE))

# Handle level completion
def complete_level():
    global current_level, current_world, unlocked_worlds, game_state
    
    if current_level < len(levels[current_world]):
        current_level += 1
    else:
        current_level = 1
        current_world += 1
        if current_world not in unlocked_worlds and current_world <= len(levels):
            unlocked_worlds.append(current_world)
    
    if current_world > len(levels):
        current_world = 1
    
    game_state = WORLD_MAP

# Main game loop
async def main():
    global game_state, current_world, current_level, time_left, score, coins, lives
    
    clock = pygame.time.Clock()
    reset_level()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if game_state == TITLE_SCREEN:
                        game_state = WORLD_MAP
                    elif game_state == LEVEL_COMPLETE:
                        complete_level()
                        game_state = WORLD_MAP
                    elif game_state == GAME_OVER:
                        current_world = 1
                        current_level = 1
                        unlocked_worlds = [1]
                        score = 0
                        coins = 0
                        lives = 3
                        game_state = WORLD_MAP
                
                # World map navigation
                if game_state == WORLD_MAP:
                    if event.key == pygame.K_LEFT:
                        if current_level > 1:
                            current_level -= 1
                        elif current_world > 1:
                            current_world -= 1
                            current_level = len(levels[current_world])
                    elif event.key == pygame.K_RIGHT:
                        if current_level < len(levels[current_world]):
                            current_level += 1
                        elif current_world < len(levels):
                            current_world += 1
                            current_level = 1
                    # Press Q to enter level
                    elif event.key == pygame.K_q and current_world in unlocked_worlds:
                        reset_level()
                        game_state = LEVEL

        if game_state == TITLE_SCREEN:
            draw_title_screen()
        elif game_state == WORLD_MAP:
            draw_world_map()
        elif game_state == LEVEL:
            keys = pygame.key.get_pressed()
            mario.update(keys, platforms, pipes)
            
            for goomba in goombas[:]:
                if goomba.update(platforms, pipes):
                    goombas.remove(goomba)
            
            for coin in coins:
                coin.update()
            
            for cloud in clouds:
                cloud.update()
            
            flagpole.update(mario)
            
            for goomba in goombas[:]:
                if mario.rect.colliderect(goomba.rect):
                    if mario.vy > 0 and mario.rect.bottom <= goomba.rect.top + 8*SCALE:
                        score += goomba.crush()
                        mario.vy = -4
                    elif not mario.invincible:
                        mario.die()
            
            for coin in coins:
                if mario.rect.colliderect(coin.rect):
                    coin.collect()
            
            time_left -= 1/60
            if time_left <= 0:
                mario.die()
            
            draw_background()
            for platform in platforms:
                platform.draw(SCREEN)
            for pipe in pipes:
                pipe.draw(SCREEN)
            for goomba in goombas:
                goomba.draw(SCREEN)
            for coin in coins:
                coin.draw(SCREEN)
            flagpole.draw(SCREEN)
            mario.draw(SCREEN)
            draw_ui()
            
        elif game_state == LEVEL_COMPLETE:
            draw_level_complete()
        elif game_state == GAME_OVER:
            draw_game_over()
        
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)

# Run the game
if platform.system() == "Windows":
    asyncio.run(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
