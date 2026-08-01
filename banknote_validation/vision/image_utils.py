"""
vision/image_utils.py
======================

General-purpose OpenCV/NumPy image helpers shared across the vision
package: color-space conversion, geometry (point ordering, perspective
transform, aspect ratio), debug drawing, and persistence.

Kept deliberately free of any single pipeline stage's business logic so
``preprocess.py``, ``paper_detector.py``, ``roi.py`` and (later)
``uv_validator.py`` can all reuse it without depending on each other
(avoids duplicated code across the package).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import numpy as np

from vision import VisionError

logger = logging.getLogger(__name__)


class ImageUtils:
    """
    Stateless collection of reusable OpenCV/NumPy image helpers.

    Implemented as static methods on a class - rather than bare module-level
    functions - to give these cross-cutting helpers a single, discoverable
    namespace (``ImageUtils.foo(...)``) consistent with the OOP style used
    throughout the rest of the project.
    """

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """
        Convert a BGR image to single-channel grayscale.

        Args:
            image: A BGR ``numpy.ndarray`` frame, or an already-grayscale
                (2-D) array (returned unchanged in that case).

        Returns:
            A single-channel grayscale image.

        Raises:
            VisionError: If ``image`` is ``None`` or the conversion fails.
        """
        import cv2

        if image is None:
            raise VisionError("Cannot convert a None image to grayscale.")
        try:
            if len(image.shape) == 2:
                return image
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to convert image to grayscale: {exc}") from exc

    @staticmethod
    def resize_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
        """
        Resize an image to an exact target size using area interpolation
        (best quality for shrinking, the common case in this pipeline).

        Args:
            image: Source image.
            width: Target width in pixels.
            height: Target height in pixels.

        Returns:
            The resized image.

        Raises:
            VisionError: If resizing fails.
        """
        import cv2

        try:
            return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to resize image to {width}x{height}: {exc}") from exc

    @staticmethod
    def frame_area(image: np.ndarray) -> int:
        """
        Return the total pixel area (``width * height``) of an image frame.

        Args:
            image: Source image.

        Returns:
            The frame area in pixels.

        Raises:
            VisionError: If ``image`` is ``None`` or malformed.
        """
        if image is None:
            raise VisionError("Cannot compute frame area of a None image.")
        try:
            height, width = image.shape[:2]
            return int(width * height)
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to compute frame area: {exc}") from exc

    @staticmethod
    def compute_aspect_ratio(width: float, height: float) -> float:
        """
        Compute a normalized, orientation-independent aspect ratio.

        Always returns ``long_side / short_side`` (i.e. >= 1.0) so callers
        don't need to special-case whether a rectangle is in landscape or
        portrait orientation.

        Args:
            width: Rectangle width.
            height: Rectangle height.

        Returns:
            The aspect ratio as a float >= 1.0.

        Raises:
            VisionError: If either dimension is non-positive.
        """
        if width <= 0 or height <= 0:
            raise VisionError(
                f"Cannot compute aspect ratio for non-positive dimensions: {width}x{height}."
            )
        long_side = max(width, height)
        short_side = min(width, height)
        return float(long_side / short_side)

    @staticmethod
    def order_points(points: np.ndarray) -> np.ndarray:
        """
        Order 4 arbitrary (x, y) corner points as
        ``[top-left, top-right, bottom-right, bottom-left]``.

        Required for a geometrically stable perspective transform,
        regardless of the order OpenCV's contour/polygon approximation
        happened to return the points in.

        Args:
            points: A ``(4, 1, 2)`` or ``(4, 2)`` array of corner points
                (e.g. as returned by ``cv2.approxPolyDP``).

        Returns:
            A ``(4, 2)`` float32 array ordered
            ``[top-left, top-right, bottom-right, bottom-left]``.

        Raises:
            VisionError: If ``points`` does not contain exactly 4 points.
        """
        try:
            pts = points.reshape(4, 2).astype("float32")
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Expected exactly 4 corner points: {exc}") from exc

        try:
            ordered = np.zeros((4, 2), dtype="float32")

            sum_coords = pts.sum(axis=1)
            ordered[0] = pts[np.argmin(sum_coords)]   # top-left: smallest x+y
            ordered[2] = pts[np.argmax(sum_coords)]   # bottom-right: largest x+y

            diff_coords = np.diff(pts, axis=1).reshape(-1)
            ordered[1] = pts[np.argmin(diff_coords)]  # top-right: smallest (y-x)
            ordered[3] = pts[np.argmax(diff_coords)]  # bottom-left: largest (y-x)

            return ordered
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to order quadrilateral points: {exc}") from exc

    @staticmethod
    def four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
        """
        Apply a perspective ("bird's-eye view") warp so a skewed/rotated
        quadrilateral region of ``image`` is mapped onto an upright,
        undistorted rectangle.

        Args:
            image: Source frame containing the region to warp.
            points: 4 (x, y) corner points bounding the region, in any
                order (they are re-ordered internally via
                :meth:`order_points`).

        Returns:
            The perspective-warped region as a new image.

        Raises:
            VisionError: If the transform cannot be computed or applied.
        """
        import cv2

        ordered = ImageUtils.order_points(points)
        top_left, top_right, bottom_right, bottom_left = ordered

        try:
            width_a = np.linalg.norm(bottom_right - bottom_left)
            width_b = np.linalg.norm(top_right - top_left)
            max_width = max(int(width_a), int(width_b))

            height_a = np.linalg.norm(top_right - bottom_right)
            height_b = np.linalg.norm(top_left - bottom_left)
            max_height = max(int(height_a), int(height_b))

            if max_width <= 0 or max_height <= 0:
                raise VisionError(
                    f"Computed a zero-area warp target ({max_width}x{max_height}) "
                    "from the given quadrilateral points."
                )

            destination = np.array(
                [
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1],
                ],
                dtype="float32",
            )

            transform_matrix = cv2.getPerspectiveTransform(ordered, destination)
            warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))
            return warped
        except VisionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to apply perspective transform: {exc}") from exc

    @staticmethod
    def draw_contour_overlay(
        image: np.ndarray,
        contour: np.ndarray,
        color_bgr: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 3,
    ) -> np.ndarray:
        """
        Draw a contour on a copy of ``image`` for debug visualization.

        Args:
            image: Source image (left untouched; a copy is drawn on).
            contour: Contour/points to draw, as returned by
                ``cv2.findContours``.
            color_bgr: BGR draw color. Defaults to green.
            thickness: Line thickness in pixels.

        Returns:
            A new image with the contour overlaid.

        Raises:
            VisionError: If drawing fails.
        """
        import cv2

        try:
            overlay = image.copy()
            cv2.drawContours(overlay, [contour], -1, color_bgr, thickness)
            return overlay
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to draw contour overlay: {exc}") from exc

    @staticmethod
    def save_image(image: np.ndarray, path: Path, jpeg_quality: int = 95) -> Path:
        """
        Persist an image to disk as a JPEG file, creating parent
        directories as needed. Primarily used to dump debug images from
        each pipeline stage into ``data/debug/``.

        Args:
            image: Image to save.
            path: Destination file path.
            jpeg_quality: JPEG quality (0-100).

        Returns:
            The path the image was written to.

        Raises:
            VisionError: If the image cannot be written to disk.
        """
        import cv2

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            success = cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            if not success:
                raise VisionError(f"cv2.imwrite reported failure writing to {path}.")
            logger.debug("Image saved to %s", path)
            return path
        except VisionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VisionError(f"Failed to save image to {path}: {exc}") from exc
