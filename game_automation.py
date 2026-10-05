"""
Mouse automation: left-click = select card, right-click = discard card.

Clicks go through SendInput (mouse_input.py). The game runs as administrator and, while UAC
is on, Windows drops input sent to it by programs at a lower level - so the bot must run as
administrator too (main.py relaunches itself elevated). If the optional uiAccess helper is
installed (clicker.exe, see clicker.py / build_clicker.ps1) mouse actions go through it.
Slam the mouse into a screen corner to abort.
"""
import dpi  # noqa: F401  (same pixel coordinates as the screen capture - see dpi.py)
import ctypes
import ctypes.wintypes as wt
import os
import threading
import time
from multiprocessing.connection import Listener
import mouse_input
from mouse_input import cursor_pos
from config import TIMINGS, DEBUG

_u32 = ctypes.windll.user32

CLICKER_EXE = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "OkeyClicker", "clicker.exe")


class ClickerInput:
    """Same interface as mouse_input (move / button), but performed by
    the uiAccess helper clicker.exe over a private named pipe."""

    def __init__(self, exe=CLICKER_EXE, timeout=10.0):
        key = os.urandom(16)
        address = rf"\\.\pipe\okey-clicker-{os.getpid()}-{key[:4].hex()}"
        self._listener = Listener(address, family="AF_PIPE", authkey=key)
        accepted = {}

        def accept():
            try:
                accepted["conn"] = self._listener.accept()
            except Exception as e:                 # e.g. wrong authkey
                accepted["error"] = e

        waiter = threading.Thread(target=accept, daemon=True)
        waiter.start()
        # uiAccess programs can only be started through the shell (CreateProcess refuses)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "open", exe, f'"{address}" {key.hex()}', None, 0)
        if rc <= 32:
            raise OSError(f"could not start {exe} (ShellExecute error {rc})")
        waiter.join(timeout)
        if "conn" not in accepted:
            raise TimeoutError(f"clicker.exe did not connect ({accepted.get('error', 'timed out')})")
        self._conn = accepted["conn"]
        self._call("ping")

    def _call(self, cmd, *args):
        self._conn.send((cmd, *args))
        status, value = self._conn.recv()
        if status != "ok":
            raise OSError(f"clicker.exe: {value}")
        return value

    def move(self, x, y):
        self._call("move", x, y)

    def button(self, name, down):
        self._call("button", name, down)

    def post_click(self, x, y, name="left", hold=0.08):
        self._call("post_click", x, y, name, hold)



def start_input():
    """(input backend, uses_uiaccess): the uiAccess helper if installed, else direct input."""
    if os.path.exists(CLICKER_EXE):
        try:
            return ClickerInput(), True
        except Exception as e:
            print(f"  ! uiAccess clicker could not start ({e}) - clicking directly instead")
    return mouse_input, False


def _deactivate_game():
    """Make the taskbar the active window, so the game is not active when it gets clicked.
    Windows only lets a background program change the active window right after it sent
    input - hence the Alt tap. The bot runs at normal level while the game runs as
    administrator, so Windows keeps that Alt tap away from the game itself."""
    if bot_is_admin():           # an admin bot's Alt tap WOULD reach the game -> skip
        return
    _u32.keybd_event(0x12, 0, 0, 0)
    _u32.SetForegroundWindow(_u32.FindWindowW("Shell_TrayWnd", None))
    _u32.keybd_event(0x12, 0, 0x0002, 0)
    time.sleep(0.15)


def _check_failsafe():
    """Abort (like Ctrl+C) when the user has pushed the mouse into a screen corner."""
    x, y = cursor_pos()
    vx, vy = _u32.GetSystemMetrics(76), _u32.GetSystemMetrics(77)
    vw, vh = _u32.GetSystemMetrics(78), _u32.GetSystemMetrics(79)
    if x in (vx, vx + vw - 1) and y in (vy, vy + vh - 1):
        raise KeyboardInterrupt("mouse moved to a screen corner")


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


# Windows mandatory integrity levels (the RID of the token's integrity SID)
_INTEGRITY_NAMES = {0x1000: "low", 0x2000: "normal", 0x3000: "administrator", 0x4000: "SYSTEM"}


def _integrity_of_token(tok):
    a32 = ctypes.windll.advapi32
    a32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    a32.GetSidSubAuthorityCount.argtypes = [ctypes.c_void_p]
    a32.GetSidSubAuthority.restype = ctypes.POINTER(wt.DWORD)
    a32.GetSidSubAuthority.argtypes = [ctypes.c_void_p, wt.DWORD]
    buf, n = (ctypes.c_byte * 64)(), wt.DWORD()
    if not a32.GetTokenInformation(tok, 25, buf, 64, ctypes.byref(n)):     # TokenIntegrityLevel
        return None
    sid = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
    return a32.GetSidSubAuthority(sid, a32.GetSidSubAuthorityCount(sid)[0] - 1)[0]


def integrity_at(pos=None):
    """Windows integrity level (0x2000 normal, 0x3000 administrator, 0x4000 SYSTEM) of the process
    owning the window at screen pos - or of this process when pos is None. None = unknown.
    Windows drops mouse input sent to a process with a HIGHER level than the sender."""
    k32, a32 = ctypes.windll.kernel32, ctypes.windll.advapi32
    k32.OpenProcess.restype = wt.HANDLE
    k32.CloseHandle.argtypes = [wt.HANDLE]
    a32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
    try:
        pid = wt.DWORD(k32.GetCurrentProcessId())
        if pos is not None:
            hwnd = _u32.WindowFromPoint(wt.POINT(int(pos[0]), int(pos[1])))
            _u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc = k32.OpenProcess(0x1000, False, pid.value)             # QUERY_LIMITED_INFORMATION
        if not proc:
            return None
        try:
            tok = wt.HANDLE()
            if not a32.OpenProcessToken(proc, 0x0008, ctypes.byref(tok)):   # TOKEN_QUERY
                return None
            try:
                return _integrity_of_token(tok)
            finally:
                k32.CloseHandle(tok)
        finally:
            k32.CloseHandle(proc)
    except Exception:
        return None


def uac_enabled():
    """Windows only drops input sent to higher-level programs while UAC is on (EnableLUA=1)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as k:
            return bool(winreg.QueryValueEx(k, "EnableLUA")[0])
    except OSError:
        return True


def clicks_blocked_reason(pos):
    """A message if Windows will drop our clicks on the window at pos, else None."""
    game, me = integrity_at(pos), integrity_at()
    if game is None or me is None or game <= me or not uac_enabled():
        return None
    name = _INTEGRITY_NAMES.get(game, hex(game))
    if game >= 0x4000:
        return (f"The game runs at {name} level - above administrator - so Windows drops every "
                f"click the bot sends, even when the bot runs as administrator. Close the game "
                f"and start it again normally (not via a tool or service that runs it as SYSTEM).")
    return (f"The game runs as {name} but this bot does not - Windows drops the bot's clicks. "
            f"Run the bot as administrator.")


class GameAutomation:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self._checked = False
        self.input, self.uiaccess = (mouse_input, False) if dry_run else start_input()
        if not dry_run:
            print("Clicking through the uiAccess helper (clicker.exe)" if self.uiaccess
                  else "Clicking directly (uiAccess helper not installed)")

    def _check_elevation(self, pos):
        if self._checked or self.uiaccess:        # uiAccess input is never dropped
            return
        self._checked = True
        reason = clicks_blocked_reason(pos)
        if reason:
            print(f"\n  !!! CLICKS WILL NOT WORK: {reason}\n")

    @staticmethod
    def _centre(card):
        x, y, w, h = card["position"]
        return x + w // 2, y + h // 2

    def _press(self, pos, button="left"):
        """A click the game actually registers (tested on the game):
        - left : the game ignores left presses sent through SendInput, so the click is
                 posted to its window as button messages (the cursor still glides there)
        - right: a SendInput right-click works, but only if the game is not the active
                 window at that moment - so another window is made active first."""
        x, y = int(pos[0]), int(pos[1])
        _check_failsafe()
        self._check_elevation((x, y))
        if DEBUG:
            print(f"  {button}-click at ({x}, {y})")
        if button == "right":
            _deactivate_game()
        sx, sy = cursor_pos()
        for i in range(1, 6):                   # a few real move events on the way there
            self.input.move(sx + (x - sx) * i / 5, sy + (y - sy) * i / 5)
            time.sleep(0.01)
        self.input.move(x + 1, y + 1)           # tiny wiggle so the game registers the hover
        self.input.move(x, y)
        time.sleep(TIMINGS["hover_delay"])
        if DEBUG and cursor_pos() != (x, y):
            print(f"  ! cursor is at {cursor_pos()}, not ({x}, {y}) - display scaling mismatch?")
        if button == "left":
            self.input.post_click(x, y, "left", TIMINGS["hold_delay"])
        else:
            self.input.button(button, True)
            time.sleep(TIMINGS["hold_delay"])
            self.input.button(button, False)
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
