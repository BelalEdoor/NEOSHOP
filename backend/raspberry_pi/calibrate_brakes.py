"""
raspberry_pi/calibrate_brakes.py
==================================
أداة معايرة تفاعلية — تُشغَّل مرة واحدة (أو كل ما تغيّر تركيب الفرملة على
عجلة معيّنة) لتحديد زاويتَي "التحرير" و"القفل" الصحيحتين لكل سيرفو على حدة.

الاستخدام:
    pip install adafruit-circuitpython-pca9685 adafruit-circuitpython-motor
    python calibrate_brakes.py

الأوامر أثناء التشغيل لكل سيرفو (0-3):
    +  / -   تحريك درجة واحدة
    ++ / --  تحريك 5 درجات
    r        حفظ الزاوية الحالية كـ"تحرير كامل"
    l        حفظ الزاوية الحالية كـ"قفل ثابت"
    n        الانتقال للسيرفو التالي
    q        خروج وحفظ

النتيجة تُحفَظ في brake_calibration.json ويقرأها brake_controller.py تلقائياً.
"""
import json
import os
import sys

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), "brake_calibration.json")
SERVO_CHANNELS = [0, 1, 2, 3]
STEP_SMALL = 1
STEP_BIG = 5


def _init_hardware():
    try:
        import board
        import busio
        from adafruit_pca9685 import PCA9685
        from adafruit_motor import servo

        i2c = busio.I2C(board.SCL, board.SDA)
        pca = PCA9685(i2c)
        pca.frequency = 50
        servos = {ch: servo.Servo(pca.channels[ch]) for ch in SERVO_CHANNELS}
        return servos
    except Exception as e:
        print(f"⚠️  تعذّر الوصول للهاردوير الفعلي ({e})")
        print("    السكربت سيعمل بوضع محاكاة (طباعة فقط، بدون تحريك سيرفو حقيقي).")
        return None


class FakeServo:
    def __init__(self):
        self.angle = 90


def calibrate_one(channel: int, servos):
    s = servos[channel] if servos else FakeServo()
    angle = 90.0
    s.angle = angle
    release_angle = None
    lock_angle = None

    print(f"\n══════ معايرة السيرفو رقم {channel} (عجلة {channel}) ══════")
    print("الأوامر: + / - (درجة واحدة) | ++ / -- (5 درجات) | r (حفظ كتحرير) "
          "| l (حفظ كقفل) | n (التالي) | q (خروج وحفظ)")

    while True:
        print(f"  الزاوية الحالية: {angle:.0f}°"
              f"  [تحرير محفوظ: {release_angle if release_angle is not None else '—'}]"
              f"  [قفل محفوظ: {lock_angle if lock_angle is not None else '—'}]")
        cmd = input("  > ").strip().lower()

        if cmd == "+":
            angle = min(180, angle + STEP_SMALL)
        elif cmd == "-":
            angle = max(0, angle - STEP_SMALL)
        elif cmd == "++":
            angle = min(180, angle + STEP_BIG)
        elif cmd == "--":
            angle = max(0, angle - STEP_BIG)
        elif cmd == "r":
            release_angle = angle
            print(f"  ✓ حُفظت زاوية التحرير: {release_angle}°")
        elif cmd == "l":
            lock_angle = angle
            print(f"  ✓ حُفظت زاوية القفل: {lock_angle}°")
        elif cmd == "n":
            if release_angle is None or lock_angle is None:
                confirm = input("  ⚠️ لم تحفظ الزاويتين معاً — متابعة بدون معايرة كاملة؟ (y/n) ")
                if confirm.lower() != "y":
                    continue
            break
        elif cmd == "q":
            return release_angle, lock_angle, True
        else:
            print("  أمر غير معروف")
            continue

        s.angle = angle

    return release_angle, lock_angle, False


def main():
    print("═══════════════════════════════════════════════════════════")
    print("  NEOSHOP — معايرة فرامل السلة (سيرفو لكل عجلة)")
    print("═══════════════════════════════════════════════════════════")
    servos = _init_hardware()

    calibration = {}
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                calibration = json.load(f)
            print(f"تم تحميل معايرة سابقة من {CALIBRATION_FILE}")
        except Exception:
            pass

    for ch in SERVO_CHANNELS:
        release_angle, lock_angle, quit_now = calibrate_one(ch, servos)
        if release_angle is not None or lock_angle is not None:
            entry = calibration.get(str(ch), {})
            if release_angle is not None:
                entry["release"] = release_angle
            if lock_angle is not None:
                entry["lock"] = lock_angle
            calibration[str(ch)] = entry

        with open(CALIBRATION_FILE, "w") as f:
            json.dump(calibration, f, indent=2, ensure_ascii=False)

        if quit_now:
            break

    print(f"\n✓ تم حفظ المعايرة النهائية في: {CALIBRATION_FILE}")
    print(json.dumps(calibration, indent=2, ensure_ascii=False))
    print("\nالآن شغّل brake_controller.py عادي — رح يقرأ هذه القيم تلقائياً.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم الإيقاف يدوياً")
        sys.exit(0)