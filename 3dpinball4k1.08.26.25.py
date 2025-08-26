# ------------- Ursina Pinball (single-file, no assets) -------------
# Controls:
#   Left Flipper  : A / Left Arrow
#   Right Flipper : D / Right Arrow
#   Plunger       : Hold Space, release to launch
#   Nudge         : Q (left) / E (right)  -- excessive nudging triggers TILT
#   Restart       : R (from Game Over)
#
# The game uses only Ursina primitives and simple 2D-on-table physics.

from ursina import *
import math
import random

# --- App / Window ---
app = Ursina()
window.title = 'Ursina Pinball — No Files, Just Vibes'
window.color = color.rgba(5,5,8,255)
window.fps_counter.enabled = True
try:
    application.vsync = True
    application.target_fps = 60
except:
    pass

# --- Helpers ---
def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

def reflect(v: Vec2, n: Vec2) -> Vec2:
    # reflect vector v across unit normal n
    return v - 2 * v.dot(n) * n

def closest_point_on_segment(p: Vec2, a: Vec2, b: Vec2) -> Vec2:
    ab = b - a
    ab_len2 = max(ab.x*ab.x + ab.y*ab.y, 1e-9)
    t = clamp((p - a).dot(ab) / ab_len2, 0.0, 1.0)
    return a + ab * t

# --- Constants (world units) ---
TABLE_W = 6.0
TABLE_L = 12.0
XMIN, XMAX = -TABLE_W/2, TABLE_W/2
ZMIN, ZMAX = -TABLE_L/2, TABLE_L/2

WALL_THK = 0.16
BALL_R   = 0.18
BALL_Y   = BALL_R
PLAY_ZTOP = ZMAX - WALL_THK - BALL_R
PLAY_ZBOT = ZMIN + WALL_THK + BALL_R
DRAIN_Z  = ZMIN + 0.55  # drain line

# Shooter lane (right side)
SHOOTER_W = 0.7
PLAY_XR   = XMAX - SHOOTER_W - WALL_THK - BALL_R
PLAY_XL   = XMIN + WALL_THK + BALL_R
SHOOT_X   = XMAX - (WALL_THK + SHOOTER_W/2)
SHOOT_Z   = ZMIN + 0.9

# Physics tuning
G_DOWN     = -7.5       # gravity along -z (down the table)
FRICTION   = 0.08       # rolling/air friction (fraction per sec)
REST       = 0.90       # restitution on bounces
MAX_SPEED  = 22.0       # hard clamp on ball speed
FIXED_DT   = 1/120      # physics step for integration
SUB_STEPS  = 1          # extra sub-steps if you like (keep 1 for perf)
NUDGE_PUSH = 1.8
TILT_LIMIT = 5.0        # meter threshold
TILT_DECAY = 1.7        # per second

# --- Visual Table ---
table = Entity(model='plane', scale=(TABLE_W, TABLE_L), color=color.gray, shader=None)
# Side walls (visuals only; collisions are done analytically)
wall_color = color.azure.tint(-.25)
Entity(model='cube', color=wall_color, position=(XMIN + WALL_THK/2, 0.25, 0), scale=(WALL_THK, .5, TABLE_L))
Entity(model='cube', color=wall_color, position=(PLAY_XR + WALL_THK/2, 0.25, 0), scale=(WALL_THK, .5, TABLE_L))
# Top & bottom rails
Entity(model='cube', color=wall_color, position=(0, 0.25, ZMAX - WALL_THK/2), scale=(TABLE_W, .5, WALL_THK))
Entity(model='cube', color=wall_color, position=(0, 0.25, ZMIN + WALL_THK/2), scale=(TABLE_W, .5, WALL_THK))
# Shooter lane right wall
Entity(model='cube', color=wall_color, position=(XMAX - WALL_THK/2, 0.25, 0), scale=(WALL_THK, .5, TABLE_L))
# Shooter lane divider
Entity(model='cube', color=wall_color, position=(PLAY_XR + (SHOOTER_W+WALL_THK)/2, 0.25, 0), scale=(WALL_THK, .5, TABLE_L))

# Subtle table lines for guidance (cosmetic)
for z in [-3.5, 0, 3.5]:
    Entity(model='cube', color=color.black33, position=(0, 0.01, z), scale=(TABLE_W*0.98, 0.01, 0.015))

# --- UI ---
ui = Entity(parent=camera.ui)
score_text = Text(parent=ui, text='Score: 0', position=(-.86, .46), origin=(0,0), scale=1)
balls_text = Text(parent=ui, text='Balls: 3', position=(-.86, .42), origin=(0,0), scale=1)
state_text = Text(parent=ui, text='', position=(0, .4), origin=(0,0), scale=1.2, color=color.azure)

# Plunger meter
plunger_frame = Entity(parent=ui, model='quad', color=color.rgba(255,255,255,40), origin=(-.5, .5),
                       position=(.55, -.44), scale=(.36, .04))
plunger_bar = Entity(parent=plunger_frame, model='quad', color=color.lime, origin=(-.5, .5),
                     position=(0,0), scale=(0.0, 1.0))

# --- Game Objects ---
class Ball:
    def __init__(self, x, z, color_=color.red):
        self.pos = Vec2(x, z)
        self.vel = Vec2(0, 0)
        self.r   = BALL_R
        self.ent = Entity(model='sphere', scale=self.r*2, y=BALL_Y, color=color_)
        self.sync()

    def sync(self):
        self.ent.position = (self.pos.x, BALL_Y, self.pos.y)

class Bumper:
    def __init__(self, x, z, r=0.36, strength=7.5, col=color.yellow):
        self.c = Vec2(x, z)
        self.r = r
        self.k = strength
        # Visual stack: base + cap (flat cylinder)
        self.base = Entity(model='cylinder', position=(x, 0.12, z), rotation_x=90,
                           scale=(r*2, 0.24, r*2), color=col.tint(-.35))
        self.cap  = Entity(model='cylinder', position=(x, 0.14, z), rotation_x=90,
                           scale=(r*1.7, 0.08, r*1.7), color=col)

        self.flash_t = 0.0

    def flash(self):
        self.flash_t = 0.15
        self.cap.color = color.white

    def update(self, dt):
        if self.flash_t > 0:
            self.flash_t -= dt
            if self.flash_t <= 0:
                self.cap.color = self.base.color.tint(0.6)

    def collide(self, ball: Ball, restitution=REST):
        d = ball.pos - self.c
        dist = d.length()
        target = self.r + ball.r
        if dist < target:
            n = d.normalized() if dist > 1e-6 else Vec2(0,1)
            # Positional correction
            ball.pos = self.c + n * (target + 1e-3)
            # Velocity response
            vn = ball.vel.dot(n)
            if vn < 0:
                ball.vel -= (1 + restitution) * vn * n
            # Kicker
            ball.vel += n * self.k
            self.flash()
            return True
        return False

class Flipper:
    def __init__(self, pivot: Vec2, length=1.25, thick=0.22, left=True):
        self.pivot = Vec2(pivot.x, pivot.y)
        self.length = length
        self.thick = thick
        self.left = left

        self.rest_deg = 20 if left else 160
        self.flip_deg = 70 if left else 110
        self.angle_deg = self.rest_deg
        self.ang_vel_deg = 0.0
        self.flip_speed = 900.0   # deg/s upward
        self.return_speed = 640.0 # deg/s downward
        self.pressed = False

        self.root = Entity(position=(self.pivot.x, 0.15, self.pivot.y))
        # body aligned along +x in local; origin at left end for hinge rotation
        self.body = Entity(parent=self.root, model='cube', origin_x=-.5,
                           scale=(self.length, .12, self.thick), color=color.orange)
        self.hinge = Entity(parent=self.root, model='cylinder', rotation_x=90,
                            scale=(self.thick, .18, self.thick), color=color.brown)
        self.root.rotation_y = self.angle_deg

        # Small post near tip for extra bounce feel (visual)
        tip = self.pivot + self.direction() * self.length
        self.tip_post = Entity(model='cylinder', position=(tip.x, 0.12, tip.y), rotation_x=90,
                               scale=(self.thick*0.45, .12, self.thick*0.45), color=color.azure.tint(-.2))

    def direction(self) -> Vec2:
        a = math.radians(self.angle_deg)
        return Vec2(math.cos(a), math.sin(a))

    def set_pressed(self, v: bool):
        self.pressed = v

    def update(self, dt):
        target = self.flip_deg if self.pressed else self.rest_deg
        speed = self.flip_speed if self.pressed else self.return_speed
        delta = target - self.angle_deg
        step = clamp(abs(delta), 0, speed*dt)
        step = step if delta >= 0 else -step
        new_angle = self.angle_deg + step
        self.ang_vel_deg = (new_angle - self.angle_deg) / max(dt, 1e-6)
        self.angle_deg = new_angle
        self.root.rotation_y = self.angle_deg
        # Move tip post visual
        tip = self.pivot + self.direction() * self.length
        self.tip_post.position = (tip.x, 0.12, tip.y)

    def segment(self):
        d = self.direction()
        p0 = self.pivot
        p1 = self.pivot + d * self.length
        return p0, p1

    def collide_ball(self, ball: Ball, restitution=REST):
        p0, p1 = self.segment()
        q = closest_point_on_segment(ball.pos, p0, p1)
        d = ball.pos - q
        dist = d.length()
        eff_r = ball.r + self.thick*0.45
        if dist < eff_r:
            n = d.normalized() if dist > 1e-6 else (ball.pos - self.pivot).normalized()
            # push out
            ball.pos += n * (eff_r - dist + 1e-3)
            # flipper point linear velocity (2D)
            ang_vel_rad = math.radians(self.ang_vel_deg)
            r = q - p0
            v_point = Vec2(-ang_vel_rad * r.y, ang_vel_rad * r.x)
            v_rel = ball.vel - v_point
            vn = v_rel.dot(n)
            if vn < 0:
                ball.vel = v_point + (v_rel - (1 + restitution)*vn*n)
                # base kick so even slow returns have some oomph
                ball.vel += n * 0.6
            return True
        return False

# --- Game Controller ---
class PinballGame:
    def __init__(self):
        self.score = 0
        self.balls = 3
        self.state = 'ready'  # 'ready', 'play', 'tilt', 'gameover'
        self.tilt_meter = 0.0
        self.tilt_lock = 0.0

        # Ball
        self.ball = Ball(SHOOT_X, SHOOT_Z, color_=color.red)
        self.in_shooter = True
        self.plunger_charge = 0.0
        self.plunger_max = 16.0

        # Bumpers (classic tri)
        self.bumpers = [
            Bumper(-1.2,  2.7, r=0.36, strength=7.4, col=color.yellow),
            Bumper( 0.0,  3.3, r=0.36, strength=7.8, col=color.yellow),
            Bumper( 1.2,  2.7, r=0.36, strength=7.4, col=color.yellow),
        ]
        # Posts near slings (small pegs for fun)
        self.posts = [
            Bumper(-2.5, -1.6, r=0.18, strength=5.0, col=color.cyan),
            Bumper( 2.5, -1.6, r=0.18, strength=5.0, col=color.cyan),
        ]

        # Flippers
        self.left_flip  = Flipper(Vec2(-1.15, -4.2), left=True)
        self.right_flip = Flipper(Vec2( 1.15, -4.2), left=False)

        # Cosmetic arch at top lanes
        Entity(model='cube', color=color.black33, position=(0, 0.02, 4.7), scale=(TABLE_W*0.86, .02, .02))

        # Launch guide (visual plunger cylinder)
        self.plunger_vis = Entity(model='cube', color=color.lime.tint(-.3),
                                  position=(SHOOT_X, 0.12, ZMIN + 0.3), scale=(.08, .12, 1.0))

        self.acc = 0.0  # physics accumulator

        self.update_ui()
        self.show_state('Ball Ready — hold SPACE to launch')

    def update_ui(self):
        score_text.text = f'Score: {self.score}'
        balls_text.text = f'Balls: {self.balls}'

    def show_state(self, msg, color_=color.azure):
        state_text.text = msg
        state_text.color = color_

    # --- Input handling (called from global input) ---
    def set_left(self, pressed: bool):
        if self.state != 'tilt':
            self.left_flip.set_pressed(pressed)

    def set_right(self, pressed: bool):
        if self.state != 'tilt':
            self.right_flip.set_pressed(pressed)

    def nudge(self, dirx: float):
        # simple lateral impulse; builds tilt meter
        if self.state in ('play', 'ready') and self.tilt_lock <= 0:
            self.ball.vel.x += dirx * NUDGE_PUSH
            self.tilt_meter += 1.0
            if self.tilt_meter >= TILT_LIMIT:
                self.state = 'tilt'
                self.left_flip.set_pressed(False)
                self.right_flip.set_pressed(False)
                self.tilt_lock = 3.0
                self.show_state('TILT! Flippers locked', color_=color.red)

    def restart(self):
        self.score = 0
        self.balls = 3
        self.state = 'ready'
        self.tilt_meter = 0.0
        self.tilt_lock = 0.0
        self.reset_to_shooter()
        self.update_ui()
        self.show_state('Ball Ready — hold SPACE to launch', color_=color.azure)

    # --- Game mechanics ---
    def reset_to_shooter(self):
        self.ball.pos = Vec2(SHOOT_X, SHOOT_Z)
        self.ball.vel = Vec2(0, 0)
        self.in_shooter = True
        self.plunger_charge = 0.0
        self.ball.sync()

    def launch_if_ready(self):
        if not self.in_shooter:
            return
        power = clamp(self.plunger_charge, 0, self.plunger_max)
        # base + charged impulse
        self.ball.vel = Vec2(0, 7.0 + power)
        self.in_shooter = False
        self.state = 'play'
        self.show_state('')

    def step_physics(self, dt):
        # Flippers animate first (so their angular vel is updated before collision)
        self.left_flip.update(dt)
        self.right_flip.update(dt)

        # Gravity along -z direction
        self.ball.vel += Vec2(0, G_DOWN) * dt

        # Friction / drag
        spd = self.ball.vel.length()
        if spd > 0:
            drag = clamp(FRICTION * dt, 0.0, 1.0)
            self.ball.vel *= (1.0 - drag)

        # Clamp speed
        s = self.ball.vel.length()
        if s > MAX_SPEED:
            self.ball.vel = self.ball.vel.normalized() * MAX_SPEED

        # Integrate
        self.ball.pos += self.ball.vel * dt

        # Shooter lane constraints while in_shooter
        if self.in_shooter:
            # Keep ball within shooter rail
            self.ball.pos.x = clamp(self.ball.pos.x, SHOOT_X - 0.05, SHOOT_X + 0.05)
            self.ball.pos.y = clamp(self.ball.pos.y, ZMIN + 0.4, -3.6)

        # Walls (playfield, not the shooter lane)
        if not self.in_shooter:
            if self.ball.pos.x < PLAY_XL:
                self.ball.pos.x = PLAY_XL
                if self.ball.vel.x < 0: self.ball.vel.x = -self.ball.vel.x * REST
            if self.ball.pos.x > PLAY_XR:
                self.ball.pos.x = PLAY_XR
                if self.ball.vel.x > 0: self.ball.vel.x = -self.ball.vel.x * REST
            if self.ball.pos.y > PLAY_ZTOP:
                self.ball.pos.y = PLAY_ZTOP
                if self.ball.vel.y > 0: self.ball.vel.y = -abs(self.ball.vel.y) * REST

        # Top shooter stop (prevent exiting table via shooter)
        if self.in_shooter and self.ball.pos.y > -3.6:
            self.ball.pos.y = -3.6
            if self.ball.vel.y > 0: self.ball.vel.y *= -REST

        # Drain detection
        if not self.in_shooter and self.ball.pos.y < DRAIN_Z:
            self.lose_ball()
            return

        # Bumpers / posts
        bumped = False
        for b in self.bumpers:
            if b.collide(self.ball, restitution=REST):
                self.add_score(100)
                bumped = True
        for p in self.posts:
            if p.collide(self.ball, restitution=REST):
                self.add_score(35)
                bumped = True

        # Flipper collisions (after bumpers so we resolve most interpenetrations first)
        hit_l = self.left_flip.collide_ball(self.ball, restitution=REST)
        hit_r = self.right_flip.collide_ball(self.ball, restitution=REST)
        if hit_l or hit_r:
            self.add_score(5)

        # Bottom safety rail (light bounce to avoid sticky corners)
        if self.ball.pos.y < PLAY_ZBOT and not self.in_shooter:
            if self.ball.vel.y < 0:
                self.ball.vel.y *= 0.98

        self.ball.sync()

    def add_score(self, pts):
        self.score += pts
        self.update_ui()

    def lose_ball(self):
        self.balls -= 1
        self.update_ui()
        if self.balls <= 0:
            self.state = 'gameover'
            self.show_state('Game Over — press R to restart', color_=color.orange)
        else:
            self.state = 'ready'
            self.reset_to_shooter()
            self.show_state('Ball Ready — hold SPACE to launch', color_=color.azure)

    def update(self, dt):
        # Plunger UI + charging
        if self.state in ('ready', 'play'):
            if self.in_shooter and held_keys['space']:
                self.plunger_charge = clamp(self.plunger_charge + 24.0*dt, 0.0, self.plunger_max)
            elif self.in_shooter and not held_keys['space'] and self.plunger_charge > 0:
                # released: launch the ball
                self.launch_if_ready()
            # update plunger visuals
            plunger_bar.scale_x = (self.plunger_charge / self.plunger_max)
            self.plunger_vis.scale_z = 1.0 - 0.65*(self.plunger_charge / self.plunger_max)

        # Tilt decay and lock timer
        if self.tilt_meter > 0:
            self.tilt_meter = max(0.0, self.tilt_meter - TILT_DECAY * dt)
        if self.tilt_lock > 0:
            self.tilt_lock -= dt
            if self.tilt_lock <= 0 and self.state == 'tilt':
                # Recover from tilt
                self.state = 'play' if not self.in_shooter else 'ready'
                self.show_state('')

        # Physics stepping: fixed dt accumulator
        self.acc += min(dt, 0.05)
        steps = 0
        while self.acc >= FIXED_DT and steps < 6:
            self.step_physics(FIXED_DT / SUB_STEPS)
            for _ in range(SUB_STEPS-1):
                self.step_physics(FIXED_DT / SUB_STEPS)
            self.acc -= FIXED_DT
            steps += 1

        # Update bumper flashes
        for b in self.bumpers: b.update(dt)
        for p in self.posts:   p.update(dt)


game = PinballGame()

# --- Global Input Bridge ---
def input(key):
    if key in ('a', 'left arrow'):      game.set_left(True)
    if key in ('a up', 'left arrow up'): game.set_left(False)

    if key in ('d', 'right arrow'):       game.set_right(True)
    if key in ('d up', 'right arrow up'): game.set_right(False)

    if key == 'q': game.nudge(-1.0)
    if key == 'e': game.nudge(+1.0)

    if key == 'r' and game.state == 'gameover':
        game.restart()

# --- Frame Update ---
def update():
    game.update(time.dt)

# --- Camera ---
camera.position = Vec3(0, 12, -14)
camera.look_at(Vec3(0, 0.0, 2.5))
DirectionalLight(direction=(0.4, -1, -0.2), shadows=False)

app.run()
# -------------------------------------------------------------------
