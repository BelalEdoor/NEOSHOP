import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../../hooks/useApi'
import toast from 'react-hot-toast'
import {
  ShoppingCart, Plus, Pencil, Trash2, X,
  Search, Wifi, WifiOff, RefreshCw, Save,
  CheckCircle2, AlertTriangle, Loader2, Tag
} from 'lucide-react'

const EMPTY_FORM = { cart_number: '', rfid_uid: '' }

const STATUS_COLORS = {
  ACTIVE:              { bg: '#dcfce7', color: '#15803d', dot: '#16a34a' },
  PENDING_PAYMENT:     { bg: '#fef9c3', color: '#854d0e', dot: '#d97706' },
  PAYMENT_IN_PROGRESS: { bg: '#dbeafe', color: '#1e40af', dot: '#2563eb' },
  PAID:                { bg: '#f0fdf4', color: '#166534', dot: '#22c55e' },
  CANCELLED:           { bg: '#fee2e2', color: '#991b1b', dot: '#ef4444' },
  FAILED:              { bg: '#fce7f3', color: '#9d174d', dot: '#ec4899' },
}

// ─── Confirm Delete Modal ─────────────────────────────────────────────────────
function ConfirmModal({ cart, onConfirm, onCancel, isAr }) {
  return (
    <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.55)',display:'flex',alignItems:'center',justifyContent:'center',padding:20,zIndex:1000 }}>
      <div style={{ borderRadius:20,boxShadow:'0 24px 80px rgba(0,0,0,0.3)',width:'100%',maxWidth:380,background:'var(--surface)',overflow:'hidden' }}>
        <div style={{ padding:'28px 24px 16px',textAlign:'center' }}>
          <div style={{ width:60,height:60,borderRadius:18,background:'#fef2f2',border:'2px solid #fca5a5',display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 14px' }}>
            <Trash2 style={{ width:26,height:26,color:'#dc2626' }} />
          </div>
          <h3 style={{ fontSize:17,fontWeight:900,color:'var(--text)',margin:'0 0 8px' }}>
            {isAr ? 'حذف العربة' : 'Delete Cart'}
          </h3>
          <p style={{ fontSize:13,color:'var(--text3)',margin:0 }}>
            {isAr ? `هل أنت متأكد من حذف "${cart?.cart_number}"؟` : `Delete "${cart?.cart_number}"? This cannot be undone.`}
          </p>
          <p style={{ fontSize:11,fontFamily:'monospace',fontWeight:700,color:'var(--primary)',marginTop:6 }}>
            RFID: {cart?.rfid_uid}
          </p>
        </div>
        <div style={{ display:'flex',gap:10,padding:'8px 20px 20px' }}>
          <button onClick={onCancel}
            style={{ flex:1,padding:'10px 0',borderRadius:11,fontWeight:700,fontSize:13,cursor:'pointer',background:'var(--surface2)',color:'var(--text2)',border:'1px solid var(--border)' }}>
            {isAr ? 'إلغاء' : 'Cancel'}
          </button>
          <button onClick={onConfirm}
            style={{ flex:1,padding:'10px 0',borderRadius:11,fontWeight:800,fontSize:13,cursor:'pointer',background:'#dc2626',color:'#fff',border:'none' }}>
            {isAr ? 'حذف' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Cart Form Modal ──────────────────────────────────────────────────────────
function CartModal({ mode, form, setForm, onSave, onClose, saving, isAr }) {
  const isEdit = mode === 'edit'

  return (
    <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.55)',display:'flex',alignItems:'center',justifyContent:'center',padding:20,zIndex:1000 }}>
      <div style={{ borderRadius:22,boxShadow:'0 24px 80px rgba(0,0,0,0.3)',width:'100%',maxWidth:440,background:'var(--surface)',overflow:'hidden' }}>

        {/* Header */}
        <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',padding:'18px 22px',background: isEdit ? 'linear-gradient(135deg,#d97706,#b45309)' : 'linear-gradient(135deg,#4f46e5,#7c3aed)',color:'#fff' }}>
          <div style={{ display:'flex',alignItems:'center',gap:10 }}>
            <div style={{ width:38,height:38,borderRadius:12,background:'rgba(255,255,255,0.2)',display:'flex',alignItems:'center',justifyContent:'center' }}>
              {isEdit ? <Pencil style={{ width:18,height:18 }} /> : <Plus style={{ width:18,height:18 }} />}
            </div>
            <div>
              <p style={{ fontWeight:900,fontSize:15,margin:0 }}>
                {isEdit ? (isAr ? 'تعديل العربة' : 'Edit Cart') : (isAr ? 'إضافة عربة جديدة' : 'Add New Cart')}
              </p>
              <p style={{ fontSize:11,opacity:0.7,margin:'2px 0 0' }}>
                {isAr ? 'ربط RFID UID بالعربة' : 'Link RFID UID to cart'}
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ width:32,height:32,borderRadius:8,border:'none',background:'rgba(255,255,255,0.2)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'#fff' }}>
            <X style={{ width:16,height:16 }} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding:'20px 22px',display:'flex',flexDirection:'column',gap:16 }}>

          {/* How to get RFID hint */}
          <div style={{ background:'#eff6ff',border:'1px solid #bfdbfe',borderRadius:12,padding:'10px 14px' }}>
            <p style={{ fontSize:11,fontWeight:700,color:'#1d4ed8',margin:'0 0 3px' }}>
              📡 {isAr ? 'كيف تحصل على RFID UID؟' : 'How to get RFID UID?'}
            </p>
            <p style={{ fontSize:11,color:'#1e40af',margin:0,lineHeight:1.6 }}>
              {isAr
                ? 'Arduino IDE → Serial Monitor (115200) → قرّب البطاقة من RC522'
                : 'Arduino IDE → Serial Monitor (115200) → Bring card near RC522'}
            </p>
            <code style={{ fontSize:11,color:'#2563eb',fontWeight:700 }}>
              [RFID] Card detected: A1:B2:C3:D4
            </code>
          </div>

          {/* Cart Number */}
          <div>
            <label style={{ fontSize:12,fontWeight:700,color:'var(--text2)',display:'block',marginBottom:6 }}>
              {isAr ? 'رقم العربة *' : 'Cart Number *'}
            </label>
            <input
              value={form.cart_number}
              onChange={e => setForm(f => ({ ...f, cart_number: e.target.value }))}
              placeholder="CART-001"
              style={{ width:'100%',padding:'11px 14px',borderRadius:11,border:'1.5px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:14,fontWeight:700,outline:'none',boxSizing:'border-box',fontFamily:'monospace' }}
              onFocus={e => e.target.style.borderColor='#4f46e5'}
              onBlur={e  => e.target.style.borderColor='var(--border)'}
            />
          </div>

          {/* RFID UID */}
          <div>
            <label style={{ fontSize:12,fontWeight:700,color:'var(--text2)',display:'block',marginBottom:6 }}>
              {isAr ? 'RFID UID *' : 'RFID UID *'}
            </label>
            <input
              value={form.rfid_uid}
              onChange={e => setForm(f => ({ ...f, rfid_uid: e.target.value.toUpperCase() }))}
              placeholder="A1:B2:C3:D4"
              dir="ltr"
              style={{ width:'100%',padding:'11px 14px',borderRadius:11,border:'1.5px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:14,fontWeight:800,outline:'none',boxSizing:'border-box',fontFamily:'monospace',letterSpacing:'0.06em' }}
              onFocus={e => e.target.style.borderColor='#4f46e5'}
              onBlur={e  => e.target.style.borderColor='var(--border)'}
            />
            <p style={{ fontSize:11,color:'var(--text3)',margin:'5px 0 0' }}>
              {isAr ? 'المعرّف الفيزيائي للبطاقة — يُستخدم لتعريف العربة عند محطة الدفع' : 'Physical card identifier — used to identify cart at payment station'}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display:'flex',gap:10,padding:'0 22px 20px' }}>
          <button onClick={onClose}
            style={{ flex:1,padding:'11px 0',borderRadius:12,fontWeight:700,fontSize:13,cursor:'pointer',background:'var(--surface2)',color:'var(--text2)',border:'1px solid var(--border)' }}>
            {isAr ? 'إلغاء' : 'Cancel'}
          </button>
          <button onClick={onSave} disabled={saving || !form.cart_number.trim() || !form.rfid_uid.trim()}
            style={{ flex:2,padding:'11px 0',borderRadius:12,fontWeight:800,fontSize:13,cursor: saving||!form.cart_number.trim()||!form.rfid_uid.trim() ? 'not-allowed':'pointer',background:'#4f46e5',color:'#fff',border:'none',opacity: saving||!form.cart_number.trim()||!form.rfid_uid.trim() ? 0.5:1,display:'flex',alignItems:'center',justifyContent:'center',gap:7 }}>
            {saving
              ? <Loader2 style={{ width:15,height:15,animation:'spin 1s linear infinite' }} />
              : <Save style={{ width:15,height:15 }} />
            }
            {isAr ? 'حفظ' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main AdminCarts Page ─────────────────────────────────────────────────────
export default function AdminCarts() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [carts,   setCarts]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search,  setSearch]  = useState('')
  const [modal,   setModal]   = useState(null)   // null | 'add' | 'edit'
  const [form,    setForm]    = useState(EMPTY_FORM)
  const [editId,  setEditId]  = useState(null)
  const [deleteCart, setDeleteCart] = useState(null)
  const [saving,  setSaving]  = useState(false)

  // ── Load Carts ─────────────────────────────────────────────────────────────
  const loadCarts = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/carts/')
      setCarts(data || [])
    } catch {
      toast.error(isAr ? 'فشل تحميل العربات' : 'Failed to load carts')
    } finally { setLoading(false) }
  }

  useEffect(() => { loadCarts() }, [])

  // ── Filtered ───────────────────────────────────────────────────────────────
  const filtered = carts.filter(c =>
    !search ||
    c.cart_number?.toLowerCase().includes(search.toLowerCase()) ||
    c.rfid_uid?.toLowerCase().includes(search.toLowerCase()) ||
    c.status?.toLowerCase().includes(search.toLowerCase())
  )

  // ── Add ────────────────────────────────────────────────────────────────────
  const openAdd = () => { setForm(EMPTY_FORM); setEditId(null); setModal('add') }

  // ── Edit ───────────────────────────────────────────────────────────────────
  const openEdit = (cart) => {
    setForm({ cart_number: cart.cart_number, rfid_uid: cart.rfid_uid })
    setEditId(cart.id)
    setModal('edit')
  }

  // ── Save (Add or Edit) ────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!form.cart_number.trim() || !form.rfid_uid.trim()) return
    setSaving(true)
    try {
      if (modal === 'add') {
        // POST /api/carts/register
        const { data } = await api.post(
          `/carts/register?cart_number=${encodeURIComponent(form.cart_number.trim())}&rfid_uid=${encodeURIComponent(form.rfid_uid.trim())}`
        )
        setCarts(prev => [data, ...prev])
        toast.success(isAr ? '✅ تم إضافة العربة' : '✅ Cart added')
      } else {
        // PUT /api/carts/{id}
        const { data } = await api.put(`/carts/${editId}`, {
          cart_number: form.cart_number.trim(),
          rfid_uid:    form.rfid_uid.trim(),
        })
        setCarts(prev => prev.map(c => c.id === editId ? data : c))
        toast.success(isAr ? '✅ تم تحديث العربة' : '✅ Cart updated')
      }
      setModal(null)
    } catch (err) {
      const msg = err.response?.data?.detail || (isAr ? 'فشل الحفظ' : 'Save failed')
      toast.error(msg)
    } finally { setSaving(false) }
  }

  // ── Delete ─────────────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!deleteCart) return
    try {
      await api.delete(`/carts/${deleteCart.id}`)
      setCarts(prev => prev.filter(c => c.id !== deleteCart.id))
      toast.success(isAr ? '🗑️ تم حذف العربة' : '🗑️ Cart deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'فشل الحذف' : 'Delete failed'))
    } finally { setDeleteCart(null) }
  }

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:18,height:'100%' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0 }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:900,color:'var(--text)',margin:0 }}>
            {isAr ? 'إدارة العربات' : 'Cart Management'}
          </h1>
          <p style={{ fontSize:12,color:'var(--text3)',margin:'3px 0 0' }}>
            {isAr ? `${carts.length} عربة مسجّلة` : `${carts.length} registered carts`}
          </p>
        </div>
        <div style={{ display:'flex',gap:8 }}>
          <button onClick={loadCarts}
            style={{ display:'flex',alignItems:'center',gap:5,padding:'8px 14px',borderRadius:10,border:'1px solid var(--border)',background:'var(--surface)',color:'var(--text2)',fontWeight:700,fontSize:12,cursor:'pointer' }}>
            <RefreshCw style={{ width:13,height:13 }} />
            {isAr ? 'تحديث' : 'Refresh'}
          </button>
          <button onClick={openAdd}
            style={{ display:'flex',alignItems:'center',gap:6,padding:'8px 18px',borderRadius:10,border:'none',background:'#4f46e5',color:'#fff',fontWeight:800,fontSize:13,cursor:'pointer',boxShadow:'0 3px 12px rgba(79,70,229,0.3)' }}>
            <Plus style={{ width:15,height:15 }} />
            {isAr ? 'إضافة عربة' : 'Add Cart'}
          </button>
        </div>
      </div>

      {/* ── Search ─────────────────────────────────────────────────────────── */}
      <div style={{ position:'relative',flexShrink:0 }}>
        <Search style={{ position:'absolute',insetInlineStart:12,top:'50%',transform:'translateY(-50%)',width:15,height:15,color:'var(--text3)' }} />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={isAr ? 'ابحث برقم العربة أو RFID...' : 'Search by cart number or RFID...'}
          style={{ width:'100%',padding:'10px 14px 10px 36px',borderRadius:11,border:'1.5px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:13,outline:'none',boxSizing:'border-box' }}
          onFocus={e => e.target.style.borderColor='#4f46e5'}
          onBlur={e  => e.target.style.borderColor='var(--border)'}
        />
      </div>

      {/* ── Stats Row ──────────────────────────────────────────────────────── */}
      <div style={{ display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,flexShrink:0 }}>
        {[
          { label: isAr ? 'إجمالي العربات' : 'Total Carts',   value: carts.length,                                          color:'#4f46e5' },
          { label: isAr ? 'نشطة الآن'      : 'Active Now',     value: carts.filter(c=>c.status==='ACTIVE').length,           color:'#16a34a' },
          { label: isAr ? 'قيد الدفع'      : 'In Payment',     value: carts.filter(c=>['PENDING_PAYMENT','PAYMENT_IN_PROGRESS'].includes(c.status)).length, color:'#d97706' },
        ].map((s,i) => (
          <div key={i} style={{ borderRadius:14,padding:'14px 16px',background:'var(--surface)',border:'1px solid var(--border)' }}>
            <p style={{ fontSize:24,fontWeight:900,color:s.color,margin:0 }}>{s.value}</p>
            <p style={{ fontSize:12,fontWeight:600,color:'var(--text3)',margin:'3px 0 0' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      <div style={{ borderRadius:18,border:'1px solid var(--border)',background:'var(--surface)',overflow:'hidden',flex:1,display:'flex',flexDirection:'column' }}>

        {/* Table Header */}
        <div style={{ display:'grid',gridTemplateColumns:'50px 1fr 1fr 120px 80px',gap:8,padding:'10px 18px',background:'var(--surface2)',borderBottom:'2px solid var(--border)',fontSize:11,fontWeight:800,color:'var(--text3)',textTransform:'uppercase',letterSpacing:'0.05em',flexShrink:0 }}>
          <span>#</span>
          <span>{isAr ? 'رقم العربة' : 'Cart Number'}</span>
          <span>RFID UID</span>
          <span style={{ textAlign:'center' }}>{isAr ? 'الحالة' : 'Status'}</span>
          <span style={{ textAlign:'center' }}>{isAr ? 'إجراءات' : 'Actions'}</span>
        </div>

        {/* Rows */}
        <div style={{ flex:1,overflowY:'auto' }}>
          {loading ? (
            <div style={{ display:'flex',justifyContent:'center',paddingTop:60 }}>
              <Loader2 style={{ width:28,height:28,color:'var(--primary)',animation:'spin 1s linear infinite' }} />
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',height:200,color:'var(--text3)',gap:10 }}>
              <ShoppingCart style={{ width:44,height:44,opacity:0.2 }} />
              <p style={{ fontWeight:700,fontSize:15,margin:0 }}>
                {search ? (isAr ? 'لا نتائج' : 'No results') : (isAr ? 'لا توجد عربات مسجّلة' : 'No carts registered yet')}
              </p>
              {!search && (
                <button onClick={openAdd}
                  style={{ marginTop:6,padding:'8px 20px',borderRadius:10,border:'none',background:'#4f46e5',color:'#fff',fontWeight:700,fontSize:13,cursor:'pointer' }}>
                  {isAr ? 'أضف عربة الآن' : 'Add a cart now'}
                </button>
              )}
            </div>
          ) : filtered.map((cart, idx) => {
            const s = STATUS_COLORS[cart.status] || STATUS_COLORS.ACTIVE
            return (
              <div key={cart.id}
                style={{ display:'grid',gridTemplateColumns:'50px 1fr 1fr 120px 80px',gap:8,padding:'13px 18px',alignItems:'center',borderBottom:'1px solid var(--border)',transition:'background 0.1s',background: idx%2===0?'var(--surface)':'rgba(0,0,0,0.012)' }}
                onMouseEnter={e => e.currentTarget.style.background='var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background=idx%2===0?'var(--surface)':'rgba(0,0,0,0.012)'}>

                {/* # */}
                <span style={{ fontSize:11,fontWeight:700,color:'var(--text3)' }}>{idx+1}</span>

                {/* Cart Number */}
                <div style={{ display:'flex',alignItems:'center',gap:10 }}>
                  <div style={{ width:36,height:36,borderRadius:10,background:'#ede9fe',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
                    <ShoppingCart style={{ width:17,height:17,color:'#7c3aed' }} />
                  </div>
                  <div>
                    <p style={{ fontWeight:800,fontSize:14,color:'var(--text)',margin:0 }}>{cart.cart_number}</p>
                    <p style={{ fontSize:10,color:'var(--text3)',margin:'2px 0 0' }}>ID: {cart.id}</p>
                  </div>
                </div>

                {/* RFID UID */}
                <div style={{ display:'flex',alignItems:'center',gap:7 }}>
                  <Tag style={{ width:13,height:13,color:'var(--text3)',flexShrink:0 }} />
                  <code style={{ fontSize:13,fontWeight:800,color:'var(--primary)',letterSpacing:'0.05em',background:'var(--surface2)',padding:'3px 8px',borderRadius:6 }}>
                    {cart.rfid_uid}
                  </code>
                </div>

                {/* Status */}
                <div style={{ display:'flex',justifyContent:'center' }}>
                  <span style={{ display:'flex',alignItems:'center',gap:5,padding:'4px 10px',borderRadius:20,background:s.bg,color:s.color,fontSize:11,fontWeight:700,whiteSpace:'nowrap' }}>
                    <span style={{ width:7,height:7,borderRadius:'50%',background:s.dot,flexShrink:0 }} />
                    {cart.status?.replace('_',' ') || 'ACTIVE'}
                  </span>
                </div>

                {/* Actions */}
                <div style={{ display:'flex',alignItems:'center',justifyContent:'center',gap:6 }}>
                  <button onClick={() => openEdit(cart)}
                    title={isAr ? 'تعديل' : 'Edit'}
                    style={{ width:30,height:30,borderRadius:8,border:'1px solid var(--border)',background:'var(--surface)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text3)',transition:'all 0.15s' }}
                    onMouseEnter={e => { e.currentTarget.style.background='#eff6ff'; e.currentTarget.style.color='#2563eb'; e.currentTarget.style.borderColor='#93c5fd' }}
                    onMouseLeave={e => { e.currentTarget.style.background='var(--surface)'; e.currentTarget.style.color='var(--text3)'; e.currentTarget.style.borderColor='var(--border)' }}>
                    <Pencil style={{ width:13,height:13 }} />
                  </button>
                  <button onClick={() => setDeleteCart(cart)}
                    title={isAr ? 'حذف' : 'Delete'}
                    style={{ width:30,height:30,borderRadius:8,border:'1px solid var(--border)',background:'var(--surface)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text3)',transition:'all 0.15s' }}
                    onMouseEnter={e => { e.currentTarget.style.background='#fef2f2'; e.currentTarget.style.color='#dc2626'; e.currentTarget.style.borderColor='#fca5a5' }}
                    onMouseLeave={e => { e.currentTarget.style.background='var(--surface)'; e.currentTarget.style.color='var(--text3)'; e.currentTarget.style.borderColor='var(--border)' }}>
                    <Trash2 style={{ width:13,height:13 }} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Modals ─────────────────────────────────────────────────────────── */}
      {(modal === 'add' || modal === 'edit') && (
        <CartModal
          mode={modal} form={form} setForm={setForm}
          onSave={handleSave} onClose={() => setModal(null)}
          saving={saving} isAr={isAr}
        />
      )}
      {deleteCart && (
        <ConfirmModal
          cart={deleteCart}
          onConfirm={handleDelete}
          onCancel={() => setDeleteCart(null)}
          isAr={isAr}
        />
      )}

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
