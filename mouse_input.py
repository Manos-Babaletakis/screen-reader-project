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


_WM_MOUSEMOVE = 0x0200
_WM_BUTTON = {"left": (0x0201, 0x0202, 0x0001), "right": (0x0204, 0x0205, 0x0002)}  # (down, up, MK_)


def post_click(x, y, name="left", hold=0.08):
    """Click by posting the button messages straight to the window at SCREEN pixel (x, y).
    The game ignores left presses that come through SendInput, but accepts these."""
    _u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    hwnd = _u32.WindowFromPoint(wt.POINT(int(x), int(y)))
    p = wt.POINT(int(x), int(y))
    _u32.ScreenToClient(hwnd, ctypes.byref(p))
    lparam = (p.y & 0xFFFF) << 16 | (p.x & 0xFFFF)
    down, up, mk = _WM_BUTTON[name]
    _u32.PostMessageW(hwnd, _WM_MOUSEMOVE, 0, lparam)
    time.sleep(0.03)
    if not _u32.PostMessageW(hwnd, down, mk, lparam):
        raise OSError(f"PostMessage failed (error {ctypes.GetLastError()})")
    time.sleep(hold)
    _u32.PostMessageW(hwnd, up, 0, lparam)
