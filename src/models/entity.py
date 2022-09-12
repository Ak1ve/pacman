from __future__ import annotations
from typing import TYPE_CHECKING, TypeAlias, Literal
from dataclasses import dataclass

import pygame as pg


if TYPE_CHECKING:
    from src.models.board import Board

from src.models.assets import fetch_surface
from src.models.config import *

_DIR_MAP: dict[Direction, Point] = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0), "none": (0, 0)}


class Entity:
    def __init__(self,
                 x: int | float,
                 y: int | float,
                 speed: int | float,
                 surface_path: str,
                 add_direction: Point = (0, 0),
                 is_ghost: bool = False):
        self.x, self.y = x, y
        self.speed = speed
        self.surface = fetch_surface(surface_path)
        self._add_direction = add_direction
        self._is_ghost = is_ghost

        self.mask = pg.mask.from_surface(self.surface)

    @property
    def pos(self) -> Point:
        return self.x, self.y

    @pos.setter
    def pos(self, value: Point):
        self.x, self.y = value

    def change_direction(self, direction: Direction) -> None:
        add_x, add_y = _DIR_MAP[direction]
        self._add_direction = (self.speed * add_x, self.speed * add_y)

    def advance(self, *, reverse: bool = False) -> None:
        x, y = self._add_direction if not reverse else (-x for x in self._add_direction)
        self.x += x
        self.y += y

    def on_event(self, event: pg.event.Event) -> None:
        pass

    def update(self, board: Board) -> None:
        if self._add_direction == (0, 0):
            # don't have to move... if you can't lol
            return

        self.advance()
        r = self.mask.get_rect()
        r.x, r.y = 0, 0
        if board.collides_with_wall(self.mask, self.pos, is_ghost=self._is_ghost):
            self.advance(reverse=True)
            self.change_direction("none")  # can no longer move


class AIEntity(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, is_ghost=True, **kwargs)
        self.moves: list[Point] = []

    def path_find_to(self, board: Board, point: Point, *, moves: list[Point] = None) -> None:
        if moves is None:
            moves = []


class PacMan(Entity):
    def __init__(self, spawn_location: Point) -> None:
        c = global_config()
        super().__init__(spawn_location[0], spawn_location[1], c.pacman_speed, c.board.pacman_path)
        self.queued_direction: Direction = "none"

    def change(self, direction: Direction) -> None:
        self.queued_direction = direction

    def update(self, board: Board) -> None:
        if self.queued_direction != "none":
            self.change_direction(self.queued_direction)
        super().update(board)



