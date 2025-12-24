import logging
import keyboard
from core.constants import AUGMENT_LOWER_COLOR, AUGMENT_UPPER_COLOR
from core.screen_manager import ScreenManager
from utils.cv_utils import extract_image_text, find_augment_location, find_enemy_locations, find_shop_location, save_color_mask
from utils.general_utils import move_percent

sm = ScreenManager()
sm.start_camera()
while True:
    keyboard.wait('home')
    frame = sm.get_latest_frame()
    shop = find_shop_location(frame)
    if shop:
        move_percent(shop[0], shop[1])

