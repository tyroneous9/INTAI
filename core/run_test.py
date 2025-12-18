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
    find_ally_location,
    get_distance,
    is_game_ended,
    is_game_started,
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
    polling_thread = threading.Thread(target=poll_live_client_data, args=(latest_game_data, shutdown_event, game_data_lock), daemon=True)
    polling_thread.start()
    while not shutdown_event.is_set():
        if is_game_started(latest_game_data):
            break
        time.sleep(1)

    logging.info("Game has started.")
    
    # Main loop
    while not shutdown_event.is_set():
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            game_ended = is_game_ended(latest_game_data)
            # test data access
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            logging.info(f"Current HP: {current_hp}")
            current_level = latest_game_data["activePlayer"]["level"]
            logging.info(f"Current Level: {current_level}")
            
            # Exits loop on game end
            if game_ended:
                logging.info("Game loop has exited.")
                break
        # poll time delay
    
