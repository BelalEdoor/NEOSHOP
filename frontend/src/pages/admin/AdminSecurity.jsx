import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ShieldAlert, CheckCircle, Unlock, Lock, Wifi, WifiOff, Bell, Trash2, Eye, X, User, ShoppingCart, Clock, CheckCircle2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { formatPrice } from '../../utils/format'
import { theftApi } from '../../hooks/useApi'

const WS_URL = `ws://localhost:8000/ws/admin`

// ── نوع الإشعار ──────────────────────────────────────────────────────────────
// alert_type القادمة فعلياً من الباك اند (routers/theft.py):
//   PLEASE_SCAN_PRODUCT → إنذار مبكر (عدّ تنازلي على نقطة البيع)
//   PRODUCT_NOT_SCANNED → تحذير سرقة فعلي (الفرامل فُعِّلت)
function AlertBadge({ alertType }) {
  const map = {
    PRODUCT_NOT_SCANNED:       { bg: '#fee2e2', color: '#dc2626', label: '🚨 تحذير سرقة' },
    CAMERA_OBSTRUCTED:         { bg: '#fee2e2', color: '#dc2626', label: '🎥🚫 تغطية الكاميرا' },
    ITEM_RETURNED_NOT_REMOVED: { bg: '#fef9c3', color: '#854d0e', label: '↩️ إرجاع بدون حذف' },
    PLEASE_SCAN_PRODUCT:       { bg: '#fff7ed', color: '#d97706', label: '⚠️ إنذار مبكر' },
  }
  const s = map[alertType] || { bg: '#fff7ed', color: '#d97706', label: '⚠️ إنذار مبكر' }
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 20, fontSize: 11, fontWeight: 800,
      background: s.bg, color: s.color,
    }}>
      {s.label}
    </span>
  )
}

// ── بطاقة حدث واحد ───────────────────────────────────────────────────────────
function EventCard({ event, onDismiss, onRelease, onReview }) {
  const isAlert = event.alertType === 'PRODUCT_NOT_SCANNED' || event.alertType === 'CAMERA_OBSTRUCTED'
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
          <AlertBadge alertType={event.alertType} />
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>{event.time}</span>
          {event.sessionId && (
            <span style={{ fontSize: 10, color: 'var(--text3)' }}>#{event.sessionId}</span>
          )}
          {event.resolved && (
            <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 700 }}>✓ محلول</span>
          )}
        </div>
        <p style={{ fontWeight: 700, fontSize: 13, margin: '4px 0 2px', color: 'var(--text)' }}>
          {event.description || (event.product
            ? `منتج غير مسحوب: ${event.product}`
            : 'حدث أمني')}
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
          {event.canRelease && !event.cleared && event.sessionId && (
            <button onClick={() => onRelease(event.sessionId)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 800, fontSize: 11, cursor: 'pointer' }}>
              <Unlock style={{ width: 12, height: 12 }} />
              تفعيل السلة
            </button>
          )}
          <button onClick={() => onReview(event)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text2)', fontWeight: 800, fontSize: 11, cursor: 'pointer' }}>
            <Eye style={{ width: 12, height: 12 }} />
            مراجعة
          </button>
        </div>
      </div>
      <button onClick={() => onDismiss(event.id)}
        style={{ flexShrink: 0, width: 28, height: 28, borderRadius: 8, border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--text3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Trash2 style={{ width: 13, height: 13 }} />
      </button>
    </div>
  )
}

// ── مودال المراجعة — كل تفاصيل الحدث ─────────────────────────────────────────
function ReviewModal({ event, onClose, isAr }) {
  if (!event) return null

  const Row = ({ icon: Icon, label, value }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <Icon style={{ width: 16, height: 16, color: 'var(--text3)', flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: 'var(--text3)', minWidth: 110 }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', flex: 1, textAlign: isAr ? 'left' : 'right' }}>
        {value ?? '—'}
      </span>
    </div>
  )

  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--surface)', borderRadius: 18, width: '100%', maxWidth: 440,
        maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: '1px solid var(--border)',
        }}>
          <h3 style={{ fontSize: 16, fontWeight: 900, margin: 0, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldAlert style={{ width: 18, height: 18, color: '#ef4444' }} />
            {isAr ? 'مراجعة الحدث' : 'Event Review'}
          </h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)' }}>
            <X style={{ width: 20, height: 20 }} />
          </button>
        </div>

        <div style={{ padding: '4px 20px 20px' }}>
          <div style={{ margin: '10px 0 14px' }}>
            <AlertBadge alertType={event.alertType} />
          </div>
          <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', margin: '0 0 10px' }}>
            {event.description || '—'}
          </p>

          <Row icon={ShoppingCart} label={isAr ? 'رقم السلة' : 'Cart'} value={event.cartNumber} />
          <Row icon={Bell} label={isAr ? 'رقم الجلسة' : 'Session'} value={event.sessionId ? `#${event.sessionId}` : null} />
          <Row icon={User} label={isAr ? 'حساب العميل' : 'Customer'}
               value={event.customerName ? `${event.customerName}${event.customerEmail ? ` (${event.customerEmail})` : ''}` : null} />
          <Row icon={ShieldAlert} label={isAr ? 'طبيعة النشاط' : 'Activity type'} value={event.alertType} />
          <Row icon={Clock} label={isAr ? 'وقت الحدث' : 'Detected at'}
               value={event.detectedAt ? new Date(event.detectedAt).toLocaleString(isAr ? 'ar-SA' : 'en-US') : event.time} />
          <Row icon={CheckCircle2} label={isAr ? 'وقت الحل' : 'Resolved at'}
               value={event.resolvedAt ? new Date(event.resolvedAt).toLocaleString(isAr ? 'ar-SA' : 'en-US') : (isAr ? 'لم يُحل بعد' : 'Not resolved yet')} />
          <Row icon={Lock} label={isAr ? 'تفعيل الفرامل' : 'Brake activated'}
               value={event.brakeActivated ? (isAr ? 'نعم' : 'Yes') : (isAr ? 'لا' : 'No')} />
        </div>
      </div>
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
  const [lockedSessionId, setLockedSessionId] = useState(null)
  const [wsStatus,    setWsStatus]    = useState('disconnected') // connected | disconnected | connecting
  const [scanLog,     setScanLog]     = useState([])
  const [alertCount,  setAlertCount]  = useState(0)
  const [reviewEvent, setReviewEvent] = useState(null)   // الحدث المفتوح حالياً بمودال المراجعة
  const [historyLoaded, setHistoryLoaded] = useState(false)

  const wsRef    = useRef(null)
  const retryRef = useRef(null)

  // ── تحويل استجابة الباك اند (TheftLogOut) لنفس شكل event المستخدَم محلياً ──
  const mapLogToEvent = (log) => ({
    id:            log.id,
    alertType:     log.alert_type,
    sessionId:     log.session_id,
    product:       null,
    description:   log.description,
    canRelease:    log.alert_type === 'PRODUCT_NOT_SCANNED' && !log.resolved,
    time:          log.detected_at ? new Date(log.detected_at).toLocaleTimeString('ar-SA') : '',
    resolved:      log.resolved,
    cleared:       log.resolved,
    // ─── حقول إضافية لمودال "مراجعة" فقط (غير موجودة بأحداث الـ WS الحية،
    // تُملأ من قاعدة البيانات — راجع GET /api/theft/) ───────────────────
    cartNumber:    log.cart_number,
    customerName:  log.customer_name,
    customerEmail: log.customer_email,
    detectedAt:    log.detected_at,
    resolvedAt:    log.resolved_at,
    brakeActivated: log.brake_activated,
  })

  // ── جلب السجل الدائم من قاعدة البيانات عند فتح الصفحة ─────────────────────
  // ⚠️ كان "سجل الأحداث" يعتمد فقط على رسائل WebSocket الحية بالذاكرة —
  // أي تحديث للصفحة كان يفقد كل السجل السابق بالكامل. الآن يُجلَب آخر ١٠٠
  // حدث فعلياً من قاعدة البيانات (theft_logs) أولاً، وتُدمَج معه أي أحداث
  // حية تصل لاحقاً عبر WebSocket — فيبقى السجل موجوداً حتى بعد Refresh.
  useEffect(() => {
    theftApi.listAlerts({ limit: 100 })
      .then(({ data }) => {
        setEvents(data.map(mapLogToEvent))
        setHistoryLoaded(true)
      })
      .catch(() => setHistoryLoaded(true))
  }, [])

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
      case 'theft_alert': {
        // شكل data الفعلي القادم من routers/theft.py::create_alert (كل
        // تنبيهات الراسبيري باي الآن تمرّ من هنا — راجع theft_agent.py):
        //   { alert_id, session_id, cart_id, cart_rfid, alert_type,
        //     description, object_class, grace_seconds, brake_activated,
        //     can_release }
        const data = msg.data || {}
        const isAlarm = data.alert_type === 'PRODUCT_NOT_SCANNED' || data.alert_type === 'CAMERA_OBSTRUCTED'
        const event = {
          id:            data.alert_id || Date.now(),
          alertType:     data.alert_type,
          sessionId:     data.session_id,
          product:       data.object_class,
          description:   data.description,
          canRelease:    !!data.can_release,
          time:          new Date().toLocaleTimeString('ar-SA'),
          resolved:      false,
          detectedAt:    new Date().toISOString(),
          brakeActivated: !!data.brake_activated,
          // cart_number/customer الكاملين غير متوفّرين بالبث الحي (تحتاج
          // استعلام مرتبط بجدول users) — cart_id متوفّر كبديل مؤقت لحظة
          // الحدوث، ويكتمل تلقائياً بالتفاصيل الكاملة (cart_number/العميل)
          // عند إعادة تحميل الصفحة لاحقاً (يُجلَب حينها من قاعدة البيانات).
          cartNumber:    data.cart_id ? `#${data.cart_id}` : null,
        }
        // ⚠️ لو فيه سطر سابق بنفس alert_id (نادر لكن ممكن عند إعادة بث)،
        // استبدله بدل التكرار — يمنع ازدواج نفس الحدث بسجل الأحداث.
        setEvents(prev => [event, ...prev.filter(e => e.id !== event.id).slice(0, 99)])
        if (isAlarm) {
          setAlertCount(n => n + 1)
          try { new Audio('/alert.mp3').play() } catch {}
        }
        break
      }

      case 'cart_update':
        setCartState(msg.data || {})
        break

      case 'cart_locked':
        setCartLocked(msg.locked)
        setLockedSessionId(msg.locked ? (msg.session_id ?? null) : null)
        break

      case 'scan_event':
        setScanLog(prev => [{
          barcode: msg.barcode,
          product: msg.product,
          time:    new Date(msg.time || Date.now()).toLocaleTimeString('ar-SA'),
        }, ...prev.slice(0, 19)])
        break

      case 'theft_alert_cleared':
        // تعليم آخر تنبيه لنفس الجلسة كمحلول (يصل عند مسح ناجح أو تحرير يدوي)
        setEvents(prev => prev.map(e =>
          (msg.data?.session_id && e.sessionId === msg.data.session_id)
            ? { ...e, cleared: true, resolved: true, canRelease: false, resolvedAt: new Date().toISOString() }
            : e
        ))
        break
    }
  }

  // ── تفعيل السلة (تحرير الفرامل) — يستخدم REST الفعلي، وليس رسالة
  // WebSocket وهمية لم يكن الباك اند يتعامل معها أصلاً.
  const releaseCart = async (sessionId) => {
    if (!sessionId) return
    try {
      await theftApi.releaseCart(sessionId)
      toast.success('تم تفعيل السلة وتحرير الفرامل')
      setEvents(prev => prev.map(e => e.sessionId === sessionId
        ? { ...e, cleared: true, resolved: true, canRelease: false, resolvedAt: new Date().toISOString() }
        : e))
      if (lockedSessionId === sessionId) {
        setCartLocked(false)
        setLockedSessionId(null)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'تعذّر تفعيل السلة')
    }
  }

  const handleUnlockCart = () => releaseCart(lockedSessionId)

  const dismissEvent = (id) => {
    setEvents(prev => prev.filter(e => e.id !== id))
  }

  const clearAll = () => {
    setEvents([])
    setAlertCount(0)
  }

  // ── Status indicator ────────────────────────────────────────────────────
  const wsColor = wsStatus === 'connected' ? '#10b981' : wsStatus === 'connecting' ? '#f59e0b' : '#ef4444'
  const wsLabel = wsStatus === 'connected' ? 'متصل' : wsStatus === 'connecting' ? 'جاري الاتصال…' : 'غير متصل'
  const activeAlerts = events.filter(e =>
    (e.alertType === 'PRODUCT_NOT_SCANNED' || e.alertType === 'CAMERA_OBSTRUCTED') && !e.cleared
  )

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
                <EventCard key={event.id} event={event} onDismiss={dismissEvent} onRelease={releaseCart} onReview={setReviewEvent} />
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

      <ReviewModal event={reviewEvent} onClose={() => setReviewEvent(null)} isAr={isAr} />

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}