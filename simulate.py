"""Simulate full games to measure how often a strategy reaches 300 / 400 points."""
import random, sys, time
from okey_rules import ALL_CARDS, HAND_SIZE
from okey_solver import OkeySolver

def run(n_games, mode, budget=0.05, seed=1):
    rng = random.Random(seed)
    solver = OkeySolver(time_budget=budget, min_samples=20, max_samples=400, seed=seed)
    scores = []
    for g in range(n_games):
        deck = list(ALL_CARDS); rng.shuffle(deck)
        if mode == "heuristic":
            scores.append(solver.play_out(deck[:HAND_SIZE], deck[HAND_SIZE:]))
            continue
        hand, pos, total = deck[:HAND_SIZE], HAND_SIZE, 0
        while True:
            unseen = deck[pos:]
            mv, _ = solver.best_move(hand, unseen)
            if mv[0] == 'end': break
            if mv[0] == 'play':
                for c in mv[1]: hand.remove(c)
                total += mv[2]; k = 3
            else:
                hand.remove(mv[1]); k = 1
            draw = deck[pos:pos + k]; pos += len(draw); hand += draw
        scores.append(total)
    return scores

def report(name, s):
    n = len(s)
    print(f"{name:10s} games={n:4d} mean={sum(s)/n:6.1f}  "
          f"P(>=300)={sum(x>=300 for x in s)/n:5.1%}  P(>=400)={sum(x>=400 for x in s)/n:5.1%}  "
          f"min={min(s)} max={max(s)}")

if __name__ == "__main__":
    mode, n = sys.argv[1], int(sys.argv[2])
    t = time.time(); s = run(n, mode); report(mode, s); print(f"{time.time()-t:.0f}s")
