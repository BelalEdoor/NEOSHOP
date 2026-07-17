import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore, useThemeStore, ADMIN_EMAILS } from './store'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OnboardingPage from './pages/OnboardingPage'
import POSPage from './pages/POSPage'
import AIModelPage from './pages/AIModelPage'
import ProfilePage from './pages/ProfilePage'
import MapPage from './pages/MapPage'
import OffersPage from './pages/OffersPage'
import Layout from './components/ui/Layout'
import SplashLogo from './components/ui/SplashLogo'
import AdminLayout from './pages/admin/AdminLayout'
import AdminOverview from './pages/admin/AdminOverview'
import AdminNotifications from './pages/admin/AdminNotifications'
import AdminMap from './pages/admin/AdminMap'
import AdminProducts from './pages/admin/AdminProducts'
import AdminCarts from './pages/admin/AdminCarts'
import AdminInvoices from './pages/admin/AdminInvoices'
import AdminEmployees from './pages/admin/AdminEmployees'
import AdminInventory from './pages/admin/AdminInventory'
import AdminSuppliers from './pages/admin/AdminSuppliers'
import './i18n'

function RequireAuth({ children }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }) {
  const { token, user } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  if (!ADMIN_EMAILS.includes(user?.email)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const init = useThemeStore((s) => s.init)
  useEffect(() => { init() }, [init])

  return (
    <BrowserRouter>
      <SplashLogo />
      <Toaster position="top-center" toastOptions={{ duration: 3500, style: { fontFamily: 'Cairo, sans-serif' } }} />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />

        {/* Main POS Layout */}
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<POSPage />} />
          <Route path="ai" element={<AIModelPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="offers" element={<OffersPage />} />
        </Route>

        {/* Admin Dashboard Layout */}
        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <AdminLayout />
            </RequireAdmin>
          }
        >
          <Route index element={<AdminOverview />} />
          <Route path="notifications" element={<AdminNotifications />} />
          <Route path="map" element={<AdminMap />} />
          <Route path="products"  element={<AdminProducts />} />
          <Route path="carts"     element={<AdminCarts />} />
          <Route path="invoices"  element={<AdminInvoices />} />
          <Route path="employees" element={<AdminEmployees />} />
          <Route path="inventory" element={<AdminInventory />} />
          <Route path="suppliers" element={<AdminSuppliers />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}