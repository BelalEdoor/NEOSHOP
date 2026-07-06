import React from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle, MapPin, X, ArrowRight } from 'lucide-react'
import { formatPrice } from '../../utils/format'

export default function AllergenModal({ result, product, onClose, onContinue }) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  if (!result) return null

  const isSafe = result.is_safe

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className={`p-5 ${isSafe ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {isSafe ? (
                <CheckCircle className="w-8 h-8 text-green-500 shrink-0" />
              ) : (
                <AlertTriangle className="w-8 h-8 text-red-500 shrink-0" />
              )}
              <div>
                <h2 className={`text-lg font-bold ${isSafe ? 'text-green-800' : 'text-red-800'}`}>
                  {isSafe ? t('safeProduct') : t('unsafeProduct')}
                </h2>
                <p className="text-sm text-gray-600 mt-0.5">{product?.name}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-black/10 transition-colors">
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-4">
          {/* Warning message */}
          {result.warning_message && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-700">
              {result.warning_message}
            </div>
          )}

          {/* Matched allergens */}
          {result.matched_allergens?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Detected Allergens</p>
              <div className="flex flex-wrap gap-2">
                {result.matched_allergens.map((a) => (
                  <span key={a} className="px-2.5 py-1 rounded-full bg-red-100 text-red-700 text-sm font-medium">
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Suggestions */}
          {result.suggestions?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                {t('suggestions')}
              </p>
              <div className="space-y-2">
                {result.suggestions.map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3 rounded-xl bg-green-50 border border-green-100">
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{s.name}</p>
                      <p className="text-xs text-gray-500">{s.brand} · {formatPrice(s.price)}</p>
                    </div>
                    <span className="text-xs bg-green-200 text-green-800 px-2 py-0.5 rounded-full">Safe</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-2 pt-2">
            <button
              onClick={() => { navigate('/map', { state: { highlight: product } }); onClose() }}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <MapPin className="w-4 h-4" />
              {t('viewOnMap')}
            </button>

            {!isSafe && (
              <button
                onClick={() => { onContinue(); onClose() }}
                className="btn-danger flex items-center justify-center gap-2"
              >
                {t('continueAnyway')}
                <ArrowRight className="w-4 h-4" />
              </button>
            )}

            {isSafe && (
              <button
                onClick={() => { onContinue(); onClose() }}
                className="btn-primary flex items-center justify-center gap-2"
              >
                {t('addToCart')}
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
