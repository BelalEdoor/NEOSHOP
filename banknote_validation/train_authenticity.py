"""
train_authenticity.py
======================

Trains a convolutional autoencoder on UV images of GENUINE banknotes
only (we have no counterfeit samples), then calibrates a reconstruction-
error threshold. At inference time, any UV image whose reconstruction
error is ABOVE the threshold is flagged "suspicious" (anomaly detection,
not a 2-class genuine/counterfeit classifier — there is no counterfeit
class to train against).

Why this approach:
  - We only have genuine-note UV captures. A normal classifier needs
    both classes to learn a decision boundary; we don't have that.
  - An autoencoder trained ONLY on genuine UV images learns to compress
    and reconstruct the fluorescent security features (threads, ink
    patterns) that appear under UV on real notes. It gets very good at
    reconstructing genuine notes specifically.
  - A counterfeit note's UV response differs (different/no fluorescent
    ink, different thread pattern) -> the autoencoder, never having
    seen that pattern, reconstructs it poorly -> high reconstruction
    error -> flagged.

CAVEAT (important, read before trusting this in production):
  The threshold below is calibrated ONLY on genuine notes. We have never
  tested it against a real counterfeit or altered note. Treat "suspicious"
  as "needs a second check", not "confirmed counterfeit", until you can
  validate against real counterfeit samples and retune the threshold.

Data used: only the UV images (uv_*.jpg) inside dataset/20 and
dataset/50 — both denominations are pooled together, because the
autoencoder should learn "what genuine UV fluorescence looks like"
in general, not per-denomination. (RGB images are NOT used here; RGB
lighting doesn't carry the fluorescent security features.)

Usage:
    python3 train_authenticity.py
Outputs (in ./outputs/):
    best_autoencoder.pt         - best PyTorch checkpoint (by val loss)
    autoencoder_uv.onnx         - ONNX export of the best model
    authenticity_threshold.json - calibrated anomaly threshold + stats
    authenticity_report.txt     - training/calibration summary
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from PIL import Image
from torchvision import transforms

SEED = 42
BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "dataset"
OUT_DIR = BASE_DIR / "outputs"
IMG_SIZE = 128
BATCH_SIZE = 16
EPOCHS = 40
VAL_FRACTION = 0.15
LR = 1e-3
# Safety margin multiplier applied on top of the max observed genuine
# reconstruction error, to set the final anomaly threshold. Increase
# this if genuine notes are getting false-flagged; decrease it (closer
# to 1.0) if it's not sensitive enough once you have counterfeit
# samples to test against.
THRESHOLD_MARGIN = 1.15

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


class UVGenuineDataset(Dataset):
    """Loads only uv_*.jpg files from dataset/20 and dataset/50, pooled."""

    def __init__(self, paths: list[Path], transform):
        self.paths = paths
        self.transform = transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int):
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img)


def collect_uv_paths() -> list[Path]:
    paths = sorted(DATASET_DIR.glob("*/uv_*.jpg"))
    if not paths:
        raise RuntimeError(
            f"No uv_*.jpg files found under {DATASET_DIR}. "
            "Run organize_dataset.py first."
        )
    return paths


def stratified_split(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Split train/val while keeping the 20/50 ratio balanced in both."""
    by_class: dict[str, list[Path]] = {}
    for p in paths:
        by_class.setdefault(p.parent.name, []).append(p)

    rng = random.Random(SEED)
    train_paths, val_paths = [], []
    for label, items in by_class.items():
        items = items[:]
        rng.shuffle(items)
        n_val = max(1, int(len(items) * VAL_FRACTION))
        val_paths.extend(items[:n_val])
        train_paths.extend(items[n_val:])
    return train_paths, val_paths


class ConvAutoencoder(nn.Module):
    """
    Small convolutional autoencoder. Encoder downsamples 128x128 -> 8x8,
    decoder mirrors it back up. Sized to be trainable on ~340 genuine
    UV images without overfitting to a trivial identity mapping.
    """

    def __init__(self) -> None:
        super().__init__()

        def enc_block(in_c, out_c):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, 3, stride=2, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            )

        def dec_block(in_c, out_c):
            return nn.Sequential(
                nn.ConvTranspose2d(in_c, out_c, 4, stride=2, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            )

        self.encoder = nn.Sequential(
            enc_block(3, 16),    # 128 -> 64
            enc_block(16, 32),   # 64  -> 32
            enc_block(32, 64),   # 32  -> 16
            enc_block(64, 96),   # 16  -> 8
        )
        self.decoder = nn.Sequential(
            dec_block(96, 64),   # 8   -> 16
            dec_block(64, 32),   # 16  -> 32
            dec_block(32, 16),   # 32  -> 64
            nn.ConvTranspose2d(16, 3, 4, stride=2, padding=1),  # 64 -> 128
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        return self.decoder(z)


def per_image_recon_error(model, loader, device) -> np.ndarray:
    """Mean-squared reconstruction error per image (not averaged over batch)."""
    model.eval()
    errors = []
    with torch.no_grad():
        for x in loader:
            x = x.to(device)
            recon = model(x)
            err = ((recon - x) ** 2).mean(dim=[1, 2, 3])
            errors.extend(err.cpu().numpy().tolist())
    return np.array(errors)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    uv_paths = collect_uv_paths()
    train_paths, val_paths = stratified_split(uv_paths)
    print(f"UV genuine images -> train: {len(train_paths)}, val: {len(val_paths)}")

    train_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomRotation(5),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
        ]
    )
    eval_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
        ]
    )

    train_ds = UVGenuineDataset(train_paths, train_tf)
    val_ds = UVGenuineDataset(val_paths, eval_tf)
    # Also build a train-set loader WITHOUT augmentation, used only for
    # computing clean reconstruction-error stats after training.
    train_eval_ds = UVGenuineDataset(train_paths, eval_tf)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    train_eval_loader = DataLoader(train_eval_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model = ConvAutoencoder().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss = 0.0
        for x in train_loader:
            x = x.to(device)
            optimizer.zero_grad()
            recon = model(x)
            loss = criterion(recon, x)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * x.size(0)
        scheduler.step()

        train_loss = running_loss / len(train_loader.dataset)

        model.eval()
        val_running = 0.0
        with torch.no_grad():
            for x in val_loader:
                x = x.to(device)
                recon = model(x)
                val_running += criterion(recon, x).item() * x.size(0)
        val_loss = val_running / len(val_loader.dataset)

        print(f"Epoch {epoch:2d}/{EPOCHS} | train_loss={train_loss:.5f} | val_loss={val_loss:.5f}")

        if val_loss <= best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), OUT_DIR / "best_autoencoder.pt")

    # Reload best checkpoint for calibration + export
    model.load_state_dict(torch.load(OUT_DIR / "best_autoencoder.pt", map_location=device))

    val_errors = per_image_recon_error(model, val_loader, device)
    train_errors = per_image_recon_error(model, train_eval_loader, device)
    all_genuine_errors = np.concatenate([val_errors, train_errors])

    # Threshold: max observed genuine reconstruction error * safety margin.
    # More robust than mean+k*std with a small sample (avoids false
    # positives on genuine notes that happen to reconstruct slightly worse).
    max_genuine_error = float(all_genuine_errors.max())
    threshold = max_genuine_error * THRESHOLD_MARGIN

    stats = {
        "val_error_mean": float(val_errors.mean()),
        "val_error_std": float(val_errors.std()),
        "val_error_min": float(val_errors.min()),
        "val_error_max": float(val_errors.max()),
        "train_error_mean": float(train_errors.mean()),
        "all_genuine_error_max": max_genuine_error,
        "threshold_margin": THRESHOLD_MARGIN,
        "threshold": threshold,
        "img_size": IMG_SIZE,
        "n_train": len(train_paths),
        "n_val": len(val_paths),
    }
    (OUT_DIR / "authenticity_threshold.json").write_text(json.dumps(stats, indent=2))

    report = (
        f"Genuine-note reconstruction error stats (n_train={len(train_paths)}, "
        f"n_val={len(val_paths)}):\n"
        f"  val:   mean={val_errors.mean():.6f} std={val_errors.std():.6f} "
        f"min={val_errors.min():.6f} max={val_errors.max():.6f}\n"
        f"  train: mean={train_errors.mean():.6f} max={train_errors.max():.6f}\n\n"
        f"Calibrated anomaly threshold (max genuine error * {THRESHOLD_MARGIN}): "
        f"{threshold:.6f}\n"
        f"Any new UV image with reconstruction error ABOVE this is flagged 'suspicious'.\n\n"
        f"CAVEAT: threshold calibrated only on genuine notes (no counterfeit samples\n"
        f"were available). Validate against real counterfeit/altered notes before\n"
        f"trusting this in production, and retune THRESHOLD_MARGIN if needed.\n"
    )
    print(report)
    (OUT_DIR / "authenticity_report.txt").write_text(report)

    # Export to ONNX for Raspberry Pi (ONNX Runtime) deployment.
    # `dynamo=False` is only accepted on newer torch (>=2.9, where the
    # torch.export-based exporter became default); older torch versions
    # don't have that kwarg at all, so fall back gracefully.
    model.eval()
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=device)
    export_kwargs = dict(
        input_names=["input"],
        output_names=["reconstruction"],
        dynamic_axes={"input": {0: "batch"}, "reconstruction": {0: "batch"}},
        opset_version=12,
    )
    try:
        torch.onnx.export(model, dummy, OUT_DIR / "autoencoder_uv.onnx", dynamo=False, **export_kwargs)
    except TypeError:
        torch.onnx.export(model, dummy, OUT_DIR / "autoencoder_uv.onnx", **export_kwargs)
    print(f"Saved ONNX autoencoder to {OUT_DIR / 'autoencoder_uv.onnx'}")


if __name__ == "__main__":
    main()