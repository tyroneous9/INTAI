# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
import random

from core.constants import (
    HEALTH_TICK_COLOR, ENEMY_HEALTH_BAR_COLOR, LEAGUE_GAME_WINDOW_TITLE, SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import terminate_window, poll_live_client_data
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
    global current_ally_index
    ally_location = find_ally_location()
    if ally_location:
        # look to attack
        enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR, HEALTH_TICK_COLOR)
        if enemy_location:
            keyboard.press(_keybinds.get("center_camera"))
            distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
            if distance_to_enemy < 500:
                # Self preservation
                if _latest_game_data['data']:
                    current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
                    max_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("maxHealth")
                    if current_hp is not None and max_hp:
                        hp_percent = (current_hp / max_hp)
                        if hp_percent < .3:
                            # Retreat away from enemy using screen center as base
                            retreat(SCREEN_CENTER, enemy_location, duration=0.5)
                            if hp_percent == 0:
                                return
                attack_enemy()
                
            keyboard.release(_keybinds.get("center_camera"))
        follow_ally(current_ally_index)
        time.sleep(0.13)  # After following ally
    else:
        # look for ally
        current_ally_index = random.randint(0, len(ally_keys) - 1)
        time.sleep(0.18)  # Sleep after random selection
    move_to_ally(current_ally_index + 1)
    time.sleep(0.18)  # Sleep after moving to ally

def follow_ally(ally_index, distance=250):
    keyboard.send(ally_keys[ally_index])
    time.sleep(0.13)  # Sleep after following ally

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

    while not stop_event.is_set() and not is_game_started(_latest_game_data['data']):
        time.sleep(3)
        
    # Main loop
    while not stop_event.is_set():
        if _latest_game_data['data']:
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            if current_hp == 0:
                zero_hp_start = time.time()
                while not stop_event.is_set():
                    current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
                    if current_hp != 0:
                        break
                    elapsed = time.time() - zero_hp_start
                    if elapsed > 100:
                        logging.info("Exiting game due to being dead for over 100 seconds.")
                        terminate_window(LEAGUE_GAME_WINDOW_TITLE)
                        return
                    time.sleep(1)
        # combat_phase()
        time.sleep(0.01)

# For testing purposes
# python -m core.run_test
if __name__ == "__main__":
    time.sleep(2)
    stop_event = threading.Event()
    run_game_loop(stop_event)
