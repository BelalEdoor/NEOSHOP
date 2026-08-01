"""
raspberry_pi/camera_stream.py
==============================
يعمل على الراسبيري باي المثبَّت على العربة (وليس على الباك اند). مهمته
الوحيدة: التقاط إطارات من كاميرا العربة وبثّها مباشرة إلى الباك اند عبر
WebSocket ليقوم نموذج الرؤية الحاسوبية (cv/theft_logic.py) بتحليلها.

الاتصال:
    ws://<BACKEND_HOST>:8000/ws/camera/<CART_RFID>

CART_RFID هو نفس معرّف العربة الثابت المُخزَّن بجدول carts.rfid_uid —
لا حاجة لمعرفة session_id؛ الباك اند يبحث تلقائياً عن الجلسة النشطة
المرتبطة بهذه العربة مع كل إطار (راجع websocket_router.py::websocket_camera).

التشغيل:
    pip install opencv-python-headless websockets
    python camera_stream.py --host 192.168.1.50 --rfid RFID-DEFAULT-001

يمكن أيضاً ضبط القيم كمتغيرات بيئة بدل الوسائط:
    BACKEND_HOST, BACKEND_PORT, CART_RFID, CAMERA_INDEX, TARGET_FPS
"""
import argparse
import asyncio
import logging
import os
import time

import cv2
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("camera_stream")


def parse_args():
    p = argparse.ArgumentParser(description="NEOSHOP — Raspberry Pi camera → backend CV stream")
    p.add_argument("--host", default=os.environ.get("BACKEND_HOST", "localhost"),
                    help="عنوان IP أو hostname للباك اند")
    p.add_argument("--port", type=int, default=int(os.environ.get("BACKEND_PORT", 8000)))
    p.add_argument("--rfid", default=os.environ.get("CART_RFID", "RFID-DEFAULT-001"),
                    help="RFID UID الخاص بهذه العربة (carts.rfid_uid بقاعدة البيانات)")
    p.add_argument("--camera-index", type=int, default=int(os.environ.get("CAMERA_INDEX", 0)),
                    help="فهرس كاميرا OpenCV (عادة 0 لكاميرا الراسبيري باي المتصلة عبر USB/CSI)")
    p.add_argument("--fps", type=float, default=float(os.environ.get("TARGET_FPS", 8)),
                    help="عدد الإطارات المُرسَلة بالثانية — لا حاجة لأكثر من ٥-١٠ لأن التحليل ليس بالزمن الحقيقي الكامل")
    p.add_argument("--jpeg-quality", type=int, default=80)
    return p.parse_args()


async def stream_camera(args):
    ws_url = f"ws://{args.host}:{args.port}/ws/camera/{args.rfid}"
    frame_interval = 1.0 / max(args.fps, 0.1)

    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        log.error(f"تعذّر فتح الكاميرا (index={args.camera_index})")
        return

    log.info(f"الكاميرا جاهزة — سيتم البث إلى {ws_url}")

    while True:  # حلقة إعادة الاتصال — لو انقطع الباك اند نعيد المحاولة تلقائياً
        try:
            async with websockets.connect(ws_url, max_size=None) as ws:
                log.info("✓ متصل بالباك اند")
                while True:
                    start = time.time()
                    ok, frame = cap.read()
                    if not ok:
                        log.warning("فشل قراءة إطار من الكاميرا — إعادة المحاولة")
                        await asyncio.sleep(0.5)
                        continue

                    ok, buf = cv2.imencode(
                        ".jpg", frame,
                        [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality],
                    )
                    if not ok:
                        continue

                    await ws.send(buf.tobytes())

                    elapsed = time.time() - start
                    await asyncio.sleep(max(0.0, frame_interval - elapsed))

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            log.warning(f"انقطع الاتصال بالباك اند ({e}) — إعادة المحاولة خلال 3 ثوانٍ")
            await asyncio.sleep(3)
        except KeyboardInterrupt:
            break

    cap.release()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(stream_camera(args))
    except KeyboardInterrupt:
        log.info("تم الإيقاف يدوياً")
