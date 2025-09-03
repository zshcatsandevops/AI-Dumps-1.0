from ursina import *

app = Ursina()

# Set window properties to target 60 FPS
window.fps_counter.enabled = True
window.exit_button.enabled = False
window.title = "Super Mario 64 3D - Peach's Castle"

# Mario entity (3D capsule to represent Mario)
mario = Entity(
    model='cube',  # Using cube, but you can use 'sphere' or custom model
    color=color.red,
    scale=(0.5, 1, 0.5),
    position=(0, 0, 0),
    collider='box'
)
mario.jump_strength = 5
mario.y_velocity = 0
mario.grounded = True
mario.gravity = 0.2
mario.movement_speed = 0.1
mario.rotation_speed = 5

# Add a hat to Mario (simple representation)
mario_hat = Entity(
    model='cube',
    color=color.red,
    scale=(0.6, 0.3, 0.6),
    position=(0, 0.6, 0),
    parent=mario
)

# Ground entity
ground = Entity(
    model='cube',
    color=color.green,
    scale=(50, 1, 50),
    position=(0, -3, 0),
    collider='box',
    texture='white_cube'
)

# Simplified Peach's Castle (using 3D shapes)
castle_base = Entity(
    model='cube',
    color=color.white,
    scale=(10, 4, 10),
    position=(0, -1, 15),
    collider='box'
)

castle_walls = Entity(
    model='cube',
    color=rgb(255, 220, 220),
    scale=(12, 6, 8),
    position=(0, 1, 15),
    collider='box'
)

castle_tower = Entity(
    model='cube',  # Changed from cylinder to cube
    color=color.white,
    scale=(3, 8, 3),
    position=(5, 1, 15),
    collider='box'
)

# Tower roof (cube shaped like a pyramid)
castle_tower_roof = Entity(
    model='cube',
    color=color.red,
    scale=(4, 3, 4),
    position=(5, 5, 15),
    rotation=(0, 45, 0)
)

# Second tower
castle_tower2 = Entity(
    model='cube',  # Changed from cylinder to cube
    color=color.white,
    scale=(3, 8, 3),
    position=(-5, 1, 15),
    collider='box'
)

castle_tower_roof2 = Entity(
    model='cube',
    color=color.red,
    scale=(4, 3, 4),
    position=(-5, 5, 15),
    rotation=(0, 45, 0)
)

# Main castle roof
castle_roof = Entity(
    model='cube',  # Changed from pyramid to cube
    color=color.blue,
    scale=(14, 4, 10),
    position=(0, 4, 15),
    rotation=(0, 45, 0)
)

# Castle door
castle_door = Entity(
    model='cube',
    color=color.brown,
    scale=(2, 3, 0.5),
    position=(0, -1.5, 10.5)
)

# Castle flag on pole
flag_pole = Entity(
    model='cube',  # Changed from cylinder to cube
    color=color.gray,
    scale=(0.1, 10, 0.1),
    position=(5, 5, 15)
)

castle_flag = Entity(
    model='cube',
    color=color.yellow,
    scale=(1.5, 1, 0.1),
    position=(5.8, 9, 15)
)

# Collectible star (rotating)
star = Entity(
    model='sphere',
    color=color.yellow,
    scale=(0.5, 0.5, 0.5),
    position=(3, -2, 5),
    collider='sphere'
)

# Additional stars scattered around
star2 = Entity(
    model='sphere',
    color=color.yellow,
    scale=(0.5, 0.5, 0.5),
    position=(-5, -2, -3),
    collider='sphere'
)

star3 = Entity(
    model='sphere',
    color=color.yellow,
    scale=(0.5, 0.5, 0.5),
    position=(8, -2, 8),
    collider='sphere'
)

# Decorative elements
tree1 = Entity(
    model='cube',  # Changed from cylinder to cube
    color=color.brown,
    scale=(1, 3, 1),
    position=(-10, -1.5, 5)
)
tree1_leaves = Entity(
    model='sphere',
    color=color.green,
    scale=(3, 3, 3),
    position=(-10, 1, 5)
)

tree2 = Entity(
    model='cube',  # Changed from cylinder to cube
    color=color.brown,
    scale=(1, 3, 1),
    position=(10, -1.5, -5)
)
tree2_leaves = Entity(
    model='sphere',
    color=color.green,
    scale=(3, 3, 3),
    position=(10, 1, -5)
)

# HUD
stars = 0
health = 3
star_text = Text(
    text=f'Stars: {stars}',
    position=(-0.8, 0.45),
    scale=2,
    color=color.yellow
)
health_text = Text(
    text=f'Health: {health}',
    position=(-0.8, 0.4),
    scale=2,
    color=color.red
)

# Camera setup (3D third-person perspective)
camera.position = (0, 5, -10)
camera.rotation_x = 20
camera.parent = mario
camera.z = -10
camera.y = 8
camera.fov = 60

# Lighting
light = DirectionalLight()
light.look_at(Vec3(1, -1, 1))
AmbientLight(color=color.rgba(100, 100, 100, 255))

# Update function for movement and game logic
def update():
    global stars, health
    
    # Get movement input
    move_x = held_keys['d'] - held_keys['a']
    move_z = held_keys['w'] - held_keys['s']
    
    # Calculate movement direction
    if move_x != 0 or move_z != 0:
        # Move Mario in 3D space
        direction = Vec3(move_x, 0, move_z).normalized()
        mario.x += direction.x * mario.movement_speed
        mario.z += direction.z * mario.movement_speed
        
        # Rotate Mario to face movement direction
        if move_z > 0:
            target_rotation = 0
            if move_x > 0:
                target_rotation = -45
            elif move_x < 0:
                target_rotation = 45
        elif move_z < 0:
            target_rotation = 180
            if move_x > 0:
                target_rotation = -135
            elif move_x < 0:
                target_rotation = 135
        elif move_x > 0:
            target_rotation = -90
        elif move_x < 0:
            target_rotation = 90
        else:
            target_rotation = mario.rotation_y
        
        # Smooth rotation
        mario.rotation_y = lerp(mario.rotation_y, target_rotation, mario.rotation_speed * time.dt)
    
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
    for star_entity in [star, star2, star3]:
        if star_entity and star_entity.enabled and mario.intersects(star_entity).hit:
            stars += 1
            star_text.text = f'Stars: {stars}'
            star_entity.enabled = False
            destroy(star_entity)
    
    # Rotate stars for visual effect
    if star and star.enabled:
        star.rotation_y += 2
    if star2 and star2.enabled:
        star2.rotation_y += 2
    if star3 and star3.enabled:
        star3.rotation_y += 2
    
    # Castle boundary (optional - keep Mario in play area)
    mario.x = clamp(mario.x, -24, 24)
    mario.z = clamp(mario.z, -24, 24)

# Input handler for additional controls
def input(key):
    global health
    
    if key == 'r':
        # Reset position
        mario.position = (0, 0, 0)
        mario.y_velocity = 0
        mario.grounded = True
    
    if key == 'escape':
        application.quit()

# Sky
Sky(color=color.cyan)  # Changed from sky_blue to cyan

app.run()
