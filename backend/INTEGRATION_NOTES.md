# ملاحظات الدمج — موديل التحليلات + محرّك التوصيات

هذا الملف يوثّق ما تمت إضافته للمشروع الأصلي (لا شيء من منطق المشروع القديم
تم حذفه أو تغييره جوهرياً — كل ما يلي إضافي).

## 1. موديل التحليلات (Manager Analytics)

- حزمة جديدة: `analytics/` (router, service, sales, schemas).
- مسجّلة في `main.py` على: `/api/admin/analytics/...`
- Endpoints: `sales`, `top-products`, `inventory`, `product-performance`,
  `category-performance`, `inventory-alerts`, `sales-trends`, `insights`.
- تعمل مباشرة بدون أي إعداد إضافي — تعتمد فقط على جداول `products`,
  `cart_items`, `invoices` الموجودة أصلاً.
- الواجهة: قسم "تحليلات المتجر" الجديد داخل `AdminOverview.jsx` (رسوم بيانية
  عبر `recharts`، بطاقات إحصائية، تنبيهات مخزون، رؤى ذكية).

## 2. محرّك التوصيات (Recommendation Engine)

- حزمة جديدة: `recommendation/` (recommender, health_checker, filters,
  alternative_generator, user_profile, preference_builder, embeddings,
  vector_store... إلخ).
- راوترين جديدين مسجّلين في `main.py`:
  - `GET /api/recommendations/{product_id}` — تحليل منتج واحد (صحة + بدائل
    آمنة + توصيات مشابهة).
  - `GET /api/ai/recommendations/{user_id}` — توصيات عامة بناءً على سجل
    مشتريات المستخدم.
- تم توسيع `routers/analysis.py` (بدون حذف أي منطق موجود) بإضافة
  `product_health` و`recommendations` لاستجابات:
  - `POST /api/analysis/ai/{product_id}`
  - `GET  /api/analysis/barcode-scan/{barcode}`
- تم توسيع موديل `Product` بحقول اختيارية جديدة (لا تكسر أي بيانات قديمة):
  `subcategory`, `protein_g`, `fat_g`, `saturated_fat_g`, `carbohydrates_g`,
  `fiber_g`, `cholesterol_mg`, `is_vegan`, `is_vegetarian`, `is_gluten_free`,
  `is_lactose_free`.
- **إصلاح مهم**: كانت `analyze_product()` في المشروع الأصل (file2) تستدعي
  `generate_safe_alternatives()` بدون تمرير `db` session، مما كان سيسبب
  فشلاً فعلياً عند الاستخدام. تم إصلاح هذا في `recommendation/analyze_product.py`.

### كيف تُفعّل محرّك التوصيات بالكامل

المحرّك يحتاج فهرس بحث دلالي (FAISS) مبني من كتالوج منتجات غني بالتصنيفات
الفرعية والمعلومات الغذائية:

1. **(اختياري) إثراء كتالوج المنتجات**: بدل `seed.py` البسيط، يمكنك تشغيل
   المولّد الجاهز الذي يبني منتجات واقعية بكل الحقول الجديدة (subcategory،
   nutrition، dietary labels):
   ```bash
   python database/seed_products.py
   ```
   هذا يقرأ من `database/products.csv` (منتجات جاهزة توليدها عبر
   `database/generators/*.py`) ويملأ جدول `products` + `product_allergens`.
   ⚠️ يحذف المنتجات الحالية أولاً — لا تشغّله على قاعدة بيانات إنتاج فيها
   بيانات مهمة بدون نسخ احتياطي.

2. **بناء فهرس التوصيات (FAISS + embeddings)**:
   ```bash
   cd recommendation
   python build_recommendation.py
   ```
   هذا يولّد `products.index` و`products.pkl` في جذر الباك اند، ويحتاج
   `DATABASE_URL` في `.env` + حزم `sentence-transformers` و`faiss-cpu`
   (موجودة بـ `requirements.txt`).

3. تم تضمين نسخة **ابتدائية جاهزة** من `products.index` و`products.pkl` في
   هذا المشروع للتجربة الفورية — لكنها **يجب إعادة بناؤها** (الخطوة 2) بعد
   أي تعديل على كتالوج المنتجات حتى تبقى التوصيات دقيقة ومطابقة لـ IDs
   الفعلية بقاعدة بياناتك.

### التعامل الآمن مع غياب المكتبات الثقيلة

كل استدعاء لمحرّك التوصيات (في `routers/analysis.py` و`routers/recommendations.py`
و`routers/ai.py`) مغلّف بمعالجة أخطاء: إن لم تُثبَّت `faiss-cpu` أو
`sentence-transformers` بعد، أو لم يُبنَ الفهرس، تستمر بقية الـ API بشكل
طبيعي (الفحص الأساسي للحساسية والحالات الصحية القديم يبقى يعمل دائماً لأنه
لا يعتمد على الفهرس إطلاقاً).
