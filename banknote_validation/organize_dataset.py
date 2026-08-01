"""
organize_dataset.py
====================

Takes the raw capture folders produced by the cart's RGB and UV cameras
(each capture session's filename index restarts at 001) and sorts them
into class folders suitable for training:

    dataset/20/<rgb|uv>_xxxxx.jpg
    dataset/50/<rgb|uv>_xxxxx.jpg

Session -> label mapping for THIS capture batch (verified visually):

    RGB (rgb_capture_*):
        session 1 (6 frames,  140336-140352) -> empty tray, no note -> SKIPPED
        session 2 (100 frames, 140430-141000) -> 20 NIS (green note)
        session 3 (100 frames, 141915-142446) -> 50 NIS (purple/red note)

    UV (uv_capture_*):
        session 1 (100 frames, 141004-141639) -> 20 NIS
        session 2 (100 frames, 142450-143125) -> 50 NIS

If you capture a new batch later, just update SESSION_LABELS_RGB /
SESSION_LABELS_UV below (sessions are auto-detected by index reset,
you only need to say which label each detected session belongs to,
or None to skip it).

Before running, extract the raw capture archives next to this script:
    capture.7z  -> raw_rgb/capture/*.jpg
    capture1.7z -> raw_uv/capture/*.jpg
(7z x capture.7z -oraw_rgb  /  7z x capture1.7z -oraw_uv)
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
# Extract capture.7z  -> raw_rgb/capture/*.jpg
# Extract capture1.7z -> raw_uv/capture/*.jpg
RAW_RGB_DIR = BASE_DIR / "raw_rgb" / "capture"
RAW_UV_DIR = BASE_DIR / "raw_uv" / "capture"
OUT_DIR = BASE_DIR / "dataset"

# Order = chronological order of sessions as detected (index resets to 001).
SESSION_LABELS_RGB = [None, "20", "50"]
SESSION_LABELS_UV = ["20", "50"]

FILENAME_RE = re.compile(r"(rgb|uv)_capture_(\d{8})_(\d{6})_(\d{3})\.jpg")


def detect_sessions(folder: Path) -> list[list[Path]]:
    files = sorted(folder.glob("*.jpg"))
    sessions: list[list[Path]] = []
    current: list[Path] = []
    for f in files:
        m = FILENAME_RE.match(f.name)
        if not m:
            continue
        idx = int(m.group(4))
        if idx == 1 and current:
            sessions.append(current)
            current = []
        current.append(f)
    if current:
        sessions.append(current)
    return sessions


def copy_sessions(folder: Path, labels: list[str | None], prefix: str) -> dict[str, int]:
    sessions = detect_sessions(folder)
    if len(sessions) != len(labels):
        raise RuntimeError(
            f"{folder}: detected {len(sessions)} sessions but {len(labels)} "
            f"labels configured. Update SESSION_LABELS_* to match."
        )
    counts: dict[str, int] = {}
    for session, label in zip(sessions, labels):
        if label is None:
            continue
        dest_dir = OUT_DIR / label
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in session:
            dest = dest_dir / f"{prefix}_{src.name}"
            shutil.copy2(src, dest)
        counts[label] = counts.get(label, 0) + len(session)
    return counts


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    rgb_counts = copy_sessions(RAW_RGB_DIR, SESSION_LABELS_RGB, prefix="rgb")
    uv_counts = copy_sessions(RAW_UV_DIR, SESSION_LABELS_UV, prefix="uv")

    print("RGB images copied per class:", rgb_counts)
    print("UV images copied per class :", uv_counts)

    for label_dir in sorted(OUT_DIR.iterdir()):
        n = len(list(label_dir.glob("*.jpg")))
        print(f"TOTAL class '{label_dir.name}': {n} images")


if __name__ == "__main__":
    main()
