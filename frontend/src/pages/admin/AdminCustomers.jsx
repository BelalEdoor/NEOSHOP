import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import {
  Loader2, Search, X, Pencil, Save, KeyRound, Ban, ShieldCheck,
  Receipt, HeartPulse, User as UserIcon, Mail, Cake, Users2,
} from 'lucide-react'
import { adminCustomerApi } from '../../hooks/useApi'

// ─────────────────────────────────────────────────────────────────────────────
// Detail / edit drawer
// ─────────────────────────────────────────────────────────────────────────────
function CustomerDrawer({ customer, isAr, onClose, onUpdated }) {
  const [form, setForm] = useState({
    name: customer.name || '',
    email: customer.email || '',
    age: customer.age ?? '',
    gender: customer.gender || '',
    allergies: (customer.allergies || []).join(', '),
    other_health_notes: customer.other_health_notes || '',
  })
  const [saving, setSaving] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [resetting, setResetting] = useState(false)
  const [invoices, setInvoices] = useState([])
  const [invoicesLoading, setInvoicesLoading] = useState(true)

  useEffect(() => {
    setInvoicesLoading(true)
    adminCustomerApi.getInvoices(customer.id)
      .then(({ data }) => setInvoices(data || []))
      .catch(() => {})
      .finally(() => setInvoicesLoading(false))
  }, [customer.id])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        name: form.name,
        email: form.email,
        age: form.age === '' ? null : parseInt(form.age),
        gender: form.gender || null,
        allergies: form.allergies.split(',').map(s => s.trim()).filter(Boolean),
        other_health_notes: form.other_health_notes || null,
      }
      const { data } = await adminCustomerApi.update(customer.id, payload)
      onUpdated(data)
      toast.success(isAr ? '✅ تم حفظ التعديلات' : '✅ Changes saved')
    } catch (err) {
      toast.error(err?.response?.data?.detail || (isAr ? 'تعذّر الحفظ' : 'Could not save'))
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async () => {
    setToggling(true)
    try {
      const fn = customer.is_active ? adminCustomerApi.disable : adminCustomerApi.enable
      const { data } = await fn(customer.id)
      onUpdated({ ...customer, is_active: data.is_active })
      toast.success(
        data.is_active
          ? (isAr ? '✅ تم إعادة تفعيل الحساب' : '✅ Account reactivated')
          : (isAr ? '🚫 تم إيقاف الحساب' : '🚫 Account disabled')
      )
    } catch (err) {
      toast.error(err?.response?.data?.detail || (isAr ? 'تعذّر تنفيذ العملية' : 'Could not perform action'))
    } finally {
      setToggling(false)
    }
  }

  const handleResetPassword = async () => {
    if (newPassword.trim().length < 6) {
      toast.error(isAr ? 'كلمة المرور يجب أن تكون 6 أحرف على الأقل' : 'Password must be at least 6 characters')
      return
    }
    setResetting(true)
    try {
      await adminCustomerApi.resetPassword(customer.id, newPassword.trim())
      setNewPassword('')
      toast.success(isAr ? '✅ تم تعيين كلمة مرور جديدة' : '✅ New password set')
    } catch (err) {
      toast.error(err?.response?.data?.detail || (isAr ? 'تعذّر تعيين كلمة المرور' : 'Could not reset password'))
    } finally {
      setResetting(false)
    }
  }

  const field = (label, icon, input) => (
    <div>
      <label className="flex items-center gap-1.5 text-xs font-bold mb-1.5" style={{ color: 'var(--text3)' }}>
        {icon}{label}
      </label>
      {input}
    </div>
  )

  const inputStyle = {
    width: '100%', padding: '9px 12px', borderRadius: 10, fontSize: 13,
    border: '1px solid var(--border)', background: 'var(--surface2)', color: 'var(--text)',
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', justifyContent: 'flex-end' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)' }} onClick={onClose} />
      <div style={{
        position: 'relative', width: '100%', maxWidth: 460, height: '100%', overflowY: 'auto',
        background: 'var(--surface)', padding: 24, boxShadow: '-8px 0 30px rgba(0,0,0,0.2)',
      }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-extrabold flex items-center gap-2" style={{ color: 'var(--text)' }}>
            <UserIcon className="w-5 h-5" style={{ color: 'var(--primary)' }} />
            {customer.name}
          </h2>
          <button onClick={onClose} className="p-2 rounded-xl" style={{ background: 'var(--surface2)' }}>
            <X className="w-4 h-4" style={{ color: 'var(--text3)' }} />
          </button>
        </div>

        {/* حالة الحساب */}
        <div className="flex items-center justify-between mb-5 p-3 rounded-xl"
          style={{ background: customer.is_active ? '#dcfce7' : '#fee2e2' }}>
          <span className="text-xs font-bold" style={{ color: customer.is_active ? '#15803d' : '#991b1b' }}>
            {customer.is_active ? (isAr ? '🟢 الحساب نشط' : '🟢 Account active') : (isAr ? '🚫 الحساب موقوف' : '🚫 Account disabled')}
          </span>
          <button onClick={handleToggleActive} disabled={toggling}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white"
            style={{ background: toggling ? 'var(--text3)' : customer.is_active ? '#dc2626' : '#16a34a' }}>
            {toggling ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : customer.is_active ? <Ban className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            {customer.is_active ? (isAr ? 'تعطيل' : 'Disable') : (isAr ? 'تفعيل' : 'Enable')}
          </button>
        </div>

        {/* بيانات الحساب */}
        <div className="space-y-3 mb-5">
          {field(isAr ? 'الاسم' : 'Name', <UserIcon className="w-3.5 h-3.5" />,
            <input style={inputStyle} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />)}
          {field(isAr ? 'البريد الإلكتروني' : 'Email', <Mail className="w-3.5 h-3.5" />,
            <input style={inputStyle} value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />)}
          <div className="grid grid-cols-2 gap-3">
            {field(isAr ? 'العمر' : 'Age', <Cake className="w-3.5 h-3.5" />,
              <input type="number" style={inputStyle} value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} />)}
            {field(isAr ? 'الجنس' : 'Gender', <Users2 className="w-3.5 h-3.5" />,
              <select style={inputStyle} value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}>
                <option value="">—</option>
                <option value="male">{isAr ? 'ذكر' : 'Male'}</option>
                <option value="female">{isAr ? 'أنثى' : 'Female'}</option>
              </select>)}
          </div>
        </div>

        {/* الملف الصحي */}
        <div className="mb-5">
          <p className="flex items-center gap-1.5 text-xs font-bold mb-2" style={{ color: 'var(--text3)' }}>
            <HeartPulse className="w-3.5 h-3.5" style={{ color: '#dc2626' }} />
            {isAr ? 'الملف الصحي' : 'Health profile'}
          </p>
          {field(isAr ? 'الحساسيات (مفصولة بفاصلة)' : 'Allergies (comma separated)', null,
            <input style={inputStyle} value={form.allergies}
              onChange={e => setForm({ ...form, allergies: e.target.value })}
              placeholder={isAr ? 'مثال: مكسرات، حليب' : 'e.g. nuts, milk'} />)}
          <div className="mt-3">
            {field(isAr ? 'ملاحظات صحية' : 'Health notes', null,
              <textarea style={{ ...inputStyle, minHeight: 70, resize: 'vertical' }} value={form.other_health_notes}
                onChange={e => setForm({ ...form, other_health_notes: e.target.value })} />)}
          </div>
        </div>

        <button onClick={handleSave} disabled={saving}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold text-white mb-6"
          style={{ background: 'var(--primary)' }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {isAr ? 'حفظ التعديلات' : 'Save changes'}
        </button>

        {/* كلمة المرور */}
        <div className="mb-6 p-3 rounded-xl" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
          <p className="flex items-center gap-1.5 text-xs font-bold mb-2" style={{ color: 'var(--text2)' }}>
            <KeyRound className="w-3.5 h-3.5" /> {isAr ? 'كلمة المرور' : 'Password'}
          </p>
          <p className="text-[11px] mb-2" style={{ color: 'var(--text3)' }}>
            {isAr
              ? 'لأسباب أمنية، لا يمكن عرض كلمة المرور الحالية (مخزَّنة مُجزَّأة). يمكنك تعيين كلمة مرور جديدة للعميل.'
              : "For security reasons the current password can't be shown (stored hashed). You can set a new one for this customer."}
          </p>
          <div className="flex gap-2">
            <input type="text" style={inputStyle} placeholder={isAr ? 'كلمة مرور جديدة' : 'New password'}
              value={newPassword} onChange={e => setNewPassword(e.target.value)} />
            <button onClick={handleResetPassword} disabled={resetting}
              className="px-4 rounded-xl text-xs font-bold text-white shrink-0"
              style={{ background: resetting ? 'var(--text3)' : '#1e40af' }}>
              {resetting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (isAr ? 'تعيين' : 'Set')}
            </button>
          </div>
        </div>

        {/* الفواتير */}
        <div>
          <p className="flex items-center gap-1.5 text-xs font-bold mb-2" style={{ color: 'var(--text2)' }}>
            <Receipt className="w-3.5 h-3.5" /> {isAr ? 'الفواتير' : 'Invoices'} ({invoices.length})
          </p>
          {invoicesLoading ? (
            <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--primary)' }} /></div>
          ) : invoices.length === 0 ? (
            <p className="text-xs text-center py-6" style={{ color: 'var(--text3)' }}>{isAr ? 'لا توجد فواتير بعد' : 'No invoices yet'}</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {invoices.map(inv => (
                <div key={inv.id} className="flex items-center justify-between p-2.5 rounded-lg"
                  style={{ background: 'var(--surface2)' }}>
                  <div>
                    <p className="text-xs font-bold" style={{ color: 'var(--text)' }}>{inv.invoice_code || `#${inv.id}`}</p>
                    <p className="text-[10px]" style={{ color: 'var(--text3)' }}>{inv.status}</p>
                  </div>
                  <span className="text-xs font-bold" style={{ color: 'var(--primary)' }}>${inv.total_amount?.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
export default function AdminCustomers() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'

  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState(null)

  const load = useCallback((query) => {
    setLoading(true)
    adminCustomerApi.list(query)
      .then(({ data }) => setCustomers(data || []))
      .catch(() => toast.error(isAr ? 'فشل تحميل قائمة العملاء' : 'Failed to load customers'))
      .finally(() => setLoading(false))
  }, [isAr])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const id = setTimeout(() => load(q || undefined), 350)
    return () => clearTimeout(id)
  }, [q, load])

  const handleUpdated = (updated) => {
    setCustomers(prev => prev.map(c => c.id === updated.id ? { ...c, ...updated } : c))
    setSelected(prev => prev ? { ...prev, ...updated } : prev)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>{t('customersTitle')}</h1>
          <p className="text-sm" style={{ color: 'var(--text3)' }}>{t('customersSubtitle')}</p>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 absolute top-1/2 -translate-y-1/2 start-3" style={{ color: 'var(--text3)' }} />
          <input value={q} onChange={e => setQ(e.target.value)}
            placeholder={isAr ? 'بحث بالاسم أو البريد...' : 'Search name or email...'}
            style={{
              padding: '9px 12px 9px 34px', borderRadius: 12, fontSize: 13, width: 260,
              border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)',
            }} />
        </div>
      </div>

      <div className="card overflow-x-auto p-0">
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--primary)' }} /></div>
        ) : customers.length === 0 ? (
          <div className="text-sm py-16 text-center" style={{ color: 'var(--text3)' }}>{isAr ? 'لا يوجد عملاء' : 'No customers'}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {[
                  isAr ? 'الاسم' : 'Name', isAr ? 'البريد' : 'Email',
                  isAr ? 'الحالة' : 'Status', isAr ? 'الطلبات' : 'Orders',
                  isAr ? 'إجمالي الإنفاق' : 'Total spent', '',
                ].map(h => (
                  <th key={h} className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {customers.map(c => (
                <tr key={c.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td className="px-4 py-3 font-semibold" style={{ color: 'var(--text)' }}>{c.name}</td>
                  <td className="px-4 py-3" style={{ color: 'var(--text2)' }}>{c.email}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex px-2 py-1 rounded-full text-[11px] font-bold"
                      style={{ background: c.is_active ? '#dcfce7' : '#fee2e2', color: c.is_active ? '#15803d' : '#991b1b' }}>
                      {c.is_active ? (isAr ? 'نشط' : 'Active') : (isAr ? 'موقوف' : 'Disabled')}
                    </span>
                  </td>
                  <td className="px-4 py-3" style={{ color: 'var(--text2)' }}>{c.total_orders}</td>
                  <td className="px-4 py-3 font-bold" style={{ color: 'var(--primary)' }}>${c.total_spent?.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => setSelected(c)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold"
                      style={{ background: 'var(--surface2)', color: 'var(--text2)' }}>
                      <Pencil className="w-3.5 h-3.5" /> {isAr ? 'إدارة' : 'Manage'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selected && (
        <CustomerDrawer customer={selected} isAr={isAr} onClose={() => setSelected(null)} onUpdated={handleUpdated} />
      )}
    </div>
  )
}
