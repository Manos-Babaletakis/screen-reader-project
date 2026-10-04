# Okey Bot - Implementation Summary

## Game Rules Implemented

Based on Metin2 Okey Card Game rules:

### Valid Combinations

**SETS** - 3 or more cards with the same number, any color
- Example: 7♠, 7♥, 7♦
- 3 cards = minimum valid set
- More cards = higher score

**RUNS** - exactly 3 consecutive cards of the same color
- Example: 6♠, 7♠, 8♠
- Must be consecutive (no gaps)
- Same color only

### Game Flow

1. Bot reads 5 cards from hand
2. Finds all valid SETS and RUNS
3. Scores each combination
4. Plays the highest-scoring combination
5. If no valid combinations, discards the worst card
6. Pulls new cards from deck
7. Repeat until deck empty

### Scoring System

Each combination is scored based on:
- **Length**: 10 points per card
- **Type bonus**: +5 for sets (they're slightly more valuable)
- **Card values**: Sum of card numbers in combo
- **Worst card**: Lowest number cards that appear multiple times

### Decision Logic

```
If hand has valid SETS or RUNS:
  ├─ Score each combination
  ├─ Play the one with highest score
  └─ Reason: "Found SET/RUN with X cards (score: Y)"

Else (no valid combinations):
  ├─ Identify worst card
  ├─ Discard it
  └─ Reason: "No valid sets/runs, discarding worst"
```

## Bot Architecture

### Core Files

**`card_recognizer.py`** - Vision Module
- Auto-detects card window (handles movable window)
- Detects individual cards (up to 5)
- Identifies color (HSV-based)
- Reads number (OCR-based)

**`decision_engine.py`** - Game Logic Module
- Implements Okey rules
- Finds valid sets: `_find_sets()`
- Finds valid runs: `_find_runs()`
- Scores combinations: `_score_combination()`
- Selects worst card: `_find_worst_card()`
- **Main function**: `decide()` - returns action + cards

**`game_automation.py`** - Automation Module
- Clicks cards (left-click for use/select)
- Right-clicks cards (for discard)
- Presses keys
- Handles timing/delays

**`window_detector.py`** - Window Locator
- Auto-detects the card game window
- Finds golden border of Okey window
- Validates window region
- Fallback to manual coordinates if needed

**`main.py`** - Orchestrator
- Ties all modules together
- Main game loop
- Test mode (read without playing)

**`calibrate.py`** - Setup Tool
- Tests window detection
- Tests color detection
- Tests OCR
- Generates debug images

### Configuration

**`config.py`** - Central settings
- `AUTO_DETECT_WINDOW`: Enable/disable auto window detection
- `GAME_REGION`: Manual coordinates (fallback)
- `COLOR_RANGES`: HSV values for card colors
- `CONTROLS`: Game controls (click/discard/pull)
- `TIMINGS`: Delays between actions
- `STRATEGY`: Game preferences
- `DEBUG`: Enable detailed logging

## Implementation Details

### How Sets Are Found

```python
# Group cards by number
by_number = {}
for card in cards:
    if card.number not in by_number:
        by_number[card.number] = []
    by_number[card.number].append(card)

# Any group with 3+ cards = valid set
for number, cards_with_number in by_number.items():
    if len(cards_with_number) >= 3:
        return valid_set
```

### How Runs Are Found

```python
# Group cards by color
by_color = {}
for card in cards:
    if card.color not in by_color:
        by_color[card.color] = []
    by_color[card.color].append(card)

# For each color, find consecutive sequences
for color, cards_of_color in by_color.items():
    sort_by_number(cards_of_color)
    
    # Look for 3+ consecutive numbers
    for consecutive_sequence in find_sequences(cards_of_color):
        if len(consecutive_sequence) >= 3:
            return valid_run
```

### How Scoring Works

```python
def score_combination(combo):
    score = 0
    
    # Base: 10 points per card
    score += len(combo.cards) * 10
    
    # Type bonus: sets are worth slightly more
    if combo.type == "SET":
        score += 5
    
    # Add each card's number value
    for card in combo.cards:
        score += card.number
    
    return score

# Example:
# Set of three 7s (7, 7, 7)
# = 3*10 + 5 + 7+7+7 = 30 + 5 + 21 = 56 points
```

## Customization Guide

### Use Different Strategy

Edit `decision_engine.py`:

```python
def decide(self, cards):
    # Use one of the example strategies
    return self.strategy_aggressive(cards)  # or strategy_conservative, etc.
```

Or copy from `strategy_examples.py`:
- `strategy_aggressive` - Play any valid combo
- `strategy_conservative` - Only play high-scoring combos
- `strategy_minimize_discard` - Rarely discard
- `strategy_runs_preferred` - Favor runs over sets
- `strategy_smart_discard` - Smart discard logic

### Adjust Scoring

In `decision_engine.py`, edit `_score_combination()`:

```python
def _score_combination(self, combo, cards):
    score = 0
    
    # Increase weight on combination length
    score += len(combo["indices"]) * 20  # was 10
    
    # Increase bonus for sets
    if combo["type"] == "SET":
        score += 25  # was 5
    
    # Don't count card values (just count combo size)
    # for idx in combo["indices"]:
    #     score += cards[idx]["number"]
    
    return score
```

### Change Discard Logic

In `decision_engine.py`, edit `_find_worst_card()`:

```python
def _find_worst_card(self, cards):
    # Option 1: Discard highest card
    return max(range(len(cards)), key=lambda i: cards[i]["number"])
    
    # Option 2: Discard middle card (keep extremes)
    sorted_by_num = sorted(enumerate(cards), key=lambda x: x[1]["number"])
    return sorted_by_num[len(sorted_by_num) // 2][0]
    
    # Option 3: Discard most common number
    ...
```

### Debug Game Decisions

```python
def decide(self, cards):
    # Analyze current hand
    analysis = self.analyze_cards(cards)
    
    # Print what you have
    print("Hand:", analysis["card_list"])
    print("Valid Sets:", analysis["valid_sets"])
    print("Valid Runs:", analysis["valid_runs"])
    
    # Use default logic
    return super().decide(cards)
```

## Testing & Iteration

### Safe Testing

1. **Run calibration first**
   ```bash
   python calibrate.py
   ```
   - Verifies card detection
   - Generates debug images
   - No game interaction

2. **Test recognition only**
   ```python
   # In main.py, uncomment:
   bot.test_card_recognition()  # Read 5 times, no clicks
   ```

3. **Test with DEBUG enabled**
   ```python
   # In config.py:
   DEBUG = True
   ```
   - See detailed decision logic
   - Verify card detection
   - Check automation commands

### Performance Tuning

**If bot is too slow:**
- Reduce `TIMINGS["loop_delay"]` in config.py
- But give game time to respond!

**If cards not detected:**
- Run `calibrate.py` and check images
- Adjust HSV color ranges
- Ensure card window is fully visible

**If wrong combinations played:**
- Enable DEBUG mode
- Check `analyze_cards()` output
- Verify `_find_sets()` and `_find_runs()` logic
- Adjust scoring in `_score_combination()`

## Safety Features

✓ **Emergency Stop** - Move mouse to corner anytime  
✓ **Window Detection Validation** - Ensures valid region before reading  
✓ **Error Handling** - Continues on failures, doesn't crash  
✓ **Timing Delays** - Gives game time to respond  
✓ **Debug Logging** - Track exactly what bot is doing  
✓ **Test Mode** - Try without playing first  

## Expected Performance

**First run:**
- ~30 seconds (OCR model download + init)

**Per decision cycle:**
- ~2-3 seconds (capture + recognize + decide + execute)

**Bottleneck:**
- OCR reading numbers (EasyOCR is slow but accurate)

**Optimization potential:**
- Switch to faster OCR library
- Cache color detection
- Batch operations
