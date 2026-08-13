"""
build_dataset.py — Turn green-screen product photos into a YOLOv8-ready
custom dataset, WITHOUT manual bounding-box labeling.

HOW IT WORKS
------------
1. For each raw photo, auto-segment the product from the green background
   using chroma-key masking (HSV green range) -> get a clean cutout + exact
   bounding box for free (no manual annotation needed).
2. For each cutout, generate N synthetic training images by pasting it onto
   random real-world-ish backgrounds at random rotation, scale, and position.
   This is what fixes "only detects it in one orientation" — the model
   will see the product rotated 0-360°, at multiple sizes, during training.
3. Write everything out in standard YOLOv8 dataset format:
     dataset/
       images/train/*.jpg   images/val/*.jpg
       labels/train/*.txt   labels/val/*.txt   (YOLO format: class cx cy w h, normalized)
       data.yaml            (class names, train/val paths)

YOUR FOLDER SETUP (before running)
-----------------------------------
Put your raw green-screen photos in:
    raw_photos/
      coca_cola/*.jpg
      coffee_bag/*.jpg
      canned_olives/*.jpg
      guzel_chocolate/*.jpg
      ... one subfolder per product, folder name = class name

Then run:
    python build_dataset.py

RECOMMENDATIONS FOR RAW PHOTOS
-------------------------------
- 15-30 real photos per product is a good minimum (you're already close,
  based on the batch you shared). More angles/lighting in the RAW photos
  still helps even with augmentation — augmentation multiplies variety,
  it doesn't invent camera angles you never captured (e.g. if you never
  photographed the product upside-down, take a few of those too).
- Keep the green background consistent — this script assumes a fairly
  uniform chroma-key green. If your green varies a lot between shots,
  loosen GREEN_HSV_LOWER/UPPER below.
"""

import os
import glob
import random
import shutil

import cv2
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────
RAW_DIR = "raw_photos"
OUT_DIR = "dataset"
BACKGROUNDS_DIR = "backgrounds"   # optional: put a few real photos of your
                                   # store/counter/floor here for more
                                   # realistic composites. If empty, solid
                                   # random-color backgrounds are used instead.

AUGMENTATIONS_PER_PHOTO = 25   # synthetic images generated per raw photo
VAL_SPLIT = 0.15               # fraction held out for validation
OUTPUT_SIZE = (640, 640)       # YOLOv8 default training resolution

# Chroma-key green range (HSV). Widen if your green screen isn't uniform.
GREEN_HSV_LOWER = np.array([35, 40, 40])
GREEN_HSV_UPPER = np.array([85, 255, 255])

random.seed(42)
np.random.seed(42)


# ── Step 1: segment product from green background ──────────────────────────
def segment_product(image_path):
    """Returns (cutout_bgr, alpha_mask, bbox) or None if segmentation fails."""
    img = cv2.imread(image_path)
    if img is None:
        return None

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green_mask = cv2.inRange(hsv, GREEN_HSV_LOWER, GREEN_HSV_UPPER)
    product_mask = cv2.bitwise_not(green_mask)

    # Clean up noise
    kernel = np.ones((7, 7), np.uint8)
    product_mask = cv2.morphologyEx(product_mask, cv2.MORPH_OPEN, kernel)
    product_mask = cv2.morphologyEx(product_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(product_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 500:  # too small, likely noise
        return None

    x, y, w, h = cv2.boundingRect(largest)
    clean_mask = np.zeros_like(product_mask)
    cv2.drawContours(clean_mask, [largest], -1, 255, thickness=cv2.FILLED)

    cutout_bgr = img[y:y + h, x:x + w]
    cutout_mask = clean_mask[y:y + h, x:x + w]
    return cutout_bgr, cutout_mask, (x, y, w, h)


# ── Step 2: synthetic augmentation (rotation/scale/position/background) ────
def load_backgrounds():
    if not os.path.isdir(BACKGROUNDS_DIR):
        return []
    paths = glob.glob(os.path.join(BACKGROUNDS_DIR, "*.jpg")) + \
            glob.glob(os.path.join(BACKGROUNDS_DIR, "*.png"))
    return [cv2.imread(p) for p in paths if cv2.imread(p) is not None]


def random_background(bg_pool, size):
    w, h = size
    if bg_pool:
        bg = random.choice(bg_pool)
        bg = cv2.resize(bg, (w, h))
        return bg.copy()
    # fallback: random muted solid color (roughly store-shelf-ish tones)
    color = [random.randint(120, 220) for _ in range(3)]
    return np.full((h, w, 3), color, dtype=np.uint8)


def rotate_cutout(cutout_bgr, mask, angle):
    h, w = cutout_bgr.shape[:2]
    diag = int(np.sqrt(h ** 2 + w ** 2)) + 4
    canvas_bgr = np.zeros((diag, diag, 3), dtype=np.uint8)
    canvas_mask = np.zeros((diag, diag), dtype=np.uint8)
    ox, oy = (diag - w) // 2, (diag - h) // 2
    canvas_bgr[oy:oy + h, ox:ox + w] = cutout_bgr
    canvas_mask[oy:oy + h, ox:ox + w] = mask

    M = cv2.getRotationMatrix2D((diag / 2, diag / 2), angle, 1.0)
    rotated_bgr = cv2.warpAffine(canvas_bgr, M, (diag, diag))
    rotated_mask = cv2.warpAffine(canvas_mask, M, (diag, diag))

    ys, xs = np.where(rotated_mask > 0)
    if len(xs) == 0:
        return cutout_bgr, mask
    x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    return rotated_bgr[y1:y2 + 1, x1:x2 + 1], rotated_mask[y1:y2 + 1, x1:x2 + 1]


def composite(cutout_bgr, mask, bg):
    bh, bw = bg.shape[:2]
    ch, cw = cutout_bgr.shape[:2]

    scale = random.uniform(0.25, 0.6) * min(bw / cw, bh / ch)
    new_w, new_h = max(1, int(cw * scale)), max(1, int(ch * scale))
    cutout_r = cv2.resize(cutout_bgr, (new_w, new_h))
    mask_r = cv2.resize(mask, (new_w, new_h))

    max_x, max_y = max(1, bw - new_w), max(1, bh - new_h)
    px, py = random.randint(0, max_x), random.randint(0, max_y)

    out = bg.copy()
    roi = out[py:py + new_h, px:px + new_w]
    alpha = (mask_r.astype(np.float32) / 255.0)[..., None]
    roi[:] = (alpha * cutout_r + (1 - alpha) * roi).astype(np.uint8)
    out[py:py + new_h, px:px + new_w] = roi

    # brightness jitter for lighting variety
    factor = random.uniform(0.8, 1.2)
    out = np.clip(out.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    cx = (px + new_w / 2) / bw
    cy = (py + new_h / 2) / bh
    nw = new_w / bw
    nh = new_h / bh
    return out, (cx, cy, nw, nh)


# ── Main pipeline ────────────────────────────────────────────────────────
def main():
    if not os.path.isdir(RAW_DIR):
        print(f"[ERROR] '{RAW_DIR}/' not found. Create it with one subfolder per product.")
        return

    class_names = sorted([
        d for d in os.listdir(RAW_DIR)
        if os.path.isdir(os.path.join(RAW_DIR, d))
    ])
    if not class_names:
        print(f"[ERROR] No product subfolders found inside '{RAW_DIR}/'.")
        return
    print(f"[INFO] Found {len(class_names)} product classes: {class_names}")

    for split in ("train", "val"):
        os.makedirs(os.path.join(OUT_DIR, "images", split), exist_ok=True)
        os.makedirs(os.path.join(OUT_DIR, "labels", split), exist_ok=True)

    bg_pool = load_backgrounds()
    print(f"[INFO] Using {len(bg_pool) if bg_pool else 0} custom backgrounds "
          f"(0 = falling back to random solid colors)")

    total_generated = 0
    for class_id, class_name in enumerate(class_names):
        photos = glob.glob(os.path.join(RAW_DIR, class_name, "*"))
        photos = [p for p in photos if p.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not photos:
            print(f"[WARN] No photos found for '{class_name}', skipping.")
            continue

        print(f"[INFO] {class_name}: {len(photos)} raw photos -> "
              f"{len(photos) * AUGMENTATIONS_PER_PHOTO} synthetic images")

        img_counter = 0
        for photo_path in photos:
            seg = segment_product(photo_path)
            if seg is None:
                print(f"  [WARN] Could not segment {photo_path} — check green "
                      f"screen uniformity or lower the area threshold.")
                continue
            cutout_bgr, mask, _ = seg

            for i in range(AUGMENTATIONS_PER_PHOTO):
                angle = random.uniform(0, 360)
                rot_cutout, rot_mask = rotate_cutout(cutout_bgr, mask, angle)

                bg = random_background(bg_pool, OUTPUT_SIZE)
                composited, (cx, cy, nw, nh) = composite(rot_cutout, rot_mask, bg)

                split = "val" if random.random() < VAL_SPLIT else "train"
                fname = f"{class_name}_{img_counter:04d}"
                img_counter += 1
                total_generated += 1

                cv2.imwrite(os.path.join(OUT_DIR, "images", split, fname + ".jpg"), composited)
                with open(os.path.join(OUT_DIR, "labels", split, fname + ".txt"), "w") as f:
                    f.write(f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")

    # data.yaml for YOLOv8 training
    yaml_path = os.path.join(OUT_DIR, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {os.path.abspath(OUT_DIR)}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write(f"nc: {len(class_names)}\n")
        f.write(f"names: {class_names}\n")

    print(f"\n[DONE] Generated {total_generated} synthetic training images "
          f"across {len(class_names)} classes.")
    print(f"[DONE] Dataset ready at: {os.path.abspath(OUT_DIR)}")
    print(f"\nTrain with:\n  yolo detect train data={yaml_path} model=yolov8n.pt "
          f"epochs=50 imgsz=640")


if __name__ == "__main__":
    main()