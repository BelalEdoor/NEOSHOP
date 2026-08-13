import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { authApi } from '../hooks/useApi'
import api from '../hooks/useApi'
import { useAuthStore, ADMIN_EMAILS } from '../store'
import {
  ShoppingBag, Mail, Lock, Loader2, Globe,
  UserX, Eye, EyeOff
} from 'lucide-react'
import i18n from '../i18n/index'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth  = useAuthStore((s) => s.setAuth)
  const isAr     = i18n.language === 'ar'

  // جزء من تجربة العميل الفاتحة دائماً — راجع ملاحظة components/ui/Layout.jsx
  useEffect(() => { document.documentElement.classList.remove('dark') }, [])


  const [form,     setForm]     = useState({ email: '', password: '' })
  const [loading,  setLoading]  = useState(false)
  const [errors,   setErrors]   = useState({})
  const [notFound, setNotFound] = useState(false)
  const [showPass, setShowPass] = useState(false)

  // الهوية الثابتة لهذه العربة — مضبوطة مرة واحدة في .env لكل راسبيري باي
  // ولا تتغيّر أبداً. الباك اند يسحب rfid_uid الحالي من قاعدة البيانات
  // بنفسه عند بدء الجلسة، فتغيير الأونر للبطاقة لاحقاً من لوحة التحكم
  // ينعكس تلقائياً بدون أي حاجة لإعادة بناء الفرونت اند.
  const CART_NUMBER = import.meta.env.VITE_CART_NUMBER || null

  const validate = () => {
    const e = {}
    if (!form.email.trim()) e.email = isAr ? 'البريد مطلوب' : 'Email required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = isAr ? 'بريد غير صالح' : 'Invalid email'
    if (!form.password) e.password = isAr ? 'كلمة المرور مطلوبة' : 'Password required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setNotFound(false)

    try {
      const emailLower = form.email.toLowerCase().trim()

      // ── Step 1: تسجيل الدخول ──────────────────────────────────────────
      const { data } = await authApi.login({ email: emailLower, password: form.password })
      const { user, access_token } = data

      // Admin يروح مباشرة للداشبورد بدون جلسة تسوق
      if (ADMIN_EMAILS.includes(user.email)) {
        setAuth(user, access_token)
        toast.success(`👑 ${isAr ? 'مرحباً' : 'Welcome'} ${user.name}!`)
        navigate('/admin')
        return
      }

      // ── Step 2: فتح جلسة تسوق مرتبطة بالعربة تلقائياً ───────────────
      // CART_NUMBER هو الهوية الثابتة للعربة المثبّتة في .env لهاد الراسبيري
      // باي — الباك اند يحلّ rfid_uid الحالي من جدول carts بنفسه.
      const params = CART_NUMBER ? `?cart_number=${encodeURIComponent(CART_NUMBER)}` : ''
      try {
        await api.post(
          `/sessions/start${params}`,
          null,
          { headers: { Authorization: `Bearer ${access_token}` } }
        )
      } catch (sessionErr) {
        if (CART_NUMBER && sessionErr?.response?.status === 404) {
          // العربة غير مسجّلة بقاعدة البيانات بعد — سجّل الدخول عادي وأبلغ
          // المستخدم بدل ما يفشل تسجيل الدخول بالكامل بسبب هذا الخطأ
          toast.error(
            isAr
              ? `⚠️ عربة "${CART_NUMBER}" غير مسجّلة بعد — راجع الأونر`
              : `⚠️ Cart "${CART_NUMBER}" is not registered yet — contact the owner`
          )
        } else {
          throw sessionErr
        }
      }

      // حفظ بيانات المستخدم والتوكن
      setAuth(user, access_token)

      toast.success(
        CART_NUMBER
          ? (isAr ? `✅ مرحباً ${user.name}! جلسة التسوق بدأت` : `✅ Welcome ${user.name}! Shopping session started`)
          : (isAr ? `✅ مرحباً ${user.name}!` : `✅ Welcome ${user.name}!`)
      )

      navigate('/')

    } catch (err) {
      const status = err.response?.status
      const detail = (err.response?.data?.detail || '').toLowerCase()

      if (status === 401 || detail.includes('invalid') || detail.includes('incorrect')) {
        setNotFound(true)
      } else if (!err.response) {
        toast.error(isAr ? '⚠️ تعذّر الاتصال بالخادم' : '⚠️ Cannot connect to server')
      } else {
        toast.error(err.response?.data?.detail || (isAr ? 'فشل تسجيل الدخول' : 'Login failed'))
      }
    } finally { setLoading(false) }
  }

  const toggleLang = () => {
    const next = i18n.language === 'en' ? 'ar' : 'en'
    i18n.changeLanguage(next)
    document.body.dir = next === 'ar' ? 'rtl' : 'ltr'
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'var(--bg)' }}>

      <button onClick={toggleLang}
        className="fixed top-4 end-4 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text2)' }}>
        <Globe className="w-4 h-4" />
        {i18n.language === 'ar' ? 'EN' : 'عربي'}
      </button>

      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
            style={{ background: 'var(--primary)' }}>
            <ShoppingBag className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold" style={{ color: 'var(--text)' }}>
            NEOSHOP
          </h1>
          <p className="mt-1" style={{ color: 'var(--text2)' }}>
            {isAr ? 'سجّل دخولك لبدء التسوق' : 'Sign in to start shopping'}
          </p>

          {/* إظهار رقم العربة الحالية */}
          {CART_NUMBER && (
            <div className="inline-flex items-center gap-2 mt-3 px-4 py-2 rounded-full text-sm font-bold"
              style={{ background: '#ede9fe', color: '#7c3aed' }}>
              🛒 {isAr ? 'العربة:' : 'Cart:'} {CART_NUMBER}
            </div>
          )}
        </div>

        {/* Error Banner */}
        {notFound && (
          <div className="mb-4 p-4 rounded-2xl flex items-start gap-3"
            style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
            <UserX className="w-5 h-5 mt-0.5 flex-shrink-0 text-red-500" />
            <div>
              <p className="font-bold text-sm text-red-700">
                {isAr ? 'البريد أو كلمة المرور غير صحيحة' : 'Invalid email or password'}
              </p>
              <Link to="/register" className="text-sm font-bold mt-1 inline-block"
                style={{ color: '#2563eb' }}>
                {isAr ? 'إنشاء حساب جديد ←' : 'Create account ←'}
              </Link>
            </div>
          </div>
        )}

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold mb-1.5"
                style={{ color: 'var(--text2)' }}>
                {isAr ? 'البريد الإلكتروني' : 'Email'}
              </label>
              <div className="relative">
                <Mail className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4"
                  style={{ color: 'var(--text3)' }} />
                <input type="email" value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  className={`input ps-10 ${errors.email ? 'border-red-400' : ''}`}
                  placeholder="you@example.com" dir="ltr" autoComplete="email" />
              </div>
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold mb-1.5"
                style={{ color: 'var(--text2)' }}>
                {isAr ? 'كلمة المرور' : 'Password'}
              </label>
              <div className="relative">
                <Lock className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4"
                  style={{ color: 'var(--text3)' }} />
                <input type={showPass ? 'text' : 'password'} value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  className={`input ps-10 pe-10 ${errors.password ? 'border-red-400' : ''}`}
                  placeholder="••••••••" dir="ltr" autoComplete="current-password" />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute end-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text3)' }}>
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password}</p>}
            </div>

            <button type="submit"
              className="btn-primary w-full flex items-center justify-center gap-2"
              disabled={loading}>
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isAr ? 'تسجيل الدخول' : 'Login'}
            </button>
          </form>

          <p className="text-center text-sm mt-5" style={{ color: 'var(--text2)' }}>
            {isAr ? 'ليس لديك حساب؟' : "Don't have an account?"}{' '}
            <Link to="/register" className="font-bold" style={{ color: 'var(--primary)' }}>
              {isAr ? 'سجّل الآن' : 'Sign Up'}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}