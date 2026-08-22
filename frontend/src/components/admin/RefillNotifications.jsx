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
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { createAdminWebSocket, paymentApi, theftApi } from '../../hooks/useApi'
import { useRefillStore, useTheftStore } from '../../store'

// ── محتوى toast تنبيه السرقة ────────────────────────────────────────────────
// عند التصعيد (تفعيل الفرامل) يظهر زر "تفعيل السلة" مباشرةً داخل الإشعار،
// فيقدر الموظف يحلّ المشكلة بضغطة واحدة بدون فتح صفحة الإشعارات أصلاً.
function TheftToastContent({ data, isAr, onDismiss, onReleased, visible }) {
  const navigate = useNavigate()
  const [releasing, setReleasing] = useState(false)
  const isEscalated = !!(data.brake_activated || data.can_release)

  const handleRelease = async () => {
    setReleasing(true)
    try {
      await theftApi.releaseCart(data.session_id)
      onReleased?.(data.session_id)
      toast.success(isAr ? '🔓 تم تفعيل السلة وتحرير الفرامل' : '🔓 Cart re-enabled — brakes released')
      onDismiss()
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        (isAr ? 'تعذّر تفعيل السلة' : 'Could not re-enable the cart')
      )
    } finally {
      setReleasing(false)
    }
  }

  // ── بطاقة التوست الفعلية ────────────────────────────────────────────────
  // ⚠️ toast.custom() بعكس toast.error()/toast.success() — لا يعطي أي
  // خلفية أو padding أو ظل تلقائياً؛ التصميم بالكامل مسؤولية هذا العنصر.
  // كان مفقوداً سابقاً (الفرق الوحيد عن سبب ظهور تنبيه السرقة "عارياً"
  // وملتصقاً بالصفحة بعكس تنبيهات إعادة التعبئة العادية). الأنماط أدناه
  // تطابق بطاقة توست عادية قياسية + حركة دخول/خروج سلسة عبر `visible`.
  return (
    <div
      dir={isAr ? 'rtl' : 'ltr'}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        width: '100%', maxWidth: 380, minWidth: 300,
        background: isEscalated ? '#fef2f2' : '#ffffff',
        border: `1.5px solid ${isEscalated ? '#fecaca' : '#e5e7eb'}`,
        borderRadius: 14,
        padding: '12px 14px',
        boxShadow: '0 10px 30px -5px rgba(0,0,0,0.15), 0 4px 8px -2px rgba(0,0,0,0.08)',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0) scale(1)' : 'translateY(-8px) scale(0.95)',
        transition: 'all 0.2s ease',
      }}
    >
      <span style={{ fontSize: 22, flexShrink: 0 }}>{isEscalated ? '🔒' : '🚨'}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, fontWeight: 800, fontSize: 13, color: '#111827' }}>
          {isEscalated
            ? (isAr ? 'تم تفعيل فرامل العربة' : 'Cart brake activated')
            : (isAr ? 'منتج بالسلة بانتظار المسح' : 'Item in cart awaiting scan')}
        </p>
        <p style={{ margin: '2px 0 0', fontSize: 11, color: '#6b7280' }}>
          {isAr ? 'عربة رقم' : 'Cart'} #{data.cart_id ?? '—'} · {isAr ? 'جلسة' : 'session'} #{data.session_id}
          {data.object_class && <span> · {data.object_class}</span>}
        </p>
      </div>

      {isEscalated && (
        <button
          onClick={handleRelease}
          disabled={releasing}
          style={{
            flexShrink: 0, padding: '6px 12px', borderRadius: 10, border: 'none',
            background: releasing ? '#86efac' : '#059669', color: '#fff',
            fontWeight: 800, fontSize: 11, cursor: releasing ? 'default' : 'pointer',
          }}
        >
          {releasing
            ? (isAr ? '...' : '...')
            : (isAr ? 'تفعيل السلة' : 'Re-enable')}
        </button>
      )}

      <button
        onClick={() => { navigate(`/admin/map?cart=${data.cart_id ?? ''}`); onDismiss() }}
        style={{
          flexShrink: 0, padding: '6px 12px', borderRadius: 10, border: 'none',
          background: '#dc2626', color: '#fff', fontWeight: 800, fontSize: 11, cursor: 'pointer',
        }}
      >
        {isAr ? 'الخريطة' : 'Map'}
      </button>

      <button
        onClick={onDismiss}
        aria-label={isAr ? 'إغلاق' : 'Dismiss'}
        style={{
          flexShrink: 0, width: 22, height: 22, borderRadius: 8, border: 'none',
          background: 'transparent', color: '#9ca3af', cursor: 'pointer',
          fontSize: 14, lineHeight: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        ✕
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
              (t) => (
                <TheftToastContent
                  data={msg.data}
                  isAr={isAr}
                  visible={t.visible}
                  onDismiss={() => toast.dismiss(t.id)}
                  onReleased={removeTheftBySession}
                />
              ),
              // التنبيه المصعَّد (فرامل مفعّلة) يبقى ظاهراً حتى يتصرّف الموظف،
              // لأن اختفاءه تلقائياً يعني ضياع زر "تفعيل السلة" من أمامه.
              // position صراحةً حتى يتوضّع كبطاقة عادية أعلى الصفحة (نفس
              // مكان بقية التنبيهات)، بدل الاعتماد على الموضع الافتراضي
              // الذي كان يُظهره ملتصقاً بحافة الشاشة بلا مسافة واضحة.
              //
              // ⚠️ id ثابت مبني على session_id — هذا هو الإصلاح الأساسي:
              // بدونه، كل حدث لاحق لنفس الجلسة (تحذير أصفر ثم أحمر، أو
              // عدة تحذيرات متتالية) كان يفتح Toast منفصلاً جديداً فوق
              // القديم بدل استبداله — فتتكدّس الإشعارات فوق بعضها وتصير
              // الشاشة "معجوقة". react-hot-toast يستبدل تلقائياً أي toast
              // بنفس الـ id بدل إضافة واحد جديد.
              {
                id: `theft-${msg.data.session_id ?? 'unknown'}`,
                duration: msg.data.brake_activated || msg.data.can_release ? Infinity : 8000,
                position: 'top-center',
              }
            )
          } else if (msg.type === 'theft_alert_cleared' && msg.data?.session_id != null) {
            removeTheftBySession(msg.data.session_id)
            toast.dismiss(`theft-${msg.data.session_id}`)
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