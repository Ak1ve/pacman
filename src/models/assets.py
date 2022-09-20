from pathlib import Path
from functools import cache


import pygame as pg


__path__ = (Path(__file__).parent.parent.parent / "assets").absolute()


@cache
def fetch_surface(path: str | bytes) -> pg.Surface:
    p = (__path__ / path)
    p = str(p) if p.exists() else path
    return pg.image.load(p).convert_alpha()
