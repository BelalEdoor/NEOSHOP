import React, { useEffect, useRef, useState, useCallback } from 'react'
import { X, Camera, CameraOff, Keyboard, Scan, ZapOff, PackageX, Plus } from 'lucide-react'

/**
 * BarcodeScanner
 * - Manual mode: auto-detects when input length is complete (no Enter needed)
 * - Camera mode: uses BarcodeDetector API
 * - Hardware scanner: global keydown listener ending in Enter
 * - "Not found" modal: shown when product doesn't exist, allows custom add
 */
export default function BarcodeScanner({ onScan, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const detectorRef = useRef(null)
  const rafRef = useRef(null)
  const manualRef = useRef(null)
  const autoTimerRef = useRef(null)

  const [mode, setMode] = useState('manual')
  const [manualVal, setManualVal] = useState('')
  const [cameraError, setCameraError] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [lastScanned, setLastScanned] = useState(null)

  // ── Camera ───────────────────────────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setScanning(false)
  }, [])

  const startCamera = useCallback(async () => {
    setCameraError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 } },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      if ('BarcodeDetector' in window) {
        detectorRef.current = new window.BarcodeDetector({
          formats: ['ean_13', 'ean_8', 'code_128', 'qr_code', 'upc_a', 'upc_e'],
        })
        setScanning(true)
        const tick = async () => {
          if (!videoRef.current || videoRef.current.readyState < 2) {
            rafRef.current = requestAnimationFrame(tick)
            return
          }
          try {
            const barcodes = await detectorRef.current.detect(videoRef.current)
            if (barcodes.length > 0) {
              const code = barcodes[0].rawValue
              if (code !== lastScanned) {
                setLastScanned(code)
                onScan(code)
                setTimeout(() => setLastScanned(null), 3000)
              }
            }
          } catch (_) {}
          rafRef.current = requestAnimationFrame(tick)
        }
        rafRef.current = requestAnimationFrame(tick)
      } else {
        setCameraError('كاميرا نشطة — الرجاء توجيه الباركود (المتصفح لا يدعم الكشف التلقائي)')
        setScanning(true)
      }
    } catch (err) {
      setCameraError('لا يمكن الوصول إلى الكاميرا: ' + err.message)
    }
  }, [onScan, lastScanned])

  useEffect(() => {
    if (mode === 'camera') startCamera()
    else stopCamera()
    return stopCamera
  }, [mode]) // eslint-disable-line

  // Auto-focus manual input
  useEffect(() => {
    if (mode === 'manual' && manualRef.current) manualRef.current.focus()
  }, [mode])

  // Hardware scanner global listener
  useEffect(() => {
    let buffer = ''
    let timer = null
    const onKey = (e) => {
      if (e.key === 'Enter' && buffer.length >= 4) {
        onScan(buffer.trim())
        buffer = ''
        return
      }
      if (e.key.length === 1) {
        buffer += e.key
        clearTimeout(timer)
        timer = setTimeout(() => { buffer = '' }, 100)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => { window.removeEventListener('keydown', onKey); clearTimeout(timer) }
  }, [onScan])

  // ── Auto-detect on input complete (no Enter needed) ───────────────────
  const BARCODE_LENGTH = 13 // EAN-13 standard; also fires for shorter codes after 600ms idle
  const handleManualChange = (e) => {
    const val = e.target.value.replace(/\D/g, '') // digits only for most barcodes
    setManualVal(val)

    // Clear existing auto-timer
    if (autoTimerRef.current) clearTimeout(autoTimerRef.current)

    if (val.length === 0) return

    if (val.length >= BARCODE_LENGTH) {
      // Full EAN-13 → fire immediately
      onScan(val.trim())
      setManualVal('')
      return
    }

    // Shorter codes or custom: fire after 600ms idle (covers 8-digit, code-128, etc.)
    autoTimerRef.current = setTimeout(() => {
      if (val.trim().length >= 4) {
        onScan(val.trim())
        setManualVal('')
      }
    }, 600)
  }

  // Also allow explicit submit via Enter
  const handleManualSubmit = (e) => {
    e.preventDefault()
    if (autoTimerRef.current) clearTimeout(autoTimerRef.current)
    if (manualVal.trim().length >= 1) {
      onScan(manualVal.trim())
      setManualVal('')
    }
  }

  useEffect(() => () => { if (autoTimerRef.current) clearTimeout(autoTimerRef.current) }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden"
        style={{ background: 'var(--surface)', fontFamily: "'Tajawal','Cairo',sans-serif" }}>

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--primary)', color: '#fff' }}>
              <Scan className="w-4 h-4" />
            </div>
            <span className="font-bold" style={{ color: 'var(--text)' }}>ماسح الباركود</span>
          </div>
          <button onClick={() => { stopCamera(); onClose() }}
            className="p-2 rounded-xl transition-colors"
            style={{ color: 'var(--text3)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex gap-1 p-3" style={{ background: 'var(--surface2)', borderBottom: '1px solid var(--border)' }}>
          {[
            { id: 'manual', icon: Keyboard, label: 'إدخال يدوي' },
            { id: 'camera', icon: Camera, label: 'كاميرا' },
          ].map(({ id, icon: Icon, label }) => (
            <button key={id} onClick={() => setMode(id)}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-sm font-medium transition-all"
              style={
                mode === id
                  ? { background: 'var(--surface)', color: 'var(--primary)', border: '1px solid var(--border)', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }
                  : { color: 'var(--text3)' }
              }>
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {mode === 'camera' ? (
            <div className="space-y-3">
              <div className="relative rounded-2xl overflow-hidden bg-black aspect-video">
                <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />
                {scanning && !cameraError?.includes('لا يمكن') && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="w-3/4 h-0.5 bg-indigo-400 opacity-80 animate-scan-line" />
                    <div className="absolute inset-8 border-2 border-indigo-400/60 rounded-xl" />
                  </div>
                )}
                {!scanning && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <CameraOff className="w-10 h-10 text-white/40" />
                  </div>
                )}
              </div>
              {cameraError && (
                <p className="text-xs text-amber-600 bg-amber-50 rounded-xl p-3 text-center">{cameraError}</p>
              )}
              {lastScanned && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-3 text-center">
                  <p className="text-xs text-green-600 font-medium">✓ تم الكشف</p>
                  <p className="text-sm font-mono text-green-800 mt-1">{lastScanned}</p>
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wide mb-2"
                  style={{ color: 'var(--text3)' }}>
                  أدخل رقم الباركود
                </label>
                <div className="flex gap-2">
                  <input
                    ref={manualRef}
                    type="text"
                    inputMode="numeric"
                    value={manualVal}
                    onChange={handleManualChange}
                    placeholder="6291003034908"
                    className="input font-mono font-bold text-base flex-1"
                    autoComplete="off"
                    dir="ltr"
                    style={{ letterSpacing: '0.06em' }}
                  />
                  <button type="submit" disabled={!manualVal.trim()}
                    className="px-4 py-2 rounded-xl font-bold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{ background: 'var(--primary)', color: '#fff' }}>
                    بحث
                  </button>
                </div>
                {/* Progress indicator */}
                {manualVal.length > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 rounded-full h-1.5 overflow-hidden" style={{ background: 'var(--surface2)' }}>
                      <div className="h-full rounded-full transition-all duration-200"
                        style={{
                          width: `${Math.min(100, (manualVal.length / BARCODE_LENGTH) * 100)}%`,
                          background: manualVal.length >= BARCODE_LENGTH ? '#22c55e' : 'var(--primary)',
                        }} />
                    </div>
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text3)' }}>
                      {manualVal.length}/{BARCODE_LENGTH}
                    </span>
                  </div>
                )}
              </div>
              <p className="text-xs text-center" style={{ color: 'var(--text3)' }}>
                💡 يُكتشف الباركود تلقائياً عند اكتمال الإدخال
              </p>
            </form>
          )}
        </div>
      </div>

      <style>{`
        @keyframes scan-line {
          0%, 100% { transform: translateY(-40px); opacity: 0.4; }
          50% { transform: translateY(40px); opacity: 1; }
        }
        .animate-scan-line { animation: scan-line 1.8s ease-in-out infinite; }
      `}</style>
    </div>
  )
}
