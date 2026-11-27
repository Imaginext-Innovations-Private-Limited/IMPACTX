import React, { useState } from 'react'
import {
  Home, Cloud, BarChart2, Newspaper, Beef, Bell, Wallet,
  Menu, X, Sprout, ChevronRight, MessageSquare, Globe, Check,
  PhoneCall, PawPrint, MapPin, Navigation as NavigationIcon, Loader2
} from 'lucide-react'
import { useI18n, LANGUAGES } from '../context/I18nContext'
import { useLocationContext } from '../context/LocationContext'

const NAV_ITEMS = [
  { id: 'home',           label: 'Home',             labelKn: 'ಮುಖಪುಟ',                  icon: Home,          active: true  },
  { id: 'weather',        label: 'Weather',          labelKn: 'ಹವಾಮಾನ',                  icon: Cloud,         active: true  },
  { id: 'market',         label: 'Markets',          labelKn: 'ಮಾರುಕಟ್ಟೆ',                icon: BarChart2,     active: true  },
  { id: 'news',           label: 'Agri News',        labelKn: 'ಕೃಷಿ ಸುದ್ದಿ',              icon: Newspaper,     active: true  },
  { id: 'dairy',          label: 'Dairy',            labelKn: 'ಹೈನುಗಾರಿಕೆ',              icon: Beef,          active: true  },
  { id: 'finances',       label: 'Finances',         labelKn: 'ಆರ್ಥಿಕ',                  icon: Wallet,        active: true  },
  { id: 'help_contacts',  label: 'Help & Contacts',  labelKn: 'ಸಹಾಯ & ಸಂಪರ್ಕಗಳು',        icon: PhoneCall,     active: true  },
  { id: 'livestock_pets', label: 'Livestock & Pets', labelKn: 'ಜಾನುವಾರು & ಸಾಕುಪ್ರಾಣಿಗಳು', icon: PawPrint,      active: true  },
  { id: 'whatsapp',       label: 'WhatsApp Bot',     labelKn: 'ವಾಟ್ಸಾಪ್ ಬೋಟ್',          icon: MessageSquare, active: true  },
]

function ComingSoonPage({ item }) {
  const { t } = useI18n()
  const Icon = item.icon
  const localizedLabel = t(item.id, item.label)

  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <div className="w-20 h-20 rounded-full bg-green-50 border-2 border-green-100 flex items-center justify-center mb-4">
        <Icon className="w-10 h-10 text-green-400" />
      </div>
      <h2 className="text-xl font-bold text-gray-700 mb-1">{localizedLabel}</h2>
      <p className="text-sm text-gray-400 mb-2">{item.labelKn}</p>
      <span className="text-xs bg-amber-100 text-amber-700 px-3 py-1 rounded-full font-medium">
        🚀 {t('coming_soon')}
      </span>
      <p className="text-xs text-gray-400 mt-4 max-w-xs leading-relaxed">
        This feature is planned for the next sprint. The navigation shell and routing are ready.
      </p>
    </div>
  )
}

export default function Navigation({ activeTab, onTabChange, unreadNotificationsCount = 0, onOpenNotifications, children }) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [langMenuOpen, setLangMenuOpen] = useState(false)
  const [locMenuOpen, setLocMenuOpen] = useState(false)
  const { lang, setLang, t, currentLanguage } = useI18n()
  const {
    location,
    gpsStatus,
    districts,
    needsManualPicker,
    setNeedsManualPicker,
    detectGpsLocation,
    selectDistrict,
  } = useLocationContext()

  const bottomItems = NAV_ITEMS.slice(0, 5)  // first 5 in bottom bar

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top app bar */}
      <header className="bg-white border-b border-gray-200 px-3 sm:px-4 py-2 flex flex-wrap items-center justify-between gap-2 shadow-xs sticky top-0 z-30 min-w-0">
        <div className="flex items-center gap-2 cursor-pointer min-w-0 shrink-0" onClick={() => onTabChange('home')}>
          <div className="w-8 h-8 rounded-lg bg-green-600 flex items-center justify-center shrink-0">
            <Sprout className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-gray-800 leading-tight truncate">{t('app_title')}</h1>
            <p className="text-[10px] text-green-600 leading-tight truncate">{t('app_subtitle')}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Compact Live Location Pill */}
          <div className="relative">
            <button
              onClick={() => {
                setLocMenuOpen(!locMenuOpen)
                setNeedsManualPicker(false)
              }}
              className={`flex items-center gap-1 px-2 py-1.5 rounded-lg text-xs font-semibold border transition-colors max-w-[140px] sm:max-w-[190px] ${
                location
                  ? 'bg-sky-50 hover:bg-sky-100 border-sky-200 text-sky-800'
                  : 'bg-amber-50 hover:bg-amber-100 border-amber-300 text-amber-800'
              }`}
              title={location ? `Active Location: ${location.location_name}` : 'Set your taluk or district'}
              aria-label="Location selector"
            >
              {gpsStatus === 'detecting' ? (
                <Loader2 className="w-3.5 h-3.5 text-sky-600 animate-spin shrink-0" />
              ) : (
                <MapPin className={`w-3.5 h-3.5 shrink-0 ${location ? 'text-sky-600' : 'text-amber-600'}`} />
              )}
              <span className="truncate">
                {location?.location_name || (gpsStatus === 'detecting' ? 'Locating…' : 'Set District')}
              </span>
            </button>

            {(locMenuOpen || needsManualPicker) && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => {
                    setLocMenuOpen(false)
                    setNeedsManualPicker(false)
                  }}
                />
                <div className="absolute right-0 mt-1 w-64 bg-white rounded-xl shadow-xl border border-gray-200 p-2.5 z-50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-gray-400">
                      Farm Location (Taluk / District)
                    </span>
                    <button
                      onClick={() => detectGpsLocation()}
                      className="flex items-center gap-1 text-[11px] font-semibold text-sky-600 hover:text-sky-700"
                      title="Detect live GPS location"
                    >
                      <NavigationIcon className="w-3 h-3" />
                      Use GPS
                    </button>
                  </div>

                  {gpsStatus === 'denied' && !location && (
                    <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5">
                      GPS permission denied. Please pick your district below for local weather & crop advice:
                    </p>
                  )}

                  {location && (
                    <div className="text-[11px] bg-sky-50 border border-sky-100 rounded-lg px-2.5 py-1.5 text-sky-900">
                      <span className="font-semibold">Active:</span> {location.location_name}
                      {location.source === 'gps' && (
                        <span className="ml-1 text-[10px] text-emerald-700 font-semibold">(Live GPS)</span>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="block text-[10px] font-semibold text-gray-500 mb-1">
                      Select District Manually
                    </label>
                    <select
                      value={districts.find(d => d.name === location?.location_name || d.district === location?.district)?.id || ''}
                      onChange={(e) => {
                        if (e.target.value) {
                          selectDistrict(e.target.value)
                          setLocMenuOpen(false)
                        }
                      }}
                      className="w-full text-xs bg-gray-50 border border-gray-300 rounded-lg px-2.5 py-1.5 text-gray-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="">-- Choose District --</option>
                      {districts.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}{d.name_kannada ? ` (${d.name_kannada})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Language Selector Dropdown */}
          <div className="relative">
            <button
              onClick={() => setLangMenuOpen(!langMenuOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 transition-colors shrink-0"
              title={t('select_language')}
              aria-label="Language selector"
            >
              <Globe className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span className="font-bold">{currentLanguage.name}</span>
            </button>

            {langMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setLangMenuOpen(false)} />
                <div className="absolute right-0 mt-1 w-44 bg-white rounded-xl shadow-xl border border-gray-200 py-1.5 z-50">
                  <div className="px-3 py-1 text-[10px] uppercase font-bold text-gray-400">
                    {t('select_language')}
                  </div>
                  {LANGUAGES.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => {
                        setLang(l.code)
                        setLangMenuOpen(false)
                      }}
                      className={`w-full flex items-center justify-between px-3 py-1.5 text-xs text-left transition-colors ${
                        lang === l.code ? 'bg-emerald-50 text-emerald-700 font-bold' : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span>{l.flag}</span>
                        <span>{l.name}</span>
                      </div>
                      {lang === l.code ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <span className="text-[10px] text-gray-400">{l.label}</span>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Quick WhatsApp Bot Shortcut Pill */}
          <button
            onClick={() => onTabChange('whatsapp')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors shrink-0 ${
              activeTab === 'whatsapp'
                ? 'bg-emerald-700 text-white'
                : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
            }`}
            title="Open WhatsApp AI Advisory Simulator"
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden xs:inline">{t('whatsapp')}</span>
          </button>

          {/* Notification Bell Button */}
          <button
            onClick={onOpenNotifications || (() => onTabChange('notifications'))}
            className="relative p-2 text-gray-600 hover:text-green-700 hover:bg-green-50 rounded-lg transition-colors shrink-0"
            aria-label="Notifications"
            title="Open Scheme & Relief Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
                {unreadNotificationsCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setDrawerOpen(true)}
            className="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors shrink-0"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto pb-20">
        {children}
      </main>

      {/* Bottom navigation bar (mobile) */}
      <nav className="fixed bottom-0 left-0 right-0 z-20 bg-white border-t border-gray-200 safe-area-pb">
        <div className="flex items-center justify-around px-2 py-1">
          {bottomItems.map(item => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            const itemLabel = t(item.id, item.label)
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-xl transition-all min-w-[52px]
                  ${isActive ? 'text-green-600 bg-green-50' : 'text-gray-400 hover:text-gray-600'}`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : 'stroke-2'}`} />
                <span className={`text-[9px] font-medium leading-none ${isActive ? 'text-green-600' : ''}`}>
                  {itemLabel}
                </span>
                {isActive && <span className="w-1 h-1 rounded-full bg-green-500" />}
              </button>
            )
          })}
        </div>
      </nav>

      {/* Side drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
          <div className="relative ml-auto w-72 bg-white h-full shadow-2xl flex flex-col">
            {/* Drawer header */}
            <div className="bg-gradient-to-br from-green-700 to-green-600 px-4 py-6">
              <button onClick={() => setDrawerOpen(false)} className="absolute top-3 right-3 text-white/70 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
                  <Sprout className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h2 className="text-white font-bold">{t('app_title')}</h2>
                  <p className="text-green-200 text-xs">{t('app_subtitle')}</p>
                </div>
              </div>
            </div>

            {/* Language Selection Grid inside Drawer */}
            <div className="p-3 bg-gray-50 border-b border-gray-200">
              <p className="text-[11px] font-bold text-gray-500 mb-2 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-emerald-600" />
                <span>{t('select_language')}</span>
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                {LANGUAGES.map((l) => (
                  <button
                    key={l.code}
                    onClick={() => {
                      setLang(l.code)
                    }}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                      lang === l.code
                        ? 'bg-emerald-600 text-white border-emerald-700 font-bold'
                        : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <span>{l.name}</span>
                    <span className="text-[10px] opacity-75">{l.code.toUpperCase()}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Drawer nav items */}
            <nav className="flex-1 py-3 overflow-y-auto">
              {NAV_ITEMS.map(item => {
                const Icon = item.icon
                const isActive = activeTab === item.id
                const itemLabel = t(item.id, item.label)
                const subLabel = item.id === 'help_contacts' || item.id === 'livestock_pets'
                  ? t(`${item.id}_sub`, item.labelKn)
                  : item.labelKn
                return (
                  <button
                    key={item.id}
                    onClick={() => { onTabChange(item.id); setDrawerOpen(false) }}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors
                      ${isActive ? 'bg-green-50 border-r-4 border-green-600 text-green-700' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{itemLabel}</p>
                      <p className="text-xs text-gray-400">{subLabel}</p>
                    </div>
                    {!item.active && (
                      <span className="text-[10px] bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded font-medium">Soon</span>
                    )}
                    <ChevronRight className="w-4 h-4 text-gray-300" />
                  </button>
                )
              })}
            </nav>

            <div className="px-4 py-3 border-t text-xs text-gray-400 text-center">
              Karnataka Farmer Advisory · Indic Multilingual
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export { ComingSoonPage, NAV_ITEMS }
