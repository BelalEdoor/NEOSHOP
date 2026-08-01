import React, { useEffect, useState, useRef } from 'react'

/**
 * components/pos/TheftWarningModal.jsx
 * ======================================
 * الشاشة الحمراء المنبثقة على نقطة البيع عندما يرصد نظام الرؤية الحاسوبية
 * منتجاً وُضِع بالسلة دون مسح باركود (alert_type=UNSCANNED_IN_CART).
 *
 * تعرض عدّاً تنازلياً (افتراضياً 10 ثوانٍ، تُملَى من grace_seconds التي
 * يرسلها الباك اند — راجع cv/alert_handler.py) وتطلب من العميل إعادة مسح
 * المنتج فوراً. تُغلَق تلقائياً عند وصول:
 *   - "theft_alert_cleared"  → أعاد العميل المسح في الوقت المحدد.
 *   - "cart_locked" (locked=true) → انتهت المهلة والباك اند فعّل الفرامل
 *     فعلياً؛ عندها تتحول الشاشة لحالة "تم إيقاف السلة" بدل العدّ التنازلي.
 */
export default function TheftWarningModal({ alert, locked, isAr, onDismiss }) {
  const graceSeconds = alert?.grace_seconds || 10
  const [remaining, setRemaining] = useState(graceSeconds)
  const startRef = useRef(Date.now())

  useEffect(() => {
    if (!alert) return
    startRef.current = Date.now()
    setRemaining(graceSeconds)
    const id = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 1000
      setRemaining(Math.max(0, Math.ceil(graceSeconds - elapsed)))
    }, 250)
    return () => clearInterval(id)
  }, [alert, graceSeconds])

  if (!alert && !locked) return null

  const productLabel = alert?.object_class || (isAr ? 'المنتج' : 'the item')

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300,
      background: 'rgba(153,27,27,0.75)', backdropFilter: 'blur(3px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
      animation: 'theftPulse 1s ease-in-out infinite',
    }}>
      <div style={{
        width: '100%', maxWidth: 440, borderRadius: 26, overflow: 'hidden',
        background: '#fff', boxShadow: '0 30px 100px rgba(0,0,0,0.5)', textAlign: 'center',
      }}>
        {locked ? (
          <>
            <div style={{ background: 'linear-gradient(135deg,#7f1d1d,#450a0a)', padding: '30px 24px' }}>
              <div style={{ fontSize: 46, marginBottom: 6 }}>🔒</div>
              <h2 style={{ color: '#fff', fontWeight: 900, fontSize: 20, margin: 0 }}>
                {isAr ? 'تم إيقاف العربة' : 'Cart Stopped'}
              </h2>
            </div>
            <div style={{ padding: '20px 26px 26px' }}>
              <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.7, margin: 0 }}>
                {isAr
                  ? 'لم يتم إعادة مسح المنتج في الوقت المحدد، فتم تفعيل فرامل العربة تلقائياً وتنبيه فريق الأمن. يرجى انتظار موظف الأمن.'
                  : 'The item was not rescanned in time, so the cart brakes were engaged automatically and security has been alerted. Please wait for a staff member.'}
              </p>
            </div>
          </>
        ) : (
          <>
            <div style={{ background: 'linear-gradient(135deg,#ef4444,#b91c1c)', padding: '26px 24px 20px' }}>
              <div style={{ fontSize: 42, marginBottom: 4 }}>⚠️</div>
              <h2 style={{ color: '#fff', fontWeight: 900, fontSize: 19, margin: 0 }}>
                {isAr ? 'تنبيه: منتج غير مسحوب' : 'Warning: Unscanned Item'}
              </h2>
              <p style={{ color: 'rgba(255,255,255,0.85)', fontSize: 13, margin: '6px 0 0' }}>
                {isAr
                  ? `تم رصد "${productLabel}" داخل السلة دون مسح الباركود`
                  : `"${productLabel}" was detected in the cart without a barcode scan`}
              </p>
            </div>
            <div style={{ padding: '22px 26px 8px' }}>
              <div style={{
                width: 96, height: 96, borderRadius: '50%', margin: '0 auto 14px',
                background: remaining <= 3 ? '#fee2e2' : '#fff7ed',
                border: `4px solid ${remaining <= 3 ? '#dc2626' : '#f59e0b'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{
                  fontSize: 38, fontWeight: 900,
                  color: remaining <= 3 ? '#dc2626' : '#d97706',
                }}>{remaining}</span>
              </div>
              <p style={{ fontSize: 14, fontWeight: 700, color: '#111827', margin: '0 0 4px' }}>
                {isAr ? 'الرجاء إعادة مسح باركود المنتج فوراً' : 'Please rescan the item barcode now'}
              </p>
              <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 20px' }}>
                {isAr
                  ? 'في حال عدم المسح خلال المدة، سيتم إيقاف العربة تلقائياً'
                  : "If not scanned in time, the cart will be stopped automatically"}
              </p>
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes theftPulse {
          0%, 100% { background: rgba(153,27,27,0.75); }
          50%      { background: rgba(185,28,28,0.85); }
        }
      `}</style>
    </div>
  )
}
