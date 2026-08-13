"""
merge_roboflow_dataset.py — Fold a downloaded public dataset (e.g. Roboflow's
Retail Product Recognition) into your own dataset/, remapped from specific
brand classes down to broad shape/packaging categories.

WHY REMAP INSTEAD OF USING THEIR CLASSES DIRECTLY
---------------------------------------------------
Your barcode scanner already identifies the EXACT product. The CV model's
job is only to notice "a [category]-shaped thing was picked up / placed
unscanned" — it doesn't need to know it's specifically Cadbury Dairy Milk
vs a different chocolate bar. Collapsing hundreds of specific brand
classes down to ~5 broad categories means:
  - Every one of their labeled images becomes USABLE training data for you,
    regardless of whether they happen to sell that exact brand
  - Far more examples per class than any single-SKU approach could give you
  - Much less prone to the overfitting/false-positive problem you hit
    training on 2-4 photos of one specific product

HOW TO USE
----------
1. On Roboflow Universe, download the dataset in "YOLOv8" format (creates
   a zip with train/valid/test folders, each containing images/ + labels/,
   plus a data.yaml listing their class names).
2. Unzip it somewhere, e.g. ./roboflow_export/
3. Edit CATEGORY_MAP below — map their specific class names to your 5
   broad categories. Any of their classes NOT in this map get dropped
   from that image's labels (the image is still used — if it has ZERO
   remaining relevant boxes after remapping, it becomes a free negative
   example, which is exactly what you need more of).
4. Run:
     python merge_roboflow_dataset.py --source roboflow_export --dest dataset
   This merges into your existing dataset/ (created by build_dataset.py),
   respecting their train/valid split (valid -> your val).
5. Re-check dataset/data.yaml — it's rewritten with the unified category
   list. Then retrain as usual.

ATTRIBUTION
-----------
Public datasets are often CC BY licensed — if you redistribute or publish
anything trained partly on one, credit it (e.g. "Retail Product Recognition
dataset, APU University, CC BY 4.0") in your README.
"""

import argparse
import os
import glob
import shutil
import yaml

# ── EDIT THIS: map their class names -> your broad categories ──────────────
# Left side = exactly as it appears in the source dataset's data.yaml names
# list. Right side = one of your own category names. Add as many lines as
# needed; anything not listed is dropped (safely — see docstring above).
CATEGORY_MAP = {
    "bottle": "bottle",
    "candy": "candy",
    "chips": "chips",
    "chocolate": "chocolate",
    "nuts": "nuts",
    "pasta": "pasta",
}
OUR_CATEGORIES = sorted(set(CATEGORY_MAP.values()))


def load_source_classes(source_dir):
    yaml_path = os.path.join(source_dir, "data.yaml")
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"No data.yaml found in {source_dir}")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    names = data["names"]
    if isinstance(names, dict):
        # some exports use {0: "name", 1: "name"} instead of a list
        names = [names[i] for i in range(len(names))]
    return names


def find_split_dirs(source_dir):
    """Roboflow exports usually have train/ valid/ (sometimes test/), each
    with images/ and labels/ subfolders. Map 'valid' -> our 'val'."""
    splits = {}
    for name, our_name in [("train", "train"), ("valid", "val"), ("val", "val"), ("test", "val")]:
        img_dir = os.path.join(source_dir, name, "images")
        lbl_dir = os.path.join(source_dir, name, "labels")
        if os.path.isdir(img_dir) and os.path.isdir(lbl_dir):
            splits[our_name] = splits.get(our_name, []) + [(img_dir, lbl_dir)]
    return splits


def remap_label_file(src_label_path, source_class_names, category_to_id):
    """Read a YOLO label file using SOURCE class ids, return new lines using
    OUR category ids. Boxes for unmapped classes are dropped."""
    new_lines = []
    with open(src_label_path) as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            src_class_id = int(parts[0])
            if src_class_id >= len(source_class_names):
                continue
            src_name = source_class_names[src_class_id]
            our_category = CATEGORY_MAP.get(src_name)
            if our_category is None:
                continue  # not in our taxonomy, drop this box
            new_class_id = category_to_id[our_category]
            new_lines.append(f"{new_class_id} {' '.join(parts[1:])}")
    return new_lines  # empty list = valid negative example (no relevant objects)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Path to unzipped Roboflow export")
    parser.add_argument("--dest", default="dataset", help="Your existing dataset/ folder")
    parser.add_argument("--list-classes", action="store_true",
                         help="Just print the source dataset's class names and exit "
                              "(use this first to build CATEGORY_MAP)")
    args = parser.parse_args()

    source_class_names = load_source_classes(args.source)

    if args.list_classes:
        print(f"[INFO] {len(source_class_names)} classes found in {args.source}:")
        for name in source_class_names:
            mapped = CATEGORY_MAP.get(name, "— NOT MAPPED (will be dropped) —")
            print(f"  {name!r:40s} -> {mapped}")
        return

    if not CATEGORY_MAP:
        print("[ERROR] CATEGORY_MAP is empty. Run with --list-classes first, "
              "then edit CATEGORY_MAP at the top of this script.")
        return

    for split in ("train", "val"):
        os.makedirs(os.path.join(args.dest, "images", split), exist_ok=True)
        os.makedirs(os.path.join(args.dest, "labels", split), exist_ok=True)

    category_to_id = {name: i for i, name in enumerate(OUR_CATEGORIES)}
    print(f"[INFO] Your unified categories: {category_to_id}")

    split_dirs = find_split_dirs(args.source)
    if not split_dirs:
        print(f"[ERROR] Couldn't find train/valid images+labels folders under {args.source}. "
              f"Check the unzipped structure matches a standard Roboflow YOLOv8 export.")
        return

    total_kept, total_dropped_empty, total_images = 0, 0, 0
    for split, dirs in split_dirs.items():
        for img_dir, lbl_dir in dirs:
            for img_path in glob.glob(os.path.join(img_dir, "*")):
                if not img_path.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                base = os.path.splitext(os.path.basename(img_path))[0]
                lbl_path = os.path.join(lbl_dir, base + ".txt")
                if not os.path.exists(lbl_path):
                    continue

                new_lines = remap_label_file(lbl_path, source_class_names, category_to_id)
                total_images += 1
                if new_lines:
                    total_kept += 1
                else:
                    total_dropped_empty += 1  # becomes a negative example, not skipped

                out_name = f"rf_{split}_{total_images:05d}"
                shutil.copy(img_path, os.path.join(args.dest, "images", split, out_name + os.path.splitext(img_path)[1]))
                with open(os.path.join(args.dest, "labels", split, out_name + ".txt"), "w") as f:
                    f.write("\n".join(new_lines) + ("\n" if new_lines else ""))

    # rewrite data.yaml with the unified category list
    yaml_path = os.path.join(args.dest, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {os.path.abspath(args.dest)}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write(f"nc: {len(OUR_CATEGORIES)}\n")
        f.write(f"names: {OUR_CATEGORIES}\n")

    print(f"\n[DONE] Merged {total_images} images from {args.source}")
    print(f"  {total_kept} contain at least one relevant category box")
    print(f"  {total_dropped_empty} became negative examples (no relevant boxes) — "
          f"this is a bonus, not wasted data")
    print(f"[DONE] dataset/data.yaml rewritten with categories: {OUR_CATEGORIES}")
    print(f"\nIMPORTANT: your OWN photos (via build_dataset.py) must use these SAME "
          f"category folder names in raw_photos/ (e.g. raw_photos/bottle/, not "
          f"raw_photos/coca_cola/) for everything to line up under one class list.")


if __name__ == "__main__":
    main()
