import threading
import time
import logging
import numpy as np
import cv2
import dxcam
from PIL import Image
import pytesseract
import os

from core.constants import ALLY_HEALTH_INNER_COLOR, ENEMY_HEALTH_INNER_COLOR, HEALTH_BORDER_COLOR, PSM, THRESHHOLD, TESSERACT_PATH

# Configure tesseract path
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except Exception:
    raise ImportError("Tesseract path not configured properly")

# ===========================
# Screen Capture Utilities
# ===========================


class ScreenManager:
    """
    DXGI-based screen capture manager using `dxcam`.
    """

    def __init__(self, shutdown_event):
        self._dxcam = None
        self._bg_thread = None
        self.shutdown_event = shutdown_event
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        try:
            
            self._dxcam = dxcam.create(output_color="BGR")
        except Exception:
            raise RuntimeError("dxcam backend not available — install dxcam for DXGI capture")


    def start_capture_thread(self, fps=30):
        if self._bg_thread and self._bg_thread.is_alive():
            return True

        def _loop():
            period = 1.0 / max(1, int(fps))
            while not self.shutdown_event.is_set():
                try:
                    f = self._dxcam.grab()
                    with self._frame_lock:
                        self._latest_frame = f
                except Exception:
                    logging.exception("dxcam capture error")
                time.sleep(period)

        self._bg_thread = threading.Thread(target=_loop, daemon=True)
        self._bg_thread.start()
        return True


    def stop_capture_thread(self, timeout=60):
        if self._bg_thread and self._bg_thread.is_alive():
            try:
                self._bg_thread.join(timeout=timeout)
            finally:
                    if self._bg_thread.is_alive():
                        logging.error("Capture thread failed to exit within the given timeout.")
                        raise RuntimeError("Capture thread failed to exit within the given timeout.")
                    else:
                        self._bg_thread = None
        else:
            logging.error("Capture thread is not running, failed to close")

    # Latest-frame access (non-blocking, requires thread to be active)
    def get_latest_frame(self):
        return self._latest_frame
    
    # Single-frame capture (blocking)
    def get_single_frame(self):
        return self._dxcam.grab()


# ===========================
# Screen Search Utilities
# ===========================


def get_color_mask(img, color_bgr, tolerance=0):
    """Return a binary mask where pixels within `tolerance` of `color_bgr` are 255.

    Args:
        img (np.ndarray): BGR image.
        color_bgr (tuple/list/np.ndarray): BGR color to match.
        tolerance (int or tuple): scalar or per-channel tolerance.

    Returns:
        np.ndarray: single-channel mask (dtype=uint8) with binary values.
    """

    col = np.array(color_bgr, dtype=np.int16)
    lower = np.clip(col - np.array(tolerance, dtype=np.int16), 0, 255).astype(np.uint8)
    upper = np.clip(col + np.array(tolerance, dtype=np.int16), 0, 255).astype(np.uint8)
    return cv2.inRange(img, lower, upper)


def save_color_mask(img, color_bgr, tolerance=0):
    """Compute a color mask and save it to disk.

    Args:
        img (np.ndarray): BGR image.
        color_bgr (tuple): BGR color to match.
        tolerance (int): scalar tolerance per channel.

    Returns:
        str: full path to written mask image.
    """
    if img is None:
        raise ValueError("img is required for save_color_mask")
    out_dir = os.path.join("temp")
    filename = "color_mask.png"
    mask = get_color_mask(img, color_bgr, tolerance=tolerance)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    # write mask (single-channel) as PNG
    cv2.imwrite(out_path, mask)
    return out_path


def find_champion_location(img, health_bar_bgr):
    """
    Finds the champion location by searching for health bar and border colors in the screenshot.
    
    Returns:
        tuple or None: (x, y) location if found, else None.
    """

    # Adjust as necessary if color matching is too strict/loose
    tolerance = 2

    # Build health bar and border masks using helper
    mask_health_bar = get_color_mask(img, health_bar_bgr, tolerance=tolerance)
    mask_health_border = get_color_mask(img, HEALTH_BORDER_COLOR, tolerance=tolerance)

    # Vectorized check: shift the border mask right 1 pixel
    border_shifted = np.zeros_like(mask_health_border)
    border_shifted[:, 1:] = mask_health_border[:, :-1]
    hits = cv2.bitwise_and(mask_health_bar, border_shifted)
    ys, xs = np.nonzero(hits)
    if ys.size > 0:
        y0, x0 = int(ys[0]), int(xs[0])
        champion_location = (x0 + 50, y0 + 160)
        return champion_location

    return None


def save_champion_location(img, health_bar_bgr, tolerance=2):
    """Compute champion hits and save an overlay image showing all hit locations.

    Args:
        img (np.ndarray): BGR image to search.
        health_bar_bgr (tuple): BGR color of the health inner bar.
        tolerance (int): color tolerance per channel.

    Returns:
        str: path to the saved image.
    """
    if img is None:
        raise ValueError("img is required for save_champion_location")

    out_dir = os.path.join("temp")
    filename = "champions_found.png"
    mask_health_bar = get_color_mask(img, health_bar_bgr, tolerance=tolerance)
    mask_health_border = get_color_mask(img, HEALTH_BORDER_COLOR, tolerance=tolerance)
    border_shifted = np.zeros_like(mask_health_border)
    border_shifted[:, 1:] = mask_health_border[:, :-1]
    hits = cv2.bitwise_and(mask_health_bar, border_shifted)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    cv2.imwrite(out_path, hits)
    return out_path


def find_ally_location(img):
    """
    Finds the location of an ally champion by searching for ally health bar and border colors.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    return find_champion_location(img, ALLY_HEALTH_INNER_COLOR)


def find_enemy_location(img):
    """
    Finds the location of an enemy champion by searching for enemy health bar and border colors.
    Returns:
        tuple or None: (x, y) location if found, else None.
    """
    return find_champion_location(img, ENEMY_HEALTH_INNER_COLOR)


# ===========================
# OCR Utilities
# ===========================


def extract_image_text(img):
    """Extract text from an image using Tesseract.

    Args:
        img (np.ndarray): BGR image to run OCR on (required).
        thresh (int): binary threshold value.
        psm (int): tesseract page segmentation mode.

    Returns:
        str: extracted text.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, proc = cv2.threshold(gray, int(THRESHHOLD), 255, cv2.THRESH_BINARY)
    pil_img = Image.fromarray(proc)
    return pytesseract.image_to_string(pil_img, config=f"--psm {PSM}")


def extract_image_text_with_locations(img):
    """Extract text and bounding boxes from an image.

    Returns a dict mapping line numbers to lists of {'text','box'}.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, proc = cv2.threshold(gray, int(THRESHHOLD), 255, cv2.THRESH_BINARY)
    pil_img = Image.fromarray(proc)
    data = pytesseract.image_to_data(pil_img, config=f"--psm {PSM}", output_type=pytesseract.Output.DICT)
    results = {}
    n = len(data.get("text", []))
    for i in range(n):
        txt = data["text"][i].strip()
        if not txt:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        line = data.get("line_num", [0])[i] or 0
        results.setdefault(line, []).append({"text": txt, "box": (x, y, w, h)})
    return results


def find_text_location(target_text, img, case_sensitive=False):
    """Find the bounding box of exact matching text in the provided image."""
    lines = extract_image_text_with_locations(img=img)
    for entries in lines.values():
        for e in entries:
            a = e["text"]
            if case_sensitive:
                if a == target_text:
                    return e["box"]
            else:
                if a.lower() == target_text.lower():
                    return e["box"]
    return None


def find_text_location_retry(target_text, img, attempts=5, delay=0.2):
    """Retry finding text in `img` for a number of attempts (useful for dynamic UIs)."""
    for _ in range(attempts):
        loc = find_text_location(target_text, img=img)
        if loc:
            return loc
        time.sleep(delay)
    return None


