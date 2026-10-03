"""
Okey solver: picks the move with the highest EXPECTED FINAL SCORE.

Every unseen card is known (1 of each card), so the solver knows exactly what can
still be drawn.
  * deck_left <= exact_limit : exact expectimax over every possible draw
  * otherwise                : Monte-Carlo rollouts. All moves are tested on the SAME
                               random deck orders (paired comparison, low noise) and
                               followed by a fast heuristic policy.
A 100-point same-colour run is always taken (nothing scores more); if several exist,
the rollouts choose which one.

Moves: ('play', (a,b,c), points) | ('discard', card) | ('end',)
"""
import random
import time
from itertools import combinations
from okey_rules import (hand_combos, mask_of, bits_of, number_of,
                        RUN_WINDOWS, SET_GROUPS)

W_RUN = (0.15, 1.0, 3.0)   # run window value by how many of its other 2 cards we hold
SET_SCALE = 0.02


def legal_moves(hand, deck_left):
    combos = hand_combos(hand)
    runs = [m for m in combos if m[2]]
    if runs:
        return [('play', c, s) for s, c, _ in runs]
    moves = [('play', c, s) for s, c, _ in combos]
    if deck_left > 0:
        moves += [('discard', x) for x in hand]
    return moves


def _removed_info(mv):
    if mv[0] == 'play':
        return mv[1], mv[2], 3
    return (mv[1],), 0, 1


class OkeySolver:
    def __init__(self, time_budget=0.8, exact_limit=7, min_samples=60,
                 max_samples=3000, base_threshold=60, endgame_cutoff=3, seed=None):
        self.time_budget = time_budget
        self.exact_limit = exact_limit
        self.min_samples = min_samples
        self.max_samples = max_samples
        self.base_threshold = base_threshold
        self.endgame_cutoff = endgame_cutoff
        self.rng = random.Random(seed)
        self._memo = {}

    # ------------------------------------------------------------ heuristic
    @staticmethod
    def _potential(x, hand_mask, alive_mask):
        p = 0.0
        for a, b in RUN_WINDOWS[x]:
            if alive_mask & a and alive_mask & b:
                p += W_RUN[bool(hand_mask & a) + bool(hand_mask & b)]
        n = number_of(x)
        for a, b in SET_GROUPS[x]:
            if alive_mask & a and alive_mask & b:
                p += SET_SCALE * n * (1 + bool(hand_mask & a) + bool(hand_mask & b))
        return p

    def _base_move(self, hand, hand_mask, alive_mask, deck_left):
        combos = hand_combos(hand)
        if combos:
            runs = [m for m in combos if m[2]]
            if runs:
                if len(runs) == 1:
                    return ('play', runs[0][1], 100)
                best, best_v = None, -1.0
                for s, c, _ in runs:
                    rm = mask_of(c)
                    hm, am = hand_mask & ~rm, alive_mask & ~rm
                    v = sum(self._potential(x, hm, am) for x in bits_of(hm))
                    if v > best_v:
                        best, best_v = (s, c), v
                return ('play', best[1], best[0])
            s, c, _ = max(combos)
            thr = self.base_threshold if deck_left > self.endgame_cutoff else 0
            if s >= thr or deck_left == 0:
                return ('play', c, s)
        if deck_left == 0:
            return ('end',)
        worst, worst_p = hand[0], 1e9
        for x in hand:
            p = self._potential(x, hand_mask, alive_mask)
            if p < worst_p:
                worst, worst_p = x, p
        return ('discard', worst)

    @staticmethod
    def _apply(hand, hand_mask, alive_mask, mv, deck, pos):
        removed, gain, k = _removed_info(mv)
        rm = mask_of(removed)
        new_hand = [c for c in hand if not (rm >> c) & 1]
        draw = deck[pos:pos + k]
        new_hand.extend(draw)
        hm = hand_mask & ~rm
        for c in draw:
            hm |= 1 << c
        return new_hand, hm, alive_mask & ~rm, pos + len(draw), gain

    def _rollout(self, hand, hand_mask, alive_mask, deck, pos):
        total, n = 0, len(deck)
        while True:
            mv = self._base_move(hand, hand_mask, alive_mask, n - pos)
            if mv[0] == 'end':
                return total
            hand, hand_mask, alive_mask, pos, gain = self._apply(
                hand, hand_mask, alive_mask, mv, deck, pos)
            total += gain

    def play_out(self, hand, deck):
        """Play a whole game with the plain heuristic (no search). Used for benchmarking."""
        hand = list(hand)
        hm = mask_of(hand)
        alive = hm | mask_of(deck)
        return self._rollout(hand, hm, alive, list(deck), 0)

    # ---------------------------------------------------------------- exact
    def _exact(self, hand_mask, unseen_mask):
        key = (hand_mask, unseen_mask)
        v = self._memo.get(key)
        if v is not None:
            return v
        hand = bits_of(hand_mask)
        unseen = bits_of(unseen_mask)
        moves = legal_moves(hand, len(unseen))
        best = 0.0
        for mv in moves:
            best = max(best, self._exact_move(hand_mask, unseen_mask, unseen, mv))
        if len(self._memo) > 3_000_000:
            self._memo.clear()
        self._memo[key] = best
        return best

    def _exact_move(self, hand_mask, unseen_mask, unseen, mv):
        removed, gain, k = _removed_info(mv)
        hm = hand_mask & ~mask_of(removed)
        k = min(k, len(unseen))
        if k == 0:
            return gain + self._exact(hm, unseen_mask)
        tot, cnt = 0.0, 0
        for draw in combinations(unseen, k):
            dm = mask_of(draw)
            tot += self._exact(hm | dm, unseen_mask & ~dm)
            cnt += 1
        return gain + tot / cnt

    # ----------------------------------------------------------------- main
    def best_move(self, hand, unseen):
        """
        hand   : cards on the table (ids)
        unseen : cards still in the deck (ids)
        Returns (move, info) where info = {move: expected final points from here}
        """
        hand, unseen = list(hand), list(unseen)
        deck_left = len(unseen)
        moves = legal_moves(hand, deck_left)
        if not moves:
            return ('end',), {}
        if len(moves) == 1:
            return moves[0], {moves[0]: None}

        hand_mask, unseen_mask = mask_of(hand), mask_of(unseen)
        if deck_left <= self.exact_limit:
            vals = [self._exact_move(hand_mask, unseen_mask, unseen, mv) for mv in moves]
        else:
            alive = hand_mask | unseen_mask
            sums = [0.0] * len(moves)
            n, t0 = 0, time.perf_counter()
            while True:
                deck = unseen[:]
                self.rng.shuffle(deck)
                for i, mv in enumerate(moves):
                    h2, hm2, al2, p2, gain = self._apply(hand, hand_mask, alive, mv, deck, 0)
                    sums[i] += gain + self._rollout(h2, hm2, al2, deck, p2)
                n += 1
                if n >= self.max_samples or (
                        n >= self.min_samples and time.perf_counter() - t0 > self.time_budget):
                    break
            vals = [s / n for s in sums]
        best = max(range(len(moves)), key=lambda i: vals[i])
        return moves[best], {mv: v for mv, v in zip(moves, vals)}
