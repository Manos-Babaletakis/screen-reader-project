"""
Card recognizer: finds the row of 5 face-up cards ANYWHERE on screen (the window is
movable), then reads each card's colour (hue of the card face) and number (the dark
digit printed on it).
"""
import dpi  # noqa: F401  (must come before mss - see dpi.py)
import os
import cv2
import numpy as np
import mss
from config import COLOR_RANGES, COLOURS, MAX_NUMBER, HAND_SIZE, DEBUG, SAVE_SCREENSHOTS, SCREENSHOT_DIR

# Everything scales with the game's UI size, measured from the cards themselves.
# REF_CARD: card face size the digit reader was tuned on (cards are resized to it).
REF_CARD_W, REF_CARD_H = 38, 52
# Card height in the screenshot the button/deck templates were cut from (they match at
# 0.8x on a screen where cards are 52 px - i.e. they were cut at 125 % zoom).
TEMPLATE_CARD_H = 65
# card height relative to screen height, while the real size is still unknown (wide on purpose,
# but not below 3 %: the floating blue damage numbers are ~2 % tall and form a 'row' too)
CARD_H_FRAC = (0.03, 0.12)
CARD_H_TOL = (0.8, 1.25)       # once the card height is known: accept this range around it
# screen elements found by template matching, cut from screenshots of the card window
_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = {
    "end": os.path.join(_HERE, "end_button.png"),    # restarts the game
    "yes": os.path.join(_HERE, "yes_button.png"),    # confirms a discard
    "deck": os.path.join(_HERE, "deck.png"),         # left-click draws a card
}
# full sweep, only used when no card has been seen yet (so the UI scale is unknown)
SWEEP_SCALES = [round(0.5 + 0.05 * i, 2) for i in range(31)]          # 0.50 .. 2.00


class CardRecognizer:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]
        self.row_box = None            # (x, y, w, h) of the card row, cached for speed
        self.card_h = None             # measured card height in px (sets the UI scale)
        self._ocr = None
        self._ocr_kind = None
        self._tpl = {}                 # name -> (image, scale that matched)
        self._digit_cache = {}         # card face pixels -> number (skips OCR for repeats)
        self._shared_scale = None      # last scale any template matched at
        self._tpl_cache = {}           # (name, scale) -> resized template
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

    @property
    def scale(self):
        """Card size relative to REF_CARD_H (None = no card row seen yet)."""
        return self.card_h / REF_CARD_H if self.card_h else None

    @property
    def template_scale(self):
        """How much the templates must be resized to match the screen. Before any card has
        been measured (a new game starts with an empty table) assume the usual card size."""
        return (self.card_h or REF_CARD_H) / TEMPLATE_CARD_H

    def find_cards(self, frame, any_size=False):
        """Return up to HAND_SIZE card boxes [(x,y,w,h,colour)] forming one row, left->right.
        Once the card height is known only cards of about that size count (fewer false
        positives); any_size=True searches every plausible size again."""
        if self.card_h and not any_size:
            hmin, hmax = CARD_H_TOL[0] * self.card_h, CARD_H_TOL[1] * self.card_h
        else:
            H = self.monitor["height"]  # relative to the SCREEN, even for a cropped frame
            hmin, hmax = CARD_H_FRAC[0] * H, CARD_H_FRAC[1] * H
        k = max(3, int(round(5 * (self.scale or 1))))
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        blobs = []
        for name, m in self._colour_masks(hsv).items():
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
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

    def _scaled_template(self, name, s):
        key = (name, s)
        if key not in self._tpl_cache:
            tpl = self._tpl[name][0]
            self._tpl_cache[key] = tpl if s == 1.0 else cv2.resize(
                tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
        return self._tpl_cache[key]

    def _find_template(self, name, min_score=0.75, sweep=False):
        """SCREEN (x, y) of the centre of a template image, or None if it is not visible.
        Tries the scale that matched last time (one match - fast enough to poll), then the
        scale implied by the measured card size (+-8 %). With sweep=True a miss retries
        every scale from 0.5x to 2x (coarse pass at half resolution, then refined).
        A scale that matches is remembered."""
        if name not in self._tpl:
            self._tpl[name] = (cv2.imread(TEMPLATES[name]), None)
        known_scale = self._tpl[name][1]
        frame = self.grab()

        def match(scales, img=frame, shrink=1):
            best = (-1, None, None)
            for s in scales:
                t = self._scaled_template(name, round(s / shrink, 3))
                if t.shape[0] > img.shape[0] or t.shape[1] > img.shape[1] or min(t.shape[:2]) < 6:
                    continue
                _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED))
                if score > best[0]:
                    best = (score, s, ((loc[0] + t.shape[1] // 2) * shrink, (loc[1] + t.shape[0] // 2) * shrink))
            return best

        # The Yes button is small: it only scores high within ~1-2 % of the right scale, and
        # the scale guessed from the card height (51-52 px) is right on that edge. So try
        # this template's last scale, then the scale another template (the deck - found
        # before any discard) matched at - all were cut at the same zoom - and only guess
        # from the card height (in 2 % steps) when nothing has matched yet.
        score, tried = -1, []
        for first in (known_scale, self._shared_scale):
            if first and first not in tried and score < min_score:
                tried.append(first)
                score, s, centre = match([first])
        if score < min_score and not tried:
            c = self.template_scale
            guesses = [round(c * f, 3) for f in (1.0, 0.98, 1.02, 0.96, 1.04, 0.92, 1.08)]
            score, s, centre = match(guesses)
        if score < min_score and sweep:                # missed: try every scale
            half = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            _, coarse, _ = match(SWEEP_SCALES, half, shrink=2)
            if coarse is not None:
                score, s, centre = match([round(coarse * f, 3) for f in (0.97, 0.985, 1.0, 1.015, 1.03)])
        if DEBUG:
            print(f"  {name} match {score:.2f} (scale {s})")
        if score < min_score:
            return None
        self._tpl[name] = (self._tpl[name][0], s)
        self._shared_scale = s
        return centre[0] + self.monitor["left"], centre[1] + self.monitor["top"]

    def find_end_button(self):
        return self._find_template("end", sweep=True)

    def find_yes_button(self):
        """The 'Yes' of the discard / end-game confirmation dialogs.
        With no dialog open, random screen areas score ~0.56-0.59. The 'No' button scores
        ~0.68, but it is always shown next to 'Yes', which scores higher, so the best match
        is Yes. 0.75 leaves room for the small score loss of a rescaled template."""
        return self._find_template("yes", min_score=0.75)

    def find_deck(self):
        return self._find_template("deck", sweep=True)

    def count_cards(self):
        """How many face-up cards are in the row (no OCR - fast)."""
        return len(self.find_cards(self.grab()))

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
            # verbose=False: easyocr's download progress bar crashes cp1252 consoles
            self._ocr, self._ocr_kind = easyocr.Reader(['en'], gpu=False, verbose=False), "easyocr"
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
            if len(found) < expected and self.card_h:
                # the game's UI size may have changed: look for cards of any size, but only
                # trust a new size from a row of at least 3 cards
                again = self.find_cards(frame, any_size=True)
                if len(again) >= max(expected, 3):
                    found, self.card_h = again, None
        if len(found) < expected or not found:
            self.row_box = None
            if DEBUG:
                print(f"  found {len(found)}/{expected} cards")
            return []
        if self.card_h is None and len(found) >= 3:
            self.card_h = float(np.median([b[3] for b in found]))
            if DEBUG:
                print(f"  card height {self.card_h:.0f}px -> UI scale {self.scale:.2f}")
        xs = [b[0] for b in found]; ys = [b[1] for b in found]
        x0, y0 = min(xs) + ox, min(ys) + oy
        x1 = max(b[0] + b[2] for b in found) + ox; y1 = max(b[1] + b[3] for b in found) + oy
        pad = int(0.4 * max(b[3] for b in found))
        bx, by = max(0, x0 - pad), max(0, y0 - pad)
        self.row_box = (bx, by, min(x1 + pad, self.monitor["width"]) - bx,
                        min(y1 + pad, self.monitor["height"]) - by)

        cards = []
        for i, (x, y, w, h, colour) in enumerate(found):
            # bring every card to the size the digit reader was tuned on
            face = frame[y:y + h, x:x + w]
            face = cv2.resize(face, (REF_CARD_W, REF_CARD_H),
                              interpolation=cv2.INTER_AREA if h > REF_CARD_H else cv2.INTER_CUBIC)
            # the game draws a card identically every time -> OCR each distinct face once
            key = face.tobytes()
            number = self._digit_cache.get(key)
            if number is None:
                glyph = self._glyph(face)
                number = self._read_digit(glyph) if glyph is not None else None
                if number is not None:
                    self._digit_cache[key] = number
            cards.append({"color": colour, "number": number, "index": i,
                          "position": (int(x + ox + self.monitor["left"]), int(y + oy + self.monitor["top"]), int(w), int(h))})
            if SAVE_SCREENSHOTS:
                cv2.imwrite(f"{SCREENSHOT_DIR}/card{i}_{colour}_{number}.png", frame[y:y + h, x:x + w])
        if DEBUG:
            print("  read:", [(c["color"], c["number"]) for c in cards])
        return cards
