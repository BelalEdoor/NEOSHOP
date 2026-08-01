"""
raspberry_pi/aruco_reader.py
============================
قارئ علامات ArUco — وضع المعايرة (الكاميرا مفتوحة دائماً).

يدعم الآن 4 علامات (بدلاً من علامتين)، واحدة عند كل طرف من طرفي كل ممر،
مطابقة لمخطط التوصيل الميداني:

  4x4_1000-0.svg -> marker ID 0 -> tag0 (أسفل الممر الأول)  -> case1 (forward)
  4x4_1000-1.svg -> marker ID 1 -> tag1 (أعلى الممر الأول)  -> case2 (backward)
  4x4_1000-2.svg -> marker ID 2 -> tag2 (أسفل الممر الثاني) -> case3 (forward)
  4x4_1000-3.svg -> marker ID 3 -> tag3 (أعلى الممر الثاني) -> case4 (backward)

اضغط Q للإغلاق.
"""
import time
import logging
import threading
import queue

import cv2
import requests

from config import (
    BACKEND_URL, DEVICE_KEY, CART_ID,
    CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT,
    ARUCO_DICT_NAME, DEBOUNCE_SECONDS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("aruco_reader")

# زمن الاستجابة المطلوب: أقصى ثانية واحدة من لحظة رؤية العلامة حتى وصولها
# للباك اند. لا تجعل DEBOUNCE_SECONDS في config.py أكبر من 1.0
RESPONSE_DEADLINE = min(float(DEBOUNCE_SECONDS or 1.0), 1.0)

ARUCO_DICTS = {
    "DICT_4X4_50":   cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100":  cv2.aruco.DICT_4X4_100,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50":   cv2.aruco.DICT_5X5_50,
    "DICT_6X6_50":   cv2.aruco.DICT_6X6_50,
}

aruco_dict   = cv2.aruco.getPredefinedDictionary(ARUCO_DICTS[ARUCO_DICT_NAME])
aruco_params = cv2.aruco.DetectorParameters()
# تسريع الكشف: لا حاجة لتحسين الزوايا بدقة عالية لمهمة "تمّت القراءة أم لا"
aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_NONE
aruco_params.adaptiveThreshWinSizeMin = 5
aruco_params.adaptiveThreshWinSizeMax = 15
aruco_params.adaptiveThreshWinSizeStep = 5
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# ألوان مميزة لكل علامة من العلامات الأربع
MARKER_COLORS = {
    0: (255, 100,   0),   # tag0 - أسفل الممر الأول
    1: (0,   140, 255),   # tag1 - أعلى الممر الأول
    2: (150,   0, 255),   # tag2 - أسفل الممر الثاني
    3: (255,   0, 140),   # tag3 - أعلى الممر الثاني
}
COLOR_OTHER = (100, 200, 100)
COLOR_TEXT  = (255, 255, 255)
TAG_NAMES = {
    0: 'tag0 -> Aisle1 bottom (case1)',
    1: 'tag1 -> Aisle1 top (case2)',
    2: 'tag2 -> Aisle2 bottom (case3)',
    3: 'tag3 -> Aisle2 top (case4)',
}


def get_color(mid):
    return MARKER_COLORS.get(mid, COLOR_OTHER)


# ── إرسال غير-حاجب (non-blocking) للباك اند ─────────────────────────────────
# نستخدم Session لإعادة استخدام الاتصال (يقلّل زمن كل طلب)، وطابور + خيط
# مستقل لإرسال القراءات بحيث لا يتأخر التقاط الإطارات أبداً بانتظار الشبكة.
_session = requests.Session()
_send_queue: "queue.Queue[int]" = queue.Queue()


def _sender_worker():
    while True:
        marker_id = _send_queue.get()
        t0 = time.time()
        try:
            resp = _session.post(
                f"{BACKEND_URL}/api/navigation/marker-read",
                json={"cart_id": CART_ID, "marker_id": marker_id},
                headers={"X-Device-Key": DEVICE_KEY},
                timeout=1.0,  # لا ننتظر أكثر من ثانية على الشبكة
            )
            elapsed = time.time() - t0
            if resp.status_code == 200:
                data = resp.json()
                log.info("marker %s -> section '%s' (%.0f ms)",
                          marker_id, data.get("section_name"), elapsed * 1000)
            else:
                log.warning("backend rejected marker %s: %s", marker_id, resp.status_code)
        except requests.RequestException as exc:
            log.error("cannot reach backend: %s", exc)
        finally:
            _send_queue.task_done()


threading.Thread(target=_sender_worker, daemon=True).start()


def send_marker_read(marker_id: int) -> None:
    """يضع القراءة في الطابور فوراً بدون انتظار رد الشبكة (استجابة فورية)."""
    _send_queue.put(marker_id)


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    # طابور تخزين مؤقت صغير قدر الإمكان حتى لا "تتأخر" الإطارات المعروضة
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        raise SystemExit("Camera not found — check CAMERA_INDEX in config.py")

    log.info("ArUco reader started | dict=%s | cart_id=%s | 4 markers", ARUCO_DICT_NAME, CART_ID)
    log.info("Preview window OPEN — press Q to quit")
    last_sent = {}

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                # لا وقت انتظار طويل — أعد المحاولة فوراً تقريباً
                time.sleep(0.005)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            detected_names = []
            if ids is not None:
                now = time.time()
                for i, marker_id in enumerate(ids.flatten().tolist()):
                    mid   = int(marker_id)
                    if mid not in TAG_NAMES:
                        continue  # تجاهل أي علامة غير معروفة (خارج 0-3)
                    color = get_color(mid)
                    name  = TAG_NAMES[mid]
                    detected_names.append(name)

                    # رسم إطار حول العلامة
                    pts = corners[i][0].astype(int)
                    cv2.polylines(frame, [pts], True, color, 3)

                    # اسم العلامة في المنتصف
                    cx = int(pts[:, 0].mean())
                    cy = int(pts[:, 1].mean())
                    cv2.putText(frame, name, (cx - 90, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                    # إرسال فوري (غير حاجب) للباك اند — أقل من ثانية استجابة
                    if now - last_sent.get(mid, 0) >= RESPONSE_DEADLINE:
                        send_marker_read(mid)
                        last_sent[mid] = now

            # شريط الحالة أعلى
            cv2.rectangle(frame, (0, 0), (FRAME_WIDTH, 32), (30, 30, 30), -1)
            cv2.putText(frame, f"NEOSHOP | {ARUCO_DICT_NAME} | cart: {CART_ID} | Q=quit",
                        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXT, 1)

            # شريط الحالة أسفل
            cv2.rectangle(frame, (0, FRAME_HEIGHT - 36), (FRAME_WIDTH, FRAME_HEIGHT), (20, 20, 20), -1)
            if detected_names:
                cv2.putText(frame, f"Detected: {' | '.join(detected_names)}",
                            (8, FRAME_HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (0, 255, 120), 2)
            else:
                cv2.putText(frame, "No marker detected - point camera at tag",
                            (8, FRAME_HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (120, 120, 120), 1)

            cv2.imshow("NEOSHOP ArUco - Calibration (Q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            # لا يوجد time.sleep() إضافي هنا عمداً — القراءة تعمل بأقصى FPS
            # ممكن من الكاميرا؛ زمن الاستجابة الآن محكوم فقط بـ RESPONSE_DEADLINE
            # وبسرعة الشبكة (مع timeout=1s وخيط إرسال منفصل لا يحجب الالتقاط).

    finally:
        cap.release()
        cv2.destroyAllWindows()
        log.info("ArUco reader stopped")


if __name__ == "__main__":
    main()
