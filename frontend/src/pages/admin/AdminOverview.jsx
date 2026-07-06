import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { productApi } from '../../hooks/useApi'
import api from '../../hooks/useApi'
import { formatPrice } from '../../utils/format'
import {
  TrendingUp, Package, AlertTriangle, FileText,
  DollarSign, ArrowUpRight, Inbox, RefreshCw,
  ShoppingCart, Plus, Wifi, CheckCircle2, XCircle, Loader2
} from 'lucide-react'

function loadInvoices() {
  try { return JSON.parse(localStorage.getItem('neoshop-invoices') || '[]') } catch { return [] }
}

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div style={{ borderRadius: 18, padding: 20, background: 'var(--surface)', border: '1px solid var(--border)', transition: 'all 0.2s' }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)' }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ width: 44, height: 44, borderRadius: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', background: color + '18' }}>
          <Icon style={{ width: 20, height: 20, color }} />
        </div>
      </div>
      <p style={{ fontSize: 26, fontWeight: 900, margin: 0, color: 'var(--text)' }}>{value}</p>
      <p style={{ fontSize: 13, fontWeight: 600, margin: '2px 0 0', color: 'var(--text2)' }}>{label}</p>
      {sub && <p style={{ fontSize: 11, margin: '4px 0 0', color: 'var(--text3)' }}>{sub}</p>}
    </div>
  )
}

export default function AdminOverview() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [invoices, setInvoices]   = useState([])
  const [products, setProducts]   = useState([])
  const [loading,  setLoading]    = useState(true)

  // ─── Cart Registration State ──────────────────────────────────────────────
  const [cartNumber,    setCartNumber]    = useState('')
  const [rfidUid,       setRfidUid]       = useState('')
  const [cartSaving,    setCartSaving]    = useState(false)
  const [cartMsg,       setCartMsg]       = useState(null)   // {type:'success'|'error', text:''}
  const [registeredCarts, setRegisteredCarts] = useState([])
  const [cartsLoading,  setCartsLoading]  = useState(false)

  const loadCarts = async () => {
    setCartsLoading(true)
    try {
      const { data } = await api.get('/carts/')
      setRegisteredCarts(data || [])
    } catch { setRegisteredCarts([]) }
    finally { setCartsLoading(false) }
  }

  const reload = () => {
    setInvoices(loadInvoices())
    productApi.list({ limit: 200 }).then(({ data }) => setProducts(data)).catch(() => {}).finally(() => setLoading(false))
    loadCarts()
  }

  useEffect(() => {
    reload()
    const onStorage = (e) => { if (e.key === 'neoshop-invoices') setInvoices(loadInvoices()) }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const handleRegisterCart = async () => {
    if (!cartNumber.trim() || !rfidUid.trim()) {
      setCartMsg({ type: 'error', text: isAr ? 'يرجى ملء جميع الحقول' : 'Please fill all fields' })
      return
    }
    setCartSaving(true)
    setCartMsg(null)
    try {
      await api.post(`/carts/register?cart_number=${encodeURIComponent(cartNumber.trim())}&rfid_uid=${encodeURIComponent(rfidUid.trim())}`)
      setCartMsg({ type: 'success', text: isAr ? `✅ تم تسجيل ${cartNumber} بنجاح!` : `✅ ${cartNumber} registered!` })
      setCartNumber('')
      setRfidUid('')
      loadCarts()
    } catch (err) {
      const detail = err.response?.data?.detail || (isAr ? 'فشل التسجيل' : 'Registration failed')
      setCartMsg({ type: 'error', text: `❌ ${detail}` })
    } finally { setCartSaving(false) }
  }

  const completedInvoices = invoices.filter(i => i.status === 'completed')
  const pendingInvoices   = invoices.filter(i => i.status === 'pending')
  const totalRevenue      = completedInvoices.reduce((a, i) => a + (i.total || 0), 0)
  const lowStock          = products.filter(p => p.quantity !== undefined && p.quantity < 10)

  // Recent invoices (last 5)
  const recentInvoices = [...invoices].slice(0, 5)

  const STATUS_STYLES = {
    pending:   { bg: '#fef9c3', color: '#854d0e', label: isAr ? 'انتظار' : 'Pending' },
    completed: { bg: '#dcfce7', color: '#15803d', label: isAr ? 'مكتملة' : 'Completed' },
    rejected:  { bg: '#fee2e2', color: '#dc2626', label: isAr ? 'مرفوضة' : 'Rejected' },
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%', overflowY: 'auto', paddingBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 900, color: 'var(--text)', margin: 0 }}>{t('adminDashboard')}</h1>
          <p style={{ fontSize: 12, color: 'var(--text3)', margin: '3px 0 0' }}>{isAr ? 'نظرة عامة على المتجر' : 'Store at a glance'}</p>
        </div>
        <button onClick={reload} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '7px 14px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text2)', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>
          <RefreshCw style={{ width: 13, height: 13 }} />{isAr ? 'تحديث' : 'Refresh'}
        </button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
        <StatCard icon={DollarSign}  label={isAr ? 'إيرادات مكتملة' : 'Completed Revenue'} value={formatPrice(totalRevenue)}   sub={`${completedInvoices.length} ${isAr ? 'فاتورة مكتملة' : 'completed invoices'}`} color="#2563eb" />
        <StatCard icon={FileText}    label={isAr ? 'فواتير قيد الانتظار' : 'Pending Invoices'} value={pendingInvoices.length}       sub={isAr ? 'تحتاج مراجعة' : 'Need review'} color="#d97706" />
        <StatCard icon={Package}     label={isAr ? 'إجمالي المنتجات' : 'Total Products'}     value={loading ? '…' : products.length} sub={isAr ? 'في قاعدة البيانات' : 'In database'} color="#10b981" />
        <StatCard icon={AlertTriangle} label={isAr ? 'مخزون منخفض' : 'Low Stock'}           value={loading ? '…' : lowStock.length} sub={isAr ? 'أقل من 10 قطع' : 'Below 10 units'} color="#ef4444" />
      </div>

      {/* Recent invoices */}
      <div style={{ borderRadius: 18, background: 'var(--surface)', border: '1px solid var(--border)', overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid var(--border)' }}>
          <h3 style={{ fontWeight: 800, fontSize: 14, color: 'var(--text)', margin: 0 }}>{isAr ? 'آخر الفواتير' : 'Recent Invoices'}</h3>
          {invoices.length > 5 && <span style={{ fontSize: 11, color: 'var(--text3)' }}>{isAr ? `${invoices.length} إجمالاً` : `${invoices.length} total`}</span>}
        </div>
        {recentInvoices.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 0', color: 'var(--text3)' }}>
            <Inbox style={{ width: 40, height: 40, opacity: 0.18, marginBottom: 10 }} />
            <p style={{ fontSize: 13, fontWeight: 600 }}>{isAr ? 'لا توجد فواتير بعد' : 'No invoices yet'}</p>
            <p style={{ fontSize: 11, marginTop: 4 }}>{isAr ? 'ستظهر هنا عند ترحيل فواتير من نقطة البيع' : 'Appears when POS invoices are submitted'}</p>
          </div>
        ) : recentInvoices.map((inv, idx) => {
          const s = STATUS_STYLES[inv.status] || STATUS_STYLES.pending
          return (
            <div key={inv.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 18px', borderBottom: idx < recentInvoices.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ width: 34, height: 34, borderRadius: 10, background: 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <FileText style={{ width: 16, height: 16, color: 'var(--primary)' }} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', margin: 0 }}>#{inv.id}</p>
                <p style={{ fontSize: 11, color: 'var(--text3)', margin: '1px 0 0' }}>{inv.cashier} · {inv.date}</p>
              </div>
              <div style={{ textAlign: 'end', flexShrink: 0 }}>
                <p style={{ fontWeight: 800, fontSize: 14, color: 'var(--primary)', margin: 0 }}>{formatPrice(inv.total || 0)}</p>
                <span style={{ padding: '2px 7px', borderRadius: 8, fontSize: 10, fontWeight: 700, background: s.bg, color: s.color }}>{s.label}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Low stock */}
      {!loading && lowStock.length > 0 && (
        <div style={{ borderRadius: 18, background: 'var(--surface)', border: '1.5px solid #fde68a', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '14px 18px', borderBottom: '1px solid #fde68a' }}>
            <AlertTriangle style={{ width: 18, height: 18, color: '#d97706' }} />
            <h3 style={{ fontWeight: 800, fontSize: 14, color: '#92400e', margin: 0 }}>{t('lowStockAlerts')} ({lowStock.length})</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, padding: 14 }}>
            {lowStock.map(p => (
              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, borderRadius: 12, padding: '10px 12px', background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</p>
                  <p style={{ fontSize: 11, fontWeight: 800, margin: '2px 0 0', color: p.quantity <= 3 ? '#dc2626' : '#d97706' }}>
                    {p.quantity} {isAr ? 'متبقي' : 'left'} {p.quantity <= 3 && '⚠️'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ══ Cart Registration ══════════════════════════════════════════════ */}
      <div style={{ borderRadius: 18, background: 'var(--surface)', border: '1.5px solid var(--border)', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderBottom: '1px solid var(--border)', background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: 'rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShoppingCart style={{ width: 18, height: 18, color: '#fff' }} />
          </div>
          <div>
            <h3 style={{ fontWeight: 800, fontSize: 14, color: '#fff', margin: 0 }}>
              {isAr ? 'تسجيل عربة جديدة' : 'Register New Cart'}
            </h3>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.7)', margin: '2px 0 0' }}>
              {isAr ? 'ربط RFID UID بعربة تسوق' : 'Link RFID UID to a shopping cart'}
            </p>
          </div>
        </div>

        <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* How to get RFID */}
          <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 12, padding: '10px 14px' }}>
            <p style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8', margin: '0 0 4px' }}>
              {isAr ? '📡 كيف تحصل على RFID UID؟' : '📡 How to get RFID UID?'}
            </p>
            <p style={{ fontSize: 11, color: '#1e40af', margin: 0, lineHeight: 1.6 }}>
              {isAr
                ? 'افتح Arduino IDE → Serial Monitor (115200 baud) → قرّب بطاقة RFID من RC522 → انسخ الـ UID الظاهر'
                : 'Open Arduino IDE → Serial Monitor (115200 baud) → Bring RFID card near RC522 → Copy the UID shown'}
            </p>
            <p style={{ fontSize: 11, color: '#3b82f6', margin: '4px 0 0', fontFamily: 'monospace', fontWeight: 700 }}>
              [RFID] Card detected: A1:B2:C3:D4
            </p>
          </div>

          {/* Input fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text2)', display: 'block', marginBottom: 6 }}>
                {isAr ? 'رقم العربة' : 'Cart Number'}
              </label>
              <input
                value={cartNumber}
                onChange={e => setCartNumber(e.target.value)}
                placeholder="CART-001"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1.5px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, fontWeight: 600, outline: 'none', boxSizing: 'border-box', fontFamily: 'monospace' }}
                onFocus={e => e.target.style.borderColor = '#4f46e5'}
                onBlur={e => e.target.style.borderColor = 'var(--border)'}
              />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text2)', display: 'block', marginBottom: 6 }}>
                {isAr ? 'RFID UID (من Serial Monitor)' : 'RFID UID (from Serial Monitor)'}
              </label>
              <input
                value={rfidUid}
                onChange={e => setRfidUid(e.target.value)}
                placeholder="A1:B2:C3:D4"
                dir="ltr"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1.5px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, fontWeight: 700, outline: 'none', boxSizing: 'border-box', fontFamily: 'monospace', letterSpacing: '0.05em' }}
                onFocus={e => e.target.style.borderColor = '#4f46e5'}
                onBlur={e => e.target.style.borderColor = 'var(--border)'}
              />
            </div>
          </div>

          {/* Message */}
          {cartMsg && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderRadius: 10, background: cartMsg.type === 'success' ? '#f0fdf4' : '#fef2f2', border: `1px solid ${cartMsg.type === 'success' ? '#86efac' : '#fca5a5'}` }}>
              {cartMsg.type === 'success'
                ? <CheckCircle2 style={{ width: 16, height: 16, color: '#16a34a', flexShrink: 0 }} />
                : <XCircle     style={{ width: 16, height: 16, color: '#dc2626', flexShrink: 0 }} />
              }
              <p style={{ fontSize: 12, fontWeight: 700, margin: 0, color: cartMsg.type === 'success' ? '#15803d' : '#dc2626' }}>
                {cartMsg.text}
              </p>
            </div>
          )}

          {/* Register button */}
          <button
            onClick={handleRegisterCart}
            disabled={cartSaving || !cartNumber.trim() || !rfidUid.trim()}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '11px 0', borderRadius: 12, border: 'none', background: !cartNumber.trim() || !rfidUid.trim() ? 'var(--text3)' : '#4f46e5', color: '#fff', fontWeight: 800, fontSize: 14, cursor: !cartNumber.trim() || !rfidUid.trim() ? 'not-allowed' : 'pointer', opacity: !cartNumber.trim() || !rfidUid.trim() ? 0.5 : 1, transition: 'all 0.15s' }}
            onMouseEnter={e => { if (cartNumber.trim() && rfidUid.trim()) e.currentTarget.style.background = '#3730a3' }}
            onMouseLeave={e => { if (cartNumber.trim() && rfidUid.trim()) e.currentTarget.style.background = '#4f46e5' }}>
            {cartSaving
              ? <Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} />
              : <Plus style={{ width: 16, height: 16 }} />
            }
            {isAr ? 'تسجيل العربة' : 'Register Cart'}
          </button>

          {/* Registered carts list */}
          {cartsLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0' }}>
              <Loader2 style={{ width: 20, height: 20, color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
            </div>
          ) : registeredCarts.length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', margin: '0 0 8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {isAr ? `العربات المسجّلة (${registeredCarts.length})` : `Registered Carts (${registeredCarts.length})`}
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {registeredCarts.map(cart => (
                  <div key={cart.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderRadius: 10, background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{ width: 32, height: 32, borderRadius: 8, background: '#ede9fe', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <ShoppingCart style={{ width: 15, height: 15, color: '#7c3aed' }} />
                      </div>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 800, color: 'var(--text)', margin: 0 }}>{cart.cart_number}</p>
                        <p style={{ fontSize: 11, color: 'var(--text3)', margin: '2px 0 0', fontFamily: 'monospace', letterSpacing: '0.04em' }}>{cart.rfid_uid}</p>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Wifi style={{ width: 13, height: 13, color: '#16a34a' }} />
                      <span style={{ fontSize: 10, fontWeight: 700, color: '#15803d', background: '#dcfce7', padding: '2px 8px', borderRadius: 8 }}>
                        {cart.status || 'ACTIVE'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
    </div>
  )
}
