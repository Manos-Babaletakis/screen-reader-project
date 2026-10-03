"""
Keeps track of every card in the game:
  unseen    - still in the deck (can be drawn)
  on_table  - the cards currently face up
  played    - cards used in scored combinations
  discarded - cards thrown away
Because there is exactly 1 of each card, `unseen` is known exactly at all times.
"""
from okey_rules import ALL_CARDS, card_name


class CardTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.unseen = set(ALL_CARDS)
        self.on_table = []
        self.played = []
        self.discarded = []
        self.score = 0
        self.combos = []          # (points, cards)

    def observe(self, table_cards):
        """Call with the cards read from the screen. Anything seen leaves the deck."""
        self.on_table = list(table_cards)
        self.unseen -= set(table_cards)

    def record_play(self, cards, points):
        self.played.extend(cards)
        self.score += points
        self.combos.append((points, tuple(cards)))

    def record_discard(self, card):
        self.discarded.append(card)

    @property
    def deck_left(self):
        return len(self.unseen)

    def summary(self):
        f = lambda cs: ", ".join(card_name(c) for c in sorted(cs)) or "-"
        return (f"score={self.score}  deck_left={self.deck_left}\n"
                f"  table    : {f(self.on_table)}\n"
                f"  played   : {f(self.played)}\n"
                f"  discarded: {f(self.discarded)}\n"
                f"  unseen   : {f(self.unseen)}")
