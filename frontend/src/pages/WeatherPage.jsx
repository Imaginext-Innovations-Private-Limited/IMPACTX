import React, { useState, useEffect } from 'react'
import {
  Cloud, Sun, CloudRain, CloudSun, CloudFog, CloudLightning,
  Droplets, Wind, Thermometer, MapPin, AlertTriangle, CheckCircle2,
  Sprout, FlaskConical, Droplet, Calendar, Table, LayoutGrid,
  RefreshCw, Info, ArrowUpRight
} from 'lucide-react'
import { weatherApi } from '../api/client'
import { useI18n } from '../context/I18nContext'

const WEATHER_ICONS = {
  Sun: Sun,
  CloudSun: CloudSun,
  Cloud: Cloud,
  CloudRain: CloudRain,
  CloudFog: CloudFog,
  CloudLightning: CloudLightning,
  CloudDrizzle: CloudRain,
}

const ADVISORY_COLORS = {
  red: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-600 text-white',
    text: 'text-red-950',
    iconColor: 'text-red-600',
  },
  green: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    badge: 'bg-emerald-600 text-white',
    text: 'text-emerald-950',
    iconColor: 'text-emerald-600',
  },
  emerald: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    badge: 'bg-emerald-600 text-white',
    text: 'text-emerald-950',
    iconColor: 'text-emerald-600',
  },
  blue: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-600 text-white',
    text: 'text-blue-950',
    iconColor: 'text-blue-600',
  },
  amber: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'bg-amber-600 text-white',
    text: 'text-amber-950',
    iconColor: 'text-amber-700',
  },
  cyan: {
    bg: 'bg-cyan-50',
    border: 'border-cyan-200',
    badge: 'bg-cyan-700 text-white',
    text: 'text-cyan-950',
    iconColor: 'text-cyan-600',
  },
  sky: {
    bg: 'bg-sky-50',
    border: 'border-sky-200',
    badge: 'bg-sky-600 text-white',
    text: 'text-sky-950',
    iconColor: 'text-sky-600',
  },
}

export default function WeatherPage() {
  const { lang, t } = useI18n()
  const [locations, setLocations] = useState([])
  const [selectedLoc, setSelectedLoc] = useState(null)
  const [weatherData, setWeatherData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('cards') // 'cards' or 'table'

  // Load locations on mount
  useEffect(() => {
    weatherApi.getLocations()
      .then(res => {
        setLocations(res.data)
        if (res.data.length > 0) {
          // Default to Bengaluru or first location
          const defaultLoc = res.data.find(l => l.id === 'bengaluru') || res.data[0]
          setSelectedLoc(defaultLoc)
        }
      })
      .catch(() => {})
  }, [])

  // Fetch forecast whenever selectedLoc or language changes
  useEffect(() => {
    if (!selectedLoc) return
    setLoading(true)
    const langCode = lang ? (lang.includes('-') ? lang : `${lang}-IN`) : 'kn-IN'
    weatherApi.getForecast(
      selectedLoc.lat,
      selectedLoc.lon,
      selectedLoc.name,
      selectedLoc.state,
      langCode
    )
      .then(res => {
        setWeatherData(res.data)
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })
  }, [selectedLoc, lang])

  const renderWeatherIcon = (iconName, className = 'w-6 h-6') => {
    const IconComponent = WEATHER_ICONS[iconName] || CloudSun
    return <IconComponent className={className} />
  }

  const renderAdvisoryIcon = (iconName) => {
    switch (iconName) {
      case 'AlertTriangle': return <AlertTriangle className="w-5 h-5" />
      case 'CheckCircle2':  return <CheckCircle2 className="w-5 h-5" />
      case 'Sprout':        return <Sprout className="w-5 h-5" />
      case 'FlaskConical':  return <FlaskConical className="w-5 h-5" />
      case 'DropletOff':    return <Droplet className="w-5 h-5" />
      default:              return <Droplets className="w-5 h-5" />
    }
  }

  return (
    <div className="px-4 py-4 space-y-5 max-w-4xl mx-auto">
      {/* Top Location Selector Header */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-sky-100 flex items-center justify-center text-sky-600">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base sm:text-lg font-bold text-gray-800 flex items-center gap-2">
              {t('weather_page_title', '16-Day Weather & Agricultural Advisory')}
            </h1>
            <p className="text-xs text-gray-500">
              {weatherData?.labels?.agro_forecast_subtitle || t('weather_subtitle', 'Open-Meteo High-Resolution Agro-Forecast · Pan-India Zones')}
            </p>
          </div>
        </div>

        {/* District Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 font-medium">{t('district_label', 'District / Region:')}</label>
          <select
            value={selectedLoc?.id || ''}
            onChange={(e) => {
              const loc = locations.find(l => l.id === e.target.value)
              if (loc) setSelectedLoc(loc)
            }}
            className="text-xs sm:text-sm bg-gray-50 border border-gray-300 rounded-xl px-3 py-2 font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
          >
            {locations.map(l => {
              const nativeAlias = l.name_kannada ? ` (${l.name_kannada})` : ''
              const region = l.zone || l.state || ''
              const regionLabel = l.state && l.zone && !l.zone.includes(l.state) ? `${region}, ${l.state}` : region
              return (
                <option key={l.id} value={l.id}>
                  {l.name}{nativeAlias} — {regionLabel || l.state}
                </option>
              )
            })}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 flex flex-col items-center justify-center text-gray-400 gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-600" />
          <p className="text-sm">Fetching live 16-day weather & calculating farm action advisories…</p>
        </div>
      ) : !weatherData ? (
        <div className="text-center py-12 text-gray-400">Failed to load weather data.</div>
      ) : (
        <>
          {/* RULE-BASED FARM ACTION ADVISORY BANNER */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                {weatherData.labels?.live_farm_action_advisories || t('live_advisories_heading', 'Live Farm Action Advisories')} for {selectedLoc?.name}
              </h2>
              <span className="text-[11px] text-gray-400">
                {weatherData.labels?.rule_based_engine || t('rule_based_engine', 'Rule-based Agri Engine')}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {weatherData.advisories?.map((adv, idx) => {
                const colorTheme = ADVISORY_COLORS[adv.badge_color] || ADVISORY_COLORS.blue
                return (
                  <div
                    key={idx}
                    className={`${colorTheme.bg} border ${colorTheme.border} rounded-2xl p-4 shadow-sm flex flex-col justify-between transition-all hover:shadow`}
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${colorTheme.badge}`}>
                          {adv.category_localized || adv.category}
                        </span>
                        <div className={colorTheme.iconColor}>
                          {renderAdvisoryIcon(adv.icon)}
                        </div>
                      </div>

                      <h3 className={`text-sm font-bold ${colorTheme.text} leading-snug`}>
                        {adv.title}
                      </h3>
                      {(adv.title_localized || adv.title_kannada) && (
                        <p className="text-xs font-semibold text-emerald-950/80 mt-0.5">
                          {adv.title_localized || adv.title_kannada}
                        </p>
                      )}

                      <p className="text-xs text-gray-700 mt-2 leading-relaxed">
                        {adv.action}
                      </p>
                    </div>

                    {(adv.action_localized || adv.action_kannada) && (
                      <div className="mt-3 pt-2 border-t border-black/5 text-[11px] text-gray-600 italic">
                        🌾 {adv.action_localized || adv.action_kannada}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* CURRENT CONDITIONS HERO CARD */}
          <div className="bg-gradient-to-br from-sky-600 via-blue-600 to-indigo-700 rounded-3xl p-5 sm:p-6 text-white shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-white/20 backdrop-blur-md px-2.5 py-0.5 rounded-full font-medium text-sky-100">
                    {selectedLoc?.zone || selectedLoc?.state || 'Pan-India'}
                  </span>
                  <span className="text-xs text-sky-200">
                    {weatherData.is_live ? '• Live Open-Meteo' : '• Agro-Meteo Cache'}
                  </span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-extrabold mt-1">
                  {selectedLoc?.name}
                  {selectedLoc?.name_kannada ? (
                    <span className="text-lg font-normal text-sky-200 ml-2">({selectedLoc.name_kannada})</span>
                  ) : null}
                </h2>
                <p className="text-sm text-sky-100 mt-0.5">
                  {weatherData.current?.weather_desc}
                  {(weatherData.current?.weather_localized || weatherData.current?.weather_kannada) ? ` · ${weatherData.current.weather_localized || weatherData.current.weather_kannada}` : ''}
                </p>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-4xl sm:text-5xl font-black tracking-tight">
                    {weatherData.current?.temp}°C
                  </div>
                  <p className="text-xs text-sky-200">Current Temperature</p>
                </div>
                <div className="p-3 bg-white/15 rounded-2xl backdrop-blur-md">
                  {renderWeatherIcon(weatherData.daily?.[0]?.icon || 'Sun', 'w-12 h-12 text-yellow-300')}
                </div>
              </div>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4 border-t border-white/20 text-xs">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-2.5">
                <span className="flex items-center gap-1.5 text-sky-200">
                  <Droplets className="w-3.5 h-3.5" /> Relative Humidity
                </span>
                <p className="text-base font-bold mt-0.5">{weatherData.current?.humidity}%</p>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-2.5">
                <span className="flex items-center gap-1.5 text-sky-200">
                  <Sprout className="w-3.5 h-3.5" /> Soil Moisture (0–7cm)
                </span>
                <p className="text-base font-bold mt-0.5">
                  {weatherData.current?.soil_moisture_pct}%
                  <span className="text-[10px] font-normal text-sky-200 ml-1">({weatherData.current?.soil_moisture} m³/m³)</span>
                </p>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-2.5">
                <span className="flex items-center gap-1.5 text-sky-200">
                  <Wind className="w-3.5 h-3.5" /> Wind Speed
                </span>
                <p className="text-base font-bold mt-0.5">{weatherData.current?.wind_speed_kmh} km/h</p>
              </div>

              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-2.5">
                <span className="flex items-center gap-1.5 text-sky-200">
                  <Sun className="w-3.5 h-3.5" /> Evapotranspiration (ET0)
                </span>
                <p className="text-base font-bold mt-0.5">
                  {weatherData.current?.et0} mm/day
                </p>
              </div>
            </div>
          </div>

          {/* 16-DAY FORECAST SECTION */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-sky-600" />
                  {weatherData.labels?.weather_outlook || t('outlook_16_day', '16-Day Weather & Soil Outlook')}
                </h3>
                <p className="text-xs text-gray-500">
                  {weatherData.labels?.outlook_sub || t('outlook_sub', 'Extended meteorological projections for crop planning and irrigation scheduling')}
                </p>
              </div>

              {/* View Toggle */}
              <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl text-xs">
                <button
                  onClick={() => setViewMode('cards')}
                  className={`p-1.5 rounded-lg flex items-center gap-1 transition-colors ${
                    viewMode === 'cards' ? 'bg-white shadow-sm font-bold text-sky-800' : 'text-gray-600'
                  }`}
                  title="Card View"
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Cards</span>
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`p-1.5 rounded-lg flex items-center gap-1 transition-colors ${
                    viewMode === 'table' ? 'bg-white shadow-sm font-bold text-sky-800' : 'text-gray-600'
                  }`}
                  title="Table View"
                >
                  <Table className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Table</span>
                </button>
              </div>
            </div>

            {/* CARDS VIEW */}
            {viewMode === 'cards' ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {weatherData.daily?.map((day, idx) => (
                  <div
                    key={day.date}
                    className={`rounded-2xl p-3 border transition-all ${
                      idx === 0
                        ? 'bg-sky-50/70 border-sky-300 ring-2 ring-sky-400/20'
                        : 'bg-gray-50/60 border-gray-200 hover:bg-white hover:shadow-sm'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-gray-800">{day.display_date}</span>
                      {idx === 0 && (
                        <span className="text-[10px] bg-sky-600 text-white px-1.5 py-0.2 rounded font-bold">
                          Today
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-gray-400 capitalize">{day.day_name}</p>

                    <div className="flex items-center justify-between my-2">
                      <div>
                        <span className="text-lg font-black text-gray-900">{day.temp_max}°</span>
                        <span className="text-xs text-gray-400 ml-1">{day.temp_min}°</span>
                      </div>
                      <div className="text-sky-600">
                        {renderWeatherIcon(day.icon, 'w-7 h-7')}
                      </div>
                    </div>

                    <p className="text-[11px] font-medium text-gray-700 truncate">{day.weather_desc}</p>
                    <p className="text-[10px] text-gray-400 truncate">{day.weather_localized || day.weather_kannada}</p>

                    {/* Rain & Soil Bars */}
                    <div className="mt-3 pt-2 border-t border-gray-200/60 space-y-1.5 text-[10px]">
                      <div className="flex justify-between items-center text-sky-800">
                        <span className="flex items-center gap-1">
                          <CloudRain className="w-3 h-3 text-sky-600" /> Rain:
                        </span>
                        <span className="font-semibold">
                          {day.precipitation_sum_mm}mm ({day.precipitation_prob_max}%)
                        </span>
                      </div>

                      <div className="flex justify-between items-center text-emerald-800">
                        <span className="flex items-center gap-1">
                          <Sprout className="w-3 h-3 text-emerald-600" /> Soil Moisture:
                        </span>
                        <span className="font-semibold">{day.soil_moisture_pct}%</span>
                      </div>

                      {/* Mini Moisture Bar */}
                      <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${Math.min(day.soil_moisture_pct * 2, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* TABLE VIEW */
              <div className="overflow-x-auto">
                <table className="w-full text-xs sm:text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 text-left uppercase text-[11px]">
                      <th className="py-2.5 px-3 rounded-l-lg">Date</th>
                      <th className="py-2.5 px-3">Condition</th>
                      <th className="py-2.5 px-3 text-right">Max / Min Temp</th>
                      <th className="py-2.5 px-3 text-right">Precipitation</th>
                      <th className="py-2.5 px-3 text-right">Rain Chance</th>
                      <th className="py-2.5 px-3 text-right">Soil Moisture (0–7cm)</th>
                      <th className="py-2.5 px-3 text-right rounded-r-lg">ET0</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {weatherData.daily?.map((d, i) => (
                      <tr key={d.date} className={`hover:bg-sky-50/50 transition-colors ${i === 0 ? 'bg-sky-50/40 font-semibold' : ''}`}>
                        <td className="py-3 px-3">
                          <div className="font-bold text-gray-800">{d.display_date}</div>
                          <div className="text-[10px] text-gray-400">{d.day_name}</div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            {renderWeatherIcon(d.icon, 'w-5 h-5 text-sky-600')}
                            <div>
                              <p className="font-medium text-gray-800">{d.weather_desc}</p>
                              <p className="text-[10px] text-gray-400">{d.weather_localized || d.weather_kannada}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <span className="font-bold text-gray-900">{d.temp_max}°C</span>
                          <span className="text-gray-400 text-xs ml-1">/ {d.temp_min}°C</span>
                        </td>
                        <td className="py-3 px-3 text-right font-medium text-sky-800">
                          {d.precipitation_sum_mm > 0 ? `${d.precipitation_sum_mm} mm` : '0 mm'}
                        </td>
                        <td className="py-3 px-3 text-right font-medium">
                          <span className={`px-2 py-0.5 rounded-full text-xs ${
                            d.precipitation_prob_max > 60 ? 'bg-red-100 text-red-700 font-bold' :
                            d.precipitation_prob_max > 25 ? 'bg-sky-100 text-sky-700' : 'text-gray-500'
                          }`}>
                            {d.precipitation_prob_max}%
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <span className="font-bold text-emerald-800">{d.soil_moisture_pct}%</span>
                          <span className="text-xs text-gray-400 ml-1">({d.soil_moisture_m3_m3})</span>
                        </td>
                        <td className="py-3 px-3 text-right text-gray-600 font-medium">
                          {d.et0_evapotranspiration} mm
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
