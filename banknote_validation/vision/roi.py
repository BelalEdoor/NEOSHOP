"""
vision/roi.py
==============

Region-of-interest (ROI) extraction: crops - and, where possible,
perspective-corrects - the detected banknote region out of a full camera
frame, so downstream UV analysis and OCR only ever operate on the note
itself rather than the whole tray/background.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

from config import VISION_CONFIG, VisionConfig
from vision import ROIExtractionError
from vision.image_utils import ImageUtils

logger = logging.getLogger(__name__)


class ROIExtractor:
    """
    Extracts the banknote region-of-interest from a full camera frame.

    Two extraction strategies are supported:

        * :meth:`extract_perspective` - given 4 quadrilateral corner points
          (typically from :class:`~vision.paper_detector.PaperDetector`'s
          polygon approximation), warps the note to an upright,
          undistorted rectangle. Preferred when available, since it
          corrects for any rotation/skew of the inserted note.
        * :meth:`extract_bounding_box` - given an axis-aligned bounding
          box, crops the frame with configured padding. Used as a fallback
          when a clean 4-point quadrilateral was not found.

    This class intentionally has no dependency on ``PaperDetector`` - it
    operates purely on geometry (bounding boxes / corner points) passed in
    by the caller, keeping the two classes decoupled (Dependency
    Inversion Principle) and each independently unit-testable.
    """

    def __init__(self, config: VisionConfig = VISION_CONFIG) -> None:
        """
        Initialize the ROI extractor.

        Args:
            config: Vision pipeline configuration (ROI padding in pixels).
                Defaults to the module-level ``VISION_CONFIG`` singleton
                from ``config.py``.
        """
        self._config = config
        logger.debug("ROIExtractor initialized (padding=%spx).", config.ROI_PADDING_PX)

    def extract_bounding_box(
        self, image: np.ndarray, bounding_box: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Crop the frame to an axis-aligned bounding box, expanded by the
        configured padding and clamped to the frame's extents.

        Args:
            image: Full source frame.
            bounding_box: ``(x, y, w, h)`` as returned by
                ``cv2.boundingRect``.

        Returns:
            The cropped region as a new ``numpy.ndarray``.

        Raises:
            ROIExtractionError: If the resulting crop region is empty or
                the crop cannot be produced.
        """
        try:
            frame_h, frame_w = image.shape[:2]
            x, y, w, h = bounding_box
            pad = self._config.ROI_PADDING_PX

            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(frame_w, x + w + pad)
            y1 = min(frame_h, y + h + pad)

            if x1 <= x0 or y1 <= y0:
                raise ROIExtractionError(
                    f"Invalid crop region computed from bounding box {bounding_box}."
                )

            roi = image[y0:y1, x0:x1].copy()
            logger.debug("Bounding-box ROI extracted: (%s,%s)-(%s,%s).", x0, y0, x1, y1)
            return roi
        except ROIExtractionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ROIExtractionError(f"Failed to extract bounding-box ROI: {exc}") from exc

    def extract_perspective(self, image: np.ndarray, quad_points: np.ndarray) -> np.ndarray:
        """
        Warp the quadrilateral region defined by ``quad_points`` into an
        upright, perspective-corrected rectangle.

        Args:
            image: Full source frame.
            quad_points: 4 (x, y) corner points, e.g. from
                ``cv2.approxPolyDP``.

        Returns:
            The perspective-warped ROI as a new ``numpy.ndarray``.

        Raises:
            ROIExtractionError: If the warp cannot be computed or applied.
        """
        try:
            warped = ImageUtils.four_point_transform(image, quad_points)
            logger.debug("Perspective ROI extracted: shape=%s.", warped.shape)
            return warped
        except Exception as exc:  # noqa: BLE001
            raise ROIExtractionError(f"Failed to extract perspective ROI: {exc}") from exc

    def extract(
        self,
        image: np.ndarray,
        bounding_box: Tuple[int, int, int, int],
        quad_points: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Extract the best available ROI: perspective-corrected when
        ``quad_points`` is supplied and the warp succeeds, otherwise a
        padded axis-aligned bounding-box crop.

        Args:
            image: Full source frame.
            bounding_box: ``(x, y, w, h)`` fallback region.
            quad_points: Optional 4-point quadrilateral for perspective
                correction.

        Returns:
            The extracted ROI as a new ``numpy.ndarray``.

        Raises:
            ROIExtractionError: If neither extraction strategy succeeds.
        """
        if quad_points is not None:
            try:
                return self.extract_perspective(image, quad_points)
            except ROIExtractionError as exc:
                logger.warning(
                    "Perspective ROI extraction failed (%s); falling back to bounding-box crop.", exc
                )

        return self.extract_bounding_box(image, bounding_box)