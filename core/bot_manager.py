import threading
import logging

import importlib
from utils.config_utils import get_selected_game_mode
from core.constants import SUPPORTED_MODES

class BotManager:
    """
    Simple manager for bot threads.
    """

    def __init__(self, stop_event):
        """
        Initialize the BotManager.

        Args:
            stop_event (threading.Event): Event the caller sets to request its managed thread to stop
        """
        self.stop_event = stop_event
        self._manager_thread = None
    

    def start_bot_thread(self):
        """
        Runs the correct module for the selected game mode.
        """
        if self._manager_thread and self._manager_thread.is_alive():
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
                self._manager_thread = threading.Thread(target=module.run_game_loop, args=(self.stop_event,), daemon=True)
                self._manager_thread.start()
            except TypeError:
                logging.error(f"{selected_game_mode} module implementation is not compatible.")
        else:
            logging.error(f"No entry point found for '{selected_game_mode}'.")


    def wait_for_bot_thread(self, timeout=60):
        """
        Stops the bot thread.
        """
        if self._manager_thread:
            try:
                self._manager_thread.join(timeout=timeout)
            finally:
                if self._manager_thread.is_alive():
                    logging.error("Bot thread failed to exit within the given timeout.")
                    raise RuntimeError("Bot thread failed to exit within the given timeout.")
                else:
                    self._manager_thread = None
                    logging.info("Bot thread has exited.")
        else:
            logging.error("Bot thread is not running, failed to close")
        