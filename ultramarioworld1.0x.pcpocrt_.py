import pygame, sys, random, math
from enum import Enum

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Super Mario World - Complete Edition")
clock = pygame.time.Clock()
FPS = 60

# Colors
SKY = (135, 206, 250)
DARK_SKY = (100, 150, 200)
GROUND = (139, 69, 19)
GRASS = (34, 139, 34)
GREEN = (0, 200, 0)  # Added GREEN constant
PIPE_GREEN = (0, 150, 0)
BRICK = (160, 82, 45)
MARIO_RED = (220, 0, 0)
MARIO_BLUE = (0, 0, 220)
COIN_YELLOW = (255, 215, 0)
GOOMBA_BROWN = (150, 75, 0)
KOOPA_GREEN = (0, 100, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)

# Game States
class GameState(Enum):
    MENU = 1
    OVERWORLD = 2
    LEVEL = 3
    GAME_OVER = 4
    LEVEL_COMPLETE = 5

# Physics Constants
GRAVITY = 0.8
JUMP_STRENGTH = -15
RUN_SPEED = 5
WALK_SPEED = 3
MAX_FALL = 12
TILESIZE = 32

# Power-up States
class PowerState(Enum):
    SMALL = 1
    BIG = 2
    FIRE = 3

# Level Templates
LEVELS = {
    "1-1": {
        "name": "Yoshi's Island 1",
        "layout": [
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                             P                                  ",
            "                                            PPP                                 ",
            "                  ?                        PPPPP                                ",
            "                                          PPPPPPP                               ",
            "                ?   ?   ?                PPPPPPPPP            ??                ",
            "                                        PPPPPPPPPPP                             ",
            "              =========                PPPPPPPPPPPPP         ====               ",
            "                            g    o  o  PPPPPPPPPPPPPPP              g      F    ",
            "           m             ================================    ===================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
        ]
    },
    "1-2": {
        "name": "Yoshi's Island 2",
        "layout": [
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "       ?                                                                        ",
            "                   PP                                                           ",
            "      ???         PPPP         o o o                          ?   ?            ",
            "                 PPPPPP                                                         ",
            "     =====      PPPPPPPP      =========           ====                    F    ",
            "                PPPPPPPP                                      ====        ===   ",
            "             g  PPPPPPPP  k         g       o o o                 k            ",
            "=================================       ========================================",
            "=================================       ========================================",
            "=================================       ========================================",
            "================================================================================",
            "================================================================================",
        ]
    },
    "1-3": {
        "name": "Yoshi's Island 3",
        "layout": [
            "                                                                                ",
            "                                                                                ",
            "                     o                                o                        ",
            "                    ooo                              ooo                       ",
            "                   ooooo                            ooooo                      ",
            "                  ooooooo                          ooooooo                     ",
            "                                                                                ",
            "    ?   ?   ?                ====                           ?  ?  ?            ",
            "                                        ====                                   ",
            "                   ====                        ====                            ",
            "       ====                                            ====              F     ",
            "                        k              g                      ====       ===   ",
            "            g                   k            g       k               g         ",
            "================================================================================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
        ]
    },
    "2-1": {
        "name": "Donut Plains 1",
        "layout": [
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "                                                                                ",
            "          ===                                              ===                 ",
            "             ===                                        ===                    ",
            "                ===                                  ===                       ",
            "    ?              ===          PP               ===                           ",
            "                      ===      PPPP          ===          ?   ?   ?            ",
            "           o o o         === PPPPPPPP     ===                                  ",
            "                            PPPPPPPPPP ===                                F     ",
            "      ===========          PPPPPPPPPPPP            ===========          ====   ",
            "                    g      PPPPPPPPPPPPPP     k             g        k         ",
            "================================================================================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
            "================================================================================",
        ]
    }
}

class Camera:
    def __init__(self, width, height):
        self.rect = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
    
    def apply(self, entity):
        return entity.rect.move(-self.rect.x, -self.rect.y)
    
    def apply_rect(self, rect):
        return rect.move(-self.rect.x, -self.rect.y)
    
    def update(self, target, level_width):
        x = -target.rect.centerx + WIDTH // 2
        x = min(0, x)  # Don't scroll past the left
        x = max(-(level_width - WIDTH), x)  # Don't scroll past the right
        self.rect.x = x

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.power_state = PowerState.SMALL
        self.size = TILESIZE
        self.image = pygame.Surface((self.size, self.size))
        self.image.fill(MARIO_RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.running = False
        self.jump_held = False
        self.invincible = 0
        
    def update_image(self):
        height = TILESIZE * 2 if self.power_state != PowerState.SMALL else TILESIZE
        self.image = pygame.Surface((TILESIZE, height))
        color = MARIO_RED
        if self.power_state == PowerState.FIRE:
            color = WHITE
        self.image.fill(color)
        # Draw simple face
        pygame.draw.circle(self.image, BLACK, (8, 8), 2)
        pygame.draw.circle(self.image, BLACK, (24, 8), 2)
        
    def update(self, tiles, hazards):
        keys = pygame.key.get_pressed()
        
        # Horizontal movement
        self.running = keys[pygame.K_LSHIFT]
        max_speed = RUN_SPEED if self.running else WALK_SPEED
        
        if keys[pygame.K_LEFT]:
            self.vel_x = -max_speed
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            self.vel_x = max_speed
            self.facing_right = True
        else:
            self.vel_x *= 0.85  # Friction
            if abs(self.vel_x) < 0.1:
                self.vel_x = 0
        
        # Jumping
        if keys[pygame.K_SPACE]:
            if self.on_ground and not self.jump_held:
                self.vel_y = JUMP_STRENGTH
                self.jump_held = True
        else:
            self.jump_held = False
            if self.vel_y < 0:
                self.vel_y *= 0.5  # Variable jump height
        
        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL:
            self.vel_y = MAX_FALL
        
        # Move and check collisions
        dx, dy = self.vel_x, self.vel_y
        
        # Horizontal collision
        self.rect.x += dx
        for tile in tiles:
            if self.rect.colliderect(tile):
                if dx > 0:
                    self.rect.right = tile.left
                elif dx < 0:
                    self.rect.left = tile.right
                self.vel_x = 0
        
        # Vertical collision
        self.on_ground = False
        self.rect.y += dy
        for tile in tiles:
            if self.rect.colliderect(tile):
                if dy > 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = tile.bottom
                    self.vel_y = 0
        
        # Update invincibility
        if self.invincible > 0:
            self.invincible -= 1
        
        # Fall off map
        if self.rect.top > HEIGHT:
            return "dead"
        
        return None
    
    def power_up(self):
        if self.power_state == PowerState.SMALL:
            self.power_state = PowerState.BIG
            self.rect.y -= TILESIZE
        elif self.power_state == PowerState.BIG:
            self.power_state = PowerState.FIRE
        self.update_image()
    
    def take_damage(self):
        if self.invincible > 0:
            return False
        
        if self.power_state == PowerState.FIRE:
            self.power_state = PowerState.BIG
        elif self.power_state == PowerState.BIG:
            self.power_state = PowerState.SMALL
        else:
            return True  # Dead
        
        self.invincible = 120  # 2 seconds at 60 FPS
        self.update_image()
        return False

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type="goomba"):
        super().__init__()
        self.type = enemy_type
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        if enemy_type == "goomba":
            self.image.fill(GOOMBA_BROWN)
            self.speed = 1
        elif enemy_type == "koopa":
            self.image.fill(KOOPA_GREEN)
            self.speed = 2
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = self.speed
        self.vel_y = 0
        
    def update(self, tiles):
        # Gravity
        self.vel_y += GRAVITY
        if self.vel_y > MAX_FALL:
            self.vel_y = MAX_FALL
        
        # Move horizontally
        self.rect.x += self.vel_x
        for tile in tiles:
            if self.rect.colliderect(tile):
                self.vel_x *= -1
                break
        
        # Move vertically
        self.rect.y += self.vel_y
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vel_y > 0:
                    self.rect.bottom = tile.top
                    self.vel_y = 0

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(self.image, COIN_YELLOW, (10, 10), 10)
        pygame.draw.circle(self.image, YELLOW, (10, 10), 8)
        self.rect = self.image.get_rect(center=(x + TILESIZE//2, y + TILESIZE//2))
        self.bob = 0
        
    def update(self):
        self.bob += 0.1
        self.rect.y += math.sin(self.bob) * 0.5

class QuestionBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, contents="coin"):
        super().__init__()
        self.contents = contents
        self.used = False
        self.image = pygame.Surface((TILESIZE, TILESIZE))
        self.image.fill(YELLOW if not self.used else GROUND)
        self.rect = self.image.get_rect(topleft=(x, y))
        
    def hit(self):
        if not self.used:
            self.used = True
            self.image.fill(GROUND)
            return self.contents
        return None

class Level:
    def __init__(self, level_data):
        self.layout = level_data["layout"]
        self.name = level_data["name"]
        self.tiles = []
        self.enemies = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.question_blocks = pygame.sprite.Group()
        self.flag_pos = None
        self.spawn = (100, HEIGHT - 200)
        self.width = len(self.layout[0]) * TILESIZE
        
        self.build_level()
    
    def build_level(self):
        for y, row in enumerate(self.layout):
            for x, char in enumerate(row):
                pos_x = x * TILESIZE
                pos_y = y * TILESIZE
                
                if char == '=':
                    self.tiles.append(pygame.Rect(pos_x, pos_y, TILESIZE, TILESIZE))
                elif char == 'P':
                    self.tiles.append(pygame.Rect(pos_x, pos_y, TILESIZE, TILESIZE))
                elif char == 'g':
                    self.enemies.add(Enemy(pos_x, pos_y, "goomba"))
                elif char == 'k':
                    self.enemies.add(Enemy(pos_x, pos_y, "koopa"))
                elif char == 'o':
                    self.coins.add(Coin(pos_x, pos_y))
                elif char == '?':
                    block = QuestionBlock(pos_x, pos_y, "mushroom" if random.random() > 0.5 else "coin")
                    self.question_blocks.add(block)
                    self.tiles.append(block.rect)
                elif char == 'F':
                    self.flag_pos = (pos_x, pos_y)
                elif char == 'm':
                    self.spawn = (pos_x, pos_y)
    
    def draw(self, screen, camera):
        # Draw tiles
        for tile in self.tiles:
            draw_rect = camera.apply_rect(tile)
            if draw_rect.colliderect(screen.get_rect()):
                # Check if it's a question block
                is_question = False
                for qblock in self.question_blocks:
                    if qblock.rect == tile:
                        is_question = True
                        color = YELLOW if not qblock.used else GROUND
                        break
                
                if not is_question:
                    # Check if it's a pipe
                    if any(t.y < tile.y and t.x == tile.x for t in self.tiles):
                        color = PIPE_GREEN
                    else:
                        color = GROUND
                        # Draw grass on top
                        pygame.draw.rect(screen, color, draw_rect)
                        pygame.draw.rect(screen, GRASS, (draw_rect.x, draw_rect.y, TILESIZE, 6))
                        continue
                
                pygame.draw.rect(screen, color, draw_rect)
        
        # Draw flag
        if self.flag_pos:
            flag_rect = camera.apply_rect(pygame.Rect(self.flag_pos[0], self.flag_pos[1], 10, 200))
            pygame.draw.rect(screen, WHITE, flag_rect)
            pygame.draw.polygon(screen, MARIO_RED, [
                (flag_rect.x + 10, flag_rect.y),
                (flag_rect.x + 60, flag_rect.y + 30),
                (flag_rect.x + 10, flag_rect.y + 60)
            ])

class Overworld:
    def __init__(self):
        self.levels = [
            {"pos": (200, 300), "id": "1-1", "unlocked": True},
            {"pos": (300, 300), "id": "1-2", "unlocked": False},
            {"pos": (400, 250), "id": "1-3", "unlocked": False},
            {"pos": (500, 300), "id": "2-1", "unlocked": False},
        ]
        self.current_level = 0
        self.player_pos = list(self.levels[0]["pos"])
        
    def draw(self, screen):
        screen.fill(DARK_SKY)
        
        # Draw paths
        for i in range(len(self.levels) - 1):
            if self.levels[i]["unlocked"]:
                start = self.levels[i]["pos"]
                end = self.levels[i + 1]["pos"]
                pygame.draw.line(screen, WHITE, start, end, 5)
        
        # Draw level nodes
        for i, level in enumerate(self.levels):
            color = GREEN if level["unlocked"] else GROUND
            pygame.draw.circle(screen, color, level["pos"], 20)
            pygame.draw.circle(screen, WHITE, level["pos"], 20, 3)
            
            # Draw level number
            font = pygame.font.SysFont("Arial", 14, bold=True)
            text = font.render(level["id"], True, WHITE)
            screen.blit(text, (level["pos"][0] - 15, level["pos"][1] - 8))
        
        # Draw Mario
        mario_rect = pygame.Rect(self.player_pos[0] - 10, self.player_pos[1] - 30, 20, 20)
        pygame.draw.rect(screen, MARIO_RED, mario_rect)
        
        # Instructions
        font = pygame.font.SysFont("Arial", 20)
        text = font.render("Arrow Keys: Move | Enter: Select Level | ESC: Menu", True, WHITE)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 50))
    
    def update(self):
        keys = pygame.key.get_pressed()
        target_pos = list(self.levels[self.current_level]["pos"])
        
        # Smooth movement
        self.player_pos[0] += (target_pos[0] - self.player_pos[0]) * 0.1
        self.player_pos[1] += (target_pos[1] - self.player_pos[1]) * 0.1
        
        return self.current_level
    
    def move(self, direction):
        if direction == "right" and self.current_level < len(self.levels) - 1:
            if self.levels[self.current_level + 1]["unlocked"]:
                self.current_level += 1
        elif direction == "left" and self.current_level > 0:
            self.current_level -= 1
    
    def unlock_next(self):
        if self.current_level < len(self.levels) - 1:
            self.levels[self.current_level + 1]["unlocked"] = True

class Game:
    def __init__(self):
        self.state = GameState.MENU
        self.overworld = Overworld()
        self.current_level = None
        self.player = None
        self.camera = Camera(WIDTH, HEIGHT)
        self.score = 0
        self.lives = 3
        self.coins_collected = 0
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)
        
    def start_level(self, level_id):
        self.current_level = Level(LEVELS[level_id])
        self.player = Player(*self.current_level.spawn)
        self.state = GameState.LEVEL
        
    def draw_hud(self, screen):
        # Score
        score_text = self.font.render(f"SCORE: {self.score:06d}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        # Coins
        coin_text = self.font.render(f"COINS: {self.coins_collected:02d}", True, COIN_YELLOW)
        screen.blit(coin_text, (WIDTH//2 - 50, 10))
        
        # Lives
        lives_text = self.font.render(f"LIVES: {self.lives}", True, WHITE)
        screen.blit(lives_text, (WIDTH - 120, 10))
        
        # FPS
        fps = int(clock.get_fps())
        fps_color = GREEN if fps >= 58 else YELLOW if fps >= 50 else MARIO_RED
        fps_text = self.font.render(f"FPS: {fps}", True, fps_color)
        screen.blit(fps_text, (WIDTH - 100, HEIGHT - 30))
    
    def run(self):
        running = True
        
        while running:
            dt = clock.tick(FPS) / 1000.0
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.state == GameState.MENU:
                        if event.key == pygame.K_RETURN:
                            self.state = GameState.OVERWORLD
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                    elif self.state == GameState.OVERWORLD:
                        if event.key == pygame.K_RETURN:
                            level_id = self.overworld.levels[self.overworld.current_level]["id"]
                            if self.overworld.levels[self.overworld.current_level]["unlocked"]:
                                self.start_level(level_id)
                        elif event.key == pygame.K_LEFT:
                            self.overworld.move("left")
                        elif event.key == pygame.K_RIGHT:
                            self.overworld.move("right")
                        elif event.key == pygame.K_ESCAPE:
                            self.state = GameState.MENU
                    elif self.state == GameState.LEVEL:
                        if event.key == pygame.K_ESCAPE:
                            self.state = GameState.OVERWORLD
                    elif self.state == GameState.LEVEL_COMPLETE:
                        if event.key == pygame.K_RETURN:
                            self.overworld.unlock_next()
                            self.state = GameState.OVERWORLD
                    elif self.state == GameState.GAME_OVER:
                        if event.key == pygame.K_RETURN:
                            self.__init__()
            
            # Update game state
            if self.state == GameState.MENU:
                screen.fill(DARK_SKY)
                title = self.big_font.render("SUPER MARIO WORLD", True, WHITE)
                screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
                
                subtitle = self.font.render("Complete Edition", True, COIN_YELLOW)
                screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 60))
                
                start = self.font.render("Press ENTER to Start", True, WHITE)
                screen.blit(start, (WIDTH//2 - start.get_width()//2, HEIGHT//2 + 50))
                
                controls = self.font.render("Arrow Keys: Move | Space: Jump | Shift: Run", True, WHITE)
                screen.blit(controls, (WIDTH//2 - controls.get_width()//2, HEIGHT - 100))
                
            elif self.state == GameState.OVERWORLD:
                self.overworld.update()
                self.overworld.draw(screen)
                
            elif self.state == GameState.LEVEL:
                # Update player
                result = self.player.update(self.current_level.tiles, self.current_level.enemies)
                
                if result == "dead":
                    self.lives -= 1
                    if self.lives <= 0:
                        self.state = GameState.GAME_OVER
                    else:
                        # Respawn
                        self.player = Player(*self.current_level.spawn)
                
                # Update camera
                self.camera.update(self.player, self.current_level.width)
                
                # Check enemy collisions
                for enemy in self.current_level.enemies:
                    enemy.update(self.current_level.tiles)
                    if self.player.rect.colliderect(enemy.rect):
                        if self.player.vel_y > 0 and self.player.rect.bottom < enemy.rect.centery:
                            # Stomp enemy
                            enemy.kill()
                            self.score += 100
                            self.player.vel_y = JUMP_STRENGTH // 2
                        else:
                            # Take damage
                            if self.player.take_damage():
                                self.lives -= 1
                                if self.lives <= 0:
                                    self.state = GameState.GAME_OVER
                                else:
                                    self.player = Player(*self.current_level.spawn)
                
                # Check coin collection
                for coin in self.current_level.coins:
                    coin.update()
                    if self.player.rect.colliderect(coin.rect):
                        coin.kill()
                        self.coins_collected += 1
                        self.score += 50
                        if self.coins_collected >= 100:
                            self.coins_collected = 0
                            self.lives += 1
                
                # Check question blocks
                for block in self.current_level.question_blocks:
                    if self.player.rect.colliderect(block.rect) and self.player.vel_y < 0:
                        contents = block.hit()
                        if contents == "coin":
                            self.coins_collected += 1
                            self.score += 50
                        elif contents == "mushroom":
                            self.player.power_up()
                            self.score += 1000
                
                # Check flag (level complete)
                if self.current_level.flag_pos:
                    flag_rect = pygame.Rect(self.current_level.flag_pos[0], 
                                           self.current_level.flag_pos[1],
                                           20, 200)
                    if self.player.rect.colliderect(flag_rect):
                        self.state = GameState.LEVEL_COMPLETE
                        self.score += 5000
                
                # Draw everything
                screen.fill(SKY)
                
                # Draw level
                self.current_level.draw(screen, self.camera)
                
                # Draw coins
                for coin in self.current_level.coins:
                    screen.blit(coin.image, self.camera.apply(coin))
                
                # Draw enemies
                for enemy in self.current_level.enemies:
                    screen.blit(enemy.image, self.camera.apply(enemy))
                
                # Draw player (with invincibility flashing)
                if self.player.invincible == 0 or self.player.invincible % 4 < 2:
                    player_rect = self.camera.apply(self.player)
                    screen.blit(self.player.image, player_rect)
                
                # Draw HUD
                self.draw_hud(screen)
                
                # Draw level name
                if pygame.time.get_ticks() < 3000:  # Show for 3 seconds
                    level_name = self.big_font.render(self.current_level.name, True, WHITE)
                    screen.blit(level_name, (WIDTH//2 - level_name.get_width()//2, HEIGHT//3))
                
            elif self.state == GameState.LEVEL_COMPLETE:
                screen.fill(DARK_SKY)
                complete = self.big_font.render("LEVEL COMPLETE!", True, COIN_YELLOW)
                screen.blit(complete, (WIDTH//2 - complete.get_width()//2, HEIGHT//3))
                
                bonus = self.font.render(f"Bonus: 5000 points", True, WHITE)
                screen.blit(bonus, (WIDTH//2 - bonus.get_width()//2, HEIGHT//2))
                
                continue_text = self.font.render("Press ENTER to Continue", True, WHITE)
                screen.blit(continue_text, (WIDTH//2 - continue_text.get_width()//2, HEIGHT//2 + 50))
                
            elif self.state == GameState.GAME_OVER:
                screen.fill(BLACK)
                game_over = self.big_font.render("GAME OVER", True, MARIO_RED)
                screen.blit(game_over, (WIDTH//2 - game_over.get_width()//2, HEIGHT//3))
                
                final_score = self.font.render(f"Final Score: {self.score}", True, WHITE)
                screen.blit(final_score, (WIDTH//2 - final_score.get_width()//2, HEIGHT//2))
                
                restart = self.font.render("Press ENTER to Restart", True, WHITE)
                screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 50))
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()
