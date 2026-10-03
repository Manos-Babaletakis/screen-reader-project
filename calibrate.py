"""Run with the Okey window open and 5 cards visible. Shows exactly what the bot sees."""
import cv2
import config
config.SAVE_SCREENSHOTS = True
from card_recognizer import CardRecognizer

r = CardRecognizer()
frame = r.grab()
cards = r.read_cards()
if not cards:
    cv2.imwrite("calibrate_screen.png", frame)
    print("No card row found. Saved calibrate_screen.png - check the card window is on the "
          "primary monitor and fully visible (not covered).")
else:
    for c in cards:
        x, y, w, h = c["position"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, f'{c["color"]} {c["number"]}', (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imwrite("calibrate_result.png", frame)
    print("Saved calibrate_result.png (green boxes + what was read) and screenshots/*.png (each card).")
    print("If a colour is wrong, tune COLOR_RANGES in config.py.")
