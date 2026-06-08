import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { productApi } from '../hooks/useApi'
import { MapPin, Loader2, Search, X, Package, Store, Navigation } from 'lucide-react'

const SECTIONS = {
  MEAT:    { id:'MEAT',  labelAr:'الملحمة',            labelEn:'Meat & Deli',    color:'#fee2e2', stroke:'#ef4444', text:'#991b1b', dbKey:'F1', icon:'🥩' },
  VEG:     { id:'VEG',   labelAr:'حسبة الخضار',        labelEn:'Vegetables',     color:'#dcfce7', stroke:'#22c55e', text:'#14532d', dbKey:'E1', icon:'🥦' },
  AISLE1:  { id:'A1S1',  labelAr:'أدوات منزلية - أ١', labelEn:'Household A1',   color:'#e0e7ff', stroke:'#6366f1', text:'#3730a3', dbKey:'A1', icon:'🧴' },
  AISLE1B: { id:'A1S2',  labelAr:'أدوات منزلية - أ٢', labelEn:'Household A2',   color:'#e0e7ff', stroke:'#6366f1', text:'#3730a3', dbKey:'A2', icon:'🧴' },
  AISLE2:  { id:'A2S1',  labelAr:'أدوات منزلية - ب١', labelEn:'Household B1',   color:'#fce7f3', stroke:'#ec4899', text:'#9d174d', dbKey:'B1', icon:'🧹' },
  AISLE2B: { id:'A2S2',  labelAr:'أدوات منزلية - ب٢', labelEn:'Household B2',   color:'#fce7f3', stroke:'#ec4899', text:'#9d174d', dbKey:'B2', icon:'🧹' },
  AISLE3:  { id:'A3S1',  labelAr:'أدوات منزلية - ج١', labelEn:'Household C1',   color:'#fef9c3', stroke:'#eab308', text:'#854d0e', dbKey:'C1', icon:'🏠' },
  AISLE3B: { id:'A3S2',  labelAr:'أدوات منزلية - ج٢', labelEn:'Household C2',   color:'#fef9c3', stroke:'#eab308', text:'#854d0e', dbKey:'C2', icon:'🏠' },
  AISLE4:  { id:'A4S1',  labelAr:'أدوات منزلية - د١', labelEn:'Household D1',   color:'#d1fae5', stroke:'#10b981', text:'#065f46', dbKey:'D1', icon:'🪴' },
  AISLE4B: { id:'A4S2',  labelAr:'أدوات منزلية - د٢', labelEn:'Household D2',   color:'#d1fae5', stroke:'#10b981', text:'#065f46', dbKey:'D2', icon:'🪴' },
}

const DB_TO_SHELF = {}
Object.values(SECTIONS).forEach(s => { if (s.dbKey) DB_TO_SHELF[s.dbKey] = s.id })

function ShelfCard({ sec, count, isHighlighted, onClick, isAr }) {
  return (
    <button
      onClick={() => onClick(sec.id)}
      className="relative group flex flex-col items-center justify-center gap-1.5 p-3 rounded-2xl border-2 transition-all duration-200 cursor-pointer w-full h-full min-h-[90px] text-center overflow-hidden"
      style={{
        background: isHighlighted ? `linear-gradient(135deg, ${sec.stroke}22 0%, ${sec.stroke}44 100%)` : sec.color,
        borderColor: isHighlighted ? sec.stroke : `${sec.stroke}60`,
        boxShadow: isHighlighted ? `0 0 0 3px ${sec.stroke}33, 0 8px 24px ${sec.stroke}22` : '0 2px 8px rgba(0,0,0,0.06)',
        transform: isHighlighted ? 'scale(1.03)' : 'scale(1)',
      }}
    >
      {isHighlighted && (
        <span className="absolute inset-0 rounded-2xl border-2 animate-ping opacity-20"
          style={{ borderColor: sec.stroke }} />
      )}
      <span className="text-2xl leading-none">{sec.icon}</span>
      <span className="text-[11px] font-bold leading-tight" style={{ color: sec.text }}>
        {isAr ? sec.labelAr : sec.labelEn}
      </span>
      {count > 0 && (
        <span className="inline-flex items-center justify-center text-[10px] font-bold px-2 py-0.5 rounded-full"
          style={{ background: sec.stroke, color: '#fff' }}>
          {count} {isAr ? 'منتج' : 'items'}
        </span>
      )}
      <span className="absolute top-1.5 end-2 text-[9px] font-bold opacity-40" style={{ color: sec.text }}>
        {sec.dbKey}
      </span>
    </button>
  )
}

export default function MapPage() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const location = useLocation()
  const highlightFromNav = location.state?.highlight
  const selectedRef = useRef(null)

  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [highlightedShelf, setHighlightedShelf] = useState(null)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    productApi.list({ limit: 300 })
      .then(({ data }) => {
        setProducts(data)
        if (highlightFromNav?.section) {
          const shelfId = DB_TO_SHELF[highlightFromNav.section]
          if (shelfId) {
            setHighlightedShelf(shelfId)
            const found = data.find(p => p.id === highlightFromNav.id)
            if (found) setSelectedProduct(found)
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [highlightFromNav?.id])

  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [selectedProduct])

  const handleShelfClick = useCallback((shelfId) => {
    if (highlightedShelf === shelfId) {
      setHighlightedShelf(null)
      setSelectedProduct(null)
    } else {
      setHighlightedShelf(shelfId)
      const sec = Object.values(SECTIONS).find(s => s.id === shelfId)
      if (sec) {
        const first = products.find(p => p.section === sec.dbKey)
        setSelectedProduct(first || null)
      }
    }
  }, [highlightedShelf, products])

  const handleSelectProduct = (p) => {
    setSelectedProduct(p)
    const shelfId = DB_TO_SHELF[p.section]
    if (shelfId) setHighlightedShelf(shelfId)
  }

  const filtered = products.filter(p =>
    !search ||
    p.name?.toLowerCase().includes(search.toLowerCase()) ||
    (p.name_ar || '').includes(search) ||
    (p.section || '').toLowerCase().includes(search.toLowerCase())
  )

  const countByDbKey = {}
  products.forEach(p => {
    if (p.section) countByDbKey[p.section] = (countByDbKey[p.section] || 0) + 1
  })

  const activeSection = highlightedShelf ? Object.values(SECTIONS).find(s => s.id === highlightedShelf) : null
  const sectionProducts = activeSection ? products.filter(p => p.section === activeSection.dbKey) : []

  const AisleDivider = ({ label }) => (
    <div className="flex items-center gap-3 my-1">
      <div className="flex-1 border-t-2 border-dashed" style={{ borderColor: 'var(--border)' }} />
      <span className="text-[10px] font-bold px-2.5 py-1 rounded-full tracking-wider uppercase"
        style={{ background: 'var(--surface2)', color: 'var(--text3)', border: '1px solid var(--border)' }}>
        {label}
      </span>
      <div className="flex-1 border-t-2 border-dashed" style={{ borderColor: 'var(--border)' }} />
    </div>
  )

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-2xl flex items-center justify-center shadow-lg"
          style={{ background: 'linear-gradient(135deg, var(--primary), #6366f1)', color: '#fff' }}>
          <Store className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-extrabold" style={{ color: 'var(--text)' }}>
            {isAr ? 'خريطة المتجر' : 'Store Map'}
          </h1>
          <p className="text-xs" style={{ color: 'var(--text3)' }}>
            {isAr ? 'انقر على قسم لعرض المنتجات' : 'Click a section to view products'}
          </p>
        </div>
      </div>

      {/* Highlight banner */}
      {highlightFromNav && selectedProduct && activeSection && (
        <div className="flex items-center gap-3 p-3 rounded-2xl border-2 text-sm font-semibold"
          style={{ background: activeSection.color, borderColor: activeSection.stroke, color: activeSection.text }}>
          <Navigation className="w-4 h-4 shrink-0" />
          <span>
            {isAr ? 'تم تحديد موقع' : 'Located'}{' '}
            <strong>{selectedProduct.name_ar || selectedProduct.name}</strong>
            {' — '}{isAr ? 'القسم' : 'Section'} {selectedProduct.section}
          </span>
        </div>
      )}

      <div className="flex flex-col xl:flex-row gap-5">
        {/* Map */}
        <div className="flex-1 min-w-0">
          <div className="card p-5" style={{ background: 'var(--surface)' }}>
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--primary)' }} />
              </div>
            ) : (
              <div className="space-y-3">
                {/* Row 0: Meat + Special + Veg */}
                <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(5,1fr)' }}>
                  <div className="col-span-2">
                    <ShelfCard sec={SECTIONS.MEAT} count={countByDbKey[SECTIONS.MEAT.dbKey]||0}
                      isHighlighted={highlightedShelf===SECTIONS.MEAT.id} onClick={handleShelfClick} isAr={isAr} />
                  </div>
                  <div className="flex items-center justify-center">
                    <div className="rounded-2xl border-2 border-dashed w-full h-full min-h-[90px] flex flex-col items-center justify-center gap-1 p-2"
                      style={{ borderColor: 'var(--border)', background: 'var(--surface2)' }}>
                      <span className="text-xl">🏪</span>
                      <span className="text-[10px] font-bold text-center" style={{ color: 'var(--text3)' }}>
                        {isAr ? 'قسم خاص' : 'Special'}
                      </span>
                    </div>
                  </div>
                  <div className="col-span-2">
                    <ShelfCard sec={SECTIONS.VEG} count={countByDbKey[SECTIONS.VEG.dbKey]||0}
                      isHighlighted={highlightedShelf===SECTIONS.VEG.id} onClick={handleShelfClick} isAr={isAr} />
                  </div>
                </div>

                <AisleDivider label={isAr ? 'ممر ١' : 'Aisle 1'} />

                {/* Row 1 */}
                <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(5,1fr)' }}>
                  <ShelfCard sec={SECTIONS.AISLE1}  count={countByDbKey[SECTIONS.AISLE1.dbKey]||0}  isHighlighted={highlightedShelf===SECTIONS.AISLE1.id}  onClick={handleShelfClick} isAr={isAr} />
                  <ShelfCard sec={SECTIONS.AISLE1B} count={countByDbKey[SECTIONS.AISLE1B.dbKey]||0} isHighlighted={highlightedShelf===SECTIONS.AISLE1B.id} onClick={handleShelfClick} isAr={isAr} />
                  <div className="flex items-center justify-center">
                    <div className="w-0.5 h-full min-h-[60px] rounded-full" style={{ background: 'var(--border)' }} />
                  </div>
                  <ShelfCard sec={SECTIONS.AISLE2}  count={countByDbKey[SECTIONS.AISLE2.dbKey]||0}  isHighlighted={highlightedShelf===SECTIONS.AISLE2.id}  onClick={handleShelfClick} isAr={isAr} />
                  <ShelfCard sec={SECTIONS.AISLE2B} count={countByDbKey[SECTIONS.AISLE2B.dbKey]||0} isHighlighted={highlightedShelf===SECTIONS.AISLE2B.id} onClick={handleShelfClick} isAr={isAr} />
                </div>

                <AisleDivider label={isAr ? 'ممر ٢' : 'Aisle 2'} />

                {/* Row 2 */}
                <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(5,1fr)' }}>
                  <ShelfCard sec={SECTIONS.AISLE3}  count={countByDbKey[SECTIONS.AISLE3.dbKey]||0}  isHighlighted={highlightedShelf===SECTIONS.AISLE3.id}  onClick={handleShelfClick} isAr={isAr} />
                  <ShelfCard sec={SECTIONS.AISLE3B} count={countByDbKey[SECTIONS.AISLE3B.dbKey]||0} isHighlighted={highlightedShelf===SECTIONS.AISLE3B.id} onClick={handleShelfClick} isAr={isAr} />
                  <div className="flex items-center justify-center">
                    <div className="w-0.5 h-full min-h-[60px] rounded-full" style={{ background: 'var(--border)' }} />
                  </div>
                  <ShelfCard sec={SECTIONS.AISLE4}  count={countByDbKey[SECTIONS.AISLE4.dbKey]||0}  isHighlighted={highlightedShelf===SECTIONS.AISLE4.id}  onClick={handleShelfClick} isAr={isAr} />
                  <ShelfCard sec={SECTIONS.AISLE4B} count={countByDbKey[SECTIONS.AISLE4B.dbKey]||0} isHighlighted={highlightedShelf===SECTIONS.AISLE4B.id} onClick={handleShelfClick} isAr={isAr} />
                </div>

                <AisleDivider label={isAr ? 'ممر ٣' : 'Aisle 3'} />

                {/* Bottom: Cashier / Exit / Entrance */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-2xl border-2 min-h-[72px]"
                    style={{ background: 'var(--surface2)', borderColor: 'var(--border)' }}>
                    <span className="text-xl">🖥️</span>
                    <span className="text-xs font-bold" style={{ color: 'var(--text2)' }}>{isAr ? 'كاشير' : 'Cashier'}</span>
                  </div>
                  <div className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-2xl border-2 border-dashed min-h-[72px]"
                    style={{ background: '#fef2f2', borderColor: '#fca5a5' }}>
                    <span className="text-xl">🚪</span>
                    <span className="text-xs font-bold" style={{ color: '#dc2626' }}>{isAr ? 'مخرج' : 'Exit'}</span>
                    <span className="text-[10px]" style={{ color: '#ef444480' }}>← →</span>
                  </div>
                  <div className="flex flex-col items-center justify-center gap-1.5 p-3 rounded-2xl border-2 min-h-[72px]"
                    style={{ background: '#f0fdf4', borderColor: '#86efac' }}>
                    <span className="text-xl">🏬</span>
                    <span className="text-xs font-bold" style={{ color: '#15803d' }}>{isAr ? 'مدخل' : 'Entrance'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Legend */}
          <div className="mt-3 card p-4">
            <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: 'var(--text3)' }}>
              {isAr ? 'دليل الأقسام' : 'Section Guide'}
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.values(SECTIONS).map(sec => (
                <button key={sec.id} onClick={() => handleShelfClick(sec.id)}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-all duration-200 font-semibold border"
                  style={{
                    background: highlightedShelf === sec.id ? sec.stroke : sec.color,
                    borderColor: sec.stroke,
                    color: highlightedShelf === sec.id ? '#fff' : sec.text,
                    boxShadow: highlightedShelf === sec.id ? `0 2px 8px ${sec.stroke}44` : 'none',
                    transform: highlightedShelf === sec.id ? 'scale(1.05)' : 'scale(1)',
                  }}>
                  <span>{sec.icon}</span> {sec.dbKey}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="xl:w-72 space-y-4">
          {activeSection && (
            <div className="card border-2" style={{ borderColor: activeSection.stroke, background: activeSection.color + '55' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{activeSection.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-sm truncate" style={{ color: activeSection.text }}>
                    {isAr ? activeSection.labelAr : activeSection.labelEn}
                  </p>
                  <p className="text-[10px] opacity-60 font-medium" style={{ color: activeSection.text }}>
                    {isAr ? 'القسم' : 'Section'} {activeSection.dbKey}
                  </p>
                </div>
                <span className="shrink-0 text-xs font-extrabold px-2.5 py-1 rounded-full"
                  style={{ background: activeSection.stroke, color: '#fff' }}>
                  {sectionProducts.length}
                </span>
              </div>
              <div className="space-y-1.5 max-h-52 overflow-y-auto">
                {sectionProducts.length === 0 ? (
                  <div className="flex flex-col items-center py-4 gap-2">
                    <Package className="w-8 h-8 opacity-20" style={{ color: activeSection.text }} />
                    <p className="text-xs text-center opacity-60" style={{ color: activeSection.text }}>
                      {isAr ? 'لا توجد منتجات' : 'No products'}
                    </p>
                  </div>
                ) : sectionProducts.map(p => (
                  <button key={p.id}
                    ref={selectedProduct?.id === p.id ? selectedRef : null}
                    onClick={() => handleSelectProduct(p)}
                    className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs transition-all duration-150"
                    style={{
                      background: selectedProduct?.id === p.id ? activeSection.stroke : 'rgba(255,255,255,0.65)',
                      color: selectedProduct?.id === p.id ? '#fff' : activeSection.text,
                      border: `1.5px solid ${selectedProduct?.id === p.id ? activeSection.stroke : activeSection.stroke + '30'}`,
                    }}>
                    <span className="truncate font-semibold">{p.name_ar || p.name}</span>
                    <span className="shrink-0 font-extrabold">${p.price?.toFixed(2)}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search */}
          <div className="card">
            <div className="relative mb-3">
              <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text3)' }} />
              <input className="input ps-9 text-sm"
                placeholder={isAr ? 'ابحث عن منتج...' : 'Search product...'}
                value={search} onChange={e => setSearch(e.target.value)} />
              {search && (
                <button onClick={() => setSearch('')} className="absolute end-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text3)' }}>
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <p className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: 'var(--text3)' }}>
              {search ? `${isAr ? 'النتائج' : 'Results'} (${filtered.length})` : (isAr ? 'جميع المنتجات' : 'All Products')}
            </p>
            <div className="space-y-1 max-h-72 overflow-y-auto">
              {filtered.slice(0, 40).map(p => {
                const shelfId = DB_TO_SHELF[p.section]
                const sec = shelfId ? Object.values(SECTIONS).find(s => s.id === shelfId) : null
                const isSelected = selectedProduct?.id === p.id
                return (
                  <button key={p.id}
                    ref={isSelected ? selectedRef : null}
                    onClick={() => handleSelectProduct(p)}
                    className="w-full text-start px-3 py-2 rounded-xl text-sm transition-all duration-150 flex items-center justify-between gap-2"
                    style={{
                      background: isSelected ? (sec?.color || 'var(--surface2)') : 'transparent',
                      border: isSelected ? `1.5px solid ${sec?.stroke || 'var(--border)'}` : '1.5px solid transparent',
                      color: 'var(--text)',
                    }}>
                    <div className="flex items-center gap-2 min-w-0">
                      {sec && <span className="text-sm shrink-0">{sec.icon}</span>}
                      <span className="truncate text-xs" style={{ fontWeight: isSelected ? 700 : 400 }}>
                        {p.name_ar || p.name}
                      </span>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-md shrink-0 font-bold"
                      style={{ background: sec?.color || 'var(--surface2)', color: sec?.text || 'var(--text3)' }}>
                      {p.section}
                    </span>
                  </button>
                )
              })}
              {filtered.length > 40 && (
                <p className="text-xs text-center py-2" style={{ color: 'var(--text3)' }}>
                  {isAr ? `+${filtered.length - 40} منتج آخر` : `+${filtered.length - 40} more`}
                </p>
              )}
            </div>
          </div>

          {!highlightedShelf && !search && (
            <div className="text-center py-4 space-y-2">
              <MapPin className="w-8 h-8 mx-auto opacity-20" style={{ color: 'var(--text3)' }} />
              <p className="text-xs" style={{ color: 'var(--text3)' }}>
                {isAr ? 'انقر على رف لعرض المنتجات' : 'Click a shelf to view products'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
