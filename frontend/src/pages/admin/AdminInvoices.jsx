import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { invoiceApi } from '../../hooks/useApi'
import toast from 'react-hot-toast'
import {
  Search, FileText, Trash2, Eye, RefreshCw,
  Inbox, Loader2, X, ChevronDown, ChevronUp,
  ShoppingCart, Tag, Calendar, DollarSign
} from 'lucide-react'

// ─── Status Config ────────────────────────────────────────────────────────────
const STATUS = {
  CREATED:    { bg: '#eff6ff', color: '#1d4ed8', dot: '#3b82f6', label: { ar: 'منشأة',    en: 'Created'    }},
  SENT:       { bg: '#f0fdf4', color: '#15803d', dot: '#22c55e', label: { ar: 'مرسلة',    en: 'Sent'       }},
  PROCESSING: { bg: '#fef9c3', color: '#854d0e', dot: '#f59e0b', label: { ar: 'قيد الدفع', en: 'Processing' }},
  PAID:       { bg: '#dcfce7', color: '#166534', dot: '#16a34a', label: { ar: 'مدفوعة',   en: 'Paid'       }},
  CANCELLED:  { bg: '#fee2e2', color: '#991b1b', dot: '#ef4444', label: { ar: 'ملغاة',    en: 'Cancelled'  }},
}

// ─── Invoice Detail Modal ─────────────────────────────────────────────────────
function InvoiceModal({ inv, onClose, onDelete, isAr }) {
  const [deleting, setDeleting] = useState(false)
  const items = (() => { try { return JSON.parse(inv.items_json || '[]') } catch { return [] } })()
  const s = STATUS[inv.status] || STATUS.CREATED

  const handleDelete = async () => {
    if (!window.confirm(isAr ? 'هل أنت متأكد من حذف هذه الفاتورة؟' : 'Delete this invoice?')) return
    setDeleting(true)
    await onDelete(inv.id)
    setDeleting(false)
    onClose()
  }

  return (
    <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,0.55)',display:'flex',alignItems:'center',justifyContent:'center',padding:20,zIndex:1000 }}>
      <div style={{ borderRadius:22,boxShadow:'0 24px 80px rgba(0,0,0,0.3)',width:'100%',maxWidth:500,background:'var(--surface)',overflow:'hidden',maxHeight:'90vh',display:'flex',flexDirection:'column' }}>

        {/* Header */}
        <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',padding:'18px 22px',background:'linear-gradient(135deg,#1e40af,#4f46e5)',color:'#fff',flexShrink:0 }}>
          <div style={{ display:'flex',alignItems:'center',gap:10 }}>
            <div style={{ width:38,height:38,borderRadius:12,background:'rgba(255,255,255,0.2)',display:'flex',alignItems:'center',justifyContent:'center' }}>
              <FileText style={{ width:18,height:18 }} />
            </div>
            <div>
              <p style={{ fontWeight:900,fontSize:15,margin:0 }}>{inv.invoice_code || `#${inv.id}`}</p>
              <span style={{ fontSize:11,padding:'2px 8px',borderRadius:10,background:s.bg,color:s.color,fontWeight:700 }}>
                {s.label[isAr?'ar':'en']}
              </span>
            </div>
          </div>
          <button onClick={onClose} style={{ width:32,height:32,borderRadius:8,border:'none',background:'rgba(255,255,255,0.2)',cursor:'pointer',color:'#fff',display:'flex',alignItems:'center',justifyContent:'center' }}>
            <X style={{ width:16,height:16 }} />
          </button>
        </div>

        {/* Info */}
        <div style={{ padding:'16px 22px',borderBottom:'1px solid var(--border)',display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,flexShrink:0 }}>
          {[
            { label: isAr?'رقم الجلسة':'Session ID',  value: inv.session_id || '—' },
            { label: isAr?'RFID العربة':'Cart RFID',   value: inv.cart_rfid  || '—', mono: true },
            { label: isAr?'المجموع الفرعي':'Subtotal', value: `$${(inv.subtotal||0).toFixed(2)}` },
            { label: isAr?'الخصم':'Discount',          value: `$${(inv.discount||0).toFixed(2)}` },
            { label: isAr?'تاريخ الإنشاء':'Created',   value: inv.created_at ? new Date(inv.created_at).toLocaleString() : '—' },
            { label: isAr?'تاريخ الدفع':'Paid At',     value: inv.paid_at    ? new Date(inv.paid_at).toLocaleString()    : '—' },
          ].map((r,i) => (
            <div key={i} style={{ background:'var(--surface2)',borderRadius:10,padding:'10px 12px' }}>
              <p style={{ fontSize:10,fontWeight:700,color:'var(--text3)',margin:'0 0 3px',textTransform:'uppercase' }}>{r.label}</p>
              <p style={{ fontSize:13,fontWeight:800,color:'var(--text)',margin:0,fontFamily:r.mono?'monospace':'inherit' }}>{r.value}</p>
            </div>
          ))}
        </div>

        {/* Total */}
        <div style={{ display:'flex',justifyContent:'space-between',alignItems:'center',padding:'12px 22px',background:'var(--surface2)',borderBottom:'1px solid var(--border)',flexShrink:0 }}>
          <span style={{ fontWeight:700,color:'var(--text2)' }}>{isAr?'المجموع الكلي':'Total Amount'}</span>
          <span style={{ fontSize:26,fontWeight:900,color:'#16a34a' }}>${(inv.total_amount||0).toFixed(2)}</span>
        </div>

        {/* Items */}
        <div style={{ flex:1,overflowY:'auto',padding:'12px 22px' }}>
          <p style={{ fontSize:11,fontWeight:700,color:'var(--text3)',margin:'0 0 8px',textTransform:'uppercase' }}>
            {isAr?`المنتجات (${items.length})`:`Items (${items.length})`}
          </p>
          {items.length === 0 ? (
            <p style={{ color:'var(--text3)',fontSize:13 }}>{isAr?'لا توجد تفاصيل':'No item details'}</p>
          ) : items.map((item, i) => (
            <div key={i} style={{ display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:'1px solid var(--border)',fontSize:13 }}>
              <div>
                <p style={{ fontWeight:700,color:'var(--text)',margin:0 }}>{item.product_name || item.name}</p>
                <p style={{ fontSize:11,color:'var(--text3)',margin:'2px 0 0' }}>
                  ${(item.unit_price||0).toFixed(2)} × {item.quantity}
                </p>
              </div>
              <span style={{ fontWeight:800,color:'var(--primary)' }}>${(item.subtotal||0).toFixed(2)}</span>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ display:'flex',gap:10,padding:'14px 22px',borderTop:'1px solid var(--border)',flexShrink:0 }}>
          <button onClick={onClose}
            style={{ flex:1,padding:'10px 0',borderRadius:11,fontWeight:700,fontSize:13,cursor:'pointer',background:'var(--surface2)',color:'var(--text2)',border:'1px solid var(--border)' }}>
            {isAr?'إغلاق':'Close'}
          </button>
          <button onClick={handleDelete} disabled={deleting}
            style={{ flex:1,padding:'10px 0',borderRadius:11,fontWeight:800,fontSize:13,cursor:'pointer',background:'#dc2626',color:'#fff',border:'none',display:'flex',alignItems:'center',justifyContent:'center',gap:6,opacity:deleting?0.6:1 }}>
            {deleting ? <Loader2 style={{ width:14,height:14,animation:'spin 1s linear infinite' }} /> : <Trash2 style={{ width:14,height:14 }} />}
            {isAr?'حذف الفاتورة':'Delete Invoice'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main AdminInvoices ───────────────────────────────────────────────────────
export default function AdminInvoices() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [invoices, setInvoices] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [search,   setSearch]   = useState('')
  const [filter,   setFilter]   = useState('all')
  const [selected, setSelected] = useState(null)

  // ── Load from Backend ───────────────────────────────────────────────────────
  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await invoiceApi.list({ limit: 100 })
      setInvoices(data || [])
    } catch {
      toast.error(isAr ? 'فشل تحميل الفواتير' : 'Failed to load invoices')
    } finally { setLoading(false) }
  }, [isAr])

  useEffect(() => { reload() }, [reload])

  // ── Delete ──────────────────────────────────────────────────────────────────
  const handleDelete = async (id) => {
    try {
      await invoiceApi.delete(id)
      setInvoices(prev => prev.filter(i => i.id !== id))
      toast.success(isAr ? '🗑️ تم حذف الفاتورة وإعادة الجلسة لـ ACTIVE' : '🗑️ Invoice deleted — session reset to ACTIVE')
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'فشل الحذف' : 'Delete failed'))
    }
  }

  // ── Filter ──────────────────────────────────────────────────────────────────
  const filtered = invoices.filter(inv => {
    const matchFilter = filter === 'all' || inv.status === filter
    const matchSearch = !search ||
      (inv.invoice_code||'').toLowerCase().includes(search.toLowerCase()) ||
      (inv.cart_rfid||'').toLowerCase().includes(search.toLowerCase()) ||
      String(inv.session_id||'').includes(search)
    return matchFilter && matchSearch
  })

  const FILTERS = ['all','CREATED','SENT','PROCESSING','PAID','CANCELLED']

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:16,height:'100%',overflow:'hidden' }}>

      {/* Header */}
      <div style={{ display:'flex',alignItems:'flex-end',justifyContent:'space-between',flexShrink:0 }}>
        <div>
          <h1 style={{ fontSize:22,fontWeight:900,color:'var(--text)',margin:0 }}>
            {isAr?'الفواتير':'Invoices'}
          </h1>
          <p style={{ fontSize:12,color:'var(--text3)',margin:'2px 0 0' }}>
            {isAr?`${invoices.length} فاتورة`:`${invoices.length} invoices`}
          </p>
        </div>
        <button onClick={reload}
          style={{ display:'flex',alignItems:'center',gap:5,padding:'7px 14px',borderRadius:10,border:'1px solid var(--border)',background:'var(--surface)',color:'var(--text2)',fontWeight:700,fontSize:12,cursor:'pointer' }}>
          <RefreshCw style={{ width:13,height:13 }} />
          {isAr?'تحديث':'Refresh'}
        </button>
      </div>

      {/* Stats */}
      <div style={{ display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,flexShrink:0 }}>
        {[
          { label:isAr?'الكل':'Total',      value: invoices.length,                                  color:'#2563eb' },
          { label:isAr?'انتظار':'Pending',  value: invoices.filter(i=>['CREATED','SENT','PROCESSING'].includes(i.status)).length, color:'#d97706' },
          { label:isAr?'مدفوعة':'Paid',     value: invoices.filter(i=>i.status==='PAID').length,     color:'#16a34a' },
          { label:isAr?'الإيرادات':'Revenue',value:`$${invoices.filter(i=>i.status==='PAID').reduce((a,i)=>a+(i.total_amount||0),0).toFixed(2)}`, color:'#7c3aed' },
        ].map((s,i) => (
          <div key={i} style={{ borderRadius:14,padding:'12px 14px',textAlign:'center',background:'var(--surface)',border:'1px solid var(--border)' }}>
            <p style={{ fontSize:20,fontWeight:900,color:s.color,margin:0 }}>{s.value}</p>
            <p style={{ fontSize:11,fontWeight:600,color:'var(--text3)',margin:'2px 0 0' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filters + Search */}
      <div style={{ display:'flex',gap:8,flexShrink:0,flexWrap:'wrap' }}>
        <div style={{ display:'flex',gap:4,padding:4,borderRadius:12,background:'var(--surface2)',flexWrap:'wrap' }}>
          {FILTERS.map(f => {
            const s = STATUS[f]
            return (
              <button key={f} onClick={() => setFilter(f)}
                style={{ padding:'5px 12px',borderRadius:9,border:'none',fontWeight:700,fontSize:11,cursor:'pointer',background:filter===f?'var(--primary)':'transparent',color:filter===f?'#fff':'var(--text2)' }}>
                {f === 'all' ? (isAr?'الكل':'All') : (s?.label[isAr?'ar':'en'] || f)}
              </button>
            )
          })}
        </div>
        <div style={{ position:'relative',flex:1,minWidth:200 }}>
          <Search style={{ position:'absolute',insetInlineStart:10,top:'50%',transform:'translateY(-50%)',width:14,height:14,color:'var(--text3)' }} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder={isAr?'ابحث برقم الفاتورة أو RFID…':'Search by invoice code or RFID…'}
            style={{ width:'100%',padding:'8px 12px 8px 32px',borderRadius:10,border:'1px solid var(--border)',background:'var(--surface)',color:'var(--text)',fontSize:13,outline:'none',boxSizing:'border-box' }}
            onFocus={e => e.target.style.borderColor='#4f46e5'}
            onBlur={e  => e.target.style.borderColor='var(--border)'}
          />
        </div>
      </div>

      {/* Table */}
      <div style={{ flex:1,borderRadius:16,overflow:'hidden',border:'1px solid var(--border)',display:'flex',flexDirection:'column' }}>
        <div style={{ display:'grid',gridTemplateColumns:'50px 140px 100px 80px 80px 120px 80px',gap:8,padding:'10px 16px',background:'var(--surface2)',borderBottom:'2px solid var(--border)',fontSize:10,fontWeight:800,color:'var(--text3)',textTransform:'uppercase',flexShrink:0 }}>
          <span>#</span>
          <span>{isAr?'رقم الفاتورة':'Invoice'}</span>
          <span>RFID</span>
          <span>{isAr?'المجموع':'Total'}</span>
          <span>{isAr?'الحالة':'Status'}</span>
          <span>{isAr?'التاريخ':'Date'}</span>
          <span style={{ textAlign:'center' }}>{isAr?'إجراءات':'Actions'}</span>
        </div>

        <div style={{ flex:1,overflowY:'auto' }}>
          {loading ? (
            <div style={{ display:'flex',justifyContent:'center',paddingTop:60 }}>
              <Loader2 style={{ width:28,height:28,color:'var(--primary)',animation:'spin 1s linear infinite' }} />
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',height:200,color:'var(--text3)',gap:10 }}>
              <Inbox style={{ width:44,height:44,opacity:0.2 }} />
              <p style={{ fontWeight:700,fontSize:14,margin:0 }}>
                {invoices.length===0 ? (isAr?'لا توجد فواتير بعد':'No invoices yet') : (isAr?'لا نتائج':'No results')}
              </p>
              {invoices.length===0 && (
                <p style={{ fontSize:12,margin:0,opacity:0.6 }}>
                  {isAr?'ستظهر هنا فور إنشائها من الفرونت اند':'Will appear here once created from POS'}
                </p>
              )}
            </div>
          ) : filtered.map((inv, idx) => {
            const s = STATUS[inv.status] || STATUS.CREATED
            return (
              <div key={inv.id}
                style={{ display:'grid',gridTemplateColumns:'50px 140px 100px 80px 80px 120px 80px',gap:8,padding:'12px 16px',alignItems:'center',borderBottom:'1px solid var(--border)',background:idx%2===0?'var(--surface)':'rgba(0,0,0,0.012)',transition:'background 0.1s',cursor:'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background='var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background=idx%2===0?'var(--surface)':'rgba(0,0,0,0.012)'}>

                <span style={{ fontSize:11,fontWeight:700,color:'var(--text3)' }}>{idx+1}</span>

                <div style={{ display:'flex',alignItems:'center',gap:7 }}>
                  <FileText style={{ width:14,height:14,color:'var(--primary)',flexShrink:0 }} />
                  <span style={{ fontSize:12,fontWeight:800,color:'var(--text)',fontFamily:'monospace' }}>
                    {inv.invoice_code || `#${inv.id}`}
                  </span>
                </div>

                <code style={{ fontSize:11,fontWeight:700,color:'var(--text3)' }}>
                  {inv.cart_rfid || '—'}
                </code>

                <span style={{ fontWeight:900,fontSize:14,color:'#16a34a' }}>
                  ${(inv.total_amount||0).toFixed(2)}
                </span>

                <span style={{ display:'inline-flex',alignItems:'center',gap:4,padding:'3px 8px',borderRadius:20,background:s.bg,color:s.color,fontSize:10,fontWeight:700,whiteSpace:'nowrap' }}>
                  <span style={{ width:6,height:6,borderRadius:'50%',background:s.dot }} />
                  {s.label[isAr?'ar':'en']}
                </span>

                <span style={{ fontSize:11,color:'var(--text3)' }}>
                  {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : '—'}
                </span>

                <div style={{ display:'flex',justifyContent:'center',gap:5 }}>
                  <button onClick={() => setSelected(inv)}
                    title={isAr?'عرض':'View'}
                    style={{ width:28,height:28,borderRadius:7,border:'1px solid var(--border)',background:'var(--surface)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text3)' }}
                    onMouseEnter={e => { e.currentTarget.style.background='#eff6ff'; e.currentTarget.style.color='#2563eb' }}
                    onMouseLeave={e => { e.currentTarget.style.background='var(--surface)'; e.currentTarget.style.color='var(--text3)' }}>
                    <Eye style={{ width:12,height:12 }} />
                  </button>
                  <button onClick={() => handleDelete(inv.id)}
                    title={isAr?'حذف':'Delete'}
                    style={{ width:28,height:28,borderRadius:7,border:'1px solid var(--border)',background:'var(--surface)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text3)' }}
                    onMouseEnter={e => { e.currentTarget.style.background='#fef2f2'; e.currentTarget.style.color='#dc2626' }}
                    onMouseLeave={e => { e.currentTarget.style.background='var(--surface)'; e.currentTarget.style.color='var(--text3)' }}>
                    <Trash2 style={{ width:12,height:12 }} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {selected && (
        <InvoiceModal
          inv={selected} isAr={isAr}
          onClose={() => setSelected(null)}
          onDelete={handleDelete}
        />
      )}

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
