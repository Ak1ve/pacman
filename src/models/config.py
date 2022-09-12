from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Optional, Literal
import pygame as pg
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
    pacman_mask: pg.mask.Mask
    ghost_mask: pg.mask.Mask
    boundary: list[list[bool]]  # setup [y][x]
    _grid: list[list[Color]]  # setup [y][x]

    @classmethod
    def from_surface(cls, surface: pg.Surface) -> BoardData:
        grid_size = global_config().grid_size
        grid: list[list[Color]] = [[(-1, -1, -1)] * (surface.get_width() // grid_size)
                                   ] * (surface.get_height() // grid_size)  # setup [y][x]

        boundary = [[False] * surface.get_width()] * surface.get_height()

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
                    boundary[y][x] = True

                elif color == board.pacman_wall_color:
                    pacman_mask.set_at((x, y), color)

        return cls(
            ghost_spawn_locations=_color_map[board.ghost_spawn_color],
            pacman_spawn_locations=_color_map[board.pacman_spawn_color],
            pacman_mask=pg.mask.from_surface(pacman_mask),
            ghost_mask=pg.mask.from_surface(ghost_mask),
            boundary=boundary,
            _grid=grid
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


@dataclass(slots=True)
class Config:
    screen_dimensions: tuple[int, int]
    ghost_speed: float
    pacman_speed: float
    window_name: str
    board: BoardConfig
    grid_size: int

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
