"""
raspberry_pi/aruco_reader.py
============================
قارئ علامات ArUco على الراسباري باي.

الفكرة:
  - الكاميرا مثبتة على العربة وتقرأ العلامات الملصقة على الرفوف/المدخل/المخرج.
  - عند اكتشاف علامة جديدة (مع Debounce حتى لا نرسل نفس العلامة كل فريم)،
    نرسل POST إلى الباك اند:  POST /api/navigation/marker-read
  - الباك اند يحدّث CartLiveStatus ويظهر موقع العربة على الخريطة مباشرة.

التشغيل:
  python3 aruco_reader.py

المتطلبات: انظر requirements.txt (opencv-contrib-python, requests, numpy)
"""
import time
import logging

import cv2
import requests

from config import (
    BACKEND_URL, DEVICE_KEY, CART_ID,
    CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT,
    ARUCO_DICT_NAME, DEBOUNCE_SECONDS, SHOW_PREVIEW,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aruco_reader")

# ─── ArUco setup ─────────────────────────────────────────────────────────────
ARUCO_DICTS = {
    "DICT_4X4_50":  cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_5X5_50":  cv2.aruco.DICT_5X5_50,
    "DICT_6X6_50":  cv2.aruco.DICT_6X6_50,
}

aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICTS[ARUCO_DICT_NAME])
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)


def send_marker_read(marker_id: int) -> bool:
    """إرسال قراءة العلامة إلى الباك اند. يرجع True عند النجاح."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/navigation/marker-read",
            json={"cart_id": CART_ID, "marker_id": marker_id},
            headers={"X-Device-Key": DEVICE_KEY},
            timeout=3,
        )
        if resp.status_code == 200:
            data = resp.json()
            log.info("marker %s -> section '%s' (%.1f, %.1f)",
                     marker_id, data.get("section_name"),
                     data.get("pos_x", -1), data.get("pos_y", -1))
            return True
        log.warning("backend rejected marker %s: %s %s",
                    marker_id, resp.status_code, resp.text[:200])
    except requests.RequestException as exc:
        log.error("cannot reach backend: %s", exc)
    return False


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if not cap.isOpened():
        raise SystemExit("Camera not found — check CAMERA_INDEX in config.py")

    log.info("ArUco reader started (cart_id=%s, dict=%s)", CART_ID, ARUCO_DICT_NAME)

    last_sent: dict[int, float] = {}   # marker_id -> timestamp آخر إرسال

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _rejected = detector.detectMarkers(gray)

            if ids is not None:
                now = time.time()
                for marker_id in ids.flatten().tolist():
                    # Debounce: لا نعيد إرسال نفس العلامة قبل مرور DEBOUNCE_SECONDS
                    if now - last_sent.get(marker_id, 0) >= DEBOUNCE_SECONDS:
                        if send_marker_read(int(marker_id)):
                            last_sent[marker_id] = now

                if SHOW_PREVIEW:
                    cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            if SHOW_PREVIEW:
                cv2.imshow("NEOSHOP ArUco Reader", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            time.sleep(0.03)   # ~30 fps سقف — يخفف حمل المعالج
    finally:
        cap.release()
        if SHOW_PREVIEW:
            cv2.destroyAllWindows()
        log.info("ArUco reader stopped")


if __name__ == "__main__":
    main()
