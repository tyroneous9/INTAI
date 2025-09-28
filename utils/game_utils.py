import keyboard
import time
import numpy as np
import cv2
import logging
from core.constants import ALLY_HEALTH_BAR_COLOR, ENEMY_HEALTH_BAR_COLOR, HEALTH_BORDER_COLOR, SCREEN_CENTER
import random
from utils.config_utils import load_settings
from utils.general_utils import click_percent, find_text_location, get_screenshot

_keybinds, _general = load_settings()

# ===========================
# Game Data Utilities
# ===========================

def find_champion_location(health_bar_bgr, tolerance=2):
    """
    Finds the champion location by searching for health bar and border colors in the screenshot.
    Args:
        health_bar_bgr (tuple): BGR color of health bar.
        tolerance (int): Color tolerance.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    img = get_screenshot()

    # Build health bar mask
    lower_health_bar = np.array([max(c - tolerance, 0) for c in health_bar_bgr], dtype=np.uint8)
    upper_health_bar = np.array([min(c + tolerance, 255) for c in health_bar_bgr], dtype=np.uint8)
    mask_health_bar = cv2.inRange(img, lower_health_bar, upper_health_bar)

    # Build border mark mask
    lower_health_border = np.array([max(c - tolerance, 0) for c in HEALTH_BORDER_COLOR], dtype=np.uint8)
    upper_health_border = np.array([min(c + tolerance, 255) for c in HEALTH_BORDER_COLOR], dtype=np.uint8)
    mask_health_border = cv2.inRange(img, lower_health_border, upper_health_border)

    height, width = mask_health_bar.shape

    for y in range(height):
        for x in range(width):
            if mask_health_bar[y, x] > 0:
                nx = x - 1
                if nx >= 0 and mask_health_border[y, nx] > 0:
                    champion_location = (x+50, y+160)
                    return champion_location




def find_ally_location():
    """
    Finds the location of an ally champion by searching for ally health bar and border colors.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    return find_champion_location(ALLY_HEALTH_BAR_COLOR)


def find_enemy_location():
    """
    Finds the location of an enemy champion by searching for enemy health bar and border colors.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    return find_champion_location(ENEMY_HEALTH_BAR_COLOR)


def is_game_started(live_data):
    """
    Returns True if the GameStart event is present in live client data.
    """
    if not live_data:
        return False
    events = live_data.get("events", {}).get("Events", [])
    for event in events:
        if event.get("EventName") == "GameStart":
            return True
    return False


# ===========================
# Helper Utilities
# ===========================

def sleep_random(min_seconds, max_seconds):
    """
    Sleeps for a random duration between min_seconds and max_seconds.
    Args:
        min_seconds (float): Minimum sleep time in seconds.
        max_seconds (float): Maximum sleep time in seconds.
    """
    duration = random.uniform(min_seconds, max_seconds)
    time.sleep(duration)


def get_distance(coord1, coord2):
    """
    Calculates the Euclidean distance between two (x, y) coordinates.
    Args:
        coord1 (tuple): (x1, y1)
        coord2 (tuple): (x2, y2)
    Returns:
        float: Distance between the two points.
    """
    x1, y1 = coord1
    x2, y2 = coord2
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


# ===========================
# Game Control Core
# ===========================


def move_random_offset(x, y, max_offset=15):
    """
    Moves a random distance offset from the given (x, y) location using percent-based relative click.
    Args:
        x (int): X coordinate of the base location.
        y (int): Y coordinate of the base location.
        max_offset (int): Maximum percent screen distance in any direction.
    """
    offset_x = random.randint(-max_offset, max_offset)  # percent offset
    offset_y = random.randint(-max_offset, max_offset)  # percent offset
    click_percent(x, y, offset_x, offset_y, "right")


def level_up_abilities(order=("R", "Q", "W", "E")):
    """
    Levels up all abilities using the cached keybinds in the specified order.
    Always levels 'R' first by default.
    Args:
        order (tuple): The order in which to level up spells. Default is ("R", "Q", "W", "E").
    """
    time.sleep(0.5)  # Wait a moment to ensure level up is available
    hold_key = _keybinds.get("hold_to_level")
    spell_keys = {
        "Q": _keybinds.get("spell_1"),
        "W": _keybinds.get("spell_2"),
        "E": _keybinds.get("spell_3"),
        "R": _keybinds.get("spell_4"),
    }
    if hold_key and all(spell_keys.values()):
        for key in order:
            key = key.upper()
            if key not in spell_keys:
                logging.error(f"Invalid spell key: {key}. Must be 'Q', 'W', 'E', or 'R'.")
                continue
            keyboard.send(f"{hold_key}+{spell_keys[key]}")
            time.sleep(0.5)

def buy_recommended_items():
    """
    Finds the shop location and performs recommended item purchases.
    Opens the shop if not already open.
    Retries up to 5 times to find the shop location.
    """
    keyboard.send(_keybinds.get("shop"))
    time.sleep(0.5)  # Wait a moment to ensure shop is open

    shop_location = None
    max_attempts = 5
    attempts = 0
    # First search for shop location
    while not shop_location and attempts < max_attempts:
        shop_location = find_text_location("SELL")
        if shop_location:
            break
        attempts += 1
        time.sleep(0.2)

    # If not found, press shop key again and retry
    if not shop_location:
        logging.info("Shop not found, pressing shop key again and retrying...")
        keyboard.send(_keybinds.get("shop"))
        time.sleep(0.5)
        attempts = 0
        while not shop_location and attempts < max_attempts:
            shop_location = find_text_location("SELL")
            if shop_location:
                break
            attempts += 1
            time.sleep(0.2)

    if not shop_location:
        logging.warning("Shop could not be detected while attempting to shop.")
        return

    x, y = shop_location[:2]

    # Buy recommended item
    click_percent(x, y, 0, -62, "left")
    time.sleep(0.3)
    click_percent(x, y, 15, -25, "right")
    time.sleep(0.3)
    click_percent(x, y, 15, -25, "right")
    time.sleep(0.3)
    click_percent(x, y, 15, -25, "right")
    time.sleep(0.3)

    # Close shop
    keyboard.send(_keybinds.get("shop"))


def buy_items_list(item_list):
    """
    Buys a list of items by opening the shop, searching for each item, and attempting to buy it.
    Args:
        item_names (list of str): List of item names to buy.
    """
    keyboard.send(_keybinds.get("shop"))
    time.sleep(0.5)  # Wait for shop to open

    shop_location = None
    max_attempts = 5
    attempts = 0
    # First search for shop location
    while not shop_location and attempts < max_attempts:
        shop_location = find_text_location("SELL")
        if shop_location:
            break
        attempts += 1
        time.sleep(0.2)

    # If not found, press shop key again and retry
    if not shop_location:
        logging.info("Shop not found, pressing shop key again and retrying...")
        keyboard.send(_keybinds.get("shop"))
        time.sleep(0.5)
        attempts = 0
        while not shop_location and attempts < max_attempts:
            shop_location = find_text_location("SELL")
            if shop_location:
                break
            attempts += 1
            time.sleep(0.1)

    if not shop_location:
        logging.warning("Shop could not be detected while attempting to buy items.")
        return

    for item in item_list:
        # Focus search bar (Ctrl+L)
        keyboard.send("ctrl+l")
        time.sleep(0.2)
        # Type item name
        keyboard.write(item)
        time.sleep(0.2)
        # Attempt to buy
        keyboard.send("enter")
        time.sleep(0.2)

    # Close shop
    time.sleep(1)
    keyboard.send(_keybinds.get("shop"))
        


def move_to_ally(ally_number=1):
    """
    Pans camera to the specified ally and moves cursor to their location.
    Args:
        ally_number (int): The ally number to select (e.g., 1, 2, 3, 4).
    """

    ally_keys = {
        1: _keybinds.get("select_ally_1"),
        2: _keybinds.get("select_ally_2"),
        3: _keybinds.get("select_ally_3"),
        4: _keybinds.get("select_ally_4"),
    }
    ally_key = ally_keys.get(ally_number)
    keyboard.send(ally_key)
    time.sleep(0.3)
    # Move randomly near ally
    offset_x = random.randint(-15, 15)  # percent offset
    offset_y = random.randint(-15, 15)  # percent offset
    click_percent(SCREEN_CENTER[0], SCREEN_CENTER[1], offset_x, offset_y, "right")
    time.sleep(0.1)

def retreat(current_coords, threat_coords, duration=0.5):
    """
    Moves the player away from the threat location for a specified duration.
    Args:
        current_coords (tuple): Current (x, y) coordinates of the player.
        threat_coords (tuple): (x, y) coordinates of the threat/enemy.
        duration (float): Time in seconds to wait after retreat click (default: 0.5).
    """
    length = get_distance(current_coords, threat_coords)
    if length == 0:
        # Invalid coordinates, cannot retreat
        return

    dx = current_coords[0] - threat_coords[0]
    dy = current_coords[1] - threat_coords[1]
    # Normalize and scale (fixed offset)
    retreat_x = int(current_coords[0] + (dx / length) * 600)
    retreat_y = int(current_coords[1] + (dy / length) * 600)

    # Move cursor to retreat location and right-click
    click_percent(retreat_x, retreat_y, 0, 0, "right")
    time.sleep(duration)

    # Randomly use summoner spells
    press_sum_1 = random.choice([True, False])
    press_sum_2 = random.choice([True, False])

    if press_sum_1:
        sum_1_key = _keybinds.get("sum_1")
        if sum_1_key:
            keyboard.send(sum_1_key)
            time.sleep(0.1)
    if press_sum_2:
        sum_2_key = _keybinds.get("sum_2")
        if sum_2_key:
            keyboard.send(sum_2_key)
            time.sleep(0.1)


def attack_enemy():
    """
    Attacks the enemy by casting spells and using items.
    Searches for enemy location before each spell.
    """

    center_camera_key = _keybinds.get("center_camera")
    keyboard.press(center_camera_key)
    for spell_key in ["spell_4", "spell_1", "spell_2", "spell_3"]:
        enemy_location = find_enemy_location()
        if enemy_location:
            click_percent(enemy_location[0], enemy_location[1], 0, 0, "right")
            keyboard.send(_keybinds.get(spell_key))
            time.sleep(0.3)  # Delay to prevent spamming

    # Send all item keys at once (no location search)
    for item_key in ["item_1", "item_2", "item_3", "item_4", "item_5", "item_6"]:
        keyboard.send(_keybinds.get(item_key))
    
    # Dodging
    sleep_random(0.1, 0.3)
    move_random_offset(*SCREEN_CENTER, 15)
    sleep_random(0.1, 0.3)
    keyboard.release(center_camera_key)


def vote_surrender():
    """
    Votes to surrender by clicking the surrender button in the chat.
    Only proceeds if 'surrender' is set to True in the config.
    """
    if not _general.get("surrender", False):
        logging.info("Surrender is disabled. Skipping surrender vote.")
        return

    logging.info("Attempting to vote surrender...")
    time.sleep(0.5)
    keyboard.send("enter")
    time.sleep(0.5)
    keyboard.write("/ff")
    time.sleep(0.5)
    keyboard.send("enter")
    time.sleep(0.5)


