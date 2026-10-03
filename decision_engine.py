"""
Decision engine: reads the table cards, asks the solver for the move with the best
expected final score, and keeps the CardTracker up to date.

A move is only committed to the tracker once the table is seen to have changed
(so a click that didn't register can never corrupt the played/discarded lists).
"""
from config import SOLVER_TIME_BUDGET, SOLVER_EXACT_LIMIT, COLOURS, HAND_SIZE, DEBUG
from okey_rules import card_id, card_name, N_CARDS
from okey_solver import OkeySolver
from card_tracker import CardTracker


class DecisionEngine:
    def __init__(self):
        self.tracker = CardTracker()
        self.solver = OkeySolver(time_budget=SOLVER_TIME_BUDGET,
                                 exact_limit=SOLVER_EXACT_LIMIT)
        self._prev_ids = None
        self._pending = None          # ('play', cards, pts) | ('discard', card)

    def new_game(self):
        self.tracker.reset()
        self._prev_ids, self._pending = None, None

    def cards_to_ids(self, cards):
        if any(c.get("number") is None or c.get("color") not in COLOURS for c in cards):
            return None
        ids = [card_id(c["color"], c["number"]) for c in cards]
        return ids if len(set(ids)) == len(ids) else None

    def expected_on_table(self):
        """How many cards should be face up once the last move lands (fewer once the deck
        runs out, 0 after the final combo). If the move did not register there are MORE."""
        t = self.tracker
        used = len(t.played) + len(t.discarded)
        if self._pending is not None:
            used += 3 if self._pending[0] == 'play' else 1
        return min(HAND_SIZE, N_CARDS - used)

    def _follows_pending(self, ids):
        """Is the new table a possible result of the pending move? (guards against a misread digit)"""
        removed = set(self._pending[1]) if self._pending[0] == 'play' else {self._pending[1]}
        prev, now = set(self._prev_ids), set(ids)
        return prev - removed <= now and not (now & removed) and now - prev <= self.tracker.unseen

    def _commit_pending(self, ids):
        """Returns False if the table changed in a way the pending move cannot explain."""
        if self._pending is None:
            return True
        if set(ids) != set(self._prev_ids or []):       # the table changed -> move happened
            if not self._follows_pending(ids):
                return False
            if self._pending[0] == 'play':
                self.tracker.record_play(self._pending[1], self._pending[2])
            else:
                self.tracker.record_discard(self._pending[1])
        elif DEBUG:
            print("  (table unchanged - previous move did not register, retrying)")
        self._pending = None
        return True

    def decide(self, cards):
        ids = self.cards_to_ids(cards)
        if ids is None:
            return {"action": "wait", "card_indices": [],
                    "reason": "could not read every card cleanly - not risking a wrong move"}

        # new game started? (we see a card we already played/discarded)
        t = self.tracker
        if set(ids) & (set(t.played) | set(t.discarded)) and self._pending is None:
            if DEBUG:
                print("  new game detected - resetting tracker")
            self.new_game()

        if not self._commit_pending(ids):
            return {"action": "wait", "card_indices": [],
                    "reason": "table does not match the last move (misread?) - re-reading"}
        t.observe(ids)
        self._prev_ids = ids

        mv, info = self.solver.best_move(ids, sorted(t.unseen))

        if DEBUG:
            for m, v in sorted(info.items(), key=lambda kv: -(kv[1] or 0)):
                label = (f"play {[card_name(c) for c in m[1]]} (+{m[2]})" if m[0] == 'play'
                         else f"discard {card_name(m[1])}")
                print(f"    {label:58s} E[final] = {v if v is None else round(v, 1)}")

        if mv[0] == 'end':
            return {"action": "end", "card_indices": [], "reason": "no combos left - game over"}
        if mv[0] == 'play':
            self._pending = ('play', mv[1], mv[2])
            return {"action": "use", "card_indices": [ids.index(c) for c in mv[1]],
                    "reason": f"{[card_name(c) for c in mv[1]]} for {mv[2]} points"}
        self._pending = ('discard', mv[1])
        return {"action": "discard", "card_indices": [ids.index(mv[1])],
                "reason": f"discard {card_name(mv[1])}"}
