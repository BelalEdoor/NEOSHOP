# NEOSHOP — نظام تحديد موقع العربة (ArUco)

## البنية
```
raspberry_pi/            ← يعمل على العربة
  aruco_reader.py        ← قراءة العلامات وإرسالها للباك اند
  config.py              ← الإعدادات (IP السيرفر، رقم العربة، القاموس)
  generate_markers.py    ← توليد صور العلامات للطباعة
  requirements.txt

backend/                 ← يُدمج في مشروع FastAPI الحالي
  models/navigation.py   ← Section, Shelf, CartLiveStatus, MarkerReadLog
  models/__init__.py     ← (استبدل الموجود) يسجل الجداول الجديدة
  schemas/navigation.py
  routers/navigation.py
  seed_navigation.py     ← تعبئة الأقسام بإحداثيات الخريطة

frontend/
  StoreMap.jsx           ← خريطة المتجر مطابقة للتصميم المرجعي
```

## خطوات التركيب

### 1) الباك اند
انسخ الملفات إلى المشروع بنفس المسارات، ثم أضف سطرين في `main.py`:
```python
from routers import navigation
app.include_router(navigation.router, prefix="/api/navigation", tags=["Navigation"])
```
ثم شغّل التعبئة:
```bash
python3 seed_navigation.py
```
اختياري — متغيرات بيئة: `NAV_DEVICE_KEY` (مفتاح أجهزة الباي)،
`STORE_WIDTH_M` و `STORE_DEPTH_M` (افتراضياً 12 × 8).

### 2) الراسباري باي
```bash
pip3 install -r requirements.txt
python3 generate_markers.py     # اطبع العلامات والصقها (1..3 أقسام، 4 مدخل، 5 مخرج)
# عدّل config.py: BACKEND_URL و CART_ID
python3 aruco_reader.py
```

### 3) الفرونت اند
```jsx
import StoreMap from "./StoreMap";
<StoreMap cartId={1} apiBase="http://YOUR_SERVER:8000" />
```

## تدفق البيانات
```
كاميرا العربة ──ArUco──▶ aruco_reader.py ──POST /marker-read──▶ FastAPI
                                                    │
                            CartLiveStatus (upsert) + MarkerReadLog
                                                    │
الفرونت اند ◀──GET /cart/{id} كل ثانيتين──── النقطة الحمراء تتحرك
```

## اختبار بدون كاميرا (محاكاة قراءة علامة)
```bash
curl -X POST http://localhost:8000/api/navigation/marker-read \
  -H "Content-Type: application/json" \
  -H "X-Device-Key: neoshop-pi-secret-key" \
  -d '{"cart_id": 1, "marker_id": 2}'
```
يجب أن تقفز النقطة الحمراء إلى القسم 2 (5.5, 4.5).
