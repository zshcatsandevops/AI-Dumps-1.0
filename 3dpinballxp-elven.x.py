"""
Pinball (2.5D) in Pygame — single file, zero external assets.

Controls (Space Cadet style):
  Z = left flipper
  / = right flipper
  X = both flippers
  SPACE = hold/release to plunge
  Arrow keys = nudge (Left/Right/Up). Excessive nudge -> TILT
  P = pause, F = fullscreen, M = mute, N = new game, Esc = quit

Optional gamepad (PS3/SDL):
  L1/R1 => flippers, Cross (X) or R2 => plunger, D-Pad => nudge

Requires: pygame, numpy
"""

import math
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame
import numpy as np

# --------------------------------------------
# Utility
# --------------------------------------------

Vec2 = pygame.math.Vector2

def clamp(x, a, b):
    return a if x < a else b if x > b else x

def nearest_point_on_segment(a: Vec2, b: Vec2, p: Vec2) -> Vec2:
    ab = b - a
    denom = ab.dot(ab)
    if denom == 0:
        return a
    t = clamp((p - a).dot(ab) / denom, 0.0, 1.0)
    return a + ab * t

def perp(v: Vec2) -> Vec2:
    return Vec2(-v.y, v.x)

# --------------------------------------------
# Synth audio (Windows-XP-ish beeps & boinks)
# --------------------------------------------

class SoundBank:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.sounds = {}
        self._build()

    def _tone(self, freq=440.0, dur=0.08, vol=0.5, wave="sine"):
        sr = 44100
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        if wave == "sine":
            y = np.sin(2 * np.pi * freq * t)
        elif wave == "square":
            y = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave == "noise":
            y = np.random.uniform(-1, 1, size=t.shape)
        else:
            y = np.sin(2 * np.pi * freq * t)

        # Simple clickless envelope
        env = np.minimum(1.0, np.arange(len(y)) / (0.002 * sr))
        env *= np.exp(-3.0 * np.arange(len(y)) / (dur * sr + 1e-6))
        y = (y * env) * vol

        y16 = (y * 32767).astype(np.int16)
        stereo = np.column_stack([y16, y16])
        return pygame.sndarray.make_sound(stereo)

    def _sweep(self, f0=200, f1=800, dur=0.25, vol=0.5):
        sr = 44100
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        # Linear chirp phase
        k = (f1 - f0) / dur
        phase = 2 * np.pi * (f0 * t + 0.5 * k * t**2)
        y = np.sin(phase)
        env = np.minimum(1.0, np.arange(len(y)) / (0.01 * sr))
        env *= np.exp(-2.0 * np.arange(len(y)) / (dur * sr + 1e-6))
        y = (y * env) * vol
        y16 = (y * 32767).astype(np.int16)
        stereo = np.column_stack([y16, y16])
        return pygame.sndarray.make_sound(stereo)

    def _build(self):
        try:
            self.sounds["bumper"]  = self._tone(880, 0.07, 0.35, "square")
            self.sounds["slings"]  = self._tone(740, 0.06, 0.30, "square")
            self.sounds["flipper"] = self._tone(320, 0.04, 0.25, "square")
            self.sounds["launch"]  = self._sweep(160, 900, 0.25, 0.45)
            self.sounds["drain"]   = self._sweep(600, 200, 0.35, 0.4)
            self.sounds["nudge"]   = self._tone(120, 0.03, 0.2, "noise")
        except Exception:
            # Mixer might not be ready on some systems — fail safely
            self.enabled = False

    def play(self, key):
        if self.enabled and key in self.sounds:
            self.sounds[key].play()

# --------------------------------------------
# Visual helpers (soft glow & gradients)
# --------------------------------------------

def radial_glow(radius: int, color=(255, 255, 255), intensity=0.7, steps=18) -> pygame.Surface:
    """Pre-render a radial glow surface with alpha falloff."""
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    cx = cy = radius
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(255 * (i / steps) ** 2 * intensity)
        pygame.draw.circle(surf, (*color, a), (cx, cy), r)
    return surf

def draw_ball(surface, pos: Vec2, r: int):
    # Soft shadow
    shadow = pygame.Surface((r*4, r*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 80), shadow.get_rect())
    surface.blit(shadow, (pos.x - r*2 + 6, pos.y - r + 10))

    # Main sphere
    pygame.draw.circle(surface, (220, 225, 235), (int(pos.x), int(pos.y)), r)
    pygame.draw.circle(surface, (150, 160, 170), (int(pos.x), int(pos.y)), r, 2)

    # Specular highlight
    highlight = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
    pygame.draw.circle(highlight, (255, 255, 255, 160), (r//2, r//2), r//2)
    surface.blit(highlight, (int(pos.x - r), int(pos.y - r)))

# --------------------------------------------
# World geometry & objects
# --------------------------------------------

@dataclass
class Segment:
    a: Vec2
    b: Vec2
    restitution: float = 0.4
    tag: str = "wall"

@dataclass
class Bumper:
    pos: Vec2
    radius: float
    strength: float = 1.25
    score_value: int = 100
    glow: Optional[pygame.Surface] = None

@dataclass
class Flipper:
    pivot: Vec2
    length: float
    radius: float
    is_left: bool
    open_angle: float    # radians
    closed_angle: float  # radians
    angle: float
    omega: float = 0.0   # angular velocity
    pressed: bool = False

    def endpoints(self) -> Tuple[Vec2, Vec2]:
        d = Vec2(self.length, 0).rotate_rad(self.angle)
        if self.is_left:
            p0 = self.pivot
            p1 = self.pivot + d
        else:
            p0 = self.pivot
            p1 = self.pivot - d
        return p0, p1

    def update(self, dt: float):
        target = self.closed_angle if self.pressed else self.open_angle
        max_speed = 18.0  # rad/s
        prev = self.angle
        # critically damped "servo"
        diff = target - self.angle
        step = clamp(diff, -max_speed * dt, max_speed * dt)
        self.angle += step
        self.omega = (self.angle - prev) / dt if dt > 0 else 0.0

@dataclass
class Plunger:
    x: float
    top_y: float
    bottom_y: float
    power: float = 0.0
    max_power: float = 1300.0
    pulling: bool = False

    def update(self, dt: float):
        if self.pulling:
            self.power = clamp(self.power + 2200.0 * dt, 0.0, self.max_power)
        else:
            self.power = clamp(self.power - 1600.0 * dt, 0.0, self.max_power)

@dataclass
class Ball:
    pos: Vec2
    vel: Vec2
    radius: float = 12.0
    alive: bool = True
    in_lane: bool = True

# --------------------------------------------
# Physics & collisions
# --------------------------------------------

def collide_ball_segment(ball: Ball, seg: Segment):
    a, b = seg.a, seg.b
    q = nearest_point_on_segment(a, b, ball.pos)
    d = ball.pos - q
    dist = d.length()
    if dist == 0:
        n = perp(b - a)
        if n.length() == 0:
            return False
        n = n.normalize()
    else:
        n = d / dist

    overlap = ball.radius - dist
    if overlap > 0:
        # push out
        ball.pos += n * (overlap + 0.01)
        # reflect velocity
        vn = ball.vel.dot(n)
        if vn < 0:
            ball.vel -= (1.0 + seg.restitution) * vn * n
        return True
    return False

def collide_ball_capsule_with_flipper(ball: Ball, flipper: Flipper, restitution=0.35):
    p0, p1 = flipper.endpoints()
    q = nearest_point_on_segment(p0, p1, ball.pos)
    d = ball.pos - q
    dist = d.length()
    R = ball.radius + flipper.radius
    if dist == 0:
        n = (p1 - p0)
        if n.length() == 0:
            return False
        n = perp(n).normalize()
    else:
        n = d / (dist + 1e-9)

    if dist < R:
        # Surface velocity due to flipper rotation around pivot:
        r = q - flipper.pivot
        v_surface = perp(r) * flipper.omega  # omega x r in 2D
        # Separate
        ball.pos += n * (R - dist + 0.01)
        # Relative normal velocity
        v_rel = (ball.vel - v_surface).dot(n)
        if v_rel < 0:
            ball.vel -= (1.0 + restitution) * v_rel * n
            # Add some tangential "grab"
            t = perp(n)
            vt_rel = (ball.vel - v_surface).dot(t)
            ball.vel -= 0.15 * vt_rel * t
        return True
    return False

def collide_ball_bumper(ball: Ball, bumper: Bumper) -> bool:
    d = ball.pos - bumper.pos
    dist = d.length()
    R = ball.radius + bumper.radius
    if dist < R:
        n = d.normalize() if dist > 1e-6 else Vec2(0, -1)
        ball.pos += n * (R - dist + 0.01)
        vn = ball.vel.dot(n)
        # Bumpers kick hard
        ball.vel -= (1.0 + bumper.strength) * vn * n
        # Add a little extra pop
        ball.vel += n * 200
        return True
    return False

# --------------------------------------------
# Game
# --------------------------------------------

class PinballGame:
    def __init__(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        pygame.display.set_caption("Pygame Pinball (2.5D) — files=off, game=on")
        self.W, self.H = 640, 960
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.fullscreen = False

        # Colors
        self.bg_dark = (16, 20, 26)
        self.table_top = (32, 50, 70)
        self.table_side = (22, 30, 40)
        self.line_col = (90, 150, 200)

        # Sound
        self.sound = SoundBank(enabled=True)
        self.muted = False

        # Fonts
        self.font_small = pygame.font.SysFont(None, 22)
        self.font = pygame.font.SysFont(None, 30)
        self.font_big = pygame.font.SysFont(None, 48)

        # Geometry
        self.field_left  = 110
        self.field_right = 510
        self.field_top   = 110
        self.field_bottom= 860

        self.lane_left   = 530
        self.lane_right  = 600

        # Physics
        self.gravity = Vec2(0, 1600)
        self.damping = 0.995

        # World
        self.segments: List[Segment] = []
        self.slings: List[Segment] = []
        self.bumpers: List[Bumper] = []
        self._build_table()

        # Flippers
        self.left_flipper = Flipper(
            pivot=Vec2(270, 790), length=120, radius=10, is_left=True,
            open_angle=math.radians(22), closed_angle=math.radians(70),
            angle=math.radians(22)
        )
        self.right_flipper = Flipper(
            pivot=Vec2(350, 790), length=120, radius=10, is_left=False,
            open_angle=math.radians(158), closed_angle=math.radians(110),
            angle=math.radians(158)
        )

        # Plunger
        self.plunger = Plunger(
            x=(self.lane_left + self.lane_right) * 0.5,
            top_y=140, bottom_y=self.field_bottom
        )

        # Ball & game state
        self.ball: Ball = Ball(pos=Vec2(self.plunger.x, self.field_bottom-10), vel=Vec2(0, 0))
        self.score = 0
        self.balls_left = 3
        self.multiplier = 1
        self.paused = False
        self.tilt = False
        self.tilt_meter = 0.0

        # Visual assets
        for b in self.bumpers:
            b.glow = radial_glow(int(b.radius * 1.3), (110, 180, 255), intensity=0.6)
        self.bumper_flash_timer = 0.0

        # Joystick / gamepad (optional)
        pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if self.joy:
            self.joy.init()

    # -------------------------- Table & layout --------------------------

    def _build_table(self):
        L, R, T, B = self.field_left, self.field_right, self.field_top, self.field_bottom
        laneL, laneR = self.lane_left, self.lane_right

        # Outer walls (rectangle minus drain gap)
        self.segments += [
            Segment(Vec2(L, T), Vec2(R, T), 0.4),             # top
            Segment(Vec2(L, T), Vec2(L, B-60), 0.4),          # left
            Segment(Vec2(R, T), Vec2(R, B-60), 0.4),          # right (main field)
            # bottom edges slanted toward drain gap
            Segment(Vec2(L, B-60), Vec2(260, B), 0.4),
            Segment(Vec2(R, B-60), Vec2(360, B), 0.4),
        ]

        # Drain detector (invisible): gap between x=260..360 at B
        self.drain_x1, self.drain_x2, self.drain_y = 260, 360, B + 6

        # Slingshots above flippers (more bouncy)
        self.slings += [
            Segment(Vec2(L+40, B-220), Vec2(250, B-120), 1.2, "slings"),
            Segment(Vec2(R-40, B-220), Vec2(370, B-120), 1.2, "slings"),
        ]

        # Launch lane walls
        self.segments += [
            Segment(Vec2(laneL, T), Vec2(laneL, B), 0.4),     # lane left
            Segment(Vec2(laneR, T), Vec2(laneR, B), 0.4),     # lane right
            Segment(Vec2(laneL, B), Vec2(laneR, B), 0.3),     # lane floor (for resting)
        ]

        # One-way gate into field (angled deflector near top of lane)
        self.segments += [
            Segment(Vec2(laneL, T+30), Vec2(R, T+60), 0.6),   # deflect into field
        ]

        # Bumpers
        self.bumpers += [
            Bumper(Vec2(200, 250), 28, strength=1.35, score_value=150),
            Bumper(Vec2(350, 220), 28, strength=1.35, score_value=150),
            Bumper(Vec2(275, 340), 34, strength=1.45, score_value=250),
        ]

    # -------------------------- Game loop --------------------------

    def run(self):
        while True:
            dt = self.clock.tick(120) / 1000.0
            dt = min(dt, 1/30)  # avoid huge steps
            self.handle_events()
            if not self.paused:
                self.update(dt)
            self.draw()

    # -------------------------- Input --------------------------

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                elif e.key == pygame.K_f:
                    self.toggle_fullscreen()
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key == pygame.K_m:
                    self.muted = not self.muted
                    self.sound.enabled = not self.muted
                elif e.key == pygame.K_n:
                    if self.balls_left <= 0:
                        self.new_game()
                elif e.key == pygame.K_SPACE:
                    if self.ball.in_lane and self.ball.alive and not self.tilt:
                        self.plunger.pulling = True
                elif e.key == pygame.K_x:
                    self.left_flipper.pressed = True
                    self.right_flipper.pressed = True
                elif e.key == pygame.K_z:
                    self.left_flipper.pressed = True
                elif e.key == pygame.K_SLASH:
                    self.right_flipper.pressed = True

            if e.type == pygame.KEYUP:
                if e.key == pygame.K_SPACE:
                    self.release_plunger()
                elif e.key == pygame.K_x:
                    self.left_flipper.pressed = False
                    self.right_flipper.pressed = False
                elif e.key == pygame.K_z:
                    self.left_flipper.pressed = False
                elif e.key == pygame.K_SLASH:
                    self.right_flipper.pressed = False

            # Joystick/gamepad handling
            if self.joy:
                if e.type == pygame.JOYBUTTONDOWN:
                    # L1 (4), R1 (5) typical on SDL; Cross (0) for plunger
                    if e.button == 4:
                        self.left_flipper.pressed = True
                    elif e.button == 5:
                        self.right_flipper.pressed = True
                    elif e.button == 0:  # Cross
                        if self.ball.in_lane and self.ball.alive and not self.tilt:
                            self.plunger.pulling = True
                if e.type == pygame.JOYBUTTONUP:
                    if e.button == 4:
                        self.left_flipper.pressed = False
                    elif e.button == 5:
                        self.right_flipper.pressed = False
                    elif e.button == 0:  # Cross
                        self.release_plunger()
                if e.type == pygame.JOYHATMOTION:
                    # D-Pad nudge
                    hatx, haty = e.value
                    if hatx != 0 or haty != 0:
                        self.nudge(hatx * 120, -haty * 120)

        # Keyboard nudge (hold briefly)
        keys = pygame.key.get_pressed()
        if not self.tilt:
            if keys[pygame.K_LEFT]:
                self.nudge(-120, 0)
            if keys[pygame.K_RIGHT]:
                self.nudge(120, 0)
            if keys[pygame.K_UP]:
                self.nudge(0, -140)

        # Analog trigger for plunger (R2 axis ~ 5 or 4 on many pads)
        if self.joy and self.ball.in_lane and self.ball.alive and not self.tilt:
            # Try several common trigger axes
            for axis in (4, 5, 2):
                if axis < self.joy.get_numaxes():
                    val = self.joy.get_axis(axis)
                    if val > 0.4:
                        self.plunger.pulling = True
                        break

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.W, self.H), pygame.RESIZABLE)

    def release_plunger(self):
        if self.plunger.pulling and self.ball.in_lane and self.ball.alive and not self.tilt:
            power = 0.6 * self.plunger.power + 450.0
            self.ball.vel = Vec2(0, -power)
            self.ball.in_lane = True  # still in lane until deflected at the top
            self.plunger.pulling = False
            self.plunger.power = 0.0
            self.score_flash(20)
            self.sound.play("launch")

    def nudge(self, dx, dy):
        if not self.ball.alive:
            return
        impulse = Vec2(dx, dy)
        self.ball.vel += impulse
        self.tilt_meter += (abs(dx) + abs(dy)) / 550.0
        self.sound.play("nudge")
        if self.tilt_meter > 1.0:
            self.tilt = True  # lock flippers until ball drains

    # -------------------------- Update & rules --------------------------

    def update(self, dt: float):
        # Update flippers & plunger
        self.left_flipper.update(dt)
        self.right_flipper.update(dt)
        self.plunger.update(dt)

        # Decay tilt meter slowly
        self.tilt_meter = max(0.0, self.tilt_meter - 0.15 * dt)

        # Ball physics
        if self.ball.alive:
            substeps = 3
            sdt = dt / substeps
            for _ in range(substeps):
                self.ball.vel += self.gravity * sdt
                self.ball.pos += self.ball.vel * sdt
                self.ball.vel *= self.damping

                # Collide with walls
                for seg in self.segments:
                    if collide_ball_segment(self.ball, seg) and seg.tag == "wall":
                        pass

                # Collide with slings (more bounce + score)
                for s in self.slings:
                    if collide_ball_segment(self.ball, s):
                        self.score += 50 * self.multiplier
                        self.sound.play("slings")

                # Collide with flippers (unless tilted)
                if not self.tilt:
                    lf_hit = collide_ball_capsule_with_flipper(self.ball, self.left_flipper)
                    rf_hit = collide_ball_capsule_with_flipper(self.ball, self.right_flipper)
                    if lf_hit or rf_hit:
                        self.score += 10 * self.multiplier
                        self.sound.play("flipper")

                # Collide with bumpers
                any_bumper = False
                for b in self.bumpers:
                    if collide_ball_bumper(self.ball, b):
                        self.score += b.score_value * self.multiplier
                        any_bumper = True
                if any_bumper:
                    self.bumper_flash_timer = 0.08
                    self.sound.play("bumper")

                # Keep ball inside horizontal bounds (main field)
                self.ball.pos.x = clamp(self.ball.pos.x, self.field_left + self.ball.radius, self.lane_right - self.ball.radius)

                # Lane → field deflection detection (near the angled segment)
                if self.ball.in_lane and self.ball.pos.y < (self.field_top + 120):
                    # Once near the deflector, mark as "in play"
                    self.ball.in_lane = False

                # Drain check (missed by flippers)
                if (self.drain_x1 < self.ball.pos.x < self.drain_x2) and (self.ball.pos.y > self.drain_y):
                    self.ball.alive = False
                    self.sound.play("drain")
                    break

        # After drain
        if not self.ball.alive:
            if self.balls_left > 0:
                self.balls_left -= 1
                self.reset_ball()
            else:
                # Game over; wait for N
                pass

        # Bumper flash timer decay
        self.bumper_flash_timer = max(0.0, self.bumper_flash_timer - dt)

    def reset_ball(self):
        # Reset tilt when the ball is lost
        self.tilt = False
        self.tilt_meter = 0.0
        self.ball = Ball(pos=Vec2(self.plunger.x, self.field_bottom - 10), vel=Vec2(0, 0), in_lane=True, alive=True)

    def new_game(self):
        self.score = 0
        self.balls_left = 3
        self.multiplier = 1
        self.reset_ball()

    def score_flash(self, amount):
        self.score += amount * self.multiplier

    # -------------------------- Draw --------------------------

    def draw_table(self, surf: pygame.Surface):
        W, H = surf.get_size()
        # Backdrop gradient (simple two-layer)
        surf.fill(self.bg_dark)
        g = radial_glow(480, (60, 100, 160), intensity=0.25, steps=24)
        surf.blit(g, (W//2 - 480, H//2 - 520))

        # Table well (rounded rectangle illusion)
        pygame.draw.rect(surf, self.table_side, (self.field_left-18, self.field_top-18,
                                                 (self.field_right - self.field_left)+36,
                                                 (self.field_bottom - self.field_top)+80), border_radius=28)
        pygame.draw.rect(surf, self.table_top, (self.field_left, self.field_top,
                                                (self.field_right - self.field_left),
                                                (self.field_bottom - self.field_top)+40), border_radius=22)

        # Launch lane
        pygame.draw.rect(surf, (28, 36, 48), (self.lane_left-20, self.field_top-18,
                                              (self.lane_right - (self.lane_left-20)),
                                              (self.field_bottom - self.field_top)+80), border_radius=22)
        pygame.draw.rect(surf, (36, 48, 64), (self.lane_left, self.field_top,
                                              (self.lane_right - self.lane_left),
                                              (self.field_bottom - self.field_top)+40), border_radius=18)

        # Walls and slings
        for s in self.segments + self.slings:
            col = self.line_col if s.tag != "slings" else (150, 220, 255)
            pygame.draw.line(surf, col, s.a, s.b, 6)

        # Drain mouth
        pygame.draw.line(surf, (200, 80, 80), (self.drain_x1, self.field_bottom+4), (self.drain_x2, self.field_bottom+4), 6)

        # Bumpers
        for b in self.bumpers:
            # Glow
            if b.glow:
                rect = b.glow.get_rect(center=(int(b.pos.x), int(b.pos.y)))
                surf.blit(b.glow, rect.topleft)
            # Body
            pygame.draw.circle(surf, (180, 200, 255), b.pos, int(b.radius))
            pygame.draw.circle(surf, (90, 140, 220), b.pos, int(b.radius), 4)
            # Flash ring
            if self.bumper_flash_timer > 0:
                pygame.draw.circle(surf, (255, 255, 255), b.pos, int(b.radius + 6), 3)

    def draw_flipper(self, surf: pygame.Surface, fl: Flipper):
        p0, p1 = fl.endpoints()
        # Shadow
        shadow = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(shadow, (0,0,0,120), p0 + Vec2(6,10), p1 + Vec2(6,10), int(fl.radius*2)+2)
        surf.blit(shadow, (0,0))
        # Body
        pygame.draw.line(surf, (220, 220, 230), p0, p1, int(fl.radius*2))
        pygame.draw.line(surf, (90, 110, 140), p0, p1, 4)
        pygame.draw.circle(surf, (210,210,220), p0, int(fl.radius*1.2))
        pygame.draw.circle(surf, (60, 80, 110), p0, int(fl.radius*1.2), 2)

    def draw_hud(self, surf: pygame.Surface):
        # Top HUD bar
        pygame.draw.rect(surf, (15, 20, 26), (0, 0, surf.get_width(), 80))
        txt = self.font.render(f"Score: {self.score:,}", True, (220, 230, 240))
        balls = self.font.render(f"Balls: {self.balls_left}", True, (220, 230, 240))
        mult = self.font.render(f"Mult: x{self.multiplier}", True, (220, 230, 240))
        surf.blit(txt, (20, 18))
        surf.blit(balls, (260, 18))
        surf.blit(mult, (440, 18))

        # Tilt indicator
        if self.tilt:
            t = self.font_big.render("TILT", True, (255, 150, 150))
            surf.blit(t, (surf.get_width()//2 - t.get_width()//2, 18))

        # Plunger power bar
        if self.ball.in_lane and self.ball.alive:
            p = int(180 * (self.plunger.power / self.plunger.max_power))
            pygame.draw.rect(surf, (40, 60, 90), (self.lane_left+5, self.field_bottom-30, (self.lane_right-self.lane_left)-10, 16), border_radius=8)
            pygame.draw.rect(surf, (120, 200, 255), (self.lane_left+5, self.field_bottom-30, p*((self.lane_right-self.lane_left)-10)//180, 16), border_radius=8)

        # Help ribbon
        help1 = self.font_small.render("Z=/ flippers • X both • Space plunge • Arrows nudge • P pause • F fullscreen • M mute", True, (210, 220, 230))
        surf.blit(help1, (20, 54))

    def draw_ball_and_plunger(self, surf: pygame.Surface):
        # Plunger head
        y = clamp(self.field_bottom - self.plunger.power * 0.05, self.field_top + 60, self.field_bottom - 6)
        pygame.draw.line(surf, (200, 200, 220), (self.plunger.x, y), (self.plunger.x, y+24), 10)
        # Ball
        draw_ball(surf, self.ball.pos, int(self.ball.radius))

    def draw(self):
        self.draw_table(self.screen)
        # Flippers (disable motion drawing when tilted? still draw static)
        self.draw_flipper(self.screen, self.left_flipper)
        self.draw_flipper(self.screen, self.right_flipper)
        # Ball + plunger
        self.draw_ball_and_plunger(self.screen)
        # HUD
        self.draw_hud(self.screen)

        # Messages
        if self.balls_left <= 0 and not self.ball.alive:
            self.center_text("GAME OVER — press N for new game", y=460)
        elif self.ball.in_lane and self.ball.alive:
            self.center_text("Hold SPACE (or Cross/R2) to pull plunger", y=460)

        pygame.display.flip()

    def center_text(self, text, y):
        t = self.font_big.render(text, True, (235, 245, 255))
        self.screen.blit(t, (self.screen.get_width()//2 - t.get_width()//2, y))


# --------------------------------------------
# Main
# --------------------------------------------

if __name__ == "__main__":
    try:
        PinballGame().run()
    except Exception as e:
        print("Error:", e)
        pygame.quit()
        sys.exit(1)
