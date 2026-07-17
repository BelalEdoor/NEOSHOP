/**
 * store/index.js
 * ==============
 * Zustand store — تحديث لدعم الهيكلية الموزّعة الجديدة.
 *
 * التغييرات:
 *   - إضافة useSessionStore (جلسة التسوق)
 *   - إضافة usePaymentStore (حالة الدفع)
 *   - useCartStore يعمل الآن عبر Session
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Admin emails — فقط هؤلاء يمكنهم الوصول للوحة الأدمن
export const ADMIN_EMAILS = ['admin@neoshop.com', 'owner@neoshop.com']

// ─── Auth Store ───────────────────────────────────────────────────────────────
export const useAuthStore = create(
  persist(
    (set, get) => ({
      user:  null,
      token: null,
      setAuth:  (user, token) => set({ user, token }),
      setUser:  (user)        => set({ user }),
      logout:   () => set({ user: null, token: null }),
      isAdmin:  () => {
        const { user } = get()
        return user && ADMIN_EMAILS.includes(user.email)
      },
    }),
    { name: 'neoshop-auth' }
  )
)

// ─── Theme Store ──────────────────────────────────────────────────────────────
export const useThemeStore = create(
  persist(
    (set, get) => ({
      dark: false,
      toggleDark: () => {
        const next = !get().dark
        set({ dark: next })
        document.documentElement.classList.toggle('dark', next)
      },
      init: () => {
        const { dark } = get()
        document.documentElement.classList.toggle('dark', dark)
      },
    }),
    { name: 'neoshop-theme' }
  )
)

// ─── Session Store (NEW) ──────────────────────────────────────────────────────
// يُخزّن حالة جلسة التسوق الحالية
export const useSessionStore = create(
  persist(
    (set, get) => ({
      session:    null,   // الجلسة الحالية من Backend
      sessionId:  null,
      cartStatus: 'ACTIVE',

      setSession: (session) => set({
        session,
        sessionId:  session?.id || null,
        cartStatus: session?.status || 'ACTIVE',
      }),

      updateStatus: (status) => set((state) => ({
        cartStatus: status,
        session: state.session ? { ...state.session, status } : null,
      })),

      updateTotal: (total) => set((state) => ({
        session: state.session ? { ...state.session, total_amount: total } : null,
      })),

      clearSession: () => set({ session: null, sessionId: null, cartStatus: 'ACTIVE' }),
    }),
    { name: 'neoshop-session' }
  )
)

// ─── Payment Store (NEW) ──────────────────────────────────────────────────────
export const usePaymentStore = create((set) => ({
  paymentStatus:  null,   // PENDING / IN_PROGRESS / COMPLETED / FAILED
  totalDue:       0,
  amountInserted: 0,
  changeReturned: 0,
  invoiceCode:    null,

  setPaymentData: (data) => set({
    paymentStatus:  data.payment_status || null,
    totalDue:       data.total_amount   || 0,
    amountInserted: data.amount_inserted || 0,
    changeReturned: data.change_returned || 0,
    invoiceCode:    data.invoice_code   || null,
  }),

  updatePayment: (data) => set((state) => ({
    amountInserted: data.amount_inserted ?? state.amountInserted,
    changeReturned: data.change_returned ?? state.changeReturned,
    paymentStatus:  data.status          ?? state.paymentStatus,
  })),

  clearPayment: () => set({
    paymentStatus: null, totalDue: 0,
    amountInserted: 0, changeReturned: 0, invoiceCode: null,
  }),
}))

// ─── Refill Alerts Store (NEW) ─────────────────────────────────────────────────
// مصدر واحد مشترك للتنبيهات النشطة (نفاد أنابيب العملات) — يستخدمه:
//   1. RefillNotifications.jsx (البطاقة العائمة + اتصال WebSocket الوحيد)
//   2. شارة العدد بالسايدبار (AdminLayout)
//   3. صفحة الإشعارات (AdminNotifications)
// بهاي الطريقة اتصال الـ WebSocket واحد بس، وكل الأماكن بتعرض نفس البيانات.
export const useRefillStore = create((set) => ({
  pendingAlerts: [],   // [{payment_id, invoice_code, remaining_change, device_id, ...}]

  setPendingAlerts: (alerts) => set({ pendingAlerts: alerts }),

  addPendingAlert: (alert) => set((state) => {
    if (state.pendingAlerts.some(a => a.payment_id === alert.payment_id)) return state
    return { pendingAlerts: [alert, ...state.pendingAlerts] }
  }),

  removePendingAlert: (paymentId) => set((state) => ({
    pendingAlerts: state.pendingAlerts.filter(a => a.payment_id !== paymentId),
  })),
}))