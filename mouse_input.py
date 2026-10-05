"""
Low-level mouse input through SendInput - the same path as a real mouse: the cursor really
moves (the game sees the hover) and the buttons are pressed and released at that spot.
Used directly by the bot, and by clicker.py (the uiAccess helper - see clicker.py).
"""
import dpi  # noqa: F401  (same pixel coordinates as the screen capture - see dpi.py)
import ctypes
import ctypes.wintypes as wt
import time

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


def move(x, y):
    """Move the cursor to SCREEN pixel (x, y) like a real mouse (works on any monitor)."""
    vx, vy = _u32.GetSystemMetrics(76), _u32.GetSystemMetrics(77)      # virtual desktop origin
    vw, vh = _u32.GetSystemMetrics(78), _u32.GetSystemMetrics(79)      # ... and size
    _send(_MOVE | _ABSOLUTE | _VIRTUALDESK,
          round((x - vx) * 65535 / max(vw - 1, 1)), round((y - vy) * 65535 / max(vh - 1, 1)))


def button(name, down):
    if _u32.GetSystemMetrics(23):          # "swap primary and secondary buttons" is on
        name = {"left": "right", "right": "left"}[name]
    _send(_BUTTON_FLAGS[name][0 if down else 1])


def cursor_pos():
    p = wt.POINT()
    _u32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def focus_window_at(x, y):
    """Bring the (game) window under (x, y) to the front, so the first click is not used up
    just activating it."""
    hwnd = _u32.GetAncestor(_u32.WindowFromPoint(wt.POINT(int(x), int(y))), 2)    # GA_ROOT
    if hwnd and _u32.GetForegroundWindow() != hwnd:
        # Windows only lets the process that received the last input change the foreground
        # window - a quick Alt tap counts as input.
        _u32.keybd_event(0x12, 0, 0, 0)
        _u32.SetForegroundWindow(hwnd)
        _u32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.15)
