"""
Okey Bot.
    python main.py          -> DRY RUN: reads the table and shows the best move, never clicks
    python main.py --play   -> plays game after game, clicking End to restart each one
                               (slam the mouse into a screen corner to abort)
"""
import sys
import time
from card_recognizer import CardRecognizer
from decision_engine import DecisionEngine
from game_automation import GameAutomation, bot_is_admin
from config import TIMINGS, HAND_SIZE


def hand_of(cards):
    return {(c["color"], c["number"]) for c in cards}


def read_table(recognizer, expected):
    """The cards on the table, or None if they could not be read.
    [] is only a valid answer when the table should be empty (after the final combo)."""
    cards = recognizer.read_cards(max(expected, 1))
    return cards if cards or expected == 0 else None


def wait_for_change(recognizer, prev_hand, expected):
    """After an action: poll until the table shows a different set of cards."""
    t0 = time.time()
    while time.time() - t0 < TIMINGS["settle_timeout"]:
        time.sleep(TIMINGS["poll_delay"])
        cards = read_table(recognizer, expected)
        if cards is not None and hand_of(cards) != prev_hand:
            return cards
    return None


def confirm_yes(recognizer, auto, what):
    """Discarding a card and clicking End both open a Yes/No dialog - click Yes."""
    t0 = time.time()
    while time.time() - t0 < TIMINGS["confirm_timeout"]:
        pos = recognizer.find_yes_button()
        if pos is not None:
            auto.click(pos)
            # wait for the dialog to close, so it can't swallow the deck clicks
            t1 = time.time()
            while time.time() - t1 < TIMINGS["confirm_timeout"] and recognizer.find_yes_button():
                time.sleep(TIMINGS["poll_delay"])
            return True
        time.sleep(TIMINGS["poll_delay"])
    print(f"  ! {what} confirmation (Yes) not found")
    return False


def draw_cards(recognizer, auto, target):
    """Left-click the deck until `target` cards are face up (or the deck is gone)."""
    for _ in range(HAND_SIZE + 3):
        if recognizer.count_cards() >= target:
            return True
        pos = recognizer.find_deck()
        if pos is None:
            print("  ! deck not found - cannot draw")
            return False
        auto.click(pos)
        time.sleep(TIMINGS["draw_delay"])
    return recognizer.count_cards() >= target


def restart_game(recognizer, auto, last_hand):
    """Click End and wait for a fresh table of HAND_SIZE cards. Returns them, or None."""
    for _ in range(3):
        pos = recognizer.find_end_button()
        if pos is None:
            print("  ! End button not visible")
            time.sleep(1)
            continue
        auto.click(pos)
        confirm_yes(recognizer, auto, "end game")
        time.sleep(TIMINGS["draw_delay"])
        t0 = time.time()
        while time.time() - t0 < TIMINGS["restart_timeout"]:
            time.sleep(TIMINGS["poll_delay"])
            draw_cards(recognizer, auto, HAND_SIZE)      # a new game starts with an empty table
            cards = recognizer.read_cards(HAND_SIZE)
            if cards and hand_of(cards) != last_hand:
                return cards
    return None


def relaunch_as_admin():
    """The Metin2 client runs as administrator, and Windows drops clicks sent to it from a
    normal process. Re-open the bot elevated (UAC prompt) in its own console window."""
    import ctypes, os
    args = " ".join(f'"{a}"' for a in [os.path.abspath(sys.argv[0])] + sys.argv[1:])
    # an elevated cmd.exe ignores the start folder and opens in System32 -> cd there first
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", "cmd.exe", f'/s /k "cd /d "{here}" && "{sys.executable}" {args}"', here, 1)
    return rc > 32


def main():
    play = "--play" in sys.argv
    if play and not bot_is_admin():
        print("The game runs as administrator, so the bot must too - relaunching elevated...")
        if relaunch_as_admin():
            return
        print("Could not elevate (UAC declined?) - clicks will probably be ignored.")
    recognizer, engine = CardRecognizer(), DecisionEngine()
    auto = GameAutomation(dry_run=not play)
    print("PLAY MODE - clicking for real" if play else "DRY RUN - no clicks (use --play to play)")
    print("Open the Okey window with 5 cards showing. Ctrl+C to stop.\n")

    scores = []
    cards, fails = None, 0
    try:
        while True:
            if cards is None:
                cards = read_table(recognizer, engine.expected_on_table())
                if cards is None:
                    if play:      # stuck? a confirm dialog still open, or a draw was missed
                        pos = recognizer.find_yes_button()
                        if pos is not None:
                            auto.click(pos)
                        draw_cards(recognizer, auto, engine.expected_on_table())
                    time.sleep(0.5)
                    continue
            decision = engine.decide(cards)
            if decision["action"] == "wait":
                fails += 1
                print(f"  ! {decision['reason']}")
                cards = None
                if fails > 20:
                    print("Too many unreadable frames - run calibrate.py"); break
                time.sleep(0.3)
                continue
            fails = 0

            if decision["action"] == "end":
                scores.append(engine.tracker.score)
                print(f"\nGame {len(scores)} over. Score: {scores[-1]}   "
                      f"(average {sum(scores) / len(scores):.0f} over {len(scores)} games)")
                print(engine.tracker.summary() + "\n")
                last_hand = hand_of(cards)
                engine.new_game()
                if not play:
                    print("   (dry run - click End yourself, then press Enter)")
                    input(); cards = None; continue
                cards = restart_game(recognizer, auto, last_hand)
                if cards is None:
                    print("Could not start a new game (End button not found or no new cards)"); break
                continue

            print(f"-> {decision['action'].upper()}: {decision['reason']}   "
                  f"[score {engine.tracker.score}, deck {engine.tracker.deck_left}]")
            if not play:
                print("   (dry run - perform this move yourself, then press Enter)")
                input(); cards = None; continue

            prev = hand_of(cards)
            auto.execute(cards, decision)
            if decision["action"] == "discard":
                confirm_yes(recognizer, auto, "discard")
            time.sleep(TIMINGS["draw_delay"])
            draw_cards(recognizer, auto, engine.expected_on_table())
            cards = wait_for_change(recognizer, prev, engine.expected_on_table())
    except KeyboardInterrupt:
        print("\nStopped.")
    print("\n" + engine.tracker.summary())
    if scores:
        print(f"{len(scores)} games, average score {sum(scores) / len(scores):.0f}, "
              f"best {max(scores)}")


if __name__ == "__main__":
    main()
