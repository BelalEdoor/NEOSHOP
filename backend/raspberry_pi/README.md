# NEOSHOP — سكربتات الراسبيري باي

هذا المجلد **لا يعمل على الباك اند** — بل يُنسخ إلى الراسبيري باي المثبَّت
فيزيائياً على كل عربة تسوق.

## 1) camera_stream.py — بثّ الكاميرا للتحليل

يلتقط إطارات من كاميرا العربة ويبعثها إلى الباك اند (نموذج الرؤية
الحاسوبية `cv/theft_logic.py`) عبر WebSocket ليقرّر إن كان هناك منتج
دخل السلة دون مسح باركود.

```bash
pip install opencv-python-headless websockets
python camera_stream.py --host <IP الباك اند> --rfid RFID-DEFAULT-001
```

## 2) brake_controller.py — تفعيل الفرامل الفعلية

يشترك في MQTT ويحرّك 4 سيرفوهات (عبر درايفر PCA9685) لقفل/تحرير عجلات
العربة عندما يصل أمر التفعيل من الباك اند (بعد 10 ثوانٍ من عدم إعادة مسح
المنتج المشبوه — راجع `cv/alert_handler.py` بالباك اند).

```bash
pip install paho-mqtt adafruit-circuitpython-pca9685 adafruit-circuitpython-motor
python brake_controller.py --broker <IP MQTT broker> --rfid RFID-DEFAULT-001
```

> **ملاحظة معايرة:** زوايا `LOCK_ANGLE` و`RELEASE_ANGLE` بداخل
> `brake_controller.py` قيم افتراضية — يجب ضبطها فعلياً حسب تركيب
> الفرامل على العربة بعد التجربة الميدانية.

## التشغيل التلقائي عند الإقلاع

على Raspberry Pi OS، يمكن تشغيل السكربتين كخدمتَي `systemd` منفصلتين
(كل عربة تحتاج نسخة واحدة من كل سكربت، بقيمة `--rfid` الخاصة بها) حتى
تبدأ المراقبة والفرامل تلقائياً عند تشغيل الجهاز، بدون تدخّل يدوي.
