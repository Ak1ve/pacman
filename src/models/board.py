import dataclasses
import functools
import random
from typing import TypeAlias, Literal, Optional

import pygame as pg

from src.models import pathfind
from src.models.assets import fetch_surface
from src.models.config import *
from src.models.entity import PacMan, SimpleSprite, AIEntity, Ghost
from src.models.goals import *

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

        self.scatters: list[SimpleSprite] = [SimpleSprite.scatter_at(pos) for pos in self.data.scatter_points]
        self.points = [SimpleSprite.point_at(x) for x in self.data.points_points]
        self.mode: Mode = "chase"
        self.pacman = PacMan(random.choice(self.data.pacman_spawn_locations))
        self.time_since_chase = pg.time.get_ticks()

        self.ghosts: list[Ghost] = Ghost.ghosts_from_data(self.data)

    def collides_with_wall(self, mask: pg.mask.Mask, position: Point, is_ghost: bool = False) -> bool:
        rect = mask.get_rect().copy()
        rect.x, rect.y = position
        if rect.x < 0 or rect.x + rect.w > self.surface.get_width() or rect.y < 0 or rect.y\
                + rect.h > self.surface.get_height():
            return True
        p_mask = self.data.ghost_mask if is_ghost else self.data.pacman_mask
        return p_mask.overlap(mask, offset=position)

    @staticmethod
    @functools.cache
    def grid() -> pg.Surface:
        w, h = global_config().screen_dimensions
        s = pg.Surface((w, h), flags=pg.SRCALPHA)
        grid = global_config().grid_size
        for x in range(0, w, grid):
            pg.draw.line(s, (15, 155, 0, 255), (x, 0), (x, h))
            pg.draw.line(s, (15, 155, 0, 255), (0, x), (w, x))
        s.set_alpha(80)
        return s

    def get_surface(self) -> pg.Surface:
        s = self.surface.copy().convert_alpha()
        perc_scatter_done = (pg.time.get_ticks() - self.time_since_chase) / global_config().scatter_duration

        for x in self.ghosts:
            if self.mode == "chase" or (r := int(perc_scatter_done * 100)) % 2 == 0 and r >= 80:
                s.blit(x.surface, x.pos)
            else:
                s.blit(pg.transform.rotate(x.surface, 90), x.pos)

        for x in self.scatters:
            s.blit(x.surface, x.pos)

        for x in self.points:
            s.blit(x.surface, x.pos)

        if debug().draw_ghost_path:
            for g in self.ghosts:
                if len(g.moves) >= 2:
                    pg.draw.lines(s, (255, 255, 0), False, g.moves)

        if debug().show_grid:
            s.blit(self.grid(), (0, 0))

        s.blit(self.pacman.surface, self.pacman.pos)
        return s

    def collides_with_list(self, l: list[SimpleSprite]) -> bool:
        pops = []
        has = False
        for i, x in enumerate(l):
            if x.collides_with(self.pacman):
                pops.append(i)
                has = True
        for x in pops[::-1]:
            l.pop(x)
        return has

    def collides_with_scatter(self) -> bool:
        # collide for scatter
        return self.collides_with_list(self.scatters)

    def collides_with_point(self) -> bool:
        return self.collides_with_list(self.points)

    def update(self) -> None:
        # TODO ghosts
        self.pacman.update(self)
        start_chase = False
        start_scatter = False
        if self.collides_with_scatter():
            start_scatter = self.mode == "chase"
            self.mode = "scatter"
            self.time_since_chase = pg.time.get_ticks()
        if self.collides_with_point():
            pass
        if self.time_since_chase + global_config().scatter_duration < pg.time.get_ticks() and self.mode == "scatter":
            start_chase = self.mode == "scatter"
            self.mode = "chase"

        for ghost in self.ghosts:
            ghost.update(self)
            collides = ghost.rect.colliderect(self.pacman.rect)
            if collides and self.mode == "scatter":
                ghost.replace()
                continue
            elif collides:
                pg.event.post(pg.event.Event(pg.QUIT))

            can_path = ghost.can_pathfind()
            if can_path and self.mode == "scatter" or start_scatter:
                ghost.scatter_pathfind(self)
            elif can_path or start_chase:
                ghost.chase_pathfind(self)

    def on_event(self, event: pg.event.Event) -> None:
        if event.type != pg.KEYDOWN:
            return

        direction: Direction = {pg.K_s: "down", pg.K_w: "up", pg.K_a: "left", pg.K_d: "right"}.get(event.key, "none")

        if direction != "none":
            self.pacman.change(direction)
