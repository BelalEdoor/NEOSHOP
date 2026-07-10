/**
 * src/components/admin/RefillNotifications.jsx
 * ==============================================
 * تنبيهات "نفاد أنابيب العملات" — تُعرض بلوحة الأدمن.
 *
 * المصادر:
 *   1. عند فتح اللوحة: يجلب أي تنبيهات معلّقة حالياً عبر GET
 *      /api/payments/pending-refills (تحسّباً لتنبيه صار قبل ما يفتح
 *      صاحب المتجر اللوحة).
 *   2. أثناء الاستخدام: يستمع على /ws/admin (نفس القناة المستخدمة
 *      بصفحة الأمن) لأي رسالة type === 'refill_needed' أو 'refill_resolved'
 *      بالوقت الحقيقي.
 *
 * إشعارات الموقع (Browser Notification API):
 *   - يطلب الإذن (Notification.requestPermission) أول ما تُحمَّل اللوحة.
 *   - عند وصول تنبيه جديد ولوحة المتصفح غير ظاهرة (تبويب تاني/مصغّرة)،
 *     يُطلق إشعار نظام حقيقي عبر المتصفح بالإضافة للتنبيه داخل الصفحة.
 *   - بيبقى شغال حتى لو صاحب المتجر مو واقف على تبويب لوحة الأدمن تحديداً،
 *     طالما التبويب مفتوح بالخلفية (الإشعار يعتمد على اتصال الـ WebSocket).
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, Coins, BellRing, CheckCircle2, Loader2, X } from 'lucide-react'
import { paymentApi, createAdminWebSocket } from '../../hooks/useApi'

export default function RefillNotifications() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [alerts, setAlerts]           = useState([])   // [{payment_id, invoice_code, remaining_change, ...}]
  const [confirmingId, setConfirmingId] = useState(null)
  const [notifPermission, setNotifPermission] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'unsupported'
  )

  const wsRef    = useRef(null)
  const retryRef = useRef(null)

  // ── طلب إذن إشعارات الموقع أول ما تُحمَّل اللوحة ───────────────────────────
  useEffect(() => {
    if (typeof Notification === 'undefined') return
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(setNotifPermission)
    }
  }, [])

  const fireBrowserNotification = useCallback((alert) => {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
    try {
      const n = new Notification(
        isAr ? '🪙 نفدت أنابيب العملات المعدنية' : '🪙 Coin tubes are empty',
        {
          body: isAr
            ? `الفاتورة ${alert.invoice_code || '#' + alert.payment_id} — متبقي ${alert.remaining_change} ₪ لإرجاعه للعميل`
            : `Invoice ${alert.invoice_code || '#' + alert.payment_id} — ${alert.remaining_change} NIS still owed to the customer`,
          tag: `refill-${alert.payment_id}`,   // يمنع تكرار نفس التنبيه
          requireInteraction: true,
        }
      )
      n.onclick = () => { window.focus(); n.close() }
    } catch (_) {}
  }, [isAr])

  // ── جلب التنبيهات المعلّقة عند فتح اللوحة ───────────────────────────────────
  useEffect(() => {
    paymentApi.getPendingRefills()
      .then(res => setAlerts(res.data || []))
      .catch(() => {})
  }, [])

  // ── WebSocket حي ────────────────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = createAdminWebSocket()

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'refill_needed') {
          const alert = msg.data
          setAlerts(prev => {
            if (prev.some(a => a.payment_id === alert.payment_id)) return prev
            return [alert, ...prev]
          })
          toast.error(
            isAr
              ? `🪙 نفدت أنابيب العملات! الفاتورة ${alert.invoice_code || ''} — متبقي ${alert.remaining_change} ₪`
              : `🪙 Coin tubes empty! Invoice ${alert.invoice_code || ''} — ${alert.remaining_change} NIS remaining`,
            { duration: 8000 }
          )
          fireBrowserNotification(alert)
          try { new Audio('/alert.mp3').play() } catch (_) {}
        }
        if (msg.type === 'refill_resolved') {
          const { payment_id } = msg.data || {}
          setAlerts(prev => prev.filter(a => a.payment_id !== payment_id))
        }
      } catch (_) {}
    }

    ws.onclose = () => { retryRef.current = setTimeout(connect, 3000) }
    ws.onerror = () => { ws.close() }
    wsRef.current = ws
  }, [isAr, fireBrowserNotification])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  // ── تأكيد التعبئة ────────────────────────────────────────────────────────────
  const handleConfirm = async (paymentId) => {
    setConfirmingId(paymentId)
    try {
      await paymentApi.confirmRefill(paymentId)
      setAlerts(prev => prev.filter(a => a.payment_id !== paymentId))
      toast.success(isAr ? '✅ تم إخبار الجهاز، جاري إكمال الدفعة' : '✅ Device notified, resuming payment')
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        (isAr ? 'تعذّر إخبار الجهاز — تأكد من اتصال MQTT' : 'Could not notify the device — check MQTT connection')
      )
    } finally {
      setConfirmingId(null)
    }
  }

  const dismiss = (paymentId) => setAlerts(prev => prev.filter(a => a.payment_id !== paymentId))

  if (alerts.length === 0) return null

  return (
    <div style={{
      position: 'fixed', top: 16, insetInlineEnd: 16, zIndex: 200,
      display: 'flex', flexDirection: 'column', gap: 10, width: 340, maxWidth: 'calc(100vw - 32px)',
    }}>
      {notifPermission !== 'granted' && typeof Notification !== 'undefined' && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
          borderRadius: 12, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 11, color: '#92400e',
        }}>
          <BellRing style={{ width: 14, height: 14, flexShrink: 0 }} />
          <span style={{ flex: 1 }}>
            {isAr ? 'فعّل إشعارات الموقع عشان توصلك التنبيهات حتى لو التبويب مو مفتوح' : 'Enable site notifications to get alerts even when this tab isn\'t focused'}
          </span>
          <button
            onClick={() => Notification.requestPermission().then(setNotifPermission)}
            style={{ padding: '4px 10px', borderRadius: 8, border: 'none', background: '#f59e0b', color: 'white', fontSize: 11, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}
          >
            {isAr ? 'تفعيل' : 'Enable'}
          </button>
        </div>
      )}

      {alerts.map(alert => (
        <div key={alert.payment_id} style={{
          borderRadius: 14, padding: '14px 14px', background: '#fef2f2',
          border: '1.5px solid #fecaca', boxShadow: '0 8px 24px rgba(239,68,68,0.15)',
          animation: 'slideIn 0.3s ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 10, flexShrink: 0, background: '#fee2e2',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Coins style={{ width: 17, height: 17, color: '#dc2626' }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ fontWeight: 800, fontSize: 12.5, margin: 0, color: '#991b1b', display: 'flex', alignItems: 'center', gap: 5 }}>
                <AlertTriangle style={{ width: 12, height: 12 }} />
                {isAr ? 'نفدت أنابيب العملات' : 'Coin tubes empty'}
              </p>
              <p style={{ fontSize: 11.5, margin: '4px 0 0', color: '#7f1d1d' }}>
                {isAr ? 'الفاتورة' : 'Invoice'}: <b>{alert.invoice_code || `#${alert.payment_id}`}</b>
              </p>
              <p style={{ fontSize: 11.5, margin: '2px 0 0', color: '#7f1d1d' }}>
                {isAr ? 'متبقي إرجاعه للعميل' : 'Still owed to customer'}: <b>{alert.remaining_change} ₪</b>
              </p>
              {alert.device_id && (
                <p style={{ fontSize: 10, margin: '2px 0 0', color: '#b91c1c', opacity: 0.7 }}>
                  {alert.device_id}
                </p>
              )}
            </div>
            <button onClick={() => dismiss(alert.payment_id)}
              style={{ flexShrink: 0, width: 22, height: 22, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', color: '#b91c1c', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title={isAr ? 'إخفاء (بدون حل المشكلة)' : 'Dismiss (does not resolve)'}
            >
              <X style={{ width: 13, height: 13 }} />
            </button>
          </div>

          <button
            onClick={() => handleConfirm(alert.payment_id)}
            disabled={confirmingId === alert.payment_id}
            style={{
              marginTop: 10, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              padding: '9px 12px', borderRadius: 10, border: 'none', cursor: confirmingId === alert.payment_id ? 'default' : 'pointer',
              background: confirmingId === alert.payment_id ? '#fca5a5' : '#dc2626', color: 'white', fontSize: 12, fontWeight: 800,
            }}
          >
            {confirmingId === alert.payment_id
              ? <><Loader2 style={{ width: 14, height: 14 }} className="animate-spin" /> {isAr ? 'جاري الإرسال...' : 'Notifying...'}</>
              : <><CheckCircle2 style={{ width: 14, height: 14 }} /> {isAr ? 'تم تعبئة الجهاز — إكمال الدفعة' : 'Refilled — resume payment'}</>
            }
          </button>
        </div>
      ))}

      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
