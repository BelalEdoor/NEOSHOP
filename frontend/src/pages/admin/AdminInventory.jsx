import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { productApi } from '../../hooks/useApi'
import { AlertTriangle, CheckCircle, TrendingDown } from 'lucide-react'

export default function AdminInventory() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const [products, setProducts] = useState([])

  useEffect(() => {
    productApi.list({ limit: 200 }).then(({ data }) => setProducts(data)).catch(() => {})
  }, [])
  const [filter, setFilter] = useState('all')

  const low = products.filter(p => (p.quantity ?? p.stock ?? 0) <= 5)
  const medium = products.filter(p => (p.quantity ?? p.stock ?? 0) > 5 && (p.quantity ?? p.stock ?? 0) <= 15)
  const good = products.filter(p => (p.quantity ?? p.stock ?? 0) > 15)
  const filtered = filter === 'low' ? low : filter === 'medium' ? medium : filter === 'good' ? good : products

  const getStockLevel = (stock) => {
    if (stock <= 5) return { label: t('criticalStock'), color: '#ef4444', bg: '#fee2e2', pct: Math.min(100, stock * 5) }
    if (stock <= 15) return { label: t('lowStockWarning'), color: '#f59e0b', bg: '#fef3c7', pct: Math.min(100, stock * 3) }
    return { label: t('normalStock'), color: '#22c55e', bg: '#dcfce7', pct: Math.min(100, (stock / 200) * 100) }
  }

  const handleUpdateStock = (id, delta) => {
    setProducts(prev => prev.map(p => p.id === id ? { ...p, quantity: Math.max(0, (p.quantity ?? p.stock ?? 0) + delta), stock: Math.max(0, (p.quantity ?? p.stock ?? 0) + delta) } : p))
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>{t('inventoryTitle')}</h1>
        <p className="text-sm" style={{ color: 'var(--text3)' }}>{t('inventorySubtitle')}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: t('criticalStock'), value: low.length, icon: AlertTriangle, color: '#ef4444', bg: '#fee2e2' },
          { label: t('lowStockWarning'), value: medium.length, icon: TrendingDown, color: '#f59e0b', bg: '#fef3c7' },
          { label: t('normalStock'), value: good.length, icon: CheckCircle, color: '#22c55e', bg: '#dcfce7' },
        ].map(s => (
          <div key={s.label} className="rounded-2xl p-4 flex items-center gap-3"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: s.bg }}>
              <s.icon className="w-5 h-5" style={{ color: s.color }} />
            </div>
            <div>
              <p className="text-xl font-extrabold" style={{ color: s.color }}>{s.value}</p>
              <p className="text-xs font-semibold" style={{ color: 'var(--text3)' }}>{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-1 p-1 w-fit rounded-xl" style={{ background: 'var(--surface2)' }}>
        {[
          { key: 'all', label: t('all') },
          { key: 'low', label: `🔴 ${t('criticalStock')}` },
          { key: 'medium', label: `🟡 ${t('lowStockWarning')}` },
          { key: 'good', label: `🟢 ${t('normalStock')}` },
        ].map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className="px-4 py-1.5 rounded-lg text-xs font-bold transition-all"
            style={filter===f.key ? { background: 'var(--primary)', color: '#fff' } : { color: 'var(--text2)' }}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map(p => {
          const sl = getStockLevel(p.quantity ?? p.stock ?? 0)
          return (
            <div key={p.id} className="flex items-center gap-4 p-4 rounded-2xl transition-all hover:shadow-sm"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              {p.image && <img src={p.image} alt={p.name} className="w-12 h-12 rounded-xl object-cover shrink-0" />}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <p className="font-bold text-sm truncate" style={{ color: 'var(--text)' }}>
                    {isAr && p.name_ar ? p.name_ar : p.name}
                  </p>
                  <span className="text-xs px-2 py-0.5 rounded-full font-bold shrink-0"
                    style={{ background: sl.bg, color: sl.color }}>{sl.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--surface2)' }}>
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${sl.pct}%`, background: sl.color }} />
                  </div>
                  <span className="text-xs font-extrabold shrink-0" style={{ color: sl.color }}>{p.quantity ?? p.stock ?? 0}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => handleUpdateStock(p.id, -10)}
                  className="w-8 h-8 rounded-lg font-bold text-sm transition-all text-red-400 hover:bg-red-50">−</button>
                <span className="w-12 text-center text-sm font-extrabold" style={{ color: 'var(--text)' }}>{p.quantity ?? p.stock ?? 0}</span>
                <button onClick={() => handleUpdateStock(p.id, 10)}
                  className="w-8 h-8 rounded-lg font-bold text-sm transition-all text-emerald-500 hover:bg-emerald-50">+</button>
              </div>
              <div className="text-end shrink-0 hidden sm:block">
                <p className="text-xs font-bold" style={{ color: 'var(--text3)' }}>{p.section}</p>
                <p className="text-xs" style={{ color: 'var(--text3)' }}>{t(p.category?.toLowerCase()) || p.category}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
