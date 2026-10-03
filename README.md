# Okey Bot - Automated Card Game Player

An AI-powered bot that reads Okey Game cards from your screen and automatically plays them based on game strategy.

## Features

✅ **Card Recognition** - Detects up to 5 cards on screen using computer vision  
✅ **Color Detection** - Identifies all 4 card colors (red, blue, green, yellow)  
✅ **Number Recognition** - Reads card numbers (1-9) using OCR  
✅ **Automatic Decisions** - Makes strategic decisions about which cards to play  
✅ **Game Automation** - Automatically clicks cards and presses game buttons  
✅ **Safety Features** - Emergency stop (move mouse to corner)  
✅ **Modular Code** - Easy to customize strategy and configuration  

## File Structure

```
okey-bot/
├── main.py                 # Entry point - run this to play!
├── calibrate.py            # Calibration tool - run this first!
├── config.py               # Configuration (all settings in one place)
├── card_recognizer.py      # Vision & card detection
├── window_detector.py      # Auto-detects movable card window
├── decision_engine.py      # Game strategy & decision making
├── game_automation.py      # Mouse/keyboard automation
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `opencv-python` - Computer vision and image processing
- `easyocr` - Text recognition for card numbers
- `mss` - Screen capture
- `pyautogui` - Mouse and keyboard automation
- `pillow` - Image handling
- `numpy` - Numerical operations

**Note:** EasyOCR will download a model on first run (~100MB)

### Step 2: Run Calibration (Important!)

The bot has **auto-detection** for the movable card window! But you should calibrate first to ensure everything is tuned:

```bash
python calibrate.py
```

This will:
1. ✓ Auto-detect your card game window
2. ✓ Test card color detection
3. ✓ Test OCR number recognition
4. ✓ Generate debug images (captured_cards.png, mask_*.png)
5. ✓ Show you HSV values to fine-tune colors if needed

**Review the generated images** to see if the bot is seeing your cards correctly.

### Step 3: Configure Your Setup

Edit `config.py` to match your game:

```python
# Auto-detection is enabled by default!
AUTO_DETECT_WINDOW = True  # Window position detected automatically

# Game controls (for Metin2 Okey)
CONTROLS = {
    "left_click": "left",      # Select/use cards
    "right_click": "right",    # Discard cards
    "use": "enter",            # Confirm (if needed)
}

# HSV color ranges (pre-tuned for Metin2, adjust if needed)
COLOR_RANGES = {
    "red": ([160, 50, 100], [180, 255, 255]),
    "blue": ([90, 80, 80], [130, 255, 255]),
    "yellow": ([15, 100, 100], [35, 255, 255]),
}
```

If colors aren't detected well after calibration:
1. Check the mask_*.png images
2. Use HSV values from calibrate.py output
3. Adjust the ranges in `COLOR_RANGES`

## Usage

### Quick Start (Recommended Order)

**1. Calibrate (first time only)**
```bash
python calibrate.py
```
- Auto-detects your card window
- Tests color/number detection
- Generates debug images
- Shows you HSV values if you need to tune colors

**2. Run the Bot**
```bash
python main.py
```

The bot will:
1. Initialize card recognizer (downloads OCR model on first run)
2. Auto-detect the card window position
3. Print instructions
4. Start reading and playing cards

### Test Card Recognition Only

To test without clicking anything (safest):

Edit `main.py` and change:
```python
bot.run()  # Comment this out
```

To:
```python
bot.test_card_recognition()  # Uncomment this
```

This just reads cards 5 times without any clicking.

### Emergency Stop

**Move your mouse to the TOP-LEFT CORNER of your screen** to emergency stop the bot at any time (pyautogui failsafe).

## Configuration Tips

### Screen Region

Run this to find the right coordinates:
```python
import mss
import cv2

sss = mss.mss()
# Capture your whole screen to see it
screenshot = sss.grab(sss.monitors[1])
cv2.imwrite('screen.png', screenshot)
```

### Colors

If colors aren't detected:
1. Set `DEBUG = True` in `config.py`
2. Set `SAVE_SCREENSHOTS = True`
3. Run the bot
4. Check `screenshots/` to see what it detected
5. Adjust HSV values (or show me a screenshot!)

### Game Controls

Update these based on your game:
```python
CONTROLS = {
    "use": "enter",      # What key confirms playing cards?
    "discard": "d",      # What key discards cards?
    "pull": "space",     # What key pulls new cards?
}
```

## How the Bot Plays Okey

The bot implements the actual **Metin2 Okey game rules**:

### Game Mechanics
1. **SETS** - 3+ cards with the same number (any color)
   - Example: 7♠, 7♥, 7♦
   
2. **RUNS** - 3+ consecutive cards of the same color
   - Example: 6♠, 7♠, 8♠

3. **Scoring** - More cards and higher numbers = more points

### Bot Strategy
On each turn, the bot:
1. **Finds all valid sets** in hand (3+ cards with same number)
2. **Finds all valid runs** in hand (3+ consecutive, same color)
3. **Scores each combination** (length + card values)
4. **Plays the best combination** (use action)
5. **If no valid combinations** → discards the worst card

### Scoring System
- Base score: 10 points per card
- Set bonus: +5 points
- Card value: add the card number to score
- Worst card: lowest number + most common in hand

### Customizing Strategy

Edit `decision_engine.py` to customize:

**Change how combinations are scored:**
```python
def _score_combination(self, combo, cards):
    # Favor longer combinations
    score = len(combo["indices"]) * 20  # Increased from 10
    
    # Weight sets higher than runs
    if combo["type"] == "SET":
        score += 50  # Increased from 5
    
    return score
```

**Change which card to discard:**
```python
def _find_worst_card(self, cards):
    # Discard highest card instead of lowest
    return max(range(len(cards)), key=lambda i: cards[i]["number"])
```

**Add custom logic:**
```python
def decide(self, cards):
    # Example: always keep cards you can build on
    analysis = self.analyze_cards(cards)
    
    # Your custom logic here
    if some_condition:
        return {
            "action": "use",
            "card_indices": [0, 1, 2],
            "reason": "Custom logic"
        }
    
    # Fall back to default
    return super().decide(cards)
```

## Debugging

### Enable Debug Mode

Set in `config.py`:
```python
DEBUG = True
```

This will print:
- Card detection details (color, number for each card)
- Sets and runs found
- Decision reasoning (why the bot chose that action)
- Cards involved in the action
- Automation actions (clicks, key presses)

### Enable Screenshot Saving

Set in `config.py`:
```python
SAVE_SCREENSHOTS = True
```

Screenshots of each detected card will be saved to `screenshots/` folder. Useful for checking if colors/numbers are being read correctly.

### Analyze Card Composition

In `decision_engine.py`, you can call `analyze_cards()` to see what's in your hand:

```python
def decide(self, cards):
    analysis = self.analyze_cards(cards)
    
    # Shows:
    # - All cards in hand (with indices)
    # - Cards by color
    # - Cards by number
    # - Valid sets available
    # - Valid runs available
    
    print(f"Cards: {analysis['card_list']}")
    print(f"Sets: {analysis['valid_sets']}")
    print(f"Runs: {analysis['valid_runs']}")
```

### Test Recognition Without Playing

```python
bot = OkeyBot()
bot.test_card_recognition()  # Just reads, doesn't play
```

This runs the bot in test mode - it reads cards 5 times but doesn't click anything.

## Troubleshooting

### "No cards detected"
- Check `GAME_REGION` coordinates are correct
- Try `SAVE_SCREENSHOTS = True` to see what it's capturing
- Make sure cards are clearly visible in the game

### "Wrong colors detected"
- HSV values might need tuning for your display
- Run with `SAVE_SCREENSHOTS = True` and check results
- You may need different values for different lighting conditions

### "Numbers not being read"
- OCR might struggle with small/blurry text
- Try cropping card images larger in `detect_card_regions()`
- Ensure good contrast between number and card background

### "Bot clicks wrong cards"
- Check that card order detection is working (debug mode)
- Verify `GAME_REGION` coordinates
- Test clicking manually to verify your `CONTROLS` keys work

### "Game doesn't respond"
- Increase `TIMINGS["action_delay"]` - give game more time
- Make sure the game window is focused
- Check that you're using the correct keys in `CONTROLS`

## Advanced Tips

### Running Multiple Instances
- Each instance needs its own config
- Use different `GAME_REGION` values for different screen positions

### Batch Testing
```python
results = []
for i in range(100):
    cards = bot.recognizer.read_cards()
    results.append(cards)
    time.sleep(1)
```

### Custom Automation
You can extend `GameAutomation` with more actions:
```python
def double_click(self, card):
    x, y, w, h = card["position"]
    click_x = self.game_region["left"] + x + w // 2
    click_y = self.game_region["top"] + y + h // 2
    pyautogui.click(click_x, click_y, clicks=2)
```

## Performance Notes

- First run takes ~30s (OCR model download + initialization)
- Subsequent runs: ~2-5s per decision cycle
- Main bottleneck is OCR - optimize if needed

## Safety & Disclaimers

⚠️ **Use at your own risk!**

- Always test in a safe environment first
- Keep emergency stop ready (move mouse to corner)
- Use only on games where automation is allowed
- Don't leave bot running unattended

## Support

If you run into issues:

1. **Enable DEBUG mode** in `config.py`
2. **Save screenshots** to see what's being detected
3. **Check terminal output** for error messages
4. **Test recognition** without playing first

## License

Feel free to use and modify this code for your own projects!

---

**Happy gaming! 🎮**
