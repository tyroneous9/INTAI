import logging
import threading
import time
import requests
import urllib3
from core.constants import DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL


class LiveClientManager:
    """
    Simple manager for the live client API.
    """

    def __init__(self, stop_event, lock):
        """
        Initialize the LiveClientManager.

        Args:
            stop_event (threading.Event): Event the caller sets to request its managed thread to stop
            lock (threading.Lock): Lock used to protect updates to the shared `latest_game_data_container`.
        """
        self.stop_event = stop_event
        self.internal_stop_event = threading.Event()
        self.lock = lock
        self._manager_thread = None
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


    def start_polling_thread(self, latest_game_data_container, poll_time=0.1):
        """
        Continuously polls live client data and updates the provided container. Container returns None if data was not successfully retrieved.
        Exits when stop_event is set.
        Args:
            latest_game_data_container (dict): Container to store latest data.
            poll_time (int): Poll interval in seconds.
        """
        self.internal_stop_event.clear()
        if self._manager_thread and self._manager_thread.is_alive():
            logging.error("Polling thread is already running.")
            raise RuntimeError("Polling thread is already running.")
        def _loop():
            while not self.stop_event.is_set() and not self.internal_stop_event.is_set():
                data = self.fetch_live_client_data()
                # If the API call failed or returned None, skip update and retry
                if data is None:
                    time.sleep(poll_time)
                    continue

                # Replace the contents of the shared container with the latest data
                try:
                    with self.lock:
                        latest_game_data_container.update(data)
                except Exception:
                    logging.error("Failed to update latest_game_data_container with fetched data")
                    raise RuntimeError("Failed to update latest_game_data_container with fetched data")
                time.sleep(poll_time)
        
        self._manager_thread = threading.Thread(target=_loop, daemon=True)
        self._manager_thread.start()
    
    def stop_polling_thread(self, timeout=60):
        """ 
        Stops the polling thread.
        """
        self.internal_stop_event.set()
        if self._manager_thread:
            try:
                self._manager_thread.join(timeout=timeout)
            finally:
                if self._manager_thread.is_alive():
                    logging.error("Polling thread failed to exit within the given timeout.")
                    raise RuntimeError("Polling thread failed to exit within the given timeout.")
                else:
                    self._manager_thread = None
                    logging.info("Polling thread has exited.")
        else:
            logging.info("Polling thread is not running, nothing to stop.")
        
    
    def fetch_live_client_data(self):
        """
        Retrieves all game data from the live client API.
        Returns:
            dict or None: Game data if successful, else None.
        """
        try:
            res = requests.get(f"{LIVE_CLIENT_URL}/allgamedata", timeout=DEFAULT_API_TIMEOUT, verify=False)
            if res.status_code == 200:
                return res.json()
            else:
                logging.warning("Request succeeded, but game data not found.")
                time.sleep(5)
                return None
        except Exception as e:
            logging.error("Game data request failed.")
            time.sleep(5)
            return None