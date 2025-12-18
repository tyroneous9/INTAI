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
from utils.general_utils import click_percent, find_text_location, poll_live_client_data
from utils.game_utils import (
    attack_enemy,
    buy_items_list,
    find_enemy_location,
    get_distance,
    is_game_ended,
    is_game_started,
    move_to_ally,
    level_up_abilities,
    sleep_random,
    vote_surrender,
)


# ===========================
# Initialization
# ===========================

_keybinds, _general = load_settings()

# latest_game_data is created inside run_game_loop and passed to threads/functions


# ===========================
# Phase Functions
# ===========================

def shop_phase():
    """
    Handles the Arena shop phase which is detected upon level up
    """
    # Click screen center for augment cards
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    time.sleep(0.5)
    start = time.time()
    timeout = 30
    while(True):
        # Successful shopping or timeout reached
        if(buy_items_list(["","",""]) == True):
            break
        elif(time.time() - start > timeout):
            logging.warning("Timeout reached without successfully shopping")
            return
        time.sleep(0.1)
    time.sleep(0.5)
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
    level_up_abilities()


def combat_phase(latest_game_data, game_data_lock):
    # kept signature for compatibility; no live-data reads here
    """
    Handles the combat phase:
    - Finds enemy champion location and attacks w/ spells and items
    - If no enemy found, find and move toward ally
    """
    enemy_location = find_enemy_location()
    if enemy_location:
        # Move to enemy
        click_percent(enemy_location[0], enemy_location[1], 0, 0, "right")
        center_camera_key = _keybinds.get("center_camera")
        keyboard.press(center_camera_key)
        time.sleep(0.01)
        keyboard.release(center_camera_key)
        # When within combat distance
        distance_to_enemy = get_distance(SCREEN_CENTER, enemy_location)
        if distance_to_enemy < 500:      
            attack_enemy()
    else:
        # Move to ally
        move_to_ally(1)
        sleep_random(0.1, 0.2)

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
        with game_data_lock:
            started = is_game_started(latest_game_data)
        if started:
            break
        time.sleep(1)
    
    logging.info("Game has started.")

    # Main loop
    while not shutdown_event.is_set():
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            game_ended = is_game_ended(latest_game_data)

        # Exit game
        if current_hp == 0:
            logging.info("Player is dead, searching for exit button...")
            for label in ["EXITNOW", "EXIT", "EXT"]:
                exit_box = find_text_location(label)
                if exit_box:
                    x, y, w, h = exit_box
                    click_percent(x, y)
                    break
                else:
                    time.sleep(1)
            continue

        if game_ended:
            break

        # Shop phase
        if current_level > prev_level:
            time.sleep(5)
            shop_phase()
            prev_level = current_level
            vote_surrender()
            continue

        combat_phase(latest_game_data, game_data_lock)
    logging.info("Bot thread has exited.")

