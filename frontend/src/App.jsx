import React, { useState, useEffect } from 'react'
import CommodityTicker from './components/CommodityTicker'
import CommodityAnalyticsModal from './components/CommodityAnalyticsModal'
import VoiceAssistant from './components/VoiceAssistant'
import NotificationDrawer from './components/NotificationDrawer'
import Navigation, { ComingSoonPage, NAV_ITEMS } from './components/Navigation'
import WhatsAppSimulatorModal from './components/WhatsAppSimulatorModal'
import HomePage from './pages/HomePage'
import WeatherPage from './pages/WeatherPage'
import MarketsPage from './pages/MarketsPage'
import NewsPage from './pages/NewsPage'
import DairyPage from './pages/DairyPage'
import FinancePage from './pages/FinancePage'
import HelpContactsPage from './pages/HelpContactsPage'
import LivestockPetsPage from './pages/LivestockPetsPage'
import { notificationApi } from './api/client'
import { I18nProvider, useI18n } from './context/I18nContext'
import { LocationProvider } from './context/LocationContext'

function AppContent() {
  const [activeTab, setActiveTab] = useState('home')
  const [selectedCommodityModal, setSelectedCommodityModal] = useState(null)
  const [voiceQueryTrigger, setVoiceQueryTrigger] = useState(null)
  const [isNotificationOpen, setIsNotificationOpen] = useState(false)
  const [unreadNotificationsCount, setUnreadNotificationsCount] = useState(0)
  const [isWhatsAppModalOpen, setIsWhatsAppModalOpen] = useState(false)
  const { t } = useI18n()

  // Fetch initial unread notifications count
  useEffect(() => {
    notificationApi.getUnreadCount()
      .then(res => setUnreadNotificationsCount(res.data.unread_count || 0))
      .catch(() => {})
  }, [])

  const handleSelectCommodity = (commodityName) => {
    setSelectedCommodityModal(commodityName)
  }

  const handleAskVoice = (prompt) => {
    setVoiceQueryTrigger({ prompt, timestamp: Date.now() })
  }

  const handleTabChange = (tabId) => {
    if (tabId === 'whatsapp') {
      setIsWhatsAppModalOpen(true)
    } else {
      setActiveTab(tabId)
    }
  }

  const renderPage = () => {
    switch (activeTab) {
      case 'home':
        return (
          <HomePage
            onSelectCommodity={handleSelectCommodity}
            onNavigate={handleTabChange}
          />
        )
      case 'weather':
        return <WeatherPage />
      case 'market':
        return (
          <MarketsPage
            defaultCommodity={selectedCommodityModal || 'Areca Nut (Chali)'}
          />
        )
      case 'news':
        return <NewsPage onAskVoice={handleAskVoice} />
      case 'dairy':
        return <DairyPage onAskVoice={handleAskVoice} />
      case 'finances':
        return <FinancePage onAskVoice={handleAskVoice} />
      case 'help_contacts':
        return <HelpContactsPage />
      case 'livestock_pets':
        return <LivestockPetsPage />
      case 'whatsapp':
        return (
          <div className="py-6 px-4 max-w-lg mx-auto text-center">
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 space-y-3">
              <div className="w-12 h-12 bg-emerald-600 rounded-full flex items-center justify-center mx-auto text-white">
                <span className="text-xl">💬</span>
              </div>
              <h2 className="text-lg font-bold text-gray-800">{t('whatsapp_sim_title')}</h2>
              <p className="text-xs text-gray-600 leading-relaxed">
                {t('whatsapp_sim_sub')}
              </p>
              <button
                onClick={() => setIsWhatsAppModalOpen(true)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors"
              >
                {t('open_whatsapp_sim')}
              </button>
            </div>
          </div>
        )
      default: {
        const item = NAV_ITEMS.find((n) => n.id === activeTab) || {
          id: activeTab,
          label: activeTab,
          labelKn: '',
          icon: () => null,
        }
        return <ComingSoonPage item={item} />
      }
    }
  }

  return (
    <Navigation
      activeTab={activeTab}
      onTabChange={handleTabChange}
      unreadNotificationsCount={unreadNotificationsCount}
      onOpenNotifications={() => setIsNotificationOpen(false || true)}
    >
      {/* Sticky ticker at very top (inside shell, below app header) */}
      <CommodityTicker onSelectCommodity={handleSelectCommodity} />

      {/* Main page content */}
      {renderPage()}

      {/* Interactive 6-Year Historical Analytics Modal when any commodity chip or row is clicked */}
      {selectedCommodityModal && (
        <CommodityAnalyticsModal
          commodityName={selectedCommodityModal}
          onClose={() => setSelectedCommodityModal(null)}
        />
      )}

      {/* WhatsApp AI Simulator Modal wired to /api/whatsapp/simulate */}
      <WhatsAppSimulatorModal
        isOpen={isWhatsAppModalOpen}
        onClose={() => setIsWhatsAppModalOpen(false)}
      />

      {/* Slide-over Notification Drawer for Schemes, Relief & Insurance */}
      <NotificationDrawer
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
        onUnreadCountChange={setUnreadNotificationsCount}
      />

      {/* Floating multilingual voice assistant (Sprint 1 component, always available) */}
      <VoiceAssistant
        initialQuery={voiceQueryTrigger?.prompt}
        autoOpen={!!voiceQueryTrigger}
      />
    </Navigation>
  )
}

export default function App() {
  return (
    <I18nProvider>
      <LocationProvider>
        <AppContent />
      </LocationProvider>
    </I18nProvider>
  )
}
