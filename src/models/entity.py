from __future__ import annotations
import functools
from multiprocessing.pool import ThreadPool, ApplyResult
import time
from typing import TYPE_CHECKING, Optional

import pygame as pg
from tcod.path import AStar
import numpy as np

if TYPE_CHECKING:
    from src.models.board import Board

from src.models.assets import fetch_surface
from src.models.config import *

_DIR_MAP: dict[Direction, Point] = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0), "none": (0, 0)}
_ROT_MAP: dict[Direction, int] = {"up": 90, "down": -90, "left": 180, "right": 0, "none": 0}


@functools.cache
def mask_from_path(path: str, threshold: int = 127) -> pg.mask.Mask:
    return pg.mask.from_surface(fetch_surface(path), threshold)


class SimpleSprite:
    def __init__(self, path: str, pos: Point):
        self.x, self.y = pos
        self.surface = fetch_surface(path)
        self.mask = mask_from_path(path)

    @classmethod
    def scatter_at(cls, x_y: Point) -> SimpleSprite:
        return cls(
            global_config().board.scatter_path,
            x_y
        )

    @classmethod
    def point_at(cls, x_y: Point) -> SimpleSprite:
        return cls(
            global_config().board.point_path,
            x_y
        )

    @property
    def pos(self):
        return self.x, self.y

    def collides_with(self, other) -> bool:
        offset_x = other.x - self.x
        offset_y = other.y - self.y
        return bool(self.mask.overlap_area(other.mask, (offset_x, offset_y)))


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
        self._surface_path = surface_path
        self._add_direction = add_direction
        self._is_ghost = is_ghost
        self.direction: Direction = "none"
        self.mask = pg.mask.from_surface(self.surface, 1)

    @property
    def surface(self):
        return fetch_surface(self._surface_path)

    @property
    def pos(self) -> Point:
        return self.x, self.y

    @pos.setter
    def pos(self, value: Point):
        self.x, self.y = value

    def change_speed(self, speed: int | float) -> None:
        self.speed = speed
        self.change_direction(self.direction)

    def change_direction(self, direction: Direction) -> None:
        add_x, add_y = _DIR_MAP[direction]
        self._add_direction = (self.speed * add_x, self.speed * add_y)
        self.direction = direction

    def advance(self, *, reverse: bool = False) -> None:
        x, y = self._add_direction if not reverse else (-x for x in self._add_direction)
        self.x += x
        self.y += y

    def on_event(self, event: pg.event.Event) -> None:
        pass

    def advance_if_able(self, board: Board, *, recur: int = 4) -> bool:
        """

        :param board:
        :param recur:
        :return: true if advancement made
        """
        self.advance()
        r = self.mask.get_rect()
        r.x, r.y = 0, 0
        if collision := board.collides_with_wall(self.mask, (round(self.pos[0]), round(self.pos[1])), is_ghost=self._is_ghost):
            self.advance(reverse=True)
            if recur:
                speed = self.speed
                self.change_speed(1)
                self.advance_if_able(board, recur=recur - 1)
                self.change_speed(speed)

        return not collision

    def update(self, board: Board) -> None:
        if self._add_direction == (0, 0):
            # don't have to move... if you can't lol
            return

        self.advance_if_able(board)


def path_find(path: AStar, start: Point, end: Point) -> list[Point]:
    p = path.get_path(*start, *end)
    return p


def get_pool() -> ThreadPool:
    if hasattr(get_pool, "_pool"):
        return get_pool._pool
    get_pool._pool = ThreadPool(processes=global_config().pool_processes)
    return get_pool._pool


class AIEntity(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, is_ghost=True, **kwargs)
        self.thread: Optional[ApplyResult] = None
        self.moves: list[Point] = []

    def path_find_to(self, board: Board, point: Point) -> None:
        self.thread = get_pool().apply_async(path_find, (board.data.boundary, self.pos, point))

    def move_to(self, point: Point):
        x, y = point
        if x > self.x:
            self.change_direction("right")
        elif x < self.x:
            self.change_direction("left")
        elif y > self.y:
            self.change_direction("down")
        elif y < self.y:
            self.change_direction("up")
        else:
            self.change_direction("none")

    def update(self, board: Board) -> None:
        # polling the thread to check if complete
        super().update(board)
        if self.thread is not None and self.thread.ready():
            self.moves = self.thread.get()
            print(self.moves)
            self.thread = None
        if self.thread is not None and not self.thread.ready():
            self.change_direction("none")
            self.moves = []  # don't do anything if it's waiting
        if len(self.moves):
            self.move_to(self.moves.pop(0))


class Ghost(AIEntity):
    def __init__(self, pos: Point, surface: str = "pacman.png"):
        # TODO not do pacman but instead a global config
        super().__init__(*pos, global_config().ghost_speed, surface)


class PacMan(Entity):
    def __init__(self, spawn_location: Point) -> None:
        c = global_config()
        self.inc = 0
        super().__init__(spawn_location[0], spawn_location[1], c.pacman_speed, c.board.pacman_path)
        self.queued_direction: Direction = "none"

    @property
    def surface(self):
        incr_every = global_config().incr_pacman_speed
        if self.inc % incr_every < incr_every / 2:
            return fetch_surface(global_config().board.pacman_path)

        s = fetch_surface(global_config().board.pacman_open_path)
        return pg.transform.rotate(s, _ROT_MAP[self.direction])

    def change(self, direction: Direction) -> None:
        self.queued_direction = direction

    def update(self, board: Board) -> None:
        has_moved = False
        if self.queued_direction != "none":
            direction = self.direction
            self.change_direction(self.queued_direction)
            moved = self.advance_if_able(board)
            if not moved:
                self.change_direction(direction)
                self.advance_if_able(board)
            else:
                self.direction = self.queued_direction
                self.queued_direction = "none"
                has_moved = True
        else:
            has_moved = self.advance_if_able(board)
        if has_moved:
            self.inc += 1


