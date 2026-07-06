import React, { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Tag, Clock, Flame, Star, Sparkles, ShoppingBag,
  Filter, ChevronRight, Zap, Calendar, Store, Trophy,
  TrendingDown, Timer, BadgePercent, Loader2, PackageX,
} from 'lucide-react'
import { productApi, sessionApi } from '../hooks/useApi'
import { useSessionStore } from '../store'
import { formatPrice } from '../utils/format'
import toast from 'react-hot-toast'

/**
 * OffersPage.jsx
 * ==============
 * Was previously built entirely on hardcoded mock data (see the old
 * data/offersData.js, which said "Replace this with an API call" in its
 * own comment). Now pulls real offers from GET /api/products/offers --
 * actual products the store owner flagged is_on_offer=True via
 * AdminProducts.jsx, with a real old_price and optional expiry.
 *
 * Categories like "daily/monthly/in-store" from the mock data don't
 * correspond to anything in the real Product model, so filtering is
 * simplified to what's actually true of real data: all offers vs. the
 * ones with the steepest discount ("Best Deals").
 */

function useCountdown(isoDate) {
  const [timeLeft, setTimeLeft] = useState('')

  useEffect(() => {
    if (!isoDate) { setTimeLeft(null); return }
    const update = () => {
      const diff = new Date(isoDate) - Date.now()
      if (diff <= 0) { setTimeLeft('Expired'); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      if (h > 24) {
        const d = Math.floor(h / 24)
        setTimeLeft(`${d}d ${h % 24}h`)
      } else {
        setTimeLeft(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`)
      }
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [isoDate])

  return timeLeft
}

function computeDiscount(oldPrice, newPrice) {
  if (!oldPrice || oldPrice <= newPrice) return 0
  return Math.round(((oldPrice - newPrice) / oldPrice) * 100)
}

function OfferCard({ product, highlight, isAr, onAddToCart }) {
  const countdown = useCountdown(product.offer_expires_at)
  const discount = computeDiscount(product.old_price, product.price)
  const isShortExpiry = product.offer_expires_at
    ? new Date(product.offer_expires_at) - Date.now() < 12 * 3600 * 1000
    : false

  return (
    <div
      className={`group relative rounded-2xl overflow-hidden transition-all duration-300 cursor-pointer
        ${highlight
          ? 'ring-2 ring-yellow-400 ring-offset-2 shadow-xl hover:shadow-2xl hover:-translate-y-1.5'
          : 'shadow-sm hover:shadow-xl hover:-translate-y-1'
        }
      `}
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="relative h-44 overflow-hidden" style={{ background: 'var(--surface2)' }}>
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <ShoppingBag className="w-12 h-12" style={{ color: 'var(--text3)', opacity: 0.3 }} />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />

        {discount > 0 && (
          <div className="absolute top-3 start-3 bg-red-500 text-white text-xs font-extrabold px-2.5 py-1 rounded-full shadow-lg flex items-center gap-1">
            <BadgePercent className="w-3 h-3" />
            {discount}% OFF
          </div>
        )}

        {highlight && (
          <div className="absolute bottom-3 start-3 flex items-center gap-1 bg-yellow-400 text-yellow-900 text-xs font-extrabold px-2.5 py-1 rounded-full shadow-lg">
            <Trophy className="w-3 h-3" />
            {isAr ? 'أفضل عرض' : 'Best Deal'}
          </div>
        )}
      </div>

      <div className="p-4">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text3)' }}>
          {product.category}
        </span>

        <h3 className="font-bold mt-1 leading-snug text-sm" style={{ color: 'var(--text)' }}>
          {isAr && product.name_ar ? product.name_ar : product.name}
        </h3>

        <div className="flex items-baseline gap-2 mt-3">
          <span className="text-xl font-extrabold" style={{ color: 'var(--primary)' }}>
            {formatPrice(product.price)}
          </span>
          {product.old_price > product.price && (
            <span className="text-sm line-through" style={{ color: 'var(--text3)' }}>
              {formatPrice(product.old_price)}
            </span>
          )}
        </div>

        {product.old_price > product.price && (
          <div className="flex items-center gap-1 mt-1">
            <TrendingDown className="w-3 h-3 text-emerald-500" />
            <span className="text-xs text-emerald-600 font-semibold">
              {isAr ? 'وفّر' : 'Save'} {formatPrice(product.old_price - product.price)}
            </span>
          </div>
        )}

        <div className={`flex items-center gap-1.5 mt-3 pt-3 text-xs font-semibold ${isShortExpiry ? 'text-red-500' : ''}`}
          style={{ color: !isShortExpiry ? 'var(--text2)' : undefined, borderTop: '1px solid var(--border)' }}
        >
          {countdown ? (
            <>
              <Timer className="w-3.5 h-3.5" />
              {isShortExpiry ? `⚡ ${isAr ? 'ينتهي خلال' : 'Ends in'} ${countdown}` : `${isAr ? 'ينتهي خلال' : 'Ends in'} ${countdown}`}
            </>
          ) : (
            <span style={{ color: 'var(--text3)' }}>{isAr ? 'بدون تاريخ انتهاء' : 'No expiry'}</span>
          )}
          <span className="ms-auto text-xs" style={{ color: 'var(--text3)' }}>
            {product.quantity} {isAr ? 'متبقي' : 'left'}
          </span>
        </div>
      </div>

      <div
        onClick={() => onAddToCart(product)}
        className="absolute inset-0 flex items-end justify-center pb-5 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
      >
        <div className="bg-white/95 backdrop-blur-sm text-gray-800 text-xs font-bold px-4 py-2 rounded-full shadow-lg flex items-center gap-2">
          <ShoppingBag className="w-3.5 h-3.5" />
          {isAr ? 'أضف للسلة' : 'Add to Cart'}
          <ChevronRight className="w-3 h-3" />
        </div>
      </div>
    </div>
  )
}

function FilterPill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
        active ? 'text-white shadow-md scale-105' : 'hover:scale-[1.03]'
      }`}
      style={active
        ? { background: 'var(--primary)', boxShadow: '0 4px 14px rgba(37,99,235,0.35)' }
        : { background: 'var(--surface)', color: 'var(--text2)', border: '1.5px solid var(--border)' }
      }
    >
      {children}
    </button>
  )
}

export default function OffersPage() {
  const { i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const { sessionId, setSession } = useSessionStore()
  const [activeFilter, setActiveFilter] = useState('all')
  const [offerProducts, setOfferProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    productApi.offers()
      .then(({ data }) => setOfferProducts(data))
      .catch(() => toast.error(isAr ? 'فشل تحميل العروض' : 'Failed to load offers'))
      .finally(() => setLoading(false))
  }, [])

  const handleAddToCart = async (product) => {
    if (!product.barcode) {
      toast.error(isAr ? 'هذا المنتج بدون باركود' : 'This product has no barcode')
      return
    }
    try {
      // If no active session yet (customer came directly to Offers page
      // without going through the POS page first), start one automatically.
      // Same logic as POSPage.jsx's initSession.
      let activeSessionId = sessionId
      if (!activeSessionId) {
        try {
          const { data: existing } = await sessionApi.getActive()
          if (existing?.id) {
            setSession(existing)
            activeSessionId = existing.id
          }
        } catch {}

        if (!activeSessionId) {
          const { data: newSession } = await sessionApi.start(null)
          setSession(newSession)
          activeSessionId = newSession.id
        }
      }

      await sessionApi.scanProduct(activeSessionId, product.barcode)
      toast.success(`${isAr && product.name_ar ? product.name_ar : product.name} ✓`, { icon: '🛒' })
    } catch (err) {
      toast.error(err.response?.data?.detail || (isAr ? 'فشل الإضافة' : 'Failed to add'))
    }
  }

  const withDiscount = useMemo(
    () => offerProducts.map(p => ({ ...p, _discount: computeDiscount(p.old_price, p.price) })),
    [offerProducts]
  )

  const bestDeals = useMemo(() => {
    const sorted = [...withDiscount].sort((a, b) => b._discount - a._discount)
    return sorted.slice(0, Math.min(4, Math.ceil(sorted.length * 0.25) || sorted.length))
  }, [withDiscount])

  const filtered = activeFilter === 'best' ? bestDeals : withDiscount

  const filters = [
    { key: 'all',  label: isAr ? '✨ كل العروض' : '✨ All Offers' },
    { key: 'best', label: isAr ? '🏆 أفضل العروض' : '🏆 Best Deals' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--primary)' }} />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">

      <div
        className="relative overflow-hidden rounded-3xl mb-8 p-8"
        style={{ background: 'linear-gradient(135deg, var(--primary) 0%, #7c3aed 60%, #db2777 100%)' }}
      >
        <div className="absolute -top-10 -end-10 w-52 h-52 bg-white/10 rounded-full" />
        <div className="absolute -bottom-8 -start-8 w-40 h-40 bg-white/10 rounded-full" />
        <div className="absolute top-4 end-28 w-20 h-20 bg-white/10 rounded-full" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-yellow-300" />
            <span className="text-yellow-300 text-sm font-bold uppercase tracking-widest">
              {isAr ? 'حصري' : 'Exclusive'}
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 leading-tight">
            {isAr ? 'أفضل عروض اليوم' : "Today's Best Offers"}
          </h1>
          <p className="text-white/70 text-sm max-w-md">
            {isAr
              ? 'عروض مختارة من متجرنا — بعضها ينتهي قريباً!'
              : "Handpicked promotions from our store. Don't miss out — some expire soon!"}
          </p>
          <div className="flex items-center gap-3 mt-5">
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-semibold">
              <Zap className="w-4 h-4 text-yellow-300" />
              {bestDeals.length} {isAr ? 'أفضل عروض' : 'Best Deals'}
            </div>
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-semibold">
              <Tag className="w-4 h-4 text-pink-300" />
              {offerProducts.length} {isAr ? 'عرض إجمالي' : 'Total Offers'}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-1 scrollbar-none">
        <Filter className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text3)' }} />
        {filters.map((f) => (
          <FilterPill key={f.key} active={activeFilter === f.key} onClick={() => setActiveFilter(f.key)}>
            {f.label}
          </FilterPill>
        ))}
        <span className="ms-auto text-xs flex-shrink-0 font-semibold" style={{ color: 'var(--text3)' }}>
          {filtered.length} {isAr ? 'عرض' : 'offers'}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-20">
          <PackageX className="w-14 h-14 mx-auto mb-4 opacity-20" />
          <p className="font-bold text-lg" style={{ color: 'var(--text2)' }}>
            {isAr ? 'لا توجد عروض حالياً' : 'No offers right now'}
          </p>
          <p className="text-sm mt-1" style={{ color: 'var(--text3)' }}>
            {isAr ? 'تحقق مرة أخرى قريباً!' : 'Check back soon for new deals!'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((product) => (
            <OfferCard
              key={product.id}
              product={product}
              isAr={isAr}
              highlight={bestDeals.some(b => b.id === product.id)}
              onAddToCart={handleAddToCart}
            />
          ))}
        </div>
      )}
    </div>
  )
}
