"""
Super Mario 64 Ursina Engine - Peach's Castle Recreation
Features: Courtyard, Indoor areas, Lakitu Camera System
Inspired by SM64 Spaceworld Demo
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math

app = Ursina()

# Configure window
window.title = 'Super Mario 64 - Peach\'s Castle'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Sky and lighting
Sky(color=color.rgb(135, 206, 235))
scene.fog_color = color.rgb(135, 206, 235)
scene.fog_density = 0.02
light = DirectionalLight()
light.look_at(Vec3(1, -1, -1))
ambient = AmbientLight(color=color.rgba(100, 100, 100, 0.5))

class LakituCamera(Entity):
    """Lakitu-style third-person camera that follows the player"""
    def __init__(self, target=None, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.offset = Vec3(0, 8, -12)
        self.rotation_speed = 100
        self.follow_speed = 4
        self.look_at_offset = Vec3(0, 2, 0)
        self.camera_pivot = Entity()
        camera.parent = self.camera_pivot
        camera.position = self.offset
        camera.rotation = (25, 0, 0)
        
    def update(self):
        if self.target:
            # Smooth camera follow
            target_pos = self.target.position + Vec3(0, 3, 0)
            self.camera_pivot.position = lerp(
                self.camera_pivot.position, 
                target_pos, 
                time.dt * self.follow_speed
            )
            
            # Camera rotation with mouse
            if held_keys['q']:
                self.camera_pivot.rotation_y -= self.rotation_speed * time.dt
            if held_keys['e']:
                self.camera_pivot.rotation_y += self.rotation_speed * time.dt
                
            # Look at player
            camera.look_at(self.target.position + self.look_at_offset)

class MarioController(Entity):
    """Simple Mario-style character controller"""
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.red,
            scale=(1, 2, 1),
            position=(0, 1, 0),
            **kwargs
        )
        self.speed = 8
        self.jump_height = 6
        self.gravity = 20
        self.grounded = False
        self.velocity = Vec3(0, 0, 0)
        self.collider = BoxCollider(self, size=(1, 2, 1))
        
        # Add Mario hat
        self.hat = Entity(
            parent=self,
            model='cube',
            color=color.red,
            scale=(1.2, 0.3, 1.2),
            position=(0, 0.6, 0)
        )
        
        # Add eyes
        self.eye1 = Entity(
            parent=self,
            model='sphere',
            color=color.black,
            scale=0.2,
            position=(0.25, 0.3, 0.5)
        )
        self.eye2 = Entity(
            parent=self,
            model='sphere',
            color=color.black,
            scale=0.2,
            position=(-0.25, 0.3, 0.5)
        )
        
    def update(self):
        # Movement input
        movement = Vec3(0, 0, 0)
        
        if held_keys['w'] or held_keys['up arrow']:
            movement.z += 1
        if held_keys['s'] or held_keys['down arrow']:
            movement.z -= 1
        if held_keys['a'] or held_keys['left arrow']:
            movement.x -= 1
        if held_keys['d'] or held_keys['right arrow']:
            movement.x += 1
            
        # Normalize and apply speed
        if movement.length() > 0:
            movement = movement.normalized() * self.speed
            
        # Apply camera-relative movement
        forward = Vec3(camera.forward.x, 0, camera.forward.z).normalized()
        right = Vec3(camera.right.x, 0, camera.right.z).normalized()
        
        self.velocity.x = (forward * movement.z + right * movement.x).x
        self.velocity.z = (forward * movement.z + right * movement.x).z
        
        # Jumping
        if self.grounded and held_keys['space']:
            self.velocity.y = self.jump_height
            
        # Gravity
        self.velocity.y -= self.gravity * time.dt
        
        # Apply velocity
        self.position += self.velocity * time.dt
        
        # Ground check
        hit_info = raycast(self.position, Vec3(0, -1, 0), distance=1.1, ignore=[self])
        if hit_info.hit:
            self.grounded = True
            self.velocity.y = max(0, self.velocity.y)
            self.y = hit_info.world_point.y + 1
        else:
            self.grounded = False
            
        # Keep player above ground
        if self.y < 0:
            self.y = 0
            self.velocity.y = 0
            self.grounded = True

class PeachsCastle:
    """Create Peach's Castle structure and courtyard"""
    def __init__(self):
        # Ground/Courtyard
        self.courtyard = Entity(
            model='cube',
            texture='grass',
            color=color.rgb(34, 139, 34),
            scale=(100, 1, 100),
            position=(0, -0.5, 0),
            collider='box',
            texture_scale=(20, 20)
        )
        
        # Castle base
        self.castle_base = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(30, 15, 25),
            position=(0, 7, 20),
            collider='box'
        )
        
        # Castle towers
        self.tower1 = Entity(
            model='cylinder',
            color=color.rgb(255, 228, 196),
            scale=(5, 20, 5),
            position=(-12, 10, 15),
            collider='box'
        )
        
        self.tower2 = Entity(
            model='cylinder',
            color=color.rgb(255, 228, 196),
            scale=(5, 20, 5),
            position=(12, 10, 15),
            collider='box'
        )
        
        # Tower roofs (cones)
        self.roof1 = Entity(
            model='cone',
            color=color.rgb(178, 34, 34),
            scale=(7, 5, 7),
            position=(-12, 21, 15)
        )
        
        self.roof2 = Entity(
            model='cone',
            color=color.rgb(178, 34, 34),
            scale=(7, 5, 7),
            position=(12, 21, 15)
        )
        
        # Main entrance
        self.entrance = Entity(
            model='cube',
            color=color.rgb(101, 67, 33),
            scale=(8, 10, 1),
            position=(0, 5, 7)
        )
        
        # Castle door
        self.door = Entity(
            model='cube',
            color=color.rgb(139, 69, 19),
            scale=(6, 8, 0.5),
            position=(0, 4, 6.5),
            collider='box'
        )
        
        # Stained glass window
        self.window = Entity(
            model='cube',
            color=color.rgba(255, 255, 0, 128),
            scale=(10, 10, 0.5),
            position=(0, 12, 7.5)
        )
        
        # Courtyard decorations
        self.create_courtyard_elements()
        
        # Indoor area
        self.create_indoor_area()
        
    def create_courtyard_elements(self):
        """Add trees, bushes, and paths to courtyard"""
        # Trees around courtyard
        tree_positions = [
            (-20, 0, -10), (20, 0, -10), 
            (-30, 0, 0), (30, 0, 0),
            (-25, 0, 15), (25, 0, 15)
        ]
        
        for pos in tree_positions:
            # Tree trunk
            trunk = Entity(
                model='cylinder',
                color=color.rgb(101, 67, 33),
                scale=(2, 6, 2),
                position=(pos[0], pos[1] + 3, pos[2]),
                collider='box'
            )
            
            # Tree leaves
            leaves = Entity(
                model='sphere',
                color=color.rgb(34, 139, 34),
                scale=(8, 8, 8),
                position=(pos[0], pos[1] + 8, pos[2])
            )
            
        # Path to castle
        self.path = Entity(
            model='cube',
            color=color.rgb(169, 169, 169),
            scale=(10, 0.1, 40),
            position=(0, 0.01, -10)
        )
        
        # Decorative bushes
        bush_positions = [
            (-8, 0, 2), (8, 0, 2),
            (-15, 0, -5), (15, 0, -5)
        ]
        
        for pos in bush_positions:
            bush = Entity(
                model='sphere',
                color=color.rgb(0, 100, 0),
                scale=(3, 2, 3),
                position=(pos[0], pos[1] + 1, pos[2])
            )
            
    def create_indoor_area(self):
        """Create simple indoor castle area"""
        # Floor
        self.indoor_floor = Entity(
            model='cube',
            color=color.rgb(139, 90, 43),
            scale=(25, 1, 20),
            position=(0, -0.5, 35),
            collider='box'
        )
        
        # Back wall
        self.back_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(25, 15, 1),
            position=(0, 7, 45),
            collider='box'
        )
        
        # Side walls
        self.left_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(1, 15, 20),
            position=(-12, 7, 35),
            collider='box'
        )
        
        self.right_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(1, 15, 20),
            position=(12, 7, 35),
            collider='box'
        )
        
        # Ceiling
        self.ceiling = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(25, 1, 20),
            position=(0, 15, 35),
            collider='box'
        )
        
        # Indoor decorations
        self.create_indoor_decorations()
        
    def create_indoor_decorations(self):
        """Add paintings and decorations inside"""
        # Paintings on walls
        painting_positions = [
            (-11.5, 7, 30), (-11.5, 7, 40),
            (11.5, 7, 30), (11.5, 7, 40)
        ]
        
        for i, pos in enumerate(painting_positions):
            painting = Entity(
                model='cube',
                color=color.random_color(),
                scale=(0.1, 3, 4) if i < 2 else (0.1, 3, 4),
                position=pos
            )
            
        # Chandelier
        self.chandelier = Entity(
            model='sphere',
            color=color.gold,
            scale=(3, 1, 3),
            position=(0, 12, 35)
        )
        
        # Red carpet
        self.carpet = Entity(
            model='cube',
            color=color.rgb(139, 0, 0),
            scale=(5, 0.1, 15),
            position=(0, 0.02, 35)
        )

# Create game world
castle = PeachsCastle()

# Create player
player = MarioController()

# Initialize Lakitu camera
lakitu_cam = LakituCamera(target=player)

# UI Instructions
instructions = Text(
    'WASD/Arrows: Move | Space: Jump | Q/E: Rotate Camera | ESC: Exit',
    position=(-0.9, 0.45),
    scale=1,
    background=True
)

title = Text(
    'Super Mario 64 - Peach\'s Castle',
    position=(-0.15, 0.48),
    scale=2,
    color=color.red
)

# Coins collectibles
class Coin(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            model='cylinder',
            color=color.gold,
            scale=(1, 0.1, 1),
            position=position,
            collider='box'
        )
        self.rotation_speed = 100
        
    def update(self):
        self.rotation_y += self.rotation_speed * time.dt
        
        # Check collection
        if distance(self.position, player.position) < 2:
            destroy(self)
            Audio('coin', autoplay=True, volume=0.5)

# Place coins around castle
coin_positions = [
    (5, 1, 0), (-5, 1, 0),
    (10, 1, -5), (-10, 1, -5),
    (0, 1, -15), (7, 1, 10),
    (-7, 1, 10)
]

coins = [Coin(position=pos) for pos in coin_positions]

# Game loop
def update():
    # Exit on escape
    if held_keys['escape']:
        application.quit()

# Run the game
app.run()
