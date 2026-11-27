import React, { useState, useEffect } from 'react'
import CameraScanner from '../components/CameraScanner'
import { Cloud, BarChart2, Sprout, Droplets, Sun, Thermometer, ArrowRight, ExternalLink, MessageSquare } from 'lucide-react'
import { useI18n } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'
import { weatherApi } from '../api/client'

const GREETINGS = {
  kn: 'ನಮಸ್ಕಾರ · ಶುಭೋದಯ',
  hi: 'नमस्ते · शुभ प्रभात',
  te: 'నమస్కారం · శుభోదయం',
  ta: 'வணக்கம் · காலை வணக்கம்',
  mr: 'नमस्कार · शुभ प्रभात',
  en: 'Namaskara · Good morning',
}

function WeatherWidget({ onNavigate }) {
  const { t } = useI18n()
  const { location } = useLocationContext()
  const [weatherData, setWeatherData] = useState(null)

  const activeLat = location?.lat ?? 13.9299
  const activeLon = location?.lon ?? 75.5681
  const activeName = location?.location_name || location?.district || 'Shimoga'

  useEffect(() => {
    let cancelled = false
    weatherApi.getForecast(activeLat, activeLon, activeName)
      .then((res) => {
        if (!cancelled && res?.data) {
          setWeatherData(res.data)
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [activeLat, activeLon, activeName])

  const currentTemp = weatherData?.current?.temp_c ?? weatherData?.current?.temperature ?? 26
  const humidity = weatherData?.current?.humidity_pct ?? weatherData?.current?.humidity ?? 72
  const minTemp = weatherData?.daily?.[0]?.temp_min ?? weatherData?.current?.temp_min ?? 19
  const conditionText = weatherData?.current?.condition || t('partly_cloudy')

  return (
    <div
      onClick={() => onNavigate && onNavigate('weather')}
      className="bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-600 rounded-2xl p-4 text-white shadow-lg cursor-pointer hover:shadow-xl transition-all group min-w-0"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-sky-200 text-xs font-medium">
            <span className="truncate">Today's Weather · {activeName} (16-Day Forecast)</span>
            <ArrowRight className="w-3.5 h-3.5 shrink-0 group-hover:translate-x-1 transition-transform" />
          </div>
          <p className="text-2xl font-bold mt-0.5">{Math.round(currentTemp)}°C</p>
        </div>
        <Sun className="w-10 h-10 text-yellow-300 shrink-0" />
      </div>
      <div className="flex flex-wrap gap-2 sm:gap-4 text-xs text-sky-100">
        <span className="flex items-center gap-1 shrink-0"><Droplets className="w-3 h-3 shrink-0" /> {humidity}% {t('humidity')}</span>
        <span className="flex items-center gap-1 shrink-0"><Cloud className="w-3 h-3 shrink-0" /> {conditionText}</span>
        <span className="flex items-center gap-1 shrink-0"><Thermometer className="w-3 h-3 shrink-0" /> {t('min_temp')} {Math.round(minTemp)}°C</span>
      </div>
      <div className="mt-3 text-xs text-sky-100 bg-white/15 rounded-lg px-3 py-1.5 flex items-center justify-between gap-2 min-w-0">
        <span className="truncate">{t('rabi_weather_tip')}</span>
      </div>
    </div>
  )
}

function QuickStats({ onSelectCommodity, onNavigate }) {
  const { t, getCommodityName } = useI18n()
  const stats = [
    { name: 'Areca Nut (Chali)', labelKey: 'areca_price', value: '₹44,500', sub: `+2.9% ${t('today_diff')}`,  color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { name: 'Paddy (Fine)',      labelKey: 'paddy_msp',   value: '₹2,183',  sub: t('per_quintal'),   color: 'text-blue-600',    bg: 'bg-blue-50' },
    { name: 'Black Pepper',      labelKey: 'pepper',       value: '₹52,000', sub: `-3.7% ${t('today_diff')}`,  color: 'text-red-500',     bg: 'bg-red-50' },
    { name: 'Ginger (Fresh)',    labelKey: 'ginger',       value: '₹3,200',  sub: `+8.5% ${t('today_diff')}`,  color: 'text-emerald-600', bg: 'bg-emerald-50' },
  ]
  return (
    <div className="grid grid-cols-2 gap-2 sm:gap-3">
      {stats.map(s => (
        <button
          key={s.name}
          onClick={() => {
            if (onSelectCommodity) onSelectCommodity(s.name)
            else if (onNavigate) onNavigate('market')
          }}
          className={`${s.bg} rounded-xl p-3 text-left hover:ring-2 hover:ring-emerald-400 transition-all cursor-pointer min-w-0`}
        >
          <div className="flex flex-wrap items-center justify-between gap-1">
            <p className="text-xs text-gray-700 font-semibold truncate">{getCommodityName(s.name)}</p>
            <span className="text-[10px] text-gray-400 shrink-0">{t('analytics')} →</span>
          </div>
          <p className={`text-base sm:text-lg font-bold truncate ${s.color}`}>{s.value}</p>
          <p className={`text-xs ${s.color} opacity-80 font-medium truncate`}>{s.sub}</p>
        </button>
      ))}
    </div>
  )
}

function SectionHeader({ title, titleKn, icon: Icon, onMore, moreText }) {
  const { t } = useI18n()
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 mb-3 min-w-0">
      <div className="flex items-center gap-2 min-w-0">
        {Icon && <Icon className="w-4 h-4 text-emerald-600 shrink-0" />}
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-gray-800 truncate">{title}</h2>
          {titleKn && <p className="text-[10px] text-gray-400 truncate">{titleKn}</p>}
        </div>
      </div>
      {onMore && (
        <button
          onClick={onMore}
          className="text-xs text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 shrink-0"
        >
          {moreText || t('view_all')} <ArrowRight className="w-3 h-3 shrink-0" />
        </button>
      )}
    </div>
  )
}

function AgriTip({ onNavigate }) {
  const { lang, t } = useI18n()
  const tips = [
    {
      emoji: '🌧️',
      title: 'Post-monsoon advisory',
      text: 'Apply potash (MOP) @ 60 kg/ha for Areca before December to improve nut weight.',
      langText: {
        kn: 'ಅಡಿಕೆ ತೋಟಕ್ಕೆ ಡಿಸೆಂಬರ್ ಮೊದಲು ಪೊಟ್ಯಾಶ್ ಹಾಕಿ.',
        hi: 'सुपारी में दाने का वजन बढ़ाने के लिए दिसंबर से पहले पोटाश डालें।',
        te: 'పోకచెక్కలో గింజ బరువు పెరగడానికి డిసెంబర్ ముందు పొటాష్ వేయండి.',
        ta: 'பாக்கு மரங்களுக்கு டிசம்பருக்கு முன் பொட்டாஷ் இடவும்.',
        mr: 'सुपारीचे वजन वाढवण्यासाठी डिसेंबरपूर्वी पोटॅश टाकावे.',
        en: 'Apply potash (MOP) @ 60 kg/ha for Areca before December.',
      }
    },
    {
      emoji: '🐛',
      title: 'Pest alert',
      text: 'Yellow stem borer active in paddy. Apply Cartap Hydrochloride @ 500g/acre.',
      langText: {
        kn: 'ಭತ್ತದಲ್ಲಿ ಕಾಂಡ ಕೊರೆಯುವ ಹುಳು ಸಕ್ರಿಯ. ಕಾರ್ಟಾಪ್ ಹೈಡ್ರೋಕ್ಲೋರೈಡ್ ಬಳಸಿ.',
        hi: 'धान में तना छेदक सक्रिय है। कार्तप हाइड्रोक्लोराइड का प्रयोग करें।',
        te: 'వరిలో కాండం తొలుచు పురుగు నివారణకు కార్టాప్ హైడ్రోక్లోరైడ్ వాడండి.',
        ta: 'நெல்லில் தண்டு துளைப்பான் தாக்குதல். கார்டாப் ஹைட்ரோகுளோரைடு தெளிக்கவும்.',
        mr: 'भातावर खोडकीड सक्रिय. कार्टाप हायड्रोक्लोराईड वापरा.',
        en: 'Yellow stem borer active in paddy. Apply Cartap Hydrochloride.',
      }
    },
    {
      emoji: '💧',
      title: 'Water saving',
      text: 'SRI method saves 30% water in paddy. Transplant 12-day seedlings at 25×25 cm.',
      langText: {
        kn: 'SRI ಪದ್ಧತಿಯಲ್ಲಿ 30% ನೀರು ಉಳಿಸಿ. 12 ದಿನದ ಸಸಿಗಳನ್ನು ನಾಟಿ ಮಾಡಿ.',
        hi: 'एसआरआई पद्धति से धान में 30% पानी बचाएं। 12 दिन के पौधे रोपें।',
        te: 'SRI పద్ధతిలో 30% నీటిని ఆదా చేయండి. 12 రోజుల నారును నాటండి.',
        ta: 'SRI முறையில் 30% நீரை சேமியுங்கள். 12 நாள் நாற்றுகளை நடவும்.',
        mr: 'एसआरआय पद्धतीने भातामध्ये ३०% पाण्याची बचत करा.',
        en: 'SRI method saves 30% water in paddy. Transplant 12-day seedlings.',
      }
    },
  ]
  const tip = tips[Math.floor(Date.now() / 86400000) % tips.length]
  const localizedTip = tip.langText[lang] || tip.langText['en']

  return (
    <div
      onClick={() => onNavigate && onNavigate('news')}
      className="bg-amber-50 border border-amber-200 rounded-2xl p-4 cursor-pointer hover:bg-amber-100/70 transition-colors min-w-0"
    >
      <div className="flex items-start gap-3 min-w-0">
        <span className="text-2xl shrink-0">{tip.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-1 mb-0.5">
            <p className="text-xs font-bold text-amber-700 uppercase tracking-wide truncate">{tip.title}</p>
            <span className="text-[10px] text-amber-700 font-semibold shrink-0">{t('news')} →</span>
          </div>
          <p className="text-sm text-amber-900 leading-snug">{tip.text}</p>
          <p className="text-xs text-amber-700 mt-1 font-medium italic leading-snug">{localizedTip}</p>
        </div>
      </div>
    </div>
  )
}

export default function HomePage({ onSelectCommodity, onNavigate }) {
  const { lang, t } = useI18n()
  const greeting = GREETINGS[lang] || GREETINGS['en']

  return (
    <div className="px-3 sm:px-4 py-4 space-y-4 sm:space-y-5 max-w-2xl mx-auto min-w-0">
      {/* Greeting Banner & WhatsApp Simulator CTA */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <div className="min-w-0">
          <p className="text-xs text-emerald-700 font-medium">{greeting}</p>
          <h1 className="text-lg sm:text-xl font-bold text-gray-800 truncate">{t('app_title')}</h1>
          <p className="text-xs text-gray-500">November 2026 · Rabi Season 2026–27</p>
        </div>
        <button
          onClick={() => onNavigate && onNavigate('whatsapp')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors shrink-0"
        >
          <MessageSquare className="w-3.5 h-3.5 shrink-0" />
          <span>{t('whatsapp_sim_title')}</span>
        </button>
      </div>

      {/* Weather Widget with click to Weather page */}
      <WeatherWidget onNavigate={onNavigate} />

      {/* Daily tip with click to News */}
      <AgriTip onNavigate={onNavigate} />

      {/* Quick market stats with click to open 6-year analytics modal */}
      <div className="min-w-0">
        <SectionHeader
          title={t('mandi_rates_title')}
          titleKn={t('mandi_rates_sub')}
          icon={BarChart2}
          onMore={() => onNavigate && onNavigate('market')}
          moreText={t('view_all')}
        />
        <QuickStats onSelectCommodity={onSelectCommodity} onNavigate={onNavigate} />
      </div>

      {/* Camera scanner (Sprint 1 component, kept 100% intact) */}
      <div className="min-w-0">
        <SectionHeader
          title={t('scanner_title')}
          titleKn={t('scanner_sub')}
          icon={Sprout}
        />
        <CameraScanner />
      </div>

      {/* Spacer for bottom nav */}
      <div className="h-4" />
    </div>
  )
}
