"""
Collects everything that can decide whether the bot's clicks reach the game, so two
computers can be compared. Run it with the game open and the Okey window visible:
    python system_report.py
The report is printed and saved to system_report.txt.
"""
import ctypes
import ctypes.wintypes as wt
import os
import platform
import subprocess
import sys
import winreg
import config
config.DEBUG = False
config.SAVE_SCREENSHOTS = False
from card_recognizer import CardRecognizer
import game_automation as ga

OUT = []
_u32 = ctypes.windll.user32


def out(line=""):
    print(line)
    OUT.append(str(line))


def reg(path, name, root=winreg.HKEY_LOCAL_MACHINE):
    try:
        with winreg.OpenKey(root, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def ps(command):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                       capture_output=True, text=True)
    return r.stdout.strip()


def processes():
    """[(name, pid)] of every running process."""
    rows = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True).stdout
    result = []
    for line in rows.splitlines():
        parts = line.split('","')
        if len(parts) > 1:
            result.append((parts[0].strip('"'), int(parts[1])))
    return result


def token_info(pid):
    k32, a32 = ctypes.windll.kernel32, ctypes.windll.advapi32
    k32.OpenProcess.restype = wt.HANDLE
    a32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
    proc = k32.OpenProcess(0x1000, False, pid)
    tok = wt.HANDLE()
    if not proc or not a32.OpenProcessToken(proc, 0x0008, ctypes.byref(tok)):
        return "cannot open (protected?)"
    ui, elev, n = wt.DWORD(), wt.DWORD(), wt.DWORD()
    a32.GetTokenInformation(tok, 26, ctypes.byref(ui), 4, ctypes.byref(n))       # TokenUIAccess
    a32.GetTokenInformation(tok, 20, ctypes.byref(elev), 4, ctypes.byref(n))     # TokenElevation
    level = ga._integrity_of_token(tok)
    return (f"level {ga._INTEGRITY_NAMES.get(level, hex(level or 0))}, "
            f"elevated {bool(elev.value)}, uiAccess {ui.value}")


def window_owner(x, y):
    hwnd = _u32.WindowFromPoint(wt.POINT(int(x), int(y)))
    root = _u32.GetAncestor(hwnd, 2)
    cls, title = ctypes.create_unicode_buffer(128), ctypes.create_unicode_buffer(128)
    _u32.GetClassNameW(root, cls, 128)
    _u32.GetWindowTextW(root, title, 128)
    pid = wt.DWORD()
    _u32.GetWindowThreadProcessId(root, ctypes.byref(pid))
    name = next((n for n, p in processes() if p == pid.value), "?")
    ex = _u32.GetWindowLongW(root, -20)                                          # GWL_EXSTYLE
    return f'{name} (pid {pid.value}) window "{title.value}" class {cls.value}, exstyle {ex:#x}', pid.value


def main():
    # (paths in variables: backslashes inside f-string expressions need Python 3.12+)
    nt = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    pol = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
    mouse = r"Control Panel\Mouse"
    out("=== SYSTEM ===")
    out(f"Windows: {platform.platform()}  build {reg(nt, 'CurrentBuild')}  {reg(nt, 'EditionID')}")
    out(f"Python: {sys.version.split()[0]}")
    out(f"UAC: EnableLUA={reg(pol, 'EnableLUA')} ConsentPromptBehaviorAdmin={reg(pol, 'ConsentPromptBehaviorAdmin')}"
        f" PromptOnSecureDesktop={reg(pol, 'PromptOnSecureDesktop')} EnableSecureUIAPaths={reg(pol, 'EnableSecureUIAPaths')}")
    out(f"Screen: {_u32.GetSystemMetrics(0)}x{_u32.GetSystemMetrics(1)}, DPI {_u32.GetDpiForSystem()}"
        f" ({_u32.GetDpiForSystem() * 100 // 96}%)")
    out(f"Mouse: buttons swapped={bool(_u32.GetSystemMetrics(23))}"
        f" pointer speed={reg(mouse, 'MouseSensitivity', winreg.HKEY_CURRENT_USER)}"
        f" enhance precision={reg(mouse, 'MouseSpeed', winreg.HKEY_CURRENT_USER)}")
    out("Antivirus: " + ps("Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | "
                           "ForEach-Object { $_.displayName + ' (state ' + $_.productState + ')' } | Out-String").replace("\n", "; ").strip("; "))
    out(f"Bot (this python): {token_info(os.getpid())}, admin={ga.bot_is_admin()}")
    out(f"uiAccess clicker installed: {os.path.exists(ga.CLICKER_EXE)}")

    out("\n=== GAME ===")
    game = [(n, p) for n, p in processes() if "metin2" in n.lower()]
    if not game:
        out("metin2client.bin is not running")
    for name, pid in game:
        out(f"{name} pid {pid}: {token_info(pid)}")
        mods = subprocess.run(["tasklist", "/m", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"],
                              capture_output=True, text=True).stdout
        dlls = sorted({m.strip().strip('"') for m in mods.split('","')[-1].split(",")} - {""})
        windir = os.environ.get("SystemRoot", r"C:\Windows").lower()
        system_dlls = {f.lower() for f in os.listdir(os.path.join(windir, "System32"))}
        extra = [d for d in dlls if d.lower() not in system_dlls]
        out(f"  {len(dlls)} DLLs loaded; not from Windows: {', '.join(extra) or '-'}")

    out("\n=== OKEY WINDOW ===")
    r = CardRecognizer()
    deck = r.find_deck()
    if deck is None:
        out("deck not found on screen - open the Okey window, uncovered, and run again")
    else:
        out(f"deck at {deck}")
        info, pid = window_owner(*deck)
        out(f"window under the deck: {info}")
        out(f"  that process: {token_info(pid)}")
        out(f"  clicks blocked by Windows (bot without helper): {ga.clicks_blocked_reason(deck) or 'no'}")

    out("\n=== OVERLAYS / INPUT TOOLS RUNNING ===")
    keywords = ("overlay", "nvcontainer", "nvidia share", "discord", "steam", "rtss", "afterburner",
                "xbox", "gamebar", "obs", "medal", "overwolf", "razer", "logi", "synapse", "steelseries",
                "ahk", "autohotkey", "ds4", "x360ce", "vjoy", "interception", "teamviewer", "anydesk",
                "parsec", "rdp", "vpn", "sandboxie", "bluestacks")
    found = sorted({n for n, _ in processes() if any(k in n.lower() for k in keywords)})
    out(", ".join(found) or "-")

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_report.txt"), "w",
              encoding="utf8") as f:
        f.write("\n".join(OUT) + "\n")
    out("\nSaved system_report.txt")


if __name__ == "__main__":
    main()
