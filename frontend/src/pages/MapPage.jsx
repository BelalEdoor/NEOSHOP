import React, { useState, useEffect, useCallback, useRef, useLayoutEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { productApi } from '../hooks/useApi'
import { formatPrice } from '../utils/format'
import { Loader2, Search, X, Package, Store, Radio, MapPin, Navigation, ArrowUp, ArrowDown } from 'lucide-react'
import api from '../hooks/useApi'

// كل قسم عبارة عن مجموعة "أعمدة"، كل عمود فيه أرففه المكدّسة عمودياً.
// A وC عمود واحد بـ 3 أرفف (كالسابق). B الآن عمودان جنباً إلى جنب، كل
// عمود بحاله 3 أرفف (تماماً متل A وC) — B1 (B11,B12,B13) وB2 (B21,B22,B23).
const SECTIONS = [
 {
 id: 'A', nameAr: 'القسم A', nameEn: 'Section A',
 color: '#eff6ff', stroke: '#2563eb',
 columns: [
 [{ label: 'A1', dbKey: 'A1' }, { label: 'A2', dbKey: 'A2' }, { label: 'A3', dbKey: 'A3' }],
 ],
 },
 {
 id: 'B', nameAr: 'القسم B', nameEn: 'Section B',
 color: '#f5f3ff', stroke: '#7c3aed',
 columns: [
 [{ label: 'B11', dbKey: 'B11' }, { label: 'B12', dbKey: 'B12' }, { label: 'B13', dbKey: 'B13' }],
 [{ label: 'B21', dbKey: 'B21' }, { label: 'B22', dbKey: 'B22' }, { label: 'B23', dbKey: 'B23' }],
 ],
 },
 {
 id: 'C', nameAr: 'القسم C', nameEn: 'Section C',
 color: '#f0fdf4', stroke: '#16a34a',
 columns: [
 [{ label: 'C1', dbKey: 'C1' }, { label: 'C2', dbKey: 'C2' }, { label: 'C3', dbKey: 'C3' }],
 ],
 },
]

const DB_TO_SECTION = {}
SECTIONS.forEach(s => s.columns.flat().forEach(sh => { DB_TO_SECTION[sh.dbKey] = s.id }))

const SHELF_TO_SECTION_ID = {}
SECTIONS.forEach(s => s.columns.flat().forEach(sh => { SHELF_TO_SECTION_ID[sh.dbKey] = s.id }))

// الممر "القريب" لكل رف — يحدّد هل يلزم رسم سهم عبور بين الممرين أم لا.
// A كلها ملاصقة للممر الأول، C كلها ملاصقة للممر الثاني. عمود B1 (الأقرب
// للممر الثاني) وعمود B2 (الأقرب للممر الأول) — كل رف بعمود يرث نفس
// الممر القريب لعموده.
const SHELF_HOME_AISLE = {
 'A1': 1, 'A2': 1, 'A3': 1,
 'B11': 2, 'B12': 2, 'B13': 2,
 'B21': 1, 'B22': 1, 'B23': 1,
 'C1': 2, 'C2': 2, 'C3': 2,
}

// تجميع المنتجات بالقائمة الجانبية حسب "المجموعة" الحقيقية — A / C كسابقاً،
// وB تنقسم لمجموعتين B1 وB2 (بدل عرضهم كقسم واحد مبهم) حتى تكون الأقسام
// واضحة بالقائمة.
function groupKeyFor(dbKey) {
 if (!dbKey) return null
 if (dbKey.startsWith('B1')) return 'B1'
 if (dbKey.startsWith('B2')) return 'B2'
 return dbKey[0] // 'A' أو 'C'
}
const GROUP_META = {
 A:  { nameAr: 'القسم A',        nameEn: 'Section A',        color: '#2563eb', bg: '#eff6ff' },
 B1: { nameAr: 'القسم B — B1',   nameEn: 'Section B — B1',   color: '#7c3aed', bg: '#f5f3ff' },
 B2: { nameAr: 'القسم B — B2',   nameEn: 'Section B — B2',   color: '#7c3aed', bg: '#f5f3ff' },
 C:  { nameAr: 'القسم C',        nameEn: 'Section C',        color: '#16a34a', bg: '#f0fdf4' },
}
const GROUP_ORDER = ['A', 'B1', 'B2', 'C']

/*
 ============================================================================
 عقد البيانات المتوقّع من الباك اند (/navigation/cart/:cartId) — 4 علامات:
 ============================================================================
 العلامات الأربع الموضوعة على الأرض (raspberry_pi/aruco_reader.py):
   marker 0  -> tag0  (أسفل الممر الأول)   -> "case1"  دخول للأمام  (forward)
   marker 1  -> tag1  (أعلى الممر الأول)   -> "case2"  دخول للخلف   (backward)
   marker 2  -> tag2  (أسفل الممر الثاني)  -> "case3"  دخول للأمام  (forward)
   marker 3  -> tag3  (أعلى الممر الثاني)  -> "case4"  دخول للخلف   (backward)

 الحقول المتوقّعة من الـ API (كما هي مستخدمة حالياً، لا تغيير في الشكل):
   { aisle_id, in_aisle, direction, entry_direction }
 ============================================================================
*/

function useCartPosition(cartId) {
 const [pos, setPos] = useState(null)
 useEffect(() => {
 if (!cartId) return
 const tick = () =>
 api.get(`/navigation/cart/${cartId}`)
 .then(({ data }) => setPos(data))
 .catch(() => {})
 tick()
 const id = setInterval(tick, 1000) // متابعة أسرع لمطابقة زمن استجابة القارئ (<= 1 ثانية)
 return () => clearInterval(id)
 }, [cartId])
 return pos
}

function useProductPath(cartId, shelfKey) {
 const [path, setPath] = useState(null)
 useEffect(() => {
 if (!cartId || !shelfKey) { setPath(null); return }
 api.get(`/navigation/path?cart_id=${cartId}&shelf_key=${shelfKey}`)
 .then(({ data }) => setPath(data))
 .catch(() => setPath(null))
 }, [cartId, shelfKey])
 return path
}

// رقم المسار (path1..path4) حسب الممر الحالي واتجاه الدخول — مطابق للمخطط:
//   ممر1 + forward (جاء من tag0/case1)  -> path1
//   ممر1 + backward (جاء من tag1/case2) -> path2
//   ممر2 + forward (جاء من tag2/case3)  -> path3
//   ممر2 + backward (جاء من tag3/case4) -> path4
function getPathNumber(aisleId, direction) {
 if (!aisleId || !direction) return null
 if (aisleId === 1) return direction === 'forward' ? 1 : 2
 return direction === 'forward' ? 3 : 4
}

export default function MapPage() {
 const { i18n } = useTranslation()
 const isAr = i18n.language === 'ar'
 const location = useLocation()
 const highlightFromNav = location.state?.highlight

 const [products, setProducts] = useState([])
 const [loading, setLoading] = useState(true)
 const [activeSection, setActiveSection] = useState(null)
 const [activeShelf, setActiveShelf] = useState(null)
 const [selectedProduct, setSelectedProduct] = useState(null)
 const [targetShelf, setTargetShelf] = useState(null)
 const [search, setSearch] = useState('')
 const [cartId] = useState(1)

 const cartPos = useCartPosition(cartId)
 const cartPath = useProductPath(cartId, targetShelf)

 const activeAisle = cartPos?.aisle_id || null
 const cartDirection = cartPos?.direction || null
 const cartInAisle = cartPos?.in_aisle || false
 const entryDirection = cartPos?.entry_direction || null

 // الاتجاه "الحيّ" المعروض على مؤشر العربة: طالما هي داخل الممر نستخدم
 // الاتجاه المتوقّع من علامة الدخول، وبعد خروجها نستخدم الاتجاه النهائي المؤكّد
 const liveDirection = cartInAisle ? entryDirection : cartDirection

 const pathAisle = targetShelf ? SHELF_HOME_AISLE[targetShelf] : null
 const pathSection = targetShelf ? SHELF_TO_SECTION_ID[targetShelf] : null

 // هل نحتاج لعرض سهم يربط بين الممرين؟ (العربة في ممر معروف، والهدف في ممر آخر)
 const showAisleConnector = Boolean(targetShelf && pathAisle && activeAisle && pathAisle !== activeAisle)

 // نقطة العبور بين الممرين: أعلى الخريطة إذا كانت العربة داخلة للأمام (من
 // أسفل الممر) لأنها ستكمل طريقها للأمام وتعبر من فوق، أو أسفل الخريطة إذا
 // كانت داخلة للخلف (من أعلى الممر) لأنها راجعة وتعبر من تحت.
 const crossAt = liveDirection === 'backward' ? 'bottom' : 'top'
 const pathNumber = showAisleConnector ? getPathNumber(activeAisle, liveDirection) : null

 // ── قياس مواقع الممرين على الخريطة لرسم سهم الربط بينهما ───────────────────
 const gridWrapRef = useRef(null)
 const aisle1ColRef = useRef(null)
 const aisle2ColRef = useRef(null)
 const [connectorGeo, setConnectorGeo] = useState(null)

 useLayoutEffect(() => {
 const wrap = gridWrapRef.current
 const el1 = aisle1ColRef.current
 const el2 = aisle2ColRef.current
 if (!wrap || !el1 || !el2) { setConnectorGeo(null); return }

 const measure = () => {
 const wrapRect = wrap.getBoundingClientRect()
 const r1 = el1.getBoundingClientRect()
 const r2 = el2.getBoundingClientRect()
 setConnectorGeo({
 width: wrapRect.width,
 xAisle1: r1.left - wrapRect.left + r1.width / 2,
 xAisle2: r2.left - wrapRect.left + r2.width / 2,
 })
 }
 measure()
 const ro = new ResizeObserver(measure)
 ro.observe(wrap)
 window.addEventListener('resize', measure)
 return () => { ro.disconnect(); window.removeEventListener('resize', measure) }
 }, [loading])

 useEffect(() => {
 productApi.list({ limit: 300 })
 .then(({ data }) => {
 setProducts(data)
 if (highlightFromNav?.section) {
 const secId = DB_TO_SECTION[highlightFromNav.section]
 if (secId) {
 setActiveSection(secId)
 setActiveShelf(highlightFromNav.section)
 setTargetShelf(highlightFromNav.section)
 }
 }
 })
 .catch(() => {})
 .finally(() => setLoading(false))
 }, [highlightFromNav?.id])

 const countByDbKey = {}
 products.forEach(p => {
 if (p.section) countByDbKey[p.section] = (countByDbKey[p.section] || 0) + 1
 })

 const handleSectionClick = useCallback((secId) => {
 setActiveSection(prev => prev === secId ? null : secId)
 setActiveShelf(null); setSelectedProduct(null); setTargetShelf(null)
 }, [])

 const handleShelfClick = useCallback((dbKey, secId) => {
 setActiveSection(secId)
 setActiveShelf(prev => prev === dbKey ? null : dbKey)
 setSelectedProduct(null)
 setTargetShelf(prev => prev === dbKey ? null : dbKey)
 }, [])

 // اختيار منتج (من أي مكان بالقائمة الجانبية) — يفعّل السهم/الألوان على
 // الخريطة فوراً: يحدّد القسم والرف المستهدف فتُبنى isPathTarget/isShTarget
 // وسهم العبور تلقائياً حسب موقع العربة الحالي.
 const handleProductSelect = useCallback((p) => {
 setSelectedProduct(p)
 if (p.section) {
 const secId = DB_TO_SECTION[p.section]
 if (secId) { setActiveSection(secId); setActiveShelf(p.section) }
 setTargetShelf(p.section)
 }
 }, [])

 const activeSec = SECTIONS.find(s => s.id === activeSection)
 const shelfProducts = activeShelf
 ? products.filter(p => p.section === activeShelf)
 : activeSec
 ? products.filter(p => activeSec.columns.flat().some(sh => sh.dbKey === p.section))
 : []

 const filtered = products.filter(p =>
 !search ||
 p.name?.toLowerCase().includes(search.toLowerCase()) ||
 (p.name_ar || '').includes(search)
 )

 // تجميع نتائج القائمة الجانبية حسب المجموعة (A / B1 / B2 / C) لتوضيح
 // الأقسام بدل قائمة مسطّحة واحدة.
 const groupedFiltered = GROUP_ORDER
 .map(g => ({ key: g, meta: GROUP_META[g], items: filtered.filter(p => groupKeyFor(p.section) === g) }))
 .filter(g => g.items.length > 0)

 const directionText = liveDirection === 'forward'
 ? (isAr ? 'متجه للأمام →' : 'Moving forward →')
 : liveDirection === 'backward'
 ? (isAr ? '← متجه للخلف' : '← Moving backward')
 : cartInAisle ? (isAr ? 'داخل الممر...' : 'In aisle...') : null

 const aisleLabel = (id) => isAr
 ? (id === 1 ? 'الممر الأول' : 'الممر الثاني')
 : (id === 1 ? 'Aisle 1' : 'Aisle 2')

 return (
 <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 96px)' }}>
 <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
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
 {isAr ? 'انقر على قسم أو منتج لعرض المسار' : 'Click a section or product to view the path'}
 </p>
 </div>
 </div>
 {(activeAisle || cartInAisle) && (
 <div style={{
 display: 'flex', alignItems: 'center', gap: 6,
 background: '#fff0f0', border: '1.5px solid #fca5a5',
 color: '#c0392b', padding: '6px 14px', borderRadius: 12,
 fontSize: 12, fontWeight: 800,
 }}>
 <Radio size={13} className="animate-pulse" />
 {activeAisle ? aisleLabel(activeAisle) : (isAr ? 'داخل ممر' : 'In aisle')}
 {directionText && (
 <span style={{ marginInlineStart: 4, fontSize: 11, opacity: 0.8 }}>{directionText}</span>
 )}
 </div>
 )}
 </div>

 {cartPath && targetShelf && (
 <div style={{
 display: 'flex', alignItems: 'flex-start', gap: 10,
 background: '#f0fdf4', border: '1.5px solid #86efac',
 borderRadius: 12, padding: '12px 16px', marginBottom: 12,
 }}>
 <Navigation size={18} style={{ color: '#16a34a', flexShrink: 0, marginTop: 1 }} />
 <div style={{ flex: 1 }}>
 <p style={{ fontSize: 13, fontWeight: 800, color: '#15803d', marginBottom: 4 }}>
 {isAr ? `مسار إلى رف ${targetShelf}` : `Path to shelf ${targetShelf}`}
 {pathNumber && (
 <span style={{ marginInlineStart: 8, fontSize: 11, background: '#16a34a', color: '#fff', padding: '1px 8px', borderRadius: 999 }}>
 {isAr ? `المسار ${pathNumber}` : `Path ${pathNumber}`}
 </span>
 )}
 </p>
 <p style={{ fontSize: 12, color: '#166534', direction: 'ltr' }}>
 {cartPath.instruction}
 </p>
 <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
 {cartPath.steps.map((step, i) => (
 <React.Fragment key={i}>
 <span style={{
 fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
 background: step.type === 'shelf' ? '#16a34a' : '#dcfce7',
 color: step.type === 'shelf' ? '#fff' : '#15803d',
 }}>{step.label}</span>
 {i < cartPath.steps.length - 1 && (
 <span style={{ fontSize: 10, color: '#94a3b8' }}>→</span>
 )}
 </React.Fragment>
 ))}
 </div>
 </div>
 <button onClick={() => { setTargetShelf(null); setSelectedProduct(null) }}
 style={{ marginInlineStart: 'auto', flexShrink: 0, color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer' }}>
 <X size={14} />
 </button>
 </div>
 )}

 <div className="flex flex-col xl:flex-row gap-5 flex-1 min-h-0">
 {/* القائمة الجانبية: البحث + قائمة المنتجات مجمّعة حسب القسم — بترتيب
 المستند تظهر أولاً بالـ DOM، وبفضل RTL بتنعرض فعلياً على يسار الخريطة. */}
 <div className="xl:w-80 xl:order-first space-y-4">
 {activeSec && (
 <div className="card border-2" style={{ borderColor: activeSec.stroke, background: activeSec.color + '99' }}>
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
 <p style={{ fontWeight: 800, fontSize: 14, color: '#1e293b' }}>
 {isAr ? activeSec.nameAr : activeSec.nameEn}
 {activeShelf && (
 <span style={{ marginInlineStart: 8, background: activeSec.stroke, color: '#fff', fontSize: 10, fontWeight: 900, padding: '1px 8px', borderRadius: 999 }}>{activeShelf}</span>
 )}
 </p>
 <span style={{ background: activeSec.stroke, color: '#fff', fontSize: 12, fontWeight: 800, padding: '2px 10px', borderRadius: 999 }}>{shelfProducts.length}</span>
 </div>
 <div style={{ maxHeight: 260, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
 {shelfProducts.length === 0 ? (
 <div style={{ textAlign: 'center', padding: '20px 0', color: '#94a3b8' }}>
 <Package size={28} style={{ margin: '0 auto 6px', opacity: 0.2 }} />
 <p style={{ fontSize: 12 }}>{isAr ? 'لا توجد منتجات' : 'No products'}</p>
 </div>
 ) : shelfProducts.map(p => (
 <button key={p.id} onClick={() => handleProductSelect(p)}
 style={{
 width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
 padding: '8px 12px', borderRadius: 10, cursor: 'pointer',
 background: selectedProduct?.id === p.id ? activeSec.stroke : 'rgba(255,255,255,0.75)',
 color: selectedProduct?.id === p.id ? '#fff' : '#1e293b',
 border: `1px solid ${selectedProduct?.id === p.id ? activeSec.stroke : 'transparent'}`,
 transition: 'all 0.15s', fontSize: 12,
 }}>
 <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
 {p.name_ar || p.name}
 </span>
 <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
 <span style={{ fontWeight: 800 }}>{formatPrice(p.price)}</span>
 {targetShelf === p.section && <Navigation size={11} style={{ color: '#16a34a' }} />}
 </div>
 </button>
 ))}
 </div>
 </div>
 )}

 <div className="card">
 <div style={{ position: 'relative', marginBottom: 10 }}>
 <Search size={15} style={{ position: 'absolute', insetInlineStart: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text3)' }} />
 <input className="input" style={{ paddingInlineStart: 36, fontSize: 13 }}
 placeholder={isAr ? 'ابحث عن منتج...' : 'Search products...'}
 value={search} onChange={e => setSearch(e.target.value)} />
 {search && (
 <button onClick={() => setSearch('')}
 style={{ position: 'absolute', insetInlineEnd: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text3)', background: 'none', border: 'none', cursor: 'pointer' }}>
 <X size={14} />
 </button>
 )}
 </div>

 <div style={{ maxHeight: 460, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
 {groupedFiltered.map(group => (
 <div key={group.key}>
 {/* عنوان المجموعة — يوضّح القسم بشكل صريح بدل قائمة مسطّحة */}
 <div style={{
 display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px', marginBottom: 4,
 borderRadius: 8, background: group.meta.bg,
 }}>
 <span style={{ width: 8, height: 8, borderRadius: 999, background: group.meta.color, flexShrink: 0 }} />
 <span style={{ fontSize: 11, fontWeight: 900, color: group.meta.color }}>
 {isAr ? group.meta.nameAr : group.meta.nameEn}
 </span>
 <span style={{ marginInlineStart: 'auto', fontSize: 10, fontWeight: 700, color: 'var(--text3)' }}>
 {group.items.length}
 </span>
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
 {group.items.slice(0, 40).map(p => {
 const sec = SECTIONS.find(s => s.id === DB_TO_SECTION[p.section])
 const isSel = selectedProduct?.id === p.id
 return (
 <button key={p.id} onClick={() => handleProductSelect(p)}
 style={{
 width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
 padding: '7px 10px', borderRadius: 10, cursor: 'pointer',
 background: isSel ? (sec?.color || 'var(--surface2)') : 'transparent',
 border: isSel ? `1.5px solid ${sec?.stroke || 'var(--border)'}` : '1.5px solid transparent',
 transition: 'all 0.12s',
 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
 <span style={{ fontSize: 9, fontWeight: 800, padding: '1px 5px', borderRadius: 4, background: sec?.color || 'var(--surface2)', color: sec?.stroke || 'var(--text3)', border: `1px solid ${sec?.stroke || 'var(--border)'}`, flexShrink: 0 }}>{p.section}</span>
 <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: isSel ? 700 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name_ar || p.name}</span>
 </div>
 <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
 <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--primary)' }}>{formatPrice(p.price)}</span>
 {targetShelf === p.section && <Navigation size={11} style={{ color: '#16a34a' }} />}
 </div>
 </button>
 )
 })}
 </div>
 </div>
 ))}
 {groupedFiltered.length === 0 && (
 <p style={{ fontSize: 12, textAlign: 'center', padding: '16px 0', color: 'var(--text3)' }}>
 {isAr ? 'لا نتائج' : 'No results'}
 </p>
 )}
 </div>
 </div>

 {!activeSection && !search && !targetShelf && (
 <div style={{ textAlign: 'center', padding: '24px 0' }}>
 <MapPin size={32} style={{ margin: '0 auto 8px', opacity: 0.15, color: 'var(--text3)' }} />
 <p style={{ fontSize: 12, color: 'var(--text3)' }}>
 {isAr ? 'انقر على قسم أو ابحث عن منتج لعرض المسار' : 'Click or search to show path'}
 </p>
 </div>
 )}
 </div>

 <div className="flex-1 min-w-0 flex flex-col">
 <div className="card flex-1 flex flex-col" style={{ background: 'var(--surface)', padding: 24 }}>
 {loading ? (
 <div style={{ display: 'flex', flex: 1, justifyContent: 'center', alignItems: 'center', padding: 64 }}>
 <Loader2 className="animate-spin" size={32} style={{ color: 'var(--primary)' }} />
 </div>
 ) : (
 <div ref={gridWrapRef} style={{ position: 'relative', display: 'flex', flexDirection: 'column', flex: 1 }}>
 {/* شريط سهم الربط العلوي — يظهر عند العبور من الأعلى (اتجاه للأمام) */}
 <div style={{
 height: (showAisleConnector && crossAt === 'top') ? 50 : 0,
 transition: 'height 0.25s ease', overflow: 'visible', position: 'relative',
 }}>
 {showAisleConnector && crossAt === 'top' && connectorGeo && (
 <AisleConnectorArrow
 xFrom={activeAisle === 1 ? connectorGeo.xAisle1 : connectorGeo.xAisle2}
 xTo={pathAisle === 1 ? connectorGeo.xAisle1 : connectorGeo.xAisle2}
 width={connectorGeo.width}
 flip={false}
 label={isAr
 ? `اتجه إلى ${aisleLabel(pathAisle)}`
 : `Head to ${aisleLabel(pathAisle)}`}
 />
 )}
 </div>

 <div style={{ display: 'grid', gridTemplateColumns: '1fr 64px 1fr 64px 1fr', gap: 0, direction: 'ltr', flex: 1, minHeight: 480 }}>
 <SectionBlock sec={SECTIONS[2]} isActive={activeSection === SECTIONS[2].id}
 isPathTarget={pathSection === SECTIONS[2].id} countByDbKey={countByDbKey}
 activeShelf={activeShelf} targetShelf={targetShelf}
 onSectionClick={handleSectionClick} onShelfClick={handleShelfClick} isAr={isAr} />
 <AisleColumn colRef={aisle2ColRef} label={isAr ? 'ممر ثاني' : 'Aisle 2'} aisleId={2}
 activeAisle={activeAisle} cartInAisle={cartInAisle} liveDirection={liveDirection}
 isPathAisle={pathAisle === 2} />
 <SectionBlock sec={SECTIONS[1]} isActive={activeSection === SECTIONS[1].id}
 isPathTarget={pathSection === SECTIONS[1].id} countByDbKey={countByDbKey}
 activeShelf={activeShelf} targetShelf={targetShelf}
 onSectionClick={handleSectionClick} onShelfClick={handleShelfClick} isAr={isAr} />
 <AisleColumn colRef={aisle1ColRef} label={isAr ? 'ممر أول' : 'Aisle 1'} aisleId={1}
 activeAisle={activeAisle} cartInAisle={cartInAisle} liveDirection={liveDirection}
 isPathAisle={pathAisle === 1} />
 <SectionBlock sec={SECTIONS[0]} isActive={activeSection === SECTIONS[0].id}
 isPathTarget={pathSection === SECTIONS[0].id} countByDbKey={countByDbKey}
 activeShelf={activeShelf} targetShelf={targetShelf}
 onSectionClick={handleSectionClick} onShelfClick={handleShelfClick} isAr={isAr} />
 </div>

 {/* شريط سهم الربط السفلي — يظهر عند العبور من الأسفل (اتجاه للخلف) */}
 <div style={{
 height: (showAisleConnector && crossAt === 'bottom') ? 50 : 0,
 transition: 'height 0.25s ease', overflow: 'visible', position: 'relative',
 }}>
 {showAisleConnector && crossAt === 'bottom' && connectorGeo && (
 <AisleConnectorArrow
 xFrom={activeAisle === 1 ? connectorGeo.xAisle1 : connectorGeo.xAisle2}
 xTo={pathAisle === 1 ? connectorGeo.xAisle1 : connectorGeo.xAisle2}
 width={connectorGeo.width}
 flip={true}
 label={isAr
 ? `اتجه إلى ${aisleLabel(pathAisle)}`
 : `Head to ${aisleLabel(pathAisle)}`}
 />
 )}
 </div>
 </div>
 )}
 </div>
 </div>
 </div>

 <style>{`
 @keyframes cartPulse { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.2);opacity:.7} }
 @keyframes tipArrowFloatUp { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(-3px)} }
 @keyframes tipArrowFloatDown { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(3px)} }
 @keyframes connectorDash { to { stroke-dashoffset: -20; } }
 `}</style>
 </div>
 )
}

function SectionBlock({ sec, isActive, isPathTarget, countByDbKey, activeShelf, targetShelf, onSectionClick, onShelfClick, isAr }) {
 const ShelfButton = ({ sh }) => {
 const count = countByDbKey[sh.dbKey] || 0
 const isShActive = activeShelf === sh.dbKey
 const isShTarget = targetShelf === sh.dbKey
 return (
 <button key={sh.dbKey} onClick={e => { e.stopPropagation(); onShelfClick(sh.dbKey, sec.id) }}
 style={{
 width: '100%', height: '100%', padding: '0 14px', borderRadius: 12,
 border: `2px solid ${isShTarget ? '#16a34a' : isShActive ? sec.stroke : '#e2e8f0'}`,
 background: isShTarget ? '#dcfce7' : isShActive ? sec.stroke + '1a' : '#fff',
 boxShadow: isShActive || isShTarget ? '0 2px 6px rgba(0,0,0,0.06)' : 'none',
 display: 'flex', alignItems: 'center', justifyContent: 'space-between',
 cursor: 'pointer', transition: 'all 0.12s',
 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
 <span style={{
 width: 28, height: 28, borderRadius: 8, flexShrink: 0,
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 fontSize: 12, fontWeight: 900,
 background: isShTarget ? '#16a34a' : isShActive ? sec.stroke : '#f1f5f9',
 color: isShTarget || isShActive ? '#fff' : '#64748b',
 }}>{sh.label}</span>
 <span style={{ fontSize: 12, fontWeight: 700, color: isShTarget ? '#15803d' : '#374151' }}>
 {isAr ? `رف ${sh.label}` : `Shelf ${sh.label}`}
 </span>
 </div>
 <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
 {isShTarget && <Navigation size={12} style={{ color: '#16a34a' }} />}
 {count > 0 && (
 <span style={{ background: isShTarget ? '#16a34a' : isActive ? sec.stroke : '#94a3b8', color: '#fff', fontSize: 10, fontWeight: 800, padding: '1px 7px', borderRadius: 999 }}>{count}</span>
 )}
 </div>
 </button>
 )
 }

 return (
 <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
 <div onClick={() => onSectionClick(sec.id)}
 style={{
 flex: 1, border: `2px dashed ${isPathTarget ? '#16a34a' : isActive ? sec.stroke : '#d1d5db'}`,
 borderRadius: 12, background: isPathTarget ? '#f0fdf4' : isActive ? sec.color : '#fafafa',
 padding: 14, cursor: 'pointer', transition: 'all 0.2s', minHeight: 480, height: '100%', position: 'relative',
 }}>
 {isPathTarget && (
 <div style={{ position: 'absolute', top: 8, insetInlineEnd: 8, background: '#16a34a', color: '#fff', fontSize: 9, fontWeight: 900, padding: '2px 7px', borderRadius: 999, display: 'flex', alignItems: 'center', gap: 3 }}>
 <Navigation size={9} /> {isAr ? 'هدفك' : 'Goal'}
 </div>
 )}
 <p style={{ textAlign: 'center', fontWeight: 800, fontSize: 16, color: isPathTarget ? '#15803d' : isActive ? sec.stroke : '#374151', marginBottom: 14 }}>
 {isAr ? sec.nameAr : sec.nameEn}
 </p>
 {/* عمود واحد (A/C) أو عمودان جنباً إلى جنب (B) — كل عمود 3 أرفف مكدّسة بالتساوي */}
 <div style={{ display: 'grid', gridTemplateColumns: `repeat(${sec.columns.length}, 1fr)`, gap: 12, height: 'calc(100% - 44px)' }}>
 {sec.columns.map((col, ci) => (
 <div key={ci} style={{ display: 'grid', gridTemplateRows: `repeat(${col.length}, 1fr)`, gap: 10 }}>
 {col.map(sh => <ShelfButton key={sh.dbKey} sh={sh} />)}
 </div>
 ))}
 </div>
 </div>
 </div>
 )
}

function AisleColumn({ colRef, label, aisleId, activeAisle, cartInAisle, liveDirection, isPathAisle }) {
 // العربة "موجودة" في هذا الممر فقط طالما هي بداخله فعلياً (in_aisle=True).
 // بمجرد قراءة العلامة الثانية تُسجَّل "خروج" وتختفي العلامة من الممر مباشرة.
 const isCartHere = activeAisle === aisleId && cartInAisle

 // موضع العربة رأسياً داخل الممر: أسفل الممر عند الدخول للأمام (case1/case3
 // — العلامتان 0 و 2)، وأعلى الممر عند الدخول للخلف (case2/case4 — العلامتان
 // 1 و 3)، تماماً كما في المخطط.
 const atBottom = liveDirection !== 'backward'

 return (
 <div ref={colRef} style={{
 display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-between',
 padding: '18px 4px', position: 'relative', height: '100%', minHeight: 480,
 background: isCartHere
 ? 'linear-gradient(180deg,rgba(239,68,68,.07) 0%,rgba(239,68,68,.14) 50%,rgba(239,68,68,.07) 100%)'
 : isPathAisle
 ? 'linear-gradient(180deg,rgba(22,163,74,.05) 0%,rgba(22,163,74,.10) 50%,rgba(22,163,74,.05) 100%)'
 : 'transparent',
 borderRadius: 8, transition: 'background 0.4s',
 }}>
 <p style={{
 fontSize: 9, fontWeight: 700, textAlign: 'center',
 color: isCartHere ? '#ef4444' : isPathAisle ? '#16a34a' : '#94a3b8',
 writingMode: 'vertical-rl', textOrientation: 'mixed', transform: 'rotate(180deg)',
 transition: 'color 0.3s', lineHeight: 1.5, whiteSpace: 'pre-line', position: 'absolute',
 top: '50%', marginTop: -20,
 }}>{label}</p>

 {isPathAisle && !isCartHere && (
 <div style={{ position: 'absolute', top: 60, bottom: 60, width: 3, borderRadius: 2, background: 'linear-gradient(180deg,transparent,#16a34a,transparent)', opacity: 0.6 }} />
 )}

 {/* أعلى الممر — تظهر العربة هنا عند الدخول للخلف (case2/case4) */}
 <div style={{ height: 30, display: 'flex', alignItems: 'flex-start' }}>
 {isCartHere && !atBottom && <CartMarker direction={liveDirection} />}
 </div>

 <div style={{ flex: 1 }} />

 {/* أسفل الممر — تظهر العربة هنا عند الدخول للأمام (case1/case3) */}
 <div style={{ height: 30, display: 'flex', alignItems: 'flex-end' }}>
 {isCartHere && atBottom && <CartMarker direction={liveDirection} />}
 </div>
 </div>
 )
}

// دائرة تمثّل موقع العربة، مع سهم صغير يوضّح اتجاه حركتها:
// سهم للأعلى عند الدخول للأمام (forward — العلامتان 0 و 2 / case1 و case3)
// وسهم للأسفل عند الدخول للخلف (backward — العلامتان 1 و 3 / case2 و case4).
function CartMarker({ direction }) {
 const isBackward = direction === 'backward'
 return (
 <div style={{ position: 'relative', width: 22, height: 22, flexShrink: 0 }}>
 <div style={{
 width: 22, height: 22, borderRadius: '50%', background: '#ef4444',
 border: '2.5px solid #fff', boxShadow: '0 0 0 3px rgba(239,68,68,.25)',
 animation: 'cartPulse 1.2s ease-in-out infinite',
 }} />
 {direction && (
 <div style={{
 position: 'absolute',
 top: isBackward ? 22 : -15,
 left: '50%', transform: 'translateX(-50%)',
 color: '#ef4444',
 animation: `${isBackward ? 'tipArrowFloatDown' : 'tipArrowFloatUp'} .9s ease-in-out infinite`,
 }}>
 {isBackward ? <ArrowDown size={14} strokeWidth={3} /> : <ArrowUp size={14} strokeWidth={3} />}
 </div>
 )}
 </div>
 )
}

// سهم يربط بين الممرين فوق (أو تحت) الخريطة: يصعد/ينزل من الممر الحالي،
// يعبر أفقياً، ثم يدخل الممر الهدف من نفس الجهة — بحسب اتجاه حركة العربة:
//   flip=false: العبور من الأعلى (العربة متجهة للأمام)
//   flip=true : العبور من الأسفل (العربة متجهة للخلف)
function AisleConnectorArrow({ xFrom, xTo, width, label, flip }) {
 if (xFrom == null || xTo == null || xFrom === xTo) return null

 const H = 50 // ارتفاع كامل الرسم
 const BRIDGE_Y = flip ? (H - 20) : 20 // ارتفاع الخط الأفقي (الجسر بين الممرين)
 const outerY = flip ? 0 : H // الطرف البعيد (داخل الممرين)

 return (
 <svg width={width} height={H} viewBox={`0 0 ${width} ${H}`}
 style={{ position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none' }}>
 <defs>
 <marker id={`aisleConnectorArrowHead-${flip ? 'b' : 't'}`} markerWidth="9" markerHeight="9" refX="4.5" refY="4.5" orient="auto">
 <path d="M0,0 L9,4.5 L0,9 Z" fill="#16a34a" />
 </marker>
 </defs>

 {/* وصلة من الممر الحالي — خط بدون رأس سهم (مجرد وصلة) */}
 <line x1={xFrom} y1={outerY} x2={xFrom} y2={BRIDGE_Y}
 stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeDasharray="1 6"
 style={{ animation: 'connectorDash 0.8s linear infinite' }} />

 {/* الجسر الأفقي بين الممرين — رأس السهم يشير لاتجاه الحركة */}
 <line x1={xFrom} y1={BRIDGE_Y} x2={xTo} y2={BRIDGE_Y}
 stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round"
 markerEnd={`url(#aisleConnectorArrowHead-${flip ? 'b' : 't'})`} />

 {/* دخول الممر الهدف — رأس سهم يشير نحو نقطة الدخول */}
 <line x1={xTo} y1={BRIDGE_Y} x2={xTo} y2={outerY}
 stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round"
 markerEnd={`url(#aisleConnectorArrowHead-${flip ? 'b' : 't'})`} />

 {label && (
 <text x={(xFrom + xTo) / 2} y={flip ? BRIDGE_Y + 16 : BRIDGE_Y - 7} textAnchor="middle"
 fontSize="10" fontWeight="800" fill="#15803d">
 {label}
 </text>
 )}
 </svg>
 )
}
