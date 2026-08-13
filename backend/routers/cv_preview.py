"""
routers/cv_preview.py
======================
معاينة مباشرة (Debug/CV Preview) لخط أنابيب الرؤية الحاسوبية عبر المتصفح.

⚠️ لا يوجد هنا أي استدلال: لا YOLO، لا MediaPipe، لا Tracker ثانٍ، لا نسخة
ثانية من theft_logic. كل ما يحدث هنا هو قراءة آخر JPEG جاهز (مُعلَّق عليه
مسبقاً) من cv/preview.py::preview_store، الذي ينشره cv/theft_logic.py
تلقائياً بعد كل إطار حقيقي يعالجه خط أنابيب /ws/camera/{rfid}.

تنسيق الـ multipart أدناه مطابق تماماً لِـ routers/camera.py (البثّ الموجود
أصلاً والمُتحقَّق أنه يعمل بالمتصفح): بدون Content-Length، ونوع محتوى
image/jpeg ثابت طوال البث (لا يُخلَط بأي جزء نصّي وسط البث — بعض المتصفحات
تكسر عرض <img> لعنصر multipart/x-mixed-replace نهائياً إن استقبل جزءاً
بنوع محتوى مختلف، حتى لو وصلت بعده صور سليمة).

الوصول (من لابتوب/جهاز على نفس شبكة الباك اند):
    http://<BACKEND_IP>:<PORT>/cv/preview                → صفحة HTML + الصورة
    http://<BACKEND_IP>:<PORT>/cv/preview?session_id=102  → جلسة/عربة محدَّدة
    http://<BACKEND_IP>:<PORT>/cv/preview/stream          → بثّ MJPEG خام مباشرة

اختياري بالكامل: لو محدا فتح هاد الرابط، preview_store مجرّد قاموس بالذاكرة
يُستبدَل مرجعه مع كل إطار — لا تكلفة تُذكر ولا تراكم، ولا أي تأثير على بث
الكاميرا الحقيقي أو معالجة الفرامل أو باقي الباك اند.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from cv.preview import preview_store, placeholder_jpeg

router = APIRouter()
log = logging.getLogger("neoshop.cv.preview")

_BOUNDARY = b"frame"
_POLL_INTERVAL = 0.05    # فحص كل ٥٠ مللي ثانية لوجود إطار جديد — لا علاقة بمعدّل التحليل الفعلي
_IDLE_RESEND = 1.0       # إعادة إرسال صورة "بانتظار الكاميرا" كل ثانية حتى يبقى الاتصال حياً


@router.get("/preview", response_class=HTMLResponse)
def preview_page(session_id: Optional[int] = Query(None, description="اختياري — لمتابعة جلسة/عربة محدَّدة")):
    active = preview_store.active_sessions()
    stream_src = "/cv/preview/stream" + (f"?session_id={session_id}" if session_id is not None else "")

    if active:
        links = "".join(
            f'<a href="/cv/preview?session_id={sid}" '
            f'style="margin:0 8px;color:{"#38bdf8" if sid != session_id else "#facc15"};'
            f'font-weight:{"700" if sid == session_id else "400"}">#{sid}</a>'
            for sid in active
        )
    else:
        links = "<span style='color:#888'>لا توجد جلسات نشطة بعد — بانتظار أول إطار كاميرا</span>"

    title_suffix = f" — جلسة #{session_id}" if session_id is not None else " (آخر جلسة نشطة تلقائياً)"

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="utf-8">
  <title>CV Preview — NEOSHOP</title>
  <style>
    body {{ background:#0f172a; color:#e2e8f0; font-family:system-ui,sans-serif;
            text-align:center; padding:24px; margin:0; }}
    h1 {{ font-size:17px; font-weight:700; margin-bottom:4px; }}
    p.hint {{ color:#94a3b8; font-size:12px; margin:0 0 16px; }}
    img {{ max-width:95vw; max-height:78vh; border-radius:12px; background:#000;
           box-shadow:0 10px 40px rgba(0,0,0,.5); }}
    .sessions {{ margin-top:14px; font-size:13px; }}
    .legend {{ margin-top:14px; font-size:11px; color:#94a3b8; }}
    .legend span {{ margin:0 8px; }}
  </style>
</head>
<body>
  <h1>🎥 معاينة خط أنابيب الرؤية الحاسوبية (الباك اند){title_suffix}</h1>
  <p class="hint">أداة تصحيح أخطاء فقط — بدون تأثير على خط المعالجة الحقيقي</p>
  <img src="{stream_src}" />
  <p class="sessions">الجلسات النشطة: {links}</p>
  <p class="legend">
    <span style="color:#ffff00">■ أصفر</span> اكتشاف منتج خام
    <span style="color:#ffc800">■ برتقالي</span> اكتشاف يد خام
    <span style="color:#00ff00">■ أخضر</span> متتبَّع
    <span style="color:#ffa500">■ برتقالي غامق</span> دخل السلة
    <span style="color:#ff0000">■ أحمر</span> مستقرّ بالسلة (قيد المراقبة)
    <span style="color:#808080">■ رمادي</span> تم التحقق منه (ممسوح)
  </p>
</body>
</html>"""
    return HTMLResponse(content=html)


def _part(jpeg_bytes: bytes) -> bytes:
    """
    جزء multipart واحد — نفس التنسيق المستخدَم فعلياً وبنجاح في
    routers/camera.py::_mjpeg_frames (بدون Content-Length).
    """
    return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"


async def _mjpeg_generator(session_id: Optional[int]):
    last_ts = None
    try:
        while True:
            jpeg, updated_at = preview_store.get(session_id)

            if jpeg is None:
                # نوع المحتوى يبقى image/jpeg طوال البث دائماً (صورة "بانتظار
                # الكاميرا" مولَّدة، مش نص) — حتى لا يكسر بعض المتصفحات عرض
                # <img> لعنصر multipart/x-mixed-replace عند تبديل نوع المحتوى.
                yield _part(placeholder_jpeg())
                await asyncio.sleep(_IDLE_RESEND)
                continue

            if updated_at != last_ts:
                last_ts = updated_at
                yield _part(jpeg)

            await asyncio.sleep(_POLL_INTERVAL)
    except asyncio.CancelledError:
        # المتصفح أغلق الاتصال — إنهاء نظيف بدون أي أثر على البث الأصلي
        log.debug(f"[CV Preview] client disconnected (session_id={session_id})")
        raise


@router.get("/preview/stream")
async def preview_stream(session_id: Optional[int] = Query(None)):
    return StreamingResponse(
        _mjpeg_generator(session_id),
        media_type=b"multipart/x-mixed-replace; boundary=frame".decode(),
    )