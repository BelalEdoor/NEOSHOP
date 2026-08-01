import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ShieldAlert } from 'lucide-react'
import { useAuthStore } from '../../store'

/**
 * components/ui/AccountDisabledModal.jsx
 * =======================================
 * شاشة منبثقة تظهر على صفحة حساب العميل عندما يُعطَّل حسابه من لوحة
 * الأدمن (مثلاً بعد نشاط مشبوه لم يُحل عبر خريطة مراقبة العربات).
 *
 * لا تحذف الحساب أو بياناته — فقط تمنع الاستمرار بالتسوق حتى تتم مراجعة
 * الحالة وإعادة تفعيل الحساب من لوحة الأدمن. مثبَّتة بـ Layout.jsx فتظهر
 * فوق أي صفحة (POS/Profile/Map/...) بمجرد أن يرجع أي طلب API بـ 403
 * "Account disabled" (راجع hooks/useApi.js).
 */
export default function AccountDisabledModal() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(127,29,29,0.55)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div style={{
        width: '100%', maxWidth: 420, borderRadius: 24, overflow: 'hidden',
        background: '#fff', boxShadow: '0 24px 80px rgba(0,0,0,0.4)',
        textAlign: 'center',
      }}>
        <div style={{ background: 'linear-gradient(135deg,#dc2626,#991b1b)', padding: '28px 24px' }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%', margin: '0 auto 14px',
            background: 'rgba(255,255,255,0.18)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <ShieldAlert style={{ width: 32, height: 32, color: '#fff' }} />
          </div>
          <h2 style={{ color: '#fff', fontWeight: 900, fontSize: 20, margin: 0 }}>
            {isAr ? '🚫 تم إيقاف الحساب' : '🚫 Account Suspended'}
          </h2>
        </div>
        <div style={{ padding: '22px 26px 26px' }}>
          <p style={{ fontSize: 14, color: '#374151', lineHeight: 1.7, margin: 0 }}>
            {isAr
              ? 'تم إيقاف حسابك مؤقتاً من قبل إدارة المتجر بسبب نشاط مشبوه تم رصده بواسطة نظام المراقبة. يرجى التوجه إلى موظف الأمن أو خدمة العملاء لمراجعة الحالة وإعادة تفعيل حسابك.'
              : 'Your account has been temporarily suspended by store management due to suspicious activity detected by the monitoring system. Please contact a security officer or customer service to review your case and reactivate your account.'}
          </p>
          <button onClick={handleLogout} style={{
            marginTop: 20, width: '100%', padding: '12px 0', borderRadius: 14,
            border: 'none', background: '#111827', color: '#fff',
            fontWeight: 800, fontSize: 14, cursor: 'pointer',
          }}>
            {isAr ? 'تسجيل الخروج' : 'Log out'}
          </button>
        </div>
      </div>
    </div>
  )
}
