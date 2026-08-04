"""
vision/reference_matcher.py
============================

Denomination reference-image comparison.

Given the denomination recognized by OCR, this module loads the
manually-captured reference images from ``reference_data/<value>/``,
runs BOTH the captured note and the reference note through the exact
same preprocessing pipeline already used elsewhere in the project
(``vision.preprocess.Preprocessor``), extracts simple OpenCV contour-based
features from each, and compares them.

No machine learning of any kind is used - every feature (contours,
contour area, bounding rectangles, contour centers, mean intensity,
contour count) and every comparison (position/area/intensity/count
tolerances) is computed with plain OpenCV/NumPy.

Public API (used by ``services.validator.BanknoteValidator``):

    load_reference_image(denomination, image_type)
    compare_reference_with_capture(captured_white, captured_uv, denomination)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from config import (
    PATHS,
    REFERENCE_MATCH_CONFIG,
    VISION_CONFIG,
    PathsConfig,
    ReferenceMatchConfig,
    VisionConfig,
)
from vision import ReferenceMatchError
from vision.preprocess import Preprocessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContourFeature:
    """A single extracted contour's geometry."""

    area: float
    bounding_rect: Tuple[int, int, int, int]  # (x, y, w, h)
    center: Tuple[float, float]               # (cx, cy)


@dataclass(frozen=True)
class ImageFeatureSet:
    """Every feature extracted from one preprocessed image."""

    contour_count: int
    contours: List[ContourFeature] = field(default_factory=list)
    mean_intensity: float = 0.0


@dataclass(frozen=True)
class FeatureComparisonResult:
    """Outcome of comparing one captured/reference feature-set pair (white or UV)."""

    similarity_score: float
    matched_count: int
    unmatched_count: int
    contour_count_match: bool
    intensity_match: bool


@dataclass(frozen=True)
class ReferenceComparisonResult:
    """
    Combined outcome (white + UV) of comparing a captured banknote against
    its denomination's reference images.
    """

    denomination: int
    similarity_score: float
    is_authentic: bool
    matched_features_count: int
    unmatched_features_count: int
    white_comparison: FeatureComparisonResult
    uv_comparison: FeatureComparisonResult


# --------------------------------------------------------------------------
# Internal: feature extraction / comparison
# (supporting logic for the two public helper functions below)
# --------------------------------------------------------------------------
def _extract_features(image: np.ndarray, preprocessor: Preprocessor) -> ImageFeatureSet:
    """
    Run the shared preprocessing pipeline on ``image`` and extract
    contour-based features (contours, contour area, bounding rectangles,
    contour centers, mean intensity, contour count) using OpenCV only.

    Args:
        image: A raw BGR image (captured frame or reference image).
        preprocessor: The exact same ``vision.preprocess.Preprocessor``
            pipeline instance already used elsewhere in the project.

    Returns:
        An :class:`ImageFeatureSet`.

    Raises:
        ReferenceMatchError: If ``image`` is empty/None or extraction fails.
    """
    import cv2

    if image is None or image.size == 0:
        raise ReferenceMatchError("Cannot extract features from an empty/None image.")

    try:
        preprocessed = preprocessor.preprocess(image)
        contours, _ = cv2.findContours(preprocessed.morphed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        features: List[ContourFeature] = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area <= 0:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                cx = moments["m10"] / moments["m00"]
                cy = moments["m01"] / moments["m00"]
            else:
                cx, cy = float(x + w / 2.0), float(y + h / 2.0)
            features.append(ContourFeature(area=area, bounding_rect=(x, y, w, h), center=(cx, cy)))

        mean_intensity = float(np.mean(preprocessed.grayscale))

        return ImageFeatureSet(contour_count=len(features), contours=features, mean_intensity=mean_intensity)
    except ReferenceMatchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ReferenceMatchError(f"Feature extraction failed: {exc}") from exc


def _compare_features(
    captured: ImageFeatureSet,
    reference: ImageFeatureSet,
    config: ReferenceMatchConfig,
) -> FeatureComparisonResult:
    """
    Compare a captured feature-set against a reference feature-set:
    number of contours, contour positions, contour sizes, and contour
    intensity - each within a configurable tolerance from
    :class:`~config.ReferenceMatchConfig`.

    Args:
        captured: Features extracted from the captured (preprocessed) image.
        reference: Features extracted from the reference (preprocessed) image.
        config: Tolerances governing the comparison.

    Returns:
        A :class:`FeatureComparisonResult` with a ``similarity_score`` in
        ``[0.0, 1.0]`` and matched/unmatched contour counts.
    """
    count_diff = abs(captured.contour_count - reference.contour_count)
    contour_count_match = count_diff <= config.CONTOUR_COUNT_TOLERANCE

    intensity_diff = abs(captured.mean_intensity - reference.mean_intensity)
    intensity_match = intensity_diff <= config.INTENSITY_TOLERANCE

    # Greedy nearest-neighbor matching: each reference contour is paired
    # with the closest not-yet-used captured contour whose position and
    # area both fall within the configured tolerances.
    remaining_captured = list(captured.contours)
    matched_count = 0
    for ref_contour in reference.contours:
        best_index: Optional[int] = None
        best_distance: Optional[float] = None

        for index, cap_contour in enumerate(remaining_captured):
            dx = ref_contour.center[0] - cap_contour.center[0]
            dy = ref_contour.center[1] - cap_contour.center[1]
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > config.POSITION_TOLERANCE_PX:
                continue

            if ref_contour.area <= 0:
                continue
            area_diff_ratio = abs(ref_contour.area - cap_contour.area) / ref_contour.area
            if area_diff_ratio > config.AREA_TOLERANCE_RATIO:
                continue

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = index

        if best_index is not None:
            matched_count += 1
            remaining_captured.pop(best_index)

    unmatched_count = reference.contour_count - matched_count
    total_reference = max(reference.contour_count, 1)

    contour_score = matched_count / total_reference
    count_score = 1.0 if contour_count_match else 0.0
    intensity_score = 1.0 if intensity_match else 0.0

    # Weighted blend: contour matching dominates, count/intensity refine it.
    similarity_score = (contour_score * 0.6) + (count_score * 0.2) + (intensity_score * 0.2)

    return FeatureComparisonResult(
        similarity_score=similarity_score,
        matched_count=matched_count,
        unmatched_count=unmatched_count,
        contour_count_match=contour_count_match,
        intensity_match=intensity_match,
    )


# --------------------------------------------------------------------------
# Public helper functions (integrated into services.validator.BanknoteValidator)
# --------------------------------------------------------------------------
def load_reference_image(
    denomination: int,
    image_type: str,
    paths: PathsConfig = PATHS,
    reference_config: ReferenceMatchConfig = REFERENCE_MATCH_CONFIG,
) -> np.ndarray:
    """
    Load the manually-captured reference image for a denomination.

    Args:
        denomination: Recognized denomination (e.g. 20, 50, 100, 200) -
            must match a ``reference_data/<denomination>/`` folder.
        image_type: Either ``"white"`` or ``"uv"``.
        paths: Filesystem locations. Defaults to the module-level ``PATHS``
            singleton from ``config.py``.
        reference_config: Reference-matching configuration (filenames).
            Defaults to the module-level ``REFERENCE_MATCH_CONFIG``
            singleton from ``config.py``.

    Returns:
        The loaded reference image as a BGR ``numpy.ndarray``.

    Raises:
        ReferenceMatchError: If ``image_type`` is invalid, the reference
            file does not exist, or it cannot be read.
    """
    import cv2

    if image_type not in ("white", "uv"):
        raise ReferenceMatchError(f"Unknown reference image_type: {image_type!r} (expected 'white' or 'uv').")

    filename = reference_config.WHITE_IMAGE_FILENAME if image_type == "white" else reference_config.UV_IMAGE_FILENAME
    path = paths.REFERENCE_DATA_DIR / str(denomination) / filename

    if not path.exists():
        raise ReferenceMatchError(
            f"Reference image not found for denomination {denomination}: {path}. "
            "Capture and place the reference images (see reference_data/<value>/README.txt) "
            "before validating this denomination."
        )

    image = cv2.imread(str(path))
    if image is None or image.size == 0:
        raise ReferenceMatchError(f"Failed to load reference image at {path}.")

    logger.debug("Loaded reference %s image for denomination %s from %s.", image_type, denomination, path)
    return image


def compare_reference_with_capture(
    captured_white: np.ndarray,
    captured_uv: np.ndarray,
    denomination: int,
    preprocessor: Optional[Preprocessor] = None,
    vision_config: VisionConfig = VISION_CONFIG,
    reference_config: ReferenceMatchConfig = REFERENCE_MATCH_CONFIG,
    paths: PathsConfig = PATHS,
) -> ReferenceComparisonResult:
    """
    Load the denomination's reference images and compare them against the
    captured banknote.

    Both the captured images and the reference images are passed through
    the exact same ``vision.preprocess.Preprocessor`` pipeline already
    used throughout the project before any feature is extracted, so the
    comparison never operates on raw pixels.

    Args:
        captured_white: Captured banknote ROI under white-LED illumination.
        captured_uv: Captured banknote ROI under UV illumination.
        denomination: OCR-recognized denomination used to locate
            ``reference_data/<denomination>/``.
        preprocessor: Shared preprocessing pipeline instance to reuse
            (recommended, to match ``BanknoteValidator``'s existing
            pipeline exactly). Defaults to a new ``Preprocessor`` built
            from ``vision_config`` if omitted.
        vision_config: Preprocessing configuration, only used if
            ``preprocessor`` is not supplied. Defaults to the module-level
            ``VISION_CONFIG`` singleton from ``config.py``.
        reference_config: Comparison tolerances. Defaults to the
            module-level ``REFERENCE_MATCH_CONFIG`` singleton from
            ``config.py``.
        paths: Filesystem locations. Defaults to the module-level
            ``PATHS`` singleton from ``config.py``.

    Returns:
        A :class:`ReferenceComparisonResult` with a combined similarity
        score, an authenticity flag, and matched/unmatched feature counts.

    Raises:
        ReferenceMatchError: If either captured image is empty/None, the
            reference images cannot be loaded, or feature
            extraction/comparison fails.
    """
    if captured_white is None or captured_white.size == 0:
        raise ReferenceMatchError("compare_reference_with_capture() requires a non-empty captured_white image.")
    if captured_uv is None or captured_uv.size == 0:
        raise ReferenceMatchError("compare_reference_with_capture() requires a non-empty captured_uv image.")

    active_preprocessor = preprocessor if preprocessor is not None else Preprocessor(vision_config)

    reference_white = load_reference_image(denomination, "white", paths, reference_config)
    reference_uv = load_reference_image(denomination, "uv", paths, reference_config)

    captured_white_features = _extract_features(captured_white, active_preprocessor)
    reference_white_features = _extract_features(reference_white, active_preprocessor)
    captured_uv_features = _extract_features(captured_uv, active_preprocessor)
    reference_uv_features = _extract_features(reference_uv, active_preprocessor)

    white_comparison = _compare_features(captured_white_features, reference_white_features, reference_config)
    uv_comparison = _compare_features(captured_uv_features, reference_uv_features, reference_config)

    similarity_score = (white_comparison.similarity_score + uv_comparison.similarity_score) / 2.0
    matched_features_count = white_comparison.matched_count + uv_comparison.matched_count
    unmatched_features_count = white_comparison.unmatched_count + uv_comparison.unmatched_count
    is_authentic = similarity_score >= reference_config.MIN_SIMILARITY_SCORE

    logger.info(
        "Reference comparison: denomination=%s similarity=%.3f authentic=%s matched=%s unmatched=%s",
        denomination, similarity_score, is_authentic, matched_features_count, unmatched_features_count,
    )

    return ReferenceComparisonResult(
        denomination=denomination,
        similarity_score=similarity_score,
        is_authentic=is_authentic,
        matched_features_count=matched_features_count,
        unmatched_features_count=unmatched_features_count,
        white_comparison=white_comparison,
        uv_comparison=uv_comparison,
    )