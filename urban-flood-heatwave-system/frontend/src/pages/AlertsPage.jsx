import { useEffect } from 'react'
import { Bell, Trash2 } from 'lucide-react'
import { AlertBanner } from '../components/AlertBanner'
import { alertsApi } from '../services/api'
import { useAlertStore } from '../store/alertStore'

const DEMO_ALERTS = [
  { id: 1, alert_type: 'FLOOD', severity: 'CRITICAL', city: 'Mumbai', zone_id: 'z1', title: '🚨 CRITICAL Flood Warning – Dharavi', message: 'CRITICAL flood warning for Dharavi. Evacuate immediately. Do NOT walk or drive through flooded streets.', created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 6*3600000).toISOString() },
  { id: 2, alert_type: 'HEATWAVE', severity: 'WARNING', city: 'Mumbai', title: '🌡️ Heatwave Alert – Mumbai', message: 'Heatwave conditions in Mumbai. Feels like 46.2°C. Find a cooling centre near you.', created_at: new Date().toISOString(), expires_at: new Date(Date.now() + 4*3600000).toISOString() },
  { id: 3, alert_type: 'FLOOD', severity: 'WARNING', city: 'Mumbai', zone_id: 'z2', title: '⚠️ Flood Risk Alert – Kurla', message: 'Flood risk in Kurla is HIGH (score: 65%). Avoid low-lying streets. Use the app to find safe routes.', created_at: new Date(Date.now() - 1800000).toISOString(), expires_at: new Date(Date.now() + 3*3600000).toISOString() },
  { id: 4, alert_type: 'FLOOD', severity: 'WARNING', city: 'Mumbai', zone_id: 'z5', title: '⚠️ Flood Risk Alert – Andheri', message: 'Flood risk in Andheri is HIGH. Waterlogging reported near subway exits.', created_at: new Date(Date.now() - 3600000).toISOString(), expires_at: new Date(Date.now() + 2*3600000).toISOString() },
]

export default function AlertsPage() {
  const { alerts, setAlerts } = useAlertStore()

  useEffect(() => {
    setAlerts(DEMO_ALERTS)
    alertsApi.getActive().then(r => { if (r.data?.length) setAlerts(r.data) }).catch(() => {})
  }, [])

  const dismiss = async id => {
    try { await alertsApi.deactivate(id) } catch {}
    setAlerts(alerts.filter(a => a.id !== id))
  }

  const critical = alerts.filter(a => a.severity === 'CRITICAL')
  const others = alerts.filter(a => a.severity !== 'CRITICAL')

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Bell size={22}/> Active Alerts</h1>
          <p className="text-sm text-gray-400 mt-1">{alerts.length} active alert{alerts.length !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {critical.length > 0 && (
        <div>
          <h2 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3">🚨 Critical</h2>
          <div className="space-y-3">
            {critical.map(a => <AlertBanner key={a.id} alert={a} onDismiss={dismiss} />)}
          </div>
        </div>
      )}

      {others.length > 0 && (
        <div>
          <h2 className="text-xs font-bold text-orange-400 uppercase tracking-wider mb-3">⚠ Warnings</h2>
          <div className="space-y-3">
            {others.map(a => <AlertBanner key={a.id} alert={a} onDismiss={dismiss} />)}
          </div>
        </div>
      )}

      {alerts.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <Bell size={40} className="mx-auto mb-3 opacity-30" />
          <p>No active alerts. All clear!</p>
        </div>
      )}
    </div>
  )
}
