import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mockSuppliers } from '../../data/adminData'
import { Plus, Pencil, Trash2, X, Truck, DollarSign, AlertTriangle } from 'lucide-react'

const EMPTY = { name:'', contact:'', category:'Dairy', balance:'', status:'active' }
const CATS = ['Dairy','Produce','Bakery','Beverages','Meat','Snacks','Pantry']

export default function AdminSuppliers() {
  const { t } = useTranslation()
  const [suppliers, setSuppliers] = useState(() => {
    try { return JSON.parse(localStorage.getItem('neoshop-suppliers') || '[]') } catch { return [] }
  })

  const persistSuppliers = (list) => {
    setSuppliers(list)
    localStorage.setItem('neoshop-suppliers', JSON.stringify(list))
  }
  const [modal, setModal] = useState(false)
  const [form, setForm] = useState(EMPTY)
  const [editId, setEditId] = useState(null)
  const [deleteId, setDeleteId] = useState(null)

  const STATUS_STYLES = {
    active:   { bg: '#dcfce7', color: '#15803d', label: t('active') },
    inactive: { bg: '#f1f5f9', color: '#64748b', label: t('inactive') },
  }

  const openAdd = () => { setForm(EMPTY); setEditId(null); setModal(true) }
  const openEdit = (s) => { setForm({ ...s, balance: s.balance.toString() }); setEditId(s.id); setModal(true) }
  const handleSave = () => {
    if (!form.name.trim()) return
    const item = { ...form, balance: parseFloat(form.balance) || 0 }
    if (!editId) setSuppliers(prev => [{ ...item, id: Date.now(), lastOrder: '-' }, ...prev])
    else setSuppliers(prev => prev.map(s => s.id === editId ? { ...s, ...item } : s))
    setModal(false)
  }
  const handleDelete = () => {
    setSuppliers(prev => prev.filter(s => s.id !== deleteId))
    setDeleteId(null)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>{t('suppliersTitle')}</h1>
          <p className="text-sm" style={{ color: 'var(--text3)' }}>{t('suppliersSubtitle')}</p>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white"
          style={{ background: 'var(--primary)' }}>
          <Plus className="w-4 h-4" /> {t('addSupplier')}
        </button>
      </div>

      <div className="rounded-2xl p-4 flex items-center gap-4" style={{ background: 'linear-gradient(135deg,#1e40af,#312e81)', color:'white' }}>
        <div className="w-12 h-12 rounded-2xl bg-white/20 flex items-center justify-center"><DollarSign className="w-6 h-6" /></div>
        <div>
          <p className="text-2xl font-extrabold">${suppliers.reduce((a,s)=>a+s.balance,0).toLocaleString()}</p>
          <p className="text-white/70 text-sm">{t('totalSupplied')}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {suppliers.map(s => {
          const st = STATUS_STYLES[s.status] || STATUS_STYLES.active
          return (
            <div key={s.id} className="rounded-2xl p-5 transition-all hover:shadow-md"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: 'var(--primary-light)' }}>
                    <Truck className="w-5 h-5" style={{ color: 'var(--primary)' }} />
                  </div>
                  <div>
                    <p className="font-bold text-sm" style={{ color: 'var(--text)' }}>{s.name}</p>
                    <p className="text-xs" style={{ color: 'var(--text3)' }}>{t(s.category?.toLowerCase()) || s.category}</p>
                  </div>
                </div>
                <span className="text-xs font-bold px-2 py-0.5 rounded-lg" style={{ background: st.bg, color: st.color }}>
                  {st.label}
                </span>
              </div>
              <div className="space-y-1.5 mb-4">
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('contact')}</span>
                  <span style={{ color: 'var(--text)' }}>{s.contact}</span>
                </div>
                {s.phone && (
                  <div className="flex justify-between text-xs">
                    <span style={{ color: 'var(--text3)' }}>{t('phone')}</span>
                    <span style={{ color: 'var(--text)' }} dir="ltr">{s.phone}</span>
                  </div>
                )}
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('lastDelivery')}</span>
                  <span style={{ color: 'var(--text)' }}>{s.lastOrder || '—'}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('revenue')}</span>
                  <span className="font-extrabold" style={{ color: 'var(--primary)' }}>${s.balance.toLocaleString()}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => openEdit(s)} className="flex-1 py-1.5 rounded-xl text-xs font-bold transition-all"
                  style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                  {t('edit')}
                </button>
                <button onClick={() => setDeleteId(s.id)} className="py-1.5 px-3 rounded-xl text-xs font-bold"
                  style={{ background: '#fee2e2', color: '#ef4444' }}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-sm rounded-2xl overflow-hidden shadow-2xl" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h3 className="font-extrabold" style={{ color: 'var(--text)' }}>{editId ? t('editSupplier') : t('addSupplier')}</h3>
              <button onClick={() => setModal(false)} style={{ color: 'var(--text3)' }}><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-3">
              {[
                { label: t('supplierName'), key: 'name' },
                { label: t('contact'), key: 'contact' },
                { label: t('phone'), key: 'phone', dir: 'ltr' },
                { label: t('revenue'), key: 'balance', type: 'number' },
              ].map(({ label, key, type='text', dir }) => (
                <div key={key}>
                  <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{label}</label>
                  <input type={type} className="input" dir={dir || 'auto'}
                    value={form[key]||''} onChange={e=>setForm({...form,[key]:e.target.value})} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('category')}</label>
                <select className="input" value={form.category} onChange={e=>setForm({...form,category:e.target.value})}>
                  {CATS.map(c=><option key={c} value={c}>{t(c.toLowerCase())||c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('status')}</label>
                <select className="input" value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
                  <option value="active">{t('active')}</option>
                  <option value="inactive">{t('inactive')}</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 px-6 py-4" style={{ borderTop: '1px solid var(--border)' }}>
              <button onClick={() => setModal(false)} className="flex-1 py-2.5 rounded-xl font-semibold text-sm"
                style={{ background: 'var(--surface2)', color: 'var(--text2)', border: '1px solid var(--border)' }}>
                {t('cancel')}
              </button>
              <button onClick={handleSave} className="flex-1 py-2.5 rounded-xl font-bold text-sm text-white"
                style={{ background: 'var(--primary)' }}>
                {t('save')}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <div className="w-full max-w-sm rounded-2xl p-6 text-center shadow-2xl" style={{ background: 'var(--surface)' }}>
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <h3 className="font-extrabold mb-2" style={{ color: 'var(--text)' }}>{t('confirmDelete')}</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--text3)' }}>{t('areYouSure')}</p>
            <div className="flex gap-3">
              <button onClick={()=>setDeleteId(null)} className="flex-1 py-2.5 rounded-xl font-semibold"
                style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text2)' }}>
                {t('cancel')}
              </button>
              <button onClick={handleDelete} className="flex-1 py-2.5 rounded-xl font-bold text-white" style={{ background: '#ef4444' }}>
                {t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
