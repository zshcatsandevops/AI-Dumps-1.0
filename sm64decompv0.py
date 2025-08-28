import pygame
import sys
import math
import numpy as np
import threading
import random

# Initialize Pygame
pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except pygame.error:
    print("Mixer init failed, using defaults for sound generation")

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
MAX_FALL_SPEED = 10
JUMP_SPEED = -12
YOSHI_SPEED = 3
TILE_SIZE = 32

# Colors
SKY_BLUE = (135, 206, 235)
GROUND_BROWN = (139, 69, 19)
YOSHI_GREEN = (0, 255, 0)
YOSHI_RED = (255, 0, 0)
YOSHI_WHITE = (255, 255, 255)
ENEMY_RED = (255, 0, 0)
EGG_YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BRICK_ORANGE = (189, 94, 0)
QUESTION_YELLOW = (255, 215, 0)
PIPE_GREEN = (0, 128, 0)

# Note frequencies
note_freq = {
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23, 'G4': 392.00, 
    'A4': 440.00, 'B4': 493.88, 'Bb4': 466.16, 'C5': 523.25, 'D5': 587.33, 
    'E5': 659.25, 'F5': 698.46, 'G5': 784.00, 'A5': 880.00, 'B5': 987.77, 
    'Bb5': 932.33, 'C6': 1046.50, 'G#4': 415.30, 'F#5': 739.99, 
    'F#4': 369.99, 'D#5': 622.25, 'rest': 0
}

# SMB theme notes
smb_theme_notes = [
    'E5', 'E5', 'rest', 'E5', 'rest', 'C5', 'E5', 'rest', 'G5', 'rest', 'rest', 'rest', 
    'G4', 'rest', 'rest', 'rest', 'C5', 'rest', 'rest', 'G4', 'rest', 'rest', 'E4', 
    'rest', 'rest', 'rest', 'A4', 'rest', 'B4', 'rest', 'Bb4', 'A4', 'rest'
]

def generate_sound(frequency, duration, sample_rate=22050, amplitude=0.3):
    """Generate a sine wave sound for the given frequency and duration"""
    if frequency == 0:
        return None
    
    frames = int(duration * sample_rate)
    arr = np.zeros(frames)
    
    for i in range(frames):
        time = float(i) / sample_rate
        arr[i] = amplitude * np.sin(2 * np.pi * frequency * time)
    
    # Add envelope to prevent clicking
    fade_frames = min(frames // 10, 100)
    for i in range(fade_frames):
        arr[i] *= i / fade_frames
        arr[frames - 1 - i] *= i / fade_frames
    
    arr = (arr * 32767).astype(np.int16)
    stereo_arr = np.zeros((frames, 2), dtype=np.int16)
    stereo_arr[:, 0] = arr
    stereo_arr[:, 1] = arr
    
    return pygame.sndarray.make_sound(stereo_arr)

# Generate sounds
sounds = {}
for note, freq in note_freq.items():
    if note == 'rest':
        sounds[note] = None
    else:
        sounds[note] = generate_sound(freq, 0.1)

jump_sound = generate_sound(523, 0.1)  # C5
collect_sound = generate_sound(880, 0.1)  # A5
death_sound = generate_sound(220, 0.3)  # A3

class MusicPlayer:
    def __init__(self):
        self.playing = False
        self.thread = None
        self.current_note = 0
    
    def play_theme(self):
        if not self.playing:
            self.playing = True
            self.thread = threading.Thread(target=self._play_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        self.playing = False
    
    def _play_loop(self):
        channel = pygame.mixer.Channel(0)
        while self.playing:
            note = smb_theme_notes[self.current_note % len(smb_theme_notes)]
            if note == 'rest':
                pygame.time.wait(100)
            else:
                sound = sounds.get(note)
                if sound and self.playing:
                    channel.play(sound)
                    pygame.time.wait(100)
            self.current_note += 1

# Sprite data
yoshi_pixels = [
    [0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0],
    [0,0,0,0,0,0,1,1,1,1,1,1,1,1,0,0],
    [0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,0,0,1,1,1,2,2,3,1,1,1,1,0],
    [0,0,0,0,0,1,1,1,2,2,3,1,1,1,1,0],
    [0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [4,4,4,0,1,1,1,1,1,1,0,4,4,4,0,0],
    [4,4,4,0,1,1,1,1,1,1,0,4,4,4,0,0],
    [4,4,0,0,1,1,1,1,1,1,0,4,4,0,0,0]
]

sprite_colors = [
    (0, 0, 0, 0),  # 0: transparent
    YOSHI_GREEN,   # 1: green
    YOSHI_WHITE,   # 2: white
    BLACK,         # 3: black
    YOSHI_RED,     # 4: red
]

goomba_pixels = [
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [0,1,1,1,1,1,2,2,2,2,1,1,1,1,1,0],
    [0,1,1,1,1,2,2,3,3,2,2,1,1,1,1,0],
    [0,1,1,1,1,2,2,3,3,2,2,1,1,1,1,0],
    [0,1,1,1,1,2,2,2,2,2,2,1,1,1,1,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],
    [0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,0,1,1,0,0,0,0]
]

goomba_colors = [
    (0, 0, 0, 0),     # 0: transparent
    (139, 69, 19),    # 1: brown body
    YOSHI_WHITE,      # 2: white eyes
    BLACK,            # 3: black pupils
]

def create_sprite_surface(pixels, colors, scale=2):
    """Create a pygame surface from pixel data"""
    size = len(pixels)
    surface = pygame.Surface((size * scale, size * scale), pygame.SRCALPHA)
    
    for y, row in enumerate(pixels):
        for x, pixel in enumerate(row):
            if pixel > 0:
                color = colors[pixel]
                rect = pygame.Rect(x * scale, y * scale, scale, scale)
                surface.fill(color, rect)
    
    return surface

class GameObject:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
    
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def update(self, level):
        pass
    
    def draw(self, screen, camera_x):
        pass

class Yoshi(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, TILE_SIZE, TILE_SIZE)
        self.sprite = create_sprite_surface(yoshi_pixels, sprite_colors)
        self.facing_right = True
        self.alive = True
        self.invulnerable = 0
        
    def update(self, level):
        if not self.alive:
            return
            
        if self.invulnerable > 0:
            self.invulnerable -= 1
        
        # Handle input
        keys = pygame.key.get_pressed()
        
        # Horizontal movement
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -YOSHI_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = YOSHI_SPEED
            self.facing_right = True
        
        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = JUMP_SPEED
            if jump_sound:
                pygame.mixer.Channel(1).play(jump_sound)
        
        # Apply gravity
        if not self.on_ground:
            self.vel_y += GRAVITY
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED
        
        # Move horizontally
        self.x += self.vel_x
        self.check_horizontal_collisions(level)
        
        # Move vertically
        self.y += self.vel_y
        self.check_vertical_collisions(level)
        
        # Check if fell off screen
        if self.y > SCREEN_HEIGHT + 100:
            self.die()
    
    def check_horizontal_collisions(self, level):
        # Check world boundaries
        if self.x < 0:
            self.x = 0
            self.vel_x = 0
        
        # Check tile collisions
        for tile in level.tiles:
            if self.get_rect().colliderect(tile.get_rect()):
                if self.vel_x > 0:  # Moving right
                    self.x = tile.x - self.width
                elif self.vel_x < 0:  # Moving left
                    self.x = tile.x + tile.width
                self.vel_x = 0
    
    def check_vertical_collisions(self, level):
        self.on_ground = False
        
        for tile in level.tiles:
            if self.get_rect().colliderect(tile.get_rect()):
                if self.vel_y > 0:  # Falling down
                    self.y = tile.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:  # Jumping up
                    self.y = tile.y + tile.height
                    self.vel_y = 0
    
    def die(self):
        if self.alive:
            self.alive = False
            if death_sound:
                pygame.mixer.Channel(1).play(death_sound)
    
    def take_damage(self):
        if self.invulnerable == 0:
            self.invulnerable = 120  # 2 seconds at 60 FPS
            return True
        return False
    
    def draw(self, screen, camera_x):
        if not self.alive:
            return
            
        screen_x = self.x - camera_x
        if -self.width <= screen_x <= SCREEN_WIDTH:
            sprite = self.sprite
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            
            # Flash when invulnerable
            if self.invulnerable == 0 or (self.invulnerable // 5) % 2:
                screen.blit(sprite, (screen_x, self.y))

class Goomba(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, TILE_SIZE, TILE_SIZE)
        self.sprite = create_sprite_surface(goomba_pixels, goomba_colors)
        self.vel_x = -1  # Move left
        self.alive = True
        self.squashed = False
        self.squash_timer = 0
        
    def update(self, level):
        if not self.alive:
            return
            
        if self.squashed:
            self.squash_timer += 1
            if self.squash_timer > 30:  # Remove after half second
                self.alive = False
            return
        
        # Move horizontally
        self.x += self.vel_x
        
        # Check horizontal collisions with tiles
        for tile in level.tiles:
            if self.get_rect().colliderect(tile.get_rect()):
                self.vel_x = -self.vel_x  # Reverse direction
                if self.vel_x > 0:
                    self.x = tile.x + tile.width
                else:
                    self.x = tile.x - self.width
        
        # Apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL_SPEED:
            self.vel_y = MAX_FALL_SPEED
        
        # Move vertically
        self.y += self.vel_y
        
        # Check vertical collisions
        self.on_ground = False
        for tile in level.tiles:
            if self.get_rect().colliderect(tile.get_rect()):
                if self.vel_y > 0:  # Falling
                    self.y = tile.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
        
        # Remove if fell off screen
        if self.y > SCREEN_HEIGHT + 100:
            self.alive = False
    
    def squash(self):
        if not self.squashed:
            self.squashed = True
            self.vel_x = 0
            self.height = TILE_SIZE // 2
            if collect_sound:
                pygame.mixer.Channel(2).play(collect_sound)
    
    def draw(self, screen, camera_x):
        if not self.alive:
            return
            
        screen_x = self.x - camera_x
        if -self.width <= screen_x <= SCREEN_WIDTH:
            if self.squashed:
                # Draw squashed version
                rect = pygame.Rect(screen_x, self.y, self.width, self.height)
                pygame.draw.rect(screen, (139, 69, 19), rect)
            else:
                screen.blit(self.sprite, (screen_x, self.y))

class Tile(GameObject):
    def __init__(self, x, y, tile_type):
        super().__init__(x, y, TILE_SIZE, TILE_SIZE)
        self.tile_type = tile_type
        self.surface = self.create_tile_surface()
    
    def create_tile_surface(self):
        surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
        
        if self.tile_type == 'ground':
            surface.fill(GROUND_BROWN)
            # Add simple texture
            for i in range(0, TILE_SIZE, 4):
                pygame.draw.line(surface, (100, 50, 10), (i, 0), (i, TILE_SIZE))
                pygame.draw.line(surface, (100, 50, 10), (0, i), (TILE_SIZE, i))
        
        elif self.tile_type == 'brick':
            surface.fill(BRICK_ORANGE)
            # Draw brick pattern
            pygame.draw.rect(surface, BLACK, (0, 0, TILE_SIZE, TILE_SIZE), 2)
            pygame.draw.line(surface, BLACK, (TILE_SIZE//2, 0), (TILE_SIZE//2, TILE_SIZE//2))
            pygame.draw.line(surface, BLACK, (0, TILE_SIZE//2), (TILE_SIZE, TILE_SIZE//2))
            pygame.draw.line(surface, BLACK, (TILE_SIZE//4, TILE_SIZE//2), (TILE_SIZE//4, TILE_SIZE))
            pygame.draw.line(surface, BLACK, (3*TILE_SIZE//4, TILE_SIZE//2), (3*TILE_SIZE//4, TILE_SIZE))
        
        elif self.tile_type == 'question':
            surface.fill(QUESTION_YELLOW)
            pygame.draw.rect(surface, BLACK, (0, 0, TILE_SIZE, TILE_SIZE), 3)
            # Draw question mark
            font = pygame.font.Font(None, TILE_SIZE)
            text = font.render('?', True, BLACK)
            text_rect = text.get_rect(center=(TILE_SIZE//2, TILE_SIZE//2))
            surface.blit(text, text_rect)
        
        elif self.tile_type == 'pipe':
            surface.fill(PIPE_GREEN)
            pygame.draw.rect(surface, BLACK, (0, 0, TILE_SIZE, TILE_SIZE), 2)
        
        return surface
    
    def draw(self, screen, camera_x):
        screen_x = self.x - camera_x
        if -self.width <= screen_x <= SCREEN_WIDTH:
            screen.blit(self.surface, (screen_x, self.y))

class Level:
    def __init__(self):
        self.tiles = []
        self.enemies = []
        self.width = 0
        self.generate_level()
    
    def generate_level(self):
        # Create a simple level
        level_data = [
            # Ground level
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "                                                                ",
            "            BB    ??                BB    ??                   ",
            "                                                                ",
            "                     EB                                        ",
            "                  ############                                 ",
            "                  ############                                 ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",
        ]
        
        self.width = len(level_data[0]) * TILE_SIZE
        
        for y, row in enumerate(level_data):
            for x, char in enumerate(row):
                tile_x = x * TILE_SIZE
                tile_y = y * TILE_SIZE
                
                if char == 'G':
                    self.tiles.append(Tile(tile_x, tile_y, 'ground'))
                elif char == 'B':
                    self.tiles.append(Tile(tile_x, tile_y, 'brick'))
                elif char == '?':
                    self.tiles.append(Tile(tile_x, tile_y, 'question'))
                elif char == '#':
                    self.tiles.append(Tile(tile_x, tile_y, 'pipe'))
                elif char == 'E':
                    self.enemies.append(Goomba(tile_x, tile_y - TILE_SIZE))
    
    def update(self):
        # Update enemies
        for enemy in self.enemies[:]:  # Use slice to avoid modification during iteration
            enemy.update(self)
            if not enemy.alive:
                self.enemies.remove(enemy)
    
    def draw(self, screen, camera_x):
        # Draw tiles
        for tile in self.tiles:
            tile.draw(screen, camera_x)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(screen, camera_x)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Yoshi - 2025 PC Port")
        self.clock = pygame.time.Clock()
        self.camera_x = 0
        self.yoshi = Yoshi(100, 400)
        self.level = Level()
        self.music_player = MusicPlayer()
        self.score = 0
        self.lives = 3
        self.font = pygame.font.Font(None, 36)
        self.running = True
        self.game_state = "menu"  # "menu", "playing", "game_over"
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_state == "menu":
                    if event.key == pygame.K_SPACE:
                        self.start_game()
                elif self.game_state == "game_over":
                    if event.key == pygame.K_SPACE:
                        self.restart_game()
                elif event.key == pygame.K_ESCAPE:
                    self.game_state = "menu"
    
    def start_game(self):
        self.game_state = "playing"
        self.music_player.play_theme()
        self.yoshi = Yoshi(100, 400)
        self.level = Level()
        self.camera_x = 0
        self.score = 0
        self.lives = 3
    
    def restart_game(self):
        self.start_game()
    
    def update_camera(self):
        # Follow Yoshi with the camera
        target_x = self.yoshi.x - SCREEN_WIDTH // 3
        if target_x < 0:
            target_x = 0
        elif target_x > self.level.width - SCREEN_WIDTH:
            target_x = self.level.width - SCREEN_WIDTH
        
        self.camera_x = target_x
    
    def check_collisions(self):
        # Check Yoshi vs enemies
        yoshi_rect = self.yoshi.get_rect()
        
        for enemy in self.level.enemies[:]:
            if enemy.alive and not enemy.squashed:
                enemy_rect = enemy.get_rect()
                
                if yoshi_rect.colliderect(enemy_rect):
                    # Check if Yoshi is above the enemy (jumping on it)
                    if (self.yoshi.vel_y > 0 and 
                        self.yoshi.y + self.yoshi.height - 10 < enemy.y):
                        # Squash enemy
                        enemy.squash()
                        self.yoshi.vel_y = JUMP_SPEED // 2  # Small bounce
                        self.score += 100
                    else:
                        # Yoshi takes damage
                        if self.yoshi.take_damage():
                            self.lives -= 1
                            if self.lives <= 0:
                                self.game_over()
    
    def game_over(self):
        self.game_state = "game_over"
        self.music_player.stop()
        self.yoshi.die()
    
    def update(self):
        if self.game_state == "playing":
            self.yoshi.update(self.level)
            self.level.update()
            self.update_camera()
            self.check_collisions()
            
            # Check if Yoshi died
            if not self.yoshi.alive:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over()
                else:
                    # Respawn Yoshi
                    self.yoshi = Yoshi(100, 400)
    
    def draw_ui(self):
        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        # Draw lives
        lives_text = self.font.render(f"Lives: {self.lives}", True, WHITE)
        self.screen.blit(lives_text, (10, 50))
    
    def draw_menu(self):
        title_font = pygame.font.Font(None, 72)
        subtitle_font = pygame.font.Font(None, 36)
        
        title_text = title_font.render("SUPER YOSHI", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        
        subtitle_text = subtitle_font.render("2025 PC Port", True, WHITE)
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3 + 80))
        
        start_text = self.font.render("Press SPACE to Start", True, WHITE)
        start_rect = start_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        
        controls_text = self.font.render("Controls: Arrow Keys/WASD to move, SPACE to jump", True, WHITE)
        controls_rect = controls_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100))
        
        self.screen.blit(title_text, title_rect)
        self.screen.blit(subtitle_text, subtitle_rect)
        self.screen.blit(start_text, start_rect)
        self.screen.blit(controls_text, controls_rect)
    
    def draw_game_over(self):
        game_over_font = pygame.font.Font(None, 72)
        
        game_over_text = game_over_font.render("GAME OVER", True, WHITE)
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        
        final_score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
        final_score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        
        restart_text = self.font.render("Press SPACE to Restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
        
        self.screen.blit(game_over_text, game_over_rect)
        self.screen.blit(final_score_text, final_score_rect)
        self.screen.blit(restart_text, restart_rect)
    
    def draw(self):
        self.screen.fill(SKY_BLUE)
        
        if self.game_state == "menu":
            self.draw_menu()
        elif self.game_state == "playing":
            self.level.draw(self.screen, self.camera_x)
            self.yoshi.draw(self.screen, self.camera_x)
            self.draw_ui()
        elif self.game_state == "game_over":
            self.draw_game_over()
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        self.music_player.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
