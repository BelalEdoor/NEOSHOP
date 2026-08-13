"""
cv/webcam_test.py
=================
اختبار مرئي مباشر لنظام كشف السرقة باستخدام كاميرا اللابتوب.

يفتح الكاميرا ويعرض:
  - المنطقتين (Zone 1 / Zone 2) كخطوط ملونة على الشاشة
  - صناديق YOLO حول الكائنات المكتشفة
  - مؤقت المدة لكل كائن في Zone 1
  - تنبيه واضح على الشاشة عند اكتشاف سلوك مشبوه

تشغيل من داخل backend/:
    python cv/webcam_test.py

اضغط Q للخروج، S لمحاكاة عملية مسح.
"""
import sys
import time
from pathlib import Path
import cv2

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from cv import config as cv_config
from cv import zones
from cv.detector import Detector
from cv.theft_logic import TheftDetectionService

try:
    detector = Detector()
    print(f"[OK] YOLO model loaded")
except Exception as e:
    print(f"[ERROR] Could not load YOLO model: {e}")
    print("Make sure YOLO_MODEL_PATH is set in your .env file")
    sys.exit(1)

# ── Colours ──────────────────────────────────────────────────────────────────
PRODUCT_COLOR = (255, 255, 0)   # yellow — detected product
HAND_COLOR = (255, 0, 0)        # blue   — hand/person
ALERT_COLOR = (0, 0, 255)       # red    — alert

SESSION_ID = 1
svc = TheftDetectionService()
alert_message = None
alert_until = 0.0

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Could not open webcam (index 0). Try index 1 if you have multiple cameras.")
    sys.exit(1)

print("\n[WEBCAM TEST] Starting live detection...")
print(f"  Zone boundary: top {int(cv_config.ZONE_BOUNDARY*100)}% of frame = Zone 1 (scan area)")
print(f"  Zone 1 time threshold: {cv_config.ZONE1_TIME_THRESHOLD}s before warning")
print(f"  Zone 2 settle frames: {cv_config.SETTLE_FRAMES_REQUIRED}")
print("  Press Q to quit, S to simulate a scan\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to read from webcam")
        break

    h, w = frame.shape[:2]
    now = time.time()

    # ── Run YOLO ─────────────────────────────────────────────────────────────
    detections = detector.detect(frame)

    # ── Update tracker + evaluate threats ────────────────────────────────────
    alerts = svc.update(SESSION_ID, detections, h)
    for alert in alerts:
        alert_message = alert["description"]
        alert_until = now + 4.0
        print(f"[ALERT] {alert['alert_type']} — {alert['description']}")

    # ── Draw zones ───────────────────────────────────────────────────────────
    frame = zones.draw_zone_overlay(frame)

    # ── Draw detections ───────────────────────────────────────────────────────
    for det in detections:
        x1, y1, x2, y2 = [int(c) for c in det["xyxy"]]
        label = det["label"]
        conf = det["conf"]
        color = HAND_COLOR if det.get("category") == "hand" else PRODUCT_COLOR

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{label} {conf:.2f}",
                    (x1, max(y1 - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # ── Draw tracked object status ───────────────────────────────────────────
    tracked = svc.tracker.get_tracked(SESSION_ID)
    for tid, obj in tracked.items():
        cx = int((obj.box[0] + obj.box[2]) / 2)
        cy = int((obj.box[1] + obj.box[3]) / 2)

        if getattr(obj, "stable_in_cart", False):
            cv2.putText(frame, "Stable in cart", (cx - 45, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        elif getattr(obj, "in_cart_zone", False):
            cv2.putText(frame, "In cart", (cx - 30, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

    # ── Draw active alert banner ──────────────────────────────────────────────
    if now < alert_until and alert_message:
        cv2.rectangle(frame, (0, 0), (w, 55), ALERT_COLOR, -1)
        cv2.putText(frame, "⚠ THEFT ALERT", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, alert_message[:70], (10, 47),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # ── Status bar ───────────────────────────────────────────────────────────
    from cv import scan_events
    scanned = "yes" if scan_events.has_recent_scan(SESSION_ID, cv_config.SCAN_MATCH_WINDOW_SECONDS) else "no"
    status = f"Recent scan: {scanned} | Tracked objects: {len(tracked)} | Press Q to quit"
    cv2.putText(frame, status, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    cv2.imshow("NEOSHOP — Theft Detection Test", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == ord('Q'):
        break
    elif key == ord('s'):
        svc.register_scanned_product(SESSION_ID, 999)
        print("[SIMULATED] Product scanned — recent scan registered")

cap.release()
cv2.destroyAllWindows()
print("\n[DONE] Webcam test ended.")
