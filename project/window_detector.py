"""
Window Detector Module
Automatically finds the Okey card game window on screen (since it's movable)
"""

import cv2
import numpy as np
import mss
from config import DEBUG


class WindowDetector:
    """Detects the Okey card game window location"""
    
    def __init__(self):
        """Initialize the window detector"""
        self.screen = mss.mss()
    
    def find_card_window(self):
        """
        Scan the screen to find the Okey card game window
        Looks for the distinctive golden/yellow borders and card pattern
        
        Returns:
            Dictionary with window region: {"top": y, "left": x, "width": w, "height": h}
            or None if window not found
        """
        # Capture full screen
        screenshot = self.screen.grab(self.screen.monitors[1])
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        if DEBUG:
            print("Scanning screen for Okey card window...")
        
        # Convert to HSV for color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Look for the golden/yellow decorative border of the card game window
        # Gold/yellow hue range in HSV
        lower_gold = np.array([15, 100, 100])
        upper_gold = np.array([35, 255, 255])
        
        mask = cv2.inRange(hsv, lower_gold, upper_gold)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for a large rectangular region (the card game window)
        potential_windows = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Card window should be large enough and roughly rectangular
            if w > 250 and h > 150 and w < 600 and h < 400:
                aspect_ratio = w / h
                # Card window is roughly 2:1 to 3:1 width:height
                if 1.5 < aspect_ratio < 4.0:
                    area = cv2.contourArea(contour)
                    potential_windows.append({
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                        "area": area
                    })
        
        if not potential_windows:
            if DEBUG:
                print("  ✗ Card window not found")
            return None
        
        # Sort by area (largest is likely the card window)
        potential_windows.sort(key=lambda w: w["area"], reverse=True)
        window = potential_windows[0]
        
        # The detected region is the border; we need the card area inside it
        # Cards are typically in the top portion of the window
        card_region = {
            "top": window["y"] + 20,
            "left": window["x"] + 25,
            "width": window["w"] - 50,
            "height": window["h"] // 2 - 30  # Top half contains cards
        }
        
        if DEBUG:
            print(f"  ✓ Card window found at ({card_region['left']}, {card_region['top']})")
            print(f"    Size: {card_region['width']}x{card_region['height']}")
        
        return card_region
    
    def find_card_window_by_template(self):
        """
        Alternative method: Look for specific card patterns
        (More advanced, but more reliable)
        
        Returns:
            Dictionary with window region or None
        """
        screenshot = self.screen.grab(self.screen.monitors[1])
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Look for the characteristic card shape/number pattern
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Cards have clear borders - look for strong edges
        edges = cv2.Canny(gray, 50, 150)
        
        # Find horizontal lines (card edges are often horizontal)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 2))
        h_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Get the bounding rectangle of the largest contour
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)
            
            return {
                "top": y,
                "left": x,
                "width": w,
                "height": h
            }
        
        return None


def validate_window_region(region):
    """
    Validate that a window region seems reasonable
    
    Args:
        region: Dictionary with top, left, width, height
    
    Returns:
        Boolean: True if region is valid
    """
    if not region:
        return False
    
    # Check dimensions
    if region["width"] < 200 or region["height"] < 80:
        return False
    
    if region["width"] > 800 or region["height"] > 400:
        return False
    
    # Check position
    if region["top"] < 0 or region["left"] < 0:
        return False
    
    return True
