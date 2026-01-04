""" 
ARAM Mode Automation Script

Compatibility: ARAM, ARAM Mayhem

Setup: No special setup required
"""


import time
import threading
import logging
from core.constants import SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.general_utils import click_percent, move_mouse_percent, send_keybind, send_keybind
from utils.game_utils import (
    attack_enemy,
    buy_recommended_items,
    get_distance,
    is_game_ended,
    is_game_started,
    move_random_offset,
    pan_to_ally,
    level_up_abilities,
    tether_offset,
    vote_surrender,
)
from utils.cv_utils import find_ally_locations, find_augment_location, find_enemy_locations, find_player_location


    

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()

    game_data_lock = threading.Lock()
    latest_game_data = {}
    live_client_manager = LiveClientManager(stop_event, game_data_lock)
    live_client_manager.start_polling_thread(latest_game_data)

    screen_manager = ScreenManager()
    screen_manager.start_camera(target_fps=60)

    # Wait for game start
    while True:
        if stop_event.is_set(): 
            return
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game loop has started")

    # Warm the camera
    time.sleep(1)
    distances = [725]

    for input_distance in distances:
        player = find_player_location(screen_manager.get_latest_frame())
        enemies = find_enemy_locations(screen_manager.get_latest_frame())
        tether_offset(player, enemies[0], input_distance)
        # give the game a moment to process the move and update screen
        time.sleep(2)
        player = find_player_location(screen_manager.get_latest_frame())
        enemies = find_enemy_locations(screen_manager.get_latest_frame())
        actual = get_distance(player, enemies[0])
        diff = actual - input_distance
        logging.info("Requested=%d Measured=%.2f Diff=%.2f", input_distance, actual, diff)
        # update player for the next iteration

    # Cleanup and exit test
    live_client_manager.stop_polling_thread()
    screen_manager.stop_camera()
    logging.info("Tether tests complete")
    return

