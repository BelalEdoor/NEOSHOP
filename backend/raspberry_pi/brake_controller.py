"""
raspberry_pi/brake_controller.py
==================================
يعمل على الراسبيري باي المثبَّت على العربة. يشترك في MQTT topic
`security/brake` وينفّذ أمر تفعيل/تحرير فرامل العربة فعلياً — أربعة
سيرفوهات (واحد لكل عجلة) متصلة بدرايفر PCA9685 (I2C) على الراسبيري باي.

⚠️ مهم — لماذا الزوايا هنا "لكل سيرفو على حدة" وليست ثابتة موحّدة:
    الفرملة آلية احتكاكية (ذراع أكريليك يضغط على إطار العجلة)، مركَّبة
    يدوياً بغراء حراري على كل عجلة من الأربع. بما أن كل تركيب مختلف
    قليلاً، فزاوية "القفل" و"التحرير" الصحيحتين تختلفان من سيرفو لآخر.
    استخدم سكربت `calibrate_brakes.py` المرفق لتحديد القيمة الصحيحة لكل
    عجلة على حدة، وسيتم حفظها في `brake_calibration.json` ويقرأه هذا
    السكربت تلقائياً.

رسالة MQTT المستلمة (يبعثها الباك اند — راجع mqtt/client.py::publish_brake_command
وcv/alert_handler.py عند انتهاء مهلة الـ 10 ثوانٍ دون إعادة مسح):

    topic: security/brake
    payload: {"cart_rfid": "RFID-DEFAULT-001", "brake": "activate" | "release"}

التشغيل:
    pip install paho-mqtt adafruit-circuitpython-pca9685 adafruit-circuitpython-motor
    # أولاً — معايرة كل سيرفو (مرة واحدة فقط، أو كلما تغيّر التركيب):
    python calibrate_brakes.py
    # بعدها التشغيل العادي:
    python brake_controller.py --broker 192.168.1.50 --rfid RFID-DEFAULT-001
"""
import argparse
import json
import logging
import os
import time

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("brake_controller")

# ─── إعدادات عامة ──────────────────────────────────────────────────────────────
NUM_SERVOS      = 4                 # سيرفو واحد لكل عجلة
SERVO_CHANNELS  = [0, 1, 2, 3]      # قنوات PCA9685 المتصلة بالسيرفوهات الأربعة
CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), "brake_calibration.json")

# قيم افتراضية "احتياطية" فقط تُستخدَم إن لم توجد معايرة محفوظة لقناة معيّنة —
# هذه أرقام عشوائية غير مضمونة؛ لا تعتمد عليها، استخدم calibrate_brakes.py.
DEFAULT_RELEASE_ANGLE = 0
DEFAULT_LOCK_ANGLE    = 90

_pca = None
_servo_kit = {}   # {channel: servo.Servo}


def _load_calibration() -> dict:
    """
    يقرأ زوايا القفل/التحرير المعايَرة فعلياً لكل قناة (يكتبها
    calibrate_brakes.py). الشكل:
        {"0": {"release": 12, "lock": 68}, "1": {...}, ...}
    """
    if not os.path.exists(CALIBRATION_FILE):
        log.warning(
            f"⚠️ لا يوجد ملف معايرة ({CALIBRATION_FILE}) — سيتم استخدام قيم "
            f"افتراضية غير مضمونة ({DEFAULT_RELEASE_ANGLE}°/{DEFAULT_LOCK_ANGLE}°) "
            f"لكل السيرفوهات. شغّل calibrate_brakes.py أولاً للحصول على قفل موثوق."
        )
        return {}
    try:
        with open(CALIBRATION_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"تعذّر قراءة ملف المعايرة ({e}) — سيتم استخدام القيم الافتراضية")
        return {}


_calibration = _load_calibration()


def _angle_for(channel: int, kind: str) -> float:
    """kind = 'release' | 'lock'"""
    cal = _calibration.get(str(channel))
    if cal and kind in cal:
        return cal[kind]
    return DEFAULT_RELEASE_ANGLE if kind == "release" else DEFAULT_LOCK_ANGLE


def _init_hardware():
    """تهيئة درايفر PCA9685 عبر I2C. تُستدعى مرة واحدة عند بدء التشغيل."""
    global _pca, _servo_kit
    try:
        import board
        import busio
        from adafruit_pca9685 import PCA9685
        from adafruit_motor import servo

        i2c = busio.I2C(board.SCL, board.SDA)
        _pca = PCA9685(i2c)
        _pca.frequency = 50  # 50Hz قياسي لسيرفوهات RC

        _servo_kit = {ch: servo.Servo(_pca.channels[ch]) for ch in SERVO_CHANNELS}
        log.info(f"✓ تم تهيئة {NUM_SERVOS} سيرفوهات عبر PCA9685")
    except Exception as e:
        log.warning(
            f"تعذّر تهيئة الهاردوير الفعلي ({e}) — سيعمل السكربت بوضع "
            f"المحاكاة (طباعة الأوامر فقط بدون تحريك سيرفو حقيقي)."
        )
        _pca = None
        _servo_kit = {}


def _set_servo(channel: int, angle: float):
    if _servo_kit:
        _servo_kit[channel].angle = angle
    else:
        log.info(f"[SIM] تحريك السيرفو {channel} إلى الزاوية {angle}°")


def activate_brake():
    log.warning("🔒 تفعيل فرامل العربة — قفل العجلات الأربع (زوايا معايَرة لكل عجلة)")
    for ch in SERVO_CHANNELS:
        angle = _angle_for(ch, "lock")
        _set_servo(ch, angle)
        log.info(f"  عجلة {ch}: → {angle}°")


def release_brake():
    log.info("🔓 تحرير فرامل العربة — العجلات حرة")
    for ch in SERVO_CHANNELS:
        angle = _angle_for(ch, "release")
        _set_servo(ch, angle)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("✓ متصل بـ MQTT broker")
        client.subscribe("security/brake", qos=1)
    else:
        log.error(f"فشل الاتصال بـ MQTT (rc={rc})")


def make_on_message(cart_rfid: str):
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            return

        if payload.get("cart_rfid") != cart_rfid:
            return  # ليس أمراً موجَّهاً لهذه العربة

        cmd = payload.get("brake")
        if cmd == "activate":
            activate_brake()
        elif cmd == "release":
            release_brake()
    return on_message


def main():
    parser = argparse.ArgumentParser(description="NEOSHOP — Cart brake controller (Raspberry Pi)")
    parser.add_argument("--broker", default=os.environ.get("MQTT_BROKER_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MQTT_BROKER_PORT", 1883)))
    parser.add_argument("--rfid", default=os.environ.get("CART_RFID", "RFID-DEFAULT-001"))
    args = parser.parse_args()

    if not _calibration:
        log.warning(
            "⚠️ تشغيل بدون معايرة — يُنصح بشدة بتشغيل calibrate_brakes.py أولاً "
            "قبل الاعتماد على هذا النظام فعلياً في المتجر."
        )

    _init_hardware()
    release_brake()  # حالة ابتدائية آمنة: العجلات حرة

    client = mqtt.Client(client_id=f"neoshop-brake-{args.rfid}")
    client.on_connect = on_connect
    client.on_message = make_on_message(args.rfid)
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    log.info(f"جاري الاتصال بـ {args.broker}:{args.port} لمراقبة فرامل العربة {args.rfid}...")
    client.connect(args.broker, args.port, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()