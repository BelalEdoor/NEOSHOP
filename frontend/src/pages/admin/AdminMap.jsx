import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
 Loader2, Store, Radio, ShoppingCart, ArrowUp, ArrowDown,
 X, User as UserIcon, Receipt, Ban, ShieldCheck, VideoOff, Video,
} from 'lucide-react'
import api, { BASE_URL } from '../../hooks/useApi'
import { useAuthStore } from '../../store'

/**
 * pages/admin/AdminMap.jsx
 * ========================
 * نفس تصميم خريطة العميل (pages/MapPage.jsx) بالضبط — نفس الأقسام A/B/C
 * (وB مقسّمة لعمودين B1/B2، كل عمود 3 أرفف تماماً متل A وC)، نفس الممرّين
 * ونفس الألوان — لكن بدل عرض عربة واحدة (عميل واحد)، تعرض *كل* العربات
 * النشطة بنفس الوقت، وكل نقطة عربة على الخريطة معنونة بمعرّفها
 * (cart_number). تتحدّث تلقائياً كل ثانية (polling)، بنفس زمن استجابة
 * قارئ ArUco.
 */

const SECTIONS = [
 {
 id: 'A', nameAr: 'القسم A', nameEn: 'Section A',
 columns: [
 [{ label: 'A1', dbKey: 'A1' }, { label: 'A2', dbKey: 'A2' }, { label: 'A3', dbKey: 'A3' }],
 ],
 },
 {
 id: 'B', nameAr: 'القسم B', nameEn: 'Section B',
 columns: [
 [{ label: 'B11', dbKey: 'B11' }, { label: 'B12', dbKey: 'B12' }, { label: 'B13', dbKey: 'B13' }],
 [{ label: 'B21', dbKey: 'B21' }, { label: 'B22', dbKey: 'B22' }, { label: 'B23', dbKey: 'B23' }],
 ],
 },
 {
 id: 'C', nameAr: 'القسم C', nameEn: 'Section C',
 columns: [
 [{ label: 'C1', dbKey: 'C1' }, { label: 'C2', dbKey: 'C2' }, { label: 'C3', dbKey: 'C3' }],
 ],
 },
]

function useAllCartPositions() {
 const [carts, setCarts] = useState([])
 const [loading, setLoading] = useState(true)

 const fetchCarts = useCallback(() => {
 api.get('/navigation/carts')
 .then(({ data }) => setCarts(data || []))
 .catch(() => {})
 .finally(() => setLoading(false))
 }, [])

 useEffect(() => {
 fetchCarts()
 const id = setInterval(fetchCarts, 1000) // مطابق لزمن استجابة قارئ ArUco (<= 1 ثانية)
 return () => clearInterval(id)
 }, [fetchCarts])

 return { carts, loading, refresh: fetchCarts }
}

export default function AdminMap() {
 const { i18n } = useTranslation()
 const isAr = i18n.language === 'ar'
 const { carts, loading } = useAllCartPositions()
 const [monitorCartId, setMonitorCartId] = useState(null)
 const [searchParams] = useSearchParams()

 // إتاحة الانتقال المباشر لمراقبة عربة معيّنة من زر "الانتقال للخريطة"
 // بتنبيهات الأمن (AdminNotifications.jsx / toast السرقة) عبر ?cart=<id>
 useEffect(() => {
   const cartParam = searchParams.get('cart')
   if (cartParam) setMonitorCartId(parseInt(cartParam, 10))
 }, [searchParams])

 const activeCarts = carts.filter(c => c.in_aisle)
 const cartsIn = (aisleId, atBottom) =>
 activeCarts.filter(c => c.aisle_id === aisleId && ((c.entry_direction !== 'backward') === atBottom))

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
 {isAr ? 'مواقع كل العربات النشطة، تتحدّث تلقائياً' : 'All active cart positions, live'}
 </p>
 </div>
 </div>
 {activeCarts.length > 0 && (
 <div style={{
 display: 'flex', alignItems: 'center', gap: 6,
 background: '#fff0f0', border: '1.5px solid #fca5a5',
 color: '#c0392b', padding: '6px 14px', borderRadius: 12,
 fontSize: 12, fontWeight: 800,
 }}>
 <Radio size={13} className="animate-pulse" />
 {isAr ? `${activeCarts.length} عربة داخل الممرات الآن` : `${activeCarts.length} cart(s) in aisles`}
 </div>
 )}
 </div>

 <div className="flex flex-col xl:flex-row gap-5 flex-1 min-h-0">
 <div className="flex-1 min-w-0 flex flex-col">
 <div className="card flex-1 flex flex-col" style={{ background: 'var(--surface)', padding: 24 }}>
 {loading ? (
 <div style={{ display: 'flex', flex: 1, justifyContent: 'center', alignItems: 'center', padding: 64 }}>
 <Loader2 className="animate-spin" size={32} style={{ color: 'var(--primary)' }} />
 </div>
 ) : (
 <div style={{ display: 'grid', gridTemplateColumns: '1fr 64px 1fr 64px 1fr', gap: 0, direction: 'ltr', flex: 1, minHeight: 480 }}>
 <SectionBlock sec={SECTIONS[2]} isAr={isAr} />
 <AisleColumn label={isAr ? 'ممر ثاني' : 'Aisle 2'} bottomCarts={cartsIn(2, true)} topCarts={cartsIn(2, false)} onCartClick={setMonitorCartId} />
 <SectionBlock sec={SECTIONS[1]} isAr={isAr} />
 <AisleColumn label={isAr ? 'ممر أول' : 'Aisle 1'} bottomCarts={cartsIn(1, true)} topCarts={cartsIn(1, false)} onCartClick={setMonitorCartId} />
 <SectionBlock sec={SECTIONS[0]} isAr={isAr} />
 </div>
 )}
 </div>
 </div>

 <div className="xl:w-80 space-y-4">
 <div className="card border-2" style={{ borderColor: 'var(--border)', background: 'var(--surface)' }}>
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
 <p style={{ fontWeight: 800, fontSize: 14, color: 'var(--text)' }}>
 {isAr ? 'العربات' : 'Carts'}
 </p>
 <span style={{ background: 'var(--primary)', color: '#fff', fontSize: 12, fontWeight: 800, padding: '2px 10px', borderRadius: 999 }}>{carts.length}</span>
 </div>
 <div style={{ maxHeight: 520, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
 {carts.length === 0 ? (
 <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text3)' }}>
 <ShoppingCart size={28} style={{ margin: '0 auto 6px', opacity: 0.2 }} />
 <p style={{ fontSize: 12 }}>{isAr ? 'لا توجد بيانات عربات بعد' : 'No cart data yet'}</p>
 </div>
 ) : carts.map(c => (
 <div key={c.cart_id} onClick={() => setMonitorCartId(c.cart_id)} style={{
 width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
 padding: '8px 12px', borderRadius: 10, cursor: 'pointer',
 background: c.in_aisle ? '#fff0f0' : 'var(--surface2)',
 border: `1px solid ${c.in_aisle ? '#fca5a5' : 'var(--border)'}`,
 fontSize: 12,
 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
 <span style={{
 width: 26, height: 26, borderRadius: 8, flexShrink: 0,
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 background: c.in_aisle ? '#ef4444' : 'var(--border)', color: '#fff',
 }}>
 <ShoppingCart size={13} />
 </span>
 <span style={{ fontWeight: 700, color: 'var(--text)' }}>{c.cart_number || `#${c.cart_id}`}</span>
 </div>
 <span style={{ color: 'var(--text3)', fontSize: 11 }}>
 {c.aisle_id ? aisleLabel(c.aisle_id) : (isAr ? 'غير معروف' : 'Unknown')}
 {c.in_aisle && (c.entry_direction === 'backward' ? ' ↓' : ' ↑')}
 </span>
 </div>
 ))}
 </div>
 </div>
 </div>
 </div>

 <style>{`
 @keyframes cartPulse { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.2);opacity:.7} }
 @keyframes tipArrowFloatUp { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(-3px)} }
 @keyframes tipArrowFloatDown { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(3px)} }
 `}</style>

 {monitorCartId && (
 <CartMonitorModal cartId={monitorCartId} isAr={isAr} onClose={() => setMonitorCartId(null)} />
 )}
 </div>
 )
}

// نفس SectionBlock من صفحة العميل بالضبط (نفس الألوان والأبعاد)، لكن بدون
// تفاعل (لا نقر، لا عدّاد منتجات) — عرض ثابت فقط لتوضيح مكان كل رف بالخريطة.
// يدعم عمود واحد (A/C) أو عمودين جنباً إلى جنب (B) بنفس منطق صفحة العميل.
function SectionBlock({ sec, isAr }) {
 const ShelfButton = ({ sh }) => (
 <div style={{
 width: '100%', height: '100%', padding: '0 14px', borderRadius: 12,
 border: '2px solid #e2e8f0', background: '#fff',
 display: 'flex', alignItems: 'center', gap: 8,
 }}>
 <span style={{
 width: 28, height: 28, borderRadius: 8, flexShrink: 0,
 display: 'flex', alignItems: 'center', justifyContent: 'center',
 fontSize: 12, fontWeight: 900, background: '#f1f5f9', color: '#64748b',
 }}>{sh.label}</span>
 <span style={{ fontSize: 12, fontWeight: 700, color: '#374151' }}>
 {isAr ? `رف ${sh.label}` : `Shelf ${sh.label}`}
 </span>
 </div>
 )

 return (
 <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
 <div style={{
 flex: 1, border: '2px dashed #d1d5db',
 borderRadius: 12, background: '#fafafa',
 padding: 14, minHeight: 480, height: '100%', position: 'relative',
 }}>
 <p style={{ textAlign: 'center', fontWeight: 800, fontSize: 16, color: '#374151', marginBottom: 14 }}>
 {isAr ? sec.nameAr : sec.nameEn}
 </p>
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

// نفس AisleColumn من صفحة العميل، لكن يدعم عرض أكثر من عربة بنفس الوقت
// (صفّ متعدد النقاط بدل نقطة واحدة) — كل نقطة معنونة بمعرّف العربة وقابلة
// للنقر لفتح نافذة المراقبة.
function AisleColumn({ label, bottomCarts, topCarts, onCartClick }) {
 const hasAny = bottomCarts.length > 0 || topCarts.length > 0

 return (
 <div style={{
 display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-between',
 padding: '18px 4px', position: 'relative', height: '100%', minHeight: 480,
 background: hasAny
 ? 'linear-gradient(180deg,rgba(239,68,68,.07) 0%,rgba(239,68,68,.14) 50%,rgba(239,68,68,.07) 100%)'
 : 'transparent',
 borderRadius: 8, transition: 'background 0.4s',
 }}>
 <p style={{
 fontSize: 9, fontWeight: 700, textAlign: 'center',
 color: hasAny ? '#ef4444' : '#94a3b8',
 writingMode: 'vertical-rl', textOrientation: 'mixed', transform: 'rotate(180deg)',
 transition: 'color 0.3s', lineHeight: 1.5, whiteSpace: 'pre-line', position: 'absolute',
 top: '50%', marginTop: -20,
 }}>{label}</p>

 {/* أعلى الممر — عربات داخلة للخلف (case2/case4) */}
 <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8, minHeight: 30 }}>
 {topCarts.map(c => (
 <CartMarker key={c.cart_id} direction="backward" label={c.cart_number || `#${c.cart_id}`}
 onClick={() => onCartClick?.(c.cart_id)} />
 ))}
 </div>

 <div style={{ flex: 1 }} />

 {/* أسفل الممر — عربات داخلة للأمام (case1/case3) */}
 <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8, minHeight: 30 }}>
 {bottomCarts.map(c => (
 <CartMarker key={c.cart_id} direction="forward" label={c.cart_number || `#${c.cart_id}`}
 onClick={() => onCartClick?.(c.cart_id)} />
 ))}
 </div>
 </div>
 )
}

// نفس CartMarker من صفحة العميل بالضبط (نفس الدائرة الحمراء والسهم)، مع
// إضافة: ليبل صغير عند النقطة يعرض معرّف العربة، والنقطة نفسها قابلة للنقر
// لفتح نافذة "مراقبة العربة" (الحساب + الفاتورة الحالية + الكاميرا).
function CartMarker({ direction, label, onClick }) {
 const isBackward = direction === 'backward'
 return (
 <button
 onClick={onClick}
 title={label}
 style={{
 display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
 background: 'none', border: 'none', padding: 4, cursor: 'pointer',
 }}
 >
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
 {label && (
 <span style={{
 fontSize: 9, fontWeight: 900, color: '#c0392b', whiteSpace: 'nowrap',
 background: '#fff', padding: '1px 6px', borderRadius: 999, border: '1px solid #fca5a5',
 marginTop: isBackward ? 6 : 2,
 }}>
 {label}
 </span>
 )}
 </button>
 )
}

// ══════════════════════════════════════════════════════════════════════════
// نافذة "مراقبة العربة" — تظهر بمنتصف الشاشة عند الضغط على أي نقطة عربة:
// الحساب المسجَّل + الفاتورة الحالية (قيد الإنشاء) + بث كاميرا مباشر +
// زر تعطيل/تفعيل الحساب عند حدوث نشاط مشبوه.
// ══════════════════════════════════════════════════════════════════════════
function CartMonitorModal({ cartId, isAr, onClose }) {
 const token = useAuthStore(s => s.token)
 const [data, setData] = useState(null)
 const [loading, setLoading] = useState(true)
 const [toggling, setToggling] = useState(false)
 const [cameraError, setCameraError] = useState(false)

 const load = useCallback(() => {
 api.get(`/navigation/cart/${cartId}/monitor`)
 .then(({ data }) => setData(data))
 .catch(() => toast.error(isAr ? 'تعذّر تحميل بيانات العربة' : 'Could not load cart data'))
 .finally(() => setLoading(false))
 }, [cartId, isAr])

 useEffect(() => { load() }, [load])

 // إغلاق بـ Escape
 useEffect(() => {
 const onKey = e => { if (e.key === 'Escape') onClose() }
 window.addEventListener('keydown', onKey)
 return () => window.removeEventListener('keydown', onKey)
 }, [onClose])

 const handleToggleAccount = async () => {
 if (!data?.user) return
 setToggling(true)
 try {
 const action = data.user.is_active ? 'disable' : 'enable'
 const { data: updated } = await api.post(`/users/${data.user.id}/${action}`)
 setData(d => ({ ...d, user: { ...d.user, is_active: updated.is_active } }))
 toast.success(
 updated.is_active
 ? (isAr ? '✅ تم إعادة تفعيل الحساب' : '✅ Account re-enabled')
 : (isAr ? '🚫 تم تعطيل الحساب' : '🚫 Account disabled')
 )
 } catch (err) {
 toast.error(err?.response?.data?.detail || (isAr ? 'فشلت العملية' : 'Action failed'))
 } finally {
 setToggling(false)
 }
 }

 const cameraSrc = token
 ? `${BASE_URL}/camera/stream?token=${encodeURIComponent(token)}&cart_id=${cartId}`
 : null

 return (
 <div
 onClick={onClose}
 style={{
 position: 'fixed', inset: 0, zIndex: 1000,
 background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(2px)',
 display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
 }}
 >
 <div
 onClick={e => e.stopPropagation()}
 style={{
 width: '100%', maxWidth: 640, maxHeight: '88vh', overflowY: 'auto',
 background: 'var(--surface)', borderRadius: 20, border: '1px solid var(--border)',
 boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
 }}
 >
 {/* Header */}
 <div style={{
 display: 'flex', alignItems: 'center', justifyContent: 'space-between',
 padding: '16px 20px', borderBottom: '1px solid var(--border)', position: 'sticky', top: 0,
 background: 'var(--surface)', borderRadius: '20px 20px 0 0', zIndex: 1,
 }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
 <div style={{ width: 36, height: 36, borderRadius: 10, background: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
 <ShoppingCart size={17} style={{ color: '#fff' }} />
 </div>
 <div>
 <p style={{ margin: 0, fontWeight: 900, fontSize: 15, color: 'var(--text)' }}>
 {data?.cart_number || `#${cartId}`}
 </p>
 <p style={{ margin: 0, fontSize: 11, color: 'var(--text3)' }}>
 {isAr ? 'مراقبة العربة' : 'Cart Monitor'}
 </p>
 </div>
 </div>
 <button onClick={onClose} style={{ width: 34, height: 34, borderRadius: 9, border: 'none', background: 'var(--surface2)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)' }}>
 <X size={16} />
 </button>
 </div>

 {loading ? (
 <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
 <Loader2 className="animate-spin" size={28} style={{ color: 'var(--primary)' }} />
 </div>
 ) : (
 <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>

 {/* الحساب المسجَّل */}
 <div style={{ borderRadius: 14, border: '1px solid var(--border)', padding: 14, background: 'var(--surface2)' }}>
 <p style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0 0 10px', fontSize: 12, fontWeight: 800, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
 <UserIcon size={13} /> {isAr ? 'الحساب المسجَّل' : 'Registered Account'}
 </p>
 {data?.user ? (
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
 <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
 <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
 {data.user.name?.[0]?.toUpperCase() || '?'}
 </div>
 <div>
 <p style={{ margin: 0, fontWeight: 700, fontSize: 13, color: 'var(--text)' }}>{data.user.name}</p>
 <p style={{ margin: 0, fontSize: 12, color: 'var(--text3)' }}>{data.user.email}</p>
 </div>
 </div>
 <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
 <span style={{
 fontSize: 10, fontWeight: 800, padding: '3px 9px', borderRadius: 999,
 background: data.user.is_active ? '#dcfce7' : '#fee2e2',
 color: data.user.is_active ? '#15803d' : '#991b1b',
 }}>
 {data.user.is_active ? (isAr ? 'نشط' : 'Active') : (isAr ? 'معطّل' : 'Disabled')}
 </span>
 <button
 onClick={handleToggleAccount}
 disabled={toggling}
 style={{
 display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 10,
 border: 'none', fontWeight: 800, fontSize: 12, cursor: 'pointer', color: '#fff',
 background: toggling ? 'var(--text3)' : data.user.is_active ? '#dc2626' : '#16a34a',
 }}
 >
 {toggling
 ? <Loader2 size={14} className="animate-spin" />
 : data.user.is_active ? <Ban size={14} /> : <ShieldCheck size={14} />
 }
 {data.user.is_active
 ? (isAr ? 'تعطيل الحساب' : 'Disable account')
 : (isAr ? 'إعادة تفعيل' : 'Re-enable')}
 </button>
 </div>
 </div>
 ) : (
 <p style={{ fontSize: 12, color: 'var(--text3)', margin: 0 }}>
 {isAr ? 'لا يوجد حساب مرتبط بهذه العربة حالياً' : 'No account linked to this cart right now'}
 </p>
 )}
 </div>

 {/* الفاتورة الحالية */}
 <div style={{ borderRadius: 14, border: '1px solid var(--border)', padding: 14 }}>
 <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
 <p style={{ display: 'flex', alignItems: 'center', gap: 6, margin: 0, fontSize: 12, fontWeight: 800, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
 <Receipt size={13} /> {isAr ? 'الفاتورة الحالية' : 'Current Invoice'}
 </p>
 {data?.session_status && (
 <span style={{ fontSize: 10, fontWeight: 800, padding: '2px 8px', borderRadius: 999, background: 'var(--surface2)', color: 'var(--text2)' }}>
 {data.session_status}
 </span>
 )}
 </div>
 {data?.items?.length ? (
 <>
 <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 220, overflowY: 'auto' }}>
 {data.items.map(it => (
 <div key={it.product_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, padding: '6px 8px', borderRadius: 8, background: 'var(--surface2)' }}>
 <span style={{ color: 'var(--text)', fontWeight: 600 }}>
 {(isAr && it.name_ar) || it.name} <span style={{ color: 'var(--text3)', fontWeight: 400 }}>× {it.quantity}</span>
 </span>
 <span style={{ fontWeight: 800, color: 'var(--primary)' }}>${it.line_total.toFixed(2)}</span>
 </div>
 ))}
 </div>
 <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, paddingTop: 10, borderTop: '1px dashed var(--border)' }}>
 <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text)' }}>{isAr ? 'الإجمالي' : 'Total'}</span>
 <span style={{ fontSize: 15, fontWeight: 900, color: '#16a34a' }}>${data.total_amount.toFixed(2)}</span>
 </div>
 </>
 ) : (
 <p style={{ fontSize: 12, color: 'var(--text3)', margin: 0, textAlign: 'center', padding: '10px 0' }}>
 {isAr ? 'السلة فارغة حالياً' : 'Cart is currently empty'}
 </p>
 )}
 </div>

 {/* بث الكاميرا */}
 <div style={{ borderRadius: 14, border: '1px solid var(--border)', padding: 14 }}>
 <p style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '0 0 10px', fontSize: 12, fontWeight: 800, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
 <Video size={13} /> {isAr ? 'مراقبة مباشرة' : 'Live Camera'}
 </p>
 <div style={{ borderRadius: 10, overflow: 'hidden', background: '#0f172a', aspectRatio: '16/9', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
 {cameraSrc && !cameraError ? (
 <img
 src={cameraSrc}
 alt="cart camera"
 onError={() => setCameraError(true)}
 style={{ width: '100%', height: '100%', objectFit: 'cover' }}
 />
 ) : (
 <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, color: '#94a3b8' }}>
 <VideoOff size={22} />
 <span style={{ fontSize: 11 }}>{isAr ? 'الكاميرا غير متاحة حالياً' : 'Camera unavailable'}</span>
 </div>
 )}
 </div>
 </div>
 </div>
 )}
 </div>
 </div>
 )
}
