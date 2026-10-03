"""
Strategy Examples
Different ways to customize the bot's game logic for Okey
Copy these examples into decision_engine.py's decide() method
"""

# ===================================================================
# STRATEGY 1: AGGRESSIVE - Always play valid combinations
# ===================================================================
def strategy_aggressive(self, cards):
    """
    Play any valid set or run found, prioritize longer combinations
    """
    sets = self._find_sets(cards)
    runs = self._find_runs(cards)
    
    # Find longest combination
    best = None
    for combo in sets + runs:
        if not best or len(combo["indices"]) > len(best["indices"]):
            best = combo
    
    if best:
        return {
            "action": "use",
            "card_indices": best["indices"],
            "reason": f"Aggressive: Playing {len(best['indices'])}-card {best['type']}"
        }
    
    # Discard if no combo
    worst = self._find_worst_card(cards)
    return {
        "action": "discard",
        "card_indices": [worst],
        "reason": "Aggressive: No valid combo found, discarding worst"
    }


# ===================================================================
# STRATEGY 2: CONSERVATIVE - Only play high-value combinations
# ===================================================================
def strategy_conservative(self, cards):
    """
    Only play combinations worth 25+ points
    Otherwise wait for better combinations
    """
    sets = self._find_sets(cards)
    runs = self._find_runs(cards)
    
    best_combo = None
    best_score = 0
    
    for combo in sets + runs:
        score = self._score_combination(combo, cards)
        if score > best_score:
            best_score = score
            best_combo = combo
    
    # Only play if score is high enough
    if best_combo and best_score >= 25:
        return {
            "action": "use",
            "card_indices": best_combo["indices"],
            "reason": f"Conservative: High-value combo ({best_score} points)"
        }
    
    # Otherwise discard worst card
    worst = self._find_worst_card(cards)
    return {
        "action": "discard",
        "card_indices": [worst],
        "reason": f"Conservative: Waiting for better combo (best: {best_score} points)"
    }


# ===================================================================
# STRATEGY 3: MAXIMIZE HAND SIZE - Keep cards, minimize discards
# ===================================================================
def strategy_minimize_discard(self, cards):
    """
    Rarely discard - always try to keep hand size up
    """
    sets = self._find_sets(cards)
    runs = self._find_runs(cards)
    
    best_combo = None
    best_score = 0
    
    for combo in sets + runs:
        score = self._score_combination(combo, cards)
        if score > best_score:
            best_score = score
            best_combo = combo
    
    # Always play if possible
    if best_combo:
        return {
            "action": "use",
            "card_indices": best_combo["indices"],
            "reason": f"Playing to keep hand full: {best_combo['description']}"
        }
    
    # Pull more cards instead of discarding
    if len(cards) < 5:
        return {
            "action": "pull",
            "card_indices": [],
            "reason": "Hand not full - pulling more cards"
        }
    
    # Only discard as last resort
    worst = self._find_worst_card(cards)
    return {
        "action": "discard",
        "card_indices": [worst],
        "reason": "No combos and hand full - must discard"
    }


# ===================================================================
# STRATEGY 4: RUNS ONLY - Prefer runs over sets
# ===================================================================
def strategy_runs_preferred(self, cards):
    """
    Prefer runs (consecutive same color) over sets
    Runs earn more total points if they're longer
    """
    sets = self._find_sets(cards)
    runs = self._find_runs(cards)
    
    # Find best run
    best_run = None
    for run in runs:
        if not best_run or len(run["indices"]) > len(best_run["indices"]):
            best_run = run
    
    # Find best set
    best_set = None
    for s in sets:
        if not best_set or len(s["indices"]) > len(best_set["indices"]):
            best_set = s
    
    # Prefer runs: only play set if run is missing
    if best_run:
        return {
            "action": "use",
            "card_indices": best_run["indices"],
            "reason": f"Run priority: Playing {best_run['description']}"
        }
    
    if best_set:
        return {
            "action": "use",
            "card_indices": best_set["indices"],
            "reason": f"Run not available: Playing set of {best_set['num']}s"
        }
    
    # Discard if no combos
    worst = self._find_worst_card(cards)
    return {
        "action": "discard",
        "card_indices": [worst],
        "reason": "No runs or sets available"
    }


# ===================================================================
# STRATEGY 5: SMART DISCARD - Discard cards based on context
# ===================================================================
def strategy_smart_discard(self, cards):
    """
    When discarding, consider:
    - Cards that block future combos
    - High numbers that can't be easily played
    - Cards you already have pairs of
    """
    sets = self._find_sets(cards)
    runs = self._find_runs(cards)
    
    best_combo = None
    best_score = 0
    
    for combo in sets + runs:
        score = self._score_combination(combo, cards)
        if score > best_score:
            best_score = score
            best_combo = combo
    
    if best_combo:
        return {
            "action": "use",
            "card_indices": best_combo["indices"],
            "reason": f"Playing combo: {best_combo['description']}"
        }
    
    # Smart discard logic
    analysis = self.analyze_cards(cards)
    
    # Don't discard cards that appear once
    for i, card in enumerate(cards):
        count = len(analysis["by_number"].get(card["number"], []))
        # If this card is unique, keep it
        if count == 1:
            # Find a different card to discard
            for j, other_card in enumerate(cards):
                other_count = len(analysis["by_number"].get(other_card["number"], []))
                if other_count > 1:  # Discard duplicates instead
                    return {
                        "action": "discard",
                        "card_indices": [j],
                        "reason": f"Smart discard: {other_card['color']} {other_card['number']} (duplicate)"
                    }
    
    # Fallback to worst card
    worst = self._find_worst_card(cards)
    return {
        "action": "discard",
        "card_indices": [worst],
        "reason": "Smart discard: worst card"
    }


# ===================================================================
# HOW TO USE THESE EXAMPLES
# ===================================================================
"""
1. Copy one of these functions into decision_engine.py
2. Replace the decide() method with your chosen strategy
3. Or call the strategy function from within decide():

Example in decision_engine.py:

    def decide(self, cards):
        # Use the aggressive strategy
        return self.strategy_aggressive(cards)
    
    def strategy_aggressive(self, cards):
        # Copy the function body from above
        ...

4. Tweak the values to suit your playstyle
5. Run the bot and see how it performs!
"""
