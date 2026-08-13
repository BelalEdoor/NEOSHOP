/**
 * src/pages/admin/AdminNotifications.jsx
 * =======================================
 * صفحة "الإشعارات" بالسايدبار — مركز موحّد لتنبيهات نفاد أنابيب العملات:
 *
 *   1. تنبيهات نشطة (Active Alerts) — نفس القائمة الحية المشتركة عبر
 *      useRefillStore (تتحدّث فوراً لو صار تنبيه جديد وإنت واقف على
 *      الصفحة، لأنها نفس المصدر يلي البطاقة العائمة بتستخدمه). فيها
 *      زر "تم تعبئة الجهاز" لكل تنبيه، نفس وظيفة البطاقة العائمة تمامًا.
 *
 *   2. السجل (History) — كل حدث نفاد أنابيب صار (نشط أو محلول)، الأحدث
 *      أولاً، عبر GET /api/payments/refill-notifications. يُجلب مرة عند
 *      فتح الصفحة، وله زر تحديث يدوي.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Coins, CheckCircle2, Loader2, Clock, History, RefreshCw, AlertCircle, Wrench, Trash2, ShieldAlert, MapPin, Lock, Unlock } from 'lucide-react'
import { paymentApi, theftApi } from '../../hooks/useApi'
import { useRefillStore, useTheftStore } from '../../store'

function formatDateTime(iso, isAr) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(isAr ? 'ar-EG' : 'en-US', {
      dateStyle: 'medium', timeStyle: 'short',
    })
  } catch (_) { return iso }
}

export default function AdminNotifications() {
  const { t, i18n } = useTranslation()
  const isAr = i18n.language === 'ar'
  const navigate = useNavigate()

  const alerts            = useRefillStore(s => s.pendingAlerts)
  const removePendingAlert = useRefillStore(s => s.removePendingAlert)

  const theftAlerts          = useTheftStore(s => s.activeAlerts)
  const removeTheftBySession = useTheftStore(s => s.removeAlertBySession)
  const [resolvingId, setResolvingId] = useState(null)

  const [releasingId, setReleasingId] = useState(null)

  const handleResolveTheft = async (alert) => {
    setResolvingId(alert.alert_id)
    try {
      if (alert.alert_id) await theftApi.resolveAlert(alert.alert_id)
      removeTheftBySession(alert.session_id)
      toast.success(isAr ? '✅ تم إغلاق التنبيه' : '✅ Alert resolved')
    } catch (err) {
      toast.error(err?.response?.data?.detail || (isAr ? 'تعذّر إغلاق التنبيه' : 'Could not resolve alert'))
    } finally {
      setResolvingId(null)
    }
  }

  // ── زر "تفعيل السلة" ─────────────────────────────────────────────────
  // الضغط عليه يعني أن المشكلة حُلّت: الباك اند يرسل أمر تحرير الفرامل
  // للراسبيري باي (MQTT + WebSocket معاً)، يفكّ قفل العربة، يصفّر حالة
  // محرّك الرؤية للجلسة حتى لا تُقفل فوراً من جديد، ويسجّل BRAKE_RELEASED
  // بقاعدة البيانات مع إغلاق كل تنبيهات الجلسة المفتوحة.
  const handleReleaseCart = async (alert) => {
    setReleasingId(alert.session_id)
    try {
      await theftApi.releaseCart(alert.session_id)
      removeTheftBySession(alert.session_id)
      toast.success(isAr ? '🔓 تم تفعيل السلة وتحرير الفرامل' : '🔓 Cart re-enabled — brakes released')
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        (isAr ? 'تعذّر تفعيل السلة — تأكد من اتصال العربة' : 'Could not re-enable the cart — check the cart connection')
      )
    } finally {
      setReleasingId(null)
    }
  }

  const [history, setHistory]           = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [confirmingId, setConfirmingId] = useState(null)
  const [forcingId, setForcingId]       = useState(null)
  const [deletingId, setDeletingId]     = useState(null)

  const loadHistory = useCallback(() => {
    setHistoryLoading(true)
    paymentApi.getRefillNotifications()
      .then(res => setHistory(res.data || []))
      .catch(() => toast.error(isAr ? 'فشل تحميل السجل' : 'Failed to load history'))
      .finally(() => setHistoryLoading(false))
  }, [isAr])

  useEffect(() => { loadHistory() }, [loadHistory])

  const handleConfirm = async (paymentId) => {
    setConfirmingId(paymentId)
    try {
      await paymentApi.confirmRefill(paymentId)
      removePendingAlert(paymentId)
      toast.success(isAr ? '✅ تم إخبار الجهاز، جاري إكمال الدفعة' : '✅ Device notified, resuming payment')
      loadHistory()  // حدّث السجل عشان يعكس الحالة الجديدة فورًا
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        (isAr ? 'تعذّر إخبار الجهاز — تأكد من اتصال MQTT' : 'Could not notify the device — check MQTT connection')
      )
    } finally {
      setConfirmingId(null)
    }
  }

  // ── إعادة تفعيل يدوي — لصفوف السجل "بانتظار التعبئة" اللي ما ظهرت
  // كتنبيه نشط (حالة يتيمة: refill_requested_at موجود بس status الحالي
  // مش AWAITING_REFILL، غالبًا بسبب انقطاع اتصال أو إعادة تشغيل الباك
  // اند بمنتصف المعالجة). بيتجاوز فحص الحالة وينشر refill_done مباشرة.
  const handleForceReactivate = async (paymentId) => {
    setForcingId(paymentId)
    try {
      await paymentApi.forceReactivate(paymentId)
      toast.success(isAr ? '✅ تم إرسال أمر التفعيل للجهاز يدوياً' : '✅ Manual reactivation sent to the device')
      loadHistory()
    } catch (err) {
      toast.error(
        err?.response?.data?.detail ||
        (isAr ? 'تعذّر الإرسال — تأكد من اتصال MQTT' : 'Could not send — check MQTT connection')
      )
    } finally {
      setForcingId(null)
    }
  }

  // ── حذف إشعار من السجل — لا يمسّ حالة الدفعة نفسها، فقط يخفيها من هذا
  // السجل (يصفّر تواريخ طلب/حل التعبئة على الدفعة بالباك اند).
  const handleDelete = async (paymentId) => {
    setDeletingId(paymentId)
    try {
      await paymentApi.deleteRefillNotification(paymentId)
      setHistory(h => h.filter(row => row.payment_id !== paymentId))
      removePendingAlert(paymentId)
      toast.success(isAr ? '🗑️ تم حذف الإشعار' : '🗑️ Notification deleted')
    } catch (err) {
      toast.error(err?.response?.data?.detail || (isAr ? 'تعذّر حذف الإشعار' : 'Could not delete notification'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-extrabold" style={{ color: 'var(--text)' }}>
          {t('notificationsTitle')}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text3)' }}>
          {t('notificationsSubtitle')}
        </p>
      </div>

      {/* ── تنبيهات الأمن (سرقة / منتج غير مسحوب) ──────────────────────────── */}
      <section>
        <h2 className="text-sm font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--text2)' }}>
          <ShieldAlert className="w-4 h-4" style={{ color: '#dc2626' }} />
          {isAr ? 'تنبيهات الأمن' : 'Security Alerts'}
          {theftAlerts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold text-white" style={{ background: '#dc2626' }}>
              {theftAlerts.length}
            </span>
          )}
        </h2>

        {theftAlerts.length === 0 ? (
          <div className="card text-sm py-8 text-center" style={{ color: 'var(--text3)' }}>
            {isAr ? 'لا توجد تنبيهات أمن نشطة' : 'No active security alerts'}
          </div>
        ) : (
          <div className="space-y-3">
            {theftAlerts.map(alert => (
              <div key={alert.session_id} className="card"
                style={{ borderInlineStart: `4px solid ${alert.brake_activated ? '#7f1d1d' : '#dc2626'}` }}>
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: alert.brake_activated ? '#fee2e2' : '#fff7ed' }}>
                      {alert.brake_activated
                        ? <Lock className="w-5 h-5" style={{ color: '#7f1d1d' }} />
                        : <ShieldAlert className="w-5 h-5" style={{ color: '#dc2626' }} />}
                    </div>
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text)' }}>
                        {alert.brake_activated
                          ? (isAr ? '🔒 تم تفعيل فرامل العربة' : '🔒 Cart brake activated')
                          : (isAr ? 'منتج داخل السلة بانتظار المسح' : 'Item in cart awaiting scan')}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text3)' }}>
                        {isAr ? 'عربة' : 'Cart'} #{alert.cart_id ?? '—'} · {isAr ? 'جلسة' : 'session'} #{alert.session_id}
                        {alert.object_class && <span> · {alert.object_class}</span>}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* يظهر فقط بعد تفعيل الفرامل فعلياً — الضغط عليه يعني
                        أن المشكلة حُلّت فتُحرَّر الفرامل وتُفكّ العربة */}
                    {(alert.brake_activated || alert.can_release) && (
                      <button
                        onClick={() => handleReleaseCart(alert)}
                        disabled={releasingId === alert.session_id}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all"
                        style={{ background: releasingId === alert.session_id ? '#86efac' : '#059669' }}
                      >
                        {releasingId === alert.session_id
                          ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <Unlock className="w-4 h-4" />}
                        {isAr ? 'تفعيل السلة' : 'Re-enable cart'}
                      </button>
                    )}
                    <button
                      onClick={() => navigate(`/admin/map?cart=${alert.cart_id ?? ''}`)}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all"
                      style={{ background: '#1e40af' }}
                    >
                      <MapPin className="w-4 h-4" />
                      {isAr ? 'الانتقال للخريطة' : 'Go to map'}
                    </button>
                    <button
                      onClick={() => handleResolveTheft(alert)}
                      disabled={resolvingId === alert.alert_id}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all"
                      style={{ background: resolvingId === alert.alert_id ? '#86efac' : '#16a34a' }}
                    >
                      {resolvingId === alert.alert_id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <CheckCircle2 className="w-4 h-4" />}
                      {isAr ? 'إغلاق' : 'Resolve'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── تنبيهات نشطة ─────────────────────────────────────────────────────── */}
      <section>
        <h2 className="text-sm font-bold mb-3 flex items-center gap-2" style={{ color: 'var(--text2)' }}>
          <AlertCircle className="w-4 h-4" style={{ color: '#dc2626' }} />
          {t('activeAlerts')}
          {alerts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold text-white" style={{ background: '#dc2626' }}>
              {alerts.length}
            </span>
          )}
        </h2>

        {alerts.length === 0 ? (
          <div className="card text-sm py-8 text-center" style={{ color: 'var(--text3)' }}>
            {t('noActiveAlerts')}
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map(alert => (
              <div key={alert.payment_id} className="card"
                style={{ borderInlineStart: '4px solid #dc2626' }}>
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: '#fee2e2' }}>
                      <Coins className="w-5 h-5" style={{ color: '#dc2626' }} />
                    </div>
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text)' }}>
                        {alert.invoice_code || `#${alert.payment_id}`}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text3)' }}>
                        {isAr ? 'متبقي إرجاعه للعميل' : 'Still owed to customer'}: <b>{alert.remaining_change} ₪</b>
                        {alert.device_id && <span> · {alert.device_id}</span>}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleConfirm(alert.payment_id)}
                      disabled={confirmingId === alert.payment_id}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all"
                      style={{ background: confirmingId === alert.payment_id ? '#fca5a5' : '#dc2626' }}
                    >
                      {confirmingId === alert.payment_id
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> {isAr ? 'جاري الإرسال...' : 'Notifying...'}</>
                        : <><CheckCircle2 className="w-4 h-4" /> {t('refillConfirmBtn')}</>
                      }
                    </button>
                    <button
                      onClick={() => handleDelete(alert.payment_id)}
                      disabled={deletingId === alert.payment_id}
                      title={isAr ? 'حذف الإشعار' : 'Delete notification'}
                      className="p-2 rounded-xl transition-all"
                      style={{ background: 'var(--surface2)', color: 'var(--text3)' }}
                    >
                      {deletingId === alert.payment_id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />
                      }
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── السجل ────────────────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text2)' }}>
            <History className="w-4 h-4" />
            {t('historyLog')}
          </h2>
          <button onClick={loadHistory} disabled={historyLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{ background: 'var(--surface2)', color: 'var(--text2)' }}>
            <RefreshCw className={`w-3.5 h-3.5 ${historyLoading ? 'animate-spin' : ''}`} />
            {isAr ? 'تحديث' : 'Refresh'}
          </button>
        </div>

        {historyLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--primary)' }} />
          </div>
        ) : history.length === 0 ? (
          <div className="card text-sm py-8 text-center" style={{ color: 'var(--text3)' }}>
            {t('noHistoryYet')}
          </div>
        ) : (
          <div className="card overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  <th className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{t('invoice')}</th>
                  <th className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{isAr ? 'المبلغ' : 'Amount'}</th>
                  <th className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{t('status')}</th>
                  <th className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{t('requestedAt')}</th>
                  <th className="text-start px-4 py-3 font-semibold" style={{ color: 'var(--text3)' }}>{t('resolvedAt')}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {history.map(row => (
                  <tr key={row.payment_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="px-4 py-3 font-semibold" style={{ color: 'var(--text)' }}>
                      {row.invoice_code || `#${row.payment_id}`}
                    </td>
                    <td className="px-4 py-3" style={{ color: 'var(--text2)' }}>{row.remaining_change} ₪</td>
                    <td className="px-4 py-3">
                      {row.status === 'resolved' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-bold"
                          style={{ background: '#dcfce7', color: '#166534' }}>
                          <CheckCircle2 className="w-3 h-3" /> {t('resolvedStatus')}
                        </span>
                      ) : (
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-bold"
                            style={{ background: '#fee2e2', color: '#991b1b' }}>
                            <Clock className="w-3 h-3" /> {t('stillWaiting')}
                          </span>
                          {/* لو ما ظاهر بقسم "تنبيهات نشطة" فوق (حالة يتيمة) —
                              زر احتياطي يدوي يشتغل حتى بدون تنبيه رسمي */}
                          {!alerts.some(a => a.payment_id === row.payment_id) && (
                            <button
                              onClick={() => handleForceReactivate(row.payment_id)}
                              disabled={forcingId === row.payment_id}
                              title={isAr ? 'الدفعة مش ظاهرة كتنبيه نشط — استخدم هذا كحل احتياطي' : 'Not showing as an active alert — use this as a fallback'}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-[11px] font-bold transition-all"
                              style={{ background: forcingId === row.payment_id ? '#fde68a' : '#f59e0b', color: 'white' }}
                            >
                              {forcingId === row.payment_id
                                ? <Loader2 className="w-3 h-3 animate-spin" />
                                : <Wrench className="w-3 h-3" />
                              }
                              {isAr ? 'إعادة تفعيل يدوي' : 'Force reactivate'}
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text3)' }}>{formatDateTime(row.requested_at, isAr)}</td>
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text3)' }}>{formatDateTime(row.resolved_at, isAr)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(row.payment_id)}
                        disabled={deletingId === row.payment_id}
                        title={isAr ? 'حذف الإشعار' : 'Delete notification'}
                        className="p-2 rounded-lg transition-all"
                        style={{ background: 'var(--surface2)', color: deletingId === row.payment_id ? 'var(--text3)' : '#dc2626' }}
                      >
                        {deletingId === row.payment_id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Trash2 className="w-3.5 h-3.5" />
                        }
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}