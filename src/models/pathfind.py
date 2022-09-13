from __future__ import annotations
import dataclasses
from typing import TypeAlias, TYPE_CHECKING
import sys

if TYPE_CHECKING:
    from src.models.config import *

import src.models.config as config

Matrix: TypeAlias = list[list[bool]]


sys.setrecursionlimit(10000000)


@dataclasses.dataclass
class Vertex:
    is_wall: bool
    visited: bool = False


def cross_sections(matrix: Matrix, grid_size: int) -> dict[Point, Vertex]:
    vertices = {}
    for y in range(0, len(matrix), grid_size):
        for x in range(0, len(matrix[0]), grid_size):
            vertices[(x, y)] = Vertex(not matrix[y][x])

    return vertices


def normalize(point: Point) -> Point:
    x, y = point
    c = config.global_config().grid_size
    return x // c * c, y // c * c


class Grid:
    def __init__(self, matrix: list[list[bool]], grid_size: int):  # setup [y][x] False == wall
        self._vertices = cross_sections(matrix, grid_size)

    def _clear_visits(self) -> None:
        for v in self._vertices.values():
            v.visited = False

    def _path(self, start: Point, end: Point, path: list[Point]) -> bool:
        if start not in self._vertices.keys():
            return False

        if start == end:
            path.append(start)
            return True

        v = self._vertices[start]
        if v.visited or v.is_wall:
            return False
        v.visited = True

        c = config.global_config().grid_size
        dx_dy = [(-c, 0), (0, -c), (c, 0), (0, c)]

        x, y = start
        for dx, dy in dx_dy:
            if self._path((x + dx, y + dy), end, path):
                path.append(start)
                return True
        return False

    def get_path(self, start: Point, end: Point) -> list[Point]:
        self._clear_visits()
        p = []
        self._path(normalize(start), normalize(end), p)
        return p
