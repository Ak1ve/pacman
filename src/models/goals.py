from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, TypeAlias
from random import randint

if TYPE_CHECKING:
    from src.models.board import Board

from src.models.config import *


GoalFunc: TypeAlias = "Callable[[Board], Point]"


__all__ = ("to_random", "to_pacman", "to_point", "units_away_pacman", "GoalFunc")


def to_random(board: Board) -> Point:
    w, h = global_config().screen_dimensions
    while True:
        if board.data.boundary.valid_point(p := (randint(0, w), randint(0, h))):
            return p


def to_pacman(board: Board) -> Point:
    return board.pacman.pos


def to_point(point: Point) -> GoalFunc:
    def i(board: Board) -> Point:  # NOQA
        return point
    return i


def units_away_pacman(units: int) -> GoalFunc:
    def i(board: Board) -> Point:
        px, py = board.pacman.pos
        x, y = 9999, 9999
        theta = 0
        dtheta = .15
        while not board.data.boundary.valid_point((x, y)):
            theta += dtheta
            x = px + units * math.cos(theta)
            y = py + units * math.sin(theta)
        return x, y
    return i
