""" 
Yuumi Bot Automation Script

Compatibility: Summoner's Rift

Setup: Set preferred champion to Yuumi in settings
"""

import time
import threading
import logging

import keyboard
from core.constants import SCREEN_CENTER
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.cv_utils import find_ally_locations, find_attached_ally_location, find_attached_ally_location, find_enemy_locations
from utils.game_utils import (
    buy_recommended_items,
    get_distance,
    is_game_ended,
    is_game_started,
    level_up_abilities,
    level_up_ability,
    pan_to_ally,
    vote_surrender,
)
from utils.general_utils import move_mouse_percent

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()
    spell_keys = [
        _keybinds.get("spell_1"),
        _keybinds.get("spell_2"),
        _keybinds.get("spell_3"),
        _keybinds.get("spell_4"),
        _keybinds.get("sum_1"),
        _keybinds.get("sum_2")
    ]
    recall_key = _keybinds.get("recall")
    center_camera_key = _keybinds.get("center_camera")

    # Target ally is the preferred ally to attach to while the current ally is the one currently attached to, Ally 5 is generally the ADC
    ally_priority_list = [4, 1, 2, 3]  # Order to try attaching
    attached = False
    attach_timeout = 2
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
    start_time = time.time()
    buy_recommended_items(screen_manager) 
    
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

        # Level up
        if current_level > prev_level:
            if current_level == 1:
                level_up_ability('E')
            elif current_level == 2:
                level_up_ability('Q')
            else:
                level_up_abilities(order=('R', 'E', 'Q', 'W'))
            prev_level = current_level

        # Shop if dead, continue otherwise
        if current_hp == 0:
            end_time = 20 + time.monotonic()
            while not game_ended and not stop_event.is_set():
                if buy_recommended_items(screen_manager) == True:
                    break
                elif time.monotonic() > end_time:
                    break
                time.sleep(1)
            vote_surrender()
            continue

        if not attached:
            # Attach to target ally if alive, other allies if dead
            # NOTE: position field in game data may help verify ADC role
            end_time = time.time() + attach_timeout
            ally_number = ally_priority_list[0]
            while not game_ended and not stop_event.is_set():
                # Check if dead
                with game_data_lock:
                    current_hp = latest_game_data["activePlayer"]["championStats"]["currentHealth"]
                if current_hp == 0:
                    logging.info("Died while trying to attach.")
                    break
                # Check if attached successfully
                attached_ally_location = find_attached_ally_location(screen_manager.get_latest_frame())
                if attached_ally_location:
                    logging.info("Successfully attached.")
                    attached = True
                    break
                # Attempt to attach
                pan_to_ally(ally_number)
                if find_ally_locations(screen_manager.get_latest_frame()):
                    move_mouse_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
                    keyboard.send(spell_keys[1])
                    time.sleep(3)
                    end_time = time.time() + attach_timeout
                if time.time() > end_time:
                    logging.info("Attach window timed out.")
                    break
            if not attached:
                logging.info("No allies found, recalling.")
                keyboard.send(recall_key) 
                time.sleep(9)
                buy_recommended_items(screen_manager)
        elif attached:
            time.sleep(0.1)
            #  Periodically check if currently attached ally is dead
            keyboard.press(center_camera_key)
            time.sleep(0.01)
            keyboard.release(center_camera_key) 
            if not find_attached_ally_location(screen_manager.get_latest_frame()):
                attached = False
                logging.info("Attached ally gone, detaching.")
                continue
            # Attached ally logic
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            if enemy_locations:
                # check enemy relative location
                keyboard.press(center_camera_key)
                time.sleep(0.01)
                keyboard.release(center_camera_key) 
                enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
                attached_ally_location = find_attached_ally_location(screen_manager.get_latest_frame())
                if attached_ally_location:
                    for enemy_location in enemy_locations: 
                        distance_to_enemy = get_distance(attached_ally_location, enemy_location)
                        if distance_to_enemy < 600:
                            move_mouse_percent(enemy_location[0], enemy_location[1])
                            keyboard.send(spell_keys[0])
                            keyboard.send(spell_keys[2])
                            keyboard.send(spell_keys[3])
                            keyboard.send(spell_keys[4])
                            keyboard.send(spell_keys[5])
                            for item_key in ["item_1", "item_2", "item_3", "item_4", "item_5", "item_6"]:
                                keyboard.send(_keybinds.get(item_key))
                            break

            
        