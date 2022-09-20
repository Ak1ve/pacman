from __future__ import annotations
import functools
import random
from multiprocessing.pool import ThreadPool, ApplyResult
from typing import TYPE_CHECKING, Optional

import pygame as pg

if TYPE_CHECKING:
    from src.models.board import Board

from src.models.pathfind import Grid
from src.models.assets import fetch_surface
from src.models.config import *
from src.models.goals import *

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
        self.has_moved = False
        self.queued_direction: Direction = "none"
        self.stopped_since = -1

    @property
    def rect(self) -> pg.Rect:
        return pg.Rect(self.x, self.y, self.surface.get_width(), self.surface.get_height())

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
        if collision := board.collides_with_wall(self.mask, (round(self.pos[0]), round(self.pos[1])),
                                                 is_ghost=self._is_ghost):
            self.advance(reverse=True)
            if recur:
                speed = self.speed
                self.change_speed(1)
                self.advance_if_able(board, recur=recur - 1)
                self.change_speed(speed)

        return not collision

    def change(self, direction: Direction) -> None:
        self.queued_direction = direction

    def update(self, board: Board) -> None:
        self.has_moved = False
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
                self.has_moved = True
        else:
            self.has_moved = self.advance_if_able(board)
        if self.has_moved:
            self.stopped_since = -1
        elif self.stopped_since == -1:
            self.stopped_since = pg.time.get_ticks()


def path_find(path: Grid, start: Point, end: Point) -> list[Point]:
    p = path.get_path(start, end)
    return p


def within(a: Point, b: Point, delta: float | int) -> bool:
    if a is None or b is None:
        return False
    x1, y1 = a
    x2, y2 = b
    return abs(x2 - x1) + abs(y2 - y1) <= delta


def get_pool() -> ThreadPool:
    if hasattr(get_pool, "__pool__"):
        return get_pool.__pool__
    get_pool.__pool__ = ThreadPool(global_config().pool_processes)
    return get_pool.__pool__


class AIEntity(Entity):
    def __init__(self, chase_goals: list[GoalFunc], scatter_goals: list[GoalFunc], *args, **kwargs):
        super().__init__(*args, is_ghost=True, **kwargs)
        self.thread: Optional[ApplyResult] = None
        self.moves: list[Point] = []
        self._current_destination: Optional[Point] = None
        self.chase_goals = chase_goals
        self.scatter_goals = scatter_goals
        self._aggression_length = 0

    def path_find_to(self, board: Board, point: Point) -> None:
        self.thread = get_pool().apply_async(path_find, (board.data.boundary, self.pos, point))
        self.change("none")
        self.moves = []

    def can_pathfind(self) -> bool:
        aggression = global_config().ghost_aggression
        length = len(self.moves) <= aggression < self._aggression_length
        return not len(self.moves) and self.thread is None or length and self.thread is None

    def scatter_pathfind(self, board: Board) -> None:
        algorithm = random.choice(self.scatter_goals)
        self.path_find_to(board, algorithm(board))

    def chase_pathfind(self, board: Board) -> None:
        algorithm = random.choice(self.chase_goals)
        self.path_find_to(board, algorithm(board))

    def move_to(self, point: Point):
        x, y = point

        if self.x == x and self.y == y:
            if len(self.moves):
                self._advance_goal()
        else:
            lst = [self.y - y, y - self.y, self.x - x, x - self.x]  # up down left right
            mx = max(lst)
            if lst.count(mx) >= 2 and len(self.moves) >= 3:
                self.move_to(self.moves[random.randint(1, 2)])
                return
            direction = ["up", "down", "left", "right"][lst.index(mx)]
            self.change(direction)  # NOQA

    def _advance_goal(self) -> None:
        if len(self.moves):
            self._current_destination = self.moves.pop(0)
            self.move_to(self._current_destination)

    def update(self, board: Board) -> None:
        last_pos = self.pos
        super().update(board)
        # polling the thread to check if complete
        if self.thread is not None and self.thread.ready():
            self.moves = self.thread.get()
            self.thread = None
            self._aggression_length = len(self.moves)

        if len(self.moves) and self._current_destination is None:
            self._current_destination = self.pos

        if within(self.pos, self._current_destination, global_config().grid_size):
            self._advance_goal()
        elif not within(self.pos, self._current_destination, global_config().re_pathfind_distance):
            self._advance_goal()
        if last_pos == self.pos and self.thread is None:
            self._advance_goal()


class Ghost(AIEntity):
    def __init__(self, chase_goals: list[GoalFunc], scatter_goals: list[GoalFunc], pos: Point,
                 surface: str):
        super().__init__(chase_goals, scatter_goals, *pos, global_config().ghost_speed, surface)
        self.start_pos = pos

    @classmethod
    def ghosts_from_data(cls, data: BoardData) -> list[Ghost]:
        c = global_config()
        random.shuffle(data.ghost_spawn_locations)
        return [Ghost(goals.chase, goals.scatter, spawn, ghost_path) for ghost_path, goals, spawn
                in zip(c.board.ghosts(), c.ghost_goals, data.ghost_spawn_locations)]

    def replace(self) -> None:
        self.pos = self.start_pos


class PacMan(Entity):
    def __init__(self, spawn_location: Point) -> None:
        c = global_config()
        self.inc = 0
        super().__init__(spawn_location[0], spawn_location[1], c.pacman_speed, c.board.pacman_path)

    @property
    def surface(self):
        incr_every = global_config().incr_pacman_speed
        if self.inc % incr_every < incr_every / 2:
            return fetch_surface(global_config().board.pacman_path)

        s = fetch_surface(global_config().board.pacman_open_path)
        return pg.transform.rotate(s, _ROT_MAP[self.direction])

    def update(self, board: Board) -> None:
        super().update(board)
        if self.has_moved:
            self.inc += 1
