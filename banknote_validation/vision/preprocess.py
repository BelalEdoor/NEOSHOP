"""
vision/preprocess.py
=====================

Shared OpenCV preprocessing pipeline: grayscale -> Gaussian blur ->
adaptive threshold -> morphology.

Used by both ``paper_detector.py`` (RGB frame -> "is this paper money?")
and, in a later step, ``uv_validator.py`` (UV frame -> security-feature
analysis), so the pipeline lives in its own module rather than being
duplicated in each detector.

All kernel sizes, thresholds and iteration counts are sourced exclusively
from ``config.VisionConfig`` - no magic numbers live in this file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from config import VISION_CONFIG, VisionConfig
from vision import PreprocessError
from vision.image_utils import ImageUtils

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreprocessResult:
    """
    Bundles every intermediate stage of the preprocessing pipeline.

    Keeping intermediate stages (rather than only the final binary image)
    lets debug tooling persist each step to ``data/debug/`` and lets
    callers reuse an already-computed grayscale/blurred frame without
    recomputing it.
    """

    grayscale: np.ndarray
    blurred: np.ndarray
    thresholded: np.ndarray
    morphed: np.ndarray


class Preprocessor:
    """
    Applies the standard grayscale -> blur -> adaptive-threshold ->
    morphology pipeline to a captured frame, producing a clean binary image
    suitable for contour-based detection.

    Stateless aside from its configuration, so a single instance can safely
    be reused (or shared via dependency injection) across multiple frames
    and across both the RGB and UV pipelines.
    """

    def __init__(self, config: VisionConfig = VISION_CONFIG) -> None:
        """
        Initialize the preprocessor.

        Args:
            config: Vision pipeline configuration (blur kernel, threshold
                block size/constant, morphology kernel/iterations).
                Defaults to the module-level ``VISION_CONFIG`` singleton
                from ``config.py``.
        """
        self._config = config
        logger.debug(
            "Preprocessor initialized (blur=%s, thresh_block=%s, morph=%s).",
            config.GAUSSIAN_KERNEL_SIZE, config.ADAPTIVE_THRESH_BLOCK_SIZE, config.MORPH_KERNEL_SIZE,
        )

        # The morphology structuring element depends only on static config
        # and is identical for every frame this instance processes. It is
        # computed lazily (on first use in apply_morphology()) and cached
        # here rather than recomputed on every call, avoiding redundant
        # per-frame CPU work on Raspberry Pi 5. Kept lazy (rather than
        # built eagerly here) so constructing a Preprocessor never requires
        # OpenCV to be installed, consistent with every other method in
        # this class.
        self._morph_kernel = None

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert the input frame to grayscale.

        Args:
            image: Raw BGR frame.

        Returns:
            Single-channel grayscale image.

        Raises:
            PreprocessError: If conversion fails.
        """
        try:
            return ImageUtils.to_grayscale(image)
        except Exception as exc:  # noqa: BLE001
            raise PreprocessError(f"Grayscale conversion failed: {exc}") from exc

    def apply_gaussian_blur(self, gray_image: np.ndarray) -> np.ndarray:
        """
        Smooth a grayscale image with a Gaussian blur to suppress sensor
        noise before thresholding.

        Args:
            gray_image: Single-channel grayscale image.

        Returns:
            The blurred image.

        Raises:
            PreprocessError: If the blur operation fails.
        """
        import cv2

        try:
            return cv2.GaussianBlur(
                gray_image,
                self._config.GAUSSIAN_KERNEL_SIZE,
                self._config.GAUSSIAN_SIGMA_X,
            )
        except Exception as exc:  # noqa: BLE001
            raise PreprocessError(f"Gaussian blur failed: {exc}") from exc

    def apply_adaptive_threshold(self, blurred_image: np.ndarray) -> np.ndarray:
        """
        Binarize a blurred grayscale image using adaptive (local-mean)
        thresholding, which is far more robust than a global threshold
        under the uneven lighting typical of an enclosed scanning tray.

        Args:
            blurred_image: Output of :meth:`apply_gaussian_blur`.

        Returns:
            A binary (0/255) image.

        Raises:
            PreprocessError: If ``ADAPTIVE_THRESH_BLOCK_SIZE`` is even
                (OpenCV requires an odd block size) or the operation fails.
        """
        import cv2

        block_size = self._config.ADAPTIVE_THRESH_BLOCK_SIZE
        if block_size % 2 == 0:
            raise PreprocessError(
                f"ADAPTIVE_THRESH_BLOCK_SIZE must be odd, got {block_size}."
            )
        try:
            return cv2.adaptiveThreshold(
                blurred_image,
                self._config.ADAPTIVE_THRESH_MAX_VALUE,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                self._config.ADAPTIVE_THRESH_C,
            )
        except Exception as exc:  # noqa: BLE001
            raise PreprocessError(f"Adaptive threshold failed: {exc}") from exc

    def apply_morphology(self, binary_image: np.ndarray) -> np.ndarray:
        """
        Apply morphological closing (dilation followed by erosion) to the
        binary image to close small gaps in detected edges/regions before
        contour extraction.

        Args:
            binary_image: Output of :meth:`apply_adaptive_threshold`.

        Returns:
            The morphologically-closed binary image.

        Raises:
            PreprocessError: If the morphology operation fails.
        """
        import cv2

        try:
            if self._morph_kernel is None:
                self._morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self._config.MORPH_KERNEL_SIZE)
            return cv2.morphologyEx(
                binary_image,
                cv2.MORPH_CLOSE,
                self._morph_kernel,
                iterations=self._config.MORPH_ITERATIONS,
            )
        except Exception as exc:  # noqa: BLE001
            raise PreprocessError(f"Morphology operation failed: {exc}") from exc

    def preprocess(self, image: np.ndarray) -> PreprocessResult:
        """
        Run the full preprocessing pipeline on a captured frame.

        Args:
            image: The raw BGR frame straight from the camera.

        Returns:
            A :class:`PreprocessResult` bundling every intermediate stage
            (grayscale, blurred, thresholded, morphed).

        Raises:
            PreprocessError: If ``image`` is ``None`` or any stage of the
                pipeline fails.
        """
        if image is None:
            raise PreprocessError("Cannot preprocess a None image.")

        logger.debug("Starting preprocessing pipeline.")
        grayscale = self.to_grayscale(image)
        blurred = self.apply_gaussian_blur(grayscale)
        thresholded = self.apply_adaptive_threshold(blurred)
        morphed = self.apply_morphology(thresholded)
        logger.debug("Preprocessing pipeline complete.")

        return PreprocessResult(
            grayscale=grayscale,
            blurred=blurred,
            thresholded=thresholded,
            morphed=morphed,
        )
