from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias, Optional, Literal

import pygame as pg
from tcod.path import AStar
import numpy as np

from src.models.assets import fetch_surface

__all__ = ("Point", "Config", "set_global_config", "global_config", "Color", "BoardData", "BoardConfig", "Direction",
           "Mode")

Point: TypeAlias = tuple[int | float, int | float]

Color: TypeAlias = tuple[int, int, int]

Direction: TypeAlias = Literal["up", "down", "left", "right", "none"]

Mode: TypeAlias = Literal["chase", "scatter"]


@dataclass()
class BoardData:
    ghost_spawn_locations: list[Point]
    pacman_spawn_locations: list[Point]
    scatter_points: list[Point]
    points_points: list[Point]
    pacman_mask: pg.mask.Mask
    ghost_mask: pg.mask.Mask
    boundary: AStar

    @classmethod
    def from_surface(cls, surface: pg.Surface) -> BoardData:
        grid_size = global_config().grid_size
        grid: list[list[Color]] = [[(-1, -1, -1)] * (surface.get_width() // grid_size)
                                   ] * (surface.get_height() // grid_size)  # setup [y][x]

        boundary = [[1 for _ in range(surface.get_width())] for __ in range(surface.get_height())]
        points = []

        board = global_config().board
        pacman_mask = pg.Surface(surface.get_size(), flags=pg.SRCALPHA)
        ghost_mask = pg.Surface(surface.get_size(), flags=pg.SRCALPHA)
        pacman_mask.fill((0, 0, 0, 0))
        ghost_mask.fill((0, 0, 0, 0))

        _color_map: dict[Color, list[Point]] = {
            board.pacman_spawn_color: [],
            board.ghost_spawn_color: [],
            board.scatter_color: []
        }

        for x in range(surface.get_width()):
            for y in range(surface.get_height()):
                color = tuple(surface.get_at((x, y)))[:3]
                # is an increment of grid_size:
                if y % grid_size == 0 == x % grid_size:
                    grid[y // grid_size][x // grid_size] = color
                if color in _color_map.keys():
                    _color_map[color].append((x, y))
                elif color == board.wall_color:
                    pacman_mask.set_at((x, y), color)
                    ghost_mask.set_at((x, y), color)
                    boundary[y][x] = 0
                elif color == board.pacman_wall_color:
                    pacman_mask.set_at((x, y), color)

        for y in range(len(boundary)):
            for x in range(len(boundary[0])):
                touches_wall = any(0 <= y + dy < len(boundary) and 0 <= x + dx < len(boundary[0]) and boundary[y + dy][x + dx] == 0 for dx in range(-1, 2) for dy in range(-1, 2))
                if touches_wall:
                    continue
                boundary[y][x] = -1


        pac_mask = pg.mask.from_surface(pacman_mask, 1)
        ghost_mask = pg.mask.from_surface(ghost_mask, 1)

        for y in range(len(grid)):
            for x in range(len(grid[0])):
                realx, realy = x * grid_size, y * grid_size
                surf = fetch_surface(global_config().board.point_path)
                w, h = surf.get_size()
                w -= 1
                h -= 1
                if all(realx+w < surface.get_width() and
                       realy+h < surface.get_height() and surface.get_at((posx, posy)) == (0, 0, 0, 0) for posx, posy in (
                        (realx, realy),
                        (realx+w, realy),
                        (realx+w, realy+h),
                        (realx, realy+h)
                )):
                    points.append((realx, realy))
                    pg.draw.rect(surface, (1, 1, 1, 1), (realx, realy, w, h))
                elif x < 10:
                    pass

        return cls(
            ghost_spawn_locations=_color_map[board.ghost_spawn_color],
            pacman_spawn_locations=_color_map[board.pacman_spawn_color],
            pacman_mask=pac_mask,
            ghost_mask=ghost_mask,
            boundary=AStar(np.array(boundary), diagonal=0),
            points_points=points,
            scatter_points=_color_map[board.scatter_color],
        )


@dataclass(slots=True)
class BoardConfig:
    wall_color: Color
    pacman_wall_color: Color
    pacman_spawn_color: Color
    ghost_spawn_color: Color
    scatter_color: Color
    board_path: str = "board.png"
    information_path: str = "information.png"
    pacman_path: str = "pacman.png"
    pacman_open_path: str = "pacman_open.png"
    scatter_path: str = "scatter.png"
    point_path: str = "points.png"


@dataclass(slots=True)
class Config:
    screen_dimensions: tuple[int, int]
    ghost_speed: float
    pacman_speed: float
    window_name: str
    board: BoardConfig
    grid_size: int
    pool_processes: int
    incr_pacman_speed: int = 30
    scatter_duration: int = 60*20*10  # 10 seconds

    @property
    def board_surface(self) -> pg.Surface:
        return fetch_surface(self.board.board_path)


__global_config__: Optional[Config] = None


def set_global_config(config: Config) -> None:
    global __global_config__
    __global_config__ = config


def global_config() -> Config:
    if __global_config__ is None:
        raise ValueError("Global config not set")
    return __global_config__
