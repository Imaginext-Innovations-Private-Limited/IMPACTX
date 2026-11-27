import React, { useState, useRef } from 'react'
import {
  Camera, Upload, Sprout, Bug, FlaskConical, Layers,
  Loader2, X, CheckCircle, AlertTriangle,
  Mic, MicOff, MapPin, ShieldAlert, Droplets, Stethoscope, MessageSquare
} from 'lucide-react'
import { scanApi } from '../api/client'
import { useI18n } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'

const LANG_BCP47 = {
  kn: 'kn-IN',
  hi: 'hi-IN',
  ta: 'ta-IN',
  te: 'te-IN',
  mr: 'mr-IN',
  en: 'en-IN',
}

const MODES = [
  { id: 1, name: 'Crop Info',  nameKn: 'ಬೆಳೆ ಮಾಹಿತಿ',     icon: Sprout,       color: 'green', description: 'Identify crop & cultivation guide' },
  { id: 2, name: 'Disease',    nameKn: 'ರೋಗ ಪತ್ತೆ',        icon: Bug,          color: 'red',   description: 'Diagnose disease & treatment' },
  { id: 3, name: 'Fertilizer', nameKn: 'ರಸಗೊಬ್ಬರ / ಔಷಧಿ', icon: FlaskConical, color: 'blue',  description: 'Scan product label for dosage' },
  { id: 4, name: 'Soil',       nameKn: 'ಮಣ್ಣು ವಿಶ್ಲೇಷಣೆ',  icon: Layers,       color: 'amber', description: 'Soil type & suitable crops' },
]

const COLOR_MAP = {
  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800', btn: 'bg-green-600 hover:bg-green-700', active: 'ring-green-500 bg-green-600 text-white' },
  red:   { bg: 'bg-red-50',   border: 'border-red-200',   text: 'text-red-700',   badge: 'bg-red-100 text-red-800',     btn: 'bg-red-600 hover:bg-red-700',     active: 'ring-red-500 bg-red-600 text-white' },
  blue:  { bg: 'bg-blue-50',  border: 'border-blue-200',  text: 'text-blue-700',  badge: 'bg-blue-100 text-blue-800',   btn: 'bg-blue-600 hover:bg-blue-700',   active: 'ring-blue-500 bg-blue-600 text-white' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800', btn: 'bg-amber-600 hover:bg-amber-700', active: 'ring-amber-500 bg-amber-600 text-white' },
}

const SAMPLE_PRESETS = [
  { label: 'Crop (Paddy)',     mode: 1, file: '/samples/sample_paddy.jpg',       name: 'sample_paddy.jpg' },
  { label: 'Leaf Blight',      mode: 2, file: '/samples/sample_leaf_blight.jpg', name: 'sample_leaf_blight.jpg' },
  { label: 'Pesticide Bottle', mode: 3, file: '/samples/sample_pesticide.jpg',   name: 'sample_pesticide.jpg' },
  { label: 'Soil',             mode: 4, file: '/samples/sample_soil.jpg',        name: 'sample_soil.jpg' },
]

function formatRangeOrValue(val, unit = '') {
  if (val == null || val === '') return null
  if (typeof val === 'object') {
    if (val.min != null && val.max != null && (val.min !== 0 || val.max !== 0)) {
      return `${val.min}–${val.max}${unit ? ` ${unit}` : ''}`
    }
    if (val.row != null && val.plant != null && (val.row !== 0 || val.plant !== 0)) {
      return `${val.row} × ${val.plant}${unit ? ` ${unit}` : ''}`
    }
    if (val.total != null && val.total !== 0) {
      return `${val.total}${unit ? ` ${unit}` : ''}`
    }
    return null
  }
  if (val === 0) return null
  return `${val}${unit ? ` ${unit}` : ''}`
}

function SectionBlock({ icon: Icon, title, accentClass, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2 shadow-2xs">
      <div className="flex items-center gap-1.5 pb-1.5 border-b border-gray-100">
        <Icon className={`w-4 h-4 shrink-0 ${accentClass}`} />
        <h4 className="text-xs font-bold uppercase tracking-wide text-gray-700">{title}</h4>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function Row({ label, value }) {
  if (!value) return null
  return (
    <div className="flex gap-2">
      <p className="text-xs font-semibold text-gray-500 w-28 flex-shrink-0">{label}</p>
      <p className="text-xs text-gray-800 flex-1 leading-relaxed">{value}</p>
    </div>
  )
}

function BulletList({ label, items, badgeClass = 'bg-gray-50 text-gray-800' }) {
  if (!Array.isArray(items) || items.length === 0) return null
  return (
    <div>
      {label && <p className="text-[11px] font-semibold text-gray-500 mb-1">{label}</p>}
      <ul className="space-y-1">
        {items.map((item, idx) => (
          <li key={idx} className={`text-xs rounded-lg px-2.5 py-1.5 ${badgeClass}`}>
            • {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

function StructuredScanReport({ data, effectiveMode, onReset }) {
  if (data.is_blurry_or_unreadable || effectiveMode === 'blurry') {
    return (
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 space-y-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-amber-900">Photo Too Blurry or Unclear</h4>
            <p className="text-xs text-amber-800 leading-relaxed">
              {data.retake_photo_message || data.formatted_whatsapp_reply || 'Please retake a closer, sharper, well-lit photo so the label or crop symptoms can be read accurately.'}
            </p>
          </div>
        </div>
        <button
          onClick={onReset}
          className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold"
        >
          Retake / Upload Clear Photo
        </button>
      </div>
    )
  }

  const dosage = data.dosage && typeof data.dosage === 'object' ? data.dosage : null
  const hasDosage = dosage && (dosage.per_litre || dosage.per_knapsack_15L || dosage.per_barrel_200L || dosage.per_acre)
  const heightText = formatRangeOrValue(data.crop_height_cm, 'cm')
  const spacingText = formatRangeOrValue(data.spacing_cm, 'cm')
  const waterText = formatRangeOrValue(data.water_requirement_mm, 'mm')
  const yieldText = formatRangeOrValue(data.expected_yield_tons_per_ha, 't/ha')

  return (
    <div className="space-y-3">
      {/* Direct Answer to Farmer's Question */}
      {data.direct_answer_to_question && (
        <div className="bg-emerald-600 text-white rounded-xl p-3 space-y-1 shadow-xs">
          <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-emerald-100">
            <MessageSquare className="w-3.5 h-3.5" />
            Answer to Your Question
          </div>
          <p className="text-xs leading-relaxed">{data.direct_answer_to_question}</p>
        </div>
      )}

      {/* 1. Diagnosis / Product Identified */}
      <SectionBlock icon={Stethoscope} title="Diagnosis / Product Identified" accentClass="text-emerald-600">
        {data.product_name && <Row label="Product Name" value={data.product_name} />}
        {data.type && <Row label="Product Type" value={data.type} />}
        {data.manufacturer && <Row label="Manufacturer" value={data.manufacturer} />}
        {data.active_ingredient && <Row label="Active / NPK" value={data.active_ingredient} />}

        {data.detected_crop && <Row label="Crop" value={data.detected_crop} />}
        {data.disease_name && <Row label="Disease / Pest" value={data.disease_name} />}
        {data.severity && <Row label="Severity" value={data.severity} />}
        {Array.isArray(data.affected_parts) && data.affected_parts.length > 0 && (
          <Row label="Affected Parts" value={data.affected_parts.join(', ')} />
        )}
        {data.symptoms && <Row label="Symptoms" value={data.symptoms} />}
        {data.cause && <Row label="Cause (Weather)" value={data.cause} />}

        {data.lifespan && <Row label="Lifespan" value={data.lifespan} />}
        {Array.isArray(data.suitable_soil) && data.suitable_soil.length > 0 && (
          <Row label="Suitable Soil" value={data.suitable_soil.join(', ')} />
        )}
        {yieldText && <Row label="Expected Yield" value={yieldText} />}
        {data.msp_rs_per_quintal > 0 && (
          <Row label="MSP" value={`₹${Number(data.msp_rs_per_quintal).toLocaleString('en-IN')}/quintal`} />
        )}

        {data.soil_type && <Row label="Soil Type" value={data.soil_type} />}
        {data.characteristics && typeof data.characteristics === 'object' && Object.values(data.characteristics).some(Boolean) && (
          <div className="grid grid-cols-2 gap-1.5 pt-1">
            {Object.entries(data.characteristics).map(([k, v]) => v ? (
              <div key={k} className="bg-amber-50 rounded-lg p-2">
                <p className="text-[10px] text-amber-600 capitalize">{k.replace(/_/g, ' ')}</p>
                <p className="text-xs font-semibold text-amber-900">{v}</p>
              </div>
            ) : null)}
          </div>
        )}
        <BulletList label="Deficiencies" items={data.deficiencies} badgeClass="bg-amber-50 text-amber-900" />
      </SectionBlock>

      {/* 2. Uses & Solution */}
      <SectionBlock icon={Sprout} title="Uses & Solution" accentClass="text-blue-600">
        {data.purpose && <Row label="Uses / Purpose" value={data.purpose} />}
        <BulletList label="Target Uses" items={data.uses} badgeClass="bg-blue-50 text-blue-900" />
        {Array.isArray(data.crops_suitable) && data.crops_suitable.length > 0 && (
          <Row label="Suitable Crops" value={data.crops_suitable.join(', ')} />
        )}
        <BulletList label="Organic Treatments" items={data.organic_treatments} badgeClass="bg-green-50 text-green-800" />
        <BulletList label="Chemical Treatments" items={data.chemical_treatments} badgeClass="bg-blue-50 text-blue-800" />
        {data.recommended_fertilizers && <Row label="Nutrition Support" value={data.recommended_fertilizers} />}
        <BulletList label="Cultivation Steps" items={data.cultivation_steps} badgeClass="bg-green-50 text-green-800" />
        <BulletList label="Soil Amendments" items={data.amendments_recommended} badgeClass="bg-amber-50 text-amber-900" />
        {Array.isArray(data.ranked_suitable_crops) && data.ranked_suitable_crops.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <p className="text-[11px] font-semibold text-gray-500">Recommended Crops</p>
            {data.ranked_suitable_crops.map((c, idx) => (
              <div key={idx} className="flex gap-2 items-start bg-green-50 rounded-lg p-2">
                <span className="w-5 h-5 rounded-full bg-green-600 text-white text-[10px] flex items-center justify-center font-bold shrink-0">
                  {c.rank || idx + 1}
                </span>
                <div>
                  <p className="text-xs font-semibold text-gray-800">{c.crop}</p>
                  <p className="text-[11px] text-gray-600">{c.reason}</p>
                </div>
              </div>
            ))}
          </div>
        )}
        {data.current_weather_context && <Row label="Weather Context" value={data.current_weather_context} />}
      </SectionBlock>

      {/* 3. Dosage & Method */}
      <SectionBlock icon={Droplets} title="Dosage & Method" accentClass="text-sky-600">
        {hasDosage && (
          <div className="bg-blue-50 rounded-lg p-2.5 space-y-1">
            {dosage.per_litre && <Row label="Per Litre" value={dosage.per_litre} />}
            {dosage.per_knapsack_15L && <Row label="Per 15L Knapsack" value={dosage.per_knapsack_15L} />}
            {dosage.per_barrel_200L && <Row label="Per 200L Barrel" value={dosage.per_barrel_200L} />}
            {dosage.per_acre && <Row label="Per Acre" value={dosage.per_acre} />}
          </div>
        )}
        {data.using_method && <Row label="Using Method" value={data.using_method} />}
        {data.application_method && <Row label="Application" value={data.application_method} />}
        {data.spray_frequency && <Row label="Spray Frequency" value={data.spray_frequency} />}
        {Array.isArray(data.recommended_pesticides) && data.recommended_pesticides.length > 0 && (
          <Row label="Recommended" value={data.recommended_pesticides.join(', ')} />
        )}
        {data.suitable_weather && <Row label="Spray Weather" value={data.suitable_weather} />}
        {heightText && <Row label="Crop Height" value={heightText} />}
        {spacingText && <Row label="Spacing" value={spacingText} />}
        {waterText && <Row label="Water Need" value={waterText} />}
        {data.irrigation_method && <Row label="Irrigation" value={data.irrigation_method} />}
        {data.harvest_timing && <Row label="Harvest Timing" value={data.harvest_timing} />}
      </SectionBlock>

      {/* 4. Safety Cautions */}
      <SectionBlock icon={ShieldAlert} title="Safety Cautions" accentClass="text-red-600">
        <BulletList label="Precautions & PHI" items={data.safety_cautions} badgeClass="bg-red-50 text-red-800" />
        <BulletList label="Side Effects / Risks" items={data.side_effects} badgeClass="bg-amber-50 text-amber-900" />
        {data.mfr_date_check && <Row label="Expiry Check" value={data.mfr_date_check} />}
        {data.prevention && <Row label="Prevention" value={data.prevention} />}
        <BulletList label="Not Recommended" items={data.not_recommended} badgeClass="bg-red-50 text-red-800" />
      </SectionBlock>
    </div>
  )
}

export default function CameraScanner() {
  const { lang } = useI18n()
  const { location } = useLocationContext()

  const [mode, setMode] = useState(1)
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [question, setQuestion] = useState('')
  const [isListeningQuestion, setIsListeningQuestion] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const fileInputRef = useRef(null)
  const cameraInputRef = useRef(null)
  const speechRecRef = useRef(null)

  const loadSamplePreset = async (preset) => {
    try {
      setError(null)
      setResult(null)
      setMode(preset.mode)
      const res = await fetch(preset.file)
      const blob = await res.blob()
      const file = new File([blob], preset.name, { type: 'image/jpeg' })
      setImageFile(file)
      setImagePreview(preset.file)
    } catch {
      setError('Failed to load sample image.')
    }
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setImageFile(file)
    setResult(null)
    setError(null)
    const reader = new FileReader()
    reader.onload = ev => setImagePreview(ev.target.result)
    reader.readAsDataURL(file)
  }

  const toggleQuestionVoice = () => {
    if (isListeningQuestion) {
      speechRecRef.current?.stop()
      setIsListeningQuestion(false)
      return
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setError('Voice input for photo questions is not supported in this browser; please type your question.')
      return
    }
    const rec = new SpeechRecognition()
    rec.lang = LANG_BCP47[lang] || 'en-IN'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (ev) => {
      const spoken = ev.results?.[0]?.[0]?.transcript || ''
      setQuestion(prev => (prev ? `${prev} ${spoken}` : spoken))
      setIsListeningQuestion(false)
    }
    rec.onerror = () => setIsListeningQuestion(false)
    rec.onend = () => setIsListeningQuestion(false)
    speechRecRef.current = rec
    setIsListeningQuestion(true)
    rec.start()
  }

  const handleScan = async () => {
    if (!imageFile) return
    setScanning(true)
    setError(null)
    setResult(null)

    const fd = new FormData()
    fd.append('image', imageFile)
    fd.append('mode', mode)
    fd.append('language', LANG_BCP47[lang] || 'en-IN')
    if (question.trim()) fd.append('question', question.trim())
    if (location?.lat != null) fd.append('lat', String(location.lat))
    if (location?.lon != null) fd.append('lon', String(location.lon))
    if (location?.location_name) fd.append('location_name', location.location_name)

    try {
      const r = await scanApi.scan(fd)
      setResult(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Live Gemini scan failed. Please try again.')
    } finally {
      setScanning(false)
    }
  }

  const reset = () => {
    setImageFile(null)
    setImagePreview(null)
    setQuestion('')
    setResult(null)
    setError(null)
  }

  const activeMode = MODES.find(m => m.id === mode)
  const colors = COLOR_MAP[activeMode.color]

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-green-700 to-green-600 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Camera className="w-5 h-5 text-white shrink-0" />
          <div className="min-w-0">
            <h2 className="text-white font-bold text-sm truncate">Smart Crop Scanner</h2>
            <p className="text-green-200 text-xs truncate">ಸ್ಮಾರ್ಟ್ ಕ್ಯಾಮೆರಾ ಸ್ಕ್ಯಾನರ್</p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-green-100 bg-white/15 px-2 py-1 rounded-full max-w-[160px] truncate">
          <MapPin className="w-3 h-3 shrink-0" />
          <span className="truncate">{location?.location_name || 'Set location'}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Mode selector */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Select Scan Mode</p>
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            {MODES.map(m => {
              const c = COLOR_MAP[m.color]
              const Icon = m.icon
              const isActive = mode === m.id
              return (
                <button
                  key={m.id}
                  onClick={() => { setMode(m.id); setResult(null) }}
                  className={`flex items-center gap-2 p-2.5 rounded-xl border-2 text-left transition-all min-w-0 ${
                    isActive
                      ? `ring-2 ${c.active} border-transparent`
                      : `${c.bg} ${c.border} ${c.text} hover:opacity-80`
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : ''}`} />
                  <div className="min-w-0">
                    <p className={`text-xs font-bold truncate ${isActive ? 'text-white' : ''}`}>{m.name}</p>
                    <p className={`text-[10px] leading-tight truncate ${isActive ? 'text-white/80' : 'opacity-70'}`}>{m.nameKn}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Try Sample Photo Preset Buttons */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wide">Try Sample Photo</p>
          <div className="flex flex-wrap gap-2 items-center">
            {SAMPLE_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => loadSamplePreset(preset)}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-gray-100 hover:bg-green-50 hover:text-green-700 hover:border-green-300 border border-gray-200 text-gray-700 transition-colors text-center shrink-0 min-w-0"
                title={`Try ${preset.label}`}
              >
                📸 {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Image input */}
        {!imagePreview ? (
          <div className="flex gap-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className={`flex-1 flex flex-col items-center gap-1.5 py-6 rounded-xl border-2 border-dashed ${colors.border} ${colors.bg} ${colors.text} hover:opacity-80 transition-opacity`}
            >
              <Upload className="w-6 h-6" />
              <span className="text-xs font-medium">Upload Photo</span>
            </button>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className={`flex-1 flex flex-col items-center gap-1.5 py-6 rounded-xl border-2 border-dashed ${colors.border} ${colors.bg} ${colors.text} hover:opacity-80 transition-opacity`}
            >
              <Camera className="w-6 h-6" />
              <span className="text-xs font-medium">Take Photo</span>
            </button>
            <input ref={fileInputRef}   type="file" accept="image/*" className="hidden" onChange={handleFileSelect} />
            <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFileSelect} />
          </div>
        ) : (
          <div className="relative rounded-xl overflow-hidden border border-gray-200">
            <img src={imagePreview} alt="Selected" className="w-full h-40 object-cover" />
            <button onClick={reset} className="absolute top-2 right-2 bg-black/60 text-white rounded-full p-1 hover:bg-black/80">
              <X className="w-4 h-4" />
            </button>
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
              <p className="text-white text-xs">{imageFile?.name}</p>
            </div>
          </div>
        )}

        {/* Optional Photo Question Input (Text + Voice) */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-gray-600">
            Ask a specific question about this photo (optional)
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder='e.g., "Can I spray this on paddy during flowering?"'
              disabled={scanning}
              className="flex-1 text-xs rounded-xl border border-gray-300 px-3 py-2 bg-gray-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <button
              type="button"
              onClick={toggleQuestionVoice}
              disabled={scanning}
              className={`w-9 h-9 rounded-xl flex items-center justify-center border transition-colors shrink-0 ${
                isListeningQuestion
                  ? 'bg-red-500 text-white border-red-600 animate-pulse'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-green-50 hover:text-green-700'
              }`}
              title={isListeningQuestion ? 'Stop listening' : 'Speak your question'}
            >
              {isListeningQuestion ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Scan button */}
        {imageFile && !result && (
          <button
            onClick={handleScan}
            disabled={scanning}
            className={`w-full py-3 rounded-xl text-white font-semibold flex items-center justify-center gap-2 transition-all ${colors.btn} disabled:opacity-60`}
          >
            {scanning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing with Live Gemini…</>
            ) : (
              <><Camera className="w-4 h-4" /> Analyze with {activeMode.name}</>
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start justify-between gap-2">
            <div className="flex gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-700">{error}</p>
            </div>
            {imageFile && (
              <button
                onClick={handleScan}
                className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700 shrink-0"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Result card */}
        {result && (
          <div className={`${colors.bg} ${colors.border} border rounded-xl p-3.5 space-y-3`}>
            <div className="flex items-center gap-2">
              <CheckCircle className={`w-4 h-4 ${colors.text} shrink-0`} />
              <span className={`text-xs font-bold uppercase tracking-wide ${colors.text} truncate`}>
                {result.analysis?.mode_name || activeMode.name} – Live Gemini Analysis
              </span>
              <span className="ml-auto text-[11px] text-gray-500 shrink-0">{result.file_size_kb} KB</span>
            </div>

            <StructuredScanReport
              data={result.analysis || result.result || {}}
              effectiveMode={result.mode}
              onReset={reset}
            />

            <button onClick={reset} className="mt-2 w-full text-xs text-gray-500 underline hover:text-gray-700">
              Scan another image
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
