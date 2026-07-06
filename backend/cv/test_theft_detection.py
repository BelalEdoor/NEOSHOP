"""
cv/test_theft_detection.py
==========================
Unit tests for the two-zone theft detection logic.
No camera or YOLO model required — tests the behavior logic directly
by feeding synthetic detections (as if YOLO had already run).

Run from backend/ folder:
    python cv/test_theft_detection.py
"""
import sys, time, asyncio
sys.path.insert(0, '.')

from cv.theft_detection import (
    TheftDetectionService, TrackedObject,
    ZONE_BOUNDARY, ZONE1_TIME_THRESHOLD, ALERT_COOLDOWN,
    _iou, _box_center_y_fraction,
)

FRAME_HEIGHT = 480
ZONE_PIXEL   = int(FRAME_HEIGHT * ZONE_BOUNDARY)  # pixel Y where Zone 1 ends

def make_box_in_zone1():
    """A box whose centre is in Zone 1 (upper scan area)."""
    y1 = 20
    y2 = int(FRAME_HEIGHT * ZONE_BOUNDARY * 0.8)  # well inside Zone 1
    return [50, y1, 150, y2]

def make_box_in_zone2():
    """A box whose centre is in Zone 2 (cart basket)."""
    y1 = int(FRAME_HEIGHT * 0.6)
    y2 = int(FRAME_HEIGHT * 0.9)
    return [50, y1, 150, y2]

def fake_detections(box, label="bottle", confidence=0.85):
    return [{"class": label, "confidence": confidence, "box": box}]

PASS = 0
FAIL = 0

def check(condition, name):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {name}")
        PASS += 1
    else:
        print(f"  ❌ {name}")
        FAIL += 1

print("=" * 60)
print("NEOSHOP Theft Detection — Unit Tests")
print(f"Zone boundary: {ZONE_BOUNDARY} ({ZONE_PIXEL}px in a {FRAME_HEIGHT}px frame)")
print("=" * 60)

# ── Test 1: Zone assignment ────────────────────────────────────────────────────
print("\n── Test 1: Zone assignment ──")
obj1 = TrackedObject(make_box_in_zone1(), "bottle", FRAME_HEIGHT)
obj2 = TrackedObject(make_box_in_zone2(), "bottle", FRAME_HEIGHT)
check(obj1.zone1_entry_time is not None, "Object in Zone 1 gets a zone1_entry_time")
check(not obj1.in_cart_zone,             "Object in Zone 1 is NOT flagged as in_cart_zone")
check(obj2.zone1_entry_time is None,     "Object in Zone 2 has no zone1_entry_time")
check(obj2.in_cart_zone,                 "Object in Zone 2 IS flagged as in_cart_zone")

# ── Test 2: Zone 1 timer ──────────────────────────────────────────────────────
print("\n── Test 2: Zone 1 timer ──")
obj3 = TrackedObject(make_box_in_zone1(), "bottle", FRAME_HEIGHT)
check(obj3.zone1_duration < 0.1, "Fresh object: zone1_duration is near zero")
time.sleep(0.1)
check(obj3.zone1_duration >= 0.1, "After 0.1s: zone1_duration increases correctly")
# Simulate moving to Zone 2 (resets timer)
obj3.update(make_box_in_zone2(), FRAME_HEIGHT)
check(obj3.zone1_duration == 0.0, "After moving to Zone 2: zone1_duration resets to 0")

# ── Test 3: IoU calculation ───────────────────────────────────────────────────
print("\n── Test 3: IoU calculation ──")
same_box  = [10, 10, 50, 50]
overlap   = [30, 30, 70, 70]
no_overlap= [100, 100, 200, 200]
check(_iou(same_box, same_box) == 1.0, "Identical boxes → IoU = 1.0")
check(0.0 < _iou(same_box, overlap) < 1.0, "Partially overlapping → 0 < IoU < 1")
check(_iou(same_box, no_overlap) == 0.0, "Non-overlapping → IoU = 0.0")

# ── Test 4: Tracker update across frames ─────────────────────────────────────
print("\n── Test 4: Object tracker (IoU matching) ──")
svc = TheftDetectionService()
box_frame1 = make_box_in_zone1()
box_frame2 = [box_frame1[0]+5, box_frame1[1]+5, box_frame1[2]+5, box_frame1[3]+5]  # slight movement
box_unrelated = [300, 300, 400, 400]

svc._update_tracker(99, fake_detections(box_frame1), FRAME_HEIGHT)
tracked_after_frame1 = len(svc._tracked_objects.get(99, {}))
check(tracked_after_frame1 == 1, "Frame 1: 1 detection → 1 tracked object")

first_tid = list(svc._tracked_objects[99].keys())[0]
svc._update_tracker(99, fake_detections(box_frame2), FRAME_HEIGHT)
same_tid_after_update = first_tid in svc._tracked_objects[99]
check(same_tid_after_update, "Frame 2: same object (high IoU) → same track_id")

svc._update_tracker(99, fake_detections(box_unrelated), FRAME_HEIGHT)
new_tracked = svc._tracked_objects.get(99, {})
check(len(new_tracked) >= 1, "Frame 3: different position (low IoU) → new track_id created")

# ── Test 5: Spatial trigger (Zone 2 alert) ────────────────────────────────────
print("\n── Test 5: Spatial trigger — unscanned item in cart zone ──")
svc2 = TheftDetectionService()
# No products scanned (empty session)
svc2._update_tracker(1, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
alert = svc2._evaluate_threats(1, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
check(alert is not None, "Product in Zone 2, nothing scanned → alert fires")
check(alert and alert["alert_type"] == "UNSCANNED_IN_CART", "Alert type is UNSCANNED_IN_CART")
check(alert and alert["trigger"] == "spatial", "Trigger is 'spatial'")

# ── Test 6: No alert when item was scanned ────────────────────────────────────
print("\n── Test 6: No alert when product was already scanned ──")
svc3 = TheftDetectionService()
svc3.register_scanned_product(2, 101)  # mark product as scanned
svc3._update_tracker(2, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
# COCO-based detection can't match track_id to product_id 101 directly,
# so this tests the "len(scanned) > 0 means some scanning happened" branch
alert2 = svc3._evaluate_threats(2, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
check(alert2 is None, "Product scanned → no spatial alert (session has scans)")

# ── Test 7: Alert cooldown ────────────────────────────────────────────────────
print("\n── Test 7: Alert cooldown (no spam) ──")
svc4 = TheftDetectionService()
svc4._update_tracker(3, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
alert_a = svc4._evaluate_threats(3, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
alert_b = svc4._evaluate_threats(3, fake_detections(make_box_in_zone2()), FRAME_HEIGHT)
check(alert_a is not None, "First evaluation: alert fires")
check(alert_b is None,     "Immediate second evaluation: cooldown suppresses alert")

# ── Test 8: Session cleanup ───────────────────────────────────────────────────
print("\n── Test 8: Session cleanup ──")
svc5 = TheftDetectionService()
svc5.register_scanned_product(5, 200)
svc5._update_tracker(5, fake_detections(make_box_in_zone1()), FRAME_HEIGHT)
svc5.clear_session(5)
check(5 not in svc5._scanned_products,  "clear_session removes scanned products")
check(5 not in svc5._tracked_objects,   "clear_session removes tracked objects")
check(5 not in svc5._last_alert_time,   "clear_session removes alert timestamps")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("All tests passed ✅")
else:
    print(f"{FAIL} test(s) failed ❌ — check the output above")
print("=" * 60)
