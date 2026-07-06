import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldAlert, CheckCircle, Unlock, Lock, Wifi, WifiOff, Bell, Trash2, Eye } from 'lucide-react'
import { formatPrice } from '../../utils/format'

const WS_URL = `ws://localhost:8000/ws/admin`

// ── نوع الإشعار ──────────────────────────────────────────────────────────────
function AlertBadge({ level }) {
  const isAlert = level === 'alert'
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 800,
      background: isAlert ? '#fee2e2' : '#fff7ed',
      color: isAlert ? '#dc2626' : '#d97706',
    }}>
      {isAlert ? '🚨 تحذير سرقة' : '⚠️ إنذار مبكر'}
    </span>
  )
}

// ── بطاقة حدث واحد ───────────────────────────────────────────────────────────
function EventCard({ event, onDismiss }) {
  const isAlert = event.level === 'alert'
  return (
    <div style={{
      borderRadius: 14, padding: '12px 14px',
      background: isAlert ? '#fef2f2' : '#fff7ed',
      border: `1.5px solid ${isAlert ? '#fecaca' : '#fed7aa'}`,
      display: 'flex', alignItems: 'flex-start', gap: 12,
      animation: 'slideIn 0.3s ease',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10, flexShrink: 0,
        background: isAlert ? '#fee2e2' : '#ffedd5',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18,
      }}>
        {isAlert ? '🚨' : '⚠️'}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <AlertBadge level={event.level} />
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>{event.time}</span>
        </div>
        <p style={{ fontWeight: 700, fontSize: 13, margin: '4px 0 2px', color: 'var(--text)' }}>
          {event.level === 'alert'
            ? `منتج غير مسحوب في اليد: ${event.product}`
            : `تحذير: ${event.product} — لم يُمسح بعد`
          }
        </p>
      </div>
      <button onClick={() => onDismiss(event.id)}
        style={{ flexShrink: 0, width: 28, height: 28, borderRadius: 8, border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--text3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Trash2 style={{ width: 13, height: 13 }} />
      </button>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
export default function AdminSecurity() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [events,      setEvents]      = useState([])
  const [cartState,   setCartState]   = useState({ items: [], total: 0 })
  const [cartLocked,  setCartLocked]  = useState(false)
  const [wsStatus,    setWsStatus]    = useState('disconnected') // connected | disconnected | connecting
  const [scanLog,     setScanLog]     = useState([])
  const [alertCount,  setAlertCount]  = useState(0)

  const wsRef    = useRef(null)
  const retryRef = useRef(null)

  // ── WebSocket ───────────────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setWsStatus('connecting')
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      setWsStatus('connected')
      clearTimeout(retryRef.current)
      // طلب الحالة الحالية
      ws.send(JSON.stringify({ type: 'request_cart_state' }))
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        handleMessage(msg)
      } catch {}
    }

    ws.onclose = () => {
      setWsStatus('disconnected')
      // إعادة الاتصال بعد 3 ثواني
      retryRef.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => { ws.close() }
    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const handleMessage = (msg) => {
    switch (msg.type) {
      case 'theft_alert':
        const event = {
          id:      Date.now(),
          level:   msg.level,
          product: msg.product || 'منتج مجهول',
          time:    new Date(msg.timestamp || Date.now()).toLocaleTimeString('ar-SA'),
        }
        setEvents(prev => [event, ...prev.slice(0, 49)])
        if (msg.level === 'alert') {
          setAlertCount(n => n + 1)
          // صوت تحذير
          try { new Audio('/alert.mp3').play() } catch {}
        }
        break

      case 'cart_update':
        setCartState(msg.data || {})
        break

      case 'cart_locked':
        setCartLocked(msg.locked)
        break

      case 'scan_event':
        setScanLog(prev => [{
          barcode: msg.barcode,
          product: msg.product,
          time:    new Date(msg.time || Date.now()).toLocaleTimeString('ar-SA'),
        }, ...prev.slice(0, 19)])
        break

      case 'alert_cleared':
        // تعليم آخر alert كمحلول
        setEvents(prev => prev.map((e, i) => i === 0 ? { ...e, cleared: true } : e))
        break
    }
  }

  const send = (msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }

  const handleUnlockCart = () => {
    send({ type: 'unlock_cart' })
  }

  const handleDismissAlert = () => {
    send({ type: 'dismiss_alert' })
  }

  const dismissEvent = (id) => {
    setEvents(prev => prev.filter(e => e.id !== id))
  }

  const clearAll = () => {
    setEvents([])
    setAlertCount(0)
    handleDismissAlert()
  }

  // ── Status indicator ────────────────────────────────────────────────────
  const wsColor = wsStatus === 'connected' ? '#10b981' : wsStatus === 'connecting' ? '#f59e0b' : '#ef4444'
  const wsLabel = wsStatus === 'connected' ? 'متصل' : wsStatus === 'connecting' ? 'جاري الاتصال…' : 'غير متصل'
  const activeAlerts = events.filter(e => e.level === 'alert' && !e.cleared)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', overflowY: 'auto', paddingBottom: 20 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 900, color: 'var(--text)', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldAlert style={{ width: 22, height: 22, color: '#ef4444' }} />
            {isAr ? 'مراقبة الأمن' : 'Security Monitor'}
          </h1>
          <p style={{ fontSize: 12, color: 'var(--text3)', margin: '3px 0 0' }}>
            {isAr ? 'نظام الكشف عن السرقة — مرتبط بنظام الرؤية الحاسوبية' : 'Theft detection — linked to CV system'}
          </p>
        </div>

        {/* WebSocket status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 20, background: 'var(--surface2)', border: '1px solid var(--border)' }}>
          {wsStatus === 'connected'
            ? <Wifi style={{ width: 14, height: 14, color: wsColor }} />
            : <WifiOff style={{ width: 14, height: 14, color: wsColor }} />
          }
          <span style={{ fontSize: 12, fontWeight: 700, color: wsColor }}>{wsLabel}</span>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, flexShrink: 0 }}>
        {[
          { label: isAr ? 'تنبيهات نشطة' : 'Active Alerts', value: activeAlerts.length, color: '#ef4444', icon: '🚨' },
          { label: isAr ? 'إجمالي الأحداث' : 'Total Events', value: events.length, color: '#f59e0b', icon: '📋' },
          { label: isAr ? 'عمليات مسح' : 'Scans', value: scanLog.length, color: '#10b981', icon: '✓' },
          { label: isAr ? 'حالة السلة' : 'Cart Status', value: cartLocked ? (isAr ? 'مقفلة' : 'Locked') : (isAr ? 'مفتوحة' : 'Open'), color: cartLocked ? '#ef4444' : '#10b981', icon: cartLocked ? '🔒' : '🔓' },
        ].map(s => (
          <div key={s.label} style={{ borderRadius: 14, padding: '12px 14px', background: 'var(--surface)', border: '1px solid var(--border)', textAlign: 'center' }}>
            <p style={{ fontSize: 22, fontWeight: 900, color: s.color, margin: 0 }}>{s.value}</p>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', margin: '2px 0 0' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Cart lock control */}
      {cartLocked && (
        <div style={{ borderRadius: 16, padding: '14px 18px', background: '#fef2f2', border: '2px solid #fecaca', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Lock style={{ width: 20, height: 20, color: '#dc2626' }} />
            <div>
              <p style={{ fontWeight: 800, fontSize: 14, color: '#dc2626', margin: 0 }}>
                {isAr ? '🔒 السلة مقفلة حالياً' : '🔒 Cart is currently LOCKED'}
              </p>
              <p style={{ fontSize: 11, color: '#ef4444', margin: '2px 0 0' }}>
                {isAr ? 'تم إيقاف السلة بسبب كشف محاولة سرقة' : 'Cart stopped due to theft detection'}
              </p>
            </div>
          </div>
          <button onClick={handleUnlockCart}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 18px', borderRadius: 10, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 800, fontSize: 13, cursor: 'pointer' }}>
            <Unlock style={{ width: 15, height: 15 }} />
            {isAr ? 'فتح السلة' : 'Unlock Cart'}
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16, flex: 1, minHeight: 0 }}>

        {/* Events list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
            <h3 style={{ fontWeight: 800, fontSize: 14, color: 'var(--text)', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Bell style={{ width: 15, height: 15, color: activeAlerts.length > 0 ? '#ef4444' : 'var(--text3)' }} />
              {isAr ? 'سجل الأحداث' : 'Event Log'}
              {alertCount > 0 && (
                <span style={{ background: '#ef4444', color: '#fff', fontSize: 10, fontWeight: 800, padding: '1px 6px', borderRadius: 20 }}>{alertCount}</span>
              )}
            </h3>
            {events.length > 0 && (
              <button onClick={clearAll} style={{ fontSize: 11, color: '#ef4444', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}>
                {isAr ? 'مسح الكل' : 'Clear all'}
              </button>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {events.length === 0 ? (
              <div style={{ textAlign: 'center', paddingTop: 50, color: 'var(--text3)' }}>
                <CheckCircle style={{ width: 44, height: 44, margin: '0 auto 10px', opacity: 0.18 }} />
                <p style={{ fontWeight: 600, fontSize: 13 }}>{isAr ? 'لا توجد أحداث' : 'No events'}</p>
                <p style={{ fontSize: 11 }}>{isAr ? 'النظام يعمل بشكل طبيعي' : 'System running normally'}</p>
              </div>
            ) : (
              events.map(event => (
                <EventCard key={event.id} event={event} onDismiss={dismissEvent} />
              ))
            )}
          </div>
        </div>

        {/* Scan log */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflow: 'hidden' }}>
          <h3 style={{ fontWeight: 800, fontSize: 14, color: 'var(--text)', margin: 0, flexShrink: 0 }}>
            {isAr ? '✓ سجل المسح' : '✓ Scan Log'}
          </h3>
          <div style={{ flex: 1, overflowY: 'auto', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
            {scanLog.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text3)' }}>
                <p style={{ fontSize: 12 }}>{isAr ? 'لا توجد عمليات مسح بعد' : 'No scans yet'}</p>
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ background: 'var(--surface2)' }}>
                    {[isAr ? 'المنتج' : 'Product', isAr ? 'الوقت' : 'Time'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'start', fontSize: 10, fontWeight: 800, color: 'var(--text3)', textTransform: 'uppercase' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {scanLog.map((s, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border)', background: i % 2 === 0 ? 'var(--surface)' : 'var(--surface2)' }}>
                      <td style={{ padding: '7px 12px', fontWeight: 600, color: 'var(--text)' }}>{s.product}</td>
                      <td style={{ padding: '7px 12px', color: 'var(--text3)', fontSize: 11 }}>{s.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Cart items summary */}
          {cartState.items?.length > 0 && (
            <div style={{ borderRadius: 14, background: 'var(--surface)', border: '1px solid var(--border)', padding: '12px 14px', flexShrink: 0 }}>
              <p style={{ fontWeight: 700, fontSize: 12, margin: '0 0 8px', color: 'var(--text2)' }}>
                {isAr ? 'السلة الحالية' : 'Current Cart'} ({cartState.items.length})
              </p>
              {cartState.items.slice(0, 4).map((item, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '3px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ color: 'var(--text)' }}>{item.product?.name || item.name}</span>
                  <span style={{ color: 'var(--primary)', fontWeight: 700 }}>×{item.quantity}</span>
                </div>
              ))}
              {cartState.items.length > 4 && (
                <p style={{ fontSize: 10, color: 'var(--text3)', margin: '4px 0 0' }}>+{cartState.items.length - 4} more</p>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, paddingTop: 6, borderTop: '1px solid var(--border)' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)' }}>Total</span>
                <span style={{ fontSize: 14, fontWeight: 900, color: 'var(--primary)' }}>{formatPrice(cartState.total || 0)}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
