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
from game_automation import GameAutomation
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


def restart_game(recognizer, auto, last_hand):
    """Click End and wait for a fresh table of HAND_SIZE cards. Returns them, or None."""
    for _ in range(3):
        pos = recognizer.find_end_button()
        if pos is None:
            print("  ! End button not visible")
            time.sleep(1)
            continue
        auto.click(pos)
        t0 = time.time()
        while time.time() - t0 < TIMINGS["restart_timeout"]:
            time.sleep(TIMINGS["poll_delay"])
            cards = recognizer.read_cards(HAND_SIZE)
            if cards and hand_of(cards) != last_hand:
                return cards
    return None


def main():
    play = "--play" in sys.argv
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
            cards = wait_for_change(recognizer, prev, engine.expected_on_table())
    except KeyboardInterrupt:
        print("\nStopped.")
    print("\n" + engine.tracker.summary())
    if scores:
        print(f"{len(scores)} games, average score {sum(scores) / len(scores):.0f}, "
              f"best {max(scores)}")


if __name__ == "__main__":
    main()
