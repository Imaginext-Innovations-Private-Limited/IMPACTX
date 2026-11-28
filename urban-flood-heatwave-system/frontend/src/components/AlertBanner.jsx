import { AlertTriangle, X } from 'lucide-react'
import { clsx } from 'clsx'

const SEVERITY_STYLES = {
  CRITICAL: 'bg-red-950 border-red-600 text-red-200',
  WARNING:  'bg-orange-950 border-orange-600 text-orange-200',
  INFO:     'bg-blue-950 border-blue-600 text-blue-200',
}

export function AlertBanner({ alert, onDismiss }) {
  const style = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.INFO
  return (
    <div className={clsx(
      'alert-banner flex items-start gap-3 p-4 rounded-lg border',
      style
    )}>
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm">{alert.title}</p>
        <p className="text-xs opacity-80 mt-0.5">{alert.message}</p>
        <p className="text-xs opacity-50 mt-1">
          {alert.city} · {new Date(alert.created_at).toLocaleTimeString()}
        </p>
      </div>
      {onDismiss && (
        <button onClick={() => onDismiss(alert.id)} className="shrink-0 opacity-50 hover:opacity-100">
          <X size={16} />
        </button>
      )}
    </div>
  )
}
