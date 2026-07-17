"""
routers/camera.py
==================
بث فيديو MJPEG من كاميرا مراقبة المتجر — تُستخدم من نافذة "مراقبة العربة"
بخريطة الأدمن (AdminMap.jsx) عند الضغط على أي نقطة عربة.

ملاحظة مهمة عن حدود هذا التنفيذ:
  النظام حالياً يدعم كاميرا واحدة فقط (CAMERA_STREAM_URL في core/config.py،
  نفس الكاميرا المستخدمة لكشف السرقة في cv/theft_detection.py). بث "خاص
  بكل عربة على حدة" يتطلب كاميرا فيزيائية مستقلة لكل عربة أو نظام تتبّع/
  تحويل زاوية تلقائي، وهذا خارج نطاق هذا التعديل. حالياً: فتح المراقبة لأي
  عربة يعرض نفس بث كاميرا المتجر العامة (cart_id يُستقبل ويُمرَّر لأغراض
  التسجيل/التوسعة المستقبلية فقط).

لماذا التوكن عبر query param؟
  عنصر <img> بالمتصفح ما بقدر يرسل Authorization header، فبنستقبل الـ JWT
  كـ query param بدل ذلك (نمط شائع لبث الصور/الفيديو محمي بمصادقة).
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError

from core.config import settings
from core.database import SessionLocal
from models.user import User

log = logging.getLogger("neoshop.camera")
router = APIRouter()

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log.warning("[camera] opencv-python not installed — live stream disabled")


def _verify_token_param(token: str) -> User:
    """نفس تحقّق get_current_user لكن من query param بدل Authorization header."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token")
    except JWTError:
        raise HTTPException(401, "Invalid token")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    finally:
        db.close()

    if not user or not user.is_active:
        raise HTTPException(401, "Invalid or disabled account")
    return user


def _mjpeg_frames():
    src = settings.CAMERA_STREAM_URL
    cap = cv2.VideoCapture(int(src) if src.isdigit() else src)
    if not cap.isOpened():
        raise RuntimeError("Camera not accessible")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            )
    finally:
        cap.release()


@router.get("/stream")
def stream(token: str = Query(...), cart_id: int = Query(None)):
    user = _verify_token_param(token)
    if user.email not in settings.get_admin_emails():
        raise HTTPException(403, "Admin access required")

    if not CV2_AVAILABLE:
        raise HTTPException(503, "Camera support not installed on the server (opencv-python)")

    try:
        return StreamingResponse(
            _mjpeg_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
    except RuntimeError:
        raise HTTPException(503, "Camera not accessible")