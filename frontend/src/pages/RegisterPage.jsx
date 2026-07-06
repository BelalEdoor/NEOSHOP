import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { authApi } from '../hooks/useApi'
import { useAuthStore } from '../store'
import { ShoppingBag, Mail, Lock, User, Loader2, Eye, EyeOff, Globe } from 'lucide-react'
import i18n from '../i18n/index'

export default function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})
  const [showPass, setShowPass] = useState(false)

  const validate = () => {
    const e = {}
    if (!form.name.trim()) e.name = t('nameRequired')
    if (!form.email.trim()) e.email = t('required')
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = t('invalidEmail')
    if (!form.password) e.password = t('required')
    else if (form.password.length < 6) e.password = t('passwordMin')
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      const { data } = await authApi.register({
        name:     form.name.trim(),
        email:    form.email.trim().toLowerCase(),
        password: form.password,
        role:     'customer',
      })
      setAuth(data.user, data.access_token)
      toast.success(`✅ ${t('welcomeBack')} ${data.user.name}!`)
      navigate('/onboarding')
    } catch (err) {
      const msg = err.response?.data?.detail || t('login')
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(next)
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--bg)' }}>
      <button onClick={toggleLang}
        className="fixed top-4 end-4 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text2)' }}>
        <Globe className="w-4 h-4" />
        {t('language')}
      </button>

      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4" style={{ background: 'var(--primary)' }}>
            <ShoppingBag className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold" style={{ color: 'var(--text)' }}>{t('registerTitle')}</h1>
          <p className="mt-1" style={{ color: 'var(--text2)' }}>{t('registerSubtitle')}</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Name */}
            <div>
              <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>{t('name')}</label>
              <div className="relative">
                <User className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
                <input type="text" value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  className={`input ps-10 ${errors.name ? 'border-red-400' : ''}`}
                  placeholder={t('name')} autoComplete="name" />
              </div>
              {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name}</p>}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>{t('email')}</label>
              <div className="relative">
                <Mail className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
                <input type="email" value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  className={`input ps-10 ${errors.email ? 'border-red-400' : ''}`}
                  placeholder="you@example.com" dir="ltr" autoComplete="email" />
              </div>
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>{t('password')}</label>
              <div className="relative">
                <Lock className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
                <input type={showPass ? 'text' : 'password'} value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  className={`input ps-10 pe-10 ${errors.password ? 'border-red-400' : ''}`}
                  placeholder="••••••••" dir="ltr" autoComplete="new-password" />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute end-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text3)' }}>
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {t('signUp')}
            </button>
          </form>

          <p className="text-center text-sm mt-5" style={{ color: 'var(--text2)' }}>
            {t('haveAccount')}{' '}
            <Link to="/login" className="font-bold" style={{ color: 'var(--primary)' }}>{t('signIn')}</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
