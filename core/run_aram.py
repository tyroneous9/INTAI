# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import ctypes
import time
import threading
import winsound
import keyboard
import logging
import random

from core.constants import (
    HEALTH_BORDER_COLOR, ENEMY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    find_ally_location,
    get_distance,
    is_game_started,
    move_to_ally,
    find_champion_location,
    buy_recommended_items,
    level_up_abilities,
    retreat,
    vote_surrender,
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
    global current_ally_index
    ally_location = find_ally_location()
    if ally_location:
        # look to attack
        logging.info("ally found, looking for enemy.")
        enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR)
        if enemy_location:
            keyboard.press(_keybinds.get("center_camera"))
            keyboard.release(_keybinds.get("center_camera"))
            distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
            if distance_to_enemy < 500:
                # Self preservation
                if _latest_game_data['data']:
                    current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
                    max_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("maxHealth")
                    if current_hp is not None and max_hp:
                        hp_percent = (current_hp / max_hp)
                        if hp_percent < .3:
                            retreat(SCREEN_CENTER, enemy_location)
                attack_enemy()
        else:
            # No enemy found, switch to another ally
            logging.info("No enemy found, switching ally.")
            current_ally_index = random.randint(0, len(ally_keys) - 1)
            time.sleep(0.18)
    else:
        # look for ally
        current_ally_index = random.randint(0, len(ally_keys) - 1)
        time.sleep(0.18)
    move_to_ally(current_ally_index + 1)
    time.sleep(0.18)  # Sleep after moving to ally


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
    prev_level = 0

    while not stop_event.is_set() and not is_game_started(_latest_game_data['data']):
        time.sleep(1)

    logging.info("Game has started.")
    buy_recommended_items()
    
    # Main loop
    while not stop_event.is_set():
        if _latest_game_data['data']:

            # Just level up
            current_level = _latest_game_data['data']["activePlayer"].get("level")
            if current_level is not None and current_level > prev_level:
                level_up_abilities()
                prev_level = current_level

            # Dead, thus shop
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            if current_hp == 0:
                buy_recommended_items()
                time.sleep(3)
                vote_surrender()
                continue

        combat_phase()

        # Small delay to allow thread switching
        time.sleep(0.01)

# For testing purposes
# python -m core.run_arena
if __name__ == "__main__":
    time.sleep(2)
    stop_event = threading.Event()
    run_game_loop(stop_event)
