import threading
import logging

import importlib
from utils.config_utils import get_selected_game_mode
from core.constants import SUPPORTED_MODES

class BotManager:
    """
    Simple manager for bot threads.
    """

    def __init__(self, shutdown_event):
        self.shutdown_event = shutdown_event
        self.bot_thread = None
    

    def run_bot(self):
        """
        Runs the correct module for the selected game mode.
        """
        if self.bot_thread and self.bot_thread.is_alive():
            logging.error("Game loop is already running.")
            raise RuntimeError("Game loop is already running.")
        selected_game_mode = get_selected_game_mode()
        mode_info = SUPPORTED_MODES.get(selected_game_mode)
        logging.info(f"Starting bot for mode: {mode_info.get('module')}")
        module_name = mode_info.get("module")
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logging.error(f"Could not import module '{module_name}': {e}")
            return
        if hasattr(module, "run_game_loop"):
            try:
                self.bot_thread = threading.Thread(target=module.run_game_loop, args=(self.shutdown_event,), daemon=True)
                self.bot_thread.start()
            except TypeError:
                logging.error(f"{selected_game_mode} module implementation is not compatible.")
        else:
            logging.error(f"No entry point found for '{selected_game_mode}'.")


    def stop_bot(self, timeout=60):
        """
        Block until the game thread finishes or `timeout` elapses.
        """
        if self.bot_thread and self.bot_thread.is_alive():
            try:
                self.bot_thread.join(timeout=timeout)
            finally:
                if self.bot_thread.is_alive():
                    logging.error("Bot thread failed to exit within the given timeout.")
                    raise RuntimeError("Bot thread failed to exit within the given timeout.")
                else:
                    self.bot_thread = None
        