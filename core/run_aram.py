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
    buy_recommended_items,
    find_ally_location,
    find_enemy_location,
    get_distance,
    is_game_ended,
    is_game_started,
    move_random_offset,
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

def shop_phase(shutdown_event):
    """
    Handles the shop phase which occurs when dead or at game start
    """
    # Click screen center for augment cards
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(0.5)
    timeout = 30
    end_time = time.time() + timeout
    while not shutdown_event.is_set():
        # Successful shopping or timeout reached
        if(buy_recommended_items() == True):
            time.sleep(0.5)
            break
        elif time.time() > end_time:
            logging.warning("Timeout reached without successfully shopping")
            return
        time.sleep(0.5)
        click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    
    
def combat_phase(latest_game_data, game_data_lock):
    global current_ally_index
    center_camera_key = _keybinds.get("center_camera")
    ally_location = find_ally_location()
    if ally_location:
        # check enemy location
        enemy_location = find_enemy_location()
        if enemy_location:
             # check enemy relative location
            keyboard.press(center_camera_key)
            time.sleep(0.01)
            enemy_location = find_enemy_location()
            if enemy_location: 
                distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
                if distance_to_enemy < 600:
                    attack_enemy()
                    move_random_offset(*SCREEN_CENTER, 15)
            keyboard.release(center_camera_key)
        else:
            # No enemy found, switch to another ally
            current_ally_index = random.randint(0, len(ally_keys) - 1)
            time.sleep(0.01)
    else:
        # look for ally
        current_ally_index = random.randint(0, len(ally_keys) - 1)
        time.sleep(0.01)
    move_to_ally(current_ally_index + 1)
    time.sleep(0.01)  # Sleep after moving to ally
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])


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
    game_ended_event = threading.Event()
    polling_thread = threading.Thread(target=poll_live_client_data, args=(latest_game_data, game_ended_event, game_data_lock), daemon=True)
    polling_thread.start()
    prev_level = 0

    while not shutdown_event.is_set():
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game loop has started.")
    time.sleep(5)
    shop_phase(shutdown_event)
    
    # Main loop
    while not shutdown_event.is_set():
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            game_ended = is_game_ended(latest_game_data)

        # Exits loop on game end
        if game_ended:
            game_ended_event.set()
            polling_thread.join()
            logging.info("Game loop has exited.")
            break

        # Level up
        if current_level > prev_level:
            level_up_abilities()
            prev_level = current_level

        # Shop or combat phase
        if current_hp == 0:
            logging.info("Entering shop phase.")
            shop_phase(shutdown_event)
            vote_surrender()
        else:
            logging.info("Entering combat phase.")
            combat_phase(latest_game_data, game_data_lock)