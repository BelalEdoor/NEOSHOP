import React, { useState, useMemo } from 'react'
import {
  Tag, Clock, Flame, Star, Sparkles, ShoppingBag,
  Filter, ChevronRight, Zap, Calendar, Store, Trophy,
  TrendingDown, Timer, BadgePercent,
} from 'lucide-react'
import { offers, OFFER_TYPES, getBestDeals } from '../data/offersData'

// ── Countdown hook ───────────────────────────────────────────────────────────
function useCountdown(isoDate) {
  const [timeLeft, setTimeLeft] = React.useState('')

  React.useEffect(() => {
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

// ── Badge color map ───────────────────────────────────────────────────────────
const BADGE_STYLES = {
  red:    { bg: 'bg-red-500',    text: 'text-white' },
  orange: { bg: 'bg-orange-500', text: 'text-white' },
  blue:   { bg: 'bg-blue-500',   text: 'text-white' },
  purple: { bg: 'bg-purple-500', text: 'text-white' },
  green:  { bg: 'bg-emerald-500',text: 'text-white' },
  yellow: { bg: 'bg-yellow-400', text: 'text-gray-900' },
  indigo: { bg: 'bg-indigo-500', text: 'text-white' },
  cyan:   { bg: 'bg-cyan-500',   text: 'text-white' },
}

// ── Individual Offer Card ─────────────────────────────────────────────────────
function OfferCard({ offer, highlight }) {
  const countdown = useCountdown(offer.expiresAt)
  const badge = BADGE_STYLES[offer.badgeColor] || BADGE_STYLES.blue
  const isShortExpiry = new Date(offer.expiresAt) - Date.now() < 12 * 3600 * 1000

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
      {/* Image */}
      <div className="relative h-44 overflow-hidden">
        <img
          src={offer.image}
          alt={offer.title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />
        {/* Overlay gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />

        {/* Discount badge */}
        {offer.discount && (
          <div className={`absolute top-3 start-3 ${badge.bg} ${badge.text} text-xs font-extrabold px-2.5 py-1 rounded-full shadow-lg flex items-center gap-1`}>
            <BadgePercent className="w-3 h-3" />
            {offer.discount}% OFF
          </div>
        )}

        {/* Promo tag */}
        {offer.promoTag && (
          <div className="absolute top-3 end-3 bg-white/90 backdrop-blur-sm text-gray-800 text-xs font-bold px-2.5 py-1 rounded-full shadow">
            {offer.promoTag}
          </div>
        )}

        {/* Best deal crown */}
        {offer.isBestDeal && (
          <div className="absolute bottom-3 start-3 flex items-center gap-1 bg-yellow-400 text-yellow-900 text-xs font-extrabold px-2.5 py-1 rounded-full shadow-lg">
            <Trophy className="w-3 h-3" />
            Best Deal
          </div>
        )}

        {/* Loyalty tag */}
        {offer.isLoyalty && (
          <div className="absolute bottom-3 start-3 flex items-center gap-1 bg-indigo-500 text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-lg">
            <Star className="w-3 h-3" />
            Loyalty Reward
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text3)' }}>
          {offer.category}
        </span>

        <h3 className="font-bold mt-1 leading-snug text-sm" style={{ color: 'var(--text)' }}>
          {offer.title}
        </h3>
        <p className="text-xs mt-1 line-clamp-1" style={{ color: 'var(--text2)' }}>
          {offer.description}
        </p>

        {/* Pricing */}
        {offer.newPrice !== null ? (
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-xl font-extrabold" style={{ color: 'var(--primary)' }}>
              ${offer.newPrice.toFixed(2)}
            </span>
            {offer.oldPrice && (
              <span className="text-sm line-through" style={{ color: 'var(--text3)' }}>
                ${offer.oldPrice.toFixed(2)}
              </span>
            )}
          </div>
        ) : (
          <div className="mt-3">
            <span className="text-sm font-bold" style={{ color: 'var(--primary)' }}>
              Special Promotion
            </span>
          </div>
        )}

        {/* Savings callout */}
        {offer.oldPrice && offer.newPrice && (
          <div className="flex items-center gap-1 mt-1">
            <TrendingDown className="w-3 h-3 text-emerald-500" />
            <span className="text-xs text-emerald-600 font-semibold">
              Save ${(offer.oldPrice - offer.newPrice).toFixed(2)}
            </span>
          </div>
        )}

        {/* Countdown */}
        <div className={`flex items-center gap-1.5 mt-3 pt-3 text-xs font-semibold ${isShortExpiry ? 'text-red-500' : ''}`}
          style={!isShortExpiry ? { color: 'var(--text2)', borderTop: '1px solid var(--border)' } : { borderTop: '1px solid var(--border)' }}
        >
          <Timer className="w-3.5 h-3.5" />
          {isShortExpiry ? `⚡ Ends in ${countdown}` : `Ends in ${countdown}`}
          {offer.stock !== null && (
            <span className="ms-auto text-xs" style={{ color: 'var(--text3)' }}>
              {offer.stock} left
            </span>
          )}
        </div>
      </div>

      {/* Hover CTA overlay */}
      <div className="absolute inset-0 flex items-end justify-center pb-5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
        <div className="bg-white/95 backdrop-blur-sm text-gray-800 text-xs font-bold px-4 py-2 rounded-full shadow-lg flex items-center gap-2">
          <ShoppingBag className="w-3.5 h-3.5" />
          View Offer
          <ChevronRight className="w-3 h-3" />
        </div>
      </div>
    </div>
  )
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ icon: Icon, title, subtitle, iconColor, children, accentClass }) {
  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-5">
        <div className={`w-10 h-10 rounded-2xl flex items-center justify-center ${accentClass}`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <div>
          <h2 className="font-extrabold text-lg leading-tight" style={{ color: 'var(--text)' }}>{title}</h2>
          <p className="text-xs" style={{ color: 'var(--text2)' }}>{subtitle}</p>
        </div>
      </div>
      {children}
    </section>
  )
}

// ── Filter pill component ─────────────────────────────────────────────────────
function FilterPill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
        active
          ? 'text-white shadow-md scale-105'
          : 'hover:scale-[1.03]'
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

// ── Main OffersPage ───────────────────────────────────────────────────────────
export default function OffersPage() {
  const [activeFilter, setActiveFilter] = useState('all')

  const filters = [
    { key: 'all',     label: '✨ All Offers' },
    { key: 'daily',   label: '⚡ Daily' },
    { key: 'monthly', label: '📅 Monthly' },
    { key: 'instore', label: '🏪 In-Store' },
    { key: 'best',    label: '🏆 Best Deals' },
  ]

  const filteredOffers = useMemo(() => {
    if (activeFilter === 'all')     return offers
    if (activeFilter === 'best')    return getBestDeals()
    return offers.filter((o) => o.type === activeFilter)
  }, [activeFilter])

  const daily   = filteredOffers.filter((o) => o.type === OFFER_TYPES.DAILY)
  const monthly = filteredOffers.filter((o) => o.type === OFFER_TYPES.MONTHLY)
  const instore = filteredOffers.filter((o) => o.type === OFFER_TYPES.INSTORE)
  const showAll = activeFilter === 'all' || activeFilter === 'best'

  const bestDeals = getBestDeals()

  return (
    <div className="max-w-6xl mx-auto">

      {/* ── Hero Header ───────────────────────────────────────────────────── */}
      <div
        className="relative overflow-hidden rounded-3xl mb-8 p-8"
        style={{
          background: 'linear-gradient(135deg, var(--primary) 0%, #7c3aed 60%, #db2777 100%)',
        }}
      >
        {/* Decorative circles */}
        <div className="absolute -top-10 -end-10 w-52 h-52 bg-white/10 rounded-full" />
        <div className="absolute -bottom-8 -start-8 w-40 h-40 bg-white/10 rounded-full" />
        <div className="absolute top-4 end-28 w-20 h-20 bg-white/10 rounded-full" />

        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-yellow-300" />
            <span className="text-yellow-300 text-sm font-bold uppercase tracking-widest">Exclusive</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 leading-tight">
            Today's Best Offers
          </h1>
          <p className="text-white/70 text-sm max-w-md">
            Handpicked daily, monthly & in-store promotions. Don't miss out — some expire soon!
          </p>
          <div className="flex items-center gap-3 mt-5">
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-semibold">
              <Zap className="w-4 h-4 text-yellow-300" />
              {bestDeals.length} Best Deals
            </div>
            <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-semibold">
              <Tag className="w-4 h-4 text-pink-300" />
              {offers.length} Total Offers
            </div>
          </div>
        </div>
      </div>

      {/* ── Filter Bar ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-1 scrollbar-none">
        <Filter className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text3)' }} />
        {filters.map((f) => (
          <FilterPill key={f.key} active={activeFilter === f.key} onClick={() => setActiveFilter(f.key)}>
            {f.label}
          </FilterPill>
        ))}
        <span className="ms-auto text-xs flex-shrink-0 font-semibold" style={{ color: 'var(--text3)' }}>
          {filteredOffers.length} offers
        </span>
      </div>

      {/* ── Best Deals Highlight Strip (shown when filter = all or best) ── */}
      {(activeFilter === 'all' || activeFilter === 'best') && bestDeals.length > 0 && (
        <div className="mb-10 rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, #fef9c3 0%, #fde68a 100%)', border: '1.5px solid #fcd34d' }}>
          <div className="flex items-center gap-2 mb-4">
            <Trophy className="w-5 h-5 text-yellow-600" />
            <span className="font-extrabold text-yellow-800 text-base">🔥 Best Deals Right Now</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {bestDeals.map((offer) => (
              <OfferCard key={offer.id} offer={offer} highlight />
            ))}
          </div>
        </div>
      )}

      {/* ── Daily Offers ──────────────────────────────────────────────────── */}
      {(showAll ? daily.length > 0 : activeFilter === 'daily' && filteredOffers.length > 0) && (
        <Section
          icon={Flame}
          title="Daily Offers"
          subtitle="Flash deals refreshed every 24 hours"
          iconColor="text-red-500"
          accentClass="bg-red-50"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {(showAll ? daily : filteredOffers).map((offer) => (
              <OfferCard key={offer.id} offer={offer} highlight={offer.isBestDeal} />
            ))}
          </div>
        </Section>
      )}

      {/* ── Monthly Offers ────────────────────────────────────────────────── */}
      {(showAll ? monthly.length > 0 : activeFilter === 'monthly' && filteredOffers.length > 0) && (
        <Section
          icon={Calendar}
          title="Monthly Promotions"
          subtitle="Long-lasting value throughout the month"
          iconColor="text-blue-500"
          accentClass="bg-blue-50"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {(showAll ? monthly : filteredOffers).map((offer) => (
              <OfferCard key={offer.id} offer={offer} highlight={offer.isBestDeal} />
            ))}
          </div>
        </Section>
      )}

      {/* ── In-Store Promotions ───────────────────────────────────────────── */}
      {(showAll ? instore.length > 0 : activeFilter === 'instore' && filteredOffers.length > 0) && (
        <Section
          icon={Store}
          title="In-Store Promotions"
          subtitle="Exclusive deals available in our physical stores"
          iconColor="text-emerald-500"
          accentClass="bg-emerald-50"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {(showAll ? instore : filteredOffers).map((offer) => (
              <OfferCard key={offer.id} offer={offer} highlight={offer.isBestDeal} />
            ))}
          </div>
        </Section>
      )}

      {/* Empty state */}
      {filteredOffers.length === 0 && (
        <div className="text-center py-20">
          <Tag className="w-14 h-14 mx-auto mb-4 opacity-20" />
          <p className="font-bold text-lg" style={{ color: 'var(--text2)' }}>No offers found</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text3)' }}>Check back soon for new deals!</p>
        </div>
      )}
    </div>
  )
}
