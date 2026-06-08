import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { userApi } from '../hooks/useApi'
import { useAuthStore } from '../store'
import { User, Mail, Shield, X, Plus, Loader2, CheckCircle } from 'lucide-react'

const COMMON_ALLERGIES = ['milk','nuts','peanuts','gluten','eggs','soy','fish','shellfish','sesame','sulfites']

export default function ProfilePage() {
  const { t } = useTranslation()
  const { user, setUser } = useAuthStore()

  const [form, setForm] = useState({
    name: user?.name || '',
    email: user?.email || '',
    allergies: user?.allergies || [],
  })
  const [allergyInput, setAllergyInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  const addAllergy = (allergy) => {
    const a = allergy.trim().toLowerCase()
    if (!a || form.allergies.includes(a)) return
    setForm({ ...form, allergies: [...form.allergies, a] })
    setAllergyInput('')
  }

  const removeAllergy = (a) => setForm({ ...form, allergies: form.allergies.filter(x => x !== a) })

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); addAllergy(allergyInput) }
  }

  const handleSave = async () => {
    setLoading(true)
    setSaved(false)
    try {
      const { data } = await userApi.updateMe({ name: form.name, email: form.email, allergies: form.allergies })
      setUser(data)
      setSaved(true)
      toast.success(t('profileUpdated') || 'Profile updated!')
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">

      {/* Header card */}
      <div className="card flex items-center gap-5">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center shrink-0"
          style={{ background: 'var(--primary-light)' }}>
          <User className="w-8 h-8" style={{ color: 'var(--primary)' }} />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text)' }}>{user?.name}</h1>
          <p className="text-sm" style={{ color: 'var(--text2)' }}>{user?.email}</p>
          {user?.created_at && (
            <p className="text-xs mt-1" style={{ color: 'var(--text3)' }}>
              {t('memberSince')} {new Date(user.created_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>

      {/* Edit form */}
      <div className="card space-y-5">
        <h2 className="font-bold text-lg flex items-center gap-2" style={{ color: 'var(--text)' }}>
          <User className="w-5 h-5" style={{ color: 'var(--primary)' }} />
          {t('editProfile')}
        </h2>

        <div>
          <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>{t('name')}</label>
          <input type="text" className="input" value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })} />
        </div>

        <div>
          <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>{t('email')}</label>
          <div className="relative">
            <Mail className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
            <input type="email" className="input ps-10" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })} dir="ltr" />
          </div>
        </div>

        <button onClick={handleSave} disabled={loading} className="btn-primary flex items-center gap-2">
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {saved && <CheckCircle className="w-4 h-4" />}
          {t('saveChanges')}
        </button>
      </div>

      {/* Allergies section */}
      <div className="card space-y-4">
        <h2 className="font-bold text-lg flex items-center gap-2" style={{ color: 'var(--text)' }}>
          <Shield className="w-5 h-5 text-orange-500" />
          {t('allergies')}
        </h2>

        <p className="text-sm" style={{ color: 'var(--text2)' }}>{t('allergiesHelp')}</p>

        {/* Current allergies */}
        {form.allergies.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {form.allergies.map(a => (
              <span key={a} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium"
                style={{ background: '#fff7ed', border: '1px solid #fed7aa', color: '#c2410c' }}>
                {a}
                <button onClick={() => removeAllergy(a)} className="hover:text-red-600 transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <input type="text" className="input flex-1"
            placeholder={t('addAllergy') || 'Add allergy...'}
            value={allergyInput}
            onChange={e => setAllergyInput(e.target.value)}
            onKeyDown={handleKeyDown} />
          <button onClick={() => addAllergy(allergyInput)} className="btn-secondary flex items-center gap-1.5">
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>

        {/* Quick add */}
        <div>
          <p className="text-xs mb-2" style={{ color: 'var(--text3)' }}>Common allergies:</p>
          <div className="flex flex-wrap gap-2">
            {COMMON_ALLERGIES.filter(a => !form.allergies.includes(a)).map(a => (
              <button key={a} onClick={() => addAllergy(a)}
                className="px-2.5 py-1 rounded-full text-xs transition-all hover:-translate-y-0.5"
                style={{ border: '1px solid var(--border)', color: 'var(--text2)', background: 'var(--surface2)' }}>
                + {a}
              </button>
            ))}
          </div>
        </div>

        <button onClick={handleSave} disabled={loading} className="btn-primary flex items-center gap-2">
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {saved && <CheckCircle className="w-4 h-4" />}
          {t('saveChanges')}
        </button>
      </div>
    </div>
  )
}
