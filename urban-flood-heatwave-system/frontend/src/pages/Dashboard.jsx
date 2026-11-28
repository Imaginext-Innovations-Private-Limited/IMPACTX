import { useEffect, useState } from 'react'
import { Droplets, Thermometer, AlertTriangle, Users, RefreshCw } from 'lucide-react'
import { StatCard } from '../components/StatCard'
import { AlertBanner } from '../components/AlertBanner'
import FloodRiskMap from '../components/FloodRiskMap'
import { RiskBadge } from '../components/RiskBadge'
import { floodApi, alertsApi } from '../services/api'
import { useAlertStore } from '../store/alertStore'

// Mock city coordinates for demo
const DEMO_ZONES = [
  { zone_id: 'z1', name: 'Dharavi', city: 'Mumbai', latitude: 19.040, longitude: 72.854, risk_score: 0.82, risk_level: 'CRITICAL', is_flooded: true },
  { zone_id: 'z2', name: 'Kurla', city: 'Mumbai', latitude: 19.072, longitude: 72.880, risk_score: 0.65, risk_level: 'HIGH', is_flooded: false },
  { zone_id: 'z3', name: 'Worli', city: 'Mumbai', latitude: 19.017, longitude: 72.816, risk_score: 0.38, risk_level: 'MEDIUM', is_flooded: false },
  { zone_id: 'z4', name: 'Bandra', city: 'Mumbai', latitude: 19.054, longitude: 72.841, risk_score: 0.15, risk_level: 'LOW', is_flooded: false },
  { zone_id: 'z5', name: 'Andheri', city: 'Mumbai', latitude: 19.113, longitude: 72.868, risk_score: 0.72, risk_level: 'HIGH', is_flooded: false },
]

const DEMO_ALERTS = [
  { id: 1, alert_type: 'FLOOD', severity: 'CRITICAL', city: 'Mumbai', title: '🚨 CRITICAL Flood Warning – Dharavi', message: 'CRITICAL flood warning for Dharavi. Evacuate immediately. Do NOT walk or drive through flooded streets.', created_at: new Date().toISOString() },
  { id: 2, alert_type: 'HEATWAVE', severity: 'WARNING', city: 'Mumbai', title: '🌡️ Heatwave Alert – Mumbai', message: 'Heatwave conditions in Mumbai. Feels like 46.2°C. Find a cooling centre near you.', created_at: new Date().toISOString() },
]

export default function Dashboard() {
  const [zones, setZones] = useState(DEMO_ZONES)
  const [loading, setLoading] = useState(false)
  const { alerts, setAlerts } = useAlertStore()

  useEffect(() => {
    setAlerts(DEMO_ALERTS)
    // Try to load live data (only override demo if API returns results)
    floodApi.getZones().then(r => { if (r.data?.length) setZones(r.data) }).catch(() => {})
    alertsApi.getActive().then(r => { if (r.data?.length) setAlerts(r.data) }).catch(() => {})
  }, [])

  const critical = zones.filter(z => z.risk_level === 'CRITICAL').length
  const high = zones.filter(z => z.risk_level === 'HIGH').length
  const flooded = zones.filter(z => z.is_flooded).length

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Command Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Real-time flood & heatwave monitoring · Mumbai</p>
        </div>
        <button
          onClick={() => { setLoading(true); setTimeout(() => setLoading(false), 1000) }}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Alert banners */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.slice(0, 3).map(a => (
            <AlertBanner key={a.id} alert={a} />
          ))}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Critical Zones" value={critical} subtitle="Evacuate immediately" icon={AlertTriangle} color="red" />
        <StatCard title="High Risk Zones" value={high} subtitle="Avoid if possible" icon={Droplets} color="orange" />
        <StatCard title="Active Floods" value={flooded} subtitle="Streets submerged" icon={Droplets} color="blue" />
        <StatCard title="Heat Index" value="46.2°C" subtitle="Feels like in Dharavi" icon={Thermometer} color="orange" />
      </div>

      {/* Map + Zone list */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden" style={{ height: '420px' }}>
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-semibold text-sm text-white">Live Flood Risk Map</h2>
            <div className="flex gap-3 text-xs text-gray-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"/>Critical</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block"/>High</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500 inline-block"/>Medium</span>
            </div>
          </div>
          <FloodRiskMap zones={zones} center={[19.0760, 72.8777]} zoom={12} />
        </div>

        {/* Zone list */}
        <div className="bg-gray-900 rounded-xl border border-gray-800">
          <div className="px-4 py-3 border-b border-gray-800">
            <h2 className="font-semibold text-sm text-white">Zone Risk Summary</h2>
          </div>
          <div className="p-3 space-y-2 overflow-y-auto" style={{ maxHeight: '360px' }}>
            {zones.sort((a,b) => b.risk_score - a.risk_score).map(zone => (
              <div key={zone.zone_id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-white">{zone.name}</p>
                  <p className="text-xs text-gray-400">{(zone.risk_score * 100).toFixed(0)}% risk</p>
                </div>
                <RiskBadge level={zone.risk_level} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
