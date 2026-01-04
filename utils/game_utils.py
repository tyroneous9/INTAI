import keyboard
import time
import logging
import requests
from core.constants import DATA_DRAGON_DEFAULT_LOCALE, DATA_DRAGON_VERSIONS_URL, SCREEN_CENTER
import random
from utils.config_utils import load_settings
from utils.cv_utils import find_shop_location
from utils.general_utils import click_percent, send_keybind, move_mouse_percent

_keybinds, _general = load_settings()


# ===========================
# Data Dragon Utilities
# ===========================


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
        try:
            cid = int(champ.get("key"))
        except Exception:
            continue
        champions_map[cid] = champ.get("name")
    return champions_map


# ===========================
# Game Data Utilities
# ===========================


def is_game_started(game_data):
    """
    Returns (bool):
        True if the GameStart event is present in live client data.
    """
    if not game_data:
        return False
    events = game_data.get("events", {}).get("Events", [])
    for event in events:
        if event.get("EventName") == "GameStart":
            return True
    return False


def is_game_ended(game_data):
    """
    Returns (bool):
        True if the GameEnd event is present in live client data or there is no more game data.
    """
    if not game_data:
        return True
    events = game_data["events"]["Events"]
    for event in events:
        if event["EventName"] == "GameEnd":
            return True
    return False


def log_game_data(game_data):
    """
    Logs key game data for debugging purposes.
    Args:
        game_data (dict): Live client game data.
    """
    if not game_data:
        logging.info("No game data available.")
        return

    def _format_obj(obj, indent=0):
        pad = '  ' * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                lines.append(f"{pad}{k}: {_format_obj(v, indent+1)}")
            return "\n".join(lines)
        if isinstance(obj, list):
            lines = []
            for i, item in enumerate(obj):
                lines.append(f"{pad}- {_format_obj(item, indent+1)}")
            return "\n".join(lines)
        return str(obj)
    
    current_hp = game_data["activePlayer"]["championStats"]["currentHealth"]
    max_hp = game_data["activePlayer"]["championStats"]["maxHealth"]
    current_level = game_data["activePlayer"]["level"]
    events = game_data.get("events", {})

    logging.info(f"Player Level: {current_level}")
    logging.info(f"Current HP: {current_hp} / {max_hp}")

    try:
        logging.info("Events:\n%s", _format_obj(events))
    except Exception:
        logging.exception("Failed formatting events; logging raw repr.")
        logging.info("Events: %s", repr(events))


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
# Game Control Utilities
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


def level_up_abilities(order=('R', 'Q', 'W', 'E')):
    """
    Levels up all abilities in the specified order.
    Always levels 'R' first by default.
    Args:
        order (tuple): The order in which to level up spells. Default is ('R', 'Q', 'W', 'E').
    """
    event_map = {
        'Q': 'evtLevelSpell1',
        'W': 'evtLevelSpell2',
        'E': 'evtLevelSpell3',
        'R': 'evtLevelSpell4',
    }
    for key in order:
        k = key.upper()
        evt = event_map.get(k)
        if not evt:
            logging.error(f"Invalid key parameter: {k}. Must be Q, W, E, or R.")
            continue
        send_keybind(evt, _keybinds)


def level_up_ability(ability='R'):
    """
    Levels up a single ability.
    Always levels 'R' first by default.
    Args:
        ability (char): The ability to level up. Default is 'R'.
    """
    event_map = {
        'Q': 'evtLevelSpell1',
        'W': 'evtLevelSpell2',
        'E': 'evtLevelSpell3',
        'R': 'evtLevelSpell4',
    }
    k = ability.upper()
    evt = event_map.get(k)
    if not evt:
        logging.error(f"Invalid ability parameter: {ability}. Must be Q, W, E, or R.")
        return
    send_keybind(evt, _keybinds)


def buy_recommended_items(screen_manager):
    """
    Finds the shop location and performs recommended item purchases.
    Opens the shop if not already open.
    Returns true if shop was successfully opened and also closed after purchase.
    Args:
        screen_manager (ScreenManager): The screen manager instance.
    NOTE:
        Augment popups will automatically close the shop and also nullify interaction with it.
    """
    shop_location = find_shop_location(screen_manager.get_latest_frame())
    
    # Open shop if not already open
    if not shop_location:
        send_keybind("evtOpenShop", _keybinds)
        time.sleep(0.5)
        shop_location = find_shop_location(screen_manager.get_latest_frame())
        if not shop_location:
            send_keybind("evtOpenShop", _keybinds)
            time.sleep(0.5)
            return False

    # Shop found, now buy items
    x, y = shop_location[:2]
    click_percent(x, y, 0, -64, "left")
    time.sleep(0.5)
    click_percent(x, y, 15, -25, "right")
    click_percent(x, y, 15, -25, "right")
    time.sleep(0.5)

    # Ensure shop is closed
    send_keybind("evtOpenShop", _keybinds)
    time.sleep(0.5)
    if find_shop_location(screen_manager.get_latest_frame()):
        return False
    return True


def buy_items_list(screen_manager, item_list):
    """
    Buys a list of items by opening the shop, searching for each item, and attempting to buy it.
    Args:
        item_names (list of str): List of item names to buy.
    NOTE: Shop CANNOT be obstructed (by augment popups or other UI elements) or else chat will be opened instead.
    """
    shop_location = find_shop_location(screen_manager.get_latest_frame())
        
    # Open shop if not already open
    if not shop_location:
        send_keybind("evtOpenShop", _keybinds)
        time.sleep(0.5)
        shop_location = find_shop_location(screen_manager.get_latest_frame())
        if not shop_location:
            time.sleep(0.5)
            send_keybind("evtOpenShop", _keybinds)
            return False

    # Shop found, now buy items
    for item in item_list:
        keyboard.send("ctrl+l")
        time.sleep(0.5)
        keyboard.write(item)
        time.sleep(0.5)
        keyboard.send("enter")
        time.sleep(0.5)

    # Ensure shop is closed
    send_keybind("evtOpenShop", _keybinds)
    time.sleep(0.5)
    if find_shop_location(screen_manager.get_latest_frame()):
        return False
    return True


def pan_to_ally(ally_number=1):
    """
    Pans camera to the specified ally and moves cursor to their location.
    Args:
        ally_number (int): The ally number to select (e.g., 1, 2, 3, 4).
    """
    if ally_number == 1:
        send_keybind("evtSelectAlly1", _keybinds, press_time=0.01)
    elif ally_number == 2:
        send_keybind("evtSelectAlly2", _keybinds, press_time=0.01)
    elif ally_number == 3:
        send_keybind("evtSelectAlly3", _keybinds, press_time=0.01)
    elif ally_number == 4:
        send_keybind("evtSelectAlly4", _keybinds, press_time=0.01)
    else:
        logging.error(f"Invalid ally number: {ally_number}. Must be 1, 2, 3, or 4.")
    

def retreat(current_coords, threat_coords, retreat_distance_modifier=1.0):
    """
    Moves the player away from the threat location by a distance proportional to the
    current separation multiplied by `retreat_distance_modifier`.

    Args:
        current_coords (tuple): Current (x, y) coordinates of the player.
        threat_coords (tuple): (x, y) coordinates of the threat/enemy.
        retreat_distance_modifier (float): Multiplier applied to the current distance
            between player and threat to compute how far to move away. For example,
            a value of 1.2 will move to 120% of the current separation in the
            opposite direction. (Default: 1.0)
    """
    length = get_distance(current_coords, threat_coords)
    if length == 0:
        logging.error("Cannot retreat: current coordinates are the same as threat coordinates.")
        return

    dx = current_coords[0] - threat_coords[0]
    dy = current_coords[1] - threat_coords[1]

    # Determine retreat distance proportional to current separation
    retreat_distance = int(length * retreat_distance_modifier)
    # Fallback to a sensible minimum so very small distances still move
    if retreat_distance < 50:
        retreat_distance = 50

    # Normalize direction and scale by retreat_distance
    retreat_x = int(current_coords[0] + (dx / length) * retreat_distance)
    retreat_y = int(current_coords[1] + (dy / length) * retreat_distance)

    # Move toward calculated retreat location
    click_percent(retreat_x, retreat_y, 0, 0, "right")

    # Small fixed pause to let retreat action complete
    time.sleep(0.1)

def attack_enemy(enemy_coords):
    """
    Attacks the enemy by casting spells and using items.
    Args:
        enemy_coords (tuple): (x, y) coordinates of the enemy.
    """
    move_mouse_percent(enemy_coords[0], enemy_coords[1])
    send_keybind("evtPlayerAttackMoveClick", _keybinds)
    send_keybind("evtCastSpell1", _keybinds)
    send_keybind("evtCastSpell2", _keybinds)
    send_keybind("evtCastSpell3", _keybinds)
    send_keybind("evtCastSpell4", _keybinds)
    send_keybind("evtSelfCastAvatarSpell1", _keybinds)
    send_keybind("evtSelfCastAvatarSpell2", _keybinds)
    send_keybind("evtUseItem1", _keybinds)
    send_keybind("evtUseItem2", _keybinds)
    send_keybind("evtUseItem3", _keybinds)
    send_keybind("evtUseItem4", _keybinds)
    send_keybind("evtUseItem5", _keybinds)
    send_keybind("evtUseItem6", _keybinds)
    


def vote_surrender():
    """
    Votes to surrender by typing the surrender command in chat.
    Only proceeds if 'surrender' is set to True in the config.
    """
    if not _general.get("surrender", False):
        return

    time.sleep(1)
    keyboard.send("enter")
    time.sleep(0.5)
    keyboard.write("/ff")
    time.sleep(1)
    keyboard.send("enter")
    time.sleep(0.5)


