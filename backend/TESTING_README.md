# NEOSHOP — Lightweight Test Setup (Backend Only)

This is the REAL NEOSHOP backend (your team's actual repo), with the
recommendation engine patch already applied, set up to run WITHOUT the
heavy computer-vision dependencies (no torch/ultralytics/opencv needed).

Theft detection (camera + YOLO) is automatically disabled and the app
logs a warning instead of crashing — everything else (auth, products,
cart, sessions, payments, and the recommendation engine) works exactly
as the full system would.

This has already been tested end-to-end (register → set allergies →
scan a product → get a block/warning + substitute) — see the test
output you were shown in chat. Following these exact steps reproduces
the same result.

## 1. Install Python dependencies (lightweight — no torch/opencv)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          (Windows)
# source venv/bin/activate     (Mac/Linux)

pip install -r requirements-lite.txt
```

This skips `opencv-python-headless`, `ultralytics`, `torch`, `torchvision`
— those are only used by `cv/theft_detection.py`, which now degrades
gracefully and logs a warning instead of crashing when they're missing.

## 2. Configure environment

Create a `.env` file in the `backend/` folder:

```
DATABASE_URL=sqlite:///./neoshop.db
SECRET_KEY=any-random-string-for-local-testing
ENV=development
```

SQLite (a single local file, no MySQL server needed) is the fastest way
to test this on a laptop. Switch to your real MySQL `DATABASE_URL` later
once you're past local testing — nothing in the code needs to change.

## 3. Start the backend

```bash
uvicorn main:app --reload
```

You should see something like:
```
[CV] opencv-python not installed — frame analysis disabled
[CV] YOLOv8 not installed — theft detection disabled
✓ Database tables created
WARNING: [MQTT] Could not connect ... — running without MQTT
✓ Admin user created (admin@neoshop.com / admin1234)
✓ Default carts created
✓ Products seeded
✅ NEOSHOP Backend ready!
```

All of those warnings are expected and harmless for this lightweight
test — the app already auto-creates tables and seeds default products
and an admin account on first run (that's `main.py`'s existing
`_auto_seed()`, untouched).

## 4. Seed the recommendation engine's allergen/condition lists

In a second terminal (keep the server running):

```bash
cd backend
python seed_recommendation_engine.py
```

This adds 12 allergens + 3 health conditions (Diabetes, Hypertension,
Obesity) — one-time, safe to re-run.

## 5. Open the interactive API docs

Go to: **http://127.0.0.1:8000/docs**

This is FastAPI's auto-generated page — every endpoint is listed and
clickable, no separate tool needed.

## 6. Test the flow yourself

### Register
`POST /api/auth/register`
```json
{"name": "Your Name", "email": "you@test.com", "password": "test1234", "role": "customer"}
```
Copy the `access_token` from the response.

### Authorize
Click the "Authorize" button (top right of `/docs`) and paste the token.

### Set your allergies
`PUT /api/users/me`
```json
{"allergies": ["peanuts", "nuts"]}
```

### Find a product to test against
`GET /api/products/` — lists all seeded products. Try barcode
`6001003001001` (Mixed Nuts — contains peanuts) or `6001007001001`
(Basmati Rice — safe).

### Run the recommendation check
`POST /api/analysis/check`
```json
{"product_id": 8}
```
(use the real `id` from the product list, not the barcode)

You should get back `is_safe`, `matched_allergens`, a warning message,
and — if unsafe — a list of safe substitute products.

## 7. (Optional) Run the frontend too

```bash
cd frontend
npm install
npm run dev
```

Then update the frontend's API base URL to point at
`http://127.0.0.1:8000` if it isn't already, and you can test through
the actual UI (ProfilePage for allergies, the POS page for scanning)
instead of `/docs`.

## What's different from the full system

| | Full system | This lightweight setup |
|---|---|---|
| Theft detection (camera/YOLO) | Active | Disabled, logs a warning |
| MQTT (ESP32 payment hardware) | Connects to a real broker | Fails to connect, logs a warning, rest of app unaffected |
| Database | MySQL | SQLite (single file, zero setup) |
| Recommendation engine | ✅ Same code | ✅ Same code |
| Auth / registration | ✅ Same code | ✅ Same code |
| Products / cart / sessions | ✅ Same code | ✅ Same code |

Nothing about the recommendation engine, auth, or product logic is
different — only the camera/MQTT hardware-dependent pieces are turned
off, because there's no camera or ESP32 connected to a laptop anyway.

## Switching back to the full system later

Use `requirements.txt` (the original, not `-lite`) once you're ready to
test theft detection with a real camera, and point `DATABASE_URL` back
at MySQL. No code changes needed either way.
