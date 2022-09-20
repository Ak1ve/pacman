from __future__ import annotations

import pygame as pg

from src.models.config import *
from src.models.board import Board


class Window:
    def __init__(self):
        self.display = pg.display.set_mode(global_config().screen_dimensions)
        pg.display.set_caption(global_config().window_name)
        self.board = Board()
        self.clock = pg.time.Clock()

    def run(self):
        is_running = True
        while is_running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    is_running = False
                self.board.on_event(event)
            self.board.update()
            self.draw()
            self.clock.tick(60)

    def draw(self):
        self.display.fill((255, 255, 255))
        self.display.blit(self.board.get_surface(), (0, 0))
        pg.display.flip()
