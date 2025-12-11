# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
import random

from core.constants import (
    HEALTH_BORDER_COLOR, ENEMY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import click_percent, poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    find_ally_location,
    find_enemy_location,
    get_distance,
    is_game_started,
    move_to_ally,
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

def shop_phase():
    """
    Handles the Arena shop phase which is detected upon level up
    """
    # Click screen center for augment cards
    time.sleep(2)
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(1)
    buy_recommended_items()
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    
def combat_phase():
    global current_ally_index
    ally_location = find_ally_location()
    if ally_location:
        # look to attack
        logging.info("ally found, looking for enemy.")
        enemy_location = find_enemy_location()
        if enemy_location:
            center_camera_key = _keybinds.get("center_camera")
            distance_to_enemy = get_distance(SCREEN_CENTER, find_enemy_location())
            keyboard.press(center_camera_key)
            time.sleep(0.1)
            keyboard.release(center_camera_key)
            
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

def run_game_loop(game_end_event):
    """
    Main loop for bot:
    - Waits for GameStart event before starting main loop
    - Runs shop phase when the active player's level increases (phase change)
    - Otherwise runs combat phase
    - Exits when monitor_game_end detects game end
    """

    # Game initialization
    polling_thread = threading.Thread(target=poll_live_client_data, args=(_latest_game_data, game_end_event), daemon=True)
    polling_thread.start()
    prev_level = 0

    while not game_end_event.is_set() and not is_game_started(_latest_game_data['data']):
        time.sleep(1)

    logging.info("Game has started.")
    time.sleep(5)
    shop_phase()
    
    # Main loop
    while not game_end_event.is_set():
        if _latest_game_data['data']:

            # Just level up
            current_level = _latest_game_data['data']["activePlayer"].get("level")
            if current_level is not None and current_level > prev_level:
                level_up_abilities()
                prev_level = current_level

            # Dead, thus shop
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            if current_hp == 0:
                shop_phase()
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
    game_end_event = threading.Event()
    run_game_loop(game_end_event)
