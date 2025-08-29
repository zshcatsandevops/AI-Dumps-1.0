from ursina import *
import random

app = Ursina()

# Define clamp function (not built-in in Ursina or standard Python for this purpose)
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

# Camera setup
camera.fov = 90  # Perspective projection for 3D
camera.position = (5, 5, -15)  # Initial position behind player
camera.rotation = (15, -30, 0)  # Slight tilt for better view
camera.smoothness = 5  # Controls camera follow speed

# Player setup
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='cube', scale=(1, 1, 1), color=color.white, collider='box', **kwargs)
        self.speed = 5
        self.jump_strength = 8
        self.gravity = 20
        self.velocity_y = 0
        self.grounded = False

    def update(self):
        # Gravity and vertical movement
        self.velocity_y -= self.gravity * time.dt
        self.y += self.velocity_y * time.dt

        # Ground check (simple raycast downward)
        ray = raycast(self.position, direction=(0, -1, 0), distance=0.6, ignore=[self])
        if ray.hit:
            self.y = ray.world_point.y + 0.5  # Adjust to ground level
            self.velocity_y = 0
            self.grounded = True
        else:
            self.grounded = False

        # Horizontal movement (WASD or arrows)
        direction = Vec3(
            held_keys['d'] - held_keys['a'] + held_keys['right arrow'] - held_keys['left arrow'],
            0,
            held_keys['w'] - held_keys['s'] + held_keys['up arrow'] - held_keys['down arrow']
        ).normalized() * self.speed
        self.position += direction * time.dt

        # Keep player within bounds
        self.x = clamp(self.x, -25, 25)
        self.z = clamp(self.z, -25, 25)

    def input(self, key):
        if key == 'space' and self.grounded:
            self.velocity_y = self.jump_strength

player = Player(position=(0, 0, 0))

# Ground
ground = Entity(model='plane', scale=(50, 1, 50), position=(0, -5, 0), collider='box', color=color.green)

# Platforms
platforms = [
    Entity(model='cube', scale=(4, 0.5, 4), position=(5, -2, 5), collider='box', color=color.brown),
    Entity(model='cube', scale=(4, 0.5, 4), position=(10, 0, 0), collider='box', color=color.brown),
    Entity(model='cube', scale=(4, 0.5, 4), position=(15, 2, -5), collider='box', color=color.brown)
]

# Coins
coins = []
for i in range(5):
    x = random.randint(5, 20)
    y = random.randint(-2, 5)
    z = random.randint(-10, 10)
    coin = Entity(model='sphere', scale=0.5, position=(x, y, z), color=color.yellow, collider='sphere')
    coins.append(coin)

# Enemies with patrol data
enemies = []
for i in range(3):
    x = random.randint(10, 30)
    z = random.randint(-10, 10)
    enemy = Entity(model='cube', scale=(1, 1, 1), position=(x, -4, z), color=color.red, collider='box')
    enemy.patrol_start = x - 2
    enemy.patrol_end = x + 2
    enemy.patrol_speed = 2
    enemy.direction = 1
    enemies.append(enemy)

# Goal (Flag)
flag = Entity(model='cube', scale=(1, 2, 1), position=(30, -3, 0), color=color.blue, collider='box')

# Text (positioned in screen space)
score = 0
score_text = Text(text=f'Score: {score}', position=(-0.8, 0.4), origin=(0, 0))

# Update function
def update():
    global score
    # Coin collection
    for coin in coins[:]:
        if player.intersects(coin).hit:
            coins.remove(coin)
            destroy(coin)
            score += 10
            score_text.text = f'Score: {score}'

    # Enemy movement (patrol along x-axis)
    for enemy in enemies:
        enemy.x += enemy.patrol_speed * enemy.direction * time.dt
        if enemy.x > enemy.patrol_end:
            enemy.x = enemy.patrol_end
            enemy.direction = -1
        elif enemy.x < enemy.patrol_start:
            enemy.x = enemy.patrol_start
            enemy.direction = 1

        # Check collision with player
        if player.intersects(enemy).hit:
            player.position = (0, 0, 0)  # Reset to start
            score = 0
            score_text.text = f'Score: {score}'

    # Win condition
    if player.intersects(flag).hit:
        score_text.text = f'WIN! Score: {score}'

    # Camera follows player (Mario 64-style third-person)
    target_pos = player.position + Vec3(5, 5, -10)  # Offset behind and above
    camera.position = lerp(camera.position, target_pos, camera.smoothness * time.dt)
    camera.look_at(player.position + Vec3(0, 1, 0))  # Look at player's head

# Background (skybox-like)
sky = Entity(model='sphere', scale=100, color=color.cyan, double_sided=True)

app.run()
