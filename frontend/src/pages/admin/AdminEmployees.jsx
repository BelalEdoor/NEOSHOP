import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { mockEmployees } from '../../data/adminData'
import { Plus, Pencil, Trash2, X, DollarSign, AlertTriangle } from 'lucide-react'

const ROLES = ['Cashier','Supervisor','Stock Manager','Admin']
const EMPTY = { name:'', name_ar:'', role:'Cashier', email:'', salary:'', status:'active', joinDate:'', vacationDays:'15', usedVacation:'0' }

export default function AdminEmployees() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const [employees, setEmployees] = useState(() => {
    try { return JSON.parse(localStorage.getItem('neoshop-employees') || '[]') } catch { return [] }
  })
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [editId, setEditId] = useState(null)
  const [deleteId, setDeleteId] = useState(null)

  const STATUS_STYLES = {
    active:     { bg: '#dcfce7', color: '#15803d', label: t('active') },
    'on-leave': { bg: '#fef9c3', color: '#854d0e', label: t('onLeave') },
    inactive:   { bg: '#f1f5f9', color: '#64748b', label: t('inactive') },
  }

  const openAdd = () => { setForm(EMPTY); setModal('form'); setEditId(null) }
  const openEdit = (e) => {
    setForm({ ...e, salary: e.salary.toString(), vacationDays: e.vacationDays.toString(), usedVacation: e.usedVacation.toString() })
    setEditId(e.id); setModal('form')
  }

  const handleSave = () => {
    if (!form.name.trim()) return
    const item = { ...form, salary: parseFloat(form.salary)||0, vacationDays: parseInt(form.vacationDays)||0, usedVacation: parseInt(form.usedVacation)||0 }
    if (!editId) setEmployeesAndSave(prev => [{ ...item, id: Date.now() }, ...prev])
    else setEmployeesAndSave(prev => prev.map(e => e.id === editId ? { ...e, ...item } : e))
    setModal(null)
  }

  const handleDelete = () => {
    setEmployeesAndSave(prev => prev.filter(e => e.id !== deleteId))
    setDeleteId(null)
  }

  const totalSalary = employees.filter(e => e.status === 'active').reduce((a,e) => a+e.salary, 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>{t('employeesTitle')}</h1>
          <p className="text-sm" style={{ color: 'var(--text3)' }}>{t('employeesSubtitle')}</p>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white"
          style={{ background: 'var(--primary)' }}>
          <Plus className="w-4 h-4" /> {t('addEmployee')}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl p-4 text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <p className="text-xl font-extrabold text-blue-500">{employees.filter(e=>e.status==='active').length}</p>
          <p className="text-xs font-semibold mt-1" style={{ color: 'var(--text3)' }}>{t('active')} {t('activeStaff')}</p>
        </div>
        <div className="rounded-2xl p-4 text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <p className="text-xl font-extrabold text-amber-500">{employees.filter(e=>e.status==='on-leave').length}</p>
          <p className="text-xs font-semibold mt-1" style={{ color: 'var(--text3)' }}>{t('onLeave')}</p>
        </div>
        <div className="rounded-2xl p-4 text-center" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <p className="text-xl font-extrabold text-emerald-500">₪{totalSalary.toLocaleString()}</p>
          <p className="text-xs font-semibold mt-1" style={{ color: 'var(--text3)' }}>{t('totalPayroll')}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {employees.map(emp => {
          const s = STATUS_STYLES[emp.status] || STATUS_STYLES.inactive
          const remaining = emp.vacationDays - emp.usedVacation
          return (
            <div key={emp.id} className="rounded-2xl p-4 transition-all hover:-translate-y-0.5"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)' }}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center font-extrabold text-white text-base"
                    style={{ background: 'linear-gradient(135deg,#1e40af,#6366f1)' }}>
                    {(isAr && emp.name_ar ? emp.name_ar : emp.name)?.[0]}
                  </div>
                  <div>
                    <p className="font-bold text-sm" style={{ color: 'var(--text)' }}>
                      {isAr && emp.name_ar ? emp.name_ar : emp.name}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text3)' }}>{emp.role}</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-lg text-[11px] font-bold" style={{ background: s.bg, color: s.color }}>
                  {s.label}
                </span>
              </div>
              <div className="space-y-1.5 mb-3">
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('salary')}</span>
                  <span className="font-bold" style={{ color: 'var(--primary)' }}>₪{emp.salary.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('vacationDays')}</span>
                  <span className="font-semibold" style={{ color: 'var(--text)' }}>
                    {emp.usedVacation}/{emp.vacationDays} ({remaining} {t('remaining')})
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span style={{ color: 'var(--text3)' }}>{t('joinDate')}</span>
                  <span style={{ color: 'var(--text2)' }}>{emp.joinDate}</span>
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <button onClick={() => openEdit(emp)} className="flex-1 py-1.5 rounded-xl text-xs font-bold transition-all"
                  style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}>
                  {t('edit')}
                </button>
                <button onClick={() => setDeleteId(emp.id)} className="py-1.5 px-3 rounded-xl text-xs font-bold transition-all"
                  style={{ background: '#fee2e2', color: '#ef4444' }}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Form Modal */}
      {modal === 'form' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-md rounded-2xl overflow-hidden shadow-2xl" style={{ background: 'var(--surface)' }}>
            <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
              <h3 className="font-extrabold" style={{ color: 'var(--text)' }}>{editId ? t('editEmployee') : t('addEmployee')}</h3>
              <button onClick={() => setModal(null)} style={{ color: 'var(--text3)' }}><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-3 max-h-[65vh] overflow-y-auto">
              {[
                { label: t('name'), key: 'name' },
                { label: `${t('name')} (AR)`, key: 'name_ar', dir: 'rtl' },
                { label: t('email'), key: 'email', type: 'email' },
                { label: t('salary'), key: 'salary', type: 'number' },
                { label: t('joinDate'), key: 'joinDate', type: 'date' },
                { label: t('vacationDays'), key: 'vacationDays', type: 'number' },
                { label: t('usedVacation'), key: 'usedVacation', type: 'number' },
              ].map(({ label, key, type='text', dir }) => (
                <div key={key}>
                  <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{label}</label>
                  <input type={type} className="input" dir={dir || 'auto'}
                    value={form[key]||''} onChange={e => setForm({...form,[key]:e.target.value})} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('role')}</label>
                <select className="input" value={form.role} onChange={e=>setForm({...form,role:e.target.value})}>
                  {ROLES.map(r=><option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold mb-1" style={{ color: 'var(--text2)' }}>{t('status')}</label>
                <select className="input" value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>
                  <option value="active">{t('active')}</option>
                  <option value="on-leave">{t('onLeave')}</option>
                  <option value="inactive">{t('inactive')}</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 px-6 py-4" style={{ borderTop: '1px solid var(--border)' }}>
              <button onClick={() => setModal(null)} className="flex-1 py-2.5 rounded-xl font-semibold text-sm"
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

      {/* Delete Modal */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)' }}>
          <div className="w-full max-w-sm rounded-2xl p-6 text-center shadow-2xl" style={{ background: 'var(--surface)' }}>
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <h3 className="font-extrabold mb-2" style={{ color: 'var(--text)' }}>{t('confirmDelete')}</h3>
            <p className="text-sm mb-5" style={{ color: 'var(--text3)' }}>{t('areYouSure')}</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="flex-1 py-2.5 rounded-xl font-semibold"
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
