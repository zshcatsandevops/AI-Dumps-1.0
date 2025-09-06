# program.py
"""
Paper 64 — a tiny, single-file 'paper character in N64-style 3D' demo in pure Pygame.
- No external files/assets (everything is procedural).
- Software 3D (perspective projection, back-face culling, painter's algorithm).
- Flat shading, simple directional light, and optional distance fog.
- Low-res internal render scaled up for crunchy N64-ish look.
- A billboard "paper" hero that can flip paper-thin.

Controls:
  W/S = move forward/back, A/D = strafe, Arrow Left/Right = yaw, Arrow Up/Down = pitch
  F = flip the paper hero, O = toggle outlines, G = toggle fog
  1 / 2 = decrease/increase pixelation (render scale)
  ESC = quit
"""

import math
import sys
import time
import random
import pygame

# -----------------------------
# Basic vector math (tuple-based)
# -----------------------------
def v_add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def v_sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def v_mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def v_dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def v_cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def v_len(a): return math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2])
def v_norm(a):
    L = v_len(a)
    if L < 1e-8: return (0.0, 0.0, 0.0)
    return (a[0]/L, a[1]/L, a[2]/L)

def clamp(x, lo, hi): 
    if x < lo: return lo
    if x > hi: return hi
    return x

def lerp(a, b, t): return a*(1.0-t) + b*t
def mix_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))

# -----------------------------
# Camera transforms & projection
# -----------------------------
def world_to_camera(p, cam_pos, yaw, pitch):
    # Translate
    x = p[0] - cam_pos[0]
    y = p[1] - cam_pos[1]
    z = p[2] - cam_pos[2]
    # Rotate by -yaw around Y
    cy, sy = math.cos(yaw), math.sin(yaw)
    x2 =  cy*x + sy*z
    z2 = -sy*x + cy*z
    # Rotate by -pitch around X
    cp, sp = math.cos(pitch), math.sin(pitch)
    y3 =  cp*y + sp*z2
    z3 = -sp*y + cp*z2
    return (x2, y3, z3)

def dir_world_to_camera(d, yaw, pitch):
    # Rotate a direction vector by -yaw, -pitch (no translate)
    cy, sy = math.cos(yaw), math.sin(yaw)
    x2 =  cy*d[0] + sy*d[2]
    z2 = -sy*d[0] + cy*d[2]
    cp, sp = math.cos(pitch), math.sin(pitch)
    y3 =  cp*d[1] + sp*z2
    z3 = -sp*d[1] + cp*z2
    return (x2, y3, z3)

def project(cam_pt, w, h, focal, near):
    x, y, z = cam_pt
    if z <= near: 
        return None
    sx = w*0.5 + (x * focal) / z
    sy = h*0.5 - (y * focal) / z
    return (sx, sy)

# -----------------------------
# Simple mesh builders (triangles)
# Each triangle: {"v": [(x,y,z), (x,y,z), (x,y,z)], "color": (r,g,b)}
# -----------------------------
def make_cube(center=(0,0,0), size=1.0, color=(180,180,190)):
    cx, cy, cz = center
    s = size * 0.5
    # 8 vertices
    v = [
        (cx - s, cy - s, cz - s),
        (cx + s, cy - s, cz - s),
        (cx + s, cy + s, cz - s),
        (cx - s, cy + s, cz - s),
        (cx - s, cy - s, cz + s),
        (cx + s, cy - s, cz + s),
        (cx + s, cy + s, cz + s),
        (cx - s, cy + s, cz + s),
    ]
    # Faces as triangles (CCW outward)
    faces = [
        (0,1,2,3),  # back  (-Z)
        (5,4,7,6),  # front (+Z)
        (4,0,3,7),  # left  (-X)
        (1,5,6,2),  # right (+X)
        (4,5,1,0),  # bottom(-Y)
        (3,2,6,7),  # top   (+Y)
    ]
    out = []
    # Slight color variation per face for readability
    face_tints = [(0,0,-20), (0,0,10), (-10,0,0), (10,0,0), (0,-10,0), (20,20,20)]
    for f_i, (a,b,c,d) in enumerate(faces):
        ca = tuple(clamp(color[i] + face_tints[f_i][i], 0, 255) for i in range(3))
        # two triangles
        out.append({"v":[v[a], v[b], v[c]], "color":ca})
        out.append({"v":[v[a], v[c], v[d]], "color":ca})
    return out

def make_ground(y=0.0, half=12.0, cells=12, base_color=(70,130,90)):
    """Checkerboard-ish low-poly ground plane split into grid triangles with upward normals."""
    tris = []
    step = (half*2.0)/cells
    for i in range(cells):
        for j in range(cells):
            x0 = -half + i*step
            z0 = -half + j*step
            x1 = x0 + step
            z1 = z0 + step

            # CCW order from above: (x0,z0)->(x1,z0)->(x1,z1)->(x0,z1)
            v0 = (x0, y, z0)
            v1 = (x1, y, z0)
            v2 = (x1, y, z1)
            v3 = (x0, y, z1)

            # Alternate tint for checkerboard
            alt = ((i + j) & 1) == 0
            tint = 12 if alt else -12
            c = tuple(clamp(base_color[k] + tint, 0, 255) for k in range(3))

            # Two triangles with normals +Y (ensure consistent winding)
            tris.append({"v":[v0, v1, v2], "color":c})
            tris.append({"v":[v0, v3, v2], "color":c})
    return tris

def make_pillar(x, z, height=2.5, size=0.8, color=(150,110,80)):
    """A simple box pillar sitting on ground."""
    cy = height * 0.5
    return make_cube(center=(x, cy, z), size=size, color=color)

# -----------------------------
# Paper hero sprite (procedural)
# -----------------------------
def build_paper_hero_surface(t_ms, w=64, h=96):
    """Return a per-frame paper hero Surface (blink + bob), with alpha."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf = surf.convert_alpha()
    # Paper rectangle
    rect_color = (245, 245, 235)
    border = (10, 10, 10)
    pygame.draw.rect(surf, rect_color, (2, 2, w-4, h-4), border_radius=6)
    pygame.draw.rect(surf, border,      (2, 2, w-4, h-4), width=3, border_radius=6)

    # A simple face (friendly, non-IP)
    # Blink every ~3 seconds for 160ms
    blink = (t_ms % 3000) < 160
    eye_h = 10 if not blink else 2
    eye_w = 12
    eye_y = h*0.35
    eye_x_off = 16
    eye_color = (20, 20, 20)
    pygame.draw.ellipse(surf, eye_color, (w*0.5 - eye_x_off - eye_w, eye_y, eye_w, eye_h))
    pygame.draw.ellipse(surf, eye_color, (w*0.5 + eye_x_off,        eye_y, eye_w, eye_h))

    # Simple smile
    mouth_w = 28
    mouth_h = 14
    mouth_y = int(h*0.62)
    pygame.draw.arc(surf, (30,30,30), (int(w*0.5 - mouth_w/2), mouth_y, mouth_w, mouth_h), 
                    math.radians(10), math.radians(170), 2)

    # Suggest a little "crease"
    pygame.draw.line(surf, (40,40,40), (int(w*0.2), int(h*0.2)), (int(w*0.35), int(h*0.15)), 1)
    pygame.draw.line(surf, (40,40,40), (int(w*0.65), int(h*0.25)), (int(w*0.8), int(h*0.2)), 1)
    return surf

def draw_paper_hero(lowres_surface, hero_world_pos, cam_pos, yaw, pitch, focal, rw, rh,
                    near, world_height=1.75, width_scale=1.0, t_ms=0):
    """Billboard paper hero facing camera. Draw shadow and sprite scaled by distance."""
    # Project ground point for shadow
    ground_world = (hero_world_pos[0], 0.0, hero_world_pos[2])
    cpt_ground = world_to_camera(ground_world, cam_pos, yaw, pitch)
    if cpt_ground[2] > near:
        ground_px = project(cpt_ground, rw, rh, focal, near)
    else:
        ground_px = None

    # Paper hero position (center-bottom anchored)
    cpt = world_to_camera(hero_world_pos, cam_pos, yaw, pitch)
    if cpt[2] <= near:
        return  # behind camera or too close

    # Scale by perspective: world_height -> pixel height
    pix_h = max(1, int((focal * world_height) / cpt[2]))
    pix_w = max(1, int(pix_h * 0.65 * width_scale))  # thin card when flipped

    # Shadow (ellipse with alpha) — projected at ground point
    if ground_px is not None:
        shadow_radius_world = 0.45
        shadow_pix_w = int((focal * shadow_radius_world) / max(cpt_ground[2], 0.1))
        shadow_pix_h = max(2, int(shadow_pix_w * 0.45))
        sh = pygame.Surface((shadow_pix_w*2, shadow_pix_h*2), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0,0,0,85), (0, 0, sh.get_width(), sh.get_height()))
        lowres_surface.blit(sh, (ground_px[0] - sh.get_width()/2, ground_px[1] - sh.get_height()/2))

    # Build face (with blink)
    sprite = build_paper_hero_surface(t_ms, 64, 96)
    sprite = pygame.transform.smoothscale(sprite, (pix_w, pix_h)) if pix_w*pix_h < 20000 else pygame.transform.scale(sprite, (pix_w, pix_h))
    anchor_x = int((rw*0.5 + (cpt[0]*focal)/cpt[2]) - pix_w/2)
    anchor_y = int((rh*0.5 - (cpt[1]*focal)/cpt[2]) - pix_h)   # anchor to feet
    lowres_surface.blit(sprite, (anchor_x, anchor_y))

# -----------------------------
# Renderer
# -----------------------------
class Renderer:
    def __init__(self, rw, rh, fov_deg=70.0, near=0.1, far=120.0):
        self.rw, self.rh = rw, rh
        self.near, self.far = near, far
        self.fov = math.radians(fov_deg)
        self.focal = (rw * 0.5) / math.tan(self.fov * 0.5)
        self.fog_color = (92, 112, 138)
        self.fog_on = True
        self.outlines = True
        # Lighting
        self.ambient = 0.28
        self.light_dir_world = v_norm((0.55, 0.85, -0.3))  # above and slightly behind camera

    def set_size(self, rw, rh):
        self.rw, self.rh = rw, rh
        self.focal = (rw * 0.5) / math.tan(self.fov * 0.5)

    def shade(self, base_color, n_cam, light_cam):
        # Simple Lambert with ambient; light vector points *from* light *toward* scene
        lambert = max(0.0, -v_dot(n_cam, light_cam))
        shade = self.ambient + lambert * (1.0 - self.ambient)
        return (int(base_color[0]*shade), int(base_color[1]*shade), int(base_color[2]*shade))

    def fog_mix(self, color, z, fog_start=18.0, fog_end=60.0):
        if not self.fog_on:
            return color
        t = clamp((z - fog_start) / (fog_end - fog_start), 0.0, 1.0)
        return mix_color(color, self.fog_color, t)

    def draw_triangles(self, lowres_surface, tris_world, cam_pos, yaw, pitch):
        light_cam = dir_world_to_camera(self.light_dir_world, yaw, pitch)

        draw_list = []
        near = self.near
        rw, rh, focal = self.rw, self.rh, self.focal

        # Transform, cull, shade, project
        for tri in tris_world:
            a_w, b_w, c_w = tri["v"]
            a = world_to_camera(a_w, cam_pos, yaw, pitch)
            b = world_to_camera(b_w, cam_pos, yaw, pitch)
            c = world_to_camera(c_w, cam_pos, yaw, pitch)

            if a[2] <= near or b[2] <= near or c[2] <= near:
                # (No near-plane clipping; keep it simple)
                continue

            # Back-face culling via normal · centroid sign (camera at origin, facing +Z)
            ab = v_sub(b, a)
            ac = v_sub(c, a)
            n = v_norm(v_cross(ab, ac))
            centroid = ((a[0]+b[0]+c[0]) / 3.0, (a[1]+b[1]+c[1]) / 3.0, (a[2]+b[2]+c[2]) / 3.0)
            if v_dot(n, centroid) >= 0.0:
                continue

            # Shade (flat)
            base_color = tri["color"]
            color = self.shade(base_color, n, light_cam)
            color = self.fog_mix(color, centroid[2])

            # Project to 2D
            pa = project(a, rw, rh, focal, near)
            pb = project(b, rw, rh, focal, near)
            pc = project(c, rw, rh, focal, near)
            if not pa or not pb or not pc:
                continue

            draw_list.append({
                "pts": [pa, pb, pc],
                "z": centroid[2],
                "color": color
            })

        # Painter's algorithm (far -> near)
        draw_list.sort(key=lambda t: t["z"], reverse=True)

        # Draw
        pg = pygame
        for item in draw_list:
            pts = item["pts"]
            pg.draw.polygon(lowres_surface, item["color"], pts)
            if self.outlines:
                pg.draw.polygon(lowres_surface, (10,10,10), pts, 1)

# -----------------------------
# World setup
# -----------------------------
def build_world():
    tris = []
    # Ground (y=0)
    tris.extend(make_ground(y=0.0, half=14.0, cells=12, base_color=(70, 135, 90)))

    # A few pillars / crates
    random.seed(4)
    positions = [(-5, 7), (-2, 5), (3, 6), (6, 4), (-7, 9), (0, 10)]
    for (x, z) in positions:
        tris.extend(make_pillar(x, z, height=random.uniform(1.6, 3.2),
                                size=random.uniform(0.7, 1.2),
                                color=(150, 110, 80)))
    # Some colored cubes as scenery
    tris.extend(make_cube(center=(0, 0.5, 3.0), size=1.0, color=(120,160,200)))
    tris.extend(make_cube(center=(-3.0, 0.5, 2.5), size=1.0, color=(200,140,120)))
    tris.extend(make_cube(center=(3.0, 1.0, 8.0), size=2.0, color=(160,120,180)))
    return tris

# -----------------------------
# Main application
# -----------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Paper 64 — Pygame demo (no files)")

    # Window size and low-res internal render (pixelation scale)
    WIDTH, HEIGHT = 960, 720
    render_scale = 3  # 1=crispy, 2/3/4=chunkier pixels (toggle with 1/2 keys)
    rw, rh = WIDTH // render_scale, HEIGHT // render_scale

    window = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    # Low-res working surface
    def make_lowres():
        return pygame.Surface((rw, rh)).convert()

    lowres = make_lowres()

    # Renderer & world
    renderer = Renderer(rw, rh, fov_deg=70.0, near=0.1, far=120.0)
    world_tris = build_world()

    # Camera follows hero (3rd person)
    hero_pos = [0.0, 1.0, 0.0]
    hero_speed = 3.5
    yaw, pitch = 0.0, math.radians(-8.0)  # slight down angle
    cam_height = 2.2
    cam_distance = 3.8

    # Flip animation for paper hero (drives width_scale)
    flip_state = 1.0      # 1.0 normal width, ~0.07 edge-on
    flip_target = 1.0
    flip_speed = 6.0      # interp speed

    running = True
    t0 = time.perf_counter()
    outlines_info = True
    fog_info = True

    while running:
        dt = clock.tick(60) / 1000.0
        t_ms = int((time.perf_counter() - t0) * 1000)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_f:
                    # Toggle flip (animate towards thin or normal)
                    flip_target = 0.07 if flip_state > 0.5 else 1.0
                elif e.key == pygame.K_o:
                    renderer.outlines = not renderer.outlines
                    outlines_info = True
                elif e.key == pygame.K_g:
                    renderer.fog_on = not renderer.fog_on
                    fog_info = True
                elif e.key == pygame.K_1:
                    render_scale = clamp(render_scale + 1, 1, 6)
                    rw, rh = WIDTH // render_scale, HEIGHT // render_scale
                    renderer.set_size(rw, rh)
                    lowres = pygame.Surface((rw, rh)).convert()
                elif e.key == pygame.K_2:
                    render_scale = clamp(render_scale - 1, 1, 6)
                    rw, rh = WIDTH // render_scale, HEIGHT // render_scale
                    renderer.set_size(rw, rh)
                    lowres = pygame.Surface((rw, rh)).convert()

        # Camera/hero movement
        keys = pygame.key.get_pressed()
        turn_speed = math.radians(85.0) * dt
        move = [0.0, 0.0, 0.0]

        if keys[pygame.K_LEFT]:
            yaw -= turn_speed
        if keys[pygame.K_RIGHT]:
            yaw += turn_speed
        if keys[pygame.K_UP]:
            pitch = clamp(pitch - math.radians(65.0) * dt, math.radians(-60.0), math.radians(60.0))
        if keys[pygame.K_DOWN]:
            pitch = clamp(pitch + math.radians(65.0) * dt, math.radians(-60.0), math.radians(60.0))

        # Movement relative to yaw
        forward = (math.sin(yaw), 0.0, math.cos(yaw))  # camera/hero forward (looks along +Z)
        right   = (math.cos(yaw), 0.0, -math.sin(yaw))

        speed = hero_speed * (1.6 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1.0)
        if keys[pygame.K_w]:
            move = v_add(move, v_mul(forward, speed * dt))
        if keys[pygame.K_s]:
            move = v_add(move, v_mul(forward, -speed * dt))
        if keys[pygame.K_a]:
            move = v_add(move, v_mul(right, -speed * dt))
        if keys[pygame.K_d]:
            move = v_add(move, v_mul(right,  speed * dt))

        hero_pos[0] += move[0]
        hero_pos[2] += move[2]
        # keep on ground
        hero_pos[1] = 1.0

        # Follow camera (3rd person)
        cam_pos = (
            hero_pos[0] - forward[0]*cam_distance,
            hero_pos[1] + cam_height,
            hero_pos[2] - forward[2]*cam_distance
        )

        # Flip animation lerp
        flip_state = lerp(flip_state, flip_target, clamp(flip_speed * dt, 0.0, 1.0))

        # Bobbing offset for hero (cute bounce)
        bob = math.sin(t_ms*0.006) * 0.06
        hero_draw_pos = (hero_pos[0], 1.0 + bob, hero_pos[2])

        # --- Render to low-res surface ---
        # Sky/background
        lowres.fill((92, 112, 138))  # fog/sky color matches renderer.fog_color

        # World
        renderer.draw_triangles(lowres, world_tris, cam_pos, yaw, pitch)

        # Paper hero (billboard)
        draw_paper_hero(
            lowres, hero_draw_pos, cam_pos, yaw, pitch,
            renderer.focal, renderer.rw, renderer.rh,
            renderer.near, world_height=1.75,
            width_scale=flip_state, t_ms=t_ms
        )

        # UI overlay (draw on window after scaling)
        scaled = pygame.transform.scale(lowres, (WIDTH, HEIGHT))
        window.blit(scaled, (0,0))

        # HUD
        fps = clock.get_fps()
        hud_lines = [
            f"FPS: {fps:5.1f}   Render Scale: {render_scale}x   Tris: {len(world_tris)}",
            "WASD move  |  Arrows look  |  F flip  |  O outlines  |  G fog  |  1/2 pixelation  |  Esc quit"
        ]
        if outlines_info:
            hud_lines.append(f"Outlines: {'ON' if renderer.outlines else 'OFF'}")
        if fog_info:
            hud_lines.append(f"Fog: {'ON' if renderer.fog_on else 'OFF'}")

        y = 8
        for line in hud_lines:
            text = font.render(line, True, (240,240,240))
            window.blit(text, (10, y))
            y += 18

        # Reset one-shot info lines after display ~1 sec
        if outlines_info or fog_info:
            if t_ms % 1000 > 850:
                outlines_info = False
                fog_info = False

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
