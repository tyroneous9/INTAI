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
        self.lock = threading.Lock()


    def _is_bot_running(self):
        """
        Return True if the game bot thread is alive.
        """
        return bool(self.bot_thread and self.bot_thread.is_alive())
    

    def run_bot(self):
        """
        Runs the correct module for the selected game mode.
        Uses `self.shutdown_event` (if set) as the shutdown signal and passes it
        to the mode-specific `run_game_loop` implementation when present.
        """
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
                with self.lock:
                    if self._is_bot_running():
                        logging.error("Game loop is already running.")
                        raise RuntimeError("Game loop is already running.")
                self.bot_thread = threading.Thread(target=module.run_game_loop, args=(self.shutdown_event,), daemon=True)
                self.bot_thread.start()
            except TypeError:
                logging.error(f"{selected_game_mode} module implementation is not compatible.")
        else:
            logging.error(f"No entry point found for '{selected_game_mode}'.")


    def stop_bot(self, timeout=60):
        """
        Block until the game thread finishes or `timeout` elapses.
        If the timeout elapses without the thread finishing, raises a RuntimeError.
        """
        if self._is_bot_running():
            try:
                self.bot_thread.join(timeout)
            finally:
                if self.bot_thread.is_alive():
                    logging.error("Bot thread failed to exit within the given timeout.")
                    raise RuntimeError("Bot thread failed to exit within the given timeout.")
                else:
                    with self.lock:  
                        self.bot_thread = None
        