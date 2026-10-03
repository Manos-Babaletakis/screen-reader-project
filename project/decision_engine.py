"""
Decision Engine Module
Contains Okey game logic and strategy for deciding which cards to play

Okey Rules:
- SET: 3 cards with same number, any color (e.g., 7♠, 7♥, 7♦)
- RUN: 3+ consecutive cards, same color (e.g., 6♠, 7♠, 8♠)
- Goal: Find and play valid combinations to earn points
- Strategy: Maximize point value by finding high-value combinations
"""

from config import STRATEGY, DEBUG


class DecisionEngine:
    """Makes decisions about which cards to play based on Okey game logic"""
    
    def __init__(self):
        """Initialize the decision engine"""
        self.strategy = STRATEGY
        self.played_combinations = []  # Track what we've played
    
    def decide(self, cards):
        """
        Analyze cards and decide what to do (Okey Game Logic)
        
        Args:
            cards: List of card dictionaries from CardRecognizer
                  [{"color": str, "number": int, "position": tuple, "index": int}, ...]
        
        Returns:
            Dictionary with decision:
            {
                "action": "use" | "discard" | "pull",
                "card_indices": [0, 2, 3],  # Which cards to interact with
                "reason": "explanation"      # Why this decision was made
            }
        """
        
        if DEBUG:
            print("\n=== DECISION ENGINE ===")
            print(f"Analyzing {len(cards)} cards...")
        
        # If we have too few cards, pull more
        if len(cards) < self.strategy["min_cards_before_pull"]:
            decision = {
                "action": "pull",
                "card_indices": [],
                "reason": f"Too few cards ({len(cards)}), pulling more"
            }
            if DEBUG:
                print(f"Decision: {decision['action']} - {decision['reason']}")
            return decision
        
        # ==================== OKEY GAME LOGIC ====================
        
        # Find all valid combinations (sets and runs)
        sets = self._find_sets(cards)
        runs = self._find_runs(cards)
        
        if DEBUG:
            print(f"Found {len(sets)} sets and {len(runs)} runs")
        
        # Score each combination
        best_combination = None
        best_score = 0
        
        for combo in sets + runs:
            score = self._score_combination(combo, cards)
            if score > best_score:
                best_score = score
                best_combination = combo
        
        # If we found a good combination, use it
        if best_combination and best_score > 0:
            decision = {
                "action": "use",
                "card_indices": best_combination["indices"],
                "reason": f"Found {best_combination['type']}: {best_combination['description']} (score: {best_score})"
            }
        else:
            # No good combination - discard worst card
            worst_idx = self._find_worst_card(cards)
            decision = {
                "action": "discard",
                "card_indices": [worst_idx],
                "reason": f"No valid sets/runs found, discarding card {worst_idx} ({cards[worst_idx]['color']} {cards[worst_idx]['number']})"
            }
        
        if DEBUG:
            print(f"Decision: {decision['action']} - {decision['reason']}")
            if decision['card_indices']:
                print(f"Cards: {decision['card_indices']}")
        
        return decision
    
    def _find_sets(self, cards):
        """
        Find all valid SETS in hand
        A SET = 3+ cards with the same number, any color
        
        Args:
            cards: List of card dictionaries
        
        Returns:
            List of valid set combinations
        """
        sets = []
        
        # Group by number
        by_number = {}
        for i, card in enumerate(cards):
            num = card["number"]
            if num not in by_number:
                by_number[num] = []
            by_number[num].append(i)
        
        # For each number, if we have 3+ cards, it's a valid set
        for num, indices in by_number.items():
            if len(indices) >= 3:
                sets.append({
                    "type": "SET",
                    "indices": indices,
                    "description": f"3x {num}s ({', '.join([cards[i]['color'] for i in indices])})",
                    "num": num
                })
        
        return sets
    
    def _find_runs(self, cards):
        """
        Find all valid RUNS in hand
        A RUN = 3+ consecutive cards of the same color
        
        Args:
            cards: List of card dictionaries
        
        Returns:
            List of valid run combinations
        """
        runs = []
        
        # Group by color
        by_color = {}
        for i, card in enumerate(cards):
            color = card["color"]
            if color not in by_color:
                by_color[color] = []
            by_color[color].append((card["number"], i))
        
        # For each color, look for consecutive sequences
        for color, num_indices in by_color.items():
            # Sort by number
            num_indices.sort(key=lambda x: x[0])
            numbers = [x[0] for x in num_indices]
            indices = [x[1] for x in num_indices]
            
            # Find consecutive sequences of length 3+
            for start_idx in range(len(numbers)):
                run_numbers = []
                run_indices = []
                
                for i in range(start_idx, len(numbers)):
                    # Check if consecutive
                    if not run_numbers or numbers[i] == run_numbers[-1] + 1:
                        run_numbers.append(numbers[i])
                        run_indices.append(indices[i])
                    else:
                        break
                
                # If we have a run of 3+, add it
                if len(run_numbers) >= 3:
                    runs.append({
                        "type": "RUN",
                        "indices": run_indices,
                        "description": f"{run_numbers[0]}-{run_numbers[-1]} {color}",
                        "color": color,
                        "numbers": run_numbers
                    })
        
        return runs
    
    def _score_combination(self, combo, cards):
        """
        Score a combination based on:
        - Length (more cards = higher score)
        - Type (sets are worth more than runs typically)
        - Card values (higher cards = higher score)
        
        Args:
            combo: Combination dictionary
            cards: List of all cards
        
        Returns:
            Integer score
        """
        score = 0
        
        # Base score from card count
        score += len(combo["indices"]) * 10
        
        # Bonus for sets vs runs
        if combo["type"] == "SET":
            score += 5  # Sets are slightly more valuable
        
        # Add value from card numbers
        for idx in combo["indices"]:
            score += cards[idx]["number"]
        
        return score
    
    def _find_worst_card(self, cards):
        """
        Find the worst card to discard
        Worst = lowest number, most common in hand (less useful)
        
        Args:
            cards: List of card dictionaries
        
        Returns:
            Index of worst card
        """
        # Count card frequency by number
        number_counts = {}
        for card in cards:
            num = card["number"]
            number_counts[num] = number_counts.get(num, 0) + 1
        
        # Find the lowest card that appears most frequently
        worst_idx = 0
        worst_score = float('inf')
        
        for i, card in enumerate(cards):
            # Score = card value (lower is worse) - frequency (higher count = worse)
            score = card["number"] - (number_counts[card["number"]] * 2)
            
            if score < worst_score:
                worst_score = score
                worst_idx = i
        
        return worst_idx
    
    def analyze_cards(self, cards):
        """
        Helper function: Analyze card composition for debugging
        Shows sets, runs, and card organization
        
        Returns:
            Dictionary with detailed card analysis
        """
        analysis = {
            "total_cards": len(cards),
            "by_color": {},
            "by_number": {},
            "valid_sets": [],
            "valid_runs": [],
            "card_list": []
        }
        
        # List all cards
        for i, card in enumerate(cards):
            analysis["card_list"].append(f"{i}: {card['color'][0].upper()} {card['number']}")
        
        # Count by color
        for card in cards:
            color = card["color"]
            if color not in analysis["by_color"]:
                analysis["by_color"][color] = []
            analysis["by_color"][color].append(card["number"])
        
        # Count by number
        for card in cards:
            num = card["number"]
            if num not in analysis["by_number"]:
                analysis["by_number"][num] = []
            analysis["by_number"][num].append(card["color"])
        
        # Find all valid sets (3+ cards with same number)
        for num, colors in analysis["by_number"].items():
            if len(colors) >= 3:
                analysis["valid_sets"].append(f"{num}x ({len(colors)} cards)")
        
        # Find all valid runs (3+ consecutive, same color)
        for color in analysis["by_color"]:
            numbers = sorted(analysis["by_color"][color])
            # Look for consecutive sequences
            for i in range(len(numbers) - 2):
                if numbers[i+1] == numbers[i] + 1 and numbers[i+2] == numbers[i+1] + 1:
                    run_end = numbers[i] + 2
                    for j in range(i+2, len(numbers)):
                        if numbers[j] == run_end + 1:
                            run_end = numbers[j]
                        else:
                            break
                    analysis["valid_runs"].append(f"{color}: {numbers[i]}-{run_end}")
                    break  # Don't double-count overlapping runs
        
        return analysis
