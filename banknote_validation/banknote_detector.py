"""
UV Banknote Counterfeit Detection Prototype
=============================================

Simple, classical computer-vision pipeline (NO machine learning) for a
smart-shopping-cart prototype. It works entirely with:

    - OpenCV image processing (grayscale, thresholding, morphology, contours)
    - Tesseract OCR (via pytesseract) to read a security number printed on
      the banknote that only becomes visible / bright under UV light.

Pipeline
--------
1. Capture UV image (camera or file).
2. Detect the banknote's outer edges and straighten it (perspective
   warp) into a fixed-size canonical image - see alignment.py. This
   makes the fixed ROI boxes below reliable even if the note was
   rotated/tilted when photographed.
3. Convert the aligned image to grayscale.
4. Threshold -> keep only bright/glowing UV regions on a black background.
5. Light morphology to remove noise specks.
6. Find contours of the remaining bright regions.
7. Crop two fixed candidate ROIs (bottom-left, top-left) from the
   ALIGNED image.
8. Run Tesseract OCR on both ROIs, in ALL orientations the note could
   plausibly have ended up in (normal, rotated 180, and mirrored),
   since alignment corrects skew/rotation but not a note inserted
   upside-down or flipped left-right.
9. Clean/normalize the OCR text (digits only, Arabic-Indic -> ASCII digits).
10. Match the cleaned text against known denominations (20/50/100/200).
11. Decide AUTHENTIC vs FAKE based on whether an expected denomination
    number was found glowing in one of the ROI/orientation combinations.
12. Save every intermediate image + a result.txt into a new timestamped
    folder under output/ so every attempt can be inspected later.

Everything you are likely to need to tune lives in the CONFIG section
at the top of the file. Alignment-specific config (NOTE_DETECTION_THRESHOLD,
ALIGNED_WIDTH/HEIGHT) lives in alignment.py.
"""

import os
import cv2
import numpy as np
import pytesseract
from datetime import datetime

from alignment import align_banknote, ALIGNED_WIDTH, ALIGNED_HEIGHT

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES TO MATCH YOUR CHAMBER / CAMERA / LIGHTING
# =============================================================================

# Path to the tesseract binary. On macOS with Homebrew this is typically:
#   /opt/homebrew/bin/tesseract   (Apple Silicon)
#   /usr/local/bin/tesseract      (Intel Mac)
TESSERACT_PATH = "/usr/local/bin/tesseract"

# Camera index used by cv2.VideoCapture when no image file is supplied.
CAMERA_INDEX = 0

# --- Thresholding ------------------------------------------------------
# Grayscale threshold used to isolate the bright/glowing UV regions.
# Pixels >= THRESHOLD_VALUE become white (255), everything else becomes
# black (0). Increase this value if too much background noise glows;
# decrease it if the security number is too dim to survive thresholding.
THRESHOLD_VALUE = 180

# --- Morphology ----------------------------------------------------------
# Kernel size used to clean small noise specks after thresholding.
# Set to (1, 1) to effectively disable morphology.
MORPH_KERNEL_SIZE = (3, 3)
MORPH_ITERATIONS = 1

# --- Contour filtering -----------------------------------------------------
# Ignore contours smaller than this area (removes single-pixel noise).
MIN_CONTOUR_AREA = 15

# --- Regions of Interest -------------------------------------------------
# ROIs are defined as (x, y, w, h) in pixels, measured against the
# ALIGNED/STRAIGHTENED image produced by alignment.py - i.e. a canonical
# ALIGNED_WIDTH x ALIGNED_HEIGHT image (see alignment.py), NOT the raw
# camera frame.
#
# CALIBRATED from a real UV sample: the security number was found at
# roughly x:872-1008, y:144-248 in the 1200x600 aligned image (i.e. the
# upper-right area of the note). TOP_LEFT_ROI below covers that spot with
# padding.
#
# Because align_banknote() corrects rotation/skew but NOT a 180-degree
# flip (note inserted upside-down), BOTTOM_LEFT_ROI is set to the
# mirrored position (opposite corner) as a second candidate, so the
# number is still found if the note happens to come out flipped.
#
# On top of that positional fallback, EACH of these two ROI crops is now
# also OCR'd in every orientation listed in OCR_ORIENTATIONS below
# (normal, rotated 180, and left-right mirrored), since we can't know
# ahead of time how a given capture ended up oriented - the note can go
# into the chamber upside-down (rotate 180) AND/OR flipped face-for-face
# (mirror), and these are two DIFFERENT physical situations that need
# two different image transforms to undo.
#
# NOTE: cropping happens on the ALIGNED grayscale image, not the
# thresholded one - thresholding is only used to check whether something
# is glowing at all / to find contours for the debug overlay.
TOP_LEFT_ROI = (840, 100, 180, 170)     # (x, y, w, h) - normal orientation
BOTTOM_LEFT_ROI = (180, 330, 180, 170)  # (x, y, w, h) - 180-flipped orientation

# --- Per-denomination ROIs --------------------------------------------------
# IMPORTANT: real banknotes of different denominations are physically
# different SIZES (a 20 NIS note is not the same size as a 50/100/200 NIS
# note). alignment.py always warps whatever note it sees into the same
# canonical ALIGNED_WIDTH x ALIGNED_HEIGHT rectangle, which means the
# security number does NOT land in the same pixel location for every
# denomination - each one needs its own calibrated ROI pair.
#
# TOP_LEFT_ROI / BOTTOM_LEFT_ROI above are kept as the generic FALLBACK used
# when a denomination has no calibrated entry below (or when the
# denomination isn't known yet, e.g. testing without the classifier).
#
# DENOMINATION_ROIS maps: denomination (int) -> {"top_left": (x,y,w,h),
#                                                  "bottom_left": (x,y,w,h)}
#
# HOW TO CALIBRATE A NEW DENOMINATION:
#   1. Run the pipeline once on a real UV sample of that denomination
#      (denomination=None is fine for this calibration run).
#   2. Open 07_detected_regions.jpg in the output/<timestamp>/ folder - the
#      yellow boxes show every bright UV blob that was found.
#   3. Identify which cluster of boxes is the actual glowing security
#      number (as opposed to the serial number text or the security
#      thread strip), note its combined (x, y, w, h) with ~20px padding,
#      and use that as "top_left" for this denomination.
#   4. Mirror it for "bottom_left" (covers the case where the note went
#      into the chamber physically upside-down):
#         x' = ALIGNED_WIDTH  - x - w
#         y' = ALIGNED_HEIGHT - y - h
#
# 20 NIS: calibrated from a real UV sample - the glowing "20" security
# digits were found clustered around x:774-881, y:163-242 in the aligned
# 1200x600 image; padded by ~20px on each side below.
DENOMINATION_ROIS: dict[int, dict[str, tuple[int, int, int, int]]] = {
    20: {
        "top_left": (754, 143, 147, 119),
        "bottom_left": (299, 338, 147, 119),
    },
    # TODO: not yet calibrated - currently just reuses the generic
    # fallback ROI (TOP_LEFT_ROI / BOTTOM_LEFT_ROI), which is unlikely to
    # be accurate for the real 50 NIS note size. Send a UV capture of a 50
    # NIS note through the pipeline and follow the steps above to replace
    # these with real numbers.
    50: {
        "top_left": TOP_LEFT_ROI,
        "bottom_left": BOTTOM_LEFT_ROI,
    },
}


def get_rois_for_denomination(denomination):
    """
    Look up the calibrated (top_left, bottom_left) ROI pair for a given
    denomination (int, or a numeric string like "20").

    Falls back to the generic TOP_LEFT_ROI / BOTTOM_LEFT_ROI (with a
    printed warning) if the denomination is None or has no calibrated
    entry in DENOMINATION_ROIS yet.
    """
    default_rois = {"top_left": TOP_LEFT_ROI, "bottom_left": BOTTOM_LEFT_ROI}

    if denomination is None:
        return default_rois

    try:
        key = int(denomination)
    except (TypeError, ValueError):
        print(f"[WARN] Could not parse denomination '{denomination}' - using default ROI.")
        return default_rois

    rois = DENOMINATION_ROIS.get(key)
    if rois is None:
        print(
            f"[WARN] No calibrated ROI for {key} NIS yet - using the generic "
            f"default ROI (may be inaccurate for this note size). Calibrate "
            f"it in DENOMINATION_ROIS inside banknote_detector.py."
        )
        return default_rois

    return rois


# --- OCR -------------------------------------------------------------------
# Restrict Tesseract to digits only, single line of text.
OCR_CONFIG = "--psm 7 -c tessedit_char_whitelist=0123456789"

# Threshold applied to each ROI crop BEFORE sending it to Tesseract.
#
# Set to an int (0-255) to force one fixed manual threshold for every
# note, or to None (RECOMMENDED, default) to let each ROI pick its own
# threshold automatically via Otsu's method, based on that specific
# crop's own brightness histogram.
#
# WHY: a fixed number tends to work great for whichever single sample it
# was tuned on and silently fail (empty OCR reading -> falsely REJECTED)
# on anything with different UV brightness - which is exactly what
# happened here: 165 was tuned against a 20 NIS sample and correctly read
# "20", but the same fixed 165 produced no OCR reading at all on a 50 NIS
# sample whose UV capture was noticeably brighter/more overexposed
# overall. Otsu recalculates the right cutoff for EACH crop individually,
# so it adapts across denominations, cameras, and lighting automatically.
OCR_THRESHOLD_VALUE = None

# Orientations to try OCR in, for each ROI crop. We don't know ahead of
# time how a given capture ended up oriented, because there are actually
# TWO independent physical ways a note can be seated "wrong" in the
# chamber, and they are NOT the same transform:
#
#   - upside-down insertion  -> equivalent to rotating the image 180
#     degrees (flips both the horizontal AND vertical axis together).
#   - face-for-face / left-right flipped insertion -> equivalent to a
#     pure horizontal MIRROR (flips left-right only, top/bottom stays
#     put). This is what a "20" note that reads as a backwards/mirrored
#     "20" looks like - cv2.ROTATE_180 alone does NOT undo this, only a
#     horizontal flip does.
#
# A note could in principle also end up upside-down AND mirrored at the
# same time (mirror + rotate180 combined), so that combination is
# included too for completeness.
#
# Each entry maps: orientation label -> a function that transforms a
# grayscale ROI image into that orientation ("identity" for no change).
#   key   -> label stored in result info / filenames
#   value -> callable: roi_image -> transformed_roi_image
OCR_ORIENTATIONS = {
    "normal": lambda img: img,
    "flipped180": lambda img: cv2.rotate(img, cv2.ROTATE_180),
    "mirrored": lambda img: cv2.flip(img, 1),
    "mirrored_flipped180": lambda img: cv2.rotate(cv2.flip(img, 1), cv2.ROTATE_180),
}

# --- Denominations ---------------------------------------------------------
# Extensible list of denominations the system knows how to recognize.
# Add/remove values here to support new banknotes.
KNOWN_DENOMINATIONS = [20, 50, 100, 200]

# Whether the OCR'd digits must exactly match one of KNOWN_DENOMINATIONS
# to count as a detected UV security number.
#   True  -> strict: the reading must equal 20, 50, 100, or 200 exactly.
#            A misread digit (e.g. OCR returning "30" for a genuine "50")
#            fails detection even though a number IS glowing.
#   False -> lenient: presence matters more than exact value. ANY
#            non-empty digit reading in a ROI (in either orientation)
#            counts as "a UV security number was detected" - the
#            specific value is not required to match the list. This is
#            more forgiving of OCR misreads (see the "30" vs "50" case)
#            since what actually matters for authenticity is whether
#            the security ink glows and prints readable digits at all,
#            not that OCR nails the exact denomination.
# The recognized value (if any) is still reported for reference either
# way - this flag only changes what counts as a pass/fail.
REQUIRE_KNOWN_DENOMINATION = True

# --- Output ------------------------------------------------------------
OUTPUT_ROOT = "output"

# Arabic-Indic / Persian digit -> ASCII digit translation table.
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
DIGIT_TRANSLATION_TABLE = str.maketrans(
    ARABIC_INDIC_DIGITS + PERSIAN_DIGITS,
    "01234567890123456789"
)

# Point pytesseract at the configured tesseract binary.
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# =============================================================================
# PIPELINE FUNCTIONS
# =============================================================================

def capture_image(image_path=None):
    """
    Capture (or load) the UV image of the banknote.

    If image_path is given, the image is loaded from disk (useful for
    testing with sample photos). Otherwise, a single frame is grabbed
    from the configured camera.
    """
    if image_path:
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not read image at: {image_path}")
        return image

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {CAMERA_INDEX}")

    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        raise RuntimeError("Failed to capture a frame from the camera")

    return frame


def preprocess_image(image):
    """Convert the UV image to grayscale."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray


def apply_uv_threshold(gray_image, threshold_value=THRESHOLD_VALUE):
    """
    Threshold the grayscale image so that only bright UV-glowing regions
    remain white on a black background. Also applies a light morphological
    "open" operation to remove small noise specks.

    Returns (thresholded_image, morphed_image).
    """
    _, thresh = cv2.threshold(
        gray_image, threshold_value, 255, cv2.THRESH_BINARY
    )

    kernel = np.ones(MORPH_KERNEL_SIZE, np.uint8)
    morphed = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, kernel, iterations=MORPH_ITERATIONS
    )

    return thresh, morphed


def find_uv_contours(morphed_image, min_area=MIN_CONTOUR_AREA):
    """Find contours of the remaining bright regions after thresholding."""
    contours, _ = cv2.findContours(
        morphed_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = [c for c in contours if cv2.contourArea(c) >= min_area]
    return contours


def extract_rois(gray_image, rois_cfg=None):
    """
    Crop the two candidate ROIs (bottom-left, top-left) from the grayscale
    image, based on the note's fixed position in the chamber.

    rois_cfg: {"top_left": (x,y,w,h), "bottom_left": (x,y,w,h)} - normally
        obtained via get_rois_for_denomination(denomination) so the crop
        matches the ACTUAL note size being processed. Falls back to the
        generic TOP_LEFT_ROI / BOTTOM_LEFT_ROI if not provided (e.g. when
        calling this function directly without a known denomination).

    Returns a dict: {"bottom_left": roi_image, "top_left": roi_image}
    """
    if rois_cfg is None:
        rois_cfg = {"top_left": TOP_LEFT_ROI, "bottom_left": BOTTOM_LEFT_ROI}

    def crop(roi_box):
        x, y, w, h = roi_box
        h_img, w_img = gray_image.shape[:2]
        # Clamp to image bounds so we never crash on a misconfigured ROI.
        x2 = min(x + w, w_img)
        y2 = min(y + h, h_img)
        x = max(0, x)
        y = max(0, y)
        return gray_image[y:y2, x:x2]

    return {
        "bottom_left": crop(rois_cfg["bottom_left"]),
        "top_left": crop(rois_cfg["top_left"]),
    }


def clean_ocr_text(raw_text):
    """
    Normalize raw OCR text:
      - translate Arabic-Indic / Persian digits to ASCII digits
      - strip whitespace
      - keep numeric characters only
    """
    if not raw_text:
        return ""

    translated = raw_text.translate(DIGIT_TRANSLATION_TABLE)
    digits_only = "".join(ch for ch in translated if ch.isdigit())
    return digits_only


def run_ocr(roi_image):
    """
    Run Tesseract OCR on a single ROI image (as-is, no rotation applied)
    and return the cleaned, digits-only string (may be empty if nothing
    was recognized).
    """
    if roi_image is None or roi_image.size == 0:
        return ""

    # Threshold first so adjacent digits (which can glow into one
    # connected blob at lower thresholds) are cleanly separated before
    # OCR sees them.
    if OCR_THRESHOLD_VALUE is None:
        # Otsu computes the cutoff from THIS crop's own histogram, so it
        # self-adjusts to however bright/dim this particular note/capture
        # happens to be instead of relying on one fixed number tuned for
        # a single sample (see OCR_THRESHOLD_VALUE comment above).
        _, roi_thresh = cv2.threshold(
            roi_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    else:
        _, roi_thresh = cv2.threshold(
            roi_image, OCR_THRESHOLD_VALUE, 255, cv2.THRESH_BINARY
        )

    # Slight upscaling helps Tesseract with small ROIs.
    scaled = cv2.resize(roi_thresh, None, fx=3.0, fy=3.0,
                         interpolation=cv2.INTER_CUBIC)

    raw_text = pytesseract.image_to_string(scaled, config=OCR_CONFIG)
    return clean_ocr_text(raw_text)


def is_roi_likely_uv_glow(roi_image, min_bright_ratio=0.05):
    """
    Check if the ROI image contains enough glowing UV pixels (>= THRESHOLD_VALUE)
    to be considered a genuine glowing UV feature (rather than plain printed text/background).
    """
    if roi_image is None or roi_image.size == 0:
        return False

    bright_pixels = np.count_nonzero(roi_image >= THRESHOLD_VALUE)
    total_pixels = roi_image.size
    ratio = bright_pixels / total_pixels
    return ratio >= min_bright_ratio


def run_ocr_both_orientations(roi_image):
    """
    Run OCR on a ROI crop in every orientation listed in OCR_ORIENTATIONS
    (by default: normal, rotated 180, mirrored, and mirrored+rotated180).

    We can't know in advance how a given capture ended up oriented (the
    chamber doesn't physically force one orientation, and upside-down
    insertion and left-right/face flipping are two DIFFERENT physical
    situations - see the OCR_ORIENTATIONS comment above), so instead of
    guessing we just try every configured orientation and let
    detect_denomination() accept whichever one (if any) produces a
    usable reading.

    Returns a dict: {orientation_name: cleaned_ocr_text, ...}, using the
    same keys as OCR_ORIENTATIONS (e.g. "normal", "flipped180",
    "mirrored", "mirrored_flipped180").
    """
    results = {}

    # Check ROI UV glow density before invoking OCR. If it fails, return empty readings.
    if not is_roi_likely_uv_glow(roi_image):
        for orientation_name in OCR_ORIENTATIONS:
            results[orientation_name] = ""
        return results

    for orientation_name, transform_fn in OCR_ORIENTATIONS.items():
        if roi_image is None or roi_image.size == 0:
            results[orientation_name] = ""
            continue

        oriented_roi = transform_fn(roi_image)
        results[orientation_name] = run_ocr(oriented_roi)

    return results


def detect_denomination(roi_ocr_results):
    """
    Given OCR results for every (roi, orientation) combination, determine
    which UV security number (if any) was recognized, and which ROI +
    orientation it came from.

    roi_ocr_results: dict shaped like
        {
            "bottom_left": {"normal": "...", "flipped180": "...",
                             "mirrored": "...", "mirrored_flipped180": "..."},
            "top_left":    {"normal": "...", "flipped180": "...",
                             "mirrored": "...", "mirrored_flipped180": "..."},
        }

    Checked in a fixed, deterministic order (bottom_left before
    top_left; orientations in the order they appear in
    OCR_ORIENTATIONS) so that if two combinations happen to both
    produce a reading, the result is reproducible.

    Matching behavior depends on REQUIRE_KNOWN_DENOMINATION:
      - True:  only counts as detected if the digits exactly equal one
               of KNOWN_DENOMINATIONS (strict - a misread like "30"
               instead of "50" is treated as nothing detected).
      - False: ANY non-empty digit reading counts as detected, whether
               or not it happens to match KNOWN_DENOMINATIONS - presence
               of a readable glowing number matters, not its exact value.

    Returns (value_or_None, source_roi_name_or_None,
             source_orientation_or_None, matched_text, is_known_denomination)
      - value_or_None: the recognized number as an int (for reference/
        display), or None if nothing was detected.
      - is_known_denomination: True if `value` is one of
        KNOWN_DENOMINATIONS, False otherwise. Still reported even in
        lenient mode, purely for information (e.g. to flag "detected a
        number but it doesn't match any known denomination" cases).
    """
    for roi_name in ("bottom_left", "top_left"):
        for orientation_name in OCR_ORIENTATIONS:
            text = roi_ocr_results.get(roi_name, {}).get(orientation_name, "")
            if not text:
                continue

            # Length filter: only accept strings with 2 or 3 digits
            if len(text) not in (2, 3):
                continue

            is_known = text in (str(d) for d in KNOWN_DENOMINATIONS)

            if REQUIRE_KNOWN_DENOMINATION and not is_known:
                # Strict mode: a reading that doesn't match a known
                # denomination doesn't count - keep looking at the
                # other ROI/orientation combinations.
                continue

            # Either strict mode + it matched, or lenient mode where any
            # non-empty reading is accepted regardless of its value.
            try:
                value = int(text)
            except ValueError:
                value = None
            return value, roi_name, orientation_name, text, is_known

    return None, None, None, "", False


def determine_authenticity(value):
    """
    Apply the core authenticity rule:
      - a UV security number was recognized -> AUTHENTIC
        (in strict mode this means it matched a known denomination; in
        lenient mode any readable glowing number qualifies - see
        REQUIRE_KNOWN_DENOMINATION)
      - nothing recognized -> FAKE
    """
    return "AUTHENTIC" if value is not None else "FAKE"


def draw_result(image, denomination, status, source_roi_name, rois_cfg=None):
    """
    Draw the ROI rectangle (that produced the OCR match, if any), plus a
    plain English status label, on a copy of the original image.

    rois_cfg: the same {"top_left": ..., "bottom_left": ...} dict used by
        extract_rois(), so the rectangle drawn matches whichever ROI pair
        was actually used for THIS note's denomination. Falls back to the
        generic TOP_LEFT_ROI / BOTTOM_LEFT_ROI if not provided.

    NOTE: no numbers/digits are ever written on the image - only a
    security-mark status message ("Security Mark Detected" /
    "No Security Mark Detected"), regardless of which denomination (if
    any) was actually read internally.
    """
    if rois_cfg is None:
        rois_cfg = {"top_left": TOP_LEFT_ROI, "bottom_left": BOTTOM_LEFT_ROI}

    result_image = image.copy()

    roi_box = None
    if source_roi_name == "bottom_left":
        roi_box = rois_cfg["bottom_left"]
    elif source_roi_name == "top_left":
        roi_box = rois_cfg["top_left"]

    color = (0, 200, 0) if status == "AUTHENTIC" else (0, 0, 255)

    if roi_box is not None:
        x, y, w, h = roi_box
        cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 3)

    label = "Security Mark Detected" if status == "AUTHENTIC" else "No Security Mark Detected"
    cv2.putText(
        result_image, label, (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA
    )

    return result_image


def draw_detected_regions(image, contours):
    """Draw rectangles around every detected bright UV contour (debug view)."""
    debug_image = image.copy()
    if len(debug_image.shape) == 2:  # grayscale -> BGR for colored boxes
        debug_image = cv2.cvtColor(debug_image, cv2.COLOR_GRAY2BGR)

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 255), 2)

    return debug_image


def draw_ocr_on_roi(roi_image, ocr_text):
    """
    Return a color copy of an ROI with a plain English detection label
    written on it - NOT the actual OCR digits, so no numbers ever get
    drawn on any saved/displayed image.
    """
    if roi_image is None or roi_image.size == 0:
        canvas = np.zeros((60, 220), dtype=np.uint8)
    else:
        canvas = roi_image

    color_roi = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    label = "Security Mark Detected" if ocr_text else "None"
    cv2.putText(
        color_roi, label, (5, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA
    )
    return color_roi


# =============================================================================
# DEBUG / OUTPUT SAVING
# =============================================================================

def create_output_folder():
    """Create a new timestamped output folder for this processing attempt."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_path = os.path.join(OUTPUT_ROOT, timestamp)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path, timestamp


def save_debug_images(folder_path, images):
    """
    Save every pipeline stage image into folder_path using the required
    numbered filenames.

    images: dict mapping filename -> image array
    """
    for filename, img in images.items():
        cv2.imwrite(os.path.join(folder_path, filename), img)


def save_result_text(folder_path, info):
    """Write result.txt with all processing information."""
    lines = [
        "-" * 32,
        "BANKNOTE PROCESSING RESULT",
        "-" * 32,
        f"Timestamp: {info['timestamp']}",
        f"Threshold: {info['threshold']}",
        f"Classifier denomination (ROI selection): {info['classifier_denomination'] if info['classifier_denomination'] is not None else 'UNKNOWN (used default ROI)'}",
        f"Banknote edges detected: {'YES' if info['note_detected'] else 'NO (fallback used)'}",
        f"Detected regions: {info['num_contours']}",
    ]
    for roi_name in ("bottom_left", "top_left"):
        for orientation_name in OCR_ORIENTATIONS:
            value = info[f"{roi_name}_ocr"].get(orientation_name, "")
            lines.append(
                f"{roi_name.replace('_', '-').title()} OCR ({orientation_name}): {value or 'NONE'}"
            )
    lines += [
        f"Detected denomination: {info['denomination'] if info['denomination'] is not None else 'UNKNOWN'}",
        f"Matches a known denomination (20/50/100/200): {'YES' if info['is_known_denomination'] else 'NO'}",
        f"Matching mode: {'STRICT (must match known denomination)' if info['require_known_denomination'] else 'LENIENT (any readable number counts)'}",
        f"Matched ROI / orientation: {info['source_roi'] or '-'} / {info['source_orientation'] or '-'}",
        f"UV security mark: {'DETECTED' if info['denomination'] is not None else 'NOT DETECTED'}",
        f"Final status: {info['status']}",
        "-" * 32,
    ]
    text = "\n".join(lines)

    with open(os.path.join(folder_path, "result.txt"), "w") as f:
        f.write(text + "\n")

    return text


# =============================================================================
# MAIN ORCHESTRATION
# =============================================================================

def process_banknote(image_path=None, classifier_denomination=None, threshold_value=THRESHOLD_VALUE):
    """
    Run the full pipeline end-to-end on a single banknote image, saving
    every intermediate stage to a new timestamped output folder.

    classifier_denomination: the denomination predicted by the RGB
        classifier (e.g. 20, 50, or "20", "50" as a string) - used ONLY to
        pick the correct security-mark ROI pair for THIS note's physical
        size (see DENOMINATION_ROIS above). Pass None to use the generic
        fallback ROI (e.g. when testing this module standalone without a
        known denomination).

        NOTE: this is intentionally a different variable from the local
        `denomination` used further below in this function, which holds
        the value actually OCR-read off the UV security mark - the two
        can legitimately differ (that mismatch is exactly what the
        authenticity check is looking for).

    Returns the result info dict.
    """
    folder_path, timestamp = create_output_folder()

    # 1. Capture / load UV image.
    original = capture_image(image_path)

    # 2. Detect banknote edges and straighten (perspective warp) it into
    #    a fixed-size canonical image. Falls back to a plain resize of
    #    the original if no note contour could be found.
    aligned, note_mask, note_found = align_banknote(original)

    # 3. Grayscale (of the ALIGNED image from here on).
    gray = preprocess_image(aligned)

    # 4. Threshold.
    thresh, morphed = apply_uv_threshold(gray, threshold_value)

    # 5. Contours of glowing regions.
    contours = find_uv_contours(morphed)
    detected_regions_img = draw_detected_regions(gray, contours)

    # 6. Extract ROIs calibrated for THIS note's denomination (falls back
    #    to the generic ROI if this denomination isn't calibrated yet).
    rois_cfg = get_rois_for_denomination(classifier_denomination)
    rois = extract_rois(gray, rois_cfg)

    # 7. OCR on each ROI, in EVERY orientation configured in
    #    OCR_ORIENTATIONS (normal, rotated180, mirrored,
    #    mirrored+rotated180), since we don't know ahead of time how
    #    this capture ended up oriented in the chamber.
    roi_ocr_results = {
        "bottom_left": run_ocr_both_orientations(rois["bottom_left"]),
        "top_left": run_ocr_both_orientations(rois["top_left"]),
    }

    # 8-9. Determine detected value + authenticity from whichever
    # (roi, orientation) combination produced a usable reading first
    # (see REQUIRE_KNOWN_DENOMINATION for strict vs lenient matching).
    denomination, source_roi_name, source_orientation, matched_text, is_known_denomination = detect_denomination(
        roi_ocr_results
    )
    status = determine_authenticity(denomination)

    # Debug overlays - show the OCR text for the orientation that
    # actually matched (falls back to "normal" if nothing matched, so
    # there's still something informative to look at).
    bl_display_orientation = source_orientation if source_roi_name == "bottom_left" else "normal"
    tl_display_orientation = source_orientation if source_roi_name == "top_left" else "normal"
    bl_ocr_img = draw_ocr_on_roi(
        rois["bottom_left"], roi_ocr_results["bottom_left"][bl_display_orientation]
    )
    tl_ocr_img = draw_ocr_on_roi(
        rois["top_left"], roi_ocr_results["top_left"][tl_display_orientation]
    )
    final_img = draw_result(aligned, denomination, status, source_roi_name, rois_cfg)

    # Save all pipeline stage images in the required order.
    save_debug_images(folder_path, {
        "01_original_uv.jpg": original,
        "02_note_mask.jpg": note_mask,
        "03_aligned_banknote.jpg": aligned,
        "04_grayscale.jpg": gray,
        "05_threshold.jpg": thresh,
        "06_morphology.jpg": morphed,
        "07_detected_regions.jpg": detected_regions_img,
        "08_bottom_left_roi.jpg": rois["bottom_left"],
        "09_top_left_roi.jpg": rois["top_left"],
        "10_bottom_left_ocr.jpg": bl_ocr_img,
        "11_top_left_ocr.jpg": tl_ocr_img,
        "12_final_result.jpg": final_img,
    })

    info = {
        "timestamp": timestamp,
        "threshold": threshold_value,
        "note_detected": note_found,
        "num_contours": len(contours),
        "classifier_denomination": classifier_denomination,
        "rois_used": rois_cfg,
        "bottom_left_ocr": roi_ocr_results["bottom_left"],
        "top_left_ocr": roi_ocr_results["top_left"],
        "denomination": denomination,
        "is_known_denomination": is_known_denomination,
        "require_known_denomination": REQUIRE_KNOWN_DENOMINATION,
        "source_roi": source_roi_name,
        "source_orientation": source_orientation,
        "status": status,
    }

    result_text = save_result_text(folder_path, info)

    # Console debugging output.
    print(result_text)
    print("\nProcessing complete.")
    print(f"Results saved to:\n{folder_path}/")

    return info


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    # Usage:
    #   python banknote_detector.py                            -> capture from camera
    #   python banknote_detector.py path/to/image.jpg           -> use a sample image
    #   python banknote_detector.py path/to/image.jpg 20        -> also use the 20 NIS ROI calibration
    image_arg = sys.argv[1] if len(sys.argv) > 1 else None
    denomination_arg = sys.argv[2] if len(sys.argv) > 2 else None

    process_banknote(
        image_path=image_arg,
        classifier_denomination=denomination_arg,
        threshold_value=THRESHOLD_VALUE,
    )