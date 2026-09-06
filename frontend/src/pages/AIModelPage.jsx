import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store'
import { productApi, analysisApi } from '../hooks/useApi'
import toast from 'react-hot-toast'
import {
  Brain, ScanLine, Loader2, MapPin, ShoppingCart,
  AlertTriangle, CheckCircle, Package, Sparkles, Zap, Barcode
} from 'lucide-react'
import { cartApi } from '../hooks/useApi'
import { formatPrice } from '../utils/format'

export default function AIModelPage() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const barcodeRef = useRef(null)

  const [barcodeVal, setBarcodeVal] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  // result: { product, allergenResult, recEngine }

  useEffect(() => {
    if (barcodeRef.current) barcodeRef.current.focus()
  }, [])

  const handleScan = async (barcode) => {
    if (!barcode.trim() || loading) return
    setLoading(true)
    setBarcodeVal('')
    setResult(null)

    try {
      let product
      try {
        const { data } = await productApi.byBarcode(barcode.trim())
        product = data
      } catch {
        toast.error(`المنتج غير موجود: ${barcode}`, { icon: '🔍' })
        setLoading(false)
        if (barcodeRef.current) barcodeRef.current.focus()
        return
      }

      let allergenResult = { is_safe: true, matched_allergens: [], suggestions: [] }
      try {
        const { data } = await analysisApi.check(product.id, user?.allergies)
        allergenResult = data
      } catch {}

      // Show basic result immediately
      setResult({ product, allergenResult, recEngine: null, recEngineLoading: true })
      setLoading(false)

      // Fetch health score + similar-product recommendations from the
      // recommendation engine (routers/analysis.py::_recommendation_engine_extras)
      try {
        const { data } = await analysisApi.aiAnalysis(product.id)
        setResult((prev) => prev ? {
          ...prev,
          allergenResult: data.allergen_check || prev.allergenResult,
          recEngine: {
            productHealth: data.product_health,
            recommendations: data.recommendations || [],
            available: data.recommendations_available,
          },
          recEngineLoading: false,
        } : null)
      } catch {
        setResult((prev) => prev ? { ...prev, recEngineLoading: false } : null)
      }
    } catch {
      toast.error('حدث خطأ')
      setLoading(false)
    } finally {
      if (barcodeRef.current) barcodeRef.current.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleScan(barcodeVal)
  }

  const handleAddToCart = async (product) => {
    try {
      await cartApi.add(product.id, 1)
      toast.success(`${product.name} ✓`, { icon: '🛒' })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل الإضافة')
    }
  }

  const isResultSafe = Boolean(
    result?.allergenResult?.is_safe && result?.recEngine?.productHealth?.safe !== false
  )

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'var(--primary)' }}>
          <Brain className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="font-extrabold text-xl" style={{ color: 'var(--text)' }}>{t('aiModelTitle')}</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>{t('aiModelSubtitle')}</p>
        </div>
      </div>

      {/* Barcode Input */}
      <div className="card mb-6">
        <label className="flex items-center gap-2 text-sm font-bold mb-3" style={{ color: 'var(--text2)' }}>
          <Barcode className="w-4 h-4" style={{ color: 'var(--primary)' }} />
          {t('barcodeInput').split('…')[0]}
        </label>
        <div className="relative">
          <ScanLine className="absolute start-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: loading ? 'var(--primary)' : 'var(--text3)' }} />
          <input
            ref={barcodeRef}
            type="text"
            value={barcodeVal}
            onChange={(e) => setBarcodeVal(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            className="input ps-12 text-lg font-mono"
            placeholder={loading ? t('aiAnalyzing') : t('aiScanBarcode')}
            autoFocus
            autoComplete="off"
            dir="ltr"
            style={{ fontSize: '1.05rem', letterSpacing: '0.05em' }}
          />
          {loading && <Loader2 className="absolute end-4 top-1/2 -translate-y-1/2 w-5 h-5 animate-spin" style={{ color: 'var(--primary)' }} />}
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--text3)' }}>⌨️ اضغط Enter بعد إدخال الباركود</p>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Product Info */}
          <div className="card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-extrabold text-lg" style={{ color: 'var(--text)' }}>{result.product.name}</h2>
                {result.product.name_ar && (
                  <p className="text-sm" style={{ color: 'var(--text2)' }}>{result.product.name_ar}</p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs px-2 py-1 rounded-full font-semibold" style={{ background: 'var(--surface2)', color: 'var(--text2)' }}>
                    {result.product.category}
                  </span>
                  {result.product.section && (
                    <span className="text-xs px-2 py-1 rounded-full font-semibold" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                      <MapPin className="w-3 h-3 inline me-1" />
                      {result.product.section}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-2xl font-extrabold" style={{ color: '#22c55e' }}>{formatPrice(result.product.price)}</p>
            </div>

            {/* Safety Status */}
            <div className="mt-4 p-3 rounded-xl flex items-center gap-3"
              style={{
                background: isResultSafe ? '#dcfce7' : '#fef2f2',
                border: `1px solid ${isResultSafe ? '#86efac' : '#fca5a5'}`
              }}>
              {isResultSafe
                ? <CheckCircle className="w-5 h-5 flex-shrink-0" style={{ color: '#16a34a' }} />
                : <AlertTriangle className="w-5 h-5 flex-shrink-0" style={{ color: '#dc2626' }} />
              }
              <div>
                <p className="font-bold text-sm" style={{ color: isResultSafe ? '#15803d' : '#b91c1c' }}>
                  {isResultSafe ? '✅ ' + t('safeProduct') : '⚠️ ' + t('unsafeProduct')}
                </p>
                {result.allergenResult.matched_allergens?.length > 0 && (
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {result.allergenResult.matched_allergens.map((a) => (
                      <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">{a}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => navigate('/map', { state: { highlight: result.product } })}
                className="flex-1 py-2 rounded-xl font-bold text-sm flex items-center justify-center gap-2"
                style={{ background: 'var(--surface2)', color: 'var(--text)' }}
              >
                <MapPin className="w-4 h-4" />
                {t('viewOnMap')}
              </button>
              <button
                onClick={() => handleAddToCart(result.product)}
                className="flex-1 py-2 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2"
                style={{ background: 'var(--primary)' }}
              >
                <ShoppingCart className="w-4 h-4" />
                {t('addToCartBtn')}
              </button>
            </div>
          </div>

          {/* Alternatives */}
          {result.allergenResult.suggestions?.length > 0 && (
            <div className="card">
              <h3 className="font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--text)' }}>
                <Sparkles className="w-4 h-4 text-amber-500" />
                {t('suggestions')}
              </h3>
              <div className="space-y-2">
                {result.allergenResult.suggestions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3 rounded-xl" style={{ background: 'var(--surface2)' }}>
                    <div>
                      <p className="text-sm font-bold" style={{ color: 'var(--text)' }}>{s.name}</p>
                      <p className="text-xs" style={{ color: 'var(--text3)' }}>{formatPrice(s.price)}</p>
                    </div>
                    <button
                      onClick={() => handleAddToCart(s)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-white"
                      style={{ background: 'var(--primary)' }}
                    >
                      {t('addToCartBtn')}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ══ محرّك التوصيات — Health Score + منتجات مشابهة ══════════════ */}
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4" style={{ color: 'var(--primary)' }} />
              <h3 className="font-bold" style={{ color: 'var(--text)' }}>
                {t('recommendationEngine', 'محرّك التوصيات')}
              </h3>
              {result.recEngineLoading && <Loader2 className="w-4 h-4 animate-spin ms-auto" style={{ color: 'var(--primary)' }} />}
            </div>

            {result.recEngineLoading ? (
              <div className="space-y-2">
                <div className="h-3 rounded-full animate-pulse" style={{ background: 'var(--surface2)', width: '70%' }} />
                <div className="h-3 rounded-full animate-pulse" style={{ background: 'var(--surface2)', width: '50%' }} />
              </div>
            ) : result.recEngine?.productHealth ? (
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-2xl font-extrabold" style={{ color: 'var(--primary)' }}>
                      {result.recEngine.productHealth.health_score}
                      <span className="text-sm font-semibold" style={{ color: 'var(--text3)' }}>/100</span>
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text3)' }}>
                      {t('healthScore', 'الدرجة الصحية')}
                    </p>
                  </div>
                  <span
                    className="text-xs px-2 py-1 rounded-full font-semibold"
                    style={{ background: 'var(--surface2)', color: 'var(--text2)' }}
                  >
                    {result.recEngine.productHealth.risk_level}
                  </span>
                </div>

                {result.recEngine.productHealth.warnings?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {result.recEngine.productHealth.warnings.map((w, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold">
                        {w}
                      </span>
                    ))}
                  </div>
                )}

                {result.recEngine.recommendations?.length > 0 && (
                  <div>
                    <p className="text-xs font-bold mb-2" style={{ color: 'var(--text2)' }}>
                      {t('similarProducts', 'منتجات مشابهة موصى بها')}
                    </p>
                    <div className="space-y-2">
                      {result.recEngine.recommendations.map((r) => (
                        <div key={r.id} className="flex items-center justify-between p-2.5 rounded-xl" style={{ background: 'var(--surface2)' }}>
                          <div className="min-w-0">
                            <p className="text-sm font-bold truncate" style={{ color: 'var(--text)' }}>{r.name}</p>
                            <p className="text-xs" style={{ color: 'var(--text3)' }}>{r.category}</p>
                          </div>
                          <span className="text-xs font-bold px-2 py-1 rounded-full flex-shrink-0" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                            {r.match_percentage}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm" style={{ color: 'var(--text3)' }}>
                <Sparkles className="w-4 h-4 inline me-1" />
                {t('recommendationEngineUnavailable', 'محرّك التوصيات غير متاح حالياً (يحتاج فهرس بيانات مبني مسبقاً)')}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: 'var(--surface2)' }}>
            <Brain className="w-10 h-10" style={{ color: 'var(--text3)' }} />
          </div>
          <p className="font-bold text-lg" style={{ color: 'var(--text2)' }}>{t('aiScanBarcode')}</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text3)' }}>ستظهر نتائج التحليل هنا فور مسح الباركود</p>
        </div>
      )}
    </div>
  )
}