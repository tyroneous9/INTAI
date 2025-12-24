# ==========================================================
# Test Mode Script
# ==========================================================

import time
import threading
import logging

from core.constants import (
    SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import click_percent, poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    is_game_ended,
    is_game_started,
    log_game_data,
)
from utils.cv_utils import ScreenManager, find_ally_locations, find_augment_location, find_enemy_locations

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(shutdown_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()
    ally_keys = [
        _keybinds.get("select_ally_1"),
        _keybinds.get("select_ally_2"),
        _keybinds.get("select_ally_3"),
        _keybinds.get("select_ally_4"),
    ]

    screen_manager = ScreenManager()
    screen_manager.start(fps=30)

    latest_game_data = {}
    game_data_lock = threading.Lock()
    stop_event = threading.Event()
    polling_thread = poll_live_client_data(latest_game_data, stop_event, game_data_lock)
    
    current_ally_index = 0
    prev_level = 0

    # Wait for game start
    while not shutdown_event.is_set():
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game loop has started.")
    
    # Main game loop
    while not shutdown_event.is_set():
        # Fetch data
        with game_data_lock:
            game_ended = is_game_ended(latest_game_data)
            log_game_data(latest_game_data)
            
        # Exits loop on game end
        if game_ended:
            polling_thread.join()
            logging.info("Game loop has exited.")
            break

        # Check for augment
        augment = find_augment_location(screen_manager.get_latest_frame())
        if augment:
            click_percent(augment[0], augment[1])
            time.sleep(0.5)

        # test interval
        time.sleep(5)
    
