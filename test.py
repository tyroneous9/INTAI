import keyboard
from core.constants import AUGMENT_BORDER_COLOR, AUGMENT_INNER_COLOR, ENEMY_HEALTH_INNER_COLOR, HEALTH_BORDER_COLOR
from utils.cv_utils import ScreenManager, find_enemy_location, save_champion_location, save_color_mask
from utils.general_utils import click_percent

screen = ScreenManager(shutdown_event=None)

while True:
    keyboard.wait('home')
    screenshot = screen.get_single_frame()
    save_color_mask(screenshot, HEALTH_BORDER_COLOR, tolerance=0)
    # save_champion_location(screenshot, AUGMENT_INNER_COLOR, tolerance=40)
    enemy = find_enemy_location(screenshot)
    if enemy:
        click_percent(enemy[0], enemy[1], 0, 0, "left")
        print("found")
    else:
        print("not found")