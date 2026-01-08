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
    get_game_distance,
    is_game_ended,
    is_game_started,
    level_up_abilities,
    level_up_ability,
    move_random_offset,
    pan_to_ally,
    tether_offset,
    vote_surrender,
)
from utils.general_utils import click_percent, move_mouse_percent, send_keybind

# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()

    # Target ally is the preferred ally to attach to while the current ally is the one currently attached to, Ally 5 is generally the ADC
    ally_priority_list = [4, 2, 3, 1]  # Fixed order to try attaching
    attached = False
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
    time.sleep(10) # Wait for allies to leave spawn so you can properly pan camera to attach
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
            # On a timer, attach to an ally according to the priority list. If the ally is found, the timer is reset, else look for the next ally.
            # NOTE: position field in game data may help verify ADC role
            ally_index = 0
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
                pan_to_ally(ally_priority_list[ally_index])
                time.sleep(0.5) # Allow frame update
                pan_to_ally(ally_priority_list[ally_index])
                if find_ally_locations(screen_manager.get_latest_frame()):
                    # move_mouse_percent(SCREEN_CENTER[0], SCREEN_CENTER[1])
                    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1], button="right")
                    send_keybind("evtCastSpell2", _keybinds)
                    time.sleep(2) # Wait for attach animation
                # Try next ally if not found
                else:
                    logging.info(f"Ally {ally_priority_list[ally_index]} not found, trying next ally.")
                    ally_index += 1
                    # No allies found, just recall
                    if ally_index == len(ally_priority_list):
                        logging.info("No allies found, recalling.")
                        send_keybind("evtUseItem7", _keybinds)
                        time.sleep(9)
                        buy_recommended_items(screen_manager)
                        break
                    time.sleep(1) # Allow frame update
        elif attached:
            time.sleep(0.1)
            #  Periodically check if currently attached ally is dead
            send_keybind("evtCameraSnap", _keybinds, press_time=0.2)
            if not find_attached_ally_location(screen_manager.get_latest_frame()):
                attached = False
                logging.info("Detached from ally.")
                # Logic after detaching due to ally death or ally recall
                enemy = find_enemy_locations(screen_manager.get_latest_frame())
                if enemy:
                    tether_offset(SCREEN_CENTER, enemy[0], 1000)
                else:
                    buy_recommended_items(screen_manager)
                    # Move out of ally if they haven't moved yet
                    move_random_offset(SCREEN_CENTER[0], SCREEN_CENTER[1], 20)
                    time.sleep(1)
            # Attached ally logic
            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
            if enemy_locations:
                # check enemy relative location
                send_keybind("evtCameraLockToggle", _keybinds)
                enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
                attached_ally_location = find_attached_ally_location(screen_manager.get_latest_frame())
                if attached_ally_location:
                    for enemy_location in enemy_locations: 
                        distance_to_enemy = get_game_distance(attached_ally_location, enemy_location)
                        if distance_to_enemy < 600:
                            move_mouse_percent(enemy_location[0], enemy_location[1])
                            send_keybind("evtCastSpell1", _keybinds)
                            send_keybind("evtCastSpell3", _keybinds)
                            send_keybind("evtCastSpell4", _keybinds)
                            send_keybind("evtCastAvatarSpell1", _keybinds)
                            send_keybind("evtCastAvatarSpell2", _keybinds)
                            for item_key in ["evtUseItem1", "evtUseItem2", "evtUseItem3", "evtUseItem4", "evtUseItem5", "evtUseItem6"]:
                                send_keybind(item_key, _keybinds)
                            # Track Q
                            time.sleep(0.5)
                            enemy_locations = find_enemy_locations(screen_manager.get_latest_frame())
                            if enemy_locations:
                                move_mouse_percent(enemy_locations[0][0], enemy_locations[0][1])
                            break
                send_keybind("evtCameraLockToggle", _keybinds)

            
        