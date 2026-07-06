# NeoShop - macOS Setup Guide

This guide explains how to run the NeoShop project on macOS.

---

# Prerequisites

Make sure the following are installed:

- Python 3.11 (or Python 3)
- Node.js (LTS)
- npm
- Git

Check versions:

```bash
python3 --version
node -v
npm -v
```

---

# Project Structure

```
neoshop_final/
│
├── backend/
│
└── frontend/
```

---

# Terminal 1 - Start Backend

Navigate to the backend folder:

```bash
cd ~/Desktop/neoshop_final/backend
```

## Create a virtual environment (First time only)

```bash
python3.11 -m venv venv
```

If Python 3.11 is unavailable:

```bash
python3 -m venv venv
```

## Activate the virtual environment

```bash
source venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements-lite.txt
```

## Start the backend server

```bash
uvicorn main:app --reload
```

The backend should now be running at:

```
http://127.0.0.1:8000
```

---

# Terminal 2 - Seed Recommendation Engine

Open a new Terminal.

Navigate to the backend folder:

```bash
cd ~/Desktop/neoshop_final/backend
```

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run the recommendation engine:

```bash
python seed_recommendation_engine.py
```

If the above command doesn't work:

```bash
python3 seed_recommendation_engine.py
```

---

# Terminal 3 - Start Frontend

Open another Terminal.

Navigate to the frontend folder:

```bash
cd ~/Desktop/neoshop_final/frontend
```

Install dependencies (first time only):

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend should now be available at:

```
http://localhost:5173
```

---

# Troubleshooting

## Vite Permission Denied

If you receive:

```
Permission denied
```

Run:

```bash
rm -rf node_modules
rm package-lock.json

npm install

chmod +x node_modules/.bin/vite

npm run dev
```

---

## Python Command Not Found

Use:

```bash
python3
```

instead of:

```bash
python
```

---

## Re-activating the Virtual Environment

Whenever you reopen the project:

```bash
cd ~/Desktop/neoshop_final/backend
source venv/bin/activate
```

---

# Running Order

Start the project in this order:

1. Backend

```bash
uvicorn main:app --reload
```

2. Recommendation Engine

```bash
python seed_recommendation_engine.py
```

3. Frontend

```bash
npm run dev
```

---

# Project URLs

Backend

```
http://127.0.0.1:8000
```

Frontend

```
http://localhost:5173
```

---

Happy Coding! 🚀