"""
infer.py
========

Loads the exported ONNX model and classifies a captured banknote image
as "20" or "50" using ONNX Runtime (same runtime already used elsewhere
in the RPi vision pipeline).

CLI usage:
    python3 infer.py path/to/image.jpg

Programmatic usage (e.g. from paper_detector.py after a note is
localized in the frame):
    from infer import CurrencyClassifier
    clf = CurrencyClassifier()
    label, confidence = clf.predict(bgr_frame)   # bgr_frame: np.ndarray from cv2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

MODEL_PATH = Path(__file__).parent / "outputs" / "currency_classifier.onnx"
CLASS_NAMES_PATH = Path(__file__).parent / "outputs" / "class_names.json"
IMG_SIZE = 160


class CurrencyClassifier:
    def __init__(self, model_path: Path = MODEL_PATH, class_names_path: Path = CLASS_NAMES_PATH) -> None:
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.class_names = json.loads(Path(class_names_path).read_text())

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        image: HxWx3 array, RGB, uint8 (0-255). If you have a BGR frame
        from cv2 (cv2.imread / cv2.VideoCapture), convert it first with
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).
        """
        import cv2

        resized = cv2.resize(image, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
        normalized = resized.astype(np.float32) / 255.0
        chw = np.transpose(normalized, (2, 0, 1))  # HWC -> CHW
        return chw[np.newaxis, ...]  # add batch dim

    def predict(self, image_rgb: np.ndarray) -> tuple[str, float]:
        x = self._preprocess(image_rgb)
        logits = self.session.run(None, {self.input_name: x})[0][0]
        probs = np.exp(logits - logits.max())
        probs /= probs.sum()
        idx = int(probs.argmax())
        return self.class_names[idx], float(probs[idx])


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 infer.py path/to/image.jpg")
        sys.exit(1)

    import cv2

    img_path = sys.argv[1]
    bgr = cv2.imread(img_path)
    if bgr is None:
        print(f"Could not read image: {img_path}")
        sys.exit(1)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    clf = CurrencyClassifier()
    label, confidence = clf.predict(rgb)
    print(f"Predicted: {label} NIS  (confidence={confidence:.4f})")


if __name__ == "__main__":
    main()
