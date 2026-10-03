"""
Calibration Tool
Helps tune window detection and color ranges
"""

import cv2
import numpy as np
import mss
import time
from window_detector import WindowDetector, validate_window_region
from config import GAME_REGION


def calibrate_window_detection():
    """
    Test window auto-detection and show results
    """
    print("\n" + "=" * 60)
    print("WINDOW DETECTION CALIBRATION")
    print("=" * 60)
    
    detector = WindowDetector()
    
    print("\nTesting window detection...")
    print("(Make sure the Okey card game window is visible)")
    
    for attempt in range(3):
        print(f"\nAttempt {attempt + 1}/3...")
        detected = detector.find_card_window()
        
        if detected and validate_window_region(detected):
            print(f"  ✓ Window found!")
            print(f"    Top: {detected['top']}")
            print(f"    Left: {detected['left']}")
            print(f"    Width: {detected['width']}")
            print(f"    Height: {detected['height']}")
            return detected
        else:
            print(f"  ✗ Not found, retrying...")
            time.sleep(1)
    
    print("\n✗ Could not auto-detect window")
    print("Using manual coordinates from config.py")
    return GAME_REGION


def calibrate_colors():
    """
    Test color detection and help tune HSV ranges
    """
    print("\n" + "=" * 60)
    print("COLOR DETECTION CALIBRATION")
    print("=" * 60)
    
    screen = mss.mss()
    
    print("\nCapturing card area...")
    screenshot = screen.grab(GAME_REGION)
    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    # Save the captured area
    cv2.imwrite("captured_cards.png", frame)
    print("  ✓ Saved: captured_cards.png")
    
    # Show HSV values
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Get some sample pixels and their HSV values
    h, w = frame.shape[:2]
    sample_points = [
        (w // 6, h // 2, "First card (left)"),
        (w // 3, h // 2, "Second card"),
        (w // 2, h // 2, "Middle card"),
        (2 * w // 3, h // 2, "Fourth card"),
        (5 * w // 6, h // 2, "Last card (right)"),
    ]
    
    print("\nSample HSV values from card centers:")
    print("(Use these to tune COLOR_RANGES in config.py)")
    
    for x, y, label in sample_points:
        hsv_val = hsv[y, x]
        h_val, s_val, v_val = hsv_val
        print(f"  {label:25s}: H={h_val:3d}  S={s_val:3d}  V={v_val:3d}")
    
    # Analyze color distribution
    print("\n\nColor Distribution Analysis:")
    print("-" * 60)
    
    # Test each color range
    color_ranges = {
        "red": ([160, 50, 100], [180, 255, 255]),
        "blue": ([90, 80, 80], [130, 255, 255]),
        "yellow": ([15, 100, 100], [35, 255, 255]),
        "green": ([35, 80, 80], [85, 255, 255]),
    }
    
    for color_name, (lower_list, upper_list) in color_ranges.items():
        lower = np.array(lower_list)
        upper = np.array(upper_list)
        mask = cv2.inRange(hsv, lower, upper)
        pixel_count = cv2.countNonZero(mask)
        percentage = (pixel_count / (hsv.shape[0] * hsv.shape[1])) * 100
        
        print(f"  {color_name:10s}: {pixel_count:6d} pixels ({percentage:5.1f}%)")
        
        # Save mask for visual inspection
        cv2.imwrite(f"mask_{color_name}.png", mask)
    
    print("\nMask images saved for visual inspection:")
    print("  - mask_red.png, mask_blue.png, etc.")
    
    print("\nIf colors aren't detected well:")
    print("  1. Check the captured_cards.png and mask_*.png images")
    print("  2. Adjust HSV ranges in COLOR_RANGES (config.py)")
    print("  3. Hue: 0-180 | Saturation: 0-255 | Value: 0-255")


def test_ocr():
    """
    Test OCR on captured cards
    """
    print("\n" + "=" * 60)
    print("OCR CALIBRATION")
    print("=" * 60)
    
    try:
        from easyocr import Reader
        from config import OCR_LANGUAGE
        
        print("\nInitializing OCR reader...")
        reader = Reader(OCR_LANGUAGE)
        
        screen = mss.mss()
        screenshot = screen.grab(GAME_REGION)
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Try to detect cards and read numbers
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        cards_found = 0
        print("\nTesting OCR on detected cards:")
        
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by card size
            if w > 30 and h > 50:
                card_img = frame[y:y+h, x:x+w]
                
                # Try OCR
                result = reader.readtext(card_img, detail=0)
                
                if result:
                    text = ' '.join(result)
                    print(f"  Card {cards_found + 1}: {text}")
                    cards_found += 1
                else:
                    print(f"  Card {cards_found + 1}: [no text detected]")
                    cards_found += 1
        
        print(f"\nDetected {cards_found} cards total")
        
    except Exception as e:
        print(f"✗ OCR test failed: {e}")


def show_summary():
    """
    Show a summary of detected configuration
    """
    print("\n" + "=" * 60)
    print("CALIBRATION SUMMARY")
    print("=" * 60)
    
    print("\nDetected Configuration:")
    print(f"  Game Region: {GAME_REGION}")
    print("\nTo apply these settings:")
    print("  1. Update GAME_REGION in config.py if needed")
    print("  2. Run the bot: python main.py")
    
    print("\nTroubleshooting:")
    print("  - Set DEBUG = True in config.py for detailed logs")
    print("  - Set SAVE_SCREENSHOTS = True to debug card detection")
    print("  - Check captured_cards.png to verify card area")


def main():
    """Run all calibration tests"""
    print("\n" + "=" * 60)
    print("OKEY BOT - CALIBRATION TOOL")
    print("=" * 60)
    
    # Test window detection
    detected_region = calibrate_window_detection()
    
    # Test color detection
    calibrate_colors()
    
    # Test OCR
    test_ocr()
    
    # Show summary
    show_summary()
    
    print("\n✓ Calibration complete!")
    print("\nNext steps:")
    print("  1. Review the generated images (captured_cards.png, mask_*.png)")
    print("  2. Adjust settings in config.py if needed")
    print("  3. Run: python main.py")


if __name__ == "__main__":
    main()
