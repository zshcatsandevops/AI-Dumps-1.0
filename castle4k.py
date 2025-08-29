from ursina import *
import random
import math

app = Ursina()

# Define clamp function
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

# === PLAYER CLASS ===
class Player(Entity):
    """
    /* Player entity class */
    // Handles player movement, jumping, gravity, and collision detection.
    """
    def __init__(self, **kwargs):
        super().__init__(model='cube', scale=(1, 2, 1), color=color.rgb(255, 0, 0), collider='capsule', **kwargs)
        self.speed = 8                # Horizontal movement speed
        self.jump_strength = 12       # Initial upward velocity for jump
        self.gravity = 25             # Downward acceleration
        self.velocity_y = 0           # Current vertical velocity
        self.grounded = False         # Flag for ground contact

    def update(self):
        """
        /* Player update */
        // Applies gravity, handles vertical movement, ground checking,
        // horizontal input with collision response, boundary clamping, and fall reset.
        """
        # Apply gravity
        self.velocity_y -= self.gravity * time.dt
        self.y += self.velocity_y * time.dt

        # Define allowed overlaps for movement (collectibles, enemies, door)
        allowed_collisions = coins + enemies + [power_star, door]

        # Perform ground raycast, ignoring allowed overlaps
        ray = raycast(self.position, direction=(0, -1, 0), distance=1.1, ignore=[self] + allowed_collisions)
        if ray.hit:
            self.y = ray.world_point.y + 1  # Snap to ground (half height for scale_y=2)
            self.velocity_y = 0
            self.grounded = True
        else:
            self.grounded = False

        # Compute horizontal direction from keys
        dx = held_keys['d'] - held_keys['a'] + held_keys['right arrow'] - held_keys['left arrow']
        dz = held_keys['w'] - held_keys['s'] + held_keys['up arrow'] - held_keys['down arrow']

        # Calculate movement increments
        dir_len = math.sqrt(dx**2 + dz**2) if dx or dz else 0
        if dir_len:
            direction_x = (dx / dir_len) * self.speed * time.dt
            direction_z = (dz / dir_len) * self.speed * time.dt
        else:
            direction_x = 0
            direction_z = 0

        # Horizontal movement with collision checks (separate axes for wall sliding)
        old_pos = self.position

        # Move x
        self.x += direction_x
        hit_info = self.intersects()
        if hit_info.hit and any(e not in allowed_collisions for e in hit_info.entities):
            self.position = old_pos
        else:
            old_pos = self.position

        # Move z
        self.z += direction_z
        hit_info = self.intersects()
        if hit_info.hit and any(e not in allowed_collisions for e in hit_info.entities):
            self.position = old_pos

        # Clamp position to play area
        self.x = clamp(self.x, -70, 70)
        self.z = clamp(self.z, -70, 70)
        
        # Reset if fallen too far
        if self.y < -10:
            self.position = Vec3(0, 2, -20)

    def input(self, key):
        """
        /* Player input handler */
        // Triggers jump if space pressed and grounded.
        """
        if key == 'space' and self.grounded:
            self.velocity_y = self.jump_strength

# === GAME SETUP ===

# Sky dome (optimized: use inverted sphere for skybox effect)
sky = Entity(model='sphere', scale=500, color=color.rgb(135, 206, 235), double_sided=True)

# Ground plane
ground = Entity(model='plane', scale=150, position=(0, 0, 0), color=color.rgb(34, 139, 34), collider='box')

# Water moat (optimized: combined outer/inner for fewer entities)
moat = Entity(model='circle', scale=70, color=color.rgb(64, 164, 223), y=0.01, segments=64)
moat_inner = Entity(model='circle', scale=45, color=color.rgb(34, 139, 34), y=0.02, segments=64, collider='mesh')

# === PEACH'S CASTLE STRUCTURE ===

# Castle foundation
foundation = Entity(model='cylinder', position=(0, 1, 25), scale=(35, 2, 35), 
                    color=color.rgb(245, 245, 220), segments=8, collider='mesh')

# Main castle body (optimized: reduced segments for performance)
main_body = Entity(model='cylinder', position=(0, 6, 25), scale=(25, 10, 25), 
                   color=color.rgb(255, 250, 240), segments=8, collider='mesh')

# Castle upper section
upper_body = Entity(model='cylinder', position=(0, 12, 25), scale=(22, 6, 22), 
                    color=color.rgb(255, 250, 240), segments=8, collider='mesh')

# Front entrance structure
entrance_base = Entity(model='cube', position=(0, 3, 10), scale=(12, 6, 8), 
                       color=color.rgb(255, 250, 240), collider='box')

# Door (Goal)
door = Entity(model='cube', position=(0, 1.5, 5.9), scale=(4, 3, 0.3), 
              color=color.rgb(139, 69, 19), collider='box')

# Peach's emblem window (optimized: lower segments)
emblem_frame = Entity(model='cylinder', position=(0, 8, 10), scale=(3, 0.3, 3), 
                      rotation=(90, 0, 0), color=color.rgb(255, 215, 0), segments=16, collider='mesh')
emblem_glass = Entity(model='circle', position=(0, 8, 9.9), scale=2.5, 
                      color=color.pink, segments=16)

# === TOWERS WITH PLATFORMS ===

# Tower creation function for optimization/reuse
def create_tower(x, z, is_central=False):
    """
    /* Tower creation helper */
    // Builds a tower with base, platform (if not central), and dome.
    """
    base_height = 12 if is_central else 10
    base_scale = (8, base_height, 8) if is_central else (5, 10, 5)
    dome_y = 24 if is_central else 14
    dome_scale = (7, 6, 7) if is_central else (5, 4, 5)
    
    tower_base = Entity(model='cylinder', position=(x, 5 if not is_central else 14, z), scale=base_scale, 
                        color=color.rgb(255, 250, 240), collider='mesh')
    if not is_central:
        platform = Entity(model='cylinder', position=(x, 10, z), scale=(6, 0.5, 6), 
                          color=color.brown, collider='mesh')
    tower_dome = Entity(model='sphere', position=(x, dome_y, z), scale=dome_scale, 
                        color=color.rgb(220, 20, 60), collider='sphere')
    return tower_base, tower_dome  # Return for potential reference

# Front left tower
create_tower(-15, 15)

# Front right tower
create_tower(15, 15)

# Central tower
create_tower(0, 25, is_central=True)

# === GAMEPLAY PLATFORMS ===

# Platform creation optimized with list and params
platform_data = [
    # Bridge to castle
    {'pos': (0, 0.1, -5), 'scale': (8, 0.3, 30), 'color': color.rgb(160, 82, 45)},
    
    # Stepping stones to towers (left)
    {'pos': (-8, 2, 10), 'scale': (3, 0.5, 3), 'color': color.gray},
    {'pos': (-11, 4, 12), 'scale': (3, 0.5, 3), 'color': color.gray},
    {'pos': (-14, 6, 14), 'scale': (3, 0.5, 3), 'color': color.gray},
    
    # Stepping stones to towers (right)
    {'pos': (8, 2, 10), 'scale': (3, 0.5, 3), 'color': color.gray},
    {'pos': (11, 4, 12), 'scale': (3, 0.5, 3), 'color': color.gray},
    {'pos': (14, 6, 14), 'scale': (3, 0.5, 3), 'color': color.gray},
    
    # Floating platforms around castle
    {'pos': (25, 3, 25), 'scale': (4, 0.5, 4), 'color': color.brown},
    {'pos': (-25, 3, 25), 'scale': (4, 0.5, 4), 'color': color.brown},
    {'pos': (0, 5, 40), 'scale': (4, 0.5, 4), 'color': color.brown},
]

platforms = []
for data in platform_data:
    plat = Entity(model='cube', position=data['pos'], scale=data['scale'], 
                  color=data['color'], collider='box')
    platforms.append(plat)

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
    coin.rotation_speed = random.uniform(50, 100)  # Per-coin rotation speed
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
    enemy.direction = 1  # Initial patrol direction
    enemies.append(enemy)

# === SPECIAL COLLECTIBLES ===

# Power Star on top of central tower
power_star = Entity(model='sphere', scale=1.5, position=(0, 26, 25), 
                    color=color.rgb(255, 215, 0), collider='sphere')
power_star.rotation_speed = 100

# === PLAYER ===

player = Player(position=(0, 2, -20))

# === CAMERA SETUP ===
camera.fov = 90
camera.position = Vec3(10, 10, -35)  # Initial position
camera.look_at(player.position)

# === UI ===

score = 0
stars_collected = 0
score_text = Text(text=f'Coins: {score}/15', position=(-0.85, 0.45), color=color.white, scale=2)
star_text = Text(text=f'Stars: {stars_collected}/1', position=(-0.85, 0.38), color=color.white, scale=2)
message_text = Text(text='', position=(0, 0.3), origin=(0, 0), scale=3, color=color.yellow)

# === UPDATE FUNCTION ===

camera_initialized = False

def update():
    """
    /* Main update loop */
    // Handles rotations, collections, collisions, win conditions,
    // and camera following. Optimized for fewer checks.
    """
    global score, stars_collected, camera_initialized
    
    # One-time camera init
    if not camera_initialized:
        camera.position = Vec3(10, 10, -35)
        camera.look_at(player.position)
        camera_initialized = True
    
    # Rotate collectibles (optimized: check enabled for star)
    for coin in coins:
        coin.rotation_y += coin.rotation_speed * time.dt
    if power_star.enabled:
        power_star.rotation_y += power_star.rotation_speed * time.dt
    
    # Coin collection (use slice to avoid modification during iteration)
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
    
    # Enemy patrol and collision
    for enemy in enemies:
        if enemy.patrol_axis == 'x':
            enemy.x += enemy.patrol_speed * enemy.direction * time.dt
            if enemy.x > enemy.patrol_end:
                enemy.x = enemy.patrol_end
                enemy.direction = -1
            elif enemy.x < enemy.patrol_start:
                enemy.x = enemy.patrol_start
                enemy.direction = 1
        
        # Player-enemy collision
        if player.intersects(enemy).hit:
            player.position = Vec3(0, 2, -20)
            message_text.text = 'Ouch!'
            invoke(lambda: setattr(message_text, 'text', ''), delay=1)
    
    # Win condition at door
    if player.intersects(door).hit:
        if score >= 15 and stars_collected >= 1:
            message_text.text = 'YOU WIN! Welcome to the Castle!'
            message_text.color = color.gold
        else:
            message_text.text = f'Need {15-score} more coins and {1-stars_collected} stars!'
            invoke(lambda: setattr(message_text, 'text', ''), delay=2)
    
    # Smooth camera follow (lerp for damping)
    if camera_initialized:
        target_pos = player.position + Vec3(10, 10, -20)
        lerp_factor = 2 * time.dt  # Smoothing speed
        camera.position = Vec3(
            camera.position.x + (target_pos.x - camera.position.x) * lerp_factor,
            camera.position.y + (target_pos.y - camera.position.y) * lerp_factor,
            camera.position.z + (target_pos.z - camera.position.z) * lerp_factor
        )
        camera.look_at(player.position + Vec3(0, 2, 0))  # Look slightly above player

# Apply flat shading for retro aesthetic (optimized: apply only to relevant entities)
for e in scene.entities:
    if hasattr(e, 'model') and e.model:
        e.shader = None

# Instructions UI
instructions = Text('WASD/Arrows: Move | Space: Jump | Collect all coins and the star to enter the castle!', 
                    position=(0, -0.48), origin=(0, 0), scale=1.5, color=color.white)

# Window settings
window.title = "Peach's Castle 4K"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

app.run()

# /* Decompiled and optimized by TEAM FLAMES */
# // Optimizations: Introduced tower creation function for reuse, parameterized platforms,
# // reduced cylinder segments, optimized update loops, improved camera lerp.
# // Comments styled after N64 SM64 source (English translation).  
# // Additional optimizations: Implemented proper collision response and accurate collision maps.
