import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { allergensApi, healthConditionsApi, onboardingApi } from '../hooks/useApi'
import { useAuthStore } from '../store'
import { ShieldCheck, Loader2, ArrowRight, SkipForward } from 'lucide-react'

/**
 * OnboardingPage.jsx
 * ==================
 * Shown once, right after registration. Skippable on purpose (decision:
 * "skippable, but encouraged" -- not mandatory). Lets the customer pick:
 *   - allergies (from the shared backend list, so they match exactly what
 *     the recommendation engine checks against)
 *   - health conditions (new -- backend-only before this, now has a UI)
 *   - a free-text note (stored as-is, never auto-matched against products --
 *     decision: "store as a note only, no automatic matching")
 *
 * Skipping or submitting both set onboarding_completed = true, so this
 * page is never shown again automatically after the first time.
 */
export default function OnboardingPage() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const navigate = useNavigate()
  const { user, setUser } = useAuthStore()

  const [allergenOptions, setAllergenOptions] = useState([])
  const [conditionOptions, setConditionOptions] = useState([])
  const [selectedAllergies, setSelectedAllergies] = useState([])
  const [selectedConditions, setSelectedConditions] = useState([]) // [{condition_id, severity}]
  const [otherNotes, setOtherNotes] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    Promise.all([allergensApi.list(), healthConditionsApi.list()])
      .then(([allergensRes, conditionsRes]) => {
        if (cancelled) return
        setAllergenOptions(allergensRes.data || [])
        setConditionOptions(conditionsRes.data || [])
      })
      .catch(() => {
        if (!cancelled) toast.error(isAr ? 'فشل تحميل القوائم' : 'Failed to load options')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const toggleAllergy = (name) => {
    setSelectedAllergies(prev =>
      prev.includes(name) ? prev.filter(a => a !== name) : [...prev, name]
    )
  }

  const toggleCondition = (id) => {
    setSelectedConditions(prev => {
      const exists = prev.find(c => c.condition_id === id)
      if (exists) return prev.filter(c => c.condition_id !== id)
      return [...prev, { condition_id: id, severity: 'moderate' }]
    })
  }

  const isConditionSelected = (id) => selectedConditions.some(c => c.condition_id === id)

  const finishWith = async (skip) => {
    setSubmitting(true)
    try {
      const payload = skip
        ? { allergies: [], health_conditions: [], other_notes: null }
        : { allergies: selectedAllergies, health_conditions: selectedConditions, other_notes: otherNotes.trim() || null }
      const { data } = await onboardingApi.submit(payload)
      setUser(data)
      if (!skip) toast.success(isAr ? '✅ تم حفظ ملفك الصحي' : '✅ Health profile saved')
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'حدث خطأ' : 'Something went wrong'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10" style={{ background: 'var(--bg)' }}>
      <div className="w-full max-w-xl">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
            style={{ background: 'var(--primary-light)' }}>
            <ShieldCheck className="w-8 h-8" style={{ color: 'var(--primary)' }} />
          </div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>
            {t('onboardingTitle')}
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text2)' }}>
            {t('onboardingSubtitle')}
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--primary)' }} />
          </div>
        ) : (
          <div className="card space-y-6">

            {/* Allergies */}
            <div>
              <p className="text-sm font-semibold mb-2" style={{ color: 'var(--text2)' }}>
                {t('onboardingAllergiesLabel')}
              </p>
              <div className="flex flex-wrap gap-2">
                {allergenOptions.map(a => {
                  const active = selectedAllergies.includes(a.name)
                  return (
                    <button key={a.id} type="button" onClick={() => toggleAllergy(a.name)}
                      className="px-3 py-1.5 rounded-full text-sm font-medium transition-all"
                      style={active
                        ? { background: 'var(--primary)', color: '#fff', border: '1px solid var(--primary)' }
                        : { border: '1px solid var(--border)', color: 'var(--text2)', background: 'var(--surface2)' }}>
                      {isAr && a.name_ar ? a.name_ar : a.name}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Health conditions */}
            <div>
              <p className="text-sm font-semibold mb-2" style={{ color: 'var(--text2)' }}>
                {t('onboardingConditionsLabel')}
              </p>
              <div className="flex flex-wrap gap-2">
                {conditionOptions.map(c => {
                  const active = isConditionSelected(c.id)
                  return (
                    <button key={c.id} type="button" onClick={() => toggleCondition(c.id)}
                      className="px-3 py-1.5 rounded-full text-sm font-medium transition-all"
                      style={active
                        ? { background: '#c2410c', color: '#fff', border: '1px solid #c2410c' }
                        : { border: '1px solid var(--border)', color: 'var(--text2)', background: 'var(--surface2)' }}>
                      {isAr && c.name_ar ? c.name_ar : c.name}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Free-text note -- stored only, never auto-matched */}
            <div>
              <label className="block text-sm font-semibold mb-1.5" style={{ color: 'var(--text2)' }}>
                {t('onboardingOtherLabel')}
              </label>
              <textarea
                className="input w-full"
                rows={3}
                placeholder={t('onboardingOtherPlaceholder')}
                value={otherNotes}
                onChange={e => setOtherNotes(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={() => finishWith(true)}
                disabled={submitting}
                className="btn-secondary flex-1 flex items-center justify-center gap-2">
                <SkipForward className="w-4 h-4" />
                {t('onboardingSkip')}
              </button>
              <button
                type="button"
                onClick={() => finishWith(false)}
                disabled={submitting}
                className="btn-primary flex-1 flex items-center justify-center gap-2">
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                {t('onboardingContinue')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
