# ==========================================================
# Arena Mode Automation Script
# ==========================================================

import time
import threading
import keyboard
import logging
import random

from core.constants import (
    SCREEN_CENTER
)
from utils.config_utils import load_settings
from utils.general_utils import click_percent, poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    buy_items_list,
    find_ally_location,
    find_enemy_location,
    get_distance,
    is_game_ended,
    is_game_started,
    move_to_ally,
    level_up_abilities,
    retreat,
    vote_surrender,
)


# ===========================
# Initialization
# ===========================

_keybinds, _general = load_settings()
# latest_game_data is created in run_game_loop and passed to threads/functions

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
    Handles the shop phase which occurs when dead or at game start
    """
    # Click screen center for augment cards
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(0.2)
    start = time.time()
    timeout = 20
    while(True):
        # Successful shopping or timeout reached
        if(buy_items_list(["","",""]) == True):
            break
        elif(time.time() - start > timeout):
            logging.warning("Timeout reached without successfully shopping")
            return
        time.sleep(0.1)
    time.sleep(0.2)
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    
def combat_phase(latest_game_data, game_data_lock):
    global current_ally_index
    center_camera_key = _keybinds.get("center_camera")
    ally_location = find_ally_location()
    if ally_location:
        # check enemy location
        logging.info("ally found, looking for enemy.")
        enemy_location = find_enemy_location()
        if enemy_location:
             # check enemy relative location
            keyboard.press(center_camera_key)
            time.sleep(0.01)
            enemy_location = find_enemy_location()
            if enemy_location: 
                distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
                if distance_to_enemy < 500:
                    # Self preservation before attacking
                    with game_data_lock:
                        ap = latest_game_data["activePlayer"]
                        champ_stats = ap.get("championStats") 
                        current_hp = champ_stats.get("currentHealth")
                        max_hp = champ_stats.get("maxHealth")
                    hp_percent = (current_hp / max_hp)
                    if hp_percent < .3:
                        retreat(SCREEN_CENTER, enemy_location)
                    attack_enemy()
            keyboard.release(center_camera_key)
        else:
            # No enemy found, switch to another ally
            logging.info("No enemy found, switching ally.")
            current_ally_index = random.randint(0, len(ally_keys) - 1)
            time.sleep(0.1)
    else:
        # look for ally
        current_ally_index = random.randint(0, len(ally_keys) - 1)
        time.sleep(0.1)
        click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    move_to_ally(current_ally_index + 1)
    time.sleep(0.1)  # Sleep after moving to ally


# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(shutdown_event):
    """
    Main loop called by the connector
    """

    # Game initialization
    latest_game_data = {}
    game_data_lock = threading.Lock()
    polling_thread = threading.Thread(target=poll_live_client_data, args=(latest_game_data, shutdown_event, game_data_lock), daemon=True)
    polling_thread.start()
    prev_level = 0

    while not shutdown_event.is_set():
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game has started.")
    time.sleep(5)
    shop_phase()
    
    # Main loop
    while not shutdown_event.is_set():
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            game_ended = is_game_ended(latest_game_data)

        # Level up
        if current_level is not None and current_level > prev_level:
            level_up_abilities()
            prev_level = current_level

        # Dead, thus shop
        if current_hp == 0:
            shop_phase()
            vote_surrender()
            continue

        # Exits loop on game end
        if game_ended:
            logging.info("Game loop has exited.")
            break

        # Combat phase
        combat_phase(latest_game_data, game_data_lock)

    logging.info("Bot thread has exited.")
