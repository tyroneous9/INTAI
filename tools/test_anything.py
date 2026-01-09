
import os
import sys
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import winsound
import keyboard
from core.screen_manager import ScreenManager
from utils.cv_utils import find_arena_exit_location, find_attached_ally_location, find_enemy_locations, find_player_location, find_shop_location
from utils.game_utils import get_game_distance, tether_offset
from utils.general_utils import move_mouse_percent

sm = ScreenManager()
sm.start_camera()

while True:
    keyboard.wait('v')
    frame = sm.get_latest_frame()

    player_location = find_player_location(frame)
    enemy_locations = find_enemy_locations(frame)
    if player_location and enemy_locations:
        enemy = enemy_locations[0]

    attach = find_shop_location(frame)
    if attach:
        move_mouse_percent(attach[0], attach[1])
    




    winsound.Beep(1000, 100)