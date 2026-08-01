"""
train.py
========

Trains a lightweight CNN to classify a captured banknote image as
"20" or "50" (NIS), then exports the trained model to ONNX so it can
be served with ONNX Runtime on the Raspberry Pi (consistent with the
rest of the vision pipeline, which already moved off PyTorch on-device
due to Cortex-A72 incompatibility).

Trained from scratch on purpose (no ImageNet-pretrained backbone):
  - the two classes are already highly separable (note color/pattern),
    so a small from-scratch CNN converges fast and generalizes fine
    on ~400 images.
  - avoids depending on downloading pretrained weights, keeping this
    reproducible fully offline.

Usage:
    python3 train.py
Outputs (in ./outputs/):
    best_model.pt          - best PyTorch checkpoint (by val accuracy)
    currency_classifier.onnx - ONNX export of the best model
    class_names.json       - index -> label mapping used by the model
    training_report.txt    - final val accuracy + confusion matrix
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms

SEED = 42
BASE_DIR = Path(__file__).parent
DATASET_DIR = BASE_DIR / "dataset"
OUT_DIR = BASE_DIR / "outputs"
IMG_SIZE = 160
BATCH_SIZE = 16
EPOCHS = 20
VAL_FRACTION = 0.15
LR = 1e-3

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


class TinyCurrencyNet(nn.Module):
    """
    Small depthwise-separable CNN (MobileNet-style blocks) sized for
    Raspberry Pi CPU inference via ONNX Runtime. ~150K params.
    """

    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()

        def conv_bn(in_c, out_c, stride):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, 3, stride, 1, bias=False),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            )

        def dw_sep(in_c, out_c, stride):
            return nn.Sequential(
                nn.Conv2d(in_c, in_c, 3, stride, 1, groups=in_c, bias=False),
                nn.BatchNorm2d(in_c),
                nn.ReLU(inplace=True),
                nn.Conv2d(in_c, out_c, 1, 1, 0, bias=False),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            )

        self.features = nn.Sequential(
            conv_bn(3, 16, 2),      # 160 -> 80
            dw_sep(16, 32, 2),      # 80  -> 40
            dw_sep(32, 64, 2),      # 40  -> 20
            dw_sep(64, 96, 2),      # 20  -> 10
            dw_sep(96, 128, 2),     # 10  -> 5
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x).flatten(1)
        return self.classifier(x)


def build_dataloaders():
    train_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomRotation(15),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.1),
            transforms.ToTensor(),
        ]
    )
    val_tf = transforms.Compose(
        [
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
        ]
    )

    full_train = datasets.ImageFolder(DATASET_DIR, transform=train_tf)
    full_val = datasets.ImageFolder(DATASET_DIR, transform=val_tf)
    class_names = full_train.classes  # sorted alphabetically -> ['20', '50']

    n_val = int(len(full_train) * VAL_FRACTION)
    n_train = len(full_train) - n_val
    gen = torch.Generator().manual_seed(SEED)
    train_idx, val_idx = random_split(range(len(full_train)), [n_train, n_val], generator=gen)

    train_ds = torch.utils.data.Subset(full_train, train_idx.indices)
    val_ds = torch.utils.data.Subset(full_val, val_idx.indices)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    return train_loader, val_loader, class_names


def evaluate(model, loader, device):
    model.eval()
    correct, total = 0, 0
    confusion = np.zeros((2, 2), dtype=int)
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            preds = model(x).argmax(1)
            correct += (preds == y).sum().item()
            total += y.size(0)
            for t, p in zip(y.cpu().numpy(), preds.cpu().numpy()):
                confusion[t, p] += 1
    return correct / total, confusion


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_loader, val_loader, class_names = build_dataloaders()
    print("Classes:", class_names)

    model = TinyCurrencyNet(num_classes=len(class_names)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * x.size(0)
        scheduler.step()

        train_loss = running_loss / len(train_loader.dataset)
        val_acc, _ = evaluate(model, val_loader, device)
        print(f"Epoch {epoch:2d}/{EPOCHS} | train_loss={train_loss:.4f} | val_acc={val_acc:.4f}")

        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), OUT_DIR / "best_model.pt")

    # Reload best checkpoint for final report + export
    model.load_state_dict(torch.load(OUT_DIR / "best_model.pt", map_location=device))
    final_acc, confusion = evaluate(model, val_loader, device)

    report = (
        f"Best validation accuracy: {final_acc:.4f}\n"
        f"Classes (index order): {class_names}\n"
        f"Confusion matrix (rows=true, cols=pred):\n{confusion}\n"
    )
    print(report)
    (OUT_DIR / "training_report.txt").write_text(report)
    (OUT_DIR / "class_names.json").write_text(json.dumps(class_names))

    # Export to ONNX for Raspberry Pi (ONNX Runtime) deployment.
    # `dynamo=False` is only accepted on newer torch (>=2.9); older torch
    # versions don't have that kwarg at all, so fall back gracefully.
    model.eval()
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE, device=device)
    export_kwargs = dict(
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=12,
    )
    try:
        torch.onnx.export(model, dummy, OUT_DIR / "currency_classifier.onnx", dynamo=False, **export_kwargs)
    except TypeError:
        torch.onnx.export(model, dummy, OUT_DIR / "currency_classifier.onnx", **export_kwargs)
    print(f"Saved ONNX model to {OUT_DIR / 'currency_classifier.onnx'}")


if __name__ == "__main__":
    main()