"""
Card Recognition Module
Detects and recognizes cards on screen using OpenCV and OCR
"""

import cv2
import numpy as np
import mss
from easyocr import Reader
import os
from config import (
    GAME_REGION, MIN_CARD_WIDTH, MIN_CARD_HEIGHT,
    COLOR_RANGES, OCR_LANGUAGE, DEBUG, SAVE_SCREENSHOTS, SCREENSHOT_DIR,
    AUTO_DETECT_WINDOW
)
from window_detector import WindowDetector, validate_window_region


class CardRecognizer:
    """Detects and recognizes cards on screen"""
    
    def __init__(self):
        """Initialize the card recognizer"""
        self.screen = mss.mss()
        self.game_region = GAME_REGION
        
        # Initialize window detector if auto-detection is enabled
        self.window_detector = None
        if AUTO_DETECT_WINDOW:
            self.window_detector = WindowDetector()
            print("Window auto-detection enabled")
        
        # Initialize OCR reader (loads model on first use)
        print("Initializing OCR reader... (this may take a moment)")
        self.reader = Reader(OCR_LANGUAGE)
        print("OCR ready!")
        
        # Create screenshot directory if needed
        if SAVE_SCREENSHOTS:
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    
    def capture_screen(self):
        """
        Capture the game area from screen
        Returns: OpenCV image (BGR format)
        """
        screenshot = self.screen.grab(self.game_region)
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return frame
    
    def detect_card_regions(self, frame):
        """
        Find individual card locations using contour detection
        
        Args:
            frame: OpenCV image
        
        Returns:
            List of tuples: [(x, y, width, height), ...]
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        card_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by minimum card size
            if w > MIN_CARD_WIDTH and h > MIN_CARD_HEIGHT:
                card_regions.append((x, y, w, h))
        
        # Sort left to right
        card_regions.sort(key=lambda r: r[0])
        
        if DEBUG:
            print(f"Detected {len(card_regions)} card regions")
        
        return card_regions
    
    def recognize_card(self, card_image):
        """
        Extract color and number from a card image
        
        Args:
            card_image: Cropped OpenCV image of a single card
        
        Returns:
            Dictionary: {"color": str, "number": int}
        """
        # Detect color
        color = self._detect_color(card_image)
        
        # Extract number using OCR
        number = self._extract_number(card_image)
        
        return {
            "color": color,
            "number": number
        }
    
    def _detect_color(self, card_image):
        """
        Detect card color based on HSV color space
        
        Args:
            card_image: Cropped card image
        
        Returns:
            String: color name ("red", "blue", "green", "yellow", or "unknown")
        """
        # Convert to HSV
        hsv = cv2.cvtColor(card_image, cv2.COLOR_BGR2HSV)
        
        max_matches = 0
        detected_color = "unknown"
        
        # Test each color range
        for color_name, (lower_list, upper_list) in COLOR_RANGES.items():
            lower = np.array(lower_list)
            upper = np.array(upper_list)
            
            # Create mask for this color
            mask = cv2.inRange(hsv, lower, upper)
            matches = cv2.countNonZero(mask)
            
            if matches > max_matches:
                max_matches = matches
                detected_color = color_name
        
        if DEBUG:
            print(f"  Color detected: {detected_color} (confidence: {max_matches} pixels)")
        
        return detected_color
    
    def _extract_number(self, card_image):
        """
        Extract the card number using OCR
        
        Args:
            card_image: Cropped card image
        
        Returns:
            Integer: card number (1-9), or None if not found
        """
        try:
            result = self.reader.readtext(card_image, detail=0)
            
            if result:
                # Try to parse as number
                for text in result:
                    if text.isdigit():
                        num = int(text)
                        if 1 <= num <= 9:
                            if DEBUG:
                                print(f"  Number detected: {num}")
                            return num
        except Exception as e:
            if DEBUG:
                print(f"  OCR error: {e}")
        
        if DEBUG:
            print(f"  Number: not found")
        return None
    
    def read_cards(self):
        """
        Main function: capture screen and recognize all visible cards
        
        Returns:
            List of dictionaries: [{"color": str, "number": int, "position": (x, y, w, h)}, ...]
        """
        # Auto-detect window position if enabled
        if self.window_detector:
            detected_region = self.window_detector.find_card_window()
            if validate_window_region(detected_region):
                self.game_region = detected_region
            elif DEBUG:
                print("  ✗ Window detection failed, using last known position")
        
        # Capture screen
        frame = self.capture_screen()
        
        # Find card regions
        card_regions = self.detect_card_regions(frame)
        
        # Recognize each card
        cards = []
        for idx, (x, y, w, h) in enumerate(card_regions):
            card_image = frame[y:y+h, x:x+w]
            
            if DEBUG:
                print(f"Recognizing card {idx + 1}/{len(card_regions)}:")
            
            card_data = self.recognize_card(card_image)
            card_data["position"] = (x, y, w, h)
            card_data["index"] = idx
            
            cards.append(card_data)
            
            # Save screenshot if enabled
            if SAVE_SCREENSHOTS:
                filename = f"{SCREENSHOT_DIR}/card_{idx}_{card_data['color']}_{card_data['number']}.png"
                cv2.imwrite(filename, card_image)
        
        return cards
