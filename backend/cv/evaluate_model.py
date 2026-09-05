"""
cv/evaluate_model.py
=====================
سكربت مستقل — يُشغَّل يدوياً من الطرفية، وليس جزءاً من خط أنابيب الكشف
الحي بالعربة (theft_logic.py / detector.py).

⚠️ ليش منفصل ومش داخل analyze_frame؟
Precision/Recall/mAP هي مقاييس *تقييم* تحتاج "أرض حقيقة" (ground-truth
labels) معروفة مسبقاً لكل صورة — أي تعرف مسبقاً وين بالضبط المفروض
يكون كل منتج بكل صورة تحقّق. فريمات الكاميرا الحية أثناء تشغيل العربة
الفعلي ما إلها تصنيف "صحيح" معروف مسبقاً، فمافي طريقة تحسب منها هالمقاييس
بشكل مباشر. كل اللي تقدر تشوفه لحظياً بالفريم الحي هو "confidence"
(ثقة الكشف) لكل صندوق — وهو موجود أصلاً باللوق (راجع _factors_str
بـ theft_logic.py، الحقل conf=).

الاستخدام:
    python -m cv.evaluate_model --weights path/to/best.pt --data path/to/data.yaml

data.yaml هو نفس ملف الإعداد المستخدم وقت تدريب نموذج YOLO (يحدّد مسار
صور/تسميات مجموعة التحقّق val/).
"""
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a trained YOLO model: Precision, Recall, mAP50, mAP50-95"
    )
    parser.add_argument("--weights", required=True, help="Path to trained .pt weights")
    parser.add_argument("--data", required=True, help="Path to data.yaml (validation set)")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    metrics = model.val(data=args.data, imgsz=args.imgsz)

    # ملاحظة: "accuracy" مش مصطلح رسمي بكشف الأجسام (object detection)،
    # أقرب مكافئ فعلي إلها هو الـ Precision (من كل كشف قاله الموديل
    # "هذا منتج"، كم فعلاً كان صحيح). لو قصدك "accuracy" التصنيف
    # التقليدي (single-label classification)، لازم تحدد أي موديل بالضبط
    # (مثال: TinyCurrencyNet لتصنيف فئة العملة) — هاد السكربت خاص بموديل
    # YOLO الكشف فقط.
    precision = float(metrics.box.mp)   # mean Precision عبر كل الفئات
    recall = float(metrics.box.mr)      # mean Recall عبر كل الفئات
    map50 = float(metrics.box.map50)    # mAP@IoU=0.5
    map50_95 = float(metrics.box.map)   # mAP@IoU=0.5:0.95

    print("=" * 55)
    print(f" Precision (≈ accuracy):  {precision:.4f}")
    print(f" Recall:                  {recall:.4f}")
    print(f" mAP50:                   {map50:.4f}")
    print(f" mAP50-95:                {map50_95:.4f}")
    print("=" * 55)

    # تفصيل لكل فئة (منتج) على حدة — مفيد لمعرفة أي منتج ضعيف تحديداً
    if hasattr(metrics.box, "ap_class_index"):
        names = model.names
        for i, cls_idx in enumerate(metrics.box.ap_class_index):
            cls_name = names.get(int(cls_idx), str(cls_idx)) if isinstance(names, dict) else names[int(cls_idx)]
            print(f"   - {cls_name:<20} mAP50={metrics.box.ap50[i]:.4f}")


if __name__ == "__main__":
    main()