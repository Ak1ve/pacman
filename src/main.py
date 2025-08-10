from src.models.window import Window
from src.models.config import *
from src.models.goals import *


def main():
    c = Config(
        screen_dimensions=(1150, 500),
        ghost_speed=1.25,
        ghost_aggression=10,
        pacman_speed=1.5,
        window_name="PacMan",
        board=BoardConfig(
            wall_color=(255, 255, 255),
            pacman_spawn_color=(255, 0, 0),
            ghost_spawn_color=(0, 255, 0),
            scatter_color=(255, 0, 255),
            pacman_wall_color=(0, 0, 255)
        ),
        grid_size=10,
        re_pathfind_distance=30,
        pool_processes=15,
        debug=Debug(
            draw_ghost_path=True,
            show_grid=False
        ),
        ghost_goals=[
            Goals(
                scatter=[to_random],
                chase=[to_pacman]
            ),
            Goals(
                scatter=[to_point((0, 0)), units_away_pacman(200)],
                chase=[units_away_pacman(90)]
            ),
            Goals(
                scatter=[to_random, units_away_pacman(30)],
                chase=[to_random, units_away_pacman(100), units_away_pacman(500)]
            ),
            Goals(
                scatter=[units_away_pacman(500)],
                chase=[units_away_pacman(50), units_away_pacman(100), units_away_pacman(200)]
            ),
            Goals(
                scatter=[units_away_pacman(250)],
                chase=[to_pacman, units_away_pacman(90)]
            ),
        ]
    )
    set_global_config(c)
    window = Window()

    window.run()


if __name__ == '__main__':
    main()
