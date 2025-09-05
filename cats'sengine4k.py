#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
program.py — CatOS / Enhanced M&L Engine with GBA Graphics
--------------------------------------------------------------------------------
Enhanced with:
  • Ryen as the shop clerk (Fawful removed)
  • Superstar Saga-style item menu (Tab/I key)
  • GBA-authentic graphics with pixel-perfect rendering
  • Enhanced visual effects and color palette
  • Programmatically generated Superstar Saga-style sprites

Controls
--------
  Movement (lead bro):  W A S D or Arrow Keys
  Interact / Talk:      E
  Swap lead bro:        Q
  Open Item Menu:       TAB or I
  Open Shop (near NPC): E when beside Ryen
  Advance text:         SPACE / ENTER
  Fast-forward text:    SPACE / ENTER (while text is typing)
  Shop/Menu nav:        W/S or UP/DOWN;  ENTER = Select;  ESC/BACKSPACE = Exit
  Quit:                 ESC (from overworld when no UI is open)

Requirements
------------
  pip install pygame

Then run:  python program.py
"""

import pygame
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import sys
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TILE_SIZE = 48
FPS = 60

# GBA-Style Color Palette
BLACK = (8, 8, 16)
WHITE = (248, 248, 240)
RED = (232, 0, 0)  # Mario's authentic red
GREEN = (0, 200, 0)  # Luigi's authentic green
DARK_BLUE = (16, 24, 48)
AZURE = (56, 168, 248)
LIGHT_AZURE = (120, 200, 248)
GRAY = (72, 80, 88)
LIGHT_GRAY = (152, 160, 168)
DARK_GRAY = (40, 48, 56)
WALL_COLOR = (48, 56, 72)
FLOOR_TILE1 = (96, 104, 112)
FLOOR_TILE2 = (88, 96, 104)
COUNTER_COLOR = (136, 96, 56)
COUNTER_LIGHT = (168, 120, 72)
RYEN_COLOR = (120, 184, 248)
RYEN_DARK = (88, 136, 200)
PANEL_COLOR = (24, 32, 48, 240)
BUTTON_COLOR = (48, 56, 80)
BUTTON_HOVER = (88, 104, 144)
DETAIL_PANEL = (32, 40, 56)
MENU_BG = (32, 40, 64)
MENU_BORDER = (248, 216, 120)
MENU_BORDER_DARK = (184, 152, 80)
ITEM_SELECT = (248, 232, 168)
SHADOW_COLOR = (0, 0, 0, 100)
MARIO_RED = (232, 56, 40)
MARIO_BLUE = (32, 96, 200)
LUIGI_GREEN = (64, 200, 64)
LUIGI_BLUE = (64, 120, 216)
SKIN_COLOR = (248, 184, 136)
SHOE_COLOR = (120, 72, 40)

# ------------------------------
# Data Models
# ------------------------------

@dataclass
class Item:
    name: str
    desc: str
    price_coins: int = 0
    price_shards: int = 0
    key_item: bool = False
    category: str = "item"  # item, gear, key


@dataclass
class Inventory:
    coins: int = 50
    shards: int = 2
    items: Dict[str, int] = field(default_factory=dict)

    def add(self, item: Item, qty: int = 1):
        self.items[item.name] = self.items.get(item.name, 0) + qty

    def can_afford(self, item: Item) -> bool:
        return (self.coins >= item.price_coins) and (self.shards >= item.price_shards)

    def pay(self, item: Item) -> bool:
        if not self.can_afford(item):
            return False
        self.coins -= item.price_coins
        self.shards -= item.price_shards
        return True

    def get_items_by_category(self, category: str) -> List[Tuple[str, int]]:
        result = []
        for item_name, qty in self.items.items():
            # Find item in catalog
            for cat_item in CATALOG:
                if cat_item.name == item_name and cat_item.category == category:
                    result.append((item_name, qty))
                    break
        return result


# ------------------------------
# GBA-Style Graphics Helper
# ------------------------------

def draw_gba_panel(screen, rect, highlighted=False):
    """Draw a GBA-style panel with gradient and borders"""
    # Main fill
    base_color = BUTTON_HOVER if highlighted else BUTTON_COLOR
    pygame.draw.rect(screen, base_color, rect)
    
    # Gradient effect (lighter at top)
    gradient_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 3)
    lighter = tuple(min(255, c + 20) for c in base_color)
    pygame.draw.rect(screen, lighter, gradient_rect)
    
    # Border
    pygame.draw.rect(screen, MENU_BORDER if highlighted else WHITE, rect, 2)
    # Inner shadow
    pygame.draw.rect(screen, DARK_GRAY, rect, 1)


def draw_gba_text_panel(screen, rect):
    """Draw a GBA-style text panel with decorative corners"""
    # Background
    pygame.draw.rect(screen, DARK_BLUE, rect)
    
    # Border with rounded corner effect
    pygame.draw.rect(screen, MENU_BORDER, rect, 3)
    pygame.draw.rect(screen, MENU_BORDER_DARK, rect, 1)
    
    # Corner decorations
    corner_size = 8
    corners = [
        (rect.left, rect.top),
        (rect.right - corner_size, rect.top),
        (rect.left, rect.bottom - corner_size),
        (rect.right - corner_size, rect.bottom - corner_size)
    ]
    for cx, cy in corners:
        pygame.draw.rect(screen, ITEM_SELECT, (cx, cy, corner_size, corner_size))
        pygame.draw.rect(screen, MENU_BORDER_DARK, (cx, cy, corner_size, corner_size), 1)


# ------------------------------
# Sprite Generator (Superstar Saga Style)
# ------------------------------

def generate_mario_sprites():
    """Generate Mario sprites programmatically in Superstar Saga style"""
    sprites = {}
    size = (32, 48)
    
    # Down direction (idle and walking)
    down_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (red)
        pygame.draw.rect(surf, MARIO_RED, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, MARIO_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (18, 8, 4, 12))
        
        # Draw face
        pygame.draw.rect(surf, SKIN_COLOR, (10, 10, 12, 8))
        
        # Draw eyes (animation)
        if i % 2 == 0:
            pygame.draw.rect(surf, BLACK, (12, 12, 2, 2))
            pygame.draw.rect(surf, BLACK, (18, 12, 2, 2))
        else:
            pygame.draw.rect(surf, BLACK, (13, 13, 1, 1))
            pygame.draw.rect(surf, BLACK, (19, 13, 1, 1))
        
        # Draw hat
        pygame.draw.rect(surf, MARIO_RED, (8, 4, 16, 6))
        pygame.draw.rect(surf, MARIO_RED, (6, 6, 20, 4))
        
        # Draw mustache
        pygame.draw.rect(surf, BLACK, (12, 16, 8, 2))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (4, 20, 4, 4))
            pygame.draw.rect(surf, SKIN_COLOR, (24, 20, 4, 4))
        
        down_frames.append(surf)
    
    sprites["idle_down"] = [down_frames[0]]
    sprites["walk_down"] = down_frames
    
    # Up direction
    up_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (red)
        pygame.draw.rect(surf, MARIO_RED, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, MARIO_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (18, 8, 4, 12))
        
        # Draw face (looking up)
        pygame.draw.rect(surf, SKIN_COLOR, (10, 6, 12, 8))
        
        # Draw eyes
        pygame.draw.rect(surf, BLACK, (12, 10, 2, 2))
        pygame.draw.rect(surf, BLACK, (18, 10, 2, 2))
        
        # Draw hat (tilted back)
        pygame.draw.rect(surf, MARIO_RED, (8, 2, 16, 6))
        pygame.draw.rect(surf, MARIO_RED, (6, 4, 20, 4))
        
        # Draw mustache (smaller when looking up)
        pygame.draw.rect(surf, BLACK, (13, 14, 6, 1))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (4, 16, 4, 4))
            pygame.draw.rect(surf, SKIN_COLOR, (24, 16, 4, 4))
        
        up_frames.append(surf)
    
    sprites["idle_up"] = [up_frames[0]]
    sprites["walk_up"] = up_frames
    
    # Left direction
    left_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (red)
        pygame.draw.rect(surf, MARIO_RED, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, MARIO_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, MARIO_BLUE, (18, 8, 4, 12))
        
        # Draw face (profile)
        pygame.draw.rect(surf, SKIN_COLOR, (6, 10, 10, 8))
        
        # Draw eye
        pygame.draw.rect(surf, BLACK, (10, 12, 2, 2))
        
        # Draw hat (side view)
        pygame.draw.rect(surf, MARIO_RED, (6, 4, 12, 6))
        pygame.draw.rect(surf, MARIO_RED, (4, 6, 14, 4))
        
        # Draw nose
        pygame.draw.rect(surf, SKIN_COLOR, (14, 12, 4, 4))
        
        # Draw mustache
        pygame.draw.rect(surf, BLACK, (14, 16, 6, 2))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (2, 20, 4, 4))
        
        left_frames.append(surf)
    
    sprites["idle_left"] = [left_frames[0]]
    sprites["walk_left"] = left_frames
    
    # Right direction (mirror of left)
    right_frames = []
    for frame in left_frames:
        right_frames.append(pygame.transform.flip(frame, True, False))
    
    sprites["idle_right"] = [right_frames[0]]
    sprites["walk_right"] = right_frames
    
    return sprites


def generate_luigi_sprites():
    """Generate Luigi sprites programmatically in Superstar Saga style"""
    sprites = {}
    size = (32, 48)
    
    # Down direction (idle and walking)
    down_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (green)
        pygame.draw.rect(surf, LUIGI_GREEN, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, LUIGI_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (18, 8, 4, 12))
        
        # Draw face
        pygame.draw.rect(surf, SKIN_COLOR, (10, 10, 12, 8))
        
        # Draw eyes (animation)
        if i % 2 == 0:
            pygame.draw.rect(surf, BLACK, (12, 12, 2, 2))
            pygame.draw.rect(surf, BLACK, (18, 12, 2, 2))
        else:
            pygame.draw.rect(surf, BLACK, (13, 13, 1, 1))
            pygame.draw.rect(surf, BLACK, (19, 13, 1, 1))
        
        # Draw hat
        pygame.draw.rect(surf, LUIGI_GREEN, (8, 4, 16, 6))
        pygame.draw.rect(surf, LUIGI_GREEN, (6, 6, 20, 4))
        
        # Draw mustache
        pygame.draw.rect(surf, BLACK, (12, 16, 8, 2))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (4, 20, 4, 4))
            pygame.draw.rect(surf, SKIN_COLOR, (24, 20, 4, 4))
        
        down_frames.append(surf)
    
    sprites["idle_down"] = [down_frames[0]]
    sprites["walk_down"] = down_frames
    
    # Up direction
    up_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (green)
        pygame.draw.rect(surf, LUIGI_GREEN, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, LUIGI_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (18, 8, 4, 12))
        
        # Draw face (looking up)
        pygame.draw.rect(surf, SKIN_COLOR, (10, 6, 12, 8))
        
        # Draw eyes
        pygame.draw.rect(surf, BLACK, (12, 10, 2, 2))
        pygame.draw.rect(surf, BLACK, (18, 10, 2, 2))
        
        # Draw hat (tilted back)
        pygame.draw.rect(surf, LUIGI_GREEN, (8, 2, 16, 6))
        pygame.draw.rect(surf, LUIGI_GREEN, (6, 4, 20, 4))
        
        # Draw mustache (smaller when looking up)
        pygame.draw.rect(surf, BLACK, (13, 14, 6, 1))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (4, 16, 4, 4))
            pygame.draw.rect(surf, SKIN_COLOR, (24, 16, 4, 4))
        
        up_frames.append(surf)
    
    sprites["idle_up"] = [up_frames[0]]
    sprites["walk_up"] = up_frames
    
    # Left direction
    left_frames = []
    for i in range(4):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw body (green)
        pygame.draw.rect(surf, LUIGI_GREEN, (8, 8, 16, 24))
        
        # Draw overalls (blue)
        pygame.draw.rect(surf, LUIGI_BLUE, (8, 20, 16, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (10, 8, 4, 12))
        pygame.draw.rect(surf, LUIGI_BLUE, (18, 8, 4, 12))
        
        # Draw face (profile)
        pygame.draw.rect(surf, SKIN_COLOR, (6, 10, 10, 8))
        
        # Draw eye
        pygame.draw.rect(surf, BLACK, (10, 12, 2, 2))
        
        # Draw hat (side view)
        pygame.draw.rect(surf, LUIGI_GREEN, (6, 4, 12, 6))
        pygame.draw.rect(surf, LUIGI_GREEN, (4, 6, 14, 4))
        
        # Draw nose
        pygame.draw.rect(surf, SKIN_COLOR, (14, 12, 4, 4))
        
        # Draw mustache
        pygame.draw.rect(surf, BLACK, (14, 16, 6, 2))
        
        # Draw shoes
        pygame.draw.rect(surf, SHOE_COLOR, (8, 32, 6, 8))
        pygame.draw.rect(surf, SHOE_COLOR, (18, 32, 6, 8))
        
        # Draw hands (animation)
        if i == 1 or i == 3:
            pygame.draw.rect(surf, SKIN_COLOR, (2, 20, 4, 4))
        
        left_frames.append(surf)
    
    sprites["idle_left"] = [left_frames[0]]
    sprites["walk_left"] = left_frames
    
    # Right direction (mirror of left)
    right_frames = []
    for frame in left_frames:
        right_frames.append(pygame.transform.flip(frame, True, False))
    
    sprites["idle_right"] = [right_frames[0]]
    sprites["walk_right"] = right_frames
    
    return sprites


# ------------------------------
# Textbox (Superstar Saga-style)
# ------------------------------

class TextBox:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 26)
        self.name_font = pygame.font.Font(None, 22)
        self.enabled = False
        self.lines = []
        self.index = 0
        self._full = ''
        self._shown = ''
        self._typing = False
        self._accum = 0.0
        self._cps = 48.0  # characters per second
        self.on_complete = None
        self.arrow_y = 0
        self.arrow_dir = 1
        self.speaker = ''
        self.arrow_timer = 0

    def say(self, lines: List[Tuple[str, str]], on_complete: Optional[Callable] = None):
        """lines: [(speaker, text), ...]"""
        self.lines = lines
        self.index = 0
        self.on_complete = on_complete
        self.enabled = True
        self._start_line()

    def _start_line(self):
        if self.index >= len(self.lines):
            # done
            self._close()
            if self.on_complete:
                self.on_complete()
            return
        speaker, text = self.lines[self.index]
        self.speaker = speaker
        self._full = text
        self._shown = ''
        self._typing = True
        self._accum = 0.0

    def instant_finish_line(self):
        self._shown = self._full
        self._typing = False

    def _close(self):
        self.enabled = False

    def next(self):
        if self._typing:
            self.instant_finish_line()
        else:
            self.index += 1
            self._start_line()

    def update(self, dt):
        if not self.enabled or not self._typing:
            return
        # typewriter effect
        if self._shown == self._full:
            self._typing = False
            return
        self._accum += dt * self._cps
        while self._accum >= 1.0 and len(self._shown) < len(self._full):
            self._shown += self._full[len(self._shown)]
            self._accum -= 1.0

        # Arrow animation
        if not self._typing:
            self.arrow_timer += dt
            self.arrow_y = math.sin(self.arrow_timer * 4) * 6

    def draw(self):
        if not self.enabled:
            return
        
        # Background panel with GBA style
        panel_rect = pygame.Rect(40, SCREEN_HEIGHT - 200, SCREEN_WIDTH - 80, 160)
        draw_gba_text_panel(self.screen, panel_rect)
        
        # Nameplate with gradient
        nameplate_rect = pygame.Rect(40, SCREEN_HEIGHT - 245, 200, 38)
        draw_gba_panel(self.screen, nameplate_rect, highlighted=True)
        
        # Speaker name
        name_surface = self.name_font.render(self.speaker, True, WHITE)
        name_rect = name_surface.get_rect(center=(140, SCREEN_HEIGHT - 226))
        self.screen.blit(name_surface, name_rect)
        
        # Text content (with word wrap)
        lines = self._wrap_text(self._shown, SCREEN_WIDTH - 120)
        y_offset = 0
        for line in lines:
            text_surface = self.font.render(line, True, WHITE)
            # Add shadow
            shadow_surface = self.font.render(line, True, BLACK)
            self.screen.blit(shadow_surface, (62, SCREEN_HEIGHT - 168 + y_offset))
            self.screen.blit(text_surface, (60, SCREEN_HEIGHT - 170 + y_offset))
            y_offset += 30
        
        # Next arrow (animated)
        if not self._typing:
            arrow_points = [
                (SCREEN_WIDTH - 100, SCREEN_HEIGHT - 60 + self.arrow_y),
                (SCREEN_WIDTH - 110, SCREEN_HEIGHT - 70 + self.arrow_y),
                (SCREEN_WIDTH - 90, SCREEN_HEIGHT - 70 + self.arrow_y)
            ]
            pygame.draw.polygon(self.screen, ITEM_SELECT, arrow_points)
            pygame.draw.polygon(self.screen, MENU_BORDER_DARK, arrow_points, 1)

    def _wrap_text(self, text, max_width):
        """Simple word wrapping"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines[:4]  # Max 4 lines


# ------------------------------
# Item Menu (Superstar Saga Style)
# ------------------------------

class ItemMenu:
    def __init__(self, screen, inventory: Inventory):
        self.screen = screen
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        self.inv = inventory
        self.enabled = False
        self.tab = 0  # 0: Items, 1: Gear, 2: Key Items
        self.selected = 0
        self.tabs = ["Items", "Gear", "Key Items"]
        
    def open(self):
        self.enabled = True
        self.selected = 0
        self.tab = 0
    
    def close(self):
        self.enabled = False
    
    def handle_input(self, key):
        if not self.enabled:
            return False
        
        if key == pygame.K_ESCAPE or key == pygame.K_BACKSPACE or key == pygame.K_TAB or key == pygame.K_i:
            self.close()
            return True
        elif key == pygame.K_a or key == pygame.K_LEFT:
            self.tab = (self.tab - 1) % 3
            self.selected = 0
            return True
        elif key == pygame.K_d or key == pygame.K_RIGHT:
            self.tab = (self.tab + 1) % 3
            self.selected = 0
            return True
        elif key == pygame.K_w or key == pygame.K_UP:
            items = self._get_current_items()
            if items:
                self.selected = max(0, self.selected - 1)
            return True
        elif key == pygame.K_s or key == pygame.K_DOWN:
            items = self._get_current_items()
            if items:
                self.selected = min(len(items) - 1, self.selected + 1)
            return True
        return False
    
    def _get_current_items(self):
        category = ["item", "gear", "key"][self.tab]
        return self.inv.get_items_by_category(category)
    
    def draw(self):
        if not self.enabled:
            return
        
        # Main background
        main_rect = pygame.Rect(60, 60, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 160)
        pygame.draw.rect(self.screen, MENU_BG, main_rect)
        pygame.draw.rect(self.screen, MENU_BORDER, main_rect, 4)
        pygame.draw.rect(self.screen, MENU_BORDER_DARK, main_rect, 2)
        
        # Draw tabs
        tab_width = 140
        for i, tab_name in enumerate(self.tabs):
            x = 100 + i * (tab_width + 20)
            y = 80
            tab_rect = pygame.Rect(x, y, tab_width, 35)
            
            if i == self.tab:
                draw_gba_panel(self.screen, tab_rect, highlighted=True)
                color = BLACK
            else:
                draw_gba_panel(self.screen, tab_rect, highlighted=False)
                color = LIGHT_GRAY
            
            text = self.font.render(tab_name, True, color)
            text_rect = text.get_rect(center=(x + tab_width//2, y + 18))
            self.screen.blit(text, text_rect)
        
        # Item list area
        list_rect = pygame.Rect(100, 140, 400, 400)
        pygame.draw.rect(self.screen, DARK_GRAY, list_rect)
        pygame.draw.rect(self.screen, WHITE, list_rect, 1)
        
        # Draw items
        items = self._get_current_items()
        if items:
            for i, (name, qty) in enumerate(items):
                y = 150 + i * 35
                
                # Selection highlight
                if i == self.selected:
                    sel_rect = pygame.Rect(110, y - 2, 380, 30)
                    pygame.draw.rect(self.screen, ITEM_SELECT, sel_rect)
                    pygame.draw.rect(self.screen, MENU_BORDER_DARK, sel_rect, 1)
                
                # Item name
                text = self.font.render(name, True, WHITE if i == self.selected else LIGHT_GRAY)
                self.screen.blit(text, (120, y))
                
                # Quantity
                if qty > 1:
                    qty_text = self.font.render(f"×{qty}", True, WHITE)
                    self.screen.blit(qty_text, (450, y))
        else:
            empty_text = self.font.render("(No items)", True, LIGHT_GRAY)
            empty_rect = empty_text.get_rect(center=(300, 300))
            self.screen.blit(empty_text, empty_rect)
        
        # Description panel
        desc_rect = pygame.Rect(520, 140, 380, 400)
        draw_gba_panel(self.screen, desc_rect)
        
        # Show selected item description
        if items and 0 <= self.selected < len(items):
            item_name = items[self.selected][0]
            # Find full item data
            for cat_item in CATALOG:
                if cat_item.name == item_name:
                    # Name
                    name_text = self.title_font.render(cat_item.name, True, WHITE)
                    self.screen.blit(name_text, (540, 160))
                    
                    # Category badge
                    cat_text = cat_item.category.upper()
                    if cat_item.key_item:
                        cat_text = "KEY ITEM"
                    badge_rect = pygame.Rect(540, 200, 100, 25)
                    pygame.draw.rect(self.screen, MENU_BORDER, badge_rect)
                    pygame.draw.rect(self.screen, MENU_BORDER_DARK, badge_rect, 1)
                    cat_surface = self.font.render(cat_text, True, BLACK)
                    cat_rect = cat_surface.get_rect(center=(590, 212))
                    self.screen.blit(cat_surface, cat_rect)
                    
                    # Description
                    desc_lines = self._wrap_text(cat_item.desc, 340)
                    y = 240
                    for line in desc_lines:
                        desc_surface = self.font.render(line, True, WHITE)
                        self.screen.blit(desc_surface, (540, y))
                        y += 28
                    break
        
        # Bottom info
        coins_text = self.title_font.render(f"Coins: {self.inv.coins}   Shards: {self.inv.shards}", True, ITEM_SELECT)
        self.screen.blit(coins_text, (100, SCREEN_HEIGHT - 120))
        
        # Controls hint
        hint_text = self.font.render("A/D: Switch tabs • W/S: Navigate • Tab/I: Close", True, LIGHT_GRAY)
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 80))
        self.screen.blit(hint_text, hint_rect)
    
    def _wrap_text(self, text, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


# ------------------------------
# Grid World
# ------------------------------

class GridWorld:
    """Grid map with collision; '.' floor, '#' wall, 'S' shop counter, 'O' portal, 'R' Ryen."""
    def __init__(self, ascii_map: str):
        self.grid = [list(row) for row in ascii_map.strip('\n').splitlines()]
        self.h = len(self.grid)
        self.w = len(self.grid[0]) if self.h else 0
        self.ryen_pos = None
        self.portal_pos = None
        self.shop_counter_pos = None
        
        # Find special positions
        for y, row in enumerate(self.grid):
            for x, c in enumerate(row):
                if c == 'R':
                    self.ryen_pos = (x, y)
                    self.grid[y][x] = '.'  # Replace with floor
                elif c == 'O':
                    self.portal_pos = (x, y)
                    self.grid[y][x] = '.'
                elif c == 'S':
                    self.shop_counter_pos = (x, y)

    def is_blocked(self, gx: int, gy: int) -> bool:
        if gx < 0 or gy < 0 or gx >= self.w or gy >= self.h:
            return True
        c = self.grid[gy][gx]
        return c == '#' or c == 'S'

    def to_screen(self, gx: int, gy: int) -> Tuple[int, int]:
        """Convert grid coordinates to screen pixels"""
        x = gx * TILE_SIZE + TILE_SIZE // 2
        y = gy * TILE_SIZE + TILE_SIZE // 2
        return x, y

    def draw(self, screen, camera_x, camera_y):
        for y, row in enumerate(self.grid):
            for x, c in enumerate(row):
                px, py = self.to_screen(x, y)
                px -= camera_x
                py -= camera_y
                
                # Draw checkered floor pattern
                tile_color = FLOOR_TILE1 if (x + y) % 2 == 0 else FLOOR_TILE2
                pygame.draw.rect(screen, tile_color, (px - TILE_SIZE//2, py - TILE_SIZE//2, TILE_SIZE, TILE_SIZE))
                
                # Draw tile borders
                pygame.draw.rect(screen, DARK_GRAY, (px - TILE_SIZE//2, py - TILE_SIZE//2, TILE_SIZE, TILE_SIZE), 1)
                
                # Draw walls with 3D effect
                if c == '#':
                    # Main wall
                    wall_rect = pygame.Rect(px - TILE_SIZE//2 + 4, py - TILE_SIZE//2 + 4, TILE_SIZE - 8, TILE_SIZE - 8)
                    pygame.draw.rect(screen, WALL_COLOR, wall_rect)
                    # Top highlight
                    pygame.draw.rect(screen, LIGHT_GRAY, (wall_rect.x, wall_rect.y, wall_rect.width, 4))
                    # Border
                    pygame.draw.rect(screen, BLACK, wall_rect, 2)
                
                # Draw shop counter with detail
                elif c == 'S':
                    counter_rect = pygame.Rect(px - TILE_SIZE//2 + 2, py - TILE_SIZE//2 + 2, TILE_SIZE - 4, TILE_SIZE - 4)
                    pygame.draw.rect(screen, COUNTER_COLOR, counter_rect)
                    # Wood grain effect
                    for i in range(0, TILE_SIZE - 4, 6):
                        pygame.draw.line(screen, COUNTER_LIGHT, (counter_rect.x + i, counter_rect.y), 
                                       (counter_rect.x + i, counter_rect.y + counter_rect.height), 1)
                    pygame.draw.rect(screen, BLACK, counter_rect, 2)
        
        # Draw animated portal
        if self.portal_pos:
            px, py = self.to_screen(self.portal_pos[0], self.portal_pos[1])
            px -= camera_x
            py -= camera_y
            
            # Multi-layer portal effect
            t = pygame.time.get_ticks() / 1000.0
            for i in range(3):
                radius = int(TILE_SIZE * (0.25 + i * 0.1) + math.sin(t * 2 + i) * 3)
                alpha = 180 - i * 40
                color = (*LIGHT_AZURE, alpha)
                
                # Create surface for transparency
                portal_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(portal_surf, color, (radius, radius), radius)
                screen.blit(portal_surf, (px - radius, py - radius))
            
            # Outer ring
            pygame.draw.circle(screen, AZURE, (px, py), int(TILE_SIZE * 0.4), 3)


# ------------------------------
# Character (Bro) with Generated Sprites
# ------------------------------

class Bro:
    def __init__(self, name: str, grid: GridWorld, gx: int, gy: int):
        self.name = name
        self.grid = grid
        self.gx = gx
        self.gy = gy
        self.px, self.py = grid.to_screen(gx, gy)
        self.target_gx = gx
        self.target_gy = gy
        self.moving = False
        self.move_progress = 0.0
        self.move_speed = 8.0  # tiles per second
        self.is_lead = False
        self.trail = []  # Recent positions for follower
        self.bounce = 0
        self.direction = "down"  # "up", "down", "left", "right"
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.2  # seconds per frame
        
        # Generate sprites programmatically
        if name == "Mario":
            self.sprites = generate_mario_sprites()
        else:
            self.sprites = generate_luigi_sprites()

    def get_current_sprite(self):
        state = "walk" if self.moving else "idle"
        direction = self.direction
        
        # Get the animation frames for current state and direction
        frames = self.sprites.get(f"{state}_{direction}", self.sprites["idle_down"])
        
        # Calculate current frame based on animation timer
        frame_index = int(self.animation_timer / self.animation_speed) % len(frames)
        return frames[frame_index]

    def try_step(self, dx: int, dy: int) -> bool:
        if self.moving:
            return False
        tx, ty = self.gx + dx, self.gy + dy
        if self.grid.is_blocked(tx, ty):
            return False
        
        # Update direction
        if dx > 0:
            self.direction = "right"
        elif dx < 0:
            self.direction = "left"
        elif dy > 0:
            self.direction = "down"
        elif dy < 0:
            self.direction = "up"
        
        # Record current position in trail
        self.trail.append((self.gx, self.gy))
        if len(self.trail) > 10:  # Keep trail short
            self.trail.pop(0)
        
        self.target_gx = tx
        self.target_gy = ty
        self.moving = True
        self.move_progress = 0.0
        return True

    def update(self, dt):
        # Update animation
        if self.moving:
            self.animation_timer += dt
        else:
            self.animation_timer = 0  # Reset to first frame when idle
        
        if not self.moving:
            # Idle bounce animation
            self.bounce = math.sin(pygame.time.get_ticks() / 500.0) * 2
            return
        
        self.move_progress += dt * self.move_speed
        if self.move_progress >= 1.0:
            self.gx = self.target_gx
            self.gy = self.target_gy
            self.px, self.py = self.grid.to_screen(self.gx, self.gy)
            self.moving = False
            self.move_progress = 0.0
        else:
            # Interpolate position
            start_x, start_y = self.grid.to_screen(self.gx, self.gy)
            end_x, end_y = self.grid.to_screen(self.target_gx, self.target_gy)
            t = self.move_progress
            # Smooth easing
            t = t * t * (3.0 - 2.0 * t)
            self.px = int(start_x + (end_x - start_x) * t)
            self.py = int(start_y + (end_y - start_y) * t)
            # Walking bounce
            self.bounce = abs(math.sin(t * math.pi)) * 4

    def draw(self, screen, camera_x, camera_y):
        x = self.px - camera_x
        y = self.py - camera_y - int(self.bounce)
        
        # Enhanced shadow
        shadow_surf = pygame.Surface((32, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, SHADOW_COLOR, (0, 0, 32, 12))
        screen.blit(shadow_surf, (x - 16, y + 12))
        
        # Get and draw current sprite
        sprite = self.get_current_sprite()
        sprite_rect = sprite.get_rect(center=(x, y - 10))  # Adjust for sprite height
        screen.blit(sprite, sprite_rect)
        
        # Lead indicator
        if self.is_lead:
            star_y = y - 35 + math.sin(pygame.time.get_ticks() / 300.0) * 3
            pygame.draw.polygon(screen, ITEM_SELECT, 
                              [(x, star_y - 8), (x - 6, star_y + 2), (x + 6, star_y + 2)])
            pygame.draw.polygon(screen, MENU_BORDER_DARK, 
                              [(x, star_y - 8), (x - 6, star_y + 2), (x + 6, star_y + 2)], 1)


# ------------------------------
# Shop UI
# ------------------------------

class ShopUI:
    def __init__(self, screen, inventory: Inventory, catalog: List[Item]):
        self.screen = screen
        self.font = pygame.font.Font(None, 26)
        self.title_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 22)
        self.inv = inventory
        self.catalog = catalog
        self.selected = 0
        self.enabled = False
        self.on_close = None

    def open(self):
        self.enabled = True
        self.selected = 0

    def close(self):
        self.enabled = False
        if self.on_close:
            self.on_close()

    def handle_input(self, key):
        if not self.enabled:
            return False
        
        if key == pygame.K_w or key == pygame.K_UP:
            self.selected = max(0, self.selected - 1)
            return True
        elif key == pygame.K_s or key == pygame.K_DOWN:
            self.selected = min(len(self.catalog) - 1, self.selected + 1)
            return True
        elif key == pygame.K_RETURN or key == pygame.K_SPACE:
            self.buy_selected()
            return True
        elif key == pygame.K_ESCAPE or key == pygame.K_BACKSPACE:
            self.close()
            return True
        return False

    def buy_selected(self):
        it = self.catalog[self.selected]
        if not self.inv.can_afford(it):
            Banner.show(self.screen, "Not enough funds!")
            return
        self.inv.pay(it)
        self.inv.add(it, 1)
        Banner.show(self.screen, f"Got {it.name}!")

    def draw(self):
        if not self.enabled:
            return
        
        # Main panel with GBA styling
        panel_rect = pygame.Rect(50, 50, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 150)
        pygame.draw.rect(self.screen, MENU_BG, panel_rect)
        pygame.draw.rect(self.screen, MENU_BORDER, panel_rect, 4)
        pygame.draw.rect(self.screen, MENU_BORDER_DARK, panel_rect, 2)
        
        # Title with decorative underline
        title = self.title_font.render("Ryen's Time Travel Shop", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 90))
        self.screen.blit(title, title_rect)
        pygame.draw.line(self.screen, MENU_BORDER, (title_rect.left - 20, 110), (title_rect.right + 20, 110), 2)
        
        subtitle = self.small_font.render("W/S or ↑/↓ to browse • ENTER to buy • ESC to exit", True, LIGHT_GRAY)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH//2, 130))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Item list area
        list_bg = pygame.Rect(70, 160, 380, 340)
        pygame.draw.rect(self.screen, DARK_GRAY, list_bg)
        pygame.draw.rect(self.screen, WHITE, list_bg, 1)
        
        # Draw items
        visible_start = max(0, self.selected - 3)
        visible_end = min(len(self.catalog), visible_start + 8)
        
        for i in range(visible_start, visible_end):
            item = self.catalog[i]
            y = 170 + (i - visible_start) * 40
            
            # Selection highlight
            if i == self.selected:
                sel_rect = pygame.Rect(75, y - 2, 370, 36)
                pygame.draw.rect(self.screen, ITEM_SELECT, sel_rect)
                pygame.draw.rect(self.screen, MENU_BORDER_DARK, sel_rect, 2)
            
            # Item name
            color = BLACK if i == self.selected else WHITE
            text = self.font.render(item.name, True, color)
            self.screen.blit(text, (85, y + 5))
        
        # Detail panel
        detail_rect = pygame.Rect(470, 160, 430, 340)
        draw_gba_panel(self.screen, detail_rect)
        
        # Selected item details
        if 0 <= self.selected < len(self.catalog):
            item = self.catalog[self.selected]
            
            # Item name with category
            name_text = item.name
            name_surface = self.title_font.render(name_text, True, WHITE)
            self.screen.blit(name_surface, (490, 180))
            
            if item.key_item:
                key_badge = pygame.Rect(490, 215, 80, 25)
                pygame.draw.rect(self.screen, MENU_BORDER, key_badge)
                key_text = self.small_font.render("KEY ITEM", True, BLACK)
                self.screen.blit(key_text, (498, 218))
            
            # Description
            desc_lines = self._wrap_text(item.desc, 390)
            y = 250
            for line in desc_lines:
                desc_surface = self.small_font.render(line, True, WHITE)
                self.screen.blit(desc_surface, (490, y))
                y += 25
            
            # Price display with icons
            price_y = 410
            if item.price_coins > 0:
                coin_text = f"💰 {item.price_coins} coins"
                coin_surface = self.font.render(coin_text, True, ITEM_SELECT)
                self.screen.blit(coin_surface, (490, price_y))
                price_y += 30
            
            if item.price_shards > 0:
                shard_text = f"💎 {item.price_shards} shard(s)"
                shard_surface = self.font.render(shard_text, True, LIGHT_AZURE)
                self.screen.blit(shard_surface, (490, price_y))
            
            # Affordability indicator
            if not self.inv.can_afford(item):
                cant_afford = self.small_font.render("(Can't afford)", True, RED)
                self.screen.blit(cant_afford, (490, 470))
        
        # Wallet display with frame
        wallet_rect = pygame.Rect(70, SCREEN_HEIGHT - 120, 350, 40)
        draw_gba_panel(self.screen, wallet_rect, highlighted=True)
        wallet_text = f"💰 {self.inv.coins} coins   💎 {self.inv.shards} shards"
        wallet_surface = self.font.render(wallet_text, True, BLACK)
        wallet_rect = wallet_surface.get_rect(center=(245, SCREEN_HEIGHT - 100))
        self.screen.blit(wallet_surface, wallet_rect)

    def _wrap_text(self, text, max_width):
        """Simple text wrapping"""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.small_font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines


# ------------------------------
# Banner (Toast notification)
# ------------------------------

class Banner:
    active_banners = []
    
    def __init__(self, screen, text):
        self.screen = screen
        self.text = text
        self.font = pygame.font.Font(None, 26)
        self.life = 2.0
        self.timer = 0
        Banner.active_banners.append(self)
    
    @classmethod
    def show(cls, screen, text):
        return cls(screen, text)
    
    def update(self, dt):
        self.timer += dt
        if self.timer >= self.life:
            if self in Banner.active_banners:
                Banner.active_banners.remove(self)
            return False
        return True
    
    def draw(self):
        alpha = max(0, 255 * (1.0 - self.timer / self.life))
        
        # GBA-style banner
        text_surface = self.font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        
        # Background with border
        bg_rect = text_rect.inflate(60, 30)
        pygame.draw.rect(self.screen, MENU_BG, bg_rect)
        pygame.draw.rect(self.screen, MENU_BORDER, bg_rect, 3)
        pygame.draw.rect(self.screen, MENU_BORDER_DARK, bg_rect, 1)
        
        # Text
        self.screen.blit(text_surface, text_rect)
    
    @classmethod
    def update_all(cls, dt):
        cls.active_banners = [b for b in cls.active_banners if b.update(dt)]
    
    @classmethod
    def draw_all(cls):
        for banner in cls.active_banners:
            banner.draw()


# ------------------------------
# Game Data
# ------------------------------

ASCII_MAP = r"""
########################
#.............#.......R#
#..######.....#.........
#..#....#.....#...O.....
#..#....#.....#.........
#..#....#.....#####.....
#..#....#.........S.....
#..######...............
#.......................
########################
"""

CATALOG = [
    Item("Chrono Shard", "A sliver of yesterday. Stabilizes small rifts.", price_shards=1, category="key"),
    Item("Warp Ticket", "One‑way hop through a friendly portal.", price_coins=20, category="item"),
    Item("Starbean Brew", "Perk‑up potion that tastes oddly heroic.", price_coins=10, category="item"),
    Item("Pocket Shroom", "Tiny heal for tiny scrapes.", price_coins=5, category="item"),
    Item("Time Badge", "Badge that boosts damage with perfect timing.", price_coins=35, category="gear"),
    Item("Past Boots", "Boots that remember your last step.", price_coins=30, category="gear"),
    Item("Future Gloves", "Gloves slightly ahead of their time.", price_coins=30, category="gear"),
    Item("Rift Stabilizer", "Key device for medium rifts. Handle with care.", price_shards=2, key_item=True, category="key"),
    Item("Ultra Nut", "The nuttiest nut. Restores 50 HP.", price_coins=15, category="item"),
    Item("Refreshing Herb", "Cures all status ailments. Smells minty!", price_coins=12, category="item"),
    Item("1-Up Super", "Revives fallen bros with full HP!", price_coins=80, category="item"),
]


# ------------------------------
# Main Game
# ------------------------------

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("M&L Time Shop — GBA Enhanced Engine")
        self.clock = pygame.time.Clock()
        
        # Create world
        self.world = GridWorld(ASCII_MAP)
        
        # Create characters
        self.mario = Bro("Mario", self.world, 2, 7)
        self.luigi = Bro("Luigi", self.world, 3, 7)
        self.mario.is_lead = True
        
        # Create Ryen NPC position
        self.ryen_x, self.ryen_y = self.world.ryen_pos if self.world.ryen_pos else (20, 1)
        
        # UI systems
        self.textbox = TextBox(self.screen)
        self.inv = Inventory()
        self.shop = ShopUI(self.screen, self.inv, CATALOG)
        self.shop.on_close = self._shop_closed
        self.item_menu = ItemMenu(self.screen, self.inv)
        
        # Game state
        self.state = 'explore'  # 'explore' | 'dialog' | 'shop' | 'menu'
        self.camera_x = 0
        self.camera_y = 0
        
        # Fonts for labels
        self.small_font = pygame.font.Font(None, 20)
        
        # Initial items
        self.inv.add(Item("Pocket Shroom", "", 0, 0, False, "item"), 3)
        self.inv.add(Item("Refreshing Herb", "", 0, 0, False, "item"), 1)
        
        # Initial banner
        Banner.show(self.screen, "Press Tab/I for items • E to talk to Ryen")

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_input(event.key)
            
            self.update(dt)
            self.draw()
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

    def handle_input(self, key):
        # Dialog state
        if self.state == 'dialog':
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                self.textbox.next()
            return True
        
        # Shop state
        if self.state == 'shop':
            self.shop.handle_input(key)
            return True
        
        # Menu state
        if self.state == 'menu':
            self.item_menu.handle_input(key)
            if not self.item_menu.enabled:
                self.state = 'explore'
            return True
        
        # Explore state
        if key == pygame.K_ESCAPE:
            return False  # Quit
        
        lead = self.lead_bro()
        
        if key == pygame.K_TAB or key == pygame.K_i:
            self.state = 'menu'
            self.item_menu.open()
        elif key == pygame.K_q:
            self.swap_lead()
        elif key == pygame.K_e:
            # Check if near Ryen
            if self._adjacent_to_ryen(lead):
                self.open_ryen_shop_dialog()
            # Check if on portal
            elif self._on_portal(lead):
                self.enter_portal_cutscene()
        else:
            # Movement
            moved = False
            if key in (pygame.K_w, pygame.K_UP):
                moved = lead.try_step(0, -1)
            elif key in (pygame.K_s, pygame.K_DOWN):
                moved = lead.try_step(0, 1)
            elif key in (pygame.K_a, pygame.K_LEFT):
                moved = lead.try_step(-1, 0)
            elif key in (pygame.K_d, pygame.K_RIGHT):
                moved = lead.try_step(1, 0)
            
            if moved:
                self._after_lead_moved()
        
        return True

    def update(self, dt):
        # Update characters
        self.mario.update(dt)
        self.luigi.update(dt)
        
        # Update textbox
        self.textbox.update(dt)
        
        # Update banners
        Banner.update_all(dt)
        
        # Update camera to follow lead bro
        lead = self.lead_bro()
        target_x = lead.px - SCREEN_WIDTH // 2
        target_y = lead.py - SCREEN_HEIGHT // 2
        self.camera_x += (target_x - self.camera_x) * 0.15
        self.camera_y += (target_y - self.camera_y) * 0.15

    def draw(self):
        # GBA-style background gradient
        for y in range(0, SCREEN_HEIGHT, 4):
            fade = int(20 + (y / SCREEN_HEIGHT) * 10)
            pygame.draw.rect(self.screen, (fade, fade, fade + 8), (0, y, SCREEN_WIDTH, 4))
        
        # Draw world
        self.world.draw(self.screen, self.camera_x, self.camera_y)
        
        # Draw Ryen clerk NPC
        if self.world.ryen_pos:
            rx, ry = self.world.to_screen(self.ryen_x, self.ryen_y)
            rx -= self.camera_x
            ry -= self.camera_y
            
            # Ryen sprite
            # Shadow
            shadow_surf = pygame.Surface((30, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, SHADOW_COLOR, (0, 0, 30, 10))
            self.screen.blit(shadow_surf, (rx - 15, ry + 10))
            
            # Body
            pygame.draw.rect(self.screen, RYEN_COLOR, (rx - 14, ry - 20, 28, 36))
            pygame.draw.rect(self.screen, RYEN_DARK, (rx - 12, ry - 5, 24, 18))
            # Face
            pygame.draw.rect(self.screen, (248, 208, 176), (rx - 10, ry - 16, 20, 10))
            # Hair
            pygame.draw.rect(self.screen, (88, 64, 40), (rx - 14, ry - 20, 28, 6))
            # Outline
            pygame.draw.rect(self.screen, BLACK, (rx - 14, ry - 20, 28, 36), 2)
            
            # Label with background
            label_text = "Ryen (Shop)"
            label = self.small_font.render(label_text, True, WHITE)
            label_rect = label.get_rect(center=(rx, ry - 35))
            
            # Label background
            label_bg = label_rect.inflate(10, 4)
            pygame.draw.rect(self.screen, MENU_BG, label_bg)
            pygame.draw.rect(self.screen, MENU_BORDER_DARK, label_bg, 1)
            self.screen.blit(label, label_rect)
            
            # Interaction hint
            if self._adjacent_to_ryen(self.lead_bro()):
                hint = self.small_font.render("[E] Talk", True, ITEM_SELECT)
                hint_rect = hint.get_rect(center=(rx, ry - 52))
                hint_bg = hint_rect.inflate(8, 2)
                pygame.draw.rect(self.screen, BLACK, hint_bg)
                self.screen.blit(hint, hint_rect)
        
        # Draw characters with order based on Y position
        chars = [(self.mario.py, self.mario), (self.luigi.py, self.luigi)]
        chars.sort(key=lambda x: x[0])
        for _, char in chars:
            char.draw(self.screen, self.camera_x, self.camera_y)
        
        # Draw UI elements
        self.textbox.draw()
        self.shop.draw()
        self.item_menu.draw()
        Banner.draw_all()
        
        # HUD
        if self.state == 'explore':
            # HUD background
            hud_rect = pygame.Rect(8, 8, 250, 30)
            pygame.draw.rect(self.screen, MENU_BG, hud_rect)
            pygame.draw.rect(self.screen, MENU_BORDER_DARK, hud_rect, 2)
            
            lead_text = f"Lead: {self.lead_bro().name} (Q swap)"
            lead_surface = self.small_font.render(lead_text, True, WHITE)
            self.screen.blit(lead_surface, (15, 15))

    def lead_bro(self) -> Bro:
        return self.mario if self.mario.is_lead else self.luigi

    def swap_lead(self):
        self.mario.is_lead = not self.mario.is_lead
        self.luigi.is_lead = not self.luigi.is_lead
        Banner.show(self.screen, f"{self.lead_bro().name} takes the lead!")

    def _adjacent_to_ryen(self, bro: Bro) -> bool:
        if not self.world.ryen_pos:
            return False
        rx, ry = self.world.ryen_pos
        return abs(bro.gx - rx) <= 1 and abs(bro.gy - ry) <= 1

    def _on_portal(self, bro: Bro) -> bool:
        if not self.world.portal_pos:
            return False
        px, py = self.world.portal_pos
        return bro.gx == px and bro.gy == py

    def _after_lead_moved(self):
        # Make follower move to leader's previous position
        lead = self.mario if self.mario.is_lead else self.luigi
        follow = self.luigi if self.mario.is_lead else self.mario
        
        if lead.trail and not follow.moving:
            target_pos = lead.trail.pop(0)
            follow.target_gx, follow.target_gy = target_pos
            follow.moving = True
            follow.move_progress = 0.0

    def open_ryen_shop_dialog(self):
        self.state = 'dialog'
        lines = [
            ("Ryen", "Welcome to the Time Travel Shop! I'm Ryen, temporal merchant extraordinaire."),
            ("Ryen", "I deal in coins, time shards, and everything in between!"),
            ("Ryen", "My wares can help stabilize rifts and navigate the timestream safely."),
            ("Ryen", "Take a look at what's in stock today!")
        ]
        self.textbox.say(lines, on_complete=self._open_shop_after_dialog)

    def _open_shop_after_dialog(self):
        self.state = 'shop'
        self.shop.open()

    def _shop_closed(self):
        self.state = 'explore'
        Banner.show(self.screen, "Thanks for shopping at Ryen's!")

    def enter_portal_cutscene(self):
        self.state = 'dialog'
        lines = [
            ("Portal", "This temporal gateway hums with chrono energy..."),
            ("Ryen", "Careful! You'll need a Rift Stabilizer to use this safely."),
            ("Ryen", "Come see me at the shop if you need one!")
        ]
        def after():
            Banner.show(self.screen, "The portal shimmers mysteriously...")
            self.state = 'explore'
        self.textbox.say(lines, on_complete=after)


# ------------------------------
# Entry Point
# ------------------------------

if __name__ == '__main__':
    game = Game()
    game.run()
