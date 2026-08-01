"""
main.py
========

Banknote validation pipeline.

1. User selects a WHITE/RGB banknote image from the computer.
2. CurrencyClassifier (existing trained model, infer.py) predicts the
   denomination (20 / 50 / ...).
3. User selects a UV banknote image from the computer.
4. UVValidator (vision/uv_validator.py) analyzes the UV image for genuine
   fluorescent security features:
       grayscale -> blur -> adaptive threshold -> morphology -> contours
       -> UV brightness ratio -> bright-region count -> is_valid
5. Final result is ACCEPTED or REJECTED.

Note on ROI extraction:
    The UV image selected here is expected to already be a crop of the
    note itself (not a full camera frame with background), so
    ROIExtractor is not required in this manual/file-picker flow. If this
    script is later wired to the live camera pipeline (full frame with
    background), extract the note region with
    ``vision.roi.ROIExtractor().extract(...)`` *before* calling
    ``UVValidator.validate(...)``.

Usage:
    python3 main.py
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import cv2

from infer import CurrencyClassifier
from config import CAMERA_CONFIG, PATHS, VISION_CONFIG
from vision import UVValidationError
from vision.uv_validator import UVValidator


# ----------------------------------------------------------------------------
# File selection helpers
# ----------------------------------------------------------------------------
def select_image(title: str) -> str:
    """Open a file dialog and return the selected image path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        title=title,
        filetypes=[
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("JPG files", "*.jpg *.jpeg"),
            ("PNG files", "*.png"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()
    return path


def load_rgb_image(path: str):
    """Load an image with OpenCV and convert BGR -> RGB (for CurrencyClassifier)."""
    bgr = cv2.imread(path)

    if bgr is None:
        raise ValueError(f"Could not read image: {path}")

    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def load_bgr_image(path: str):
    """Load an image with OpenCV, keeping the native BGR order (for UVValidator)."""
    bgr = cv2.imread(path)

    if bgr is None:
        raise ValueError(f"Could not read image: {path}")

    return bgr


def save_image(image_bgr, directory: Path, filename: str) -> Path:
    """
    Persist a BGR image under ``directory`` (created if missing) using the
    configured JPEG quality.

    Args:
        image_bgr: Image to save, in BGR order (OpenCV's native order).
        directory: Target directory, e.g. ``PATHS.UV_IMAGE_DIR`` or
            ``PATHS.DEBUG_IMAGE_DIR``.
        filename: Target filename, e.g. ``"20260731_142201_uv_raw.jpg"``.

    Returns:
        The full path the image was written to.
    """
    directory.mkdir(parents=True, exist_ok=True)
    out_path = directory / filename
    cv2.imwrite(str(out_path), image_bgr, [cv2.IMWRITE_JPEG_QUALITY, CAMERA_CONFIG.JPEG_QUALITY])
    return out_path


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------
def main() -> None:
    print()
    print("=" * 60)
    print("             BANKNOTE VALIDATION")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Select WHITE/RGB image
    # ---------------------------------------------------------
    print("\n[1] Select the WHITE/RGB banknote image...")

    rgb_path = select_image("Select WHITE / RGB banknote image")

    if not rgb_path:
        print("No RGB image selected.")
        return

    print(f"Selected RGB image: {rgb_path}")

    rgb_image = load_rgb_image(rgb_path)

    classifier = CurrencyClassifier()
    denomination, confidence = classifier.predict(rgb_image)

    print(f"\nCurrency       : {denomination} NIS")
    print(f"Confidence     : {confidence:.4f} ({confidence:.2%})")
    print("-" * 60)

    # ---------------------------------------------------------
    # 2. Select UV image
    # ---------------------------------------------------------
    print("\n[2] Select the UV banknote image...")

    uv_path = select_image("Select UV banknote image")

    if not uv_path:
        print("No UV image selected.")
        return

    print(f"Selected UV image: {uv_path}")

    uv_image = load_bgr_image(uv_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_uv_path = save_image(uv_image, PATHS.UV_IMAGE_DIR, f"{timestamp}_uv_raw.jpg")
    print(f"Saved raw UV image to: {raw_uv_path}")

    # ---------------------------------------------------------
    # 3. UV authenticity check
    # ---------------------------------------------------------
    print("\nChecking UV authenticity...")

    validator = UVValidator()

    try:
        result = validator.validate(uv_image)
    except UVValidationError as exc:
        print(f"\nUV validation failed: {exc}")

        failed_path = save_image(uv_image, PATHS.DEBUG_IMAGE_DIR, f"{timestamp}_uv_error.jpg")
        print(f"Saved failed UV image to: {failed_path}")

        print("\n" + "=" * 60)
        print(f"FINAL DECISION : REJECTED (UV validation error)")
        print("=" * 60)
        print()
        return

    cfg = VISION_CONFIG

    print(f"\nUV Mean Brightness : {result.mean_brightness:.4f}")
    print(f"Bright Pixel Ratio  : {result.bright_pixel_ratio:.4f}")
    print(
        f"Allowed Ratio       : {cfg.UV_MIN_BRIGHT_PIXEL_RATIO:.4f} - "
        f"{cfg.UV_MAX_BRIGHT_PIXEL_RATIO:.4f}"
    )
    print(f"Bright Regions      : {result.num_bright_regions}")
    print(f"Required Regions    : {cfg.UV_MIN_BRIGHT_REGIONS}")
    print("-" * 60)

    if result.is_valid:
        authenticity = "GENUINE"
        final_result = "ACCEPTED"
    else:
        authenticity = "SUSPICIOUS"
        final_result = "REJECTED"

    # Save a copy tagged with the verdict, and a debug overlay showing the
    # detected fluorescent regions (contours) that drove the decision.
    verdict_path = save_image(
        uv_image, PATHS.UV_IMAGE_DIR, f"{timestamp}_uv_{final_result.lower()}.jpg"
    )
    print(f"Saved UV image ({final_result}) to: {verdict_path}")

    # Debug visualization: the raw UV image next to an ISOLATED mask that
    # highlights only locally-brighter details (the fluorescent digits /
    # security thread), not the whole overexposed note surface.
    #
    # A plain global threshold (old approach) fails when the lighting is
    # strong (e.g. 4x UV LEDs): the entire note crosses the threshold and
    # the mask turns almost all-white, drowning out the actual feature.
    #
    # Top-hat filtering fixes this without touching the lighting: for each
    # pixel it subtracts the *local neighborhood's* brightness (computed
    # via a morphological "opening" with a kernel bigger than a digit's
    # stroke width but smaller than the note itself). A digit is brighter
    # than its immediate surroundings even on an overexposed note, so it
    # survives; the broad, evenly-bright background gets cancelled out.
    gray = cv2.cvtColor(uv_image, cv2.COLOR_BGR2GRAY)

    # Tune this: must be bigger than the digit stroke width, smaller than
    # the note. Too small -> background survives too. Too big -> digits
    # get cancelled out too. Start around 20-30px and adjust by eye.
    TOPHAT_KERNEL_SIZE = 25
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (TOPHAT_KERNEL_SIZE, TOPHAT_KERNEL_SIZE))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)

    # Otsu picks the cut-off from this shot's own histogram instead of a
    # fixed number, so it adapts automatically to how strong the lighting
    # was for this particular capture.
    _, bright_mask = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright_mask_bgr = cv2.cvtColor(bright_mask, cv2.COLOR_GRAY2BGR)

    debug_overlay = cv2.hconcat([uv_image, bright_mask_bgr])

    debug_path = save_image(
        debug_overlay, PATHS.DEBUG_IMAGE_DIR, f"{timestamp}_uv_regions_debug.jpg"
    )
    print(f"Saved UV regions debug image to: {debug_path}")

    cv2.imshow("UV Fluorescent Regions (press any key to continue)", debug_overlay)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------
    print()
    print("=" * 60)
    print("                    RESULT")
    print("=" * 60)
    print(f"Currency       : {denomination} NIS")
    print(f"Confidence     : {confidence:.2%}")
    print(f"UV Authenticity: {authenticity}")
    print(f"Bright Ratio   : {result.bright_pixel_ratio:.4f}")
    print(f"Bright Regions : {result.num_bright_regions}")
    print("-" * 60)
    print(f"FINAL DECISION : {final_result}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()