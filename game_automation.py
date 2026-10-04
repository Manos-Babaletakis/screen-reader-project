"""Mouse automation: left-click = select card, right-click = discard card."""
import ctypes
import ctypes.wintypes as wt
import time
import pyautogui
from config import TIMINGS, DEBUG

pyautogui.FAILSAFE = True     # slam the mouse into a screen corner to abort
pyautogui.PAUSE = 0.0


def bot_is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def window_is_elevated(pos):
    """True if the window at screen pos belongs to a process running as administrator.
    Windows silently drops mouse clicks sent from a normal process to an elevated window
    (the cursor still moves, but the click never arrives)."""
    try:
        k32, a32 = ctypes.windll.kernel32, ctypes.windll.advapi32
        hwnd = ctypes.windll.user32.WindowFromPoint(wt.POINT(int(pos[0]), int(pos[1])))
        pid = wt.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc = k32.OpenProcess(0x1000, False, pid.value)       # QUERY_LIMITED_INFORMATION
        if not proc:
            return None
        try:
            tok = wt.HANDLE()
            if not a32.OpenProcessToken(proc, 0x0008, ctypes.byref(tok)):   # TOKEN_QUERY
                return True                                    # access denied -> elevated
            try:
                elev, n = wt.DWORD(), wt.DWORD()
                a32.GetTokenInformation(tok, 20, ctypes.byref(elev), 4, ctypes.byref(n))  # TokenElevation
                return bool(elev.value)
            finally:
                k32.CloseHandle(tok)
        finally:
            k32.CloseHandle(proc)
    except Exception:
        return None


class GameAutomation:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self._checked = False

    def _check_elevation(self, pos):
        if self._checked:
            return
        self._checked = True
        if not bot_is_admin() and window_is_elevated(pos):
            print("\n  !!! The game runs as ADMINISTRATOR but this bot does not.\n"
                  "  !!! Windows blocks the bot's clicks. Close this terminal / VS Code and\n"
                  "  !!! re-open it with 'Run as administrator', then start the bot again.\n")

    @staticmethod
    def _centre(card):
        x, y, w, h = card["position"]
        return x + w // 2, y + h // 2

    def _press(self, pos, button="left"):
        """A click the game actually registers: hover first, then hold the button briefly.
        (pyautogui.click() teleports + presses + releases in the same instant, which the
        game client often never sees - especially right-clicks.)"""
        x, y = int(pos[0]), int(pos[1])
        self._check_elevation((x, y))
        if DEBUG:
            print(f"  {button}-click at ({x}, {y})")
        pyautogui.moveTo(x, y, duration=0.05)
        pyautogui.moveTo(x + 1, y + 1)          # tiny wiggle so the game registers the hover
        pyautogui.moveTo(x, y)
        time.sleep(TIMINGS["hover_delay"])
        pyautogui.mouseDown(button=button)
        time.sleep(TIMINGS["hold_delay"])
        pyautogui.mouseUp(button=button)
        time.sleep(TIMINGS["click_delay"])

    def click(self, pos):
        if not self.dry_run:
            self._press(pos, "left")

    def execute(self, cards, decision):
        action, idxs = decision["action"], decision["card_indices"]
        if self.dry_run or action not in ("use", "discard"):
            return
        if action == "use":
            # right-to-left: if the remaining cards re-flow after a click, the cards
            # still to be clicked (further left) have not moved.
            for i in sorted(idxs, key=lambda i: -cards[i]["position"][0]):
                self._press(self._centre(cards[i]), "left")
        else:
            self._press(self._centre(cards[idxs[0]]), "right")
