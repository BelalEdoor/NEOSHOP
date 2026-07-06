import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  X, MapPin, ShoppingCart, AlertTriangle, CheckCircle,
  Brain, Loader2, Sparkles, Package
} from 'lucide-react'
import { formatPrice } from '../../utils/format'

export default function AIAnalysisModal({
  product,
  allergenResult,
  aiAnalysis,
  aiLoading,
  onClose,
  onAddToCart,
  onAddAlternative,
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [adding, setAdding] = useState(false)

  const isSafe = allergenResult?.is_safe ?? true
  const matchedAllergens = allergenResult?.matched_allergens ?? []
  const suggestions = allergenResult?.suggestions ?? []

  const handleAddToCart = async () => {
    setAdding(true)
    await onAddToCart(product)
    setAdding(false)
  }

  const handleViewMap = () => {
    navigate('/map', { state: { highlight: product } })
    onClose()
  }

  const riskLevel = !isSafe ? 'high' : matchedAllergens.length > 0 ? 'medium' : 'low'
  const riskConfig = {
    high: { label: t('unsafeProduct'), color: '#dc2626', bg: '#fef2f2', border: '#fca5a5' },
    medium: { label: '⚠️ تحذير', color: '#d97706', bg: '#fffbeb', border: '#fcd34d' },
    low: { label: t('safeProduct'), color: '#16a34a', bg: '#f0fdf4', border: '#86efac' },
  }
  const risk = riskConfig[riskLevel]

  const tabs = [
    { id: 'overview', label: t('overview'), icon: Package },
    { id: 'analysis', label: t('aiAnalysis'), icon: Brain },
    ...(suggestions.length > 0 ? [{ id: 'alternatives', label: `${t('suggestions')} (${suggestions.length})`, icon: Sparkles }] : []),
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm">
      <div
        className="w-full sm:max-w-lg sm:rounded-3xl rounded-t-3xl overflow-hidden flex flex-col"
        style={{ background: 'var(--surface)', maxHeight: '92vh' }}
      >
        {/* Header */}
        <div className="px-5 pt-5 pb-4" style={{ background: risk.bg, borderBottom: `1px solid ${risk.border}` }}>
          <div className="w-10 h-1 rounded-full mx-auto mb-4 sm:hidden" style={{ background: 'var(--border)' }} />

          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold mb-2"
                style={{ background: risk.bg, color: risk.color, border: `1px solid ${risk.border}` }}>
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: risk.color }} />
                {risk.label}
              </div>
              <h2 className="font-extrabold text-lg leading-tight" style={{ color: 'var(--text)' }}>{product.name}</h2>
              {product.name_ar && <p className="text-sm mt-0.5" style={{ color: 'var(--text2)' }}>{product.name_ar}</p>}
            </div>
            <button onClick={onClose} className="p-2 rounded-xl hover:opacity-70 transition-opacity" style={{ color: 'var(--text3)' }}>
              <X className="w-5 h-5" />
            </button>
          </div>

          {matchedAllergens.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {matchedAllergens.map((a) => (
                <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">{a}</span>
              ))}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: '1px solid var(--border)' }}>
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className="flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-semibold transition-colors"
              style={{
                borderBottom: activeTab === id ? '2px solid var(--primary)' : '2px solid transparent',
                color: activeTab === id ? 'var(--primary)' : 'var(--text2)',
                background: 'var(--surface)',
              }}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-5">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {/* Safety */}
              <div className="p-4 rounded-2xl" style={{ background: risk.bg, border: `1px solid ${risk.border}` }}>
                <div className="flex items-center gap-2">
                  {isSafe
                    ? <CheckCircle className="w-5 h-5" style={{ color: '#16a34a' }} />
                    : <AlertTriangle className="w-5 h-5" style={{ color: '#dc2626' }} />
                  }
                  <span className="font-bold" style={{ color: risk.color }}>
                    {isSafe ? '✅ ' + t('safeProduct') : '⚠️ ' + t('unsafeProduct')}
                  </span>
                </div>
                {product.allergens?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {product.allergens.map((a) => (
                      <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">{a}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Product details */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm py-2" style={{ borderBottom: '1px solid var(--border)' }}>
                  <span style={{ color: 'var(--text2)' }}>الفئة</span>
                  <span className="font-semibold" style={{ color: 'var(--text)' }}>{product.category}</span>
                </div>
                {product.section && (
                  <div className="flex justify-between text-sm py-2" style={{ borderBottom: '1px solid var(--border)' }}>
                    <span style={{ color: 'var(--text2)' }}>{t('productLocation')}</span>
                    <span className="font-semibold" style={{ color: 'var(--primary)' }}>القسم {product.section}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm py-2">
                  <span style={{ color: 'var(--text2)' }}>السعر</span>
                  <span className="font-extrabold text-base" style={{ color: '#22c55e' }}>{formatPrice(product.price)}</span>
                </div>
              </div>

              {product.description && (
                <p className="text-sm" style={{ color: 'var(--text2)' }}>{product.description}</p>
              )}
            </div>
          )}

          {activeTab === 'analysis' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4" style={{ color: 'var(--primary)' }} />
                <h3 className="font-bold" style={{ color: 'var(--text)' }}>{t('aiAnalysis')}</h3>
                {aiLoading && <Loader2 className="w-4 h-4 animate-spin ms-auto" style={{ color: 'var(--primary)' }} />}
              </div>
              {aiLoading ? (
                <div className="space-y-2">
                  {[80, 60, 70, 50].map((w, i) => (
                    <div key={i} className="h-3 rounded-full animate-pulse" style={{ background: 'var(--surface2)', width: `${w}%` }} />
                  ))}
                </div>
              ) : aiAnalysis ? (
                <div className="text-sm leading-relaxed p-4 rounded-xl" style={{ background: 'var(--surface2)', color: 'var(--text2)' }}>
                  {typeof aiAnalysis === 'string' ? aiAnalysis : JSON.stringify(aiAnalysis, null, 2)}
                </div>
              ) : (
                <div className="text-center py-6">
                  <Sparkles className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text3)' }} />
                  <p className="text-sm" style={{ color: 'var(--text3)' }}>خدمة AI غير متاحة حالياً</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'alternatives' && (
            <div>
              <h3 className="font-bold mb-3" style={{ color: 'var(--text)' }}>
                <Sparkles className="w-4 h-4 inline me-1 text-amber-500" />
                {t('suggestions')}
              </h3>
              <div className="space-y-2">
                {suggestions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3 rounded-xl" style={{ background: 'var(--surface2)' }}>
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text)' }}>{s.name}</p>
                      {s.name_ar && <p className="text-xs" style={{ color: 'var(--text3)' }}>{s.name_ar}</p>}
                      <p className="text-xs font-semibold" style={{ color: '#22c55e' }}>{formatPrice(s.price)}</p>
                    </div>
                    <button
                      onClick={() => onAddAlternative(s)}
                      className="px-3 py-1.5 rounded-xl text-xs font-bold text-white"
                      style={{ background: 'var(--primary)' }}
                    >
                      {t('addToCartBtn')}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 flex gap-2" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
          {product.section && (
            <button onClick={handleViewMap} className="btn-secondary flex-1 flex items-center justify-center gap-2 text-sm">
              <MapPin className="w-4 h-4" />
              {t('viewOnMap')}
            </button>
          )}
          <button
            onClick={handleAddToCart}
            disabled={adding}
            className="btn-primary flex-1 flex items-center justify-center gap-2 text-sm"
          >
            {adding ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />}
            {t('addToCartBtn')}
          </button>
        </div>
      </div>
    </div>
  )
}
