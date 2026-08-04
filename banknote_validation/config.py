"""
config.py
=========

Centralized configuration for the Smart Shopping System - Banknote
Validation Module.

This is the SINGLE source of truth for every tunable value in the project:
GPIO pin assignments, camera settings, vision-processing thresholds, OCR
settings, servo angles/timings, denomination definitions, file paths and
logging configuration.

No other module should hardcode a GPIO pin number, a magic threshold value,
or a file path. Everything must be imported from here. This keeps the
system easy to re-tune/re-wire without touching business logic.

All values are grouped into small, purpose-specific dataclasses and exposed
as module-level singleton instances (e.g. ``GPIO_CONFIG``, ``CAMERA_CONFIG``)
so callers can do:

    from config import GPIO_CONFIG, SERVO_CONFIG

Author: Senior CV / Python Architecture Team
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


# ==============================================================================
# BASE PATHS
# ==============================================================================

@dataclass(frozen=True)
class PathsConfig:
    """
    Filesystem locations used by the application.

    All paths are resolved relative to the project root so the application
    can be launched from any working directory (e.g. as a systemd service).
    """

    PROJECT_ROOT: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    RGB_IMAGE_DIR: Path = DATA_DIR / "rgb"
    UV_IMAGE_DIR: Path = DATA_DIR / "uv"
    DEBUG_IMAGE_DIR: Path = DATA_DIR / "debug"
    LOG_DIR: Path = PROJECT_ROOT / "logs"
    LOG_FILE: Path = LOG_DIR / "banknote_validation.log"

    # Manually-captured, per-denomination reference images
    # (reference_data/<denomination>/white.jpg, reference_data/<denomination>/uv.jpg)
    # used by vision.reference_matcher for genuine-note feature comparison.
    REFERENCE_DATA_DIR: Path = PROJECT_ROOT / "reference_data"

    def ensure_directories(self) -> None:
        """
        Create all required directories if they do not already exist.

        This is called once at application startup so downstream modules
        (camera capture, debug image dumping, logging) never have to worry
        about missing folders.

        Note: the per-denomination subfolders under ``REFERENCE_DATA_DIR``
        (and the ``white.jpg``/``uv.jpg`` files inside them) are NOT
        created here - those must be manually captured and placed ahead of
        time; only the top-level ``REFERENCE_DATA_DIR`` is guaranteed to
        exist.
        """
        for directory in (
            self.DATA_DIR,
            self.RGB_IMAGE_DIR,
            self.UV_IMAGE_DIR,
            self.DEBUG_IMAGE_DIR,
            self.LOG_DIR,
            self.REFERENCE_DATA_DIR,
        ):
            directory.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# GPIO PIN MAP (BCM numbering) — the ONLY place pin numbers may be defined
# ==============================================================================

@dataclass(frozen=True)
class GPIOConfig:
    """
    BCM GPIO pin assignments for every peripheral on the Raspberry Pi 5.

    Change wiring here ONLY. Hardware wrapper classes (hardware/*.py) must
    read pin numbers exclusively from this dataclass - never hardcode a pin
    number inside a driver class.
    """

    IR_SENSOR_PIN: int = 17          # Digital IR obstacle/insertion sensor (input)
    SERVO_PIN: int = 18              # MG996R servo signal (hardware PWM capable pin)
    WHITE_LED_PIN: int = 22          # White LED array (illumination for RGB capture)
    UV_LED_PIN: int = 23             # UV LED array (illumination for UV capture)

    # gpiozero pin factory to use. "lgpio" is the recommended factory on
    # Raspberry Pi 5 (replaces the legacy RPi.GPIO / pigpio sysfs approach).
    PIN_FACTORY: str = "lgpio"


# ==============================================================================
# CAMERA / IMAGE CAPTURE
# ==============================================================================

@dataclass(frozen=True)
class CameraConfig:
    """Configuration for the USB webcam used to capture RGB and UV images."""

    DEVICE_INDEX: int = 0            # /dev/video0
    FRAME_WIDTH: int = 1920
    FRAME_HEIGHT: int = 1080
    WARMUP_FRAMES: int = 5           # frames to discard while auto-exposure settles
    CAPTURE_RETRIES: int = 3         # number of retry attempts on capture failure
    CAPTURE_TIMEOUT_SEC: float = 3.0
    AUTO_EXPOSURE: bool = True
    JPEG_QUALITY: int = 95           # used when persisting captured frames to disk

    # On Linux/Raspberry Pi OS, explicitly requesting the V4L2 backend avoids
    # OpenCV's slower auto-probing of multiple backends and is the correct
    # backend for a USB webcam on this platform.
    USE_V4L2_BACKEND: bool = True


# ==============================================================================
# IR SENSOR
# ==============================================================================

@dataclass(frozen=True)
class IRSensorConfig:
    """Configuration for the IR banknote-presence sensor."""

    # Most IR obstacle sensors pull the line LOW when an object is detected.
    ACTIVE_STATE_LOW: bool = True
    DEBOUNCE_TIME_SEC: float = 0.05
    POLL_INTERVAL_SEC: float = 0.1
    DETECTION_HOLD_SEC: float = 0.3  # object must be present continuously this long


# ==============================================================================
# SERVO (MG996R) — dispenser / accept-reject gate
# ==============================================================================

@dataclass(frozen=True)
class ServoConfig:
    """
    Configuration for the MG996R servo that physically accepts/rejects the
    banknote.

    Angle convention:
        0°   -> neutral / resting position
        +45° -> "accept" (REAL banknote) swing
        -45° -> "reject" (FAKE banknote) swing
    """

    MIN_PULSE_WIDTH_SEC: float = 0.0005   # 0.5 ms
    MAX_PULSE_WIDTH_SEC: float = 0.0025   # 2.5 ms
    FRAME_WIDTH_SEC: float = 0.020        # 20 ms (50 Hz)

    NEUTRAL_ANGLE_DEG: float = 0.0
    ACCEPT_ANGLE_DEG: float = 45.0
    REJECT_ANGLE_DEG: float = -45.0

    # "Shake" performed after a FAKE verdict to physically dislodge the note.
    SHAKE_POSITIVE_ANGLE_DEG: float = 2.0
    SHAKE_NEGATIVE_ANGLE_DEG: float = -2.0
    SHAKE_CYCLES: int = 3
    SHAKE_STEP_DELAY_SEC: float = 0.15

    HOLD_AT_TARGET_SEC: float = 2.0       # dwell time at +45/-45 before returning
    MOVE_SETTLE_SEC: float = 0.3          # delay to let the servo physically reach position


# ==============================================================================
# LIGHTING (White LED + UV LED)
# ==============================================================================

@dataclass(frozen=True)
class LightingConfig:
    """Timing configuration for the illumination stages of the pipeline."""

    WHITE_LED_WARMUP_SEC: float = 0.3
    UV_LED_WARMUP_SEC: float = 0.5
    LED_COOLDOWN_SEC: float = 0.1


# ==============================================================================
# VISION / IMAGE PROCESSING
# ==============================================================================

@dataclass(frozen=True)
class VisionConfig:
    """
    Parameters for the OpenCV preprocessing and analysis pipeline applied to
    both the RGB (paper detection) and UV (security-feature) images.
    """

    # --- Gaussian blur ---
    # Larger kernel smooths out the sensor-grain noise typical of low-light
    # UV captures BEFORE thresholding, which is the main source of the
    # "salt-and-pepper" white dots seen in the binarized output.
    GAUSSIAN_KERNEL_SIZE: tuple[int, int] = (9, 9)
    GAUSSIAN_SIGMA_X: float = 0.0

    # --- Adaptive threshold ---
    # Bigger block size -> each pixel is compared against a wider local
    # neighborhood average, so it's less sensitive to a single noisy pixel.
    # Bigger C -> raises the cutoff a note's local mean must exceed before
    # being called "bright", which suppresses weak/noisy false positives.
    ADAPTIVE_THRESH_BLOCK_SIZE: int = 51   # must be odd
    ADAPTIVE_THRESH_C: int = 15
    ADAPTIVE_THRESH_MAX_VALUE: int = 255

    # --- Morphology ---
    # MORPH_KERNEL_SIZE / MORPH_ITERATIONS below are used for the existing
    # closing operation (fills small gaps in real features).
    MORPH_KERNEL_SIZE: tuple[int, int] = (5, 5)
    MORPH_ITERATIONS: int = 2

    # NEW: opening operation (erosion -> dilation), applied BEFORE closing.
    # This is what actually removes small isolated white speckles/dots,
    # since erosion wipes out anything smaller than the kernel and dilation
    # then restores the size of whatever survived (the real "50" text).
    # Kept moderate deliberately: this feeds BOTH the debug visualization
    # AND the real UVValidator accept/reject decision. (5,5)x2 iterations
    # was tried and completely erased thin genuine security features
    # (security thread, digit strokes) before contour extraction, causing
    # UV_MIN_BRIGHT_REGIONS to never be met -> false REJECTED verdicts.
    # Rely on MIN_NOISE_BLOB_AREA_PX (post-contour area filtering) as the
    # primary noise defense instead of an aggressive opening here.
    MORPH_OPEN_KERNEL_SIZE: tuple[int, int] = (3, 3)
    MORPH_OPEN_ITERATIONS: int = 1

    # NEW: after finding contours/blobs in the binary image, drop anything
    # smaller than this area (in pixels). Cleans up any speckles that
    # survive the morphological opening step above.
    MIN_NOISE_BLOB_AREA_PX: int = 20

    # --- UV top-hat debug visualization (main.py) ---
    # Structuring-element size for the top-hat filter used to isolate
    # locally-bright UV features (digits/security thread) from an evenly
    # overexposed note surface. Must be bigger than a digit's stroke width
    # but smaller than the note itself. Too small -> background survives
    # too (this was the noise source); too big -> real features get
    # cancelled out too. Start around 20-30px and adjust by eye.
    UV_TOPHAT_KERNEL_SIZE: int = 25

    # Manual bias added ON TOP OF the automatically-computed Otsu cutoff
    # before thresholding the top-hat result. Otsu alone often sits too
    # low, letting faint local-contrast bumps (residual noise, paper
    # texture) count as "bright". Raising this offset pushes the cutoff
    # higher so only genuinely strong fluorescent features survive.
    # Increase in small steps (5-10 at a time) and re-check the debug
    # image; too high will start eating real security-feature pixels too
    # (this happened at 15 - dropped back down here).
    UV_TOPHAT_THRESHOLD_OFFSET: int = 8

    # Gaussian blur kernel applied ONLY before the top-hat debug
    # visualization (not the shared VISION_CONFIG.GAUSSIAN_KERNEL_SIZE
    # used by the actual accept/reject pipeline in UVValidator). Kept
    # separate so smoothing out noise for the *debug image* never risks
    # softening the features the real decision is based on. Top-hat is a
    # local-contrast operator, so noise suppression matters more here than
    # in the main pipeline - hence a larger kernel than GAUSSIAN_KERNEL_SIZE.
    UV_TOPHAT_PRE_BLUR_KERNEL_SIZE: tuple[int, int] = (15, 15)

    # Morphological-opening kernel/iterations used to clean the top-hat
    # DEBUG mask ONLY - deliberately kept separate from
    # MORPH_OPEN_KERNEL_SIZE/MORPH_OPEN_ITERATIONS above (which feed the
    # real UVValidator accept/reject decision). This one can be tuned as
    # aggressively as needed purely for a cleaner-looking debug image
    # without ever risking erasing genuine security features from the
    # actual pipeline's contour detection again.
    UV_TOPHAT_MASK_OPEN_KERNEL_SIZE: tuple[int, int] = (5, 5)
    UV_TOPHAT_MASK_OPEN_ITERATIONS: int = 2

    # --- Contour / paper-shape detection ---
    MIN_CONTOUR_AREA_RATIO: float = 0.15   # min area (as ratio of frame area) to be "paper"
    MAX_CONTOUR_AREA_RATIO: float = 0.95
    APPROX_POLY_EPSILON_RATIO: float = 0.02
    MIN_ASPECT_RATIO: float = 1.6          # banknotes are elongated rectangles
    MAX_ASPECT_RATIO: float = 3.2

    # --- ROI extraction ---
    ROI_PADDING_PX: int = 10

    # --- UV brightness / security-thread analysis ---
    UV_BRIGHTNESS_THRESHOLD: int = 200      # pixel intensity considered "fluorescent"
    UV_MIN_BRIGHT_PIXEL_RATIO: float = 0.006  # min fraction of ROI that must fluoresce
    UV_MAX_BRIGHT_PIXEL_RATIO: float = 0.60
    UV_MIN_BRIGHT_REGIONS: int = 1          # min distinct fluorescent blobs expected


# ==============================================================================
# REFERENCE-IMAGE FEATURE COMPARISON
# ==============================================================================

@dataclass(frozen=True)
class ReferenceMatchConfig:
    """
    Parameters for comparing OpenCV contour-based features extracted from a
    captured banknote (white + UV) against the manually-captured reference
    images for its OCR-recognized denomination (``reference_data/<value>/``).

    No machine learning is involved: this purely governs classic
    contour/geometry/intensity comparison tolerances in
    ``vision.reference_matcher``.
    """

    # Reference image filenames expected inside each reference_data/<value>/ folder.
    WHITE_IMAGE_FILENAME: str = "white.jpg"
    UV_IMAGE_FILENAME: str = "uv.jpg"

    # Max allowed difference in total contour count between captured and reference.
    CONTOUR_COUNT_TOLERANCE: int = 3

    # Max allowed distance (pixels) between a reference contour's center and
    # a captured contour's center for them to be considered the same feature.
    POSITION_TOLERANCE_PX: float = 25.0

    # Max allowed relative difference in contour area (|ref-cap| / ref) for
    # two matched contours to still count as a match.
    AREA_TOLERANCE_RATIO: float = 0.30

    # Max allowed difference in mean grayscale intensity (0-255) between
    # captured and reference images.
    INTENSITY_TOLERANCE: float = 25.0

    # Minimum combined similarity score (0.0-1.0) required to consider the
    # captured note a match for its reference.
    MIN_SIMILARITY_SCORE: float = 0.6


# ==============================================================================
# OCR
# ==============================================================================

@dataclass(frozen=True)
class OCRConfig:
    """Configuration for the EasyOCR-based denomination reader."""

    LANGUAGES: tuple[str, ...] = ("en",)
    USE_GPU: bool = False                  # Raspberry Pi 5 has no CUDA GPU
    MIN_CONFIDENCE: float = 0.45
    ALLOWLIST: str = "0123456789NISnis"    # restrict recognized character set
    DETAIL: int = 1                        # 1 = return boxes + text + confidence

    # EasyOCR inference time scales with pixel count and runs on CPU only on
    # Raspberry Pi 5 (USE_GPU=False above). ROIs wider than this are
    # downscaled (aspect-ratio preserved) before recognition; denomination
    # digits remain easily legible well below this width. Set to 0 to
    # disable downscaling entirely.
    MAX_IMAGE_WIDTH: int = 800


# ==============================================================================
# DENOMINATIONS (business domain data)
# ==============================================================================

@dataclass(frozen=True)
class Denomination:
    """A single supported banknote denomination."""

    value: int
    currency_code: str = "NIS"
    ocr_tokens: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DenominationConfig:
    """Registry of all denominations supported by the system."""

    SUPPORTED: tuple[Denomination, ...] = (
        Denomination(10, "NIS", ("10",)),
        Denomination(20, "NIS", ("20",)),
        Denomination(50, "NIS", ("50",)),
        Denomination(100, "NIS", ("100",)),
        Denomination(200, "NIS", ("200",)),
    )

    def values(self) -> tuple[int, ...]:
        """Return the numeric values of all supported denominations."""
        return tuple(d.value for d in self.SUPPORTED)


# ==============================================================================
# VALIDATION LOGIC
# ==============================================================================

@dataclass(frozen=True)
class ValidationConfig:
    """High-level thresholds governing the REAL vs FAKE decision."""

    REQUIRE_UV_FEATURES: bool = True
    REQUIRE_OCR_MATCH: bool = True
    # Whether the note must also match its denomination's reference images
    # (reference_data/<value>/white.jpg + uv.jpg) to be accepted as REAL.
    REQUIRE_REFERENCE_MATCH: bool = True
    MAX_PIPELINE_RETRIES: int = 1   # retry the whole capture/validate cycle on failure


# ==============================================================================
# LOGGING
# ==============================================================================

@dataclass(frozen=True)
class LoggingConfig:
    """Application-wide logging configuration."""

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    MAX_BYTES: int = 5 * 1024 * 1024   # 5 MB per log file before rotation
    BACKUP_COUNT: int = 5
    LOG_TO_CONSOLE: bool = True


# ==============================================================================
# MODULE-LEVEL SINGLETONS
# ==============================================================================
# Import these instances elsewhere, e.g.:
#     from config import GPIO_CONFIG, SERVO_CONFIG, VISION_CONFIG
# ==============================================================================

PATHS: Final[PathsConfig] = PathsConfig()
GPIO_CONFIG: Final[GPIOConfig] = GPIOConfig()
CAMERA_CONFIG: Final[CameraConfig] = CameraConfig()
IR_SENSOR_CONFIG: Final[IRSensorConfig] = IRSensorConfig()
SERVO_CONFIG: Final[ServoConfig] = ServoConfig()
LIGHTING_CONFIG: Final[LightingConfig] = LightingConfig()
VISION_CONFIG: Final[VisionConfig] = VisionConfig()
REFERENCE_MATCH_CONFIG: Final[ReferenceMatchConfig] = ReferenceMatchConfig()
OCR_CONFIG: Final[OCRConfig] = OCRConfig()
DENOMINATION_CONFIG: Final[DenominationConfig] = DenominationConfig()
VALIDATION_CONFIG: Final[ValidationConfig] = ValidationConfig()
LOGGING_CONFIG: Final[LoggingConfig] = LoggingConfig()

# Ensure runtime directories exist as soon as configuration is imported.
PATHS.ensure_directories()