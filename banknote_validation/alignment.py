"""
Banknote Alignment Module
==========================

Classical OpenCV routine (NO machine learning) to find the banknote's
outer edges under UV light and straighten it into a fixed-size,
axis-aligned rectangle before the rest of the pipeline runs.

Why this exists
----------------
The security-mark ROIs (BOTTOM_LEFT_ROI / TOP_LEFT_ROI in
banknote_detector.py) are fixed pixel boxes. That only works reliably if
the banknote appears in EXACTLY the same position/rotation in every
photo. In practice the note is rarely placed perfectly straight, so this
module:

    1. Thresholds the UV image at a LOW threshold to find the whole
       banknote's glowing silhouette (banknote paper itself glows
       faintly under UV due to optical brighteners - this is a
       different, much lower threshold than the one used later to
       isolate just the bright security number).
    2. Finds the largest contour (assumed to be the banknote) and
       reduces it to 4 corner points.
    3. Applies a 4-point perspective transform to warp the banknote into
       a fixed-size rectangle, regardless of how it was rotated/tilted
       in the original photo.

After alignment, BOTTOM_LEFT_ROI / TOP_LEFT_ROI can be calibrated ONCE
against the canonical ALIGNED_WIDTH x ALIGNED_HEIGHT image and should
then stay valid across differently-rotated captures.

Limitations (by design, kept simple on purpose):
    - This corrects in-plane rotation/skew/perspective. It does NOT
      detect a banknote inserted upside-down or flipped 180 degrees -
      that still needs a physical guide/slot in the chamber so the note
      always goes in the same way up.
    - Requires the banknote to be reasonably brighter than the chamber
      background under UV. If NOTE_DETECTION_THRESHOLD is not tuned for
      your lighting, contour detection may fail - in that case this
      module falls back to using the original, unwarped image so the
      rest of the pipeline still runs.
"""

import cv2
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================

# Threshold used ONLY to separate the whole banknote silhouette from the
# dark chamber background. Banknote paper usually glows faintly under UV
# (optical brighteners), even outside of the specific security ink -
# this is normally MUCH LOWER than THRESHOLD_VALUE in
# banknote_detector.py, which isolates just the bright security number.
NOTE_DETECTION_THRESHOLD = 60

# Minimum contour area (in pixels) to be considered a valid banknote
# outline. Filters out small noise blobs. Tune based on your camera
# resolution / distance from the note.
MIN_NOTE_AREA = 5000

# Canonical size (in pixels) the banknote is warped/resized to after
# alignment. Keep the aspect ratio close to your real banknotes
# (Israeli new shekel notes are roughly 76mm x 150mm -> ~1:1.97).
# BOTTOM_LEFT_ROI / TOP_LEFT_ROI in banknote_detector.py should be
# calibrated against THIS size, not the raw camera resolution.
ALIGNED_WIDTH = 1200
ALIGNED_HEIGHT = 600

# Kernel size used to close small gaps in the note silhouette so it
# forms one solid blob before contour detection.
CLOSE_KERNEL_SIZE = (15, 15)


# =============================================================================
# FUNCTIONS
# =============================================================================

def find_banknote_contour(gray_image, threshold_value=NOTE_DETECTION_THRESHOLD,
                           min_area=MIN_NOTE_AREA):
    """
    Threshold the grayscale UV image at a LOW threshold to find the whole
    banknote silhouette, then return the largest valid contour (assumed
    to be the banknote).

    Returns (contour_or_None, note_mask_image).
    """
    _, note_mask = cv2.threshold(
        gray_image, threshold_value, 255, cv2.THRESH_BINARY
    )

    # Close small gaps so the banknote silhouette forms one solid blob.
    kernel = np.ones(CLOSE_KERNEL_SIZE, np.uint8)
    note_mask = cv2.morphologyEx(note_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(
        note_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None, note_mask

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < min_area:
        return None, note_mask

    return largest, note_mask


def get_four_corners(contour):
    """
    Reduce a contour to exactly 4 corner points.

    Tries polygon approximation first (works well on clean, straight
    edges). Falls back to the rotated minimum-area bounding box if
    approximation does not produce exactly 4 points (handles rounded
    corners / slightly noisy edges).
    """
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

    if len(approx) == 4:
        return approx.reshape(4, 2).astype("float32")

    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    return box.astype("float32")


def order_points(pts):
    """
    Order 4 points consistently as: top-left, top-right, bottom-right,
    bottom-left - regardless of how the banknote was rotated in frame.
    """
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left     -> smallest x+y
    rect[2] = pts[np.argmax(s)]  # bottom-right -> largest x+y

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right    -> smallest x-y
    rect[3] = pts[np.argmax(diff)]  # bottom-left  -> largest x-y

    return rect


def warp_banknote(image, corners, width=ALIGNED_WIDTH, height=ALIGNED_HEIGHT):
    """
    Apply a 4-point perspective transform to straighten the banknote into
    a fixed-size, axis-aligned rectangle.
    """
    ordered = order_points(corners)

    destination = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1],
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(ordered, destination)
    warped = cv2.warpPerspective(image, matrix, (width, height))
    return warped


def align_banknote(image, gray_image=None):
    """
    Full alignment routine:
      1. Find the banknote's outer contour under UV light.
      2. Reduce it to 4 corner points.
      3. Perspective-warp the ORIGINAL COLOR image into a fixed-size,
         straightened rectangle.

    Returns (aligned_image, note_mask, found):
      - aligned_image: the warped, straightened image, OR a resized copy
        of the original image if no contour was found (safe fallback so
        the rest of the pipeline can still run).
      - note_mask: the thresholded mask used for contour detection
        (useful for debugging).
      - found: True if a banknote contour was successfully detected.
    """
    if gray_image is None:
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    contour, note_mask = find_banknote_contour(gray_image)

    if contour is None:
        # Fallback: could not find the note outline. Resize the original
        # image to the canonical size so downstream ROI coordinates are
        # still meaningful, and let the caller know detection failed.
        fallback = cv2.resize(image, (ALIGNED_WIDTH, ALIGNED_HEIGHT))
        return fallback, note_mask, False

    corners = get_four_corners(contour)
    aligned = warp_banknote(image, corners)

    return aligned, note_mask, True