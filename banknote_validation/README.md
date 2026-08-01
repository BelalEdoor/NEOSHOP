# Currency Denomination Classifier (20 / 50 NIS)

## شو صار

فحصت الصور اللي بعتها (RGB + UV)، ولقيت إنها متقسمة تلقائيًا لجلسات (كل جلسة بترجع الترقيم لـ 001):

| المصدر | الجلسة | عدد الصور | التصنيف |
|---|---|---|---|
| RGB | 140336–140352 | 6 | فاضية (ما في ورقة نقدية) — استبعدتها |
| RGB | 140430–141000 | 100 | **20** (ورقة خضرا) |
| RGB | 141915–142446 | 100 | **50** (ورقة بنفسجية/حمرا) |
| UV | 141004–141639 | 100 | **20** |
| UV | 142450–143125 | 100 | **50** |

المجموع: 200 صورة لفئة "20" و200 صورة لفئة "50" (RGB + UV مع بعض عشان الموديل يشتغل صح على النوعين).

**ملاحظة:** ما استخدمت خط preprocessing الكلاسيكي (grayscale → blur → adaptive threshold → morphology) زي ما طلبت — الموديل بياخد الصورة الخام مباشرة، بس بيعمل resize (160×160) و normalize (0–1) جوه كود الـ inference نفسه.

## النتيجة

دربت CNN خفيف (depthwise-separable، ~150K parameter، من الصفر بدون pretrained weights عشان يشتغل offline وما يعتمد على تحميل أوزان من الإنترنت):

```
Best validation accuracy: 1.0000 (34/34 على split التحقق)
Confusion matrix: [[34, 0], [0, 26]]  -> صفر أخطاء
```

جربته كمان يدويًا على صور RGB و UV من الفئتين وطلعت النتايج كلها صح مع confidence عالي (0.68–0.99).

## الملفات

```
organize_dataset.py   - يرتب صور الالتقاط الخام (RGB/UV) في dataset/20 و dataset/50
train.py               - يدرب الموديل ويصدره ONNX
infer.py                - سكربت جاهز يستخدم ONNX Runtime للتصنيف
outputs/
  best_model.pt              - checkpoint بايثون (لو حبيت تكمل تدريب لاحقًا)
  currency_classifier.onnx   - **الموديل النهائي اللي بتحطه على الـ Raspberry Pi (مدرب وجاهز، مش لازم تعيد التدريب)**
  class_names.json           - ["20", "50"] (ترتيب الـ output classes)
  training_report.txt        - دقة التحقق + confusion matrix
```

## لو بدك تعيد التدريب بنفسك (اختياري — الموديل الجاهز موجود بالفعل)

الموديل المدرب `outputs/currency_classifier.onnx` جاهز للاستخدام مباشرة على الـ Pi. بس لو حابب تعيد التدريب (مثلاً بعد ما تضيف صور جديدة):

1. ثبّت المتطلبات: `pip install -r requirements.txt`
2. فك ضغط الأرشيفين الخام **جنب هاي السكربتات** بهاي البنية بالظبط:
   ```
   currency_classifier/
     raw_rgb/capture/*.jpg   <- فك capture.7z هون
     raw_uv/capture/*.jpg    <- فك capture1.7z هون
   ```
   (على الماك: `7z x capture.7z -oraw_rgb` و `7z x capture1.7z -oraw_uv`، أو أي برنامج فك ضغط عادي بس تأكد المجلد الناتج اسمه `raw_rgb`/`raw_uv` وفيه مجلد `capture` جواه)
3. شغّل بالترتيب:
   ```bash
   python3 organize_dataset.py
   python3 train.py
   ```

## الاستخدام على الـ Raspberry Pi

بس محتاج (مش لازم PyTorch):
```bash
pip install onnxruntime opencv-python numpy
```

```python
from infer import CurrencyClassifier
import cv2

clf = CurrencyClassifier()  # يحمّل outputs/currency_classifier.onnx تلقائيًا
frame_bgr = cv2.imread("captured_note.jpg")   # أو فريم من الكاميرا
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
label, confidence = clf.predict(frame_rgb)
print(label, confidence)   # مثلاً: "20" 0.9986
```

`predict()` بترجع `("20"|"50", confidence)` وبتقدر تربطها مباشرة مع `paper_detector.py` بعد ما يحدد إن في ورقة نقدية بالإطار.

## لو بدك تعيد التدريب على صور جديدة

1. حط الصور الجديدة بنفس نمط التسمية (`rgb_capture_YYYYMMDD_HHMMSS_NNN.jpg` أو `uv_capture_...`).
2. عدّل `SESSION_LABELS_RGB` / `SESSION_LABELS_UV` في `organize_dataset.py` حسب ترتيب الجلسات الجديدة.
3. شغّل: `python3 organize_dataset.py && python3 train.py`

---

## وحدة كشف التزوير (UV Authenticity / Anomaly Detection)

### ليش anomaly detection مش classifier عادي؟

عنا بس صور عملات **أصلية** تحت UV — ما في ولا عينة مزورة نتدرب عليها. فما فيني أبني classifier بفئتين (أصلي/مزور) لأنه ما في شي "مزور" يتعلم شكله. البديل المنطقي: **autoencoder** يتدرب فقط على صور UV الأصلية، يتعلم يعيد بناءها منيح جدًا (الخيوط الفلورية، أنماط الحبر...). أي صورة UV بتختلف عن هاد النمط — سواء عملة مزورة أو صورة ملتقطة بظروف غريبة — بيطلع خطأ إعادة البناء (reconstruction error) فيها أعلى من صور الأصلي، فبتنعلّم "مشكوك فيها".

**⚠️ مهم:** الحد (threshold) معايَر بس على صور أصلية (ما في عينة مزورة نختبر عليها فعليًا). اعتبر النتيجة "مشكوك فيها" = يحتاج فحص إضافي، مش "تأكيد إنها مزورة"، لحد ما تجرّبه على عملة مزورة حقيقية وتضبط `THRESHOLD_MARGIN` حسب النتيجة.

### تقسيمة الداتا

- بتاخد بس صور `uv_*.jpg` من `dataset/20` و `dataset/50` (200 صورة UV أصلية إجمالًا — 100 لكل فئة). صور RGB ما بتستخدم هون لأنها ما بتحمل خصائص التوهج تحت UV.
- الفئتين (20 و50) بتترمّجوا مع بعض بنفس الـ dataset — الهدف إن الـ autoencoder يتعلم "شكل التوهج الأصلي تحت UV" بشكل عام، مش خاص بفئة وحدة.
- التقسيم train/val بطريقة **stratified** (85% تدريب / 15% تحقق) — يعني نسبة 20/50 محفوظة بكل من التدريب والتحقق، مش عشوائي بالكامل.

### الملفات الجديدة

```
train_authenticity.py   - يدرب الـ autoencoder على صور UV الأصلية ويصدره ONNX
infer_authenticity.py   - سكربت ONNX Runtime يحسب reconstruction error ويقارنه بالـ threshold
outputs/ (بعد التدريب):
  best_autoencoder.pt          - checkpoint بايثون
  autoencoder_uv.onnx          - الموديل النهائي (يستخدم على الـ Pi)
  authenticity_threshold.json  - الـ threshold المحسوب + إحصائيات الأخطاء
  authenticity_report.txt      - ملخص التدريب والمعايرة
```

### كيف تدرب

```bash
pip install -r requirements.txt
python3 organize_dataset.py   # إذا ما شغّلته قبل
python3 train_authenticity.py
```

### كيف تستخدمه على الـ Pi

```python
from infer_authenticity import AuthenticityChecker
import cv2

checker = AuthenticityChecker()  # يحمّل outputs/autoencoder_uv.onnx + threshold تلقائيًا
frame_bgr = cv2.imread("uv_captured_note.jpg")
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
is_genuine, error, threshold = checker.check(frame_rgb)
print("genuine" if is_genuine else "suspicious", error, threshold)
```

بتقدر تربطه مع `infer.py` (تصنيف 20/50) بحيث تشغّل الاثنين على نفس الالتقاطة: `infer.py` يحدد الفئة من صورة RGB، و`infer_authenticity.py` يفحص صورة UV لنفس الورقة إذا في شبهة تزوير.