import numpy as np
import cv2
from PIL import Image
import pytesseract
import os

from core.constants import ALLY_HEALTH_INNER_COLOR, AUGMENT_BORDER_COLOR, AUGMENT_INNER_COLOR, ENEMY_HEALTH_INNER_COLOR, HEALTH_BORDER_COLOR, PSM, THRESHHOLD, TESSERACT_PATH

# Configure tesseract path
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except Exception:
    raise ImportError("Tesseract path not configured properly")


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


def _find_adjacent_colors_columns(img, left_bgr, right_bgr, left_tolerance=0, right_tolerance=0, run_length=1):
    """
    Find all champion locations by detecting connected groups of hits where the
    health-inner color and health-border color align (border shifted right).

    Args:
        img (np.ndarray): BGR image to search.
        health_bar_bgr (tuple): BGR color of the health inner bar.

    Returns:
        list[tuple]: list of (x, y) locations (may be empty).
    """

    # Build masks for both colors
    mask_left_bgr = get_color_mask(img, left_bgr, tolerance=left_tolerance)
    mask_right_bgr = get_color_mask(img, right_bgr, tolerance=right_tolerance)
    
    # Vectorized check: shift the left mask right 1 pixel, and get their overlap locations
    border_shifted = np.zeros_like(mask_left_bgr)
    border_shifted[:, 1:] = mask_left_bgr[:, :-1]
    hits = cv2.bitwise_and(mask_right_bgr, border_shifted)

    # Use cumulative-sum to detect vertical runs
    if hits is None or hits.size == 0:
        return []
    bin_mask = (hits > 0).astype(np.int32)
    H, W = bin_mask.shape
    if run_length > H:
        return []

    csum = np.vstack([np.zeros((1, W), dtype=np.int32), bin_mask.cumsum(axis=0, dtype=np.int32)])
    runs = csum[run_length:] - csum[:-run_length]

    ys, xs = np.where(runs == run_length)
    if ys.size == 0:
        return []

    locations = []
    for y, x in zip(ys, xs):
        locations.append((int(x), int(y)))

    return locations


def find_ally_locations(img):
    """
    Finds the location of an ally champion by using ally health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors_columns(img, HEALTH_BORDER_COLOR, ALLY_HEALTH_INNER_COLOR, left_tolerance=0, right_tolerance=0, run_length=4)
    if not locations:
        return []
    return [(x + 50, y + 160) for (x, y) in locations]

def find_enemy_locations(img):
    """
    Finds the location of an enemy champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors_columns(img, HEALTH_BORDER_COLOR, ENEMY_HEALTH_INNER_COLOR, left_tolerance=0, right_tolerance=0, run_length=4)
    if not locations:
        return []
    return [(x + 50, y + 160) for (x, y) in locations]


def find_augment_location(img):
    """
    Finds the location of the augment by using hide augment button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors_columns(img, AUGMENT_BORDER_COLOR, AUGMENT_INNER_COLOR, left_tolerance=0, right_tolerance=0, run_length=1)
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1] - 400)
    
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

    Returns:
        results ({}): a dict mapping line numbers to lists of {'text','box'}.
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


def find_text_location(img, target_text, case_sensitive=False):
    """
    Find the bounding box of exact matching text in the provided image.
    Args:
        img (np.ndarray): BGR image to search.
        target_text (str): text to find.
        case_sensitive (bool): whether the match is case-sensitive.
    Returns:
        int (x, y, w, h): bounding box of found text
    """
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
    return []
