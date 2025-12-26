"""
Simple script to fetch and print Live Client `/allgamedata` on keypress.

Usage:
    python fetch_live_data.py
    Press `Home` to print the latest `/allgamedata` JSON.
    Press `Esc` or Ctrl-C to quit.

This script uses `core.live_client_manager.LiveClientManager` to poll the
Live Client API in a background thread and prints the shared container
contents when requested.
"""

import json
import logging
import threading
import time
import os
from datetime import datetime
import keyboard

from core.live_client_manager import LiveClientManager


def main():
    logging.basicConfig(level=logging.INFO)

    stop_event = threading.Event()
    lock = threading.Lock()
    latest_game_data = {}

    manager = LiveClientManager(stop_event, lock)
    manager.start_polling_thread(latest_game_data)

    print("LiveClient polling started. Press Home to print /allgamedata. Esc to exit.")

    try:
        while True:
            event = keyboard.read_event()
            if event.event_type != keyboard.KEY_DOWN:
                continue

            if event.name == "home":
                with lock:
                    snapshot = dict(latest_game_data)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"allgamedata_{timestamp}.json"
                project_root = os.path.abspath(os.path.dirname(__file__))
                outdir = os.path.join(project_root, "temp")
                os.makedirs(outdir, exist_ok=True)
                outpath = os.path.join(outdir, filename)
                try:
                    with open(outpath, "w", encoding="utf-8") as fh:
                        json.dump(snapshot, fh, indent=2, ensure_ascii=False)
                    print(f"Wrote /allgamedata snapshot to: {outpath}")
                except Exception as e:
                    logging.error("Failed to write snapshot to %s: %s", outpath, e)
                    print(f"Failed to write snapshot: {e}")

            elif event.name == "esc":
                print("Exiting on Esc...")
                break

    except KeyboardInterrupt:
        print("Interrupted, shutting down...")
    finally:
        stop_event.set()
        try:
            manager.stop_polling_thread()
        except Exception as e:
            logging.error("Error stopping polling thread: %s", e)


if __name__ == "__main__":
    main()
