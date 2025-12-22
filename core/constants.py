# ==========================================================
# Project-wide constants
# ==========================================================

import win32api
import os


# ===========================
# League General
# ===========================
LEAGUE_CLIENT_WINDOW_TITLE = "League of Legends"
LEAGUE_GAME_WINDOW_TITLE = "League of Legends (TM) Client"

SUPPORTED_MODES = {
    "arena": {
        "module": "core.run_arena",
        "queue_id": 1700
    },
    "aram": {
        "module": "core.run_aram",
        "queue_id": 450
    },
    "test": {
        "module": "core.run_test",
        "queue_id": -1
    },
    # Add more modes as needed
}

# ===========================
# Ingame Color Definitions (BGR)
# ===========================

# Health bar colors
HEALTH_BORDER_COLOR = (8, 4, 8) # Black
PLAYER_HEALTH_INNER_COLOR = (66, 199, 66) # Green
ENEMY_HEALTH_INNER_COLOR = (90, 101, 206) # Red
ALLY_HEALTH_INNER_COLOR = (247, 186, 66)  # Blue
AUGMENT_INNER_COLOR = (116, 97, 8) # Blue
AUGMENT_BORDER_COLOR = (196, 167, 89) # Light Blue
TEST_COLOR = (27, 38, 154)  # Configurable color for testing

# ===========================
# League APIs
# ===========================

# Default timeout for API calls (seconds)
DEFAULT_API_TIMEOUT = 60

# LiveClientData
LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata"

# LCU
LCU_MATCHMAKING_READY_CHECK = "/lol-matchmaking/v1/ready-check"
LCU_CHAMP_SELECT_SESSION = "/lol-champ-select/v1/session"
LCU_GAMEFLOW_PHASE = "/lol-gameflow/v1/gameflow-phase"
LCU_SUMMONER = "/lol-summoner/v1/current-summoner"
LCU_CHAMPIONS_MINIMAL = "/lol-champions/v1/inventories/{summoner_id}/champions-minimal"



GAMEFLOW_PHASES = {
    "NONE": "None",
    "LOBBY": "Lobby",
    "READY_CHECK": "ReadyCheck",
    "CHAMP_SELECT": "ChampionSelect",
    "GAME_START": "GameStart",
    "IN_PROGRESS": "InProgress",
    "PRE_END_OF_GAME": "PreEndOfGame",
    "END_OF_GAME": "EndOfGame",
}
CHAMP_SELECT_SUBPHASES = {
    "BAN_PICK": "BAN_PICK"
}

# Data Dragon
DATA_DRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DATA_DRAGON_DEFAULT_LOCALE = "en_US"


# ===========================
# Screen Geometry
# ===========================

# Get screen dimensions using win32api
SCREEN_WIDTH = win32api.GetSystemMetrics(0)
SCREEN_HEIGHT = win32api.GetSystemMetrics(1)
SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

# ===========================
# OCR Configuration
# ===========================

# Tesseract OCR executable path (relative to project root)
TESSERACT_PATH = os.path.join(os.path.dirname(__file__), "..", "tesseract", "tesseract.exe")

# Default threshold for image binarization
THRESHHOLD = 70  

# Page Segmentation Mode for Tesseract
PSM = 11  



