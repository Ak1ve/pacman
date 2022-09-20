from __future__ import annotations
import dataclasses
import functools
import heapq
import math
from collections import defaultdict
from enum import Enum
from typing import TypeAlias, TYPE_CHECKING, Callable
import sys
from queue import PriorityQueue

import numpy as np

if TYPE_CHECKING:
    from src.models.config import *

import src.models.config as config

Matrix: TypeAlias = list[list[int]]  # False == wall

sys.setrecursionlimit(10000000)


@dataclasses.dataclass()
class Vertex:
    valid_vertices: list[Point]


def is_wall(matrix: Matrix, x, y) -> bool:
    return not matrix[y][x]


def cross_sections(matrix: Matrix, grid_size: int) -> dict[Point, Vertex]:
    vertices: dict[Point, Vertex] = {}
    for y in range(0, len(matrix), grid_size):
        for x in range(0, len(matrix[0]), grid_size):
            if is_wall(matrix, x, y):
                continue
            p = [(x, y-1), (x, y+1), (x+1, y), (x-1, y)]
            c = [(x, y-grid_size), (x, y+grid_size), (x+grid_size, y), (x-grid_size, y)]
            vertices[(x, y)] = Vertex(
                [pc for pp, pc in zip(p, c) if not is_wall(matrix, pp[0], pp[1])]
            )

    return vertices


def normalize(point: Point) -> Point:
    x, y = point
    c = config.global_config().grid_size
    return math.ceil(x / c) * c, math.ceil(y / c) * c


class SortingPath(Enum):
    CLOSEST = "CLOSEST"
    FARTHEST = "FARTHEST"

    def heuristic(self, a: Point, b: Point) -> float:
        h = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if self == SortingPath.CLOSEST:
            return h

        if self == SortingPath.FARTHEST:
            return -h

    def distance(self, a: Point, b: Point) -> float:
        return np.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def reconstruct_path(came_from: dict[Point, Point], current: Point) -> list[Point]:
    total_path = [current]
    while current in came_from.keys():
        current = came_from[current]
        total_path.append(current)
    return total_path[::-1]


class Grid:
    def __init__(self, matrix: list[list[int]], grid_size: int):  # setup [y][x] False == wall
        self._vertices = cross_sections(matrix, grid_size)

    def _a_star(self, start: Point, goal: Point, h: SortingPath):
        # modification of https://en.wikipedia.org/wiki/A*_search_algorithm#Pseudocode
        stack: list[tuple[float, Point]] = []

        came_from: dict[Point, Point] = {}
        g_score = {start: 0}

        f_score = {start: h.heuristic(start, goal)}

        heapq.heappush(stack, (f_score[start], start))

        while len(stack):
            current: Point = heapq.heappop(stack)[-1]  # the node in openSet having the lowest fScore[] value
            if current == goal:
                return reconstruct_path(came_from, current)

            for i, x in enumerate(stack):
                if x[-1] == current:
                    stack.pop(i)
                    break
            if current not in self._vertices:
                continue
            for neighbor in self._vertices[current].valid_vertices:
                tentative_score = g_score.get(current, math.inf) + h.distance(current, neighbor)
                if tentative_score < g_score.get(neighbor, math.inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_score
                    f_score[neighbor] = tentative_score + h.heuristic(neighbor, goal)
                    if neighbor not in [i[-1] for i in stack]:
                        heapq.heappush(stack, (f_score.get(neighbor, math.inf), neighbor))
        return []

    """def _path(self, start: Point, end: Point, path: list[Point], visited: set[Point]) -> bool:
        if start not in self._vertices.keys() or start in visited:
            return False

        if start == end:
            path.append(start)
            return True

        visited.add(start)
        for px, py in choose(SortingPath.CLOSEST, self._vertices[start].valid_vertices, end):
            if self._path((px, py), end, path, visited):
                path.append(start)
                return True
        return False"""

    def get_path(self, start: Point, end: Point, sorting_path: SortingPath = SortingPath.FARTHEST) -> list[Point]:
        return self._a_star(normalize(start), normalize(end), sorting_path)

    def valid_point(self, point: Point) -> bool:
        return normalize(point) in self._vertices
