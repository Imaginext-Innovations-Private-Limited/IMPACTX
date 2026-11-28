import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AlertTriangle, Map, Thermometer, Camera, Navigation, BarChart3, Bell } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import FloodMap from './pages/FloodMap'
import HeatwaveMap from './pages/HeatwaveMap'
import AlertsPage from './pages/AlertsPage'
import ReportPage from './pages/ReportPage'
import RouteFinder from './pages/RouteFinder'
import AnalyticsPage from './pages/AnalyticsPage'
import { useAlertStore } from './store/alertStore'

const NAV_ITEMS = [
  { to: '/',          label: 'Dashboard',     icon: BarChart3 },
  { to: '/flood-map', label: 'Flood Map',     icon: Map },
  { to: '/heat-map',  label: 'Heatwave',      icon: Thermometer },
  { to: '/alerts',    label: 'Alerts',        icon: Bell },
  { to: '/report',    label: 'Report',        icon: Camera },
  { to: '/route',     label: 'Safe Route',    icon: Navigation },
  { to: '/analytics', label: 'Analytics',     icon: BarChart3 },
]

export default function App() {
  const { criticalCount } = useAlertStore()

  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
          {/* Logo */}
          <div className="p-5 border-b border-gray-800">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <AlertTriangle size={20} className="text-white" />
              </div>
              <div>
                <p className="font-bold text-sm text-white leading-tight">Urban Early</p>
                <p className="text-xs text-blue-400">Warning System</p>
              </div>
            </div>
          </div>

          {/* Nav links */}
          <nav className="flex-1 p-3 space-y-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`
                }
              >
                <Icon size={16} />
                {label}
                {label === 'Alerts' && criticalCount > 0 && (
                  <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 pulse-critical">
                    {criticalCount}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="p-4 border-t border-gray-800 text-xs text-gray-500 text-center">
            v1.0.0 · Live Data
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto bg-gray-950">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/flood-map"  element={<FloodMap />} />
            <Route path="/heat-map"   element={<HeatwaveMap />} />
            <Route path="/alerts"     element={<AlertsPage />} />
            <Route path="/report"     element={<ReportPage />} />
            <Route path="/route"      element={<RouteFinder />} />
            <Route path="/analytics"  element={<AnalyticsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
