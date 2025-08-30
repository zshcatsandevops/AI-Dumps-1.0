from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()

# Create a Mario-like character
class Mario(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = 'cube'
        self.color = color.red
        self.scale_y = 2
        self.speed = 6
        self.jump_height = 0.3
        self.jump_duration = 0.3
        
    def input(self, key):
        super().input(key)
        if key == 'q':
            # Check if Mario is near any door
            for door in doors:
                if distance(self.position, door.position) < 5:
                    print("Mario is entering the castle!")
                    # Add your level loading logic here

# Create the ground
ground = Entity(
    model='plane',
    texture='grass',
    texture_scale=(10, 10),
    scale=(100, 1, 100),
    collider='box'
)

# Create Peach's Castle
castle = Entity(
    model='cube',
    texture='brick',
    scale=(20, 15, 20),
    position=(0, 7.5, 0),
    collider='box'
)

# Create castle roof
roof = Entity(
    model='cone',
    color=color.red,
    scale=(22, 10, 22),
    position=(0, 17, 0),
    rotation=(0, 0, 180)
)

# Create castle towers
tower1 = Entity(
    model='cylinder',
    texture='brick',
    scale=(4, 20, 4),
    position=(-12, 10, -12)
)

tower2 = Entity(
    model='cylinder',
    texture='brick',
    scale=(4, 20, 4),
    position=(12, 10, -12)
)

tower3 = Entity(
    model='cylinder',
    texture='brick',
    scale=(4, 20, 4),
    position=(-12, 10, 12)
)

tower4 = Entity(
    model='cylinder',
    texture='brick',
    scale=(4, 20, 4),
    position=(12, 10, 12)
)

# Create tower roofs
tower_roof1 = Entity(
    model='cone',
    color=color.red,
    scale=(5, 5, 5),
    position=(-12, 20, -12),
    rotation=(0, 0, 180)
)

tower_roof2 = Entity(
    model='cone',
    color=color.red,
    scale=(5, 5, 5),
    position=(12, 20, -12),
    rotation=(0, 0, 180)
)

tower_roof3 = Entity(
    model='cone',
    color=color.red,
    scale=(5, 5, 5),
    position=(-12, 20, 12),
    rotation=(0, 0, 180)
)

tower_roof4 = Entity(
    model='cone',
    color=color.red,
    scale=(5, 5, 5),
    position=(12, 20, 12),
    rotation=(0, 0, 180)
)

# Create doors
doors = []
door_positions = [
    (0, 0, 10),  # Front door
    (0, 0, -10), # Back door
    (10, 0, 0),  # Right door
    (-10, 0, 0)  # Left door
]

for pos in door_positions:
    door = Entity(
        model='cube',
        color=color.brown,
        scale=(3, 5, 0.2),
        position=pos,
        collider='box'
    )
    doors.append(door)

# Create Mario
mario = Mario()
mario.position = (0, 2, -20)
mario.rotation = (0, 0, 0)

# Create sky
sky = Sky()

# Create instructions text
instructions = Text(
    text="Super Mario 64 Tech Demo\nUse WASD to move, Space to jump\nPress Q near doors to enter",
    position=(-0.8, 0.4),
    scale=1.5
)

# Update function to check for door proximity
def update():
    for door in doors:
        if distance(mario.position, door.position) < 5:
            door.color = color.yellow  # Highlight door when near
        else:
            door.color = color.brown  # Reset door color

app.run()
