from __future__ import annotations

import math
import random
from dataclasses import InitVar, dataclass, field as dataclass_field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Type, Set
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import deque
import types

import pygame as pg
from pygame.math import Vector2

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
CONSOLE_HEIGHT = 100
MAP_WIDTH = 10000
MAP_HEIGHT = 10000
TILE_SIZE = 100
MINI_MAP_WIDTH = 200
MINI_MAP_HEIGHT = 150
PAN_EDGE = 0
PAN_SPEED = 10
FITNESS_PANEL_HEIGHT = 280

class Team(Enum):
    RED = 1
    BLUE = 2
    GREEN = 3
    CYAN = 4
    MAGENTA = 5
    ORANGE = 6
    YELLOW = 7
    GREY = 8

RED_COLOR = pg.Color(255, 0, 0)
BLUE_COLOR = pg.Color(0, 0, 255)
GREEN_COLOR = pg.Color(0, 255, 0)
CYAN_COLOR = pg.Color(0, 255, 255)
MAGENTA_COLOR = pg.Color(255, 0, 255)
ORANGE_COLOR = pg.Color(255, 165, 0)
YELLOW_COLOR = pg.Color(255, 255, 0)
GREY_COLOR = pg.Color(128, 128, 128)

team_to_color = {
    Team.RED: RED_COLOR,
    Team.BLUE: BLUE_COLOR,
    Team.GREEN: GREEN_COLOR,
    Team.CYAN: CYAN_COLOR,
    Team.MAGENTA: MAGENTA_COLOR,
    Team.ORANGE: ORANGE_COLOR,
    Team.YELLOW: YELLOW_COLOR,
    Team.GREY: GREY_COLOR,
}

team_to_name = {
    Team.RED: "Red",
    Team.BLUE: "Blue",
    Team.GREEN: "Green",
    Team.CYAN: "Cyan",
    Team.MAGENTA: "Magenta",
    Team.ORANGE: "Orange",
    Team.YELLOW: "Yellow",
    Team.GREY: "Grey",
}

class GameState(Enum):
    MENU = 1
    SKIRMISH_SETUP = 2
    PLAYING = 3
    VICTORY = 4
    DEFEAT = 5

MAPS = {
    "Desert": {"width": 2560, "height": 2560, "color": (139, 120, 80)},
    "Forest": {"width": 3200, "height": 3200, "color": (34, 100, 34)},
    "Ice": {"width": 2560, "height": 2560, "color": (180, 200, 220)},
    "Urban": {"width": 5000, "height": 5000, "color": (100, 100, 100)},
}

UNIT_CLASSES = {
    "Infantry": {
        "cost": 100,
        "hp": 45,
        "speed": 0.7,
        "attack_range": 80,
        "sight_range": 120,
        "weapons": [
            {"name": "Rifle", "damage": 10, "fire_rate": 0.5, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 1, "cooldown": 25}
        ],
        "size": (16, 16),
        "air": False,
        "is_building": False,
        "height": 8
    },
    "Tank": {
        "cost": 700,
        "hp": 300,
        "speed": 0.8,
        "attack_range": 80,
        "sight_range": 200,
        "weapons": [
            {"name": "Cannon", "damage": 80, "fire_rate": 0.6, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 2, "cooldown": 50}
        ],
        "size": (30, 20),
        "air": False,
        "is_building": False,
        "height": 5
    },
    "Grenadier": {
        "cost": 300,
        "hp": 45,
        "speed": 0.7,
        "attack_range": 100,
        "sight_range": 120,
        "weapons": [
            {"name": "Grenade", "damage": 20, "fire_rate": 0.5, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 1, "cooldown": 20}
        ],
        "size": (16, 16),
        "air": False,
        "is_building": False,
        "height": 8
    },
    "RocketSoldier": {
        "cost": 200,
        "hp": 45,
        "speed": 0.7,
        "attack_range": 140,
        "sight_range": 130,
        "weapons": [
            {"name": "Rocket", "damage": 120, "fire_rate": 0.3, "projectile_speed": 8, "projectile_length": 2, "projectile_width": 2, "cooldown": 80}
        ],
        "size": (16, 16),
        "air": False,
        "is_building": False,
        "height": 8
    },
    "MachineGunVehicle": {
        "cost": 500,
        "hp": 200,
        "speed": 0.9,
        "attack_range": 120,
        "sight_range": 200,
        "weapons": [
            {"name": "MG", "damage": 25, "fire_rate": 0.5, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 1, "cooldown": 50}
        ],
        "size": (35, 25),
        "air": False,
        "is_building": False,
        "height": 6
    },
    "RocketArtillery": {
        "cost": 800,
        "hp": 150,
        "speed": 0.7,
        "attack_range": 150,
        "sight_range": 175,
        "weapons": [
            {"name": "Rockets", "damage": 200, "fire_rate": 0.1, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 1, "cooldown": 150}
        ],
        "size": (40, 25),
        "air": False,
        "is_building": False,
        "height": 8
    },
    "AttackHelicopter": {
        "cost": 1000,
        "hp": 200,
        "speed": 0.9,
        "attack_range": 100,
        "sight_range": 175,
        "weapons": [
            {"name": "Missiles", "damage": 30, "fire_rate": 0.5, "projectile_speed": 10, "projectile_length": 1, "projectile_width": 1, "cooldown": 40}
        ],
        "size": (25, 15),
        "air": True,
        "fly_height": 10,
        "is_building": False,
        "height": 4
    },
    "Headquarters": {
        "cost": 1000,
        "starting_credits": 7500,
        "hp": 500,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "size": (40, 40),
        "air": False,
        "is_building": True,
        "height": 35
    },
    "Barracks": {
        "cost": 300,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "producible": ["Infantry", "Grenadier", "RocketSoldier"],
        "production_time": 60,
        "size": (32, 32),
        "air": False,
        "is_building": True,
        "height": 25
    },
    "WarFactory": {
        "cost": 500,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "producible": ["Tank", "MachineGunVehicle", "RocketArtillery"],
        "production_time": 60,
        "size": (40, 32),
        "air": False,
        "is_building": True,
        "height": 30
    },
    "Hangar": {
        "cost": 600,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "producible": ["AttackHelicopter"],
        "production_time": 90,
        "size": (36, 28),
        "air": False,
        "is_building": True,
        "height": 20
    },
    "PowerPlant": {
        "cost": 300,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "size": (32, 32),
        "air": False,
        "is_building": True,
        "height": 15
    },
    "OilDerrick": {
        "cost": 300,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 100,
        "income_interval": 300,
        "size": (24, 32),
        "air": False,
        "is_building": True,
        "height": 60
    },
    "Refinery": {
        "cost": 2000,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 150,
        "income_interval": 300,
        "size": (48, 32),
        "air": False,
        "is_building": True,
        "height": 25
    },
    "ShaleFracker": {
        "cost": 800,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 165,
        "income_interval": 300,
        "size": (28, 28),
        "air": False,
        "is_building": True,
        "height": 20
    },
    "BlackMarket": {
        "cost": 1500,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 150,
        "income_interval": 300,
        "size": (36, 24),
        "air": False,
        "is_building": True,
        "height": 15
    },
    "Turret": {
        "cost": 400,
        "hp": 200,
        "speed": 0,
        "attack_range": 300,
        "sight_range": 200,
        "weapons": [
            {"name": "TurretGun", "damage": 20, "fire_rate": 0.67, "projectile_speed": 5, "projectile_length": 10, "projectile_width": 4, "cooldown": 30}
        ],
        "size": (24, 24),
        "air": False,
        "is_building": True,
        "height": 25
    }
}

PROJECTILE_LIFETIME = 1.0
PARTICLES_PER_EXPLOSION = 3
PLASMA_BURN_PARTICLES = 3
PLASMA_BURN_DURATION = 1.0

class TerrainFeature:
    def __init__(self, position: tuple, feature_type: str):
        self.position = Vector2(position)
        self.feature_type = feature_type
        self.rect = pg.Rect(position[0] - 20, position[1] - 20, 40, 40)
        if self.feature_type == "pebbles":
            self.num_pebbles = random.randint(2, 6)
            base_offsets = [(-6, -2), (-3, 0), (0, -4), (4, 1), (2, 5), (-1, 3), (5, -1)]
            self.selected_offsets = random.sample(base_offsets, min(self.num_pebbles, len(base_offsets)))
            self.pebbles = []
            for dx, dy in self.selected_offsets:
                pebble_size = random.uniform(4, 8)
                aspect_ratio = random.uniform(0.5, 1.5)
                pebble_width = pebble_size
                pebble_height = pebble_size * aspect_ratio
                outer_color = (random.randint(140, 160), random.randint(140, 160), random.randint(140, 160))
                inner_color = (random.randint(100, 130), random.randint(100, 130), random.randint(100, 130))
                self.pebbles.append({
                    'dx': dx, 'dy': dy, 'width': pebble_width, 'height': pebble_height,
                    'outer': outer_color, 'inner': inner_color
                })

    def draw(self, surface: pg.Surface, camera: Camera):
        screen_pos = camera.world_to_iso(self.position, camera.zoom)
        zoom = camera.zoom
        if self.feature_type == "tree":
            trunk_width = int(8 * zoom)
            trunk_height = int(20 * zoom)
            trunk_rect = pg.Rect(screen_pos[0] - trunk_width // 2, screen_pos[1], trunk_width, trunk_height)
            pg.draw.rect(surface, (139, 69, 19), trunk_rect)
            foliage_radius = int(25 * zoom)
            pg.draw.circle(surface, (0, 128, 0), (int(screen_pos[0]), int(screen_pos[1] - 10 * zoom)), foliage_radius)
            pg.draw.circle(surface, (34, 139, 34), (int(screen_pos[0] - 10 * zoom), int(screen_pos[1] - 5 * zoom)), int(15 * zoom))
            pg.draw.circle(surface, (34, 139, 34), (int(screen_pos[0] + 10 * zoom), int(screen_pos[1] - 5 * zoom)), int(15 * zoom))
        elif self.feature_type == "boulder":
            boulder_radius = int(25 * zoom)
            pg.draw.ellipse(surface, (105, 105, 105), (screen_pos[0] - boulder_radius, screen_pos[1] - boulder_radius // 2, boulder_radius * 2, boulder_radius))
            pg.draw.ellipse(surface, (70, 70, 70), (screen_pos[0] - boulder_radius // 2, screen_pos[1] - boulder_radius // 2, boulder_radius, boulder_radius // 2))
        elif self.feature_type == "rock":
            rock_width = int(15 * zoom)
            rock_height = int(10 * zoom)
            pg.draw.ellipse(surface, (128, 128, 128), (screen_pos[0] - rock_width // 2, screen_pos[1] - rock_height // 2, rock_width, rock_height))
            pg.draw.ellipse(surface, (90, 90, 90), (screen_pos[0] - rock_width // 4, screen_pos[1] - rock_height // 4, rock_width // 2, rock_height // 2))
        elif self.feature_type == "bush":
            bush_radius = int(18 * zoom)
            pg.draw.circle(surface, (0, 100, 0), (int(screen_pos[0]), int(screen_pos[1])), bush_radius)
            pg.draw.circle(surface, (34, 139, 34), (int(screen_pos[0] - 8 * zoom), int(screen_pos[1] - 5 * zoom)), int(12 * zoom))
            pg.draw.circle(surface, (0, 120, 0), (int(screen_pos[0] + 6 * zoom), int(screen_pos[1] + 3 * zoom)), int(10 * zoom))
            pg.draw.line(surface, (139, 69, 19), screen_pos, (screen_pos[0], screen_pos[1] + 5 * zoom), int(2 * zoom))
        elif self.feature_type == "twigs":
            twig_length = int(12 * zoom)
            twig_width = int(2 * zoom)
            pg.draw.line(surface, (101, 67, 33), screen_pos, (screen_pos[0] + twig_length, screen_pos[1]), twig_width)
            pg.draw.line(surface, (101, 67, 33), (screen_pos[0] + twig_length // 2, screen_pos[1]), 
                         (screen_pos[0] + twig_length // 2 - 5 * zoom, screen_pos[1] - 8 * zoom), twig_width)
            pg.draw.line(surface, (101, 67, 33), (screen_pos[0] + twig_length // 2, screen_pos[1]), 
                         (screen_pos[0] + twig_length // 2 + 6 * zoom, screen_pos[1] + 4 * zoom), twig_width)
            pg.draw.circle(surface, (0, 100, 0), (int(screen_pos[0] + 3 * zoom), int(screen_pos[1] - 2 * zoom)), int(3 * zoom))
        elif self.feature_type == "pebbles":
            for pebble in self.pebbles:
                px = screen_pos[0] + pebble['dx'] * zoom
                py = screen_pos[1] + pebble['dy'] * zoom
                pebble_width = int(pebble['width'] * zoom)
                pebble_height = int(pebble['height'] * zoom)
                pg.draw.ellipse(surface, pebble['outer'], (px - pebble_width//2, py - pebble_height//2, pebble_width, pebble_height))
                inner_width = pebble_width // 2
                inner_height = pebble_height // 2
                pg.draw.ellipse(surface, pebble['inner'], (px - inner_width//2, py - inner_height//2, inner_width, inner_height))

def generate_terrain_features(map_name: str, map_width: int, map_height: int) -> List[TerrainFeature]:
    features = []
    num_tiles = (map_width // TILE_SIZE) * (map_height // TILE_SIZE)
    
    tree_density = 0.02 if map_name == "Forest" else 0.005
    boulder_density = 0.01
    rock_density = 0.03
    bush_density = 0.025 if "Forest" in map_name else 0.01
    twig_density = 0.015 if "Forest" in map_name or "Woodland" in map_name else 0.005
    pebble_density = 0.04 if "Desert" in map_name or "Riverbed" in map_name else 0.02
    
    num_trees = int(num_tiles * tree_density)
    num_boulders = int(num_tiles * boulder_density)
    num_rocks = int(num_tiles * rock_density)
    num_bushes = int(num_tiles * bush_density)
    num_twigs = int(num_tiles * twig_density)
    num_pebbles = int(num_tiles * pebble_density)
    
    def add_feature(ftype, count, cluster=False):
        for _ in range(count):
            attempts = 0
            while attempts < 10:
                x = random.randint(0, map_width)
                y = random.randint(0, map_height)
                new_rect = pg.Rect(x - 20, y - 20, 40, 40)
                if all(not new_rect.colliderect(f.rect.inflate(10, 10) if f.feature_type == ftype else f.rect) for f in features):
                    features.append(TerrainFeature((x, y), ftype))
                    break
                attempts += 1
    
    add_feature("tree", num_trees)
    add_feature("boulder", num_boulders)
    add_feature("rock", num_rocks)
    add_feature("bush", num_bushes)
    add_feature("twigs", num_twigs, cluster=True)  
    add_feature("pebbles", num_pebbles, cluster=True)  
    
    return features

def snap_to_grid(pos: tuple[float, float], grid_size: int = TILE_SIZE) -> tuple[float, float]:
    return (round(pos[0] / grid_size) * grid_size, round(pos[1] / grid_size) * grid_size)

def is_valid_building_position(
    position: tuple[float, float],
    team: Team,
    new_building_cls: Type,
    buildings: list,
    map_width: int = MAP_WIDTH,
    map_height: int = MAP_HEIGHT,
    building_range: int = 200,
    margin: int = 60,
) -> bool:
    width, height = UNIT_CLASSES[new_building_cls.__name__]["size"]
    half_w_n, half_h_n = width / 2, height / 2
    temp_rect = pg.Rect(position[0] - half_w_n, position[1] - half_h_n, width, height)
    if not (0 <= temp_rect.left and temp_rect.right <= map_width and
            0 <= temp_rect.top and temp_rect.bottom <= map_height):
        return False
    
    proposed_center = position
    
    has_nearby_friendly = False
    for building in buildings:
        if building.team == team and building.health > 0:
            e_size = UNIT_CLASSES[building.unit_type]["size"]
            half_w_e, half_h_e = e_size[0] / 2, e_size[1] / 2
            min_dist = max(half_w_n + half_w_e, half_h_n + half_h_e) + margin
            dist = math.hypot(proposed_center[0] - building.position.x, proposed_center[1] - building.position.y)
            if dist < min_dist:
                return False
            if dist <= building_range:
                has_nearby_friendly = True
        
        if building.health > 0 and building.rect.colliderect(temp_rect):
            return False
    
    return has_nearby_friendly or new_building_cls.__name__ == "Headquarters"

def find_free_spawn_position(building_pos: tuple, target_pos: tuple, global_buildings, global_units, unit_size=(40, 40), map_width=MAP_WIDTH, map_height=MAP_HEIGHT):
    for _ in range(20):
        offset_x = random.uniform(-60, 60)
        offset_y = random.uniform(-60, 60)
        pos_x = max(0, min(target_pos[0] + offset_x, map_width))
        pos_y = max(0, min(target_pos[1] + offset_y, map_height))
        unit_rect = pg.Rect(pos_x - unit_size[0]/2, pos_y - unit_size[1]/2, unit_size[0], unit_size[1])
        overlaps_building = any(b.rect.colliderect(unit_rect) for b in global_buildings if b.health > 0)
        overlaps_unit = any(u.rect.colliderect(unit_rect) for u in global_units if u.health > 0 and not u.air)
        if not overlaps_building and not overlaps_unit:
            return (pos_x, pos_y)
    return (max(0, min(target_pos[0], map_width)), max(0, min(target_pos[1], map_height)))

def calculate_formation_positions(
    center: tuple[float, float],
    target: tuple[float, float],
    num_units: int,
) -> list[tuple[float, float]]:
    if num_units == 0:
        return []
    positions = []
    spacing = 30
    cols = max(1, int(math.sqrt(num_units)))
    for i in range(num_units):
        row, col = i // cols, i % cols
        x = center[0] + (col - cols / 2) * spacing
        y = center[1] + (row - num_units / cols / 2) * spacing
        positions.append((x, y))
    return positions

def get_starting_positions(map_width: int, map_height: int, num_players: int):
    edge_dist = 250
    half_w = map_width / 2
    half_h = map_height / 2

    base_positions = [
        (half_w, edge_dist),  
        (map_width - edge_dist, edge_dist),  
        (map_width - edge_dist, half_h),  
        (map_width - edge_dist, map_height - edge_dist),  
        (half_w, map_height - edge_dist),  
        (edge_dist, map_height - edge_dist),  
        (edge_dist, half_h),  
        (edge_dist, edge_dist),  
    ]

    step = max(1, 8 // num_players)
    selected_positions = base_positions[::step][:num_players]

    while len(selected_positions) < num_players:
        selected_positions.append(base_positions[len(selected_positions) % 8])

    return selected_positions

class SpatialHash:
    def __init__(self, cell_size: int = 200):
        self.cell_size = cell_size
        self.grid: Dict[tuple[int, int], list] = {}

    def get_key(self, pos: Vector2) -> tuple[int, int]:
        return (int(pos.x // self.cell_size), int(pos.y // self.cell_size))

    def add(self, obj):
        key = self.get_key(obj.position)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(obj)

    def query(self, pos: Vector2, radius: float) -> list:
        cx = int(pos.x // self.cell_size)
        cy = int(pos.y // self.cell_size)
        keys = set()
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                keys.add((cx + dx, cy + dy))
        nearby = []
        for k in keys:
            if k in self.grid:
                for o in self.grid[k]:
                    if o.distance_to(pos) <= radius:
                        nearby.append(o)
        return nearby

def absolute_world_to_iso(world_pos: tuple, zoom: float) -> tuple[float, float]:
    dx, dy = world_pos
    iso_x = (dx - dy) * (zoom / 2)
    iso_y = (dx + dy) * (zoom / 2)
    return (iso_x, iso_y)

class Camera:
    def __init__(self):
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.width = SCREEN_WIDTH - 200
        self.height = SCREEN_HEIGHT
        self.zoom = 1.0
        self.rect = pg.Rect(0, 0, self.width, self.height)
        self.target_rect = pg.Rect(self.rect)
        self.update_view_size()
    
    def update_view_size(self):
        view_w = self.width / self.zoom
        view_h = self.height / self.zoom
        self.rect.size = (view_w, view_h)
        self.target_rect.size = (view_w, view_h)
    
    def snap_to_point(self, world_point: tuple[float, float]):
        sc_x, sc_y = self.width / 2, self.height / 2
        dx_sc = (sc_x + 2 * sc_y) / self.zoom
        dy_sc = (2 * sc_y - sc_x) / self.zoom
        self.rect.x = world_point[0] - dx_sc
        self.rect.y = world_point[1] - dy_sc
    
    def update_zoom(self, delta, mouse_screen_pos=None):
        if mouse_screen_pos is None:
            mouse_screen_pos = (self.width / 2, self.height / 2)
        sx, sy = mouse_screen_pos
        old_dx = (sx + 2 * sy) / self.zoom
        old_dy = (2 * sy - sx) / self.zoom
        old_world_x = self.rect.x + old_dx
        old_world_y = self.rect.y + old_dy
        old_zoom = self.zoom
        if delta > 0:
            self.zoom = min(self.zoom * 1.1, 3.0)
        else:
            self.zoom = max(self.zoom / 1.1, 0.5)
        self.update_view_size()
        new_dx = (sx + 2 * sy) / self.zoom
        new_dy = (2 * sy - sx) / self.zoom
        self.rect.x = old_world_x - new_dx
        self.rect.y = old_world_y - new_dy
        self.target_rect.x = self.rect.x
        self.target_rect.y = self.rect.y
        self.clamp()
    
    def world_to_iso(self, world_pos: tuple, zoom: float) -> tuple[float, float]:
        dx = world_pos[0] - self.rect.x
        dy = world_pos[1] - self.rect.y
        iso_x = (dx - dy) * (zoom / 2)
        iso_y = (dx + dy) * (zoom / 4)
        return (iso_x, iso_y)
    
    def world_to_iso_3d(self, world_x: float, world_y: float, world_z: float, zoom: float) -> tuple[float, float]:
        dx = world_x - self.rect.x
        dy = world_y - self.rect.y
        iso_x = (dx - dy) * (zoom / 2)
        iso_y = (dx + dy) * (zoom / 4) - world_z * (zoom / 2)
        return (iso_x, iso_y)
    
    def screen_to_world(self, screen_pos: tuple) -> tuple[float, float]:
        iso_x, iso_y = screen_pos
        dx = (iso_x + 2 * iso_y) / self.zoom
        dy = (2 * iso_y - iso_x) / self.zoom
        return (
            self.rect.x + dx,
            self.rect.y + dy
        )
    
    def get_screen_rect(self, world_rect: pg.Rect) -> pg.Rect:
        corners = [
            (world_rect.left, world_rect.top),
            (world_rect.right, world_rect.top),
            (world_rect.right, world_rect.bottom),
            (world_rect.left, world_rect.bottom),
        ]
        iso_corners = [self.world_to_iso(corner, self.zoom) for corner in corners]
        xs = [p[0] for p in iso_corners]
        ys = [p[1] for p in iso_corners]
        return pg.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def get_render_bounds(self, tile_size: int = TILE_SIZE) -> tuple[float, float, float, float]:
        screen_corners = [(0, 0), (self.width, 0), (self.width, self.height), (0, self.height)]
        world_corners = [self.screen_to_world(c) for c in screen_corners]
        min_wx = min(p[0] for p in world_corners) - tile_size
        max_wx = max(p[0] for p in world_corners) + tile_size
        min_wy = min(p[1] for p in world_corners) - tile_size
        max_wy = max(p[1] for p in world_corners) + tile_size
        return min_wx, max_wx, min_wy, max_wy
    
    def update(self, selected_units: list, mouse_pos: tuple, interface_rect: pg.Rect, keys=None):
        if keys is None:
            keys = pg.key.get_pressed()
        
        pressed_pan = keys[pg.K_w] or keys[pg.K_a] or keys[pg.K_s] or keys[pg.K_d]
        
        mx, my = mouse_pos
        pan_delta = PAN_SPEED / self.zoom
        
        if mx < PAN_EDGE:
            self.rect.x += pan_delta
            self.rect.y -= pan_delta
        if mx > SCREEN_WIDTH - PAN_EDGE and self.rect.right < self.map_width:
            self.rect.x -= pan_delta
            self.rect.y += pan_delta
        if my < PAN_EDGE:
            self.rect.x += 2 * pan_delta
            self.rect.y += 2 * pan_delta
        if my > SCREEN_HEIGHT - PAN_EDGE and self.rect.bottom < self.map_height:
            self.rect.x -= 2 * pan_delta
            self.rect.y -= 2 * pan_delta
        
        if keys[pg.K_w]:
            self.rect.x += 2 * pan_delta
            self.rect.y += 2 * pan_delta
        if keys[pg.K_s]:
            self.rect.x -= 2 * pan_delta
            self.rect.y -= 2 * pan_delta
        if keys[pg.K_a]:
            self.rect.x += pan_delta
            self.rect.y -= pan_delta
        if keys[pg.K_d]:
            self.rect.x -= pan_delta
            self.rect.y += pan_delta
        
        if interface_rect.collidepoint(mx, my):
            self.clamp()
            return
        
        if selected_units and not pressed_pan:
            avg_x = sum(u.position[0] for u in selected_units) / len(selected_units)
            avg_y = sum(u.position[1] for u in selected_units) / len(selected_units)
            target_point = (avg_x, avg_y)
            self.target_rect.x = target_point[0] - (self.width / 0.1)
            self.target_rect.y = target_point[1] - (self.height / 0.1)
            self.snap_to_point(target_point)
            self.target_rect.x = self.rect.x
            self.target_rect.y = self.rect.y
            lerp_alpha = 0.1
            self.rect.x = self.rect.x + (self.target_rect.x - self.rect.x) * lerp_alpha
            self.rect.y = self.rect.y + (self.target_rect.y - self.rect.y) * lerp_alpha
        
        self.clamp()
    
    def clamp(self):
        self.rect.x = min(self.rect.x, self.map_width - self.rect.width)
        self.rect.y = min(self.rect.y, self.map_height - self.rect.height)
        self.target_rect.x = min(self.target_rect.x, self.map_width - self.target_rect.width)
        self.target_rect.y = min(self.target_rect.y, self.map_height - self.target_rect.height)

class FogOfWar:
    def __init__(self, map_width: int, map_height: int, tile_size: int = TILE_SIZE, spectator: bool = False):
        self.tile_size = tile_size
        num_tiles_x = map_width // tile_size
        num_tiles_y = map_height // tile_size
        self.explored = [[False] * num_tiles_y for _ in range(num_tiles_x)]
        self.visible = [[False] * num_tiles_y for _ in range(num_tiles_x)]
        if spectator:
            self.explored = [[True] * num_tiles_y for _ in range(num_tiles_x)]
            self.visible = [[True] * num_tiles_y for _ in range(num_tiles_x)]
    
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
    
    def update_visibility(self, ally_units, ally_buildings, global_buildings):
        if not ally_units and not ally_buildings:
            return
        num_tiles_x = len(self.visible)
        num_tiles_y = len(self.visible[0])
        self.visible = [[False] * num_tiles_y for _ in range(num_tiles_x)]
        for unit in ally_units:
            self.reveal(unit.position, unit.sight_range)
        for building in ally_buildings:
            if building.health > 0:
                self.reveal(building.position, building.sight_range)
        for building in global_buildings:
            if building.health > 0:
                tx, ty = int(building.position[0] // self.tile_size), int(building.position[1] // self.tile_size)
                if 0 <= tx < num_tiles_x and 0 <= ty < num_tiles_y:
                    building.is_seen = building.is_seen or self.visible[tx][ty]
    
    def is_visible(self, pos: tuple) -> bool:
        tx, ty = int(pos[0] // self.tile_size), int(pos[1] // self.tile_size)
        if 0 <= tx < len(self.visible) and 0 <= ty < len(self.visible[0]):
            return self.visible[tx][ty]
        return False
    
    def is_explored(self, pos: tuple) -> bool:
        tx, ty = int(pos[0] // self.tile_size), int(pos[1] // self.tile_size)
        if 0 <= tx < len(self.explored) and 0 <= ty < len(self.explored[0]):
            return self.explored[tx][ty]
        return False
    
    def draw(self, surface: pg.Surface, camera: Camera):
        min_wx, max_wx, min_wy, max_wy = camera.get_render_bounds(self.tile_size)
        start_tx = max(0, int(min_wx // self.tile_size))
        start_ty = max(0, int(min_wy // self.tile_size))
        end_tx = min(len(self.visible), int(max_wx // self.tile_size) + 2)
        end_ty = min(len(self.visible[0]), int(max_wy // self.tile_size) + 2)
        zoom = camera.zoom
        fog_overlay = pg.Surface((int(camera.width), int(camera.height)), pg.SRCALPHA)
        fog_overlay.fill((0, 0, 0, 0))
        for tx in range(start_tx, end_tx):
            wx = tx * self.tile_size
            for ty in range(start_ty, end_ty):
                wy = ty * self.tile_size
                if not self.visible[tx][ty]:
                    alpha = 255 if not self.explored[tx][ty] else 100
                    color = (0, 0, 0, alpha)
                    c1 = (wx, wy)
                    c2 = (wx + self.tile_size, wy)
                    c3 = (wx + self.tile_size, wy + self.tile_size)
                    c4 = (wx, wy + self.tile_size)
                    iso1 = camera.world_to_iso(c1, zoom)
                    iso2 = camera.world_to_iso(c2, zoom)
                    iso3 = camera.world_to_iso(c3, zoom)
                    iso4 = camera.world_to_iso(c4, zoom)
                    pg.draw.polygon(fog_overlay, color, [iso1, iso2, iso3, iso4])
        surface.blit(fog_overlay, (0, 0))

class Particle(pg.sprite.Sprite):
    def __init__(self, pos: tuple, vx: float, vy: float, size: int, color: pg.Color, lifetime: int):
        super().__init__()
        self.position = Vector2(pos)
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.lifetime = lifetime * 10
        self.age = 0
        self.image = pg.Surface((size, size), pg.SRCALPHA)
        pg.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect = self.image.get_rect(center=self.position)
    
    def update(self):
        self.position.x += self.vx
        self.position.y += self.vy
        self.age += 1
        alpha = int(255 * (1 - self.age / self.lifetime))
        self.image.set_alpha(alpha)
        self.rect.center = self.position
        if self.age >= self.lifetime:
            self.kill()
    
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_rect = camera.get_screen_rect(self.rect)
        if not screen_rect.colliderect((0, 0, camera.width, camera.height)):
            return
        screen_pos = camera.world_to_iso(self.position, camera.zoom)
        scaled_size = (int(self.image.get_width() * camera.zoom), int(self.image.get_height() * camera.zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)

class PlasmaBurnParticle(Particle):
    def __init__(self, pos: tuple, entity, color: pg.Color, lifetime: int):
        super().__init__(pos, 0, 0, 4, color, lifetime)
        self.entity = entity
        self.offset = Vector2(random.uniform(-20, 20), random.uniform(-10, 10))
        self.initial_lifetime = lifetime * 30

    def update(self):
        body_angle = getattr(self.entity, 'body_angle', 0)
        rotated_offset = self.offset.rotate_rad(-body_angle)
        self.position = self.entity.position + rotated_offset
        self.age += 1
        alpha = int(255 * (1 - self.age / self.initial_lifetime))
        self.image.set_alpha(alpha)
        self.rect.center = self.position
        if self.age >= self.initial_lifetime:
            self.kill()

def create_explosion(position: tuple, particles: pg.sprite.Group, team: Team, count: int = PARTICLES_PER_EXPLOSION):
    color = team_to_color[team]
    for _ in range(count):
        vx = random.uniform(-3, 3)
        vy = random.uniform(-3, 3)
        size = random.randint(2, 4)
        lifetime = random.randint(3, 7)
        particles.add(Particle(position, vx, vy, size, color, lifetime))

class Projectile(pg.sprite.Sprite):
    def __init__(self, pos: tuple, direction: Vector2, damage: int, team: Team, weapon: Dict[str, Any]):
        super().__init__()
        self.position = Vector2(pos)
        self.direction = direction.normalize() if direction.length() > 0 else Vector2(1, 0)
        self.damage = damage
        self.team = team
        self.speed = weapon["projectile_speed"]
        self.lifetime = PROJECTILE_LIFETIME * 30
        self.age = 0
        self.length = weapon["projectile_length"]
        self.width = weapon["projectile_width"]
        self.angle = math.atan2(self.direction.y, self.direction.x)
        self.image = pg.Surface((self.length, self.width), pg.SRCALPHA)
        color = team_to_color[team]
        for i in range(self.length):
            alpha = int(255 * (i / self.length))
            pg.draw.line(self.image, (color.r, color.g, color.b, alpha), (i, 0), (i, self.width), 1)
        self.rect = self.image.get_rect(center=self.position)
        self.trail = deque(maxlen=5)
    
    def update(self):
        self.trail.append(self.position.copy())
        self.position += self.direction * self.speed
        self.age += 1
        self.rect.center = self.position
        if self.age >= self.lifetime:
            self.kill()
    
    def draw(self, surface: pg.Surface, camera: Camera):
        screen_rect = camera.get_screen_rect(self.rect)
        if not screen_rect.colliderect((0, 0, camera.width, camera.height)):
            return
        screen_pos = camera.world_to_iso(self.position, camera.zoom)
        if len(self.trail) > 1:
            trail_positions = [camera.world_to_iso(pos, camera.zoom) for pos in self.trail]
            num_segments = len(trail_positions) - 1
            for i in range(num_segments):
                p1 = trail_positions[i]
                p2 = trail_positions[i + 1]
                age_factor = i / max(1, num_segments - 1)
                c = pg.Color(team_to_color[self.team])
                intensity = 0.3 + 0.7 * age_factor
                trail_color = (
                    int(c.r * intensity),
                    int(c.g * intensity),
                    int(c.b * intensity)
                )
                trail_width = max(1, int(self.width * camera.zoom * (0.2 + 0.3 * age_factor)))
                pg.draw.line(surface, trail_color, p1, p2, trail_width)
        scaled_length = int(self.length * camera.zoom)
        scaled_width = int(self.width * camera.zoom)
        if scaled_length > 0 and scaled_width > 0:
            scaled_image = pg.transform.smoothscale(self.image, (scaled_length, scaled_width))
            rotated_image = pg.transform.rotate(scaled_image, -math.degrees(self.angle))
            rot_rect = rotated_image.get_rect(center=screen_pos)
            surface.blit(rotated_image, rot_rect.topleft)

def check_collision(entity, projectile):
    proj_rect = pg.Rect(projectile.position.x - projectile.length/2, projectile.position.y - projectile.width/2, projectile.length, projectile.width)
    if hasattr(entity, 'radius'):
        dist = entity.distance_to(projectile.position)
        return dist < (entity.radius + max(projectile.length, projectile.width) / 2)
    else:
        return entity.rect.colliderect(proj_rect)

class GameObject(pg.sprite.Sprite, ABC):
    def __init__(self, position: tuple, team: Team):
        super().__init__()
        self.position = Vector2(position)
        self.team = team
        self.health = 100
        self.max_health = 100
        self.under_attack = False
        self.under_attack_timer = 0
        self.selected = False
        self.is_seen = False
        self.body_angle = 0
        self.plasma_burn_particles: list[PlasmaBurnParticle] = []
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.image = pg.Surface((32, 32))
        self.rect = self.image.get_rect(center=position)
    
    def distance_to(self, other_pos: tuple) -> float:
        return self.position.distance_to(other_pos)
    
    def displacement_to(self, other_pos: tuple) -> float:
        dx = other_pos[0] - self.position.x
        dy = other_pos[1] - self.position.y
        return (dx, dy)
    
    def draw_health_bar(self, screen, camera, mouse_pos: tuple = None):
        hovered = False
        if mouse_pos is not None:
            screen_rect = camera.get_screen_rect(self.rect)
            if screen_rect.collidepoint(mouse_pos):
                hovered = True
        
        show = True
        if self.is_building:
            if self.health >= self.max_health:
                show = False
        else:
            if not (self.under_attack or hovered):
                show = False
        
        if not show:
            return
        
        screen_pos = camera.world_to_iso(self.position, camera.zoom)
        health_ratio = self.health / self.max_health
        color = (0, 255, 0) if health_ratio > 0.5 else (255, 0, 0)
        bar_width = 25
        bar_height = 4
        bar_x = screen_pos[0] - bar_width / 2
        bar_y = screen_pos[1] - (self.rect.height / 2 * camera.zoom) - bar_height - 2
        pg.draw.rect(screen, (0, 0, 0), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
        pg.draw.rect(screen, color, (bar_x, bar_y, bar_width * health_ratio, bar_height))
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
    
    def take_damage(self, damage: int, particles: pg.sprite.Group):
        self.health -= damage
        self.under_attack = True
        self.under_attack_timer = 120
        if self.health < self.max_health * 0.7 and random.random() < 0.3:
            color = team_to_color[self.team]
            for _ in range(PLASMA_BURN_PARTICLES):
                self.plasma_burn_particles.append(PlasmaBurnParticle(self.position, self, color, PLASMA_BURN_DURATION))
        return self.health <= 0

    @abstractmethod
    def update(self): 
        pass

class Unit(GameObject):
    def __init__(self, position: tuple, team: Team, unit_type: str, hq=None):
        super().__init__(position, team)
        self.team_color = team_to_color[team]
        self.hq = hq
        stats = UNIT_CLASSES[unit_type]
        self.stats = stats.copy()
        self.unit_type = unit_type
        self.health = stats["hp"]
        self.max_health = stats["hp"]
        self.speed = stats["speed"]
        self.sight_range = stats["sight_range"]
        self.attack_range = stats["attack_range"]
        self.weapons = stats["weapons"]
        self.is_building = stats["is_building"]
        self.is_vehicle = unit_type in ["Tank", "MachineGunVehicle", "RocketArtillery", "AttackHelicopter"]
        self.current_weapon = 0
        self.attack_target = None
        self.last_shot_time = 0
        self.cooldown = stats["weapons"][0].get("cooldown", 0) if stats["weapons"] else 0
        self.move_target = None
        self.formation_target = None
        self.player_ordered = False
        self.random_offset_angle = random.uniform(-0.5, 0.5)
        self.turret_angle = 0
        self.body_angle = 0
        self.air = stats["air"]
        self.fly_height = stats.get("fly_height", 0)
        self.size = stats["size"]
        self.rect = pg.Rect(self.position.x - self.size[0]/2, self.position.y - self.size[1]/2, *self.size)
        if "income" in stats:
            self.income = stats["income"]
            self.collection_timer = 0
        if "producible" in stats:
            self.rally_point = Vector2(position[0] + 80, position[1])
            self.production_queue = []
            self.production_timer = None
        self._setup_drawing(unit_type)
    
    def draw_static(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = self.fly_height if self.air else 0
        top_z = base_z + h
        bfl = (pos.x - w / 2, pos.y - d / 2, base_z)
        bfr = (pos.x + w / 2, pos.y - d / 2, base_z)
        bbr = (pos.x + w / 2, pos.y + d / 2, base_z)
        bbl = (pos.x - w / 2, pos.y + d / 2, base_z)
        tfl = (pos.x - w / 2, pos.y - d / 2, top_z)
        tfr = (pos.x + w / 2, pos.y - d / 2, top_z)
        tbr = (pos.x + w / 2, pos.y + d / 2, top_z)
        tbl = (pos.x - w / 2, pos.y + d / 2, top_z)
        p_bfl = camera.world_to_iso_3d(*bfl, zoom)
        p_bfr = camera.world_to_iso_3d(*bfr, zoom)
        p_bbr = camera.world_to_iso_3d(*bbr, zoom)
        p_bbl = camera.world_to_iso_3d(*bbl, zoom)
        p_tfl = camera.world_to_iso_3d(*tfl, zoom)
        p_tfr = camera.world_to_iso_3d(*tfr, zoom)
        p_tbr = camera.world_to_iso_3d(*tbr, zoom)
        p_tbl = camera.world_to_iso_3d(*tbl, zoom)
        base_points = [p_bfl, p_bfr, p_bbr, p_bbl]
        front_points = [p_bfl, p_bfr, p_tfr, p_tfl]
        pg.draw.polygon(surface, self.team_color, front_points)
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        pg.draw.polygon(surface, side_color, [p_bfr, p_bbr, p_tbr, p_tfr])
        pg.draw.polygon(surface, side_color, [p_bbr, p_bbl, p_tbl, p_tbr])
        pg.draw.polygon(surface, side_color, [p_bbl, p_bfl, p_tfl, p_tbl])
        roof_color = pg.Color(128, 128, 128) if self.is_building else pg.Color(100, 100, 100)
        roof_points = [p_tfl, p_tfr, p_tbr, p_tbl]
        pg.draw.polygon(surface, roof_color, roof_points)
        outline_color = pg.Color(0, 0, 0)
        all_edges = [
            [p_bfl, p_bfr, p_bbr, p_bbl, p_bfl],
            [p_tfl, p_tfr, p_tbr, p_tbl, p_tfl],
            [p_bfl, p_tfl],
            [p_bfr, p_tfr],
            [p_bbr, p_tbr],
            [p_bbl, p_tbl],
        ]
        for edge in all_edges:
            if len(edge) > 2:
                for i in range(len(edge) - 1):
                    pg.draw.line(surface, outline_color, edge[i], edge[i + 1], int(2 * zoom))
            else:
                pg.draw.line(surface, outline_color, edge[0], edge[1], int(2 * zoom))
        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), base_points, int(2 * zoom))
        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)

    def draw_humanoid(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        pos = self.position
        angle = self.body_angle
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        team_color = self.team_color
        side_color = tuple(max(0, c - 50) for c in team_color)
        outline_color = pg.Color(0, 0, 0)

        torso_w = 1.2
        torso_d = 0.8
        torso_h = 3.0
        torso_base_z = 2.0
        self.draw_rotated_box(surface, camera, torso_w, torso_d, torso_h, angle, torso_base_z, team_color, side_color, team_color, outline_color, zoom, False)

        head_base_z = torso_base_z + torso_h
        head_offset_x = 0.0 * cos_a - 0.0 * sin_a
        head_offset_y = 0.0 * sin_a + 0.0 * cos_a
        head_pos_x = pos.x + head_offset_x
        head_pos_y = pos.y + head_offset_y
        head_r_world = 0.5
        head_center_3d = (head_pos_x, head_pos_y, head_base_z + head_r_world)
        head_screen = camera.world_to_iso_3d(*head_center_3d, zoom)
        scaled_head_r = int(head_r_world * zoom * 2)
        if scaled_head_r > 0:
            pg.draw.circle(surface, team_color, (int(head_screen[0]), int(head_screen[1])), scaled_head_r)
            pg.draw.circle(surface, outline_color, (int(head_screen[0]), int(head_screen[1])), scaled_head_r, 1)

        arm_length_world = 1.5
        arm_start_z = torso_base_z + 1.5

        left_offset_x = -0.6 * cos_a - 0.4 * sin_a
        left_offset_y = -0.6 * sin_a + 0.4 * cos_a
        arm_l_start_x = pos.x + left_offset_x
        arm_l_start_y = pos.y + left_offset_y
        arm_l_end_x = arm_l_start_x - arm_length_world * cos_a
        arm_l_end_y = arm_l_start_y - arm_length_world * sin_a
        p_l_start = camera.world_to_iso_3d(arm_l_start_x, arm_l_start_y, arm_start_z, zoom)
        p_l_end = camera.world_to_iso_3d(arm_l_end_x, arm_l_end_y, arm_start_z, zoom)
        pg.draw.line(surface, team_color, p_l_start, p_l_end, int(2 * zoom))
        pg.draw.line(surface, outline_color, p_l_start, p_l_end, 1)

        right_offset_x = 0.6 * cos_a - 0.4 * sin_a
        right_offset_y = 0.6 * sin_a + 0.4 * cos_a
        arm_r_start_x = pos.x + right_offset_x
        arm_r_start_y = pos.y + right_offset_y
        arm_r_end_x = arm_r_start_x + arm_length_world * cos_a
        arm_r_end_y = arm_r_start_y + arm_length_world * sin_a
        p_r_start = camera.world_to_iso_3d(arm_r_start_x, arm_r_start_y, arm_start_z, zoom)
        p_r_end = camera.world_to_iso_3d(arm_r_end_x, arm_r_end_y, arm_start_z, zoom)
        pg.draw.line(surface, team_color, p_r_start, p_r_end, int(2 * zoom))
        pg.draw.line(surface, outline_color, p_r_start, p_r_end, 1)

        leg_length_world = 2.0
        leg_start_z = 0.0

        leg_l_offset_x = -0.3 * cos_a - 0.2 * sin_a
        leg_l_offset_y = -0.3 * sin_a + 0.2 * cos_a
        leg_l_start_x = pos.x + leg_l_offset_x
        leg_l_start_y = pos.y + leg_l_offset_y
        leg_l_end_x = leg_l_start_x - leg_length_world * sin_a  
        leg_l_end_y = leg_l_start_y + leg_length_world * cos_a
        p_leg_l_start = camera.world_to_iso_3d(leg_l_start_x, leg_l_start_y, leg_start_z, zoom)
        p_leg_l_end = camera.world_to_iso_3d(leg_l_end_x, leg_l_end_y, leg_start_z, zoom)
        pg.draw.line(surface, team_color, p_leg_l_start, p_leg_l_end, int(3 * zoom))
        pg.draw.line(surface, outline_color, p_leg_l_start, p_leg_l_end, 1)

        leg_r_offset_x = 0.3 * cos_a - 0.2 * sin_a
        leg_r_offset_y = 0.3 * sin_a + 0.2 * cos_a
        leg_r_start_x = pos.x + leg_r_offset_x
        leg_r_start_y = pos.y + leg_r_offset_y
        leg_r_end_x = leg_r_start_x + leg_length_world * sin_a
        leg_r_end_y = leg_r_start_y - leg_length_world * cos_a
        p_leg_r_start = camera.world_to_iso_3d(leg_r_start_x, leg_r_start_y, leg_start_z, zoom)
        p_leg_r_end = camera.world_to_iso_3d(leg_r_end_x, leg_r_end_y, leg_start_z, zoom)
        pg.draw.line(surface, team_color, p_leg_r_start, p_leg_r_end, int(3 * zoom))
        pg.draw.line(surface, outline_color, p_leg_r_start, p_leg_r_end, 1)

        if self.selected:
            base_screen = camera.world_to_iso(pos, zoom)
            select_r = int(8 * zoom)
            pg.draw.circle(surface, (255, 255, 0), (int(base_screen[0]), int(base_screen[1])), select_r, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)

    def draw_rotated_box(self, surface: pg.Surface, camera: Camera, w: float, d: float, h: float, angle: float, base_z: float, team_color, side_color, roof_color, outline_color: pg.Color, zoom: float, is_turret: bool = False, p_bottom: list = None):
        cos = math.cos(angle)
        sin = math.sin(angle)

        def rotate_rel(points, cos, sin):
            return [(x * cos - y * sin, x * sin + y * cos, z) for x, y, z in points]

        rel_bottom = [
            (-w / 2, -d / 2, 0),
            (w / 2, -d / 2, 0),
            (w / 2, d / 2, 0),
            (-w / 2, d / 2, 0),
        ]
        rel_top = [(x, y, h) for x, y, _ in rel_bottom]
        rot_bottom = rotate_rel(rel_bottom, cos, sin)
        rot_top = rotate_rel(rel_top, cos, sin)
        full_bottom = [(self.position.x + rx, self.position.y + ry, base_z + rz) for rx, ry, rz in rot_bottom]
        full_top = [(self.position.x + rx, self.position.y + ry, base_z + rz) for rx, ry, rz in rot_top]
        p_bottom_local = [camera.world_to_iso_3d(*pt, zoom) for pt in full_bottom]
        p_top = [camera.world_to_iso_3d(*pt, zoom) for pt in full_top]
        if p_bottom is not None:
            p_bottom[:] = p_bottom_local

        wall_indices = [
            [0, 1, 1, 0],
            [1, 2, 2, 1],
            [2, 3, 3, 2],
            [3, 0, 0, 3],
        ]
        avg_ys = []
        for widx in wall_indices:
            ys = [
                full_bottom[widx[0]][1],
                full_bottom[widx[1]][1],
                full_top[widx[2]][1],
                full_top[widx[3]][1],
            ]
            avg_ys.append(sum(ys) / 4)
        front_idx = avg_ys.index(min(avg_ys))

        for i, widx in enumerate(wall_indices):
            points = [
                p_bottom_local[widx[0]],
                p_bottom_local[widx[1]],
                p_top[widx[2]],
                p_top[widx[3]],
            ]
            color = team_color if i == front_idx else side_color
            pg.draw.polygon(surface, color, points)

        pg.draw.polygon(surface, roof_color, p_top)

        all_points = p_bottom_local + p_top
        bottom_edge = [0, 1, 2, 3, 0]
        top_edge = [4, 5, 6, 7, 4]
        verticals = [[0, 4], [1, 5], [2, 6], [3, 7]]
        all_edges = [bottom_edge, top_edge] + verticals
        line_width = int(1 * zoom) if is_turret else int(2 * zoom)
        for edge in all_edges:
            if len(edge) > 2:
                for j in range(len(edge) - 1):
                    pg.draw.line(surface, outline_color, all_points[edge[j]], all_points[edge[j + 1]], line_width)
            else:
                pg.draw.line(surface, outline_color, all_points[edge[0]], all_points[edge[1]], line_width)

    def draw_vehicle(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = self.fly_height if self.air else 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        roof_color = pg.Color(100, 100, 100)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []
        self.draw_rotated_box(surface, camera, w, d, h, self.body_angle, base_z, self.team_color, side_color, roof_color, outline_color, zoom, False, p_bottom)
        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))
        if self.unit_type == "Tank":
            turret_w = w * 0.4
            turret_d = d * 0.4
            turret_h = h * 0.6
        elif self.unit_type == "MachineGunVehicle":
            turret_w = w * 0.25
            turret_d = d * 0.25
            turret_h = h * 0.4
        elif self.unit_type == "RocketArtillery":
            turret_w = w * 0.5
            turret_d = d * 0.3
            turret_h = h * 0.8
        elif self.unit_type == "AttackHelicopter":
            turret_w = w * 0.2
            turret_d = d * 0.2
            turret_h = h * 0.3
        else:
            turret_w = w * 0.3
            turret_d = d * 0.3
            turret_h = h * 0.5
        turret_base_z = base_z + h
        self.draw_rotated_box(surface, camera, turret_w, turret_d, turret_h, self.turret_angle, turret_base_z, self.team_color, side_color, roof_color, outline_color, zoom, True)
        if self.unit_type == "Tank":
            barrel_length = 20
            barrel_width = 3
            barrel_height = 4
            turret_center_x = pos.x
            turret_center_y = pos.y
            turret_center_z = turret_base_z + turret_h / 2
            cos_t = math.cos(self.turret_angle)
            sin_t = math.sin(self.turret_angle)
            front_offset = turret_d / 2
            barrel_start_x = turret_center_x + front_offset * cos_t
            barrel_start_y = turret_center_y + front_offset * sin_t
            barrel_start_z = turret_center_z
            barrel_end_x = barrel_start_x + barrel_length * cos_t
            barrel_end_y = barrel_start_y + barrel_length * sin_t
            barrel_end_z = barrel_start_z + barrel_height / 2
            perp_cos = -sin_t
            perp_sin = cos_t
            b1 = (barrel_start_x - (barrel_width / 2) * perp_cos, barrel_start_y - (barrel_width / 2) * perp_sin, barrel_start_z - barrel_height / 2)
            b2 = (barrel_start_x + (barrel_width / 2) * perp_cos, barrel_start_y + (barrel_width / 2) * perp_sin, barrel_start_z - barrel_height / 2)
            b3 = (barrel_end_x + (barrel_width / 2) * perp_cos, barrel_end_y + (barrel_width / 2) * perp_sin, barrel_end_z - barrel_height / 2)
            b4 = (barrel_end_x - (barrel_width / 2) * perp_cos, barrel_end_y - (barrel_width / 2) * perp_sin, barrel_end_z - barrel_height / 2)
            p_b1 = camera.world_to_iso_3d(*b1, zoom)
            p_b2 = camera.world_to_iso_3d(*b2, zoom)
            p_b3 = camera.world_to_iso_3d(*b3, zoom)
            p_b4 = camera.world_to_iso_3d(*b4, zoom)
            barrel_color = tuple(min(255, c + 20) for c in self.team_color)
            pg.draw.polygon(surface, barrel_color, [p_b1, p_b2, p_b3, p_b4])
            pg.draw.line(surface, outline_color, p_b1, p_b2, int(1 * zoom))
            pg.draw.line(surface, outline_color, p_b2, p_b3, int(1 * zoom))
            pg.draw.line(surface, outline_color, p_b3, p_b4, int(1 * zoom))
            pg.draw.line(surface, outline_color, p_b4, p_b1, int(1 * zoom))
        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)
    
    def _closest_point_on_rect(self, rect: pg.Rect, pos: tuple) -> tuple[float, float]:
        return (
            max(rect.left, min(pos[0], rect.right)),
            max(rect.top, min(pos[1], rect.bottom))
        )
    
    def get_chase_position_for_building(self, target_building) -> Vector2 | None:
        closest = self._closest_point_on_rect(target_building.rect, self.position)
        dir_to_closest = Vector2(closest) - self.position
        dist_to_closest = dir_to_closest.length()
        if dist_to_closest <= self.attack_range:
            return None
        if dist_to_closest == 0:
            return None
        dir_unit = dir_to_closest.normalize()
        
        target_pos = Vector2(closest) - dir_unit * self.attack_range
        
        perp_dir = dir_unit.rotate_rad(math.pi / 2)
        max_spread = min(15, self.attack_range * 0.15)  
        spread_dist = random.uniform(-max_spread, max_spread)
        target_pos += perp_dir * spread_dist
        
        new_closest = self._closest_point_on_rect(target_building.rect, target_pos)
        new_dist = Vector2(new_closest).distance_to(target_pos)
        if new_dist > self.attack_range:
            overage = new_dist - self.attack_range
            adjust_dir = (Vector2(new_closest) - target_pos).normalize()
            target_pos += adjust_dir * overage * 0.5  
        
        target_pos.x = max(0, min(target_pos.x, self.map_width))
        target_pos.y = max(0, min(target_pos.y, self.map_height))
        return target_pos
    
    def _setup_drawing(self, unit_type: str):
        self.height = self.stats.get("height", 0)
        
        if unit_type in ["Infantry", "Grenadier", "RocketSoldier"]:
            self.draw = self.draw_humanoid
        elif unit_type in ["Barracks", "WarFactory", "Hangar", "PowerPlant", 
                           "OilDerrick", "Refinery", "ShaleFracker", "BlackMarket", "Turret"]:
            pass
        else:
            self.draw = self.draw_static if not self.is_vehicle else self.draw_vehicle
    
    def _update_production(self, friendly_units, all_units):
        if self.production_queue:
            if self.production_timer is None:
                self.production_timer = self.stats["production_time"]
            self.production_timer -= 1
            if self.production_timer <= 0:
                item = self.production_queue.pop(0)
                unit_type = item['unit_type']
                repeat = item.get('repeat', False)
                spawn_pos = (self.rect.right, self.rect.centery)
                try:
                    new_unit = globals()[unit_type](spawn_pos, self.team, hq=self.hq)
                except KeyError:
                    new_unit = globals()["Infantry"](spawn_pos, self.team, hq=self.hq)
                new_unit.map_width = self.map_width
                new_unit.map_height = self.map_height
                self.hq.stats['units_created'] += 1
                new_unit.position = Vector2(spawn_pos)
                new_unit.rect.center = new_unit.position
                new_unit.move_target = self.rally_point
                friendly_units.add(new_unit)
                all_units.add(new_unit)
                if repeat:
                    self.production_queue.append({'unit_type': unit_type, 'repeat': True})
                self.production_timer = None
    
    def update(self, particles=None, friendly_units=None, all_units=None, global_buildings=None, projectiles=None, enemy_units=None, enemy_buildings=None):
        self.under_attack_timer = max(0, self.under_attack_timer - 1)
        self.under_attack = self.under_attack_timer > 0
        
        if self.last_shot_time > 0:
            self.last_shot_time -= 1
        
        if self.attack_target:
            if not hasattr(self.attack_target, 'health') or self.attack_target.health <= 0:
                if self.move_target == self.attack_target.position:
                    self.move_target = None
                self.attack_target = None
            elif self.distance_to(self.attack_target.position) > self.sight_range:
                if self.move_target == self.attack_target.position:
                    self.move_target = None
                self.attack_target = None
        
        if not self.is_building:
            if self.attack_target and self.attack_target.health > 0:
                if self.attack_target.is_building:
                    closest = self._closest_point_on_rect(self.attack_target.rect, self.position)
                    dir_to_closest = Vector2(closest) - self.position
                    dist = dir_to_closest.length()
                else:
                    dist = self.distance_to(self.attack_target.position)
                if self.attack_target.is_building:
                    closest_enemy = self._closest_point_on_rect(self.attack_target.rect, self.position)
                    dir_to_enemy = Vector2(closest_enemy) - self.position
                else:
                    dir_to_enemy = Vector2(self.attack_target.position) - self.position
                if dir_to_enemy.length() > 0:
                    dir_to_enemy = dir_to_enemy.normalize()
                self.turret_angle = math.atan2(dir_to_enemy.y, dir_to_enemy.x)
                if dist <= self.attack_range:
                    original_move_target = self.move_target
                    self.move_target = None
                    if not self.attack_target.is_building and random.random() < 0.1:
                        self.position += dir_to_enemy.rotate_rad(random.uniform(-0.5, 0.5)) * self.speed * 0.2
                else:
                    if self.attack_target.is_building:
                        chase_pos = self.get_chase_position_for_building(self.attack_target)
                        if chase_pos is not None:
                            self.move_target = chase_pos
                        else:
                            self.move_target = None
                    else:
                        self.move_target = self.attack_target.position
        
        if not self.attack_target:
            self.turret_angle = self.body_angle
        
        half_w = self.rect.width / 2
        half_h = self.rect.height / 2
        if self.move_target:
            mt_x = max(half_w, min(self.move_target[0], self.map_width - half_w))
            mt_y = max(half_h, min(self.move_target[1], self.map_height - half_h))
            self.move_target = (mt_x, mt_y)
            dir_to_target = Vector2(self.move_target) - self.position
            dist_to_move = dir_to_target.length()
            if dist_to_move > 5:
                move_dir = dir_to_target.normalize()
                self.position += move_dir * self.speed
                self.body_angle = math.atan2(move_dir.y, move_dir.x)
            else:
                self.move_target = None
        
        self.position.x = max(half_w, min(self.position.x, self.map_width - half_w))
        self.position.y = max(half_h, min(self.position.y, self.map_height - half_h))
        
        if hasattr(self, 'stats') and "producible" in self.stats and friendly_units is not None and all_units is not None:
            self._update_production(friendly_units, all_units)
        
        if hasattr(self, 'collection_timer'):
            self.collection_timer += 1
            if self.collection_timer >= self.stats.get("income_interval", 300):
                income = self.stats["income"]
                self.hq.credits += income
                self.hq.stats['credits_earned'] += income
                self.collection_timer = 0
        
        self.rect.center = self.position
        
        self.plasma_burn_particles = [p for p in self.plasma_burn_particles if p.alive()]
    
    def get_attack_range(self) -> float:
        return self.attack_range
    
    def get_damage(self) -> int:
        if self.weapons:
            return self.weapons[0]["damage"]
        return 0
    
    def shoot(self, target, projectiles: pg.sprite.Group):
        if not self.weapons or self.last_shot_time > 0:
            return
        weapon = self.weapons[0]
        if target.is_building:
            closest = self._closest_point_on_rect(target.rect, self.position)
            dist = Vector2(closest).distance_to(self.position)
            aim_pos = closest
        else:
            dist = self.distance_to(target.position)
            time_to_target = dist / weapon["projectile_speed"]
            target_vel = Vector2(
                target.speed * math.cos(getattr(target, 'body_angle', 0)) if hasattr(target, 'speed') else 0,
                target.speed * math.sin(getattr(target, 'body_angle', 0)) if hasattr(target, 'speed') else 0
            )
            predicted_pos = target.position + target_vel * time_to_target
            aim_pos = predicted_pos
        if dist > self.get_attack_range():
            return
        vec = aim_pos - self.position
        if vec.length() == 0:
            return
        direction = vec.normalize()
        proj = Projectile(self.position, direction, weapon["damage"], self.team, weapon)
        projectiles.add(proj)
        self.last_shot_time = weapon["cooldown"]
        self.turret_angle = math.atan2(direction.y, direction.x)
        create_explosion(self.position, pg.sprite.Group(), self.team, 3)

class Infantry(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Infantry", hq=hq)

class RocketSoldier(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "RocketSoldier", hq=hq)

class Tank(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Tank", hq=hq)

class Grenadier(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Grenadier", hq=hq)

class MachineGunVehicle(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "MachineGunVehicle", hq=hq)

class RocketArtillery(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "RocketArtillery", hq=hq)

class AttackHelicopter(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "AttackHelicopter", hq=hq)

class Headquarters(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Headquarters", hq=hq)
        self.credits = self.stats["starting_credits"]
        self.power_output = 100
        self.power_usage = 50
        self.has_enough_power = True
        self.production_queue: list[Dict[str, Any]] = []
        self.production_timer = None
        self.pending_building = None
        self.pending_building_pos = None
        self.rally_point = Vector2(position[0] + (100 if team == Team.GREEN else position[0] - 100), position[1])
        self.radius = 50
        self.stats = {
            "units_created": 0,
            "units_lost": 0,
            "units_destroyed": 0,
            "buildings_constructed": 0,
            "buildings_lost": 0,
            "buildings_destroyed": 0,
            "credits_earned": 0,
        }
    
    def place_building(self, position: tuple, unit_cls: Type, all_buildings):
        all_buildings_list = list(all_buildings)
        if is_valid_building_position(position, self.team, unit_cls, all_buildings_list):
            unit_type = unit_cls.__name__
            building = unit_cls(position, self.team, hq=self)
            building.map_width = self.map_width
            building.map_height = self.map_height
            if unit_type in ["WarFactory", "Barracks", "Hangar"]:
                building.parent_hq = self
            all_buildings.add(building)
            self.stats['buildings_constructed'] += 1
            self.credits -= UNIT_CLASSES[unit_type]["cost"]
            self.pending_building = None

import math
import pygame as pg

class PowerPlant(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "PowerPlant", hq=hq)

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        main_w = w * 1.2
        main_d = d * 1.0
        main_h = h * 0.6
        self.draw_rotated_box(surface, camera, main_w, main_d, main_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        elev_w = w * 0.6
        elev_d = d * 0.6
        elev_h = h * 0.4
        elev_base_z = base_z + main_h
        self.draw_rotated_box(surface, camera, elev_w, elev_d, elev_h, self.body_angle, elev_base_z, tuple(min(255, c + 20) for c in self.team_color), side_color, self.team_color, outline_color, zoom, False)

        vent_x = pos.x
        vent_y = pos.y
        vent_base = (vent_x, vent_y, elev_base_z + elev_h)
        vent_top = (vent_x, vent_y, elev_base_z + elev_h + h * 0.5)
        p_vent_base = camera.world_to_iso_3d(*vent_base, zoom)
        p_vent_top = camera.world_to_iso_3d(*vent_top, zoom)
        vent_color = pg.Color(80, 80, 80)
        pg.draw.line(surface, vent_color, p_vent_base, p_vent_top, int(4 * zoom))
        pg.draw.circle(surface, pg.Color(60, 60, 60), (int(p_vent_top[0]), int(p_vent_top[1])), int(3 * zoom))

        for offset in [0.3, -0.3]:
            for ang in [0, math.pi/2]:
                tower_x = pos.x + offset * w * math.cos(self.body_angle + ang)
                tower_y = pos.y + offset * w * math.sin(self.body_angle + ang)
                tower_base = (tower_x, tower_y, base_z + main_h * 0.5)
                tower_top = (tower_x, tower_y, tower_base[2] + h * 0.3)
                p_tower_base = camera.world_to_iso_3d(*tower_base, zoom)
                p_tower_top = camera.world_to_iso_3d(*tower_top, zoom)
                radius = int(w * 0.08 * zoom)
                pg.draw.circle(surface, pg.Color(100, 100, 100), (int(p_tower_base[0]), int(p_tower_base[1])), radius)
                pg.draw.circle(surface, pg.Color(80, 80, 80), (int(p_tower_top[0]), int(p_tower_top[1])), radius - 1)
                pg.draw.line(surface, outline_color, p_tower_base, p_tower_top, int(2 * zoom))

        for i in range(4):
            start_ang = i * math.pi / 2 + self.body_angle
            start_x = pos.x + 0.4 * w * math.cos(start_ang)
            start_y = pos.y + 0.4 * w * math.sin(start_ang)
            end_ang = (i + 1) * math.pi / 2 + self.body_angle
            end_x = pos.x + 0.4 * w * math.cos(end_ang)
            end_y = pos.y + 0.4 * w * math.sin(end_ang)
            pipe_z = base_z + main_h * 0.7
            p_start = camera.world_to_iso_3d(start_x, start_y, pipe_z, zoom)
            p_end = camera.world_to_iso_3d(end_x, end_y, pipe_z, zoom)
            pg.draw.line(surface, pg.Color(120, 120, 120), p_start, p_end, int(2 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class OilDerrick(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "OilDerrick", hq=hq)

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        base_w = w * 1.8
        base_d = d * 1.8
        base_h = h * 0.15
        self.draw_rotated_box(surface, camera, base_w, base_d, base_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        tower_w = w * 0.4
        tower_d = d * 0.4
        tower_h = h * 0.85
        tower_base_z = base_z + base_h
        self.draw_rotated_box(surface, camera, tower_w, tower_d, tower_h, self.body_angle, tower_base_z, pg.Color(100, 80, 50), side_color, pg.Color(100, 80, 50), outline_color, zoom, False)

        arm_length = w * 1.4
        arm_width = w * 0.08
        arm_height = d * 0.08
        arm_base_z = tower_base_z + tower_h * 0.75
        arm_angle = math.pi / 4  
        arm_cos = math.cos(arm_angle)
        arm_sin = math.sin(arm_angle)
        arm_start_x = pos.x
        arm_start_y = pos.y
        arm_end_x = arm_start_x + arm_length * arm_cos * cos - arm_length * arm_sin * sin
        arm_end_y = arm_start_y + arm_length * arm_cos * sin + arm_length * arm_sin * cos
        p_arm_start = camera.world_to_iso_3d(arm_start_x, arm_start_y, arm_base_z, zoom)
        p_arm_end = camera.world_to_iso_3d(arm_end_x, arm_end_y, arm_base_z, zoom)
        arm_color = pg.Color(60, 50, 30)
        pg.draw.line(surface, arm_color, p_arm_start, p_arm_end, int(4 * zoom))

        drill_x = arm_end_x
        drill_y = arm_end_y
        drill_base = (drill_x, drill_y, arm_base_z)
        drill_tip = (drill_x, drill_y, arm_base_z - h * 0.3)
        p_drill_base = camera.world_to_iso_3d(*drill_base, zoom)
        p_drill_tip = camera.world_to_iso_3d(*drill_tip, zoom)
        drill_color = pg.Color(80, 60, 40)
        pg.draw.circle(surface, drill_color, (int(p_drill_base[0]), int(p_drill_base[1])), int(w * 0.15 * zoom))
        pg.draw.line(surface, pg.Color(40, 30, 20), p_drill_base, p_drill_tip, int(3 * zoom))

        for strut_angle in [0, math.pi / 2]:
            strut_x = pos.x + (tower_w * 0.5) * math.cos(strut_angle + self.body_angle)
            strut_y = pos.y + (tower_w * 0.5) * math.sin(strut_angle + self.body_angle)
            strut_base = (strut_x, strut_y, tower_base_z)
            strut_top = (strut_x * 0.8, strut_y * 0.8, tower_base_z + tower_h * 0.3)
            p_strut_base = camera.world_to_iso_3d(*strut_base, zoom)
            p_strut_top = camera.world_to_iso_3d(*strut_top, zoom)
            pg.draw.line(surface, pg.Color(80, 70, 50), p_strut_base, p_strut_top, int(2 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class Refinery(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Refinery", hq=hq)
        self.radius = 60

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        main_w = w * 1.0
        main_d = d * 1.2
        main_h = h * 0.4
        self.draw_rotated_box(surface, camera, main_w, main_d, main_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        upper_w = w * 0.8
        upper_d = d * 1.0
        upper_h = h * 0.3
        upper_base_z = base_z + main_h
        self.draw_rotated_box(surface, camera, upper_w, upper_d, upper_h, self.body_angle, upper_base_z, tuple(min(255, c + 10) for c in self.team_color), side_color, self.team_color, outline_color, zoom, False)

        for silo_offset in [-w * 0.4, w * 0.4]:
            silo_x = pos.x + silo_offset * cos
            silo_y = pos.y + silo_offset * sin
            silo_base = (silo_x, silo_y, upper_base_z + upper_h)
            silo_top = (silo_x, silo_y, silo_base[2] + h * 0.6)
            p_silo_base = camera.world_to_iso_3d(*silo_base, zoom)
            p_silo_top = camera.world_to_iso_3d(*silo_top, zoom)
            silo_color = pg.Color(100, 100, 100)
            radius = int(w * 0.15 * zoom)
            pg.draw.circle(surface, silo_color, (int(p_silo_base[0]), int(p_silo_base[1])), radius)
            pg.draw.circle(surface, pg.Color(80, 80, 80), (int(p_silo_top[0]), int(p_silo_top[1])), radius - 2)
            pg.draw.line(surface, outline_color, p_silo_base, p_silo_top, int(3 * zoom))

        for vat_offset in [-d * 0.3, d * 0.3]:
            vat_x = pos.x + vat_offset * sin  
            vat_y = pos.y - vat_offset * cos
            vat_base = (vat_x, vat_y, base_z + main_h * 0.5)
            vat_top = (vat_x, vat_y, vat_base[2] + h * 0.2)
            p_vat_base = camera.world_to_iso_3d(*vat_base, zoom)
            p_vat_top = camera.world_to_iso_3d(*vat_top, zoom)
            vat_color = pg.Color(120, 90, 40)
            radius = int(d * 0.12 * zoom)
            pg.draw.circle(surface, vat_color, (int(p_vat_base[0]), int(p_vat_base[1])), radius)
            pg.draw.circle(surface, pg.Color(100, 70, 30), (int(p_vat_top[0]), int(p_vat_top[1])), radius - 1)
            pg.draw.line(surface, outline_color, p_vat_base, p_vat_top, int(2 * zoom))

        for i in range(3):
            start_x = pos.x - w * 0.3 * cos + i * 0.2 * w * cos
            start_y = pos.y - w * 0.3 * sin + i * 0.2 * w * sin
            end_x = pos.x + w * 0.3 * cos + i * 0.2 * w * cos
            end_y = pos.y + w * 0.3 * sin + i * 0.2 * w * sin
            pipe_z = base_z + h * 0.6
            p_start = camera.world_to_iso_3d(start_x, start_y, pipe_z, zoom)
            p_end = camera.world_to_iso_3d(end_x, end_y, pipe_z, zoom)
            pg.draw.line(surface, pg.Color(150, 150, 150), p_start, p_end, int(2 * zoom))

        for dock_offset in [-w * 0.5, w * 0.5]:
            dock_x = pos.x + dock_offset * cos
            dock_y = pos.y + dock_offset * sin
            dock_base = (dock_x, dock_y, upper_base_z)
            dock_top = (dock_x, dock_y, upper_base_z + upper_h * 0.2)
            p_dock_base = camera.world_to_iso_3d(*dock_base, zoom)
            p_dock_top = camera.world_to_iso_3d(*dock_top, zoom)
            pg.draw.line(surface, pg.Color(80, 80, 80), p_dock_base, p_dock_top, int(3 * zoom))

        control_w = w * 0.3
        control_d = d * 0.3
        control_h = h * 0.5
        control_offset_x = d * 0.4 * sin
        control_offset_y = -d * 0.4 * cos
        control_x = pos.x + control_offset_x
        control_y = pos.y + control_offset_y
        control_base = (control_x, control_y, base_z + h)
        control_top = (control_x, control_y, base_z + h + control_h)
        p_control_base = camera.world_to_iso_3d(*control_base, zoom)
        p_control_top = camera.world_to_iso_3d(*control_top, zoom)
        pg.draw.line(surface, pg.Color(80, 80, 100), p_control_base, p_control_top, int(4 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class ShaleFracker(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "ShaleFracker", hq=hq)

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        self.draw_rotated_box(surface, camera, w * 1.1, d * 0.9, h * 0.7, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        pump_w = w * 0.35
        pump_d = d * 0.35
        pump_h = h * 0.9
        pump_base_z = base_z
        self.draw_rotated_box(surface, camera, pump_w, pump_d, pump_h, self.body_angle, pump_base_z, pg.Color(120, 100, 80), side_color, pg.Color(100, 80, 60), outline_color, zoom, False)

        for cyl_side in [-w * 0.4, w * 0.4]:
            cyl_x = pos.x + cyl_side * cos
            cyl_y = pos.y + cyl_side * sin
            cyl_base = (cyl_x, cyl_y, base_z)
            cyl_top = (cyl_x, cyl_y, base_z + pump_h * 0.8)
            p_cyl_base = camera.world_to_iso_3d(*cyl_base, zoom)
            p_cyl_top = camera.world_to_iso_3d(*cyl_top, zoom)
            pg.draw.line(surface, pg.Color(100, 100, 120), p_cyl_base, p_cyl_top, int(3 * zoom))
            pg.draw.circle(surface, pg.Color(80, 80, 100), (int(p_cyl_base[0]), int(p_cyl_base[1])), int(2 * zoom))
            pg.draw.circle(surface, pg.Color(60, 60, 80), (int(p_cyl_top[0]), int(p_cyl_top[1])), int(2 * zoom))

        for gauge_offset in [(-w * 0.15, -d * 0.2), (w * 0.15, -d * 0.2)]:
            gauge_x = pos.x + gauge_offset[0] * cos - gauge_offset[1] * sin
            gauge_y = pos.y + gauge_offset[0] * sin + gauge_offset[1] * cos
            gauge_z = base_z + h * 0.5
            p_gauge = camera.world_to_iso_3d(gauge_x, gauge_y, gauge_z, zoom)
            pg.draw.circle(surface, pg.Color(200, 100, 100), (int(p_gauge[0]), int(p_gauge[1])), int(2 * zoom))

        drill_x = pos.x
        drill_y = pos.y
        drill_base = (drill_x, drill_y, base_z + pump_h)
        drill_tip = (drill_x, drill_y, base_z + pump_h + h * 0.5)
        p_drill_base = camera.world_to_iso_3d(*drill_base, zoom)
        p_drill_tip = camera.world_to_iso_3d(*drill_tip, zoom)
        pg.draw.line(surface, pg.Color(60, 60, 60), p_drill_base, p_drill_tip, int(3 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class BlackMarket(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "BlackMarket", hq=hq)

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        self.draw_rotated_box(surface, camera, w * 1.0, d * 0.9, h * 0.8, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        tent_h = h * 0.4
        tent_base_z = base_z + h * 0.8
        tent_w = w * 1.2
        tent_d = d * 1.1
        rel_tent_bottom = [
            (-tent_w / 2, -tent_d / 2, 0),
            (tent_w / 2, -tent_d / 2, 0),
            (tent_w / 2, tent_d / 2, 0),
            (-tent_w / 2, tent_d / 2, 0),
        ]
        rel_tent_top = [(x, y, tent_h) for x, y, _ in rel_tent_bottom]
        def rotate_rel(points, cos, sin):
            return [(x * cos - y * sin, x * sin + y * cos, z) for x, y, z in points]
        rot_tent_bottom = rotate_rel(rel_tent_bottom, cos, sin)
        rot_tent_top = rotate_rel(rel_tent_top, cos, sin)
        full_tent_bottom = [(pos.x + rx, pos.y + ry, tent_base_z + rz) for rx, ry, rz in rot_tent_bottom]
        full_tent_top = [(pos.x + rx, pos.y + ry, tent_base_z + rz) for rx, ry, rz in rot_tent_top]
        p_tent_bottom = [camera.world_to_iso_3d(*pt, zoom) for pt in full_tent_bottom]
        p_tent_top = [camera.world_to_iso_3d(*pt, zoom) for pt in full_tent_top]
        tent_color = pg.Color(180, 100, 50)
        pg.draw.polygon(surface, tent_color, p_tent_bottom + p_tent_top)

        for crate_x_off in [-w * 0.3, w * 0.3]:
            for crate_y_off in [-d * 0.2, d * 0.2]:
                crate_x = pos.x + crate_x_off * cos - crate_y_off * sin
                crate_y = pos.y + crate_x_off * sin + crate_y_off * cos
                crate_w = w * 0.15
                crate_d = d * 0.15
                crate_h = h * 0.25
                crate_color = pg.Color(140, 90, 40)
                crate_base = (crate_x, crate_y, base_z)
                crate_top = (crate_x, crate_y, base_z + crate_h)
                p_crate_base = camera.world_to_iso_3d(*crate_base, zoom)
                p_crate_top = camera.world_to_iso_3d(*crate_top, zoom)
                pg.draw.rect(surface, crate_color, (int(p_crate_base[0] - crate_w * zoom), int(p_crate_base[1] - crate_d * zoom), int(crate_w * zoom * 2), int(crate_d * zoom * 2)))

        sign_x = pos.x + w * 0.4 * cos
        sign_y = pos.y + w * 0.4 * sin
        sign_z = base_z + h
        p_sign = camera.world_to_iso_3d(sign_x, sign_y, sign_z, zoom)
        pg.draw.rect(surface, pg.Color(255, 200, 0), (int(p_sign[0] - 15 * zoom), int(p_sign[1] - 10 * zoom), int(30 * zoom), int(20 * zoom)))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class Turret(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Turret", hq=hq)

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        roof_color = pg.Color(120, 120, 120)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        base_w = w * 1.3
        base_d = d * 1.3
        base_h = h * 0.5
        self.draw_rotated_box(surface, camera, base_w, base_d, base_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        turret_w = w * 0.7
        turret_d = d * 0.7
        turret_h = h * 0.7
        turret_base_z = base_z + base_h
        self.draw_rotated_box(surface, camera, turret_w, turret_d, turret_h, self.turret_angle, turret_base_z, self.team_color, side_color, roof_color, outline_color, zoom, True)

        barrel_length = w * 1.8
        barrel_width = w * 0.12
        barrel_height = d * 0.12
        barrel_base_z = turret_base_z + turret_h / 2
        cos_t = math.cos(self.turret_angle)
        sin_t = math.sin(self.turret_angle)
        front_offset = turret_d / 2 * 0.9
        barrel_start_x = pos.x + front_offset * cos_t
        barrel_start_y = pos.y + front_offset * sin_t
        barrel_start_z = barrel_base_z
        barrel_end_x = barrel_start_x + barrel_length * cos_t
        barrel_end_y = barrel_start_y + barrel_length * sin_t
        barrel_end_z = barrel_start_z
        perp_cos = -sin_t
        perp_sin = cos_t
        b1 = (barrel_start_x - (barrel_width / 2) * perp_cos, barrel_start_y - (barrel_width / 2) * perp_sin, barrel_start_z - barrel_height / 2)
        b2 = (barrel_start_x + (barrel_width / 2) * perp_cos, barrel_start_y + (barrel_width / 2) * perp_sin, barrel_start_z - barrel_height / 2)
        b3 = (barrel_end_x + (barrel_width / 2) * perp_cos, barrel_end_y + (barrel_width / 2) * perp_sin, barrel_end_z - barrel_height / 2)
        b4 = (barrel_end_x - (barrel_width / 2) * perp_cos, barrel_end_y - (barrel_width / 2) * perp_sin, barrel_end_z - barrel_height / 2)
        p_b1 = camera.world_to_iso_3d(*b1, zoom)
        p_b2 = camera.world_to_iso_3d(*b2, zoom)
        p_b3 = camera.world_to_iso_3d(*b3, zoom)
        p_b4 = camera.world_to_iso_3d(*b4, zoom)
        barrel_color = tuple(min(255, c + 40) for c in self.team_color)
        pg.draw.polygon(surface, barrel_color, [p_b1, p_b2, p_b3, p_b4])
        pg.draw.line(surface, outline_color, p_b1, p_b2, int(2 * zoom))
        pg.draw.line(surface, outline_color, p_b3, p_b4, int(2 * zoom))

        coax_x = barrel_start_x - (barrel_width * 0.5) * perp_cos
        coax_y = barrel_start_y - (barrel_width * 0.5) * perp_sin
        coax_end_x = coax_x + (barrel_length * 0.8) * cos_t
        coax_end_y = coax_y + (barrel_length * 0.8) * sin_t
        p_coax_start = camera.world_to_iso_3d(coax_x, coax_y, barrel_base_z - barrel_height, zoom)
        p_coax_end = camera.world_to_iso_3d(coax_end_x, coax_end_y, barrel_base_z - barrel_height, zoom)
        pg.draw.line(surface, pg.Color(100, 100, 100), p_coax_start, p_coax_end, int(1 * zoom))

        ammo_x = pos.x - (barrel_width * 1.5) * perp_cos
        ammo_y = pos.y - (barrel_width * 1.5) * perp_sin
        ammo_z = barrel_base_z - barrel_height
        ammo_size = w * 0.15
        p_ammo = camera.world_to_iso_3d(ammo_x, ammo_y, ammo_z, zoom)
        ammo_color = pg.Color(80, 80, 100)
        pg.draw.rect(surface, ammo_color, (int(p_ammo[0] - ammo_size * zoom), int(p_ammo[1] - ammo_size * zoom), int(ammo_size * zoom * 2), int(ammo_size * zoom * 1.5)))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class Barracks(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Barracks", hq=hq)
        self.parent_hq = None

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        main_w = w * 1.3
        main_d = d * 1.1
        main_h = h * 0.7
        self.draw_rotated_box(surface, camera, main_w, main_d, main_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        platform_w = w * 0.8
        platform_d = d * 0.4
        platform_h = h * 0.1
        front_offset = -d * 0.6 * cos
        side_offset = -d * 0.6 * sin
        platform_x = pos.x + front_offset
        platform_y = pos.y + side_offset
        platform_base = (platform_x, platform_y, base_z)
        platform_top = (platform_x, platform_y, base_z + platform_h)
        p_platform_base = camera.world_to_iso_3d(*platform_base, zoom)
        p_platform_top = camera.world_to_iso_3d(*platform_top, zoom)
        pg.draw.line(surface, pg.Color(100, 100, 100), p_platform_base, p_platform_top, int(3 * zoom))

        door_w = w * 0.5
        door_h = h * 0.4
        door_center_x = pos.x - d * 0.5 * cos
        door_center_y = pos.y - d * 0.5 * sin
        door_bl = (door_center_x - door_w / 2, door_center_y, base_z + platform_h)
        door_br = (door_center_x + door_w / 2, door_center_y, base_z + platform_h)
        door_tl = (door_center_x - door_w / 2, door_center_y, base_z + platform_h + door_h)
        door_tr = (door_center_x + door_w / 2, door_center_y, base_z + platform_h + door_h)
        p_door_bl = camera.world_to_iso_3d(*door_bl, zoom)
        p_door_br = camera.world_to_iso_3d(*door_br, zoom)
        p_door_tl = camera.world_to_iso_3d(*door_tl, zoom)
        p_door_tr = camera.world_to_iso_3d(*door_tr, zoom)
        door_color = pg.Color(50, 50, 50)
        pg.draw.polygon(surface, door_color, [p_door_bl, p_door_br, p_door_tr, p_door_tl])

        window_size = w * 0.1
        for win_y in [base_z + platform_h + h * 0.2, base_z + platform_h + h * 0.5]:
            for win_side in [-door_w * 0.3, door_w * 0.3]:
                win_x = door_center_x + win_side
                win_y_pos = door_center_y
                p_win = camera.world_to_iso_3d(win_x, win_y_pos, win_y, zoom)
                pg.draw.rect(surface, pg.Color(100, 150, 200), (int(p_win[0] - window_size * zoom), int(p_win[1] - window_size * 0.5 * zoom), int(window_size * zoom * 2), int(window_size * zoom)))

        hatch_x = pos.x + w * 0.6 * cos
        hatch_y = pos.y + w * 0.6 * sin
        hatch_base = (hatch_x, hatch_y, base_z + main_h * 0.5)
        hatch_top = (hatch_x, hatch_y, hatch_base[2] + h * 0.2)
        p_hatch_base = camera.world_to_iso_3d(*hatch_base, zoom)
        p_hatch_top = camera.world_to_iso_3d(*hatch_top, zoom)
        pg.draw.line(surface, pg.Color(60, 60, 60), p_hatch_base, p_hatch_top, int(2 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class WarFactory(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "WarFactory", hq=hq)
        self.parent_hq = None

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        main_w = w * 1.2
        main_d = d * 1.3
        main_h = h * 0.6
        self.draw_rotated_box(surface, camera, main_w, main_d, main_h, self.body_angle, base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        attach_w = w * 0.4
        attach_d = d * 0.5
        attach_h = h * 0.4
        for attach_off in [-main_d * 0.3 * sin, main_d * 0.3 * sin]:  
            attach_x = pos.x + attach_off
            attach_y = pos.y - attach_off * cos / sin if sin != 0 else pos.y
            attach_base = (attach_x, attach_y, base_z + main_h * 0.2)
            self.draw_rotated_box(surface, camera, attach_w, attach_d, attach_h, self.body_angle, attach_base[2], pg.Color(90, 90, 90), side_color, pg.Color(90, 90, 90), outline_color, zoom, False)

        crane_base_z = base_z + main_h
        crane_length = w * 1.5
        crane_offset = d * 0.2
        crane_start_x = pos.x - (crane_length / 2) * cos + crane_offset * sin
        crane_start_y = pos.y - (crane_length / 2) * sin - crane_offset * cos
        crane_end_x = pos.x + (crane_length / 2) * cos + crane_offset * sin
        crane_end_y = pos.y + (crane_length / 2) * sin - crane_offset * cos
        p_crane_start = camera.world_to_iso_3d(crane_start_x, crane_start_y, crane_base_z, zoom)
        p_crane_end = camera.world_to_iso_3d(crane_end_x, crane_end_y, crane_base_z, zoom)
        crane_color = pg.Color(100, 100, 100)
        pg.draw.line(surface, crane_color, p_crane_start, p_crane_end, int(5 * zoom))

        pulley_x = (crane_start_x + crane_end_x) / 2
        pulley_y = (crane_start_y + crane_end_y) / 2
        p_pulley = camera.world_to_iso_3d(pulley_x, pulley_y, crane_base_z + h * 0.1, zoom)
        pg.draw.circle(surface, pg.Color(80, 80, 80), (int(p_pulley[0]), int(p_pulley[1])), int(4 * zoom))

        stack_offsets = [-w * 0.2, 0, w * 0.2]
        stack_heights = [h * 0.6, h * 0.8, h * 0.4]
        for off, height in zip(stack_offsets, stack_heights):
            stack_x = pos.x + off * cos
            stack_y = pos.y + off * sin
            stack_base = (stack_x, stack_y, base_z + main_h)
            stack_top = (stack_x, stack_y, stack_base[2] + height)
            p_stack_base = camera.world_to_iso_3d(*stack_base, zoom)
            p_stack_top = camera.world_to_iso_3d(*stack_top, zoom)
            stack_color = pg.Color(70, 70, 70)
            radius = int(w * 0.06 * zoom)
            pg.draw.circle(surface, stack_color, (int(p_stack_base[0]), int(p_stack_base[1])), radius)
            pg.draw.circle(surface, pg.Color(60, 60, 60), (int(p_stack_top[0]), int(p_stack_top[1])), radius - 1)
            pg.draw.line(surface, outline_color, p_stack_base, p_stack_top, int(3 * zoom))

        door_w = w * 0.7
        door_h = h * 0.4
        door_center_x = pos.x - d * 0.6 * cos
        door_center_y = pos.y - d * 0.6 * sin
        door_bl = (door_center_x - door_w / 2, door_center_y, base_z)
        door_br = (door_center_x + door_w / 2, door_center_y, base_z)
        door_tl = (door_center_x - door_w / 2, door_center_y, base_z + door_h)
        door_tr = (door_center_x + door_w / 2, door_center_y, base_z + door_h)
        p_door_bl = camera.world_to_iso_3d(*door_bl, zoom)
        p_door_br = camera.world_to_iso_3d(*door_br, zoom)
        p_door_tl = camera.world_to_iso_3d(*door_tl, zoom)
        p_door_tr = camera.world_to_iso_3d(*door_tr, zoom)
        door_color = pg.Color(40, 40, 40)
        pg.draw.polygon(surface, door_color, [p_door_bl, p_door_br, p_door_tr, p_door_tl])

        for level in [base_z + h * 0.3, base_z + h * 0.6]:
            for win_off in [-w * 0.4, w * 0.4, 0]:
                win_x = pos.x + win_off * cos
                win_y = pos.y + win_off * sin
                p_win = camera.world_to_iso_3d(win_x, win_y, level, zoom)
                win_size = w * 0.08
                pg.draw.rect(surface, pg.Color(150, 200, 255), (int(p_win[0] - win_size * zoom), int(p_win[1] - win_size * 0.5 * zoom), int(win_size * zoom * 2), int(win_size * zoom)))

        conv_x1 = pos.x - w * 0.5 * cos
        conv_y1 = pos.y - w * 0.5 * sin
        conv_x2 = pos.x + w * 0.5 * cos
        conv_y2 = pos.y + w * 0.5 * sin
        conv_z = base_z + main_h * 0.8
        p_conv1 = camera.world_to_iso_3d(conv_x1, conv_y1, conv_z, zoom)
        p_conv2 = camera.world_to_iso_3d(conv_x2, conv_y2, conv_z, zoom)
        pg.draw.line(surface, pg.Color(90, 90, 90), p_conv1, p_conv2, int(3 * zoom))

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)


class Hangar(Unit):
    def __init__(self, position: tuple, team: Team, hq=None):
        super().__init__(position, team, "Hangar", hq=hq)
        self.parent_hq = None

    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        zoom = camera.zoom
        w, d = self.size
        h = self.height
        pos = self.position
        base_z = 0
        side_color = tuple(max(0, c - 50) for c in self.team_color)
        outline_color = pg.Color(0, 0, 0)
        p_bottom = []

        cos = math.cos(self.body_angle)
        sin = math.sin(self.body_angle)

        platform_w = w * 1.4
        platform_d = d * 1.2
        platform_h = h * 0.2
        platform_base_z = base_z
        self.draw_rotated_box(surface, camera, platform_w, platform_d, platform_h, self.body_angle, platform_base_z, self.team_color, side_color, self.team_color, outline_color, zoom, False, p_bottom)

        pillar_radius = w * 0.08
        pillar_h = platform_h
        pillar_offsets = [(-platform_w * 0.4, -platform_d * 0.4), (platform_w * 0.4, -platform_d * 0.4), (platform_w * 0.4, platform_d * 0.4), (-platform_w * 0.4, platform_d * 0.4)]
        for off_x, off_y in pillar_offsets:
            pillar_x = pos.x + off_x * cos - off_y * sin
            pillar_y = pos.y + off_x * sin + off_y * cos
            pillar_ground = (pillar_x, pillar_y, base_z)
            pillar_top = (pillar_x, pillar_y, base_z + pillar_h)
            p_pillar_ground = camera.world_to_iso_3d(*pillar_ground, zoom)
            p_pillar_top = camera.world_to_iso_3d(*pillar_top, zoom)
            pg.draw.line(surface, pg.Color(80, 80, 80), p_pillar_ground, p_pillar_top, int(4 * zoom))
            pg.draw.circle(surface, pg.Color(100, 100, 100), (int(p_pillar_ground[0]), int(p_pillar_ground[1])), int(pillar_radius * zoom))

        tower_w = w * 0.3
        tower_d = d * 0.3
        tower_h = h * 0.6
        tower_offset_x = w * 0.6 * cos
        tower_offset_y = w * 0.6 * sin
        tower_x = pos.x + tower_offset_x
        tower_y = pos.y + tower_offset_y
        tower_base = (tower_x, tower_y, base_z + platform_h)
        tower_top = (tower_x, tower_y, tower_base[2] + tower_h)
        self.draw_rotated_box(surface, camera, tower_w, tower_d, tower_h, self.body_angle, tower_base[2], pg.Color(100, 80, 60), side_color, pg.Color(100, 80, 60), outline_color, zoom, False)

        win_x = tower_x
        win_y = tower_y
        win_z = tower_base[2] + tower_h * 0.5
        p_win = camera.world_to_iso_3d(win_x, win_y, win_z, zoom)
        win_size = w * 0.1
        pg.draw.rect(surface, pg.Color(150, 200, 255), (int(p_win[0] - win_size * zoom), int(p_win[1] - win_size * 0.5 * zoom), int(win_size * zoom * 2), int(win_size * zoom)))

        pad_center_x = pos.x
        pad_center_y = pos.y
        pad_center_z = base_z + platform_h * 0.5
        p_pad_center = camera.world_to_iso_3d(pad_center_x, pad_center_y, pad_center_z, zoom)
        pg.draw.circle(surface, pg.Color(255, 255, 255, 100), (int(p_pad_center[0]), int(p_pad_center[1])), int(w * 0.5 * zoom), 2)

        if self.selected:
            pg.draw.polygon(surface, (255, 255, 0), p_bottom, int(2 * zoom))

        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)

class GameConsole:
    def __init__(self):
        self.messages = []
    
    def log(self, message: str):
        self.messages.append(message)
    
    def handle_event(self, event):
        pass
    
    def draw(self, surface: pg.Surface):
        pass

class AI:
    def __init__(self, hq, console, build_dir=math.pi, allies: Set[Team] = frozenset()):
        self.hq = hq
        self.console = console
        self.allies = allies
        self.action_timer = 0
        self.build_attempts = {}
        self.economy_level = 0
        self.military_strength = 0
        self.enemy_strength = 0
        self.threat_level = 0
        self.scout_timer = 0
        self.defense_timer = 0
        self.attack_timer = 0
        self.patrol_timer = 0
        self.build_queue = []
        self.barracks_index = 0
        self.warfactory_index = 0
        self.hangar_index = 0
        self.known_enemy_pos = None
        self.nearby_enemies = []  
        self.personality = random.choice(['aggressive', 'defensive', 'balanced', 'rusher'])
        self.timer_offset = random.randint(0, 180)
        self.interval_multiplier = random.uniform(0.7, 1.3)
        self.build_jitter = random.uniform(0.1, 0.5)
        self.aggression_bias = 1.2 if self.personality in ['aggressive', 'rusher'] else 0.8 if self.personality == 'defensive' else 1.0
        self.economy_bias = 1.0  
        
        base_priorities = {
            "Infantry": 0.6, "Grenadier": 0.2, "RocketSoldier": 0.1, "Tank": 0.15,
            "MachineGunVehicle": 0.05, "RocketArtillery": 0.05, "AttackHelicopter": 0.0,
        }
        if self.personality == 'rusher':
            base_priorities["Infantry"] *= 1.5
            base_priorities["AttackHelicopter"] *= 0.5
        elif self.personality == 'defensive':
            base_priorities["Grenadier"] *= 1.5
            base_priorities["Tank"] *= 0.5
        self.production_priorities = base_priorities
        self.preferred_build_direction = build_dir
        self.build_bias_strength = 0.3  
        self.resource_target = 5  
        self.military_target = 3
        self.power_target = 2
        self.defense_target = 2
        self.expansion_factor = 1.0  

    def _send_attack_group(self, friendly_units, enemy_buildings, enemy_units, num_to_send, map_width, map_height):
        if num_to_send <= 0:
            return
        primary_target = self._get_nearest_enemy_target(enemy_buildings, enemy_units, friendly_units[0].position if friendly_units else (0, 0))
        if not primary_target:
            return
        target_center = primary_target.position if not hasattr(primary_target, 'rect') else primary_target.rect.center
        total_pos = Vector2(0, 0)
        for u in friendly_units[:num_to_send]:
            total_pos += Vector2(u.position)
        avg_pos = total_pos / num_to_send
        dir_to_target = Vector2(target_center) - avg_pos
        if dir_to_target.length() == 0:
            return
        dir_unit = dir_to_target.normalize()
        perp = dir_unit.rotate_rad(math.pi / 2)
        spacing = 30 * (1 + self.economy_level * 0.2)
        attack_dist = 80
        positions = []
        half = (num_to_send - 1) / 2
        for i in range(num_to_send):
            offset = (i - half) * spacing
            flank_pos = Vector2(target_center) - dir_unit * attack_dist + perp * offset
            flank_pos.x = max(0, min(flank_pos.x, map_width))
            flank_pos.y = max(0, min(flank_pos.y, map_height))
            positions.append(tuple(flank_pos))
        attackers = friendly_units[:num_to_send]
        for unit, pos in zip(attackers, positions):
            unit.attack_target = primary_target
            unit.move_target = pos

    def update_rally_points(self, friendly_buildings, enemy_pos, map_width, map_height):
        if not enemy_pos:
            return
        dir_vec = Vector2(enemy_pos) - self.hq.position
        if dir_vec.length() == 0:
            return
        dir_unit = dir_vec.normalize()
        advance = 200 + min(500, self.military_strength * 25)
        target = self.hq.position + dir_unit * advance
        target.x = max(0, min(target.x, map_width))
        target.y = max(0, min(target.y, map_height))
        for b in [b for b in friendly_buildings if hasattr(b, 'rally_point')]:
            offset = Vector2(random.uniform(-30,30), random.uniform(-30,30))
            b.rally_point = target + offset
            b.rally_point.x = max(0, min(b.rally_point.x, map_width))
            b.rally_point.y = max(0, min(b.rally_point.y, map_height))
    
    def assess_situation(self, friendly_units, friendly_buildings, enemy_units, enemy_buildings):
        self.military_strength = len([u for u in friendly_units if u.health > 0])
        self.enemy_strength = len([u for u in enemy_units if u.health > 0])
        
        hq_pos = self.hq.position
        nearby_enemies = [u for u in enemy_units if u.health > 0 and u.distance_to(hq_pos) < 600]
        self.threat_level = len(nearby_enemies) / max(1, self.enemy_strength) if self.enemy_strength > 0 else 0
        self.nearby_enemies = nearby_enemies  
        
        resource_buildings = [b for b in friendly_buildings if b.unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]]
        self.economy_level = len(resource_buildings) // 2  

        self.resource_count = len([b for b in friendly_buildings if b.unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"] and b.health > 0])
        self.turret_count = len([b for b in friendly_buildings if b.unit_type == "Turret" and b.health > 0])
        self.military_prod_count = len([b for b in friendly_buildings if b.unit_type in ["Barracks", "WarFactory", "Hangar"] and b.health > 0])
        self.power_count = len([b for b in friendly_buildings if b.unit_type == "PowerPlant" and b.health > 0])
        self.total_buildings = self.military_prod_count + self.resource_count + self.power_count + self.turret_count
        
        power_plants = len([b for b in friendly_buildings if b.unit_type == "PowerPlant"])
        self.power_shortage = power_plants < self.economy_level + 1

        time_factor = max(1.0, (self.action_timer / 3600) ** 0.5)  
        self.expansion_factor = time_factor * (1 + self.economy_bias)
        self.resource_target = max(5, int(self.total_buildings * 0.3 * self.expansion_factor) + int(self.action_timer / 1200))
        self.military_target = max(3, int(self.resource_count * 1.5 * self.expansion_factor))
        self.power_target = max(2, int((self.resource_target + self.military_target) * 0.4 * self.expansion_factor))
        self.defense_target = max(2, int(self.total_buildings * 0.15 * self.expansion_factor))

        enemy_hq = min(
            (b for b in enemy_buildings if b.unit_type == "Headquarters" and b.health > 0),
            key=lambda b: self.hq.distance_to(b.position),
            default=None
        )
        if enemy_hq:
            self.known_enemy_pos = enemy_hq.position

        inf_prio = 0.5 if self.threat_level > 0.5 else 0.6
        gren_prio = 0.3 if self.threat_level > 0.5 else 0.2
        rocket_prio = 0.1 if self.economy_level >= 1 else 0.0
        tank_prio = 0.15 if self.economy_level >= 1 else 0.05
        mgv_prio = 0.05 if self.economy_level >= 2 else 0.0
        rocket_art_prio = 0.05 if self.economy_level >= 2 else 0.0
        heli_prio = 0.1 if self.economy_level >= 2 else 0.0
        total_prio = inf_prio + gren_prio + rocket_prio + tank_prio + mgv_prio + rocket_art_prio + heli_prio
        if total_prio > 0:
            inf_prio /= total_prio
            gren_prio /= total_prio
            rocket_prio /= total_prio
            tank_prio /= total_prio
            mgv_prio /= total_prio
            rocket_art_prio /= total_prio
            heli_prio /= total_prio
        self.production_priorities = {
            "Infantry": inf_prio,
            "Grenadier": gren_prio,
            "RocketSoldier": rocket_prio,
            "Tank": tank_prio,
            "MachineGunVehicle": mgv_prio,
            "RocketArtillery": rocket_art_prio,
            "AttackHelicopter": heli_prio,
        }
    
    def _get_nearest_enemy_building(self, enemy_buildings, from_pos):
        if not enemy_buildings:
            return None
        
        building_weights = {
            Headquarters: 1.0,
            Barracks: 0.8,
            WarFactory: 0.8,
            Hangar: 0.8,
            Refinery: 0.7,
            PowerPlant: 0.6,
            Turret: 0.5,
            OilDerrick: 0.4,
            ShaleFracker: 0.4,
            BlackMarket: 0.4,
        }
        
        def weighted_dist(b):
            weight = building_weights.get(type(b), 1.0)
            dist = b.distance_to(from_pos)
            return dist / weight  
        
        return min(
            (b for b in enemy_buildings if b.health > 0),
            key=weighted_dist,
            default=None
        )
    
    def _get_nearest_enemy_target(self, enemy_buildings, enemy_units, from_pos):
        if enemy_buildings:
            building_target = self._get_nearest_enemy_building(enemy_buildings, from_pos)
        else:
            building_target = None
        
        if enemy_units:
            unit_target = min((u for u in enemy_units if u.health > 0 and u.unit_type in ["Infantry", "Grenadier"]), key=lambda u: u.distance_to(from_pos), default=None)
            if not unit_target:
                unit_target = min((u for u in enemy_units if u.health > 0), key=lambda u: u.distance_to(from_pos), default=None)
        else:
            unit_target = None
        
        if building_target and unit_target:
            if building_target.distance_to(from_pos) < unit_target.distance_to(from_pos):
                return building_target
            else:
                return unit_target
        elif building_target:
            return building_target
        elif unit_target:
            return unit_target
        return None
    
    def find_build_position(self, building_cls, all_buildings, map_width, map_height, prefer_near_hq=True):
        default_area = 2560 * 1440
        map_area = map_width * map_height
        scale = math.sqrt(map_area / default_area)
        hq_pos = self.hq.position
        half_w, half_h = UNIT_CLASSES[building_cls.__name__]["size"][0] / 2, UNIT_CLASSES[building_cls.__name__]["size"][1] / 2
        max_attempts = 2000
        attempts = 0

        if building_cls.__name__ in ["PowerPlant", "Barracks", "WarFactory", "Hangar"]:
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 100, (150 + 50 * scale + 100 * self.economy_level)  
        elif building_cls.__name__ in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]:
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 120, (200 + 100 * scale + 150 * self.economy_level)  
        elif building_cls.__name__ == "Turret":
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 80, (150 + 30 * scale + 50 * self.economy_level)
        else:
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 100, (180 + 50 * scale + 100 * self.economy_level)

        if not prefer_near_hq:
            dist_min, dist_max = max(200, dist_min), 400 * scale + 200 * self.economy_level

        ring_step = 25 * scale
        num_samples_per_ring = 25
        angle_jitter = math.pi * self.build_jitter * (1.5 if self.personality == 'rusher' else 1.0)
        for ring_dist in range(int(dist_min), int(dist_max + 100), int(ring_step)):
            for _ in range(num_samples_per_ring):
                angle_offset = random.uniform(-angle_jitter, angle_jitter) + random.uniform(-0.2, 0.2)
                angle = bias_angle + angle_offset
                dist = ring_dist + random.uniform(-ring_step / 2, ring_step / 2)
                center_x = hq_pos.x + dist * math.cos(angle)
                center_y = hq_pos.y + dist * math.sin(angle)
                center_x = max(half_w, min(map_width - half_w, center_x))
                center_y = max(half_h, min(map_height - half_h, center_y))
                snapped_center = snap_to_grid((center_x, center_y))
                position = snapped_center
                if is_valid_building_position(
                    position, self.hq.team, building_cls, list(all_buildings),
                    map_width, map_height, margin=60
                ):
                    return position
                attempts += 1
                if attempts > max_attempts:
                    break
            if attempts > max_attempts:
                break
        return None
    
    def queue_unit_production(self, barracks_list, war_factory_list, hangar_list, friendly_units):
        num_units = len([u for u in friendly_units if u.health > 0])
        target_units = min(200, max(12, int(self.military_strength * 1.1) + int(self.threat_level * 15) + int(self.economy_level * 5)))  
        
        if self.economy_level < 1:
            return  
        
        if num_units < target_units:
            max_queue_light = 3 if self.economy_level < 2 else 5  
            max_queue_heavy = 2 if self.economy_level < 2 else 4
            
            if barracks_list:
                barracks = barracks_list[self.barracks_index % len(barracks_list)]
                self.barracks_index += 1
                if len(barracks.production_queue) < max_queue_light:
                    if self.threat_level > 0.5:
                        unit_type = random.choices(list(self.production_priorities.keys()), weights=[0.7, 0.2, 0.1, 0.0, 0, 0, 0])[0]
                    else:
                        unit_type = random.choices(list(self.production_priorities.keys()), weights=list(self.production_priorities.values()))[0]
                    
                    cost = UNIT_CLASSES[unit_type]["cost"]
                    if self.hq.credits >= cost:
                        barracks.production_queue.append({'unit_type': unit_type, 'repeat': False})
                        self.hq.credits -= cost
                        if random.random() < 0.4 and unit_type == "Infantry" and num_units < 10:  
                            barracks.production_queue[-1]['repeat'] = True
            
            if war_factory_list and self.economy_level > 1:
                war_factory = war_factory_list[self.warfactory_index % len(war_factory_list)]
                self.warfactory_index += 1
                if len(war_factory.production_queue) < max_queue_heavy:
                    heavy_unit = random.choice(["Tank", "MachineGunVehicle", "RocketArtillery"])
                    cost = UNIT_CLASSES[heavy_unit]["cost"]
                    if self.hq.credits >= cost and num_units < target_units * 0.7:
                        war_factory.production_queue.append({'unit_type': heavy_unit, 'repeat': False})
                        self.hq.credits -= cost
            
            if hangar_list and self.economy_level >= 2:
                hangar = hangar_list[self.hangar_index % len(hangar_list)]
                self.hangar_index += 1
                if len(hangar.production_queue) < max_queue_heavy and random.random() < 0.2:  
                    hangar.production_queue.append({'unit_type': "AttackHelicopter", 'repeat': False})
                    self.hq.credits -= UNIT_CLASSES["AttackHelicopter"]["cost"]
    
    def build_defenses(self, all_buildings, map_width, map_height):
        if self.threat_level > 0.2 and self.turret_count < self.defense_target and self.hq.credits >= UNIT_CLASSES["Turret"]["cost"]:
            pos = self.find_build_position(Turret, all_buildings, map_width, map_height, prefer_near_hq=True)
            if pos:
                self.hq.place_building(pos, Turret, all_buildings)
    
    def strategize_attacks(self, friendly_units, enemy_hq, enemy_buildings=None, enemy_units=None, map_width=MAP_WIDTH, map_height=MAP_HEIGHT):
        if not enemy_hq and not enemy_buildings and not enemy_units:
            return
        
        self.defense_timer += 1
        defense_check_interval = 3  
        defense_threshold = 0.1  
        interrupt_prob = 0.7 if self.threat_level > 0.5 else 0.3  
        
        if self.defense_timer > defense_check_interval and self.threat_level > defense_threshold and self.nearby_enemies:
            hq_pos = self.hq.position
            nearby_friends = [u for u in friendly_units if u.health > 0 and u.distance_to(hq_pos) < 800]
            if nearby_friends:
                for friend in nearby_friends:
                    should_interrupt = (friend.move_target is None) or (random.random() < interrupt_prob)
                    if should_interrupt:
                        nearest_threat = min(self.nearby_enemies, key=lambda e: friend.distance_to(e.position))
                        friend.attack_target = nearest_threat
                        friend.move_target = nearest_threat.position
                self.defense_timer = random.randint(0, defense_check_interval)
        
        self.scout_timer += 1
        scout_interval = int(20 * self.interval_multiplier)  
        if self.scout_timer > scout_interval and len(friendly_units) > 1:
            scout_target = enemy_hq.position if enemy_hq else ((self._get_nearest_enemy_building(enemy_buildings, friendly_units[0].position if friendly_units else (0, 0)).position if enemy_buildings else (0, 0)))
            scout_tx = max(0, min(scout_target[0] + random.uniform(-200, 200), map_width))
            scout_ty = max(0, min(scout_target[1] + random.uniform(-200, 200), map_height))
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None][:8]  
            for scout in idle_units:
                scout.move_target = (scout_tx, scout_ty)
            self.scout_timer = random.randint(0, scout_interval // 2)
        
        self.attack_timer += 1
        attack_interval = int(10 * self.interval_multiplier)  
        attack_fraction = (0.5 if self.threat_level > 0.5 else 0.4) * self.aggression_bias  
        if self.attack_timer > attack_interval:
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None]
            if len(idle_units) > 0:
                num_to_send = max(1, int(len(idle_units) * attack_fraction * random.uniform(0.9, 1.3)))  
                self._send_attack_group(idle_units, enemy_buildings, enemy_units, num_to_send, map_width, map_height)
            self.attack_timer = random.randint(0, attack_interval // 2)
        
        push_threshold = 0.5 * self.aggression_bias  
        if self.military_strength > self.enemy_strength * push_threshold:
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None]
            if len(idle_units) > 3:
                attack_fraction = (0.9 if self.threat_level > 0.5 else 0.7) * self.aggression_bias  
                num_to_send = int(len(idle_units) * attack_fraction)
                self._send_attack_group(idle_units, enemy_buildings, enemy_units, num_to_send, map_width, map_height)
        
        self.patrol_timer += 1
        patrol_interval = int(60 * self.interval_multiplier)  
        if self.patrol_timer > patrol_interval:
            idle_in_base = [u for u in friendly_units if u.health > 0 and u.move_target is None and u.distance_to(self.hq.position) < 300]
            if idle_in_base:
                num_patrol = min(8, len(idle_in_base))  
                patrol_target = (enemy_hq.position if enemy_hq else self.known_enemy_pos)
                if patrol_target:
                    patrol_tx = max(0, min(patrol_target[0] + random.uniform(-300, 300), map_width))
                    patrol_ty = max(0, min(patrol_target[1] + random.uniform(-300, 300), map_height))
                else:
                    patrol_tx = random.uniform(0, map_width)
                    patrol_ty = random.uniform(0, map_height)
                for unit in idle_in_base[:num_patrol]:
                    unit.move_target = (patrol_tx, patrol_ty)
            self.patrol_timer = random.randint(0, patrol_interval // 2)
    
    def update(self, friendly_units, friendly_buildings, enemy_units, enemy_buildings, all_buildings, map_width=MAP_WIDTH, map_height=MAP_HEIGHT):
        self.assess_situation(friendly_units, friendly_buildings, enemy_units, enemy_buildings)
        self.action_timer += 1
        
        effective_timer = (self.action_timer + self.timer_offset) * self.interval_multiplier
        
        if int(effective_timer) % int(60 * self.interval_multiplier) == 0:
            barracks_list = [b for b in friendly_buildings if b.unit_type == "Barracks" and b.health > 0]
            war_factory_list = [b for b in friendly_buildings if b.unit_type == "WarFactory" and b.health > 0]
            hangar_list = [b for b in friendly_buildings if b.unit_type == "Hangar" and b.health > 0]
            self.queue_unit_production(barracks_list, war_factory_list, hangar_list, friendly_units)
        
        if int(effective_timer) % 120 == 0:
            enemy_hq = min(
                (b for b in enemy_buildings if b.unit_type == "Headquarters" and b.health > 0),
                key=lambda b: self.hq.distance_to(b.position),
                default=None
            )
            enemy_pos = enemy_hq.position if enemy_hq else self.known_enemy_pos
            self.update_rally_points(friendly_buildings, enemy_pos, map_width, map_height)
        
        economy_check_interval = int(60 * self.interval_multiplier)  
        if int(effective_timer) % economy_check_interval == 0 and self.hq.credits >= 300:
            
            priorities = []
            if self.resource_count < self.resource_target:
                priorities.append('resource')
            if self.power_count < self.power_target:
                priorities.append('power')
            if self.military_prod_count < self.military_target:
                priorities.append('military')
            if self.turret_count < self.defense_target:
                priorities.append('defense')
            
            if priorities:
                priority_type = random.choice(priorities)
            else:
                
                rand = random.random()
                if rand < 0.4:
                    priority_type = 'resource'
                elif rand < 0.7:
                    priority_type = 'military'
                elif rand < 0.85:
                    priority_type = 'power'
                else:
                    priority_type = 'defense'
            
            cls = None
            if priority_type == 'resource':
                
                if self.resource_count == 0:
                    cls = OilDerrick
                elif len([b for b in friendly_buildings if b.unit_type == "Refinery"]) < 2:
                    cls = Refinery
                else:
                    cls = random.choice([ShaleFracker, BlackMarket, OilDerrick])  
            elif priority_type == 'power':
                cls = PowerPlant
            elif priority_type == 'military':
                
                built_barracks = len([b for b in friendly_buildings if b.unit_type == "Barracks"])
                built_factory = len([b for b in friendly_buildings if b.unit_type == "WarFactory"])
                built_hangar = len([b for b in friendly_buildings if b.unit_type == "Hangar"])
                if built_barracks < max(2, self.resource_count // 3):
                    cls = Barracks
                elif built_factory < max(1, self.resource_count // 4):
                    cls = WarFactory
                elif built_hangar < max(1, self.resource_count // 5):
                    cls = Hangar
                else:
                    
                    if built_barracks < self.military_target * 0.4:
                        cls = Barracks
                    elif built_factory < self.military_target * 0.3:
                        cls = WarFactory
                    else:
                        cls = Hangar
            elif priority_type == 'defense':
                cls = Turret
            
            if cls:
                cost = UNIT_CLASSES[cls.__name__]["cost"]
                if self.hq.credits >= cost:
                    
                    prefer_near = random.random() > 0.2 or self.total_buildings < 10
                    pos = self.find_build_position(cls, all_buildings, map_width, map_height, prefer_near_hq=prefer_near)
                    if pos:
                        self.hq.place_building(pos, cls, all_buildings)
        
        self.build_defenses(all_buildings, map_width, map_height)  
        
        enemy_hq = min(
            (b for b in enemy_buildings if b.unit_type == "Headquarters" and b.health > 0),
            key=lambda b: self.hq.distance_to(b.position),
            default=None
        )
        self.strategize_attacks(friendly_units, enemy_hq, enemy_buildings, enemy_units, map_width, map_height)

@dataclass(kw_only=True)
class ProductionInterface:
    WIDTH: ClassVar = 200
    MARGIN_X: ClassVar = 20
    CREDITS_POS_Y: ClassVar = 10
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
    str_to_building_class: dict = dataclass_field(default_factory=lambda: {
        "Barracks": Barracks,
        "WarFactory": WarFactory,
        "Hangar": Hangar,
        "PowerPlant": PowerPlant,
        "Turret": Turret,
        "OilDerrick": OilDerrick,
        "Refinery": Refinery,
        "ShaleFracker": ShaleFracker,
        "BlackMarket": BlackMarket,
    })
    
    def __post_init__(self, all_buildings):
        self.placing_cls = None
        self.surface = pg.Surface((self.WIDTH, SCREEN_HEIGHT - CONSOLE_HEIGHT))
        self.producer = self.hq
        self._create_top_buttons()
        self.unit_button_labels = {
            "Infantry": "Infantry",
            "Grenadier": "Grenadier",
            "RocketSoldier": "Rocket Soldier",
            "Tank": "Tank",
            "MachineGunVehicle": "MG Vehicle",
            "RocketArtillery": "Rocket Artillery",
            "AttackHelicopter": "Attack Heli",
            "Barracks": "Barracks",
            "WarFactory": "War Factory",
            "Hangar": "Hangar",
            "PowerPlant": "Power Plant",
            "Turret": "Turret",
            "OilDerrick": "Oil Derrick",
            "Refinery": "Refinery",
            "ShaleFracker": "Shale Fracker",
            "BlackMarket": "Black Market",
        }
        self.update_producer(self.hq)
    
    def _create_top_buttons(self):
        self.top_rects.clear()
        start_x = self.MARGIN_X
        for i, label in enumerate(['Repair', 'Sell', 'Map']):
            x = start_x + i * (self.TOP_BUTTON_WIDTH + self.TOP_BUTTON_SPACING)
            rect = pg.Rect(x, self.TOP_BUTTONS_POS_Y, self.TOP_BUTTON_WIDTH, self.TOP_BUTTON_HEIGHT)
            self.top_rects[label] = rect
    
    def update_producer(self, selected_building):
        if isinstance(selected_building, (Barracks, WarFactory, Hangar)):
            self.producer = selected_building
            if isinstance(selected_building, Barracks):
                self.producible_items = ["Infantry", "Grenadier", "RocketSoldier"]
            elif isinstance(selected_building, WarFactory):
                self.producible_items = ["Tank", "MachineGunVehicle", "RocketArtillery"]
            elif isinstance(selected_building, Hangar):
                self.producible_items = ["AttackHelicopter"]
        else:
            self.producer = self.hq
            self.producible_items = ["Barracks", "WarFactory", "Hangar", "PowerPlant", "Turret", "OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]
        self.item_rects = {}
        y = self.PROD_ITEMS_START_Y
        for i, item in enumerate(self.producible_items):
            rect = pg.Rect(self.MARGIN_X, y + i * self.ITEM_HEIGHT, self._BUTTON_WIDTH, self.ITEM_BUTTON_HEIGHT)
            self.item_rects[item] = rect
    
    def draw(self, surface_: pg.Surface, own_buildings, all_buildings):
        self.surface.fill(self.FILL_COLOR)
        pg.draw.rect(self.surface, self.LINE_COLOR, self.surface.get_rect(), width=2)
        
        self.surface.blit(
            self.font.render(f"Credits: ${self.hq.credits}", True, pg.Color("white")),
            (self.MARGIN_X, self.CREDITS_POS_Y),
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
        
        for label, rect in self.top_rects.items():
            color = self.INACTIVE_TAB_COLOR
            pg.draw.rect(self.surface, color, rect, border_radius=self.BUTTON_RADIUS)
            pg.draw.rect(self.surface, self.LINE_COLOR, rect, 1)
            text_surf = self.font.render(label, True, pg.Color("white"))
            text_rect = text_surf.get_rect(center=rect.center)
            self.surface.blit(text_surf, text_rect)
        
        for item, rect in self.item_rects.items():
            cost = UNIT_CLASSES[item]["cost"]
            label = self.unit_button_labels[item]
            can_produce = self.hq.credits >= cost
            color = self.ACTION_ALLOWED_COLOR if can_produce else self.ACTION_BLOCKED_COLOR
            pg.draw.rect(self.surface, color, rect, border_radius=self.BUTTON_RADIUS)
            label_surf = self.font.render(label, True, pg.Color("white"))
            label_rect = label_surf.get_rect(x=rect.x + 5, y=rect.y + 5)
            self.surface.blit(label_surf, label_rect)
            cost_surf = self.font.render(f"({cost})", True, pg.Color("white"))
            cost_rect = cost_surf.get_rect(x=rect.x + 5, y=rect.y + 25)
            self.surface.blit(cost_surf, cost_rect)
        
        if hasattr(self.producer, 'production_queue') and self.producer.production_queue:
            queue_y = self.PRODUCTION_QUEUE_POS_Y
            self.surface.blit(
                self.font.render("Queue:", True, pg.Color("white")),
                (self.MARGIN_X, queue_y),
            )
            queue_y += 20
            for i, item in enumerate(self.producer.production_queue):
                unit_type = item['unit_type'] if 'unit_type' in item else item['cls'].__name__
                repeat_text = " [R]" if item['repeat'] else ""
                text = f"{self.unit_button_labels.get(unit_type, unit_type)}{repeat_text}"
                self.surface.blit(
                    self.font.render(text, True, pg.Color("white")),
                    (self.MARGIN_X + 10, queue_y),
                )
                repeat_rect = pg.Rect(self.MARGIN_X + 150, queue_y, 20, 20)
                repeat_color = self.ACTION_ALLOWED_COLOR if item['repeat'] else self.INACTIVE_TAB_COLOR
                pg.draw.rect(self.surface, repeat_color, repeat_rect, border_radius=2)
                if item['repeat']:
                    self.surface.blit(
                        self.font.render("R", True, pg.Color("white")),
                        (repeat_rect.x + 6, repeat_rect.y + 3),
                    )
                if i == 0 and self.producer.production_timer is not None:
                    progress = 1 - (self.producer.production_timer / 90.0) if 'Hangar' in str(type(self.producer)) else 1 - (self.producer.production_timer / 60.0)
                    bar_width = 100 * progress
                    pg.draw.rect(self.surface, self.ACTION_ALLOWED_COLOR, (self.MARGIN_X + 10, queue_y + 20, bar_width, 5))
                    pg.draw.rect(self.surface, self.LINE_COLOR, (self.MARGIN_X + 10, queue_y + 20, 100, 5), 1)
                queue_y += 25
        
        surface_.blit(self.surface, (SCREEN_WIDTH - self.WIDTH, 0))
    
    def handle_click(self, screen_pos, own_buildings):
        local_pos = (screen_pos[0] - (SCREEN_WIDTH - self.WIDTH), screen_pos[1])
        
        for label, rect in self.top_rects.items():
            if rect.collidepoint(local_pos):
                if label == 'Repair':
                    if self.producer != self.hq:
                        missing = self.producer.max_health - self.producer.health
                        if missing > 0:
                            cost = missing * 1
                            if self.hq.credits >= cost:
                                self.hq.credits -= cost
                                self.producer.health = self.producer.max_health
                elif label == 'Sell':
                    if self.producer != self.hq:
                        return ('sell', self.producer)
                elif label == 'Map':
                    pass
                return True
        
        for item, rect in self.item_rects.items():
            if rect.collidepoint(local_pos):
                cost = UNIT_CLASSES[item]["cost"]
                if self.hq.credits >= cost:
                    if isinstance(self.producer, Headquarters):
                        self.placing_cls = self.str_to_building_class[item]
                    else:
                        if len(self.producer.production_queue) < self.MAX_PRODUCTION_QUEUE_LENGTH:
                            self.producer.production_queue.append({'unit_type': item, 'repeat': False})
                            self.hq.credits -= cost
                        return True
                return False
        return False

def get_iso_bounds(map_w: int, map_h: int, zoom: float = 1.0) -> tuple[float, float, float, float]:
    corners = [(0, 0), (map_w, 0), (map_w, map_h), (0, map_h)]
    isos = [absolute_world_to_iso(c, zoom) for c in corners]
    min_x = min(ix for ix, iy in isos)
    max_x = max(ix for ix, iy in isos)
    min_y = min(iy for ix, iy in isos)
    max_y = max(iy for ix, iy in isos)
    return min_x, max_x, min_y, max_y

def draw_mini_map(screen: pg.Surface, camera: Camera, fog_of_war: FogOfWar, map_width: int, map_height: int, map_color: tuple, buildings, all_units, player_allies: Set[Team]):
    mini_map_rect = pg.Rect(SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT, MINI_MAP_WIDTH, MINI_MAP_HEIGHT)
    mini_map = pg.Surface((MINI_MAP_WIDTH, MINI_MAP_HEIGHT))
    mini_map.fill((0, 0, 0))
    
    min_x1, max_x1, min_y1, max_y1 = get_iso_bounds(map_width, map_height, 1.0)
    span_x1 = max_x1 - min_x1
    span_y1 = max_y1 - min_y1
    mini_zoom = min(MINI_MAP_WIDTH / span_x1, MINI_MAP_HEIGHT / span_y1)
    
    center_offset_x = (MINI_MAP_WIDTH - span_x1 * mini_zoom) / 2
    center_offset_y = (MINI_MAP_HEIGHT - span_y1 * mini_zoom) / 2
    draw_offset_x = center_offset_x - min_x1 * mini_zoom
    draw_offset_y = center_offset_y - min_y1 * mini_zoom
    
    tile_size_world = TILE_SIZE
    num_tx = map_width // tile_size_world
    num_ty = map_height // tile_size_world
    
    base_r, base_g, base_b = map_color
    
    for tx in range(num_tx):
        for ty in range(num_ty):
            tile_center_x = (tx + 0.5) * tile_size_world
            tile_center_y = (ty + 0.5) * tile_size_world
            if not fog_of_war.is_explored((tile_center_x, tile_center_y)):
                continue
            
            c1 = (tx * tile_size_world, ty * tile_size_world)
            c2 = (c1[0] + tile_size_world, c1[1])
            c3 = (c2[0], c2[1] + tile_size_world)
            c4 = (c1[0], c3[1])
            
            iso_c1 = absolute_world_to_iso(c1, mini_zoom)
            iso_c2 = absolute_world_to_iso(c2, mini_zoom)
            iso_c3 = absolute_world_to_iso(c3, mini_zoom)
            iso_c4 = absolute_world_to_iso(c4, mini_zoom)
            
            draw_points = [
                (iso_c1[0] + draw_offset_x, iso_c1[1] + draw_offset_y),
                (iso_c2[0] + draw_offset_x, iso_c2[1] + draw_offset_y),
                (iso_c3[0] + draw_offset_x, iso_c3[1] + draw_offset_y),
                (iso_c4[0] + draw_offset_x, iso_c4[1] + draw_offset_y),
            ]
            
            var_r = ((tx * 17 + ty * 31) % 41) - 20
            var_g = ((tx * 23 + ty * 37) % 41) - 20
            var_b = ((tx * 29 + ty * 41) % 41) - 20
            tile_r = max(0, min(255, base_r + var_r))
            tile_g = max(0, min(255, base_g + var_g))
            tile_b = max(0, min(255, base_b + var_b))
            
            if not fog_of_war.is_visible((tile_center_x, tile_center_y)):
                avg = (tile_r + tile_g + tile_b) // 3
                tile_r = tile_g = tile_b = avg
            
            pg.draw.polygon(mini_map, (tile_r, tile_g, tile_b), draw_points)
    
    for building in buildings:
        if building.health > 0 and (building.team in player_allies or building.is_seen) and fog_of_war.is_explored(building.position):
            iso_pos = absolute_world_to_iso(building.position, mini_zoom)
            draw_pos = (iso_pos[0] + draw_offset_x, iso_pos[1] + draw_offset_y)
            size = 3
            color = team_to_color[building.team]
            pg.draw.rect(mini_map, color, (draw_pos[0] - size, draw_pos[1] - size, size * 2, size * 2))
    
    for unit in all_units:
        if unit.health > 0 and (unit.team in player_allies or fog_of_war.is_visible(unit.position)):
            iso_pos = absolute_world_to_iso(unit.position, mini_zoom)
            draw_pos = (iso_pos[0] + draw_offset_x, iso_pos[1] + draw_offset_y)
            color = team_to_color[unit.team]
            pg.draw.circle(mini_map, color, (int(draw_pos[0]), int(draw_pos[1])), 1)
    
    cam_world_tl = (camera.rect.x, camera.rect.y)
    cam_world_br = (camera.rect.right, camera.rect.bottom)
    cam_corners = [cam_world_tl, (cam_world_br[0], cam_world_tl[1]), cam_world_br, (cam_world_tl[0], cam_world_br[1])]
    iso_cams = [absolute_world_to_iso(c, mini_zoom) for c in cam_corners]
    cam_draw_points = [(ix + draw_offset_x, iy + draw_offset_y) for ix, iy in iso_cams]
    pg.draw.polygon(mini_map, (255, 255, 255), cam_draw_points, 1)
    
    screen.blit(mini_map, (SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT))
    return mini_map_rect

def draw_fitness_panel(screen: pg.Surface, g):
    panel_x = 10
    panel_y = 10
    panel_width = 180
    panel_height = 250
    panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)
    panel_surf = pg.Surface((panel_width, panel_height), pg.SRCALPHA)
    panel_surf.fill((40, 40, 40, 128))
    screen.blit(panel_surf, panel_rect.topleft)
    pg.draw.rect(screen, (100, 100, 100), panel_rect, 2)
    
    font = g["font"]
    y_offset = panel_y + 10
    title_surf = font.render("Fitness", True, (255, 255, 255))
    screen.blit(title_surf, (panel_x + 10, y_offset))
    y_offset += 30
    
    for team in g["teams"]:
        hq = g["hqs"][team]
        if hq.health <= 0:
            continue
        
        name = team_to_name[team]
        fitness = g["current_fitness"].get(team, 0)
        delta = g["fitness_deltas"].get(team, 0)
        
        name_surf = font.render(f"{name}:", True, team_to_color[team])
        screen.blit(name_surf, (panel_x + 10, y_offset))
        
        value_surf = font.render(str(fitness), True, (255, 255, 255))
        screen.blit(value_surf, (panel_x + 120, y_offset))
        
        if delta != 0:
            delta_text = f"{ '+' if delta > 0 else ''}{delta}"
            delta_color = (0, 255, 0) if delta > 0 else (255, 0, 0)
            delta_surf = font.render(delta_text, True, delta_color)
            screen.blit(delta_surf, (panel_x + 140, y_offset))
        
        y_offset += 25

def handle_unit_collisions(all_units: list, unit_hash: SpatialHash):
    for i, unit in enumerate(all_units):
        if unit.health <= 0 or unit.air:
            continue
        nearby = unit_hash.query(unit.position, max(unit.rect.width, unit.rect.height))
        for other in nearby:
            if other is unit or other.health <= 0 or other.air or id(other) <= id(unit):
                continue
            if unit.rect.colliderect(other.rect):
                dx = other.position.x - unit.position.x
                dy = other.position.y - unit.position.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    r1 = max(unit.rect.width, unit.rect.height) / 2
                    r2 = max(other.rect.width, other.rect.height) / 2
                    overlap = max(0, r1 + r2 - dist)
                    if overlap > 0:
                        push = overlap * 0.5
                        direction_x = dx / dist
                        direction_y = dy / dist
                        unit.position.x -= direction_x * push
                        unit.position.y -= direction_y * push
                        other.position.x += direction_x * push
                        other.position.y += direction_y * push

def handle_unit_building_collisions(all_units: list, all_buildings: list, building_hash: SpatialHash):
    for unit in [u for u in all_units if u.health > 0 and not u.air]:
        nearby_builds = building_hash.query(unit.position, max(unit.rect.width, unit.rect.height) + 50)
        for building in [b for b in nearby_builds if b.health > 0]:
            if unit.rect.colliderect(building.rect):
                dx = building.position.x - unit.position.x
                dy = building.position.y - unit.position.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    r1 = max(unit.rect.width, unit.rect.height) / 2
                    r2 = max(building.rect.width, building.rect.height) / 2
                    overlap = max(0, r1 + r2 - dist)
                    if overlap > 0:
                        direction_x = dx / dist
                        direction_y = dy / dist
                        unit.position.x -= direction_x * overlap
                        unit.position.y -= direction_y * overlap

def handle_attacks(team: Team, all_units: list, all_buildings: list, projectiles, particles, unit_hash: SpatialHash, building_hash: SpatialHash, alliances: Dict[Team, Set[Team]]):
    unit_allies = alliances[team]
    armed_entities = []
    for u in all_units:
        if u.team == team and hasattr(u, 'weapons') and u.weapons and u.health > 0:
            armed_entities.append(u)
    for b in all_buildings:
        if b.team == team and hasattr(b, 'weapons') and b.weapons and b.health > 0:
            armed_entities.append(b)
    for entity in armed_entities:
        if entity.last_shot_time != 0:
            continue
        closest_unit_in_range = None
        min_unit_dist_in_range = float("inf")
        closest_building_in_range = None
        min_building_dist_in_range = float("inf")
        closest_overall = None
        min_overall_dist = float("inf")
        candidates = unit_hash.query(entity.position, entity.sight_range) + building_hash.query(entity.position, entity.sight_range)
        for obj in candidates:
            if hasattr(obj, 'team') and obj.team not in unit_allies and hasattr(obj, 'health') and obj.health > 0:
                if obj.is_building:
                    closest_pt = entity._closest_point_on_rect(obj.rect, entity.position)
                    dist = Vector2(closest_pt).distance_to(entity.position)
                else:
                    dist = entity.distance_to(obj.position)
                if dist <= entity.sight_range:
                    if dist < min_overall_dist:
                        closest_overall, min_overall_dist = obj, dist
                    
                    if dist <= entity.attack_range:
                        if not obj.is_building:
                            if dist < min_unit_dist_in_range:
                                closest_unit_in_range, min_unit_dist_in_range = obj, dist
                        else:
                            if dist < min_building_dist_in_range:
                                closest_building_in_range, min_building_dist_in_range = obj, dist
        
        if closest_unit_in_range:
            closest_target = closest_unit_in_range
        elif closest_building_in_range:
            closest_target = closest_building_in_range
        elif closest_overall:
            closest_target = closest_overall
        else:
            closest_target = None
        
        if closest_target:
            entity.attack_target = closest_target
            if closest_target.is_building:
                closest_pt = entity._closest_point_on_rect(closest_target.rect, entity.position)
                dir_c = Vector2(closest_pt) - entity.position
                dist_to_target = dir_c.length()
            else:
                dist_to_target = entity.distance_to(closest_target.position)
            if dist_to_target <= entity.attack_range:
                entity.shoot(closest_target, projectiles)
            else:
                if not entity.is_building:
                    if closest_target.is_building:
                        chase_pos = entity.get_chase_position_for_building(closest_target)
                        entity.move_target = chase_pos if chase_pos is not None else None
                    else:
                        entity.move_target = closest_target.position

def handle_projectiles(projectiles, all_units, all_buildings, particles, g):
    for projectile in list(projectiles):
        proj_allies = g["alliances"][projectile.team]
        enemy_units = [u for u in all_units if u.team not in proj_allies and u.health > 0]
        enemy_buildings = [b for b in all_buildings if b.team not in proj_allies and b.health > 0]
        
        hit = False
        for e in enemy_units + enemy_buildings:
            if check_collision(e, projectile):
                if e.take_damage(projectile.damage, particles):
                    create_explosion(e.position, particles, e.team)
                    attacker_hq = g["hqs"][projectile.team]
                    if hasattr(e, 'hq') and e.hq:
                        if e.is_building:
                            e.hq.stats['buildings_lost'] += 1
                            attacker_hq.stats['buildings_destroyed'] += 1
                        else:
                            e.hq.stats['units_lost'] += 1
                            attacker_hq.stats['units_destroyed'] += 1
                    if e in all_units:
                        all_units.remove(e)
                        if isinstance(e, Unit):
                            for team, ug in g["unit_groups"].items():
                                if e in ug:
                                    ug.remove(e)
                    elif e in all_buildings:
                        all_buildings.remove(e)
                hit = True
                break
        if hit:
            projectile.kill()

def cleanup_dead_entities(g):
    for group_name in ["global_units"]:
        group = g[group_name]
        dead = [obj for obj in group if hasattr(obj, 'health') and obj.health <= 0]
        for d in dead:
            group.remove(d)
            if hasattr(d, 'plasma_burn_particles'):
                for p in d.plasma_burn_particles:
                    if hasattr(p, 'kill'):
                        p.kill()
                d.plasma_burn_particles = []
    
    for group_name in ["global_buildings"]:
        group = g[group_name]
        dead = [obj for obj in group if hasattr(obj, 'health') and obj.health <= 0]
        for d in dead:
            group.remove(d)
            if hasattr(d, 'plasma_burn_particles'):
                for p in d.plasma_burn_particles:
                    if hasattr(p, 'kill'):
                        p.kill()
                d.plasma_burn_particles = []
    
    for team, ug in g["unit_groups"].items():
        dead = [u for u in ug if hasattr(u, 'health') and u.health <= 0]
        for d in dead:
            ug.remove(d)
            if hasattr(d, 'plasma_burn_particles'):
                for p in d.plasma_burn_particles:
                    if hasattr(p, 'kill'):
                        p.kill()
                d.plasma_burn_particles = []

class MenuButton:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
    
    def update(self, mouse_pos):
        self.current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
    
    def draw(self, surface, font):
        pg.draw.rect(surface, self.current_color, self.rect, border_radius=10)
        text_surf = font.render(self.text, True, pg.Color("white"))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class MainMenu:
    def __init__(self, font_large, font_medium):
        self.font_large = font_large
        self.font_medium = font_medium
        self.skirmish_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 60, 200, 60, "Single Player", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
        self.quit_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 40, 200, 60, "Quit", pg.Color(150, 50, 50), pg.Color(200, 100, 100))
    
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.skirmish_btn.is_clicked(event.pos):
                return "skirmish_setup"
            if self.quit_btn.is_clicked(event.pos):
                return "quit"
        return None
    
    def update(self, mouse_pos):
        self.skirmish_btn.update(mouse_pos)
        self.quit_btn.update(mouse_pos)
    
    def draw(self, surface):
        surface.fill(pg.Color(40, 40, 40))
        title = self.font_large.render("RTS GAME", True, pg.Color(0, 255, 200))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        surface.blit(title, title_rect)
        self.skirmish_btn.draw(surface, self.font_medium)
        self.quit_btn.draw(surface, self.font_medium)

class SkirmishSetup:
    def __init__(self, font_large, font_medium):
        self.font_large = font_large
        self.font_medium = font_medium
        self.game_mode = None
        self.size_choice = None
        self.map_choice = None
        
        self.mode_1v1 = MenuButton(SCREEN_WIDTH // 2 - 300, 150, 80, 50, "1v1", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.mode_2v2 = MenuButton(SCREEN_WIDTH // 2 - 200, 150, 80, 50, "2v2", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.mode_3v3 = MenuButton(SCREEN_WIDTH // 2 - 100, 150, 80, 50, "3v3", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.mode_4v4 = MenuButton(SCREEN_WIDTH // 2, 150, 80, 50, "4v4", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.mode_4ffa = MenuButton(SCREEN_WIDTH // 2 + 100, 150, 80, 50, "4FFA", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        
        self.size_tiny = MenuButton(200, 220, 120, 50, "Tiny", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_small = MenuButton(350, 220, 120, 50, "Small", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_medium = MenuButton(500, 220, 120, 50, "Medium", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_large = MenuButton(650, 220, 120, 50, "Large", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        self.size_huge = MenuButton(800, 220, 120, 50, "Huge", pg.Color(50, 100, 150), pg.Color(100, 150, 200))
        
        self.map_buttons = {}
        map_list = list(MAPS.keys())
        for i, map_name in enumerate(map_list):
            x = 100 + (i % 2) * 300
            y = 350 + (i // 2) * 80
            self.map_buttons[map_name] = MenuButton(x, y, 200, 60, map_name, pg.Color(100, 100, 100), pg.Color(150, 150, 150))
        
        self.start_btn = MenuButton(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT - 100, 160, 50, "Start Game", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
        self.spectate_btn = MenuButton(SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT - 100, 160, 50, "Spectate", pg.Color(100, 50, 150), pg.Color(150, 100, 200))
        self.back_btn = MenuButton(20, SCREEN_HEIGHT - 70, 120, 50, "Back", pg.Color(150, 100, 50), pg.Color(200, 150, 100))
    
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.mode_1v1.is_clicked(event.pos):
                self.game_mode = "1v1"
            elif self.mode_2v2.is_clicked(event.pos):
                self.game_mode = "2v2"
            elif self.mode_3v3.is_clicked(event.pos):
                self.game_mode = "3v3"
            elif self.mode_4v4.is_clicked(event.pos):
                self.game_mode = "4v4"
            elif self.mode_4ffa.is_clicked(event.pos):
                self.game_mode = "4ffa"
            
            if self.size_tiny.is_clicked(event.pos):
                self.size_choice = "tiny"
            elif self.size_small.is_clicked(event.pos):
                self.size_choice = "small"
            elif self.size_medium.is_clicked(event.pos):
                self.size_choice = "medium"
            elif self.size_large.is_clicked(event.pos):
                self.size_choice = "large"
            elif self.size_huge.is_clicked(event.pos):
                self.size_choice = "huge"
            
            for map_name, btn in self.map_buttons.items():
                if btn.is_clicked(event.pos):
                    self.map_choice = map_name
            
            if self.start_btn.is_clicked(event.pos) and self.game_mode and self.size_choice and self.map_choice:
                return ("start_game", self.game_mode, self.size_choice, self.map_choice, False)
            
            if self.spectate_btn.is_clicked(event.pos) and self.game_mode and self.size_choice and self.map_choice:
                return ("start_game", self.game_mode, self.size_choice, self.map_choice, True)
            
            if self.back_btn.is_clicked(event.pos):
                return "menu"
        
        return None
    
    def update(self, mouse_pos):
        self.mode_1v1.update(mouse_pos)
        self.mode_2v2.update(mouse_pos)
        self.mode_3v3.update(mouse_pos)
        self.mode_4v4.update(mouse_pos)
        self.mode_4ffa.update(mouse_pos)
        self.size_tiny.update(mouse_pos)
        self.size_small.update(mouse_pos)
        self.size_medium.update(mouse_pos)
        self.size_large.update(mouse_pos)
        self.size_huge.update(mouse_pos)
        for btn in self.map_buttons.values():
            btn.update(mouse_pos)
        self.start_btn.update(mouse_pos)
        self.spectate_btn.update(mouse_pos)
        self.back_btn.update(mouse_pos)
    
    def draw(self, surface):
        surface.fill(pg.Color(40, 40, 40))
        
        title = self.font_large.render("Skirmish Setup", True, pg.Color(0, 255, 200))
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 40))
        surface.blit(title, title_rect)
        
        mode_label = self.font_medium.render("Select Game Mode:", True, pg.Color(200, 200, 200))
        surface.blit(mode_label, (50, 120))
        self.mode_1v1.draw(surface, self.font_medium)
        self.mode_2v2.draw(surface, self.font_medium)
        self.mode_3v3.draw(surface, self.font_medium)
        self.mode_4v4.draw(surface, self.font_medium)
        self.mode_4ffa.draw(surface, self.font_medium)
        
        if self.game_mode:
            mode_text = self.font_medium.render(f"Selected: {self.game_mode}", True, pg.Color(100, 255, 100))
            surface.blit(mode_text, (SCREEN_WIDTH - 250, 160))
        
        size_label = self.font_medium.render("Select Size:", True, pg.Color(200, 200, 200))
        surface.blit(size_label, (50, 190))
        self.size_tiny.draw(surface, self.font_medium)
        self.size_small.draw(surface, self.font_medium)
        self.size_medium.draw(surface, self.font_medium)
        self.size_large.draw(surface, self.font_medium)
        self.size_huge.draw(surface, self.font_medium)
        
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
        self.spectate_btn.draw(surface, self.font_medium)
        self.back_btn.draw(surface, self.font_medium)

class VictoryScreen:
    def __init__(self, font_large, font_medium, is_victory: bool | None, all_stats: dict, player_team=None):
        self.font_large = font_large
        self.font_medium = font_medium
        self.is_victory = is_victory
        self.all_stats = all_stats
        self.player_team = player_team
        self.continue_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 300, 200, 60, "Continue", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
        
        self.table_x = 100
        self.table_y = 250
        self.table_width = 800
        self.col_widths = [100] * 8
        self.row_height = 30
        self.num_rows = len(all_stats) + 1
        self.table_height = self.num_rows * self.row_height
        self.line_color = pg.Color(255, 255, 255)
        self.header_color = pg.Color(100, 100, 100)
        self.row_color_even = pg.Color(40, 40, 40)
        self.row_color_odd = pg.Color(60, 60, 60)
    
    def get_team_enum(self, name):
        for t, n in team_to_name.items():
            if n == name:
                return t
        return None
    
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.continue_btn.is_clicked(event.pos):
                return "menu"
        return None
    
    def update(self, mouse_pos):
        self.continue_btn.update(mouse_pos)
    
    def draw(self, surface):
        surface.fill(pg.Color(20, 20, 20))
        
        if self.is_victory is None:
            title_text = "MATCH ENDED"
            title_color = pg.Color(0, 255, 200)
            message_text = "All HQs have been destroyed."
            message_color = pg.Color(200, 200, 200)
        elif self.is_victory:
            title_text = "VICTORY!"
            title_color = pg.Color(0, 255, 100)
            message_text = "All enemies defeated!"
            message_color = pg.Color(100, 255, 150)
        else:
            title_text = "DEFEAT!"
            title_color = pg.Color(255, 50, 50)
            message_text = "Your HQ was destroyed!"
            message_color = pg.Color(255, 100, 100)
        
        title = self.font_large.render(title_text, True, title_color)
        message = self.font_medium.render(message_text, True, message_color)
        
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        msg_rect = message.get_rect(center=(SCREEN_WIDTH // 2, 200))
        
        surface.blit(title, title_rect)
        surface.blit(message, msg_rect)
        
        if self.all_stats:
            for i in range(self.num_rows + 1):
                y = self.table_y + i * self.row_height
                pg.draw.line(surface, self.line_color, (self.table_x, y), (self.table_x + self.table_width, y), 2)
            
            x_pos = self.table_x
            for width in self.col_widths:
                pg.draw.line(surface, self.line_color, (x_pos, self.table_y), (x_pos, self.table_y + self.table_height), 2)
                x_pos += width
            
            headers = ["Player", "Produced", "Killed", "Casualties", "Built", "Raized", "Raized by", "Economy"]
            x_pos = self.table_x
            for i, header in enumerate(headers):
                text_surf = self.font_medium.render(header, True, pg.Color("white"))
                text_rect = text_surf.get_rect(center=(x_pos + self.col_widths[i] // 2, self.table_y + self.row_height // 2))
                pg.draw.rect(surface, self.header_color, (x_pos, self.table_y, self.col_widths[i], self.row_height))
                surface.blit(text_surf, text_rect)
                x_pos += self.col_widths[i]
            
            sorted_stats = sorted(self.all_stats.items(), key=lambda item: item[0])
            x_pos = self.table_x
            for row_idx, (team_name, stats) in enumerate(sorted_stats):
                row_y = self.table_y + (row_idx + 1) * self.row_height
                row_color = self.row_color_even if row_idx % 2 == 0 else self.row_color_odd
                pg.draw.rect(surface, row_color, (self.table_x, row_y, self.table_width, self.row_height))
                
                team_enum = self.get_team_enum(team_name)
                team_color = team_to_color[team_enum] if team_enum else pg.Color(255, 255, 255)
                
                values = [
                    team_name,
                    str(stats.get('units_created', 0)),
                    str(stats.get('units_destroyed', 0)),
                    str(stats.get('units_lost', 0)),
                    str(stats.get('buildings_constructed', 0)),
                    str(stats.get('buildings_destroyed', 0)),
                    str(stats.get('buildings_lost', 0)),
                    f"${stats.get('credits_earned', 0):,}"
                ]
                
                for col_idx, value in enumerate(values):
                    color = team_color if col_idx == 0 else pg.Color(255, 255, 255)
                    text_surf = self.font_medium.render(value, True, color)
                    text_rect = text_surf.get_rect(center=(x_pos + self.col_widths[col_idx] // 2, row_y + self.row_height // 2))
                    surface.blit(text_surf, text_rect)
                    x_pos += self.col_widths[col_idx]
                x_pos = self.table_x
        
        self.continue_btn.draw(surface, self.font_medium)

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
    
    def initialize_game(self, game_mode, size_name, map_name, spectate=False):
        map_data = MAPS[map_name]
        base_width = map_data["width"]
        base_height = map_data["height"]
        color = map_data["color"]
        
        size_scales = {
            "tiny": 0.80,
            "small": 0.80,
            "medium": 0.80,
            "large": 0.80,
            "huge": 0.80,
        }
        scale = size_scales[size_name]
        map_width = int(base_width * scale)
        map_height = int(base_height * scale)
        
        terrain_features = generate_terrain_features(map_name, map_width, map_height)
        
        player_units = pg.sprite.Group()
        ai_units = pg.sprite.Group()
        global_units = pg.sprite.Group()
        global_buildings = pg.sprite.Group()
        projectiles = pg.sprite.Group()
        particles = pg.sprite.Group()
        selected_units = pg.sprite.Group()
        
        unit_groups = {}
        hqs = {}
        teams_list = []
        player_side = []
        enemy_side = []
        
        if game_mode == "1v1":
            player_side = [Team.RED]
            enemy_side = [Team.GREEN]
            num_players = 2
        elif game_mode == "2v2":
            player_side = [Team.RED, Team.BLUE]
            enemy_side = [Team.ORANGE, Team.YELLOW]
            num_players = 4
        elif game_mode == "3v3":
            player_side = [Team.RED, Team.BLUE, Team.CYAN]
            enemy_side = [Team.MAGENTA, Team.ORANGE, Team.YELLOW]
            num_players = 6
        elif game_mode == "4v4":
            player_side = [Team.RED, Team.BLUE, Team.GREEN, Team.CYAN]
            enemy_side = [Team.MAGENTA, Team.ORANGE, Team.YELLOW, Team.GREY]
            num_players = 8
        elif game_mode == "4ffa":
            player_side = [Team.RED]
            enemy_side = [Team.BLUE, Team.GREEN, Team.CYAN]
            num_players = 4
        
        teams_list = player_side + enemy_side
        positions = get_starting_positions(map_width, map_height, num_players)
        
        for i, team in enumerate(teams_list):
            pos = positions[i]
            hq = Headquarters(pos, team)
            hq.map_width = map_width
            hq.map_height = map_height
            hq.stats = {
                "units_created": 3,
                "units_lost": 0,
                "units_destroyed": 0,
                "buildings_constructed": 1,
                "buildings_lost": 0,
                "buildings_destroyed": 0,
                "credits_earned": 0,
            }
            hq.rally_point = Vector2(pos[0] + (100 if pos[0] < map_width / 2 else -100), pos[1])
            hqs[team] = hq
            units = pg.sprite.Group()
            for j in range(3):
                offset = find_free_spawn_position(pos, pos, global_buildings.sprites(), global_units.sprites(), map_width=map_width, map_height=map_height)
                unit = Infantry(offset, team, hq=hq)
                unit.map_width = map_width
                unit.map_height = map_height
                units.add(unit)
            unit_groups[team] = units
        
        if not spectate:
            player_units = unit_groups[Team.RED]
            for team in teams_list:
                if team != Team.RED:
                    ai_units.add(unit_groups[team])
        else:
            player_units = pg.sprite.Group()
            for team in teams_list:
                ai_units.add(unit_groups[team])
        
        for ug in unit_groups.values():
            global_units.add(ug)
        for hq in hqs.values():
            global_buildings.add(hq)
        
        alliances = {}
        player_side_set = set(player_side)
        enemy_side_set = set(enemy_side)
        for team in teams_list:
            if team in player_side_set:
                alliances[team] = frozenset(player_side)
            else:
                alliances[team] = frozenset(enemy_side)
        
        if not spectate:
            player_hq = hqs[Team.RED]
            player_team = Team.RED
            player_allies = alliances[player_team]
        else:
            player_hq = None
            player_team = None
            player_allies = set()
        
        ais = []
        for team in teams_list:
            if not spectate and team == Team.RED:
                continue
            i = teams_list.index(team)
            pos = positions[i]
            center_x = map_width / 2
            center_y = map_height / 2
            build_dir = math.atan2(center_y - pos[1], center_x - pos[0])
            random.seed(team.value * 12345)
            ai = AI(hqs[team], GameConsole(), build_dir=build_dir, allies=alliances[team])
            ais.append(ai)
        
        camera = Camera()
        camera.map_width = map_width
        camera.map_height = map_height
        if spectate:
            camera.rect.center = (map_width / 2, map_height / 2)
        
        interface = None
        interface_rect = None
        if not spectate:
            interface = ProductionInterface(hq=player_hq, all_buildings=global_buildings, font=self.font_medium)
            interface_rect = pg.Rect(SCREEN_WIDTH - 200, 0, 200, SCREEN_HEIGHT - CONSOLE_HEIGHT)
        else:
            interface_rect = pg.Rect(0, 0, 0, 0)  
        
        self.game_data = {
            "player_units": player_units,
            "ai_units": ai_units,
            "global_units": global_units,
            "global_buildings": global_buildings,
            "projectiles": projectiles,
            "particles": particles,
            "selected_units": selected_units,
            "unit_groups": unit_groups,
            "hqs": hqs,
            "player_hq": player_hq,
            "player_team": player_team,
            "player_allies": player_allies,
            "alliances": alliances,
            "interface": interface,
            "console": GameConsole(),
            "fog_of_war": FogOfWar(map_width, map_height, spectator=spectate),
            "camera": camera,
            "map_color": color,
            "map_width": map_width,
            "map_height": map_height,
            "game_mode": game_mode,
            "selected_building": None,
            "selecting": False,
            "select_start": None,
            "select_rect": None,
            "ais": ais,
            "font": self.font_medium,
            "interface_rect": interface_rect,
            "spectator": spectate,
            "teams": teams_list,
            "terrain_features": terrain_features,
            "previous_fitness": {team: 0 for team in teams_list},
            "current_fitness": {},
            "fitness_deltas": {},
        }
    
    def run_game(self):
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
                        g["camera"].update_zoom(event.y, mouse_pos)
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
                        if not g.get("spectator", False):
                            for unit in g["player_units"]:
                                unit.selected = False
                            g["selected_units"].empty()
                            if g["selected_building"]:
                                g["selected_building"].selected = False
                            g["selected_building"] = None
                            g["selecting"] = False
                            if g["interface"]:
                                g["interface"].update_producer(g["player_hq"])
                        continue
                    
                    if g.get("spectator", False):
                        continue
                    
                    world_pos = g["camera"].screen_to_world(mouse_pos)
                    world_pos = (max(0, min(world_pos[0], g["map_width"])), max(0, min(world_pos[1], g["map_height"])))
                    target_x, target_y = mouse_pos
                    
                    if event.button == 1:
                        own_buildings = [b for b in g["global_buildings"] if b.team == g["player_team"]]
                        result = g["interface"].handle_click(mouse_pos, own_buildings)
                        if result:
                            if isinstance(result, tuple) and result[0] == 'sell':
                                building_to_sell = result[1]
                                if building_to_sell in g["global_buildings"]:
                                    g["global_buildings"].remove(building_to_sell)
                                    g["player_hq"].credits += UNIT_CLASSES[building_to_sell.unit_type]["cost"] // 2
                                    if g["selected_building"] == building_to_sell:
                                        g["selected_building"] = None
                                        g["interface"].update_producer(g["player_hq"])
                            continue
                        
                        if g["interface"].placing_cls is not None and not g["interface_rect"].collidepoint(mouse_pos):
                            snapped = snap_to_grid(world_pos)
                            buildings_list = list(g["global_buildings"])
                            unit_type = g["interface"].placing_cls.__name__
                            cost = UNIT_CLASSES[unit_type]["cost"]
                            if g["player_hq"].credits >= cost and is_valid_building_position(
                                snapped, g["player_team"], g["interface"].placing_cls, buildings_list,
                                g["map_width"], g["map_height"]
                            ):
                                building = g["interface"].placing_cls(snapped, g["player_team"], hq=g["player_hq"])
                                building.map_width = g["map_width"]
                                building.map_height = g["map_height"]
                                g["global_buildings"].add(building)
                                g["player_hq"].credits -= cost
                                g["interface"].placing_cls = None
                            else:
                                g["interface"].placing_cls = None
                            continue
                        
                        clicked_building = next(
                            (b for b in g["global_buildings"] if b.team == g["player_team"] and g["camera"].get_screen_rect(b.rect).collidepoint(target_x, target_y)),
                            None,
                        )
                        if clicked_building:
                            if g["selected_building"] and g["selected_building"] != clicked_building:
                                g["selected_building"].selected = False
                            clicked_building.selected = True
                            g["selected_building"] = clicked_building
                            for unit in g["player_units"]:
                                unit.selected = False
                            g["selected_units"].empty()
                            g["interface"].update_producer(clicked_building)
                        else:
                            if g["selected_building"]:
                                g["selected_building"].selected = False
                            g["selected_building"] = None
                            g["interface"].update_producer(g["player_hq"])
                            g["selecting"] = True
                            g["select_start"] = mouse_pos
                            g["select_rect"] = pg.Rect(target_x, target_y, 0, 0)
                    
                    elif event.button == 3:
                        if g["interface"].placing_cls is not None:
                            g["interface"].placing_cls = None
                        elif g["selected_building"] and hasattr(g["selected_building"], 'rally_point'):
                            g["selected_building"].rally_point = Vector2(world_pos)
                        elif g["selected_units"]:
                            clicked_enemy = None
                            unit_list = list(g["global_units"])
                            building_list = [b for b in g["global_buildings"] if b.health > 0]
                            for u in unit_list:
                                screen_rect = g["camera"].get_screen_rect(u.rect)
                                if screen_rect.collidepoint(mouse_pos) and u.team not in g["player_allies"] and u.health > 0:
                                    clicked_enemy = u
                                    break
                            if not clicked_enemy:
                                for b in building_list:
                                    screen_rect = g["camera"].get_screen_rect(b.rect)
                                    if screen_rect.collidepoint(mouse_pos) and b.team not in g["player_allies"] and b.health > 0:
                                        clicked_enemy = b
                                        break
                            if clicked_enemy:
                                for unit in g["selected_units"]:
                                    unit.attack_target = clicked_enemy
                                    if clicked_enemy.is_building:
                                        chase_pos = unit.get_chase_position_for_building(clicked_enemy)
                                        unit.move_target = chase_pos if chase_pos is not None else None
                                    else:
                                        unit.move_target = clicked_enemy.position
                            else:
                                formation_positions = calculate_formation_positions(
                                    center=world_pos, target=world_pos, num_units=len(g["selected_units"])
                                )
                                for unit, pos in zip(g["selected_units"], formation_positions):
                                    unit.move_target = pos
                                    unit.attack_target = None
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
                    g["interface"].update_producer(g["player_hq"])
                    
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
                        if g["interface"] and g["interface"].placing_cls is not None:
                            g["interface"].placing_cls = None
                        else:
                            self.state = GameState.MENU
                            return
            
            g["camera"].update(g["selected_units"].sprites() if not g.get("spectator", False) else [], pg.mouse.get_pos(), g["interface_rect"], keys)
            
            unit_list = list(g["global_units"])
            building_list = [b for b in g["global_buildings"] if b.health > 0]
            
            def update_unit(unit):
                unit.update()
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(update_unit, unit) for unit in [u for u in unit_list if not u.is_building]]
                for future in futures:
                    future.result()
            
            for building in building_list:
                building_team = building.team
                friendly_units_for_build = g["unit_groups"].get(building_team, pg.sprite.Group())
                allies = g["alliances"][building_team]
                enemy_units_for_build = [u for u in g["global_units"].sprites() if u.team not in allies and u.health > 0]
                enemy_buildings_for_build = [b for b in g["global_buildings"].sprites() if b.team not in allies and b.health > 0]
                building.update(
                    particles=g["particles"],
                    friendly_units=friendly_units_for_build,
                    all_units=g["global_units"],
                    global_buildings=g["global_buildings"],
                    projectiles=g["projectiles"],
                    enemy_units=enemy_units_for_build,
                    enemy_buildings=enemy_buildings_for_build
                )
            
            g["projectiles"].update()
            g["particles"].update()
            
            unit_hash = SpatialHash(200)
            for u in unit_list:
                unit_hash.add(u)
            
            building_hash = SpatialHash(200)
            for b in building_list:
                building_hash.add(b)
            
            handle_unit_collisions(unit_list, unit_hash)
            handle_unit_building_collisions(unit_list, building_list, building_hash)
            
            for unit in unit_list:
                unit.rect.center = unit.position
            
            unique_teams = set(g["teams"])
            for team in unique_teams:
                handle_attacks(team, unit_list, building_list, g["projectiles"], g["particles"], unit_hash, building_hash, g["alliances"])
            
            handle_projectiles(g["projectiles"], unit_list, building_list, g["particles"], g)
            
            cleanup_dead_entities(g)
            
            for ai in g["ais"]:
                their_team = ai.hq.team
                friendly_units_list = g["unit_groups"][their_team].sprites()
                friendly_buildings_list = [b for b in building_list if b.team == their_team]
                enemy_units_list = [u for team, ug in g["unit_groups"].items() if team not in ai.allies for u in ug.sprites() if u.health > 0]
                enemy_buildings_list = [b for b in building_list if b.team not in ai.allies]
                ai.update(friendly_units_list, friendly_buildings_list, enemy_units_list, enemy_buildings_list, g["global_buildings"], g["map_width"], g["map_height"])
            
            if "previous_fitness" not in g:
                g["previous_fitness"] = {team: 0 for team in g["teams"]}
            g["current_fitness"] = {}
            g["fitness_deltas"] = {}
            for team in g["teams"]:
                hq = g["hqs"][team]
                if hq.health > 0:
                    stats = hq.stats
                    fitness = (stats.get('units_destroyed', 0) * 10 +
                               stats.get('buildings_destroyed', 0) * 20 -
                               stats.get('units_lost', 0) * 5 -
                               stats.get('buildings_lost', 0) * 10 +
                               stats.get('credits_earned', 0) // 50)
                    g["current_fitness"][team] = fitness
                    prev = g["previous_fitness"].get(team, 0)
                    delta = fitness - prev
                    g["fitness_deltas"][team] = delta
                    g["previous_fitness"][team] = fitness
            
            if not g.get("spectator", False):
                ally_units = [u for team in g["player_allies"] for u in g["unit_groups"][team].sprites()]
                ally_buildings = [b for b in g["global_buildings"].sprites() if b.team in g["player_allies"]]
                g["fog_of_war"].update_visibility(ally_units, ally_buildings, g["global_buildings"].sprites())
            else:
                g["fog_of_war"].update_visibility([], [], g["global_buildings"].sprites())
            
            alive_hqs = [hq for hq in g["hqs"].values() if hq.health > 0]
            all_stats = {team_to_name[team]: hq.stats for team, hq in g["hqs"].items()}
            if g["player_hq"] and g["player_hq"].health <= 0:
                self.state = GameState.DEFEAT
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, False, all_stats, g["player_team"])
            elif len(alive_hqs) <= 1:
                if len(alive_hqs) == 0:
                    is_player_victory = None if g.get("spectator", False) else False
                    self.state = GameState.VICTORY if g.get("spectator", False) else GameState.DEFEAT
                else:
                    last_hq = alive_hqs[0]
                    if g.get("spectator", False):
                        is_player_victory = None
                    else:
                        is_player_victory = (last_hq == g["player_hq"])
                    self.state = GameState.VICTORY if is_player_victory else GameState.DEFEAT
                
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, is_player_victory, all_stats, g.get("player_team"))
            
            self.screen.fill(pg.Color("black"))
            
            map_color = g["map_color"]
            base_r, base_g, base_b = map_color
            zoom = g["camera"].zoom
            min_wx, max_wx, min_wy, max_wy = g["camera"].get_render_bounds()
            num_tx = g["map_width"] // TILE_SIZE
            num_ty = g["map_height"] // TILE_SIZE
            start_tx = max(0, int(min_wx // TILE_SIZE))
            start_ty = max(0, int(min_wy // TILE_SIZE))
            end_tx = min(num_tx, int(max_wx // TILE_SIZE) + 2)
            end_ty = min(num_ty, int(max_wy // TILE_SIZE) + 2)
            for tx in range(start_tx, end_tx):
                wx = tx * TILE_SIZE
                for ty in range(start_ty, end_ty):
                    wy = ty * TILE_SIZE
                    var_r = ((tx * 17 + ty * 31) % 41) - 20
                    var_g = ((tx * 23 + ty * 37) % 41) - 20
                    var_b = ((tx * 29 + ty * 41) % 41) - 20
                    tile_r = max(0, min(255, base_r + var_r))
                    tile_g = max(0, min(255, base_g + var_g))
                    tile_b = max(0, min(255, base_b + var_b))
                    c1 = (wx, wy)
                    c2 = (wx + TILE_SIZE, wy)
                    c3 = (wx + TILE_SIZE, wy + TILE_SIZE)
                    c4 = (wx, wy + TILE_SIZE)
                    iso1 = g["camera"].world_to_iso(c1, zoom)
                    iso2 = g["camera"].world_to_iso(c2, zoom)
                    iso3 = g["camera"].world_to_iso(c3, zoom)
                    iso4 = g["camera"].world_to_iso(c4, zoom)
                    pg.draw.polygon(self.screen, (tile_r, tile_g, tile_b), [iso1, iso2, iso3, iso4])
            
            for feature in g["terrain_features"]:
                if g["fog_of_war"].is_visible(feature.position):
                    feature.draw(self.screen, g["camera"])
            
            draw_allies = set(g["teams"]) if g.get("spectator", False) else g["player_allies"]
            fog = g["fog_of_war"]
            if not g.get("spectator", False):
                g["fog_of_war"].draw(self.screen, g["camera"])
            mouse_pos = pg.mouse.get_pos() if g.get("interface") else None
            for building in building_list:
                visible = building.team in draw_allies or fog.is_visible(building.position) or building.is_seen
                if building.health > 0 and visible:
                    building.draw(self.screen, g["camera"], mouse_pos)
            
            if g["interface"] and not g.get("spectator", False):
                if g["interface"].placing_cls is not None:
                    mouse_pos = pg.mouse.get_pos()
                    ghost_pos = g["camera"].screen_to_world(mouse_pos)
                    snapped = snap_to_grid(ghost_pos)
                    buildings_list = list(g["global_buildings"])
                    unit_type = g["interface"].placing_cls.__name__
                    valid = is_valid_building_position(
                        snapped, g["player_team"], g["interface"].placing_cls, buildings_list,
                        g["map_width"], g["map_height"]
                    )
                    width, height = UNIT_CLASSES[unit_type]["size"]
                    half_w, half_h = width / 2, height / 2
                    temp_rect = pg.Rect(snapped[0] - half_w, snapped[1] - half_h, width, height)
                    screen_ghost = g["camera"].get_screen_rect(temp_rect)
                    color = ProductionInterface.PLACEMENT_VALID_COLOR if valid else ProductionInterface.PLACEMENT_INVALID_COLOR
                    line_width = int(2 * g["camera"].zoom)
                    pg.draw.rect(self.screen, color, screen_ghost, line_width)
                
                for unit in [u for u in unit_list if not u.is_building]:
                    visible = unit.team in draw_allies or fog.is_visible(unit.position)
                    if unit.health > 0 and visible:
                        unit.draw(self.screen, g["camera"], mouse_pos)
            else:
                for unit in [u for u in unit_list if not u.is_building]:
                    if unit.health > 0:
                        unit.draw(self.screen, g["camera"])
            
            for projectile in g["projectiles"]:
                projectile.draw(self.screen, g["camera"])
            
            for particle in g["particles"]:
                particle.draw(self.screen, g["camera"])
            
            if g["interface"] and not g.get("spectator", False):
                g["interface"].draw(self.screen, [b for b in g["global_buildings"] if b.team == g["player_team"]], g["global_buildings"])
            
            if not g.get("spectator", False) and g["selecting"] and g["select_rect"]:
                pg.draw.rect(self.screen, (255, 255, 255), g["select_rect"], 2)
            
            draw_allies_mini = set(g["teams"]) if g.get("spectator", False) else g["player_allies"]
            mini_rect = draw_mini_map(self.screen, g["camera"], g["fog_of_war"], g["map_width"], g["map_height"], g["map_color"], g["global_buildings"], g["global_units"], draw_allies_mini)
            
            draw_fitness_panel(self.screen, g)
            
            pg.display.flip()
            self.clock.tick(60)
    
    def run(self):
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
                        _, game_mode, size_choice, map_choice, spectate = result
                        self.initialize_game(game_mode, size_choice, map_choice, spectate)
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

if __name__ == "__main__":
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("Paper Tigers")
    clock = pg.time.Clock()
    
    font_large = pg.font.SysFont(None, 72)
    font_medium = pg.font.SysFont(None, 28)
    
    manager = GameManager(screen, clock, font_large, font_medium)
    manager.run()
