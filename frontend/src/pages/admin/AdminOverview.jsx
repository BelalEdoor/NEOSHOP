import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { productApi, analyticsApi } from '../../hooks/useApi'
import { formatPrice } from '../../utils/format'
import {
  TrendingUp, Package, AlertTriangle, FileText,
  DollarSign, ArrowUpRight, Inbox, RefreshCw,
  ShoppingCart, Loader2
} from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
} from 'recharts'

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

  // ─── تحليلات المتجر (Manager Analytics) ────────────────────────────────────
  const [salesAnalytics, setSalesAnalytics] = useState({
    total_revenue: 0,
    total_orders: 0,
    successful_orders: 0,
    cancelled_orders: 0,
    average_order_value: 0,
  })
  const [inventoryAnalytics, setInventoryAnalytics] = useState({
    total_products: 0,
    inventory_value: 0,
    healthy_inventory: 0,
    low_stock: 0,
    out_of_stock: 0,
  })
  const [salesTrends,         setSalesTrends]         = useState([])
  const [categoryPerformance, setCategoryPerformance] = useState([])
  const [topProducts,         setTopProducts]         = useState([])
  const [inventoryAlerts,     setInventoryAlerts]     = useState([])
  const [insights,            setInsights]            = useState([])
  const [analyticsLoading,    setAnalyticsLoading]    = useState(true)

  const loadAnalytics = () => {
    setAnalyticsLoading(true)
    Promise.all([
      analyticsApi.sales(),
      analyticsApi.inventory(),
      analyticsApi.salesTrends(30),
      analyticsApi.categoryPerformance(),
      analyticsApi.topProducts(5),
      analyticsApi.inventoryAlerts(),
      analyticsApi.insights(),
    ])
      .then(([sales, inventory, trends, category, top, alerts, ins]) => {
        setSalesAnalytics(sales.data)
        setInventoryAnalytics(inventory.data)
        setSalesTrends(trends.data || [])
        setCategoryPerformance(category.data || [])
        setTopProducts(top.data || [])
        setInventoryAlerts(alerts.data || [])
        setInsights(ins.data || [])
      })
      .catch(() => {})
      .finally(() => setAnalyticsLoading(false))
  }

  const reload = () => {
    setInvoices(loadInvoices())
    productApi.list({ limit: 200 }).then(({ data }) => setProducts(data)).catch(() => {}).finally(() => setLoading(false))
    loadAnalytics()
  }

  useEffect(() => {
    reload()
    const onStorage = (e) => { if (e.key === 'neoshop-invoices') setInvoices(loadInvoices()) }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])


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

  const sortedSalesTrends = [...salesTrends].sort((a, b) => new Date(a.date) - new Date(b.date))

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

      {/* ══ تحليلات المتجر (Manager Analytics) ══════════════════════════════ */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        <TrendingUp style={{ width: 16, height: 16, color: 'var(--primary)' }} />
        <h2 style={{ fontSize: 15, fontWeight: 800, color: 'var(--text)', margin: 0 }}>
          {isAr ? 'تحليلات المتجر' : 'Store Analytics'}
        </h2>
      </div>

      {/* Analytics stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
        <StatCard
          icon={DollarSign}
          label={isAr ? 'إجمالي إيرادات المبيعات' : 'Total Sales Revenue'}
          value={analyticsLoading ? '…' : formatPrice(salesAnalytics.total_revenue)}
          sub={`${salesAnalytics.total_orders} ${isAr ? 'طلب' : 'orders'}`}
          color="#2563eb"
        />
        <StatCard
          icon={ShoppingCart}
          label={isAr ? 'متوسط قيمة الطلب' : 'Average Order Value'}
          value={analyticsLoading ? '…' : formatPrice(salesAnalytics.average_order_value)}
          sub={`${salesAnalytics.successful_orders} ${isAr ? 'مدفوعة' : 'paid'} · ${salesAnalytics.cancelled_orders} ${isAr ? 'ملغاة' : 'cancelled'}`}
          color="#8b5cf6"
        />
        <StatCard
          icon={Package}
          label={isAr ? 'قيمة المخزون' : 'Inventory Value'}
          value={analyticsLoading ? '…' : formatPrice(inventoryAnalytics.inventory_value)}
          sub={`${inventoryAnalytics.total_products} ${isAr ? 'منتج' : 'products'}`}
          color="#10b981"
        />
        <StatCard
          icon={AlertTriangle}
          label={isAr ? 'نفاد المخزون' : 'Out of Stock'}
          value={analyticsLoading ? '…' : inventoryAnalytics.out_of_stock}
          sub={`${inventoryAnalytics.healthy_inventory} ${isAr ? 'بحالة جيدة' : 'healthy'}`}
          color="#ef4444"
        />
      </div>

      {/* Charts: Sales Trends + Category Performance */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 14 }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20, minWidth: 0 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
            {isAr ? 'اتجاهات المبيعات (30 يوم)' : 'Sales Trends (30 days)'}
          </h3>
          {salesTrends.length === 0 ? (
            <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)', fontSize: 13 }}>
              {isAr ? 'لا توجد بيانات' : 'No data available'}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={sortedSalesTrends} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => formatPrice(Number(value))} />
                <Line type="monotone" dataKey="revenue" name={isAr ? 'الإيرادات' : 'Revenue'} stroke="#2563eb" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20, minWidth: 0 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
            {isAr ? 'أداء الفئات' : 'Category Performance'}
          </h3>
          {categoryPerformance.length === 0 ? (
            <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)', fontSize: 13 }}>
              {isAr ? 'لا توجد بيانات' : 'No data available'}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={categoryPerformance} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="category" width={80} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => formatPrice(Number(value))} />
                <Bar dataKey="revenue" name={isAr ? 'الإيرادات' : 'Revenue'} fill="#10b981" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top Products + Inventory Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 14 }}>
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
            {isAr ? 'المنتجات الأكثر مبيعاً' : 'Top Selling Products'}
          </h3>
          {topProducts.length === 0 ? (
            <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
              {isAr ? 'لا توجد بيانات مبيعات' : 'No sales data'}
            </div>
          ) : topProducts.map((item) => (
            <div key={item.rank} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', margin: 0 }}>#{item.rank} {item.product}</p>
                <p style={{ fontSize: 11, color: 'var(--text3)', margin: '2px 0 0' }}>{item.category || '—'}</p>
              </div>
              <div style={{ textAlign: 'end', flexShrink: 0 }}>
                <p style={{ fontWeight: 800, fontSize: 13, color: 'var(--text)', margin: 0 }}>{item.quantity_sold} {isAr ? 'مباع' : 'sold'}</p>
                <p style={{ fontSize: 11, color: 'var(--text3)', margin: '2px 0 0' }}>{formatPrice(item.revenue)}</p>
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
            {isAr ? 'تنبيهات المخزون' : 'Inventory Alerts'}
          </h3>
          {inventoryAlerts.length === 0 ? (
            <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
              {isAr ? 'لا توجد تنبيهات حالياً' : 'No alerts'}
            </div>
          ) : inventoryAlerts.slice(0, 5).map((alert) => (
            <div key={alert.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', margin: 0 }}>{alert.product}</p>
                <span style={{
                  fontSize: 10, fontWeight: 800, padding: '3px 8px', borderRadius: 20, flexShrink: 0,
                  background: ['OUT_OF_STOCK', 'CRITICAL_STOCK', 'NO_SALES'].includes(alert.alert_type) ? '#fee2e2' : '#fef3c7',
                  color: ['OUT_OF_STOCK', 'CRITICAL_STOCK', 'NO_SALES'].includes(alert.alert_type) ? '#b91c1c' : '#92400e',
                }}>
                  {alert.alert_type.replaceAll('_', ' ')}
                </span>
              </div>
              <p style={{ fontSize: 11, color: 'var(--text3)', margin: '4px 0 0' }}>
                {isAr ? `المخزون: ${alert.current_stock} • المباع: ${alert.quantity_sold}` : `Stock: ${alert.current_stock} • Sold: ${alert.quantity_sold}`}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Smart Insights */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>
          {isAr ? 'رؤى ذكية' : 'Smart Insights'}
        </h3>
        {insights.length === 0 ? (
          <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
            {isAr ? 'لا توجد رؤى حالياً' : 'No insights available'}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
            {insights.map((insight, index) => {
              const isWarning = insight.severity === 'WARNING'
              return (
                <div key={`${insight.type}-${index}`} style={{
                  padding: 14, borderRadius: 12, border: '1px solid',
                  borderColor: isWarning ? '#fecaca' : '#bbf7d0',
                  background: isWarning ? '#fef2f2' : '#f0fdf4',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, gap: 8 }}>
                    <strong style={{ fontSize: 13 }}>{insight.title}</strong>
                    <span style={{
                      fontSize: 10, fontWeight: 800, padding: '3px 8px', borderRadius: 20, flexShrink: 0,
                      background: isWarning ? '#fee2e2' : '#dcfce7',
                      color: isWarning ? '#b91c1c' : '#15803d',
                    }}>
                      {isWarning ? (isAr ? 'تنبيه' : 'Warning') : (isAr ? 'معلومة' : 'Info')}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, lineHeight: 1.6, color: 'var(--text2)', margin: 0 }}>{insight.message}</p>
                </div>
              )
            })}
          </div>
        )}
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

      <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
    </div>
  )
}
