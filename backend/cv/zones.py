"""
cv/zones.py
===========
هندسة المنطقتين (Two-Zone geometry) للكاميرا المثبَّتة على العربة.

Zone 1 ("scan") : أعلى نسبة config.ZONE_BOUNDARY من الإطار
Zone 2 ("cart")  : الباقي

التصنيف يعتمد على مركز صندوق الاكتشاف (cx, cy) وليس الزاوية العلوية —
المركز أكثر استقراراً لتحديد "أي منطقة يقع فيها الكائن".
"""

from cv import config as cv_config


def boundary_pixel_y(frame_height: int) -> int:
    """السطر (pixel) الذي يفصل Zone 1 عن Zone 2."""
    return int(frame_height * cv_config.ZONE_BOUNDARY)


def classify_point(cy: float, frame_height: int) -> str:
    """إحداثي y (بالبكسل) + ارتفاع الإطار → اسم المنطقة."""
    boundary = boundary_pixel_y(frame_height)
    return cv_config.ZONE_1_NAME if cy < boundary else cv_config.ZONE_2_NAME


def bbox_center(xyxy) -> tuple:
    """xyxy = (x1, y1, x2, y2) -> (cx, cy)"""
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def draw_zone_overlay(frame, color_zone1=(0, 200, 0), color_zone2=(0, 100, 255)):
    """يرسم خط الحدود + تسميات المنطقتين على الإطار (BGR, OpenCV). يُعيد frame."""
    import cv2

    h, w = frame.shape[:2]
    boundary = boundary_pixel_y(h)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, boundary), color_zone1, -1)
    cv2.rectangle(overlay, (0, boundary), (w, h), color_zone2, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    cv2.line(frame, (0, boundary), (w, boundary), (255, 255, 255), 2)
    cv2.putText(frame, "Zone 1 — SCAN AREA", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_zone1, 2)
    cv2.putText(frame, "Zone 2 — CART BASKET", (10, boundary + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_zone2, 2)
    return frame
