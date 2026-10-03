"""
Okey Bot configuration.
The card row is found automatically anywhere on the primary monitor (the window is movable).
"""

# ============ DECK & SCORING (your server's rules) ============
# 5 cards on the table + "x 19" in the deck = 24 cards = 3 colours x numbers 1-8.
COLOURS = ["red", "yellow", "blue"]
MAX_NUMBER = 8
HAND_SIZE = 5

SAME_COLOUR_RUN_POINTS = 100   # 3 consecutive cards, same colour (always 100)
MIXED_RUN_MULTIPLIER = 10      # 3 consecutive, mixed colours: lowest card x 10
SET_MULTIPLIER = 10            # 3 cards of the same number: number x 10

# ============ COLOUR DETECTION (HSV: H 0-180, S 0-255, V 0-255) ============
# Each colour is a list of (lower, upper) ranges. Measured with calibrate.py:
# yellow card face H~25, blue H~102, red H~179-3 (wraps around 0); S~210-230, V~185-200.
COLOR_RANGES = {
    "red":    [([0, 120, 100], [8, 255, 255]), ([165, 120, 100], [180, 255, 255])],
    "yellow": [([18, 150, 120], [32, 255, 255])],
    "blue":   [([95, 100, 100], [125, 255, 255])],
}

# ============ SOLVER ============
SOLVER_TIME_BUDGET = 2         # seconds per decision (more = slightly better play)
SOLVER_EXACT_LIMIT = 9         # solve exactly when <= this many cards are left in the deck

# ============ TIMING (seconds) ============
TIMINGS = {
    "click_delay": 0.08,       # between clicks on cards
    "settle_timeout": 3.0,     # max wait for the table to change after an action
    "poll_delay": 0.15,        # between screen reads while waiting
}

# ============ DEBUG ============
DEBUG = True
SAVE_SCREENSHOTS = True       # save each read card to SCREENSHOT_DIR (for debugging)
SCREENSHOT_DIR = "./screenshots"
