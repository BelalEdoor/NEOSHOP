"""
websocket_router.py
===================
إدارة WebSocket connections للـ Frontend (Raspberry Pi) ولوحة الأدمن.

Channels:
  /ws/cart/{session_id}  ← Raspberry Pi (Frontend per session)
  /ws/admin              ← لوحة إدارة المتجر
  /ws/pos/{session_id}   ← نقطة البيع
"""
import json
import logging
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone

from cv.log_colors import colorize, MAGENTA

router = APIRouter()
log    = logging.getLogger("neoshop.ws")


# ══════════════════════════════════════════════════════════════════════════════
# ConnectionManager
# ══════════════════════════════════════════════════════════════════════════════
class ConnectionManager:
    """
    إدارة كل اتصالات WebSocket في النظام.
    يدعم 3 قنوات: Cart (per session), Admin, POS.
    """

    def __init__(self):
        self._admin_clients: Set[WebSocket] = set()
        self._session_clients: Dict[int, Set[WebSocket]] = {}  # session_id → clients
        self._cart_locked: Dict[int, bool] = {}
        # أجهزة الراسبيري باي المتصلة ببثّ الكاميرا — cart_rfid → sockets.
        # نفس الاتصال يُستخدَم بالاتجاه المعاكس لإرسال أوامر الفرامل، فلا
        # يحتاج الجهاز اتصالاً ثانياً ولا broker شغّالاً ليستقبل الأمر.
        self._device_clients: Dict[str, Set[WebSocket]] = {}

    # ── Admin ──────────────────────────────────────────────────────────────
    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self._admin_clients.add(ws)
        log.info(f"[WS] Admin connected ({len(self._admin_clients)} active)")

    def disconnect_admin(self, ws: WebSocket):
        self._admin_clients.discard(ws)

    async def broadcast_to_admin(self, message: dict):
        for ws in list(self._admin_clients):
            await self._safe_send(ws, message)

    # ── Session / Cart ─────────────────────────────────────────────────────
    async def connect_to_session(self, ws: WebSocket, session_id: int):
        await ws.accept()
        if session_id not in self._session_clients:
            self._session_clients[session_id] = set()
        self._session_clients[session_id].add(ws)
        log.info(f"[WS] Client connected to session {session_id}")
        # إرسال حالة القفل الحالية
        locked = self._cart_locked.get(session_id, False)
        await self._safe_send(ws, {"type": "cart_locked", "locked": locked})

    def disconnect_from_session(self, ws: WebSocket, session_id: int):
        if session_id in self._session_clients:
            self._session_clients[session_id].discard(ws)

    def session_client_count(self, session_id: int) -> int:
        """
        عدد المتصفحات المتصلة فعلياً بجلسة معيّنة الآن (نقطة البيع + أي
        قناة أخرى تستخدم /ws/cart أو /ws/pos لنفس الجلسة). تُستخدَم من
        cv/alert_handler.py لتشخيص "التحذير ما بيوصل نقطة البيع" — لو
        القيمة 0 لحظة إرسال تنبيه، فالمشكلة إن الفرونت اند غير متصل أصلاً،
        مش أن الباك اند فشل بإرسال شي.
        """
        return len(self._session_clients.get(session_id, set()))

    async def broadcast_to_session(self, session_id: int, message: dict):
        """إرسال رسالة لجميع clients المرتبطين بجلسة معيّنة (+ لوحة الأدمن)."""
        await self.broadcast_to_session_only(session_id, message)
        # أيضاً أرسل للأدمن
        await self.broadcast_to_admin(message)

    async def broadcast_to_session_only(self, session_id: int, message: dict):
        """
        إرسال للجلسة فقط بدون تكرار الرسالة للأدمن.
        تُستخدَم من cv/alert_handler.py لأن إشعار لوحة التحكم يُرسَل هناك
        بشكل منفصل بحمولة مختلفة (تحتوي can_release لزر "تفعيل السلة")،
        فلو استخدمنا broadcast_to_session لوصل الأدمن إشعاران لكل تنبيه.
        """
        clients = self._session_clients.get(session_id, set())
        for ws in list(clients):
            await self._safe_send(ws, message)

    # ── Devices (Raspberry Pi) ─────────────────────────────────────────────
    def register_device(self, ws: WebSocket, cart_rfid: str):
        self._device_clients.setdefault(cart_rfid, set()).add(ws)

    def unregister_device(self, ws: WebSocket, cart_rfid: str):
        if cart_rfid in self._device_clients:
            self._device_clients[cart_rfid].discard(ws)
            if not self._device_clients[cart_rfid]:
                self._device_clients.pop(cart_rfid, None)

    async def send_to_device(self, cart_rfid: str, message: dict) -> bool:
        """
        إرسال أمر لراسبيري باي عربة معيّنة عبر اتصال الكاميرا المفتوح.
        يُرجع True إذا وصل الأمر لجهاز واحد على الأقل.
        """
        clients = self._device_clients.get(cart_rfid, set())
        if not clients:
            log.warning(f"[WS] No device connected for cart_rfid={cart_rfid}")
            return False
        delivered = False
        for ws in list(clients):
            if await self._safe_send(ws, message):
                delivered = True
        return delivered

    def connected_devices(self) -> list:
        return sorted(self._device_clients.keys())

    async def set_cart_locked(self, session_id: int, locked: bool):
        self._cart_locked[session_id] = locked
        await self.broadcast_to_session(session_id, {
            "type": "cart_locked",
            "locked": locked,
            "session_id": session_id,
        })

    # ── Helpers ────────────────────────────────────────────────────────────
    async def _safe_send(self, ws: WebSocket, data: dict) -> bool:
        try:
            await ws.send_json(data)
            return True
        except Exception:
            return False


# ─── Global Instance ──────────────────────────────────────────────────────────
manager = ConnectionManager()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/cart/{session_id}")
async def websocket_cart(websocket: WebSocket, session_id: int):
    """
    Raspberry Pi يتصل هنا لاستقبال تحديثات جلسة التسوق.
    يستقبل: cart_update, cart_locked, theft_alert, payment_update
    """
    await manager.connect_to_session(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                # الرسائل من Raspberry Pi → Backend
                if msg_type == "barcode_scan":
                    # الرازبيري يُبلّغ عن مسح باركود
                    log.info(f"[WS] Barcode scan from session {session_id}: {msg}")
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_from_session(websocket, session_id)
        log.info(f"[WS] Session {session_id} disconnected")
    except RuntimeError as e:
        # "WebSocket is not connected. Need to call accept first." — يصير
        # أحياناً لو العميل قطع الاتصال بسرعة كبيرة جداً أثناء نافذة الـ
        # accept() نفسها (سباق تايمنغ نادر بين الفرونت اند والباك اند، ليس
        # خللاً بمنطق التطبيق). قبل هذا التعديل كان يظهر كـ Traceback كامل
        # غير مُعالَج بالسيرفر (Exception in ASGI application) رغم أنه غير
        # ضارّ فعلياً — الآن يُسجَّل بهدوء وتُنظَّف حالة الاتصال بأمان.
        log.warning(f"[WS] Session {session_id}: connection dropped during handshake ({e})")
        manager.disconnect_from_session(websocket, session_id)
@router.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """
    لوحة الأدمن تتصل هنا لاستقبال تحديثات في real-time.
    تستقبل: theft_alert, cart_update, payment_complete, session_started
    """
    await manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)
        log.info("[WS] Admin disconnected")
    except RuntimeError as e:
        log.warning(f"[WS] Admin: connection dropped during handshake ({e})")
        manager.disconnect_admin(websocket)


@router.websocket("/ws/pos/{session_id}")
async def websocket_pos(websocket: WebSocket, session_id: int):
    """نقطة البيع — مشابهة لـ /ws/cart لكن مخصصة لشاشة الدفع."""
    await manager.connect_to_session(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_from_session(websocket, session_id)
    except RuntimeError as e:
        log.warning(f"[WS] POS session {session_id}: connection dropped during handshake ({e})")
        manager.disconnect_from_session(websocket, session_id)


@router.websocket("/ws/camera/{cart_rfid}")
async def websocket_camera(websocket: WebSocket, cart_rfid: str):
    """
    Raspberry Pi يتصل هنا ويبعث إطارات JPEG (binary frames) من الكاميرا
    المثبَّتة على العربة، إطاراً بعد إطار، بشكل مستمر طوال جلسة التسوق.

    لماذا cart_rfid وليس session_id؟
      جهاز الراسبيري باي مثبَّت فيزيائياً على عربة واحدة بشكل دائم
      (هويته الثابتة هي RFID العربة)، بينما session_id يتغيّر مع كل عميل
      جديد يستخدم نفس العربة. البحث عن الجلسة النشطة يتم هنا في كل مرة
      تصل فيها مجموعة إطارات، فلا يحتاج الراسبيري باي معرفة session_id
      أو إعادة الاتصال عند تبديل العميل.

    كل إطار يُمرَّر إلى theft_service.analyze_frame()، والذي بدوره يستدعي
    تلقائياً handle_theft_alert() (المسجَّلة عبر set_theft_callback في
    main.py) عند رصد أي سلوك مشبوه — لا حاجة لأي منطق إضافي هنا.
    """
    from core.rfid_utils import normalize_rfid

    # نطبّع الـ RFID فور وصوله — أي صيغة (":", "-", حالة أحرف مختلفة)
    # تتحوّل لنفس الشكل الموحّد، حتى لو الراسبيري باي لسا يبعث صيغة قديمة.
    cart_rfid = normalize_rfid(cart_rfid)

    await websocket.accept()
    manager.register_device(websocket, cart_rfid)
    log.info(f"[WS] Camera connected for cart_rfid={cart_rfid}")

    import time as _time
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.cart import Cart, CartStatus
    from cv.theft_detection import theft_service

    # كاش خفيف للجلسة النشطة: البحث بقاعدة البيانات مع *كل* إطار (٨ إطارات
    # بالثانية × عدد العربات) استعلام مكرّر بلا داعٍ ويصير عنق زجاجة. نبحث
    # مرة كل ثانيتين فقط — كافٍ تماماً لأن الجلسة لا تتغيّر إلا عند تبديل عميل.
    cached_session_id: Optional[int] = None
    cached_cart_id: Optional[int] = None
    last_lookup = 0.0
    LOOKUP_INTERVAL = 2.0
    frame_count = 0

    await manager._safe_send(websocket, {"type": "connected", "cart_rfid": cart_rfid})

    try:
        while True:
            message = await websocket.receive()

            # رسائل نصية من الجهاز (heartbeat / تأكيد تنفيذ أمر الفرامل)
            if "text" in message and message["text"] is not None:
                try:
                    msg = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "ping":
                    await manager._safe_send(websocket, {"type": "pong"})
                elif msg.get("type") == "brake_ack":
                    log.info(f"[WS] Brake ack from {cart_rfid}: {msg.get('state')}")
                continue

            if "bytes" not in message or message["bytes"] is None:
                if message.get("type") == "websocket.disconnect":
                    break
                continue

            frame_bytes = message["bytes"]

            now = _time.time()
            if now - last_lookup >= LOOKUP_INTERVAL:
                last_lookup = now
                db = SessionLocal()
                try:
                    # المصدر الأساسي لهوية العربة هو جدول carts (rfid_uid
                    # مُطبَّع مسبقاً عند التسجيل عبر routers/cart.py). نحصل
                    # على cart.id أولاً ثم نبحث عن الجلسة النشطة به — بدل
                    # الاعتماد على مطابقة نصية مباشرة لعمود cart_rfid
                    # المكرّر داخل shopping_sessions، اللي ممكن يحمل صيغة
                    # قديمة/غير مطبّعة من جلسات سابقة.
                    if cached_cart_id is None:
                        cart = db.query(Cart).filter(Cart.rfid_uid == cart_rfid).first()
                        cached_cart_id = cart.id if cart else None

                    session = None
                    if cached_cart_id is not None:
                        session = db.query(ShoppingSession).filter(
                            ShoppingSession.cart_id == cached_cart_id,
                            ShoppingSession.status == CartStatus.ACTIVE,
                        ).order_by(ShoppingSession.id.desc()).first()

                    # شبكة أمان: لو ما في cart.id (مثلاً العربة مو مسجّلة
                    # بجدول carts بعد) أو ما لقينا جلسة عبر cart_id، جرّب
                    # المطابقة النصية المباشرة كخيار احتياطي فقط.
                    if session is None:
                        session = db.query(ShoppingSession).filter(
                            ShoppingSession.cart_rfid == cart_rfid,
                            ShoppingSession.status == CartStatus.ACTIVE,
                        ).order_by(ShoppingSession.id.desc()).first()

                    if session is None:
                        log.warning(
                            f"[WS] Frames from cart_rfid={cart_rfid} but no ACTIVE "
                            f"shopping session found (cart_id={cached_cart_id})"
                        )

                    new_session_id = session.id if session else None
                    # ── لوق واضح كل ما تتبدّل الجلسة المتابَعة لهذه العربة ──
                    # لو تبديل جلسات سريع ومتكرر ظهر هون (خصوصاً أرقام متتالية
                    # قريبة من بعض بفارق ثوانٍ)، هذا يعني الفرونت اند عم يعيد
                    # إنشاء جلسات جديدة بمعدّل غير طبيعي (bug بحلقة useEffect
                    # مثلاً) — راجع POSPage.jsx::initSession.
                    if new_session_id != cached_session_id:
                        log.warning(
                            colorize(
                                f"[WS] 🔄 cart_rfid={cart_rfid}: tracked session changed "
                                f"{cached_session_id} → {new_session_id}",
                                MAGENTA, bold=True,
                            )
                        )
                    cached_session_id = new_session_id
                finally:
                    db.close()

            if cached_session_id is None:
                # ما في جلسة تسوق نشطة مرتبطة بهذه العربة حالياً — تجاهل الإطار
                continue

            frame_count += 1
            if frame_count == 1:
                log.info(
                    f"[WS] First frame received cart_rfid={cart_rfid} "
                    f"session={cached_session_id} size={len(frame_bytes)}B"
                )
            elif frame_count % 100 == 0:
                log.info(
                    f"[WS] {frame_count} frames processed cart_rfid={cart_rfid} "
                    f"session={cached_session_id}"
                )

            await theft_service.analyze_frame(frame_bytes, cached_session_id)

    except WebSocketDisconnect:
        log.info(f"[WS] Camera disconnected for cart_rfid={cart_rfid}")
    except Exception as e:
        log.error(f"[WS] Camera stream error ({cart_rfid}): {e}")
    finally:
        manager.unregister_device(websocket, cart_rfid)