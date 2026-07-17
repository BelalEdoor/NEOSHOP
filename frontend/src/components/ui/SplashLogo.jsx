import React, { useEffect, useState } from 'react'
import { ShoppingBag } from 'lucide-react'

/**
 * SplashLogo.jsx
 * ==============
 * علامة/شعار المشروع (NEOSHOP) تظهر كبطاقة منبثقة متحركة لعدة ثوانٍ عند
 * أول فتح للموقع (موظف أو عميل)، ثم تختفي تدريجياً لتترك مكانها للشعار
 * الصغير الثابت أعلى الصفحة (الموجود أصلاً بشريط التنقّل / صفحة الدخول).
 *
 * تظهر مرة واحدة فقط لكل جلسة متصفح (sessionStorage) — حتى لا تتكرر مع كل
 * تنقّل بين الصفحات، فقط عند أول فتح فعلي للموقع.
 */
export default function SplashLogo() {
  const alreadyShown = typeof window !== 'undefined' && sessionStorage.getItem('neoshop-splash-shown') === '1'
  const [visible, setVisible] = useState(!alreadyShown)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    if (alreadyShown) return
    sessionStorage.setItem('neoshop-splash-shown', '1')

    const leaveTimer  = setTimeout(() => setLeaving(true), 1800)
    const removeTimer = setTimeout(() => setVisible(false), 2400)
    return () => { clearTimeout(leaveTimer); clearTimeout(removeTimer) }
  }, [alreadyShown])

  if (!visible) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'linear-gradient(160deg, #0b6e5c 0%, #084f41 100%)',
        opacity: leaving ? 0 : 1,
        transition: 'opacity 0.6s ease',
        pointerEvents: leaving ? 'none' : 'auto',
      }}
    >
      <div
        style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
          animation: leaving
            ? 'neoshopSplashOut 0.6s ease forwards'
            : 'neoshopSplashIn 0.7s cubic-bezier(0.34,1.56,0.64,1) forwards',
        }}
      >
        <div
          style={{
            width: 88, height: 88, borderRadius: 24,
            background: 'rgba(255,255,255,0.15)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 12px 40px rgba(0,0,0,0.25)',
            animation: 'neoshopSplashPulse 1.6s ease-in-out infinite',
          }}
        >
          <ShoppingBag style={{ width: 44, height: 44, color: '#fff' }} />
        </div>
        <p style={{ margin: 0, fontSize: 26, fontWeight: 900, letterSpacing: '0.08em', color: '#fff' }}>
          NEOSHOP
        </p>
      </div>

      <style>{`
        @keyframes neoshopSplashIn {
          0%   { opacity: 0; transform: scale(0.6); }
          100% { opacity: 1; transform: scale(1); }
        }
        @keyframes neoshopSplashOut {
          0%   { opacity: 1; transform: scale(1); }
          100% { opacity: 0; transform: scale(0.85) translateY(-10px); }
        }
        @keyframes neoshopSplashPulse {
          0%, 100% { transform: scale(1); }
          50%      { transform: scale(1.06); }
        }
      `}</style>
    </div>
  )
}
