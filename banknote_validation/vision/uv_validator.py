"""
vision/uv_validator.py
========================

UV security-feature validation: analyzes a banknote ROI captured under UV
illumination to determine whether it exhibits genuine fluorescent security
features (workflow step 8/10).

Pipeline (all steps operate on the already-extracted banknote ROI, i.e. the
output of ``vision.roi.ROIExtractor``, not the full camera frame):

    1. grayscale
    2. Gaussian blur
    3. adaptive threshold
    4. morphology
    5. contour extraction
    6. UV brightness analysis
    7. ROI validation
 
Steps 1-4 reuse :class:`vision.preprocess.Preprocessor` (the same pipeline
used by ``paper_detector.py``) to avoid duplicating OpenCV boilerplate.
This module adds the UV-specific logic on top: structural contours found by
the shared pipeline are cross-checked against actual pixel brightness so
only genuinely fluorescing regions - not just any structural edge - count
as a security feature.

This module contains no OCR or denomination-reading logic; it only answers
"does this ROI show valid UV security features?".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from config import VISION_CONFIG, VisionConfig
from vision import UVValidationError
from vision.preprocess import Preprocessor, PreprocessResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UVValidationResult:
    """
    Outcome of a UV security-feature validation pass over a single ROI.

    ``is_valid`` is the primary business signal, combining both the
    fraction of the ROI that fluoresces and the number of distinct
    fluorescent regions found. The remaining fields expose the underlying
    measurements for logging, debugging, and persisting alongside the
    captured UV image.
    """

    is_valid: bool
    bright_pixel_ratio: float
    mean_brightness: float
    num_bright_regions: int
    bright_regions: List[np.ndarray] = field(default_factory=list)


class UVValidator:
    """
    Analyzes a UV-illuminated banknote ROI for genuine fluorescent security
    features.

    Combines two independent signals, both required to pass for
    ``is_valid`` to be True:

        * **Coverage** - the fraction of ROI pixels whose grayscale
          intensity exceeds ``VisionConfig.UV_BRIGHTNESS_THRESHOLD`` must
          fall within ``[UV_MIN_BRIGHT_PIXEL_RATIO, UV_MAX_BRIGHT_PIXEL_RATIO]``.
          Too little fluorescence means no security thread/print reacted to
          UV light; too much (e.g. a fully fluorescing sheet of plain
          printer paper) is itself a counterfeit indicator.
        * **Region count** - at least ``UV_MIN_BRIGHT_REGIONS`` distinct
          fluorescent blobs must be found via contour analysis of the
          preprocessed binary image, each cross-checked against actual
          grayscale brightness. This rejects a single diffuse glow (e.g.
          from uneven UV LED illumination) that happens to satisfy the
          coverage ratio without forming a real, localized security mark.

    Dependency injection: a :class:`~vision.preprocess.Preprocessor`
    instance can be supplied so this class can be unit tested against a
    fake/stub preprocessor without invoking real OpenCV operations.
    """

    #: Minimum ROI dimension (in pixels, either axis) accepted by
    #: `_validate_roi`. Guards against silently analyzing a degenerate
    #: sliver produced by a bad upstream crop.
    MIN_ROI_DIMENSION_PX: int = 20

    #: Minimum contour area (in pixels) considered for brightness
    #: cross-checking. Filters out single-pixel noise blobs from the
    #: contour list before they're even brightness-tested.
    MIN_CONTOUR_AREA_PX: float = 4.0

    def __init__(
        self,
        config: VisionConfig = VISION_CONFIG,
        preprocessor: Optional[Preprocessor] = None,
    ) -> None:
        """
        Initialize the UV validator.

        Args:
            config: Vision pipeline configuration (UV brightness threshold,
                min/max bright-pixel ratio, minimum bright-region count).
                Defaults to the module-level ``VISION_CONFIG`` singleton
                from ``config.py``.
            preprocessor: Preprocessing pipeline used to binarize the ROI
                before contour detection. Defaults to a new
                :class:`Preprocessor` built from the same ``config``.
        """
        self._config = config
        self._preprocessor = preprocessor if preprocessor is not None else Preprocessor(config)
        logger.debug(
            "UVValidator initialized (brightness_threshold=%s, ratio_range=[%.3f, %.3f], min_regions=%s).",
            config.UV_BRIGHTNESS_THRESHOLD,
            config.UV_MIN_BRIGHT_PIXEL_RATIO,
            config.UV_MAX_BRIGHT_PIXEL_RATIO,
            config.UV_MIN_BRIGHT_REGIONS,
        )

    # --------------------------------------------------------------------
    # Step: ROI validation
    # --------------------------------------------------------------------
    def _validate_roi(self, image: np.ndarray) -> None:
        """
        Validate that ``image`` is a usable, non-degenerate ROI before any
        analysis is performed.

        Args:
            image: The UV-illuminated ROI to validate.

        Raises:
            UVValidationError: If ``image`` is ``None``, empty, or smaller
                than :attr:`MIN_ROI_DIMENSION_PX` on either axis.
        """
        if image is None or image.size == 0:
            raise UVValidationError("Cannot validate UV security features on an empty/None ROI.")

        height, width = image.shape[:2]
        if height < self.MIN_ROI_DIMENSION_PX or width < self.MIN_ROI_DIMENSION_PX:
            raise UVValidationError(
                f"UV ROI is too small to analyze reliably: {width}x{height}px "
                f"(minimum {self.MIN_ROI_DIMENSION_PX}px per side)."
            )

    # --------------------------------------------------------------------
    # Steps 1-4: grayscale / blur / adaptive threshold / morphology
    # --------------------------------------------------------------------
    def _preprocess(self, image: np.ndarray) -> PreprocessResult:
        """
        Run the shared grayscale -> blur -> adaptive-threshold -> morphology
        pipeline on the UV ROI.

        Args:
            image: The UV-illuminated ROI.

        Returns:
            A :class:`~vision.preprocess.PreprocessResult` with every
            intermediate stage.

        Raises:
            UVValidationError: If preprocessing fails.
        """
        try:
            return self._preprocessor.preprocess(image)
        except Exception as exc:  # noqa: BLE001
            raise UVValidationError(f"UV image preprocessing failed: {exc}") from exc

    # --------------------------------------------------------------------
    # Step 5: contour extraction
    # --------------------------------------------------------------------
    def _extract_contours(self, binary_image: np.ndarray) -> List[np.ndarray]:
        """
        Extract candidate security-feature contours from the preprocessed
        binary image, discarding contours below :attr:`MIN_CONTOUR_AREA_PX`.

        Args:
            binary_image: Output of the preprocessing pipeline's morphology
                stage.

        Returns:
            A list of candidate contours (possibly empty).

        Raises:
            UVValidationError: If contour extraction fails.
        """
        import cv2

        try:
            contours, _ = cv2.findContours(binary_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            return [c for c in contours if cv2.contourArea(c) >= self.MIN_CONTOUR_AREA_PX]
        except Exception as exc:  # noqa: BLE001
            raise UVValidationError(f"UV contour extraction failed: {exc}") from exc

    # --------------------------------------------------------------------
    # Step 6: UV brightness analysis
    # --------------------------------------------------------------------
    def _compute_bright_pixel_ratio(self, gray_image: np.ndarray) -> float:
        """
        Compute the fraction of ROI pixels whose grayscale intensity
        exceeds ``VisionConfig.UV_BRIGHTNESS_THRESHOLD`` (i.e. the fraction
        of the note that is genuinely fluorescing under UV light).

        Uses a simple global threshold (independent of the adaptive/
        structural contour pipeline) so the coverage measurement isn't
        biased by edge-detection artifacts - it directly answers "how much
        of this ROI is bright".

        Args:
            gray_image: Grayscale UV ROI.

        Returns:
            The bright-pixel fraction, in ``[0.0, 1.0]``.

        Raises:
            UVValidationError: If the brightness mask cannot be computed.
        """
        import cv2

        try:
            _, bright_mask = cv2.threshold(
                gray_image, self._config.UV_BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY
            )
            bright_pixel_count = int(np.count_nonzero(bright_mask))
            total_pixel_count = int(bright_mask.size)
            if total_pixel_count == 0:
                raise UVValidationError("UV ROI has zero pixels; cannot compute brightness ratio.")
            return bright_pixel_count / total_pixel_count
        except UVValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise UVValidationError(f"UV brightness ratio computation failed: {exc}") from exc

    def _region_mean_brightness(self, gray_image: np.ndarray, contour: np.ndarray) -> float:
        """
        Compute the mean grayscale intensity of the pixels enclosed by a
        single contour.

        Args:
            gray_image: Grayscale UV ROI the contour was found in.
            contour: A single contour, as returned by
                :meth:`_extract_contours`.

        Returns:
            The mean pixel intensity within the contour, in ``[0.0, 255.0]``.

        Raises:
            UVValidationError: If the mean cannot be computed.
        """
        import cv2

        try:
            mask = np.zeros(gray_image.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, color=255, thickness=cv2.FILLED)
            mean_value = cv2.mean(gray_image, mask=mask)[0]
            return float(mean_value)
        except Exception as exc:  # noqa: BLE001
            raise UVValidationError(f"Failed to compute region brightness: {exc}") from exc

    def _filter_bright_regions(
        self, contours: List[np.ndarray], gray_image: np.ndarray
    ) -> List[np.ndarray]:
        """
        Keep only the contours whose mean grayscale brightness exceeds
        ``VisionConfig.UV_BRIGHTNESS_THRESHOLD``.

        This is what distinguishes a genuine fluorescent security mark from
        an ordinary structural edge that the adaptive-threshold/morphology
        pipeline picked up but that isn't actually bright under UV light.

        Args:
            contours: Candidate contours from :meth:`_extract_contours`.
            gray_image: Grayscale UV ROI the contours were found in.

        Returns:
            The subset of ``contours`` that are genuinely bright regions.
        """
        bright_regions = [
            contour for contour in contours
            if self._region_mean_brightness(gray_image, contour) >= self._config.UV_BRIGHTNESS_THRESHOLD
        ]
        return bright_regions

    # --------------------------------------------------------------------
    # Orchestration
    # --------------------------------------------------------------------
    def validate(self, image: np.ndarray) -> UVValidationResult:
        """
        Run the full UV security-feature validation pipeline on a banknote
        ROI captured under UV illumination.

        Args:
            image: The UV-illuminated banknote ROI (typically the output of
                ``vision.roi.ROIExtractor.extract()`` applied to a UV
                frame).

        Returns:
            A :class:`UVValidationResult` describing whether valid UV
            security features were found, along with the underlying
            brightness/region measurements. An ROI with no fluorescent
            features returns ``is_valid=False`` - this is a normal,
            expected outcome and does NOT raise.

        Raises:
            UVValidationError: If the ROI is invalid (``None``, empty, or
                too small) or if any underlying OpenCV operation fails.
        """
        self._validate_roi(image)

        preprocessed = self._preprocess(image)
        contours = self._extract_contours(preprocessed.morphed)
        bright_regions = self._filter_bright_regions(contours, preprocessed.grayscale)

        bright_pixel_ratio = self._compute_bright_pixel_ratio(preprocessed.grayscale)
        mean_brightness = float(np.mean(preprocessed.grayscale))
        num_bright_regions = len(bright_regions)

        ratio_ok = (
            self._config.UV_MIN_BRIGHT_PIXEL_RATIO
            <= bright_pixel_ratio
            <= self._config.UV_MAX_BRIGHT_PIXEL_RATIO
        )
        region_count_ok = num_bright_regions >= self._config.UV_MIN_BRIGHT_REGIONS
        is_valid = ratio_ok and region_count_ok

        logger.info(
            "UV validation: is_valid=%s bright_ratio=%.4f (range=[%.4f, %.4f]) "
            "regions=%s (min=%s) mean_brightness=%.1f",
            is_valid,
            bright_pixel_ratio,
            self._config.UV_MIN_BRIGHT_PIXEL_RATIO,
            self._config.UV_MAX_BRIGHT_PIXEL_RATIO,
            num_bright_regions,
            self._config.UV_MIN_BRIGHT_REGIONS,
            mean_brightness,
        )

        return UVValidationResult(
            is_valid=is_valid,
            bright_pixel_ratio=bright_pixel_ratio,
            mean_brightness=mean_brightness,
            num_bright_regions=num_bright_regions,
            bright_regions=bright_regions,
        )
