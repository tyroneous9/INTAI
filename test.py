import logging
import time
import keyboard
from core.constants import AUGMENT_LOWER_COLOR, AUGMENT_UPPER_COLOR
from core.screen_manager import ScreenManager
from utils.cv_utils import extract_image_text, find_arena_exit_location, find_attached_ally_location, find_augment_location, find_enemy_locations, find_player_location, find_shop_location, save_color_mask
from utils.game_utils import get_distance
from utils.general_utils import move_mouse_percent

sm = ScreenManager()
sm.start_camera()

while True:
    keyboard.wait('home')
    frame = sm.get_latest_frame()
    player_location = find_player_location(frame)
    enemy_locations = find_enemy_locations(frame)
    print(f"player: {player_location}")
    print(f"enemies: {enemy_locations}")
    print(f"distance: {get_distance(player_location, enemy_locations[0])}")


