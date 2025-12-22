import keyboard
from core.screen_manager import ScreenManager
from utils.cv_utils import find_enemy_locations
from utils.general_utils import move_percent

sm = ScreenManager(None)

while True:
    keyboard.wait('home')
    screenshot = sm.get_screenshot()
    enemies = find_enemy_locations(screenshot)
    if enemies is not None:
        for enemy in enemies:
            print(f"Found enemy at: {enemy}")