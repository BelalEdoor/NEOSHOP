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
import { createAdminWebSocket, paymentApi } from '../../hooks/useApi'
import { useRefillStore } from '../../store'

export default function RefillNotifications() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const setPendingAlerts    = useRefillStore(s => s.setPendingAlerts)
  const addPendingAlert     = useRefillStore(s => s.addPendingAlert)
  const removePendingAlert  = useRefillStore(s => s.removePendingAlert)

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
  }, [addPendingAlert, removePendingAlert, isAr])

  return null
}
