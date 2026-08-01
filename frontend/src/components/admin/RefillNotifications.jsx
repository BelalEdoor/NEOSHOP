/**
 * src/components/admin/RefillNotifications.jsx
 * ===============================================
 * لا يعرض أي واجهة (return null) — كان سابقاً بطاقة/لوحة تنبيهات عائمة
 * مكرّرة بجانب السايدبار (نسخة مطابقة لصفحة /admin/notifications)، تم
 * حذفها بناءً على طلب المستخدم وإبقاء صفحة الإشعارات الوحيدة ضمن السايدبار
 * (pages/admin/AdminNotifications.jsx).
 *
 * هذا المكوّن الآن مسؤول فقط عن نقطة اتصال WebSocket الإدارية الوحيدة
 * (/ws/admin) التي تغذّي useRefillStore بالتنبيهات الحية، والتي منها
 * تُشتق:
 *   1. شارة العدد بجانب "الإشعارات" بالسايدبار (AdminLayout)
 *   2. قائمة "تنبيهات نشطة" بصفحة الإشعارات (AdminNotifications)
 * يبقى مثبّتاً بكل صفحات لوحة الأدمن (AdminLayout) عشان الاتصال ما ينقطع
 * عند التنقّل بين الصفحات.
 */
import { useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { createAdminWebSocket, paymentApi } from '../../hooks/useApi'
import { useRefillStore, useTheftStore } from '../../store'

// ── محتوى toast تنبيه السرقة — زر "الانتقال للخريطة" بجانب الوصف ────────────
function TheftToastContent({ data, isAr, onDismiss }) {
  const navigate = useNavigate()
  const isEscalated = !!data.brake_activated
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 260 }}>
      <span style={{ fontSize: 20 }}>{isEscalated ? '🔒' : '🚨'}</span>
      <div style={{ flex: 1 }}>
        <p style={{ margin: 0, fontWeight: 800, fontSize: 13, color: '#111827' }}>
          {isEscalated
            ? (isAr ? 'تم تفعيل فرامل العربة' : 'Cart brake activated')
            : (isAr ? 'منتج غير مسحوب بالسلة' : 'Unscanned item in cart')}
        </p>
        <p style={{ margin: '2px 0 0', fontSize: 11, color: '#6b7280' }}>
          {isAr ? 'عربة رقم' : 'Cart'} #{data.cart_id ?? '—'} · {isAr ? 'جلسة' : 'session'} #{data.session_id}
        </p>
      </div>
      <button
        onClick={() => { navigate(`/admin/map?cart=${data.cart_id ?? ''}`); onDismiss() }}
        style={{
          flexShrink: 0, padding: '6px 12px', borderRadius: 10, border: 'none',
          background: '#dc2626', color: '#fff', fontWeight: 800, fontSize: 11, cursor: 'pointer',
        }}
      >
        {isAr ? 'الخريطة' : 'Map'}
      </button>
    </div>
  )
}

export default function RefillNotifications() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const setPendingAlerts    = useRefillStore(s => s.setPendingAlerts)
  const addPendingAlert     = useRefillStore(s => s.addPendingAlert)
  const removePendingAlert  = useRefillStore(s => s.removePendingAlert)

  const addTheftAlert         = useTheftStore(s => s.addAlert)
  const removeTheftBySession  = useTheftStore(s => s.removeAlertBySession)

  const wsRef   = useRef(null)
  const retryRef = useRef(null)

  // ── تحميل أولي: أي تنبيهات معلّقة من قبل فتح لوحة الأدمن ─────────────────
  useEffect(() => {
    paymentApi.getPendingRefills()
      .then(({ data }) => setPendingAlerts(data || []))
      .catch(() => {})
  }, [setPendingAlerts])

  // ── اتصال WebSocket الإداري الوحيد — يبقى مفتوحاً طوال وجود لوحة الأدمن ──
  useEffect(() => {
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      const ws = createAdminWebSocket()
      wsRef.current = ws

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg.type === 'refill_needed' && msg.data) {
            addPendingAlert(msg.data)
            toast.error(
              isAr
                ? `⚠️ نفدت أنابيب العملات — ${msg.data.invoice_code || `#${msg.data.payment_id}`}`
                : `⚠️ Coin tubes empty — ${msg.data.invoice_code || `#${msg.data.payment_id}`}`,
              { duration: 6000 }
            )
          } else if (msg.type === 'refill_resolved' && msg.data?.payment_id != null) {
            removePendingAlert(msg.data.payment_id)
          } else if (msg.type === 'theft_alert' && msg.data) {
            // تنبيه سرقة (منتج غير مسحوب / تفعيل فرامل) — راجع
            // cv/alert_handler.py بالباك اند لسير العمل الكامل.
            addTheftAlert(msg.data)
            toast.custom(
              (t) => <TheftToastContent data={msg.data} isAr={isAr} onDismiss={() => toast.dismiss(t.id)} />,
              { duration: 8000 }
            )
          } else if (msg.type === 'theft_alert_cleared' && msg.data?.session_id != null) {
            removeTheftBySession(msg.data.session_id)
          }
        } catch { /* ignore malformed frames */ }
      }

      ws.onclose = () => {
        if (cancelled) return
        // إعادة محاولة الاتصال بعد ثانيتين لو انقطع (مثلاً إعادة تشغيل الباك اند)
        retryRef.current = setTimeout(connect, 2000)
      }
      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      cancelled = true
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [addPendingAlert, removePendingAlert, addTheftAlert, removeTheftBySession, isAr])

  return null
}
