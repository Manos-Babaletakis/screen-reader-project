"""
Configuration file for Okey Bot
Adjust all parameters here to match your setup
"""

# ============ SCREEN CONFIGURATION ============
# Since the Okey card window is movable, we can either:
# A) Set fixed coordinates (if window doesn't move much)
# B) Use AUTO_DETECT = True to find the window automatically

AUTO_DETECT_WINDOW = True  # Automatically find the card game window

# If AUTO_DETECT_WINDOW = False, use these fixed coordinates:
GAME_REGION = {
    "top": 160,       # pixels from top of screen
    "left": 365,      # pixels from left of screen
    "width": 290,     # width of card area
    "height": 130     # height of card area
}

# ============ CARD DETECTION ============
# Minimum card dimensions (in pixels) to avoid false positives
MIN_CARD_WIDTH = 30
MIN_CARD_HEIGHT = 50

# ============ COLOR DETECTION (HSV Ranges) ============
# HSV color ranges for the 4 card colors
# Format: "color_name": ([H_min, S_min, V_min], [H_max, S_max, V_max])
# Hue: 0-180, Saturation: 0-255, Value: 0-255
# 
# These are calibrated for Metin2 Okey cards visible in the screenshot
# If colors aren't detected, set DEBUG=True and SAVE_SCREENSHOTS=True to tune
COLOR_RANGES = {
    "red": ([160, 50, 100], [180, 255, 255]),      # Dark red/crimson
    "blue": ([90, 80, 80], [130, 255, 255]),       # Dark blue/navy
    "yellow": ([15, 100, 100], [35, 255, 255]),    # Bright yellow/gold
    "green": ([35, 80, 80], [85, 255, 255]),       # Green (if present)
}

# ============ OCR CONFIGURATION ============
# Language for card number recognition
OCR_LANGUAGE = ['en']

# ============ GAME CONTROLS ============
# Metin2 Okey controls - may need adjustment based on your keybinds
# 
# Common Metin2 Okey mechanics:
# - Left-click cards to select them
# - Right-click or press a key to discard selected cards
# - Cards auto-pull or use after action
#
CONTROLS = {
    "left_click": "left",      # Select cards (primary action)
    "right_click": "right",    # Discard selected cards
    "use": "enter",            # Confirm/use selected cards (if needed)
    "discard": "right",        # Discard cards (right-click)
    "pull": "space",           # Pull new cards (may auto-happen)
    "confirm": "enter",        # Confirm action
}

# ============ TIMING ============
# Delays between actions (in seconds)
TIMINGS = {
    "click_delay": 0.2,      # Delay between clicking cards
    "action_delay": 0.5,     # Delay between actions
    "pull_delay": 1.0,       # Delay after pulling cards
    "loop_delay": 1.0,       # Delay between main loop iterations
}

# ============ DECISION ENGINE ============
# Customize your Okey game strategy here
STRATEGY = {
    "min_cards_before_pull": 2,  # Pull more if hand falls below this size
    "aggressive": True,           # Always try to play valid sets/runs (vs discarding)
}

# ============ OKEY GAME LOGIC ============
# The bot will automatically:
# 1. Find all valid SETS (3+ cards with same number, any color)
# 2. Find all valid RUNS (3+ consecutive cards, same color)
# 3. Score and play the best combination
# 4. Discard worst cards if no valid combinations found
#
# You can override this by editing decision_engine.py _find_sets(), _find_runs(), etc.

# ============ DEBUG/LOGGING ============
DEBUG = True                    # Print detailed logs
SAVE_SCREENSHOTS = False        # Save detected cards for debugging
SCREENSHOT_DIR = "./screenshots"  # Where to save screenshots
