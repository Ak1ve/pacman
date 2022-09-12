from pathlib import Path
from functools import cache


import pygame as pg


__path__ = (Path(__file__).parent.parent.parent / "assets").absolute()


@cache
def fetch_surface(path: str | bytes) -> pg.Surface:
    return pg.image.load(str(__path__ / path)).convert_alpha()
