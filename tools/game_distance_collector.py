"""
Simple data collector to append player/enemy screen positions to CSV.

Creates/uses: data/game_distance_samples.csv (appends, does not overwrite)
Columns: timestamp,player_x,player_y,enemy_x,enemy_y,game_distance
(Leave `game_distance` empty for later manual entry)
"""

import os
import csv
import time
import logging
import sys
from datetime import datetime, timezone
import keyboard

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.screen_manager import ScreenManager
from utils.cv_utils import find_player_location, find_enemy_locations

logging.basicConfig(level=logging.INFO)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "game_distance_samples.csv")
HEADER = ["timestamp", "player_x", "player_y", "enemy_x", "enemy_y", "game_distance"]
KEY = "v" # key to hold for snapshots
INTERVAL = 0.1  # seconds between snapshots while holding the key


def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(HEADER)
        logging.info("Created CSV: %s", CSV_PATH)


def capture_once(screen_manager):
    # grab a single frame (doesn't start the camera thread)
    frame = None
    try:
        frame = screen_manager.grab()
    except Exception:
        logging.exception("Failed to grab frame from ScreenManager")
        return 0

    if frame is None:
        return 0

    player = find_player_location(frame)
    if not player:
        return 0

    enemies = find_enemy_locations(frame)
    if not enemies:
        return 0

    rows_written = 0
    ts = datetime.now(timezone.utc).isoformat()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for idx, en in enumerate(enemies, start=1):
            row = [ts, int(player[0]), int(player[1]), int(en[0]), int(en[1]), ""]
            writer.writerow(row)
            rows_written += 1

    return rows_written


def main():
    ensure_data_file()

    sm = ScreenManager()

    key = KEY
    hold_interval = max(0.0, float(INTERVAL))
    logging.info("Hold '%s' to capture snapshots every %.3fs. Press ESC to abort.", key, hold_interval)
    total = 0
    try:
        # Main loop: wait for key press and capture while held
        while True:
            if keyboard.is_pressed("esc"):
                logging.info("Abort key pressed; exiting hold mode.")
                break
            if keyboard.is_pressed(key):
                # Capture while key remains pressed
                while keyboard.is_pressed(key):
                    written = capture_once(sm)
                    total += written
                    time.sleep(hold_interval)
            time.sleep(0.01)
    except KeyboardInterrupt:
        logging.info("Interrupted by user")

    logging.info("Total rows appended: %d", total)


if __name__ == "__main__":
    main()
