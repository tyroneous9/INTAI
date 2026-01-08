"""
Simple script to fetch and print Live Client `/allgamedata` on keypress.

Usage:
    python fetch_live_data.py
    Press `Home` to print the latest `/allgamedata` JSON.
    Press `Esc` or Ctrl-C to quit.

This script uses `core.live_client_manager.LiveClientManager` to fetch the
Live Client API once on startup, writes a snapshot, and then exits.
"""

import json
import logging
import threading
import os
from datetime import datetime
import sys
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.live_client_manager import LiveClientManager


def main():
    logging.basicConfig(level=logging.INFO)

    stop_event = threading.Event()
    lock = threading.Lock()

    manager = LiveClientManager(stop_event, lock)

    print("Fetching /allgamedata once...")
    data = manager.fetch_live_client_data()
    if data is None:
        logging.error("Failed to fetch /allgamedata from Live Client API.")
        print("Failed to fetch /allgamedata.")
        return 1

    snapshot = data
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
    return 0


if __name__ == "__main__":
    main()
