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
from utils.general_utils import click_percent, terminate_window, poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    find_ally_location,
    get_distance,
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
_latest_game_data = {'data': None}

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

def run_game_loop(stop_event):
    """
    Main loop for bot:
    - Waits for GameStart event before starting main loop
    - Runs shop phase when the active player's level increases (phase change)
    - Otherwise runs combat phase
    - Exits when monitor_game_end detects game end
    """

    # Game initialization
    polling_thread = threading.Thread(target=poll_live_client_data, args=(_latest_game_data, stop_event), daemon=True)
    polling_thread.start()
        
    # Main loop
    while not stop_event.is_set():
        combat_phase()
        time.sleep(0.01)

# For testing purposes
# python -m core.run_test
if __name__ == "__main__":
    time.sleep(2)
    stop_event = threading.Event()
    run_game_loop(stop_event)
