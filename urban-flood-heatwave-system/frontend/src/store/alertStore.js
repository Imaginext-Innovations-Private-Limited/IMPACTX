import { create } from 'zustand'

export const useAlertStore = create((set, get) => ({
  alerts: [],
  criticalCount: 0,

  setAlerts: (alerts) => set({
    alerts,
    criticalCount: alerts.filter(a => a.severity === 'CRITICAL').length,
  }),

  addAlert: (alert) => set(state => {
    const alerts = [alert, ...state.alerts]
    return { alerts, criticalCount: alerts.filter(a => a.severity === 'CRITICAL').length }
  }),
}))
