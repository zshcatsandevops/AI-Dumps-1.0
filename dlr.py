from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from random import uniform, choice
from math import sin, cos

# Initialize app with specific window size
app = Ursina()
window.title = 'Cool, Cool Mountain Recreation in Ursina (SM64 Style)'
window.size = (600, 400)
window.borderless = False
window.fullscreen = False
window.fps_counter.enabled = True
window.vsync = True

# Sky and lighting
Sky(color=color.rgb(135, 206, 235))
DirectionalLight(parent=scene, y=3, z=-3, rotation=(45, -45, 0))

# Player (first-person controller for exploration)
player = FirstPersonController(
    position=(0, 55, 0), 
    speed=10,
    jump_height=3,
    mouse_sensitivity=Vec2(40, 40)
)
player.gravity = 0.8

# Base mountain geometry
base = Entity(
    model='circle', 
    scale=(50, 1, 50), 
    y=0, 
    color=color.white.tint(-0.1), 
    collider='mesh',
    texture='white_cube'
)

# Layered conical mountain shape
mountain_layers = []
for i in range(1, 11):
    layer_scale = 50 - i * 4.5
    layer = Entity(
        model='cylinder', 
        scale=(layer_scale, 2, layer_scale), 
        y=i * 5, 
        color=color.white.tint(-0.05 * i), 
        collider='mesh',
        texture='white_cube'
    )
    mountain_layers.append(layer)

# Top platform
top_platform = Entity(
    model='cube', 
    scale=(10, 1, 10), 
    y=50, 
    color=color.white, 
    collider='box',
    texture='white_cube'
)

# Cabin at top
cabin = Entity(
    model='cube', 
    scale=(5, 4, 5), 
    position=(0, 52, 0), 
    color=color.rgb(139, 69, 19), 
    collider='box',
    texture='white_cube'
)

# Cabin roof
roof = Entity(
    model='cone', 
    scale=(6, 2, 6), 
    position=(0, 54.5, 0), 
    color=color.rgb(165, 42, 42), 
    collider='box'
)

# Chimney (entry to slide)
chimney = Entity(
    model='cube', 
    scale=(1.5, 3, 1.5), 
    position=(1.5, 56, 1.5), 
    color=color.dark_gray, 
    collider='box'
)

# Slide path winding down the mountain
slide_parts = []
slide_positions = [
    Vec3(0, 50, 5), Vec3(5, 45, 10), Vec3(10, 40, 5), Vec3(15, 35, 0),
    Vec3(10, 30, -5), Vec3(5, 25, -10), Vec3(0, 20, -5), Vec3(-5, 15, 0),
    Vec3(-10, 10, 5), Vec3(-5, 5, 10), Vec3(0, 1, 5)
]

for i in range(len(slide_positions) - 1):
    start = slide_positions[i]
    end = slide_positions[i + 1]
    midpoint = (start + end) / 2
    
    slide_seg = Entity(
        model='cube', 
        scale=(4, 0.5, distance(start, end)), 
        position=midpoint,
        color=color.rgb(135, 206, 250), 
        collider='box'
    )
    slide_seg.look_at(end)
    slide_parts.append(slide_seg)

# Bottom cabin
bottom_cabin = Entity(
    model='cube', 
    scale=(4, 3, 4), 
    position=(0, 1.5, 5), 
    color=color.rgb(139, 69, 19), 
    collider='box',
    texture='white_cube'
)

# Penguins (improved models)
def create_penguin(pos, scale_factor=1):
    body = Entity(
        model='sphere', 
        scale=(1.5*scale_factor, 2*scale_factor, 1.5*scale_factor), 
        position=pos, 
        color=color.black.tint(0.3), 
        collider='sphere'
    )
    belly = Entity(
        model='sphere', 
        scale=(1.2*scale_factor, 1.6*scale_factor, 0.5*scale_factor), 
        position=pos + Vec3(0, 0, 0.5*scale_factor), 
        color=color.white, 
        parent=body
    )
    return body

mother_penguin = create_penguin(Vec3(5, 2, 10), 1.2)
baby_penguin = create_penguin(Vec3(3, 51, 3), 0.8)

# Snowman
snowman_base = Entity(
    model='sphere', 
    scale=3, 
    position=(20, 3, 20), 
    color=color.white, 
    collider='sphere'
)
snowman_middle = Entity(
    model='sphere', 
    scale=2.2, 
    position=(20, 5.5, 20), 
    color=color.white, 
    collider='sphere'
)
snowman_head = Entity(
    model='sphere', 
    scale=1.5, 
    position=(25, 20, 25), 
    color=color.white, 
    collider='sphere'
)

# Power Stars
stars = []
star_positions = [
    (0, 2, 5), (10, 40, 0), (-10, 20, 0), 
    (20, 10, 20), (0, 56, 0)
]

for pos in star_positions:
    star = Entity(
        model='cube', 
        scale=1.5, 
        position=pos, 
        color=color.yellow, 
        collider='box'
    )
    star.rotation_y = 45
    stars.append(star)

# Coins scattered around
coins = []
collected_coins = 0
for _ in range(20):
    coin_pos = (
        uniform(-25, 25), 
        uniform(2, 45), 
        uniform(-25, 25)
    )
    coin = Entity(
        model='cylinder', 
        scale=(0.8, 0.1, 0.8), 
        position=coin_pos, 
        color=color.yellow, 
        collider='box',
        rotation=(90, 0, 0)
    )
    coins.append(coin)

# Bridges
bridge1 = Entity(
    model='cube', 
    scale=(10, 0.5, 3), 
    position=(15, 30, 15), 
    rotation=(0, 45, 0), 
    color=color.rgb(139, 90, 43), 
    collider='box'
)

bridge2 = Entity(
    model='cube', 
    scale=(5, 0.5, 3), 
    position=(20, 25, 20), 
    rotation=(0, 45, 0), 
    color=color.rgb(139, 90, 43), 
    collider='box'
)

# Enemies (Spindrifts)
enemies = []
for _ in range(5):
    enemy = Entity(
        model='cone', 
        scale=(1.5, 2, 1.5), 
        position=(
            uniform(-20, 20), 
            uniform(5, 40), 
            uniform(-20, 20)
        ), 
        color=color.rgb(144, 238, 144), 
        collider='sphere'
    )
    enemies.append(enemy)

# UI Text
coin_text = Text(
    'Coins: 0', 
    position=(-0.85, 0.45), 
    scale=2, 
    color=color.yellow
)

info_text = Text(
    'Press R to rearrange level', 
    position=(-0.85, 0.40), 
    scale=1.5, 
    color=color.white
)

# Game state
rearranged = False
time_accumulator = 0

def update():
    global rearranged, collected_coins, time_accumulator
    
    time_accumulator += time.dt
    
    # Rotate stars
    for star in stars:
        star.rotation_y += 100 * time.dt
        star.y += sin(time_accumulator * 2) * 0.01
    
    # Rotate coins
    for coin in coins:
        if coin.enabled:
            coin.rotation_z += 200 * time.dt
    
    # Enemy movement (spin and float)
    for i, enemy in enumerate(enemies):
        enemy.rotation_y += 150 * time.dt
        enemy.y += sin(time_accumulator * 3 + i) * 0.02
    
    # Collect coins
    for coin in coins:
        if coin.enabled and distance(player.position, coin.position) < 2:
            coin.enabled = False
            collected_coins += 1
            coin_text.text = f'Coins: {collected_coins}'
    
    # Collect stars
    for star in stars:
        if star.enabled and distance(player.position, star.position) < 2:
            star.enabled = False
            print("You got a Power Star!")
    
    # Slide physics (simple)
    for i, slide_part in enumerate(slide_parts):
        if distance(player.position, slide_part.position) < 3:
            # Apply sliding force downward along the slide
            if i < len(slide_positions) - 1:
                slide_direction = (slide_positions[i + 1] - slide_positions[i]).normalized()
                player.position += slide_direction * time.dt * 5
    
    # Dynamic rearrangement
    if held_keys['r'] and not rearranged:
        rearranged = True
        info_text.text = 'Level Rearranged!'
        
        # Relocate stars
        for star in stars:
            if star.enabled:
                star.position = Vec3(
                    uniform(-25, 25), 
                    uniform(5, 55), 
                    uniform(-25, 25)
                )
        
        # Discolor coins and stars
        for coin in coins:
            if coin.enabled:
                coin.color = choice([
                    color.red, color.blue, 
                    color.green, color.violet, 
                    color.orange
                ])
        
        for star in stars:
            if star.enabled:
                star.color = choice([
                    color.cyan, color.magenta, 
                    color.lime, color.pink
                ])
        
        # Rearrange level elements
        bridge2.position += Vec3(5, -5, 5)
        snowman_head.position = Vec3(
            uniform(10, 30), 
            uniform(20, 40), 
            uniform(10, 30)
        )
        
        # Reposition enemies
        for enemy in enemies:
            enemy.position = Vec3(
                uniform(-25, 25), 
                uniform(5, 50), 
                uniform(-25, 25)
            )
        
        # Change enemy colors
        for enemy in enemies:
            enemy.color = choice([
                color.red.tint(-0.2), 
                color.green.tint(-0.2), 
                color.blue.tint(-0.2)
            ])
    
    # Reset rearrangement with T key
    if held_keys['t'] and rearranged:
        rearranged = False
        info_text.text = 'Press R to rearrange level'

# Camera controls info
controls_text = Text(
    'WASD: Move | Mouse: Look | Space: Jump | R: Rearrange | T: Reset', 
    position=(0, -0.45), 
    origin=(0, 0),
    scale=1.2, 
    color=color.white
)

# Run the game
app.run()
