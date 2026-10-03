"""
Game Automation Module
Handles mouse and keyboard automation to interact with the game
"""

import pyautogui
import time
from config import CONTROLS, TIMINGS, GAME_REGION, DEBUG


class GameAutomation:
    """Handles mouse/keyboard automation for game interaction"""
    
    def __init__(self):
        """Initialize the automation module"""
        # Safety feature: move mouse to top-left corner to emergency stop
        pyautogui.FAILSAFE = True
        
        # Slow down pyautogui to ensure reliability
        pyautogui.PAUSE = 0.1
        
        self.controls = CONTROLS
        self.timings = TIMINGS
        self.game_region = GAME_REGION
        
        if DEBUG:
            print("Game Automation initialized")
            print("  - Move mouse to top-left corner to emergency stop")
    
    def click_card(self, card):
        """
        Click on a specific card
        
        Args:
            card: Card dictionary with "position" key
        """
        x, y, w, h = card["position"]
        
        # Calculate center of card
        click_x = self.game_region["left"] + x + w // 2
        click_y = self.game_region["top"] + y + h // 2
        
        if DEBUG:
            print(f"Clicking card at ({click_x}, {click_y})")
        
        pyautogui.click(click_x, click_y)
        time.sleep(self.timings["click_delay"])
    
    def click_cards(self, cards, card_indices):
        """
        Click on multiple cards in sequence
        
        Args:
            cards: List of card dictionaries
            card_indices: List of card indices to click
        """
        if DEBUG:
            print(f"Clicking {len(card_indices)} cards")
        
        for idx in card_indices:
            if idx < len(cards):
                self.click_card(cards[idx])
    
    def right_click_card(self, card):
        """
        Right-click on a specific card (for discarding)
        
        Args:
            card: Card dictionary with "position" key
        """
        x, y, w, h = card["position"]
        
        # Calculate center of card
        click_x = self.game_region["left"] + x + w // 2
        click_y = self.game_region["top"] + y + h // 2
        
        if DEBUG:
            print(f"Right-clicking card at ({click_x}, {click_y})")
        
        pyautogui.rightClick(click_x, click_y)
        time.sleep(self.timings["click_delay"])
    
    def right_click_cards(self, cards, card_indices):
        """
        Right-click on multiple cards in sequence (for discarding)
        
        Args:
            cards: List of card dictionaries
            card_indices: List of card indices to right-click
        """
        if DEBUG:
            print(f"Right-clicking {len(card_indices)} cards")
        
        for idx in card_indices:
            if idx < len(cards):
                self.right_click_card(cards[idx])
    
    def press_key(self, key_name):
        """
        Press a keyboard key
        
        Args:
            key_name: Name of key to press (from config CONTROLS)
        """
        if key_name in self.controls:
            key = self.controls[key_name]
            if DEBUG:
                print(f"Pressing key: {key}")
            pyautogui.press(key)
            time.sleep(self.timings["action_delay"])
        else:
            if DEBUG:
                print(f"Warning: Unknown key '{key_name}'")
    
    def execute_decision(self, cards, decision):
        """
        Execute a decision: click cards and press appropriate keys
        
        Args:
            cards: List of card dictionaries
            decision: Dictionary from DecisionEngine.decide()
        """
        action = decision.get("action", "pull")
        card_indices = decision.get("card_indices", [])
        
        if DEBUG:
            print(f"\nExecuting action: {action}")
        
        # Click the cards involved in this action
        if card_indices:
            if action == "discard":
                # For discard: right-click the cards
                self.right_click_cards(cards, card_indices)
            else:
                # For use: left-click the cards
                self.click_cards(cards, card_indices)
        
        # Press the action key if needed
        if action == "use":
            self.press_key("use")
        elif action == "pull":
            self.press_key("pull")
        
        # Extra delay after action completes
        time.sleep(self.timings["action_delay"])
    
    def wait(self, seconds):
        """
        Wait for specified seconds (respects FAILSAFE)
        
        Args:
            seconds: Time to wait in seconds
        """
        if DEBUG:
            print(f"Waiting {seconds}s...")
        time.sleep(seconds)
