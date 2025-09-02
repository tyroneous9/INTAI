# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
import random

from core.constants import (
    HEALTH_TICK_COLOR, ENEMY_HEALTH_BAR_COLOR, SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import click_percent, poll_live_client_data, find_text_location
from utils.game_utils import (
    attack_enemy,
    find_ally_location,
    get_distance,
    move_random_offset,
    move_to_ally,
    find_champion_location,
    buy_recommended_items,
    level_up_abilities,
    retreat_to_ally,
    sleep_random,
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
    ally_location = find_ally_location()
    if ally_location:
        # look to attack
        enemy_location = find_champion_location(ENEMY_HEALTH_BAR_COLOR, HEALTH_TICK_COLOR)
        if enemy_location:
            keyboard.press(_keybinds.get("center_camera"))
            time.sleep(0.08)
            keyboard.release(_keybinds.get("center_camera"))
            distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
            if distance_to_enemy < 600:
                attack_enemy()
                # Self preservation
                if _latest_game_data['data']:
                    current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
                    max_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("maxHealth")
                    if current_hp is not None and max_hp:
                        hp_percent = (current_hp / max_hp)
                        if hp_percent < .3:
                            retreat_to_ally(current_ally_index + 1)
                            if hp_percent == 0:
                                return
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
    Main loop for Arena bot:
    - Waits for GameStart event before starting main loop
    - Runs shop phase when the active player's level increases (phase change)
    - Otherwise runs combat phase
    - Exits when monitor_game_end detects game end
    """

    # Game initialization
    polling_thread = threading.Thread(target=poll_live_client_data, args=(_latest_game_data, stop_event), daemon=True)
    polling_thread.start()
    prev_level = 0
    logging.info("Bot has started.")

    while not stop_event.is_set():
        if _latest_game_data['data']:
            # Shop phase
            current_level = _latest_game_data['data']["activePlayer"].get("level")
            if current_level is not None and current_level > prev_level:
                for _ in range(current_level - prev_level):
                    # Level up abilities
                    level_up_abilities()
                prev_level = current_level
                
            # Dead, thus shop
            current_hp = _latest_game_data['data']["activePlayer"].get("championStats", {}).get("currentHealth")
            if current_hp == 0:
                logging.info("Player is dead, now shopping.")
                buy_recommended_items()
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
