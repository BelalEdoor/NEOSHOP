import React, { useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore, ADMIN_EMAILS } from '../../store'
import { ShoppingCart, User, Map, LogOut, ShoppingBag, Globe, Brain, Tag, Shield } from 'lucide-react'
import i18n from '../../i18n/index'
import AccountDisabledModal from './AccountDisabledModal'

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout, accountDisabled } = useAuthStore()
  const navigate = useNavigate()
  const isAdmin = user && ADMIN_EMAILS.includes(user.email)

  // واجهة العميل/الموظف بنقطة البيع لازم تضل بالوضع الفاتح دائماً، بغض
  // النظر عن أي تفضيل "داكن" محفوظ سابقاً (مثلاً لو صاحب المتجر فعّل
  // الوضع الداكن آخر مرة كان بلوحة الأدمن على نفس الجهاز). بما إنّ Layout
  // هذا يبقى مثبّتاً طول فترة تواجد العميل بأي صفحة من صفحات نقطة البيع
  // (POS / AI / Map / Offers / Profile عبر <Outlet/> بدون إعادة تركيب)،
  // هذا التأثير يضمن بقاءها فاتحة بكل تنقّل، مش بس بنقطة البيع.
  useEffect(() => {
    document.documentElement.classList.remove('dark')
  }, [])

  const handleLogout = () => { logout(); navigate('/login') }

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(next)
    document.body.dir = next === 'ar' ? 'rtl' : 'ltr'
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      {/* Navbar — deep teal brand bar */}
      <nav style={{ background: 'var(--primary)', borderBottom: 'none', flexShrink: 0, zIndex: 40 }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between" style={{ height: 60 }}>
          <NavLink to="/" className="flex items-center gap-2 font-extrabold text-lg" style={{ color: '#fff' }}>
            <div style={{ width: 34, height: 34, background: 'var(--accent)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ShoppingBag className="w-5 h-5" style={{ color: 'var(--primary)' }} />
            </div>
            NEOSHOP
          </NavLink>

          <div className="flex items-center gap-1.5">
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <ShoppingCart className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline">{t('pos')}</span>
            </NavLink>
            <NavLink to="/ai" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Brain className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline">{t('aiModel')}</span>
            </NavLink>
            <NavLink to="/map" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Map className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline">{t('map')}</span>
            </NavLink>
            <NavLink to="/offers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Tag className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline">{t('offers') || 'Offers'}</span>
            </NavLink>
            <NavLink to="/profile" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <User className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline">{t('profile')}</span>
            </NavLink>

            {isAdmin && (
              <NavLink to="/admin" className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ms-1"
                style={{ background: 'var(--accent)', color: 'var(--primary)', boxShadow: '0 2px 8px rgba(15,212,160,0.35)' }}>
                <Shield className="w-4 h-4" />
                <span className="hidden sm:inline">{t('admin')}</span>
              </NavLink>
            )}

            <button onClick={toggleLang} className="nav-link">
              <Globe className="w-[18px] h-[18px]" />
              <span className="hidden sm:inline text-xs">{t('language')}</span>
            </button>

            <div className="flex items-center gap-2 ms-1 ps-2" style={{ borderInlineStart: '1px solid rgba(15,212,160,0.25)' }}>
              <span className="text-xs hidden md:block" style={{ color: 'rgba(255,255,255,0.6)' }}>{user?.name}</span>
              <button onClick={handleLogout} className="nav-link !px-2.5" title={t('logout')}>
                <LogOut className="w-[18px] h-[18px]" style={{ color: 'rgba(255,255,255,0.5)' }} />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Page content — fills remaining height; scrolls internally when content
          is taller than the viewport. Previously this was overflow:hidden,
          which silently clipped any page taller than the screen (Profile,
          AI scanner results, etc.) instead of letting the user scroll to it. */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8" style={{ overflowY: 'auto', minHeight: 0 }}>
        <Outlet />
      </main>

      {accountDisabled && <AccountDisabledModal />}
    </div>
  )
}
