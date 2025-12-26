import logging
import time
import keyboard
from core.constants import AUGMENT_LOWER_COLOR, AUGMENT_UPPER_COLOR
from core.screen_manager import ScreenManager
from utils.cv_utils import extract_image_text, find_arena_exit_location, find_attached_ally_location, find_augment_location, find_enemy_locations, find_player_location, find_shop_location, save_color_mask
from utils.general_utils import move_mouse_percent

sm = ScreenManager()
sm.start_camera()

while True:
    keyboard.wait('home')
    frame = sm.get_latest_frame()
    location = find_attached_ally_location(frame)
    if location:
        move_mouse_percent(location[0], location[1])
        print(f"location: {location}")

    while True:
        location = find_player_location(sm.get_latest_frame())
        if location:
            print(f"found")
        else:
            print(f"not found")
        time.sleep(0.2)

