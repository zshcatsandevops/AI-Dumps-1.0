# pinball_game.py
from ursina import *
import random

# Initialize Ursina app with 60 FPS target
app = Ursina()
window.fps_counter.enabled = True
application.fps = 60  # Lock to 60 FPS

# Set up the scene
scene.fog_density = 0.01
Sky()

# Playfield (a tilted plane)
playfield = Entity(
    model='plane',
    scale=(10, 20, 1),
    rotation=(10, 0, 0),  # Tilted like a pinball table
    texture='white_cube',
    color=color.gray,
    collider='box'
)

# Ball with manual physics
ball = Entity(
    model='sphere',
    scale=0.3,
    color=color.red,
    collider='sphere',
    position=(0, 1, 0.5)
)
ball.velocity = Vec3(0, 0, 0)  # Custom velocity for manual physics
ball.gravity = 9.81  # Standard gravity
ball.friction = 0.1  # Low friction

# Flippers (left and right)
left_flipper = Entity(
    model='cube',
    scale=(2, 0.2, 0.5),
    color=color.blue,
    position=(-3, -8, 0.5),
    collider='box',
    rotation=(0, 0, 0)
)

right_flipper = Entity(
    model='cube',
    scale=(2, 0.2, 0.5),
    color=color.blue,
    position=(3, -8, 0.5),
    collider='box',
    rotation=(0, 0, 0)
)

# Bumper (cylindrical, using box collider for stability)
bumper = Entity(
    model='cylinder',
    scale=(0.5, 0.5, 0.5),
    color=color.green,
    position=(0, 2, 0.5),
    collider='box'  # Simpler collider to avoid mesh issues
)

# Camera setup
camera.position = (0, -10, -20)
camera.rotation_x = 30

# Score tracking
score = 0
score_text = Text(text=f'Score: {score}', position=(-0.8, 0.4), scale=2)

# Manual physics and flipper controls
def update():
    global score
    try:
        # Apply gravity and friction to ball
        ball.velocity.y -= ball.gravity * time.dt
        ball.velocity *= (1 - ball.friction * time.dt)
        ball.position += ball.velocity * time.dt

        # Left flipper (Z key)
        if held_keys['z']:
            left_flipper.rotation_z = lerp(left_flipper.rotation_z, 45, time.dt * 10)
            if ball.position.y < -7 and abs(ball.position.x + 3) < 2 and ball.intersects(left_flipper).hit:
                ball.velocity = Vec3(0, 5, 2)  # Apply force
        else:
            left_flipper.rotation_z = lerp(left_flipper.rotation_z, 0, time.dt * 10)

        # Right flipper (M key)
        if held_keys['m']:
            right_flipper.rotation_z = lerp(right_flipper.rotation_z, -45, time.dt * 10)
            if ball.position.y < -7 and abs(ball.position.x - 3) < 2 and ball.intersects(right_flipper).hit:
                ball.velocity = Vec3(0, 5, 2)  # Apply force
        else:
            right_flipper.rotation_z = lerp(right_flipper.rotation_z, 0, time.dt * 10)

        # Bumper collision
        if ball.intersects(bumper).hit:
            score += 10
            score_text.text = f'Score: {score}'
            ball.velocity = Vec3(random.uniform(-2, 2), 5, 2)  # Random bounce

        # Playfield collision (simple bounce)
        if ball.intersects(playfield).hit:
            if ball.position.y < -0.5:
                ball.velocity.y = abs(ball.velocity.y) * 0.8  # Bounce with damping

        # Reset ball if it falls off
        if ball.position.y < -15:
            ball.position = (0, 1, 0.5)
            ball.velocity = Vec3(0, 0, 0)

    except Exception as e:
        print(f"Error in update: {e}")  # Log errors to debug crashes

# Input for launching the ball (spacebar)
def input(key):
    if key == 'space':
        ball.velocity = Vec3(0, 5, 10)  # Launch ball

# Run the game with error handling
try:
    app.run()
except Exception as e:
    print(f"Game crashed: {e}")
