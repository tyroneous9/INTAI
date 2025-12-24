# python -m core.main

import asyncio
import logging
import threading
import random
import time
import winsound
from utils.config_utils import (
    disable_insecure_request_warning, get_selected_game_mode, load_config
)
from core.constants import (
    LEAGUE_GAME_WINDOW_TITLE,
    SUPPORTED_MODES,
    LCU_GAMEFLOW_PHASE,
    LCU_CHAMP_SELECT_SESSION,
    LEAGUE_CLIENT_WINDOW_TITLE,
    GAMEFLOW_PHASES,
    CHAMP_SELECT_SUBPHASES
)
from utils.general_utils import bring_window_to_front, enable_logging, listen_for_exit, wait_for_window
from lcu_driver import Connector
from core.menu import show_menu  
from core.bot_manager import BotManager


# State variables
last_phase = None
shutdown_event = threading.Event()

# Module instances
connector = Connector()
bot_manager = BotManager(shutdown_event)

# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    """
    Handler for when the connector is ready and connected to the League Client.
    Waits for the client window, then triggers the initial gameflow phase logic.
    """
    connector.loop = asyncio.get_running_loop()
    # Activate the client window
    bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
    logging.info("Connected to League client.")

    # Check current gameflow phase and run the handler logic
    try:
        phase_resp = await connection.request('get', '/lol-gameflow/v1/gameflow-phase')
        current_phase = await phase_resp.json()
        await on_gameflow_phase(connection, type('Event', (object,), {"data": current_phase})())
    except Exception as e:
        logging.error(f"Failed to check gameflow phase: {e}")


@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_gameflow_phase(connection, event):
    """
    Handles changes in the overall gameflow phase (lobby, matchmaking, champ select, game start, etc.).
    Manages lobby creation, queueing, ready check, bot thread lifecycle, and play-again requests.
    """
    global last_phase
    phase = event.data
    if phase == last_phase:
        return
    last_phase = phase

    await asyncio.sleep(1)  # Small delay to ensure phase is stable

    # Create a lobby
    if phase == GAMEFLOW_PHASES["NONE"]:
        selected_game_mode = get_selected_game_mode()
        mode_info = SUPPORTED_MODES.get(selected_game_mode)
        queue_id = mode_info.get("queue_id")
        try:
            await connection.request('post', '/lol-lobby/v2/lobby', data={"queueId": queue_id})
            logging.info(f"{selected_game_mode.capitalize()} lobby created.")
        except Exception as e:
            logging.error(f"Failed to create {selected_game_mode} lobby: {e}")

    # Start queue
    if phase == GAMEFLOW_PHASES["LOBBY"]:
        try:
            await connection.request('post', '/lol-lobby/v2/lobby/matchmaking/search')
            logging.info("[EVENT] Starting queue.")
        except Exception as e:
            logging.error(f"Failed to start queue: {e}")

    # Accept ready check
    if phase == GAMEFLOW_PHASES["READY_CHECK"]:
        try:
            await connection.request('post', '/lol-matchmaking/v1/ready-check/accept')
            logging.info("Accepted ready check.")
        except Exception as e:
            logging.error(f"Failed to accept ready check: {e}")

    # Start bot loop thread on game start
    if phase == GAMEFLOW_PHASES["IN_PROGRESS"]:
        logging.info("[EVENT] Game is in progress.")
        # Activate the game window
        bring_window_to_front(LEAGUE_GAME_WINDOW_TITLE)

        # Start the bot via the bot manager
        bot_manager.start_bot_thread()

    # Clean up bot thread and play again on end of game
    if phase == GAMEFLOW_PHASES["PRE_END_OF_GAME"]:
        logging.info("[EVENT] Game ended.")
 
        # Stop the bot thread
        bot_manager.wait_for_bot_thread()
        
        # make sure game window is closed
        while wait_for_window(LEAGUE_GAME_WINDOW_TITLE, timeout=30) != None:
            time.sleep(1)

        # Play again (recreate lobby)
        try:
            await connection.request('post', '/lol-lobby/v2/play-again')
            logging.info("Sent play-again request.")
        except Exception as e:
            logging.error(f"Failed to send play-again request: {e}")

@connector.ws.register(LCU_CHAMP_SELECT_SESSION, event_types=('CREATE', 'UPDATE',))
async def on_champ_select_session(connection, event):
    """
    Handles champ select session updates, including subphase changes.
    Picks a champion during the BAN_PICK subphase.
    Logs API response status for debugging/rate limit detection.
    """
    session_data = event.data
    timer = session_data.get('timer', {})
    champ_phase = timer.get('phase')
    actions = session_data.get('actions', [])
    local_cell_id = session_data.get('localPlayerCellId')

    if champ_phase == CHAMP_SELECT_SUBPHASES["BAN_PICK"]:
        config = load_config()
        preferred_champion_obj = config.get("General", {}).get("preferred_champion", {})
        preferred_champ_id = preferred_champion_obj.get("id") if isinstance(preferred_champion_obj, dict) else None

        for action_group in actions:
            for action in action_group:
                # Ban phase
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'ban' and action.get('isInProgress'):
                    grid_resp = await connection.request('get', '/lol-champ-select/v1/all-grid-champions')
                    grid_data = await grid_resp.json()
                    pickable_champ_ids = [
                        champ['id'] for champ in grid_data
                        if (champ.get('owned') or champ.get('freeToPlay'))
                        and not champ.get('selectionStatus', {}).get('pickedByOtherOrBanned', False)
                    ]
                    action_id = action.get('id')
                    ban_champ_id = random.choice(pickable_champ_ids)
                    response = await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": ban_champ_id, "completed": True}
                    )
                    await asyncio.sleep(0.5)
                # Pick phase
                if action.get('actorCellId') == local_cell_id and action.get('type') == 'pick' and action.get('isInProgress'):
                    grid_resp = await connection.request('get', '/lol-champ-select/v1/all-grid-champions')
                    grid_data = await grid_resp.json()
                    owned_or_free_champs = [
                        champ['id'] for champ in grid_data
                        if (champ.get('owned') or champ.get('freeToPlay'))
                    ]
                    action_id = action.get('id')

                    # Try preferred champion
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": preferred_champ_id, "completed": True}
                    )

                    # Try bravery champion
                    await connection.request(
                        'patch',
                        f'/lol-champ-select/v1/session/actions/{action_id}',
                        data={"championId": -3, "completed": True}
                    )

                    # Try random champion
                    if owned_or_free_champs:
                        champ_id = random.choice(owned_or_free_champs)
                        logging.info(f"Picking random champion ID: {champ_id}")
                        await connection.request(
                            'patch',
                            f'/lol-champ-select/v1/session/actions/{action_id}',
                            data={"championId": champ_id, "completed": True}
                        )
                    return

@connector.close
async def disconnect(connection):
    """
    Handler for disconnect event.
    Closes the connector and logs the disconnection.
    """
    logging.info("[INFO] Connector has been closed.")


# ===========================
# Script Functions
# ===========================

 
def run_script():
    logging.info("Starting Script. Waiting for client...")
    connector.start()

def shutdown():
    logging.info("Shutting down program...")
    shutdown_event.set()

    # Stop connector
    fut = asyncio.run_coroutine_threadsafe(connector.stop(), connector.loop)
    fut.result(timeout=10)

    # Wait for bot thread
    bot_manager.wait_for_bot_thread()

    logging.info("Shut down complete.")
    winsound.Beep(500,200)

# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    """
    Main entry point for the League Bot Launcher.
    Handles menu navigation and starts the connector.
    """
    disable_insecure_request_warning()
    enable_logging()
    listen_for_exit(shutdown)
    show_menu(run_script)



