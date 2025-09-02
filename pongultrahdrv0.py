#!/usr/bin/env python3
import pygame, socket, threading, json, select, time, sys

# --- constants ---
WIDTH, HEIGHT = 640, 480
PADDLE_W, PADDLE_H = 12, 80
BALL_R = 8
MARGIN = 24
SPEED = 300
FPS = 60

DISC_PORT, TCP_PORT = 45200, 45201
TOKEN, REPLY = b"ULTRA_PONG", b"PONG_OK"

# --- helpers ---
def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj) + "\n").encode())
    except Exception:
        pass

def recv_json(sock, buf=b""):
    try:
        data = sock.recv(4096)
        if not data:
            return "__CLOSE__", buf
        buf += data
        if b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            return json.loads(line), buf
    except BlockingIOError:
        return None, buf
    except Exception:
        return "__CLOSE__", buf
    return None, buf

def discover(timeout=1.0):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(TOKEN, ("255.255.255.255", DISC_PORT))
        data, addr = s.recvfrom(1024)
        if data == REPLY:
            return (addr[0], TCP_PORT)
    except Exception:
        pass
    # fallback localhost
    try:
        socket.create_connection(("127.0.0.1", TCP_PORT), 0.2).close()
        return ("127.0.0.1", TCP_PORT)
    except Exception:
        return None

# --- server game loop ---
def host():
    # discovery responder
    def responder(stop):
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.bind(("", DISC_PORT))
        while not stop.is_set():
            try:
                d, a = u.recvfrom(1024)
            except:
                continue
            if d == TOKEN:
                u.sendto(REPLY, a)

    stop = threading.Event()
    threading.Thread(target=responder, args=(stop,), daemon=True).start()
    srv = socket.socket()
    srv.bind(("", TCP_PORT))
    srv.listen(1)
    srv.settimeout(0.5)

    gs = {
        "p1": HEIGHT // 2,
        "p2": HEIGHT // 2,
        "bx": WIDTH // 2,
        "by": HEIGHT // 2,
        "vx": SPEED,
        "vy": SPEED / 3,
        "s1": 0,
        "s2": 0,
    }
    client = None
    cbuf = b""

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)

    while True:
        dt = clock.tick(FPS) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                stop.set()
                return
        k = pygame.key.get_pressed()
        gs["p1"] += (-1 if k[pygame.K_w] else 1 if k[pygame.K_s] else 0) * SPEED * dt
        gs["p1"] = max(PADDLE_H // 2, min(HEIGHT - PADDLE_H // 2, gs["p1"]))

        # accept
        if not client:
            try:
                client, _ = srv.accept()
                client.setblocking(False)
                cbuf = b""
            except socket.timeout:
                pass

        # recv client input
        if client:
            msg, cbuf = recv_json(client, cbuf)
            if msg == "__CLOSE__":
                client.close()
                client = None
            elif msg and isinstance(msg, dict) and msg.get("type") == "in":
                gs["p2"] += msg["d"] * SPEED * dt
                gs["p2"] = max(PADDLE_H // 2, min(HEIGHT - PADDLE_H // 2, gs["p2"]))

        # physics
        gs["bx"] += gs["vx"] * dt
        gs["by"] += gs["vy"] * dt
        if gs["by"] - BALL_R < 0 or gs["by"] + BALL_R > HEIGHT:
            gs["vy"] *= -1
        if (
            gs["bx"] - BALL_R < MARGIN + PADDLE_W
            and abs(gs["by"] - gs["p1"]) < PADDLE_H / 2
        ):
            gs["vx"] = abs(gs["vx"])
        if (
            gs["bx"] + BALL_R > WIDTH - MARGIN - PADDLE_W
            and abs(gs["by"] - gs["p2"]) < PADDLE_H / 2
        ):
            gs["vx"] = -abs(gs["vx"])
        if gs["bx"] < 0:
            gs["s2"] += 1
            gs.update(
                {"bx": WIDTH // 2, "by": HEIGHT // 2, "vx": SPEED, "vy": SPEED / 3}
            )
        if gs["bx"] > WIDTH:
            gs["s1"] += 1
            gs.update(
                {"bx": WIDTH // 2, "by": HEIGHT // 2, "vx": -SPEED, "vy": SPEED / 3}
            )

        if client:
            send_json(client, {"type": "state", **gs})

        # draw
        screen.fill((0, 0, 0))
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (MARGIN, gs["p1"] - PADDLE_H // 2, PADDLE_W, PADDLE_H),
        )
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (WIDTH - MARGIN - PADDLE_W, gs["p2"] - PADDLE_H // 2, PADDLE_W, PADDLE_H),
        )
        pygame.draw.circle(
            screen, (255, 255, 255), (int(gs["bx"]), int(gs["by"])), BALL_R
        )
        txt = font.render(f"{gs['s1']}  {gs['s2']}", 1, (200, 200, 200))
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 20))
        pygame.display.flip()

# --- client game loop ---
def join(addr):
    sock = socket.create_connection(addr)
    sock.setblocking(False)
    buf = b""
    state = None
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)
    while True:
        dt = clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
        k = pygame.key.get_pressed()
        d = -1 if k[pygame.K_w] else 1 if k[pygame.K_s] else 0
        send_json(sock, {"type": "in", "d": d})
        msg, buf = recv_json(sock, buf)
        if msg == "__CLOSE__":
            return
        if msg and isinstance(msg, dict) and msg.get("type") == "state":
            state = msg
        screen.fill((0, 0, 0))
        if state:
            pygame.draw.rect(
                screen,
                (255, 255, 255),
                (MARGIN, state["p1"] - PADDLE_H // 2, PADDLE_W, PADDLE_H),
            )
            pygame.draw.rect(
                screen,
                (255, 255, 255),
                (WIDTH - MARGIN - PADDLE_W, state["p2"] - PADDLE_H // 2, PADDLE_W, PADDLE_H),
            )
            pygame.draw.circle(
                screen, (255, 255, 255), (int(state["bx"]), int(state["by"])), BALL_R
            )
            txt = font.render(f"{state['s1']}  {state['s2']}", 1, (200, 200, 200))
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 20))
        pygame.display.flip()

# --- main ---
if __name__ == "__main__":
    addr = discover()
    if addr:
        join(addr)
    else:
        host()
