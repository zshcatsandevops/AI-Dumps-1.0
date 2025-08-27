import ursina
from ursina import *

app = Ursina()

# Set window properties to target 60 FPS
window.fps_counter.enabled = True
window.exit_button.enabled = False
window.title = "Super Mario 64 - Peach's Castle"

# Mario entity (flat quad to mimic SM64 aesthetic)
mario = Entity(
    model='quad',
    color=color.red,
    scale=(0.5, 1, 0.1),
    position=(0, 0, 0),
    collider='box'
)
mario.jump_strength = 5
mario.y_velocity = 0
mario.grounded = True
mario.gravity = 0.2

# Ground entity
ground = Entity(
    model='cube',
    color=color.green,
    scale=(50, 1, 50),
    position=(0, -3, 0),
    collider='box'
)

# Simplified Peach's Castle (using basic shapes)
castle_base = Entity(
    model='cube',
    color=color.white,
    scale=(10, 4, 10),
    position=(0, -1, 10),
    collider='box'
)
castle_walls = Entity(
    model='cube',
    color=color.white,
    scale=(12, 6, 1),
    position=(0, 0, 15),
    collider='box'
)
castle_tower = Entity(
    model='cube',
    color=color.white,
    scale=(3, 8, 3),
    position=(5, 1, 10),
    collider='box'
)
castle_roof = Entity(
    model='quad',
    color=color.blue,
    scale=(12, 12),
    position=(0, 2, 10),
    rotation=(90, 0, 0)
)
castle_flag = Entity(
    model='quad',
    color=color.yellow,
    scale=(1, 1),
    position=(5, 5, 10)
)

# Collectible star
star = Entity(
    model='quad',
    color=color.yellow,
    scale=(0.5, 0.5),
    position=(3, -2, 5),
    collider='box'
)

# HUD
stars = 0
health = 3
star_text = Text(
    text=f'Stars: {stars}',
    position=(-0.6, 0.4),
    scale=2
)
health_text = Text(
    text=f'Health: {health}',
    position=(-0.6, 0.35),
    scale=2
)

# Camera setup
camera.orthographic = True
camera.fov = 20
camera.position = (0, 5, -20)
camera.look_at(mario)

# Update function for movement and game logic
def update():
    global stars
    # Mario movement (WASD controls inspired by SM64 PC port)
    mario.x += held_keys['d'] * 0.1
    mario.x -= held_keys['a'] * 0.1
    mario.z += held_keys['w'] * 0.1
    mario.z -= held_keys['s'] * 0.1

    # Jumping
    if held_keys['space'] and mario.grounded:
        mario.y_velocity = mario.jump_strength
        mario.grounded = False

    # Apply gravity
    mario.y_velocity -= mario.gravity
    mario.y += mario.y_velocity * time.dt * 60  # Normalize for 60 FPS

    # Ground collision
    if mario.y < -2:
        mario.y = -2
        mario.y_velocity = 0
        mario.grounded = True

    # Star collection
    if mario.intersects(star).hit:
        stars += 1
        star_text.text = f'Stars: {stars}'
        destroy(star)

    # Camera follows Mario
    camera.position = (mario.x, mario.y + 5, -20)

app.run()
