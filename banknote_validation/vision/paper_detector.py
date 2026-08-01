"""
vision/paper_detector.py
==========================

Paper-shape detection: determines whether the captured RGB image contains
a rectangular, banknote-proportioned paper object.

This implements workflow step 4 ("Verify that the inserted object is paper
money") using pure shape/geometry analysis - grayscale, blur, adaptive
threshold, morphology, contour extraction, area-ratio filtering and
aspect-ratio filtering. It does NOT attempt to read the denomination
(that's the OCR package's job) or check UV security features (that's
``uv_validator.py``, added in a later step); it only answers "is this a
banknote-shaped piece of paper?".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from config import VISION_CONFIG, VisionConfig
from vision import PaperDetectionError
from vision.image_utils import ImageUtils
from vision.preprocess import Preprocessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperDetectionResult:
    """
    Outcome of a paper-detection pass over a single frame.

    ``is_paper`` is the primary business signal. The remaining fields
    (populated whenever available, even when ``is_paper`` is False due to a
    failed aspect-ratio check) let downstream stages - ROI extraction, debug
    overlays - reuse the detected geometry without re-running contour
    detection from scratch.
    """

    is_paper: bool
    contour: Optional[np.ndarray] = None
    quad_points: Optional[np.ndarray] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    aspect_ratio: Optional[float] = None
    area_ratio: Optional[float] = None


class PaperDetector:
    """
    Detects a rectangular, banknote-proportioned paper object in an RGB
    frame using contour analysis.

    Pipeline: preprocess (grayscale/blur/threshold/morphology) -> find
    contours -> pick the largest contour within the configured area-ratio
    bounds -> validate its aspect ratio -> approximate a 4-point
    quadrilateral for later perspective-correct ROI extraction.

    Dependency injection: a :class:`~vision.preprocess.Preprocessor`
    instance can be supplied so this class can be unit tested against a
    fake/stub preprocessor without invoking real OpenCV operations.
    """

    def __init__(
        self,
        config: VisionConfig = VISION_CONFIG,
        preprocessor: Optional[Preprocessor] = None,
    ) -> None:
        """
        Initialize the paper detector.

        Args:
            config: Vision pipeline configuration (contour area-ratio
                bounds, aspect-ratio bounds, polygon approximation
                tolerance). Defaults to the module-level ``VISION_CONFIG``
                singleton from ``config.py``.
            preprocessor: Preprocessing pipeline used to binarize the frame
                before contour detection. Defaults to a new
                :class:`Preprocessor` built from the same ``config``.
        """
        self._config = config
        self._preprocessor = preprocessor if preprocessor is not None else Preprocessor(config)
        logger.debug("PaperDetector initialized.")

    def _find_contours(self, binary_image: np.ndarray) -> List[np.ndarray]:
        """
        Find external contours in a binary image.

        Args:
            binary_image: Output of the preprocessing pipeline's morphology
                stage.

        Returns:
            A list of contours (possibly empty).

        Raises:
            PaperDetectionError: If contour detection fails.
        """
        import cv2

        try:
            contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return list(contours)
        except Exception as exc:  # noqa: BLE001
            raise PaperDetectionError(f"Contour detection failed: {exc}") from exc

    def _largest_valid_contour(
        self, contours: List[np.ndarray], frame_area: int
    ) -> Optional[np.ndarray]:
        """
        Return the largest contour whose area falls within the configured
        ``[MIN_CONTOUR_AREA_RATIO, MAX_CONTOUR_AREA_RATIO]`` fraction of the
        total frame area.

        Args:
            contours: Candidate contours, as returned by
                :meth:`_find_contours`.
            frame_area: Total pixel area of the source frame.

        Returns:
            The best-matching contour, or ``None`` if no contour qualifies.
        """
        import cv2

        min_area = frame_area * self._config.MIN_CONTOUR_AREA_RATIO
        max_area = frame_area * self._config.MAX_CONTOUR_AREA_RATIO

        candidates = sorted(contours, key=cv2.contourArea, reverse=True)
        for contour in candidates:
            area = cv2.contourArea(contour)
            if min_area <= area <= max_area:
                return contour
        return None

    def _approximate_quadrilateral(self, contour: np.ndarray) -> Optional[np.ndarray]:
        """
        Approximate a contour to a simplified polygon and return it only if
        it resolves to exactly 4 vertices (a clean rectangle/quadrilateral).

        Args:
            contour: Source contour to approximate.

        Returns:
            A ``(4, 1, 2)`` array of corner points, or ``None`` if the
            contour does not approximate to a quadrilateral.

        Raises:
            PaperDetectionError: If polygon approximation fails.
        """
        import cv2

        try:
            perimeter = cv2.arcLength(contour, True)
            epsilon = self._config.APPROX_POLY_EPSILON_RATIO * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            return approx if len(approx) == 4 else None
        except Exception as exc:  # noqa: BLE001
            raise PaperDetectionError(f"Polygon approximation failed: {exc}") from exc

    def detect(self, image: np.ndarray) -> PaperDetectionResult:
        """
        Analyze a captured RGB frame and determine whether it contains a
        banknote-shaped paper object.

        Args:
            image: The raw BGR frame captured under white-LED illumination.

        Returns:
            A :class:`PaperDetectionResult`. ``is_paper`` is ``False`` when
            no qualifying rectangular contour is found, or when the best
            candidate's aspect ratio falls outside the configured banknote
            proportions - this is a normal, expected outcome and does NOT
            raise an exception.

        Raises:
            PaperDetectionError: If the underlying OpenCV operations
                themselves fail (e.g. a malformed input image), as opposed
                to simply not finding a matching shape.
        """
        if image is None or image.size == 0:
            raise PaperDetectionError("Cannot run paper detection on an empty/None image.")

        preprocessed = self._preprocessor.preprocess(image)
        contours = self._find_contours(preprocessed.morphed)
        if not contours:
            logger.info("Paper detection: no contours found in frame.")
            return PaperDetectionResult(is_paper=False)

        frame_area = ImageUtils.frame_area(image)
        best_contour = self._largest_valid_contour(contours, frame_area)
        if best_contour is None:
            logger.info("Paper detection: no contour matched the configured area-ratio bounds.")
            return PaperDetectionResult(is_paper=False)

        import cv2

        try:
            x, y, w, h = cv2.boundingRect(best_contour)
            area_ratio = float(cv2.contourArea(best_contour)) / frame_area
            aspect_ratio = ImageUtils.compute_aspect_ratio(w, h)
        except Exception as exc:  # noqa: BLE001
            raise PaperDetectionError(f"Failed to compute contour geometry: {exc}") from exc

        if not (self._config.MIN_ASPECT_RATIO <= aspect_ratio <= self._config.MAX_ASPECT_RATIO):
            logger.info(
                "Paper detection: aspect ratio %.2f outside allowed range [%.2f, %.2f].",
                aspect_ratio, self._config.MIN_ASPECT_RATIO, self._config.MAX_ASPECT_RATIO,
            )
            return PaperDetectionResult(
                is_paper=False,
                contour=best_contour,
                bounding_box=(x, y, w, h),
                aspect_ratio=aspect_ratio,
                area_ratio=area_ratio,
            )

        quad_points = self._approximate_quadrilateral(best_contour)

        logger.info(
            "Paper detected: aspect_ratio=%.2f area_ratio=%.3f quad_found=%s",
            aspect_ratio, area_ratio, quad_points is not None,
        )
        return PaperDetectionResult(
            is_paper=True,
            contour=best_contour,
            quad_points=quad_points,
            bounding_box=(x, y, w, h),
            aspect_ratio=aspect_ratio,
            area_ratio=area_ratio,
        )
