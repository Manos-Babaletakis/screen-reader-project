"""
Mouse automation: left-click = select card, right-click = discard card.

Input goes through SendInput - the same path as a real mouse: the cursor really moves
(the game sees the hover) and the buttons are pressed and released at that spot.
(pyautogui teleports the cursor with SetCursorPos, which the game client does not always
notice, and silently swallows errors from its button presses.)
Slam the mouse into a screen corner to abort.
"""
import dpi  # noqa: F401  (same pixel coordinates as the screen capture - see dpi.py)
import ctypes
import ctypes.wintypes as wt
import time
from config import TIMINGS, DEBUG

_u32 = ctypes.windll.user32

_MOVE, _ABSOLUTE, _VIRTUALDESK = 0x0001, 0x8000, 0x4000
_BUTTON_FLAGS = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010)}    # (down, up)


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _INPUT(ctypes.Structure):
    # the real INPUT is a union, but MOUSEINPUT is its largest member - same size/layout
    _fields_ = [("type", wt.DWORD), ("mi", _MOUSEINPUT)]


def _send(flags, dx=0, dy=0):
    inp = _INPUT(0, _MOUSEINPUT(dx, dy, 0, flags, 0, 0))
    if _u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)) != 1:
        raise OSError(f"SendInput failed (error {ctypes.GetLastError()})")


def _move(x, y):
    """Move the cursor to SCREEN pixel (x, y) like a real mouse (works on any monitor)."""
    vx, vy = _u32.GetSystemMetrics(76), _u32.GetSystemMetrics(77)      # virtual desktop origin
    vw, vh = _u32.GetSystemMetrics(78), _u32.GetSystemMetrics(79)      # ... and size
    _send(_MOVE | _ABSOLUTE | _VIRTUALDESK,
          round((x - vx) * 65535 / max(vw - 1, 1)), round((y - vy) * 65535 / max(vh - 1, 1)))


def _button(button, down):
    if _u32.GetSystemMetrics(23):          # "swap primary and secondary buttons" is on
        button = {"left": "right", "right": "left"}[button]
    _send(_BUTTON_FLAGS[button][0 if down else 1])


def cursor_pos():
    p = wt.POINT()
    _u32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def _check_failsafe():
    """Abort (like Ctrl+C) when the user has pushed the mouse into a screen corner."""
    x, y = cursor_pos()
    vx, vy = _u32.GetSystemMetrics(76), _u32.GetSystemMetrics(77)
    vw, vh = _u32.GetSystemMetrics(78), _u32.GetSystemMetrics(79)
    if x in (vx, vx + vw - 1) and y in (vy, vy + vh - 1):
        raise KeyboardInterrupt("mouse moved to a screen corner")


def focus_window_at(pos):
    """Bring the (game) window under pos to the front, so the first click is not used up
    just activating it. Returns the window handle."""
    hwnd = _u32.GetAncestor(_u32.WindowFromPoint(wt.POINT(int(pos[0]), int(pos[1]))), 2)  # GA_ROOT
    if hwnd and _u32.GetForegroundWindow() != hwnd:
        # Windows only lets the process that received the last input change the foreground
        # window - a quick Alt tap counts as input.
        _u32.keybd_event(0x12, 0, 0, 0)
        _u32.SetForegroundWindow(hwnd)
        _u32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.15)
    return hwnd


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


_INTEGRITY_NAMES = {0x1000: "normal", 0x2000: "administrator", 0x3000: "SYSTEM", 0x4000: "protected"}


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
    """Windows integrity level (0x1000 normal, 0x2000 admin, 0x3000 SYSTEM) of the process
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


def clicks_blocked_reason(pos):
    """A message if Windows will drop our clicks on the window at pos, else None."""
    game, me = integrity_at(pos), integrity_at()
    if game is None or me is None or game <= me:
        return None
    name = _INTEGRITY_NAMES.get(game, hex(game))
    if game >= 0x3000:
        return (f"The game runs at {name} level - above administrator - so Windows drops every "
                f"click the bot sends, even when the bot runs as administrator. Close the game "
                f"and start it again normally (not via a tool or service that runs it as SYSTEM).")
    return (f"The game runs as {name} but this bot does not - Windows drops the bot's clicks. "
            f"Run the bot as administrator.")


class GameAutomation:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self._checked = False

    def _check_elevation(self, pos):
        if self._checked:
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
        """A click the game actually registers: glide onto the spot, hover, then hold the
        button briefly. (Teleport + press + release in the same instant is often missed.)"""
        x, y = int(pos[0]), int(pos[1])
        _check_failsafe()
        self._check_elevation((x, y))
        focus_window_at((x, y))
        if DEBUG:
            print(f"  {button}-click at ({x}, {y})")
        sx, sy = cursor_pos()
        for i in range(1, 6):                   # a few real move events on the way there
            _move(sx + (x - sx) * i / 5, sy + (y - sy) * i / 5)
            time.sleep(0.01)
        _move(x + 1, y + 1)                     # tiny wiggle so the game registers the hover
        _move(x, y)
        time.sleep(TIMINGS["hover_delay"])
        if DEBUG and cursor_pos() != (x, y):
            print(f"  ! cursor is at {cursor_pos()}, not ({x}, {y}) - display scaling mismatch?")
        _button(button, True)
        time.sleep(TIMINGS["hold_delay"])
        _button(button, False)
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
