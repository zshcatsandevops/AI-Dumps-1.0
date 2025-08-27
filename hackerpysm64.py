from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math

# Initialize Ursina
app = Ursina()
window.title = 'Super Mario 64 - Peach\'s Castle'
window.borderless = False
window.fullscreen = False
window.fps_counter.enabled = True
window.vsync = True

# Sky and lighting
Sky(color=color.rgb(135, 206, 235))
DirectionalLight(y=10, x=3, z=-5, shadows=True)
AmbientLight(color=color.rgba(100, 100, 120, 255))

# Mario character class with full 3D movement
class Mario(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.red,
            scale=(0.8, 1.6, 0.8),
            position=(0, 1, -15)
        )
        
        # Mario parts for visual
        self.head = Entity(
            parent=self,
            model='sphere',
            color=color.rgb(255, 220, 177),
            scale=(0.8, 0.5, 0.8),
            position=(0, 0.6, 0)
        )
        
        self.cap = Entity(
            parent=self.head,
            model='sphere',
            color=color.red,
            scale=(1.1, 0.6, 1.1),
            position=(0, 0.2, 0)
        )
        
        self.mustache = Entity(
            parent=self.head,
            model='cube',
            color=color.black,
            scale=(0.6, 0.1, 0.2),
            position=(0, -0.1, 0.4)
        )
        
        # Movement properties
        self.velocity = Vec3(0, 0, 0)
        self.grounded = False
        self.jump_count = 0
        self.max_jumps = 3  # Triple jump!
        self.movement_speed = 5
        self.jump_height = 8
        self.gravity = 20
        self.air_control = 0.3
        
        # Long jump properties
        self.long_jumping = False
        self.long_jump_timer = 0
        
        # Animation properties
        self.bob_timer = 0
        self.original_y = 1
        
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
        
        if movement.length() > 0:
            movement = movement.normalized()
            
            # Face movement direction
            if not self.long_jumping:
                look_at = self.position + movement
                self.look_at(Vec3(look_at.x, self.y, look_at.z))
            
        # Apply movement
        if self.grounded:
            self.velocity.x = movement.x * self.movement_speed
            self.velocity.z = movement.z * self.movement_speed
        else:
            # Air control
            self.velocity.x += movement.x * self.movement_speed * self.air_control * time.dt
            self.velocity.z += movement.z * self.movement_speed * self.air_control * time.dt
            
            # Limit air speed
            horizontal_speed = Vec2(self.velocity.x, self.velocity.z).length()
            if horizontal_speed > self.movement_speed * 1.5:
                self.velocity.x = (self.velocity.x / horizontal_speed) * self.movement_speed * 1.5
                self.velocity.z = (self.velocity.z / horizontal_speed) * self.movement_speed * 1.5
        
        # Long jump
        if self.long_jumping:
            self.long_jump_timer -= time.dt
            if self.long_jump_timer <= 0:
                self.long_jumping = False
                
        # Apply gravity
        self.velocity.y -= self.gravity * time.dt
        
        # Apply velocity
        self.position += self.velocity * time.dt
        
        # Ground detection
        if self.y <= 1:
            self.y = 1
            self.velocity.y = 0
            if not self.grounded:
                self.grounded = True
                self.jump_count = 0
                self.long_jumping = False
        else:
            self.grounded = False
            
        # Walking animation
        if self.grounded and movement.length() > 0:
            self.bob_timer += time.dt * 10
            self.head.y = 0.6 + math.sin(self.bob_timer) * 0.05
        else:
            self.bob_timer = 0
            self.head.y = 0.6
            
        # Rotation animation when jumping
        if not self.grounded and not self.long_jumping:
            self.rotation_x += 360 * time.dt
        else:
            self.rotation_x = lerp(self.rotation_x, 0, time.dt * 10)
            
    def jump(self):
        if self.grounded or self.jump_count < self.max_jumps:
            if self.jump_count == 0:
                # Regular jump
                self.velocity.y = self.jump_height
            elif self.jump_count == 1:
                # Double jump
                self.velocity.y = self.jump_height * 1.2
            elif self.jump_count == 2:
                # Triple jump - highest!
                self.velocity.y = self.jump_height * 1.5
                
            self.jump_count += 1
            self.grounded = False
            
    def long_jump(self):
        if self.grounded and held_keys['shift'] and self.velocity.length() > 2:
            self.velocity.y = self.jump_height * 0.7
            
            # Boost forward
            forward = Vec3(self.forward.x, 0, self.forward.z).normalized()
            self.velocity += forward * 8
            
            self.long_jumping = True
            self.long_jump_timer = 0.5
            self.grounded = False
            self.jump_count = self.max_jumps  # Can't jump during long jump

# Castle courtyard ground
ground = Entity(
    model='plane',
    texture='white_cube',
    color=color.rgb(34, 139, 34),
    scale=(100, 1, 100),
    texture_scale=(50, 50)
)

# Peach's Castle main structure
castle_base = Entity(
    model='cube',
    color=color.rgb(255, 218, 185),
    position=(0, 7, 20),
    scale=(30, 14, 20)
)

# Castle towers
left_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 200, 160),
    position=(-12, 10, 20),
    scale=(5, 10, 5)
)

right_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 200, 160),
    position=(12, 10, 20),
    scale=(5, 10, 5)
)

center_tower = Entity(
    model='cylinder',
    color=color.rgb(255, 200, 160),
    position=(0, 15, 20),
    scale=(6, 12, 6)
)

# Tower roofs (cone shapes)
left_roof = Entity(
    model='cone',
    color=color.red,
    position=(-12, 15, 20),
    scale=(7, 5, 7)
)

right_roof = Entity(
    model='cone',
    color=color.red,
    position=(12, 15, 20),
    scale=(7, 5, 7)
)

center_roof = Entity(
    model='cone',
    color=color.red,
    position=(0, 21, 20),
    scale=(8, 6, 8)
)

# Castle entrance
entrance = Entity(
    model='cube',
    color=color.rgb(139, 69, 19),
    position=(0, 3, 9),
    scale=(8, 6, 1)
)

# Bridge to castle
bridge = Entity(
    model='cube',
    color=color.rgb(160, 82, 45),
    position=(0, 0.5, 0),
    scale=(6, 0.5, 20)
)

# Moat around castle
moat_left = Entity(
    model='cube',
    color=color.rgb(64, 164, 223),
    position=(-15, -0.5, 10),
    scale=(18, 1, 40)
)

moat_right = Entity(
    model='cube',
    color=color.rgb(64, 164, 223),
    position=(15, -0.5, 10),
    scale=(18, 1, 40)
)

# Trees around courtyard
class Tree(Entity):
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            color=color.rgb(101, 67, 33),
            position=position,
            scale=(1, 4, 1)
        )
        
        self.leaves = Entity(
            model='sphere',
            color=color.rgb(34, 139, 34),
            position=position + Vec3(0, 4, 0),
            scale=5
        )

# Place trees
trees = [
    Tree(Vec3(-25, 2, -10)),
    Tree(Vec3(25, 2, -10)),
    Tree(Vec3(-30, 2, 5)),
    Tree(Vec3(30, 2, 5)),
    Tree(Vec3(-25, 2, 25)),
    Tree(Vec3(25, 2, 25)),
]

# Coins to collect
class Coin(Entity):
    def __init__(self, position):
        super().__init__(
            model='cylinder',
            color=color.yellow,
            position=position,
            scale=(0.8, 0.1, 0.8),
            rotation=(90, 0, 0)
        )
        self.rotation_speed = 100
        
    def update(self):
        self.rotation_z += self.rotation_speed * time.dt
        
        # Check collection
        if distance(self.position, mario.position) < 1.5:
            game.collect_coin()
            destroy(self)

# Place coins
coins = [
    Coin(Vec3(5, 2, 0)),
    Coin(Vec3(-5, 2, 0)),
    Coin(Vec3(0, 2, 5)),
    Coin(Vec3(0, 2, -5)),
    Coin(Vec3(10, 2, 10)),
    Coin(Vec3(-10, 2, 10)),
]

# Game manager
class GameManager:
    def __init__(self):
        self.coins = 0
        self.stars = 0
        
        # UI
        self.coin_text = Text(
            f'Coins: {self.coins}',
            position=(-0.85, 0.45),
            scale=2,
            color=color.yellow
        )
        
        self.star_text = Text(
            f'Stars: {self.stars}/120',
            position=(-0.85, 0.38),
            scale=2,
            color=color.white
        )
        
        self.controls_text = Text(
            'CONTROLS:\nWASD: Move\nSpace: Jump (Triple Jump!)\nShift+Space: Long Jump\nMouse: Camera',
            position=(0.4, 0.4),
            scale=1.2,
            color=color.white
        )
        
        self.title_text = Text(
            'SUPER MARIO 64\nPeach\'s Castle',
            position=(0, 0.3),
            scale=3,
            color=color.red,
            origin=(0, 0)
        )
        
    def collect_coin(self):
        self.coins += 1
        self.coin_text.text = f'Coins: {self.coins}'
        
        if self.coins >= 100:
            self.coins = 0
            self.stars += 1
            self.star_text.text = f'Stars: {self.stars}/120'
            self.coin_text.text = f'Coins: {self.coins}'

# Initialize game
game = GameManager()

# Create Mario
mario = Mario()

# Third-person camera
camera.position = (0, 8, -25)
camera.rotation_x = 20
camera.parent = None

# Camera follow system
class CameraController:
    def __init__(self):
        self.distance = 15
        self.height = 8
        self.smoothing = 5
        self.rotation = 0
        
    def update(self):
        # Mouse camera control
        if mouse.right:
            self.rotation -= mouse.velocity[0] * 100
            
        # Calculate target position
        angle = math.radians(self.rotation)
        target_x = mario.x + math.sin(angle) * self.distance
        target_z = mario.z - math.cos(angle) * self.distance
        target_y = mario.y + self.height
        
        # Smooth camera movement
        camera.position = lerp(
            camera.position,
            Vec3(target_x, target_y, target_z),
            time.dt * self.smoothing
        )
        
        # Look at Mario
        camera.look_at(mario.position + Vec3(0, 2, 0))

cam_controller = CameraController()

def input(key):
    if key == 'space':
        mario.jump()
    elif key == 'space' and held_keys['shift']:
        mario.long_jump()

def update():
    mario.update()
    cam_controller.update()

app.run()
