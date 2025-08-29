from ursina import *
import random
import math

app = Ursina()

# Define clamp function
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

# === PLAYER CLASS ===
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='cube', scale=(1, 2, 1), color=color.rgb(255, 0, 0), collider='box', **kwargs)
        self.speed = 8
        self.jump_strength = 12
        self.gravity = 25
        self.velocity_y = 0
        self.grounded = False

    def update(self):
        # Gravity and vertical movement
        self.velocity_y -= self.gravity * time.dt
        self.y += self.velocity_y * time.dt

        # Ground check
        ray = raycast(self.position, direction=(0, -1, 0), distance=1.1, ignore=[self])
        if ray.hit:
            self.y = ray.world_point.y + 1
            self.velocity_y = 0
            self.grounded = True
        else:
            self.grounded = False

        # Horizontal movement
        direction = Vec3(
            held_keys['d'] - held_keys['a'] + held_keys['right arrow'] - held_keys['left arrow'],
            0,
            held_keys['w'] - held_keys['s'] + held_keys['up arrow'] - held_keys['down arrow']
        ).normalized() * self.speed
        self.position += direction * time.dt

        # Keep player within bounds
        self.x = clamp(self.x, -70, 70)
        self.z = clamp(self.z, -70, 70)
        
        # Prevent falling below ground
        if self.y < -10:
            self.position = Vec3(0, 2, -20)  # Reset position

    def input(self, key):
        if key == 'space' and self.grounded:
            self.velocity_y = self.jump_strength

# === GAME SETUP ===

# Camera setup
camera.fov = 90
camera.position = (10, 10, -25)
camera.rotation = (20, -30, 0)
camera.smoothness = 5

# Sky background
Sky(color=color.rgb(135, 206, 235))

# Ground plane
ground = Entity(model='plane', scale=150, position=(0, 0, 0), color=color.rgb(34, 139, 34), collider='box')

# Water moat
moat = Entity(model='circle', scale=70, color=color.rgb(64, 164, 223), y=-0.05, segments=64)
moat_inner = Entity(model='circle', scale=45, color=color.rgb(34, 139, 34), y=-0.04, segments=64, collider='box')

# === PEACH'S CASTLE STRUCTURE ===

# Castle foundation
foundation = Entity(model='cylinder', position=(0, 1, 25), scale=(35, 2, 35), 
                   color=color.rgb(245, 245, 220), segments=8, collider='box')

# Main castle body
main_body = Entity(model='cylinder', position=(0, 6, 25), scale=(25, 10, 25), 
                  color=color.rgb(255, 250, 240), segments=8, collider='box')

# Castle upper section
upper_body = Entity(model='cylinder', position=(0, 12, 25), scale=(22, 6, 22), 
                   color=color.rgb(255, 250, 240), segments=8, collider='box')

# Front entrance structure
entrance_base = Entity(model='cube', position=(0, 3, 10), scale=(12, 6, 8), 
                      color=color.rgb(255, 250, 240), collider='box')

# Door (Goal)
door = Entity(model='cube', position=(0, 1.5, 5.9), scale=(4, 3, 0.3), 
             color=color.rgb(139, 69, 19), collider='box')

# Peach's emblem window
emblem_frame = Entity(model='cylinder', position=(0, 8, 10), scale=(3, 0.3, 3), 
                     rotation=(90, 0, 0), color=color.rgb(255, 215, 0), segments=16)
emblem_glass = Entity(model='circle', position=(0, 8, 9.9), scale=2.5, 
                     color=color.pink, segments=16)

# === TOWERS WITH PLATFORMS ===

# Front left tower with platform
fl_tower_base = Entity(model='cylinder', position=(-15, 5, 15), scale=(5, 10, 5), 
                      color=color.rgb(255, 250, 240), collider='box')
fl_platform = Entity(model='cylinder', position=(-15, 10, 15), scale=(6, 0.5, 6), 
                    color=color.brown, collider='box')
fl_tower_dome = Entity(model='sphere', position=(-15, 14, 15), scale=(5, 4, 5), 
                      color=color.rgb(220, 20, 60))

# Front right tower with platform
fr_tower_base = Entity(model='cylinder', position=(15, 5, 15), scale=(5, 10, 5), 
                      color=color.rgb(255, 250, 240), collider='box')
fr_platform = Entity(model='cylinder', position=(15, 10, 15), scale=(6, 0.5, 6), 
                    color=color.brown, collider='box')
fr_tower_dome = Entity(model='sphere', position=(15, 14, 15), scale=(5, 4, 5), 
                      color=color.rgb(220, 20, 60))

# Central tower
central_base = Entity(model='cylinder', position=(0, 14, 25), scale=(8, 12, 8), 
                     color=color.rgb(255, 250, 240), collider='box')
central_dome = Entity(model='sphere', position=(0, 24, 25), scale=(7, 6, 7), 
                     color=color.rgb(220, 20, 60))

# === GAMEPLAY PLATFORMS ===

platforms = [
    # Bridge to castle
    Entity(model='cube', position=(0, 0.1, -5), scale=(8, 0.3, 30), 
           color=color.rgb(160, 82, 45), collider='box'),
    
    # Stepping stones to towers
    Entity(model='cube', scale=(3, 0.5, 3), position=(-8, 2, 10), collider='box', color=color.gray),
    Entity(model='cube', scale=(3, 0.5, 3), position=(-11, 4, 12), collider='box', color=color.gray),
    Entity(model='cube', scale=(3, 0.5, 3), position=(-14, 6, 14), collider='box', color=color.gray),
    
    Entity(model='cube', scale=(3, 0.5, 3), position=(8, 2, 10), collider='box', color=color.gray),
    Entity(model='cube', scale=(3, 0.5, 3), position=(11, 4, 12), collider='box', color=color.gray),
    Entity(model='cube', scale=(3, 0.5, 3), position=(14, 6, 14), collider='box', color=color.gray),
    
    # Floating platforms around castle
    Entity(model='cube', scale=(4, 0.5, 4), position=(25, 3, 25), collider='box', color=color.brown),
    Entity(model='cube', scale=(4, 0.5, 4), position=(-25, 3, 25), collider='box', color=color.brown),
    Entity(model='cube', scale=(4, 0.5, 4), position=(0, 5, 40), collider='box', color=color.brown),
]

# === COINS ===

coins = []
coin_positions = [
    # Coins on bridge
    (0, 1, -10), (0, 1, -5), (0, 1, 0),
    
    # Coins on stepping stones
    (-8, 3, 10), (8, 3, 10),
    
    # Coins on tower platforms
    (-15, 11, 15), (15, 11, 15),
    
    # Coins around castle
    (25, 4, 25), (-25, 4, 25), (0, 6, 40),
    (10, 1, 35), (-10, 1, 35),
    
    # Hidden coins
    (0, 15, 25), (20, 1, 0), (-20, 1, 0),
]

for pos in coin_positions:
    coin = Entity(model='sphere', scale=0.8, position=pos, color=color.yellow, collider='sphere')
    coin.rotation_speed = random.uniform(50, 100)
    coins.append(coin)

# === ENEMIES ===

enemies = []
enemy_paths = [
    # Enemy patrolling bridge
    {'pos': (0, 1, -15), 'start': -4, 'end': 4, 'axis': 'x', 'speed': 3},
    
    # Enemy near left tower
    {'pos': (-15, 1, 5), 'start': -20, 'end': -10, 'axis': 'x', 'speed': 2},
    
    # Enemy near right tower  
    {'pos': (15, 1, 5), 'start': 10, 'end': 20, 'axis': 'x', 'speed': 2},
    
    # Enemy behind castle
    {'pos': (0, 1, 35), 'start': -10, 'end': 10, 'axis': 'x', 'speed': 2.5},
]

for enemy_data in enemy_paths:
    enemy = Entity(model='cube', scale=(1.5, 1.5, 1.5), position=enemy_data['pos'], 
                  color=color.rgb(128, 0, 128), collider='box')
    enemy.patrol_start = enemy_data['start']
    enemy.patrol_end = enemy_data['end']
    enemy.patrol_speed = enemy_data['speed']
    enemy.patrol_axis = enemy_data['axis']
    enemy.direction = 1
    enemies.append(enemy)

# === SPECIAL COLLECTIBLES ===

# Power Star on top of central tower
power_star = Entity(model='sphere', scale=1.5, position=(0, 26, 25), 
                   color=color.rgb(255, 215, 0), collider='sphere')
power_star.rotation_speed = 100

# === PLAYER ===

player = Player(position=(0, 2, -20))

# === UI ===

score = 0
stars_collected = 0
score_text = Text(text=f'Coins: {score}/15', position=(-0.85, 0.45), origin=(0, 0), scale=2)
star_text = Text(text=f'Stars: {stars_collected}/1', position=(-0.85, 0.38), origin=(0, 0), scale=2)
message_text = Text(text='', position=(0, 0.3), origin=(0, 0), scale=3, color=color.yellow)

# === UPDATE FUNCTION ===

def update():
    global score, stars_collected
    
    # Rotate coins and star
    for coin in coins:
        coin.rotation_y += coin.rotation_speed * time.dt
    power_star.rotation_y += power_star.rotation_speed * time.dt
    
    # Coin collection
    for coin in coins[:]:
        if player.intersects(coin).hit:
            coins.remove(coin)
            destroy(coin)
            score += 1
            score_text.text = f'Coins: {score}/15'
            
    # Power star collection
    if power_star.enabled and player.intersects(power_star).hit:
        power_star.enabled = False
        stars_collected = 1
        star_text.text = f'Stars: {stars_collected}/1'
        message_text.text = 'POWER STAR!'
        invoke(lambda: setattr(message_text, 'text', ''), delay=2)
    
    # Enemy movement and collision
    for enemy in enemies:
        if enemy.patrol_axis == 'x':
            enemy.x += enemy.patrol_speed * enemy.direction * time.dt
            if enemy.x > enemy.patrol_end:
                enemy.x = enemy.patrol_end
                enemy.direction = -1
            elif enemy.x < enemy.patrol_start:
                enemy.x = enemy.patrol_start
                enemy.direction = 1
        
        # Check collision with player
        if player.intersects(enemy).hit:
            player.position = Vec3(0, 2, -20)  # Reset position
            message_text.text = 'Ouch!'
            invoke(lambda: setattr(message_text, 'text', ''), delay=1)
    
    # Win condition - reach castle door with all coins and star
    if player.intersects(door).hit:
        if score >= 15 and stars_collected >= 1:
            message_text.text = 'YOU WIN! Welcome to the Castle!'
            message_text.color = color.gold
        else:
            message_text.text = f'Need {15-score} more coins and {1-stars_collected} stars!'
            invoke(lambda: setattr(message_text, 'text', ''), delay=2)
    
    # Camera follows player (Mario 64-style)
    target_pos = player.position + Vec3(8, 8, -15)
    camera.position = lerp(camera.position, target_pos, camera.smoothness * time.dt)
    camera.look_at(player.position + Vec3(0, 2, 0))

# Flat shading for retro look
for e in scene.entities:
    if e.model:
        e.shader = None

# Instructions
instructions = Text('WASD/Arrows: Move | Space: Jump | Collect all coins and the star to enter the castle!', 
                   position=(0, -0.48), origin=(0, 0), scale=1.5)

app.run()
