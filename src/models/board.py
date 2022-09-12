import dataclasses
import random
from typing import TypeAlias, Literal, Optional

import pygame as pg

from src.models.assets import fetch_surface
from src.models.config import *
from src.models.entity import PacMan


"""@dataclasses.dataclass()
class _Cell:  # this is for an optimization for collision which is probably really dumb... but idc
    is_wall: bool
    visited: bool


def collect_walls(surface: pg.Surface, wall_color: Color) -> list[pg.Rect]:  # formatted [y][x]
    cells = [[_Cell(surface.get_at((x, y)) == wall_color, False)
              for x in range(surface.get_width())] for y in range(surface.get_height())]
    walls = []
    for iy, y in enumerate(cells):
        for ix, x in enumerate(y):  # only doing horizontal slices... because I can
            start = None
            end = None
            while ix < len(y) and not (cell := cells[iy][ix]).visited and cell.is_wall:
                if start is None:
                    start = (ix, iy)
                end = (ix, iy)
                cells[iy][ix].visited = True
                ix += 1
            if start is not None:
                left, top = start
                width, height = end[0] - start[0], end[1] - start[1]
                walls.append(pg.Rect(left, top, max(1, width), max(height, 1)))
    return walls
"""


class Board:
    def __init__(self):
        self.surface = global_config().board_surface.copy()
        self.data = BoardData.from_surface(fetch_surface(global_config().board.information_path))

        self.pacman = PacMan(random.choice(self.data.pacman_spawn_locations))

    def collides_with_wall(self, mask: pg.mask.Mask, position: Point, is_ghost: bool = False) -> bool:
        rect = mask.get_rect().copy()
        rect.x, rect.y = position
        if rect.x < 0 or rect.x + rect.w > self.surface.get_width() or rect.y < 0 or rect.y\
                + rect.h > self.surface.get_height():
            return True
        p_mask = self.data.ghost_mask if is_ghost else self.data.pacman_mask
        return p_mask.overlap(mask, offset=position)

    def get_surface(self) -> pg.Surface:
        s = self.surface.copy()  # TODO ghosts
        # s.blit(fetch_surface("information.png"), (0, 0))
        s.blit(self.pacman.surface, self.pacman.pos)
        """if self.overlap is not None:
            pg.draw.circle(s, (255, 255, 0), self.overlap, 10)"""
        return s

    def update(self) -> None:
        # TODO ghosts
        self.pacman.update(self)

    def on_event(self, event: pg.event.Event) -> None:
        if event.type != pg.KEYDOWN:
            return

        direction: Direction = {pg.K_s: "down", pg.K_w: "up", pg.K_a: "left", pg.K_d: "right"}.get(event.key, "none")

        if direction != "none":
            self.pacman.change_direction(direction)
