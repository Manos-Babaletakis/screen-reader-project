"""
Okey Bot.
    python main.py          -> DRY RUN: reads the table and shows the best move, never clicks
    python main.py --play   -> plays for you (slam the mouse into a screen corner to abort)
"""
import sys
import time
from card_recognizer import CardRecognizer
from decision_engine import DecisionEngine
from game_automation import GameAutomation
from config import TIMINGS, HAND_SIZE


def wait_for_change(recognizer, prev_hand, expected):
    """After an action: poll until the table shows a different set of cards."""
    t0 = time.time()
    while time.time() - t0 < TIMINGS["settle_timeout"]:
        time.sleep(TIMINGS["poll_delay"])
        cards = recognizer.read_cards(expected)
        if cards and {(c["color"], c["number"]) for c in cards} != prev_hand:
            return cards
    return None


def main():
    play = "--play" in sys.argv
    recognizer, engine = CardRecognizer(), DecisionEngine()
    auto = GameAutomation(dry_run=not play)
    print("PLAY MODE - clicking for real" if play else "DRY RUN - no clicks (use --play to play)")
    print("Open the Okey window with 5 cards showing. Ctrl+C to stop.\n")

    cards, fails = None, 0
    try:
        while True:
            if cards is None:
                cards = recognizer.read_cards(engine.expected_on_table())
                if not cards:
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
                print(f"\nGame over. Final score: {engine.tracker.score}")
                print(engine.tracker.summary()); break

            print(f"-> {decision['action'].upper()}: {decision['reason']}   "
                  f"[score {engine.tracker.score}, deck {engine.tracker.deck_left}]")
            if not play:
                print("   (dry run - perform this move yourself, then press Enter)")
                input(); cards = None; continue

            prev = {(c["color"], c["number"]) for c in cards}
            auto.execute(cards, decision)
            cards = wait_for_change(recognizer, prev, engine.expected_on_table())
    except KeyboardInterrupt:
        print("\nStopped.")
    print("\n" + engine.tracker.summary())


if __name__ == "__main__":
    main()
