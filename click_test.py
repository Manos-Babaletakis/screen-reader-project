"""
Checks that the game accepts the bot's clicks on THIS computer. Run it at the start of a
game (empty table, full deck):
    python click_test.py
It left-clicks the deck (should draw a card), then right-clicks that card and confirms
with Yes (should discard it). Results are printed and saved to click_test.log.
"""
import sys
import time
import config
config.SAVE_SCREENSHOTS = False
from card_recognizer import CardRecognizer
from game_automation import (GameAutomation, bot_is_admin, window_is_elevated, integrity_at,
                             clicks_blocked_reason, uac_enabled, _INTEGRITY_NAMES)
from main import relaunch_as_admin

LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


def wait_count(r, target, timeout=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        n = r.count_cards()
        if n == target:
            return n
        time.sleep(0.1)
    return r.count_cards()


def main():
    r, auto = CardRecognizer(), GameAutomation(dry_run=False)
    deck = r.find_deck()
    if deck is None:
        log("FAIL: deck not found - is the Okey window open and not covered?"); return
    game, me = integrity_at(deck), integrity_at()
    log(f"game level: {_INTEGRITY_NAMES.get(game, game)} | this script: {_INTEGRITY_NAMES.get(me, me)}"
        f" | UAC on: {uac_enabled()}")
    log(f"clicking through: {'uiAccess helper (clicker.exe)' if auto.uiaccess else 'this script directly'}")
    if not auto.uiaccess and game is not None and game >= 0x3000 and clicks_blocked_reason(deck):
        log("FAIL: " + clicks_blocked_reason(deck)); return
    if not auto.uiaccess and window_is_elevated(deck) and not bot_is_admin():
        log("relaunching as admin (accept the UAC prompt)...")
        if relaunch_as_admin():
            sys.exit(0)
        log("FAIL: could not get admin rights - Windows will block every click"); return

    before = r.count_cards()
    log(f"cards on table: {before}")
    if before >= config.HAND_SIZE:
        log("table is full - start a new game (or discard a card) and run this again"); return

    auto.click(deck)
    after = wait_count(r, before + 1)
    log(f"LEFT-click on deck  -> cards {before} -> {after}: {'OK' if after == before + 1 else 'FAIL'}")
    if after != before + 1:
        return

    cards = r.read_cards(after)
    if not cards:
        log("could not read the cards - skipping the right-click test"); return
    card = cards[-1]
    auto.execute(cards, {"action": "discard", "card_indices": [len(cards) - 1]})
    t0, yes = time.time(), None
    while yes is None and time.time() - t0 < 2:
        yes = r.find_yes_button()
    log(f"RIGHT-click on {card['color']} {card['number']} -> Yes dialog: {'OK' if yes else 'FAIL (no dialog)'}")
    if yes:
        auto.click(yes)
        final = wait_count(r, after - 1)
        log(f"LEFT-click on Yes   -> cards {after} -> {final}: {'OK' if final == after - 1 else 'FAIL'}")


if __name__ == "__main__":
    try:
        main()
    finally:
        if LOG:
            with open(__file__.replace("click_test.py", "click_test.log"), "w") as f:
                f.write("\n".join(LOG) + "\n")
