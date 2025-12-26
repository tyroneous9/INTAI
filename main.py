# python -m core.main

import asyncio
import logging
import threading
import random
import time
import winsound
from utils.config_utils import (
    get_selected_game_mode, load_config
)
from core.constants import (
    LEAGUE_GAME_WINDOW_TITLE,
    SUPPORTED_MODES,
    LCU_GAMEFLOW_PHASE,
    LCU_CHAMP_SELECT_SESSION,
    LEAGUE_CLIENT_WINDOW_TITLE,
    GAMEFLOW_PHASES,
    CHAMP_SELECT_SUBPHASES
)
from utils.general_utils import bring_window_to_front, enable_logging, listen_for_exit, wait_for_window
from core.menu import show_menu  
from core.LCU_Manager import LCUManager

# State variables
shutdown_event = threading.Event()

# Module instances
lcu_manager = LCUManager(shutdown_event)

# Connector event handlers moved to `core/LCU_Manager.py`.


# ===========================
# Script Functions
# ===========================

 
def run_script():
    logging.info("Starting Script. Waiting for client...")
    lcu_manager.start()

def shutdown():
    logging.info("Shutting down program...")
    shutdown_event.set()

    # Stop connector/manager
    try:
        lcu_manager.stop()
    except Exception:
        logging.exception("Error while stopping LCU manager")

    # Wait for bot thread
    try:
        lcu_manager.bot_manager.wait_for_bot_thread()
    except Exception:
        logging.exception("Error while waiting for bot thread")

    logging.info("Shut down complete.")
    winsound.Beep(500,200)

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    """
    Main entry point for the League Bot Launcher.
    Handles menu navigation and starts the connector.
    """
    enable_logging()
    listen_for_exit(shutdown)
    show_menu(run_script)



