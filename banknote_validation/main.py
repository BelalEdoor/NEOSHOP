"""
main.py
========

Unified Banknote Validation Pipeline
-------------------------------------
Merges the two previously separate projects:

    1) DENOMINATION CLASSIFIER (infer.py)
       Trained ONNX CNN (CurrencyClassifier) that predicts the note's
       value ("20" / "50" / ...) from a normal WHITE/RGB photo.

    2) UV AUTHENTICITY CHECK (alignment.py + banknote_detector.py)
       Classical OpenCV + Tesseract OCR pipeline that reads the
       fluorescent security number printed on the note under UV light
       and decides AUTHENTIC / FAKE. This is the exact pipeline that
       shipped inside banknote_testing.zip, untouched.

Flow
----
1. User picks a WHITE/RGB image from disk.
   -> CurrencyClassifier.predict() returns (denomination, confidence).
2. User picks a UV image of the SAME note from disk.
   -> banknote_detector.process_banknote() runs the full classical CV
      pipeline (alignment -> threshold -> ROI crop -> OCR -> decision)
      and returns an info dict, including info["status"] which is
      "AUTHENTIC" or "FAKE". Every intermediate stage image is saved
      under output/<timestamp>/ exactly as before (unchanged behavior).
3. The two results are combined into one final decision:
      ACCEPTED  -> UV check says AUTHENTIC
      REJECTED  -> UV check says FAKE

Usage:
    python3 main.py
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog

import cv2

from infer import CurrencyClassifier
from banknote_detector import process_banknote


# ----------------------------------------------------------------------------
# File selection helper
# ----------------------------------------------------------------------------
def select_image(title: str) -> str:
    """Open a file dialog and return the selected image path (or '' if cancelled)."""
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


# ----------------------------------------------------------------------------
# Stage 1: Denomination classification (WHITE / RGB image)
# ----------------------------------------------------------------------------
def classify_denomination(classifier: CurrencyClassifier) -> tuple[str, float] | None:
    print("\n[1] Select the WHITE / RGB banknote image...")
    rgb_path = select_image("Select WHITE / RGB banknote image")

    if not rgb_path:
        print("No RGB image selected.")
        return None

    print(f"Selected RGB image: {rgb_path}")

    bgr = cv2.imread(rgb_path)
    if bgr is None:
        print(f"Could not read image: {rgb_path}")
        return None

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    denomination, confidence = classifier.predict(rgb)

    print(f"\nCurrency       : {denomination} NIS")
    print(f"Confidence     : {confidence:.4f} ({confidence:.2%})")
    print("-" * 60)

    return denomination, confidence


# ----------------------------------------------------------------------------
# Stage 2: UV authenticity check (UV image)
# ----------------------------------------------------------------------------
def check_authenticity(classifier_denomination: str) -> dict | None:
    print("\n[2] Select the UV banknote image...")
    uv_path = select_image("Select UV banknote image")

    if not uv_path:
        print("No UV image selected.")
        return None

    print(f"Selected UV image: {uv_path}")
    print("\nRunning UV authenticity pipeline (alignment -> threshold -> OCR)...\n")

    # process_banknote() runs the entire classical-CV pipeline from
    # banknote_detector.py end-to-end and saves every debug stage image
    # under output/<timestamp>/, exactly like the original standalone
    # script. We pass the classifier's denomination through so it picks
    # the security-mark ROI pair calibrated for THIS note's physical size
    # (see DENOMINATION_ROIS in banknote_detector.py) instead of always
    # using the same fixed ROI regardless of denomination.
    info = process_banknote(image_path=uv_path, classifier_denomination=classifier_denomination)
    return info


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    print()
    print("=" * 60)
    print("             BANKNOTE VALIDATION")
    print("=" * 60)

    classifier = CurrencyClassifier()

    denom_result = classify_denomination(classifier)
    if denom_result is None:
        return
    denomination, confidence = denom_result

    uv_info = check_authenticity(denomination)
    if uv_info is None:
        return

    authenticity = uv_info["status"]  # "AUTHENTIC" or "FAKE"
    final_result = "ACCEPTED" if authenticity == "AUTHENTIC" else "REJECTED"

    print()
    print("=" * 60)
    print("                    FINAL RESULT")
    print("=" * 60)
    print(f"Currency (model)   : {denomination} NIS")
    print(f"Confidence (model) : {confidence:.2%}")
    print(f"UV Authenticity    : {authenticity}")
    print(f"Matched ROI        : {uv_info['source_roi'] or '-'} / {uv_info['source_orientation'] or '-'}")
    print("-" * 60)
    print(f"FINAL DECISION     : {final_result}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()