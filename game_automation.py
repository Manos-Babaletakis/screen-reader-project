"""Mouse automation: left-click = select card, right-click = discard card."""
import time
import pyautogui
from config import TIMINGS, DEBUG

pyautogui.FAILSAFE = True     # slam the mouse into a screen corner to abort
pyautogui.PAUSE = 0.0


class GameAutomation:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run

    @staticmethod
    def _centre(card):
        x, y, w, h = card["position"]
        return x + w // 2, y + h // 2

    def click(self, pos):
        if not self.dry_run:
            pyautogui.click(*pos, button="left")
            time.sleep(TIMINGS["click_delay"])

    def execute(self, cards, decision):
        action, idxs = decision["action"], decision["card_indices"]
        if self.dry_run or action not in ("use", "discard"):
            return
        if action == "use":
            # right-to-left: if the remaining cards re-flow after a click, the cards
            # still to be clicked (further left) have not moved.
            for i in sorted(idxs, key=lambda i: -cards[i]["position"][0]):
                pyautogui.click(*self._centre(cards[i]), button="left")
                time.sleep(TIMINGS["click_delay"])
        else:
            pyautogui.click(*self._centre(cards[idxs[0]]), button="right")
            time.sleep(TIMINGS["click_delay"])
