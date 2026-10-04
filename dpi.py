"""
Make this process DPI-aware BEFORE mss or pyautogui are loaded.

With Windows display scaling above 100%, a non-aware process sees a shrunken "logical"
screen: mss then captures only part of the real screen, while pyautogui (which turns on
DPI awareness when it is imported) clicks in real pixels - so capture and clicks disagree
and cards/buttons near the right or bottom of the screen are never found.
Import this module first; it is a no-op on non-Windows systems.
"""
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per-monitor aware (Windows 8.1+)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()       # system aware (older Windows)
    except Exception:
        pass
