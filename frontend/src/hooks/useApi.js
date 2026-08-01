/**
 * useApi.js
 * =========
 * HTTP client للتواصل مع Backend الجديد.
 * تم تحديث الـ endpoints لتتوافق مع الهيكلية الموزّعة.
 *
 * التغييرات الرئيسية:
 *   - إضافة sessionApi (إدارة جلسات التسوق)
 *   - تحديث cartApi → يعمل عبر sessions الآن
 *   - إضافة paymentApi
 *   - إضافة theftApi
 *   - الـ baseURL تقرأ من VITE_API_URL
 */
import axios from 'axios'
import { useAuthStore } from '../store'

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api'
const WS_BASE  = import.meta.env.VITE_WS_URL  || 'ws://localhost:8000'
export { BASE_URL }

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Auth interceptor ────────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('neoshop-auth')
  if (raw) {
    try {
      const { state } = JSON.parse(raw)
      if (state?.token) config.headers.Authorization = `Bearer ${state.token}`
    } catch (_) {}
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // الحساب مُعطَّل من لوحة الأدمن (مثلاً بعد رصد نشاط مشبوه) — أظهر شاشة
    // منبثقة على صفحة الحساب بدل تسجيل خروج صامت. راجع
    // components/ui/AccountDisabledModal.jsx المثبَّت بـ Layout.jsx.
    if (err.response?.status === 403 && err.response?.data?.detail === 'Account disabled') {
      useAuthStore.getState().setAccountDisabled(true)
      return Promise.reject(err)
    }
    if (err.response?.status === 401) {
      const isAdminRoute = window.location.pathname.startsWith('/admin')
      const raw = localStorage.getItem('neoshop-auth')
      let hadToken = false
      try { hadToken = !!JSON.parse(raw)?.state?.token } catch (_) {}
      if (!isAdminRoute && hadToken) {
        localStorage.removeItem('neoshop-auth')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
}

// ─── User ─────────────────────────────────────────────────────────────────────
export const userApi = {
  getMe:    () => api.get('/users/me'),
  updateMe: (data) => api.put('/users/me', data),
}

// ─── Products ─────────────────────────────────────────────────────────────────
export const productApi = {
  list:      (params) => api.get('/products/', { params }),
  get:       (id)     => api.get(`/products/${id}`),
  byBarcode: (barcode) => api.get(`/products/barcode/${barcode}`),
  create:    (data)   => api.post('/products/', data),
  update:    (id, data) => api.put(`/products/${id}`, data),
  remove:    (id)     => api.delete(`/products/${id}`),
}

// ─── Sessions (NEW — إدارة جلسات التسوق) ─────────────────────────────────────
export const sessionApi = {
  /** بدء جلسة تسوق جديدة عند تسجيل الدخول */
  start:    (cartRfid = null) => api.post('/sessions/start', null, {
    params: cartRfid ? { cart_rfid: cartRfid } : {},
  }),
  /** الجلسة النشطة الحالية للعميل */
  getActive: () => api.get('/sessions/active'),
  /** جلسة محددة بالـ ID */
  get:       (sessionId) => api.get(`/sessions/${sessionId}`),
  /** مسح باركود وإضافة منتج إلى الجلسة */
  scanProduct: (sessionId, barcode, quantity = 1) =>
    api.post(`/sessions/${sessionId}/scan`, null, {
      params: { barcode, quantity },
    }),
  /** إزالة منتج من الجلسة */
  removeProduct: (sessionId, productId) =>
    api.delete(`/sessions/${sessionId}/remove/${productId}`),
  /** إنهاء التسوق → PENDING_PAYMENT + إنشاء فاتورة */
  finish:    (sessionId) => api.post(`/sessions/${sessionId}/finish`),
}

// ─── Cart (legacy compatibility — يعمل عبر Sessions الآن) ────────────────────
export const cartApi = {
  /** جلب عناصر الجلسة النشطة */
  get: async () => {
    const activeRes = await sessionApi.getActive()
    return activeRes  // الـ session يحتوي على items
  },
  /** إضافة منتج عبر barcode */
  addByBarcode: async (sessionId, barcode) =>
    sessionApi.scanProduct(sessionId, barcode),
  /** إزالة منتج */
  remove: (sessionId, productId) =>
    sessionApi.removeProduct(sessionId, productId),
  /** إنهاء التسوق */
  finish: (sessionId) => sessionApi.finish(sessionId),
}

// ─── Invoices ─────────────────────────────────────────────────────────────────
export const invoiceApi = {
  list:   (params) => api.get('/invoices/', { params }),
  get:    (id)     => api.get(`/invoices/${id}`),
  delete: (id)     => api.delete(`/invoices/${id}`),
}

// ─── Payment ──────────────────────────────────────────────────────────────────
export const paymentApi = {
  getStatus:    (sessionId) => api.get(`/payments/status/${sessionId}`),
  getPayments:  (sessionId) => api.get(`/payments/session/${sessionId}`),
  cancel:       (paymentId) => api.post(`/payments/cancel/${paymentId}`),
  // NEW — نفاد أنابيب العملات وتعبئتها
  getPendingRefills: () => api.get('/payments/pending-refills'),
  confirmRefill:     (paymentId) => api.post(`/payments/confirm-refill/${paymentId}`),
  getRefillNotifications: (limit = 100) => api.get('/payments/refill-notifications', { params: { limit } }),
  deleteRefillNotification: (paymentId) => api.delete(`/payments/refill-notifications/${paymentId}`),
  forceReactivate: (paymentId) => api.post(`/payments/force-reactivate/${paymentId}`),
}

// ─── Analysis (AI) ────────────────────────────────────────────────────────────
export const analysisApi = {
  check:       (product_id, user_allergies) =>
    api.post('/analysis/check', { product_id, user_allergies }),
  quickCheck:  (product_id) =>
    api.get(`/analysis/quick/${product_id}`),
  aiAnalysis:  (product_id) =>
    api.post(`/analysis/ai/${product_id}`),
  barcodeScan: (barcode) =>
    api.get(`/analysis/barcode-scan/${barcode}`),
}

// ─── Onboarding (allergies / health conditions picked right after register) ──
export const allergensApi = {
  list: () => api.get('/analysis/allergens'),
}

export const healthConditionsApi = {
  list: () => api.get('/analysis/health-conditions'),
}

export const onboardingApi = {
  submit: (payload) => api.post('/analysis/onboarding', payload),
}

// ─── Theft / Security ─────────────────────────────────────────────────────────
export const theftApi = {
  listAlerts:   (params) => api.get('/theft/', { params }),
  resolveAlert: (alertId) => api.patch(`/theft/${alertId}/resolve`),
}

// ─── Admin Dashboard ──────────────────────────────────────────────────────────
export const adminApi = {
  overview:    () => api.get('/admin/overview'),
  topProducts: (limit = 10) => api.get('/admin/top-products', { params: { limit } }),
  salesSummary: () => api.get('/admin/sales-summary'),
}

// ─── Admin — حسابات العملاء (AdminCustomers.jsx) ───────────────────────────────
export const adminCustomerApi = {
  list:      (q) => api.get('/users/admin/customers', { params: q ? { q } : {} }),
  get:       (id) => api.get(`/users/admin/customers/${id}`),
  getInvoices: (id) => api.get(`/users/admin/customers/${id}/invoices`),
  update:    (id, data) => api.put(`/users/admin/customers/${id}`, data),
  resetPassword: (id, newPassword) => api.post(`/users/admin/customers/${id}/reset-password`, { new_password: newPassword }),
  disable:   (id) => api.post(`/users/${id}/disable`),
  enable:    (id) => api.post(`/users/${id}/enable`),
}

// ─── WebSocket helpers ────────────────────────────────────────────────────────
export const createCartWebSocket = (sessionId) => {
  const token = (() => {
    try {
      const raw = localStorage.getItem('neoshop-auth')
      return JSON.parse(raw)?.state?.token || ''
    } catch { return '' }
  })()
  return new WebSocket(`${WS_BASE}/ws/cart/${sessionId}`)
}

export const createAdminWebSocket = () =>
  new WebSocket(`${WS_BASE}/ws/admin`)

export default api