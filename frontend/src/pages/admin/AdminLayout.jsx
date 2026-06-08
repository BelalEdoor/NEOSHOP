import React, { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore, useThemeStore } from '../../store'
import i18n from '../../i18n/index'
import {
  LayoutDashboard, Package, FileText, Users, Truck, BarChart3,
  ChevronLeft, ChevronRight, ShieldAlert, LogOut, Sun, Moon,
  ShoppingBag, Shield, Menu, Globe, ShoppingCart
} from 'lucide-react'

export default function AdminLayout() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { dark, toggleDark } = useThemeStore()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const isAr = i18n.language === 'ar'

  const NAV_ITEMS = [
    { to: '/admin',            icon: LayoutDashboard, labelKey: 'adminDashboard', end: true },
    { to: '/admin/products',   icon: Package,         labelKey: 'productsTitle'  },
    { to: '/admin/carts',      icon: ShoppingCart,    labelKey: 'cartsTitle'     },
    { to: '/admin/invoices',   icon: FileText,        labelKey: 'invoicesTitle'  },
    { to: '/admin/employees',  icon: Users,           labelKey: 'employeesTitle' },
    { to: '/admin/inventory',  icon: BarChart3,       labelKey: 'inventoryTitle' },
    { to: '/admin/suppliers',  icon: Truck,           labelKey: 'suppliersTitle' },
  ]

  const handleLogout = () => { logout(); navigate('/login') }

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(next)
  }

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-white/20 shrink-0">
          <Shield className="w-5 h-5 text-white" />
        </div>
        {!collapsed && (
          <div>
            <p className="font-extrabold text-white text-sm tracking-wider">NEOSHOP</p>
            <p className="text-white/50 text-[10px] uppercase tracking-widest">{t('adminPanel')}</p>
          </div>
        )}
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        {NAV_ITEMS.map(({ to, icon: Icon, labelKey, end }) => (
          <NavLink
            key={to} to={to} end={end}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 mx-3 mb-1 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                isActive ? 'bg-white/20 text-white shadow-lg' : 'text-white/60 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {!collapsed && <span>{t(labelKey)}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
        {!collapsed && (
          <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-xl bg-white/10">
            <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center text-white font-bold text-sm">
              {user?.name?.[0] || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-xs font-bold truncate">{user?.name || 'Admin'}</p>
              <p className="text-white/50 text-[10px] truncate">{user?.email}</p>
            </div>
          </div>
        )}
        <div className="flex items-center gap-1 flex-wrap">
          <button onClick={toggleDark}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-white/60 hover:bg-white/10 hover:text-white transition-all text-xs"
            title={dark ? t('lightMode') : t('darkMode')}>
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {!collapsed && (dark ? t('lightMode') : t('darkMode'))}
          </button>
          <button onClick={toggleLang}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-white/60 hover:bg-white/10 hover:text-white transition-all text-xs">
            <Globe className="w-4 h-4" />
            {!collapsed && t('language')}
          </button>
          <button onClick={handleLogout}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-red-300 hover:bg-red-500/20 hover:text-red-200 transition-all text-xs">
            <LogOut className="w-4 h-4" />
            {!collapsed && t('logout')}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div style={{ height: "100vh", display: "flex", overflow: "hidden", background: 'var(--bg)', fontFamily: "'Cairo', sans-serif" }}>
      {/* Desktop Sidebar */}
      <aside
        className="hidden lg:flex flex-col sticky top-0 h-screen transition-all duration-300 shrink-0"
        style={{
          width: collapsed ? '72px' : '220px',
          background: 'linear-gradient(160deg, #1e3a8a 0%, #1e40af 40%, #312e81 100%)',
        }}
      >
        <SidebarContent />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -end-3 top-20 w-6 h-6 rounded-full flex items-center justify-center text-white shadow-lg z-10 transition-all"
          style={{ background: '#1e40af', border: '2px solid rgba(255,255,255,0.2)' }}
        >
          {collapsed
            ? (isAr ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />)
            : (isAr ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />)
          }
        </button>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute start-0 top-0 h-full w-64 flex flex-col"
            style={{ background: 'linear-gradient(160deg, #1e3a8a 0%, #1e40af 40%, #312e81 100%)' }}>
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="sticky top-0 z-30 flex items-center justify-between px-6 py-3 shadow-sm"
          style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 rounded-xl transition-colors"
              style={{ color: 'var(--text2)' }}>
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="font-extrabold text-base" style={{ color: 'var(--text)' }}>{t('adminDashboard')}</h2>
              <p className="text-xs" style={{ color: 'var(--text3)' }}>{t('adminSubtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/')}
              className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all"
              style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              {t('backToPOS')}
            </button>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center font-bold text-sm text-white"
              style={{ background: 'linear-gradient(135deg, #1e40af, #6366f1)' }}>
              {user?.name?.[0] || 'A'}
            </div>
          </div>
        </header>

        <main style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
