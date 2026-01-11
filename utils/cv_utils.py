import numpy as np
import cv2
import os
from core.constants import ALLY_HEALTH_RIGHT_COLOR, ARENA_EXIT_LOWER_COLOR, ARENA_EXIT_UPPER_COLOR, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_RIGHT_COLOR, AUGMENT_LOWER_COLOR, AUGMENT_UPPER_COLOR, ENEMY_HEALTH_RIGHT_COLOR, HEALTH_LEFT_COLOR, PLAYER_HEALTH_RIGHT_COLOR, SHOP_LOWER_COLOR, SHOP_UPPER_COLOR, THRESHHOLD


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


def _find_adjacent_colors(
    img,
    bgr_1,
    bgr_2,
    bgr_1_tolerance=0,
    bgr_2_tolerance=0,
    run_length=1,
    shift_axis='x'
):
    """
    Find all adjacent color pairs
    Args:
        img (np.ndarray): BGR image to search.
        bgr_1: BGR color on the adjacent left or top side, depending on shift_axis.
        bgr_2: BGR color on the adjacent right or bottom side, depending on shift_axis.
        bgr_1_tolerance: tolerance for bgr_1,
        bgr_2_tolerance: tolerance for bgr_2,
        run_length: minimum number of adjacent pixels along opposite axis of shift_axis to validate a pair.
        shift_axis: 'x' to search horizontally (adjacent columns), 'y' to search vertically (adjacent rows).
    Returns:
        list[tuple]: list of (x, y) locations (may be empty).
    """

    # Build masks for both colors
    mask_bgr_1 = get_color_mask(img, bgr_1, tolerance=bgr_1_tolerance)
    mask_bgr_2 = get_color_mask(img, bgr_2, tolerance=bgr_2_tolerance)

    if mask_bgr_1 is None or mask_bgr_2 is None:
        raise ValueError("Two colors are required")

    H, W = mask_bgr_1.shape

    found_locations = []

    shift = 1
    border_shifted = np.zeros_like(mask_bgr_1)

    if shift_axis == 'x':
        # shift columns: move bgr_1 mask right by 1 pixel
        if shift < W:
            border_shifted[:, shift:] = mask_bgr_1[:, :-shift]
    elif shift_axis == 'y':
        # shift rows: move bgr_1 mask down by 1 pixel
        if shift < H:
            border_shifted[shift:, :] = mask_bgr_1[:-shift, :]
    else:
        raise ValueError(f"Invalid shift_axis: {shift_axis}")

    hits = cv2.bitwise_and(mask_bgr_2, border_shifted)
    bin_mask = (hits > 0).astype(np.int32)

    # For vertical adjacency (shift_axis == 'y') transpose so run detection logic stays the same
    proc = bin_mask if shift_axis == "x" else bin_mask.T
    Hp, Wp = proc.shape
    if run_length > Hp:
        return []

    csum = np.vstack([np.zeros((1, Wp), dtype=np.int32), proc.cumsum(axis=0, dtype=np.int32)])
    runs = csum[run_length:] - csum[:-run_length]

    ys, xs = np.where(runs == run_length)
    for y, x in zip(ys, xs):
        if shift_axis == 'x':
            found_locations.append((int(x), int(y)))
        elif shift_axis == 'y':
            # proc is transposed: original x = y, original y = x
            found_locations.append((int(y), int(x)))

    if not found_locations:
        return []

    # De-duplicate while preserving order
    uniq = list(dict.fromkeys(found_locations))
    return uniq


def find_ally_locations(img):
    """
    Finds the location of an ally champion by using ally health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, ALLY_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
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
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, ENEMY_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    return [(x + 50, y + 160) for (x, y) in locations]


def find_player_location(img):
    """
    Finds the location of the player champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, HEALTH_LEFT_COLOR, PLAYER_HEALTH_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0] + 50, first_location[1] + 160)


def find_attached_ally_location(img):
    """
    Finds the location of an enemy champion by using enemy health bar and border colors.
    Args:
        img (np.ndarray): BGR image to search.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, ATTACHED_ALLY_LEFT_COLOR, ATTACHED_ALLY_RIGHT_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=4, shift_axis='x')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0] + 50, first_location[1] + 160)


def find_augment_location(img):
    """
    Finds the location of the augment by using hide augment button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, AUGMENT_UPPER_COLOR, AUGMENT_LOWER_COLOR, bgr_1_tolerance=3, bgr_2_tolerance=3, run_length=1, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1] - 400)


def find_shop_location(img):
    """
    Finds the location of the shop by using hide shop button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, SHOP_UPPER_COLOR, SHOP_LOWER_COLOR, bgr_1_tolerance=2, bgr_2_tolerance=5, run_length=1, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1])


def find_arena_exit_location(img):
    """
    Finds the location of the shop by using hide shop button's inner and border colors.
    Returns:
        list of (x,y) coordinates
    """
    locations = _find_adjacent_colors(img, ARENA_EXIT_UPPER_COLOR, ARENA_EXIT_LOWER_COLOR, bgr_1_tolerance=1, bgr_2_tolerance=0, run_length=1, shift_axis='y')
    if not locations:
        return []
    first_location = locations[0]
    return (first_location[0], first_location[1])