import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { productApi, cartApi, analysisApi } from '../hooks/useApi'
import { useAuthStore } from '../store'
import { formatPrice } from '../utils/format'
import AllergenModal from '../components/cart/AllergenModal'
import BarcodeScanner from '../components/pos/BarcodeScanner'
import AIAnalysisModal from '../components/pos/AIAnalysisModal'
import {
  Search, ShoppingCart, Plus, Minus, X, Loader2,
  Package, ScanLine
} from 'lucide-react'

const CATEGORIES = ['Dairy', 'Bakery', 'Snacks', 'Beverages', 'Produce', 'Meat', 'Fish', 'Pantry']
const AI_BACKEND_URL = ''

export default function DashboardPage() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const user  = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.token)

  const [products,  setProducts]  = useState([])
  const [cartItems, setCartItems] = useState([])
  const [loading,   setLoading]   = useState(true)
  const [search,    setSearch]    = useState('')
  const [category,  setCategory]  = useState('')

  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false)
  const [barcodeProcessing,  setBarcodeProcessing]  = useState(false)
  const [lastBarcode,        setLastBarcode]         = useState(null)
  const [analysisModal,      setAnalysisModal]       = useState(null)
  const [modalData,          setModalData]           = useState(null)

  const fetchProducts = useCallback(async () => {
    try {
      const { data } = await productApi.list({ search, category: category || undefined, limit: 50 })
      setProducts(data)
    } catch { toast.error(isAr ? 'فشل تحميل المنتجات' : 'Failed to load products') }
  }, [search, category, isAr])

  const fetchCart = useCallback(async () => {
    try { const { data } = await cartApi.get(); setCartItems(data) } catch {}
  }, [])

  useEffect(() => {
    setLoading(true)
    const calls = token ? [fetchProducts(), fetchCart()] : [fetchProducts()]
    Promise.all(calls).finally(() => setLoading(false))
  }, [fetchProducts, fetchCart, token])

  const doAddToCart = async (product) => {
    try {
      await cartApi.add(product.id, 1); await fetchCart()
      toast.success(`${isAr ? (product.name_ar || product.name) : product.name} ✓`, { duration: 1800, icon: '🛒' })
    } catch (err) { toast.error(err.response?.data?.detail || (isAr ? 'فشل الإضافة' : 'Failed to add')) }
  }

  const handleRemoveItem = async (itemId) => {
    try { await cartApi.remove(itemId); setCartItems(p => p.filter(i => i.id !== itemId)) }
    catch { toast.error(isAr ? 'فشل الحذف' : 'Failed') }
  }

  const handleUpdateQty = async (item, delta) => {
    const q = item.quantity + delta
    if (q <= 0) { await handleRemoveItem(item.id); return }
    try {
      await cartApi.update(item.id, q)
      setCartItems(p => p.map(i => i.id === item.id ? { ...i, quantity: q } : i))
    } catch {}
  }

  const handleClearCart = async () => {
    try { await cartApi.clear(); setCartItems([]); toast.success(isAr ? 'تم إفراغ السلة' : 'Cart cleared') }
    catch {}
  }

  const handleAddProduct = async (product) => {
    try {
      const { data: result } = await analysisApi.check(product.id, user?.allergies)
      setModalData({ result, product, pendingAdd: product })
    } catch { await doAddToCart(product) }
  }

  const fetchAIAnalysis = async (product) => {
    try {
      const resp = await fetch(`${AI_BACKEND_URL}/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: product.name, user_allergies: user?.allergies || [], detailed_analysis: false }),
      })
      if (!resp.ok) return null
      const data = await resp.json()
      return data.analysis || null
    } catch { return null }
  }

  const handleBarcodeScan = async (barcode) => {
    if (barcodeProcessing || barcode === lastBarcode) return
    setLastBarcode(barcode); setBarcodeProcessing(true); setShowBarcodeScanner(false)
    try {
      let product = null
      try { const { data } = await productApi.byBarcode(barcode); product = data }
      catch { toast.error(`${isAr ? 'غير موجود' : 'Not found'}: ${barcode}`, { icon: '🔍' }); setBarcodeProcessing(false); setTimeout(() => setLastBarcode(null), 2000); return }
      let allergenResult = { is_safe: true, matched_allergens: [], suggestions: [] }
      try { const { data } = await analysisApi.check(product.id, user?.allergies); allergenResult = data } catch {}
      setAnalysisModal({ product, allergenResult, aiAnalysis: null, aiLoading: true })
      const aiAnalysis = await fetchAIAnalysis(product)
      setAnalysisModal(prev => prev ? { ...prev, aiAnalysis, aiLoading: false } : null)
    } catch {}
    finally { setBarcodeProcessing(false); setTimeout(() => setLastBarcode(null), 3000) }
  }

  const cartTotal = cartItems.reduce((s, i) => s + (i.product?.price || 0) * i.quantity, 0)
  const cartCount = cartItems.reduce((s, i) => s + i.quantity, 0)

  return (
    <div style={{ display: 'flex', gap: 20, height: 'calc(100vh - 56px)', overflow: 'hidden', padding: '0 0 0 0' }}>

      {/* Products panel */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ display: 'flex', gap: 8, padding: '12px 0', flexShrink: 0 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search style={{ position: 'absolute', insetInlineStart: 11, top: '50%', transform: 'translateY(-50%)', width: 15, height: 15, color: 'var(--text3)' }} />
            <input className="input" style={{ paddingInlineStart: 34 }} placeholder={t('search')} value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <select className="input" style={{ width: 'auto' }} value={category} onChange={e => setCategory(e.target.value)}>
            <option value="">{t('allCategories')}</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={() => setShowBarcodeScanner(true)} disabled={barcodeProcessing}
            style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '0 14px', borderRadius: 10, border: 'none', background: 'var(--primary)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0, height: 40 }}>
            {barcodeProcessing ? <Loader2 style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} /> : <ScanLine style={{ width: 14, height: 14 }} />}
            {isAr ? 'مسح' : 'Scan'}
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 80 }}>
              <Loader2 style={{ width: 30, height: 30, color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
            </div>
          ) : products.length === 0 ? (
            <div style={{ textAlign: 'center', paddingTop: 60, color: 'var(--text3)' }}>
              <Package style={{ width: 44, height: 44, margin: '0 auto 10px', opacity: 0.18 }} />
              <p style={{ fontWeight: 600 }}>{isAr ? 'لا توجد منتجات' : 'No products'}</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))', gap: 12, paddingBottom: 16 }}>
              {products.map(p => <ProductCard key={p.id} product={p} onAdd={handleAddProduct} isAr={isAr} t={t} />)}
            </div>
          )}
        </div>
      </div>

      {/* Cart panel */}
      <div style={{ width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', paddingTop: 12 }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 18, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <h2 style={{ fontWeight: 800, fontSize: 14, display: 'flex', alignItems: 'center', gap: 7, margin: 0, color: 'var(--text)' }}>
              <ShoppingCart style={{ width: 16, height: 16, color: 'var(--primary)' }} />
              {t('myCart')}
              {cartCount > 0 && <span style={{ background: 'var(--primary)', color: '#fff', fontSize: 10, fontWeight: 800, padding: '1px 6px', borderRadius: 20 }}>{cartCount}</span>}
            </h2>
            {cartItems.length > 0 && (
              <button onClick={handleClearCart} style={{ fontSize: 11, color: '#ef4444', fontWeight: 700, background: 'none', border: 'none', cursor: 'pointer' }}>{t('clearCart')}</button>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 10px' }}>
            {cartItems.length === 0 ? (
              <div style={{ textAlign: 'center', paddingTop: 50, color: 'var(--text3)' }}>
                <Package style={{ width: 40, height: 40, margin: '0 auto 10px', opacity: 0.15 }} />
                <p style={{ fontSize: 12, fontWeight: 600 }}>{t('emptyCart')}</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                {cartItems.map(item => (
                  <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: 11, background: 'var(--surface2)' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {isAr ? (item.product?.name_ar || item.product?.name) : item.product?.name}
                      </p>
                      <p style={{ fontSize: 10, color: 'var(--text3)', margin: 0 }}>{formatPrice(item.product?.price || 0)}</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                      <button onClick={() => handleUpdateQty(item, -1)} style={{ width: 20, height: 20, borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Minus style={{ width: 9, height: 9 }} />
                      </button>
                      <span style={{ width: 20, textAlign: 'center', fontWeight: 800, fontSize: 12 }}>{item.quantity}</span>
                      <button onClick={() => handleUpdateQty(item, 1)} style={{ width: 20, height: 20, borderRadius: 5, border: '1px solid var(--border)', background: 'var(--surface)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Plus style={{ width: 9, height: 9 }} />
                      </button>
                    </div>
                    <button onClick={() => handleRemoveItem(item.id)} style={{ width: 22, height: 22, borderRadius: 5, border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)' }}>
                      <X style={{ width: 12, height: 12 }} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {cartItems.length > 0 && (
            <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)' }}>{t('total')}</span>
              <span style={{ fontSize: 19, fontWeight: 900, color: 'var(--primary)' }}>{formatPrice(cartTotal)}</span>
            </div>
          )}
        </div>
      </div>

      {showBarcodeScanner && <BarcodeScanner onScan={handleBarcodeScan} onClose={() => setShowBarcodeScanner(false)} />}
      {analysisModal && (
        <AIAnalysisModal product={analysisModal.product} allergenResult={analysisModal.allergenResult} aiAnalysis={analysisModal.aiAnalysis} aiLoading={analysisModal.aiLoading}
          onClose={() => setAnalysisModal(null)} onAddToCart={async (p) => { await doAddToCart(p); setAnalysisModal(null) }} onAddAlternative={async (a) => { await doAddToCart(a) }} />
      )}
      {modalData && (
        <AllergenModal result={modalData.result} product={modalData.product} onClose={() => setModalData(null)} onContinue={() => doAddToCart(modalData.pendingAdd)} />
      )}
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}

function ProductCard({ product, onAdd, isAr, t }) {
  const [adding, setAdding] = useState(false)
  const handleAdd = async () => { setAdding(true); await onAdd(product); setAdding(false) }
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 14, padding: 12, display: 'flex', flexDirection: 'column', gap: 7, transition: 'box-shadow 0.15s', cursor: 'default' }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.08)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 10, fontWeight: 700, background: 'var(--primary)', color: '#fff', padding: '2px 8px', borderRadius: 20 }}>{product.category}</span>
        {product.allergens?.length > 0 && <span style={{ fontSize: 10, background: '#fff7ed', color: '#c2410c', padding: '2px 6px', borderRadius: 20 }}>⚠️</span>}
      </div>
      <h3 style={{ fontWeight: 700, fontSize: 12, color: 'var(--text)', margin: 0, lineHeight: 1.3 }}>
        {isAr ? (product.name_ar || product.name) : product.name}
      </h3>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto' }}>
        <span style={{ fontSize: 16, fontWeight: 900, color: 'var(--primary)' }}>{formatPrice(product.price)}</span>
        <button onClick={handleAdd} disabled={adding}
          style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '5px 10px', borderRadius: 9, border: 'none', background: 'var(--primary)', color: '#fff', fontWeight: 700, fontSize: 11, cursor: 'pointer', opacity: adding ? 0.6 : 1 }}>
          {adding ? <Loader2 style={{ width: 11, height: 11, animation: 'spin 1s linear infinite' }} /> : <Plus style={{ width: 11, height: 11 }} />}
          {t('addToCart')}
        </button>
      </div>
    </div>
  )
}
