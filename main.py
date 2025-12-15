# python -m core.main

import asyncio
import logging
import os
import threading
import random
import importlib
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
from utils.general_utils import bring_window_to_front, exit_listener, enable_logging
from lcu_driver import Connector
from core.menu import show_menu  

connector = Connector()

# State variables
last_phase = None
shutdown_event = threading.Event()
game_end_event = threading.Event()

# Thread references
game_loop_thread = None


# ===========================
# LCU Event Listeners
# ===========================

@connector.ready
async def connect(connection):
    """
    Handler for when the connector is ready and connected to the League Client.
    Waits for the client window, then triggers the initial gameflow phase logic.
    """

    # Activate the client window
    bring_window_to_front(LEAGUE_CLIENT_WINDOW_TITLE)
    logging.info("Connected to League client.")

    # Check current gameflow phase and run the handler logic
    try:
        phase_resp = await connection.request('get', '/lol-gameflow/v1/gameflow-phase')
        current_phase = await phase_resp.json()
        await on_gameflow_phase(connection, type('Event', (object,), {'data': current_phase})())
    except Exception as e:
        logging.error(f"Failed to check gameflow phase: {e}")


@connector.ws.register(LCU_GAMEFLOW_PHASE, event_types=('UPDATE',))
async def on_gameflow_phase(connection, event):
    """
    Handles changes in the overall gameflow phase (lobby, matchmaking, champ select, game start, etc.).
    Manages lobby creation, queueing, ready check, bot thread lifecycle, and play-again requests.
    """
    global last_phase, game_loop_thread
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

        # Start the game loop thread
        game_loop_thread = threading.Thread(target=run_game_loop, args=(game_end_event,shutdown_event), daemon=True)
        game_loop_thread.start()

    # Clean up bot thread and play again on end of game
    if phase == GAMEFLOW_PHASES["PRE_END_OF_GAME"]:
        logging.info("[EVENT] Game ended.")
        game_end_event.set()
        game_loop_thread.join()
        game_end_event.clear()
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
async def disconnect(_):
    """
    Handler for disconnect event.
    Closes the connector and logs the disconnection.
    """
    await connector.stop()
    logging.info("[INFO] League Client has been closed.")


# ===========================
# Script Functions
# ===========================


def run_game_loop(game_end_event, shutdown_event):
    """
    Runs the correct bot loop for the selected game mode.
    The loop should exit when game_end_event is set (signaled by EndOfGame phase).
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
        module.run_game_loop(game_end_event, shutdown_event)
    elif hasattr(module, "main"):
        module.main()
    else:
        logging.error(f"No entry point found for '{selected_game_mode}'.")

 
def run_script():
    logging.info("Starting Script. Waiting for client...")
    connector.start()

def shutdown():
    logging.info("Shutting down program...")
    shutdown_event.set()
    
    # Join threads
    if game_loop_thread is not None:
        try:
            game_loop_thread.join(timeout=5)
        except Exception:
            logging.exception("Failed to join game loop thread.")

    logging.info("Shut down complete.")
    os._exit(0)

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
    threading.Thread(target=exit_listener, daemon=True, args=(shutdown,)).start()
    show_menu(run_script)



