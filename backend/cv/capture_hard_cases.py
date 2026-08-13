"""
capture_hard_cases.py — Fast, in-place photo capture for real deployment
conditions (cluttered background, varied lighting/distance/occlusion),
to fix the "works in clean test, fails in the lab" gap.

WHY THIS EXISTS
----------------
Your model was trained mostly on clean/staged photos. It performs worse
in a busy lab because it never saw that kind of background, lighting, or
distance during training. The fix isn't a code tweak — it's showing the
model real hard-case examples. This script makes capturing those fast:
no fumbling with a phone camera and manually renaming/sorting files.

HOW TO USE
----------
    python capture_hard_cases.py

Controls (webcam preview window):
    1-6   switch which product category you're photographing
          (edit CATEGORIES below to match your real category names)
    SPACE or S   save the current frame to raw_photos_hard/<category>/
    Q     quit

WHILE SHOOTING, deliberately vary these for EVERY product:
    - Distance: close, medium, far (not just close-up)
    - Angle: front, side, tilted, partially turned away
    - Occlusion: hand covering part of the label, fingers in front
    - Background: your actual lab/cart environment, not a plain wall
    - Lighting: wherever you'll actually be using the cart

Aim for at least 15-20 photos per category from THIS script, mixed in
with your existing training photos, before retraining. This directly
targets the failure mode you're seeing — real background/lighting/
distance variety is what a clean studio dataset can't give you.

Photos are saved as:
    raw_photos_hard/<category>/<category>_<counter>_<timestamp>.jpg
This folder structure matches build_dataset.py and the Roboflow upload
workflow you're already using — just point either at raw_photos_hard/
the same way you did for raw_photos/.
"""

import os
import time
import cv2

# Edit this to match your real category names exactly (must match
# PRODUCT_CLASSES / your Roboflow class names for anything you plan to
# merge back into the same training set).
CATEGORIES = {
    ord("1"): "bottle",
    ord("2"): "candy",
    ord("3"): "chips",
    ord("4"): "chocolate",
    ord("5"): "nuts",
    ord("6"): "pasta",
}

OUTPUT_DIR = "raw_photos_hard"
CAMERA_SOURCE = 0  # change if using a different camera index


def ensure_dir(category: str) -> str:
    path = os.path.join(OUTPUT_DIR, category)
    os.makedirs(path, exist_ok=True)
    return path


def next_filename(category: str) -> str:
    folder = ensure_dir(category)
    existing = [f for f in os.listdir(folder) if f.startswith(category + "_")]
    counter = len(existing) + 1
    timestamp = int(time.time())
    return os.path.join(folder, f"{category}_{counter:03d}_{timestamp}.jpg")


def draw_overlay(frame, category, saved_count):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 70), (0, 0, 0), -1)
    cv2.putText(frame, f"Category: {category}  (saved this session: {saved_count})",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, "1-6 switch category | SPACE/S save | Q quit",
                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return frame


def main():
    cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[WARN] CAP_DSHOW failed to open camera, retrying with default backend...")
        cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera source: {CAMERA_SOURCE}")
        print("[ERROR] Check that no other app (webcam_test.py, Zoom, Teams, browser tab, etc.) "
              "is currently using the camera, and that CAMERA_SOURCE (currently "
              f"{CAMERA_SOURCE}) is the right index for your device.")
        return

    category = CATEGORIES[ord("1")]
    saved_count = 0
    print(f"[INFO] Starting capture. Current category: {category}")
    print("[INFO] Vary distance, angle, occlusion, and lighting between shots.")
  #just a comment to test the commit :) 
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[WARN] Frame grab failed, retrying...")
            continue

        display = frame.copy()
        display = draw_overlay(display, category, saved_count)
        cv2.imshow("Hard-Case Capture", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key in CATEGORIES:
            category = CATEGORIES[key]
            print(f"[INFO] Switched category -> {category}")
        elif key == ord(" ") or key == ord("s"):
            path = next_filename(category)
            cv2.imwrite(path, frame)
            saved_count += 1
            print(f"[SAVED] {path}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"[DONE] Saved {saved_count} photos this session -> {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
