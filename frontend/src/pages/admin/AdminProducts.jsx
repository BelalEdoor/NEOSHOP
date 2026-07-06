import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { productApi } from '../../hooks/useApi'
import { formatPrice } from '../../utils/format'
import toast from 'react-hot-toast'
import { Plus, Pencil, Trash2, X, Search, AlertTriangle, Check } from 'lucide-react'

const EMPTY = { name: '', name_ar: '', category: 'Dairy', price: '', stock: '', barcode: '', section: 'A1', is_on_offer: false, old_price: '', offer_expires_at: '' }
const CATEGORIES = ['Dairy','Bakery','Snacks','Beverages','Produce','Meat','Pantry']
const SECTIONS = ['A1','A2','B1','B2','C1','C2','D1','D2','E1','F1']

export default function AdminProducts() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const [products, setProducts] = useState([])
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [editId, setEditId] = useState(null)

  const [deleteId, setDeleteId] = useState(null)
  const [saved, setSaved] = useState(false)

  // Load products from backend API
  useEffect(() => {
    productApi.list({ limit: 200 }).then(({ data }) => setProducts(data)).catch(() => {})
  }, [])

  const filtered = products.filter(p =>
    !search ||
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.name_ar && p.name_ar.includes(search)) ||
    p.category.toLowerCase().includes(search.toLowerCase()) ||
    p.barcode?.includes(search)
  )

  const openAdd = () => { setForm(EMPTY); setModal('add'); setEditId(null) }
  const openEdit = (p) => {
    setForm({
      ...p,
      price: String(p.price ?? ''),
      stock: String(p.quantity ?? p.stock ?? 0),
      old_price: p.old_price != null ? String(p.old_price) : '',
      offer_expires_at: p.offer_expires_at ? p.offer_expires_at.slice(0, 16) : '', // ISO -> datetime-local input format
    })
    setEditId(p.id); setModal('edit')
  }

  const handleSave = async () => {
    if (!form.name.trim()) return
    const payload = {
      name: form.name.trim(),
      name_ar: form.name_ar?.trim() || null,
      price: parseFloat(form.price) || 0,
      barcode: form.barcode?.trim() || null,
      quantity: parseInt(form.stock) || 0,
      category: form.category,
      section: form.section || null,
      is_on_offer: !!form.is_on_offer,
      old_price: form.is_on_offer && form.old_price ? parseFloat(form.old_price) : null,
      offer_expires_at: form.is_on_offer && form.offer_expires_at ? new Date(form.offer_expires_at).toISOString() : null,
    }
    try {
      if (modal === 'add') {
        const { data } = await productApi.create(payload)
        setProducts(prev => [data, ...prev])
        toast.success(isAr ? '✅ تم إضافة المنتج' : '✅ Product added')
      } else {
        const { data } = await productApi.update(editId, payload)
        setProducts(prev => prev.map(p => p.id === editId ? data : p))
        toast.success(isAr ? '✅ تم تحديث المنتج' : '✅ Product updated')
      }
      setModal(null)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      const detail = err.response?.data?.detail
      toast.error(detail || (isAr ? 'فشل الحفظ' : 'Save failed'))
    }
  }

  const handleDelete = async () => {
    try {
      await productApi.remove(deleteId)
      setProducts(prev => prev.filter(p => p.id !== deleteId))
      toast.success(isAr ? '🗑️ تم حذف المنتج' : '🗑️ Product deleted')
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'فشل الحذف' : 'Delete failed'))
    } finally {
      setDeleteId(null)
    }
  }

  const CategoryBadge = ({ cat }) => {
    const colors = { Dairy:'#0ea5e9',Bakery:'#f59e0b',Snacks:'#ef4444',Beverages:'#8b5cf6',Produce:'#22c55e',Meat:'#f97316',Pantry:'#64748b' }
    return (
      <span className="px-2 py-0.5 rounded-lg text-[11px] font-bold text-white"
        style={{ background: colors[cat] || '#64748b' }}>
        {t(cat.toLowerCase()) || cat}
      </span>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>{t('productsTitle')}</h1>
          <p className="text-sm" style={{ color: 'var(--text3)' }}>{products.length} {t('productsSubtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="flex items-center gap-1 text-xs font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-2 rounded-xl">
              <Check className="w-3.5 h-3.5" /> {t('saved')}
            </span>
          )}
          <button onClick={openAdd} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5"
            style={{ background: 'var(--primary)', boxShadow: '0 4px 14px rgba(37,99,235,0.3)' }}>
            <Plus className="w-4 h-4" /> {t('addProduct')}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
        <input
          className="input ps-10" value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={`${t('search')}…`}
        />
      </div>

      {/* Table */}
      <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ background: 'var(--surface2)', borderBottom: '1px solid var(--border)' }}>
                {[t('productName'), t('category'), t('price'), t('stockQty'), t('barcode'), ''].map((h,i) => (
                  <th key={i} className="px-4 py-3 text-start text-xs font-bold uppercase tracking-wide"
                    style={{ color: 'var(--text3)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-10" style={{ color: 'var(--text3)' }}>{t('noResults')}</td></tr>
              ) : filtered.map(p => (
                <tr key={p.id} className="transition-colors hover:opacity-90" style={{ borderBottom: '1px solid var(--border)' }}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {p.image && <img src={p.image} alt={p.name} className="w-9 h-9 rounded-lg object-cover shrink-0" />}
                      <div>
                        <p className="font-semibold text-sm flex items-center gap-1.5" style={{ color: 'var(--text)' }}>
                          {isAr && p.name_ar ? p.name_ar : p.name}
                          {p.is_on_offer && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-bold text-white" style={{ background:'#dc2626' }}>
                              {isAr ? 'عرض' : 'OFFER'}
                            </span>
                          )}
                        </p>
                        {p.name_ar && <p className="text-xs" style={{ color: 'var(--text3)' }}>
                          {isAr ? p.name : p.name_ar}
                        </p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><CategoryBadge cat={p.category} /></td>
                  <td className="px-4 py-3 font-bold" style={{ color: 'var(--primary)' }}>{formatPrice(p.price)}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold text-xs px-2 py-1 rounded-lg ${p.stock <= 0 ? 'bg-red-100 text-red-600' : p.stock < 10 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {(p.quantity ?? p.stock ?? 0) <= 0 ? t('outOfStock') : (p.quantity ?? p.stock ?? 0) < 10 ? `⚠️ ${p.quantity ?? p.stock ?? 0}` : (p.quantity ?? p.stock ?? 0)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs" style={{ color: 'var(--text3)' }}>{p.barcode || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEdit(p)} className="p-1.5 rounded-lg transition-all hover:scale-110"
                        style={{ color: 'var(--primary)', background: 'var(--primary-light)' }}>
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setDeleteId(p.id)} className="p-1.5 rounded-lg transition-all hover:scale-110"
                        style={{ color: '#ef4444', background: '#fee2e2' }}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-md rounded-2xl overflow-hidden shadow-2xl" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h3 className="font-extrabold text-base" style={{ color: 'var(--text)' }}>
                {modal === 'add' ? t('addProduct') : t('editProduct')}
              </h3>
              <button onClick={() => setModal(null)} style={{ color: 'var(--text3)' }}><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              {[
                { label: t('productNameEn'), key: 'name', type: 'text' },
                { label: t('productNameAr'), key: 'name_ar', type: 'text', dir: 'rtl' },
                { label: t('price'), key: 'price', type: 'number' },
                { label: t('stockQty'), key: 'stock', type: 'number' },
                { label: t('barcode'), key: 'barcode', type: 'text' },
              ].map(({ label, key, type, dir }) => (
                <div key={key}>
                  <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{label}</label>
                  <input type={type} className="input" dir={dir || 'auto'}
                    value={form[key] || ''} onChange={e => setForm({ ...form, [key]: e.target.value })} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('category')}</label>
                <select className="input" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })}>
                  {CATEGORIES.map(c => <option key={c} value={c}>{t(c.toLowerCase()) || c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('storageSection')}</label>
                <select className="input" value={form.section} onChange={e => setForm({ ...form, section: e.target.value })}>
                  {SECTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* Offer fields -- real discount data, replaces the old hardcoded mock offers page */}
              <div className="rounded-xl p-3" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <label className="flex items-center justify-between gap-3 cursor-pointer">
                  <span className="text-xs font-bold" style={{ color: 'var(--text2)' }}>
                    {isAr ? 'عرض خاص (تخفيض)' : 'On offer (discount)'}
                  </span>
                  <button type="button"
                    onClick={() => setForm({ ...form, is_on_offer: !form.is_on_offer })}
                    className="relative shrink-0 w-11 h-6 rounded-full transition-colors"
                    style={{ background: form.is_on_offer ? 'var(--primary)' : 'var(--border)' }}>
                    <span className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform"
                      style={{ transform: form.is_on_offer ? 'translateX(1.25rem)' : 'translateX(0.125rem)' }} />
                  </button>
                </label>

                {form.is_on_offer && (
                  <div className="mt-3 space-y-3">
                    <div>
                      <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>
                        {isAr ? 'السعر الأصلي (قبل الخصم)' : 'Original price (before discount)'}
                      </label>
                      <input type="number" step="0.01" className="input"
                        placeholder={isAr ? 'يجب أن يكون أعلى من السعر الحالي' : 'Must be higher than current price'}
                        value={form.old_price || ''} onChange={e => setForm({ ...form, old_price: e.target.value })} />
                    </div>
                    <div>
                      <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>
                        {isAr ? 'تاريخ انتهاء العرض (اختياري)' : 'Offer expires at (optional)'}
                      </label>
                      <input type="datetime-local" className="input"
                        value={form.offer_expires_at || ''} onChange={e => setForm({ ...form, offer_expires_at: e.target.value })} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-3 px-6 py-4" style={{ borderTop: '1px solid var(--border)' }}>
              <button onClick={() => setModal(null)} className="flex-1 py-2.5 rounded-xl font-semibold text-sm transition-all"
                style={{ background: 'var(--surface2)', color: 'var(--text2)', border: '1px solid var(--border)' }}>
                {t('cancel')}
              </button>
              <button onClick={handleSave} className="flex-1 py-2.5 rounded-xl font-bold text-sm text-white transition-all"
                style={{ background: 'var(--primary)' }}>
                {t('save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-sm rounded-2xl p-6 text-center shadow-2xl" style={{ background: 'var(--surface)' }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ background: '#fee2e2' }}>
              <AlertTriangle className="w-7 h-7 text-red-500" />
            </div>
            <h3 className="font-extrabold text-lg mb-2" style={{ color: 'var(--text)' }}>{t('confirmDelete')}</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--text3)' }}>{t('areYouSure')}</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="flex-1 py-2.5 rounded-xl font-semibold text-sm"
                style={{ background: 'var(--surface2)', color: 'var(--text2)', border: '1px solid var(--border)' }}>
                {t('cancel')}
              </button>
              <button onClick={handleDelete} className="flex-1 py-2.5 rounded-xl font-bold text-sm text-white"
                style={{ background: '#ef4444' }}>
                {t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
