# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
import random

from core.constants import (
    HEALTH_BORDER_COLOR, ENEMY_HEALTH_BAR_COLOR, LEAGUE_GAME_WINDOW_TITLE, SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    buy_items_list,
    find_ally_location,
    get_distance,
    is_game_ended,
    is_game_started,
    log_game_data,
    move_to_ally,
    find_champion_location,
    buy_recommended_items,
    retreat,
)


# ===========================
# Initialization
# ===========================

_keybinds, _general = load_settings()

ally_keys = [
    _keybinds.get("select_ally_1"),
    _keybinds.get("select_ally_2"),
    _keybinds.get("select_ally_3"),
    _keybinds.get("select_ally_4"),
]

current_ally_index = 0


# ===========================
# Phase Functions
# ===========================

def combat_phase():
    attack_enemy()

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(shutdown_event):
    """
    Module entrypoint
    """

    # Game initialization
    latest_game_data = {}
    game_data_lock = threading.Lock()
    game_ended_event = threading.Event()
    polling_thread = threading.Thread(target=poll_live_client_data, args=(latest_game_data, game_ended_event, game_data_lock), daemon=True)
    polling_thread.start()
    
    while not shutdown_event.is_set():
        if is_game_started(latest_game_data):
            break
        time.sleep(1)

    logging.info("Game has started.")
    
    # Main loop
    while not shutdown_event.is_set():
        with game_data_lock:
            game_ended = is_game_ended(latest_game_data)
            log_game_data(latest_game_data)
            
        
        # Exits loop on game end
        if game_ended:
            game_ended_event.set()
            polling_thread.join()
            logging.info("Game loop has exited.")
            break
            
        # test shop
        # buy_items_list([""])

        # test interval
        time.sleep(5)
    
