import React from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore, useThemeStore, ADMIN_EMAILS } from '../../store'
import { ShoppingCart, User, Map, LogOut, ShoppingBag, Globe, Brain, Sun, Moon, Tag, Shield } from 'lucide-react'
import i18n from '../../i18n/index'

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { dark, toggleDark } = useThemeStore()
  const navigate = useNavigate()
  const isAdmin = user && ADMIN_EMAILS.includes(user.email)

  const handleLogout = () => { logout(); navigate('/login') }

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(next)
    document.body.dir = next === 'ar' ? 'rtl' : 'ltr'
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      {/* Navbar — fixed height, never moves */}
      <nav style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', flexShrink: 0, zIndex: 40 }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between" style={{ height: 56 }}>
          <NavLink to="/" className="flex items-center gap-2 font-extrabold text-lg" style={{ color: 'var(--primary)' }}>
            <ShoppingBag className="w-5 h-5" />
            NEOSHOP
          </NavLink>

          <div className="flex items-center gap-1">
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <ShoppingCart className="w-4 h-4" />
              <span className="hidden sm:inline">{t('pos')}</span>
            </NavLink>
            <NavLink to="/ai" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Brain className="w-4 h-4" />
              <span className="hidden sm:inline">{t('aiModel')}</span>
            </NavLink>
            <NavLink to="/map" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Map className="w-4 h-4" />
              <span className="hidden sm:inline">{t('map')}</span>
            </NavLink>
            <NavLink to="/offers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Tag className="w-4 h-4" />
              <span className="hidden sm:inline">{t('offers') || 'Offers'}</span>
            </NavLink>
            <NavLink to="/profile" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">{t('profile')}</span>
            </NavLink>

            {isAdmin && (
              <NavLink to="/admin" className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ms-1"
                style={{ background: 'linear-gradient(135deg,#1e40af,#312e81)', color: '#fff', boxShadow: '0 2px 8px rgba(30,64,175,0.35)' }}>
                <Shield className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{t('admin')}</span>
              </NavLink>
            )}

            <button onClick={toggleDark} className="nav-link" title={dark ? t('lightMode') : t('darkMode')}>
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button onClick={toggleLang} className="nav-link">
              <Globe className="w-4 h-4" />
              <span className="hidden sm:inline text-xs">{t('language')}</span>
            </button>

            <div className="flex items-center gap-2 ms-1 ps-2" style={{ borderInlineStart: '1px solid var(--border)' }}>
              <span className="text-xs hidden md:block" style={{ color: 'var(--text2)' }}>{user?.name}</span>
              <button onClick={handleLogout} className="nav-link !px-2" title={t('logout')}>
                <LogOut className="w-4 h-4 text-red-400" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Page content — fills remaining height, pages control their own scroll */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8" style={{ overflow: 'hidden', minHeight: 0 }}>
        <Outlet />
      </main>
    </div>
  )
}
