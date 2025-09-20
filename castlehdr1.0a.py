"""
Super Mario 64 - Inner Peach's Castle Recreation
Features: Main Lobby, Painting Rooms, Multiple Floors, Grand Staircase
Complete interior castle exploration
"""

from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math

app = Ursina()

# Configure window
window.title = 'Super Mario 64 - Inner Peach\'s Castle'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Sky and lighting
Sky(color=color.rgb(135, 206, 235))
light = DirectionalLight()
light.look_at(Vec3(1, -1, -1))
ambient = AmbientLight(color=color.rgba(150, 150, 150, 0.6))

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
            target_pos = self.target.position + Vec3(0, 3, 0)
            self.camera_pivot.position = lerp(
                self.camera_pivot.position, 
                target_pos, 
                time.dt * self.follow_speed
            )
            
            if held_keys['q']:
                self.camera_pivot.rotation_y -= self.rotation_speed * time.dt
            if held_keys['e']:
                self.camera_pivot.rotation_y += self.rotation_speed * time.dt
                
            camera.look_at(self.target.position + self.look_at_offset)

class MarioController(Entity):
    """Mario-style character controller with enhanced movement"""
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.red,
            scale=(1, 2, 1),
            position=(0, 1, 0),
            **kwargs
        )
        self.speed = 8
        self.jump_height = 8
        self.gravity = 20
        self.grounded = False
        self.velocity = Vec3(0, 0, 0)
        self.collider = BoxCollider(self, size=(1, 2, 1))
        
        # Mario appearance
        self.hat = Entity(
            parent=self,
            model='cube',
            color=color.red,
            scale=(1.2, 0.3, 1.2),
            position=(0, 0.6, 0)
        )
        
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
        movement = Vec3(0, 0, 0)
        
        if held_keys['w'] or held_keys['up arrow']:
            movement.z += 1
        if held_keys['s'] or held_keys['down arrow']:
            movement.z -= 1
        if held_keys['a'] or held_keys['left arrow']:
            movement.x -= 1
        if held_keys['d'] or held_keys['right arrow']:
            movement.x += 1
            
        if movement.length() > 0:
            movement = movement.normalized() * self.speed
            
        forward = Vec3(camera.forward.x, 0, camera.forward.z).normalized()
        right = Vec3(camera.right.x, 0, camera.right.z).normalized()
        
        self.velocity.x = (forward * movement.z + right * movement.x).x
        self.velocity.z = (forward * movement.z + right * movement.x).z
        
        if self.grounded and held_keys['space']:
            self.velocity.y = self.jump_height
            
        self.velocity.y -= self.gravity * time.dt
        self.position += self.velocity * time.dt
        
        hit_info = raycast(self.position, Vec3(0, -1, 0), distance=1.1, ignore=[self])
        if hit_info.hit:
            self.grounded = True
            self.velocity.y = max(0, self.velocity.y)
            self.y = hit_info.world_point.y + 1
        else:
            self.grounded = False
            
        if self.y < 0:
            self.y = 0
            self.velocity.y = 0
            self.grounded = True

class InnerPeachesCastle:
    """Complete inner castle structure with multiple rooms and floors"""
    def __init__(self):
        self.create_main_lobby()
        self.create_first_floor_rooms()
        self.create_second_floor()
        self.create_basement()
        self.create_courtyard_door()
        self.create_star_doors()
        
    def create_main_lobby(self):
        """Create the iconic main lobby with checkered floor"""
        # Main lobby floor (checkered pattern)
        for x in range(-15, 16, 3):
            for z in range(-20, 21, 3):
                color_tile = color.white if (x + z) % 6 == 0 else color.black
                tile = Entity(
                    model='cube',
                    color=color_tile,
                    scale=(3, 0.1, 3),
                    position=(x, 0, z),
                    collider='box'
                )
        
        # Lobby walls
        # Front wall with entrance
        self.front_wall_left = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(7, 20, 2),
            position=(-11, 10, -20),
            collider='box'
        )
        
        self.front_wall_right = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(7, 20, 2),
            position=(11, 10, -20),
            collider='box'
        )
        
        self.front_wall_top = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(8, 10, 2),
            position=(0, 15, -20),
            collider='box'
        )
        
        # Back wall
        self.back_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(30, 20, 2),
            position=(0, 10, 20),
            collider='box'
        )
        
        # Side walls
        self.left_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(2, 20, 40),
            position=(-15, 10, 0),
            collider='box'
        )
        
        self.right_wall = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(2, 20, 40),
            position=(15, 10, 0),
            collider='box'
        )
        
        # Ceiling with skylight
        self.ceiling = Entity(
            model='cube',
            color=color.rgb(255, 228, 196),
            scale=(30, 1, 40),
            position=(0, 20, 0),
            collider='box'
        )
        
        # Central skylight
        self.skylight = Entity(
            model='cube',
            color=color.rgba(135, 206, 250, 100),
            scale=(8, 0.5, 8),
            position=(0, 19.8, 0)
        )
        
        # Grand staircase
        self.create_grand_staircase()
        
        # Sun carpet in center
        self.sun_carpet = Entity(
            model='cylinder',
            color=color.rgb(255, 215, 0),
            scale=(8, 0.02, 8),
            position=(0, 0.05, 0),
            rotation=(90, 0, 0)
        )
        
        # Pillars
        pillar_positions = [
            (-10, 0, -10), (10, 0, -10),
            (-10, 0, 10), (10, 0, 10)
        ]
        
        for pos in pillar_positions:
            pillar = Entity(
                model='cylinder',
                color=color.rgb(255, 228, 196),
                scale=(2, 15, 2),
                position=(pos[0], pos[1] + 7.5, pos[2]),
                collider='box'
            )
            
    def create_grand_staircase(self):
        """Create the iconic grand staircase"""
        # Main staircase steps
        for i in range(10):
            step = Entity(
                model='cube',
                color=color.rgb(139, 69, 19),
                scale=(8, 0.5, 2),
                position=(0, i * 0.5 + 0.25, 10 + i * 1.5),
                collider='box'
            )
            
        # Staircase railings
        self.left_railing = Entity(
            model='cube',
            color=color.rgb(101, 67, 33),
            scale=(0.5, 8, 15),
            position=(-4, 4, 15),
            rotation=(25, 0, 0)
        )
        
        self.right_railing = Entity(
            model='cube',
            color=color.rgb(101, 67, 33),
            scale=(0.5, 8, 15),
            position=(4, 4, 15),
            rotation=(25, 0, 0)
        )
        
    def create_first_floor_rooms(self):
        """Create painting rooms on first floor"""
        # Bob-omb Battlefield room (left)
        self.bob_omb_room_floor = Entity(
            model='cube',
            color=color.rgb(139, 90, 43),
            scale=(15, 0.1, 15),
            position=(-25, 0, 0),
            collider='box'
        )
        
        self.bob_omb_room_walls = [
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(15, 15, 1), position=(-25, 7.5, -7.5), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(15, 15, 1), position=(-25, 7.5, 7.5), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(1, 15, 15), position=(-32.5, 7.5, 0), collider='box')
        ]
        
        # Bob-omb painting
        self.bob_omb_painting = Entity(
            model='cube',
            color=color.rgb(34, 139, 34),
            scale=(6, 8, 0.2),
            position=(-32.3, 7, 0)
        )
        
        # Whomp's Fortress room (right)
        self.whomp_room_floor = Entity(
            model='cube',
            color=color.rgb(139, 90, 43),
            scale=(15, 0.1, 15),
            position=(25, 0, 0),
            collider='box'
        )
        
        self.whomp_room_walls = [
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(15, 15, 1), position=(25, 7.5, -7.5), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(15, 15, 1), position=(25, 7.5, 7.5), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(1, 15, 15), position=(32.5, 7.5, 0), collider='box')
        ]
        
        # Whomp painting
        self.whomp_painting = Entity(
            model='cube',
            color=color.rgb(169, 169, 169),
            scale=(6, 8, 0.2),
            position=(32.3, 7, 0)
        )
        
        # Princess's Secret Slide room (back)
        self.secret_room_floor = Entity(
            model='cube',
            color=color.rgb(255, 192, 203),
            scale=(10, 0.1, 10),
            position=(0, 0, 35),
            collider='box'
        )
        
        self.secret_room_walls = [
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(10, 15, 1), position=(0, 7.5, 40), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(1, 15, 10), position=(-5, 7.5, 35), collider='box'),
            Entity(model='cube', color=color.rgb(255, 228, 196), 
                   scale=(1, 15, 10), position=(5, 7.5, 35), collider='box')
        ]
        
        # Princess window/painting
        self.princess_window = Entity(
            model='cube',
            color=color.rgba(255, 192, 203, 200),
            scale=(6, 8, 0.2),
            position=(0, 10, 39.8)
        )
        
    def create_second_floor(self):
        """Create second floor with more painting rooms"""
        # Second floor platform
        self.second_floor = Entity(
            model='cube',
            color=color.rgb(139, 90, 43),
            scale=(20, 0.5, 20),
            position=(0, 10, 15),
            collider='box'
        )
        
        # Second floor railings
        railing_positions = [
            (10, 11, 15), (-10, 11, 15),
            (0, 11, 5), (0, 11, 25)
        ]
        
        for i, pos in enumerate(railing_positions):
            scale_val = (0.5, 2, 20) if i < 2 else (20, 2, 0.5)
            railing = Entity(
                model='cube',
                color=color.rgb(101, 67, 33),
                scale=scale_val,
                position=pos
            )
            
        # Cool Cool Mountain room
        self.ccm_room_floor = Entity(
            model='cube',
            color=color.rgb(173, 216, 230),
            scale=(12, 0.1, 12),
            position=(0, 10, 35),
            collider='box'
        )
        
        self.ccm_painting = Entity(
            model='cube',
            color=color.rgb(240, 248, 255),
            scale=(5, 7, 0.2),
            position=(0, 15, 40.8)
        )
        
        # Jolly Roger Bay indicator
        self.jrb_painting = Entity(
            model='cube',
            color=color.rgb(0, 119, 190),
            scale=(5, 7, 0.2),
            position=(-12, 15, 15)
        )
        
    def create_basement(self):
        """Create basement area with metal cap and Bowser door"""
        # Basement floor
        self.basement_floor = Entity(
            model='cube',
            color=color.rgb(105, 105, 105),
            scale=(30, 0.1, 30),
            position=(0, -10, 0),
            collider='box'
        )
        
        # Basement walls
        self.basement_walls = [
            Entity(model='cube', color=color.rgb(128, 128, 128), 
                   scale=(30, 15, 1), position=(0, -2.5, -15), collider='box'),
            Entity(model='cube', color=color.rgb(128, 128, 128), 
                   scale=(30, 15, 1), position=(0, -2.5, 15), collider='box'),
            Entity(model='cube', color=color.rgb(128, 128, 128), 
                   scale=(1, 15, 30), position=(-15, -2.5, 0), collider='box'),
            Entity(model='cube', color=color.rgb(128, 128, 128), 
                   scale=(1, 15, 30), position=(15, -2.5, 0), collider='box')
        ]
        
        # Stairs to basement
        for i in range(8):
            step = Entity(
                model='cube',
                color=color.rgb(105, 105, 105),
                scale=(6, 0.5, 2),
                position=(-10, -i * 1.2 - 0.5, -10 - i * 1.5),
                collider='box'
            )
            
        # Bowser door
        self.bowser_door = Entity(
            model='cube',
            color=color.rgb(139, 0, 0),
            scale=(8, 10, 1),
            position=(0, -5, 14.5),
            collider='box'
        )
        
        # Star emblem on door
        self.star_emblem = Entity(
            parent=self.bowser_door,
            model='sphere',
            color=color.gold,
            scale=(2, 2, 0.1),
            position=(0, 2, -0.6)
        )
        
    def create_courtyard_door(self):
        """Create back door to courtyard"""
        self.courtyard_door = Entity(
            model='cube',
            color=color.rgb(139, 69, 19),
            scale=(6, 9, 0.5),
            position=(0, 4.5, 19.5),
            collider='box'
        )
        
        # Door handle
        self.door_handle = Entity(
            parent=self.courtyard_door,
            model='sphere',
            color=color.gold,
            scale=(0.5, 0.5, 0.3),
            position=(2, 0, -0.3)
        )
        
    def create_star_doors(self):
        """Create star requirement doors"""
        # 1 star door
        self.star_door_1 = Entity(
            model='cube',
            color=color.rgb(255, 215, 0),
            scale=(0.5, 8, 6),
            position=(-14.5, 4, 0),
            collider='box'
        )
        
        # 3 star door  
        self.star_door_3 = Entity(
            model='cube',
            color=color.rgb(255, 215, 0),
            scale=(0.5, 8, 6),
            position=(14.5, 4, 0),
            collider='box'
        )
        
        # 8 star door (upstairs)
        self.star_door_8 = Entity(
            model='cube',
            color=color.rgb(255, 215, 0),
            scale=(6, 8, 0.5),
            position=(0, 14, 24.5),
            collider='box'
        )

class Painting(Entity):
    """Interactive painting that wobbles when approached"""
    def __init__(self, position=(0, 0, 0), painting_color=color.green, **kwargs):
        super().__init__(
            model='cube',
            color=painting_color,
            scale=(6, 8, 0.3),
            position=position,
            **kwargs
        )
        self.wobble_amount = 0
        self.wobble_speed = 5
        
        # Add frame
        self.frame = Entity(
            parent=self,
            model='cube',
            color=color.rgb(139, 69, 19),
            scale=(1.2, 1.1, 0.8),
            position=(0, 0, 0.1)
        )
        
    def update(self):
        # Wobble when player is near
        if distance(self.position, player.position) < 5:
            self.wobble_amount = min(self.wobble_amount + time.dt, 1)
        else:
            self.wobble_amount = max(self.wobble_amount - time.dt, 0)
            
        if self.wobble_amount > 0:
            self.rotation_z = math.sin(time.time() * self.wobble_speed) * 5 * self.wobble_amount
            self.scale_x = 6 + math.sin(time.time() * self.wobble_speed * 1.5) * 0.2 * self.wobble_amount

class PowerStar(Entity):
    """Collectible power star"""
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            model='sphere',
            color=color.gold,
            scale=1.5,
            position=position
        )
        self.rotation_speed = 100
        self.float_speed = 2
        self.float_height = 0.5
        self.start_y = position[1]
        
    def update(self):
        self.rotation_y += self.rotation_speed * time.dt
        self.y = self.start_y + math.sin(time.time() * self.float_speed) * self.float_height
        
        # Sparkle effect
        self.color = color.rgb(
            255,
            215 + math.sin(time.time() * 10) * 40,
            0
        )
        
        # Collection
        if distance(self.position, player.position) < 2:
            Text('STAR GET!', position=(0, 0.4), scale=3, color=color.gold, origin=(0, 0))
            destroy(self)

class Toad(Entity):
    """Toad NPC"""
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            model='cube',
            color=color.white,
            scale=(0.8, 1.5, 0.8),
            position=position,
            collider='box'
        )
        
        # Mushroom cap
        self.cap = Entity(
            parent=self,
            model='sphere',
            color=color.rgb(255, 0, 0),
            scale=(1.5, 0.8, 1.5),
            position=(0, 0.5, 0)
        )
        
        # Spots on cap
        for i in range(3):
            spot = Entity(
                parent=self.cap,
                model='sphere',
                color=color.white,
                scale=0.2,
                position=(
                    math.cos(i * 2.09) * 0.4,
                    0.2,
                    math.sin(i * 2.09) * 0.4
                )
            )
            
    def update(self):
        # Face player
        self.look_at_2d(player.position, 'y')
        
        # Show message when near
        if distance(self.position, player.position) < 3:
            if not hasattr(self, 'message'):
                self.message = Text(
                    'Welcome to Peach\'s Castle!',
                    position=(0, -0.3),
                    scale=2,
                    background=True,
                    origin=(0, 0)
                )
        elif hasattr(self, 'message'):
            destroy(self.message)
            del self.message

# Create castle
castle = InnerPeachesCastle()

# Add interactive paintings
paintings = [
    Painting(position=(-32.3, 7, 0), painting_color=color.green),
    Painting(position=(32.3, 7, 0), painting_color=color.gray),
    Painting(position=(0, 15, 40.8), painting_color=color.cyan),
    Painting(position=(-12, 15, 14.5), painting_color=color.blue)
]

# Place Toads
toads = [
    Toad(position=(5, 1, -15)),
    Toad(position=(-5, 1, -15)),
    Toad(position=(0, 11, 10))
]

# Place Power Stars
stars = [
    PowerStar(position=(0, 2, 0)),
    PowerStar(position=(-25, 2, 0)),
    PowerStar(position=(25, 2, 0)),
    PowerStar(position=(0, 12, 35)),
    PowerStar(position=(0, -8, 0))
]

# Create player
player = MarioController()
player.position = (0, 1, -15)  # Start at entrance

# Initialize camera
lakitu_cam = LakituCamera(target=player)

# UI
instructions = Text(
    'WASD/Arrows: Move | Space: Jump | Q/E: Rotate Camera | ESC: Exit',
    position=(-0.9, 0.45),
    scale=1,
    background=True
)

title = Text(
    'Inner Peach\'s Castle',
    position=(-0.1, 0.48),
    scale=2,
    color=color.red
)

# Star counter
star_count = 0
star_counter = Text(
    f'Stars: {star_count}/120',
    position=(0.7, 0.45),
    scale=2,
    color=color.gold
)

# Music note decorations
class MusicNote(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            model='sphere',
            color=color.rgb(255, 0, 255),
            scale=0.5,
            position=position
        )
        self.float_speed = random.uniform(1, 3)
        self.start_y = position[1]
        
    def update(self):
        self.y += time.dt * self.float_speed
        if self.y > self.start_y + 10:
            self.y = self.start_y

# Add ambient music notes
for i in range(5):
    note = MusicNote(
        position=(
            random.uniform(-10, 10),
            random.uniform(1, 5),
            random.uniform(-10, 10)
        )
    )

def update():
    if held_keys['escape']:
        application.quit()
        
    # Update star counter
    global star_count
    current_stars = 120 - len([s for s in stars if s])
    if current_stars != star_count:
        star_count = current_stars
        star_counter.text = f'Stars: {star_count}/120'

# Run the game
app.run()
