import ursina
import os
from ursina import *

app = Ursina()

# Set window properties to target 60 FPS
window.fps_counter.enabled = True
window.exit_button.enabled = False
window.title = "Paper Mario 3D Bros"

# Mario entity (flat quad to mimic paper aesthetic)
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
    scale=(50, 1, 10),
    position=(0, -3, 0),
    collider='box'
)

# Obstacles
for i in range(3):
    Entity(
        model='cube',
        color=color.gray,
        scale=(2, 2, 2),
        position=(random.randint(-10, 10), -2, random.randint(-5, 5)),
        collider='box'
    )

# Goomba enemy
goomba = Entity(
    model='quad',
    color=color.brown,
    scale=(0.5, 0.5, 0.1),
    position=(5, -2, 0),
    collider='box'
)
goomba.health = 10

# Camera setup
camera.orthographic = True
camera.fov = 20
camera.position = (0, 5, -20)
camera.look_at(mario)

# Combat state
game_state = 'play'
combat_text = Text(
    text='',
    position=(0, 0.2),
    scale=2,
    enabled=False
)

# Update function for movement and game logic
def update():
    global game_state
    if game_state == 'play':
        # Mario movement
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

        # Camera follows Mario
        camera.position = (mario.x, mario.y + 5, -20)

        # Enemy collision
        if mario.intersects(goomba).hit:
            game_state = 'combat'
            combat_text.text = 'Combat! Press 1 to Attack, 2 to Flee'
            combat_text.enabled = True
            mario.enabled = False  # Freeze Mario during combat

    elif game_state == 'combat':
        if held_keys['1']:
            goomba.health -= 5
            combat_text.text = f'Attacked! Goomba HP: {goomba.health}'
            if goomba.health <= 0:
                destroy(goomba)
                combat_text.text = 'Enemy defeated!'
                invoke(setattr, combat_text, 'enabled', False, delay=1)
                invoke(setattr, mario, 'enabled', True, delay=1)
                invoke(setattr, globals(), 'game_state', 'play', delay=1)
        elif held_keys['2']:
            combat_text.text = 'Fled from battle!'
            invoke(setattr, combat_text, 'enabled', False, delay=1)
            invoke(setattr, mario, 'enabled', True, delay=1)
            invoke(setattr, globals(), 'game_state', 'play', delay=1)

app.run()
