"""
mqtt/client.py
==============
خدمة MQTT المركزية — تربط الـ Backend بـ ESP32 وRaspberry Pi.

Topics المستخدمة:
  cart/items           ← تحديثات السلة من/إلى Raspberry Pi
  cart/session         ← بيانات جلسة التسوق
  cart/status          ← تغييرات حالة السلة
  cart/rfid            ← إشعار قراءة RFID من Raspberry Pi
  payment/request      → من ESP32: طلب بيانات الفاتورة
  payment/status       ← من/إلى ESP32: حالة الدفع (invoice_ready, no_invoice,
                          payment_confirmed, وكمان refill_done → إلى ESP32)
  payment/coins        ← من ESP32: تتبع العملات المعدنية
  payment/bills        ← من ESP32: تتبع الأوراق النقدية
  payment/complete     ← من ESP32: اكتمال الدفع
  payment/refill_request ← من ESP32: نفدت أنابيب العملات، الدفعة متوقفة
                            مؤقتاً وبانتظار تعبئة صاحب المتجر (NEW)
"""
import json
import logging
import asyncio
import uuid
from typing import Callable, Dict, List, Optional
import paho.mqtt.client as mqtt
from core.config import settings

log = logging.getLogger("neoshop.mqtt")


# ─── Topic Constants ──────────────────────────────────────────────────────────
class Topics:
    # Shopping Topics
    CART_ITEMS   = "cart/items"
    CART_SESSION = "cart/session"
    CART_STATUS  = "cart/status"
    CART_RFID    = "cart/rfid"

    # Payment Topics
    PAYMENT_REQUEST  = "payment/request"
    PAYMENT_STATUS   = "payment/status"
    PAYMENT_COINS    = "payment/coins"
    PAYMENT_BILLS    = "payment/bills"
    PAYMENT_COMPLETE = "payment/complete"
    REFILL_REQUEST   = "payment/refill_request"  # NEW — من ESP32 عند نفاد أنابيب العملات

    # Theft Detection
    THEFT_ALERT  = "security/theft_alert"
    BRAKE_CONTROL = "security/brake"


class MQTTService:
    """
    خدمة MQTT Singleton — تُنشأ مرة واحدة عند بدء التطبيق.
    تُدير الاتصال مع Broker وتوزّع الرسائل على الـ handlers.
    """

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Callback لإرسال تحديثات WebSocket عند استلام رسائل MQTT
        self.on_payment_update: Optional[Callable] = None
        self.on_theft_alert: Optional[Callable] = None

    def setup(self, loop: asyncio.AbstractEventLoop):
        """يُستدعى مرة واحدة عند بدء FastAPI."""
        self._loop = loop
        # FIXED — كان client_id ثابت ("neoshop-backend"). لو صار فيه أكتر من
        # عملية uvicorn شغالة بنفس الوقت (زومبي process من إعادة تشغيل سابقة
        # ما اتقفلت صح، أو تشغيل مزدوج بالغلط)، البروكر بيفصل العميل الأقدم
        # تلقائيًا كل ما عميل جديد يتصل بنفس الـ ID — وهاد بيسبب انقطاعات
        # متقطعة وغامضة. صرنا نولّد ID فريد لكل عملية، بنفس فكرة الـ ESP32.
        client_id = f"neoshop-backend-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

        if settings.MQTT_USERNAME:
            self._client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        # FIXED — بدون هذا، لو انقطع الاتصال لأي سبب (شبكة، إعادة تشغيل
        # البروكر، إلخ) العميل كان يضل مقطوع للأبد لحد إعادة تشغيل الباك
        # اند يدويًا. هيك paho بيعيد المحاولة تلقائيًا بفواصل متزايدة
        # (1s → 2s → ... → حتى 120s) بدل ما يستسلم.
        self._client.reconnect_delay_set(min_delay=1, max_delay=120)

        try:
            # FIXED — كان connect() (blocking). لو الـ broker مش متاح لحظة
            # إقلاع الباك اند (لسا ما شتغل، تأخر بالشبكة، إلخ)، connect()
            # كانت ترمي Exception فورًا، والـ except كان يلقطه *قبل* ما
            # يوصل لسطر loop_start() — يعني ما كان يشتغل أي thread بالخلفية
            # أبدًا، و self._connected تضل False للأبد (حتى لو الـ broker
            # رجع يشتغل بعدها بثانية) لحد إعادة تشغيل الباك اند يدويًا.
            # reconnect_delay_set فوق بيتحكم بإعادة الاتصال بعد انقطاع من
            # اتصال ناجح سابقًا فقط — مش بمحاولة أولى فشلت من الأساس.
            #
            # connect_async() ما بتحجب (non-blocking) وما بترمي Exception
            # لو الـ broker غير متاح لحظة الاستدعاء — بتفوّض عملية الاتصال
            # (وإعادة المحاولة بالكامل حسب reconnect_delay_set) لـ
            # loop_start()، يلي رح يستمر يحاول يتصل بالخلفية بغض النظر
            # عن حالة الـ broker وقت إقلاع الباك اند.
            self._client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
            self._client.loop_start()
            log.info(f"[MQTT] Connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} as {client_id}")
        except Exception as e:
            # لو صار استثناء هون (نادر مع connect_async، مثلاً خطأ بإعداد
            # TLS أو باراميترات غلط)، على الأقل بنسجله بوضوح كخطأ (مش
            # warning) لأنه معناه فعليًا "ما رح يشتغل MQTT إطلاقًا".
            log.error(f"[MQTT] Failed to start MQTT loop: {e} — MQTT will be unavailable until restart")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            log.info("[MQTT] Connected to broker ✓")
            # الاشتراك في جميع topics المطلوبة
            topics = [
                Topics.PAYMENT_REQUEST,
                Topics.PAYMENT_COINS,
                Topics.PAYMENT_BILLS,
                Topics.PAYMENT_COMPLETE,
                Topics.REFILL_REQUEST,
                Topics.CART_RFID,
            ]
            for topic in topics:
                client.subscribe(topic, qos=1)
                log.info(f"[MQTT] Subscribed to: {topic}")
        else:
            log.error(f"[MQTT] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc == 0:
            log.info("[MQTT] Disconnected cleanly (shutdown)")
        else:
            log.warning(f"[MQTT] Unexpected disconnect (rc={rc}) — paho will auto-reconnect with backoff")

    def _on_message(self, client, userdata, msg):
        """معالجة الرسائل الواردة من ESP32 وRaspberry Pi."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic   = msg.topic
            log.debug(f"[MQTT] Received [{topic}]: {payload}")

            # إرسال للـ handlers المسجّلة
            if topic in self._handlers:
                for handler in self._handlers[topic]:
                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            handler(topic, payload), self._loop
                        )
        except json.JSONDecodeError:
            log.warning(f"[MQTT] Invalid JSON on topic {msg.topic}")
        except Exception as e:
            log.error(f"[MQTT] Handler error: {e}")

    def subscribe(self, topic: str, handler: Callable):
        """تسجيل handler لـ topic معيّن."""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        """نشر رسالة على topic معيّن."""
        # FIXED — self._connected بينحدّث بس جوا on_connect/on_disconnect،
        # يلي بتشتغل بخيط شبكة paho المنفصل بشكل غير متزامن. ممكن يصير
        # انقطاع لحظي فعلي بالسوكيت بينما self._connected لسا True عندنا
        # (الـ callback لسا ما وصل). is_connected() من paho نفسه بيعكس
        # حالة السوكيت الحقيقية بلحظتها، فمنستخدمه كفحص إضافي حي.
        if not self._client or not self._connected or not self._client.is_connected():
            log.warning(
                f"[MQTT] Not connected — cannot publish to {topic} "
                f"(flag={self._connected}, live={self._client.is_connected() if self._client else None})"
            )
            return False
        try:
            result = self._client.publish(topic, json.dumps(payload), qos=qos)
            if result.rc != 0:
                # FIXED — كانت هاي الحالة (rc != 0، أشيعها MQTT_ERR_NO_CONN=4)
                # تُسجَّل فقط ضمن log.debug العام تحتها، يلي غالباً مستوى
                # تسجيله أوطى من المعروض، فكانت تفشل بصمت تام بدون أي أثر
                # بالسجل. صرنا نسجلها صراحة كـ warning مع رمز الخطأ.
                log.warning(f"[MQTT] Publish to {topic} returned rc={result.rc} (not queued)")
                return False
            log.debug(f"[MQTT] Published [{topic}]: {payload}")
            return True
        except Exception as e:
            log.error(f"[MQTT] Publish error: {e}")
            return False

    # ─── Helper publish methods ────────────────────────────────────────────

    def publish_cart_status(self, session_id: int, status: str, rfid: str = ""):
        """إرسال تحديث حالة السلة إلى Raspberry Pi."""
        self.publish(Topics.CART_STATUS, {
            "session_id": session_id,
            "status": status,
            "cart_rfid": rfid,
        })

    def publish_invoice_to_esp32(self, invoice_data: dict):
        """إرسال بيانات الفاتورة إلى ESP32 عبر MQTT."""
        self.publish(Topics.PAYMENT_STATUS, {
            "event": "invoice_ready",
            **invoice_data
        })

    def publish_payment_complete(self, cart_rfid: str, payment_data: dict):
        """إشعار اكتمال الدفع."""
        self.publish(Topics.PAYMENT_STATUS, {
            "event": "payment_confirmed",
            "cart_rfid": cart_rfid,
            **payment_data
        })

    def publish_refill_done(self, payment_id: int):
        """
        إشعار الـ ESP32 بأن صاحب المتجر عبّى أنابيب العملات، وأنه يقدر
        يكمل صرف الباقي المتبقي على نفس الفاتورة (بدون إلغاء أو إعادة البدء).
        """
        self.publish(Topics.PAYMENT_STATUS, {
            "event": "refill_done",
            "payment_id": payment_id,
        })

    def publish_theft_alert(self, session_id: int, alert_type: str, details: dict):
        """إرسال تنبيه سرقة."""
        self.publish(Topics.THEFT_ALERT, {
            "session_id": session_id,
            "alert_type": alert_type,
            **details
        })

    def publish_brake_command(self, cart_rfid: str, activate: bool) -> bool:
        """
        التحكم بفرامل العربة (٤ سيرفوهات على درايفر PCA9685 بالراسبيري باي).
        يُرجع True إذا نُشرت الرسالة فعلاً على الـ broker — يستخدمها
        cv/alert_handler.py ليقرّر هل يعتمد على مسار الـ WebSocket البديل.
        """
        return self.publish(Topics.BRAKE_CONTROL, {
            "cart_rfid": cart_rfid,
            "brake": "activate" if activate else "release",
        })

    @property
    def is_connected(self) -> bool:
        return self._connected


# ─── Singleton Instance ───────────────────────────────────────────────────────
mqtt_service = MQTTService()