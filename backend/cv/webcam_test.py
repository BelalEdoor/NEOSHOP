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

اضغط Q للخروج.
"""
import sys
import time
import cv2
import numpy as np

sys.path.insert(0, '.')

from cv.theft_detection import (
    TheftDetectionService,
    ZONE_BOUNDARY, ZONE1_TIME_THRESHOLD,
    PRODUCT_CLASSES, HAND_CLASSES,
    CONFIDENCE_THRESHOLD, _iou,
    TrackedObject,
)

try:
    from ultralytics import YOLO
    from core.config import settings
    model = YOLO(settings.YOLO_MODEL_PATH)
    print(f"[OK] YOLO model loaded: {settings.YOLO_MODEL_PATH}")
except Exception as e:
    print(f"[ERROR] Could not load YOLO model: {e}")
    print("Make sure YOLO_MODEL_PATH is set in your .env file")
    sys.exit(1)

# ── Colours ──────────────────────────────────────────────────────────────────
ZONE1_COLOR   = (0,   200, 0)    # green  — scan zone
ZONE2_COLOR   = (0,   100, 255)  # orange — cart basket
PRODUCT_COLOR = (255, 255,  0)   # yellow — detected product
HAND_COLOR    = (255,   0,  0)   # blue   — hand/person
ALERT_COLOR   = (0,     0, 255)  # red    — alert

SESSION_ID = 1
svc = TheftDetectionService()
alert_message = None
alert_until   = 0.0

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Could not open webcam (index 0). Try index 1 if you have multiple cameras.")
    sys.exit(1)

print("\n[WEBCAM TEST] Starting live detection...")
print(f"  Zone boundary: top {int(ZONE_BOUNDARY*100)}% of frame = Zone 1 (scan area)")
print(f"  Zone 1 time threshold: {ZONE1_TIME_THRESHOLD}s before warning")
print("  Press Q to quit\n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to read from webcam")
        break

    h, w = frame.shape[:2]
    zone_line_y = int(h * ZONE_BOUNDARY)
    now = time.time()

    # ── Run YOLO ─────────────────────────────────────────────────────────────
    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

    detections = []
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = result.names[cls_id]
            coords = box.xyxy[0].tolist()
            detections.append({
                "class":      label,
                "confidence": round(conf, 3),
                "box":        coords,
            })

    # ── Update tracker + evaluate threats ────────────────────────────────────
    svc._update_tracker(SESSION_ID, detections, h)
    alert = svc._evaluate_threats(SESSION_ID, detections, h)
    if alert:
        alert_message = alert["description"]
        alert_until   = now + 4.0
        print(f"[ALERT] {alert['alert_type']} — {alert['description']}")

    # ── Draw zones ───────────────────────────────────────────────────────────
    # Zone 1 overlay (green tint, upper area)
    zone1_overlay = frame.copy()
    cv2.rectangle(zone1_overlay, (0, 0), (w, zone_line_y), ZONE1_COLOR, -1)
    cv2.addWeighted(zone1_overlay, 0.08, frame, 0.92, 0, frame)

    # Zone 2 overlay (orange tint, lower area)
    zone2_overlay = frame.copy()
    cv2.rectangle(zone2_overlay, (0, zone_line_y), (w, h), ZONE2_COLOR, -1)
    cv2.addWeighted(zone2_overlay, 0.08, frame, 0.92, 0, frame)

    # Zone boundary line
    cv2.line(frame, (0, zone_line_y), (w, zone_line_y), (255, 255, 255), 2)

    # Zone labels
    cv2.putText(frame, "Zone 1 — SCAN AREA", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, ZONE1_COLOR, 2)
    cv2.putText(frame, "Zone 2 — CART BASKET", (10, zone_line_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, ZONE2_COLOR, 2)

    # ── Draw detections ───────────────────────────────────────────────────────
    for det in detections:
        x1, y1, x2, y2 = [int(c) for c in det["box"]]
        label = det["class"]
        conf  = det["confidence"]
        color = HAND_COLOR if label in HAND_CLASSES else PRODUCT_COLOR

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{label} {conf:.2f}",
                    (x1, max(y1 - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # ── Draw tracked object timers ────────────────────────────────────────────
    tracked = svc._tracked_objects.get(SESSION_ID, {})
    for tid, obj in tracked.items():
        duration = obj.zone1_duration
        if duration > 0:
            cx = int((obj.box[0] + obj.box[2]) / 2)
            cy = int((obj.box[1] + obj.box[3]) / 2)
            remaining = max(0, ZONE1_TIME_THRESHOLD - duration)
            timer_text = f"Scan in {remaining:.1f}s" if remaining > 0 else "SCAN NOW!"
            color = (0, 255, 0) if remaining > 1.5 else (0, 0, 255)
            cv2.putText(frame, timer_text, (cx - 40, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    # ── Draw active alert banner ──────────────────────────────────────────────
    if now < alert_until and alert_message:
        # Red banner across top of frame
        cv2.rectangle(frame, (0, 0), (w, 55), ALERT_COLOR, -1)
        cv2.putText(frame, "⚠ THEFT ALERT", (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, alert_message[:70], (10, 47),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    # ── Status bar ───────────────────────────────────────────────────────────
    scanned_count = len(svc._scanned_products.get(SESSION_ID, set()))
    status = f"Scanned: {scanned_count} | Tracked objects: {len(tracked)} | Press Q to quit"
    cv2.putText(frame, status, (10, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    cv2.imshow("NEOSHOP — Theft Detection Test", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == ord('Q'):
        break
    elif key == ord('s'):
        # Press S to simulate scanning a product (marks session as "something scanned")
        svc.register_scanned_product(SESSION_ID, 999)
        print("[SIMULATED] Product scanned — session now has 1 scanned item")

cap.release()
cv2.destroyAllWindows()
print("\n[DONE] Webcam test ended.")
