"""
websocket_router.py
===================
إدارة WebSocket connections للـ Frontend (Raspberry Pi) ولوحة الأدمن.

Channels:
  /ws/cart/{session_id}  ← Raspberry Pi (Frontend per session)
  /ws/admin              ← لوحة إدارة المتجر
  /ws/pos/{session_id}   ← نقطة البيع
"""
import json
import logging
from typing import Set, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone

router = APIRouter()
log    = logging.getLogger("neoshop.ws")


# ══════════════════════════════════════════════════════════════════════════════
# ConnectionManager
# ══════════════════════════════════════════════════════════════════════════════
class ConnectionManager:
    """
    إدارة كل اتصالات WebSocket في النظام.
    يدعم 3 قنوات: Cart (per session), Admin, POS.
    """

    def __init__(self):
        self._admin_clients: Set[WebSocket] = set()
        self._session_clients: Dict[int, Set[WebSocket]] = {}  # session_id → clients
        self._cart_locked: Dict[int, bool] = {}

    # ── Admin ──────────────────────────────────────────────────────────────
    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self._admin_clients.add(ws)
        log.info(f"[WS] Admin connected ({len(self._admin_clients)} active)")

    def disconnect_admin(self, ws: WebSocket):
        self._admin_clients.discard(ws)

    async def broadcast_to_admin(self, message: dict):
        for ws in list(self._admin_clients):
            await self._safe_send(ws, message)

    # ── Session / Cart ─────────────────────────────────────────────────────
    async def connect_to_session(self, ws: WebSocket, session_id: int):
        await ws.accept()
        if session_id not in self._session_clients:
            self._session_clients[session_id] = set()
        self._session_clients[session_id].add(ws)
        log.info(f"[WS] Client connected to session {session_id}")
        # إرسال حالة القفل الحالية
        locked = self._cart_locked.get(session_id, False)
        await self._safe_send(ws, {"type": "cart_locked", "locked": locked})

    def disconnect_from_session(self, ws: WebSocket, session_id: int):
        if session_id in self._session_clients:
            self._session_clients[session_id].discard(ws)

    async def broadcast_to_session(self, session_id: int, message: dict):
        """إرسال رسالة لجميع clients المرتبطين بجلسة معيّنة."""
        clients = self._session_clients.get(session_id, set())
        for ws in list(clients):
            await self._safe_send(ws, message)
        # أيضاً أرسل للأدمن
        await self.broadcast_to_admin(message)

    async def set_cart_locked(self, session_id: int, locked: bool):
        self._cart_locked[session_id] = locked
        await self.broadcast_to_session(session_id, {
            "type": "cart_locked",
            "locked": locked,
            "session_id": session_id,
        })

    # ── Helpers ────────────────────────────────────────────────────────────
    async def _safe_send(self, ws: WebSocket, data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            pass


# ─── Global Instance ──────────────────────────────────────────────────────────
manager = ConnectionManager()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/cart/{session_id}")
async def websocket_cart(websocket: WebSocket, session_id: int):
    """
    Raspberry Pi يتصل هنا لاستقبال تحديثات جلسة التسوق.
    يستقبل: cart_update, cart_locked, theft_alert, payment_update
    """
    await manager.connect_to_session(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                # الرسائل من Raspberry Pi → Backend
                if msg_type == "barcode_scan":
                    # الرازبيري يُبلّغ عن مسح باركود
                    log.info(f"[WS] Barcode scan from session {session_id}: {msg}")
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong", "ts": datetime.now(timezone.utc).isoformat()})

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_from_session(websocket, session_id)
        log.info(f"[WS] Session {session_id} disconnected")


@router.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """
    لوحة الأدمن تتصل هنا لاستقبال تحديثات في real-time.
    تستقبل: theft_alert, cart_update, payment_complete, session_started
    """
    await manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)
        log.info("[WS] Admin disconnected")


@router.websocket("/ws/pos/{session_id}")
async def websocket_pos(websocket: WebSocket, session_id: int):
    """نقطة البيع — مشابهة لـ /ws/cart لكن مخصصة لشاشة الدفع."""
    await manager.connect_to_session(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_from_session(websocket, session_id)
