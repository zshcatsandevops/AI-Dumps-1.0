from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math

# Initialize Ursina - 60 FPS locked
app = Ursina()
window.title = 'Super Mario 64 - Princess Peach\'s Castle'
window.borderless = False
window.fullscreen = False
window.fps_counter.enabled = True
window.vsync = True
application.target_fps = 60

# Classic SM64 Sky
Sky(texture='sky_default', color=color.rgb(107, 140, 255))
DirectionalLight(y=10, x=3, z=-5, shadows=True, shadow_map_resolution=(2048, 2048))
AmbientLight(color=color.rgba(140, 140, 160, 255))

# Mario character class with authentic SM64 movement
class Mario(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.rgb(255, 0, 0),  # Bright red overalls
            scale=(0.8, 1.2, 0.8),
            position=(0, 1, -20)
        )
        
        # Mario parts
        self.head = Entity(
            parent=self,
            model='sphere',
            color=color.rgb(255, 220, 177),
            scale=(0.9, 0.6, 0.9),
            position=(0, 0.7, 0)
        )
        
        self.cap = Entity(
            parent=self.head,
            model='sphere',
            color=color.rgb(255, 0, 0),
            scale=(1.1, 0.7, 1.1),
            position=(0, 0.25, 0)
        )
        
        # M emblem on cap
        self.emblem = Entity(
            parent=self.cap,
            model='cube',
            color=color.white,
            scale=(0.3, 0.2, 0.01),
            position=(0, 0.1, 0.55)
        )
        
        self.mustache = Entity(
            parent=self.head,
            model='cube',
            color=color.rgb(101, 67, 33),
            scale=(0.7, 0.08, 0.2),
            position=(0, -0.15, 0.45)
        )
        
        # Blue overalls bottom
        self.overalls = Entity(
            parent=self,
            model='cube',
            color=color.rgb(0, 0, 255),
            scale=(0.9, 0.6, 0.9),
            position=(0, -0.3, 0)
        )
        
        # Movement properties - authentic SM64 physics
        self.velocity = Vec3(0, 0, 0)
        self.grounded = False
        self.jump_count = 0
        self.max_jumps = 3
        self.movement_speed = 6
        self.run_speed = 10
        self.jump_height = 9
        self.double_jump_height = 11
        self.triple_jump_height = 14
        self.gravity = 25
        self.air_control = 0.4
        
        # Long jump properties
        self.long_jumping = False
        self.long_jump_timer = 0
        
        # Wall jump properties
        self.can_wall_jump = False
        self.wall_jump_timer = 0
        
        # Animation
        self.bob_timer = 0
        self.flip_rotation = 0
        
    def update(self):
        # Get input
        move_x = 0
        move_z = 0
        
        if held_keys['a']:
            move_x -= 1
        if held_keys['d']:
            move_x += 1
        if held_keys['w']:
            move_z += 1
        if held_keys['s']:
            move_z -= 1
            
        # Calculate movement direction relative to camera
        forward = Vec3(camera.forward.x, 0, camera.forward.z).normalized()
        right = Vec3(camera.right.x, 0, camera.right.z).normalized()
        
        movement = (forward * move_z + right * move_x)
        
        # Running with shift
        speed = self.run_speed if held_keys['shift'] else self.movement_speed
        
        if movement.length() > 0:
            movement = movement.normalized()
            
            # Face movement direction
            if not self.long_jumping:
                look_at = self.position + movement
                self.look_at(Vec3(look_at.x, self.y, look_at.z))
            
        # Apply movement
        if self.grounded:
            self.velocity.x = movement.x * speed
            self.velocity.z = movement.z * speed
            # Reset jump count when landing
            if self.velocity.y <= 0:
                self.jump_count = 0
        else:
            # Air control
            self.velocity.x += movement.x * speed * self.air_control * time.dt
            self.velocity.z += movement.z * speed * self.air_control * time.dt
            
            # Limit air speed
            horizontal_speed = Vec2(self.velocity.x, self.velocity.z).length()
            max_air_speed = speed * 1.5
            if horizontal_speed > max_air_speed:
                self.velocity.x = (self.velocity.x / horizontal_speed) * max_air_speed
                self.velocity.z = (self.velocity.z / horizontal_speed) * max_air_speed
        
        # Long jump decay
        if self.long_jumping:
            self.long_jump_timer -= time.dt
            if self.long_jump_timer <= 0:
                self.long_jumping = False
                
        # Apply gravity
        self.velocity.y -= self.gravity * time.dt
        
        # Terminal velocity
        if self.velocity.y < -30:
            self.velocity.y = -30
        
        # Apply velocity
        self.position += self.velocity * time.dt
        
        # Ground detection
        if self.y <= 1:
            self.y = 1
            self.velocity.y = 0
            self.grounded = True
            self.long_jumping = False
        else:
            self.grounded = False
            
        # Walking animation
        if self.grounded and movement.length() > 0:
            self.bob_timer += time.dt * 12
            self.head.y = 0.7 + math.sin(self.bob_timer) * 0.08
            self.emblem.rotation_z = math.sin(self.bob_timer * 2) * 10
        else:
            self.bob_timer = 0
            self.head.y = 0.7
            
        # Jump flip animation
        if not self.grounded and not self.long_jumping:
            if self.jump_count >= 2:
                # Triple jump spin
                self.flip_rotation += 720 * time.dt
                self.rotation_y += 360 * time.dt
            else:
                # Regular jump flip
                self.flip_rotation += 360 * time.dt
            self.rotation_x = self.flip_rotation
        else:
            self.flip_rotation = 0
            self.rotation_x = lerp(self.rotation_x, 0, time.dt * 10)
            
    def jump(self):
        if self.grounded or self.jump_count < self.max_jumps:
            # SM64-style progressive jumps
            if self.jump_count == 0:
                self.velocity.y = self.jump_height
                self.jump_count = 1
            elif self.jump_count == 1:
                self.velocity.y = self.double_jump_height
                self.jump_count = 2
            elif self.jump_count == 2:
                # Triple jump - YA-HOO!
                self.velocity.y = self.triple_jump_height
                self.jump_count = 3
                
            self.grounded = False
            
    def long_jump(self):
        if self.grounded and held_keys['shift']:
            # Check if moving forward
            if abs(self.velocity.x) > 2 or abs(self.velocity.z) > 2:
                self.velocity.y = self.jump_height * 0.6
                
                # Boost forward
                forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
                self.velocity += forward * 12
                
                self.long_jumping = True
                self.long_jump_timer = 0.6
                self.grounded = False
                self.jump_count = self.max_jumps

# Castle courtyard ground with checkered pattern
ground = Entity(
    model='plane',
    texture='white_cube',
    color=color.rgb(124, 252, 0),  # Bright green grass
    scale=(120, 1, 120),
    texture_scale=(60, 60)
)

# Courtyard stone path
path = Entity(
    model='cube',
    color=color.rgb(210, 180, 140),
    position=(0, 0.01, -5),
    scale=(8, 0.02, 30)
)

# Main Castle Base - Authentic peachy pink color
castle_base = Entity(
    model='cube',
    color=color.rgb(255, 192, 203),  # Princess Peach pink
    position=(0, 8, 25),
    scale=(35, 16, 25)
)

# Castle front detail
castle_front = Entity(
    model='cube',
    color=color.rgb(255, 182, 193),
    position=(0, 8, 12),
    scale=(20, 14, 2)
)

# Main entrance door frame
entrance_frame = Entity(
    model='cube',
    color=color.rgb(139, 90, 43),
    position=(0, 4, 11.5),
    scale=(6, 8, 0.5)
)

# Castle door (darker brown)
door = Entity(
    model='cube',
    color=color.rgb(101, 67, 33),
    position=(0, 3.5, 11),
    scale=(4, 7, 0.3)
)

# Iconic star on door
door_star = Entity(
    model='sphere',
    color=color.yellow,
    position=(0, 5, 10.8),
    scale=(1.5, 1.5, 0.3)
)

# Castle towers - Classic cylindrical design
left_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 192, 203),
    position=(-14, 11, 25),
    scale=(6, 12, 6)
)

right_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 192, 203),
    position=(14, 11, 25),
    scale=(6, 12, 6)
)

center_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 192, 203),
    position=(0, 18, 28),
    scale=(7, 16, 7)
)

# Red cone roofs - Iconic SM64 style
left_roof = Entity(
    model='cone',
    color=color.rgb(220, 20, 60),  # Crimson red
    position=(-14, 17, 25),
    scale=(8, 6, 8)
)

right_roof = Entity(
    model='cone',
    color=color.rgb(220, 20, 60),
    position=(14, 17, 25),
    scale=(8, 6, 8)
)

center_roof = Entity(
    model='cone',
    color=color.rgb(220, 20, 60),
    position=(0, 26, 28),
    scale=(9, 8, 9)
)

# Peach's stained glass window
stained_glass = Entity(
    model='cube',
    color=color.rgb(255, 182, 193),
    position=(0, 12, 11.4),
    scale=(10, 6, 0.2)
)

# Window frame
window_frame = Entity(
    model='cube',
    color=color.white,
    position=(0, 12, 11.3),
    scale=(10.5, 6.5, 0.1)
)

# Castle flags
flag_pole_left = Entity(
    model='cylinder',
    color=color.gray,
    position=(-14, 20, 25),
    scale=(0.1, 4, 0.1)
)

flag_left = Entity(
    model='cube',
    color=color.rgb(255, 0, 255),  # Magenta flag
    position=(-13.5, 21.5, 25),
    scale=(1.5, 1, 0.1)
)

flag_pole_right = Entity(
    model='cylinder',
    color=color.gray,
    position=(14, 20, 25),
    scale=(0.1, 4, 0.1)
)

flag_right = Entity(
    model='cube',
    color=color.rgb(255, 0, 255),
    position=(14.5, 21.5, 25),
    scale=(1.5, 1, 0.1)
)

# Bridge to castle with railings
bridge = Entity(
    model='cube',
    color=color.rgb(205, 133, 63),
    position=(0, 0.5, -2),
    scale=(8, 0.5, 25)
)

# Bridge railings
left_rail = Entity(
    model='cube',
    color=color.rgb(160, 82, 45),
    position=(-4, 1.5, -2),
    scale=(0.3, 2, 25)
)

right_rail = Entity(
    model='cube',
    color=color.rgb(160, 82, 45),
    position=(4, 1.5, -2),
    scale=(0.3, 2, 25)
)

# Moat water - Classic SM64 blue
moat_left = Entity(
    model='cube',
    color=color.rgb(0, 119, 190),
    position=(-16, -0.5, 15),
    scale=(20, 1, 50)
)

moat_right = Entity(
    model='cube',
    color=color.rgb(0, 119, 190),
    position=(16, -0.5, 15),
    scale=(20, 1, 50)
)

# Waterfall effect
waterfall_left = Entity(
    model='cube',
    color=color.rgb(173, 216, 230),
    position=(-16, 2, 35),
    scale=(8, 6, 0.5)
)

waterfall_right = Entity(
    model='cube',
    color=color.rgb(173, 216, 230),
    position=(16, 2, 35),
    scale=(8, 6, 0.5)
)

# Trees - Classic SM64 style
class Tree(Entity):
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            color=color.rgb(139, 69, 19),
            position=position,
            scale=(1.2, 5, 1.2)
        )
        
        # Three-sphere leaves for SM64 look
        self.leaves1 = Entity(
            model='sphere',
            color=color.rgb(0, 128, 0),
            position=position + Vec3(0, 5, 0),
            scale=4
        )
        
        self.leaves2 = Entity(
            model='sphere',
            color=color.rgb(0, 128, 0),
            position=position + Vec3(-1.5, 4, 0),
            scale=3
        )
        
        self.leaves3 = Entity(
            model='sphere',
            color=color.rgb(0, 128, 0),
            position=position + Vec3(1.5, 4, 0),
            scale=3
        )

# Place trees around courtyard
trees = [
    Tree(Vec3(-30, 2.5, -15)),
    Tree(Vec3(30, 2.5, -15)),
    Tree(Vec3(-35, 2.5, 0)),
    Tree(Vec3(35, 2.5, 0)),
    Tree(Vec3(-30, 2.5, 20)),
    Tree(Vec3(30, 2.5, 20)),
    Tree(Vec3(-25, 2.5, 35)),
    Tree(Vec3(25, 2.5, 35)),
]

# Coins - Classic yellow with red star
class Coin(Entity):
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            color=color.rgb(255, 223, 0),  # Gold color
            position=position,
            scale=(1, 0.15, 1),
            rotation=(90, 0, 0)
        )
        
        self.star = Entity(
            parent=self,
            model='cube',
            color=color.rgb(255, 0, 0),
            scale=(0.6, 0.6, 0.05),
            position=(0, 0, 0.08),
            rotation=(0, 45, 0)
        )
        
        self.rotation_speed = 120
        
    def update(self):
        self.rotation_z += self.rotation_speed * time.dt
        
        # Bobbing motion
        self.y = self.position[1] + math.sin(time.time * 2) * 0.1
        
        # Check collection
        if distance(self.position, mario.position) < 1.5:
            game.collect_coin()
            destroy(self.star)
            destroy(self)

# Place coins in classic formation
coins = []
# Circle of coins
for i in range(8):
    angle = (i / 8) * math.pi * 2
    x = math.cos(angle) * 8
    z = math.sin(angle) * 8
    coins.append(Coin(Vec3(x, 2, z - 10)))

# Line of coins on bridge
for i in range(5):
    coins.append(Coin(Vec3(0, 2, -10 + i * 3)))

# Red coins (worth more)
class RedCoin(Coin):
    def __init__(self, position):
        super().__init__(position)
        self.color = color.rgb(255, 0, 0)
        self.star.color = color.yellow
        self.value = 2

red_coins = [
    RedCoin(Vec3(-15, 3, -20)),
    RedCoin(Vec3(15, 3, -20)),
    RedCoin(Vec3(0, 3, -25)),
]

# Game manager
class GameManager:
    def __init__(self):
        self.coins = 0
        self.stars = 0
        self.power_stars_collected = []
        
        # UI - Classic SM64 style
        self.coin_counter_bg = Entity(
            parent=camera.ui,
            model='cube',
            color=color.rgba(0, 0, 0, 150),
            scale=(0.25, 0.08, 1),
            position=(-0.72, 0.45, 0)
        )
        
        self.coin_text = Text(
            f'x {self.coins:03d}',
            position=(-0.78, 0.45),
            scale=2.5,
            color=color.yellow,
            font='VeraMono.ttf'
        )
        
        self.coin_icon = Text(
            '©',  # Coin symbol
            position=(-0.85, 0.45),
            scale=3,
            color=color.yellow
        )
        
        self.star_counter_bg = Entity(
            parent=camera.ui,
            model='cube',
            color=color.rgba(0, 0, 0, 150),
            scale=(0.25, 0.08, 1),
            position=(-0.72, 0.35, 0)
        )
        
        self.star_text = Text(
            f'★ x {self.stars:03d}',
            position=(-0.82, 0.35),
            scale=2.5,
            color=color.white
        )
        
        self.controls_text = Text(
            'WASD: Move | SPACE: Jump | SHIFT: Run/Long Jump | Mouse: Camera',
            position=(0, -0.45),
            scale=1.5,
            color=color.white,
            origin=(0, 0)
        )
        
        self.title_text = Text(
            'SUPER MARIO 64',
            position=(0, 0.4),
            scale=4,
            color=color.rgb(255, 0, 0),
            origin=(0, 0)
        )
        
        # "Press Start" flashing text
        self.start_text = Text(
            'PRESS START',
            position=(0, 0.25),
            scale=2,
            color=color.white,
            origin=(0, 0)
        )
        
    def collect_coin(self, value=1):
        self.coins += value
        self.coin_text.text = f'x {self.coins:03d}'
        
        # 100 coins = 1 star (Classic SM64)
        if self.coins >= 100:
            self.coins -= 100
            self.stars += 1
            self.star_text.text = f'★ x {self.stars:03d}'
            self.coin_text.text = f'x {self.coins:03d}'
            
    def update(self):
        # Flashing start text
        self.start_text.color = color.white if int(time.time * 2) % 2 else color.rgba(255, 255, 255, 100)

# Initialize game
game = GameManager()

# Create Mario
mario = Mario()

# Third-person camera - Classic SM64 Lakitu cam
camera.position = (0, 10, -30)
camera.rotation_x = 15
camera.parent = None
camera.fov = 70

# Camera follow system
class CameraController:
    def __init__(self):
        self.distance = 18
        self.height = 10
        self.smoothing = 8
        self.rotation = 0
        self.vertical_angle = 15
        
    def update(self):
        # Mouse camera control (C-buttons style)
        if mouse.right:
            self.rotation -= mouse.velocity[0] * 150
            self.vertical_angle = clamp(self.vertical_angle - mouse.velocity[1] * 100, -30, 60)
            
        # Calculate target position
        angle = math.radians(self.rotation)
        target_x = mario.x + math.sin(angle) * self.distance
        target_z = mario.z - math.cos(angle) * self.distance
        target_y = mario.y + self.height
        
        # Smooth camera movement (Lakitu following)
        camera.position = lerp(
            camera.position,
            Vec3(target_x, target_y, target_z),
            time.dt * self.smoothing
        )
        
        # Look at Mario
        camera.look_at(mario.position + Vec3(0, 3, 0))
        camera.rotation_x = self.vertical_angle

cam_controller = CameraController()

def input(key):
    if key == 'space':
        if held_keys['shift']:
            mario.long_jump()
        else:
            mario.jump()

def update():
    mario.update()
    cam_controller.update()
    game.update()
    
    # Update coin animations
    for coin in coins:
        if coin:
            coin.update()
    for coin in red_coins:
        if coin:
            coin.update()

# Set target FPS
application.target_fps = 60

app.run()
