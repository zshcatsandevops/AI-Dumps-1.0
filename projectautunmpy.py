from ursina import *

app = Ursina(title='Project Autumn 9X Fan Game Demo')

# Player setup - simple third-person Mario-like character using cube
class Player(Entity):
    def __init__(self):
        super().__init__(
            model='cube',
            color=color.orange,  # Mario-like color
            scale=(1, 2, 1),
            position=(0, 1, 0),
            collider='box'
        )
        self.speed = 5
        self.jump_height = 8
        self.gravity = 1
        self.y_velocity = 0
        self.grounded = False
        camera.position = (0, 5, -15)  # Third-person view
        camera.look_at(self)

    def update(self):
        # Movement
        self.x += held_keys['d'] * time.dt * self.speed - held_keys['a'] * time.dt * self.speed
        self.z += held_keys['w'] * time.dt * self.speed - held_keys['s'] * time.dt * self.speed

        # Gravity and jumping
        ray = raycast(self.world_position, self.down, ignore=(self,), distance=0.1)
        if ray.hit:
            self.grounded = True
            self.y_velocity = 0
        else:
            self.grounded = False
            self.y_velocity -= self.gravity * time.dt

        if held_keys['space'] and self.grounded:
            self.y_velocity = self.jump_height

        self.y += self.y_velocity * time.dt

        # Camera follow
        camera.position = lerp(camera.position, (self.x, self.y + 5, self.z - 15), time.dt * 5)
        camera.look_at(self)

# Ground - large plane, beta-inspired dull color
ground = Entity(
    model='plane',
    scale=100,
    color=color.gray,
    collider='mesh'
)

# Platforms - simple beta-like structures with dull colors
platform1 = Entity(
    model='cube',
    scale=(10, 1, 10),
    position=(10, 3, 0),
    color=color.dark_gray,
    collider='box'
)

platform2 = Entity(
    model='cube',
    scale=(5, 1, 5),
    position=(20, 6, 5),
    color=color.light_gray,
    collider='box'
)

# Stars - collectibles, yellow spheres, inspired by SM64 stars
class Star(Entity):
    def __init__(self, position):
        super().__init__(
            model='sphere',
            color=color.yellow,
            scale=1,
            position=position,
            collider='box'
        )

    def update(self):
        self.rotation_y += time.dt * 100  # Rotating like SM64 stars

stars = [
    Star(position=(5, 2, 0)),
    Star(position=(15, 4, 0)),
    Star(position=(25, 7, 5)),
    Star(position=(-10, 5, -10))  # Hidden-ish
]

# Collect star logic
def update():
    for star in stars[:]:
        if player.intersects(star).hit:
            destroy(star)
            stars.remove(star)
            print('Star collected!')  # Simple feedback

# Beta-inspired elements: add some eerie empty space and simple enemies (red cubes)
class Enemy(Entity):
    def __init__(self, position):
        super().__init__(
            model='cube',
            color=color.red,
            scale=1.5,
            position=position,
            collider='box'
        )
        self.direction = 1

    def update(self):
        self.x += self.direction * time.dt * 2
        if abs(self.x) > 20:
            self.direction *= -1
        if self.intersects(player).hit:
            player.position = (0, 1, 0)  # Reset on hit

enemy1 = Enemy(position=(0, 1, 10))
enemy2 = Enemy(position=(15, 4, 0))

# Text for star count
star_count = Text(text='Stars: 0 / 4', position=(-0.8, 0.45), scale=2)

def global_update():
    star_count.text = f'Stars: {4 - len(stars)} / 4'

player = Player()
update = global_update  # Override update for star count

app.run()
