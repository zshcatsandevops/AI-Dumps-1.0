import pygame
import random
import math
import time

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Enhanced Super Mario RPG - No Assets")
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
LIGHT_BLUE = (173, 216, 230)
DARK_GREEN = (0, 100, 0)
PINK = (255, 182, 193)

# Game States
STATE_OVERWORLD = "overworld"
STATE_BATTLE = "battle"
STATE_MENU = "menu"
STATE_DIALOGUE = "dialogue"
STATE_SHOP = "shop"
STATE_GAMEOVER = "gameover"
STATE_WIN = "win"

class Character:
    def __init__(self, name, color, hp, mp, attack, defense):
        self.name = name
        self.color = color
        self.hp = hp
        self.max_hp = hp
        self.mp = mp
        self.max_mp = mp
        self.attack = attack
        self.defense = defense
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.current_frame = 0  # For simple animation toggle

    def level_up(self):
        self.level += 1
        self.max_hp += 20
        self.hp = self.max_hp
        self.max_mp += 10
        self.mp = self.max_mp
        self.attack += 5
        self.defense += 3
        self.exp_to_next = self.level * 100

    def update_animation(self, moving):
        if moving:
            self.current_frame = (self.current_frame + 1) % 2  # Simple toggle for 'animation'

class Player(Character):
    def __init__(self):
        super().__init__("Mario", RED, 20, 20, 20, 0)
        self.x = 400
        self.y = 300
        self.width = 30
        self.height = 40
        self.speed = 4
        self.coins = 50
        self.inventory = ["Mushroom", "Fire Flower"]
        self.current_map = "bowsers_keep"
        self.star_pieces = 0

    def move(self, keys, obstacles):
        old_x, old_y = self.x, self.y
        if keys[pygame.K_LEFT]: self.x -= self.speed
        if keys[pygame.K_RIGHT]: self.x += self.speed
        if keys[pygame.K_UP]: self.y -= self.speed
        if keys[pygame.K_DOWN]: self.y += self.speed
        player_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        for obs in obstacles:
            if player_rect.colliderect(obs):
                self.x, self.y = old_x, old_y
                break
        self.x = max(0, min(self.x, WIDTH - self.width))
        self.y = max(0, min(self.y, HEIGHT - self.height))
        moving = self.x != old_x or self.y != old_y
        self.update_animation(moving)

    def draw(self, screen):
        # Simple vector draw for Mario
        pygame.draw.rect(screen, self.color, (self.x, self.y + 15, self.width, 25))  # Body
        pygame.draw.circle(screen, self.color, (self.x + 15, self.y + 10), 10)  # Head
        pygame.draw.arc(screen, RED, (self.x + 5, self.y, 20, 20), 0, math.pi, 5)  # Hat
        pygame.draw.rect(screen, BLACK, (self.x + 8, self.y + 12, 14, 2))  # Mustache
        if self.current_frame == 1:  # 'Animation' toggle: add arm
            pygame.draw.rect(screen, self.color, (self.x + 25, self.y + 20, 5, 10))

class Party:
    def __init__(self, player):
        self.members = [player]
        self.active = [player]

    def add_member(self, char):
        self.members.append(char)
        if len(self.active) < 3:
            self.active.append(char)

    def switch(self, index1, index2):
        self.active[index1], self.active[index2] = self.active[index2], self.active[index1]

class Enemy:
    def __init__(self, name, hp, attack, defense, exp, coins, color, x=0, y=0):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.exp = exp
        self.coins = coins
        self.color = color
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40

    def draw(self, screen, x, y):
        pygame.draw.rect(screen, self.color, (x, y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (x, y, self.width, self.height), 2)

class NPC:
    def __init__(self, x, y, color, dialogue, name="NPC", shop_items=None):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 40
        self.color = color
        self.dialogue = dialogue
        self.name = name
        self.shop_items = shop_items or []  # Default to empty list to avoid None errors
        
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2)

class Map:
    def __init__(self, name, bg_color, obstacles, npcs, warps, enemies):
        self.name = name
        self.bg_color = bg_color
        self.obstacles = obstacles
        self.npcs = npcs
        self.warps = warps
        self.enemies = enemies
        
    def draw(self, screen):
        screen.fill(self.bg_color)
        
        for obs in self.obstacles:
            if obs.width > 5 and obs.height > 5:
                pygame.draw.rect(screen, BROWN, obs)
            else:
                pygame.draw.rect(screen, DARK_GREEN, obs)
                
        for warp in self.warps:
            pygame.draw.rect(screen, BLUE, warp["rect"])
            pygame.draw.rect(screen, WHITE, warp["rect"], 2)
            
        for npc in self.npcs:
            npc.draw(screen)
            
        for enemy in self.enemies:
            pygame.draw.circle(screen, enemy.color, (enemy.x, enemy.y), 15)
            pygame.draw.circle(screen, BLACK, (enemy.x, enemy.y), 15, 2)

# Full maps definition (expanded from abbreviation to prevent KeyError)
maps = {
    "bowsers_keep": Map("Bowser's Keep", GRAY, [pygame.Rect(100, 100, 600, 50)], [NPC(400, 200, RED, ["Welcome back!"])], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "marios_pad", "spawn": (50, 300)}], [Enemy("Terrapin", 10, 1, 8, 0, 0, GREEN, 300, 250)]),
    "marios_pad": Map("Mario's Pad", LIGHT_BLUE, [], [NPC(250, 300, YELLOW, ["Home sweet home!"])], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "mushroom_way", "spawn": (50, 300)}], []),
    "mushroom_way": Map("Mushroom Way", GREEN, [pygame.Rect(150, 150, 80, 80)], [NPC(450, 350, GREEN, ["Watch for Goombas!"])], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "mushroom_kingdom", "spawn": (50, 300)}], [Enemy("Goomba", 16, 3, 3, 1, 0, BROWN, 300, 250), Enemy("Sky Troopa", 10, 4, 16, 1, 1, GREEN, 500, 400)]),
    "mushroom_kingdom": Map("Mushroom Kingdom", LIGHT_BLUE, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["Join Mallow!"])], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "bandits_way", "spawn": (50, 300)}], [Enemy("Shyster", 30, 20, 26, 3, 2, BLUE, 400, 300)]),
    "bandits_way": Map("Bandit's Way", BROWN, [pygame.Rect(200, 200, 100, 100)], [], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "kero_sewers", "spawn": (50, 300)}], [Enemy("K-9", 30, 13, 13, 2, 0, GRAY, 300, 250), Enemy("Frogog", 80, 15, 8, 3, 4, GREEN, 500, 400)]),
    "kero_sewers": Map("Kero Sewers", GRAY, [pygame.Rect(300, 300, 100, 100)], [], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "tadpole_pond", "spawn": (50, 300)}], [Enemy("Rat Funk", 32, 20, 14, 2, 6, BROWN, 400, 300), Enemy("Belome", 500, 30, 25, 40, 12, RED, 600, 400)]),
    "tadpole_pond": Map("Tadpole Pond", LIGHT_BLUE, [], [NPC(300, 300, BLUE, ["Welcome to Tadpole Pond!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "kero_sewers", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "rose_way", "spawn": (50, 300)}], []),
    "rose_way": Map("Rose Way", BLUE, [pygame.Rect(200, 150, 80, 80)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "tadpole_pond", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "rose_town", "spawn": (50, 300)}], [Enemy("Starslap", 62, 25, 24, 2, 2, PINK, 400, 300)]),
    "rose_town": Map("Rose Town", LIGHT_BLUE, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["The town is under attack!"])], [{"rect": pygame.Rect(750, 250, 50, 100), "destination": "forest_maze", "spawn": (50, 300)}], []),
    "forest_maze": Map("Forest Maze", DARK_GREEN, [pygame.Rect(150, 150, 80, 80), pygame.Rect(350, 200, 80, 80)], [NPC(400, 300, BROWN, ["Be careful in the maze!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "rose_town", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "pipe_vault", "spawn": (50, 300)}], [Enemy("Amanita", 52, 35, 30, 3, 0, YELLOW, 300, 250)]),
    "pipe_vault": Map("Pipe Vault", GRAY, [pygame.Rect(100, 100, 100, 100)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "forest_maze", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "yoster_isle", "spawn": (50, 300)}], [Enemy("Sparky", 120, 40, 12, 4, 1, RED, 400, 300)]),
    "yoster_isle": Map("Yo'ster Isle", GREEN, [], [NPC(300, 300, GREEN, ["Race with Yoshis!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "pipe_vault", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "moleville", "spawn": (50, 300)}], []),
    "moleville": Map("Moleville", BROWN, [pygame.Rect(200, 200, 100, 100)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "yoster_isle", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "booster_pass", "spawn": (50, 300)}], [Enemy("Cluster", 60, 50, 21, 8, 2, GRAY, 300, 250)]),
    "booster_pass": Map("Booster Pass", GREEN, [pygame.Rect(150, 150, 80, 80)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "moleville", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "booster_tower", "spawn": (50, 300)}], [Enemy("Lakitu", 124, 43, 35, 9, 2, YELLOW, 400, 300)]),
    "booster_tower": Map("Booster Tower", GRAY, [pygame.Rect(100, 100, 600, 50)], [NPC(400, 200, RED, ["Climb the tower!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "booster_pass", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "marrymore", "spawn": (50, 300)}], [Enemy("Spookum", 98, 50, 4, 6, 4, BLUE, 300, 250)]),
    "marrymore": Map("Marrymore", LIGHT_BLUE, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["Wedding in progress!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "booster_tower", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "star_hill", "spawn": (50, 300)}], []),
    "star_hill": Map("Star Hill", BLUE, [], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "marrymore", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "seaside_town", "spawn": (50, 300)}], []),
    "seaside_town": Map("Seaside Town", LIGHT_BLUE, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["Something's off..."])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "star_hill", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "sea", "spawn": (50, 300)}], []),
    "sea": Map("Sea", BLUE, [pygame.Rect(200, 150, 80, 80)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "seaside_town", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "sunken_ship", "spawn": (50, 300)}], [Enemy("Zeostar", 90, 75, 50, 12, 0, BLUE, 400, 300)]),
    "sunken_ship": Map("Sunken Ship", GRAY, [pygame.Rect(300, 300, 100, 100)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "sea", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "lands_end", "spawn": (50, 300)}], [Enemy("Dry Bones", 0, 57, 34, 12, 6, GRAY, 300, 250)]),
    "lands_end": Map("Land's End", BROWN, [pygame.Rect(150, 150, 80, 80)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "sunken_ship", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "monstro_town", "spawn": (50, 300)}], [Enemy("Stinger", 65, 78, 43, 13, 0, YELLOW, 400, 300)]),
    "monstro_town": Map("Monstro Town", GRAY, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["Rest here!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "lands_end", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "bean_valley", "spawn": (50, 300)}], []),
    "bean_valley": Map("Bean Valley", GREEN, [pygame.Rect(200, 200, 100, 100)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "monstro_town", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "nimbus_land", "spawn": (50, 300)}], [Enemy("Chomp Chomp", 100, 92, 65, 14, 3, BROWN, 300, 250)]),
    "nimbus_land": Map("Nimbus Land", LIGHT_BLUE, [pygame.Rect(100, 100, 100, 100)], [NPC(250, 300, YELLOW, ["Cloud kingdom!"])], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "bean_valley", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "barrel_volcano", "spawn": (50, 300)}], [Enemy("Heavy Troopa", 250, 80, 50, 25, 8, GREEN, 400, 300)]),
    "barrel_volcano": Map("Barrel Volcano", RED, [pygame.Rect(150, 150, 80, 80)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "nimbus_land", "spawn": (700, 300)}, {"rect": pygame.Rect(750, 250, 50, 100), "destination": "bowsers_keep", "spawn": (50, 300)}], [Enemy("Corkpedite", 200, 80, 60, 20, 6, BROWN, 300, 250)]),
    "factory": Map("Factory", GRAY, [pygame.Rect(100, 100, 600, 50)], [], [{"rect": pygame.Rect(0, 250, 50, 100), "destination": "bowsers_keep", "spawn": (700, 300)}], [Enemy("Smithy", 2000, 50, 40, 1000, 0, BLACK, 400, 300)]),
}

class Game:
    def __init__(self):
        self.player = Player()
        self.party = Party(self.player)
        self.state = STATE_OVERWORLD
        self.current_map = maps[self.player.current_map]
        self.battle_enemy = None
        self.battle_substate = None
        self.timed_hit_start = 0
        self.timed_hit = False
        self.menu_selection = 0
        self.dialogue_text = []
        self.dialogue_index = 0
        self.current_npc = None
        self.shop_selection = 0
        self.message = ""
        self.message_timer = 0
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.bosses = ["Mack", "Croco", "Belome", "Bowyer", "Punchinello", "Bundt", "Johnny", "Speardovich", "Megasmilax", "Valentina", "Czar Dragon", "Axem Rangers", "Smithy"]
        
    def recruit_members(self):
        if self.player.current_map == "mushroom_kingdom" and len(self.party.members) == 1:
            self.party.add_member(Character("Mallow", BLUE, 20, 15, 22, 0))
        if self.player.current_map == "forest_maze" and len(self.party.members) == 2:
            self.party.add_member(Character("Geno", YELLOW, 45, 25, 60, 40))
        if self.player.current_map == "booster_tower" and len(self.party.members) == 3:
            self.party.add_member(Character("Bowser", GREEN, 80, 8, 85, 60))
        if self.player.current_map == "marrymore" and len(self.party.members) == 4:
            self.party.add_member(Character("Peach", PINK, 50, 40, 40, 24))
        
    def handle_overworld(self, keys):
        self.player.move(keys, self.current_map.obstacles)
        self.recruit_members()
        
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)
        
        # NPC interaction
        for npc in self.current_map.npcs:
            npc_rect = pygame.Rect(npc.x - 10, npc.y - 10, npc.width + 20, npc.height + 20)
            if player_rect.colliderect(npc_rect) and keys[pygame.K_SPACE]:
                self.current_npc = npc
                if npc.shop_items:
                    self.state = STATE_SHOP
                    self.shop_selection = 0
                else:
                    self.dialogue_text = npc.dialogue
                    self.dialogue_index = 0
                    self.state = STATE_DIALOGUE
        
        # Warp zones
        for warp in self.current_map.warps:
            if player_rect.colliderect(warp["rect"]):
                self.player.current_map = warp["destination"]
                self.current_map = maps[self.player.current_map]
                self.player.x, self.player.y = warp["spawn"]
        
        # Enemy encounters
        for enemy in self.current_map.enemies[:]:
            enemy_rect = pygame.Rect(enemy.x - 20, enemy.y - 20, 40, 40)
            if player_rect.colliderect(enemy_rect):
                self.battle_enemy = enemy
                self.state = STATE_BATTLE
                self.current_map.enemies.remove(enemy)
                break
        
        # Open menu
        if keys[pygame.K_m]:
            self.state = STATE_MENU
            self.menu_selection = 0
            
    def handle_battle(self, event):
        if self.battle_substate == "timed_hit":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if time.time() - self.timed_hit_start < 1:
                    self.timed_hit = True
            return
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:  # Attack with first party member
                self.message = "Press SPACE for timed hit!"
                self.message_timer = 60
                self.timed_hit_start = time.time()
                self.battle_substate = "timed_hit"
                # Damage calculated after timed hit in main loop
                
            elif event.key == pygame.K_2:  # Item (simple, use first item)
                if self.player.inventory:
                    item = self.player.inventory[0]
                    if item == "Mushroom":
                        self.party.active[0].hp = min(self.party.active[0].hp + 30, self.party.active[0].max_hp)
                        self.player.inventory.remove(item)
                        self.message = "Used Mushroom! Restored 30 HP!"
                    # Add more item effects
                    self.message_timer = 60
                    self.enemy_turn()
                    
            elif event.key == pygame.K_3:  # Run
                if random.random() > 0.3:
                    self.state = STATE_OVERWORLD
                    self.battle_enemy = None
                    self.message = "Escaped!"
                else:
                    self.message = "Can't escape!"
                self.message_timer = 60
                
    def enemy_turn(self):
        if self.battle_enemy.hp > 0:
            target = random.choice(self.party.active)
            damage = max(1, self.battle_enemy.attack - target.defense)
            target.hp -= damage
            self.message = f"{self.battle_enemy.name} attacks {target.name} for {damage} damage!"
            self.message_timer = 60
            if all(char.hp <= 0 for char in self.party.active):
                self.state = STATE_GAMEOVER
                
    def check_victory(self):
        if self.battle_enemy.hp <= 0:
            for char in self.party.members:
                char.exp += self.battle_enemy.exp
                if char.exp >= char.exp_to_next:
                    char.exp -= char.exp_to_next
                    char.level_up()
            self.player.coins += self.battle_enemy.coins
            self.message = f"Victory! Gained {self.battle_enemy.exp} EXP and {self.battle_enemy.coins} coins!"
            self.message_timer = 120
            if self.battle_enemy.name in self.bosses:
                self.player.star_pieces += 1
                if self.player.star_pieces >= 7:
                    self.state = STATE_WIN
            self.battle_enemy = None
            self.state = STATE_OVERWORLD
            
    def handle_menu(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = STATE_OVERWORLD
                
    def handle_dialogue(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.dialogue_index += 1
                if self.dialogue_index >= len(self.dialogue_text):
                    self.state = STATE_OVERWORLD
                    
    def handle_shop(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = STATE_OVERWORLD
            elif event.key == pygame.K_UP:
                self.shop_selection = max(0, self.shop_selection - 1)
            elif event.key == pygame.K_DOWN:
                self.shop_selection = min(len(self.current_npc.shop_items) - 1, self.shop_selection + 1)
            elif event.key == pygame.K_RETURN:
                item, price = self.current_npc.shop_items[self.shop_selection]
                if self.player.coins >= price:
                    self.player.coins -= price
                    self.player.inventory.append(item)
                    self.message = f"Bought {item}!"
                else:
                    self.message = "Not enough coins!"
                self.message_timer = 60
                
    def draw_overworld(self, screen):
        self.current_map.draw(screen)
        self.player.draw(screen)
        
        # Draw HUD
        pygame.draw.rect(screen, BLACK, (10, 10, 200, 80))
        pygame.draw.rect(screen, WHITE, (10, 10, 200, 80), 2)
        hp_text = self.small_font.render(f"HP: {self.player.hp}/{self.player.max_hp}", True, WHITE)
        screen.blit(hp_text, (20, 20))
        
    def draw_battle(self, screen):
        screen.fill(BLACK)
        
        # Draw enemy
        self.battle_enemy.draw(screen, WIDTH // 2 - 20, 100)
        
        # Draw party
        for i, char in enumerate(self.party.active):
            pygame.draw.rect(screen, char.color, (50 + i * 100, 400, 30, 40))
        
        # Draw message
        if self.message_timer > 0:
            msg = self.small_font.render(self.message, True, YELLOW)
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 300))
            self.message_timer -= 1
            
    def draw_menu(self, screen):
        screen.fill(BLACK)
        # Simple menu for now
        text = self.font.render("Menu", True, WHITE)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
        
    def draw_dialogue(self, screen):
        self.draw_overworld(screen)
        # Dialogue box
        pygame.draw.rect(screen, BLACK, (50, 400, WIDTH - 100, 150))
        if self.dialogue_index < len(self.dialogue_text):
            text = self.small_font.render(self.dialogue_text[self.dialogue_index], True, WHITE)
            screen.blit(text, (70, 420))
            
    def draw_shop(self, screen):
        screen.fill(BLACK)
        # Simple shop for now
        text = self.font.render("Shop", True, WHITE)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
        
    def draw_gameover(self, screen):
        screen.fill(BLACK)
        text = self.font.render("GAME OVER", True, RED)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
        
    def draw_win(self, screen):
        screen.fill(BLACK)
        text = self.font.render("YOU WIN!", True, YELLOW)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2))
        
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in [STATE_GAMEOVER, STATE_WIN]:
                            running = False
                    if self.state == STATE_BATTLE:
                        self.handle_battle(event)
                    elif self.state == STATE_MENU:
                        self.handle_menu(event)
                    elif self.state == STATE_DIALOGUE:
                        self.handle_dialogue(event)
                    elif self.state == STATE_SHOP:
                        self.handle_shop(event)
            
            keys = pygame.key.get_pressed()
            
            if self.state == STATE_OVERWORLD:
                self.handle_overworld(keys)
            
            if self.state == STATE_BATTLE and self.battle_substate == "timed_hit":
                if time.time() - self.timed_hit_start >= 1:
                    damage = max(1, self.party.active[0].attack - self.battle_enemy.defense)
                    if self.timed_hit:
                        damage = int(damage * 1.2)
                        self.message = "Timed hit! Extra damage!"
                    else:
                        self.message = f"Attack deals {damage} damage!"
                    self.battle_enemy.hp -= damage
                    self.timed_hit = False
                    self.battle_substate = None
                    self.check_victory()
                    if self.battle_enemy and self.battle_enemy.hp > 0:
                        self.enemy_turn()
            
            # Draw
            if self.state == STATE_OVERWORLD:
                self.draw_overworld(screen)
            elif self.state == STATE_BATTLE:
                self.draw_battle(screen)
            elif self.state == STATE_MENU:
                self.draw_menu(screen)
            elif self.state == STATE_DIALOGUE:
                self.draw_dialogue(screen)
            elif self.state == STATE_SHOP:
                self.draw_shop(screen)
            elif self.state == STATE_GAMEOVER:
                self.draw_gameover(screen)
            elif self.state == STATE_WIN:
                self.draw_win(screen)
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
