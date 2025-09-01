#!/usr/bin/env python3
"""
Mario MMO - DS Download Play Style
Local network auto-discovery multiplayer game
Inspired by Super Mario RPG engine mechanics
Modified to incorporate 2.5D visual elements for platforms and ground
Added basic enemies and timed hit battle mechanics inspired by Super Mario RPG
"""

import pygame
import socket
import threading
import json
import time
import random
import struct
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15
MOVE_SPEED = 5
DEPTH = 20  # Depth for 2.5D effect

# Network Constants
BROADCAST_PORT = 54321
GAME_PORT = 54322
DISCOVERY_INTERVAL = 1.0
HEARTBEAT_INTERVAL = 0.5

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
SKY_BLUE = (135, 206, 235)
DARK_GREEN = (0, 200, 0)
DARKER_GREEN = (0, 150, 0)
DARK_BROWN = (100, 50, 10)

class PlayerState(Enum):
    IDLE = 0
    WALKING = 1
    JUMPING = 2
    FALLING = 3

class NetworkManager:
    def __init__(self):
        self.is_host = False
        self.players = {}
        self.local_id = str(random.randint(1000, 9999))
        self.discovery_socket = None
        self.game_socket = None
        self.running = True
        self.host_addr = None
        
    def start_discovery(self):
        """Start network discovery thread"""
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.bind(('', BROADCAST_PORT))
        self.discovery_socket.settimeout(0.5)
        
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        threading.Thread(target=self._broadcast_presence, daemon=True).start()
        
    def _discovery_loop(self):
        """Listen for other players"""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                msg = json.loads(data.decode())
                
                if msg['type'] == 'presence' and msg['id'] != self.local_id:
                    if msg['id'] not in self.players:
                        print(f"Player {msg['id']} joined from {addr[0]}")
                    
                    self.players[msg['id']] = {
                        'addr': addr[0],
                        'last_seen': time.time(),
                        'x': msg.get('x', 100),
                        'y': msg.get('y', 300),
                        'state': msg.get('state', 'IDLE')
                    }
            except socket.timeout:
                pass
            except Exception as e:
                pass
                
    def _broadcast_presence(self):
        """Broadcast our presence to network"""
        while self.running:
            try:
                msg = {
                    'type': 'presence',
                    'id': self.local_id,
                    'x': 0,
                    'y': 0,
                    'state': 'IDLE'
                }
                self.discovery_socket.sendto(
                    json.dumps(msg).encode(),
                    ('<broadcast>', BROADCAST_PORT)
                )
            except:
                pass
            time.sleep(DISCOVERY_INTERVAL)
            
    def update_player_position(self, x, y, state):
        """Send player position update"""
        try:
            msg = {
                'type': 'presence',
                'id': self.local_id,
                'x': x,
                'y': y,
                'state': state.name
            }
            self.discovery_socket.sendto(
                json.dumps(msg).encode(),
                ('<broadcast>', BROADCAST_PORT)
            )
        except:
            pass
            
    def cleanup_disconnected(self):
        """Remove players that haven't been seen recently"""
        current_time = time.time()
        to_remove = []
        for player_id, data in self.players.items():
            if current_time - data['last_seen'] > 3.0:
                to_remove.append(player_id)
        for player_id in to_remove:
            print(f"Player {player_id} disconnected")
            del self.players[player_id]

class Player:
    def __init__(self, x, y, color=RED, is_local=True):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.width = 30
        self.height = 40
        self.color = color
        self.is_local = is_local
        self.on_ground = False
        self.state = PlayerState.IDLE
        self.facing_right = True
        
    def update(self, platforms):
        if self.is_local:
            # Handle input
            keys = pygame.key.get_pressed()
            
            # Horizontal movement
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx = -MOVE_SPEED
                self.facing_right = False
                if self.on_ground:
                    self.state = PlayerState.WALKING
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx = MOVE_SPEED
                self.facing_right = True
                if self.on_ground:
                    self.state = PlayerState.WALKING
            else:
                self.vx *= 0.8  # Friction
                if self.on_ground and abs(self.vx) < 0.1:
                    self.state = PlayerState.IDLE
            
            # Jumping
            if (keys[pygame.K_SPACE] or keys[pygame.K_w]) and self.on_ground:
                self.vy = JUMP_STRENGTH
                self.state = PlayerState.JUMPING
        
        # Apply gravity
        if not self.on_ground:
            self.vy += GRAVITY
            if self.vy > 0:
                self.state = PlayerState.FALLING
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Check platform collisions
        self.on_ground = False
        for platform in platforms:
            if self.check_collision(platform):
                if self.vy > 0:  # Falling down
                    self.y = platform['y'] - self.height
                    self.vy = 0
                    self.on_ground = True
        
        # Keep player on screen
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.width))
        
        # Ground collision
        if self.y > SCREEN_HEIGHT - 100 - self.height:
            self.y = SCREEN_HEIGHT - 100 - self.height
            self.vy = 0
            self.on_ground = True
            
    def check_collision(self, platform):
        return (self.x < platform['x'] + platform['width'] and
                self.x + self.width > platform['x'] and
                self.y < platform['y'] + platform['height'] and
                self.y + self.height > platform['y'])
    
    def draw(self, screen):
        # Draw body
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        
        # Draw face details
        eye_y = self.y + 10
        if self.facing_right:
            pygame.draw.circle(screen, WHITE, (int(self.x + 20), eye_y), 4)
            pygame.draw.circle(screen, BLACK, (int(self.x + 22), eye_y), 2)
        else:
            pygame.draw.circle(screen, WHITE, (int(self.x + 10), eye_y), 4)
            pygame.draw.circle(screen, BLACK, (int(self.x + 8), eye_y), 2)
        
        # Draw hat (Mario style)
        hat_color = RED if self.color == RED else self.color
        pygame.draw.rect(screen, hat_color, (self.x - 2, self.y - 5, self.width + 4, 8))

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = -2
        self.vy = 0
        self.width = 30
        self.height = 30
        self.color = BROWN
        self.on_ground = False
        self.state = PlayerState.WALKING
        self.facing_right = False
        self.direction_change_time = time.time() + random.uniform(2, 5)
        
    def update(self, platforms):
        # AI movement
        if time.time() > self.direction_change_time:
            self.facing_right = not self.facing_right
            self.vx = -2 if not self.facing_right else 2
            self.direction_change_time = time.time() + random.uniform(2, 5)
        
        # Apply gravity
        if not self.on_ground:
            self.vy += GRAVITY
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Check platform collisions
        self.on_ground = False
        for platform in platforms:
            if self.check_collision(platform):
                if self.vy > 0:  # Falling down
                    self.y = platform['y'] - self.height
                    self.vy = 0
                    self.on_ground = True
        
        # Keep on screen
        self.x = max(0, min(self.x, SCREEN_WIDTH - self.width))
        
        # Ground collision
        if self.y > SCREEN_HEIGHT - 100 - self.height:
            self.y = SCREEN_HEIGHT - 100 - self.height
            self.vy = 0
            self.on_ground = True
            
    def check_collision(self, obj):
        return (self.x < obj['x'] + obj['width'] and
                self.x + self.width > obj['x'] and
                self.y < obj['y'] + obj['height'] and
                self.y + self.height > obj['y'])
    
    def draw(self, screen):
        # Draw body
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        
        # Draw angry eyes
        eye_y = self.y + 10
        pygame.draw.circle(screen, WHITE, (int(self.x + 10), eye_y), 4)
        pygame.draw.circle(screen, BLACK, (int(self.x + 8), eye_y - 1), 2)
        pygame.draw.circle(screen, WHITE, (int(self.x + 20), eye_y), 4)
        pygame.draw.circle(screen, BLACK, (int(self.x + 22), eye_y - 1), 2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mario MMO - DS Download Play Style")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Network
        self.network = NetworkManager()
        self.network.start_discovery()
        
        # Game objects
        self.local_player = Player(100, 300, RED, is_local=True)
        self.remote_players = {}
        
        # Enemies
        self.enemies = [
            Enemy(200, 350),
            Enemy(450, 300),
            Enemy(550, 150),
            Enemy(650, 400),
        ]
        
        # Battle state
        self.battle_mode = False
        self.battle_timer = 0
        self.current_enemy = None
        
        # Test map platforms (Super Mario RPG style)
        self.platforms = [
            {'x': 150, 'y': 400, 'width': 200, 'height': 20},
            {'x': 400, 'y': 350, 'width': 150, 'height': 20},
            {'x': 250, 'y': 250, 'width': 100, 'height': 20},
            {'x': 500, 'y': 200, 'width': 200, 'height': 20},
            {'x': 50, 'y': 300, 'width': 80, 'height': 20},
            {'x': 600, 'y': 450, 'width': 150, 'height': 20},
        ]
        
        # Decorative elements
        self.clouds = [
            {'x': 100, 'y': 50, 'width': 60, 'height': 30},
            {'x': 300, 'y': 80, 'width': 80, 'height': 35},
            {'x': 500, 'y': 60, 'width': 70, 'height': 30},
            {'x': 700, 'y': 90, 'width': 65, 'height': 32},
        ]
        
        self.coins = [
            {'x': 200, 'y': 220, 'collected': False},
            {'x': 470, 'y': 170, 'collected': False},
            {'x': 570, 'y': 170, 'collected': False},
            {'x': 650, 'y': 420, 'collected': False},
        ]
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    # Reset position
                    self.local_player.x = 100
                    self.local_player.y = 300
                    
    def update(self):
        # Update local player if not in battle
        if not self.battle_mode:
            self.local_player.update(self.platforms)
        else:
            # Battle logic
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                elapsed = time.time() - self.battle_timer
                if 1.0 < elapsed < 1.5:
                    print("Good timed hit! Enemy defeated")
                    if self.current_enemy in self.enemies:
                        self.enemies.remove(self.current_enemy)
                else:
                    print("Bad timing, hurt!")
                self.battle_mode = False
            if time.time() - self.battle_timer > 3.0:
                print("Too slow, hurt!")
                self.battle_mode = False
            
            # Still apply gravity or keep position
        
        # Send position to network
        self.network.update_player_position(
            self.local_player.x,
            self.local_player.y,
            self.local_player.state
        )
        
        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update(self.platforms)
            
            # Check collision with local player
            if not self.battle_mode and self.local_player.check_collision(enemy):
                if self.local_player.vy > 0 and self.local_player.y < enemy.y:
                    # Jump on head, defeat enemy
                    self.local_player.vy = JUMP_STRENGTH / 1.5
                    self.enemies.remove(enemy)
                    print("Enemy defeated by jump!")
                else:
                    # Start battle
                    self.battle_mode = True
                    self.current_enemy = enemy
                    self.battle_timer = time.time()
                    print("Battle started!")
        
        # Update remote players
        self.network.cleanup_disconnected()
        
        # Sync remote players
        for player_id, data in self.network.players.items():
            if player_id not in self.remote_players:
                color = random.choice([BLUE, GREEN, YELLOW])
                self.remote_players[player_id] = Player(
                    data['x'], data['y'], color, is_local=False
                )
            else:
                # Smooth interpolation
                remote = self.remote_players[player_id]
                remote.x += (data['x'] - remote.x) * 0.3
                remote.y += (data['y'] - remote.y) * 0.3
        
        # Remove disconnected players
        to_remove = []
        for player_id in self.remote_players:
            if player_id not in self.network.players:
                to_remove.append(player_id)
        for player_id in to_remove:
            del self.remote_players[player_id]
            
        # Check coin collection
        for coin in self.coins:
            if not coin['collected']:
                if (abs(self.local_player.x + self.local_player.width/2 - coin['x']) < 20 and
                    abs(self.local_player.y + self.local_player.height/2 - coin['y']) < 20):
                    coin['collected'] = True
                    
    def draw(self):
        # Draw sky
        self.screen.fill(SKY_BLUE)
        
        # Draw clouds
        for cloud in self.clouds:
            pygame.draw.ellipse(self.screen, WHITE, 
                               (cloud['x'], cloud['y'], cloud['width'], cloud['height']))
            pygame.draw.ellipse(self.screen, WHITE,
                               (cloud['x'] - 20, cloud['y'] + 5, cloud['width'] - 10, cloud['height'] - 10))
            pygame.draw.ellipse(self.screen, WHITE,
                               (cloud['x'] + 20, cloud['y'] + 5, cloud['width'] - 10, cloud['height'] - 10))
        
        # Draw platforms with 2.5D effect
        for platform in self.platforms:
            # Top surface (green)
            top_points = [
                (platform['x'], platform['y']),
                (platform['x'] + platform['width'], platform['y']),
                (platform['x'] + platform['width'] - DEPTH, platform['y'] + DEPTH),
                (platform['x'] - DEPTH, platform['y'] + DEPTH)
            ]
            pygame.draw.polygon(self.screen, GREEN, top_points)
            
            # Front side
            front_points = [
                (platform['x'], platform['y']),
                (platform['x'] - DEPTH, platform['y'] + DEPTH),
                (platform['x'] - DEPTH, platform['y'] + DEPTH + platform['height']),
                (platform['x'], platform['y'] + platform['height'])
            ]
            pygame.draw.polygon(self.screen, DARK_GREEN, front_points)
            
            # Right side
            side_points = [
                (platform['x'] + platform['width'], platform['y']),
                (platform['x'] + platform['width'] - DEPTH, platform['y'] + DEPTH),
                (platform['x'] + platform['width'] - DEPTH, platform['y'] + DEPTH + platform['height']),
                (platform['x'] + platform['width'], platform['y'] + platform['height'])
            ]
            pygame.draw.polygon(self.screen, DARKER_GREEN, side_points)
        
        # Draw coins
        for coin in self.coins:
            if not coin['collected']:
                pygame.draw.circle(self.screen, YELLOW, (coin['x'], coin['y']), 8)
                pygame.draw.circle(self.screen, (255, 215, 0), (coin['x'], coin['y']), 6)
        
        # Draw ground with 2.5D effect
        ground_y = SCREEN_HEIGHT - 100
        ground_height = 100
        
        # Top surface (green)
        top_points = [
            (0, ground_y),
            (SCREEN_WIDTH, ground_y),
            (SCREEN_WIDTH - DEPTH, ground_y + DEPTH),
            (0 - DEPTH, ground_y + DEPTH)
        ]
        pygame.draw.polygon(self.screen, GREEN, top_points)
        
        # Front side (brown)
        front_points = [
            (0, ground_y),
            (0 - DEPTH, ground_y + DEPTH),
            (0 - DEPTH, ground_y + DEPTH + ground_height),
            (0, ground_y + ground_height)
        ]
        pygame.draw.polygon(self.screen, BROWN, front_points)
        
        # Right side
        side_points = [
            (SCREEN_WIDTH, ground_y),
            (SCREEN_WIDTH - DEPTH, ground_y + DEPTH),
            (SCREEN_WIDTH - DEPTH, ground_y + DEPTH + ground_height),
            (SCREEN_WIDTH, ground_y + ground_height)
        ]
        pygame.draw.polygon(self.screen, DARK_BROWN, side_points)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen)
        
        # Draw players
        self.local_player.draw(self.screen)
        for player in self.remote_players.values():
            player.draw(self.screen)
        
        # Draw UI
        font = pygame.font.Font(None, 36)
        
        # Player count
        player_count = len(self.remote_players) + 1
        text = font.render(f"Players: {player_count}", True, WHITE)
        self.screen.blit(text, (10, 10))
        
        # Network ID
        id_text = font.render(f"ID: {self.network.local_id}", True, WHITE)
        self.screen.blit(id_text, (10, 50))
        
        # Instructions
        small_font = pygame.font.Font(None, 24)
        instructions = [
            "Auto-detecting local players...",
            "A/D or Arrows: Move",
            "W or Space: Jump",
            "R: Reset position",
            "ESC: Quit"
        ]
        for i, instruction in enumerate(instructions):
            text = small_font.render(instruction, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH - 250, 10 + i * 25))
        
        # Draw battle UI if in battle
        if self.battle_mode:
            # Background
            pygame.draw.rect(self.screen, (200, 200, 200), (200, 150, 400, 200))
            
            # Progress bar
            progress = min((time.time() - self.battle_timer) / 3.0, 1.0)
            pygame.draw.rect(self.screen, GREEN, (250, 250, 300 * progress, 30))
            
            # Ideal zone
            pygame.draw.rect(self.screen, YELLOW, (250 + 300 * (1.0/3), 250, 300 * (0.5/3), 30))
            
            battle_text = font.render("Press SPACE in the yellow zone!", True, BLACK)
            self.screen.blit(battle_text, (220, 180))
        
        pygame.display.flip()
        
    def run(self):
        print("=== Mario MMO Started ===")
        print(f"Your Player ID: {self.network.local_id}")
        print("Scanning for local players...")
        print("Other instances on your network will auto-connect!")
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        self.network.running = False
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
