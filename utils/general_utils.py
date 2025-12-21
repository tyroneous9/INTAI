import datetime
import os
import threading
import psutil
import requests
import win32gui
import win32api
import win32con
import time
import keyboard
import logging
import win32process
from core.constants import (
    DEFAULT_API_TIMEOUT, LIVE_CLIENT_URL,
    DATA_DRAGON_VERSIONS_URL, DATA_DRAGON_DEFAULT_LOCALE
)

# ===========================
# API Utilities
# ===========================


def fetch_live_client_data():
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


def poll_live_client_data(latest_game_data_container, game_ended_event, game_data_lock, poll_time=0.1):
    """
    Continuously polls live client data and updates the provided container. Container returns None if data was not successfully retrieved.
    Exits when stop_event is set.
    Args:
        latest_game_data_container (dict): Container to store latest data.
        stop_event (threading.Event): Event to signal polling should stop.
        poll_time (int): Poll interval in seconds.
    """
    
    # Validate event parameter
    if game_ended_event is None or game_data_lock is None:
        logging.error("poll_live_client_data requires valid threading parameters.")
        return

    while not game_ended_event.is_set():
        data = fetch_live_client_data()
        # If the API call failed or returned None, skip update and retry
        if data is None:
            time.sleep(poll_time)
            continue

        # Replace the contents of the shared container with the latest data
        try:
            with game_data_lock:
                latest_game_data_container.update(data)
        except Exception:
            logging.error("Failed to update latest_game_data_container with fetched data")
            raise RuntimeError("Failed to update latest_game_data_container with fetched data")
        time.sleep(poll_time)


def fetch_data_dragon_data(endpoint, version=None, locale=DATA_DRAGON_DEFAULT_LOCALE):
    """
    Fetches static data from Riot Data Dragon.
    Args:
        endpoint (str): The endpoint, e.g. "champion".
        version (str, optional): Patch version. If None, fetches latest.
        locale (str): Language code, default from constants.
    Returns:
        dict: The JSON data from Data Dragon, or {} on failure.
    """
    try:
        if not version:
            versions = requests.get(DATA_DRAGON_VERSIONS_URL, timeout=5).json()
            version = versions[0]
        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/{locale}/{endpoint}.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Failed to fetch Data Dragon data for endpoint '{endpoint}': {e}")
        return {}

def get_champions_map():
    """
    Fetches champion data from Riot Data Dragon and returns a {id: name} mapping.
    Returns:
        dict: {champion_id: champion_name}
    """
    data = fetch_data_dragon_data("champion")
    champions_map = {}
    for champ in data.get("data", {}).values():
        champions_map[int(champ["key"])] = champ["name"]
    return champions_map


# ===========================
# Mouse and Keyboard Actions
# ===========================


def listen_for_exit(shutdown):
        """
        Listens for the exit key and then sets the shutdown_event.
        """
        def _listener(shutdown):
            logging.info("Press DELETE key to exit anytime.")
            keyboard.wait("delete")
            shutdown()
        exit_listener_thread = threading.Thread(target=_listener, args=(shutdown,), daemon=True)
        exit_listener_thread.start()
    

def click_percent(x, y, x_offset_percent=0, y_offset_percent=0, button="left"):
    """
    Clicks at (x, y) plus an optional offset specified as percent of window size.
    Args:
        x (int): Base X coordinate.
        y (int): Base Y coordinate.
        x_offset_percent (float): Offset in percent of window width.
        y_offset_percent (float): Offset in percent of window height.
        button (str): 'left' or 'right' mouse button.
    """
    hwnd = win32gui.GetForegroundWindow()
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    window_width = right - left
    window_height = bottom - top

    # Apply percent offset if provided
    new_x = x + int(window_width * (x_offset_percent / 100.0))
    new_y = y + int(window_height * (y_offset_percent / 100.0))

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    win32api.SetCursorPos((new_x, new_y))
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, new_x, new_y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, new_x, new_y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, new_x, new_y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, new_x, new_y, 0, 0)
    else:
        logging.warning(f"Unknown mouse button: {button}. Use 'left' or 'right'.")


def click_on_cursor(button="left"):
    """
    Simulates a mouse click at the current cursor position.
    """
    x, y = win32api.GetCursorPos()
    if button == "left":
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    elif button == "right":
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
    else:
        logging.warning(f"Unknown mouse button: {button}. Use 'left' or 'right'.")
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def enable_logging(log_file=None, level=logging.INFO):
    # Remove all handlers associated with the root logger object
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    if log_file is None:
        if not os.path.exists("logs"):
            os.makedirs("logs")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        log_file = f"logs/{timestamp}.log"
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def wait_for_window(window_title, timeout=60):
    """
    Waits for a window with the specified title to appear.
    Returns:
        int | None: Window handle if found, otherwise None.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            return hwnd
        time.sleep(1)

    logging.warning(f"Window '{window_title}' did not appear within {timeout} seconds.")
    return None


def bring_window_to_front(window_title, timeout=60, retry_delay=0.5):
    """
    Finds a window by title and repeatedly attempts to bring it to the foreground
    until successful or until timeout is reached.

    Args:
        window_title (str): Title of the window.
        timeout (int): Maximum time to keep trying (seconds).
        retry_delay (float): Delay between attempts (seconds).

    Returns:
        int | None: Window handle if successful, otherwise None.
    """
    end_time = time.time() + timeout
    hwnd = None

    while time.time() < end_time:
        hwnd = win32gui.FindWindow(None, window_title)

        if not hwnd:
            time.sleep(retry_delay)
            continue

        try:
            # Restore if minimized
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)

            win32gui.SetForegroundWindow(hwnd)
            return hwnd  # success

        except Exception as e:
            logging.debug(
                f"Failed to bring '{window_title}' to front (hwnd={hwnd}): {e}"
            )

        time.sleep(retry_delay)

    logging.error(
        f"Failed to bring window '{window_title}' to front after {timeout} seconds."
    )
    return None


def terminate_window(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        # Get process ID from window handle
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid)
            proc.terminate()  # or proc.kill() for immediate termination
            logging.info(f"Process {pid} terminated for window '{window_title}'.")
        except Exception as e:
            logging.error(f"Failed to terminate process {pid}: {e}")
    else:
        logging.warning(f"Window '{window_title}' not found.")