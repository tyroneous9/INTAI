
import os
import sys
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import time
import winsound
import keyboard
from core.screen_manager import ScreenManager
from utils.cv_utils import find_arena_exit_location, find_attached_ally_location, find_enemy_locations, find_player_location, find_shop_location
from utils.game_utils import get_game_distance, tether_offset
from utils.general_utils import move_mouse_percent

screen_manager = ScreenManager()
screen_manager.start_camera()

while True:
    # keyboard.wait('v')
    frame = screen_manager.get_latest_frame()

    # player_location = find_player_location(frame)
    # enemy_locations = find_enemy_locations(frame)
    # if player_location and enemy_locations:
    #     enemy = enemy_locations[0]

    exit_button = find_arena_exit_location(screen_manager.get_latest_frame())
    if exit_button:
        move_mouse_percent(exit_button[0], exit_button[1])

    # winsound.Beep(1000, 100)
    time.sleep(0.5)