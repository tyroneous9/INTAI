""" 
ARAM Mode Automation Script

Compatibility: ARAM, ARAM Mayhem

Setup: No special setup required
"""


import time
import threading
import keyboard
import logging
from core.constants import SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.general_utils import click_percent
from utils.game_utils import (
    attack_enemy,
    buy_recommended_items,
    get_distance,
    is_game_ended,
    is_game_started,
    move_random_offset,
    pan_to_ally,
    level_up_abilities,
    vote_surrender,
)
from utils.cv_utils import find_ally_locations, find_augment_location, find_enemy_locations, find_player_location

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()
    center_camera_key = _keybinds.get("center_camera")

    ally_priority_list = [1,2,3,4]
    current_ally_index = 0
    prev_level = 0

    game_data_lock = threading.Lock()
    latest_game_data = {}
    live_client_manager = LiveClientManager(stop_event, game_data_lock)
    live_client_manager.start_polling_thread(latest_game_data)

    screen_manager = ScreenManager()
    screen_manager.start_camera(target_fps=60)

    # Wait for game start
    while True:
        if stop_event.is_set(): 
            return
        if is_game_started(latest_game_data) == True:
            break
        time.sleep(1)

    logging.info("Game loop has started.")

    # Initialize champion data
    with game_data_lock:
        attack_range = latest_game_data["activePlayer"]["championStats"]["attackRange"]
    if attack_range <= 350:
        logging.info("Detected melee champion.")
        attack_range = attack_range + 300
    else:
        logging.info("Detected ranged champion.")
        attack_range = attack_range

    start_time = time.time()
    
    # Main game loop
    while True:
        # Fetch data
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
            current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
            game_ended = is_game_ended(latest_game_data)

        # Exits loop on game end or shutdown
        if game_ended or stop_event.is_set():

            live_client_manager.stop_polling_thread()
            screen_manager.stop_camera()
            logging.info("Game loop has ended.")

            elapsed = int(time.time() - start_time)
            hrs = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60
            logging.info("Game loop duration: %02d:%02d:%02d", hrs, mins, secs)
            return

        # Check for augment
        augment = find_augment_location(screen_manager.get_latest_frame())
        if augment:
            click_percent(augment[0], augment[1])
            time.sleep(0.5)
            buy_recommended_items(screen_manager)
            time.sleep(0.5)

        # Level up
        if current_level > prev_level:
            level_up_abilities()
            prev_level = current_level

        # Shop if dead, continue otherwise
        if current_hp == 0:
            end_time = 20 + time.monotonic()
            while not game_ended and not stop_event.is_set():
                augment = find_augment_location(screen_manager.get_latest_frame())
                if augment:
                    click_percent(augment[0], augment[1])
                if buy_recommended_items(screen_manager) == True:
                    break
                elif time.monotonic() > end_time:
                    break
                time.sleep(1)
            vote_surrender()
            continue

        # Combat phase
        pan_to_ally(ally_priority_list[current_ally_index])
        move_random_offset(SCREEN_CENTER[0], SCREEN_CENTER[1])
        ally_locations = find_ally_locations(screen_manager.get_latest_frame())
        if ally_locations:
            # check enemy location
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            if enemy_locations:
                # pan on self with necessary pause to allow camera to update
                keyboard.press(center_camera_key)
                time.sleep(0.5)
                enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
                player_location = find_player_location(screen_manager.get_latest_frame())
                if player_location:
                    for enemy_location in enemy_locations: 
                        distance_to_enemy = get_distance(player_location, enemy_location)
                        if distance_to_enemy < attack_range:
                            attack_enemy(enemy_location)
                            break
                keyboard.release(center_camera_key) 
            else:
                # ally but no enemy, try next ally
                current_ally_index = (current_ally_index + 1) % len(ally_priority_list)
            time.sleep(1)
            

        else:
            # look for ally
            for i in range(len(ally_priority_list)):
                pan_to_ally(ally_priority_list[i])
                if find_ally_locations(screen_manager.get_latest_frame()):
                    current_ally_index = i
                    break
        time.sleep(0.01) 