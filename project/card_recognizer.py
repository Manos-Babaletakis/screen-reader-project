"""
Card recognizer: finds the row of 5 face-up cards ANYWHERE on screen (the window is
movable), then reads each card's colour (hue of the card face) and number (the dark
digit printed on it).
"""
import os
import cv2
import numpy as np
import mss
from config import COLOR_RANGES, COLOURS, MAX_NUMBER, HAND_SIZE, DEBUG, SAVE_SCREENSHOTS, SCREENSHOT_DIR

# card face size relative to screen height (1080p: ~40x55 px)
CARD_H_FRAC = (0.035, 0.085)


class CardRecognizer:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]
        self.row_box = None            # (x, y, w, h) of the card row, cached for speed
        self._ocr = None
        self._ocr_kind = None
        if SAVE_SCREENSHOTS:
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ------------------------------------------------------------------ capture
    def grab(self, box=None):
        mon = self.monitor if box is None else {
            "left": self.monitor["left"] + box[0], "top": self.monitor["top"] + box[1],
            "width": box[2], "height": box[3]}
        return cv2.cvtColor(np.array(self.sct.grab(mon)), cv2.COLOR_BGRA2BGR)

    # ---------------------------------------------------------------- locating
    @staticmethod
    def _colour_masks(hsv):
        masks = {}
        for name in COLOURS:
            m = None
            for lo, hi in COLOR_RANGES[name] if isinstance(COLOR_RANGES[name], list) else [COLOR_RANGES[name]]:
                part = cv2.inRange(hsv, np.array(lo), np.array(hi))
                m = part if m is None else cv2.bitwise_or(m, part)
            masks[name] = m
        return masks

    def find_cards(self, frame):
        """Return up to HAND_SIZE card boxes [(x,y,w,h,colour)] forming one row, left->right."""
        H = frame.shape[0]
        hmin, hmax = CARD_H_FRAC[0] * H, CARD_H_FRAC[1] * H
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        blobs = []
        for name, m in self._colour_masks(hsv).items():
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            n, _, stats, _ = cv2.connectedComponentsWithStats(m)
            for i in range(1, n):
                x, y, w, h, area = stats[i]
                if hmin <= h <= hmax and 0.55 <= w / h <= 0.95 and area > 0.55 * w * h:
                    blobs.append((x, y, w, h, name))
        # group blobs sharing a row (similar y & height); keep the biggest group
        best = []
        for b in blobs:
            row = sorted([c for c in blobs if abs(c[1] - b[1]) < 0.15 * b[3]
                          and abs(c[3] - b[3]) < 0.15 * b[3]], key=lambda c: c[0])
            # drop overlapping duplicates
            dedup = []
            for c in row:
                if not dedup or c[0] - dedup[-1][0] > 0.6 * c[2]:
                    dedup.append(c)
            if len(dedup) > len(best):
                best = dedup
        return best[:HAND_SIZE]

    # ----------------------------------------------------------------- reading
    @staticmethod
    def _glyph(card_bgr):
        """Isolate the dark digit in the middle of the card -> white-on-black, tight crop."""
        h, w = card_bgr.shape[:2]
        inner = card_bgr[int(h * .15):int(h * .85), int(w * .12):int(w * .88)]
        gray = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)
        # the digit is far darker than the card face (works for yellow, red and blue cards)
        bw = (gray < 0.4 * np.median(gray)).astype(np.uint8) * 255
        n, lab, stats, _ = cv2.connectedComponentsWithStats(bw)
        ih = inner.shape[0]
        best = None
        for i in range(1, n):
            x, y, ww, hh, a = stats[i]
            if hh > 0.3 * ih and (best is None or a > best[1]):
                best = (i, a)
        if best is None:
            return None
        keep = (lab == best[0]).astype(np.uint8) * 255
        x, y, ww, hh = cv2.boundingRect(keep)
        g = keep[y:y + hh, x:x + ww]
        return cv2.copyMakeBorder(g, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=0)

    def _init_ocr(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._ocr, self._ocr_kind = pytesseract, "tesseract"
        except Exception:
            import easyocr
            self._ocr, self._ocr_kind = easyocr.Reader(['en'], gpu=False), "easyocr"
        if DEBUG:
            print(f"OCR backend: {self._ocr_kind}")

    def _read_digit(self, glyph):
        """OCR a single digit 1..MAX_NUMBER from a white-on-black glyph image."""
        img = cv2.resize(255 - glyph, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        allow = "".join(str(i) for i in range(1, MAX_NUMBER + 1))
        if self._ocr_kind is None:
            self._init_ocr()
        if self._ocr_kind == "easyocr":
            res = [(t, c) for _, t, c in self._ocr.readtext(img, allowlist=allow, detail=1)
                   if t.strip() in list(allow)]
            return int(max(res, key=lambda r: r[1])[0]) if res else None
        txt = self._ocr.image_to_string(
            img, config=f"--psm 8 -c tessedit_char_whitelist={allow}").strip()
        return int(txt) if txt.isdigit() and 1 <= int(txt) <= MAX_NUMBER else None

    def read_cards(self, expected=HAND_SIZE):
        """Returns [{"color","number","position":(x,y,w,h) in SCREEN pixels,"index"}] or []"""
        frame, ox, oy = None, 0, 0
        if self.row_box:
            bx, by, bw, bh = self.row_box
            frame = self.grab(self.row_box)
            ox, oy = bx, by
            found = self.find_cards(frame)
            if len(found) < expected:
                frame = None
        if frame is None:
            frame, ox, oy = self.grab(), 0, 0
            found = self.find_cards(frame)
        if len(found) < expected or not found:
            self.row_box = None
            if DEBUG:
                print(f"  found {len(found)}/{expected} cards")
            return []
        xs = [b[0] for b in found]; ys = [b[1] for b in found]
        x0, y0 = min(xs) + ox, min(ys) + oy
        x1 = max(b[0] + b[2] for b in found) + ox; y1 = max(b[1] + b[3] for b in found) + oy
        pad = 20
        self.row_box = (max(0, x0 - pad), max(0, y0 - pad), (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad)

        cards = []
        for i, (x, y, w, h, colour) in enumerate(found):
            glyph = self._glyph(frame[y:y + h, x:x + w])
            number = self._read_digit(glyph) if glyph is not None else None
            cards.append({"color": colour, "number": number, "index": i,
                          "position": (int(x + ox + self.monitor["left"]), int(y + oy + self.monitor["top"]), int(w), int(h))})
            if SAVE_SCREENSHOTS:
                cv2.imwrite(f"{SCREENSHOT_DIR}/card{i}_{colour}_{number}.png", frame[y:y + h, x:x + w])
        if DEBUG:
            print("  read:", [(c["color"], c["number"]) for c in cards])
        return cards
