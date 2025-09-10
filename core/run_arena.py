# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging

from core.constants import (
    SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import click_percent, find_text_location, poll_live_client_data, terminate_window
from utils.game_utils import (
    attack_enemy,
    buy_recommended_items,
    find_enemy_location,
    get_distance,
    is_game_started,
    move_to_ally,
    level_up_abilities,
    retreat,
    sleep_random,
    vote_surrender,
)


# ===========================
# Initialization
# ===========================

_keybinds, _general = load_settings()
_latest_game_data = {'data': None}


# ===========================
# Phase Functions
# ===========================

def shop_phase():
    """
    Handles the Arena shop phase which is detected upon level up
    """
    # Click screen center for augment cards
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(1)
    buy_recommended_items()
    time.sleep(2)
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(2)
    # Level up abilities
    level_up_abilities()


def combat_phase():
    """
    Handles the combat phase:
    - Finds enemy champion location and attacks w/ spells and items
    - If no enemy found, find and move toward ally
    """
    center_camera_key = _keybinds.get("center_camera")
    keyboard.press(center_camera_key)
    enemy_location = find_enemy_location()
    keyboard.release(center_camera_key)
    if enemy_location:
        # Move to enemy
        click_percent(enemy_location[0], enemy_location[1], 0, 0, "right")
    
        # When within combat distance
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
    else:
        # Move to ally
        move_to_ally(1)
        sleep_random(0.1, 0.3)

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

    # Notify user that game has started
    import winsound
    winsound.MessageBeep()
    
    logging.info("Game has started.")

    # Main loop
    while not stop_event.is_set():
        if _latest_game_data['data']:
             
            # Exit game
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            if current_hp == 0:
                logging.info("Player is dead, searching for exit button...")
                click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1], -3, -17)
                time.sleep(1)
                continue

            # Shop phase
            current_level = _latest_game_data['data']["activePlayer"].get("level")
            if current_level is not None and current_level > prev_level:
                time.sleep(5)
                shop_phase()
                prev_level = current_level
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
