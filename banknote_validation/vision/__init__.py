"""
vision
======

Computer-vision package for the Smart Shopping System - Banknote
Validation Module.

Contains the OpenCV-based image processing pipeline: generic image
utilities, the grayscale/blur/threshold/morphology preprocessing pipeline,
paper-shape detection (workflow step 4), region-of-interest extraction, and
UV security-feature validation (workflow step 8), the latter reusing the
same grayscale/blur/threshold/morphology preprocessing pipeline.

This ``__init__.py`` defines the shared exception hierarchy so every stage
of the pipeline raises a specific, catchable error type instead of letting
raw OpenCV/NumPy exceptions leak into the controller layer - mirroring the
pattern used in the ``hardware`` package.
"""

from __future__ import annotations


class VisionError(Exception):
    """Base exception for every failure originating in the vision package."""


class PreprocessError(VisionError):
    """Raised when an image preprocessing stage (blur/threshold/morphology) fails."""


class PaperDetectionError(VisionError):
    """Raised when paper-shape contour detection fails due to invalid input or an OpenCV error."""


class ROIExtractionError(VisionError):
    """Raised when a region-of-interest cannot be cropped or perspective-corrected."""


class UVValidationError(VisionError):
    """Raised when UV security-feature analysis fails due to invalid input or an OpenCV error."""


class ReferenceMatchError(VisionError):
    """
    Raised when denomination reference-image comparison fails: the
    reference image for a denomination is missing/unreadable, or feature
    extraction/comparison against it fails due to invalid input or an
    OpenCV error.
    """
