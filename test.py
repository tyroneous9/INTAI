import logging
import time
import winsound
import keyboard
from core.screen_manager import ScreenManager
from utils.cv_utils import find_enemy_locations, find_player_location
from utils.game_utils import get_game_distance, tether_offset

sm = ScreenManager()
sm.start_camera()

while True:
    keyboard.wait('v')
    frame = sm.get_latest_frame()
    player_location = find_player_location(frame)
    enemy_locations = find_enemy_locations(frame)
    if player_location and enemy_locations:
        # use first detected enemy
        enemy = enemy_locations[0]
        distance = get_game_distance(player_location, enemy)
        print(f"distance: {distance:.2f}, player: {player_location}, enemy: {enemy}")
        tether_offset(player_location, enemy, 550)
    
    winsound.Beep(1000, 100) 