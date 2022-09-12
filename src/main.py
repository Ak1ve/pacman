from src.models.window import Window
from src.models.config import *


def main():
    c = Config(
        screen_dimensions=(1150, 500),
        ghost_speed=1,
        pacman_speed=1,
        window_name="PacMan",
        board=BoardConfig(
            wall_color=(255, 255, 255),
            pacman_spawn_color=(255, 0, 0),
            ghost_spawn_color=(0, 255, 0),
            scatter_color=(255, 0, 255),
            pacman_wall_color=(0, 0, 255)
        ),
        grid_size=10
    )
    set_global_config(c)
    window = Window()

    window.run()


if __name__ == '__main__':
    main()