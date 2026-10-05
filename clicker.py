"""
uiAccess mouse helper.

The game runs at SYSTEM level, and while UAC is on Windows drops mouse input sent to it by
any normal or administrator program. Windows makes one per-program exception: an .exe that
asks for uiAccess (meant for accessibility tools), is signed by a trusted certificate and
is installed under Program Files. This file is built into exactly such an .exe - see
build_clicker.ps1 - and does nothing but the mouse input in mouse_input.py.

The bot starts it (Windows only starts uiAccess programs through the shell, so there are no
stdin/stdout pipes) and sends it commands over a private named pipe:
    clicker.exe <pipe address> <authkey hex>
It exits as soon as the bot closes the pipe.
"""
import sys
from multiprocessing.connection import Client
import mouse_input

COMMANDS = {
    "move": mouse_input.move,
    "button": mouse_input.button,
    "focus": mouse_input.focus_window_at,
    "ping": lambda: "pong",
}


def main():
    address, authkey = sys.argv[1], bytes.fromhex(sys.argv[2])
    with Client(address, family="AF_PIPE", authkey=authkey) as conn:
        while True:
            try:
                cmd, *args = conn.recv()
            except (EOFError, OSError):
                return                             # the bot has gone
            try:
                conn.send(("ok", COMMANDS[cmd](*args)))
            except Exception as e:                 # report, keep serving
                conn.send(("err", f"{type(e).__name__}: {e}"))


if __name__ == "__main__":
    main()
