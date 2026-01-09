""" 
Template for Automation Scripts

Compatibility: Modes here

Setup: Pregame instructions here
"""

import time
import threading
import logging
from core.live_client_manager import LiveClientManager
from core.screen_manager import ScreenManager
from utils.config_utils import load_settings
from utils.game_utils import (
    is_game_ended,
    is_game_started,
    level_up_abilities,
)


# ===========================
# Main Bot Loop
# ===========================

def run_game_loop(stop_event):
    """
    Main loop called by the connector
    """

    # Initialization
    _keybinds, _general = load_settings()
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
    
    # Main game loop
    while True:
        # Fetch data
        with game_data_lock:
            current_level = latest_game_data["activePlayer"]["level"]
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
            level_up_abilities()
            prev_level = current_level

