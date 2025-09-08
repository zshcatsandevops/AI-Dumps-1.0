from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina()

# Sky and lighting
Sky()
window.color = color.rgb(100, 200, 255)  # Light blue sky

# Player (Mario-like)
player = FirstPersonController(
    jump_height=2,
    jump_duration=0.4,
    speed=5,
    position=(0, 5, 0),
    gravity=1
)

# Ground
ground = Entity(
    model='plane',
    texture='grass',
    scale=(50, 1, 50),
    collider='mesh'
)

# Platforms
platforms = []
for x in range(-3, 4, 3):
    for z in range(-3, 4, 3):
        if (x, z) != (0, 0):  # Skip center
            p = Entity(
                model='cube',
                color=color.orange,
                scale=(2, 1, 2),
                position=(x * 3, 1, z * 3),
                collider='box'
            )
            platforms.append(p)

# Coins
coins = []
for i in range(10):
    coin = Entity(
        model='sphere',
        color=color.yellow,
        scale=0.7,
        position=(random.randint(-10, 10), random.randint(2, 8), random.randint(-10, 10)),
        collider='sphere'
    )
    coin.original_y = coin.y
    coin.rotation_speed = random.randint(50, 150)
    coins.append(coin)

# Camera settings
camera.fov = 70
player.cursor.visible = False

# Update function
def update():
    # Rotate coins
    for coin in coins:
        coin.rotation_y += time.dt * coin.rotation_speed
        coin.y = coin.original_y + math.sin(time.dt * 60 + coin.x) * 0.1  # Bob up and down

    # Coin collection
    to_destroy = []
    for coin in coins:
        if distance(player.position, coin.position) < 1.5:
            to_destroy.append(coin)
            Audio('coin_sound', autoplay=True)  # Built-in sound (optional)

    for coin in to_destroy:
        coins.remove(coin)
        destroy(coin)

    # Prevent falling below ground
    if player.y < -10:
        player.position = (0, 10, 0)

# Start game
app.run()
