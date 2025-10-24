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

import pygame as pg
from pygame.math import Vector2

# =============================================================================
# Group: Screen & Map Constants
# =============================================================================

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
CONSOLE_HEIGHT = 100
MAP_WIDTH = 2560
MAP_HEIGHT = 1440
TILE_SIZE = 40
MINI_MAP_WIDTH = 200
MINI_MAP_HEIGHT = 150
PAN_EDGE = 30
PAN_SPEED = 10

# =============================================================================
# Group: Team Colors & Mapping
# =============================================================================

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

# =============================================================================
# Group: Game States
# =============================================================================

class GameState(Enum):
    MENU = 1
    SKIRMISH_SETUP = 2
    PLAYING = 3
    VICTORY = 4
    DEFEAT = 5

# =============================================================================
# Group: Game Data & Config
# =============================================================================

MAPS = {
    "Desert": {"width": 2560, "height": 1440, "color": (139, 120, 80)},
    "Forest": {"width": 3200, "height": 1800, "color": (34, 100, 34)},
    "Ice": {"width": 2560, "height": 1440, "color": (180, 200, 220)},
    "Urban": {"width": 2560, "height": 1440, "color": (100, 100, 100)},
}

UNIT_CLASSES = {
    "Infantry": {
        "cost": 100,
        "hp": 125,
        "speed": 0.5,
        "attack_range": 40,
        "sight_range": 120,
        "weapons": [
            {"name": "Rifle", "damage": 10, "fire_rate": 0.6, "projectile_speed": 6, "projectile_length": 8, "projectile_width": 4, "cooldown": 25}
        ],
        "size": (16, 16),
        "air": False,
        "is_building": False
    },
    "Tank": {
        "cost": 700,
        "hp": 300,
        "speed": 0.6,
        "attack_range": 80,
        "sight_range": 200,
        "weapons": [
            {"name": "Cannon", "damage": 80, "fire_rate": 0.3, "projectile_speed": 5, "projectile_length": 12, "projectile_width": 6, "cooldown": 50}
        ],
        "size": (30, 20),
        "air": False,
        "is_building": False
    },
    "Grenadier": {
        "cost": 300,
        "hp": 100,
        "speed": 0.5,
        "attack_range": 100,
        "sight_range": 120,
        "weapons": [
            {"name": "Grenade", "damage": 20, "fire_rate": 0.75, "projectile_speed": 4, "projectile_length": 10, "projectile_width": 5, "cooldown": 20}
        ],
        "size": (16, 16),
        "air": False,
        "is_building": False
    },
    "MachineGunVehicle": {
        "cost": 600,
        "hp": 200,
        "speed": 0.8,
        "attack_range": 120,
        "sight_range": 200,
        "weapons": [
            {"name": "MG", "damage": 25, "fire_rate": 0.3, "projectile_speed": 6, "projectile_length": 6, "projectile_width": 3, "cooldown": 50}
        ],
        "size": (35, 25),
        "air": False,
        "is_building": False
    },
    "RocketArtillery": {
        "cost": 800,
        "hp": 150,
        "speed": 0.5,
        "attack_range": 150,
        "sight_range": 175,
        "weapons": [
            {"name": "Rockets", "damage": 200, "fire_rate": 0.1, "projectile_speed": 3, "projectile_length": 15, "projectile_width": 8, "cooldown": 150}
        ],
        "size": (40, 25),
        "air": False,
        "is_building": False
    },
    "AttackHelicopter": {
        "cost": 1200,
        "hp": 200,
        "speed": 0.9,
        "attack_range": 100,
        "sight_range": 175,
        "weapons": [
            {"name": "Missiles", "damage": 30, "fire_rate": 0.375, "projectile_speed": 7, "projectile_length": 10, "projectile_width": 4, "cooldown": 40}
        ],
        "size": (25, 15),
        "air": True,
        "fly_height": 10,
        "is_building": False
    },
    "Headquarters": {
        "cost": 1000,
        "starting_credits": 7500,
        "hp": 500,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "size": (100, 100),
        "air": False,
        "is_building": True
    },
    "Barracks": {
        "cost": 300,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "producible": ["Infantry", "Grenadier"],
        "production_time": 60,
        "gate_width": 20,
        "half_door_offset": 15,
        "door_color": (60, 60, 60),
        "size": (80, 80),
        "air": False,
        "is_building": True
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
        "gate_width": 20,
        "half_door_offset": 15,
        "door_color": (60, 60, 60),
        "size": (100, 80),
        "air": False,
        "is_building": True
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
        "gate_width": 10,
        "half_door_offset": 10,
        "door_color": (80, 80, 80),
        "size": (90, 70),
        "air": False,
        "is_building": True
    },
    "PowerPlant": {
        "cost": 300,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "size": (80, 80),
        "air": False,
        "is_building": True
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
        "size": (60, 80),
        "air": False,
        "is_building": True
    },
    "Refinery": {
        "cost": 2000,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 125,
        "income_interval": 300,
        "size": (120, 80),
        "air": False,
        "is_building": True
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
        "size": (70, 70),
        "air": False,
        "is_building": True
    },
    "BlackMarket": {
        "cost": 1500,
        "hp": 200,
        "speed": 0,
        "attack_range": 0,
        "sight_range": 200,
        "weapons": [],
        "income": 200,
        "income_interval": 300,
        "size": (90, 60),
        "air": False,
        "is_building": True
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
        "size": (60, 60),
        "air": False,
        "is_building": True
    }
}

PROJECTILE_LIFETIME = 5.0
PARTICLES_PER_EXPLOSION = 20
PLASMA_BURN_PARTICLES = 10
PLASMA_BURN_DURATION = 2.0

# =============================================================================
# Group: Drawing Recipes
# =============================================================================

# Modular drawing functions for units and buildings
def create_infantry_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size, pg.SRCALPHA)
    pg.draw.circle(image, (150, 150, 150), (8, 4), 4)
    pg.draw.circle(image, (0, 0, 0), (7, 3), 1)  
    pg.draw.circle(image, (0, 0, 0), (9, 3), 1)  
    pg.draw.rect(image, team_color, (6, 2, 4, 2))
    pg.draw.rect(image, (100, 100, 100), (6, 8, 4, 8))
    pg.draw.line(image, (120, 120, 120), (6, 10), (2, 12), 2)
    pg.draw.line(image, (120, 120, 120), (10, 10), (14, 12), 2)
    pg.draw.line(image, team_color, (14, 10), (18, 8), 2)
    pg.draw.rect(image, team_color, (18, 7, 3, 2))
    pg.draw.line(image, (80, 80, 80), (7, 16), (7, 20), 2)
    pg.draw.line(image, (80, 80, 80), (9, 16), (9, 20), 2)
    return image

def create_grenadier_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size, pg.SRCALPHA)
    pg.draw.circle(image, (150, 150, 150), (8, 4), 4)
    pg.draw.circle(image, (0, 0, 0), (7, 3), 1)
    pg.draw.circle(image, (0, 0, 0), (9, 3), 1)
    pg.draw.rect(image, team_color, (6, 2, 4, 2))
    pg.draw.rect(image, (100, 100, 100), (6, 8, 4, 8))
    pg.draw.line(image, (120, 120, 120), (6, 10), (2, 12), 2)
    pg.draw.line(image, (120, 120, 120), (10, 10), (14, 12), 2)
    pg.draw.line(image, (200, 100, 100), (14, 10), (18, 12), 2)
    pg.draw.circle(image, (200, 0, 0), (18, 12), 3)
    pg.draw.circle(image, (150, 0, 0), (12, 10), 2)  
    pg.draw.line(image, (80, 80, 80), (7, 16), (7, 20), 2)
    pg.draw.line(image, (80, 80, 80), (9, 16), (9, 20), 2)
    return image

def create_tank_surfaces(team: Team):
    team_color = team_to_color[team]
    body_surf = pg.Surface((30, 20), pg.SRCALPHA)
    pg.draw.rect(body_surf, (50, 50, 50), (0, 0, 30, 3), width=2)
    pg.draw.rect(body_surf, (50, 50, 50), (0, 17, 30, 3), width=2)
    pg.draw.rect(body_surf, team_color, (2, 3, 26, 14), width=2)
    pg.draw.line(body_surf, team_color, (0, 3), (30, 3), width=2)
    pg.draw.circle(body_surf, (60, 60, 60), (5, 10), 1, width=1)
    pg.draw.circle(body_surf, (60, 60, 60), (25, 10), 1, width=1)
    turret_surf = pg.Surface((12, 12), pg.SRCALPHA)
    pg.draw.circle(turret_surf, team_color, (6, 6), 6, width=2)
    barrel_surf = pg.Surface((20, 6), pg.SRCALPHA)
    pg.draw.line(barrel_surf, team_color, (0, 3), (20, 3), width=3)
    pg.draw.line(barrel_surf, (90, 90, 90), (20, 2), (20, 4), width=1)  
    return body_surf, turret_surf, barrel_surf

def draw_tank(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
    if self.health <= 0:
        return
    screen_pos = camera.world_to_screen(self.position)
    zoom = camera.zoom
    body_scaled = pg.transform.smoothscale(self.body_surf, (int(30 * zoom), int(20 * zoom)))
    rotated_body = pg.transform.rotate(body_scaled, -math.degrees(self.body_angle))
    body_rect = rotated_body.get_rect(center=screen_pos)
    surface.blit(rotated_body, body_rect.topleft)
    turret_scaled = pg.transform.smoothscale(self.turret_surf, (int(12 * zoom), int(12 * zoom)))
    rotated_turret = pg.transform.rotate(turret_scaled, -math.degrees(self.turret_angle))
    turret_rect = rotated_turret.get_rect()
    offset_rot = self.turret_offset.rotate_rad(self.body_angle) * zoom
    turret_center = Vector2(body_rect.center) + offset_rot
    turret_rect.center = turret_center
    surface.blit(rotated_turret, turret_rect.topleft)
    barrel_scaled = pg.transform.smoothscale(self.barrel_surf, (int(20 * zoom), int(6 * zoom)))
    rotated_barrel = pg.transform.rotate(barrel_scaled, -math.degrees(self.turret_angle))
    barrel_rect = rotated_barrel.get_rect()
    barrel_offset_rot = self.barrel_offset.rotate_rad(self.turret_angle) * zoom
    barrel_center = Vector2(turret_center) + barrel_offset_rot
    barrel_rect.center = barrel_center
    surface.blit(rotated_barrel, barrel_rect.topleft)
    if self.selected:
        radius = 15 * zoom + 3
        pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * zoom))
    self.draw_health_bar(surface, camera, mouse_pos)
    for particle in self.plasma_burn_particles:
        particle.draw(surface, camera)

def create_machinegunvehicle_surfaces(team: Team):
    team_color = team_to_color[team]
    body_surf = pg.Surface((35, 25), pg.SRCALPHA)
    pg.draw.rect(body_surf, team_color, (0, 5, 35, 15), width=2)
    wheel_positions = [5, 15, 25]
    for px in wheel_positions:
        pg.draw.circle(body_surf, (50, 50, 50), (px, 5), 3, width=2)
        pg.draw.circle(body_surf, (50, 50, 50), (px, 20), 3, width=2)
    pg.draw.line(body_surf, team_color, (0, 5), (35, 5), width=2)
    for px in wheel_positions:
        pg.draw.circle(body_surf, (40, 40, 40), (px, 5), 1, width=1)
        pg.draw.circle(body_surf, (40, 40, 40), (px, 20), 1, width=1)
    turret_surf = pg.Surface((8, 8), pg.SRCALPHA)
    pg.draw.rect(turret_surf, team_color, (0, 0, 8, 8), width=2)
    barrel_surf = pg.Surface((25, 2), pg.SRCALPHA)
    pg.draw.line(barrel_surf, team_color, (0, 1), (25, 1), width=2)
    return body_surf, turret_surf, barrel_surf

def draw_machinegunvehicle(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
    if self.health <= 0:
        return
    screen_pos = camera.world_to_screen(self.position)
    zoom = camera.zoom
    body_scaled = pg.transform.smoothscale(self.body_surf, (int(35 * zoom), int(25 * zoom)))
    rotated_body = pg.transform.rotate(body_scaled, -math.degrees(self.body_angle))
    body_rect = rotated_body.get_rect(center=screen_pos)
    surface.blit(rotated_body, body_rect.topleft)
    turret_scaled = pg.transform.smoothscale(self.turret_surf, (int(8 * zoom), int(8 * zoom)))
    rotated_turret = pg.transform.rotate(turret_scaled, -math.degrees(self.turret_angle))
    turret_rect = rotated_turret.get_rect()
    offset_rot = self.turret_offset.rotate_rad(self.body_angle) * zoom
    turret_center = Vector2(body_rect.center) + offset_rot
    turret_rect.center = turret_center
    surface.blit(rotated_turret, turret_rect.topleft)
    barrel_scaled = pg.transform.smoothscale(self.barrel_surf, (int(25 * zoom), int(2 * zoom)))
    rotated_barrel = pg.transform.rotate(barrel_scaled, -math.degrees(self.turret_angle))
    barrel_rect = rotated_barrel.get_rect()
    barrel_offset_rot = self.barrel_offset.rotate_rad(self.turret_angle) * zoom
    barrel_center = Vector2(turret_center) + barrel_offset_rot
    barrel_rect.center = barrel_center
    surface.blit(rotated_barrel, barrel_rect.topleft)
    if self.selected:
        radius = 17.5 * zoom + 3
        pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * zoom))
    self.draw_health_bar(surface, camera, mouse_pos)
    for particle in self.plasma_burn_particles:
        particle.draw(surface, camera)

def create_rocketartillery_surfaces(team: Team):
    team_color = team_to_color[team]
    body_surf = pg.Surface((40, 25), pg.SRCALPHA)
    pg.draw.rect(body_surf, team_color, (0, 5, 40, 15), width=2)
    pg.draw.rect(body_surf, (50, 50, 50), (0, 0, 40, 5), width=2)
    pg.draw.rect(body_surf, (50, 50, 50), (0, 20, 40, 5), width=2)
    pg.draw.line(body_surf, team_color, (0, 5), (40, 5), width=2)
    pg.draw.circle(body_surf, (40, 40, 40), (8, 12.5), 3, width=2)
    pg.draw.circle(body_surf, (40, 40, 40), (32, 12.5), 3, width=2)
    turret_surf = pg.Surface((12, 12), pg.SRCALPHA)
    pg.draw.rect(turret_surf, team_color, (0, 0, 12, 12), width=2)
    barrel_surf = pg.Surface((30, 8), pg.SRCALPHA)
    for i in range(3):
        pg.draw.line(barrel_surf, team_color, (i*10, 4), (i*10 + 20, 4), width=2)
    return body_surf, turret_surf, barrel_surf

def draw_rocketartillery(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
    if self.health <= 0:
        return
    screen_pos = camera.world_to_screen(self.position)
    zoom = camera.zoom
    body_scaled = pg.transform.smoothscale(self.body_surf, (int(40 * zoom), int(25 * zoom)))
    rotated_body = pg.transform.rotate(body_scaled, -math.degrees(self.body_angle))
    body_rect = rotated_body.get_rect(center=screen_pos)
    surface.blit(rotated_body, body_rect.topleft)
    turret_scaled = pg.transform.smoothscale(self.turret_surf, (int(12 * zoom), int(12 * zoom)))
    rotated_turret = pg.transform.rotate(turret_scaled, -math.degrees(self.turret_angle))
    turret_rect = rotated_turret.get_rect()
    offset_rot = self.turret_offset.rotate_rad(self.body_angle) * zoom
    turret_center = Vector2(body_rect.center) + offset_rot
    turret_rect.center = turret_center
    surface.blit(rotated_turret, turret_rect.topleft)
    barrel_scaled = pg.transform.smoothscale(self.barrel_surf, (int(30 * zoom), int(8 * zoom)))
    rotated_barrel = pg.transform.rotate(barrel_scaled, -math.degrees(self.turret_angle))
    barrel_rect = rotated_barrel.get_rect()
    barrel_offset_rot = self.barrel_offset.rotate_rad(self.turret_angle) * zoom
    barrel_center = Vector2(turret_center) + barrel_offset_rot
    barrel_rect.center = barrel_center
    surface.blit(rotated_barrel, barrel_rect.topleft)
    if self.selected:
        radius = 20 * zoom + 3
        pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * zoom))
    self.draw_health_bar(surface, camera, mouse_pos)
    for particle in self.plasma_burn_particles:
        particle.draw(surface, camera)

def create_attackhelicopter_surfaces(team: Team):
    team_color = team_to_color[team]
    body_surf = pg.Surface((25, 15), pg.SRCALPHA)
    pg.draw.ellipse(body_surf, team_color, (0, 2, 25, 11), width=2)
    pg.draw.ellipse(body_surf, (80, 80, 80), (2, 4, 21, 7), width=2)
    pg.draw.ellipse(body_surf, (150, 200, 255), (18, 3, 6, 5), width=2)
    pg.draw.line(body_surf, (90, 90, 90), (0, 7), (-5, 7), width=2)
    pg.draw.circle(body_surf, team_color, (-5, 7), 2, width=2)
    pg.draw.circle(body_surf, (60, 60, 60), (12, 7), 3, width=2)
    pg.draw.line(body_surf, team_color, (0, 0), (25, 0), width=2)
    pg.draw.line(body_surf, team_color, (5, 12), (9, 12), width=2)
    pg.draw.line(body_surf, team_color, (16, 12), (20, 12), width=2)
    turret_surf = pg.Surface((8, 6), pg.SRCALPHA)
    pg.draw.rect(turret_surf, team_color, (0, 0, 8, 6), width=2)
    barrel_surf = pg.Surface((12, 2), pg.SRCALPHA)
    pg.draw.line(barrel_surf, team_color, (0, 1), (12, 1), width=2)
    return body_surf, turret_surf, barrel_surf

def draw_attackhelicopter(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
    if self.health <= 0:
        return
    fly_screen_pos = camera.world_to_screen((self.position.x, self.position.y - self.fly_height))
    zoom = camera.zoom
    body_scaled = pg.transform.smoothscale(self.body_surf, (int(25 * zoom), int(15 * zoom)))
    rotated_body = pg.transform.rotate(body_scaled, -math.degrees(self.body_angle))
    body_rect = rotated_body.get_rect(center=fly_screen_pos)
    surface.blit(rotated_body, body_rect.topleft)
    turret_scaled = pg.transform.smoothscale(self.turret_surf, (int(8 * zoom), int(6 * zoom)))
    rotated_turret = pg.transform.rotate(turret_scaled, -math.degrees(self.turret_angle))
    turret_rect = rotated_turret.get_rect()
    offset_rot = self.turret_offset.rotate_rad(self.body_angle) * zoom
    turret_center = Vector2(body_rect.center) + offset_rot
    turret_rect.center = turret_center
    surface.blit(rotated_turret, turret_rect.topleft)
    barrel_scaled = pg.transform.smoothscale(self.barrel_surf, (int(12 * zoom), int(2 * zoom)))
    rotated_barrel = pg.transform.rotate(barrel_scaled, -math.degrees(self.turret_angle))
    barrel_rect = rotated_barrel.get_rect()
    barrel_offset_rot = self.barrel_offset.rotate_rad(self.turret_angle) * zoom
    barrel_center = Vector2(turret_center) + barrel_offset_rot
    barrel_rect.center = barrel_center
    surface.blit(rotated_barrel, barrel_rect.topleft)
    rotor_size = int(20 * zoom)
    pg.draw.circle(surface, self.team_color, (int(fly_screen_pos[0]), int(fly_screen_pos[1])), rotor_size // 2, int(2 * zoom))
    if self.selected:
        radius = 12.5 * zoom + 3
        pg.draw.circle(surface, (255, 255, 0), (int(fly_screen_pos[0]), int(fly_screen_pos[1])), int(radius), int(2 * zoom))
    self.draw_health_bar(surface, camera, mouse_pos)
    for particle in self.plasma_burn_particles:
        particle.draw(surface, camera)

def create_headquarters_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((80, 80, 80))
    pg.draw.rect(image, (100, 100, 100), (10, 10, 80, 70))
    pg.draw.rect(image, team_color, (10, 10, 80, 20))
    for i in range(5):
        win_x = 15 + i * 15
        win_y = 30 + (i % 2) * 15
        pg.draw.rect(image, (100, 150, 255), (win_x, win_y, 8, 6))
        pg.draw.rect(image, (100, 150, 255), (77 - (i % 2)*8, win_y, 8, 6))
    pg.draw.rect(image, (50, 50, 50), (40, 80, 20, 20))
    pg.draw.line(image, (30, 30, 30), (40, 80), (60, 100), 3)
    pg.draw.line(image, team_color, (50, 10), (50, 0), 2)
    pg.draw.circle(image, team_color, (50, 50), 10)
    pg.draw.arc(image, (40, 40, 40), (40, 40, 20, 20), 0, math.pi, 2)
    pg.draw.rect(image, (60, 60, 60), (20, 85, 10, 5))
    pg.draw.rect(image, (60, 60, 60), (70, 85, 10, 5))
    return image

def create_barracks_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((100, 100, 100))
    pg.draw.rect(image, (120, 120, 120), (5, 5, 70, 60))
    pg.draw.polygon(image, (90, 90, 90), [(0, 5), (80, 5), (60, 0), (20, 0)])
    for i in range(3):
        win_y = 20 + i * 12
        pg.draw.rect(image, (100, 150, 255), (15, win_y, 8, 6))
        pg.draw.rect(image, (100, 150, 255), (57, win_y, 8, 6))
    pg.draw.rect(image, (60, 60, 60), (30, 65, 20, 15))
    pg.draw.line(image, (40, 40, 40), (30, 65), (50, 80), 2)
    pg.draw.line(image, (40, 40, 40), (50, 65), (70, 80), 2)
    pg.draw.rect(image, (70, 70, 70), (70, 10, 5, 10))
    pg.draw.rect(image, (50, 50, 50), (72, 5, 1, 5))  
    pg.draw.line(image, team_color, (5, 5), (0, 0), 3)
    return image

def create_warfactory_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((150, 150, 150))
    pg.draw.rect(image, (130, 130, 130), (10, 10, 80, 50))
    pg.draw.rect(image, (140, 140, 140), (0, 0, 100, 80))
    pg.draw.rect(image, (110, 110, 110), (85, 0, 15, 30))
    pg.draw.rect(image, (200, 200, 200), (87, 2, 11, 26))
    pg.draw.circle(image, (100, 150, 255), (92, 18), 3)
    for y in [20, 40]:
        pg.draw.rect(image, (100, 150, 255), (20, y, 12, 8))
        pg.draw.rect(image, (100, 150, 255), (68, y, 12, 8))
    pg.draw.rect(image, (70, 70, 70), (40, 60, 20, 20))
    pg.draw.line(image, (50, 50, 50), (40, 60), (60, 80), 3)
    pg.draw.line(image, (50, 50, 50), (60, 60), (80, 80), 3)
    pg.draw.line(image, (90, 90, 90), (10, 70), (90, 70), 2)
    pg.draw.rect(image, team_color, (5, 5, 5, 5))
    return image

def create_hangar_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((120, 120, 120))
    pg.draw.rect(image, (140, 140, 140), (5, 10, 80, 50))
    pg.draw.polygon(image, (100, 100, 100), [(0, 10), (90, 10), (70, 0), (20, 0)])
    pg.draw.rect(image, (80, 80, 80), (40, 60, 10, 10))
    pg.draw.line(image, (60, 60, 60), (40, 60), (50, 70), 2)
    pg.draw.line(image, (60, 60, 60), (50, 60), (60, 70), 2)
    pg.draw.rect(image, (110, 110, 110), (80, 5, 10, 25))
    pg.draw.circle(image, (100, 150, 255), (85, 15), 2)
    pg.draw.rect(image, team_color, (5, 5, 80, 3))
    return image

def create_powerplant_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((200, 180, 100))
    pg.draw.rect(image, (220, 200, 120), (10, 10, 60, 50))
    pg.draw.rect(image, (150, 150, 150), (65, 5, 10, 25))
    pg.draw.rect(image, (150, 150, 150), (65, 40, 10, 25))
    pg.draw.rect(image, (100, 100, 100), (67, 7, 6, 23))
    pg.draw.rect(image, (100, 100, 100), (67, 42, 6, 23))
    pg.draw.rect(image, (120, 120, 120), (68, 0, 4, 5))  
    pg.draw.rect(image, (120, 120, 120), (68, 35, 4, 5))  
    for i in range(3):
        win_y = 20 + i * 10
        pg.draw.rect(image, (255, 255, 150), (20, win_y, 8, 6))
        pg.draw.rect(image, (255, 255, 150), (52, win_y, 8, 6))
    pg.draw.rect(image, (120, 120, 120), (35, 60, 10, 20))
    pg.draw.line(image, (140, 140, 140), (70, 30), (80, 30), 3)
    pg.draw.line(image, (140, 140, 140), (70, 50), (80, 50), 3)
    pg.draw.rect(image, team_color, (0, 0, 80, 3))
    return image

def create_oilderrick_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((139, 120, 80))
    pg.draw.rect(image, (100, 80, 60), (20, 20, 20, 50))
    pg.draw.line(image, (80, 80, 80), (30, 25), (45, 15), 4)
    pg.draw.line(image, (60, 60, 60), (45, 15), (45, 30), 3)
    pg.draw.circle(image, (60, 60, 60), (45, 15), 5)
    pg.draw.rect(image, (120, 100, 80), (10, 70, 40, 10))
    pg.draw.rect(image, team_color, (25, 75, 10, 5))
    pg.draw.line(image, (90, 70, 50), (10, 70), (10, 20), 3)
    pg.draw.line(image, (90, 70, 50), (50, 70), (50, 20), 3)
    pg.draw.rect(image, (70, 50, 30), (40, 10, 10, 10))
    return image

def create_refinery_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((100, 50, 0))
    pg.draw.ellipse(image, (120, 80, 40), (10, 10, 50, 60))
    pg.draw.ellipse(image, (120, 80, 40), (60, 10, 50, 60))
    pg.draw.circle(image, (140, 100, 60), (35, 40), 5)  
    pg.draw.circle(image, (140, 100, 60), (85, 40), 5)  
    pg.draw.rect(image, (80, 80, 80), (55, 35, 10, 10))
    pg.draw.rect(image, (60, 60, 60), (100, 20, 20, 40))
    pg.draw.rect(image, (80, 80, 80), (102, 22, 16, 36))
    pg.draw.line(image, (50, 50, 50), (60, 40), (100, 40), 4)
    pg.draw.line(image, (50, 50, 50), (60, 50), (100, 50), 4)
    pg.draw.rect(image, team_color, (0, 0, 120, 5))
    return image

def create_shalefracker_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((80, 60, 40))
    pg.draw.rect(image, (100, 80, 60), (10, 10, 50, 50))
    pg.draw.rect(image, (120, 100, 80), (20, 60, 30, 10))
    pg.draw.line(image, (60, 40, 20), (35, 10), (35, 60), 8)
    pg.draw.polygon(image, (40, 20, 0), [(33, 65), (35, 70), (37, 65)])
    pg.draw.line(image, (90, 70, 50), (10, 60), (10, 10), 3)
    pg.draw.line(image, (90, 70, 50), (60, 60), (60, 10), 3)
    pg.draw.rect(image, team_color, (5, 5, 5, 5))
    return image

def create_blackmarket_image(size: tuple, team: Team) -> pg.Surface:
    team_color = team_to_color[team]
    image = pg.Surface(size)
    image.fill((40, 40, 80))
    pg.draw.polygon(image, (60, 60, 100), [(10, 20), (35, 5), (60, 20)])
    pg.draw.line(image, (50, 50, 90), (10, 20), (60, 20), 2)
    pg.draw.polygon(image, (60, 60, 100), [(10, 40), (35, 25), (60, 40)])
    pg.draw.line(image, (50, 50, 90), (10, 40), (60, 40), 2)
    pg.draw.rect(image, (80, 60, 40), (65, 10, 20, 15))
    pg.draw.rect(image, (80, 60, 40), (65, 30, 20, 15))
    pg.draw.line(image, (70, 50, 30), (65, 15), (85, 15), 1)
    pg.draw.line(image, (70, 50, 30), (65, 35), (85, 35), 1)
    pg.draw.rect(image, (70, 70, 70), (20, 45, 20, 15))
    pg.draw.rect(image, team_color, (0, 0, 90, 3))
    return image

def create_turret_surfaces(team: Team):
    team_color = team_to_color[team]
    body_surf = pg.Surface((60, 60), pg.SRCALPHA)
    pg.draw.rect(body_surf, (100, 100, 100), (15, 35, 30, 25))
    pg.draw.rect(body_surf, (80, 80, 80), (17, 37, 26, 21))
    pg.draw.circle(body_surf, (60, 60, 60), (20, 55), 2)
    pg.draw.circle(body_surf, (60, 60, 60), (40, 55), 2)
    pg.draw.rect(body_surf, (120, 120, 120), (25, 50, 10, 5))  
    turret_surf = pg.Surface((20, 20), pg.SRCALPHA)
    pg.draw.circle(turret_surf, team_color, (10, 10), 10)
    pg.draw.circle(turret_surf, (120, 120, 120), (10, 10), 8)
    pg.draw.circle(turret_surf, (100, 150, 255), (10, 12), 2)  
    barrel_surf = pg.Surface((20, 5), pg.SRCALPHA)
    pg.draw.rect(barrel_surf, team_color, (0, 0, 20, 5))
    pg.draw.rect(barrel_surf, (90, 90, 90), (18, 2, 2, 1))  
    return body_surf, turret_surf, barrel_surf

def draw_turret(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
    if self.health <= 0:
        return
    screen_pos = camera.world_to_screen(self.position)
    zoom = camera.zoom
    body_scaled = pg.transform.smoothscale(self.body_surf, (int(60 * zoom), int(60 * zoom)))
    body_rect = body_scaled.get_rect(center=screen_pos)
    surface.blit(body_scaled, body_rect.topleft)
    turret_scaled = pg.transform.smoothscale(self.turret_surf, (int(20 * zoom), int(20 * zoom)))
    rotated_turret = pg.transform.rotate(turret_scaled, -math.degrees(self.turret_angle))
    turret_rect = rotated_turret.get_rect()
    offset_rot = self.turret_offset.rotate_rad(self.body_angle) * zoom
    turret_center = Vector2(body_rect.center) + offset_rot
    turret_rect.center = turret_center
    surface.blit(rotated_turret, turret_rect.topleft)
    barrel_scaled = pg.transform.smoothscale(self.barrel_surf, (int(20 * zoom), int(5 * zoom)))
    rotated_barrel = pg.transform.rotate(barrel_scaled, -math.degrees(self.turret_angle))
    barrel_rect = rotated_barrel.get_rect()
    barrel_offset_rot = self.barrel_offset.rotate_rad(self.turret_angle) * zoom
    barrel_center = Vector2(turret_center) + barrel_offset_rot
    barrel_rect.center = barrel_center
    surface.blit(rotated_barrel, barrel_rect.topleft)
    if self.selected:
        screen_rect = camera.get_screen_rect(self.rect)
        pg.draw.rect(surface, (255, 255, 0), screen_rect, int(3 * zoom))
    self.draw_health_bar(surface, camera, mouse_pos)
    for particle in self.plasma_burn_particles:
        particle.draw(surface, camera)

# Drawing recipe dictionary for simple rotated units
SIMPLE_DRAW_RECIPES = {
    "Infantry": create_infantry_image,
    "Grenadier": create_grenadier_image,
}

# Complex draw mappings
COMPLEX_DRAW_CLASSES = {
    "Tank": (create_tank_surfaces, draw_tank),
    "MachineGunVehicle": (create_machinegunvehicle_surfaces, draw_machinegunvehicle),
    "RocketArtillery": (create_rocketartillery_surfaces, draw_rocketartillery),
    "AttackHelicopter": (create_attackhelicopter_surfaces, draw_attackhelicopter),
    "Turret": (create_turret_surfaces, draw_turret),
}

# Static image recipes for buildings
BUILDING_DRAW_RECIPES = {
    "Headquarters": create_headquarters_image,
    "Barracks": create_barracks_image,
    "WarFactory": create_warfactory_image,
    "Hangar": create_hangar_image,
    "PowerPlant": create_powerplant_image,
    "OilDerrick": create_oilderrick_image,
    "Refinery": create_refinery_image,
    "ShaleFracker": create_shalefracker_image,
    "BlackMarket": create_blackmarket_image,
}

# =============================================================================
# Group: Placement & Spawn Utilities
# =============================================================================

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
    margin: int = 60,  # Passage margin for units
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
            # Dynamic min_dist based on sizes + margin
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

def find_free_spawn_position(building_pos: tuple, target_pos: tuple, global_buildings, global_units, unit_size=(40, 40)):
    for _ in range(20):
        offset_x = random.uniform(-60, 60)
        offset_y = random.uniform(-60, 60)
        pos_x = target_pos[0] + offset_x
        pos_y = target_pos[1] + offset_y
        unit_rect = pg.Rect(pos_x - unit_size[0]/2, pos_y - unit_size[1]/2, unit_size[0], unit_size[1])
        overlaps_building = any(b.rect.colliderect(unit_rect) for b in global_buildings if b.health > 0)
        overlaps_unit = any(u.rect.colliderect(unit_rect) for u in global_units if u.health > 0 and not u.air)
        if not overlaps_building and not overlaps_unit:
            return (pos_x, pos_y)
    return target_pos

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
    edge_dist = 150
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

# =============================================================================
# Group: Spatial Query System
# =============================================================================

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

# =============================================================================
# Group: Camera System
# =============================================================================

class Camera:
    def __init__(self):
        self.map_width = MAP_WIDTH
        self.map_height = MAP_HEIGHT
        self.width = SCREEN_WIDTH - 200
        self.height = SCREEN_HEIGHT
        self.zoom = 1.0
        self.rect = pg.Rect(0, 0, self.width, self.height)
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
    
    def update(self, selected_units: list, mouse_pos: tuple, interface_rect: pg.Rect, keys=None):
        if keys is None:
            keys = pg.key.get_pressed()
        
        pressed_pan = keys[pg.K_w] or keys[pg.K_a] or keys[pg.K_s] or keys[pg.K_d]
        
        mx, my = mouse_pos
        
        if mx < PAN_EDGE and self.rect.left > 0:
            self.rect.x -= PAN_SPEED
        if mx > SCREEN_WIDTH - PAN_EDGE and self.rect.right < self.map_width:
            self.rect.x += PAN_SPEED
        if my < PAN_EDGE and self.rect.top > 0:
            self.rect.y -= PAN_SPEED
        if my > SCREEN_HEIGHT - PAN_EDGE and self.rect.bottom < self.map_height:
            self.rect.y += PAN_SPEED
        
        if keys[pg.K_w] and self.rect.top > 0:
            self.rect.y -= PAN_SPEED
        if keys[pg.K_s] and self.rect.bottom < self.map_height:
            self.rect.y += PAN_SPEED
        if keys[pg.K_a] and self.rect.left > 0:
            self.rect.x -= PAN_SPEED
        if keys[pg.K_d] and self.rect.right < self.map_width:
            self.rect.x += PAN_SPEED
        
        if interface_rect.collidepoint(mx, my):
            self.clamp()
            return
        
        if selected_units and not pressed_pan:
            avg_x = sum(u.position[0] for u in selected_units) / len(selected_units)
            avg_y = sum(u.position[1] for u in selected_units) / len(selected_units)
            self.rect.centerx = avg_x
            self.rect.centery = avg_y
        
        self.clamp()
    
    def clamp(self):
        self.rect.x = max(0, min(self.rect.x, self.map_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, self.map_height - self.rect.height))
    
    def apply(self, rect: pg.Rect) -> pg.Rect:
        return rect.move(-self.rect.x, -self.rect.y)

# =============================================================================
# Group: Fog of War
# =============================================================================

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
        start_tx = max(0, int(camera.rect.x // self.tile_size))
        start_ty = max(0, int(camera.rect.y // self.tile_size))
        end_tx = min(len(self.visible), start_tx + int(camera.rect.width // self.tile_size) + 2)
        end_ty = min(len(self.visible[0]), start_ty + int(camera.rect.height // self.tile_size) + 2)
        zoom = camera.zoom
        tile_sw = self.tile_size * zoom
        tile_sh = self.tile_size * zoom
        fog_overlay = pg.Surface((int(camera.width), int(camera.height)), pg.SRCALPHA)
        fog_overlay.fill((0, 0, 0, 0))
        for tx in range(start_tx, end_tx):
            wx = tx * self.tile_size
            sx = (wx - camera.rect.x) * zoom
            if sx < -tile_sw or sx > camera.width:
                continue
            for ty in range(start_ty, end_ty):
                wy = ty * self.tile_size
                sy = (wy - camera.rect.y) * zoom
                if sy < -tile_sh or sy > camera.height:
                    continue
                if not self.visible[tx][ty]:
                    alpha = 255 if not self.explored[tx][ty] else 100
                    pg.draw.rect(fog_overlay, (0, 0, 0, alpha), (sx, sy, tile_sw, tile_sh))
        surface.blit(fog_overlay, (0, 0))

# =============================================================================
# Group: Particle Effects
# =============================================================================

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
        screen_pos = camera.world_to_screen(self.position)
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

# =============================================================================
# Group: Projectile System
# =============================================================================

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
        self.trail = deque(maxlen=15)
    
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
        screen_pos = camera.world_to_screen(self.position)
        if len(self.trail) > 1:
            trail_positions = [camera.world_to_screen(pos) for pos in self.trail]
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

# =============================================================================
# Group: Base Entity Classes
# =============================================================================

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
        self.image = pg.Surface((32, 32))
        self.rect = self.image.get_rect(center=position)
    
    def distance_to(self, other_pos: tuple) -> float:
        return self.position.distance_to(other_pos)
    
    def displacement_to(self, other_pos: tuple) -> float:
        dx = other_pos[0] - self.position.x
        dy = other_pos[1] - self.position.y
        return (dx, dy)
    
    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        screen_rect = camera.get_screen_rect(self.rect)
        if not screen_rect.colliderect((0, 0, camera.width, camera.height)):
            return
        screen_pos = camera.world_to_screen(self.position)
        zoom = camera.zoom
        scaled_size = (int(self.image.get_width() * zoom), int(self.image.get_height() * zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            offset_x = scaled_size[0] / 2
            offset_y = scaled_size[1] / 2
            blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
            surface.blit(scaled_image, blit_pos)
        if self.selected:
            radius = max(self.rect.width, self.rect.height) / 2 * zoom + 3
            pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * zoom))
        
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)
    
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
        
        screen_pos = camera.world_to_screen(self.position)
        health_ratio = self.health / self.max_health
        color = (0, 255, 0) if health_ratio > 0.5 else (255, 0, 0)
        bar_width = 50
        bar_height = 8
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
    def update(self): pass

class Unit(GameObject):
    def __init__(self, position: tuple, team: Team, unit_type: str, hq=None):
        super().__init__(position, team)
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
        self.team_color = team_to_color[team]
        self.hq = hq
        self.fly_height = stats.get("fly_height", 0)
        if "income" in stats:
            self.income = stats["income"]
            self.collection_timer = 0
        if "producible" in stats:
            self.rally_point = Vector2(position[0] + 80, position[1])
            self.production_queue = []
            self.production_timer = None
            self.gate_open = False
            self.gate_timer = 0
        self.rect = self.image.get_rect(center=position)
        # Modular drawing setup
        self._setup_drawing(unit_type)
    
    def _setup_drawing(self, unit_type: str):
        if unit_type in SIMPLE_DRAW_RECIPES:
            self.image = SIMPLE_DRAW_RECIPES[unit_type](UNIT_CLASSES[unit_type]["size"], self.team)
            if unit_type in ["Infantry", "Grenadier"]:
                self.needs_rotation = True
        elif unit_type in COMPLEX_DRAW_CLASSES:
            create_surfaces, draw_func = COMPLEX_DRAW_CLASSES[unit_type]
            self.body_surf, self.turret_surf, self.barrel_surf = create_surfaces(self.team)
            if unit_type == "AttackHelicopter":
                self.turret_offset = Vector2(12, 0)
                self.barrel_offset = Vector2(6, 0)
            else:
                self.turret_offset = Vector2(0, -3) if unit_type != "Turret" else Vector2(0, -15)
                self.barrel_offset = Vector2(8, 0) if unit_type == "Tank" else Vector2(10, 0) if unit_type == "MachineGunVehicle" else Vector2(15, 0) if unit_type == "RocketArtillery" else Vector2(10, 0)
            self.draw = draw_func.__get__(self, self.__class__)
        elif self.is_building and unit_type in BUILDING_DRAW_RECIPES:
            self.image = BUILDING_DRAW_RECIPES[unit_type](UNIT_CLASSES[unit_type]["size"], self.team)
        else:
            # Fallback
            self.image.fill(self.team_color)
        self.rect = self.image.get_rect(center=self.position)
    
    def _draw_gate(self, surface: pg.Surface, camera: Camera):
        door_width = self.stats.get("gate_width", 20)
        half_door_offset = self.stats.get("half_door_offset", 15)
        door_color = self.stats.get("door_color", (60, 60, 60))
        door_height = self.rect.height - 20
        half_door = door_width // 2
        left_door = pg.Rect(self.rect.right - door_width, self.rect.top + 10, half_door, door_height)
        right_door = pg.Rect(self.rect.right - half_door, self.rect.top + 10, half_door, door_height)
        open_left = left_door.move(-half_door_offset, 0)
        open_right = right_door.move(half_door_offset, 0)
        pg.draw.rect(surface, door_color, camera.get_screen_rect(open_left))
        pg.draw.rect(surface, door_color, camera.get_screen_rect(open_right))
    
    def _update_production(self, friendly_units, all_units):
        if self.gate_open:
            self.gate_timer -= 1
            if self.gate_timer <= 0:
                self.gate_open = False
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
                    new_unit = globals()[unit_type](spawn_pos, self.team)
                except KeyError:
                    new_unit = globals()["Infantry"](spawn_pos, self.team)  # fallback
                new_unit.position = Vector2(spawn_pos)
                new_unit.rect.center = new_unit.position
                new_unit.move_target = self.rally_point
                friendly_units.add(new_unit)
                all_units.add(new_unit)
                self.gate_open = True
                self.gate_timer = 60
                if repeat:
                    self.production_queue.append({'unit_type': unit_type, 'repeat': True})
                self.production_timer = None
    
    def update(self, particles=None, friendly_units=None, all_units=None, global_buildings=None, projectiles=None, enemy_units=None, enemy_buildings=None):
        self.under_attack_timer = max(0, self.under_attack_timer - 1)
        self.under_attack = self.under_attack_timer > 0
        
        if self.last_shot_time > 0:
            self.last_shot_time -= 1
        
        # Clear invalid attack target
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
                dist = self.distance_to(self.attack_target.position)
                dir_to_enemy = Vector2(self.attack_target.position) - self.position
                if dir_to_enemy.length() > 0:
                    dir_to_enemy = dir_to_enemy.normalize()
                self.turret_angle = math.atan2(dir_to_enemy.y, dir_to_enemy.x)
                if dist <= self.attack_range:
                    # Stop moving and fight
                    original_move_target = self.move_target
                    self.move_target = None
                    # Face the enemy
                    self.body_angle = self.turret_angle
                    # Small random movement to avoid clustering
                    if random.random() < 0.1:
                        self.position += dir_to_enemy.rotate_rad(random.uniform(-0.5, 0.5)) * self.speed * 0.2
                    # Restore move_target after combat if needed, but for now, stay stopped until enemy dead or out of sight
                else:
                    # Chase the target
                    if self.attack_target.is_building:
                        dir_to_center = Vector2(self.attack_target.position) - self.position
                        if dir_to_center.length() > 0:
                            dir_to_center = dir_to_center.normalize()
                            dir_from_center = -dir_to_center
                            # Add small spread to avoid clustering
                            spread_angle = random.uniform(-math.pi/6, math.pi/6)
                            dir_from_center = dir_from_center.rotate_rad(spread_angle)
                            stop_dist = self.attack_range - 10  # Stop a bit inside range to ensure attack
                            self.move_target = self.attack_target.position + dir_from_center * stop_dist
                    else:
                        self.move_target = self.attack_target.position
            
            # Normal movement if no close combat
            if not self.attack_target or self.distance_to(self.attack_target.position) > self.attack_range:
                move_dir = None
                if self.move_target:
                    dir_to_target = Vector2(self.move_target) - self.position
                    dist_to_move = dir_to_target.length()
                    if dist_to_move > 5:
                        move_dir = dir_to_target.normalize()
                        self.position += move_dir * self.speed
                        self.body_angle = math.atan2(move_dir.y, move_dir.x)
                    else:
                        self.move_target = None
        
        if not self.attack_target:
            self.turret_angle = self.body_angle
        
        if hasattr(self, 'stats') and "producible" in self.stats and friendly_units is not None and all_units is not None:
            self._update_production(friendly_units, all_units)
        
        if hasattr(self, 'collection_timer'):
            self.collection_timer += 1
            if self.collection_timer >= self.stats.get("income_interval", 300):
                if hasattr(self, 'hq') and self.hq:
                    self.hq.credits += self.income
                self.collection_timer = 0
        
        self.rect.center = self.position
        
        self.plasma_burn_particles = [p for p in self.plasma_burn_particles if p.alive()]
    
    def draw(self, surface: pg.Surface, camera: Camera, mouse_pos: tuple = None):
        if self.health <= 0:
            return
        screen_pos = camera.world_to_screen(self.position)
        if self.air:
            screen_pos = (screen_pos[0], screen_pos[1] - self.fly_height * camera.zoom)
        zoom = camera.zoom
        screen_rect = camera.get_screen_rect(self.rect)
        if not screen_rect.colliderect((0, 0, camera.width, camera.height)):
            return
        scaled_size = (int(self.image.get_width() * zoom), int(self.image.get_height() * zoom))
        if scaled_size[0] > 0 and scaled_size[1] > 0:
            scaled_image = pg.transform.smoothscale(self.image, scaled_size)
            if hasattr(self, 'needs_rotation') and self.needs_rotation:
                rotated_image = pg.transform.rotate(scaled_image, -math.degrees(self.body_angle))
                rot_rect = rotated_image.get_rect(center=screen_pos)
                surface.blit(rotated_image, rot_rect.topleft)
            else:
                offset_x = scaled_size[0] / 2
                offset_y = scaled_size[1] / 2
                blit_pos = (screen_pos[0] - offset_x, screen_pos[1] - offset_y)
                surface.blit(scaled_image, blit_pos)
        if self.selected:
            if self.is_building:
                screen_rect = camera.get_screen_rect(self.rect)
                pg.draw.rect(surface, (255, 255, 0), screen_rect, int(3 * zoom))
            else:
                radius = max(self.rect.width, self.rect.height) / 2 * zoom + 3
                pg.draw.circle(surface, (255, 255, 0), (int(screen_pos[0]), int(screen_pos[1])), int(radius), int(2 * zoom))
        if hasattr(self, 'rally_point') and self.selected:
            rally_screen = camera.world_to_screen(self.rally_point)
            pg.draw.circle(surface, (0, 255, 0), (int(rally_screen[0]), int(rally_screen[1])), 5)
        if hasattr(self, 'gate_open') and self.gate_open:
            self._draw_gate(surface, camera)
        self.draw_health_bar(surface, camera, mouse_pos)
        for particle in self.plasma_burn_particles:
            particle.draw(surface, camera)
    
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
        dist = self.distance_to(target.position)
        if dist <= self.get_attack_range():
            time_to_target = dist / weapon["projectile_speed"]
            target_vel = Vector2(target.speed * math.cos(getattr(target, 'body_angle', 0)) if hasattr(target, 'speed') else 0,
                                 target.speed * math.sin(getattr(target, 'body_angle', 0)) if hasattr(target, 'speed') else 0)
            predicted_pos = target.position + target_vel * time_to_target
            direction = (predicted_pos - self.position).normalize()
            proj = Projectile(self.position, direction, weapon["damage"], self.team, weapon)
            projectiles.add(proj)
            self.last_shot_time = weapon["cooldown"]
            self.turret_angle = math.atan2(direction.y, direction.x)
            create_explosion(self.position, pg.sprite.Group(), self.team, 3)

# =============================================================================
# Group: Unit Drawing & Creation + Specific Unit Classes
# =============================================================================

# Subclasses now lean, relying on base Unit for drawing setup
class Infantry(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Infantry")

class Tank(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Tank")

class Grenadier(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Grenadier")

class MachineGunVehicle(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "MachineGunVehicle")

class RocketArtillery(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "RocketArtillery")

class AttackHelicopter(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "AttackHelicopter")

# =============================================================================
# Group: Building Drawing & Creation + Specific Building Classes + Turret
# =============================================================================

class Headquarters(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Headquarters")
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
    
    def place_building(self, position: tuple, unit_cls: Type, all_buildings):
        all_buildings_list = list(all_buildings)
        if is_valid_building_position(position, self.team, unit_cls, all_buildings_list):
            unit_type = unit_cls.__name__
            if unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]:
                building = unit_cls(position, self.team, self)
            else:
                building = unit_cls(position, self.team)
            if unit_type in ["WarFactory", "Barracks", "Hangar"]:
                building.parent_hq = self
            all_buildings.add(building)
            self.credits -= UNIT_CLASSES[unit_type]["cost"]
            self.pending_building = None

class Barracks(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Barracks")
        self.parent_hq = None

class WarFactory(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "WarFactory")
        self.parent_hq = None

class Hangar(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Hangar")
        self.parent_hq = None

class PowerPlant(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "PowerPlant")

class OilDerrick(Unit):
    def __init__(self, position: tuple, team: Team, hq):
        super().__init__(position, team, "OilDerrick", hq=hq)

class Refinery(Unit):
    def __init__(self, position: tuple, team: Team, hq):
        super().__init__(position, team, "Refinery", hq=hq)
        self.radius = 60

class ShaleFracker(Unit):
    def __init__(self, position: tuple, team: Team, hq):
        super().__init__(position, team, "ShaleFracker", hq=hq)

class BlackMarket(Unit):
    def __init__(self, position: tuple, team: Team, hq):
        super().__init__(position, team, "BlackMarket", hq=hq)

class Turret(Unit):
    def __init__(self, position: tuple, team: Team):
        super().__init__(position, team, "Turret")

# =============================================================================
# Group: Console & Logging
# =============================================================================

class GameConsole:
    def __init__(self):
        self.messages = []
    
    def log(self, message: str):
        self.messages.append(message)
    
    def handle_event(self, event):
        pass
    
    def draw(self, surface: pg.Surface):
        pass

# =============================================================================
# Group: AI Controller
# =============================================================================

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
        self.build_queue = []
        self.barracks_index = 0
        self.warfactory_index = 0
        self.hangar_index = 0
        self.personality = random.choice(['aggressive', 'defensive', 'balanced', 'rusher'])  # Random trait
        self.timer_offset = random.randint(0, 180)  # Stagger starts by up to 3 seconds (at 60 FPS)
        self.interval_multiplier = random.uniform(0.7, 1.3)  # Vary speeds: 70-130% of base intervals
        self.build_jitter = random.uniform(0.1, 0.5)  # Extra randomness in build angles (lower = more biased)
        self.aggression_bias = 1.2 if self.personality in ['aggressive', 'rusher'] else 0.8 if self.personality == 'defensive' else 1.0
        self.economy_bias = 0.8 if self.personality in ['aggressive', 'rusher'] else 1.2 if self.personality == 'defensive' else 1.0
        
        # Adjust priorities based on personality
        base_priorities = {
            "Infantry": 0.6, "Grenadier": 0.2, "Tank": 0.15,
            "MachineGunVehicle": 0.05, "RocketArtillery": 0.05, "AttackHelicopter": 0.0,
        }
        if self.personality == 'rusher':
            base_priorities["Infantry"] *= 1.5  # Rush cheap units
            base_priorities["AttackHelicopter"] *= 0.5
        elif self.personality == 'defensive':
            base_priorities["Grenadier"] *= 1.5  # More area denial
            base_priorities["Tank"] *= 0.5
        self.production_priorities = base_priorities
        self.preferred_build_direction = build_dir
        self.build_bias_strength = 0.3  
    
    def assess_situation(self, friendly_units, friendly_buildings, enemy_units, enemy_buildings):
        self.military_strength = len([u for u in friendly_units if u.health > 0])
        self.enemy_strength = len([u for u in enemy_units if u.health > 0])
        
        hq_pos = self.hq.position
        nearby_enemies = [u for u in enemy_units if u.health > 0 and u.distance_to(hq_pos) < 600]
        self.threat_level = len(nearby_enemies) / max(1, self.enemy_strength) if self.enemy_strength > 0 else 0
        
        resource_buildings = [b for b in friendly_buildings if b.unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]]
        self.economy_level = min(3, len(resource_buildings) // 2)

        self.resource_count = len([b for b in friendly_buildings if b.unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"] and b.health > 0])
        self.turret_count = len([b for b in friendly_buildings if b.unit_type == "Turret" and b.health > 0])
        self.military_prod_count = len([b for b in friendly_buildings if b.unit_type in ["Barracks", "WarFactory", "Hangar"] and b.health > 0])
        self.power_count = len([b for b in friendly_buildings if b.unit_type == "PowerPlant" and b.health > 0])
        self.total_buildings = self.military_prod_count + self.resource_count + self.power_count + self.turret_count
        
        power_plants = len([b for b in friendly_buildings if b.unit_type == "PowerPlant"])
        self.power_shortage = power_plants < self.economy_level + 1

        inf_prio = 0.5 if self.threat_level > 0.5 else 0.6
        gren_prio = 0.3 if self.threat_level > 0.5 else 0.2
        tank_prio = 0.15 if self.economy_level >= 1 else 0.05
        mgv_prio = 0.05 if self.economy_level >= 2 else 0.0
        rocket_prio = 0.05 if self.economy_level >= 2 else 0.0
        heli_prio = 0.1 if self.economy_level >= 2 else 0.0
        total_prio = inf_prio + gren_prio + tank_prio + mgv_prio + rocket_prio + heli_prio
        if total_prio > 0:
            inf_prio /= total_prio
            gren_prio /= total_prio
            tank_prio /= total_prio
            mgv_prio /= total_prio
            rocket_prio /= total_prio
            heli_prio /= total_prio
        self.production_priorities = {
            "Infantry": inf_prio,
            "Grenadier": gren_prio,
            "Tank": tank_prio,
            "MachineGunVehicle": mgv_prio,
            "RocketArtillery": rocket_prio,
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
            dist_min, dist_max = 100, 150 + 50 * scale  
        elif building_cls.__name__ in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]:
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 120, 200 + 100 * scale
        elif building_cls.__name__ == "Turret":
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 80, 150 + 30 * scale
        else:
            bias_angle = self.preferred_build_direction
            dist_min, dist_max = 100, 180 + 50 * scale

        if not prefer_near_hq:
            dist_min, dist_max = max(200, dist_min), 400 * scale

        ring_step = 25 * scale  # Increased from 20: Wider rings to sample more spaced positions
        num_samples_per_ring = 25  # Increased from 20: More attempts per ring for better spacing
        # Increase jitter for personality
        angle_jitter = math.pi * self.build_jitter * (1.5 if self.personality == 'rusher' else 1.0)  # Rushers spread out more
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
        target_units = max(8, int(self.military_strength * 1.5) + int(self.threat_level * 25))
        
        if num_units < target_units:
            if barracks_list:
                barracks = barracks_list[self.barracks_index % len(barracks_list)]
                self.barracks_index += 1
                if len(barracks.production_queue) < 5:
                    if self.threat_level > 0.5:
                        unit_type = random.choices(list(self.production_priorities.keys()), weights=[0.7, 0.2, 0.1, 0, 0, 0])[0]
                    else:
                        unit_type = random.choices(list(self.production_priorities.keys()), weights=list(self.production_priorities.values()))[0]
                    
                    cost = UNIT_CLASSES[unit_type]["cost"]
                    if self.hq.credits >= cost:
                        barracks.production_queue.append({'unit_type': unit_type, 'repeat': False})
                        self.hq.credits -= cost
                        if random.random() < 0.4 and unit_type == "Infantry" and num_units < 5:
                            barracks.production_queue[-1]['repeat'] = True
            
            if war_factory_list:
                war_factory = war_factory_list[self.warfactory_index % len(war_factory_list)]
                self.warfactory_index += 1
                if len(war_factory.production_queue) < 3 and self.economy_level > 1:
                    heavy_unit = random.choice(["Tank", "MachineGunVehicle", "RocketArtillery"])
                    cost = UNIT_CLASSES[heavy_unit]["cost"]
                    if self.hq.credits >= cost and num_units < target_units * 0.8:
                        war_factory.production_queue.append({'unit_type': heavy_unit, 'repeat': False})
                        self.hq.credits -= cost
            
            if hangar_list:
                hangar = hangar_list[self.hangar_index % len(hangar_list)]
                self.hangar_index += 1
                if len(hangar.production_queue) < 2 and self.economy_level >= 2:
                    if random.random() < 0.2:
                        hangar.production_queue.append({'unit_type': "AttackHelicopter", 'repeat': False})
                        self.hq.credits -= UNIT_CLASSES["AttackHelicopter"]["cost"]
    
    def build_defenses(self, all_buildings, map_width, map_height):
        if self.threat_level > 0.2 and self.hq.credits >= UNIT_CLASSES["Turret"]["cost"]:
            pos = self.find_build_position(Turret, all_buildings, map_width, map_height, prefer_near_hq=True)
            if pos:
                self.hq.place_building(pos, Turret, all_buildings)
    
    def strategize_attacks(self, friendly_units, enemy_hq, enemy_buildings=None, enemy_units=None):
        if not enemy_hq and not enemy_buildings and not enemy_units:
            return
        
        self.scout_timer += 1
        scout_interval = int(60 * self.interval_multiplier)  # Varied: 42-78 frames
        if self.scout_timer > scout_interval and len(friendly_units) > 1:
            scout_target = enemy_hq.position if enemy_hq else ((self._get_nearest_enemy_building(enemy_buildings, friendly_units[0].position if friendly_units else (0, 0)).position if enemy_buildings else (0, 0)))
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None][:3]
            for scout in idle_units:
                scout.move_target = (scout_target[0] + random.uniform(-200, 200), scout_target[1] + random.uniform(-200, 200))
            self.scout_timer = random.randint(0, scout_interval // 2)  # Jitter reset
        
        self.attack_timer += 1
        attack_interval = int(30 * self.interval_multiplier)  # Varied: 21-39 frames
        attack_fraction = (0.3 if self.threat_level > 0.5 else 0.2) * self.aggression_bias  # Personality tweak
        if self.attack_timer > attack_interval:
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None]
            if len(idle_units) > 0:
                num_to_send = max(1, int(len(idle_units) * attack_fraction * random.uniform(0.8, 1.2)))  # Extra randomness
                for unit in idle_units[:num_to_send]:
                    primary_target = self._get_nearest_enemy_target(enemy_buildings, enemy_units, unit.position)
                    if primary_target:
                        unit.attack_target = primary_target
                        unit.move_target = primary_target.position
                    else:
                        if enemy_hq:
                            unit.attack_target = enemy_hq
                            unit.move_target = enemy_hq.position
                        else:
                            unit.move_target = None
            self.attack_timer = random.randint(0, attack_interval // 2)
        
        # Aggressive push: Scale by personality
        push_threshold = 0.5 * self.aggression_bias
        if self.military_strength > self.enemy_strength * push_threshold:
            idle_units = [u for u in friendly_units if u.health > 0 and u.move_target is None]
            if len(idle_units) > 3:
                attack_fraction = (0.8 if self.threat_level > 0.5 else 0.5) * self.aggression_bias
                num_to_send = int(len(idle_units) * attack_fraction)
                for unit in idle_units[:num_to_send]:
                    primary_target = self._get_nearest_enemy_target(enemy_buildings, enemy_units, unit.position)
                    if primary_target:
                        unit.attack_target = primary_target
                        unit.move_target = primary_target.position
                    else:
                        if enemy_hq:
                            unit.attack_target = enemy_hq
                            unit.move_target = enemy_hq.position
                        else:
                            unit.move_target = None
    
    def update(self, friendly_units, friendly_buildings, enemy_units, enemy_buildings, all_buildings, map_width=MAP_WIDTH, map_height=MAP_HEIGHT):
        self.assess_situation(friendly_units, friendly_buildings, enemy_units, enemy_buildings)
        self.action_timer += 1
        
        # Apply offset and multiplier for desync
        effective_timer = (self.action_timer + self.timer_offset) * self.interval_multiplier
        
        # Production: Base 60, now varied (e.g., 42-78 frames)
        if int(effective_timer) % int(60 * self.interval_multiplier) == 0:
            barracks_list = [b for b in friendly_buildings if b.unit_type == "Barracks" and b.health > 0]
            war_factory_list = [b for b in friendly_buildings if b.unit_type == "WarFactory" and b.health > 0]
            hangar_list = [b for b in friendly_buildings if b.unit_type == "Hangar" and b.health > 0]
            self.queue_unit_production(barracks_list, war_factory_list, hangar_list, friendly_units)
        
        # Building: Base 180, now varied (e.g., 126-234 frames)
        if int(effective_timer) % int(180 * self.interval_multiplier) == 0 and self.hq.credits >= 300:
            # Tweak building choice with personality
            if self.personality == 'rusher' and self.resource_count == 0:
                cls = Barracks  # Rush military over economy
            elif self.personality == 'defensive' and self.turret_count < self.total_buildings // 3:
                cls = Turret
            else:
                if self.threat_level > 0.4 and self.turret_count < min(3, self.total_buildings // 2) and self.hq.credits >= UNIT_CLASSES["Turret"]["cost"]:
                    pos = self.find_build_position(Turret, all_buildings, map_width, map_height)
                    if pos:
                        self.hq.place_building(pos, Turret, all_buildings)
                        return
                
                if self.resource_count == 0 and self.hq.credits >= UNIT_CLASSES["OilDerrick"]["cost"]:
                    cls = OilDerrick
                elif self.resource_count < 2 and self.hq.credits >= UNIT_CLASSES["Refinery"]["cost"]:
                    built_ref = any(b.unit_type == "Refinery" for b in friendly_buildings if b.health > 0)
                    if not built_ref:
                        cls = Refinery
                    else:
                        cls = random.choice([ShaleFracker, BlackMarket])
                elif self.power_shortage and self.economy_level > 0 and self.hq.credits >= UNIT_CLASSES["PowerPlant"]["cost"]:
                    cls = PowerPlant
                elif self.military_prod_count < max(1, self.resource_count // 2 + 1):
                    built_barracks = any(b.unit_type == "Barracks" for b in friendly_buildings if b.health > 0)
                    built_factory = any(b.unit_type == "WarFactory" for b in friendly_buildings if b.health > 0)
                    built_hangar = any(b.unit_type == "Hangar" for b in friendly_buildings if b.health > 0)
                    if not built_barracks:
                        cls = Barracks
                    elif self.resource_count >= 2 and not built_factory:
                        cls = WarFactory
                    elif self.resource_count >= 3 and not built_hangar:
                        cls = Hangar
                    else:
                        cls = random.choice([Barracks, WarFactory, Hangar])
                else:
                    rand = random.random()
                    if rand < 0.4:
                        cls = random.choice([Barracks, WarFactory, Hangar])
                    elif rand < 0.7:
                        cls = random.choice([OilDerrick, Refinery, ShaleFracker, BlackMarket])
                    else:
                        all_possible = [PowerPlant, Turret] + [OilDerrick, Refinery, ShaleFracker, BlackMarket]
                        cls = random.choice(all_possible)
            
            cost = UNIT_CLASSES[cls.__name__]["cost"]
            if self.hq.credits >= cost:
                pos = self.find_build_position(cls, all_buildings, map_width, map_height, prefer_near_hq=True)
                if pos:
                    self.hq.place_building(pos, cls, all_buildings)
        
        self.defense_timer += 1
        defense_interval = int(240 * self.interval_multiplier)
        threat_threshold = 0.3 * self.aggression_bias  # Aggressive AIs build turrets sooner
        if self.defense_timer > defense_interval and self.threat_level > threat_threshold and self.turret_count < min(5, self.total_buildings // 3) and self.hq.credits >= UNIT_CLASSES["Turret"]["cost"]:
            pos = self.find_build_position(Turret, all_buildings, map_width, map_height, prefer_near_hq=True)
            if pos:
                self.hq.place_building(pos, Turret, all_buildings)
            self.defense_timer = random.randint(0, defense_interval // 2)  # Reset with jitter
        
        enemy_hq = min(
            (b for b in enemy_buildings if b.unit_type == "Headquarters" and b.health > 0),
            key=lambda b: self.hq.distance_to(b.position),
            default=None
        )
        self.strategize_attacks(friendly_units, enemy_hq, enemy_buildings, enemy_units)

# =============================================================================
# Group: Production UI Constants
# =============================================================================

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
                self.producible_items = ["Infantry", "Grenadier"]
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

# =============================================================================
# Group: Game Loop Handlers
# =============================================================================

def draw_mini_map(screen: pg.Surface, camera: Camera, fog_of_war: FogOfWar, map_width: int, map_height: int, map_color: tuple, buildings, all_units, player_allies: Set[Team]):
    mini_map_rect = pg.Rect(SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT, MINI_MAP_WIDTH, MINI_MAP_HEIGHT)
    mini_map = pg.Surface((MINI_MAP_WIDTH, MINI_MAP_HEIGHT))
    mini_map.fill((0, 0, 0))
    
    num_tx = map_width // TILE_SIZE
    num_ty = map_height // TILE_SIZE
    scale_x = MINI_MAP_WIDTH / map_width
    scale_y = MINI_MAP_HEIGHT / map_height
    tile_mw = TILE_SIZE * scale_x
    tile_mh = TILE_SIZE * scale_y
    base_r, base_g, base_b = map_color
    
    for tx in range(num_tx):
        mx = tx * TILE_SIZE * scale_x
        tile_center_x = (tx + 0.5) * TILE_SIZE
        for ty in range(num_ty):
            tile_center_y = (ty + 0.5) * TILE_SIZE
            if not fog_of_war.is_explored((tile_center_x, tile_center_y)):
                continue
            my = ty * TILE_SIZE * scale_y
            var_r = ((tx * 17 + ty * 31) % 41) - 20
            var_g = ((tx * 23 + ty * 37) % 41) - 20
            var_b = ((tx * 29 + ty * 41) % 41) - 20
            tile_r = max(0, min(255, base_r + var_r))
            tile_g = max(0, min(255, base_g + var_g))
            tile_b = max(0, min(255, base_b + var_b))
            if not fog_of_war.is_visible((tile_center_x, tile_center_y)):
                avg = (tile_r + tile_g + tile_b) // 3
                tile_r = tile_g = tile_b = avg
            pg.draw.rect(mini_map, (tile_r, tile_g, tile_b), (mx, my, tile_mw, tile_mh))
            crater_seed = (tx * 123 + ty * 456) % 100
            if crater_seed < 5:
                cx = mx + tile_mw / 2
                cy = my + tile_mh / 2
                cr = tile_mw / 4
                dark_r = max(0, tile_r - 40)
                dark_g = max(0, tile_g - 40)
                dark_b = max(0, tile_b - 40)
                pg.draw.circle(mini_map, (dark_r, dark_g, dark_b), (int(cx), int(cy)), int(cr))
    
    for building in buildings:
        if building.health > 0 and (building.team in player_allies or building.is_seen) and fog_of_war.is_explored(building.position):
            color = team_to_color[building.team]
            x = int(building.position.x * scale_x)
            y = int(building.position.y * scale_y)
            pg.draw.rect(mini_map, color, (x - 2, y - 2, 5, 5))
    
    for unit in all_units:
        if unit.health > 0 and (unit.team in player_allies or fog_of_war.is_visible(unit.position)):
            color = team_to_color[unit.team]
            x = int(unit.position.x * scale_x)
            y = int(unit.position.y * scale_y)
            pg.draw.circle(mini_map, color, (x, y), 2)
    
    cam_rect = pg.Rect(
        camera.rect.x * scale_x,
        camera.rect.y * scale_y,
        camera.rect.width * scale_x,
        camera.rect.height * scale_y
    )
    pg.draw.rect(mini_map, (255, 255, 255), cam_rect, 1)
    
    screen.blit(mini_map, (SCREEN_WIDTH - MINI_MAP_WIDTH, SCREEN_HEIGHT - MINI_MAP_HEIGHT))
    return mini_map_rect

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
    # Mobile units
    for u in all_units:
        if u.team == team and hasattr(u, 'weapons') and u.weapons and u.health > 0:
            armed_entities.append(u)
    # Buildings
    for b in all_buildings:
        if b.team == team and hasattr(b, 'weapons') and b.weapons and b.health > 0:
            armed_entities.append(b)
    for entity in armed_entities:
        if entity.last_shot_time != 0:
            continue
        closest_target, min_dist = None, float("inf")
        candidates = unit_hash.query(entity.position, entity.sight_range) + building_hash.query(entity.position, entity.sight_range)
        for obj in candidates:
            if hasattr(obj, 'team') and obj.team not in unit_allies and hasattr(obj, 'health') and obj.health > 0:
                dist = entity.distance_to(obj.position)
                if dist <= entity.sight_range and dist < min_dist:
                    closest_target, min_dist = obj, dist
        if closest_target:
            entity.attack_target = closest_target
            dist_to_target = entity.distance_to(closest_target.position)
            if dist_to_target > entity.attack_range and not entity.is_building:
                # Chase the target
                if entity.attack_target.is_building:
                    dir_to_center = Vector2(entity.attack_target.position) - entity.position
                    if dir_to_center.length() > 0:
                        dir_to_center = dir_to_center.normalize()
                        dir_from_center = -dir_to_center
                        # Add small spread to avoid clustering
                        spread_angle = random.uniform(-math.pi/6, math.pi/6)
                        dir_from_center = dir_from_center.rotate_rad(spread_angle)
                        stop_dist = entity.attack_range - 10  # Stop a bit inside range to ensure attack
                        entity.move_target = entity.attack_target.position + dir_from_center * stop_dist
                else:
                    entity.move_target = entity.attack_target.position
            # Shoot if in range
            if dist_to_target <= entity.attack_range:
                entity.shoot(closest_target, projectiles)

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
    # Cleanup dead units
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
    
    # Cleanup dead buildings
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
    
    # Cleanup unit groups
    for team, ug in g["unit_groups"].items():
        dead = [u for u in ug if hasattr(u, 'health') and u.health <= 0]
        for d in dead:
            ug.remove(d)
            if hasattr(d, 'plasma_burn_particles'):
                for p in d.plasma_burn_particles:
                    if hasattr(p, 'kill'):
                        p.kill()
                d.plasma_burn_particles = []

# =============================================================================
# Group: Menu Components
# =============================================================================

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
        self.size_small.update(mouse_pos)
        self.size_medium.update(mouse_pos)
        self.size_large.update(mouse_pos)
        self.size_huge.update(mouse_pos)
        self.size_ginormous.update(mouse_pos)
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
        self.spectate_btn.draw(surface, self.font_medium)
        self.back_btn.draw(surface, self.font_medium)

class VictoryScreen:
    def __init__(self, font_large, font_medium, is_victory):
        self.font_large = font_large
        self.font_medium = font_medium
        self.is_victory = is_victory
        self.continue_btn = MenuButton(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 80, 200, 60, "Continue", pg.Color(50, 150, 50), pg.Color(100, 200, 100))
    
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.continue_btn.is_clicked(event.pos):
                return "menu"
        return None
    
    def update(self, mouse_pos):
        self.continue_btn.update(mouse_pos)
    
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

# =============================================================================
# Group: Game Orchestrator
# =============================================================================

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
            hq.rally_point = Vector2(pos[0] + (100 if pos[0] < map_width / 2 else -100), pos[1])
            hqs[team] = hq
            units = pg.sprite.Group()
            for j in range(3):
                offset = find_free_spawn_position(pos, pos, global_buildings.sprites(), global_units.sprites())
                units.add(Infantry(offset, team))
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
            random.seed(team.value * 12345)  # Seed per team for consistent "personality" across runs
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
                                if unit_type in ["OilDerrick", "Refinery", "ShaleFracker", "BlackMarket"]:
                                    building = g["interface"].placing_cls(snapped, g["player_team"], g["player_hq"])
                                else:
                                    building = g["interface"].placing_cls(snapped, g["player_team"])
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
                            # Check for clicked enemy
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
                                    dist_to_target = unit.distance_to(clicked_enemy.position)
                                    if dist_to_target > unit.attack_range:
                                        # Chase
                                        if clicked_enemy.is_building:
                                            dir_to_center = Vector2(clicked_enemy.position) - unit.position
                                            if dir_to_center.length() > 0:
                                                dir_to_center = dir_to_center.normalize()
                                                dir_from_center = -dir_to_center
                                                spread_angle = random.uniform(-math.pi/6, math.pi/6)
                                                dir_from_center = dir_from_center.rotate_rad(spread_angle)
                                                stop_dist = unit.attack_range - 10
                                                unit.move_target = clicked_enemy.position + dir_from_center * stop_dist
                                        else:
                                            unit.move_target = clicked_enemy.position
                            else:
                                # Normal move
                                formation_positions = calculate_formation_positions(
                                    center=world_pos, target=world_pos, num_units=len(g["selected_units"])
                                )
                                for unit, pos in zip(g["selected_units"], formation_positions):
                                    unit.move_target = pos
                                    unit.attack_target = None  # Clear attack target for move order
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
            
            # Unified attacks for all teams
            unique_teams = set(g["teams"])
            for team in unique_teams:
                handle_attacks(team, unit_list, building_list, g["projectiles"], g["particles"], unit_hash, building_hash, g["alliances"])
            
            handle_projectiles(g["projectiles"], unit_list, building_list, g["particles"], g)
            
            # Cleanup dead entities
            cleanup_dead_entities(g)
            
            for ai in g["ais"]:
                their_team = ai.hq.team
                friendly_units_list = g["unit_groups"][their_team].sprites()
                friendly_buildings_list = [b for b in building_list if b.team == their_team]
                enemy_units_list = [u for team, ug in g["unit_groups"].items() if team not in ai.allies for u in ug.sprites() if u.health > 0]
                enemy_buildings_list = [b for b in building_list if b.team not in ai.allies]
                ai.update(friendly_units_list, friendly_buildings_list, enemy_units_list, enemy_buildings_list, g["global_buildings"], g["map_width"], g["map_height"])
            
            if not g.get("spectator", False):
                ally_units = [u for team in g["player_allies"] for u in g["unit_groups"][team].sprites()]
                ally_buildings = [b for b in g["global_buildings"].sprites() if b.team in g["player_allies"]]
                g["fog_of_war"].update_visibility(ally_units, ally_buildings, g["global_buildings"].sprites())
            else:
                g["fog_of_war"].update_visibility([], [], g["global_buildings"].sprites())
            
            alive_hqs = [hq for hq in g["hqs"].values() if hq.health > 0]
            if g["player_hq"] and g["player_hq"].health <= 0:
                self.state = GameState.DEFEAT
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, False)
            elif len(alive_hqs) <= 1:
                self.state = GameState.VICTORY
                self.victory_screen = VictoryScreen(self.font_large, self.font_medium, True)
            else:
                if not g.get("spectator", False):
                    player_allies = g["player_allies"]
                    other_hqs_alive = any(h.health > 0 for h in g["hqs"].values() if h.team not in player_allies)
                    if not other_hqs_alive:
                        self.state = GameState.VICTORY
                        self.victory_screen = VictoryScreen(self.font_large, self.font_medium, True)
            
            self.screen.fill(pg.Color("black"))
            
            map_color = g["map_color"]
            base_r, base_g, base_b = map_color
            zoom = g["camera"].zoom
            tile_sw = TILE_SIZE * zoom
            tile_sh = TILE_SIZE * zoom
            start_tx = max(0, int(g["camera"].rect.x // TILE_SIZE))
            start_ty = max(0, int(g["camera"].rect.y // TILE_SIZE))
            end_tx = min(g["map_width"] // TILE_SIZE, start_tx + int(g["camera"].rect.width // TILE_SIZE + 2))
            end_ty = min(g["map_height"] // TILE_SIZE, start_ty + int(g["camera"].rect.height // TILE_SIZE + 2))
            for tx in range(start_tx, end_tx):
                wx = tx * TILE_SIZE
                sx = (wx - g["camera"].rect.x) * zoom
                if sx < -tile_sw or sx > g["camera"].width:
                    continue
                for ty in range(start_ty, end_ty):
                    wy = ty * TILE_SIZE
                    sy = (wy - g["camera"].rect.y) * zoom
                    if sy < -tile_sh or sy > g["camera"].height:
                        continue
                    var_r = ((tx * 17 + ty * 31) % 41) - 20
                    var_g = ((tx * 23 + ty * 37) % 41) - 20
                    var_b = ((tx * 29 + ty * 41) % 41) - 20
                    tile_r = max(0, min(255, base_r + var_r))
                    tile_g = max(0, min(255, base_g + var_g))
                    tile_b = max(0, min(255, base_b + var_b))
                    pg.draw.rect(self.screen, (tile_r, tile_g, tile_b), (sx, sy, tile_sw, tile_sh))
                    crater_seed = (tx * 123 + ty * 456) % 100
                    if crater_seed < 5:
                        cx = sx + tile_sw / 2
                        cy = sy + tile_sh / 2
                        cr = tile_sw / 4
                        dark_r = max(0, tile_r - 40)
                        dark_g = max(0, tile_g - 40)
                        dark_b = max(0, tile_b - 40)
                        pg.draw.circle(self.screen, (dark_r, dark_g, dark_b), (int(cx), int(cy)), int(cr))
            
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
