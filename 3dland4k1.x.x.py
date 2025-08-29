from ursina import *
from ursina.prefabs.platformer_controller_2d import PlatformerController2d
import random

app = Ursina()

# Camera setup
camera.orthographic = True
camera.fov = 20
camera.position = (10, 5)

# Player setup
player = PlatformerController2d(scale=(1, 1), position=(0, 0))
player.jump_height = 4
player.walk_speed = 8

# Ground
ground = Entity(model='quad', scale=(50, 1), position=(0, -5), collider='box', color=color.green)

# Platforms
platforms = [
    Entity(model='quad', scale=(4, 0.5), position=(5, -2), collider='box', color=color.brown),
    Entity(model='quad', scale=(4, 0.5), position=(10, 0), collider='box', color=color.brown),
    Entity(model='quad', scale=(4, 0.5), position=(15, 2), collider='box', color=color.brown)
]

# Coins
coins = []
for i in range(5):
    x = random.randint(5, 20)
    y = random.randint(-2, 5)
    coin = Entity(model='circle', scale=0.5, position=(x, y), color=color.yellow)
    coins.append(coin)

# Enemies with patrol data
enemies = []
for i in range(3):
    x = random.randint(10, 30)
    enemy = Entity(model='quad', scale=(1, 1), position=(x, -4), color=color.red)
    enemy.patrol_start = x - 2  # Store patrol boundaries and speed
    enemy.patrol_end = x + 2
    enemy.patrol_speed = 2
    enemy.direction = 1  # 1 for right, -1 for left
    enemies.append(enemy)

# Goal (Flag)
flag = Entity(model='quad', scale=(1, 2), position=(30, -3), color=color.blue)

# Text
score = 0
score_text = Text(text=f'Score: {score}', position=(-0.8, 0.4))

# Update function
def update():
    global score
    # Coin collection
    for coin in coins[:]:
        if player.intersects(coin).hit:
            coins.remove(coin)
            destroy(coin)
            score += 10
            score_text.text = f'Score: {score}'
    
    # Enemy movement (patrol) and collision
    for enemy in enemies:
        # Move enemy back and forth
        enemy.x += enemy.patrol_speed * enemy.direction * time.dt
        if enemy.x > enemy.patrol_end:
            enemy.x = enemy.patrol_end
            enemy.direction = -1
        elif enemy.x < enemy.patrol_start:
            enemy.x = enemy.patrol_start
            enemy.direction = 1
        
        # Check collision with player
        if player.intersects(enemy).hit:
            player.position = (0, 0)  # Reset to start
            score = 0
            score_text.text = f'Score: {score}'
    
    # Win condition
    if player.intersects(flag).hit:
        score_text.text = f'WIN! Score: {score}'

# Input handling
def input(key):
    if key == 'space' and player.grounded:
        player.jump()

# Background
bg = Entity(model='quad', scale=(50, 20), position=(0, 0, -10), color=color.cyan)

app.run()
