"""
Okey rules & scoring for your server.
Cards are ints: id = colour_index * MAX_NUMBER + (number - 1)

  3 consecutive, same colour   -> 100 points
  3 consecutive, mixed colours -> lowest number x 10
  3 of the same number         -> number x 10
"""
from itertools import combinations
from config import (COLOURS, MAX_NUMBER, HAND_SIZE, SAME_COLOUR_RUN_POINTS,
                    MIXED_RUN_MULTIPLIER, SET_MULTIPLIER)

N_COLOURS = len(COLOURS)
N_CARDS = N_COLOURS * MAX_NUMBER
ALL_CARDS = tuple(range(N_CARDS))


def card_id(colour, number):
    return COLOURS.index(colour) * MAX_NUMBER + (number - 1)


def card_from_id(i):
    return COLOURS[i // MAX_NUMBER], i % MAX_NUMBER + 1


def colour_of(i):
    return i // MAX_NUMBER


def number_of(i):
    return i % MAX_NUMBER + 1


def card_name(i):
    c, n = card_from_id(i)
    return f"{c} {n}"


def mask_of(cards):
    m = 0
    for c in cards:
        m |= 1 << c
    return m


def bits_of(mask):
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


def score_triple(a, b, c):
    """Points for 3 cards (0 if they are not a valid combination)."""
    nums = sorted((number_of(a), number_of(b), number_of(c)))
    cols = {colour_of(a), colour_of(b), colour_of(c)}
    if nums[0] == nums[1] == nums[2]:
        return SET_MULTIPLIER * nums[0], False
    if nums[1] == nums[0] + 1 and nums[2] == nums[1] + 1:
        if len(cols) == 1:
            return SAME_COLOUR_RUN_POINTS, True
        return MIXED_RUN_MULTIPLIER * nums[0], False
    return 0, False


# mask -> (points, is_same_colour_run) for every valid triple
TRIPLES = {}
for _t in combinations(ALL_CARDS, 3):
    _s, _run = score_triple(*_t)
    if _s > 0:
        TRIPLES[mask_of(_t)] = (_s, _run)

# For the heuristic: windows that would complete a same-colour run through card x
RUN_WINDOWS = [[] for _ in range(N_CARDS)]
for _col in range(N_COLOURS):
    for _start in range(1, MAX_NUMBER - 1):
        _ids = [_col * MAX_NUMBER + (_start + k - 1) for k in range(3)]
        for _x in _ids:
            _o = [i for i in _ids if i != _x]
            RUN_WINDOWS[_x].append((1 << _o[0], 1 << _o[1]))

# ...and groups that would complete a set through card x
SET_GROUPS = [[] for _ in range(N_CARDS)]
for _n in range(1, MAX_NUMBER + 1):
    _same = [c * MAX_NUMBER + (_n - 1) for c in range(N_COLOURS)]
    for _x in _same:
        _o = [i for i in _same if i != _x]
        for _pair in combinations(_o, 2):
            SET_GROUPS[_x].append((1 << _pair[0], 1 << _pair[1]))


def hand_combos(hand):
    """All valid 3-card combos in a hand: [(points, (a,b,c), is_same_colour_run)]"""
    out = []
    for a, b, c in combinations(hand, 3):
        t = TRIPLES.get((1 << a) | (1 << b) | (1 << c))
        if t:
            out.append((t[0], (a, b, c), t[1]))
    return out
