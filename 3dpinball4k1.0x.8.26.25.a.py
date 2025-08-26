from ursina import *
import math
import random

# Initialize Ursina with 600x400 window
app = Ursina()
window.size = (600, 400)
window.title = '3D Pinball Space Cadet - Windows XP Clone'
window.color = color.rgb(15, 25, 45)  # Space blue background
window.fps_counter.enabled = False
window.exit_button.enabled = False
window.borderless = False

# Camera setup for top-down view
camera.orthographic = True
camera.fov = 12
camera.position = (0, 15, -1)
camera.rotation_x = 85

# Physics constants
GRAVITY = -0.08
FRICTION = 0.98
FLIPPER_POWER = 0.8
BUMPER_POWER = 0.6
PLUNGER_MAX_POWER = 1.2
TILT_PENALTY = 3

# Table setup
table = Entity(
    model='cube',
    color=color.rgb(20, 30, 50),
    scale=(8, 0.2, 12),
    position=(0, 0, 0)
)

# Table walls
walls = [
    Entity(model='cube', color=color.gray, position=(-4, 0.5, 0), scale=(0.2, 1, 12)),  # Left wall
    Entity(model='cube', color=color.gray, position=(4, 0.5, 0), scale=(0.2, 1, 12)),   # Right wall
    Entity(model='cube', color=color.gray, position=(0, 0.5, 6), scale=(8, 1, 0.2)),    # Top wall
]

# Shooter lane separator
Entity(model='cube', color=color.gray, position=(3, 0.5, -2), scale=(0.2, 1, 8))

class Ball(Entity):
    def __init__(self):
        super().__init__(
            model='sphere',
            color=color.light_gray,
            scale=0.25,
            position=(3.5, 0.3, -4)
        )
        self.velocity = Vec3(0, 0, 0)
        self.in_play = False
        self.radius = 0.125
        
    def update(self):
        if not self.in_play:
            return
            
        # Apply gravity (table tilt)
        self.velocity += Vec3(0, 0, GRAVITY) * time.dt
        
        # Apply friction
        self.velocity *= FRICTION
        
        # Update position
        self.position += self.velocity * time.dt
        
        # Speed limit
        max_speed = 2.0
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalized() * max_speed
        
        # Table boundaries
        if self.x < -3.7:
            self.x = -3.7
            self.velocity.x = abs(self.velocity.x) * 0.8
        elif self.x > 2.8:  # Shooter lane boundary
            if self.z > -2:
                self.x = 2.8
                self.velocity.x = -abs(self.velocity.x) * 0.8
        elif self.x > 3.7:
            self.x = 3.7
            self.velocity.x = -abs(self.velocity.x) * 0.8
            
        if self.z > 5.7:
            self.z = 5.7
            self.velocity.z = -abs(self.velocity.z) * 0.8
        
        # Check for drain
        if self.z < -5.8:
            self.in_play = False
            game.ball_drained()
            
    def launch(self, power):
        self.velocity = Vec3(0, 0, power)
        self.in_play = True

class Flipper(Entity):
    def __init__(self, position, is_left=True):
        self.is_left = is_left
        self.rest_rotation = -30 if is_left else 30
        self.flip_rotation = 30 if is_left else -30
        
        super().__init__(
            model='cube',
            color=color.orange,
            scale=(1.2, 0.15, 0.2),
            position=position,
            rotation=(0, self.rest_rotation, 0)
        )
        
        self.pivot = Entity(
            model='cylinder',
            color=color.dark_gray,
            scale=(0.15, 0.2, 0.15),
            position=position
        )
        
        self.active = False
        self.angular_velocity = 0
        
    def flip(self, active):
        self.active = active
        
    def update(self):
        target = self.flip_rotation if self.active else self.rest_rotation
        self.rotation_y = lerp(self.rotation_y, target, time.dt * 15)
        self.angular_velocity = (target - self.rotation_y) * 15
        
    def check_collision(self, ball):
        # Simplified flipper collision
        dist = distance(ball.position, self.position)
        if dist < 0.7:
            # Calculate bounce direction
            direction = (ball.position - self.position).normalized()
            
            # Add flipper power if active
            power = FLIPPER_POWER if self.active else 0.3
            ball.velocity = direction * power
            ball.velocity.y = 0
            ball.velocity.z -= 0.2  # Always push ball up table
            
            # Move ball away from flipper
            ball.position = self.position + direction * 0.7
            return True
        return False

class Bumper(Entity):
    def __init__(self, position, bumper_color=color.cyan):
        super().__init__(
            model='cylinder',
            color=bumper_color,
            scale=(0.5, 0.4, 0.5),
            position=position
        )
        
        self.cap = Entity(
            model='cylinder',
            color=color.white,
            scale=(0.4, 0.1, 0.4),
            position=position + Vec3(0, 0.25, 0)
        )
        
        self.lit = False
        self.lit_timer = 0
        self.points = 100
        
    def check_collision(self, ball):
        dist = distance_xz(ball.position, self.position)
        if dist < 0.35:
            # Calculate bounce direction
            if dist > 0:
                direction = (ball.position - self.position)
                direction.y = 0
                direction = direction.normalized()
            else:
                direction = Vec3(1, 0, 0)
            
            # Apply bumper force
            ball.velocity = direction * BUMPER_POWER
            ball.velocity.z -= 0.1  # Slight upward push
            
            # Move ball outside bumper
            ball.position = self.position + direction * 0.4
            ball.position.y = 0.3
            
            # Light up
            self.lit = True
            self.lit_timer = 0.15
            self.cap.color = color.yellow
            
            return True
        return False
        
    def update(self):
        if self.lit_timer > 0:
            self.lit_timer -= time.dt
            if self.lit_timer <= 0:
                self.lit = False
                self.cap.color = color.white

class Target(Entity):
    def __init__(self, position, target_color=color.green):
        super().__init__(
            model='cube',
            color=target_color,
            scale=(0.2, 0.3, 0.5),
            position=position
        )
        self.lit = False
        self.hit_timer = 0
        self.points = 50
        
    def check_collision(self, ball):
        if abs(ball.x - self.x) < 0.2 and abs(ball.z - self.z) < 0.35:
            self.lit = True
            self.hit_timer = 0.2
            self.color = color.yellow
            
            # Bounce ball
            if ball.velocity.x > 0 and ball.x < self.x:
                ball.velocity.x = -abs(ball.velocity.x) * 0.8
            elif ball.velocity.x < 0 and ball.x > self.x:
                ball.velocity.x = abs(ball.velocity.x) * 0.8
                
            return True
        return False
        
    def update(self):
        if self.hit_timer > 0:
            self.hit_timer -= time.dt
            if self.hit_timer <= 0:
                self.lit = False
                self.color = color.green

class Lane(Entity):
    def __init__(self, position):
        super().__init__(
            model='cube',
            color=color.dark_gray,
            scale=(0.4, 0.05, 0.2),
            position=position
        )
        self.activated = False
        self.points = 25
        
    def check_collision(self, ball):
        if abs(ball.x - self.x) < 0.25 and abs(ball.z - self.z) < 0.15:
            if not self.activated:
                self.activated = True
                self.color = color.yellow
                return True
        else:
            if self.activated:
                self.activated = False
                self.color = color.dark_gray
        return False

class PinballGame:
    def __init__(self):
        self.score = 0
        self.balls = 3
        self.multiplier = 1
        self.rank = "Cadet"
        self.ranks = ["Cadet", "Ensign", "Lieutenant", "Captain", "Commander", "Admiral"]
        self.rank_thresholds = [0, 10000, 50000, 150000, 500000, 1000000]
        self.tilt_warning = 0
        
        # Ball
        self.ball = Ball()
        
        # Plunger
        self.plunger_power = 0
        self.plunger_charging = False
        self.plunger = Entity(
            model='cube',
            color=color.red,
            scale=(0.3, 0.2, 0.5),
            position=(3.5, 0.3, -5)
        )
        
        # Flippers
        self.left_flipper = Flipper(Vec3(-1, 0.2, -4), True)
        self.right_flipper = Flipper(Vec3(1, 0.2, -4), False)
        
        # Bumpers (triangular formation)
        self.bumpers = [
            Bumper(Vec3(-0.8, 0.2, 2), color.cyan),
            Bumper(Vec3(0.8, 0.2, 2), color.magenta),
            Bumper(Vec3(0, 0.2, 3.2), color.lime),
        ]
        
        # Additional mini bumpers
        self.bumpers.extend([
            Bumper(Vec3(-2, 0.2, 0), color.orange),
            Bumper(Vec3(2, 0.2, 0), color.orange),
        ])
        
        # Targets
        self.targets = [
            Target(Vec3(-3, 0.2, 4), color.green),
            Target(Vec3(-2, 0.2, 4), color.green),
            Target(Vec3(-1, 0.2, 4), color.green),
            Target(Vec3(1, 0.2, 4), color.orange),
            Target(Vec3(2, 0.2, 4), color.orange),
            Target(Vec3(3, 0.2, 4), color.orange),
        ]
        
        # Lanes
        self.lanes = [
            Lane(Vec3(-2.5, 0.15, 5)),
            Lane(Vec3(-1.5, 0.15, 5)),
            Lane(Vec3(-0.5, 0.15, 5)),
            Lane(Vec3(0.5, 0.15, 5)),
            Lane(Vec3(1.5, 0.15, 5)),
            Lane(Vec3(2.5, 0.15, 5)),
        ]
        
        # Mission
        self.mission = None
        self.mission_targets = []
        
        # UI
        self.setup_ui()
        
        # Game state
        self.game_over = False
        
    def setup_ui(self):
        self.score_text = Text(f'SCORE: {self.score}', position=(-0.85, 0.45), scale=2)
        self.balls_text = Text(f'BALLS: {self.balls}', position=(-0.85, 0.38), scale=2)
        self.rank_text = Text(f'RANK: {self.rank}', position=(-0.85, 0.31), scale=2, color=color.yellow)
        self.multiplier_text = Text('', position=(-0.85, 0.24), scale=2, color=color.lime)
        self.mission_text = Text('', position=(-0.85, 0.17), scale=1.5, color=color.cyan)
        
        self.instructions = Text(
            'CONTROLS:\nA/← : Left Flipper\nD/→ : Right Flipper\nSPACE: Launch\nT: Tilt',
            position=(0.5, 0.4),
            scale=1.2,
            color=color.gray
        )
        
        self.game_over_text = Text('', position=(0, 0), scale=4, color=color.red, enabled=False)
        
    def launch_ball(self):
        if not self.ball.in_play and self.balls > 0:
            self.ball.position = Vec3(3.5, 0.3, -4)
            self.ball.launch(self.plunger_power)
            self.plunger_power = 0
            
    def add_score(self, points):
        self.score += points * self.multiplier
        self.update_ui()
        
        # Check rank advancement
        for i, threshold in enumerate(self.rank_thresholds):
            if self.score >= threshold:
                self.rank = self.ranks[min(i, len(self.ranks) - 1)]
                
    def ball_drained(self):
        self.balls -= 1
        self.multiplier = 1
        self.tilt_warning = 0
        
        if self.balls <= 0:
            self.game_over = True
            self.game_over_text.text = 'GAME OVER\nPress R to restart'
            self.game_over_text.enabled = True
        else:
            self.ball.position = Vec3(3.5, 0.3, -4)
            self.ball.velocity = Vec3(0, 0, 0)
            
    def tilt(self):
        self.tilt_warning += 1
        if self.tilt_warning >= TILT_PENALTY:
            self.ball.in_play = False
            self.ball.velocity = Vec3(0, 0, 0)
            self.tilt_warning = 0
            
    def start_mission(self):
        self.mission = "Hit all green targets!"
        self.mission_targets = [0, 1, 2]  # First three targets
        for i in self.mission_targets:
            self.targets[i].lit = False
            
    def check_mission(self):
        if self.mission and self.mission_targets:
            complete = all(self.targets[i].lit for i in self.mission_targets)
            
            if complete:
                self.add_score(5000)
                self.multiplier = min(self.multiplier + 1, 5)
                self.mission = None
                self.mission_targets = []
                
    def update_ui(self):
        self.score_text.text = f'SCORE: {self.score:,}'
        self.balls_text.text = f'BALLS: {self.balls}'
        self.rank_text.text = f'RANK: {self.rank}'
        
        if self.multiplier > 1:
            self.multiplier_text.text = f'x{self.multiplier}'
        else:
            self.multiplier_text.text = ''
            
        if self.mission:
            self.mission_text.text = self.mission
        else:
            self.mission_text.text = ''
            
    def restart(self):
        self.__init__()
        self.game_over_text.enabled = False

# Create game instance
game = PinballGame()

def update():
    if game.game_over:
        return
        
    # Update ball physics
    game.ball.update()
    
    # Check collisions
    if game.ball.in_play:
        # Bumper collisions
        for bumper in game.bumpers:
            bumper.update()
            if bumper.check_collision(game.ball):
                game.add_score(bumper.points)
                
        # Target collisions
        for target in game.targets:
            target.update()
            if target.check_collision(game.ball):
                game.add_score(target.points)
                
        # Lane collisions
        for lane in game.lanes:
            if lane.check_collision(game.ball):
                game.add_score(lane.points)
                
        # Flipper collisions
        game.left_flipper.update()
        game.right_flipper.update()
        game.left_flipper.check_collision(game.ball)
        game.right_flipper.check_collision(game.ball)
        
    # Check mission
    game.check_mission()
    
    # Random mission start
    if not game.mission and random.random() < 0.001:
        game.start_mission()
        
    # Plunger charging visual
    if game.plunger_charging:
        game.plunger_power = min(game.plunger_power + time.dt * 2, PLUNGER_MAX_POWER)
        game.plunger.scale_z = 0.5 - (game.plunger_power / PLUNGER_MAX_POWER) * 0.3
        game.plunger.color = color.rgb(255, 255 - int(game.plunger_power * 100), 0)

def input(key):
    if key == 'space':
        if game.game_over:
            return
        if not game.ball.in_play:
            game.plunger_charging = True
            
    elif key == 'space up':
        if game.plunger_charging:
            game.plunger_charging = False
            game.launch_ball()
            game.plunger.scale_z = 0.5
            game.plunger.color = color.red
            
    elif key == 'a' or key == 'left arrow':
        game.left_flipper.flip(True)
        
    elif key == 'a up' or key == 'left arrow up':
        game.left_flipper.flip(False)
        
    elif key == 'd' or key == 'right arrow':
        game.right_flipper.flip(True)
        
    elif key == 'd up' or key == 'right arrow up':
        game.right_flipper.flip(False)
        
    elif key == 't':
        game.tilt()
        
    elif key == 'r' and game.game_over:
        game.restart()

# Add lighting
DirectionalLight(y=2, z=-1, shadows=True)
AmbientLight(color=color.rgba(100, 100, 100, 255))

app.run()
