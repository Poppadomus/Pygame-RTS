from __future__ import annotations

import math
import random
from dataclasses import InitVar, dataclass, field as dataclass_field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Type
from abc import ABC, abstractmethod

import pygame as pg
from pygame.math import Vector2

# ==================== CONSTANTS ====================
# Screen and map dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
CONSOLE_HEIGHT = 100
MAP_WIDTH = 2560
MAP_HEIGHT = 1440
TILE_SIZE = 40
MINI_MAP_WIDTH = 200
MINI_MAP_HEIGHT = 150
PAN_EDGE = 30  # Edge distance for mouse panning
PAN_SPEED = 10  # Speed of camera panning

# Game teams and states
class Team(Enum):
    GDI = 1  # Global Defense Initiative
    NOD = 2  # Brotherhood of Nod

class GameState(Enum):
    MENU = 1
    SKIRMISH_SETUP = 2
    PLAYING = 3
    VICTORY = 4
    DEFEAT = 5

# Team colors for rendering
GDI_COLOR = pg.Color(0, 200, 0)  # Green for GDI
NOD_COLOR = pg.Color(200, 0, 0)  # Red for NOD

# Available maps with dimensions and base colors
MAPS = {
    "Desert": {"width": 2560, "height": 1440, "color": (139, 120, 80)},
    "Forest": {"width": 3200, "height": 1800, "color": (34, 100, 34)},
    "Ice": {"width": 2560, "height": 1440, "color": (180, 200, 220)},
    "Urban": {"width": 2560, "height": 1440, "color": (100, 100, 100)},
}

# ==================== GEOMETRY ====================
# Snaps a position to the nearest grid point for building placement
def snap_to_grid(pos: tuple[float, float], grid_size: int = TILE_SIZE) -> tuple[float, float]:
    return (round(pos[0] / grid_size) * grid_size, round(pos[1] / grid_size) * grid_size)

# Validates if a building can be placed at the given position
def is_valid_building_position(
    position: tuple[float, float],
    team: Team,
    new_building_cls: Type,
    buildings: list,
    map_width: int = MAP_WIDTH,
    map_height: int = MAP_HEIGHT,
    building_range: int = 160,
) -> bool:
    # Create a temporary rect for the new building
    temp_rect = pg.Rect(position, new_building_cls.SIZE)
    # Check bounds
    if not (0 <= temp_rect.left and temp_rect.right <= map_width and
            0 <= temp_rect.top and temp_rect.bottom <= map_height):
        return False
    
    has_nearby_friendly = False
    # Check for nearby friendly buildings (for power/supply range)
    for building in buildings:
        if building.team == team and building.health > 0:
            dist = math.sqrt((position[0] - building.rect.centerx)**2 + (position[1] - building.rect.centery)**2)
            if dist <= building_range:
                has_nearby_friendly = True
        
        # Check for overlap with any existing building
        if building.health > 0 and building.rect.colliderect(temp_rect):
            return False
    
    # Allow HQ anywhere, others need nearby friendly
    return has_nearby_friendly or issubclass(new_building_cls, Headquarters)

# Finds a free spawn position for a unit near a target, avoiding overlaps
def find_free_spawn_position(building_pos: tuple, target_pos: tuple, global_buildings, global_units, unit_size=(40, 40)):
    for _ in range(20):  # Try up to 20 random offsets
        offset_x = random.uniform(-60, 60)
        offset_y = random.uniform(-60, 60)
        pos_x = target_pos[0] + offset_x
        pos_y = target_pos[1] + offset_y
        unit_rect = pg.Rect(pos_x - unit_size[0]/2, pos_y - unit_size[1]/2, unit_size[0], unit_size[1])
        overlaps_building = any(b.rect.colliderect(unit_rect) for b in global_buildings if b.health > 0)
        overlaps_unit = any(u.rect.colliderect(unit_rect) for u in global_units if u.health > 0)
        if not overlaps_building and not overlaps_unit:
            return (pos_x, pos_y)
    return target_pos  # Fallback to target if no free spot found

# Calculates positions for unit formation around a center
def calculate_formation_positions(
    center: tuple[float, float],
    target: tuple[float, float],
    num_units: int,
) -> list[tuple[float, float]]:
    if num_units == 0:
        return []
    positions = []
    spacing = 30  # Distance between units
    cols = max(1, int(math.sqrt(num_units)))  # Approximate square grid
    for i in range(num_units):
        row, col = i // cols, i % cols
        x = center[0] + (col - cols / 2) * spacing
        y = center[1] + (row - num_units / cols / 2) * spacing
        positions.append((x, y))
    return positions

# ==================== CAMERA ====================
# Manages the game camera/viewport
class Camera:
    def __init__(self):
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.width = SCREEN_WIDTH - 200  # Account for UI sidebar
        self.height = SCREEN_HEIGHT
        self.zoom = 1.0
        # Create rect first with initial size (zoom=1.0, so width/height unchanged)
        self.rect = pg.Rect(0, 0, self.width, self.height)
        # Now safe to update view size
        self.update_view_size()
    
    def update_view_size(self):
        view_w = self.width / self.zoom
        view_h = self.height / self.zoom
        self.rect.size = (view_w, view_h)
    
    def update_zoom(self, delta, mouse_world_pos=None):
        old_zoom = self.zoom
        old_center = self.rect.center
        if delta > 0:
            self.zoom = min(self.zoom * 1.2, 3.0)
        else:
            self.zoom = max(self.zoom / 1.2, 0.5)
        if self.zoom != old_zoom:
            self.update_view_size()
            if mouse_world_pos:
                self.rect.center = mouse_world_pos
            else:
                self.rect.center = old_center
            self.clamp()
    
    def world_to_screen(self, world_pos: tuple) -> tuple[float, float]:
        dx = world_pos[0] - self.rect.x
        dy = world_pos[1] - self.rect.y
        return (dx * self.zoom, dy * self.zoom)
    
    def screen_to_world(self, screen_pos: tuple) -> tuple[float, float]:
        return (
            self.rect.x + screen_pos[0] / self.zoom,
            self.rect.y + screen_pos[1] / self.zoom
        )
    
    def get_screen_rect(self, world_rect: pg.Rect) -> pg.Rect:
        screen_left = (world_rect.left - self.rect.x) * self.zoom
        screen_top = (world_rect.top - self.rect.y) * self.zoom
        screen_w = world_rect.width * self.zoom
        screen_h = world_rect.height * self.zoom
        return pg.Rect(screen_left, screen_top, screen_w, screen_h)
    
    # Updates camera position based on input
    def update(self, selected_units: list, mouse_pos: tuple, interface_rect: pg.Rect, keys=None):
        if keys is None:
            keys = pg.key.get_pressed()
        
        pressed_pan = keys[pg.K_w] or keys[pg.K_a] or keys[pg.K_s] or keys[pg.K_d]
        
        mx, my = mouse_pos
        
        # Edge pan: move camera when mouse near screen edges
        if mx < PAN_EDGE and self.rect.left > 0:
            self.rect.x -= PAN_SPEED
        if mx > SCREEN_WIDTH - PAN_EDGE and self.rect.right < self.map_width:
            self.rect.x += PAN_SPEED
        if my < PAN_EDGE and self.rect.top > 0:
            self.rect.y -= PAN_SPEED
        if my > SCREEN_HEIGHT - PAN_EDGE and self.rect.bottom < self.map_height:
            self.rect.y += PAN_SPEED
        
        # WASD pan: keyboard movement
        if keys[pg.K_w] and self.rect.top > 0:
            self.rect.y -= PAN_SPEED
        if keys[pg.K_s] and self.rect.bottom < self.map_height:
            self.rect.y += PAN_SPEED
        if keys[pg.K_a] and self.rect.left > 0:
            self.rect.x -= PAN_SPEED
        if keys[pg.K_d] and self.rect.right < self.map_width:
            self.rect.x += PAN_SPEED
        
        # Center on selected units if no panning
        if interface_rect.collidepoint(mx, my):
            self.clamp()
            return
        
        if selected_units and not pressed_pan:
            avg_x = sum(u.position[0] for u in selected_units) / len(selected_units)
            avg_y = sum(u.position[1] for u in selected_units) / len(selected_units)
            self.rect.centerx = avg_x
            self.rect.centery = avg_y
        
        self.clamp()  # Ensure camera stays in bounds
    
    # Clamps camera rect to map bounds
    def clamp(self):
        self.rect.x = max(0, min(self.rect.x, self.map_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, self.map_height - self.rect.height))
    
    # Applies camera offset to a rect for screen drawing
    def apply(self, rect: pg.Rect) -> pg.Rect:
        return rect.move(-self.rect.x, -self.rect.y)

# ==================== FOG OF WAR ====================
# Handles fog of war visibility and exploration
class FogOfWar:
    def __init__(self, map_width: int, map_height: int, tile_size: int = TILE_SIZE):
        self.tile_size = tile_size
        num_tiles_x = map_width // tile_size
        num_tiles_y = map_height // tile_size
        self.explored = [[False] * num_tiles_y for _ in range(num_tiles_x)]  # Explored tiles
        self.visible = [[False] * num_tiles_y for _ in range(num_tiles_x)]  # Currently visible tiles
        self.surface = pg.Surface((map_width, map_height), pg.SRCALPHA)  # Overlay surface
        self.surface.fill((0, 0, 0, 255))  # Fully black initially
    
    # Reveals tiles in a radius around a center point
    def reveal(self, center: tuple, radius: int):
        cx, cy = center
        tile_x, tile_y = int(cx // self.tile_size), int(cy // self.tile_size)
        radius_tiles = radius // self.tile_size
        for ty in range(max(0, tile_y - radius_tiles), min(len(self.explored[0]), tile_y + radius_tiles + 1)):
            for tx in range(max(0, tile_x - radius_tiles), min(len(self.explored), tile_x + radius_tiles + 1)):
                tile_center_x = tx * self.tile_size + self.tile_size // 2
                tile_center_y = ty * self.tile_size + self.tile_size // 2
                if math.sqrt((cx - tile_center_x)**2 + (cy - tile_center_y)**2) <= radius:
                    self.explored[tx][ty] = True
                    self.visible[tx][ty] = True
    
    # Updates visible tiles based on friendly units and buildings
    def update_visibility(self, units, buildings, team: Team):
        num_tiles_x = len(self.visible)
        num_tiles_y = len(self.visible[0])
        self.visible = [[False] * num_tiles_y for _ in range(num_tiles_x)]  # Reset visibility
        for unit in units:
            if unit.team == team:
                self.reveal(unit.position, 150)  # Unit sight radius
        for building in buildings:
            if building.team == team and building.health > 0:
                self.reveal(building.position, 200)  # Building sight radius
        # Update seen status for buildings
        for building in buildings:
            if building.health > 0:
                tx, ty = int(building.position[0] // self.tile_size), int(building.position[1] // self.tile_size)
                if 0 <= tx < num_tiles_x and 0 <= ty < num_tiles_y:
                    building.is_seen = getattr(building, 'is_seen', False) or self.visible[tx][ty]
    
    # Checks if a position is currently visible
    def is_visible(self, pos: tuple) -> bool:
        tx, ty = int(pos[0] // self.tile_size), int(pos[1] // self.tile_size)
        if 0 <= tx < len(self.visible) and 0 <= ty < len(self.visible[0]):
            return self.visible[tx][ty]
        return False
    
    # Checks if a position has been explored (shaded fog)
    def is_explored(self, pos: tuple) -> bool:
        tx, ty = int(pos[0] // self.tile_size), int(pos[1] // self.tile_size)
        if 0 <= tx < len(self.explored) and 0 <= ty < len(self.explored[0]):
            return self.explored[tx][ty]
        return False
    
    # Draws the fog overlay on the surface
    def draw(self, surface: pg.Surface, camera: Camera):
        self.surface.fill((0, 0, 0, 255))  # Reset to full black
        for ty in range(len(self.explored[0])):
            for tx in range(len(self.explored)):
                if self.explored[tx][ty]:
                    alpha = 0 if self.visible[tx][ty] else 100  # Transparent if visible, semi-black if explored
                    pg.draw.rect(self.surface, (0, 0, 0, alpha), (tx * self.tile_size, ty * self.tile_size, self.tile_size, self.tile_size))
        view_rect = camera.rect.clip(pg.Rect(0, 0, self.surface.get_width(), self.surface.get_height()))
        game_w = int(camera.width)
        game_h = int(camera.height)
        if view_rect.width > 0 and view_rect.height > 0:
            visible_fog = self.surface.subsurface(view_rect)
            scaled_fog = pg.transform.smoothscale(visible_fog, (game_w, game_h))
            surface.blit(scaled_fog, (0, 0))

# ==================== PARTICLES ====================
# Base particle class for effects like explosions or muzzle flash
class Particle(pg.sprite.Sprite):
    def __init__(self, pos: tuple, vx: float, vy: float, size: int, color: pg.Color, lifetime: int):
        super().__init__()
        self.position = Vector2(pos)
        self.vx = vx  # Horizontal velocity
        self.vy = vy  # Vertical velocity
        self.size = size
        self.color = color
        self.lifetime = lifetime
        self.age = 0
        self.image = pg.Surface((size, size), pg.SRCALPHA)
        pg.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect = self.image.get_rect(center=self.position)
    
    # Updates particle position and alpha
    def update(self):
        self.position.x += self.vx
        self.position.y += self.vy
        self.age += 1
        alpha = int(255 * (1 - self.age / self.lifetime))  # Fade out
        self.image.set_alpha(alpha)
        self.rect.center = self.position
        if self.age >= self.lifetime:
            self.kill()  # Remove when lifetime expires
    
    # Draws the particle with camera offset
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_screen(self.position)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)

# ==================== PROJECTILE ====================
# Projectile class for ranged attacks (e.g., tank shells)
class Projectile(pg.sprite.Sprite):
    def __init__(self, pos: tuple, target, damage: int, team: Team):
        super().__init__()
        self.position = Vector2(pos)
        self.target = target  # Target object or position
        self.damage = damage
        self.team = team
        self.speed = 5
        self.image = pg.Surface((8, 8))
        self.image.fill(pg.Color(255, 255, 0))  # Yellow bullet
        self.rect = self.image.get_rect(center=self.position)
    
    # Updates projectile towards target
    def update(self, particles: pg.sprite.Group):
        if self.target and self.target.health > 0:
            direction = Vector2(self.target.position) - self.position
            if direction.length() > 0:
                direction = direction.normalize()
                self.position += direction * self.speed
                self.rect.center = self.position
        else:
            self.kill()  # Remove if target destroyed
    
    # Draws the projectile with camera offset
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_screen(self.position)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)

# ==================== GAME OBJECTS ====================
# Abstract base class for all game objects (units, buildings)
class GameObject(pg.sprite.Sprite, ABC):
    def __init__(self, position: tuple, team: Team):
        super().__init__()
        self.position = Vector2(position)
        self.team = team
        self.health = 100
        self.max_health = 100
        self.under_attack = False
        self.selected = False
        self.is_seen = False
        self.image = pg.Surface((32, 32))
        self.rect = self.image.get_rect(center=position)
    
    # Calculates distance to another position
    def distance_to(self, other_pos: tuple) -> float:
        return self.position.distance_to(other_pos)
    
    # Calculates displacement vector to another position
    def displacement_to(self, other_pos: tuple) -> tuple[float, float]:
        dx = other_pos[0] - self.position.x
        dy = other_pos[1] - self.position.y
        return (dx, dy)
    
    # Draws the object and selection circle if selected
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_screen(self.position)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)
        if self.selected:
            radius = max(self.rect.width, self.rect.height) / 2 * camera.zoom + 3
            pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * camera.zoom))
    
    # Draws health bar if damaged or under attack
    def draw_health_bar(self, screen, camera):
        if self.health >= self.max_health and not self.under_attack:
            return
        screen_pos = camera.world_to_screen(self.position)
        health_ratio = self.health / self.max_health
        color = (0, 255, 0) if health_ratio > 0.5 else (255, 0, 0)
        bar_width = 50  # Fixed screen size
        bar_height = 8
        bar_x = screen_pos[0] - bar_width / 2
        bar_y = screen_pos[1] - (self.rect.height / 2 * camera.zoom) - bar_height - 2
        pg.draw.rect(screen, (0, 0, 0), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
        pg.draw.rect(screen, color, (bar_x, bar_y, bar_width * health_ratio, bar_height))
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
    
    @abstractmethod
    def update(self): pass  # Must be implemented by subclasses

# Base unit class inheriting from GameObject
class Unit(GameObject):
    COST = 100
    ATTACK_RANGE = 200
    ATTACK_DAMAGE = 10
    ATTACK_COOLDOWN_PERIOD = 30
    
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team)
        self.target = None  # Movement target position
        self.target_unit = None  # Attack target unit/building
        self.cooldown_timer = 0
        self.speed = 2
        self.formation_target = None
        self.player_ordered = False
    
    # Updates unit movement and cooldown
    def update(self):
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        
        if self.target:
            direction = Vector2(self.target) - self.position
            if direction.length() > 5:  # Stop when close
                direction = direction.normalize()
                self.position += direction * self.speed
        
        self.rect.center = self.position

# Infantry unit: basic foot soldier
class Infantry(Unit):
    COST = 100
    ATTACK_RANGE = 150
    ATTACK_DAMAGE = 15
    
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team)
        self.image = pg.Surface((16, 16), pg.SRCALPHA)
        # Simple pixel art: helmet, body, legs, weapon
        pg.draw.circle(self.image, (150, 150, 150), (8, 4), 4)  # Helmet
        pg.draw.rect(self.image, (100, 100, 100), (6, 8, 4, 8))  # Body
        pg.draw.line(self.image, (80, 80, 80), (8, 16), (8, 20))  # Legs
        pg.draw.line(self.image, (120, 120, 120), (10, 10), (14, 10))  # Weapon
        # Team color on body
        pg.draw.rect(self.image, GDI_COLOR if team == Team.GDI else NOD_COLOR, (6, 8, 4, 2))
        self.rect = self.image.get_rect(center=position)

# Tank unit: armored vehicle with ranged attack
class Tank(Unit):
    COST = 300
    ATTACK_RANGE = 250
    ATTACK_DAMAGE = 30
    
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team)
        self.angle = 0  # Turret rotation angle
        self.recoil = 0  # Recoil animation
        self.image = pg.Surface((30, 20), pg.SRCALPHA)
        # Tracks and body
        pg.draw.rect(self.image, (50, 50, 50), (0, -2, 30, 4))  # Top track
        pg.draw.rect(self.image, (50, 50, 50), (0, 18, 30, 4))  # Bottom track
        pg.draw.rect(self.image, (100, 100, 100), (0, 0, 30, 20))  # Body
        pg.draw.rect(self.image, (80, 80, 80), (2, 2, 26, 16))  # Inner body
        # Team color
        pg.draw.rect(self.image, GDI_COLOR if team == Team.GDI else NOD_COLOR, (0, 0, 30, 2))
        self.rect = self.image.get_rect(center=position)

# Grenadier unit: close-range explosive infantry
class Grenadier(Unit):
    COST = 250
    ATTACK_RANGE = 120
    ATTACK_DAMAGE = 30
    
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team)
        self.image = pg.Surface((16, 16), pg.SRCALPHA)
        # Helmet, body, legs
        pg.draw.circle(self.image, (150, 150, 150), (8, 4), 4)  # Helmet
        pg.draw.rect(self.image, (100, 100, 100), (6, 8, 4, 8))  # Body
        pg.draw.line(self.image, (80, 80, 80), (8, 16), (8, 20))  # Legs
        # Grenade visual
        pg.draw.circle(self.image, (200, 0, 0), (12, 10), 3)
        # Team color
        pg.draw.rect(self.image, GDI_COLOR if team == Team.GDI else NOD_COLOR, (6, 8, 4, 2))
        self.rect = self.image.get_rect(center=position)

# Machine Gun Vehicle: rapid-fire support vehicle
class MachineGunVehicle(Unit):
    COST = 400
    ATTACK_RANGE = 160
    ATTACK_DAMAGE = 8
    
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team)
        self.angle = 0
        self.recoil = 0
        self.image = pg.Surface((35, 25), pg.SRCALPHA)
        # Body and tracks
        pg.draw.rect(self.image, (100, 100, 100), (0, 0, 35, 25))  # Body
        pg.draw.rect(self.image, (80, 80, 80), (2, 2, 31, 21))  # Inner
        pg.draw.rect(self.image, (50, 50, 50), (0, -2, 35, 4))  # Top track
        pg.draw.rect(self.image, (50, 50, 50), (0, 23, 35, 4))  # Bottom track
        # Team color
        pg.draw.rect(self.image, GDI_COLOR if team == Team.GDI else NOD_COLOR, (0, 0, 35, 2))
        self.rect = self.image.get_rect(center=position)
        self.speed = 3  # Faster than basic tank

# Harvester unit: resource collector
class Harvester(Unit):
    COST = 400
    ATTACK_RANGE = 50
    
    def __init__(self, position: tuple, team: Team, hq):
        super().__init__(position, team)
        self.hq = hq  # Reference to headquarters for unloading
        self.carrying = 0  # Current iron load
        self.target_field = None  # Current iron field target
        self.state = "moving_to_field"  # State machine: moving_to_field, harvesting, returning
        self.image = pg.Surface((50, 30), pg.SRCALPHA)
        # Body and wheels
        pg.draw.rect(self.image, (120, 120, 120), (0, 0, 50, 30))  # Outer body
        pg.draw.rect(self.image, (100, 100, 100), (5, 5, 40, 20))  # Inner
        pg.draw.circle(self.image, (50, 50, 50), (10, 30), 5)  # Left wheel
        pg.draw.circle(self.image, (50, 50, 50), (40, 30), 5)  # Right wheel
        # Team color
        pg.draw.rect(self.image, GDI_COLOR if team == Team.GDI else NOD_COLOR, (0, 0, 50, 2))
        self.rect = self.image.get_rect(center=position)
    
    # Updates harvester AI: find field, harvest, return to HQ
    def update(self, enemy_units: list = None, iron_fields: list = None):
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        
        # Unload at HQ if carrying
        if self.carrying > 0 and self.distance_to(self.hq.position) < 50:
            self.hq.iron += self.carrying
            self.carrying = 0
            self.target = None
            self.target_field = None
            self.state = "moving_to_field"
        
        if self.state == "moving_to_field":
            # Find nearest field if none or depleted
            if not self.target_field or self.target_field.resources <= 0:
                if iron_fields:
                    self.target_field = min((f for f in iron_fields if f.resources > 0),
                                           key=lambda f: self.distance_to(f.position), default=None)
            
            if self.target_field:
                self.target = self.target_field.rect.center
                direction = Vector2(self.target) - self.position
                if direction.length() > 30:
                    direction = direction.normalize()
                    self.position += direction * self.speed
                else:
                    self.state = "harvesting"
                    self.target = None
            else:
                self.target = None  # No target if no fields left
        
        elif self.state == "harvesting":
            if self.target_field and self.target_field.resources > 0:
                amount = min(20, self.target_field.resources)  # Harvest batch
                self.target_field.resources -= amount
                self.carrying += amount
                self.state = "returning"
                self.target = self.hq.position
            else:
                # Field depleted (by another harvester), find new one
                self.state = "moving_to_field"
                self.target_field = None
                self.target = None
        
        elif self.state == "returning":
            direction = Vector2(self.hq.position) - self.position
            if direction.length() > 30:
                direction = direction.normalize()
                self.position += direction * self.speed
            else:
                self.hq.iron += self.carrying
                self.carrying = 0
                self.state = "moving_to_field"
        
        self.rect.center = self.position

# ==================== BUILDINGS ====================
# Base building class inheriting from GameObject
class Building(GameObject):
    COST = 500
    SIZE = (80, 80)
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team)
        self.selected = False
        self.font = font
        self.image = pg.Surface(self.SIZE)
        self.rect = self.image.get_rect(topleft=position)
        self.position = Vector2(self.rect.center)
        self.is_seen = False
        self.health = 200
        self.max_health = 200
    
    # Draws building and selection/rally point if selected
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_screen(self.position)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)
        if self.selected:
            screen_rect = camera.get_screen_rect(self.rect)
            pg.draw.rect(surface, (255, 255, 0), screen_rect, int(3 * camera.zoom))
        if self.selected and hasattr(self, 'rally_point'):
            rally_screen = camera.world_to_screen(self.rally_point)
            pg.draw.circle(surface, (0, 255, 0), (int(rally_screen[0]), int(rally_screen[1])), 5)
    
    # Draws health bar if selected or damaged
    def draw_health_bar(self, screen, camera):
        if not (self.selected or self.health < self.max_health):
            return
        screen_pos = camera.world_to_screen(self.position)
        health_ratio = self.health / self.max_health
        color = (0, 255, 0) if health_ratio > 0.5 else (255, 0, 0)
        bar_width = 50  # Fixed screen size
        bar_height = 8
        bar_x = screen_pos[0] - bar_width / 2
        bar_y = screen_pos[1] - (self.rect.height / 2 * camera.zoom) - bar_height - 2
        pg.draw.rect(screen, (0, 0, 0), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
        pg.draw.rect(screen, color, (bar_x, bar_y, bar_width * health_ratio, bar_height))
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
    
    # Basic update (overridden in subclasses)
    def update(self, particles: pg.sprite.Group = None, **kwargs):
        pass

# Headquarters: main base building, resource storage, production hub
class Headquarters(Building):
    COST = 1000
    SIZE = (100, 100)
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team, font)
        self.image.fill((80, 80, 80))  # Base gray concrete
        team_color = GDI_COLOR if team == Team.GDI else NOD_COLOR
        # Main structure: taller building
        pg.draw.rect(self.image, (100, 100, 100), (10, 10, 80, 70))  # Inner walls
        pg.draw.rect(self.image, team_color, (10, 10, 80, 20))  # Top roof with team color
        # Windows: small blue rectangles on sides
        for i in range(3):
            win_y = 30 + i * 15
            pg.draw.rect(self.image, (100, 150, 255), (15, win_y, 8, 6))  # Left windows
            pg.draw.rect(self.image, (100, 150, 255), (77, win_y, 8, 6))  # Right windows
        # Door/gate at front bottom
        pg.draw.rect(self.image, (50, 50, 50), (40, 80, 20, 20))  # Main door
        pg.draw.line(self.image, (30, 30, 30), (40, 80), (60, 100), 3)  # Gate bar
        # Details: antennas or flags on roof
        pg.draw.line(self.image, team_color, (50, 10), (50, 0), 2)  # Antenna
        # Team emblem
        pg.draw.circle(self.image, team_color, (50, 50), 10)
        self.iron = 500  # Starting resources
        self.power_output = 100
        self.power_usage = 50
        self.has_enough_power = True
        self.production_queue: list[Dict[str, Any]] = []  # Queue for production (future use)
        self.production_timer = None
        self.pending_building = None
        self.pending_building_pos = None
        self.rally_point = Vector2(position[0] + 100 if team == Team.GDI else position[0] - 100, position[1])
        self.health = 500
        self.max_health = 500
    
    # Calculates production time for a unit (placeholder)
    def get_production_time(self, unit_class, friendly_buildings):
        return 60
    
    # Places a building if valid
    def place_building(self, position: tuple, unit_cls, all_buildings):
        if is_valid_building_position(position, self.team, unit_cls, all_buildings):
            building = unit_cls(position, self.team, self.font)
            all_buildings.add(building)
            self.iron -= unit_cls.COST
            self.pending_building = None
    
    # Updates HQ (placeholder for production)
    def update(self, particles: pg.sprite.Group = None, friendly_units=None, friendly_buildings=None, all_units=None, global_buildings=None):
        # Production queue not used for units; only for potential future building queuing if implemented
        pass

# Barracks: produces infantry units
class Barracks(Building):
    COST = 300
    SIZE = (80, 80)
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team, font)
        self.image.fill((100, 100, 100))  # Base gray
        # Structure: bunker-like with sloped roof
        pg.draw.rect(self.image, (120, 120, 120), (5, 5, 70, 60))  # Inner body
        pg.draw.polygon(self.image, (90, 90, 90), [(0, 5), (80, 5), (60, 0), (20, 0)])  # Sloped roof
        # Windows: two small ones
        pg.draw.rect(self.image, (100, 150, 255), (20, 30, 8, 6))
        pg.draw.rect(self.image, (100, 150, 255), (52, 30, 8, 6))
        # Main gate/door at front, wider for units
        pg.draw.rect(self.image, (60, 60, 60), (30, 65, 20, 15))  # Door frame
        pg.draw.line(self.image, (40, 40, 40), (30, 65), (50, 80), 2)  # Left gate half
        pg.draw.line(self.image, (40, 40, 40), (50, 65), (70, 80), 2)  # Right gate half
        # Details: vents or barrels
        pg.draw.rect(self.image, (70, 70, 70), (70, 10, 5, 10))  # Vent
        self.rally_point = Vector2(self.rect.centerx + 80, self.rect.centery)
        self.production_queue: list[Dict[str, Any]] = []
        self.production_timer = None
        self.gate_open = False
        self.gate_timer = 0
    
    # Gets production time for a unit
    def get_production_time(self, unit_class):
        return 60
    
    # Updates production queue and spawns units
    def update(self, particles: pg.sprite.Group = None, friendly_units=None, all_units=None, global_buildings=None, **kwargs):
        if self.gate_open:
            self.gate_timer -= 1
            if self.gate_timer <= 0:
                self.gate_open = False
        
        if self.production_queue:
            if self.production_timer is None:
                self.production_timer = self.get_production_time(self.production_queue[0]['cls'])
            
            self.production_timer -= 1
            if self.production_timer <= 0:
                item = self.production_queue.pop(0)
                cls = item['cls']
                repeat = item['repeat']
                if issubclass(cls, Unit):
                    spawn_pos = (self.rect.right, self.rect.centery)
                    new_unit = cls(spawn_pos, self.team)
                    new_unit.position = Vector2(spawn_pos)
                    new_unit.rect.center = new_unit.position
                    new_unit.target = self.rally_point
                    if friendly_units is not None:
                        friendly_units.add(new_unit)
                    if all_units is not None:
                        all_units.add(new_unit)
                    self.gate_open = True
                    self.gate_timer = 60
                if repeat:
                    self.production_queue.append({'cls': cls, 'repeat': True})
                self.production_timer = None

    # Draws building with animated gate if open
    def draw(self, surface: pg.Surface, camera: Camera):
        super().draw(surface, camera)
        if self.gate_open:
            door_width = 20
            door_height = self.rect.height - 20
            half_door = door_width // 2
            left_door = pg.Rect(self.rect.right - door_width, self.rect.top + 10, half_door, door_height)
            right_door = pg.Rect(self.rect.right - half_door, self.rect.top + 10, half_door, door_height)
            open_left = left_door.move(-15, 0)
            open_right = right_door.move(15, 0)
            pg.draw.rect(surface, (60, 60, 60), camera.get_screen_rect(open_left))
            pg.draw.rect(surface, (60, 60, 60), camera.get_screen_rect(open_right))

# War Factory: produces vehicle units
class WarFactory(Building):
    COST = 500
    SIZE = (100, 80)
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team, font)
        self.image.fill((150, 150, 150))  # Base light gray
        # Structure: industrial with chimney
        pg.draw.rect(self.image, (130, 130, 130), (10, 10, 80, 50))  # Main body
        pg.draw.rect(self.image, (140, 140, 140), (0, 0, 100, 80))  # Outer frame
        # Chimney
        pg.draw.rect(self.image, (110, 110, 110), (85, 0, 15, 30))
        pg.draw.rect(self.image, (200, 200, 200), (87, 2, 11, 26))  # Smoke hole
        # Windows: larger for factory
        pg.draw.rect(self.image, (100, 150, 255), (20, 20, 12, 8))
        pg.draw.rect(self.image, (100, 150, 255), (68, 20, 12, 8))
        pg.draw.rect(self.image, (100, 150, 255), (20, 40, 12, 8))
        pg.draw.rect(self.image, (100, 150, 255), (68, 40, 12, 8))
        # Large gate for vehicles
        pg.draw.rect(self.image, (70, 70, 70), (40, 60, 20, 20))  # Gate frame
        pg.draw.line(self.image, (50, 50, 50), (40, 60), (60, 80), 3)  # Left gate
        pg.draw.line(self.image, (50, 50, 50), (60, 60), (80, 80), 3)  # Right gate
        # Details: conveyor belt hint
        pg.draw.line(self.image, (90, 90, 90), (10, 70), (90, 70), 2)
        self.rally_point = Vector2(self.rect.centerx + 80, self.rect.centery)
        self.production_queue: list[Dict[str, Any]] = []
        self.production_timer = None
        self.parent_hq = None
        self.gate_open = False
        self.gate_timer = 0
    
    # Gets production time for a unit
    def get_production_time(self, unit_class):
        return 60
    
    # Updates production queue and spawns units (handles Harvester specially)
    def update(self, particles: pg.sprite.Group = None, friendly_units=None, all_units=None, global_buildings=None, **kwargs):
        if self.gate_open:
            self.gate_timer -= 1
            if self.gate_timer <= 0:
                self.gate_open = False
        
        if self.production_queue:
            if self.production_timer is None:
                self.production_timer = self.get_production_time(self.production_queue[0]['cls'])
            
            self.production_timer -= 1
            if self.production_timer <= 0:
                item = self.production_queue.pop(0)
                cls = item['cls']
                repeat = item['repeat']
                if issubclass(cls, Unit):
                    spawn_pos = (self.rect.right, self.rect.centery)
                    if cls == Harvester:
                        new_unit = cls(spawn_pos, self.team, self.parent_hq)
                    else:
                        new_unit = cls(spawn_pos, self.team)
                    new_unit.position = Vector2(spawn_pos)
                    new_unit.rect.center = new_unit.position
                    new_unit.target = self.rally_point
                    if friendly_units is not None:
                        friendly_units.add(new_unit)
                    if all_units is not None:
                        all_units.add(new_unit)
                    self.gate_open = True
                    self.gate_timer = 60
                if repeat:
                    self.production_queue.append({'cls': cls, 'repeat': True})
                self.production_timer = None

    # Draws building with animated gate if open
    def draw(self, surface: pg.Surface, camera: Camera):
        super().draw(surface, camera)
        if self.gate_open:
            door_width = 20
            door_height = self.rect.height - 20
            half_door = door_width // 2
            left_door = pg.Rect(self.rect.right - door_width, self.rect.top + 10, half_door, door_height)
            right_door = pg.Rect(self.rect.right - half_door, self.rect.top + 10, half_door, door_height)
            open_left = left_door.move(-15, 0)
            open_right = right_door.move(15, 0)
            pg.draw.rect(surface, (60, 60, 60), camera.get_screen_rect(open_left))
            pg.draw.rect(surface, (60, 60, 60), camera.get_screen_rect(open_right))

# Power Plant: provides power (visual only for now)
class PowerPlant(Building):
    COST = 300
    SIZE = (80, 80)
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team, font)
        self.image.fill((200, 180, 100))  # Base yellow/ochre
        # Structure: power plant with towers
        pg.draw.rect(self.image, (220, 200, 120), (10, 10, 60, 50))  # Main building
        # Two smokestacks
        pg.draw.rect(self.image, (150, 150, 150), (65, 5, 10, 25))
        pg.draw.rect(self.image, (150, 150, 150), (65, 40, 10, 25))
        pg.draw.rect(self.image, (100, 100, 100), (67, 7, 6, 23))  # Stack opening 1
        pg.draw.rect(self.image, (100, 100, 100), (67, 42, 6, 23))  # Stack opening 2
        # Windows: glowing yellow
        for i in range(2):
            win_y = 20 + i * 15
            pg.draw.rect(self.image, (255, 255, 150), (20, win_y, 8, 6))
            pg.draw.rect(self.image, (255, 255, 150), (52, win_y, 8, 6))
        # Door: small at base
        pg.draw.rect(self.image, (120, 120, 120), (35, 60, 10, 20))
        # Details: pipes
        pg.draw.line(self.image, (140, 140, 140), (70, 30), (80, 30), 3)
        pg.draw.line(self.image, (140, 140, 140), (70, 50), (80, 50), 3)

# Turret: defensive structure with auto-targeting
class Turret(Building):
    COST = 400
    SIZE = (60, 60)
    ATTACK_RANGE = 300
    
    def __init__(self, position: tuple, team: Team, font):
        super().__init__(position, team, font)
        self.image = pg.Surface(self.SIZE, pg.SRCALPHA)
        team_color = GDI_COLOR if team == Team.GDI else NOD_COLOR
        # Base: fortified pedestal
        pg.draw.rect(self.image, (100, 100, 100), (15, 35, 30, 25))  # Pedestal
        pg.draw.rect(self.image, (80, 80, 80), (17, 37, 26, 21))  # Inner
        # Turret body: circular with details
        pg.draw.circle(self.image, team_color, (30, 25), 12)
        pg.draw.circle(self.image, (120, 120, 120), (30, 25), 10)  # Inner circle
        # Barrel: longer with reinforcements
        pg.draw.line(self.image, team_color, (30, 25), (30, 5), 5)
        pg.draw.line(self.image, (90, 90, 90), (28, 20), (28, 10), 2)  # Side support
        pg.draw.line(self.image, (90, 90, 90), (32, 20), (32, 10), 2)  # Side support
        # Details: small window or sensor
        pg.draw.circle(self.image, (100, 150, 255), (30, 28), 3)
        # Base details: bolts
        pg.draw.circle(self.image, (60, 60, 60), (20, 55), 2)
        pg.draw.circle(self.image, (60, 60, 60), (40, 55), 2)
        self.cooldown_timer = 0
    
    # Updates turret targeting and firing
    def update(self, particles: pg.sprite.Group = None, projectiles: pg.sprite.Group = None, enemy_units: list = None, **kwargs):
        if not enemy_units or not projectiles:
            return
        
        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1
        
        if self.cooldown_timer == 0:
            closest = min(
                (u for u in enemy_units if u.health > 0),
                key=lambda u: self.distance_to(u.position),
                default=None
            )
            
            if closest and self.distance_to(closest.position) <= self.ATTACK_RANGE:
                projectiles.add(Projectile(self.position, closest, 20, self.team))
                self.cooldown_timer = 30

# Iron Field: resource node for harvesters
class IronField(pg.sprite.Sprite):
    def __init__(self, x: float, y: float, font):
        super().__init__()
        self.position = Vector2(x + 15, y + 15)  # center
        self.rect = pg.Rect(x, y, 30, 30)
        self.resources = 100  # Remaining iron
        self.font = font
        self.image = pg.Surface((30, 30))
        self.image.fill((100, 100, 0))  # Greenish resource tile
    
    def update(self):
        pass
    
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_screen(self.position)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)

# ==================== GAME CONSOLE ====================
# Placeholder for in-game console/log (not implemented)
class GameConsole:
    def __init__(self):
        self.messages = []
    
    def log(self, message: str):
        self.messages.append(message)
    
    def handle_event(self, event):
        pass
    
    def draw(self, surface: pg.Surface):
        pass

# ==================== AI ====================
# Simple AI controller for enemy team
class AI:
    def __init__(self, hq, console):
        self.hq = hq
        self.console = console
        self.action_timer = 0
    
    # Updates AI decisions periodically
    def update(self, friendly_units, friendly_buildings, enemy_units, enemy_buildings, iron_fields, all_buildings):
        self.action_timer += 1
        if self.action_timer > 120:  # Act every 2 seconds at 60 FPS
            self.action_timer = 0
            if self.hq.iron >= Infantry.COST:
                barracks = next((b for b in friendly_buildings if isinstance(b, Barracks) and b.health > 0), None)
                if barracks:
                    barracks.production_queue.append({'cls': Infantry, 'repeat': False})
                    self.hq.iron -= Infantry.COST

# ==================== PRODUCTION INTERFACE ====================
# UI for production and resource management sidebar
@dataclass(kw_only=True)
class ProductionInterface:
    WIDTH: ClassVar = 200
    MARGIN_X: ClassVar = 20
    IRON_POS_Y: ClassVar = 10
    POWER_POS_Y: ClassVar = 35
    TOP_BUTTONS_POS_Y: ClassVar = 60
    TOP_BUTTON_WIDTH: ClassVar = 55
    TOP_BUTTON_HEIGHT: ClassVar = 25
    TOP_BUTTON_SPACING: ClassVar = 5
    PROD_ITEMS_START_Y: ClassVar = 100
    ITEM_HEIGHT: ClassVar = 50
    ITEM_BUTTON_HEIGHT: ClassVar = 40
    PRODUCTION_QUEUE_POS_Y: ClassVar = 300
    BUTTON_SPACING_Y: ClassVar = 10
    BUTTON_RADIUS: ClassVar = 5
    ACTION_BUTTON_HEIGHT: ClassVar = 40
    FILL_COLOR: ClassVar = pg.Color(60, 60, 60)
    LINE_COLOR: ClassVar = pg.Color(100, 100, 100)
    ACTIVE_TAB_COLOR: ClassVar = pg.Color(0, 200, 200)
    INACTIVE_TAB_COLOR: ClassVar = pg.Color(50, 50, 50)
    ACTION_ALLOWED_COLOR: ClassVar = pg.Color(0, 200, 0)
    ACTION_BLOCKED_COLOR: ClassVar = pg.Color(200, 0, 0)
    MAX_PRODUCTION_QUEUE_LENGTH: ClassVar = 5
    PLACEMENT_VALID_COLOR = (0, 255, 0)
    PLACEMENT_INVALID_COLOR = (255, 0, 0)
    
    _BUTTON_WIDTH = WIDTH - 2 * MARGIN_X
    
    hq: Headquarters
    surface: pg.Surface = dataclass_field(init=False)
    top_rects: dict = dataclass_field(init=False, default_factory=dict)
    item_rects: dict = dataclass_field(init=False, default_factory=dict)
    placing_cls: Type | None = None
    production_timer: float | None = dataclass_field(init=False, default=None)
    all_buildings: InitVar = None
    font: pg.Font = None
    producer: Any = None
    producible_items: list = dataclass_field(default_factory=list)
    
    # Initializes UI elements and sets default producer to HQ
    def __post_init__(self, all_buildings):
        self.placing_cls = None
        self.surface = pg.Surface((self.WIDTH, SCREEN_HEIGHT - CONSOLE_HEIGHT))
        self.producer = self.hq
        self._create_top_buttons()
        self.unit_button_labels = {
            Tank: "Tank",
            Infantry: "Infantry",
            Grenadier: "Grenadier",
            MachineGunVehicle: "MG Vehicle",
            Harvester: "Harvester",
            Barracks: "Barracks",
            WarFactory: "War Factory",
            PowerPlant: "Power Plant",
            Turret: "Turret",
        }
        self.update_producer(self.hq)
    
    # Creates top action buttons (Repair, Sell, Map)
    def _create_top_buttons(self):
        self.top_rects.clear()
        start_x = self.MARGIN_X
        for i, label in enumerate(['Repair', 'Sell', 'Map']):
            x = start_x + i * (self.TOP_BUTTON_WIDTH + self.TOP_BUTTON_SPACING)
            rect = pg.Rect(x, self.TOP_BUTTONS_POS_Y, self.TOP_BUTTON_WIDTH, self.TOP_BUTTON_HEIGHT)
            self.top_rects[label] = rect
    
    # Updates producible items based on selected building
    def update_producer(self, selected_building):
        self.producer = selected_building if isinstance(selected_building, (Barracks, WarFactory)) else self.hq
        self.producible_items = []
        if isinstance(selected_building, Barracks):
            self.producible_items = [Infantry, Grenadier]
        elif isinstance(selected_building, WarFactory):
            self.producible_items = [Tank, MachineGunVehicle, Harvester]
        else:
            self.producible_items = [Barracks, WarFactory, PowerPlant, Turret]
        self.item_rects = {}
        y = self.PROD_ITEMS_START_Y
        for i, cls in enumerate(self.producible_items):
            rect = pg.Rect(self.MARGIN_X, y + i * self.ITEM_HEIGHT, self._BUTTON_WIDTH, self.ITEM_BUTTON_HEIGHT)
            self.item_rects[cls] = rect
    
    # Draws the entire sidebar UI
    def draw(self, surface_: pg.Surface, own_buildings, all_buildings):
        self.surface.fill(self.FILL_COLOR)
        pg.draw.rect(self.surface, self.LINE_COLOR, self.surface.get_rect(), width=2)
        
        self.surface.blit(
            self.font.render(f"Iron: {self.hq.iron}", True, pg.Color("white")),
            (self.MARGIN_X, self.IRON_POS_Y),
        )
        
        power_color = pg.Color("green") if self.hq.has_enough_power else pg.Color("red")
        self.surface.blit(
            self.font.render(
                f"Power: {self.hq.power_output}/{self.hq.power_usage}",
                True,
                power_color,
            ),
            (self.MARGIN_X, self.POWER_POS_Y),
        )
        
        # Top action buttons
        for label, rect in self.top_rects.items():
            color = self.INACTIVE_TAB_COLOR
            pg.draw.rect(self.surface, color, rect, border_radius=self.BUTTON_RADIUS)
            pg.draw.rect(self.surface, self.LINE_COLOR, rect, 1)
            text_surf = self.font.render(label, True, pg.Color("white"))
            text_rect = text_surf.get_rect(center=rect.center)
            self.surface.blit(text_surf, text_rect)
        
        # Production items
        for cls, rect in self.item_rects.items():
            can_produce = self.hq.iron >= cls.COST
            color = self.ACTION_ALLOWED_COLOR if can_produce else self.ACTION_BLOCKED_COLOR
            pg.draw.rect(self.surface, color, rect, border_radius=self.BUTTON_RADIUS)
            label = self.unit_button_labels[cls]
            label_surf = self.font.render(label, True, pg.Color("white"))
            label_rect = label_surf.get_rect(x=rect.x + 5, y=rect.y + 5)
            self.surface.blit(label_surf, label_rect)
            cost_surf = self.font.render(f"({cls.COST})", True, pg.Color("white"))
            cost_rect = cost_surf.get_rect(x=rect.x + 5, y=rect.y + 25)
            self.surface.blit(cost_surf, cost_rect)
        
        # Production queue
        if hasattr(self.producer, 'production_queue') and self.producer.production_queue:
            queue_y = self.PRODUCTION_QUEUE_POS_Y
            self.surface.blit(
                self.font.render("Queue:", True, pg.Color("white")),
                (self.MARGIN_X, queue_y),
            )
            queue_y += 20
            for i, item in enumerate(self.producer.production_queue):
                cls = item['cls']
                repeat_text = " [R]" if item['repeat'] else ""
                text = f"{self.unit_button_labels.get(cls, cls.__name__)}{repeat_text}"
                self.surface.blit(
                    self.font.render(text, True, pg.Color("white")),
                    (self.MARGIN_X + 10, queue_y),
                )
                # Repeat button
                repeat_rect = pg.Rect(self.MARGIN_X + 150, queue_y, 20, 20)
                repeat_color = self.ACTION_ALLOWED_COLOR if item['repeat'] else self.INACTIVE_TAB_COLOR
                pg.draw.rect(self.surface, repeat_color, repeat_rect, border_radius=2)
                if item['repeat']:
                    self.surface.blit(
                        self.font.render("R", True, pg.Color("white")),
                        (repeat_rect.x + 6, repeat_rect.y + 3),
                    )
                # Progress bar for current
                if i == 0 and self.producer.production_timer is not None:
                    progress = 1 - (self.producer.production_timer / 60.0)
                    bar_width = 100 * progress
                    pg.draw.rect(self.surface, self.ACTION_ALLOWED_COLOR, (self.MARGIN_X + 10, queue_y + 20, bar_width, 5))
                    pg.draw.rect(self.surface, self.LINE_COLOR, (self.MARGIN_X + 10, queue_y + 20, 100, 5), 1)
                queue_y += 25
        
        surface_.blit(self.surface, (SCREEN_WIDTH - self.WIDTH, 0))
    
    # Handles clicks in the UI
    def handle_click(self, screen_pos, own_buildings):
        local_pos = (screen_pos[0] - (SCREEN_WIDTH - self.WIDTH), screen_pos[1])
        
        # Top buttons
        for label, rect in self.top_rects.items():
            if rect.collidepoint(local_pos):
                if label == 'Repair':
                    if self.producer != self.hq:
                        missing = self.producer.max_health - self.producer.health
                        if missing > 0:
                            cost = missing * 1  # 1 iron per HP
                            if self.hq.iron >= cost:
                                self.hq.iron -= cost
                                self.producer.health = self.producer.max_health
                elif label == 'Sell':
                    if self.producer != self.hq:
                        return ('sell', self.producer)
                elif label == 'Map':
                    pass  # TODO: Implement map toggle or action
                return True
        
        # Production items
        for cls, rect in self.item_rects.items():
            if rect.collidepoint(local_pos):
                cost = cls.COST
                if self.hq.iron >= cost:
                    if issubclass(cls, Unit):
                        if len(self.producer.production_queue) < self.MAX_PRODUCTION_QUEUE_LENGTH:
                            self.producer.production_queue.append({'cls': cls, 'repeat': False})
                            self.hq.iron -= cost
                    else:
                        self.placing_cls = cls
                    return True
                return False  # Can't afford, but clicked
        return False

# ==================== MINI MAP ====================
# Draws the minimap in the bottom-right corner
def draw_mini_map(screen: pg.Surface, camera: Camera, fog_of_war: FogOfWar, base_map: pg.Surface, buildings, all_units):
    mini_map_rect = pg.Rect(SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT, MINI_MAP_WIDTH, MINI_MAP_HEIGHT)
    mini_map = pg.Surface((MINI_MAP_WIDTH, MINI_MAP_HEIGHT))
    
    scale_x = MINI_MAP_WIDTH / camera.map_width
    scale_y = MINI_MAP_HEIGHT / camera.map_height
    
    scaled_base = pg.transform.scale(base_map, (MINI_MAP_WIDTH, MINI_MAP_HEIGHT))
    mini_map.blit(scaled_base, (0, 0))
    
    # Fog on minimap
    num_tiles_x = len(fog_of_war.explored)
    num_tiles_y = len(fog_of_war.explored[0])
    for ty in range(num_tiles_y):
        for tx in range(num_tiles_x):
            tile_x = int(tx * TILE_SIZE * scale_x)
            tile_y = int(ty * TILE_SIZE * scale_y)
            tile_w = math.ceil(TILE_SIZE * scale_x)
            tile_h = math.ceil(TILE_SIZE * scale_y)
            if not fog_of_war.explored[tx][ty]:
                pg.draw.rect(mini_map, (0, 0, 0), (tile_x, tile_y, tile_w, tile_h))
            elif not fog_of_war.visible[tx][ty]:
                semi = pg.Surface((tile_w, tile_h))
                semi.fill((0, 0, 0))
                semi.set_alpha(128)
                mini_map.blit(semi, (tile_x, tile_y))
    
    # Draw buildings on minimap
    for building in buildings:
        if building.health > 0 and building.is_seen and fog_of_war.is_explored(building.position):
            color = GDI_COLOR if building.team == Team.GDI else NOD_COLOR
            x = int(building.position.x * scale_x)
            y = int(building.position.y * scale_y)
            pg.draw.rect(mini_map, color, (x - 2, y - 2, 5, 5))
    
    # Draw units on minimap
    for unit in all_units:
        if unit.health > 0 and fog_of_war.is_visible(unit.position):
            color = GDI_COLOR if unit.team == Team.GDI else NOD_COLOR
            x = int(unit.position.x * scale_x)
            y = int(unit.position.y * scale_y)
            pg.draw.circle(mini_map, color, (x, y), 2)
    
    # Draw camera viewport outline
    cam_rect = pg.Rect(
        camera.rect.x * scale_x,
        camera.rect.y * scale_y,
        camera.rect.width * scale_x,
        camera.rect.height * scale_y
    )
    pg.draw.rect(mini_map, (255, 255, 255), cam_rect, 1)
    
    screen.blit(mini_map, (SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT))
    return mini_map_rect

# ==================== GAME FUNCTIONS ====================
# Handles unit collision resolution (simple repulsion)
def handle_collisions(all_units: list):
    for unit in all_units:
        for other in all_units:
            if unit != other and unit.rect.colliderect(other.rect):
                dist = unit.distance_to(other.position)
                if dist > 0:
                    push = 0.3 if isinstance(unit, Harvester) and isinstance(other, Harvester) else 0.5
                    dx, dy = unit.displacement_to(other.position)
                    unit.rect.x += push * dx / dist
                    unit.rect.y += push * dy / dist

# Handles unit attacks (melee and ranged)
def handle_attacks(team_units, all_units, all_buildings, projectiles, particles):
    for unit in team_units:
        if isinstance(unit, (Tank, Infantry, Grenadier, MachineGunVehicle)) and unit.cooldown_timer == 0:
            closest_target, min_dist = None, float("inf")
            
            # Prioritize targeted unit
            if unit.target_unit and unit.target_unit.health > 0:
                dist = unit.distance_to(unit.target_unit.position)
                if dist <= unit.ATTACK_RANGE:
                    closest_target, min_dist = unit.target_unit, dist
            
            # Find closest enemy otherwise
            if not closest_target:
                for obj in list(all_units) + list(all_buildings):
                    if obj.team != unit.team and obj.health > 0:
                        dist = unit.distance_to(obj.position)
                        if dist <= unit.ATTACK_RANGE and dist < min_dist:
                            closest_target, min_dist = obj, dist
            
            if closest_target:
                unit.target_unit = closest_target
                unit.target = closest_target.position
                if isinstance(unit, (Tank, MachineGunVehicle)):
                    d = unit.displacement_to(closest_target.position)
                    unit.angle = math.degrees(math.atan2(d[1], d[0]))
                    projectiles.add(Projectile(unit.position, closest_target, unit.ATTACK_DAMAGE, unit.team))
                    for _ in range(5):
                        particles.add(
                            Particle(
                                (unit.position.x, unit.position.y),
                                random.uniform(-1.5, 1.5),
                                random.uniform(-1.5, 1.5),
                                6,
                                pg.Color(100, 100, 100),
                                20,
                            )
                        )
                else:
                    closest_target.health -= unit.ATTACK_DAMAGE
                    for _ in range(3):
                        particles.add(
                            Particle(
                                unit.position,
                                random.uniform(-1, 1),
                                random.uniform(-1, 1),
                                4,
                                pg.Color(255, 200, 100),
                                10,
                            )
                        )
                    if closest_target.health <= 0:
                        closest_target.kill()
                        unit.target = unit.target_unit = None
                
                unit.cooldown_timer = unit.ATTACK_COOLDOWN_PERIOD

# Handles projectile collisions and damage
def handle_projectiles(projectiles, all_units, all_buildings, particles):
    for projectile in list(projectiles):
        enemy_units = [u for u in all_units if u.team != projectile.team and u.health > 0]
        enemy_buildings = [b for b in all_buildings if b.team != projectile.team and b.health > 0]
        
        for e in enemy_units + enemy_buildings:
            if projectile.rect.colliderect(e.rect):
                e.health -= projectile.damage
                for _ in range(5):
                    particles.add(
                        Particle(
                            (projectile.position.x, projectile.position.y),
                            random.uniform(-2, 2),
                            random.uniform(-2, 2),
                            6,
                            pg.Color(255, 200, 100),
                            15,
                        )
                    )
                projectile.kill()
                if e.health <= 0:
                    e.kill()
                break

# ==================== MENU ====================
# Base button class for menus
class MenuButton:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
    
    # Updates hover state
    def update(self, mouse_pos):
        self.current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
    
    # Draws button with text
    def draw(self, surface, font):
        pg.draw.rect(surface, self.current_color, self.rect, border_radius=10)
        text_surf = font.render(self.text, True, pg.Color("white"))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    # Checks if clicked
    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

# ==================== MENU SCREEN ====================
# Main menu screen
class MainMenu:
    def __init__(self, font_large, font_medium):
        self.font_large = font_large
        self.font_medium = font_medium
        self.skirmish_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 60, 200, 60, "Single Player", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
        self.quit_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 40, 200, 60, "Quit", pg.Color(150, 50, 50), pg.Color(200, 100, 100))
    
    # Handles menu events
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.skirmish_btn.is_clicked(event.pos):
                return "skirmish_setup"
            if self.quit_btn.is_clicked(event.pos):
                return "quit"
        return None
    
    # Updates button hovers
    def update(self, mouse_pos):
        self.skirmish_btn.update(mouse_pos)
        self.quit_btn.update(mouse_pos)
    
    # Draws menu
    def draw(self, surface):
        surface.fill(pg.Color(40, 40, 40))
        title = self.font_large.render("RTS GAME", True, pg.Color(0, 255, 200))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        surface.blit(title, title_rect)
        self.skirmish_btn.draw(surface, self.font_medium)
        self.quit_btn.draw(surface, self.font_medium)

# Skirmish setup menu
class SkirmishSetup:
    def __init__(self, font_large, font_medium):
        self.font_large = font_large
        self.font_medium = font_medium
        self.game_mode = None
        self.size_choice = None
        self.map_choice = None
        
        self.mode_1v1 = MenuButton(SCREEN_WIDTH // 2 - 60, 150, 120, 50, "1v1", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        
        self.size_small = MenuButton(200, 220, 120, 50, "Small", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_medium = MenuButton(350, 220, 120, 50, "Medium", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_large = MenuButton(500, 220, 120, 50, "Large", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_huge = MenuButton(650, 220, 120, 50, "Huge", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_ginormous = MenuButton(800, 220, 120, 50, "Ginormous", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        
        self.map_buttons = {}
        map_list = list(MAPS.keys())
        for i, map_name in enumerate(map_list):
            x = 100 + (i % 2) * 300
            y = 350 + (i // 2) * 80
            self.map_buttons[map_name] = MenuButton(x, y, 200, 60, map_name, pg.Color(100, 100, 100), pg.Color(150, 150, 150))
        
        self.start_btn = MenuButton(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 100, 160, 50, "Start Game", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
        self.back_btn = MenuButton(20, SCREEN_HEIGHT - 70, 120, 50, "Back", pg.Color(150, 100, 50), pg.Color(200, 150, 100))
    
    # Handles setup events
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.mode_1v1.is_clicked(event.pos):
                self.game_mode = "1v1"
            
            if self.size_small.is_clicked(event.pos):
                self.size_choice = "small"
            elif self.size_medium.is_clicked(event.pos):
                self.size_choice = "medium"
            elif self.size_large.is_clicked(event.pos):
                self.size_choice = "large"
            elif self.size_huge.is_clicked(event.pos):
                self.size_choice = "huge"
            elif self.size_ginormous.is_clicked(event.pos):
                self.size_choice = "ginormous"
            
            for map_name, btn in self.map_buttons.items():
                if btn.is_clicked(event.pos):
                    self.map_choice = map_name
            
            if self.start_btn.is_clicked(event.pos) and self.game_mode and self.size_choice and self.map_choice:
                return ("start_game", self.game_mode, self.size_choice, self.map_choice)
            
            if self.back_btn.is_clicked(event.pos):
                return "menu"
        
        return None
    
    # Updates button hovers
    def update(self, mouse_pos):
        self.mode_1v1.update(mouse_pos)
        self.size_small.update(mouse_pos)
        self.size_medium.update(mouse_pos)
        self.size_large.update(mouse_pos)
        self.size_huge.update(mouse_pos)
        self.size_ginormous.update(mouse_pos)
        for btn in self.map_buttons.values():
            btn.update(mouse_pos)
        self.start_btn.update(mouse_pos)
        self.back_btn.update(mouse_pos)
    
    # Draws setup screen
    def draw(self, surface):
        surface.fill(pg.Color(40, 40, 40))
        
        title = self.font_large.render("Skirmish Setup", True, pg.Color(0, 255, 200))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 40))
        surface.blit(title, title_rect)
        
        mode_label = self.font_medium.render("Select Game Mode:", True, pg.Color(200, 200, 200))
        surface.blit(mode_label, (50, 120))
        self.mode_1v1.draw(surface, self.font_medium)
        
        if self.game_mode:
            mode_text = self.font_medium.render(f"Selected: {self.game_mode}", True, pg.Color(100, 255, 100))
            surface.blit(mode_text, (SCREEN_WIDTH - 250, 160))
        
        size_label = self.font_medium.render("Select Size:", True, pg.Color(200, 200, 200))
        surface.blit(size_label, (50, 190))
        self.size_small.draw(surface, self.font_medium)
        self.size_medium.draw(surface, self.font_medium)
        self.size_large.draw(surface, self.font_medium)
        self.size_huge.draw(surface, self.font_medium)
        self.size_ginormous.draw(surface, self.font_medium)
        
        if self.size_choice:
            size_text = self.font_medium.render(f"Selected: {self.size_choice}", True, pg.Color(100, 255, 100))
            surface.blit(size_text, (SCREEN_WIDTH - 250, 230))
        
        map_label = self.font_medium.render("Select Map:", True, pg.Color(200, 200, 200))
        surface.blit(map_label, (50, 320))
        for btn in self.map_buttons.values():
            btn.draw(surface, self.font_medium)
        
        if self.map_choice:
            map_text = self.font_medium.render(f"Selected: {self.map_choice}", True, pg.Color(100, 255, 100))
            surface.blit(map_text, (SCREEN_WIDTH - 250, 390))
        
        self.start_btn.draw(surface, self.font_medium)
        self.back_btn.draw(surface, self.font_medium)

# Victory/Defeat screen
class VictoryScreen:
    def __init__(self, font_large, font_medium, is_victory):
        self.font_large = font_large
        self.font_medium = font_medium
        self.is_victory = is_victory
        self.continue_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 80, 200, 60, "Continue", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
    
    # Handles end-game events
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.continue_btn.is_clicked(event.pos):
                return "menu"
        return None
    
    # Updates button hover
    def update(self, mouse_pos):
        self.continue_btn.update(mouse_pos)
    
    # Draws victory/defeat message
    def draw(self, surface):
        surface.fill(pg.Color(20, 20, 20))
        
        if self.is_victory:
            title = self.font_large.render("VICTORY!", True, pg.Color(0, 255, 100))
            message = self.font_medium.render("All enemies defeated!", True, pg.Color(100, 255, 150))
        else:
            title = self.font_large.render("DEFEAT!", True, pg.Color(255, 50, 50))
            message = self.font_medium.render("Your HQ was destroyed!", True, pg.Color(255, 100, 100))
        
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        msg_rect = message.get_rect(center=(SCREEN_WIDTH // 2, 250))
        
        surface.blit(title, title_rect)
        surface.blit(message, msg_rect)
        self.continue_btn.draw(surface, self.font_medium)

# ==================== GAME MANAGER ====================
# Manages game states and loops
class GameManager:
    def __init__(self, screen, clock, font_large, font_medium):
        self.screen = screen
        self.clock = clock
        self.font_large = font_large
        self.font_medium = font_medium
        self.state = GameState.MENU
        
        self.main_menu = MainMenu(font_large, font_medium)
        self.skirmish_setup = SkirmishSetup(font_large, font_medium)
        self.victory_screen = None
        
        self.game_data = None
        self.running = True
    
    # Initializes game world with selected map and mode
    def initialize_game(self, game_mode, size_name, map_name):
        """Initialize a new game with selected settings"""
        map_data = MAPS[map_name]
        base_width = map_data["width"]
        base_height = map_data["height"]
        color = map_data["color"]
        
        size_scales = {
            "small": 0.75,
            "medium": 1.0,
            "large": 1.5,
            "huge": 2.0,
            "ginormous": 3.0,
        }
        scale = size_scales[size_name]
        map_width = int(base_width * scale)
        map_height = int(base_height * scale)
        
        player_units = pg.sprite.Group()
        ai_units = pg.sprite.Group()
        global_units = pg.sprite.Group()
        iron_fields = pg.sprite.Group()
        global_buildings = pg.sprite.Group()
        projectiles = pg.sprite.Group()
        particles = pg.sprite.Group()
        selected_units = pg.sprite.Group()
        
        gdi_pos = (300, 300)
        gdi_hq = Headquarters(position=gdi_pos, team=Team.GDI, font=self.font_medium)
        gdi_hq.rally_point = Vector2(gdi_pos[0] + 100, gdi_pos[1])
        
        nod_pos = (map_width - 300, map_height - 300)
        nod_hq = Headquarters(position=nod_pos, team=Team.NOD, font=self.font_medium)
        nod_hq.iron = 1500
        nod_hq.rally_point = Vector2(nod_pos[0] - 100, nod_pos[1])
        
        # Generate procedural base map with terrain variation
        base_map = pg.Surface((map_width, map_height))
        for x in range(0, map_width, TILE_SIZE):
            for y in range(0, map_height, TILE_SIZE):
                tile_color = tuple(c + random.randint(-20, 20) for c in color)
                pg.draw.rect(base_map, tile_color, (x, y, TILE_SIZE, TILE_SIZE))
                if random.random() < 0.05:
                    dark_color = tuple(max(0, c - 40) for c in tile_color)
                    pg.draw.circle(base_map, dark_color, (x + TILE_SIZE // 2, y + TILE_SIZE // 2), TILE_SIZE // 4)
        
        # Starting player units
        player_units.add(Infantry((350, 300), Team.GDI))
        player_units.add(Infantry((370, 300), Team.GDI))
        player_units.add(Infantry((390, 300), Team.GDI))
        player_units.add(Harvester((400, 400), Team.GDI, gdi_hq))
        
        # Starting AI units
        ai_units.add(Infantry((map_width - 350, map_height - 300), Team.NOD))
        ai_units.add(Infantry((map_width - 330, map_height - 300), Team.NOD))
        ai_units.add(Infantry((map_width - 310, map_height - 300), Team.NOD))
        ai_units.add(Harvester((map_width - 400, map_height - 400), Team.NOD, nod_hq))
        
        global_units.add(player_units, ai_units)
        global_buildings.add(gdi_hq, nod_hq)
        
        # Evenly spaced iron fields
        margin = 100
        ref_width = 2560.0
        scale_factor = map_width / ref_width
        cols = max(4, int(8 * scale_factor))
        rows = max(3, int(5 * scale_factor))
        spacing_x = (map_width - 2 * margin) / cols
        spacing_y = (map_height - 2 * margin) / rows
        for i in range(rows):
            for j in range(cols):
                center_x = margin + (j + 0.5) * spacing_x
                center_y = margin + (i + 0.5) * spacing_y
                field_x = center_x - 15
                field_y = center_y - 15
                iron_fields.add(IronField(field_x, field_y, self.font_medium))
        
        camera = Camera()
        camera.map_width = map_width
        camera.map_height = map_height
        
        interface_rect = pg.Rect(SCREEN_WIDTH - 200, 0, 200, SCREEN_HEIGHT - CONSOLE_HEIGHT)
        
        self.game_data = {
            "player_units": player_units,
            "ai_units": ai_units,
            "global_units": global_units,
            "iron_fields": iron_fields,
            "global_buildings": global_buildings,
            "projectiles": projectiles,
            "particles": particles,
            "selected_units": selected_units,
            "gdi_hq": gdi_hq,
            "nod_hq": nod_hq,
            "interface": ProductionInterface(hq=gdi_hq, all_buildings=global_buildings, font=self.font_medium),
            "console": GameConsole(),
            "fog_of_war": FogOfWar(map_width, map_height),
            "camera": camera,
            "base_map": base_map,
            "map_width": map_width,
            "map_height": map_height,
            "game_mode": game_mode,
            "selected_building": None,
            "selecting": False,
            "select_start": None,
            "select_rect": None,
            "ai": AI(nod_hq, GameConsole()),
            "font": self.font_medium,
            "interface_rect": interface_rect,
        }
    
    # Main game loop for playing state
    def run_game(self):
        """Main game loop"""
        g = self.game_data
        
        while self.running and self.state == GameState.PLAYING:
            keys = pg.key.get_pressed()
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.MOUSEWHEEL:
                    mouse_pos = pg.mouse.get_pos()
                    game_rect = pg.Rect(0, 0, g["camera"].width, g["camera"].height)
                    if game_rect.collidepoint(mouse_pos):
                        world_mouse = g["camera"].screen_to_world(mouse_pos)
                        g["camera"].update_zoom(event.y, world_mouse)
                elif event.type == pg.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    mini_x = SCREEN_WIDTH - MINI_MAP_WIDTH
                    mini_y = SCREEN_HEIGHT - MINI_MAP_HEIGHT
                    mini_rect = pg.Rect(mini_x, mini_y, MINI_MAP_WIDTH, MINI_MAP_HEIGHT)
                    in_minimap = mini_rect.collidepoint(mouse_pos)
                    
                    if in_minimap and event.button == 1:
                        local_x = mouse_pos[0] - mini_x
                        local_y = mouse_pos[1] - mini_y
                        scale_x = g["map_width"] / MINI_MAP_WIDTH
                        scale_y = g["map_height"] / MINI_MAP_HEIGHT
                        world_x = local_x * scale_x
                        world_y = local_y * scale_y
                        g["camera"].rect.centerx = world_x
                        g["camera"].rect.centery = world_y
                        g["camera"].clamp()
                        # Deselect units and building
                        for unit in g["player_units"]:
                            unit.selected = False
                        g["selected_units"].empty()
                        if g["selected_building"]:
                            g["selected_building"].selected = False
                        g["selected_building"] = None
                        g["selecting"] = False
                        g["interface"].update_producer(g["gdi_hq"])
                        continue
                    elif in_minimap and event.button == 3:
                        local_x = mouse_pos[0] - mini_x
                        local_y = mouse_pos[1] - mini_y
                        scale_x = g["map_width"] / MINI_MAP_WIDTH
                        scale_y = g["map_height"] / MINI_MAP_HEIGHT
                        world_pos = (local_x * scale_x, local_y * scale_y)
                        if g["interface"].placing_cls is not None:
                            g["interface"].placing_cls = None  # Cancel placement
                        elif g["selected_building"] and hasattr(g["selected_building"], 'rally_point'):
                            g["selected_building"].rally_point = Vector2(world_pos)
                        elif g["selected_units"]:
                            formation_positions = calculate_formation_positions(
                                center=world_pos, target=world_pos, num_units=len(g["selected_units"])
                            )
                            for unit, pos in zip(g["selected_units"], formation_positions):
                                unit.target = pos
                                unit.formation_target = pos
                        continue
                    
                    world_pos = g["camera"].screen_to_world(mouse_pos)
                    target_x, target_y = mouse_pos
                    
                    if event.button == 1:
                        own_buildings = [b for b in g["global_buildings"] if b.team == Team.GDI]
                        result = g["interface"].handle_click(mouse_pos, own_buildings)
                        if result:
                            if isinstance(result, tuple) and result[0] == 'sell':
                                building_to_sell = result[1]
                                if building_to_sell in g["global_buildings"]:
                                    g["global_buildings"].remove(building_to_sell)
                                    g["gdi_hq"].iron += building_to_sell.COST // 2
                                    if g["selected_building"] == building_to_sell:
                                        g["selected_building"] = None
                                        g["interface"].update_producer(g["gdi_hq"])
                            continue
                        
                        # Placement mode
                        if g["interface"].placing_cls is not None and not g["interface_rect"].collidepoint(mouse_pos):
                            snapped = snap_to_grid(world_pos)
                            buildings_list = list(g["global_buildings"])
                            if is_valid_building_position(
                                snapped, Team.GDI, g["interface"].placing_cls, buildings_list,
                                g["map_width"], g["map_height"]
                            ):
                                building = g["interface"].placing_cls(snapped, Team.GDI, g["font"])
                                if isinstance(building, (WarFactory, Barracks)):
                                    building.parent_hq = g["gdi_hq"]
                                g["global_buildings"].add(building)
                                g["gdi_hq"].iron -= g["interface"].placing_cls.COST
                            # If invalid, stay in placing mode
                            continue
                        
                        clicked_building = next(
                            (b for b in g["global_buildings"] if b.team == Team.GDI and g["camera"].get_screen_rect(b.rect).collidepoint(target_x, target_y)),
                            None,
                        )
                        if clicked_building:
                            if g["selected_building"] and g["selected_building"] != clicked_building:
                                g["selected_building"].selected = False
                            clicked_building.selected = True
                            g["selected_building"] = clicked_building
                            # Deselect units
                            for unit in g["player_units"]:
                                unit.selected = False
                            g["selected_units"].empty()
                            g["interface"].update_producer(clicked_building)
                        else:
                            if g["selected_building"]:
                                g["selected_building"].selected = False
                            g["selected_building"] = None
                            g["interface"].update_producer(g["gdi_hq"])
                            g["selecting"] = True
                            g["select_start"] = mouse_pos
                            g["select_rect"] = pg.Rect(target_x, target_y, 0, 0)
                    
                    elif event.button == 3:
                        if g["interface"].placing_cls is not None:
                            g["interface"].placing_cls = None  # Cancel placement
                        elif g["selected_building"] and hasattr(g["selected_building"], 'rally_point'):
                            g["selected_building"].rally_point = Vector2(world_pos)
                        elif g["selected_units"]:
                            formation_positions = calculate_formation_positions(
                                center=world_pos, target=world_pos, num_units=len(g["selected_units"])
                            )
                            for unit, pos in zip(g["selected_units"], formation_positions):
                                unit.target = pos
                                unit.formation_target = pos
                
                elif event.type == pg.MOUSEMOTION and g["selecting"]:
                    current_pos = event.pos
                    if g["select_start"]:
                        g["select_rect"] = pg.Rect(
                            min(g["select_start"][0], current_pos[0]),
                            min(g["select_start"][1], current_pos[1]),
                            abs(current_pos[0] - g["select_start"][0]),
                            abs(current_pos[1] - g["select_start"][1]),
                        )
                
                elif event.type == pg.MOUSEBUTTONUP and event.button == 1 and g["selecting"]:
                    g["selecting"] = False
                    for unit in g["player_units"]:
                        unit.selected = False
                    g["selected_units"].empty()
                    
                    if g["selected_building"]:
                        g["selected_building"].selected = False
                    g["selected_building"] = None
                    g["interface"].update_producer(g["gdi_hq"])
                    
                    if g["select_start"]:
                        world_start = g["camera"].screen_to_world(g["select_start"])
                        world_end = g["camera"].screen_to_world(event.pos)
                        world_rect = pg.Rect(
                            min(world_start[0], world_end[0]),
                            min(world_start[1], world_end[1]),
                            abs(world_end[0] - world_start[0]),
                            abs(world_end[1] - world_start[1]),
                        )
                        for unit in g["player_units"]:
                            if world_rect.colliderect(unit.rect):
                                unit.selected = True
                                g["selected_units"].add(unit)
                
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        if g["interface"].placing_cls is not None:
                            g["interface"].placing_cls = None
                        else:
                            self.state = GameState.MENU
                            return
            
            g["camera"].update(g["selected_units"].sprites(), pg.mouse.get_pos(), g["interface_rect"], keys)
            
            # Update units
            for unit in g["global_units"]:
                if isinstance(unit, Harvester):
                    if unit.team == Team.GDI:
                        unit.update(enemy_units=g["ai_units"], iron_fields=g["iron_fields"])
                    else:
                        unit.update(enemy_units=g["player_units"], iron_fields=g["iron_fields"])
                else:
                    unit.update()
            
            g["iron_fields"].update()
            
            # Update buildings
            for building in g["global_buildings"]:
                if building.health <= 0:
                    continue
                if isinstance(building, Headquarters):
                    if building.team == Team.GDI:
                        building.update(
                            particles=g["particles"],
                            friendly_units=g["player_units"],
                            friendly_buildings=[b for b in g["global_buildings"] if b.team == Team.GDI],
                            all_units=g["global_units"],
                            global_buildings=g["global_buildings"],
                        )
                    else:
                        building.update(
                            particles=g["particles"],
                            friendly_units=g["ai_units"],
                            friendly_buildings=[b for b in g["global_buildings"] if b.team != Team.GDI],
                            all_units=g["global_units"],
                            global_buildings=g["global_buildings"],
                        )
                elif isinstance(building, (Barracks, WarFactory)):
                    if building.team == Team.GDI:
                        building.update(
                            particles=g["particles"],
                            friendly_units=g["player_units"],
                            all_units=g["global_units"],
                            global_buildings=g["global_buildings"],
                        )
                    else:
                        building.update(
                            particles=g["particles"],
                            friendly_units=g["ai_units"],
                            all_units=g["global_units"],
                            global_buildings=g["global_buildings"],
                        )
                elif isinstance(building, Turret):
                    if building.team == Team.GDI:
                        building.update(
                            particles=g["particles"],
                            projectiles=g["projectiles"],
                            enemy_units=g["ai_units"],
                        )
                    else:
                        building.update(
                            particles=g["particles"],
                            projectiles=g["projectiles"],
                            enemy_units=g["player_units"],
                        )
                else:
                    building.update(particles=g["particles"])
            
            g["projectiles"].update(g["particles"])
            g["particles"].update()
            handle_collisions(list(g["global_units"]))
            handle_attacks(g["player_units"], g["global_units"], g["global_buildings"], g["projectiles"], g["particles"])
            handle_attacks(g["ai_units"], g["global_units"], g["global_buildings"], g["projectiles"], g["particles"])
            handle_projectiles(g["projectiles"], g["global_units"], g["global_buildings"], g["particles"])
            
            # AI update
            g["ai"].update(
                g["ai_units"], [b for b in g["global_buildings"] if b.team == Team.NOD],
                g["player_units"], [b for b in g["global_buildings"] if b.team == Team.GDI],
                g["iron_fields"], g["global_buildings"]
            )
            
            g["fog_of_war"].update_visibility(g["player_units"], g["global_buildings"], Team.GDI)
            
            for unit in g["global_units"]:
                unit.under_attack = False
            
            # Check win/lose conditions
            gdi_has_units = any(u.health > 0 for u in g["player_units"]) or g["gdi_hq"].health > 0
            nod_has_units = any(u.health > 0 for u in g["ai_units"]) or g["nod_hq"].health > 0
            
            if not gdi_has_units:
                self.state = GameState.DEFEAT
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, False)
            elif not nod_has_units:
                self.state = GameState.VICTORY
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, True)
            
            # Rendering
            self.screen.fill(pg.Color("black"))
            
            # Draw base map
            view_rect = g["camera"].rect.clip(pg.Rect(0, 0, g["base_map"].get_width(), g["base_map"].get_height()))
            game_w = int(g["camera"].width)
            game_h = int(g["camera"].height)
            if view_rect.width > 0 and view_rect.height > 0:
                visible_map = g["base_map"].subsurface(view_rect)
                scaled_map = pg.transform.smoothscale(visible_map, (game_w, game_h))
                self.screen.blit(scaled_map, (0, 0))
            
            # Draw iron fields
            for field in g["iron_fields"]:
                if field.resources > 0 and g["fog_of_war"].is_explored(field.position):
                    field.draw(surface=self.screen, camera=g["camera"])
            
            # Draw buildings
            for building in g["global_buildings"]:
                if building.health > 0 and (building.team == Team.GDI or (building.is_seen and g["fog_of_war"].is_explored(building.position)) or g["fog_of_war"].is_visible(building.position)):
                    building.draw(self.screen, g["camera"])
                    building.draw_health_bar(self.screen, g["camera"])
            
            # Draw fog
            g["fog_of_war"].draw(self.screen, g["camera"])
            
            # Ghost building
            if g["interface"].placing_cls is not None:
                mouse_pos = pg.mouse.get_pos()
                ghost_pos = g["camera"].screen_to_world(mouse_pos)
                snapped = snap_to_grid(ghost_pos)
                buildings_list = list(g["global_buildings"])
                valid = is_valid_building_position(
                    snapped, Team.GDI, g["interface"].placing_cls, buildings_list,
                    g["map_width"], g["map_height"]
                )
                temp_rect = pg.Rect(snapped, g["interface"].placing_cls.SIZE)
                screen_ghost = g["camera"].get_screen_rect(temp_rect)
                color = ProductionInterface.PLACEMENT_VALID_COLOR if valid else ProductionInterface.PLACEMENT_INVALID_COLOR
                line_width = int(2 * g["camera"].zoom)
                pg.draw.rect(self.screen, color, screen_ghost, line_width)
            
            # Draw units
            for unit in g["global_units"]:
                if unit.health > 0 and (unit.team == Team.GDI or g["fog_of_war"].is_visible(unit.position)):
                    unit.draw(self.screen, g["camera"])
                    unit.draw_health_bar(self.screen, g["camera"])
            
            # Draw projectiles
            for projectile in g["projectiles"]:
                projectile.draw(self.screen, g["camera"])
            
            # Draw particles
            for particle in g["particles"]:
                particle.draw(self.screen, g["camera"])
            
            g["interface"].draw(self.screen, [b for b in g["global_buildings"] if b.team == Team.GDI], g["global_buildings"])
            
            if g["selecting"] and g["select_rect"]:
                pg.draw.rect(self.screen, (255, 255, 255), g["select_rect"], 2)
            
            mini_rect = draw_mini_map(self.screen, g["camera"], g["fog_of_war"], g["base_map"], g["global_buildings"], g["global_units"])
            
            pg.display.flip()
            self.clock.tick(60)
    
    # Main application loop handling all states
    def run(self):
        """Main application loop"""
        while self.running:
            if self.state == GameState.MENU:
                self.main_menu.update(pg.mouse.get_pos())
                self.main_menu.draw(self.screen)
                
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        self.running = False
                    result = self.main_menu.handle_event(event)
                    if result == "skirmish_setup":
                        self.state = GameState.SKIRMISH_SETUP
                    elif result == "quit":
                        self.running = False
                
                pg.display.flip()
                self.clock.tick(60)
            
            elif self.state == GameState.SKIRMISH_SETUP:
                self.skirmish_setup.update(pg.mouse.get_pos())
                self.skirmish_setup.draw(self.screen)
                
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        self.running = False
                    result = self.skirmish_setup.handle_event(event)
                    if result == "menu":
                        self.state = GameState.MENU
                        self.skirmish_setup = SkirmishSetup(self.font_large, self.font_medium)
                    elif result and result[0] == "start_game":
                        _, game_mode, size_choice, map_choice = result
                        self.initialize_game(game_mode, size_choice, map_choice)
                        self.state = GameState.PLAYING
                
                pg.display.flip()
                self.clock.tick(60)
            
            elif self.state == GameState.PLAYING:
                self.run_game()
            
            elif self.state in (GameState.VICTORY, GameState.DEFEAT):
                self.victory_screen.update(pg.mouse.get_pos())
                self.victory_screen.draw(self.screen)
                
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        self.running = False
                    result = self.victory_screen.handle_event(event)
                    if result == "menu":
                        self.state = GameState.MENU
                        self.skirmish_setup = SkirmishSetup(self.font_large, self.font_medium)
                
                pg.display.flip()
                self.clock.tick(60)
        
        pg.quit()

# ==================== MAIN ====================
if __name__ == "__main__":
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("RTS Game - Command & Conquer Style")
    clock = pg.time.Clock()
    
    font_large = pg.font.SysFont(None, 72)
    font_medium = pg.font.SysFont(None, 28)
    
    manager = GameManager(screen, clock, font_large, font_medium)
    manager.run()
