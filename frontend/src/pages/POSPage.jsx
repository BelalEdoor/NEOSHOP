import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { productApi, sessionApi, analysisApi, createCartWebSocket } from '../hooks/useApi'
import { useAuthStore, useSessionStore, usePaymentStore } from '../store'
import { formatPrice } from '../utils/format'
import {
  Trash2, Plus, Minus, X, Loader2, Package,
  ScanLine, Zap, Tag, ReceiptText, PackageX,
  CheckCircle2, Printer, Search, Grid, ShoppingCart,
  CreditCard, Wifi, WifiOff
} from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Invoice Modal — تصميم محفوظ بدون تعديل
// ─────────────────────────────────────────────────────────────────────────────
function InvoiceModal({ invoice, onClose, isAr }) {
  return (
    <div style={OVERLAY}>
      <div style={{ borderRadius:24,boxShadow:'0 24px 80px rgba(0,0,0,0.35)',width:'100%',maxWidth:440,overflow:'hidden',background:'var(--surface)' }}>
        <div style={{ padding:'22px 26px',display:'flex',alignItems:'center',gap:14,background:'linear-gradient(135deg,#16a34a,#15803d)',color:'#fff' }}>
          <div style={{ width:48,height:48,borderRadius:16,background:'rgba(255,255,255,0.18)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
            <CheckCircle2 style={{ width:24,height:24 }} />
          </div>
          <div style={{ flex:1 }}>
            <p style={{ fontWeight:900,fontSize:17,margin:0 }}>{isAr ? 'تم إنشاء الفاتورة ✓' : 'Invoice Created ✓'}</p>
            <p style={{ fontSize:12,opacity:0.75,margin:'2px 0 0' }}>
              {isAr ? 'توجه إلى محطة الدفع لإتمام العملية' : 'Go to Payment Station to complete'}
            </p>
          </div>
          <span style={{ fontFamily:'monospace',fontSize:12,fontWeight:800,background:'rgba(255,255,255,0.2)',padding:'5px 12px',borderRadius:20,letterSpacing:'0.04em' }}>
            {invoice.invoice_code || `#${invoice.id}`}
          </span>
        </div>
        <div style={{ padding:'16px 24px',maxHeight:220,overflowY:'auto' }}>
          {(invoice.items || []).map((item,i) => (
            <div key={i} style={{ display:'flex',alignItems:'center',justifyContent:'space-between',padding:'7px 0',borderBottom:'1px solid var(--border)',fontSize:13 }}>
              <span style={{ color:'var(--text)',fontWeight:600,flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',paddingInlineEnd:12 }}>
                {isAr ? (item.product?.name_ar||item.product?.name||item.product_name) : (item.product?.name||item.product_name)}
              </span>
              <div style={{ display:'flex',gap:14,flexShrink:0 }}>
                <span style={{ color:'var(--text3)',fontSize:12 }}>×{item.quantity}</span>
                <span style={{ fontWeight:800,color:'#16a34a',minWidth:56,textAlign:'end' }}>
                  {formatPrice((item.unit_price||item.product?.price||0)*item.quantity)}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div style={{ padding:'12px 24px',display:'flex',alignItems:'center',justifyContent:'space-between',background:'var(--surface2)',borderTop:'1px solid var(--border)' }}>
          <span style={{ fontWeight:700,color:'var(--text2)',fontSize:14 }}>{isAr ? 'المجموع الكلي' : 'Total'}</span>
          <span style={{ fontSize:28,fontWeight:900,color:'#16a34a' }}>{formatPrice(invoice.total_amount||invoice.total||0)}</span>
        </div>
        <div style={{ padding:'14px 24px',background:'#fffbeb',borderTop:'1px solid #fde68a' }}>
          <p style={{ margin:0,fontSize:13,fontWeight:700,color:'#92400e',textAlign:'center' }}>
            {isAr ? '📍 توجه إلى محطة الدفع وامسح بطاقة RFID الخاصة بعربتك' : '📍 Go to Payment Station and scan your cart RFID card'}
          </p>
        </div>
        <div style={{ display:'flex',gap:10,padding:'14px 24px' }}>
          <button onClick={onClose} style={BTN_GHOST}>{isAr ? 'إغلاق' : 'Close'}</button>
          <button onClick={() => { window.print(); onClose() }} style={{ ...BTN_PRIMARY,background:'#16a34a',display:'flex',alignItems:'center',justifyContent:'center',gap:6 }}>
            <Printer style={{ width:15,height:15 }} />{isAr ? 'طباعة' : 'Print'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Recommendation Modal — shows allergen/health warnings + safe substitute
// ─────────────────────────────────────────────────────────────────────────────
function RecommendationModal({ result, scannedName, onClose, onAddSubstitute, onRemoveOriginal, isAr }) {
  if (!result) return null
  const isWarning = !result.is_safe
  return (
    <div style={OVERLAY}>
      <div style={{ borderRadius:24,boxShadow:'0 24px 80px rgba(0,0,0,0.35)',width:'100%',maxWidth:440,overflow:'hidden',background:'var(--surface)' }}>
        <div style={{ padding:'20px 24px',background: isWarning ? '#fff7ed' : '#f0fdf4', borderBottom:'1px solid var(--border)' }}>
          <div style={{ fontSize:28, marginBottom:6 }}>{isWarning ? '⚠️' : '✅'}</div>
          <div style={{ fontWeight:800, fontSize:17, color:'var(--text)' }}>
            {scannedName}
          </div>
          {isWarning ? (
            <div style={{ marginTop:6, fontSize:14, color:'#c2410c', fontWeight:600 }}>
              {result.warning_message || (isAr ? 'قد لا يكون هذا المنتج مناسباً لك' : 'This product may not be suitable for you')}
            </div>
          ) : (
            <div style={{ marginTop:6, fontSize:14, color:'#15803d', fontWeight:600 }}>
              {isAr ? 'هذا المنتج مناسب لك' : 'This product looks suitable for you'}
            </div>
          )}
        </div>

        {isWarning && result.suggestions?.length > 0 && (
          <div style={{ padding:'16px 24px' }}>
            <div style={{ fontSize:13, fontWeight:700, color:'var(--text2)', marginBottom:10 }}>
              {isAr ? 'بدائل أكثر أماناً:' : 'Safer alternatives:'}
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {result.suggestions.map(p => (
                <button key={p.id}
                  onClick={() => onAddSubstitute(p)}
                  style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
                    padding:'10px 14px', borderRadius:12, border:'1px solid var(--border)',
                    background:'var(--surface2)', cursor:'pointer', textAlign:'start' }}>
                  <span style={{ fontWeight:600, fontSize:14, color:'var(--text)' }}>
                    {isAr ? (p.name_ar || p.name) : p.name}
                  </span>
                  <span style={{ fontSize:13, color:'var(--text3)' }}>
                    {formatPrice(p.price)} {p.section ? `· ${p.section}` : ''}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ display:'flex', gap:10, padding:'16px 24px' }}>
          {isWarning && onRemoveOriginal && (
            <button onClick={onRemoveOriginal} style={{ ...BTN_GHOST, color:'#dc2626', borderColor:'#fca5a5' }}>
              {isAr ? 'عدم الإضافة' : "Don't add it"}
            </button>
          )}
          <button onClick={onClose} style={BTN_GHOST}>
            {isWarning ? (isAr ? 'إضافة على أي حال' : 'Add anyway') : (isAr ? 'حسناً' : 'OK')}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Payment Status Modal — جديد للهيكلية الموزّعة
// ─────────────────────────────────────────────────────────────────────────────
function PaymentStatusModal({ session, onClose, isAr }) {
  const paymentData = usePaymentStore(s => s)
  const remaining = Math.max(0, (paymentData.totalDue || 0) - (paymentData.amountInserted || 0))

  return (
    <div style={OVERLAY}>
      <div style={{ borderRadius:24,boxShadow:'0 24px 80px rgba(0,0,0,0.35)',width:'100%',maxWidth:420,overflow:'hidden',background:'var(--surface)' }}>
        <div style={{ padding:'22px 26px',background:'linear-gradient(135deg,#4f46e5,#7c3aed)',color:'#fff' }}>
          <div style={{ display:'flex',alignItems:'center',gap:12 }}>
            <CreditCard style={{ width:28,height:28 }} />
            <div>
              <p style={{ fontWeight:900,fontSize:17,margin:0 }}>{isAr ? 'جلسة الدفع' : 'Payment Session'}</p>
              <p style={{ fontSize:12,opacity:0.75,margin:'2px 0 0' }}>
                {isAr ? 'في انتظار الدفع عند المحطة' : 'Waiting at payment station'}
              </p>
            </div>
          </div>
        </div>
        <div style={{ padding:'24px' }}>
          <div style={{ display:'flex',justifyContent:'space-between',marginBottom:16 }}>
            <span style={{ color:'var(--text3)',fontWeight:600 }}>{isAr ? 'المجموع' : 'Total'}</span>
            <span style={{ fontWeight:900,fontSize:24,color:'var(--primary)' }}>{formatPrice(paymentData.totalDue||0)}</span>
          </div>
          {paymentData.amountInserted > 0 && (
            <>
              <div style={{ display:'flex',justifyContent:'space-between',marginBottom:8 }}>
                <span style={{ color:'var(--text3)',fontSize:13 }}>{isAr ? 'المُدفوع' : 'Inserted'}</span>
                <span style={{ fontWeight:700,color:'#16a34a' }}>{formatPrice(paymentData.amountInserted)}</span>
              </div>
              <div style={{ display:'flex',justifyContent:'space-between',marginBottom:16 }}>
                <span style={{ color:'var(--text3)',fontSize:13 }}>{isAr ? 'المتبقي' : 'Remaining'}</span>
                <span style={{ fontWeight:700,color:remaining>0?'#dc2626':'#16a34a' }}>{formatPrice(remaining)}</span>
              </div>
            </>
          )}
          {paymentData.paymentStatus === 'COMPLETED' && (
            <div style={{ background:'#f0fdf4',border:'1px solid #86efac',borderRadius:12,padding:'14px',textAlign:'center' }}>
              <CheckCircle2 style={{ width:32,height:32,color:'#16a34a',margin:'0 auto 8px' }} />
              <p style={{ fontWeight:800,color:'#15803d',margin:0 }}>
                {isAr ? '✓ تم الدفع بنجاح!' : '✓ Payment Completed!'}
              </p>
              {paymentData.changeReturned > 0 && (
                <p style={{ fontSize:13,color:'#166534',margin:'6px 0 0' }}>
                  {isAr ? `الباقي: ${formatPrice(paymentData.changeReturned)}` : `Change: ${formatPrice(paymentData.changeReturned)}`}
                </p>
              )}
            </div>
          )}
        </div>
        <div style={{ padding:'0 24px 20px' }}>
          <button onClick={onClose} style={{ ...BTN_PRIMARY,width:'100%' }}>{isAr ? 'حسناً' : 'OK'}</button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Not Found Modal — تصميم محفوظ
// ─────────────────────────────────────────────────────────────────────────────
function NotFoundModal({ modal, form, setForm, onCancel, onConfirm, isAr }) {
  return (
    <div style={OVERLAY}>
      <div style={{ borderRadius:24,boxShadow:'0 24px 80px rgba(0,0,0,0.35)',width:'100%',maxWidth:400,overflow:'hidden',background:'var(--surface)' }}>
        <div style={{ padding:'28px 24px 16px',textAlign:'center' }}>
          <div style={{ width:68,height:68,borderRadius:20,background:'#fef2f2',border:'2px solid #fca5a5',display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 14px' }}>
            <PackageX style={{ width:32,height:32,color:'#dc2626' }} />
          </div>
          <h3 style={{ fontSize:19,fontWeight:900,color:'var(--text)',margin:'0 0 6px' }}>{isAr ? 'المنتج غير موجود' : 'Product Not Found'}</h3>
          <p style={{ fontSize:13,color:'var(--text3)',margin:0 }}>
            {isAr ? 'الباركود: ' : 'Barcode: '}
            <span style={{ fontFamily:'monospace',fontWeight:800,color:'var(--primary)',letterSpacing:'0.06em' }}>{modal.barcode}</span>
          </p>
        </div>
        <div style={{ padding:'0 24px 16px',display:'flex',flexDirection:'column',gap:12 }}>
          <input
            placeholder={isAr ? 'اسم المنتج' : 'Product name'}
            value={form.name}
            onChange={e => setForm(f => ({...f, name: e.target.value}))}
            style={{ padding:'10px 14px',borderRadius:10,border:'1px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:13,outline:'none',width:'100%',boxSizing:'border-box' }}
          />
          <input
            placeholder={isAr ? 'السعر' : 'Price'}
            value={form.price}
            onChange={e => setForm(f => ({...f, price: e.target.value}))}
            type="number"
            style={{ padding:'10px 14px',borderRadius:10,border:'1px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:13,outline:'none',width:'100%',boxSizing:'border-box' }}
          />
        </div>
        <div style={{ display:'flex',gap:10,padding:'8px 24px 20px' }}>
          <button onClick={onCancel} style={BTN_GHOST}>{isAr ? 'إلغاء' : 'Cancel'}</button>
          <button onClick={onConfirm} disabled={!form.name.trim()} style={{ ...BTN_PRIMARY, opacity: form.name.trim() ? 1 : 0.45 }}>
            {isAr ? 'إضافة' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Product Search Modal — تصميم محفوظ
// ─────────────────────────────────────────────────────────────────────────────
function ProductSearchModal({ isAr, onClose, onAdd }) {
  const [query,   setQuery]   = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [isAdding, setIsAdding] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 80) }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await productApi.list(query ? { search: query } : {})
      setResults(data || [])
    } catch {} finally { setLoading(false) }
  }, [query])

  useEffect(() => { load() }, [load])

  const handleAdd = async (product) => {
    setIsAdding(true)
    try { await onAdd(product); onClose() }
    catch {} finally { setIsAdding(false) }
  }

  return (
    <div style={OVERLAY}>
      <div style={{ borderRadius:24,boxShadow:'0 24px 80px rgba(0,0,0,0.35)',width:'100%',maxWidth:480,maxHeight:'80vh',overflow:'hidden',display:'flex',flexDirection:'column',background:'var(--surface)' }}>
        <div style={{ padding:'16px 20px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:12,flexShrink:0 }}>
          <Search style={{ width:18,height:18,color:'var(--text3)' }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={isAr ? 'ابحث عن منتج…' : 'Search products…'}
            style={{ flex:1,border:'none',background:'transparent',color:'var(--text)',fontSize:15,fontWeight:600,outline:'none' }}
          />
          <button onClick={onClose} style={{ width:32,height:32,borderRadius:8,border:'none',background:'var(--surface2)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text3)' }}>
            <X style={{ width:16,height:16 }} />
          </button>
        </div>
        <div style={{ flex:1,overflowY:'auto',padding:'8px 0' }}>
          {loading ? (
            <div style={{ display:'flex',justifyContent:'center',paddingTop:40 }}>
              <Loader2 style={{ width:24,height:24,color:'var(--primary)',animation:'spin 1s linear infinite' }} />
            </div>
          ) : results.length === 0 ? (
            <div style={{ textAlign:'center',padding:'40px 20px',color:'var(--text3)' }}>
              <Package style={{ width:40,height:40,opacity:0.3,margin:'0 auto 10px' }} />
              <p style={{ fontWeight:700,fontSize:15 }}>{isAr ? 'لا نتائج' : 'No results'}</p>
            </div>
          ) : results.map(product => (
            <button key={product.id} onClick={() => handleAdd(product)} disabled={isAdding}
              style={{ width:'100%',display:'flex',alignItems:'center',gap:12,padding:'12px 20px',border:'none',background:'transparent',cursor:'pointer',textAlign:'start',transition:'background 0.1s' }}
              onMouseEnter={e => e.currentTarget.style.background='var(--surface2)'}
              onMouseLeave={e => e.currentTarget.style.background='transparent'}>
              <div style={{ width:40,height:40,borderRadius:10,background:'var(--surface2)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
                <Package style={{ width:18,height:18,color:'var(--text3)' }} />
              </div>
              <div style={{ flex:1,minWidth:0 }}>
                <p style={{ fontWeight:700,fontSize:14,color:'var(--text)',margin:0,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis' }}>
                  {isAr ? (product.name_ar||product.name) : product.name}
                </p>
                <p style={{ fontSize:11,color:'var(--text3)',margin:'2px 0 0' }}>{product.category}</p>
              </div>
              <span style={{ fontWeight:800,fontSize:14,color:'var(--primary)',flexShrink:0 }}>{formatPrice(product.price)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

const OVERLAY    = { position:'fixed',inset:0,background:'rgba(0,0,0,0.55)',display:'flex',alignItems:'center',justifyContent:'center',padding:20,zIndex:1000 }
const BTN_GHOST  = { flex:1,padding:'11px 0',borderRadius:12,fontWeight:700,fontSize:13,cursor:'pointer',background:'var(--surface2)',color:'var(--text2)',border:'1px solid var(--border)' }
const BTN_PRIMARY= { flex:1,padding:'11px 0',borderRadius:12,fontWeight:800,fontSize:13,cursor:'pointer',background:'var(--primary)',color:'#fff',border:'none' }

// ─────────────────────────────────────────────────────────────────────────────
// Main POS Page
// ─────────────────────────────────────────────────────────────────────────────
export default function POSPage() {
  const { i18n }  = useTranslation()
  const isAr      = i18n.language === 'ar'
  const user      = useAuthStore(s => s.user)
  const token     = useAuthStore(s => s.token)
  const navigate  = useNavigate()

  // ─── Session State ─────────────────────────────────────────────────────────
  const { session, sessionId, cartStatus, setSession, updateStatus, updateTotal, clearSession } = useSessionStore()
  const { setPaymentData, updatePayment, clearPayment } = usePaymentStore()

  const [cartItems,     setCartItems]     = useState([])
  const [cartLoading,   setCartLoading]   = useState(true)
  const [barcodeVal,    setBarcodeVal]    = useState('')
  const [processing,    setProcessing]    = useState(false)
  const [notFoundModal, setNotFoundModal] = useState(null)
  const [notFoundForm,  setNotFoundForm]  = useState({ name:'', price:'' })
  const [recoModal, setRecoModal] = useState(null) // { result, scannedName } | null
  const [savedInvoice,  setSavedInvoice]  = useState(null)
  const [saving,        setSaving]        = useState(false)
  const [showSearch,    setShowSearch]    = useState(false)
  const [showPayment,   setShowPayment]   = useState(false)
  const [wsConnected,   setWsConnected]   = useState(false)

  const barcodeRef = useRef(null)
  const wsRef      = useRef(null)

  // ── Auto-focus barcode input ───────────────────────────────────────────────
  useEffect(() => { barcodeRef.current?.focus() }, [])
  useEffect(() => {
    if (!showSearch && !notFoundModal && !savedInvoice && !showPayment) {
      const t = setTimeout(() => barcodeRef.current?.focus(), 120)
      return () => clearTimeout(t)
    }
  }, [showSearch, notFoundModal, savedInvoice, showPayment])
  useEffect(() => {
    const onKey = (e) => {
      const tag = document.activeElement?.tagName
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
      if (!isInput && !showSearch && !notFoundModal && !savedInvoice && !showPayment) {
        if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
          barcodeRef.current?.focus()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [showSearch, notFoundModal, savedInvoice, showPayment])

  // ── Init Session ───────────────────────────────────────────────────────────
  const initSession = useCallback(async () => {
    if (!token) { setCartLoading(false); return }

    // RFID العربة مخزّن في .env على الراسبيري باي
    const cartRfid = import.meta.env.VITE_CART_RFID || null

    try {
      let activeSession = null
      try {
        const { data } = await sessionApi.getActive()
        activeSession = data
        // إذا الجلسة موجودة بس ما عندها cart_rfid — أضفه
        if (activeSession && !activeSession.cart_rfid && cartRfid) {
          const { data: updated } = await sessionApi.start(cartRfid)
          activeSession = updated
        }
      } catch {}

      if (!activeSession) {
        const { data } = await sessionApi.start(cartRfid)
        activeSession = data
      }

      setSession(activeSession)
      setCartItems(activeSession.items || [])
    } catch (err) {
      console.error('Session init failed:', err)
      toast.error(isAr ? 'تعذّر بدء الجلسة' : 'Could not start session')
    } finally {
      setCartLoading(false)
    }
  }, [token, setSession, isAr])

  useEffect(() => { initSession() }, [initSession])

  // ── WebSocket — استقبال تحديثات real-time من Backend ──────────────────────
  useEffect(() => {
    if (!sessionId) return
    const ws = createCartWebSocket(sessionId)
    wsRef.current = ws

    ws.onopen = () => {
      setWsConnected(true)
      ws.send(JSON.stringify({ type: 'ping' }))
    }
    ws.onclose = () => setWsConnected(false)
    ws.onerror = () => setWsConnected(false)

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data)
        switch (msg.type) {
          case 'cart_update':
            // تحديث مباشر للمجموع
            if (msg.data?.total_amount !== undefined) {
              updateTotal(msg.data.total_amount)
            }
            break
          case 'session_finished':
            updateStatus('PENDING_PAYMENT')
            break
          case 'payment_started':
            updateStatus('PAYMENT_IN_PROGRESS')
            setShowPayment(true)
            break
          case 'payment_update':
            updatePayment({
              amount_inserted: msg.data?.amount_inserted,
              status: 'IN_PROGRESS',
            })
            break
          case 'payment_complete':
            updateStatus('PAID')
            updatePayment({
              amount_inserted: msg.data?.amount_inserted,
              change_returned: msg.data?.change_returned,
              status: 'COMPLETED',
            })
            toast.success(isAr ? '✅ تم الدفع بنجاح!' : '✅ Payment completed!')
            break
          case 'theft_alert':
            toast.error(
              isAr
                ? `⚠️ تنبيه أمني: ${msg.data?.description || 'نشاط مشبوه'}`
                : `⚠️ Security Alert: ${msg.data?.description || 'Suspicious activity'}`,
              { duration: 6000 }
            )
            break
          case 'cart_locked':
            if (msg.locked) {
              toast.error(isAr ? '🔒 تم قفل العربة' : '🔒 Cart locked', { duration: 5000 })
            }
            break
        }
      } catch {}
    }

    return () => { ws.close() }
  }, [sessionId, isAr])

  // ── Cart Operations ────────────────────────────────────────────────────────
  const doAddToCart = async (product) => {
    // منتج محلي (بدون ID في قاعدة البيانات)
    if (!product.id) {
      setCartItems(prev => {
        const ex = prev.find(i => i.product?.barcode === product.barcode)
        if (ex) return prev.map(i =>
          i.product?.barcode === product.barcode ? { ...i, quantity: i.quantity+1 } : i
        )
        return [...prev, { id:`local_${Date.now()}`, product_id:null, quantity:1, unit_price:product.price||0, product }]
      })
      toast.success(`✅ ${isAr ? (product.name_ar||product.name) : product.name}`, { duration:1200 })
      return
    }

    // إضافة عبر API الجلسة الجديد
    if (sessionId && product.barcode) {
      try {
        const { data: updatedItem } = await sessionApi.scanProduct(sessionId, product.barcode)
        // تحديث قائمة العناصر
        setCartItems(prev => {
          const ex = prev.find(i => i.product_id === product.id)
          if (ex) return prev.map(i => i.product_id === product.id ? updatedItem : i)
          return [...prev, updatedItem]
        })
        toast.success(`✅ ${isAr ? (product.name_ar||product.name) : product.name}`, { duration:1200 })
      } catch (err) {
        toast.error(err.response?.data?.detail || (isAr ? 'فشل الإضافة' : 'Failed to add'))
      }
    } else {
      // fallback: إضافة محلية
      setCartItems(prev => {
        const ex = prev.find(i => i.product_id === product.id)
        if (ex) return prev.map(i => i.product_id === product.id ? {...i, quantity:i.quantity+1} : i)
        return [...prev, { id:`local_${Date.now()}`, product_id:product.id, quantity:1, unit_price:product.price||0, product }]
      })
      toast.success(`✅ ${isAr ? (product.name_ar||product.name) : product.name}`, { duration:1200 })
    }
  }

  const handleBarcodeScan = async (barcode) => {
    const code = barcode.trim()
    if (!code || processing) return

    // منع المسح إذا الجلسة ليست ACTIVE
    if (cartStatus && cartStatus !== 'ACTIVE') {
      toast.error(isAr ? 'لا يمكن إضافة منتجات — الجلسة مغلقة' : 'Cannot add items — session is closed')
      return
    }

    setProcessing(true); setBarcodeVal('')
    try {
      if (sessionId) {
        // استخدام نقطة نهاية الجلسة مباشرةً (تتحقق من المخزون وتُحدّث قاعدة البيانات)
        const { data: updatedItem } = await sessionApi.scanProduct(sessionId, code)
        setCartItems(prev => {
          const ex = prev.find(i => i.product_id === updatedItem.product_id)
          if (ex) return prev.map(i => i.product_id === updatedItem.product_id ? updatedItem : i)
          return [...prev, updatedItem]
        })
        const name = isAr
          ? (updatedItem.product?.name_ar || updatedItem.product?.name)
          : updatedItem.product?.name
        toast.success(`✅ ${name}`, { duration:1200 })

        // Recommendation check -- only runs if the customer opted in
        // (decision: opt-in/out toggle, not forced on every scan) and the
        // backend itself also skips non-food categories automatically.
        if (user?.recommendations_enabled && updatedItem.product?.id) {
          analysisApi.check(updatedItem.product.id).then(({ data }) => {
            if (!data.is_safe) {
              // Keep the original cart item so choosing a substitute can
              // REPLACE it instead of adding alongside it (previously this
              // left both the unsafe item and the substitute in the cart).
              setRecoModal({ result: data, scannedName: name, originalItem: updatedItem })
            }
          }).catch(() => { /* silent -- never block the scan flow on a recommendation failure */ })
        }
      } else {
        // fallback إذا لا يوجد session
        const { data: product } = await productApi.byBarcode(code)
        await doAddToCart(product)
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setNotFoundModal({ barcode: code })
        setNotFoundForm({ name:'', price:'' })
      } else {
        toast.error(err.response?.data?.detail || (isAr ? 'خطأ' : 'Error'))
      }
    } finally { setProcessing(false) }
  }

  const handleRemoveItem = async (item) => {
    if (typeof item.id === 'string' && item.id.startsWith('local_')) {
      setCartItems(p => p.filter(i => i.id !== item.id)); return
    }
    if (sessionId && item.product_id) {
      try {
        await sessionApi.removeProduct(sessionId, item.product_id)
        setCartItems(p => p.filter(i => i.id !== item.id))
      } catch { toast.error(isAr ? 'فشل الحذف' : 'Failed') }
    } else {
      setCartItems(p => p.filter(i => i.id !== item.id))
    }
  }

  const handleUpdateQty = async (item, delta) => {
    const q = item.quantity + delta
    if (q <= 0) { await handleRemoveItem(item); return }
    // تحديث محلي فقط (سيُحدَّث في قاعدة البيانات عند المسح)
    setCartItems(p => p.map(i => i.id === item.id ? { ...i, quantity:q } : i))
  }

  const handleClearCart = async () => {
    setCartItems([])
    if (sessionId) {
      // بدء جلسة جديدة — يجب تمرير cart_rfid دائماً
      try {
        const cartRfid = import.meta.env.VITE_CART_RFID || null
        const { data } = await sessionApi.start(cartRfid)
        setSession(data)
        clearPayment()
      } catch {}
    }
    toast.success(isAr ? 'تم إفراغ السلة' : 'Cart cleared')
  }

  const handleFinishShopping = async () => {
    if (cartItems.length === 0) return
    if (!sessionId) {
      toast.error(isAr ? 'لا توجد جلسة نشطة' : 'No active session')
      return
    }
    setSaving(true)
    try {
      // إنهاء التسوق → Backend ينشئ الفاتورة ويرسلها عبر MQTT
      const { data: invoice } = await sessionApi.finish(sessionId)
      updateStatus('PENDING_PAYMENT')
      setPaymentData({
        total_amount: invoice.total_amount,
        invoice_code: invoice.invoice_code,
      })
      // بناء قائمة العناصر للعرض في الـ Modal
      const displayInvoice = {
        ...invoice,
        items: cartItems,
      }
      setSavedInvoice(displayInvoice)
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'فشل إنهاء التسوق' : 'Failed to finish'))
    } finally { setSaving(false) }
  }

  const cartTotal = cartItems.reduce((s, i) => s + (i.unit_price||i.product?.price||0)*i.quantity, 0)
  const cartCount = cartItems.reduce((s, i) => s + i.quantity, 0)
  const isSessionActive = !cartStatus || cartStatus === 'ACTIVE'
  const isPendingPayment = cartStatus === 'PENDING_PAYMENT' || cartStatus === 'PAYMENT_IN_PROGRESS'

  return (
    <div style={{ display:'grid', gridTemplateColumns:'1fr', gridTemplateRows:'1fr 72px', height:'calc(100vh - 56px)', overflow:'hidden', gap:0 }}>

      {/* ══ Invoice Panel ════════════════════════════════════════════════════ */}
      <div style={{ gridColumn:'1/2', gridRow:'1/2', display:'flex', flexDirection:'column', overflow:'hidden', background:'var(--surface)' }}>

        {/* Header bar */}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 16px', height:48, background:'var(--primary)', color:'#fff', flexShrink:0 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <ReceiptText style={{ width:17, height:17 }} />
            <span style={{ fontWeight:800, fontSize:14 }}>{isAr ? 'الفاتورة الحالية' : 'Current Invoice'}</span>
            {/* Session Status Badge */}
            {cartStatus && cartStatus !== 'ACTIVE' && (
              <span style={{ fontSize:10, fontWeight:800, background:'rgba(255,255,255,0.2)', padding:'3px 8px', borderRadius:10 }}>
                {cartStatus}
              </span>
            )}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:12, fontSize:12 }}>
            {/* WS Connection indicator */}
            <span title={wsConnected ? 'Connected' : 'Disconnected'}>
              {wsConnected
                ? <Wifi style={{ width:13, height:13, opacity:0.8 }} />
                : <WifiOff style={{ width:13, height:13, opacity:0.5 }} />
              }
            </span>
            <div style={{ display:'flex', alignItems:'center', gap:5, background:'rgba(255,255,255,0.15)', padding:'4px 10px', borderRadius:20 }}>
              <ShoppingCart style={{ width:13, height:13 }} />
              <span style={{ fontWeight:800 }}>{cartCount}</span>
              <span style={{ opacity:0.75 }}>{isAr ? 'صنف' : 'items'}</span>
            </div>
            {cartItems.length > 0 && isSessionActive && (
              <button onClick={handleClearCart} style={{ background:'rgba(255,255,255,0.18)', border:'1px solid rgba(255,255,255,0.3)', borderRadius:8, padding:'4px 12px', color:'#fff', fontSize:11, fontWeight:700, cursor:'pointer', display:'flex', alignItems:'center', gap:4 }}>
                <Trash2 style={{ width:11, height:11 }} />{isAr ? 'إفراغ' : 'Clear'}
              </button>
            )}
          </div>
        </div>

        {/* Table header */}
        <div style={{ display:'grid', gridTemplateColumns:'26px 1fr 90px 110px 80px 34px', gap:4, padding:'7px 14px', background:'var(--surface2)', borderBottom:'2px solid var(--border)', fontSize:10, fontWeight:800, color:'var(--text3)', textTransform:'uppercase', letterSpacing:'0.05em', flexShrink:0 }}>
          <span>#</span>
          <span>{isAr ? 'المنتج' : 'Product'}</span>
          <span style={{ textAlign:'center' }}>{isAr ? 'السعر' : 'Price'}</span>
          <span style={{ textAlign:'center' }}>{isAr ? 'الكمية' : 'Qty'}</span>
          <span style={{ textAlign:'end' }}>{isAr ? 'الإجمالي' : 'Total'}</span>
          <span />
        </div>

        {/* Cart rows */}
        <div style={{ flex:1, overflowY:'auto' }}>
          {cartLoading ? (
            <div style={{ display:'flex', justifyContent:'center', paddingTop:60 }}>
              <Loader2 style={{ width:26, height:26, color:'var(--primary)', animation:'spin 1s linear infinite' }} />
            </div>
          ) : cartItems.length === 0 ? (
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap:10, color:'var(--text3)', paddingBottom:30 }}>
              <div style={{ width:72, height:72, borderRadius:20, background:'var(--surface2)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                <Package style={{ width:36, height:36, opacity:0.25 }} />
              </div>
              <p style={{ fontSize:15, fontWeight:700, margin:0 }}>{isAr ? 'الفاتورة فارغة' : 'Invoice is empty'}</p>
              <p style={{ fontSize:12, margin:0, opacity:0.6 }}>{isAr ? 'امسح باركود أو ابحث عن منتج' : 'Scan a barcode or search'}</p>
            </div>
          ) : (
            cartItems.map((item, idx) => (
              <div key={item.id} style={{ display:'grid', gridTemplateColumns:'26px 1fr 90px 110px 80px 34px', gap:4, padding:'9px 14px', alignItems:'center', borderBottom:'1px solid var(--border)', background:idx%2===0?'var(--surface)':'rgba(0,0,0,0.015)', transition:'background 0.1s' }}
                onMouseEnter={e => e.currentTarget.style.background='var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background=idx%2===0?'var(--surface)':'rgba(0,0,0,0.015)'}>
                <span style={{ fontSize:10, fontWeight:700, color:'var(--text3)' }}>{idx+1}</span>
                <p style={{ fontWeight:600, fontSize:13, color:'var(--text)', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', margin:0 }}>
                  {isAr ? (item.product?.name_ar||item.product?.name) : item.product?.name}
                </p>
                <span style={{ textAlign:'center', fontSize:12, fontWeight:600, color:'var(--text3)' }}>
                  {formatPrice(item.unit_price||item.product?.price||0)}
                </span>
                <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:4 }}>
                  <button onClick={() => handleUpdateQty(item,-1)} disabled={!isSessionActive} style={{ width:24, height:24, borderRadius:6, border:'1px solid var(--border)', background:'var(--surface)', cursor:isSessionActive?'pointer':'not-allowed', display:'flex', alignItems:'center', justifyContent:'center', opacity:isSessionActive?1:0.4 }}>
                    <Minus style={{ width:10, height:10, color:'var(--text2)' }} />
                  </button>
                  <span style={{ width:26, textAlign:'center', fontWeight:800, fontSize:14, color:'var(--text)' }}>{item.quantity}</span>
                  <button onClick={() => handleUpdateQty(item,1)} disabled={!isSessionActive} style={{ width:24, height:24, borderRadius:6, border:'1px solid var(--border)', background:'var(--surface)', cursor:isSessionActive?'pointer':'not-allowed', display:'flex', alignItems:'center', justifyContent:'center', opacity:isSessionActive?1:0.4 }}>
                    <Plus style={{ width:10, height:10, color:'var(--text2)' }} />
                  </button>
                </div>
                <span style={{ textAlign:'end', fontWeight:800, fontSize:14, color:'var(--primary)' }}>
                  {formatPrice((item.unit_price||item.product?.price||0)*item.quantity)}
                </span>
                <button onClick={() => handleRemoveItem(item)} disabled={!isSessionActive}
                  style={{ width:28, height:28, borderRadius:8, border:'none', background:'transparent', cursor:isSessionActive?'pointer':'not-allowed', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text3)', transition:'color 0.1s', opacity:isSessionActive?1:0.4 }}
                  onMouseEnter={e => { if(isSessionActive) e.currentTarget.style.color='#dc2626' }}
                  onMouseLeave={e => e.currentTarget.style.color='var(--text3)'}>
                  <X style={{ width:15, height:15 }} />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Barcode input bar */}
        <div style={{ display:'flex', gap:8, padding:'10px 14px', background:'var(--surface)', borderTop:'2px solid var(--border)', flexShrink:0, alignItems:'center' }}>
          <div style={{ flex:1, position:'relative' }}>
            <div style={{ position:'absolute', insetInlineStart:12, top:'50%', transform:'translateY(-50%)', display:'flex', alignItems:'center', gap:6 }}>
              {processing
                ? <Loader2 style={{ width:17,height:17,color:'var(--primary)',animation:'spin 1s linear infinite' }} />
                : <ScanLine style={{ width:17,height:17,color:'var(--text3)' }} />
              }
            </div>
            <input
              ref={barcodeRef}
              type="text"
              value={barcodeVal}
              onChange={e => setBarcodeVal(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleBarcodeScan(barcodeVal)}
              onBlur={() => {
                if (!showSearch && !notFoundModal && !savedInvoice && !showPayment) {
                  setTimeout(() => barcodeRef.current?.focus(), 50)
                }
              }}
              disabled={processing || !isSessionActive}
              placeholder={
                !isSessionActive
                  ? (isAr ? 'الجلسة مغلقة' : 'Session closed')
                  : processing
                    ? (isAr ? 'جاري البحث…' : 'Searching…')
                    : (isAr ? 'جاهز لمسح الباركود…' : 'Ready to scan barcode…')
              }
              dir="ltr"
              autoComplete="off"
              style={{
                width:'100%', padding:'11px 12px 11px 42px',
                borderRadius:12,
                border:`2px solid ${processing?'var(--primary)':'var(--border)'}`,
                background: !isSessionActive?'var(--surface2)':processing?'rgba(79,70,229,0.04)':'var(--surface)',
                color:'var(--text)',
                fontFamily:"'JetBrains Mono',monospace",
                fontWeight:700, fontSize:16, letterSpacing:'0.08em',
                outline:'none', transition:'all 0.15s', boxSizing:'border-box',
                opacity: !isSessionActive ? 0.6 : 1,
              }}
            />
          </div>
          <button
            onClick={() => setShowSearch(true)}
            disabled={!isSessionActive}
            style={{ display:'flex', alignItems:'center', gap:6, padding:'11px 16px', borderRadius:12, border:'2px solid var(--border)', background:'var(--surface2)', color:'var(--text)', fontWeight:700, fontSize:13, cursor:isSessionActive?'pointer':'not-allowed', whiteSpace:'nowrap', flexShrink:0, opacity:isSessionActive?1:0.5 }}>
            <Search style={{ width:15, height:15 }} />
            {isAr ? 'بحث' : 'Search'}
          </button>
          <button
            onClick={() => handleBarcodeScan(barcodeVal)}
            disabled={!barcodeVal.trim() || processing || !isSessionActive}
            style={{ padding:'11px 20px', borderRadius:12, border:'none', background:'var(--primary)', color:'#fff', fontWeight:800, fontSize:13, cursor:'pointer', opacity:!barcodeVal.trim()||processing||!isSessionActive?0.45:1, whiteSpace:'nowrap', flexShrink:0 }}>
            {isAr ? 'إضافة ↵' : 'Add ↵'}
          </button>
        </div>
      </div>

      {/* ══ BOTTOM BAR ═══════════════════════════════════════════════════════ */}
      <div style={{ gridColumn:'1/2', gridRow:'2/3', display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 18px', background:'var(--surface)', borderTop:'2px solid var(--border)', gap:14 }}>
        <div style={{ display:'flex', alignItems:'baseline', gap:8 }}>
          <span style={{ fontSize:12, color:'var(--text3)', fontWeight:600 }}>{isAr ? 'الإجمالي' : 'Total'}</span>
          <span style={{ fontSize:30, fontWeight:900, color:'#16a34a', lineHeight:1 }}>{formatPrice(cartTotal)}</span>
        </div>
        <div style={{ flex:1 }} />

        {/* Offers */}
        <button onClick={() => navigate('/offers')}
          style={{ display:'flex', alignItems:'center', gap:7, padding:'10px 20px', borderRadius:11, border:'none', background:'#f59e0b', color:'#fff', fontWeight:800, fontSize:13, cursor:'pointer', transition:'all 0.15s', boxShadow:'0 3px 12px rgba(245,158,11,0.3)' }}
          onMouseEnter={e => { e.currentTarget.style.background='#d97706'; e.currentTarget.style.transform='translateY(-1px)' }}
          onMouseLeave={e => { e.currentTarget.style.background='#f59e0b'; e.currentTarget.style.transform='translateY(0)' }}>
          <Tag style={{ width:16, height:16 }} />
          {isAr ? 'العروضات' : 'Offers'}
        </button>

        {/* Pending Payment indicator */}
        {isPendingPayment && (
          <button onClick={() => setShowPayment(true)}
            style={{ display:'flex', alignItems:'center', gap:8, padding:'10px 20px', borderRadius:11, border:'2px solid #4f46e5', background:'#eef2ff', color:'#4f46e5', fontWeight:800, fontSize:13, cursor:'pointer', animation:'pulse 2s infinite' }}>
            <CreditCard style={{ width:16, height:16 }} />
            {isAr ? 'متابعة الدفع' : 'Payment Status'}
          </button>
        )}

        {/* Complete purchase / Finish Shopping */}
        {isSessionActive && (
          <button onClick={handleFinishShopping} disabled={cartItems.length===0||saving}
            style={{ display:'flex', alignItems:'center', gap:8, padding:'10px 28px', borderRadius:11, border:'none', background:cartItems.length===0?'var(--text3)':'#16a34a', color:'#fff', fontWeight:800, fontSize:14, cursor:cartItems.length===0?'not-allowed':'pointer', opacity:cartItems.length===0?0.45:1, transition:'all 0.15s', boxShadow:cartItems.length>0?'0 4px 16px rgba(22,163,74,0.35)':'none', minWidth:190 }}
            onMouseEnter={e => { if(cartItems.length>0){ e.currentTarget.style.background='#15803d'; e.currentTarget.style.transform='translateY(-1px)' } }}
            onMouseLeave={e => { e.currentTarget.style.background=cartItems.length===0?'var(--text3)':'#16a34a'; e.currentTarget.style.transform='translateY(0)' }}>
            {saving ? <Loader2 style={{ width:17,height:17,animation:'spin 1s linear infinite' }} /> : <Zap style={{ width:17,height:17 }} />}
            {isAr ? 'إنهاء التسوق' : 'Finish Shopping'}
          </button>
        )}
      </div>

      {/* ══ MODALS ═══════════════════════════════════════════════════════════ */}
      {showSearch && (
        <ProductSearchModal
          isAr={isAr}
          onClose={() => setShowSearch(false)}
          onAdd={async (p) => { await doAddToCart(p) }}
        />
      )}
      {notFoundModal && (
        <NotFoundModal
          modal={notFoundModal} form={notFoundForm} setForm={setNotFoundForm} isAr={isAr}
          onCancel={() => setNotFoundModal(null)}
          onConfirm={() => {
            const cp = { id:null, name:notFoundForm.name.trim(), name_ar:notFoundForm.name.trim(), barcode:notFoundModal.barcode, price:parseFloat(notFoundForm.price)||0 }
            doAddToCart(cp)
            setNotFoundModal(null)
          }}
        />
      )}
      {savedInvoice && (
        <InvoiceModal invoice={savedInvoice} isAr={isAr} onClose={() => setSavedInvoice(null)} />
      )}
      {recoModal && (
        <RecommendationModal
          result={recoModal.result}
          scannedName={recoModal.scannedName}
          isAr={isAr}
          onClose={() => setRecoModal(null)}
          onRemoveOriginal={async () => {
            const original = recoModal.originalItem
            setRecoModal(null)
            if (original) {
              await handleRemoveItem(original)
              toast.success(isAr ? 'تم عدم إضافة المنتج' : 'Item not added', { duration:1500 })
            }
          }}
          onAddSubstitute={async (product) => {
            const original = recoModal.originalItem
            setRecoModal(null)
            // Remove the unsafe item first -- previously this step was
            // missing, so choosing a substitute added it ALONGSIDE the
            // unsafe item instead of replacing it.
            if (original) {
              await handleRemoveItem(original)
            }
            if (product.barcode) await handleBarcodeScan(product.barcode)
          }}
        />
      )}
      {showPayment && (
        <PaymentStatusModal session={session} isAr={isAr} onClose={() => setShowPayment(false)} />
      )}

      <style>{`
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.7} }
      `}</style>
    </div>
  )
}